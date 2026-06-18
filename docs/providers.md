# TokenBridge Provider Reference

Central source of truth for all supported health data providers and their data types.
Both the Python and R packages are generated from this reference — update here first,
then propagate changes to `python/tokenbridge/providers/` and `r/R/`.

---

## Providers

| Provider ID | Status | Notes |
|---|---|---|
| `google-health` | Supported | Requires Fitbit app linked to a Google account |
| `withings` | Stub | Auth flow wired; data fetch not yet implemented |

---

## Google Health (`google-health`)

**API base:** `https://health.googleapis.com/v4/users/me`  
**Auth:** OAuth 2.0 with PKCE, scopes `https://www.googleapis.com/auth/googlehealth.*`  
**Backend:** Google Health Connect — data comes from Fitbit (and other apps the user has linked)

### Endpoint types

| Type | HTTP | Path |
|---|---|---|
| `list` | `GET` | `/dataTypes/{type}/dataPoints` |
| `dailyRollup` | `POST` | `/dataTypes/{type}/dataPoints:dailyRollUp` |

The `list` endpoint does **not** accept date filter query params — filtering must be done
client-side by comparing `startTime.seconds` to epoch boundaries.

The `dailyRollup` endpoint accepts a JSON body `{"startDate": "YYYY-MM-DD", "endDate": "YYYY-MM-DD"}`.

Three types only support `dailyRollup` (no raw datapoints available):
`floors`, `total-calories`, `calories-in-heart-rate-zone`.

### Data types

| Type ID | Category | Description | Unit | Endpoint | Notes |
|---|---|---|---|---|---|
| `sleep` | Sleep | Sleep sessions with stages | — | list | One record per session |
| `respiratory-rate-sleep-summary` | Sleep | Per-sleep RR summary | breaths/min | list | |
| `daily-sleep-temperature-derivations` | Sleep | Skin temp deviation during sleep | °C | list | Requires Fitbit Sense / Charge 6+ |
| `steps` | Activity | Step count intervals | steps | list | |
| `distance` | Activity | Distance intervals | mm | list | |
| `exercise` | Activity | Exercise sessions | — | list | Includes type, duration, GPS if available |
| `active-minutes` | Activity | Active minutes intervals | min | list | |
| `active-zone-minutes` | Activity | AZM broken down by HR zone | min | list | |
| `active-energy-burned` | Activity | Active (non-resting) calories | kcal | list | |
| `activity-level` | Activity | Activity level intervals | — | list | Sedentary/light/moderate/vigorous |
| `sedentary-period` | Activity | Sedentary intervals | — | list | |
| `altitude` | Activity | Altitude samples | m | list | |
| `swim-lengths-data` | Activity | Swim length data | — | list | Requires swim tracking device |
| `time-in-heart-rate-zone` | Activity | Time in each HR zone | min | list | |
| `floors` | Activity | Floors climbed | floors | **dailyRollup** | No raw datapoints |
| `total-calories` | Activity | Total daily calories (active + resting) | kcal | **dailyRollup** | No raw datapoints |
| `calories-in-heart-rate-zone` | Activity | Calories burned while in HR zone | kcal | **dailyRollup** | No raw datapoints |
| `vo2-max` | Activity | VO2 max estimate (raw) | mL/kg/min | list | |
| `run-vo2-max` | Activity | VO2 max from run | mL/kg/min | list | |
| `daily-vo2-max` | Activity | Daily VO2 max estimate | mL/kg/min | list | |
| `heart-rate` | Heart | Continuous HR samples | bpm | list | High volume — paginate carefully |
| `daily-resting-heart-rate` | Heart | Daily resting HR | bpm | list | |
| `daily-heart-rate-zones` | Heart | Daily time in HR zones | min | list | |
| `heart-rate-variability` | Heart | HRV samples (RMSSD) | ms | list | |
| `daily-heart-rate-variability` | Heart | Daily HRV summary | ms | list | |
| `electrocardiogram` | Heart | ECG recordings | — | list | Requires ECG-capable device |
| `irregular-rhythm-notification` | Heart | AFib / irregular rhythm alerts | — | list | |
| `oxygen-saturation` | Vitals | SpO2 samples | % | list | |
| `daily-oxygen-saturation` | Vitals | Daily SpO2 summary | % | list | |
| `daily-respiratory-rate` | Vitals | Daily resting RR | breaths/min | list | Distinct from sleep RR |
| `core-body-temperature` | Vitals | Core body temp samples | °C | list | Requires compatible device |
| `blood-glucose` | Vitals | Blood glucose measurements | mmol/L | list | Requires CGM or manual log |
| `weight` | Body | Weight measurements | kg | list | |
| `body-fat` | Body | Body fat percentage | % | list | |
| `height` | Body | Height measurements | mm | list | |
| `food` | Nutrition | Food log entries | — | list | |
| `nutrition-log` | Nutrition | Nutrition log (macros etc.) | — | list | |
| `hydration-log` | Nutrition | Hydration log | mL | list | |

### Known limitations

- The `startTime` / `endTime` query params on the `list` endpoint return HTTP 400 — filter client-side.
- Test-mode OAuth apps support up to 100 users. Production verification requires a Google review.
- Data availability depends on the user's device and Fitbit app sync status.
- `heart-rate` (raw continuous) can return thousands of records per day — use a token and paginate.

---

## Withings (`withings`)

**API base:** `https://wbsapi.withings.net`  
**Status:** Auth flow wired; fetch not yet implemented.

Planned data types (post-implementation):

| Type ID | Category | Description |
|---|---|---|
| `sleep` | Sleep | Sleep summary with stages |
| `heart-rate` | Heart | Resting HR from Withings devices |
| `weight` | Body | Weight from Withings scale |
| `blood-pressure` | Vitals | Systolic / diastolic from Withings cuff |

---

## Adding a new provider

1. Add the provider to the table above with its status and base URL
2. Add OAuth config to `supabase/functions/_shared/providers.ts`
3. Add a data types section to this file
4. Implement `python/tokenbridge/providers/{provider}.py` (subclass `HealthProvider`)
5. Implement `r/R/{provider}.R` (follow `google_health.R` pattern)
6. Register the provider in `TokenBridge._get_provider()` (Python) and `tb_fetch()` (R)
7. Export new functions in `r/NAMESPACE`
