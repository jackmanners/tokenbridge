"""SleepScan token source for TokenBridge Withings data fetching.

Usage:
    from tokenbridge.sleepscan import SleepScan

    ss = SleepScan(api_key="your-sleepscan-api-key")

    # Fetch data directly using a SleepScan-managed Withings token
    df = ss.fetch("sleep-summary", "2024-01-01", "2024-03-31", email="participant@example.com")
    df = ss.fetch("blood-pressure", "2024-01-01", "2024-03-31", withings_user_id=12345678)

    # Or retrieve just the token for use elsewhere
    token = ss.get_token(email="participant@example.com")
"""

import requests

from tokenbridge.providers.withings import _fetch_all, DATA_TYPES


class SleepScan:
    """Retrieves Withings access tokens via the SleepScan API and fetches data.

    Args:
        api_key:  SleepScan API key (X-API-Key header).
        base_url: SleepScan API base URL. Defaults to https://sleepscan.app/api.
    """

    def __init__(self, api_key: str, base_url: str = "https://sleepscan.app/api"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict:
        return {"X-API-Key": self.api_key}

    def get_token(
        self,
        email: str | None = None,
        withings_user_id: int | None = None,
        participant_id: str | None = None,
    ) -> str:
        """Return a Withings access token for the specified participant.

        Exactly one of email, withings_user_id, or participant_id must be provided.

        Returns:
            Withings access token string.

        Raises:
            ValueError: if no lookup key is provided.
            requests.HTTPError: on non-2xx response from SleepScan.
        """
        if email is not None:
            url = f"{self.base_url}/token/by-email"
            params = {"email": email}
        elif withings_user_id is not None:
            url = f"{self.base_url}/token/by-withings-id"
            params = {"withings_user_id": withings_user_id}
        elif participant_id is not None:
            url = f"{self.base_url}/token/by-participant"
            params = {"participant_id": participant_id}
        else:
            raise ValueError(
                "Provide one of: email, withings_user_id, or participant_id"
            )

        resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()["access_token"]

    def fetch(
        self,
        data_type: str,
        start_date: str,
        end_date: str,
        email: str | None = None,
        withings_user_id: int | None = None,
        participant_id: str | None = None,
    ):
        """Fetch Withings data using a SleepScan-managed token.

        Args:
            data_type:        Withings data type (see tokenbridge.providers.withings.DATA_TYPES).
            start_date:       "YYYY-MM-DD"
            end_date:         "YYYY-MM-DD"
            email:            SleepScan participant email.
            withings_user_id: Withings user ID.
            participant_id:   SleepScan participant ID.

        Returns:
            List of record dicts, same shape as wt_fetch() / tb_fetch().

        Raises:
            ValueError: unknown data_type or missing lookup key.
        """
        if data_type not in DATA_TYPES:
            available = ", ".join(DATA_TYPES)
            raise ValueError(
                f"Unknown Withings data type: {data_type!r}. Available: {available}"
            )

        token = self.get_token(
            email=email,
            withings_user_id=withings_user_id,
            participant_id=participant_id,
        )
        return _fetch_all(token, data_type, start_date, end_date)
