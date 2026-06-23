# Oura (`oura`)

**API base:** `https://api.ouraring.com/v2/usercollection`  
**Auth:** OAuth 2.0 (no PKCE), scopes `email personal daily heartrate workout tag session spo2Daily`  
**Backend:** Oura Ring (Gen 2 or Gen 3)  
**Response envelope:** `{ "data": [...], "next_token": "..." }` — standard REST pagination

## Endpoint types

| Pattern | Date params | Pagination |
|---|---|---|
| Date endpoints (all except heartrate) | `start_date` / `end_date` (YYYY-MM-DD) | `next_token` cursor |
| Datetime endpoints (`heartrate`) | `start_datetime` / `end_datetime` (ISO 8601 UTC) | `next_token` cursor |

## Data types

| Type ID | Category | Description | Notes |
|---|---|---|---|
| `daily-activity` | Activity | Daily activity summary | steps, calories, active calories, MET minutes, activity score |
| `daily-sleep` | Sleep | Daily sleep score + contributors | High-level summary; use `sleep` for full detail |
| `sleep` | Sleep | Detailed sleep sessions | Per-session: HRV, HR, stages, efficiency, latency, awake time |
| `sleep-time` | Sleep | Recommended bedtime window | Optimal sleep timing computed by Oura |
| `daily-readiness` | Readiness | Readiness score + contributors | Temperature deviation, recovery index, etc. |
| `daily-stress` | Stress | Daytime stress and recovery summary | Stress high / recovery high / day summary |
| `daily-spo2` | Vitals | Nightly SpO2 average | Breathing disturbance index included |
| `daily-resilience` | Resilience | Long-term resilience score | Requires Gen 3 |
| `cardiovascular-age` | Vitals | Estimated cardiovascular age | Pulse wave velocity + vascular age estimate; requires Gen 3 |
| `heartrate` | Heart | Continuous heart rate stream | 5-second intervals; uses datetime params not date params |
| `workout` | Activity | Auto-detected and manual workouts | type, duration, calories, distance, intensity |
| `session` | Wellbeing | Guided / unguided meditation sessions | HR and HRV time series included |
| `vo2-max` | Fitness | VO2 max estimate | Requires recent activity data |
| `tag` | Tags | User-entered tags | |
| `enhanced-tag` | Tags | Enhanced tags with context | |

## Known limitations

- `heartrate` (continuous 5-second stream) can return very large volumes — use a token and reasonable date windows.
- `daily-resilience`, `cardiovascular-age`, and `daily-spo2` require Oura Ring Gen 3.
- Oura refresh tokens do not expire by time but are invalidated if the user revokes access. The weekly keepalive will detect failures and log them.
- The Oura sandbox (`/v2/sandbox/usercollection/...`) can be used for testing without a real ring — same paths, just prefix with `/sandbox`.

## Setup

**Requires:** An Oura developer account. Data comes from Oura Ring devices.

**Create an Oura app:**

1. Sign in at [cloud.ouraring.com](https://cloud.ouraring.com) and go to **My Apps → Create New App**
2. Fill in your app name and description
3. Under **Redirect URIs**, add `https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-callback`
4. Save and copy the **Client ID** and **Client Secret**

**Add secrets to Supabase** (Project Settings → Edge Functions → Secrets):

| Secret name | Value |
|---|---|
| `OURA_CLIENT_ID` | Client ID from above |
| `OURA_CLIENT_SECRET` | Client Secret from above |

**Test** — visit this URL, you should be redirected to Oura authorisation:

`https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-start?provider=oura&user_id=test`