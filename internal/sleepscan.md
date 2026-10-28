# SleepScan integration

> **Internal** — requires a SleepScan API key. Not relevant for external deployments.

SleepScan is a separate system that manages Withings OAuth tokens for study participants. When a participant's token is held by SleepScan rather than TokenBridge, pass their identifier as `user_id` and set `sleepscan=True` (Python) or use `ss_get_token()` (R).

Set `SLEEPSCAN_API_KEY` in your `.env` file. The lookup key becomes:
- An email string (contains `@`) → looks up by email
- An integer → looks up by Withings user ID
- Any other string → looks up by SleepScan participant ID

Python: `sleepscan=True` always takes priority over `tb.fetch()`, even if a `token=` is also passed.

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

R is token-only - no `tb_fetch()`/`wt_fetch()` equivalent. Get the token, then call the Withings API directly:

```r
library(tokenbridge)

ss  <- ss_client(Sys.getenv("SLEEPSCAN_API_KEY"))
tok <- ss_get_token(ss, email = "participant@example.com")
# or: ss_get_token(ss, withings_user_id = 12345678L)
# or: ss_get_token(ss, participant_id = "SS-P001")

resp <- httr::GET(
  "https://wbsapi.withings.net/v2/sleep",
  query = list(action = "getsummary", startdateymd = "2024-01-01", enddateymd = "2024-06-30"),
  httr::add_headers(Authorization = paste("Bearer", tok))
)
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

**R:** same as above - `ss_get_token()` never needed a TokenBridge `user_id` to begin with.

## Clinic fallback (Python only)

When SleepScan returns no token, Python automatically retries via the Clinic API (`CLINIC_SLEEPSCAN_KEY`). Set the key in `.env`:

```bash
CLINIC_SLEEPSCAN_KEY=your-clinic-key
```

The fallback is transparent — `sleepscan=True` tries SleepScan first, then Clinic, then raises `RuntimeError: Could not retrieve Withings token from any source`.

R does not implement the Clinic fallback - `ss_get_token()` only tries SleepScan.

## Token source resolution (Python `tb.fetch()`)

1. `sleepscan=True` — fetch from SleepScan API (always wins when set)
2. `token=` — explicit pre-fetched token
3. Default — fetch from TokenBridge `/token` endpoint
