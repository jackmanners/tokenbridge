# R Package

The `tokenbridge` R package uses a consistent prefix convention in place of object namespacing (which is idiomatic in R).

## Installation

```r
devtools::install_github("jackmanners/tokenbridge", subdir = "r")
```

Requires R 4.0+. Dependencies: `httr`.

## Architecture

```
tb_*    TokenBridge platform - auth, token management, canonical data fetch
gh_*    Google Health shorthand - always uses "google-health" provider
wt_*    Withings shorthand - always uses "withings" provider
ou_*    Oura shorthand - always uses "oura" provider

tb_set_provider("google-health")       set session default
tb_fetch("p001", "sleep", s, e)        canonical fetch, uses default provider
gh_fetch("p001", "sleep", s, e)        Google Health shorthand
wt_fetch("p001", "activity", s, e)     Withings shorthand
ou_fetch("p001", "daily-sleep", s, e)  Oura shorthand
```

## Quick start

```r
library(tokenbridge)

tb_setup()                           # once - saves .env credentials
tb_set_provider("google-health")     # optional, it's the default

# Onboard
tb_auth_url("p001")

# Fetch
tb_fetch("p001", "sleep", "2026-05-01", "2026-06-18")
tb_fetch("p001", "steps", "2026-05-01", "2026-06-18")

# Provider shorthands
gh_fetch("p001", "heart-rate-variability", "2026-05-01", "2026-06-18")
wt_fetch("p001", "activity", "2026-05-01", "2026-06-18")
ou_fetch("p001", "daily-readiness", "2026-05-01", "2026-06-18")

# Efficient: one token for multiple fetches
tok <- tb_get_token("p001")
tb_fetch("p001", "sleep",  start, end, token = tok)
tb_fetch("p001", "steps",  start, end, token = tok)

# Browse data types
names(GH_DATA_TYPES)
names(WT_DATA_TYPES)
names(OU_DATA_TYPES)
```

## Reports

```r
resp <- httr::POST(
  paste0(Sys.getenv("TOKENBRIDGE_URL"), "/sleep-report"),
  httr::add_headers(Authorization = paste("Bearer", Sys.getenv("TOKENBRIDGE_API_KEY"))),
  body   = list(label = "P001", template = "sleep-bp",
                data = list("withings-summary" = sleep_df,
                            "withings-bp"      = bp_df)),
  encode = "json"
)
writeBin(httr::content(resp, as = "raw"), "report_p001.html")
```

→ [Reports & template authoring](../reports.md)

## See also

- [Getting Started](../getting-started.md)
- [API Reference](reference.md)
- [Providers](../providers/index.md)
