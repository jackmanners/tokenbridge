"""Withings Health API provider.

Wraps the Withings API (https://wbsapi.withings.net/) - uses TokenBridge for
auth, handles pagination and date conversion internally.

All responses are returned as flat lists of dicts.  Nested fields are
flattened with dot notation where applicable.

Supported data types::

    from tokenbridge.providers.withings import DATA_TYPES
    print(list(DATA_TYPES))

See https://developer.withings.com/api-reference/ for field-level details.
"""

from datetime import date, datetime, timezone
from typing import Optional, Sequence

import requests

from tokenbridge.providers._base import HealthProvider

_BASE = "https://wbsapi.withings.net"

# Each entry describes how to fetch the type:
#   endpoint  - API path (relative to _BASE)
#   action    - value of the ?action= param
#   date_fmt  - "ymd" (YYYY-MM-DD strings) or "unix" (epoch seconds)
#   result_key - key inside response body containing the data list
#   meastype  - (getmeas only) single measure type int
#   meastypes - (getmeas only) comma-separated type ints string
DATA_TYPES: dict[str, dict] = {
    # ── Sleep ────────────────────────────────────────────────────────────────
    "sleep-summary": {
        "endpoint": "/v2/sleep", "action": "getsummary",
        "date_fmt": "ymd", "result_key": "series",
    },
    "sleep-detail": {
        "endpoint": "/v2/sleep", "action": "get",
        "date_fmt": "unix", "result_key": "series",
    },
    # ── Activity ─────────────────────────────────────────────────────────────
    "activity": {
        "endpoint": "/v2/measure", "action": "getactivity",
        "date_fmt": "ymd", "result_key": "activities",
    },
    "workouts": {
        "endpoint": "/v2/measure", "action": "getworkouts",
        "date_fmt": "ymd", "result_key": "series",
    },
    # ── Body measurements ─────────────────────────────────────────────────────
    "weight":         {"endpoint": "/measure", "action": "getmeas", "date_fmt": "unix", "result_key": "measuregrps", "meastype": 1},
    "height":         {"endpoint": "/measure", "action": "getmeas", "date_fmt": "unix", "result_key": "measuregrps", "meastype": 4},
    "fat-ratio":      {"endpoint": "/measure", "action": "getmeas", "date_fmt": "unix", "result_key": "measuregrps", "meastype": 6},
    "fat-mass":       {"endpoint": "/measure", "action": "getmeas", "date_fmt": "unix", "result_key": "measuregrps", "meastype": 8},
    "blood-pressure": {"endpoint": "/measure", "action": "getmeas", "date_fmt": "unix", "result_key": "measuregrps", "meastypes": "9,10"},
    "heart-rate":     {"endpoint": "/measure", "action": "getmeas", "date_fmt": "unix", "result_key": "measuregrps", "meastype": 11},
    "spo2":           {"endpoint": "/measure", "action": "getmeas", "date_fmt": "unix", "result_key": "measuregrps", "meastype": 54},
    "muscle-mass":    {"endpoint": "/measure", "action": "getmeas", "date_fmt": "unix", "result_key": "measuregrps", "meastype": 76},
    "bone-mass":      {"endpoint": "/measure", "action": "getmeas", "date_fmt": "unix", "result_key": "measuregrps", "meastype": 88},
    # ── Heart / ECG ──────────────────────────────────────────────────────────
    "ecg": {
        "endpoint": "/v2/heart", "action": "list",
        "date_fmt": "unix", "result_key": "series",
    },
}

# Measure types that decode a single numeric value (value * 10^unit)
_SCALAR_MEASTYPES = {
    1: "weight_kg",
    4: "height_m",
    5: "fat_free_mass_kg",
    6: "fat_ratio_pct",
    8: "fat_mass_kg",
    9: "diastolic_bp_mmhg",
    10: "systolic_bp_mmhg",
    11: "heart_rate_bpm",
    12: "temperature_c",
    54: "spo2_pct",
    71: "body_temperature_c",
    73: "skin_temperature_c",
    76: "muscle_mass_kg",
    77: "hydration_kg",
    88: "bone_mass_kg",
    91: "pulse_wave_velocity_m_s",
    123: "vo2max_ml_min_kg",
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


def _to_unix(date_str: str, end_of_day: bool = False) -> int:
    """Convert YYYY-MM-DD to a unix timestamp (UTC midnight, or 23:59:59)."""
    d = date.fromisoformat(date_str)
    if end_of_day:
        dt = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)
    else:
        dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return int(dt.timestamp())


def _decode_measuregrps(grps: list[dict]) -> list[dict]:
    """Flatten Withings measuregrps into one dict per measurement group."""
    rows = []
    for grp in grps:
        row: dict = {
            "grpid":    grp.get("grpid"),
            "date":     grp.get("date"),
            "category": grp.get("category"),
        }
        for m in grp.get("measures", []):
            mtype = m.get("type")
            raw_val = m.get("value", 0) * (10 ** m.get("unit", 0))
            col = _SCALAR_MEASTYPES.get(mtype, f"type_{mtype}")
            row[col] = round(raw_val, 6)
        rows.append(row)
    return rows


class Withings(HealthProvider):
    """Withings health data provider.

    Usually accessed via ``tb.withings`` rather than instantiated directly.

    All public methods accept an optional ``token`` argument.  Pass a
    pre-fetched token to avoid one TokenBridge round-trip per call:

    .. code-block:: python

        token = tb.get_token("p001", provider="withings")
        sleep = wt.fetch("p001", "sleep-summary", start, end, token=token)
        weight = wt.fetch("p001", "weight",       start, end, token=token)
    """

    PROVIDER_ID = "withings"

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
        """Fetch any Withings data type by its ID.

        Args:
            user_id: TokenBridge participant ID.
            data_type: Type ID from :data:`DATA_TYPES`, e.g. ``"sleep-summary"``,
                ``"activity"``, ``"weight"``.
            start_date: Start of date range, ``"YYYY-MM-DD"``.
            end_date: End of date range, ``"YYYY-MM-DD"``.
            token: Pre-fetched access token.  Obtain with
                ``tb.get_token(user_id, provider="withings")``.

        Returns:
            List of flat dicts, one per record.  Returns an empty list if no
            data exists for the period.

        Raises:
            ValueError: If ``data_type`` is not in :data:`DATA_TYPES` or dates
                are invalid.
            RuntimeError: If the Withings API returns a non-zero status.
        """
        _validate_dates(start_date, end_date)
        if data_type not in DATA_TYPES:
            raise ValueError(
                f"Unknown Withings data type {data_type!r}. "
                f"Available: {sorted(DATA_TYPES)}"
            )
        if token is None:
            token = self._get_token(user_id)
        return _fetch_all(token, data_type, start_date, end_date, raw=raw)


# ── Internal fetch helpers ────────────────────────────────────────────────────

def _fetch_all(token: str, data_type: str, start_date: str, end_date: str, raw: bool = False) -> list[dict]:
    """Fetch all pages for a data type and return combined records."""
    spec = DATA_TYPES[data_type]
    endpoint = spec["endpoint"]
    action = spec["action"]
    date_fmt = spec["date_fmt"]
    result_key = spec["result_key"]

    # Build date params
    if date_fmt == "ymd":
        date_params = {"startdateymd": start_date, "enddateymd": end_date}
    else:
        date_params = {
            "startdate": _to_unix(start_date),
            "enddate":   _to_unix(end_date, end_of_day=True),
        }

    # Extra params for getmeas
    extra: dict = {}
    if "meastype" in spec:
        extra["meastype"] = spec["meastype"]
    if "meastypes" in spec:
        extra["meastypes"] = spec["meastypes"]

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{_BASE}{endpoint}"
    records: list[dict] = []
    offset: Optional[int] = None

    while True:
        params = {"action": action, **date_params, **extra}
        if offset is not None:
            params["offset"] = offset

        resp = requests.get(url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        body = resp.json()

        status = body.get("status", -1)
        if status != 0:
            raise RuntimeError(
                f"Withings API error (status {status}) for {data_type!r}: "
                f"{body.get('error', body)}"
            )

        if raw:
            records.append(body)
            if not body.get("body", {}).get("more"):
                break
            offset = body["body"].get("offset")
            continue

        data = body.get("body", {})
        page_records = data.get(result_key, []) or []

        if result_key == "measuregrps":
            page_records = _decode_measuregrps(page_records)

        records.extend(page_records)

        if data.get("more"):
            offset = data.get("offset")
        else:
            break

    return records
