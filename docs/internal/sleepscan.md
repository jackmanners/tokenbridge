# SleepScan integration

> **Internal** — requires a SleepScan API key. Not relevant for external deployments.

SleepScan is a separate system that manages Withings OAuth tokens for study participants. When a participant's token is held by SleepScan rather than TokenBridge, pass their identifier as `user_id` and set `sleepscan=True` — the same `tb.fetch()` / `tb_fetch()` interface is used throughout.

Set `SLEEPSCAN_API_KEY` in your `.env` file. The `user_id` argument becomes the SleepScan lookup key:
- An email string (contains `@`) → looks up by email
- An integer → looks up by Withings user ID
- Any other string → looks up by SleepScan participant ID

`sleepscan=True` always takes priority, even if a `token=` is also passed.

## Python

```python
from tokenbridge import TokenBridge

tb = TokenBridge()   # reads SLEEPSCAN_API_KEY from .env automatically

# By email
sleep = tb.fetch("participant@example.com", "sleep-summary", "2024-01-01", "2024-06-30",
                 provider="withings", sleepscan=True)

# By Withings user ID (integer)
bp = tb.withings.fetch(12345678, "blood-pressure", "2024-01-01", "2024-06-30",
                        sleepscan=True)

# By SleepScan participant ID
sleep = tb.fetch("SS-P001", "sleep-summary", "2024-01-01", "2024-06-30",
                 provider="withings", sleepscan=True)
```

## R

```r
library(tokenbridge)

# By email (SLEEPSCAN_API_KEY read from .env)
tb_set_provider("withings")
sleep <- tb_fetch("participant@example.com", "sleep-summary", "2024-01-01", "2024-06-30",
                  sleepscan = TRUE)

# Via the Withings shorthand, by Withings user ID
bp <- wt_fetch(12345678L, "blood-pressure", "2024-01-01", "2024-06-30",
               sleepscan = TRUE)

# Explicit key (overrides env)
sleep <- wt_fetch("SS-P001", "sleep-summary", "2024-01-01", "2024-06-30",
                  sleepscan = TRUE, sleepscan_key = "my-key")
```

## .env setup

```bash
TOKENBRIDGE_URL=https://your-ref.supabase.co/functions/v1
TOKENBRIDGE_API_KEY=your-tokenbridge-key
SLEEPSCAN_API_KEY=your-sleepscan-key
```

## Standalone usage (without a TokenBridge user_id)

If a participant exists in SleepScan but not TokenBridge, you can fetch without a TB user_id.

**Python:**

```python
from tokenbridge.sleepscan import SleepScan

ss    = SleepScan(api_key="...", clinic_key="...")
token = ss.get_token(email="p@lab.com")    # or withings_user_id=123

# Use the token directly with the Withings provider
from tokenbridge.providers.withings import Withings
wt   = Withings(None)
data = wt.fetch("ignored", "sleep-summary", start, end, token=token)
```

**R:**

```r
ss    <- ss_client(api_key = Sys.getenv("SLEEPSCAN_API_KEY"))
token <- ss_get_token(ss, email = "p@lab.com")
df    <- wt_fetch("ignored", "sleep-summary", start, end, token = token)

# Or fetch in one call — no TB user_id needed
df <- ss_fetch(ss, "sleep-summary", start, end, email = "p@lab.com")
```

## Clinic fallback (Python only)

When SleepScan returns no token, Python automatically retries via the Clinic API (`CLINIC_SLEEPSCAN_KEY`). Set the key in `.env`:

```bash
CLINIC_SLEEPSCAN_KEY=your-clinic-key
```

The fallback is transparent — `sleepscan=True` tries SleepScan first, then Clinic, then raises `RuntimeError: Could not retrieve Withings token from any source`.

R does not currently implement the Clinic fallback.

## Token source resolution

When `tb.fetch()` / `wt_fetch()` is called, token resolution priority is:

1. `sleepscan=True` — fetch from SleepScan API (always wins when set)
2. `token=` — explicit pre-fetched token
3. Default — fetch from TokenBridge `/token` endpoint
