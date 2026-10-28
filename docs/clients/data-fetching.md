# Data-Fetching Guide

Python and R additionally wrap each provider's data endpoints - pagination, date formatting, and (for Google Health/Withings) flattening or decoding raw fields. This layer is real and maintained, but **it's a secondary priority behind the OAuth/token layer** covered in the [Token API Reference](token-reference.md), so it can lag behind a provider's recent API changes. If something looks off or missing, check the provider's own API reference first - see [Providers](../platform/providers/index.md).

JavaScript doesn't have this layer at all, by design - see the note at the bottom.

---

## Fetching data

/// tab | Python

    :::python
    sleep = tb.fetch("p001", "sleep", "2026-05-01", "2026-06-18")
    steps = tb.fetch("p001", "steps", "2026-05-01", "2026-06-18")

    # Reuse one token across several fetches
    token = tb.get_token("p001")
    sleep = tb.fetch("p001", "sleep", start, end, token=token)
    hrv   = tb.fetch("p001", "heart-rate-variability", start, end, token=token)

    # Zero-transformation raw API response
    raw = tb.fetch("p001", "sleep-summary", start, end, provider="withings", raw=True)

///

/// tab | R

    :::r
    sleep <- tb_fetch("p001", "sleep", "2026-05-01", "2026-06-18")
    steps <- tb_fetch("p001", "steps", "2026-05-01", "2026-06-18")

    # Reuse one token across several fetches
    tok   <- tb_get_token("p001")
    sleep <- tb_fetch("p001", "sleep", start, end, token = tok)
    hrv   <- tb_fetch("p001", "heart-rate-variability", start, end, token = tok)

///

Results are flat records (Python: `list[dict]`, R: `data.frame`), one per sleep session / activity / measurement. Nested API fields are flattened with dot notation, e.g. `startTime.seconds`.

## Setting a default provider

`fetch()`/`tb_fetch()` take an explicit `provider=` on every call, or use a session default so you don't have to repeat it:

/// tab | Python

    :::python
    tb.provider = "withings"    # persists on this TokenBridge instance

    tb.fetch("p001", "sleep-summary", start, end)    # uses tb.provider

///

/// tab | R

    :::r
    tb_set_provider("withings")    # persists for the R session
    tb_get_provider()              # "withings"

    tb_fetch("p001", "sleep-summary", start, end)    # uses the session default

///

## Provider namespaces and shorthand

/// tab | Python

    :::python
    tb.google.fetch("p001", "sleep", start, end)          # always google-health
    tb.withings.fetch("p001", "activity", start, end)     # always withings
    tb.oura.fetch("p001", "daily-readiness", start, end)  # always oura
    tb.polar.fetch("p001", "sleep", start, end)
    tb.strava.fetch("p001", "activities", start, end)
    tb.strava.streams("p001", activity_id, keys=["heartrate"])  # Strava-specific
    tb.whoop.fetch("p001", "recovery", start, end)

///

/// tab | R

    :::r
    gh_fetch("p001", "heart-rate-variability", start, end)   # google-health
    wt_fetch("p001", "activity", start, end)                 # withings
    ou_fetch("p001", "daily-readiness", start, end)          # oura

///

Python covers `google-health`, `withings`, `oura`, `polar`, `strava`, `whoop`. R covers `google-health`, `withings`, `oura` only. `tb.garmin`, `tb.huawei`, `tb.health_connect`, `tb.dexcom` are registered in Python but raise `NotImplementedError` - unfinished stubs, not planned.

## Auditing a cohort

/// tab | Python

    :::python
    audit = tb.google.data_completeness(
        ["p001", "p002", "p003"], start, end,
        data_types=["sleep", "steps", "heart-rate-variability"],
    )
    # list of dicts: user_id, data_type, n, days_with_data, coverage_pct

///

/// tab | R

    :::r
    audit <- gh_data_completeness(
      c("p001", "p002", "p003"), start, end,
      data_types = c("sleep", "steps", "heart-rate-variability")
    )
    # data.frame: user_id, data_type, n, days_with_data, coverage_pct

///

See [Examples](examples.md) for a complete cohort-compliance vignette.

## SleepScan

An alternate Withings token source for participants registered through a separate system called SleepScan rather than TokenBridge's own OAuth flow.

/// tab | Python

    :::python
    tb.get_token("p@lab.com", provider="withings", sleepscan=True)
    tb.fetch("p@lab.com", "sleep-summary", start, end, provider="withings", sleepscan=True)

    # Standalone, without a TokenBridge user_id:
    from tokenbridge.sleepscan import SleepScan
    ss    = SleepScan(api_key="...")
    token = ss.get_token(email="p@lab.com")   # or withings_user_id=123

///

/// tab | R

    :::r
    wt_fetch("p@lab.com", "sleep-summary", start, end, sleepscan = TRUE)

    # Standalone, without a TokenBridge user_id:
    ss    <- ss_client("your-sleepscan-api-key")
    token <- ss_get_token(ss, email = "p@lab.com")
    df    <- ss_fetch(ss, "sleep-summary", start, end, email = "p@lab.com")

///

`user_id` is the SleepScan lookup key: an email (contains `@`) looks up by email, an integer by Withings user ID, any other string by SleepScan participant ID. Python additionally falls back to a Clinic API (`CLINIC_SLEEPSCAN_KEY`) if SleepScan itself returns nothing - R does not.

## Generating a report

```bash
# .env
TOKENBRIDGE_URL=https://xxx.supabase.co/functions/v1
TOKENBRIDGE_API_KEY=your-key
```

/// tab | Python

    :::python
    import requests
    resp = requests.post(
        f"{tb.url}/sleep-report",
        headers={"Authorization": f"Bearer {tb.api_key}"},
        json={"label": "P001", "template": "sleep-bp",
              "data": {"withings-summary": sleep_records, "withings-bp": bp_records}},
    )
    open("report.html", "wb").write(resp.content)

///

/// tab | R

    :::r
    resp <- httr::POST(
      paste0(Sys.getenv("TOKENBRIDGE_URL"), "/sleep-report"),
      httr::add_headers(Authorization = paste("Bearer", Sys.getenv("TOKENBRIDGE_API_KEY"))),
      body = list(label = "P001", template = "sleep-bp",
                  data = list(`withings-summary` = sleep_records, `withings-bp` = bp_records)),
      encode = "json"
    )
    writeBin(httr::content(resp, "raw"), "report.html")

///

Templates: `full` (sleep), `sleep-bp` (sleep + BP), `bp` (BP only). See [Reports](../platform/reports.md) for available templates and writing your own.

---

## JavaScript

Not available - by design, the JavaScript package stops at `getToken()`. Call the provider's API directly with the token; see [Providers](../platform/providers/index.md) for each one's API base and official docs, or the [Direct HTTP API](../platform/http-api.md) if you're not using a client library at all.

## Full reference

Exhaustive, auto-generated-where-possible function reference for everything on this page: [Python Data-Fetching Reference](python-reference.md) · [R Data-Fetching Reference](r-reference.md).
