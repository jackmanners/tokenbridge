"""
tokenbridge — OAuth token management + health data for research.

Quick start:
    from tokenbridge import TokenBridge

    tb = TokenBridge()                # reads .env — run `python -m tokenbridge` to set up

    # Set default provider once (optional — google-health is the default)
    tb.provider = "google-health"

    # Onboard participants
    tb.auth_url("p001")
    tb.auth_urls(["p001", "p002", "p003"])

    # Fetch data
    tb.fetch("p001", "sleep", "2026-05-01", "2026-06-18")
    tb.fetch("p001", "steps", "2026-05-01", "2026-06-18")

    # Provider namespace shorthand (always uses google-health regardless of tb.provider)
    tb.google.fetch("p001", "heart-rate-variability", "2026-05-01", "2026-06-18")

    # One-off provider override without changing tb.provider
    tb.fetch("p001", "sleep", start, end, provider="withings")

    # Efficient: get token once when fetching multiple types for the same user
    token = tb.get_token("p001")
    tb.fetch("p001", "sleep", start, end, token=token)
    tb.fetch("p001", "steps", start, end, token=token)

    # Analysis helpers
    tb.google.summary("p001", "2026-05-01", "2026-06-18")
    tb.google.data_completeness(["p001", "p002"], "2026-05-01", "2026-06-18")

Data type IDs: see docs/providers.md, or:
    from tokenbridge.providers.google_health import DATA_TYPES
    print(list(DATA_TYPES))
"""

from tokenbridge._client import TokenBridge
from tokenbridge.providers.google_health import GoogleHealth, DATA_TYPES
from tokenbridge.providers.withings import Withings
from tokenbridge.providers.oura import Oura

__all__ = ["TokenBridge", "GoogleHealth", "Withings", "Oura", "DATA_TYPES"]
__version__ = "0.1.0"
