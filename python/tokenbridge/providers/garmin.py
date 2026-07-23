"""Garmin Health API provider (OAuth 2.0, invite-only developer program).

Wraps the Garmin Health API — uses TokenBridge for auth.

NOTE: Garmin's developer program is invite-only. You must apply at
https://developer.garmin.com/gc-developer-program/overview/ and be approved
before you can register an app and obtain credentials.

Garmin's modern Health API uses OAuth 2.0. The older Connect API used OAuth
1.0a (HMAC-SHA1 signing) — this provider targets the modern API only.

Setup (once approved):
    Register your app in Garmin's developer portal and add secrets:
        GARMIN_CLIENT_ID
        GARMIN_CLIENT_SECRET

See https://developer.garmin.com/gc-developer-program/overview/ for details.
"""

from typing import Optional

import requests

from tokenbridge.providers._base import HealthProvider

_BASE = "https://apis.garmin.com"

DATA_TYPES: dict[str, dict] = {
    # ── Activities ────────────────────────────────────────────────────────────
    "activities": {
        "path": "/wellness-api/rest/activities",
        "description": "Activity summaries (type, duration, distance, HR, calories)",
    },
    "activity-details": {
        "path": "/wellness-api/rest/activityDetails",
        "description": "Per-second or per-lap detail for activities",
    },
    # ── Daily summaries ───────────────────────────────────────────────────────
    "daily-summary": {
        "path": "/wellness-api/rest/dailies",
        "description": "Daily wellness summary: steps, distance, floors, calories, HR, stress",
    },
    "epoch-summary": {
        "path": "/wellness-api/rest/epochs",
        "description": "15-minute epoch summaries (steps, intensity, HR, Met)",
    },
    # ── Sleep ─────────────────────────────────────────────────────────────────
    "sleep": {
        "path": "/wellness-api/rest/sleeps",
        "description": "Sleep stages (light, deep, REM, awake), SpO2, respiration",
    },
    # ── Body / vitals ─────────────────────────────────────────────────────────
    "body-composition": {
        "path": "/wellness-api/rest/bodyComps",
        "description": "Weight, BMI, body fat %, muscle mass, bone mass",
    },
    "heart-rate-variability": {
        "path": "/wellness-api/rest/hrv",
        "description": "Nightly HRV summary and 5-minute readings",
    },
    "stress": {
        "path": "/wellness-api/rest/stressDetails",
        "description": "3-minute stress level readings throughout the day",
    },
    "respiration": {
        "path": "/wellness-api/rest/respirationDetails",
        "description": "Breath rate throughout the day (breaths/min)",
    },
    "pulse-ox": {
        "path": "/wellness-api/rest/pulseOx",
        "description": "SpO2 readings (spot checks and overnight)",
    },
    # ── User ─────────────────────────────────────────────────────────────────
    "user-metrics": {
        "path": "/wellness-api/rest/userMetrics",
        "description": "VO2max (running and cycling), fitness age, lactate threshold",
    },
}


class Garmin(HealthProvider):
    """Garmin Health API provider (OAuth 2.0).

    Usually accessed via ``tb.garmin`` rather than instantiated directly.

    Requires Garmin developer program approval (invite-only).

    .. code-block:: python

        sleep = tb.garmin.fetch("p001", "sleep", start, end)
    """

    PROVIDER_ID = "garmin"

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
        raise NotImplementedError(
            "Garmin provider is not yet implemented. "
            "Requires Garmin developer program approval. "
            "See python/tokenbridge/providers/garmin.py to contribute."
        )
