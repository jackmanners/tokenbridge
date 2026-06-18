"""
Google Health API v4 provider.

Wraps https://health.googleapis.com/v4 — uses TokenBridge for auth,
handles pagination and client-side date filtering internally.

This module is independent of TokenBridge internals; the only coupling is
HealthProvider._get_token(), which calls the /token endpoint.

Quick start:
    from tokenbridge import TokenBridge, GoogleHealth
    tb    = TokenBridge()
    gh    = GoogleHealth(tb)
    sleep = gh.fetch_sleep("p001", "2026-05-01", "2026-06-18")

Fetching many types for one user efficiently (one token request):
    token = tb.get_token("p001")
    sleep = gh.fetch_sleep("p001", start, end, token=token)
    steps = gh.fetch_steps("p001", start, end, token=token)
    rr    = gh.fetch_respiratory_rate("p001", start, end, token=token)

Supported data types:
    from tokenbridge.providers.google_health import DATA_TYPES
    print(DATA_TYPES)  # {type_id: "list" | "dailyRollup"}
"""

import statistics
from datetime import date, datetime, timezone
from typing import Optional

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
    """
    Fetch data from the Google Health API v4 (Fitbit-backed).

    All fetch_* methods accept an optional `token` argument.  If you are
    fetching several data types for the same participant, get the token once
    and pass it through — this avoids a TokenBridge round-trip per call:

        token = tb.get_token("p001")
        sleep = gh.fetch_sleep("p001", start, end, token=token)
        steps = gh.fetch_steps("p001", start, end, token=token)
    """

    PROVIDER_ID = "google-health"

    # ── Sleep ─────────────────────────────────────────────────────────────────

    def fetch_sleep(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Sleep sessions. One dict per session."""
        return self.fetch(user_id, "sleep", start_date, end_date, token=token)

    def fetch_respiratory_rate(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Per-sleep respiratory rate summaries (breaths/min)."""
        return self.fetch(user_id, "respiratory-rate-sleep-summary", start_date, end_date, token=token)

    def fetch_sleep_temperature(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Daily skin temperature deviation during sleep."""
        return self.fetch(user_id, "daily-sleep-temperature-derivations", start_date, end_date, token=token)

    # ── Activity ──────────────────────────────────────────────────────────────

    def fetch_steps(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Step count intervals."""
        return self.fetch(user_id, "steps", start_date, end_date, token=token)

    def fetch_distance(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Distance intervals (millimetres)."""
        return self.fetch(user_id, "distance", start_date, end_date, token=token)

    def fetch_exercise(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Exercise sessions with type, duration and GPS if available."""
        return self.fetch(user_id, "exercise", start_date, end_date, token=token)

    def fetch_active_zone_minutes(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Active Zone Minutes broken down by heart rate zone."""
        return self.fetch(user_id, "active-zone-minutes", start_date, end_date, token=token)

    def fetch_active_energy(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Active (non-resting) energy burned in kilocalories."""
        return self.fetch(user_id, "active-energy-burned", start_date, end_date, token=token)

    def fetch_sedentary(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Sedentary intervals."""
        return self.fetch(user_id, "sedentary-period", start_date, end_date, token=token)

    def fetch_floors(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Floors climbed per day. Uses daily rollup (no raw datapoints available)."""
        return self.fetch(user_id, "floors", start_date, end_date, token=token)

    def fetch_vo2_max(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Daily VO2 max estimate."""
        return self.fetch(user_id, "daily-vo2-max", start_date, end_date, token=token)

    # ── Heart & circulation ───────────────────────────────────────────────────

    def fetch_heart_rate(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Resting heart rate per day."""
        return self.fetch(user_id, "daily-resting-heart-rate", start_date, end_date, token=token)

    def fetch_heart_rate_raw(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Raw continuous heart rate samples (high volume — may be slow)."""
        return self.fetch(user_id, "heart-rate", start_date, end_date, token=token)

    def fetch_heart_rate_zones(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Daily time spent in each heart rate zone."""
        return self.fetch(user_id, "daily-heart-rate-zones", start_date, end_date, token=token)

    def fetch_hrv(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Heart rate variability samples (RMSSD in milliseconds)."""
        return self.fetch(user_id, "heart-rate-variability", start_date, end_date, token=token)

    def fetch_hrv_daily(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Daily HRV summaries."""
        return self.fetch(user_id, "daily-heart-rate-variability", start_date, end_date, token=token)

    def fetch_ecg(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Electrocardiogram recordings (requires ECG-capable device)."""
        return self.fetch(user_id, "electrocardiogram", start_date, end_date, token=token)

    def fetch_irregular_rhythm(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Irregular heart rhythm notifications."""
        return self.fetch(user_id, "irregular-rhythm-notification", start_date, end_date, token=token)

    # ── Vitals ────────────────────────────────────────────────────────────────

    def fetch_oxygen_saturation(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Blood oxygen saturation (SpO2) samples."""
        return self.fetch(user_id, "oxygen-saturation", start_date, end_date, token=token)

    def fetch_oxygen_saturation_daily(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Daily SpO2 summaries."""
        return self.fetch(user_id, "daily-oxygen-saturation", start_date, end_date, token=token)

    def fetch_respiratory_rate_daily(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Daily resting respiratory rate (distinct from sleep-specific RR)."""
        return self.fetch(user_id, "daily-respiratory-rate", start_date, end_date, token=token)

    def fetch_core_temperature(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Core body temperature samples."""
        return self.fetch(user_id, "core-body-temperature", start_date, end_date, token=token)

    def fetch_blood_glucose(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Blood glucose measurements."""
        return self.fetch(user_id, "blood-glucose", start_date, end_date, token=token)

    # ── Body measurements ─────────────────────────────────────────────────────

    def fetch_weight(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Weight measurements (kilograms)."""
        return self.fetch(user_id, "weight", start_date, end_date, token=token)

    def fetch_body_fat(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Body fat percentage measurements."""
        return self.fetch(user_id, "body-fat", start_date, end_date, token=token)

    def fetch_height(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Height measurements (millimetres)."""
        return self.fetch(user_id, "height", start_date, end_date, token=token)

    # ── Nutrition ─────────────────────────────────────────────────────────────

    def fetch_nutrition(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Nutrition log entries."""
        return self.fetch(user_id, "nutrition-log", start_date, end_date, token=token)

    def fetch_hydration(self, user_id, start_date, end_date, *, token=None) -> list[dict]:
        """Hydration log entries (millilitres)."""
        return self.fetch(user_id, "hydration-log", start_date, end_date, token=token)

    # ── Generic fetch ─────────────────────────────────────────────────────────

    def fetch(
        self,
        user_id: str,
        data_type: str,
        start_date: str,
        end_date: str,
        *,
        token: Optional[str] = None,
    ) -> list[dict]:
        """
        Fetch any Google Health data type by its ID.

        data_type must be one of the keys in DATA_TYPES (e.g. "steps", "sleep").
        This is the underlying method all named helpers call — use it for types
        that don't have a dedicated helper, or to fetch many types in a loop:

            from tokenbridge.providers.google_health import DATA_TYPES
            for dt in DATA_TYPES:
                data = gh.fetch("p001", dt, start, end, token=token)
        """
        if token is None:
            token = self._get_token(user_id)
        endpoint = DATA_TYPES.get(data_type, "list")
        if endpoint == "dailyRollup":
            return _fetch_daily_rollup(token, data_type, start_date, end_date)
        return _fetch_datapoints(token, data_type, start_date, end_date)

    # ── Analysis helpers ──────────────────────────────────────────────────────

    def summary(self, user_id: str, start_date: str, end_date: str) -> dict:
        """
        Fetch sleep + respiratory rate and return summary statistics.

        Gets a single token and reuses it for both requests.  Returns:
            {
              "user_id": str,
              "period_days": int,
              "sleep":            {"n", "days_with_data", "coverage_pct", ...},
              "respiratory_rate": {"n", "days_with_data", "coverage_pct", "mean", ...},
            }
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
        """
        Run summary() for multiple participants.
        Returns {user_id: summary_dict}.
        Errors per user are caught and returned as {"error": str}.
        """
        results = {}
        for uid in user_ids:
            try:
                results[uid] = self.summary(uid, start_date, end_date)
            except Exception as e:
                results[uid] = {"error": str(e)}
        return results

    def data_completeness(
        self, user_ids: list[str], start_date: str, end_date: str
    ) -> list[dict]:
        """
        Return a flat audit table — one row per participant × data type.

        Columns: user_id, data_type, n, days_with_data, coverage_pct, error.
        Useful for checking data quality before running analysis.
        """
        rows = []
        for uid in user_ids:
            try:
                s = self.summary(uid, start_date, end_date)
                for dtype, stats in (
                    ("sleep",            s["sleep"]),
                    ("respiratory_rate", s["respiratory_rate"]),
                ):
                    rows.append({
                        "user_id":        uid,
                        "data_type":      dtype,
                        "n":              stats.get("n", 0),
                        "days_with_data": stats.get("days_with_data", 0),
                        "coverage_pct":   stats.get("coverage_pct", 0.0),
                        "error":          None,
                    })
            except Exception as e:
                rows.append({"user_id": uid, "data_type": "all",
                             "n": None, "days_with_data": None,
                             "coverage_pct": None, "error": str(e)})
        return rows


# ── Module-level fetch functions (reusable without an instance) ───────────────

def _fetch_datapoints(
    token: str, data_type: str, start_date: str, end_date: str
) -> list[dict]:
    """Paginate the dataPoints list endpoint, filter to the study window."""
    url         = f"{_BASE}/dataTypes/{data_type}/dataPoints"
    start_epoch = int(datetime.fromisoformat(f"{start_date}T00:00:00+00:00").timestamp())
    end_epoch   = int(datetime.fromisoformat(f"{end_date}T23:59:59+00:00").timestamp())
    headers     = {"Authorization": f"Bearer {token}"}
    points      = []
    page_token  = None

    while True:
        params = {"pageSize": 1000}
        if page_token:
            params["pageToken"] = page_token

        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()

        body = resp.json()
        for pt in body.get("dataPoints", []):
            pt_start = int(pt.get("startTime", {}).get("seconds", 0))
            if start_epoch <= pt_start <= end_epoch:
                points.append(_flatten(pt))

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
