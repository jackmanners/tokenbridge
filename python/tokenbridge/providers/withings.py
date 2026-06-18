"""
Withings provider — stub.

Not yet implemented.  The structure mirrors GoogleHealth so adding it later
is straightforward: implement _fetch_datapoints against the Withings API
and wire PROVIDER_ID = "withings" to the TokenBridge /token endpoint.

Withings API docs: https://developer.withings.com/developer-guide/v3/
"""

from tokenbridge.providers._base import HealthProvider


class Withings(HealthProvider):
    """Withings health data provider (not yet implemented)."""

    PROVIDER_ID = "withings"

    def fetch_sleep(self, user_id: str, start_date: str, end_date: str):
        raise NotImplementedError("Withings provider is not yet implemented.")

    def fetch_heart_rate(self, user_id: str, start_date: str, end_date: str):
        raise NotImplementedError("Withings provider is not yet implemented.")

    def fetch(self, user_id: str, measure_type: str, start_date: str, end_date: str):
        raise NotImplementedError("Withings provider is not yet implemented.")

    def summary(self, user_id: str, start_date: str, end_date: str):
        raise NotImplementedError("Withings provider is not yet implemented.")
