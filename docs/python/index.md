# Python Package

The `tokenbridge` Python package provides a single `TokenBridge` client with built-in provider access. No separate provider import needed — everything is available through `tb`.

## Installation

```bash
<<<<<<< HEAD
pip install git+https://github.com/jackmanners/tokenbridge.git#subdirectory=python
=======
pip install git+https://github.com/YOUR_USERNAME/tokenbridge.git#subdirectory=python
>>>>>>> e656476530cbfcd464560310f0bbb5cd10018519
```

Requires Python 3.10+. Dependencies: `requests`, `python-dotenv`.

## Architecture

```
TokenBridge (tb)           — auth, token management, and top-level fetch
  ├── tb.provider          — default provider string (e.g. "google-health")
  ├── tb.fetch(...)        — canonical data fetch, uses tb.provider
  ├── tb.google            — _ProviderProxy, pre-binds "google-health"
  │     ├── .fetch(...)
  │     ├── .summary(...)
  │     └── .data_completeness(...)
  ├── tb.withings          — _ProviderProxy, pre-binds "withings"
  └── tb.auth_url(...)     — participant onboarding

GoogleHealth               — can also be used directly (advanced)
  └── .fetch(user, dtype, start, end, token=None)
```

## Quick start

```python
from tokenbridge import TokenBridge

tb = TokenBridge()           # reads .env
tb.provider = "google-health"   # optional — it's the default

# Onboard
print(tb.auth_url("p001"))

# Fetch
sleep = tb.fetch("p001", "sleep", "2026-05-01", "2026-06-18")
steps = tb.fetch("p001", "steps", "2026-05-01", "2026-06-18")

# Fetch multiple types efficiently (one token request)
token = tb.get_token("p001")
sleep = tb.fetch("p001", "sleep",  start, end, token=token)
hrv   = tb.fetch("p001", "heart-rate-variability", start, end, token=token)

# Provider namespace
tb.google.fetch("p001", "sleep", start, end)
tb.google.summary("p001", start, end)

# One-off override
tb.fetch("p001", "sleep", start, end, provider="withings")
```

## See also

- [Getting Started](../getting-started.md)
- [API Reference](reference.md)
- [Providers](../providers.md)
