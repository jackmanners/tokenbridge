# TokenBridge

Self-hosted OAuth token management for health data research. TokenBridge runs the OAuth flow for providers like Google Health/Fitbit, Withings, and Oura, stores tokens for every participant, and keeps them refreshed automatically for the life of a study - so your analysis code never has to touch OAuth.

---

## Two parts, two audiences

**The Platform** is TokenBridge itself: a small, self-hosted backend (Supabase edge functions + Postgres) that someone deploys once per lab or study. It's often the same person who also writes the analysis scripts - but not always, so the two are documented separately.

**Client Libraries** (Python, R, JavaScript) are thin, optional packages that talk to an existing deployment from your research script. You don't need to understand the Platform to use one - you just need its URL and API key from whoever deployed it.

```
Deploy once (Platform)              Use it (Client Libraries)              Participant (once)
        │                                    │                                    │
        ▼                                    ▼                                    ▼
Supabase project + edge               tb.get_token("p001")            clicks auth link, signs in,
functions + Postgres      ◄───────    tb.auth_url("p001")    ───────► approves - token stored
(token storage + refresh)          (Python/R/JavaScript)              automatically from here on
```

| I want to... | Start here |
|---|---|
| Deploy my own TokenBridge instance | [Platform → Deploying TokenBridge](platform/deploying.md) |
| Use an instance someone else already deployed | [Client Libraries → Getting Started](clients/getting-started.md) |
| See a complete, realistic script | [Examples](clients/examples.md) |

---

## Supported providers

| Provider ID | Status | Notes |
|---|---|---|
| `google-health` | Supported | Requires Fitbit app linked to a Google account |
| `withings` | Supported | Requires Withings device (scale, BPM cuff, sleep mat, etc.) |
| `oura` | Supported | Requires Oura Ring (Gen 2 or Gen 3) |
| `polar` | Supported | Requires Polar watch / H-series HR strap + AccessLink app |
| `strava` | Supported | Any GPS-capable device, via upload to Strava |
| `whoop` | Supported | Requires WHOOP band (4.0 / 5.0) |

Plus Garmin, Huawei Health Kit, Health Connect, and Dexcom as unfinished stubs (token retrieval works; data fetching doesn't). Full list, data types, units, and endpoint notes: [Providers](platform/providers/index.md).
