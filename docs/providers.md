# TokenBridge Provider Reference

Central source of truth for all supported health data providers and their data types.
Both the Python and R packages are generated from this reference — update here first,
then propagate changes to `python/tokenbridge/providers/` and `r/R/`.

---

## Providers

| Provider ID | Status | Notes |
|---|---|---|
| `google-health` | Supported | Requires Fitbit app linked to a Google account |
| `withings` | Supported | Requires Withings device (scale, BPM cuff, sleep mat, etc.) |

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
**Auth:** OAuth 2.0 (no PKCE), scopes `user.info user.metrics user.activity user.sleepevents`  
**Backend:** Withings devices (scales, blood pressure monitors, sleep mats, activity trackers)  
**Response envelope:** All responses are `{ "status": 0, "body": { ... } }` — status 0 = success

### Endpoint types

| Pattern | Date params | Pagination |
|---|---|---|
| YMD endpoints (`/v2/sleep getsummary`, `/v2/measure getactivity`, `/v2/measure getworkouts`) | `startdateymd` / `enddateymd` (YYYY-MM-DD) | `more` boolean + `offset` integer |
| Unix endpoints (`/measure getmeas`, `/v2/sleep get`, `/v2/heart list`) | `startdate` / `enddate` (epoch seconds) | `more` boolean + `offset` integer |

### Data types

| Type ID | Category | Description | Unit | Notes |
|---|---|---|---|---|
| `sleep-summary` | Sleep | Daily sleep summary with stages | s | One row per sleep session; total_sleep_time, rem/light/deep durations, efficiency |
| `sleep-detail` | Sleep | High-frequency sleep stage data | — | Raw 30-second epoch data; best for detailed analysis |
| `activity` | Activity | Daily activity summary | — | steps, distance, calories, active_calories, elevation |
| `workouts` | Activity | Individual workout sessions | — | category, duration, calories, intensity |
| `weight` | Body | Weight measurements | kg | Value decoded from Withings int+exponent encoding |
| `height` | Body | Height measurements | m | |
| `fat-ratio` | Body | Body fat percentage | % | Requires BIA-capable Withings scale |
| `fat-mass` | Body | Fat mass | kg | Requires BIA-capable Withings scale |
| `blood-pressure` | Vitals | Blood pressure (systolic + diastolic in same row) | mmHg | Requires Withings blood pressure monitor |
| `heart-rate` | Vitals | Resting heart rate from BPM/scale devices | bpm | Distinct from activity HR |
| `spo2` | Vitals | Blood oxygen saturation | % | Requires compatible Withings device |
| `muscle-mass` | Body | Muscle mass | kg | Requires BIA-capable scale |
| `bone-mass` | Body | Bone mass | kg | Requires BIA-capable scale |
| `ecg` | Heart | ECG recording metadata (signal IDs) | — | Use Withings Heart v2 - Get for raw signal |

### Measure value decoding

Body measurement values from `/measure getmeas` are encoded as `value × 10^unit` (e.g. `value=800` `unit=-1` → `80.0 kg`). The client decodes this automatically — returned dicts already have the real numeric value under named columns like `weight_kg`, `fat_ratio_pct`, etc.

### Known limitations

- The Withings API requires re-authorisation when the refresh token expires (unlike Google, which issues long-lived refresh tokens). If a user's token is invalidated, `tb_get_token()` raises an error with a re-auth link.
- Some data types (BIA measurements, ECG) require specific Withings hardware.
- Test accounts (demo mode) have dummy data — use `action=getdemoaccess` in the Withings developer dashboard to access it.

---

## Adding a new provider

1. Add the provider to the table above with its status and base URL
2. Add OAuth config to `supabase/functions/_shared/providers.ts`
3. Add a data types section to this file
4. Implement `python/tokenbridge/providers/{provider}.py` (subclass `HealthProvider`)
5. Implement `r/R/{provider}.R` (follow `google_health.R` pattern)
6. Register the provider in `TokenBridge._get_provider()` (Python) and `tb_fetch()` (R)
7. Export new functions in `r/NAMESPACE`
