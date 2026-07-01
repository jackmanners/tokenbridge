# SleepScan integration

> **Internal** — requires a SleepScan API key. Not relevant for external deployments.

SleepScan is a separate system that manages Withings OAuth tokens for study participants. When a participant's token is held by SleepScan rather than TokenBridge, use the `sleepscan=` parameter to fetch their data via the same `tb.fetch()` / `tb_fetch()` interface.

Set `SLEEPSCAN_API_KEY` in your `.env` file, then pass `sleepscan=` with the participant's email, SleepScan participant ID, or Withings user ID:

## Python

```python
from tokenbridge import TokenBridge

tb = TokenBridge()   # reads SLEEPSCAN_API_KEY from .env automatically

# By email
sleep = tb.fetch("p001", "sleep-summary", "2024-01-01", "2024-06-30",
                 provider="withings", sleepscan="participant@example.com")

# By Withings user ID (integer)
bp = tb.withings.fetch("p001", "blood-pressure", "2024-01-01", "2024-06-30",
                        sleepscan=12345678)

# By SleepScan participant ID
sleep = tb.fetch("p001", "sleep-summary", "2024-01-01", "2024-06-30",
                 provider="withings", sleepscan="SS-P001")
```

`sleepscan=` can be:
- An email string (contains `@`) → looks up by email
- An integer → looks up by Withings user ID
- Any other string → looks up by SleepScan participant ID

The `user_id` first argument is still required (used as your local participant label) but is not sent to SleepScan — the `sleepscan=` value is the actual lookup key.

## R

```r
library(tokenbridge)

# By email (SLEEPSCAN_API_KEY read from .env)
tb_set_provider("withings")
sleep <- tb_fetch("p001", "sleep-summary", "2024-01-01", "2024-06-30",
                  sleepscan = "participant@example.com")

# Via the Withings shorthand
bp <- wt_fetch("p001", "blood-pressure", "2024-01-01", "2024-06-30",
               sleepscan = 12345678L)

# Explicit key (overrides env)
sleep <- wt_fetch("p001", "sleep-summary", "2024-01-01", "2024-06-30",
                  sleepscan = "SS-P001", sleepscan_key = "my-key")
```

## .env setup

```bash
TOKENBRIDGE_URL=https://your-ref.supabase.co/functions/v1
TOKENBRIDGE_API_KEY=your-tokenbridge-key
SLEEPSCAN_API_KEY=your-sleepscan-key
```

## Token source resolution

When `tb.fetch()` is called, token resolution priority is:

1. `token=` — explicit pre-fetched token (always wins)
2. `sleepscan=` — fetch from SleepScan API
3. Default — fetch from TokenBridge `/token` endpoint
