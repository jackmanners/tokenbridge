"""Google Health API v4 provider.

Wraps `https://health.googleapis.com/v4` - uses TokenBridge for auth,
handles pagination and client-side date filtering internally.

The usual entry point is `tb.fetch()` or `tb.google.fetch()` on a
`TokenBridge` instance.  Import `GoogleHealth` directly only if you want
to use it standalone:

```python
from tokenbridge import TokenBridge, GoogleHealth
tb = TokenBridge()
gh = GoogleHealth(tb)
sleep = gh.fetch("p001", "sleep", "2026-05-01", "2026-06-18")
```

Supported data types:
```python
from tokenbridge.providers.google_health import DATA_TYPES
print(list(DATA_TYPES))   # all type IDs
```

See `docs/providers/index.md` for descriptions, units, and device requirements.
"""

from datetime import date, datetime, timezone
from typing import Optional, Sequence

import requests

from tokenbridge.providers._base import HealthProvider


_BASE = "https://health.googleapis.com/v4/users/me"

# All supported data type IDs and their endpoint type.
# "list"        → GET  /v4/users/me/dataTypes/{type}/dataPoints
# "dailyRollup" → POST /v4/users/me/dataTypes/{type}/dataPoints:dailyRollUp
DATA_TYPES: dict[str, str] = {
    # ── Activity & fitness ──────────────────────────────────────────────────
    "steps":                              "list",
    "distance":                           "list",
    "active-minutes":                     "list",
    "active-zone-minutes":                "list",
    "active-energy-burned":               "list",
    "activity-level":                     "list",
    "sedentary-period":                   "list",
    "altitude":                           "list",
    "swim-lengths-data":                  "list",
    "time-in-heart-rate-zone":            "list",
    "exercise":                           "list",
    "vo2-max":                            "list",
    "run-vo2-max":                        "list",
    "daily-vo2-max":                      "list",
    # rollup-only (no individual datapoints endpoint)
    "floors":                             "dailyRollup",
    "total-calories":                     "dailyRollup",
    "calories-in-heart-rate-zone":        "dailyRollup",
    # ── Sleep ───────────────────────────────────────────────────────────────
    "sleep":                              "list",
    "daily-sleep-temperature-derivations": "list",
    "respiratory-rate-sleep-summary":     "list",
    # ── Heart & circulation ─────────────────────────────────────────────────
    "heart-rate":                         "list",
    "daily-resting-heart-rate":           "list",
    "daily-heart-rate-zones":             "list",
    "heart-rate-variability":             "list",
    "daily-heart-rate-variability":       "list",
    # ── Vitals ──────────────────────────────────────────────────────────────
    "oxygen-saturation":                  "list",
    "daily-oxygen-saturation":            "list",
    "daily-respiratory-rate":             "list",
    "core-body-temperature":              "list",
    "blood-glucose":                      "list",
    # ── Body measurements ───────────────────────────────────────────────────
    "weight":                             "list",
    "body-fat":                           "list",
    "height":                             "list",
    # ── Nutrition ───────────────────────────────────────────────────────────
    "food":                               "list",
    "nutrition-log":                      "list",
    "hydration-log":                      "list",
    # ── Specialised ─────────────────────────────────────────────────────────
    "electrocardiogram":                  "list",
    "irregular-rhythm-notification":      "list",
}


# Filter field per data type, derived from the v4 discovery doc.
# Interval types  → {snake_type}.interval.start_time
# Sample types    → {snake_type}.sample_time.physical_time
# Daily types     → {snake_type}.date
# See: https://health.googleapis.com/$discovery/rest?version=v4
_FILTER_FIELD: dict[str, str] = {
    # interval
    "steps":                               "steps.interval.start_time",
    "distance":                            "distance.interval.start_time",
    "active-minutes":                      "active_minutes.interval.start_time",
    "active-zone-minutes":                 "active_zone_minutes.interval.start_time",
    "active-energy-burned":                "active_energy_burned.interval.start_time",
    "activity-level":                      "activity_level.interval.start_time",
    "sedentary-period":                    "sedentary_period.interval.start_time",
    "altitude":                            "altitude.interval.start_time",
    "swim-lengths-data":                   "swim_lengths_data.interval.start_time",
    "time-in-heart-rate-zone":             "time_in_heart_rate_zone.interval.start_time",
    "exercise":                            "exercise.interval.start_time",
    "vo2-max":                             "vo2_max.interval.start_time",
    "run-vo2-max":                         "run_vo2_max.interval.start_time",
    "sleep":                               "sleep.interval.end_time",
    "electrocardiogram":                   "electrocardiogram.interval.start_time",
    "irregular-rhythm-notification":       "irregular_rhythm_notification.interval.start_time",
    # sample
    "heart-rate":                          "heart_rate.sample_time.physical_time",
    "heart-rate-variability":              "heart_rate_variability.sample_time.physical_time",
    "oxygen-saturation":                   "oxygen_saturation.sample_time.physical_time",
    "core-body-temperature":               "core_body_temperature.sample_time.physical_time",
    "blood-glucose":                       "blood_glucose.sample_time.physical_time",
    "weight":                              "weight.sample_time.physical_time",
    "body-fat":                            "body_fat.sample_time.physical_time",
    "height":                              "height.sample_time.physical_time",
    "food":                                "food.sample_time.physical_time",
    "hydration-log":                       "hydration_log.sample_time.physical_time",
    # daily
    "daily-vo2-max":                       "daily_vo2_max.date",
    "daily-resting-heart-rate":            "daily_resting_heart_rate.date",
    "daily-heart-rate-zones":              "daily_heart_rate_zones.date",
    "daily-heart-rate-variability":        "daily_heart_rate_variability.date",
    "daily-oxygen-saturation":             "daily_oxygen_saturation.date",
    "daily-respiratory-rate":              "daily_respiratory_rate.date",
    "daily-sleep-temperature-derivations": "daily_sleep_temperature_derivations.date",
    "respiratory-rate-sleep-summary":      "respiratory_rate_sleep_summary.date",
    "nutrition-log":                       "nutrition_log.date",
}


class GoogleHealth(HealthProvider):
    """Google Health API v4 provider (Fitbit-backed).

    Usually accessed via `tb.google` rather than instantiated directly.

    All public methods accept an optional `token` argument.  Pass a
    pre-fetched token to avoid one TokenBridge round-trip per call when
    fetching multiple types for the same participant:

    ```python
    token = tb.get_token("p001")
    sleep = gh.fetch("p001", "sleep",  start, end, token=token)
    steps = gh.fetch("p001", "steps",  start, end, token=token)
    hrv   = gh.fetch("p001", "heart-rate-variability", start, end, token=token)
    ```
    """

    PROVIDER_ID = "google-health"

    # ── Fetch ─────────────────────────────────────────────────────────────────

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
        """Fetch any Google Health data type by its ID.

        This is the primary method - all named helpers (`fetch_sleep`, etc.)
        delegate here.  Automatically routes to the correct endpoint type
        (`list` or `dailyRollup`) based on `DATA_TYPES`.

        Args:
            user_id: TokenBridge participant ID.
            data_type: Kebab-case type ID, e.g. `"sleep"`, `"steps"`,
                `"heart-rate-variability"`.  Must be a key in `DATA_TYPES`.
            start_date: Start of date range, `"YYYY-MM-DD"`.
            end_date: End of date range, `"YYYY-MM-DD"`.
            token: Pre-fetched access token.  Pass when fetching multiple
                types to avoid repeated TokenBridge round-trips.

        Returns:
            List of flat dicts, one per data point.  Nested API fields are
            flattened with dot notation, e.g. `startTime.seconds`.
            Returns an empty list if no data exists for the period.

        Example:
            ```python
            sleep = gh.fetch("p001", "sleep", "2026-05-01", "2026-06-18")

            # Loop all types with one token
            token = tb.get_token("p001")
            for dt in DATA_TYPES:
                data = gh.fetch("p001", dt, start, end, token=token)
            ```
        """
        _validate_dates(start_date, end_date)
        if token is None:
            token = self._get_token(user_id)
        endpoint = DATA_TYPES.get(data_type, "list")
        if endpoint == "dailyRollup":
            return _fetch_daily_rollup(token, data_type, start_date, end_date, raw=raw)
        return _fetch_datapoints(token, data_type, start_date, end_date, raw=raw)

    # ── Analysis helpers ──────────────────────────────────────────────────────

    def data_completeness(
        self,
        user_ids: list[str],
        start_date: str,
        end_date: str,
        data_types: Optional[Sequence[str]] = None,
    ) -> list[dict]:
        """Data completeness audit - how many days of data each participant has.

        Fetches each requested data type for each participant and returns a
        flat table of counts. One row per participant × data type.

        Args:
            user_ids: List of TokenBridge participant IDs.
            start_date: `"YYYY-MM-DD"`.
            end_date: `"YYYY-MM-DD"`.
            data_types: Data type IDs to check. Defaults to
                `["sleep", "steps", "heart-rate-variability"]`. Pass any
                subset of `DATA_TYPES` keys.

        Returns:
            List of dicts with keys: `user_id`, `data_type`, `n`,
            `days_with_data`, `coverage_pct`, `error`.

        Example:
            ```python
            audit = tb.google.data_completeness(
                ["p001", "p002"],
                "2026-05-01", "2026-06-18",
                data_types=["sleep", "steps"],
            )
            import pandas as pd
            df = pd.DataFrame(audit)
            print(df[df["coverage_pct"] < 80])
            ```
        """
        _validate_dates(start_date, end_date)
        if data_types is None:
            data_types = ["sleep", "steps", "heart-rate-variability"]
        period_days = (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days + 1
        rows = []
        for uid in user_ids:
            try:
                token = self._get_token(uid)
                for dtype in data_types:
                    try:
                        points = self.fetch(uid, dtype, start_date, end_date, token=token)
                        days = len({
                            datetime.fromtimestamp(int(p["startTime.seconds"]), tz=timezone.utc).date()
                            for p in points if "startTime.seconds" in p
                        })
                        rows.append({
                            "user_id":        uid,
                            "data_type":      dtype,
                            "n":              len(points),
                            "days_with_data": days,
                            "coverage_pct":   round(days / period_days * 100, 1) if period_days else 0.0,
                            "error":          None,
                        })
                    except Exception as e:
                        rows.append({"user_id": uid, "data_type": dtype,
                                     "n": None, "days_with_data": None,
                                     "coverage_pct": None, "error": str(e)})
            except Exception as e:
                for dtype in data_types:
                    rows.append({"user_id": uid, "data_type": dtype,
                                 "n": None, "days_with_data": None,
                                 "coverage_pct": None, "error": str(e)})
        return rows


# ── Module-level fetch functions (reusable without an instance) ───────────────

def _validate_dates(start_date: str, end_date: str) -> None:
    try:
        s = date.fromisoformat(start_date)
        e = date.fromisoformat(end_date)
    except ValueError as exc:
        raise ValueError(f"Dates must be YYYY-MM-DD format: {exc}") from exc
    if s > e:
        raise ValueError(f"start_date ({start_date}) must not be after end_date ({end_date})")


def _fetch_datapoints(
    token: str, data_type: str, start_date: str, end_date: str, raw: bool = False
) -> list[dict]:
    """Paginate the dataPoints list endpoint using the API filter parameter.

    Date filtering uses the filter query param per the discovery doc:
      https://health.googleapis.com/$discovery/rest?version=v4
    Sleep/exercise max page size is 25; other types max at 10000.
    """
    url        = f"{_BASE}/dataTypes/{data_type}/dataPoints"
    headers    = {"Authorization": f"Bearer {token}"}
    points     = []
    page_token = None

    ts_field = _FILTER_FIELD.get(data_type)
    if ts_field and ts_field.endswith(".date"):
        filter_expr = f'{ts_field} >= "{start_date}" AND {ts_field} < "{end_date}"'
    elif ts_field:
        filter_expr = (f'{ts_field} >= "{start_date}T00:00:00Z"'
                       f' AND {ts_field} < "{end_date}T23:59:59Z"')
    else:
        filter_expr = None

    while True:
        params: dict = {"pageSize": 1000}
        if filter_expr:
            params["filter"] = filter_expr
        if page_token:
            params["pageToken"] = page_token

        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()

        body = resp.json()

        if raw:
            points.append(body)
        else:
            points.extend(_flatten(pt) for pt in body.get("dataPoints", []))

        page_token = body.get("nextPageToken")
        if not page_token:
            break

    return points


def _fetch_daily_rollup(
    token: str, data_type: str, start_date: str, end_date: str, raw: bool = False
) -> list[dict]:
    """POST to the dailyRollUp endpoint for types that don't support list."""
    url  = f"{_BASE}/dataTypes/{data_type}/dataPoints:dailyRollUp"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json={"startDate": start_date, "endDate": end_date},
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if raw:
        return [body]
    return [_flatten(r) for r in body.get("dailyRollup", [])]


def _flatten(obj, prefix: str = "") -> dict:
    """Recursively flatten nested dicts/lists into dot-separated keys."""
    items: dict = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            items.update(_flatten(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            items.update(_flatten(v, f"{prefix}.{i}" if prefix else str(i)))
    else:
        items[prefix] = obj
    return items


