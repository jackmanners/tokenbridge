# TokenBridge

Centralised OAuth token management for health data research APIs.  
Point your scripts at TokenBridge instead of handling OAuth yourself — it manages the full auth flow, stores tokens in Supabase Postgres, and auto-refreshes before expiry.

```
participant (browser, once)
      │  visits auth-start URL
      ▼
  TokenBridge  ◄──── your scripts (POST /token → valid access token)
      │
      └── Supabase Postgres (token storage + auto-refresh)
```

Designed for researchers who want a self-hosted, minimal, open-source alternative to managed wearable data platforms.

## Deploy your own instance

See [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step setup.  
You need a free [Supabase](https://supabase.com) account and a [Google Cloud](https://console.cloud.google.com) project.

## Client packages

| Language | Install |
|----------|---------|
| Python | `pip install git+https://github.com/jackmanners/tokenbridge.git#subdirectory=python` |
| R | `devtools::install_github("jackmanners/tokenbridge", subdir = "r")` |

### Python

```python
from tokenbridge import TokenBridge

tb = TokenBridge()              # reads TOKENBRIDGE_URL + TOKENBRIDGE_API_KEY from .env
tb.provider = "google-health"   # set default provider once at the top of your script

# Onboard participants — send them this URL
tb.auth_url("participant-001")
tb.auth_urls(["p001", "p002", "p003"])   # batch

# Fetch data using the default provider
tb.fetch("p001", "sleep",                "2026-05-01", "2026-06-18")
tb.fetch("p001", "steps",                "2026-05-01", "2026-06-18")
tb.fetch("p001", "heart-rate-variability","2026-05-01", "2026-06-18")

# Provider namespace — always Google Health regardless of tb.provider
tb.google.fetch("p001", "sleep", "2026-05-01", "2026-06-18")

# Override provider for a single call
tb.fetch("p001", "sleep", start, end, provider="withings")

# Efficient: one token request for multiple fetches
token = tb.get_token("p001")
tb.fetch("p001", "sleep", start, end, token=token)
tb.fetch("p001", "steps", start, end, token=token)

# Analysis
tb.google.summary("p001", "2026-05-01", "2026-06-18")
tb.google.data_completeness(["p001", "p002", "p003"], "2026-05-01", "2026-06-18")
```

### R

```r
library(tokenbridge)

tb_set_provider("google-health")   # set default once (optional — it's the default)

# Onboard participants
tb_auth_url("p001")
tb_auth_urls(c("p001", "p002", "p003"))

# Fetch data using the default provider
tb_fetch("p001", "sleep",                 "2026-05-01", "2026-06-18")
tb_fetch("p001", "steps",                 "2026-05-01", "2026-06-18")
tb_fetch("p001", "heart-rate-variability","2026-05-01", "2026-06-18")

# Google Health shorthand (always uses google-health)
gh_fetch("p001", "sleep", "2026-05-01", "2026-06-18")

# Override provider for a single call
tb_fetch("p001", "sleep", start, end, provider = "withings")

# Efficient: one token for multiple fetches
tok <- tb_get_token("p001")
tb_fetch("p001", "sleep", start, end, token = tok)
tb_fetch("p001", "steps", start, end, token = tok)

# Analysis
gh_summary("p001", "2026-05-01", "2026-06-18")
gh_data_completeness(c("p001", "p002", "p003"), "2026-05-01", "2026-06-18")

# Browse available data types
names(GH_DATA_TYPES)
```

## Supported data types

All data types use their kebab-case API ID — the same string in both languages.  
See [docs/providers.md](docs/providers.md) for the full reference including units, endpoint types, and device requirements.

| Category | Example type IDs |
|---|---|
| Sleep | `sleep`, `respiratory-rate-sleep-summary`, `daily-sleep-temperature-derivations` |
| Activity | `steps`, `distance`, `exercise`, `active-zone-minutes`, `floors`, `daily-vo2-max` |
| Heart | `daily-resting-heart-rate`, `heart-rate-variability`, `daily-heart-rate-zones`, `electrocardiogram` |
| Vitals | `oxygen-saturation`, `daily-respiratory-rate`, `core-body-temperature`, `blood-glucose` |
| Body | `weight`, `body-fat`, `height` |
| Nutrition | `nutrition-log`, `hydration-log` |

## Supported providers

| Provider ID | Status |
|---|---|
| `google-health` | Supported — requires Fitbit app linked to a Google account |
| `withings` | Stub — auth wired, data fetch not yet implemented |

## License

MIT
