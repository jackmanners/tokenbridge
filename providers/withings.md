# Withings (`withings`)

**API base:** `https://wbsapi.withings.net`  
**Auth:** OAuth 2.0 (no PKCE), scopes `user.info user.metrics user.activity user.sleepevents`  
**Backend:** Withings devices (scales, blood pressure monitors, sleep mats, activity trackers)  
**Response envelope:** All responses are `{ "status": 0, "body": { ... } }` - status 0 = success

## Endpoint types

| Pattern | Date params | Pagination |
|---|---|---|
| YMD endpoints (`/v2/sleep getsummary`, `/v2/measure getactivity`, `/v2/measure getworkouts`) | `startdateymd` / `enddateymd` (YYYY-MM-DD) | `more` boolean + `offset` integer |
| Unix endpoints (`/measure getmeas`, `/v2/sleep get`, `/v2/heart list`) | `startdate` / `enddate` (epoch seconds) | `more` boolean + `offset` integer |

## Data types

| Type ID | Category | Description | Unit | Notes |
|---|---|---|---|---|
| `sleep-summary` | Sleep | Daily sleep summary with stages | s | One row per sleep session; total_sleep_time, rem/light/deep durations, efficiency |
| `sleep-detail` | Sleep | High-frequency sleep stage data | - | Raw 30-second epoch data; best for detailed analysis |
| `activity` | Activity | Daily activity summary | - | steps, distance, calories, active_calories, elevation |
| `workouts` | Activity | Individual workout sessions | - | category, duration, calories, intensity |
| `weight` | Body | Weight measurements | kg | Value decoded from Withings int+exponent encoding |
| `height` | Body | Height measurements | m | |
| `fat-ratio` | Body | Body fat percentage | % | Requires BIA-capable Withings scale |
| `fat-mass` | Body | Fat mass | kg | Requires BIA-capable Withings scale |
| `blood-pressure` | Vitals | Blood pressure (systolic + diastolic in same row) | mmHg | Requires Withings blood pressure monitor |
| `heart-rate` | Vitals | Resting heart rate from BPM/scale devices | bpm | Distinct from activity HR |
| `spo2` | Vitals | Blood oxygen saturation | % | Requires compatible Withings device |
| `muscle-mass` | Body | Muscle mass | kg | Requires BIA-capable scale |
| `bone-mass` | Body | Bone mass | kg | Requires BIA-capable scale |
| `ecg` | Heart | ECG recording metadata (signal IDs) | - | Use Withings Heart v2 - Get for raw signal |

## Measure value decoding

Body measurement values from `/measure getmeas` are encoded as `value × 10^unit` (e.g. `value=800` `unit=-1` → `80.0 kg`). The client decodes this automatically - returned dicts already have the real numeric value under named columns like `weight_kg`, `fat_ratio_pct`, etc.

## Known limitations

- The Withings API requires re-authorisation when the refresh token expires (unlike Google, which issues long-lived refresh tokens). If a user's token is invalidated, `tb_get_token()` raises an error with a re-auth link.
- Some data types (BIA measurements, ECG) require specific Withings hardware.
- Test accounts (demo mode) have dummy data - use `action=getdemoaccess` in the Withings developer dashboard to access it.

## Setup

**Requires:** A Withings developer account. Data comes from Withings devices (scales, blood pressure monitors, sleep mats, activity trackers).

**Create a Withings app:**

1. Sign up at [developer.withings.com](https://developer.withings.com) and go to your [Dashboard](https://developer.withings.com/dashboard/)
2. Click **Create an application**
3. Fill in app name and description
4. Under **Callback URL**, add `https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-callback`
5. Save and copy the **Client ID** and **Consumer Secret**

**Add secrets to Supabase** (Project Settings → Edge Functions → Secrets):

| Secret name | Value |
|---|---|
| `WITHINGS_CLIENT_ID` | Client ID from above |
| `WITHINGS_CLIENT_SECRET` | Consumer Secret from above |

**Test** - visit this URL, you should be redirected to Withings authorisation:

`https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-start?provider=withings&user_id=test`