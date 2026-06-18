# TokenBridge R client

Lightweight R client for fetching Google Health data via a
[TokenBridge](https://github.com/jackmanners/tokenbridge) deployment.

## Install

```r
# install.packages("devtools")
devtools::install_github("jackmanners/tokenbridge", subdir = "r")
```

## Setup (once)

```r
library(tokenbridge)
tb_setup()
```

Prompts for your TokenBridge URL and API key and saves them to `.env`.

## Usage

```r
library(tokenbridge)

# Onboard participants — send each person their link
tb_auth_url("participant-001")
tb_auth_urls(c("p001", "p002", "p003"))  # named vector of URLs

# Check token status (expiry, scopes) without exposing the raw token
tb_token_status("participant-001")

# Fetch data once they've authorised
sleep <- gh_fetch_sleep("participant-001", "2026-05-01", "2026-06-18")
rr    <- gh_fetch_rr("participant-001",    "2026-05-01", "2026-06-18")
hr    <- gh_fetch_heart_rate("participant-001", "2026-05-01", "2026-06-18")

# Or any data type by ID (see Google Health API discovery doc)
steps <- gh_fetch("participant-001", "steps", "2026-05-01", "2026-06-18")

# Summary statistics for one participant
s <- gh_summary("participant-001", "2026-05-01", "2026-06-18")
# $sleep: n, days_with_data, coverage_pct, mean_duration_hours
# $respiratory_rate: n, days_with_data, coverage_pct, mean, std

# Data completeness audit across a cohort
audit <- gh_data_completeness(c("p001", "p002", "p003"), "2026-05-01", "2026-06-18")
# Returns a data.frame — one row per participant × data type
```

## API reference

### tb_ — TokenBridge platform

| Function | Description |
|----------|-------------|
| `tb_setup()` | Interactive setup — saves URL and API key to `.env` |
| `tb_auth_url(user_id)` | Auth URL to send to one participant |
| `tb_auth_urls(user_ids)` | Named character vector of auth URLs |
| `tb_get_token(user_id)` | Raw access token (rarely needed directly) |
| `tb_token_status(user_id)` | Token metadata: expiry, refreshed, scopes |

### gh_ — Google Health provider

| Function | Description |
|----------|-------------|
| `gh_fetch_sleep(user_id, start, end)` | Sleep sessions as `data.frame` |
| `gh_fetch_rr(user_id, start, end)` | Respiratory rate summaries as `data.frame` |
| `gh_fetch_heart_rate(user_id, start, end)` | Daily resting heart rate as `data.frame` |
| `gh_fetch(user_id, data_type, start, end)` | Any data type by ID |
| `gh_summary(user_id, start, end)` | Coverage + stats for sleep and RR |
| `gh_summary_all(user_ids, start, end)` | Same, for multiple participants |
| `gh_data_completeness(user_ids, start, end)` | Flat audit `data.frame` |

### wt_ — Withings provider

Not yet implemented. Functions exist and will raise an informative error.

## Development

```r
devtools::load_all(".")
devtools::test()
```
