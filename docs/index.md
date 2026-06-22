# TokenBridge

**Self-hosted OAuth token management for health data research.**

TokenBridge sits between your research scripts and health APIs (Google Health / Fitbit, Withings) and handles the parts that are genuinely hard: the OAuth 2.0 PKCE flow, secure token storage, and automatic refresh before expiry.

Your scripts call `tb.fetch("p001", "sleep", start, end)` and get data back. That's it.

```
participant (browser, once)
      │  visits auth-start URL
      ▼
  TokenBridge  ◄──── your scripts (tb.fetch → valid data)
      │
      └── Supabase Postgres (token storage + auto-refresh)
```

---

## Who is this for?

**Researchers deploying their own instance** — you have a study, a Supabase account, and a Google Cloud project. You run the deployment once, add participants, and fetch data from Python or R.

**Collaborators and students** — your PI has deployed TokenBridge. You install the Python or R package, point it at their instance, and write analysis scripts without thinking about OAuth.

---

## Key features

- **Full OAuth 2.0 PKCE flow** — participants click a link, sign in with Google, approve access. Done.
- **Automatic token refresh** — tokens are refreshed proactively (5-minute window before expiry). Your scripts never see an expired token.
- **Multi-user** — one deployment supports any number of participants. Each has their own token.
- **Multi-provider** — Google Health (Fitbit-backed) is fully supported. Withings auth is wired; data fetch is in progress.
- **38 Google Health data types** — sleep, activity, heart rate, HRV, SpO2, weight, nutrition, and more. See [Providers](providers.md).
- **Python + R** — identical API shape in both languages. Type IDs are the same kebab-case strings.
- **Self-hosted** — your tokens never leave your Supabase instance.

---

## Quick install

=== "Python"

    ```bash
<<<<<<< HEAD
    pip install git+https://github.com/jackmanners/tokenbridge.git#subdirectory=python
=======
    pip install git+https://github.com/YOUR_USERNAME/tokenbridge.git#subdirectory=python
>>>>>>> e656476530cbfcd464560310f0bbb5cd10018519
    python -m tokenbridge   # interactive setup wizard
    ```

=== "R"

    ```r
<<<<<<< HEAD
    devtools::install_github("jackmanners/tokenbridge", subdir = "r")
=======
    devtools::install_github("YOUR_USERNAME/tokenbridge", subdir = "r")
>>>>>>> e656476530cbfcd464560310f0bbb5cd10018519
    library(tokenbridge)
    tb_setup()   # interactive setup wizard
    ```

---

## 30-second example

=== "Python"

    ```python
    from tokenbridge import TokenBridge

    tb = TokenBridge()

    # Send this link to your participant — they authorise once
    print(tb.auth_url("participant-001"))

    # Fetch their data
    sleep = tb.fetch("participant-001", "sleep", "2026-05-01", "2026-06-18")
    steps = tb.fetch("participant-001", "steps", "2026-05-01", "2026-06-18")

    # Audit your whole cohort
    tb.google.data_completeness(["p001", "p002", "p003"], "2026-05-01", "2026-06-18")
    ```

=== "R"

    ```r
    library(tokenbridge)

    # Send this link to your participant
    tb_auth_url("participant-001")

    # Fetch their data
    sleep <- tb_fetch("participant-001", "sleep", "2026-05-01", "2026-06-18")
    steps <- tb_fetch("participant-001", "steps", "2026-05-01", "2026-06-18")

    # Audit your whole cohort
    gh_data_completeness(c("p001", "p002", "p003"), "2026-05-01", "2026-06-18")
    ```

---

## Next steps

- [Getting Started](getting-started.md) — install, configure, and fetch your first data point
- [Deployment](deployment.md) — set up your own TokenBridge instance (20–30 minutes)
- [Providers](providers.md) — all supported data types with units and notes
- [Python reference](python/reference.md) — full API documentation
- [R reference](r/reference.md) — full API documentation
