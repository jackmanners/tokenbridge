"""Huawei Health Kit provider (HMS OAuth 2.0).

Wraps the Huawei Health Kit REST API — uses TokenBridge for auth.

NOTE: Huawei Health Kit targets the Chinese market and requires registration
in AppGallery Connect. The OAuth flow uses Huawei's own HMS OAuth 2.0
infrastructure rather than standard endpoints, and data access requires
the user's Huawei ID account and HUAWEI Health app.

Setup:
    1. Register at https://developer.huawei.com/consumer/en/
    2. Create a project in AppGallery Connect with Health Kit enabled
    3. Set the OAuth redirect URI to your Supabase auth-callback URL
    4. Add secrets:
           HUAWEI_CLIENT_ID
           HUAWEI_CLIENT_SECRET

    Data scope must be explicitly granted per data type in AppGallery Console.

See https://developer.huawei.com/consumer/en/doc/HMSCore-Guides/healthkit-introduction-0000001050071643
"""

from typing import Optional

import requests

from tokenbridge.providers._base import HealthProvider

# HMS OAuth endpoints (global, non-China)
_AUTH_BASE  = "https://oauth-login.cloud.huawei.com"
# Health Kit REST API base (China: health-drru.hicloud.com)
_BASE       = "https://health-api.cloud.huawei.com/healthkit/v1"

# HMS Health Kit scope constants map to data type groups.
# Full scope list: https://developer.huawei.com/consumer/en/doc/HMSCore-References/scope-0000001050748123
DATA_TYPES: dict[str, dict] = {
    # ── Activity ──────────────────────────────────────────────────────────────
    "step-count": {
        "data_type_name": "com.huawei.continuous.steps.total",
        "scope": "https://www.huawei.com/healthkit/step.read",
        "description": "Step count (continuous, daily total)",
    },
    "calories": {
        "data_type_name": "com.huawei.continuous.calories.burnt.total",
        "scope": "https://www.huawei.com/healthkit/calories.read",
        "description": "Calories burned (continuous)",
    },
    "activity-record": {
        "data_type_name": "com.huawei.data.activity-record",
        "scope": "https://www.huawei.com/healthkit/activity.record.read",
        "description": "Exercise sessions (sport type, duration, HR, distance)",
    },
    # ── Sleep ─────────────────────────────────────────────────────────────────
    "sleep": {
        "data_type_name": "com.huawei.continuous.sleep.fragment",
        "scope": "https://www.huawei.com/healthkit/sleep.read",
        "description": "Sleep stages (awake, light, deep, REM) and summary",
    },
    # ── Heart & vitals ────────────────────────────────────────────────────────
    "heart-rate": {
        "data_type_name": "com.huawei.continuous.heart_rate.statistics",
        "scope": "https://www.huawei.com/healthkit/heartrate.read",
        "description": "Heart rate samples (continuous)",
    },
    "blood-oxygen": {
        "data_type_name": "com.huawei.instantaneous.blood_oxygen_saturation",
        "scope": "https://www.huawei.com/healthkit/oxygenSaturation.read",
        "description": "SpO2 spot-check readings",
    },
    "blood-pressure": {
        "data_type_name": "com.huawei.instantaneous.blood_pressure",
        "scope": "https://www.huawei.com/healthkit/bloodPressure.read",
        "description": "Systolic/diastolic blood pressure readings",
    },
    "stress": {
        "data_type_name": "com.huawei.continuous.stress.statistics",
        "scope": "https://www.huawei.com/healthkit/stress.read",
        "description": "Stress level score (continuous)",
    },
    # ── Body ──────────────────────────────────────────────────────────────────
    "weight": {
        "data_type_name": "com.huawei.instantaneous.body.weight",
        "scope": "https://www.huawei.com/healthkit/bodyWeight.read",
        "description": "Body weight measurements",
    },
}


class Huawei(HealthProvider):
    """Huawei Health Kit provider (HMS OAuth 2.0).

    Usually accessed via ``tb.huawei`` rather than instantiated directly.

    Requires AppGallery Connect registration and Health Kit scope approval.

    .. code-block:: python

        sleep = tb.huawei.fetch("p001", "sleep", start, end)
    """

    PROVIDER_ID = "huawei"

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
            "Huawei Health Kit provider is not yet implemented. "
            "Requires AppGallery Connect registration with Health Kit scope. "
            "See python/tokenbridge/providers/huawei.py to contribute."
        )
