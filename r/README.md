# tokenbridge (R)

R client for [TokenBridge](https://github.com/jackmanners/tokenbridge) - a self-hosted OAuth token manager for health data research.

**Token retrieval and auth-link generation only.** This package doesn't wrap provider data APIs - get a token, then call the provider's own API directly. See the [Client Libraries docs](https://jackmanners.github.io/tokenbridge/clients/) for why, and the [Python package](https://github.com/jackmanners/tokenbridge/tree/main/python) if you want a built-in data-fetching layer instead.

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
tb_auth_url("p001", provider = "withings")
links <- tb_auth_urls(c("p001", "p002", "p003"), provider = "withings")   # named character vector

# Get a token, then call the provider's API yourself
tok <- tb_get_token("p001", provider = "withings")
resp <- httr::GET(
  "https://wbsapi.withings.net/v2/sleep",
  query = list(action = "getsummary", startdateymd = "2026-05-01", enddateymd = "2026-06-18"),
  httr::add_headers(Authorization = paste("Bearer", tok))
)
```

## Documentation

[jackmanners.github.io/tokenbridge](https://jackmanners.github.io/tokenbridge)
