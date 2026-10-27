# API Spec — Python

Single-file reference for the Python package, written to be pasted whole into
an LLM's context when wiring TokenBridge into another project or script.

**TokenBridge's job is OAuth token management, full stop.** Get a token, then
call the provider's own API directly - see [Provider Reference](providers/index.md)
for each provider's API base URL and official docs. A convenience layer
(`tb.fetch()`) exists for providers already implemented and is covered at
the bottom of this page - it's kept up with provider data routes on a
best-effort basis, maintained more slowly than the core token layer, so it
may lag behind a provider's most recent API changes. Check the provider's
own API reference if something seems off or missing.

Raw file: https://raw.githubusercontent.com/jackmanners/tokenbridge/main/docs/apispec-python.md

---

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

## TokenBridge(url, api_key, env_file, provider, sleepscan_key)

All args optional — read from env if omitted. `provider` defaults to `"google-health"`, used by `auth_url()`/`get_token()` when `provider=` isn't passed.

### .auth_url(user_id, provider) → str

Returns `{TOKENBRIDGE_URL}/auth-start?provider={provider}&user_id={user_id}&exp={exp}&sig={sig}`. `exp`/`sig` are an HMAC-SHA256 signature (keyed with `TOKENBRIDGE_API_KEY`, 7-day lifetime) over `{provider}:{user_id}:{exp}` - `auth-start` verifies them before starting the OAuth flow, so a link can't be forged or have its `user_id` tampered with. Send the link to the participant to initiate OAuth.

```python
tb = TokenBridge()
print(tb.auth_url("p001", provider="withings"))
```

### .auth_urls(user_ids, provider) → dict[str, str]

Batch version of `auth_url`.

```python
urls = tb.auth_urls(["p001", "p002", "p003"], provider="withings")
```

### .get_token(user_id, provider, sleepscan) → str

Returns a valid access token for `user_id` + `provider`. Auto-refreshes if near expiry (calls the provider's token endpoint server-side and persists the new token). Raises `RuntimeError` with a re-auth URL baked into the message if the participant hasn't authorised yet (404) or their refresh token has expired (401).

`sleepscan=True` fetches the token from the SleepScan API instead (an alternate Withings token source used for participants who registered through SleepScan rather than TokenBridge's own OAuth flow) - same `user_id` lookup rules as below.

```python
tok = tb.get_token("p001", provider="withings")
# now call the provider's own API with it, e.g.:
import requests
resp = requests.get(
    "https://wbsapi.withings.net/v2/sleep",
    params={"action": "getsummary", "startdateymd": start, "enddateymd": end},
    headers={"Authorization": f"Bearer {tok}"},
)
```

## SleepScan — alternate token source (Withings only)

Some participants' Withings access was registered through a separate system (SleepScan) rather than TokenBridge's own OAuth flow. Use `sleepscan=True` on `get_token()` to pull their token from there instead - same interface, same downstream usage.

`user_id` is the lookup key when `sleepscan=True`:
- contains `@` → by email
- `int` → by Withings user ID
- other `str` → by SleepScan participant ID

```python
tok = tb.get_token("p@lab.com", provider="withings", sleepscan=True)
```

Standalone (without going through `TokenBridge`):
```python
from tokenbridge.sleepscan import SleepScan
ss    = SleepScan(api_key="...", clinic_key="...")  # keys also read from env
token = ss.get_token(email="p@lab.com")              # or withings_user_id=123
```

**SleepScan endpoints (path params):**
- `GET https://sleepscan.app/withings-access-token/by-email/{email}` — `X-API-Key` header
- `GET https://sleepscan.app/withings-access-token/by-withings-user-id/{id}` — `X-API-Key` header

**Clinic fallback (automatic):** `POST https://clinic.sleepscan.app/api/tokens` with `Authorization: Bearer`, body `{"email": email, "force": true}` (retries with `force: false` on 403/404).

## Reports

Server-rendered, self-contained HTML reports from data you've already fetched (sleep summaries, blood pressure over time, etc.):

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

Templates: `full` (sleep), `sleep-bp` (sleep + BP), `bp` (BP only). See [Reports & template authoring](reports.md).

## Errors

| Exception | Cause |
|---|---|
| `RuntimeError: TOKENBRIDGE_URL not set` | Missing env var |
| `RuntimeError: No token found for user '...'` | User not authorised — message contains auth URL |
| `RuntimeError: Token for '...' has expired` | Refresh token expired — user must re-authorise |
| `RuntimeError: Could not retrieve Withings token from any source` | SleepScan + Clinic both failed |
| `requests.HTTPError` | Non-2xx from a provider API call you made yourself with the token |

---

## Data-fetching layer (maintained, but slowly)

`tb.fetch(user_id, data_type, start_date, end_date, ...)` and the `tb.<provider>` namespaces (`tb.google`, `tb.withings`, `tb.oura`, `tb.polar`, `tb.strava`, `tb.whoop`) wrap each provider's data endpoints - pagination, date formatting, and (for Google Health/Withings) flattening raw nested fields into dicts. We do try to keep these in step with each provider's data routes, but **it's a secondary priority behind the OAuth/token layer**, so there can be a lag between a provider API change and this catching up. If a call starts behaving oddly or a field looks missing/renamed, check the provider's own API reference first - it's the source of truth.

Full function signatures and return shapes: [Python API Reference](python/reference.md). Per-provider setup/API base/official docs: [Provider Reference](providers/index.md).

```python
# Still works today:
sleep = tb.fetch("p001", "sleep-summary", start, end, provider="withings")
raw   = tb.fetch("p001", "sleep-summary", start, end, provider="withings", raw=True)  # zero transformation
```

`tb.garmin`, `tb.huawei`, `tb.health_connect`, `tb.dexcom` are registered but raise `NotImplementedError` - these were never finished and aren't planned to be; use `get_token()` for them and call the provider API yourself.
