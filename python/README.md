# TokenBridge Python client

Lightweight Python client for fetching Google Health data via a
[TokenBridge](https://github.com/YOUR_USERNAME/tokenbridge) deployment.

## Install

```bash
pip install git+https://github.com/YOUR_USERNAME/tokenbridge.git#subdirectory=python
```

## Setup (once)

```bash
python -m tokenbridge
```

Prompts for your TokenBridge URL and API key and saves them to `.env`.

## Usage

```python
from tokenbridge import TokenBridge, GoogleHealth

tb = TokenBridge()    # reads .env automatically
gh = GoogleHealth(tb) # Google Health API (Fitbit-backed)

# Onboard a participant — send them this URL
print(tb.auth_url("participant-001"))

# Check multiple participants at once
urls = tb.auth_urls(["p001", "p002", "p003"])

# Check token status (expiry, scopes) without exposing the raw token
print(tb.token_status("participant-001"))

# Fetch data once they've authorised
sleep = gh.fetch_sleep("participant-001", "2026-05-01", "2026-06-18")
rr    = gh.fetch_respiratory_rate("participant-001", "2026-05-01", "2026-06-18")
hr    = gh.fetch_heart_rate("participant-001", "2026-05-01", "2026-06-18")

# Or any data type by ID (see Google Health API discovery doc)
steps = gh.fetch("participant-001", "steps", "2026-05-01", "2026-06-18")

# Summary statistics for one participant
s = gh.summary("participant-001", "2026-05-01", "2026-06-18")
# {"period_days": 48, "sleep": {"n": 42, "coverage_pct": 87.5, ...}, ...}

# Data completeness audit across a cohort
audit = gh.data_completeness(["p001", "p002", "p003"], "2026-05-01", "2026-06-18")

# Convert any result to a DataFrame
import pandas as pd
df = pd.DataFrame(sleep)
```

## API reference

### TokenBridge (auth layer)

| Method | Description |
|--------|-------------|
| `TokenBridge(url, api_key, env_file)` | Constructor — reads `.env` if args not provided |
| `tb.auth_url(user_id)` | Auth URL to send to one participant |
| `tb.auth_urls(user_ids)` | `{user_id: url}` dict for multiple participants |
| `tb.get_token(user_id)` | Raw access token (rarely needed directly) |
| `tb.token_status(user_id)` | Token metadata: expiry, refreshed, scopes |

### GoogleHealth (data layer)

| Method | Description |
|--------|-------------|
| `gh.fetch_sleep(user_id, start, end)` | Sleep sessions |
| `gh.fetch_respiratory_rate(user_id, start, end)` | Respiratory rate sleep summaries |
| `gh.fetch_heart_rate(user_id, start, end)` | Daily resting heart rate |
| `gh.fetch(user_id, data_type, start, end)` | Any data type by ID |
| `gh.summary(user_id, start, end)` | Coverage + stats for sleep and RR |
| `gh.summary_all(user_ids, start, end)` | Same, for multiple participants |
| `gh.data_completeness(user_ids, start, end)` | Flat audit table |

## Development

```bash
pip install -e ".[dev]"
pytest
```
