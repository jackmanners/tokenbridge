# Getting Started

This page covers installation and first use. If you need to deploy your own TokenBridge instance, see [Deployment](deployment.md) first.

---

## Installation

=== "Python"

    Requires Python 3.10+.

    ```bash
    pip install git+https://github.com/jackmanners/tokenbridge.git#subdirectory=python
    ```

    Dependencies installed automatically: `requests`, `python-dotenv`.

=== "R"

    Requires R 4.0+.

    ```r
    # Install devtools if you don't have it
    install.packages("devtools")

    devtools::install_github("jackmanners/tokenbridge", subdir = "r")
    ```

    Dependencies installed automatically: `httr`.

---

## Configuration

TokenBridge needs two values to connect to your deployment:

| Variable | Description |
|---|---|
| `TOKENBRIDGE_URL` | Your Supabase functions base URL, e.g. `https://abcdef.supabase.co/functions/v1` |
| `TOKENBRIDGE_API_KEY` | The API key you set as a Supabase secret during deployment |

The recommended way to store these is in a `.env` file in your project directory. Run the setup wizard once:

=== "Python"

    ```bash
    python -m tokenbridge
    ```

    The wizard prompts for your URL and API key, verifies the connection, and saves them to `.env`.

=== "R"

    ```r
    library(tokenbridge)
    tb_setup()
    ```

    Same as the Python wizard — prompts, verifies, saves to `.env`.

!!! warning "Keep .env out of version control"
    Your `.env` file contains your API key. Make sure `.env` is in your `.gitignore`.  
    This repo's [`.gitignore`](https://github.com/jackmanners/tokenbridge/blob/main/.gitignore) already excludes it, but make sure for repo clones.

### Manual configuration

If you prefer not to use `.env`, you can pass credentials directly:

=== "Python"

    ```python
    from tokenbridge import TokenBridge

    tb = TokenBridge(
        url="https://abcdef.supabase.co/functions/v1",
        api_key="your-api-key",
    )
    ```

=== "R"

    ```r
    # Set environment variables directly
    Sys.setenv(
      TOKENBRIDGE_URL     = "https://abcdef.supabase.co/functions/v1",
      TOKENBRIDGE_API_KEY = "your-api-key"
    )
    library(tokenbridge)
    ```

---

## Onboarding participants

Each participant needs to authorise their Google / Fitbit account once. Generate a unique URL for each person and send it to them (email, SMS, whatever works for your study).

=== "Python"

    ```python
    from tokenbridge import TokenBridge

    tb = TokenBridge()

    # Single participant
    url = tb.auth_url("participant-001")
    print(url)

    # Batch — returns {user_id: url}
    urls = tb.auth_urls(["p001", "p002", "p003", "p004"])
    for uid, url in urls.items():
        print(f"{uid}: {url}")
    ```

=== "R"

    ```r
    # Single participant
    tb_auth_url("participant-001")

    # Batch — returns named character vector
    urls <- tb_auth_urls(c("p001", "p002", "p003", "p004"))
    for (uid in names(urls)) cat(uid, ":", urls[[uid]], "\n")
    ```

The participant:

1. Clicks the link
2. Signs in with their account (Google for Fitbit, Withings, or Oura)
3. Approves the requested permissions
4. Sees a success page — done

!!! note "Google Health / Fitbit"
    Participants must have the **Fitbit app** installed and signed in with the same Google account they use to authorise. Without this, there is no health data to access.

!!! note "Test mode warning"
    If your Google Cloud app is in Testing mode (the default for new deployments), participants will see an "unverified app" warning. They should click **Advanced → Go to [app name] (unsafe)** to proceed. This is expected — see [Deployment](deployment.md#google-verification) for context.

---

## Fetching data

Once a participant has authorised, you can fetch any of their data types immediately.

### Basic fetch

=== "Python"

    ```python
    from tokenbridge import TokenBridge

    tb = TokenBridge()

    sleep = tb.fetch("p001", "sleep", "2026-05-01", "2026-06-18")
    steps = tb.fetch("p001", "steps", "2026-05-01", "2026-06-18")
    hrv   = tb.fetch("p001", "heart-rate-variability", "2026-05-01", "2026-06-18")

    print(f"Sleep sessions: {len(sleep)}")
    print(sleep[0])   # first session as a flat dict
    ```

=== "R"

    ```r
    sleep <- tb_fetch("p001", "sleep", "2026-05-01", "2026-06-18")
    steps <- tb_fetch("p001", "steps", "2026-05-01", "2026-06-18")
    hrv   <- tb_fetch("p001", "heart-rate-variability", "2026-05-01", "2026-06-18")

    nrow(sleep)    # number of sleep sessions
    head(sleep)    # first few rows
    ```

Results are returned as flat records (Python: `list[dict]`, R: `data.frame`). Nested API fields are flattened with dot notation — e.g. `startTime.seconds`.

### Setting a default provider

=== "Python"

    ```python
    tb = TokenBridge()
    tb.provider = "google-health"    # default; change to switch providers

    tb.fetch("p001", "sleep", start, end)    # uses tb.provider
    ```

=== "R"

    ```r
    tb_set_provider("google-health")    # persists for the session

    tb_fetch("p001", "sleep", start, end)    # uses the default
    ```

### Provider namespaces (Python)

Python exposes provider namespaces as attributes on `tb`. These always use the named provider regardless of `tb.provider`:

```python
tb.google.fetch("p001", "sleep", start, end)      # always google-health
tb.withings.fetch("p001", "activity", start, end) # always withings
tb.oura.fetch("p001", "daily-readiness", start, end)  # always oura
```

### Token reuse

Each call to `tb.fetch()` / `tb_fetch()` makes one request to TokenBridge to get a valid token. When fetching several data types for the same participant in one script, get the token once and pass it through:

=== "Python"

    ```python
    token = tb.get_token("p001")

    sleep = tb.fetch("p001", "sleep",                  start, end, token=token)
    steps = tb.fetch("p001", "steps",                  start, end, token=token)
    hrv   = tb.fetch("p001", "heart-rate-variability", start, end, token=token)
    rhr   = tb.fetch("p001", "daily-resting-heart-rate", start, end, token=token)
    ```

=== "R"

    ```r
    tok <- tb_get_token("p001")

    sleep <- tb_fetch("p001", "sleep",                   start, end, token = tok)
    steps <- tb_fetch("p001", "steps",                   start, end, token = tok)
    hrv   <- tb_fetch("p001", "heart-rate-variability",  start, end, token = tok)
    rhr   <- tb_fetch("p001", "daily-resting-heart-rate", start, end, token = tok)
    ```

---

## Auditing your cohort

Before running analysis, check data completeness across participants:

=== "Python"

    ```python
    audit = tb.google.data_completeness(
        ["p001", "p002", "p003"],
        "2026-05-01", "2026-06-18",
        data_types=["sleep", "steps", "heart-rate-variability"],
    )
    # list of dicts: user_id, data_type, n, days_with_data, coverage_pct
    ```

=== "R"

    ```r
    audit <- gh_data_completeness(
      c("p001", "p002", "p003"),
      "2026-05-01", "2026-06-18",
      data_types = c("sleep", "steps", "heart-rate-variability")
    )
    print(audit)   # data.frame: user_id, data_type, n, days_with_data, coverage_pct
    ```

---

## Available data types

Data type IDs are kebab-case strings passed as the `data_type` argument. Each provider has its own set:

=== "Python"

    ```python
    from tokenbridge.providers.google_health import DATA_TYPES as GH_DATA_TYPES
    from tokenbridge.providers.withings import DATA_TYPES as WT_DATA_TYPES
    from tokenbridge.providers.oura import DATA_TYPES as OU_DATA_TYPES

    print(list(GH_DATA_TYPES))   # e.g. "sleep", "steps", "heart-rate-variability", ...
    print(list(WT_DATA_TYPES))   # e.g. "sleep-summary", "activity", "weight", ...
    print(list(OU_DATA_TYPES))   # e.g. "daily-sleep", "daily-readiness", "heartrate", ...
    ```

=== "R"

    ```r
    names(GH_DATA_TYPES)   # Google Health
    names(WT_DATA_TYPES)   # Withings
    names(OU_DATA_TYPES)   # Oura
    ```

Full list with descriptions, units, and device requirements: [Provider Reference](providers.md).
