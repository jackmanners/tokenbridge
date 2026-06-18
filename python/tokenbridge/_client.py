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

    # Fetch data — three equivalent styles:
    tb.fetch("p001", "sleep", start, end)                   # canonical, uses tb.provider
    tb.google.fetch("p001", "sleep", start, end)            # provider namespace
    tb.fetch("p001", "sleep", start, end, provider="withings")  # one-off override

    # Change default provider mid-script
    tb.provider = "withings"
    tb.fetch("p001", "sleep", start, end)                   # now uses Withings

    # Efficient: get token once when fetching multiple types for the same user
    token = tb.get_token("p001")
    tb.fetch("p001", "sleep", start, end, token=token)
    tb.fetch("p001", "steps", start, end, token=token)
"""

import os
from typing import Optional

import requests
from dotenv import load_dotenv


class TokenBridge:
    """
    Client for the TokenBridge token management service.

    Set tb.provider once at the top of your script, then call tb.fetch() freely.
    Use tb.google / tb.withings as namespaced shortcuts — they always use that
    provider regardless of tb.provider.

    See docs/providers.md for all supported providers and data type IDs.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        env_file: str = ".env",
        provider: str = "google-health",
    ):
        load_dotenv(env_file)
        self.url      = (url     or os.environ.get("TOKENBRIDGE_URL",     "")).rstrip("/")
        self.api_key  =  api_key or os.environ.get("TOKENBRIDGE_API_KEY", "")
        self.provider = provider   # default provider; change freely mid-script

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
        """Namespace for Google Health — tb.google.fetch(...) always uses 'google-health'."""
        return _ProviderProxy(self, "google-health")

    @property
    def withings(self) -> "_ProviderProxy":
        """Namespace for Withings — tb.withings.fetch(...) always uses 'withings'."""
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
        """
        Fetch health data for a participant.

        data_type is the kebab-case type ID from the provider — e.g. "sleep",
        "steps", "heart-rate-variability".  See docs/providers.md for the full
        list, or:
            from tokenbridge.providers.google_health import DATA_TYPES
            print(list(DATA_TYPES))

        provider defaults to tb.provider (set at init or changed mid-script).
        Pass provider= to override for a single call without changing the default.

        Pass token= to skip a TokenBridge round-trip when fetching multiple
        types for the same user:
            token = tb.get_token("p001")
            tb.fetch("p001", "sleep", start, end, token=token)
            tb.fetch("p001", "steps", start, end, token=token)
        """
        p = provider or self.provider
        return self._get_provider(p).fetch(user_id, data_type, start_date, end_date, token=token)

    # ── Auth URL helpers ──────────────────────────────────────────────────────

    def auth_url(self, user_id: str, provider: Optional[str] = None) -> str:
        """
        Return the URL a participant should visit to authorise their account.
        Once they complete the OAuth flow, tokens are stored automatically.
        Uses tb.provider by default.
        """
        return f"{self.url}/auth-start?provider={provider or self.provider}&user_id={user_id}"

    def auth_urls(
        self, user_ids: list[str], provider: Optional[str] = None
    ) -> dict[str, str]:
        """Return {user_id: auth_url} for a list of participants."""
        p = provider or self.provider
        return {uid: self.auth_url(uid, p) for uid in user_ids}

    # ── Token management ──────────────────────────────────────────────────────

    def get_token(self, user_id: str, provider: Optional[str] = None) -> str:
        """
        Fetch a valid access token for a participant.
        TokenBridge refreshes automatically if the token is close to expiry.

        Useful when fetching multiple data types for the same user — call this
        once and pass token= to tb.fetch() to avoid repeated round-trips:
            token = tb.get_token("p001")
            sleep = tb.fetch("p001", "sleep", start, end, token=token)
            steps = tb.fetch("p001", "steps", start, end, token=token)
        """
        return self._token_response(user_id, provider or self.provider)["access_token"]

    def token_status(self, user_id: str, provider: Optional[str] = None) -> dict:
        """
        Return token metadata without exposing the raw token:
          expires_at  — ISO 8601 string
          refreshed   — bool, True if the token was refreshed on this call
          scopes      — list of granted OAuth scopes
        """
        data = self._token_response(user_id, provider or self.provider)
        return {k: data[k] for k in ("expires_at", "refreshed", "scopes") if k in data}

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_provider(self, provider_id: str):
        """Lazy-init and cache provider instances."""
        if provider_id not in self._provider_cache:
            if provider_id == "google-health":
                from tokenbridge.providers.google_health import GoogleHealth
                self._provider_cache[provider_id] = GoogleHealth(self)
            elif provider_id == "withings":
                from tokenbridge.providers.withings import Withings
                self._provider_cache[provider_id] = Withings(self)
            else:
                raise ValueError(
                    f"Unknown provider {provider_id!r}. "
                    "See docs/providers.md for supported providers."
                )
        return self._provider_cache[provider_id]

    def _token_response(self, user_id: str, provider: str) -> dict:
        resp = requests.post(
            f"{self.url}/token",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"provider": provider, "user_id": user_id},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if "access_token" not in data:
            raise RuntimeError(f"No access_token in response: {resp.text}")
        return data


class _ProviderProxy:
    """
    Thin namespace object that pre-binds a provider to tb.fetch().

    tb.google.fetch(...)   == tb.fetch(..., provider="google-health")
    tb.withings.fetch(...) == tb.fetch(..., provider="withings")

    Any other attribute is forwarded to the underlying provider instance,
    so tb.google.summary(...) and tb.google.data_completeness(...) also work.
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
        return self._tb.fetch(
            user_id, data_type, start_date, end_date,
            provider=self._provider_id, token=token,
        )

    def __getattr__(self, name: str):
        """Forward anything else (summary, data_completeness, …) to the provider."""
        return getattr(self._tb._get_provider(self._provider_id), name)

    def __repr__(self) -> str:
        return f"<TokenBridge provider={self._provider_id!r}>"
