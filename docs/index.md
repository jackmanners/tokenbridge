# TokenBridge

**OAuth token management for wearable health data research.**

Getting data out of health APIs — Google Health/Fitbit, Withings — into a research script means implementing OAuth 2.0, securely storing tokens for dozens of participants, and keeping them refreshed across a study that runs for months. TokenBridge handles all of that so you don't have to write any auth code.

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

TokenBridge is a small set of Supabase edge functions. It runs the OAuth flow, stores tokens in Postgres, and refreshes them automatically before they expire. Your scripts ask for a token, get one back, and query the provider API directly. No auth logic in your analysis code.

---

## Two ways to use it

### Using an existing deployment

If your institution or PI has deployed TokenBridge, you only need the client package. Ask them for the URL and API key, then point the package at their instance.

=== "Python"

    ```bash
    pip install git+https://github.com/jackmanners/tokenbridge.git#subdirectory=python
    python -m tokenbridge   # interactive setup — saves credentials to .env
    ```

=== "R"

    ```r
    devtools::install_github("jackmanners/tokenbridge", subdir = "r")
    library(tokenbridge)
    tb_setup()   # interactive setup — saves credentials to .env
    ```

→ Continue with [Getting Started](getting-started.md)

### Deploying your own instance

You need a free [Supabase](https://supabase.com) account and a [Google Cloud](https://console.cloud.google.com) project. Setup takes around 20–30 minutes.

→ [Basic setup walkthrough](basic-quickstart.md) — step-by-step from scratch  
→ [Deployment overview](deployment.md) — architecture, config options, adding providers

---

## Quick start

=== "Python"

    ```python
    from tokenbridge import TokenBridge

    tb = TokenBridge()   # reads .env

    # Generate a link for each participant and send it to them
    # They click once, sign in with Google, and approve access — done
    print(tb.auth_url("participant-001"))

    # Fetch data as soon as they've authorised
    sleep = tb.fetch("participant-001", "sleep", "2026-05-01", "2026-06-18")
    steps = tb.fetch("participant-001", "steps", "2026-05-01", "2026-06-18")

    # One token request for multiple data types
    token = tb.get_token("participant-001")
    sleep = tb.fetch("participant-001", "sleep",                   start, end, token=token)
    hrv   = tb.fetch("participant-001", "heart-rate-variability",  start, end, token=token)

    # Audit data coverage across your cohort
    tb.google.data_completeness(
        ["p001", "p002", "p003"], start, end,
        data_types=["sleep", "steps", "heart-rate-variability"],
    )
    ```

=== "R"

    ```r
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

    # Audit data coverage
    gh_data_completeness(
      c("p001", "p002", "p003"), start, end,
      data_types = c("sleep", "steps", "heart-rate-variability")
    )
    ```

---

## Supported providers

| Provider ID | Status | Notes |
|---|---|---|
| `google-health` | Supported | Requires Fitbit app linked to a Google account |
| `withings` | Supported | Requires Withings device (scale, BPM cuff, sleep mat, etc.) |
| `oura` | Supported | Requires Oura Ring (Gen 2 or Gen 3) |
| `oura` | Supported | Requires Oura Ring (Gen 2 or Gen 3) |

Full list of data types, units, and endpoint notes: [Providers](providers.md)
