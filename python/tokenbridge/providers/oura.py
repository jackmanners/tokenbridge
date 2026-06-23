"""Oura Ring API v2 provider.

Wraps https://api.ouraring.com/v2 — uses TokenBridge for auth,
handles pagination internally.

All responses are flat lists of dicts matching the Oura API field names
exactly (no transformation needed — Oura returns clean JSON already).

Supported data types::

    from tokenbridge.providers.oura import DATA_TYPES
    print(list(DATA_TYPES))

See https://cloud.ouraring.com/v2/docs for field-level details.
"""

from datetime import date, datetime, timezone
from typing import Optional, Sequence

import requests

from tokenbridge.providers._base import HealthProvider

_BASE = "https://api.ouraring.com/v2/usercollection"

# date_fmt: "date" → start_date/end_date (YYYY-MM-DD)
#           "datetime" → start_datetime/end_datetime (ISO 8601 with timezone)
DATA_TYPES: dict[str, dict] = {
    # ── Daily summaries ───────────────────────────────────────────────────────
    "daily-activity":       {"path": "daily_activity",              "date_fmt": "date"},
    "daily-sleep":          {"path": "daily_sleep",                 "date_fmt": "date"},
    "daily-readiness":      {"path": "daily_readiness",             "date_fmt": "date"},
    "daily-stress":         {"path": "daily_stress",                "date_fmt": "date"},
    "daily-spo2":           {"path": "daily_spo2",                  "date_fmt": "date"},
    "daily-resilience":     {"path": "daily_resilience",            "date_fmt": "date"},
    "cardiovascular-age":   {"path": "daily_cardiovascular_age",    "date_fmt": "date"},
    # ── Detailed sessions ─────────────────────────────────────────────────────
    "sleep":                {"path": "sleep",                       "date_fmt": "date"},
    "sleep-time":           {"path": "sleep_time",                  "date_fmt": "date"},
    "workout":              {"path": "workout",                     "date_fmt": "date"},
    "session":              {"path": "session",                     "date_fmt": "date"},
    # ── Continuous streams ────────────────────────────────────────────────────
    "heartrate":            {"path": "heartrate",                   "date_fmt": "datetime"},
    # ── Other ─────────────────────────────────────────────────────────────────
    "vo2-max":              {"path": "vO2_max",                     "date_fmt": "date"},
    "tag":                  {"path": "tag",                         "date_fmt": "date"},
    "enhanced-tag":         {"path": "enhanced_tag",                "date_fmt": "date"},
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


def _to_iso_datetime(date_str: str, end_of_day: bool = False) -> str:
    """Convert YYYY-MM-DD to ISO 8601 datetime with UTC timezone."""
    d = date.fromisoformat(date_str)
    if end_of_day:
        dt = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)
    else:
        dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return dt.isoformat()


class Oura(HealthProvider):
    """Oura Ring API v2 provider.

    Usually accessed via ``tb.oura`` rather than instantiated directly.

    All public methods accept an optional ``token`` argument:

    .. code-block:: python

        token = tb.get_token("p001", provider="oura")
        sleep = ou.fetch("p001", "sleep",          start, end, token=token)
        ready = ou.fetch("p001", "daily-readiness", start, end, token=token)
    """

    PROVIDER_ID = "oura"

    def fetch(
        self,
        user_id: str,
        data_type: str,
        start_date: str,
        end_date: str,
        *,
        token: Optional[str] = None,
    ) -> list[dict]:
        """Fetch any Oura data type by its ID.

        Args:
            user_id: TokenBridge participant ID.
            data_type: Type ID from :data:`DATA_TYPES`, e.g. ``"sleep"``,
                ``"daily-activity"``, ``"heartrate"``.
            start_date: Start of date range, ``"YYYY-MM-DD"``.
            end_date: End of date range, ``"YYYY-MM-DD"``.
            token: Pre-fetched access token.  Obtain with
                ``tb.get_token(user_id, provider="oura")``.

        Returns:
            List of dicts, one per record.  Field names match the Oura API
            exactly.  Returns an empty list if no data exists for the period.

        Raises:
            ValueError: If ``data_type`` is not in :data:`DATA_TYPES` or
                dates are invalid.
        """
        _validate_dates(start_date, end_date)
        if data_type not in DATA_TYPES:
            raise ValueError(
                f"Unknown Oura data type {data_type!r}. "
                f"Available: {sorted(DATA_TYPES)}"
            )
        if token is None:
            token = self._get_token(user_id)
        return _fetch_all(token, data_type, start_date, end_date)


# ── Internal fetch helpers ────────────────────────────────────────────────────

def _fetch_all(token: str, data_type: str, start_date: str, end_date: str) -> list[dict]:
    spec     = DATA_TYPES[data_type]
    url      = f"{_BASE}/{spec['path']}"
    headers  = {"Authorization": f"Bearer {token}"}

    if spec["date_fmt"] == "datetime":
        params: dict = {
            "start_datetime": _to_iso_datetime(start_date),
            "end_datetime":   _to_iso_datetime(end_date, end_of_day=True),
        }
    else:
        params = {"start_date": start_date, "end_date": end_date}

    records: list[dict] = []
    next_token: Optional[str] = None

    while True:
        if next_token:
            params["next_token"] = next_token

        resp = requests.get(url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        body = resp.json()

        records.extend(body.get("data", []))

        next_token = body.get("next_token")
        if not next_token:
            break

    return records
