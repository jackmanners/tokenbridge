"""Polar AccessLink API v3 provider.

Wraps https://www.polaraccesslink.com/v3 - uses TokenBridge for auth.

**Key differences from other providers:**

- Access tokens never expire (no refresh token) - Polar only invalidates a
  token if the user revokes access.
- New users must be registered with AccessLink via `POST /v3/users` before
  any data endpoint works. TokenBridge's `auth-callback` does this
  automatically right after the OAuth token exchange.
- Polar caps each request to a 28-day date range. `fetch()` transparently
  chunks longer ranges into multiple sequential requests and concatenates
  the results - this is the one place Polar's API shape leaks through as
  *more* requests rather than *different* usage, not a different interface.
- Uses the modern flat "list by date range" endpoints rather than the older
  transaction-based pull model (create/list/fetch/commit), which Polar
  itself now recommends against for new integrations.

Supported data types::

    from tokenbridge.providers.polar import DATA_TYPES
    print(list(DATA_TYPES))

See https://www.polar.com/accesslink-api/ for field-level details.

Setup:
    Register at https://www.polar.com/en/developers - create an app, set the
    callback URL, and add secrets to Supabase:
        POLAR_CLIENT_ID
        POLAR_CLIENT_SECRET
"""

from datetime import date, datetime, timedelta
from typing import Optional

import requests

from tokenbridge.providers._base import HealthProvider

_BASE = "https://www.polaraccesslink.com/v3"

_MAX_RANGE_DAYS = 28

# Each entry: endpoint path (relative to _BASE), and whether it supports
# from/to date filtering (all current data types do).
DATA_TYPES: dict[str, dict] = {
    "sleep": {
        "path": "/users/sleep",
        "description": "Sleep stages (light, deep, REM), interruptions, sleep score",
    },
    "activity": {
        "path": "/users/activities",
        "description": "Daily activity summary (steps, calories, activity zones)",
    },
    "nightly-recharge": {
        "path": "/users/nightly-recharge",
        "description": "Nightly recharge / ANS charge score",
    },
    "exercise": {
        "path": "/exercises",
        "description": "Individual training sessions with HR and lap data",
    },
}


def _validate_dates(start_date: str, end_date: str) -> None:
    fmt = "%Y-%m-%d"
    try:
        s = datetime.strptime(start_date, fmt).date()
        e = datetime.strptime(end_date, fmt).date()
    except ValueError:
        raise ValueError(
            f"Dates must be YYYY-MM-DD format, got: {start_date!r}, {end_date!r}"
        )
    if s > e:
        raise ValueError(
            f"start_date ({start_date}) must not be after end_date ({end_date})"
        )


def _date_chunks(start_date: str, end_date: str, max_days: int = _MAX_RANGE_DAYS):
    """Split a date range into <= max_days chunks (Polar's per-request cap)."""
    s = date.fromisoformat(start_date)
    e = date.fromisoformat(end_date)
    step = timedelta(days=max_days - 1)
    cur = s
    while cur <= e:
        chunk_end = min(cur + step, e)
        yield cur.isoformat(), chunk_end.isoformat()
        cur = chunk_end + timedelta(days=1)


class Polar(HealthProvider):
    """Polar AccessLink API v3 provider.

    Usually accessed via ``tb.polar`` rather than instantiated directly.

    .. code-block:: python

        sleep = tb.polar.fetch("p001", "sleep", start, end)
    """

    PROVIDER_ID = "polar"

    def fetch(
        self,
        user_id: str,
        data_type: str,
        start_date: str,
        end_date: str,
        *,
        token: Optional[str] = None,
        raw: bool = False,
    ) -> list[dict]:
        """Fetch any Polar data type by its ID.

        Args:
            user_id: TokenBridge participant ID.
            data_type: Type ID from :data:`DATA_TYPES`, e.g. ``"sleep"``.
            start_date: Start of date range, ``"YYYY-MM-DD"``.
            end_date: End of date range, ``"YYYY-MM-DD"``.
            token: Pre-fetched access token.

        Returns:
            List of dicts, one per record. Field names match the Polar API
            exactly. Automatically chunks ranges longer than 28 days into
            multiple requests (Polar's per-request limit).

        Raises:
            ValueError: If ``data_type`` is not in :data:`DATA_TYPES` or
                dates are invalid.
            RuntimeError: If Polar returns a non-2xx response, e.g. because
                the participant hasn't been registered via
                ``POST /v3/users`` yet.
        """
        _validate_dates(start_date, end_date)
        if data_type not in DATA_TYPES:
            raise ValueError(
                f"Unknown Polar data type {data_type!r}. "
                f"Available: {sorted(DATA_TYPES)}"
            )
        if token is None:
            token = self._get_token(user_id)
        return _fetch_all(token, data_type, start_date, end_date, raw=raw)


def _fetch_all(token: str, data_type: str, start_date: str, end_date: str, raw: bool = False) -> list[dict]:
    spec    = DATA_TYPES[data_type]
    url     = f"{_BASE}{spec['path']}"
    headers = {"Authorization": f"Bearer {token}"}

    records: list[dict] = []

    for chunk_start, chunk_end in _date_chunks(start_date, end_date):
        resp = requests.get(
            url,
            params={"from": chunk_start, "to": chunk_end},
            headers=headers,
            timeout=30,
        )
        if resp.status_code == 404:
            # Polar returns 404 when there is no data for the range - treat as empty.
            continue
        resp.raise_for_status()
        body = resp.json()

        if raw:
            records.append(body)
            continue

        # Polar returns a bare list, or occasionally {"data": [...]}.
        page_records = body if isinstance(body, list) else body.get("data", [])
        records.extend(page_records)

    return records
