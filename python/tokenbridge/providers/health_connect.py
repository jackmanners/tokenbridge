"""Android Health Connect provider (gateway-based).

Health Connect is an Android SDK — it has no cloud REST API. To access Health
Connect data from a server, a gateway app must run on the participant's Android
device and relay data to TokenBridge.

Gateway approach:
    The recommended approach is an Android app (or Tasker/Automate shortcut)
    that reads from Health Connect locally and POSTs data to a TokenBridge
    ingest endpoint. One open-source reference implementation:
        https://github.com/shuchirj/HCGateway

    Unlike other providers, there is no OAuth flow — the gateway authenticates
    to TokenBridge using the participant's user_id and API key directly.

This file is a placeholder stub. Implementing Health Connect support requires:
    1. An Android gateway app or background service
    2. A TokenBridge ingest endpoint (edge function) to receive data
    3. Storage in the same oauth_tokens / data tables (or a separate store)

See docs/providers/health-connect.md for the planned architecture.
"""

from typing import Optional

from tokenbridge.providers._base import HealthProvider

# Health Connect data types mirror Android's HealthDataTypes constants.
# https://developer.android.com/reference/kotlin/androidx/health/connect/client/records/package-summary
DATA_TYPES: dict[str, dict] = {
    "steps":              {"description": "Step count records"},
    "distance":           {"description": "Distance travelled records"},
    "calories":           {"description": "Active and total calories burned"},
    "heart-rate":         {"description": "Heart rate samples"},
    "heart-rate-variability": {"description": "HRV (RMSSD) samples"},
    "sleep":              {"description": "Sleep sessions with stages"},
    "oxygen-saturation":  {"description": "SpO2 readings"},
    "blood-pressure":     {"description": "Systolic/diastolic readings"},
    "weight":             {"description": "Body weight measurements"},
    "exercise-session":   {"description": "Exercise sessions (type, duration, route)"},
    "respiratory-rate":   {"description": "Respiratory rate samples"},
}


class HealthConnect(HealthProvider):
    """Android Health Connect provider (gateway-based, not OAuth).

    This provider cannot be used directly — Health Connect requires a gateway
    app running on the participant's Android device. See module docstring.
    """

    PROVIDER_ID = "health-connect"

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
            "Health Connect requires a gateway app on the participant's Android device. "
            "See python/tokenbridge/providers/health_connect.py for the planned architecture."
        )
