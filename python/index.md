# Python Package

The `tokenbridge` Python package provides a single `TokenBridge` client with built-in provider access. No separate provider import needed - everything is available through `tb`.

## Installation

```bash
pip install git+https://github.com/jackmanners/tokenbridge.git#subdirectory=python
```

Requires Python 3.10+. Dependencies: `requests`, `python-dotenv`.

## Architecture

```
TokenBridge (tb)           - auth, token management, and top-level fetch
  ├── tb.provider          - default provider string (e.g. "google-health")
  ├── tb.fetch(...)        - canonical data fetch, uses tb.provider
  ├── tb.google            - _ProviderProxy, pre-binds "google-health"
  │     ├── .fetch(...)
  │     └── .data_completeness(...)
  ├── tb.withings          - _ProviderProxy, pre-binds "withings"
  │     └── .fetch(...)
  ├── tb.oura              - _ProviderProxy, pre-binds "oura"
  │     └── .fetch(...)
  └── tb.auth_url(...)     - participant onboarding
```

## Quick start

```python
from tokenbridge import TokenBridge

tb = TokenBridge()           # reads .env
tb.provider = "google-health"   # optional - it's the default

# Onboard
print(tb.auth_url("p001"))

# Fetch
sleep = tb.fetch("p001", "sleep", "2026-05-01", "2026-06-18")
steps = tb.fetch("p001", "steps", "2026-05-01", "2026-06-18")

# Fetch multiple types efficiently (one token request)
token = tb.get_token("p001")
sleep = tb.fetch("p001", "sleep",  start, end, token=token)
hrv   = tb.fetch("p001", "heart-rate-variability", start, end, token=token)

# Provider namespaces
tb.google.fetch("p001", "sleep", start, end)
tb.withings.fetch("p001", "activity", start, end)
tb.oura.fetch("p001", "daily-readiness", start, end)

# One-off override
tb.fetch("p001", "sleep", start, end, provider="withings")
```

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
open("report_p001.html", "wb").write(resp.content)
```

→ [Reports & template authoring](../reports.md)

## See also

- [Getting Started](../getting-started.md)
- [API Reference](reference.md)
- [Providers](../providers/index.md)
