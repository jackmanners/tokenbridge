"""SleepScan + Clinic token sources for TokenBridge Withings data fetching.

NOTE: Personal addon/bandaid — not part of tokenbridge proper.
      Easy to remove: just delete this file and the _sleepscan_token()
      call in _client.py.

Usage via tb.fetch():
    tb = TokenBridge()   # reads SLEEPSCAN_API_KEY / CLINIC_SLEEPSCAN_KEY from .env
    records = tb.fetch("email@lab.com", "sleep-summary", start, end,
                       provider="withings", sleepscan=True)

Direct usage:
    from tokenbridge.sleepscan import SleepScan
    ss    = SleepScan(api_key="...")
    token = ss.get_token(email="participant@example.com")
"""

import os

import requests

from tokenbridge.providers.withings import _fetch_all, DATA_TYPES

# ── SleepScan ──────────────────────────────────────────────────────────────────

class SleepScan:
    """Retrieves Withings access tokens via the SleepScan API.

    Tries SleepScan first; falls back to the Clinic API if SleepScan fails
    and CLINIC_SLEEPSCAN_KEY is set.

    Args:
        api_key:      SleepScan API key (X-API-Key header).
        base_url:     SleepScan base URL. Defaults to https://sleepscan.app.
        clinic_key:   Clinic API bearer token. Reads CLINIC_SLEEPSCAN_KEY
                      from env if not provided.
        clinic_url:   Clinic API base URL. Defaults to
                      https://clinic.sleepscan.app/api.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://sleepscan.app",
        clinic_key: str | None = None,
        clinic_url: str = "https://clinic.sleepscan.app/api",
    ):
        self.api_key    = api_key
        self.base_url   = base_url.rstrip("/")
        self.clinic_key = clinic_key or os.environ.get("CLINIC_SLEEPSCAN_KEY", "")
        self.clinic_url = clinic_url.rstrip("/")

    def _headers(self) -> dict:
        return {"X-API-Key": self.api_key}

    def get_token(
        self,
        email: str | None = None,
        withings_user_id: int | None = None,
        participant_id: str | None = None,
    ) -> str:
        """Return a Withings access token for the specified participant.

        Tries SleepScan first. If that fails and a clinic key is available,
        falls back to the Clinic API (with force=True, retrying without if 403/404).

        Exactly one of email, withings_user_id, or participant_id must be provided.
        participant_id is only supported via the Clinic fallback.

        Returns:
            Withings access token string.

        Raises:
            ValueError: if no lookup key is provided.
            RuntimeError: if all sources fail.
        """
        if email is None and withings_user_id is None and participant_id is None:
            raise ValueError(
                "Provide one of: email, withings_user_id, or participant_id"
            )

        errors = []

        # ── 1. SleepScan ──────────────────────────────────────────────────────
        if email is not None or withings_user_id is not None:
            try:
                return self._sleepscan_token(email=email, withings_user_id=withings_user_id)
            except Exception as e:
                errors.append(f"SleepScan: {e}")

        # ── 2. Clinic fallback ────────────────────────────────────────────────
        if self.clinic_key and email is not None:
            try:
                return self._clinic_token(email)
            except Exception as e:
                errors.append(f"Clinic: {e}")

        raise RuntimeError(
            "Could not retrieve Withings token from any source.\n" +
            "\n".join(errors)
        )

    def _sleepscan_token(
        self,
        email: str | None = None,
        withings_user_id: int | None = None,
    ) -> str:
        if email is not None:
            url = f"{self.base_url}/withings-access-token/by-email/{requests.utils.quote(str(email), safe='')}"
        elif withings_user_id is not None:
            url = f"{self.base_url}/withings-access-token/by-withings-user-id/{withings_user_id}"
        else:
            raise ValueError("Provide email or withings_user_id for SleepScan lookup")

        resp = requests.get(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _clinic_token(self, email: str) -> str:
        """Try clinic API with force=True; retry without force on 403/404."""
        url     = f"{self.clinic_url}/tokens"
        headers = {"Authorization": f"Bearer {self.clinic_key}"}

        for force in (True, False):
            resp = requests.post(
                url, headers=headers,
                json={"email": email, "force": force},
                timeout=30,
            )
            if resp.status_code in (403, 404) and force:
                continue
            resp.raise_for_status()
            body = resp.json()
            token = (
                body.get("access_token")
                or (body.get("body") or {}).get("access_token")
            )
            if not token:
                raise RuntimeError(f"Clinic API returned no access_token: {body}")
            return token

        raise RuntimeError("Clinic API returned 403/404 for both force=True and force=False")

    def fetch(
        self,
        data_type: str,
        start_date: str,
        end_date: str,
        email: str | None = None,
        withings_user_id: int | None = None,
        participant_id: str | None = None,
    ):
        """Fetch Withings data using a SleepScan-managed token."""
        if data_type not in DATA_TYPES:
            raise ValueError(
                f"Unknown Withings data type: {data_type!r}. "
                f"Available: {', '.join(DATA_TYPES)}"
            )
        token = self.get_token(
            email=email,
            withings_user_id=withings_user_id,
            participant_id=participant_id,
        )
        return _fetch_all(token, data_type, start_date, end_date)
