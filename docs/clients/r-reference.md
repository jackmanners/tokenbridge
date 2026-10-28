# R Data-Fetching Reference

Exhaustive reference for the R package's **data-fetching layer only** -
`tb_fetch()`, the provider shorthand functions, and session-default helpers.
For `tb_setup()`, `tb_auth_url()`, `tb_auth_urls()`, and `tb_get_token()`,
see the [Token API Reference](token-reference.md) - this page doesn't repeat them.

All functions load `.env` automatically when `env_file` is specified
(default: `".env"` in the working directory).

---

## tb_set_provider / tb_get_provider

```r
tb_set_provider(provider)   # e.g. "google-health", "withings", "oura"
tb_get_provider()
```

Set/get the default provider for the current R session - used by `tb_fetch()`
when `provider=` isn't passed explicitly. See [Data-Fetching Guide](data-fetching.md#setting-a-default-provider)
for usage.

---

## tb_fetch

```r
tb_fetch(user_id, data_type, start_date, end_date,
         token        = NULL,
         provider     = tb_get_provider(),
         sleepscan    = NULL,
         sleepscan_key = NULL,
         env_file     = ".env")
```

**The canonical data fetch function.** Fetches health data for one participant and
returns a flat `data.frame` with one row per data point.

`data_type` is the kebab-case type ID - e.g. `"sleep"`, `"steps"`,
`"heart-rate-variability"`. See `names(GH_DATA_TYPES)` or [Providers](../platform/providers/index.md)
for the full list.

`provider` defaults to `tb_get_provider()`. Pass explicitly to override for a single
call without changing the session default.

**Token resolution (first match wins):**

1. `sleepscan = TRUE` → SleepScan API, then Clinic fallback (Withings only)
2. `token = <str>` → used directly
3. Default → TokenBridge `/token` endpoint using `user_id`

**Arguments**

| Argument | Type | Default | Description |
|---|---|---|---|
| `user_id` | character | - | TokenBridge participant ID (or SleepScan lookup key when `sleepscan = TRUE`) |
| `data_type` | character | - | Kebab-case type ID (e.g. `"sleep"`, `"steps"`) |
| `start_date` | character | - | Start of date range, `"YYYY-MM-DD"` |
| `end_date` | character | - | End of date range, `"YYYY-MM-DD"` |
| `token` | character | `NULL` | Pre-fetched access token. Pass to skip a TokenBridge round-trip when fetching multiple types for the same user |
| `provider` | character | `tb_get_provider()` | Provider ID. Overrides session default for this call only |
| `sleepscan` | logical | `NULL` | If `TRUE`, resolve token via SleepScan using `user_id` as lookup key (email, Withings user ID as integer string, or participant ID) |
| `sleepscan_key` | character | `NULL` | SleepScan API key. Falls back to `SLEEPSCAN_API_KEY` env var |
| `env_file` | character | `".env"` | Path to `.env` file |

**Returns** `data.frame` with one row per data point. Column names are the API field
names, flattened with dot notation (e.g. `startTime.seconds`).
Returns an empty `data.frame` if no data exists for the period.

**Examples**

```r
# Basic
sleep <- tb_fetch("p001", "sleep", "2026-05-01", "2026-06-18")
steps <- tb_fetch("p001", "steps", "2026-05-01", "2026-06-18")

# Token reuse - one TokenBridge call for multiple fetches
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

## Google Health (`gh_`)

### GH_DATA_TYPES

```r
GH_DATA_TYPES
```

Named character vector of all supported Google Health data type IDs.
Names are the kebab-case IDs to pass to `gh_fetch()` / `tb_fetch()`.
Values are `"list"` or `"dailyRollup"` (the endpoint type - handled automatically).

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

Full descriptions, units, and device requirements: [Providers](../platform/providers/index.md).

---

### gh_fetch

```r
gh_fetch(user_id, data_type, start_date, end_date,
         token = NULL, env_file = ".env")
```

Fetch Google Health data for a participant. Equivalent to
`tb_fetch(..., provider = "google-health")`.

This is the Google Health shorthand - it always uses the `"google-health"` provider
regardless of the session default set by `tb_set_provider()`.

Automatically handles the difference between `list` and `dailyRollup` endpoint types
based on `GH_DATA_TYPES`.

**Arguments**

| Argument | Type | Default | Description |
|---|---|---|---|
| `user_id` | character | - | TokenBridge participant ID |
| `data_type` | character | - | Kebab-case type ID. See `names(GH_DATA_TYPES)` |
| `start_date` | character | - | `"YYYY-MM-DD"` |
| `end_date` | character | - | `"YYYY-MM-DD"` |
| `token` | character | `NULL` | Pre-fetched access token (avoids a TokenBridge call) |
| `env_file` | character | `".env"` | Path to `.env` file |

**Returns** `data.frame` - one row per data point, columns depend on type.
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

### gh_data_completeness

```r
gh_data_completeness(user_ids, start_date, end_date, env_file = ".env")
```

Data completeness audit for multiple participants. Returns a `data.frame` with one row
per participant × data type - useful for checking data quality before running analysis.

**Arguments**

| Argument | Type | Default | Description |
|---|---|---|---|
| `user_ids` | character vector | - | TokenBridge participant IDs |
| `start_date` | character | - | `"YYYY-MM-DD"` |
| `end_date` | character | - | `"YYYY-MM-DD"` |
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
         token         = NULL,
         sleepscan     = NULL,
         sleepscan_key = NULL,
         env_file      = ".env")
```

Fetch Withings data for a participant. Equivalent to
`tb_fetch(..., provider = "withings")`.

**Arguments**

| Argument | Type | Default | Description |
|---|---|---|---|
| `user_id` | character | - | TokenBridge participant ID (or SleepScan lookup key when `sleepscan = TRUE`) |
| `data_type` | character | - | Withings type ID. See [Providers](../platform/providers/index.md) |
| `start_date` | character | - | `"YYYY-MM-DD"` |
| `end_date` | character | - | `"YYYY-MM-DD"` |
| `token` | character | `NULL` | Pre-fetched access token |
| `sleepscan` | logical | `NULL` | If `TRUE`, resolve token via SleepScan using `user_id` as lookup key |
| `sleepscan_key` | character | `NULL` | SleepScan API key. Falls back to `SLEEPSCAN_API_KEY` env var |
| `env_file` | character | `".env"` | Path to `.env` file |

**Returns** `data.frame` with one row per record.

**Examples**

```r
# Sleep summary with AHI
sleep <- wt_fetch("p001", "sleep-summary", "2026-06-01", "2026-07-01")
ahi   <- sleep$data.apnea_hypopnea_index   # nested 'data' sub-dict flattened

# Blood pressure
bp <- wt_fetch("p001", "blood-pressure", "2026-06-01", "2026-07-01")
# columns: grpid, date, category, systolic_bp_mmhg, diastolic_bp_mmhg

# Via SleepScan (token from SleepScan instead of TokenBridge)
sleep <- wt_fetch("p@lab.com", "sleep-summary", start, end, sleepscan = TRUE)
```

Supported type IDs: `"sleep-summary"`, `"sleep-detail"`, `"activity"`, `"workouts"`,
`"weight"`, `"height"`, `"fat-ratio"`, `"fat-mass"`, `"blood-pressure"`,
`"heart-rate"`, `"spo2"`, `"muscle-mass"`, `"bone-mass"`, `"ecg"`.
See [Providers](../platform/providers/index.md) for full details.

---

## Oura (`ou_`)

### ou_fetch

```r
ou_fetch(user_id, data_type, start_date, end_date,
         token = NULL, env_file = ".env")
```

Fetch Oura Ring data for a participant.

!!! warning
    Unlike `gh_fetch()`/`wt_fetch()`, this is **not** interchangeable with
    `tb_fetch(..., provider = "oura")` - `tb_fetch()`'s internal provider
    dispatch doesn't currently include an `"oura"` case and will error with
    `"Unknown provider 'oura'"`. Call `ou_fetch()` directly for Oura.

**Arguments**

| Argument | Type | Default | Description |
|---|---|---|---|
| `user_id` | character | - | TokenBridge participant ID |
| `data_type` | character | - | Oura type ID. See `names(OU_DATA_TYPES)` |
| `start_date` | character | - | `"YYYY-MM-DD"` |
| `end_date` | character | - | `"YYYY-MM-DD"` |
| `token` | character | `NULL` | Pre-fetched access token |
| `env_file` | character | `".env"` | Path to `.env` file |

**Returns** `data.frame` with one row per record.

**Example**

```r
sleep <- ou_fetch("p001", "daily-readiness", "2026-06-01", "2026-07-01")
```

See [Providers](../platform/providers/index.md) for the full Oura type ID list.

---

## Google Health data type IDs

Pass any of these strings as `gh_fetch()`'s/`tb_fetch()`'s `data_type` argument. See
[Providers](../platform/providers/index.md) for units, device requirements, and notes.

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
