# TokenBridge Python Client — API Spec

## Setup

```bash
pip install git+https://github.com/jackmanners/tokenbridge.git#subdirectory=python
```

**.env** (read automatically):
```
TOKENBRIDGE_URL=https://xxx.supabase.co/functions/v1
TOKENBRIDGE_API_KEY=your-key
SLEEPSCAN_API_KEY=your-key        # optional — enables sleepscan=True
CLINIC_SLEEPSCAN_KEY=your-key     # optional — automatic fallback if SleepScan fails
```

---

## TokenBridge(url, api_key, env_file, provider, sleepscan_key)

All args optional — read from env if omitted. `provider` defaults to `"google-health"`.

### .fetch(user_id, data_type, start_date, end_date, *, provider, token, sleepscan, raw) → list[dict]

Core method. `start_date`/`end_date` are `"YYYY-MM-DD"`.

**Token resolution (first match wins):**
1. `sleepscan=True` → SleepScan API, then Clinic fallback
2. `token=<str>` → used directly
3. Default → TokenBridge `/token` endpoint using `user_id`

**When `sleepscan=True`**, `user_id` is the lookup key:
- contains `@` → by email
- `int` → by Withings user ID
- other `str` → by SleepScan participant ID

**`raw=True`** — skip all processing; returns list of raw page body dicts (one per paginated request). Zero transformation, exact API response.

```python
tb = TokenBridge()

# Normal (user authed via TokenBridge OAuth)
tb.fetch("p001", "sleep-summary", "2026-06-01", "2026-07-01", provider="withings")

# SleepScan
tb.fetch("p@lab.com", "sleep-summary", "2026-06-01", "2026-07-01", provider="withings", sleepscan=True)

# Token reuse
tok = tb.get_token("p001", provider="withings")
tb.fetch("p001", "sleep-summary", start, end, provider="withings", token=tok)
tb.fetch("p001", "blood-pressure", start, end, provider="withings", token=tok)

# Raw response bodies
bodies = tb.fetch("p001", "sleep-summary", start, end, provider="withings", raw=True)
```

### .get_token(user_id, provider, sleepscan) → str

Returns a valid access token. Auto-refreshes if near expiry. Raises `RuntimeError` with re-auth URL if missing or expired.

`sleepscan=True` fetches from SleepScan instead of TokenBridge (same lookup logic as `fetch()`). Useful when you want to reuse one token across multiple fetches without calling `fetch()` with `sleepscan=True` each time.

```python
# TokenBridge token — reuse across multiple fetches
tok = tb.get_token("p001", provider="withings")
tb.fetch("p001", "sleep-summary", start, end, token=tok)
tb.fetch("p001", "blood-pressure", start, end, token=tok)

# SleepScan token
tok = tb.get_token("p@lab.com", provider="withings", sleepscan=True)
tb.fetch("p@lab.com", "sleep-summary", start, end, token=tok)
tb.fetch("p@lab.com", "blood-pressure", start, end, token=tok)
```

### .auth_url(user_id, provider) → str
Returns `{TOKENBRIDGE_URL}/auth-start?provider={provider}&user_id={user_id}`. Send to participant to initiate OAuth.

### .auth_urls(user_ids, provider) → dict[str, str]
Batch version of `auth_url`.

### Provider namespaces: tb.google / tb.withings / tb.oura
Pre-bind a provider. All proxy to `tb.fetch()` with provider set. Also expose provider-specific methods.

```python
tb.withings.fetch("p001", "sleep-summary", start, end)
tb.google.fetch("p001", "sleep", start, end, sleepscan=True)
tb.google.summary("p001", start, end)               # GoogleHealth-specific
tb.google.data_completeness(["p001", "p002"], s, e) # GoogleHealth-specific
```

---

## Return data

**Data is minimally processed — close to the raw API response.**

### raw=True

Returns a `list` of raw page response bodies, one element per paginated request.

| Provider | Raw page body structure |
|---|---|
| `google-health` | `{"dataPoints": [...], "nextPageToken": "..."}` (list endpoint) or `{"dailyRollup": [...]}` (rollup endpoint) |
| `withings` | `{"status": 0, "body": {"series": [...], "more": False, "offset": N}}` |
| `oura` | `{"data": [...], "next_token": null}` |

### Google Health (`provider="google-health"`)

Each record is the raw `dataPoints[]` item from the Google Health v4 API, **recursively flattened** into a single dict with dot-notation keys. Lists become indexed keys (e.g. `sleep.stages.0.type`).

```python
# Raw API response item:
# { "sleep": { "interval": { "startTime": "...", "endTime": "..." }, "summary": { "minutesAsleep": "440" } } }

# Returned as:
{ "sleep.interval.startTime": "2026-06-30T13:42:00Z",
  "sleep.interval.endTime":   "2026-06-30T22:32:00Z",
  "sleep.summary.minutesAsleep": "440",
  "sleep.stages.0.type": "AWAKE",
  "sleep.stages.0.startTime": "...",
  ... }
```

One dict per data point (sleep session, step interval, HR sample, etc.).

Key fields by type:

| Type | Key fields |
|---|---|
| `sleep` | `sleep.interval.startTime`, `sleep.interval.endTime`, `sleep.summary.minutesAsleep`, `sleep.summary.minutesInSleepPeriod`, `sleep.summary.stagesSummary.N.type/minutes/count`, `sleep.stages.N.type/startTime/endTime` |
| `steps` | `steps.interval.startTime`, `steps.interval.endTime`, `steps.steps.count` |
| `heart-rate` | `heartRate.sampleTime`, `heartRate.bpm` |
| `heart-rate-variability` | `heartRateVariability.rmssd` |
| `exercise` | `exercise.interval.startTime`, `exercise.exerciseType`, `exercise.activeCalories` |

Full type list: `from tokenbridge.providers.google_health import DATA_TYPES; print(list(DATA_TYPES))`

### Withings (`provider="withings"`)

Data is extracted from `body[result_key]` in the Withings response envelope (`{ "status": 0, "body": { ... } }`). **Two processing cases:**

**Sleep/activity/workout types** (`sleep-summary`, `sleep-detail`, `activity`, `workouts`): records returned as-is from the API. Sleep summary `data` sub-dict contains per-session metrics.

```python
records = tb.fetch("p001", "sleep-summary", start, end, provider="withings")
r = records[0]
# r keys: id, timezone, model, model_id, hash_deviceid, startdate (unix),
#         enddate (unix), date (YYYY-MM-DD), data (dict), completed, created, modified
ahi = r["data"].get("apnea_hypopnea_index")   # float or None
eff = r["data"].get("sleep_efficiency")        # float 0–1
tst = r["data"].get("total_sleep_time")        # seconds
```

**Body measurement types** (`weight`, `blood-pressure`, `heart-rate`, `spo2`, etc.): raw Withings `measuregrps` are **decoded** — int+exponent encoding (`value × 10^unit`) resolved to named columns. Each group (timestamp) becomes one flat dict.

```python
records = tb.fetch("p001", "blood-pressure", start, end, provider="withings")
r = records[0]
# r keys: grpid, date (unix), category, systolic_bp_mmhg, diastolic_bp_mmhg, heart_rate_bpm
```

Named columns: `weight_kg`, `height_m`, `fat_ratio_pct`, `fat_mass_kg`, `systolic_bp_mmhg`, `diastolic_bp_mmhg`, `heart_rate_bpm`, `spo2_pct`, `muscle_mass_kg`, `bone_mass_kg`.

Full type list: `from tokenbridge.providers.withings import DATA_TYPES; print(list(DATA_TYPES))`

### Oura (`provider="oura"`)

Records returned as-is from `body["data"]` in the Oura v2 API response. No transformation applied.

Full type list: `from tokenbridge.providers.oura import DATA_TYPES; print(list(DATA_TYPES))`

---

## Reports

```python
import requests
resp = requests.post(
    f"{tb.url}/sleep-report",
    headers={"Authorization": f"Bearer {tb.api_key}"},
    json={"label": "P001", "template": "sleep-bp", "data": {
        "withings-summary": sleep_records,
        "withings-bp":      bp_records,
    }},
)
open("report.html", "wb").write(resp.content)
```

Templates: `full` (sleep), `sleep-bp` (sleep + BP), `bp` (BP only).

---

## SleepScan addon (internal, not part of tokenbridge proper)

Two usage patterns — integrated (recommended) and standalone.

### Integrated

```python
# fetch() with sleepscan=True
tb.fetch("p@lab.com", "sleep-summary", start, end, provider="withings", sleepscan=True)
tb.fetch(12345678,    "sleep-summary", start, end, provider="withings", sleepscan=True)
tb.fetch("SS-P001",   "sleep-summary", start, end, provider="withings", sleepscan=True)

# get_token() with sleepscan=True — reuse across multiple fetches
tok = tb.get_token("p@lab.com", provider="withings", sleepscan=True)
tb.fetch("p@lab.com", "sleep-summary",  start, end, token=tok)
tb.fetch("p@lab.com", "blood-pressure", start, end, token=tok)
```

### Standalone

```python
from tokenbridge.sleepscan import SleepScan
ss    = SleepScan(api_key="...", clinic_key="...")  # keys also read from env
token = ss.get_token(email="p@lab.com")             # or withings_user_id=123
# pass token= to tb.fetch() or any provider directly
```

**SleepScan endpoints (path params):**
- `GET https://sleepscan.app/withings-access-token/by-email/{email}` — `X-API-Key` header
- `GET https://sleepscan.app/withings-access-token/by-withings-user-id/{id}` — `X-API-Key` header

**Clinic fallback (automatic):**
- `POST https://clinic.sleepscan.app/api/tokens` — `Authorization: Bearer` header
- Body: `{"email": email, "force": true}`, retries with `force: false` on 403/404
- Parses `access_token` from top-level or `body.access_token`

---

## Errors

| Exception | Cause |
|---|---|
| `RuntimeError: TOKENBRIDGE_URL not set` | Missing env var |
| `RuntimeError: No token found for user '...'` | User not authorised — message contains auth URL |
| `RuntimeError: Token for '...' has expired` | Refresh token expired — user must re-authorise (Google: likely OAuth app in Testing mode, 7-day limit) |
| `requests.HTTPError` | Provider API non-2xx |
| `ValueError: Unknown ... data type` | Invalid `data_type` string |
| `RuntimeError: Could not retrieve Withings token from any source` | SleepScan + Clinic both failed |
