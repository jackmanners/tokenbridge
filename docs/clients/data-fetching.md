# Data-Fetching Guide

**Python-only.** Python wraps each provider's data endpoints - pagination, date formatting, and (for Google Health/Withings) flattening or decoding raw fields. This layer is real and maintained, but **it's a secondary priority behind the OAuth/token layer** covered in the [Token API Reference](token-reference.md), so it can lag behind a provider's recent API changes. If something looks off or missing, check the provider's own API reference first - see [Providers](../platform/providers/index.md).

R and JavaScript don't have this layer - see the note at the bottom.

---

## Fetching data

```python
sleep = tb.fetch("p001", "sleep", "2026-05-01", "2026-06-18")
steps = tb.fetch("p001", "steps", "2026-05-01", "2026-06-18")

# Reuse one token across several fetches
token = tb.get_token("p001")
sleep = tb.fetch("p001", "sleep", start, end, token=token)
hrv   = tb.fetch("p001", "heart-rate-variability", start, end, token=token)

# Zero-transformation raw API response
raw = tb.fetch("p001", "sleep-summary", start, end, provider="withings", raw=True)
```

Results are flat records (`list[dict]`), one per sleep session / activity / measurement. Nested API fields are flattened with dot notation, e.g. `startTime.seconds`. `provider=` overrides `tb.provider` for a single call - see [Setting a default provider](token-reference.md#setting-a-default-provider) in the Token API Reference.

## Provider namespaces and shorthand

```python
tb.google.fetch("p001", "sleep", start, end)          # always google-health
tb.withings.fetch("p001", "activity", start, end)     # always withings
tb.oura.fetch("p001", "daily-readiness", start, end)  # always oura
tb.polar.fetch("p001", "sleep", start, end)
tb.strava.fetch("p001", "activities", start, end)
tb.strava.streams("p001", activity_id, keys=["heartrate"])  # Strava-specific
tb.whoop.fetch("p001", "recovery", start, end)
```

Covers `google-health`, `withings`, `oura`, `polar`, `strava`, `whoop`. `tb.garmin`, `tb.huawei`, `tb.health_connect`, `tb.dexcom` are registered but raise `NotImplementedError` - unfinished stubs, not planned.

## Auditing a cohort

```python
audit = tb.google.data_completeness(
    ["p001", "p002", "p003"], start, end,
    data_types=["sleep", "steps", "heart-rate-variability"],
)
# list of dicts: user_id, data_type, n, days_with_data, coverage_pct
```

See [Examples](examples.md) for a complete cohort-compliance vignette.

## SleepScan

An alternate Withings token source for participants registered through a separate system called SleepScan rather than TokenBridge's own OAuth flow.

```python
tb.get_token("p@lab.com", provider="withings", sleepscan=True)
tb.fetch("p@lab.com", "sleep-summary", start, end, provider="withings", sleepscan=True)

# Standalone, without a TokenBridge user_id:
from tokenbridge.sleepscan import SleepScan
ss    = SleepScan(api_key="...")
token = ss.get_token(email="p@lab.com")   # or withings_user_id=123
```

`user_id` is the SleepScan lookup key: an email (contains `@`) looks up by email, an integer by Withings user ID, any other string by SleepScan participant ID. Python additionally falls back to a Clinic API (`CLINIC_SLEEPSCAN_KEY`) if SleepScan itself returns nothing.

R has `ss_client()`/`ss_get_token()` too (token-layer only, no fetch) - see [Token API Reference](token-reference.md).

## Generating a report

Rendered locally, in-process - no server call, since the data's already in memory:

```python
from tokenbridge.reports import generate_report

html = generate_report("P001", {"withings-summary": sleep_records, "withings-bp": bp_records}, template="sleep-bp")
open("report.html", "w", encoding="utf-8").write(html)
```

Templates: `full` (sleep), `sleep-bp` (sleep + BP), `bp` (BP only). See [Reports](reports.md) for available templates and writing your own.

---

## R and JavaScript

Neither has a data-fetching layer - by design, both stop at `get_token()`/`getToken()`. Call the provider's API directly with the token; see [Providers](../platform/providers/index.md) for each one's API base and official docs, or the [Direct HTTP API](../platform/http-api.md) if you're not using a client library at all.
