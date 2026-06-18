"""Abstract base class for health data providers."""

from abc import ABC


class HealthProvider(ABC):
    """
    Base class for health data providers (Google Health, Withings, etc.).

    Each provider wraps a TokenBridge instance and fetches data from its
    own upstream API using tokens obtained via TokenBridge.  Subclasses
    set PROVIDER_ID to the string expected by the /token endpoint.
    """

    PROVIDER_ID: str  # e.g. "google-health", "withings"

    def __init__(self, tb):
        self.tb = tb

    def _get_token(self, user_id: str) -> str:
        return self.tb.get_token(user_id, provider=self.PROVIDER_ID)
