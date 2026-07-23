# Strava (`strava`)

**API base:** `https://www.strava.com/api/v3`
**Auth:** OAuth 2.0 (no PKCE), scopes `activity:read_all profile:read_all`
**Backend:** Any GPS-capable device — data is uploaded to Strava, not read from a specific wearable
**Response envelope:** Bare JSON array (activities) or a keyed object (streams)

## Key differences from other providers

- **Two-tier data model.** `fetch()` returns activity *summaries* for a date range, same as every other provider. Per-activity time-series detail (heart rate, power, GPS track) doesn't fit that shape — it's keyed by a single `activity_id`, not a date range — so it's exposed separately as `tb.strava.streams(user_id, activity_id, keys=[...])`, called after you've picked an activity from the `fetch()` results.
- **Unix timestamps, not date strings**, for the underlying `before`/`after` params (handled internally — you still pass `"YYYY-MM-DD"` to `fetch()`).
- **page/per_page pagination**, not cursor-based like most other providers here.
- **Strict rate limits**: 200 requests / 15 min, 2000 / day. `fetch()` and `streams()` raise a clear `RuntimeError` on HTTP 429 rather than retrying silently — retry/backoff policy is left to the caller.

## Data types

| Type ID | Endpoint | Description |
|---|---|---|
| `activities` | `/athlete/activities` | All activities (runs, rides, swims, etc.) with summary stats: type, distance, moving/elapsed time, elevation gain, average/max HR, average watts |

## Streams (per-activity)

```python
activities = tb.strava.fetch("p001", "activities", start, end)
streams = tb.strava.streams("p001", activities[0]["id"], keys=["heartrate", "watts", "latlng"])
# streams == {"heartrate": {"data": [...], "series_type": "distance", ...}, "watts": {...}, "latlng": {...}}
```

Available stream keys: `time`, `distance`, `latlng`, `altitude`, `velocity_smooth`, `heartrate`, `cadence`, `watts`, `temp`, `moving`, `grade_smooth`. `heartrate`/`watts`/etc. are simply absent from the response for activities recorded without that sensor.

## Known limitations

- Activities recorded manually (no GPS device) have no stream data at all.
- Rate limits are shared across your entire Strava app, not per-participant — be mindful when fetching for many participants in one script.
- `average_heartrate` / `average_watts` are only present when the activity has that sensor data.

## Setup

**Requires:** A Strava developer account (uses your normal Strava login).

**Create a Strava app:**

1. Go to [strava.com/settings/api](https://www.strava.com/settings/api) and create an app
2. Under **Authorization Callback Domain**, enter just the domain — e.g. `YOUR_PROJECT_REF.supabase.co` (Strava matches by domain, not exact URL)
3. Copy the **Client ID** and **Client Secret**

**Add secrets to Supabase** (Project Settings → Edge Functions → Secrets):

| Secret name | Value |
|---|---|
| `STRAVA_CLIENT_ID` | Client ID from above |
| `STRAVA_CLIENT_SECRET` | Client Secret from above |

**Test** — visit this URL, you should be redirected to Strava authorisation:

`https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-start?provider=strava&user_id=test`
