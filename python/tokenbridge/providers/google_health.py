"""Google Health API v4 provider.

Wraps `https://health.googleapis.com/v4` — uses TokenBridge for auth,
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

See `docs/providers.md` for descriptions, units, and device requirements.
"""

import statistics
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
    ) -> list[dict]:
        """Fetch any Google Health data type by its ID.

        This is the primary method — all named helpers (`fetch_sleep`, etc.)
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
            return _fetch_daily_rollup(token, data_type, start_date, end_date)
        return _fetch_datapoints(token, data_type, start_date, end_date)

    # ── Analysis helpers ──────────────────────────────────────────────────────

    def summary(self, user_id: str, start_date: str, end_date: str) -> dict:
        """Summary statistics for one participant (sleep + respiratory rate).

        Makes a single token request and reuses it for both data fetches.

        Args:
            user_id: TokenBridge participant ID.
            start_date: `"YYYY-MM-DD"`.
            end_date: `"YYYY-MM-DD"`.

        Returns:
            Dict with keys:

            - `user_id` (str)
            - `period_days` (int)
            - `sleep` (dict): `n`, `days_with_data`, `coverage_pct`,
              `mean_duration_hours`, `std_duration_hours`
            - `respiratory_rate` (dict): `n`, `days_with_data`,
              `coverage_pct`, `mean`, `min`, `max`, `std`

        Example:
            ```python
            s = tb.google.summary("p001", "2026-05-01", "2026-06-18")
            print(s["sleep"]["coverage_pct"])       # 92.3
            print(s["respiratory_rate"]["mean"])    # 15.2
            ```
        """
        token       = self._get_token(user_id)
        period_days = (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days + 1
        sleep       = _fetch_datapoints(token, "sleep", start_date, end_date)
        rr          = _fetch_datapoints(token, "respiratory-rate-sleep-summary", start_date, end_date)

        return {
            "user_id":           user_id,
            "period_days":       period_days,
            "sleep":             _summarise_sleep(sleep, period_days),
            "respiratory_rate":  _summarise_rr(rr, period_days),
        }

    def summary_all(
        self, user_ids: list[str], start_date: str, end_date: str
    ) -> dict[str, dict]:
        """Summary statistics for multiple participants.

        Runs `summary()` for each user ID.  Errors per participant are caught
        and returned as `{"error": str}` rather than raising.

        Args:
            user_ids: List of TokenBridge participant IDs.
            start_date: `"YYYY-MM-DD"`.
            end_date: `"YYYY-MM-DD"`.

        Returns:
            Dict mapping `user_id` to the result of `summary()`, or
            `{"error": "message"}` if that participant failed.

        Example:
            ```python
            results = tb.google.summary_all(["p001", "p002", "p003"], start, end)
            for uid, s in results.items():
                if "error" in s:
                    print(uid, "failed:", s["error"])
                else:
                    print(uid, s["sleep"]["coverage_pct"])
            ```
        """
        results = {}
        for uid in user_ids:
            try:
                results[uid] = self.summary(uid, start_date, end_date)
            except Exception as e:
                results[uid] = {"error": str(e)}
        return results

    def data_completeness(
        self,
        user_ids: list[str],
        start_date: str,
        end_date: str,
        data_types: Optional[Sequence[str]] = None,
    ) -> list[dict]:
        """Data completeness audit — how many days of data each participant has.

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
    token: str, data_type: str, start_date: str, end_date: str
) -> list[dict]:
    """Paginate the dataPoints list endpoint with server-side date filtering."""
    url     = f"{_BASE}/dataTypes/{data_type}/dataPoints"
    headers = {"Authorization": f"Bearer {token}"}
    points  = []
    page_token = None

    while True:
        params: dict = {
            "pageSize":  1000,
            "startTime": f"{start_date}T00:00:00Z",
            "endTime":   f"{end_date}T23:59:59Z",
        }
        if page_token:
            params["pageToken"] = page_token

        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()

        body = resp.json()
        points.extend(_flatten(pt) for pt in body.get("dataPoints", []))

        page_token = body.get("nextPageToken")
        if not page_token:
            break

    return points


def _fetch_daily_rollup(
    token: str, data_type: str, start_date: str, end_date: str
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
    return [_flatten(r) for r in resp.json().get("dailyRollup", [])]


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


def _summarise_sleep(sessions: list[dict], period_days: int) -> dict:
    if not sessions:
        return {"n": 0, "days_with_data": 0, "coverage_pct": 0.0}

    days, durations = set(), []

    for s in sessions:
        if ts := s.get("startTime.seconds"):
            days.add(datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat())
        for key in ("duration.seconds", "duration"):
            if key in s:
                try:
                    durations.append(float(s[key]) / 3600)
                    break
                except (TypeError, ValueError):
                    pass

    result: dict = {
        "n":             len(sessions),
        "days_with_data": len(days),
        "coverage_pct":  round(len(days) / period_days * 100, 1) if period_days else 0.0,
    }
    if durations:
        result["mean_duration_hours"] = round(statistics.mean(durations), 2)
        if len(durations) > 1:
            result["std_duration_hours"] = round(statistics.stdev(durations), 2)
    return result


def _summarise_rr(measurements: list[dict], period_days: int) -> dict:
    if not measurements:
        return {"n": 0, "days_with_data": 0, "coverage_pct": 0.0}

    days, values = set(), []

    for m in measurements:
        if ts := m.get("startTime.seconds"):
            days.add(datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat())
        for key, val in m.items():
            if any(x in key.lower() for x in ("fpval", "intval", "value")):
                try:
                    v = float(val)
                    if 4 < v < 40:
                        values.append(v)
                        break
                except (TypeError, ValueError):
                    pass

    result: dict = {
        "n":             len(measurements),
        "days_with_data": len(days),
        "coverage_pct":  round(len(days) / period_days * 100, 1) if period_days else 0.0,
    }
    if values:
        result["mean"] = round(statistics.mean(values), 2)
        result["min"]  = round(min(values), 2)
        result["max"]  = round(max(values), 2)
        if len(values) > 1:
            result["std"] = round(statistics.stdev(values), 2)
    return result
