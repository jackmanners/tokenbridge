# API Spec — R

Reference for the R package's auth and token functions - exact signatures,
return shapes, and error conditions.

**TokenBridge's job is OAuth token management, full stop.** Get a token, then
call the provider's own API directly - see [Provider Reference](providers/index.md)
for each provider's API base URL and official docs. A convenience layer
(`tb_fetch()`) exists for providers already implemented and is covered at
the bottom of this page - it's kept up with provider data routes on a
best-effort basis, maintained more slowly than the core token layer, so it
may lag behind a provider's most recent API changes. Check the provider's
own API reference if something seems off or missing.

Raw file: https://raw.githubusercontent.com/jackmanners/tokenbridge/main/docs/apispec-r.md

---

## Setup

```r
devtools::install_github("jackmanners/tokenbridge", subdir = "r")
```

**.env** (read automatically by every function via `env_file = ".env"`):
```
TOKENBRIDGE_URL=https://xxx.supabase.co/functions/v1
TOKENBRIDGE_API_KEY=your-key
SLEEPSCAN_API_KEY=your-key        # optional — enables sleepscan = TRUE
```

`tb_setup()` runs an interactive prompt and writes `.env` for you.

## tb_auth_url(user_id, provider, env_file) → character(1)

Returns `{TOKENBRIDGE_URL}/auth-start?provider={provider}&user_id={user_id}&exp={exp}&sig={sig}` - HMAC-SHA256-signed (keyed with `TOKENBRIDGE_API_KEY`, 7-day lifetime), same scheme as the Python client. Send to participant to initiate OAuth.

```r
tb_auth_url("p001", provider = "withings")
```

## tb_auth_urls(user_ids, provider, env_file) → named character vector

Batch version, named by `user_id`.

```r
links <- tb_auth_urls(c("p001", "p002", "p003"), provider = "withings")
```

## tb_get_token(user_id, provider, env_file) → character(1)

Returns a valid access token via the TokenBridge `/token` endpoint. Auto-refreshes if near expiry. `stop()`s with a re-auth URL baked into the message if the token is missing (HTTP 404) or the refresh token has expired (HTTP 401).

```r
tok <- tb_get_token("p001", provider = "withings")
# now call the provider's own API with it, e.g.:
resp <- httr::GET(
  "https://wbsapi.withings.net/v2/sleep",
  query = list(action = "getsummary", startdateymd = start, enddateymd = end),
  httr::add_headers(Authorization = paste("Bearer", tok))
)
```

## SleepScan — alternate token source (Withings only)

```r
ss    <- ss_client("your-sleepscan-api-key")
token <- ss_get_token(ss, email = "p@lab.com")   # or withings_user_id = 12345678L, or participant_id = "SS-P001"
```

`ss_get_token()` / `ss_fetch()` take exactly one of `email`, `withings_user_id`, or `participant_id`.

**Endpoints (path params):**
- `GET https://sleepscan.app/withings-access-token/by-email/{email}` — `X-API-Key` header
- `GET https://sleepscan.app/withings-access-token/by-withings-user-id/{id}` — `X-API-Key` header

## Reports

No R wrapper - call `/sleep-report` directly with `httr`:

```r
resp <- httr::POST(
  paste0(Sys.getenv("TOKENBRIDGE_URL"), "/sleep-report"),
  httr::add_headers(Authorization = paste("Bearer", Sys.getenv("TOKENBRIDGE_API_KEY"))),
  body = list(label = "P001", template = "sleep-bp",
              data = list(`withings-summary` = sleep_records, `withings-bp` = bp_records)),
  encode = "json"
)
writeBin(httr::content(resp, "raw"), "report.html")
```

## Errors

| Condition | Cause |
|---|---|
| `stop(".env is not set - run tb_setup() first.")` | Missing `TOKENBRIDGE_URL`/`TOKENBRIDGE_API_KEY` |
| `stop("No token found for user '...'")` | User not authorised — message contains auth URL |
| `stop("Token for '...' has expired ...")` | Refresh token expired — user must re-authorise |
| `stop("TokenBridge error (...): ...")` | Non-200/404/401 response from `/token` |
| HTTP error from `httr::GET`/`POST` | Non-2xx from a provider API call you made yourself |

---

## Data-fetching layer (maintained, but slowly)

`tb_fetch()` and the provider shorthand functions (`gh_fetch()`, `wt_fetch()`, `ou_fetch()`) wrap each provider's data endpoints - pagination, date formatting, and (for Google Health/Withings) flattening/decoding raw fields into named columns. We do try to keep these in step with each provider's data routes, but **it's a secondary priority behind the OAuth/token layer**, so there can be a lag between a provider API change and this catching up - check the provider's own API reference first if something looks off. Coverage is also narrower than Python: only `google-health`, `withings`, `oura` - no Polar/Strava/WHOOP/Dexcom/Garmin/Huawei in R (the Python package covers Polar/Strava/WHOOP; use it instead if you need those from R, or call the provider API directly with `tb_get_token()`'s result).

Full function signatures and return shapes: [R API Reference](r/reference.md). Per-provider setup/API base/official docs: [Provider Reference](providers/index.md).

```r
# Still works today:
sleep <- tb_fetch("p001", "sleep-summary", start, end, provider = "withings")
```
