# Python API Reference

## TokenBridge

The main client class. Import and instantiate once; use `tb.fetch()` for data and
`tb.auth_url()` for participant onboarding.

::: tokenbridge.TokenBridge
    options:
      show_source: false
      members:
        - __init__
        - fetch
        - auth_url
        - auth_urls
        - get_token
        - token_status

---

## Provider namespaces

`tb.google` and `tb.withings` are lightweight proxy objects. They pre-bind a provider
and forward every call to the underlying provider instance. This means all `GoogleHealth`
methods are available as `tb.google.<method>`.

```python
tb.google.fetch("p001", "sleep", start, end)           # same as tb.fetch(..., provider="google-health")
tb.google.summary("p001", start, end)                  # GoogleHealth.summary
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
s     = gh.summary("p001", start, end)
```

::: tokenbridge.GoogleHealth
    options:
      show_source: false
      members:
        - fetch
        - summary
        - summary_all
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

The Withings provider stub. The OAuth flow is wired but `fetch()` raises
`NotImplementedError` - implementation is in progress.

::: tokenbridge.Withings
    options:
      show_source: false
