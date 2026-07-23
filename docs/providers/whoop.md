# WHOOP (`whoop`)

**API base:** `https://api.prod.whoop.com/developer/v1`
**Auth:** OAuth 2.0 with PKCE, scopes `read:recovery read:sleep read:workout read:profile read:cycles read:body_measurement offline`
**Backend:** WHOOP band (4.0 / 5.0)
**Response envelope:** `{ "records": [...], "next_token": "..." }`

## Key differences from other providers

- **Recovery has no standalone ID.** A `recovery` record is keyed by `cycle_id` — the physiological day it belongs to — not its own id. TokenBridge returns it as-is rather than joining it against `cycle`/`sleep`; join manually on `cycle_id` if you need one row per day, since which fields to combine is analysis-specific.
- **Smaller page size.** WHOOP caps pagination at 25 records per page (vs larger page sizes elsewhere) — `fetch()` paginates transparently via `next_token`.
- **Refresh tokens are single-use.** Each refresh invalidates the previous refresh token, unlike Withings/Google's more forgiving refresh behaviour. TokenBridge's `/token` endpoint already handles this correctly — noted here in case you see auth errors after a manual token exchange outside TokenBridge.

## Data types

| Type ID | Endpoint | Description |
|---|---|---|
| `recovery` | `/recovery` | Daily recovery score, HRV (RMSSD), resting HR, SpO2 — keyed by `cycle_id` |
| `sleep` | `/activity/sleep` | Sleep performance %, efficiency %, stage breakdown, disturbances |
| `workout` | `/activity/workout` | Workout strain, sport, HR zones, distance, calories |
| `cycle` | `/cycle` | Physiological cycle (day): strain, avg/max HR, calories |

## Known limitations

- `recovery` and `sleep` records reference each other via `cycle_id`/`sleep_id` but WHOOP does not guarantee 1:1 alignment on days with irregular sleep (e.g. naps, missed nights).
- `sport_name` is a human-readable label; `sport_id` is the stable numeric identifier if you need to key on it.

## Setup

**Requires:** A WHOOP developer account.

**Create a WHOOP app:**

1. Sign up at [developer.whoop.com](https://developer.whoop.com) and register an app
2. Under **Redirect URI**, add `https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-callback`
3. Copy the **Client ID** and **Client Secret**

**Add secrets to Supabase** (Project Settings → Edge Functions → Secrets):

| Secret name | Value |
|---|---|
| `WHOOP_CLIENT_ID` | Client ID from above |
| `WHOOP_CLIENT_SECRET` | Client Secret from above |

**Test** — visit this URL, you should be redirected to WHOOP authorisation:

`https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-start?provider=whoop&user_id=test`
