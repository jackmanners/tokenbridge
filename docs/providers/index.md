# Provider Reference

A central registry of supported health data providers, integration requirements, and available data streams.

---

## Supported Providers

| Provider | Core Hardware Requirement | Auth / Account Requirement | Available Data Streams | Status |
| :--- | :--- | :--- | :--- | :--- |
| [**Google Health**](google-health.md) | Smartphone / Wearable | Fitbit app + Google Account | Activity, Sleep, Vitals | `Stable` |
| [**Withings**](withings.md) | Smart Scale, BPM, Sleep Mat | Withings ecosystem login | Weight, Blood Pressure, Sleep | `Stable` |
| [**Oura**](oura.md) | Oura Ring (Gen 2 / 3) | Oura Cloud account | Sleep, Readiness, Activity | `Stable` |
| [**Polar**](polar.md) | Polar watch / H-series HR strap | Polar Flow account + AccessLink app | Sleep, Activity, Nightly Recharge, Exercise | `Stable` |
| [**Strava**](strava.md) | Any GPS-capable device (via upload) | Strava account | Activities, HR/power/GPS streams | `Stable` |
| [**WHOOP**](whoop.md) | WHOOP band (4.0 / 5.0) | WHOOP account | Recovery, Sleep, Workout, Cycle | `Stable` |
| **Garmin** | Garmin watch | Garmin Connect + developer program approval | Activity, Sleep, Body Comp, HRV, Stress | `Stub` — requires invite-only approval |
| **Huawei Health Kit** | Huawei watch/band | Huawei ID + AppGallery Connect scope grant | Steps, Sleep, HR, SpO2, BP | `Stub` |
| **Health Connect** | Any Android phone | Gateway app on participant's device | Steps, Sleep, HR, HRV, SpO2, BP, Weight | `Stub` — no cloud OAuth, needs a gateway app |
| **Dexcom** | Dexcom CGM sensor | Dexcom developer account | Glucose (EGVs), Events, Calibrations, Devices | `Stub` — sandbox is self-service; production needs a short application |

***

### 💡 Quick Integration Notes
* All OAuth-based providers require user authorization before data fetching begins. Health Connect is the exception — see its stub for why.
* Rate limits apply globally across all endpoints based on individual provider restrictions. Strava in particular caps at 200 req/15min and 2000 req/day.
* Polar access tokens do not expire (no refresh flow); most others use standard refresh-token rotation.
* `Stub` providers raise `NotImplementedError` on `fetch()` — see each provider's module docstring in `python/tokenbridge/providers/` for implementation status and blockers.
