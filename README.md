# TokenBridge

> Handles OAuth and token storage for health data APIs so your research scripts don't have to.

[![Docs](https://img.shields.io/badge/docs-jackmanners.github.io%2Ftokenbridge-informational)](https://jackmanners.github.io/tokenbridge)
[![License: PolyForm NC](https://img.shields.io/badge/license-PolyForm%20NC-blue)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](python/)
[![R 4.0+](https://img.shields.io/badge/R-4.0%2B-276DC3?logo=r&logoColor=white)](r/)

**[Documentation](https://jackmanners.github.io/tokenbridge)** — setup guide, provider reference, API reference

---

Pulling data from Google Health/Fitbit, Withings, or Oura into a research script means dealing with OAuth, storing tokens for all your participants, and keeping them refreshed across a study that can run for months. TokenBridge handles all of that. Your scripts call one endpoint to get a valid token, then query the provider API directly.

```
Participant (once)               Your research script
     │                                  │
     │  clicks auth link                │  tb.fetch("p001", "sleep", ...)
     ▼                                  ▼
 TokenBridge  ────────────────────  /token endpoint
     │                             returns a valid access token
     └── Supabase Postgres         script calls the health API directly
         token storage + auto-refresh
```

---

## Install

**Python**
```bash
pip install git+https://github.com/jackmanners/tokenbridge.git#subdirectory=python
python -m tokenbridge   # one-time setup — saves URL and API key to .env
```

**R**
```r
devtools::install_github("jackmanners/tokenbridge", subdir = "r")
library(tokenbridge)
tb_setup()
```

---

## Usage

```python
from tokenbridge import TokenBridge
tb = TokenBridge()

# Send each participant a one-time auth link
print(tb.auth_url("p001"))

# Fetch data once they've authorised
sleep = tb.fetch("p001", "sleep", "2026-05-01", "2026-06-18")
steps = tb.fetch("p001", "steps", "2026-05-01", "2026-06-18")
```

```r
library(tokenbridge)

links <- tb_auth_urls(c("p001", "p002", "p003"))
sleep <- tb_fetch("p001", "sleep", "2026-05-01", "2026-06-18")
```

---

## License

[PolyForm Noncommercial 1.0.0](LICENSE) — free for personal, research, and educational use.
