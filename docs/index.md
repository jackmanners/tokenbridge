# TokenBridge

A small tool for pulling data from health APIs (Google Health/Fitbit, Withings, Oura) without dealing with OAuth every time.

Getting data out of these APIs into a research script means implementing OAuth, storing tokens for all your participants, and keeping them refreshed across a study that can run for months. This handles all of that so your analysis code doesn't have to.

---

## How it works

```
Participant (once)               Your research script
     │                                  │
     │  clicks auth link                │  tb.fetch("p001", "sleep", ...)
     ▼                                  ▼
 TokenBridge  ────────────────────  /token endpoint
     │                             returns a valid access token
     └── Supabase Postgres         script calls the health API directly
         token storage + refresh
```

It's a small set of Supabase edge functions. It runs the OAuth flow, stores tokens in Postgres, and refreshes them automatically before they expire. Your scripts ask for a token, get one back, and call the provider API directly.

---

## Two ways to use it

### Using an existing deployment

If someone in your lab has already set this up, you just need the client package. Get the URL and API key from them and point the package at their instance.

/// tab | Python

    :::bash
    pip install git+https://github.com/jackmanners/tokenbridge.git#subdirectory=python
    python -m tokenbridge

///

/// tab | R

    :::r
    devtools::install_github("jackmanners/tokenbridge", subdir = "r")
    library(tokenbridge)
    tb_setup()

///

→ Continue with [Getting Started](getting-started.md)

### Deploying your own instance

You need a free [Supabase](https://supabase.com) account. Setup takes around 20–30 minutes.

→ [Basic setup walkthrough](basic-quickstart.md) - step-by-step from scratch  
→ [Deployment overview](deployment.md) - architecture, config options, adding providers

---

## Quick start

/// tab | Python

    :::python
    from tokenbridge import TokenBridge

    tb = TokenBridge()   # reads .env

    # Generate a link for each participant and send it to them
    print(tb.auth_url("participant-001"))

    # Fetch data as soon as they've authorised
    sleep = tb.fetch("participant-001", "sleep", "2026-05-01", "2026-06-18")
    steps = tb.fetch("participant-001", "steps", "2026-05-01", "2026-06-18")

    # One token request for multiple data types
    token = tb.get_token("participant-001")
    sleep = tb.fetch("participant-001", "sleep",                  start, end, token=token)
    hrv   = tb.fetch("participant-001", "heart-rate-variability", start, end, token=token)

///

/// tab | R

    :::r
    library(tokenbridge)

    # Generate links for your cohort
    links <- tb_auth_urls(c("p001", "p002", "p003"))

    # Fetch data
    sleep <- tb_fetch("p001", "sleep", "2026-05-01", "2026-06-18")
    steps <- tb_fetch("p001", "steps", "2026-05-01", "2026-06-18")

    # One token for multiple data types
    tok <- tb_get_token("p001")
    sleep <- tb_fetch("p001", "sleep",                  start, end, token = tok)
    hrv   <- tb_fetch("p001", "heart-rate-variability", start, end, token = tok)

///

---

## Supported providers

| Provider ID | Status | Notes |
|---|---|---|
| `google-health` | Supported | Requires Fitbit app linked to a Google account |
| `withings` | Supported | Requires Withings device (scale, BPM cuff, sleep mat, etc.) |
| `oura` | Supported | Requires Oura Ring (Gen 2 or Gen 3) |

Full list of data types, units, and endpoint notes: [Providers](providers/index.md)
