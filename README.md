# TokenBridge

**OAuth token management for wearable health data research.**

Getting data out of health APIs (Google Health/Fitbit, Withings) into a research script means implementing OAuth 2.0, storing tokens securely, handling refresh before expiry, and doing it across dozens of participants. TokenBridge handles all of that so you don't have to.

---

## How it works

```
Participant (once)               Researcher script
     │                                  │
     │  clicks auth link                │  tb.fetch("p001", "sleep", ...)
     ▼                                  ▼
 TokenBridge  ────────────────────  /token endpoint
     │                             returns valid access token
     └── Supabase Postgres         script calls Google Health API directly
         token storage
         auto-refresh
```

TokenBridge is a small set of Supabase edge functions. It manages the OAuth flow, stores tokens in Postgres, and refreshes them automatically. Your scripts call one endpoint to get a valid token, then query the health API directly.

---

## Two ways to use it

### Someone has already deployed TokenBridge

If your PI or institution runs a TokenBridge instance, you just need the client package. Ask them for the deployment URL and API key, then:

```bash
pip install git+https://github.com/jackmanners/tokenbridge.git#subdirectory=python
python -m tokenbridge   # saves credentials to .env
```
```r
devtools::install_github("jackmanners/tokenbridge", subdir = "r")
library(tokenbridge)
tb_setup()   # saves credentials to .env
```

### Deploy your own instance

You need a free [Supabase](https://supabase.com) account and a [Google Cloud](https://console.cloud.google.com) project. Setup takes around 20–30 minutes.

→ [Deployment guide](https://jackmanners.github.io/tokenbridge/deployment/)  
→ [Basic setup walkthrough](https://jackmanners.github.io/tokenbridge/basic-quickstart/)

---

## Quick start

Once configured, the API is the same in both languages:

```python
from tokenbridge import TokenBridge

tb = TokenBridge()

# Generate an auth link for each participant and send it to them
# They click it once, sign in with Google, and approve access
print(tb.auth_url("participant-001"))

# Fetch data as soon as they've authorised
sleep = tb.fetch("participant-001", "sleep", "2026-05-01", "2026-06-18")
steps = tb.fetch("participant-001", "steps", "2026-05-01", "2026-06-18")
hrv   = tb.fetch("participant-001", "heart-rate-variability", "2026-05-01", "2026-06-18")

# Fetch multiple types efficiently with one token request
token = tb.get_token("participant-001")
sleep = tb.fetch("participant-001", "sleep", start, end, token=token)
steps = tb.fetch("participant-001", "steps", start, end, token=token)

# Audit data coverage across your cohort
tb.google.data_completeness(["p001", "p002", "p003"], start, end,
                             data_types=["sleep", "steps", "heart-rate-variability"])
```

```r
library(tokenbridge)

# Generate auth links for your cohort
links <- tb_auth_urls(c("p001", "p002", "p003"))

# Fetch data
sleep <- tb_fetch("p001", "sleep", "2026-05-01", "2026-06-18")
steps <- tb_fetch("p001", "steps", "2026-05-01", "2026-06-18")

# Efficient multi-type fetch with one token
tok <- tb_get_token("p001")
sleep <- tb_fetch("p001", "sleep", start, end, token = tok)
hrv   <- tb_fetch("p001", "heart-rate-variability", start, end, token = tok)

# Audit data coverage
gh_data_completeness(c("p001", "p002", "p003"), start, end,
                     data_types = c("sleep", "steps", "heart-rate-variability"))
```

---

## Supported providers

| Provider | Status | Notes |
|---|---|---|
| `google-health` | Supported | Requires Fitbit app linked to a Google account |
| `withings` | Supported | Requires Withings device (scale, BPM cuff, sleep mat, etc.) |

38 Google Health data types are supported — sleep, activity, heart rate, HRV, SpO2, ECG, temperature, weight, nutrition, and more. See the [provider reference](https://jackmanners.github.io/tokenbridge/providers/).

---

## Documentation

**[jackmanners.github.io/tokenbridge](https://jackmanners.github.io/tokenbridge)**

---

## License

[Polyform Noncommercial 1.0.0](LICENSE) — free for personal, research, and educational use. Commercial use requires permission.
