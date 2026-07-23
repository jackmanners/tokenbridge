"""WHOOP API v1 provider.

Wraps https://api.prod.whoop.com/developer/v1 - uses TokenBridge for auth.

**Key differences from other providers:**

- Recovery records have no standalone ID of their own - they're keyed by
  ``cycle_id`` (the physiological day they belong to). Returned as-is rather
  than joined against `cycle`/`sleep` - join them yourself via `cycle_id`
  if you need a single per-day row, since which fields you want from each
  side is analysis-specific.
- Pagination is cursor-based (`nextToken` request param / `next_token`
  response field), capped at 25 records per page (vs Withings/GH's larger
  page sizes) - `fetch()` handles this transparently.
- Refreshing a token invalidates the previous refresh token - TokenBridge's
  `/token` endpoint handles this already; noted here since it differs from
  Withings/Google's more forgiving refresh behaviour.

Supported data types::

    from tokenbridge.providers.whoop import DATA_TYPES
    print(list(DATA_TYPES))

See https://developer.whoop.com/api for field-level details.

Setup:
    Register at https://developer.whoop.com - create an app and add secrets:
        WHOOP_CLIENT_ID
        WHOOP_CLIENT_SECRET
"""

from datetime import date, datetime, timezone
from typing import Optional

import requests

from tokenbridge.providers._base import HealthProvider

_BASE = "https://api.prod.whoop.com/developer/v1"

_PAGE_LIMIT = 25

DATA_TYPES: dict[str, dict] = {
    "recovery": {
        "path": "/recovery",
        "description": "Daily recovery score, HRV, resting HR, SpO2 (keyed by cycle_id, not its own id)",
    },
    "sleep": {
        "path": "/activity/sleep",
        "description": "Sleep performance, efficiency, stages, disturbances",
    },
    "workout": {
        "path": "/activity/workout",
        "description": "Workout strain, sport, HR zones, distance, calories",
    },
    "cycle": {
        "path": "/cycle",
        "description": "Physiological cycle (day): strain, avg/max HR, calories",
    },
}


def _validate_dates(start_date: str, end_date: str) -> None:
    try:
        s = date.fromisoformat(start_date)
        e = date.fromisoformat(end_date)
    except ValueError as exc:
        raise ValueError(f"Dates must be YYYY-MM-DD format: {exc}") from exc
    if s > e:
        raise ValueError(f"start_date ({start_date}) must not be after end_date ({end_date})")


def _to_iso(date_str: str, end_of_day: bool = False) -> str:
    d = date.fromisoformat(date_str)
    if end_of_day:
        dt = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)
    else:
        dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


class Whoop(HealthProvider):
    """WHOOP API v1 provider.

    Usually accessed via ``tb.whoop`` rather than instantiated directly.

    .. code-block:: python

        recovery = tb.whoop.fetch("p001", "recovery", start, end)
        sleep    = tb.whoop.fetch("p001", "sleep",    start, end)
    """

    PROVIDER_ID = "whoop"

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
        """Fetch any WHOOP data type by its ID.

        Args:
            user_id: TokenBridge participant ID.
            data_type: Type ID from :data:`DATA_TYPES`, e.g. ``"recovery"``.
            start_date: Start of date range, ``"YYYY-MM-DD"``.
            end_date: End of date range, ``"YYYY-MM-DD"``.
            token: Pre-fetched access token.

        Returns:
            List of dicts, one per record. Field names match the WHOOP API
            exactly. Note that ``"recovery"`` records use ``cycle_id`` rather
            than their own ``id`` - see module docstring.

        Raises:
            ValueError: If ``data_type`` is not in :data:`DATA_TYPES` or
                dates are invalid.
        """
        _validate_dates(start_date, end_date)
        if data_type not in DATA_TYPES:
            raise ValueError(
                f"Unknown WHOOP data type {data_type!r}. "
                f"Available: {sorted(DATA_TYPES)}"
            )
        if token is None:
            token = self._get_token(user_id)
        return _fetch_all(token, data_type, start_date, end_date, raw=raw)


def _fetch_all(token: str, data_type: str, start_date: str, end_date: str, raw: bool = False) -> list[dict]:
    spec    = DATA_TYPES[data_type]
    url     = f"{_BASE}{spec['path']}"
    headers = {"Authorization": f"Bearer {token}"}
    params  = {
        "start": _to_iso(start_date),
        "end":   _to_iso(end_date, end_of_day=True),
        "limit": _PAGE_LIMIT,
    }

    records: list[dict] = []
    next_token: Optional[str] = None

    while True:
        if next_token:
            params["nextToken"] = next_token

        resp = requests.get(url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        body = resp.json()

        if raw:
            records.append(body)
        else:
            records.extend(body.get("records", []))

        next_token = body.get("next_token")
        if not next_token:
            break

    return records
