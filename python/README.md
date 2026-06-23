# tokenbridge (Python)

Python client for [TokenBridge](https://github.com/jackmanners/tokenbridge) - fetches health data from Google Health (Fitbit-backed) and Withings via a self-hosted OAuth token manager.

## Install

```bash
pip install git+https://github.com/jackmanners/tokenbridge.git#subdirectory=python
```

## Setup

```bash
python -m tokenbridge
```

Prompts for your TokenBridge URL and API key and saves them to `.env`.

## Usage

```python
from tokenbridge import TokenBridge

tb = TokenBridge()   # reads TOKENBRIDGE_URL + TOKENBRIDGE_API_KEY from .env

# Send each participant their auth link - they click once to authorise
print(tb.auth_url("p001"))
urls = tb.auth_urls(["p001", "p002", "p003"])   # batch

# Fetch data
sleep = tb.fetch("p001", "sleep", "2026-05-01", "2026-06-18")
steps = tb.fetch("p001", "steps", "2026-05-01", "2026-06-18")

# One token for multiple fetches (avoids repeated round-trips)
token = tb.get_token("p001")
sleep = tb.fetch("p001", "sleep",                  start, end, token=token)
hrv   = tb.fetch("p001", "heart-rate-variability", start, end, token=token)

# Use a specific provider namespace
tb.google.fetch("p001", "sleep", start, end)

# Audit data coverage across your cohort
tb.google.data_completeness(
    ["p001", "p002", "p003"], start, end,
    data_types=["sleep", "steps", "heart-rate-variability"],
)
```

All data type IDs are kebab-case strings. See [`DATA_TYPES`](tokenbridge/providers/google_health.py) or the [provider reference](https://jackmanners.github.io/tokenbridge/providers/).

## Documentation

[jackmanners.github.io/tokenbridge](https://jackmanners.github.io/tokenbridge)
