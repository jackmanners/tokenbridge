"""Strava API v3 provider.

Wraps https://www.strava.com/api/v3 - uses TokenBridge for auth.

**Key differences from other providers:**

- Activities are listed by date range via ``fetch()`` as usual, but per-activity
  detail (heart rate / power / GPS streams) doesn't fit the `fetch(start, end)`
  shape - it's keyed by a single `activity_id`, not a date range. Forcing it
  into `fetch()` would mean either one HTTP call per day (wasteful) or a
  confusing overloaded signature. Instead, streams are exposed via a separate
  :meth:`Strava.streams` method, called after you've pulled the activity list
  and picked the IDs you care about.
- Pagination is classic ``page``/``per_page`` (not cursor-based).
- Date filtering uses Unix timestamps (``before``/``after``), not date strings.
- Strava enforces strict rate limits (200 req/15min, 2000 req/day). `fetch()`
  and `streams()` raise a clear `RuntimeError` on HTTP 429 rather than
  retrying silently - retry/backoff policy is left to the caller since it
  depends on their batch size and urgency.

Supported data types::

    from tokenbridge.providers.strava import DATA_TYPES
    print(list(DATA_TYPES))

See https://developers.strava.com/docs/reference/ for field-level details.

Setup:
    Register at https://www.strava.com/settings/api - create an app and set
    the callback domain to your Supabase project ref. Add secrets:
        STRAVA_CLIENT_ID
        STRAVA_CLIENT_SECRET

    Note: Strava requires the callback URL to share a domain with the app's
    "Authorization Callback Domain" setting (not an exact URL match).
"""

from datetime import date, datetime, timezone
from typing import Optional

import requests

from tokenbridge.providers._base import HealthProvider

_BASE = "https://www.strava.com/api/v3"

DATA_TYPES: dict[str, dict] = {
    "activities": {
        "path": "/athlete/activities",
        "description": "All activities (runs, rides, swims, etc.) with summary stats",
    },
}

# Stream keys available via Strava.streams(). Comma-joined into the `keys` param.
STREAM_KEYS = (
    "time", "distance", "latlng", "altitude", "velocity_smooth",
    "heartrate", "cadence", "watts", "temp", "moving", "grade_smooth",
)


def _validate_dates(start_date: str, end_date: str) -> None:
    try:
        s = date.fromisoformat(start_date)
        e = date.fromisoformat(end_date)
    except ValueError as exc:
        raise ValueError(f"Dates must be YYYY-MM-DD format: {exc}") from exc
    if s > e:
        raise ValueError(f"start_date ({start_date}) must not be after end_date ({end_date})")


def _to_unix(date_str: str, end_of_day: bool = False) -> int:
    d = date.fromisoformat(date_str)
    if end_of_day:
        dt = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)
    else:
        dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return int(dt.timestamp())


def _get(url: str, headers: dict, params: dict) -> requests.Response:
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code == 429:
        raise RuntimeError(
            "Strava API rate limit exceeded (200 req/15min, 2000 req/day). "
            f"Response headers: {dict(resp.headers)}"
        )
    resp.raise_for_status()
    return resp


class Strava(HealthProvider):
    """Strava API v3 provider.

    Usually accessed via ``tb.strava`` rather than instantiated directly.

    .. code-block:: python

        activities = tb.strava.fetch("p001", "activities", start, end)
        streams    = tb.strava.streams("p001", activities[0]["id"], keys=["heartrate", "watts"])
    """

    PROVIDER_ID = "strava"

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
        """Fetch Strava activities for a participant.

        Args:
            user_id: TokenBridge participant ID.
            data_type: Currently only ``"activities"`` is supported. Use
                :meth:`streams` for per-activity HR/power/GPS data.
            start_date: Start of date range, ``"YYYY-MM-DD"``.
            end_date: End of date range, ``"YYYY-MM-DD"``.
            token: Pre-fetched access token.

        Returns:
            List of activity summary dicts, one per activity.

        Raises:
            ValueError: If ``data_type`` is not in :data:`DATA_TYPES` or
                dates are invalid.
            RuntimeError: On HTTP 429 (rate limit exceeded).
        """
        _validate_dates(start_date, end_date)
        if data_type not in DATA_TYPES:
            raise ValueError(
                f"Unknown Strava data type {data_type!r}. "
                f"Available: {sorted(DATA_TYPES)}. "
                "For per-activity HR/power/GPS data, use tb.strava.streams()."
            )
        if token is None:
            token = self._get_token(user_id)
        return _fetch_activities(token, start_date, end_date, raw=raw)

    def streams(
        self,
        user_id: str,
        activity_id: int,
        *,
        keys: Optional[list[str]] = None,
        token: Optional[str] = None,
    ) -> dict:
        """Fetch time-series streams (HR, power, GPS, etc.) for one activity.

        Unlike :meth:`fetch`, this is keyed by a single ``activity_id`` rather
        than a date range - call :meth:`fetch` first to get activity IDs.

        Args:
            user_id: TokenBridge participant ID.
            activity_id: Strava activity ID (from ``fetch()`` results).
            keys: Stream types to request, e.g. ``["heartrate", "watts"]``.
                Defaults to ``["time", "heartrate", "watts", "latlng", "altitude"]``.
                See :data:`STREAM_KEYS` for all options.
            token: Pre-fetched access token.

        Returns:
            Dict keyed by stream type, e.g. ``{"heartrate": {"data": [...], ...}}``.
        """
        if token is None:
            token = self._get_token(user_id)
        keys = keys or ["time", "heartrate", "watts", "latlng", "altitude"]
        resp = _get(
            f"{_BASE}/activities/{activity_id}/streams",
            headers={"Authorization": f"Bearer {token}"},
            params={"keys": ",".join(keys), "key_by_type": "true"},
        )
        return resp.json()


def _fetch_activities(token: str, start_date: str, end_date: str, raw: bool = False) -> list[dict]:
    url     = f"{_BASE}/athlete/activities"
    headers = {"Authorization": f"Bearer {token}"}
    params  = {
        "after":  _to_unix(start_date),
        "before": _to_unix(end_date, end_of_day=True),
        "per_page": 200,
    }

    records: list[dict] = []
    page = 1
    while True:
        resp = _get(url, headers, {**params, "page": page})
        body = resp.json()

        if raw:
            records.append(body)
            if not body:
                break
        else:
            if not body:
                break
            records.extend(body)

        page += 1

    return records
