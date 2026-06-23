# tokenbridge (R)

R client for [TokenBridge](https://github.com/jackmanners/tokenbridge) - fetches health data from Google Health (Fitbit-backed) and Withings via a self-hosted OAuth token manager.

## Install

```r
# install.packages("devtools")
devtools::install_github("jackmanners/tokenbridge", subdir = "r")
```

## Setup

```r
library(tokenbridge)
tb_setup()   # prompts for URL + API key, saves to .env
```

## Usage

```r
library(tokenbridge)

# Send each participant their auth link - they click once to authorise
tb_auth_url("p001")
links <- tb_auth_urls(c("p001", "p002", "p003"))   # named character vector

# Fetch data
sleep <- tb_fetch("p001", "sleep", "2026-05-01", "2026-06-18")
steps <- tb_fetch("p001", "steps", "2026-05-01", "2026-06-18")

# Google Health shorthand (always uses google-health provider)
sleep <- gh_fetch("p001", "sleep", "2026-05-01", "2026-06-18")

# One token for multiple fetches (avoids repeated round-trips)
tok <- tb_get_token("p001")
sleep <- tb_fetch("p001", "sleep",                  start, end, token = tok)
hrv   <- tb_fetch("p001", "heart-rate-variability", start, end, token = tok)

# Audit data coverage across your cohort
gh_data_completeness(
  c("p001", "p002", "p003"), start, end,
  data_types = c("sleep", "steps", "heart-rate-variability")
)

# Browse all available data type IDs
names(GH_DATA_TYPES)
```

## Documentation

[jackmanners.github.io/tokenbridge](https://jackmanners.github.io/tokenbridge)
