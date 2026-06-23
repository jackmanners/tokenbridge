# Provider Reference

A central registry of supported health data providers, integration requirements, and available data streams.

---

## Supported Providers

| Provider | Core Hardware Requirement | Auth / Account Requirement | Available Data Streams | Status |
| :--- | :--- | :--- | :--- | :--- |
| [**Google Health**](google-health.md) | Smartphone / Wearable | Fitbit app + Google Account | Activity, Sleep, Vitals | `Stable` |
| [**Withings**](withings.md) | Smart Scale, BPM, Sleep Mat | Withings ecosystem login | Weight, Blood Pressure, Sleep | `Stable` |
| [**Oura**](oura.md) | Oura Ring (Gen 2 / 3) | Oura Cloud account | Sleep, Readiness, Activity | `Stable` |

***

### 💡 Quick Integration Notes
* All providers require user OAuth2 authorization before data fetching begins.
* Rate limits apply globally across all endpoints based on individual provider restrictions.
