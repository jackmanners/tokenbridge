"""Dexcom API provider (continuous glucose monitoring).

Wraps the Dexcom API v3 - uses TokenBridge for auth.

Dexcom's developer program is tiered: Sandbox access is immediate and
self-service (returns simulated glucose data), production access for real
users requires a short application but no lengthy sales process for small
participant counts.

Setup:
    Register at https://developer.dexcom.com - create an app and add secrets:
        DEXCOM_CLIENT_ID
        DEXCOM_CLIENT_SECRET

    Sandbox base URL: https://sandbox-api.dexcom.com
    Production base URL: https://api.dexcom.com

See https://developer.dexcom.com/docs for field-level details.
"""

from typing import Optional

import requests

from tokenbridge.providers._base import HealthProvider

_BASE = "https://api.dexcom.com/v3"

DATA_TYPES: dict[str, dict] = {
    # ── Glucose ───────────────────────────────────────────────────────────────
    "egvs": {
        "path": "/users/self/egvs",
        "description": "Estimated glucose values (EGVs) - readings every 5 minutes",
    },
    # ── Events ────────────────────────────────────────────────────────────────
    "events": {
        "path": "/users/self/events",
        "description": "User-logged events: carbs, insulin, exercise, health status",
    },
    # ── Device ────────────────────────────────────────────────────────────────
    "devices": {
        "path": "/users/self/devices",
        "description": "Transmitter/receiver/app device info and last upload time",
    },
    # ── Calibrations ──────────────────────────────────────────────────────────
    "calibrations": {
        "path": "/users/self/calibrations",
        "description": "Sensor calibration events (fingerstick values used to calibrate)",
    },
}


class Dexcom(HealthProvider):
    """Dexcom API provider (continuous glucose monitoring).

    Usually accessed via ``tb.dexcom`` rather than instantiated directly.

    .. code-block:: python

        glucose = tb.dexcom.fetch("p001", "egvs", start, end)
    """

    PROVIDER_ID = "dexcom"

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
            "Dexcom provider is not yet implemented. "
            "See python/tokenbridge/providers/dexcom.py to contribute."
        )
