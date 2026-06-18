# R API Reference

Functions are grouped by prefix. All functions load `.env` automatically when
`env_file` is specified (default: `".env"` in the working directory).

---

## TokenBridge platform (`tb_`)

### tb_setup

```r
tb_setup(env_file = ".env")
```

Interactive setup wizard. Prompts for your TokenBridge URL and API key, verifies the
connection, and saves them to an `.env` file. Run once before anything else.

**Arguments**

| Argument | Type | Default | Description |
|---|---|---|---|
| `env_file` | character | `".env"` | Path to the `.env` file to write |

**Returns** Invisibly: `list(url, api_key)`

**Example**

```r
tb_setup()
# ── TokenBridge setup ─────────────────────────────
#
# TokenBridge URL [https://YOUR_PROJECT_REF.supabase.co/functions/v1]:
# > https://abcdef.supabase.co/functions/v1
# API key:
# > ••••••••••••••••••••
#
# ✓ Saved to .env
```

---

### tb_set_provider

```r
tb_set_provider(provider)
```

Set the default provider for the current R session. All subsequent `tb_fetch()`,
`tb_auth_url()`, `tb_get_token()`, and `tb_token_status()` calls use this provider
unless overridden with `provider=`.

Can be called multiple times to switch providers mid-script.

**Arguments**

| Argument | Type | Description |
|---|---|---|
| `provider` | character | Provider ID — e.g. `"google-health"`, `"withings"` |

**Returns** Invisibly: the provider string

**Example**

```r
tb_set_provider("google-health")
tb_fetch("p001", "sleep", "2026-05-01", "2026-06-18")   # uses google-health

tb_set_provider("withings")
tb_fetch("p001", "sleep", "2026-05-01", "2026-06-18")   # now uses withings
```

---

### tb_get_provider

```r
tb_get_provider()
```

Return the current session default provider (set by `tb_set_provider()`).
Default at package load: `"google-health"`.

**Returns** character — the current default provider ID

---

### tb_fetch

```r
tb_fetch(user_id, data_type, start_date, end_date,
         token    = NULL,
         provider = tb_get_provider(),
         env_file = ".env")
```

**The canonical data fetch function.** Fetches health data for one participant and
returns a flat `data.frame` with one row per data point.

`data_type` is the kebab-case type ID — e.g. `"sleep"`, `"steps"`,
`"heart-rate-variability"`. See `names(GH_DATA_TYPES)` or [Providers](../providers.md)
for the full list.

`provider` defaults to `tb_get_provider()`. Pass explicitly to override for a single
call without changing the session default.

**Arguments**

| Argument | Type | Default | Description |
|---|---|---|---|
| `user_id` | character | — | TokenBridge participant ID |
| `data_type` | character | — | Kebab-case type ID (e.g. `"sleep"`, `"steps"`) |
| `start_date` | character | — | Start of date range, `"YYYY-MM-DD"` |
| `end_date` | character | — | End of date range, `"YYYY-MM-DD"` |
| `token` | character | `NULL` | Pre-fetched access token. Pass to skip a TokenBridge round-trip when fetching multiple types for the same user |
| `provider` | character | `tb_get_provider()` | Provider ID. Overrides session default for this call only |
| `env_file` | character | `".env"` | Path to `.env` file |

**Returns** `data.frame` with one row per data point. Column names are the API field
names, flattened with dot notation (e.g. `startTime.seconds`).
Returns an empty `data.frame` if no data exists for the period.

**Examples**

```r
# Basic
sleep <- tb_fetch("p001", "sleep", "2026-05-01", "2026-06-18")
steps <- tb_fetch("p001", "steps", "2026-05-01", "2026-06-18")

# Token reuse — one TokenBridge call for multiple fetches
tok <- tb_get_token("p001")
sleep <- tb_fetch("p001", "sleep",                   "2026-05-01", "2026-06-18", token = tok)
steps <- tb_fetch("p001", "steps",                   "2026-05-01", "2026-06-18", token = tok)
hrv   <- tb_fetch("p001", "heart-rate-variability",  "2026-05-01", "2026-06-18", token = tok)
rhr   <- tb_fetch("p001", "daily-resting-heart-rate","2026-05-01", "2026-06-18", token = tok)

# Override provider for one call
tb_fetch("p001", "sleep", "2026-05-01", "2026-06-18", provider = "withings")

# Loop over all Google Health types
tok <- tb_get_token("p001")
all_data <- lapply(names(GH_DATA_TYPES), function(dt) {
  tb_fetch("p001", dt, "2026-05-01", "2026-06-18", token = tok)
})
names(all_data) <- names(GH_DATA_TYPES)
```

---

### tb_auth_url

```r
tb_auth_url(user_id, provider = tb_get_provider(), env_file = ".env")
```

Return the URL a participant should visit to authorise their account.
Send this link via email, SMS, or however you communicate with participants.
Once they complete the OAuth flow, their token is stored and you can fetch data immediately.

**Arguments**

| Argument | Type | Default | Description |
|---|---|---|---|
| `user_id` | character | — | TokenBridge participant ID |
| `provider` | character | `tb_get_provider()` | Provider to authorise |
| `env_file` | character | `".env"` | Path to `.env` file |

**Returns** character — the full auth URL

**Example**

```r
url <- tb_auth_url("participant-001")
cat("Please visit this link to connect your Fitbit:\n", url, "\n")
```

---

### tb_auth_urls

```r
tb_auth_urls(user_ids, provider = tb_get_provider(), env_file = ".env")
```

Return auth URLs for multiple participants at once.

**Arguments**

| Argument | Type | Default | Description |
|---|---|---|---|
| `user_ids` | character vector | — | TokenBridge participant IDs |
| `provider` | character | `tb_get_provider()` | Provider to authorise |
| `env_file` | character | `".env"` | Path to `.env` file |

**Returns** Named character vector: `c(user_id = url, ...)`

**Example**

```r
urls <- tb_auth_urls(c("p001", "p002", "p003", "p004"))
# Send each URL to the corresponding participant
for (uid in names(urls)) {
  cat(uid, "->", urls[[uid]], "\n")
}
```

---

### tb_get_token

```r
tb_get_token(user_id, provider = tb_get_provider(), env_file = ".env")
```

Fetch a valid access token for a participant. TokenBridge refreshes automatically
if the token is within 5 minutes of expiry.

You rarely need this directly — `tb_fetch()` and `gh_fetch()` call it internally.
Use it when you want to fetch multiple data types for the same user efficiently:

**Arguments**

| Argument | Type | Default | Description |
|---|---|---|---|
| `user_id` | character | — | TokenBridge participant ID |
| `provider` | character | `tb_get_provider()` | Provider |
| `env_file` | character | `".env"` | Path to `.env` file |

**Returns** character — the OAuth access token

**Example**

```r
tok <- tb_get_token("p001")
sleep <- tb_fetch("p001", "sleep", start, end, token = tok)
steps <- tb_fetch("p001", "steps", start, end, token = tok)
hrv   <- tb_fetch("p001", "heart-rate-variability", start, end, token = tok)
```

---

### tb_token_status

```r
tb_token_status(user_id, provider = tb_get_provider(), env_file = ".env")
```

Return token metadata for a participant without exposing the raw token.
Useful for auditing whether participants have authorised and when their tokens expire.

**Arguments**

| Argument | Type | Default | Description |
|---|---|---|---|
| `user_id` | character | — | TokenBridge participant ID |
| `provider` | character | `tb_get_provider()` | Provider |
| `env_file` | character | `".env"` | Path to `.env` file |

**Returns** Named list:

| Field | Type | Description |
|---|---|---|
| `expires_at` | character | ISO 8601 expiry timestamp |
| `refreshed` | logical | `TRUE` if the token was refreshed on this call |
| `scopes` | character vector | Granted OAuth scopes |

**Example**

```r
status <- tb_token_status("p001")
cat("Expires:", status$expires_at, "\n")
cat("Was refreshed:", status$refreshed, "\n")
```

---

## Google Health (`gh_`)

### GH_DATA_TYPES

```r
GH_DATA_TYPES
```

Named character vector of all supported Google Health data type IDs.
Names are the kebab-case IDs to pass to `gh_fetch()` / `tb_fetch()`.
Values are `"list"` or `"dailyRollup"` (the endpoint type — handled automatically).

**Usage**

```r
# See all type IDs
names(GH_DATA_TYPES)

# Check the endpoint type for a specific ID
GH_DATA_TYPES["sleep"]       # "list"
GH_DATA_TYPES["floors"]      # "dailyRollup"

# Loop over all types
tok <- tb_get_token("p001")
for (dt in names(GH_DATA_TYPES)) {
  df <- gh_fetch("p001", dt, start, end, token = tok)
  cat(dt, ":", nrow(df), "rows\n")
}
```

Full descriptions, units, and device requirements: [Providers](../providers.md).

---

### gh_fetch

```r
gh_fetch(user_id, data_type, start_date, end_date,
         token = NULL, env_file = ".env")
```

Fetch Google Health data for a participant. Equivalent to
`tb_fetch(..., provider = "google-health")`.

This is the Google Health shorthand — it always uses the `"google-health"` provider
regardless of the session default set by `tb_set_provider()`.

Automatically handles the difference between `list` and `dailyRollup` endpoint types
based on `GH_DATA_TYPES`.

**Arguments**

| Argument | Type | Default | Description |
|---|---|---|---|
| `user_id` | character | — | TokenBridge participant ID |
| `data_type` | character | — | Kebab-case type ID. See `names(GH_DATA_TYPES)` |
| `start_date` | character | — | `"YYYY-MM-DD"` |
| `end_date` | character | — | `"YYYY-MM-DD"` |
| `token` | character | `NULL` | Pre-fetched access token (avoids a TokenBridge call) |
| `env_file` | character | `".env"` | Path to `.env` file |

**Returns** `data.frame` — one row per data point, columns depend on type.
Returns an empty `data.frame` if no data exists for the period.

**Examples**

```r
# Basic
sleep <- gh_fetch("p001", "sleep", "2026-05-01", "2026-06-18")
steps <- gh_fetch("p001", "steps", "2026-05-01", "2026-06-18")

# Token reuse
tok <- tb_get_token("p001")
sleep <- gh_fetch("p001", "sleep",                  start, end, token = tok)
hrv   <- gh_fetch("p001", "heart-rate-variability", start, end, token = tok)
rhr   <- gh_fetch("p001", "daily-resting-heart-rate", start, end, token = tok)
spo2  <- gh_fetch("p001", "daily-oxygen-saturation", start, end, token = tok)
```

---

### gh_summary

```r
gh_summary(user_id, start_date, end_date, env_file = ".env")
```

Summary statistics for one participant covering sleep and respiratory rate.
Makes a single token request and reuses it for both data fetches.

**Arguments**

| Argument | Type | Default | Description |
|---|---|---|---|
| `user_id` | character | — | TokenBridge participant ID |
| `start_date` | character | — | `"YYYY-MM-DD"` |
| `end_date` | character | — | `"YYYY-MM-DD"` |
| `env_file` | character | `".env"` | Path to `.env` file |

**Returns** Named list:

```
list(
  user_id      = "p001",
  period_days  = 48,
  sleep = list(
    n                  = 45,      # number of sleep sessions
    days_with_data     = 44,      # unique days with at least one session
    coverage_pct       = 91.7,    # days_with_data / period_days * 100
    mean_duration_hours = 7.23,
    std_duration_hours  = 0.91
  ),
  respiratory_rate = list(
    n              = 44,
    days_with_data = 44,
    coverage_pct   = 91.7,
    mean           = 15.2,
    min            = 12.1,
    max            = 18.4,
    std            = 1.3
  )
)
```

**Example**

```r
s <- gh_summary("p001", "2026-05-01", "2026-06-18")
cat("Sleep coverage:", s$sleep$coverage_pct, "%\n")
cat("Mean sleep duration:", s$sleep$mean_duration_hours, "hours\n")
cat("Mean respiratory rate:", s$respiratory_rate$mean, "breaths/min\n")
```

---

### gh_summary_all

```r
gh_summary_all(user_ids, start_date, end_date, env_file = ".env")
```

Run `gh_summary()` for multiple participants.
Errors per participant are caught and returned as `list(error = "message")` for that entry
rather than stopping the whole call.

**Arguments**

| Argument | Type | Default | Description |
|---|---|---|---|
| `user_ids` | character vector | — | TokenBridge participant IDs |
| `start_date` | character | — | `"YYYY-MM-DD"` |
| `end_date` | character | — | `"YYYY-MM-DD"` |
| `env_file` | character | `".env"` | Path to `.env` file |

**Returns** Named list, one element per `user_id`. Each element is the result
of `gh_summary()`, or `list(error = "message")` if that participant failed.

**Example**

```r
summaries <- gh_summary_all(c("p001", "p002", "p003"), "2026-05-01", "2026-06-18")

for (uid in names(summaries)) {
  s <- summaries[[uid]]
  if (!is.null(s$error)) {
    cat(uid, "ERROR:", s$error, "\n")
  } else {
    cat(uid, "sleep coverage:", s$sleep$coverage_pct, "%\n")
  }
}
```

---

### gh_data_completeness

```r
gh_data_completeness(user_ids, start_date, end_date, env_file = ".env")
```

Data completeness audit for multiple participants. Returns a `data.frame` with one row
per participant × data type — useful for checking data quality before running analysis.

**Arguments**

| Argument | Type | Default | Description |
|---|---|---|---|
| `user_ids` | character vector | — | TokenBridge participant IDs |
| `start_date` | character | — | `"YYYY-MM-DD"` |
| `end_date` | character | — | `"YYYY-MM-DD"` |
| `env_file` | character | `".env"` | Path to `.env` file |

**Returns** `data.frame` with columns:

| Column | Type | Description |
|---|---|---|
| `user_id` | character | Participant ID |
| `data_type` | character | `"sleep"` or `"respiratory_rate"` |
| `n` | integer | Total data points in period |
| `days_with_data` | integer | Days with at least one data point |
| `coverage_pct` | numeric | `days_with_data / period_days * 100` |
| `error` | character | Error message if fetch failed, `NA` otherwise |

**Example**

```r
audit <- gh_data_completeness(
  c("p001", "p002", "p003", "p004"),
  "2026-05-01", "2026-06-18"
)

print(audit)
#    user_id        data_type  n days_with_data coverage_pct error
# 1     p001            sleep 45             44         91.7    NA
# 2     p001 respiratory_rate 44             44         91.7    NA
# 3     p002            sleep 47             46         95.8    NA
# ...

# Flag participants with low coverage
low <- audit[!is.na(audit$coverage_pct) & audit$coverage_pct < 80, ]
```

---

## Withings (`wt_`)

### wt_fetch

```r
wt_fetch(user_id, data_type, start_date, end_date,
         token = NULL, env_file = ".env")
```

!!! warning "Not yet implemented"
    The Withings OAuth flow is wired but data fetching is not yet implemented.
    This function currently raises an error.

Fetch Withings data for a participant. Equivalent to
`tb_fetch(..., provider = "withings")`.

**Arguments**

| Argument | Type | Default | Description |
|---|---|---|---|
| `user_id` | character | — | TokenBridge participant ID |
| `data_type` | character | — | Withings type ID |
| `start_date` | character | — | `"YYYY-MM-DD"` |
| `end_date` | character | — | `"YYYY-MM-DD"` |
| `token` | character | `NULL` | Pre-fetched access token |
| `env_file` | character | `".env"` | Path to `.env` file |

Planned type IDs: `"sleep"`, `"heart-rate"`, `"weight"`, `"blood-pressure"`.
See [Providers](../providers.md).

---

## Data type IDs

Pass any of these strings as the `data_type` argument. See [Providers](../providers.md)
for units, device requirements, and notes.

| Category | Type IDs |
|---|---|
| **Sleep** | `sleep`, `respiratory-rate-sleep-summary`, `daily-sleep-temperature-derivations` |
| **Activity** | `steps`, `distance`, `exercise`, `active-minutes`, `active-zone-minutes`, `active-energy-burned`, `activity-level`, `sedentary-period`, `altitude`, `swim-lengths-data`, `time-in-heart-rate-zone` |
| **Activity (daily rollup)** | `floors`, `total-calories`, `calories-in-heart-rate-zone` |
| **Fitness** | `vo2-max`, `run-vo2-max`, `daily-vo2-max` |
| **Heart** | `heart-rate`, `daily-resting-heart-rate`, `daily-heart-rate-zones`, `heart-rate-variability`, `daily-heart-rate-variability`, `electrocardiogram`, `irregular-rhythm-notification` |
| **Vitals** | `oxygen-saturation`, `daily-oxygen-saturation`, `daily-respiratory-rate`, `core-body-temperature`, `blood-glucose` |
| **Body** | `weight`, `body-fat`, `height` |
| **Nutrition** | `food`, `nutrition-log`, `hydration-log` |
