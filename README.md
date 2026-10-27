# TokenBridge

> Self-hosted OAuth token management for health data research.

[![Docs](https://img.shields.io/badge/docs-jackmanners.github.io%2Ftokenbridge-informational)](https://jackmanners.github.io/tokenbridge)
[![License: PolyForm NC](https://img.shields.io/badge/license-PolyForm%20NC-blue)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](python/)
[![R 4.0+](https://img.shields.io/badge/R-4.0%2B-276DC3?logo=r&logoColor=white)](r/)
[![Node 18+](https://img.shields.io/badge/node-18%2B-339933?logo=node.js&logoColor=white)](js/)

**[Full documentation](https://jackmanners.github.io/tokenbridge)**

---

Pulling data from Google Health/Fitbit, Withings, Oura, Polar, Strava, or WHOOP into a research script means dealing with OAuth, storing tokens for every participant, and keeping them refreshed across a study that can run for months. TokenBridge handles all of that once, self-hosted on your own Supabase project.

Two parts: **the Platform** (the backend you deploy once) and **Client Libraries** (Python, R, JS/TS - thin packages your scripts use to talk to it). Often the same person does both, but they're documented separately, since not always.

```
Deploy once (Platform)              Use it (Client Libraries)              Participant (once)
        │                                    │                                    │
        ▼                                    ▼                                    ▼
Supabase project + edge               tb.get_token("p001")            clicks auth link, signs in,
functions + Postgres      ◄───────    tb.auth_url("p001")    ───────► approves - token stored
(token storage + refresh)             (Python/R/JS-TS)                automatically from here on
```

---

## Deploy your own instance

See [Platform → Deploying TokenBridge](https://jackmanners.github.io/tokenbridge/platform/deploying/) - a free Supabase account, ~20-30 minutes.

## Use an existing deployment

**Python**
```bash
pip install git+https://github.com/jackmanners/tokenbridge.git#subdirectory=python
python -m tokenbridge   # one-time setup - saves URL and API key to .env
```

**R**
```r
devtools::install_github("jackmanners/tokenbridge", subdir = "r")
library(tokenbridge)
tb_setup()
```

**JS/TS** (token retrieval only - no data-fetching layer)
```bash
npm install "git+https://github.com/jackmanners/tokenbridge.git#path:js"
```

```python
from tokenbridge import TokenBridge
tb = TokenBridge()

print(tb.auth_url("p001"))                                    # send to participant
sleep = tb.fetch("p001", "sleep", "2026-05-01", "2026-06-18")  # fetch once authorised
```

See [Client Libraries → Getting Started](https://jackmanners.github.io/tokenbridge/clients/getting-started/) for R and JS/TS, or [Examples](https://jackmanners.github.io/tokenbridge/clients/examples/) for complete scripts.

---

## License

[PolyForm Noncommercial 1.0.0](LICENSE) - free for personal, research, and educational use.
