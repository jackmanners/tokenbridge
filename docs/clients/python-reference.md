# Python Data-Fetching Reference

Exhaustive, auto-generated-from-docstrings reference for the Python package's
**data-fetching layer only** - `tb.fetch()`, the provider classes, and their
methods. For `TokenBridge()`, `auth_url()`, `auth_urls()`, and `get_token()`,
see the [Token API Reference](token-reference.md) - this page doesn't repeat
them.

## TokenBridge.fetch

The canonical data-fetch dispatcher - routes to the right provider based on
`provider=` (or `tb.provider` if not passed).

::: tokenbridge.TokenBridge
    options:
      show_source: false
      members:
        - fetch

---

## Provider namespaces

`tb.google`, `tb.withings`, `tb.oura`, `tb.polar`, `tb.strava`, and `tb.whoop` are lightweight
proxy objects. Each pre-binds a provider and forwards every call to the underlying provider
instance, so all `GoogleHealth` methods are available as `tb.google.<method>`, and so on.

```python
tb.google.fetch("p001", "sleep", start, end)           # same as tb.fetch(..., provider="google-health")
tb.google.data_completeness(["p001", "p002"], s, e)    # GoogleHealth.data_completeness
```

They are read-only properties on `TokenBridge` - you cannot assign to `tb.google`.

---

## GoogleHealth

The underlying Google Health provider. You can use this directly if you prefer not to
go through `tb.fetch()`, for example when building scripts that only use one provider:

```python
from tokenbridge import TokenBridge, GoogleHealth

tb = TokenBridge()
gh = GoogleHealth(tb)

sleep = gh.fetch("p001", "sleep", start, end)
audit = gh.data_completeness(["p001", "p002"], start, end)
```

::: tokenbridge.GoogleHealth
    options:
      show_source: false
      members:
        - fetch
        - data_completeness

---

## DATA_TYPES

A dict mapping every supported Google Health type ID to its endpoint type
(`"list"` or `"dailyRollup"`). Use it to enumerate all available types:

```python
from tokenbridge.providers.google_health import DATA_TYPES

for dtype in DATA_TYPES:
    data = tb.fetch("p001", dtype, start, end, token=token)
    print(dtype, len(data))
```

::: tokenbridge.DATA_TYPES

---

## Withings

The Withings provider. Fetches health data from Withings devices (scales, blood pressure
monitors, sleep mats, activity trackers).

::: tokenbridge.Withings
    options:
      show_source: false

---

## Oura

```python
tb.oura.fetch("p001", "daily-readiness", start, end)
```

::: tokenbridge.Oura
    options:
      show_source: false
      members:
        - fetch

---

## Polar

Access tokens never expire (no refresh flow). Date ranges over 28 days are chunked into
sequential requests automatically.

```python
tb.polar.fetch("p001", "sleep", start, end)
```

::: tokenbridge.Polar
    options:
      show_source: false
      members:
        - fetch

---

## Strava

`fetch()` returns activity summaries; per-activity time-series (HR, power, GPS) is a
separate call keyed by `activity_id`, not a date range:

```python
activities = tb.strava.fetch("p001", "activities", start, end)
streams    = tb.strava.streams("p001", activities[0]["id"], keys=["heartrate", "watts"])
```

::: tokenbridge.Strava
    options:
      show_source: false
      members:
        - fetch
        - streams

---

## Whoop

```python
tb.whoop.fetch("p001", "recovery", start, end)
```

`recovery` records are keyed by `cycle_id`, not their own id - join manually if you need
recovery, sleep, and cycle in one row.

::: tokenbridge.Whoop
    options:
      show_source: false
      members:
        - fetch

---

## Unfinished providers

`tb.garmin`, `tb.huawei`, `tb.health_connect`, `tb.dexcom` are registered but every method
raises `NotImplementedError` - these were never finished and aren't planned to be. Use
`tb.get_token()` for them and call the provider API yourself.
