# R Package

The `tokenbridge` R package uses a consistent `tb_` / `gh_` / `wt_` prefix convention
in place of object namespacing (which is idiomatic in R).

## Installation

```r
<<<<<<< HEAD
devtools::install_github("jackmanners/tokenbridge", subdir = "r")
=======
devtools::install_github("YOUR_USERNAME/tokenbridge", subdir = "r")
>>>>>>> e656476530cbfcd464560310f0bbb5cd10018519
```

Requires R 4.0+. Dependencies: `httr`.

## Architecture

```
tb_*    TokenBridge platform — auth, token management, canonical data fetch
gh_*    Google Health shorthand — always uses "google-health" provider
wt_*    Withings shorthand — stub, not yet implemented

tb_set_provider("google-health")       set session default
tb_fetch("p001", "sleep", s, e)        canonical fetch, uses default provider
gh_fetch("p001", "sleep", s, e)        Google Health shorthand
```

## Quick start

```r
library(tokenbridge)

tb_setup()                           # once — saves .env credentials
tb_set_provider("google-health")     # optional, it's the default

# Onboard
tb_auth_url("p001")

# Fetch
tb_fetch("p001", "sleep", "2026-05-01", "2026-06-18")
tb_fetch("p001", "steps", "2026-05-01", "2026-06-18")

# Google Health shorthand
gh_fetch("p001", "heart-rate-variability", "2026-05-01", "2026-06-18")

# One-off override without changing session default
tb_fetch("p001", "sleep", start, end, provider = "withings")

# Efficient: one token for multiple fetches
tok <- tb_get_token("p001")
tb_fetch("p001", "sleep",  start, end, token = tok)
tb_fetch("p001", "steps",  start, end, token = tok)

# Browse data types
names(GH_DATA_TYPES)
```

## See also

- [Getting Started](../getting-started.md)
- [API Reference](reference.md)
- [Providers](../providers.md)
