"""
TokenBridge platform client.

Handles auth URLs, token retrieval, and health data fetching via providers.

Quick start:
    from tokenbridge import TokenBridge

    tb = TokenBridge()                          # reads .env
    tb.provider = "google-health"               # set once at top of script (default)

    # Auth
    tb.auth_url("p001")                         # send to participant
    tb.auth_urls(["p001", "p002", "p003"])      # batch

    # Fetch — three equivalent styles:
    tb.fetch("p001", "sleep", start, end)                      # canonical
    tb.google.fetch("p001", "sleep", start, end)               # provider namespace
    tb.fetch("p001", "sleep", start, end, provider="withings") # one-off override

    # Change default provider mid-script
    tb.provider = "withings"
    tb.fetch("p001", "sleep", start, end)   # now uses Withings

    # Token reuse: one round-trip for multiple types
    token = tb.get_token("p001")
    tb.fetch("p001", "sleep", start, end, token=token)
    tb.fetch("p001", "steps", start, end, token=token)
"""

import os
from typing import Optional

import requests
from dotenv import load_dotenv


class TokenBridge:
    """Client for the TokenBridge token management service.

    Responsible for auth URL generation, token retrieval, and routing data
    requests to the correct provider.  Set `tb.provider` once at the top of
    your script; use `tb.fetch()` for all data fetching.

    Use `tb.google` / `tb.withings` as provider-namespaced shortcuts — they
    pre-bind the provider and forward every call to the underlying provider
    instance, so `tb.google.summary(...)` also works.

    See `docs/providers/index.md` for supported providers and data type IDs.

    Attributes:
        provider: Default provider ID used by `fetch()`, `auth_url()`,
            `get_token()`, and `token_status()` when `provider=` is not
            passed explicitly.  Change at any time to switch providers
            mid-script.  Default: `"google-health"`.
        google: Provider namespace proxy pre-bound to `"google-health"`.
        withings: Provider namespace proxy pre-bound to `"withings"`.

    Example:
        ```python
        tb = TokenBridge()
        tb.provider = "google-health"

        print(tb.auth_url("p001"))
        sleep = tb.fetch("p001", "sleep", "2026-05-01", "2026-06-18")
        steps = tb.fetch("p001", "steps", "2026-05-01", "2026-06-18")

        # One token for multiple fetches
        token = tb.get_token("p001")
        sleep = tb.fetch("p001", "sleep", start, end, token=token)
        hrv   = tb.fetch("p001", "heart-rate-variability", start, end, token=token)
        ```
    """

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        env_file: str = ".env",
        provider: str = "google-health",
    ):
        """Initialise the TokenBridge client.

        Reads `TOKENBRIDGE_URL` and `TOKENBRIDGE_API_KEY` from environment
        variables (or the specified `.env` file).  Explicit arguments take
        precedence over environment variables.

        Args:
            url: TokenBridge base URL, e.g.
                `"https://abcdef.supabase.co/functions/v1"`.
                Reads `TOKENBRIDGE_URL` from env if not provided.
            api_key: TokenBridge API key.
                Reads `TOKENBRIDGE_API_KEY` from env if not provided.
            env_file: Path to the `.env` file to load.  Default `".env"`.
            provider: Default provider ID.  Default `"google-health"`.

        Raises:
            RuntimeError: If `TOKENBRIDGE_URL` or `TOKENBRIDGE_API_KEY` cannot
                be resolved from arguments or environment.

        Example:
            ```python
            # Reads .env automatically
            tb = TokenBridge()

            # Explicit credentials (no .env needed)
            tb = TokenBridge(
                url="https://abcdef.supabase.co/functions/v1",
                api_key="my-key",
            )
            ```
        """
        load_dotenv(env_file)
        self.url      = (url     or os.environ.get("TOKENBRIDGE_URL",     "")).rstrip("/")
        self.api_key  =  api_key or os.environ.get("TOKENBRIDGE_API_KEY", "")
        self.provider = provider

        if not self.url:
            raise RuntimeError(
                "TOKENBRIDGE_URL not set — run `python -m tokenbridge` to configure."
            )
        if not self.api_key:
            raise RuntimeError(
                "TOKENBRIDGE_API_KEY not set — run `python -m tokenbridge` to configure."
            )

        self._provider_cache: dict = {}

    # ── Provider namespaces ───────────────────────────────────────────────────

    @property
    def google(self) -> "_ProviderProxy":
        """Provider namespace pre-bound to `"google-health"`.

        All calls through this proxy use Google Health regardless of
        `tb.provider`.  Forwards any attribute not defined on the proxy to
        the underlying `GoogleHealth` instance, so `tb.google.summary(...)`,
        `tb.google.data_completeness(...)`, etc. all work.

        Example:
            ```python
            tb.google.fetch("p001", "sleep", start, end)
            tb.google.summary("p001", start, end)
            tb.google.data_completeness(["p001", "p002"], start, end)
            ```
        """
        return _ProviderProxy(self, "google-health")

    @property
    def oura(self) -> "_ProviderProxy":
        """Provider namespace pre-bound to ``"oura"``.

        Example:
            ```python
            tb.oura.fetch("p001", "sleep", start, end)
            tb.oura.fetch("p001", "daily-readiness", start, end)
            ```
        """
        return _ProviderProxy(self, "oura")

    @property
    def withings(self) -> "_ProviderProxy":
        """Provider namespace pre-bound to `"withings"`.

        Example:
            ```python
            tb.withings.fetch("p001", "sleep", start, end)
            ```
        """
        return _ProviderProxy(self, "withings")

    # ── Health data ───────────────────────────────────────────────────────────

    def fetch(
        self,
        user_id: str,
        data_type: str,
        start_date: str,
        end_date: str,
        *,
        provider: Optional[str] = None,
        token: Optional[str] = None,
    ) -> list[dict]:
        """Fetch health data for a participant.

        Routes to the appropriate provider and returns a flat list of records.
        Each record is a dict with dot-notation keys for nested API fields,
        e.g. `startTime.seconds`.

        `data_type` is the kebab-case type ID — e.g. `"sleep"`, `"steps"`,
        `"heart-rate-variability"`.  See `docs/providers/index.md` or:

        ```python
        from tokenbridge.providers.google_health import DATA_TYPES
        print(list(DATA_TYPES))
        ```

        Args:
            user_id: TokenBridge participant ID.
            data_type: Kebab-case data type ID.
            start_date: Start of date range, `"YYYY-MM-DD"`.
            end_date: End of date range, `"YYYY-MM-DD"`.
            provider: Override the session default (`tb.provider`) for this
                call only.  Does not change `tb.provider`.
            token: Pre-fetched access token.  Pass when fetching multiple
                types for the same participant to avoid repeated TokenBridge
                round-trips.  Obtain with `tb.get_token(user_id)`.

        Returns:
            List of dicts, one per data point.  Returns an empty list if no
            data exists for the period.

        Example:
            ```python
            # Basic
            sleep = tb.fetch("p001", "sleep", "2026-05-01", "2026-06-18")

            # Token reuse
            token = tb.get_token("p001")
            sleep = tb.fetch("p001", "sleep",  start, end, token=token)
            steps = tb.fetch("p001", "steps",  start, end, token=token)
            hrv   = tb.fetch("p001", "heart-rate-variability", start, end, token=token)

            # One-off provider override
            tb.fetch("p001", "sleep", start, end, provider="withings")
            ```
        """
        p = provider or self.provider
        return self._get_provider(p).fetch(user_id, data_type, start_date, end_date, token=token)

    # ── Auth URL helpers ──────────────────────────────────────────────────────

    def auth_url(self, user_id: str, provider: Optional[str] = None) -> str:
        """Return the auth URL for one participant.

        Send this URL to the participant.  Once they complete the OAuth flow,
        their token is stored and you can fetch data immediately.

        Args:
            user_id: TokenBridge participant ID.
            provider: Provider to authorise.  Defaults to `tb.provider`.

        Returns:
            Full auth URL as a string.

        Example:
            ```python
            url = tb.auth_url("participant-001")
            print(f"Please visit: {url}")
            ```
        """
        return f"{self.url}/auth-start?provider={provider or self.provider}&user_id={user_id}"

    def auth_urls(
        self, user_ids: list[str], provider: Optional[str] = None
    ) -> dict[str, str]:
        """Return auth URLs for multiple participants.

        Args:
            user_ids: List of TokenBridge participant IDs.
            provider: Provider to authorise.  Defaults to `tb.provider`.

        Returns:
            Dict mapping `user_id` to auth URL.

        Example:
            ```python
            urls = tb.auth_urls(["p001", "p002", "p003"])
            for uid, url in urls.items():
                print(f"{uid}: {url}")
            ```
        """
        p = provider or self.provider
        return {uid: self.auth_url(uid, p) for uid in user_ids}

    # ── Token management ──────────────────────────────────────────────────────

    def get_token(self, user_id: str, provider: Optional[str] = None) -> str:
        """Fetch a valid access token for a participant.

        TokenBridge refreshes automatically if the token is within 5 minutes
        of expiry.

        You rarely need this directly — `tb.fetch()` handles it internally.
        Use it when fetching multiple data types for the same participant to
        avoid one TokenBridge round-trip per call:

        Args:
            user_id: TokenBridge participant ID.
            provider: Provider.  Defaults to `tb.provider`.

        Returns:
            OAuth access token string.

        Example:
            ```python
            token = tb.get_token("p001")
            sleep = tb.fetch("p001", "sleep",  start, end, token=token)
            steps = tb.fetch("p001", "steps",  start, end, token=token)
            hrv   = tb.fetch("p001", "heart-rate-variability", start, end, token=token)
            ```
        """
        return self._token_response(user_id, provider or self.provider)["access_token"]

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_provider(self, provider_id: str):
        """Lazy-init and cache provider instances."""
        if provider_id not in self._provider_cache:
            if provider_id == "google-health":
                from tokenbridge.providers.google_health import GoogleHealth
                self._provider_cache[provider_id] = GoogleHealth(self)
            elif provider_id == "oura":
                from tokenbridge.providers.oura import Oura
                self._provider_cache[provider_id] = Oura(self)
            elif provider_id == "withings":
                from tokenbridge.providers.withings import Withings
                self._provider_cache[provider_id] = Withings(self)
            else:
                raise ValueError(
                    f"Unknown provider {provider_id!r}. "
                    "See docs/providers/index.md for supported providers."
                )
        return self._provider_cache[provider_id]

    def _token_response(self, user_id: str, provider: str) -> dict:
        resp = requests.post(
            f"{self.url}/token",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"provider": provider, "user_id": user_id},
            timeout=15,
        )
        if resp.status_code == 404:
            auth_url = self.auth_url(user_id, provider)
            raise RuntimeError(
                f"No token found for user '{user_id}' (provider: {provider}). "
                f"Send them this link to authorise: {auth_url}"
            )
        if resp.status_code == 401:
            raise RuntimeError(
                f"Token for '{user_id}' has expired and cannot be refreshed — "
                f"they need to re-authorise: {self.auth_url(user_id, provider)}"
            )
        resp.raise_for_status()
        data = resp.json()
        if "access_token" not in data:
            raise RuntimeError(f"Unexpected response from TokenBridge: {resp.text}")
        return data


class _ProviderProxy:
    """Thin namespace object that pre-binds a provider to `tb.fetch()`.

    `tb.google.fetch(...)` is equivalent to `tb.fetch(..., provider="google-health")`.
    Any attribute not defined on the proxy is forwarded to the underlying
    provider instance — so `tb.google.summary(...)` also works.

    This class is not intended to be instantiated directly.
    Access it via `tb.google` or `tb.withings`.
    """

    def __init__(self, tb: TokenBridge, provider_id: str):
        object.__setattr__(self, "_tb",          tb)
        object.__setattr__(self, "_provider_id", provider_id)

    def fetch(
        self,
        user_id: str,
        data_type: str,
        start_date: str,
        end_date: str,
        *,
        token=None,
    ) -> list[dict]:
        """Fetch data using this proxy's pre-bound provider.

        Args:
            user_id: TokenBridge participant ID.
            data_type: Kebab-case data type ID.
            start_date: `"YYYY-MM-DD"`.
            end_date: `"YYYY-MM-DD"`.
            token: Pre-fetched access token.

        Returns:
            List of dicts, one per data point.
        """
        return self._tb.fetch(
            user_id, data_type, start_date, end_date,
            provider=self._provider_id, token=token,
        )

    def __getattr__(self, name: str):
        """Forward anything else (summary, data_completeness, …) to the provider."""
        return getattr(self._tb._get_provider(self._provider_id), name)

    def __repr__(self) -> str:
        return f"<TokenBridge provider={self._provider_id!r}>"
