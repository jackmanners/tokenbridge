# Google Health API v4 provider
#
# Wraps https://health.googleapis.com/v4 — uses TokenBridge for auth,
# handles pagination and client-side date filtering.
#
# You rarely need to call these functions directly.
# The canonical way is via tb_fetch() in tokenbridge.R:
#
#   tb_set_provider("google-health")              # set once (it's the default)
#   tb_fetch("p001", "sleep", start, end)
#   tb_fetch("p001", "steps", start, end)
#
# gh_fetch() is the Google-Health-specific shorthand (always uses this provider):
#
#   gh_fetch("p001", "sleep", start, end)         # equivalent to tb_fetch with provider="google-health"
#
# Token reuse (one TokenBridge call for multiple fetches):
#
#   tok <- tb_get_token("p001")
#   gh_fetch("p001", "sleep", start, end, token = tok)
#   gh_fetch("p001", "steps", start, end, token = tok)
#
# Data type IDs: see names(GH_DATA_TYPES) or docs/providers/index.md
#
# Function prefix: gh_   (Google Health)

# ── Data types reference ───────────────────────────────────────────────────────

#' All supported Google Health data type IDs
#'
#' Named character vector. Names are the kebab-case type IDs to pass to
#' gh_fetch() / tb_fetch(). Values are "list" or "dailyRollup" (the endpoint
#' type — you don't need to think about this; gh_fetch handles it automatically).
#'
#' \code{names(GH_DATA_TYPES)}  — list all type IDs
#' \code{GH_DATA_TYPES["sleep"]}  — check endpoint type for a specific ID
#'
#' Full descriptions and units: see docs/providers/index.md
#'
#' @export
GH_DATA_TYPES <- c(
  # Sleep
  "sleep"                               = "list",
  "respiratory-rate-sleep-summary"      = "list",
  "daily-sleep-temperature-derivations" = "list",
  # Activity
  "steps"                               = "list",
  "distance"                            = "list",
  "active-minutes"                      = "list",
  "active-zone-minutes"                 = "list",
  "active-energy-burned"                = "list",
  "activity-level"                      = "list",
  "sedentary-period"                    = "list",
  "altitude"                            = "list",
  "swim-lengths-data"                   = "list",
  "time-in-heart-rate-zone"             = "list",
  "exercise"                            = "list",
  "vo2-max"                             = "list",
  "run-vo2-max"                         = "list",
  "daily-vo2-max"                       = "list",
  "floors"                              = "dailyRollup",
  "total-calories"                      = "dailyRollup",
  "calories-in-heart-rate-zone"         = "dailyRollup",
  # Heart & circulation
  "heart-rate"                          = "list",
  "daily-resting-heart-rate"            = "list",
  "daily-heart-rate-zones"              = "list",
  "heart-rate-variability"              = "list",
  "daily-heart-rate-variability"        = "list",
  "electrocardiogram"                   = "list",
  "irregular-rhythm-notification"       = "list",
  # Vitals
  "oxygen-saturation"                   = "list",
  "daily-oxygen-saturation"             = "list",
  "daily-respiratory-rate"              = "list",
  "core-body-temperature"               = "list",
  "blood-glucose"                       = "list",
  # Body
  "weight"                              = "list",
  "body-fat"                            = "list",
  "height"                              = "list",
  # Nutrition
  "food"                                = "list",
  "nutrition-log"                       = "list",
  "hydration-log"                       = "list"
)

# ── Main fetch function ────────────────────────────────────────────────────────

#' Fetch Google Health data for a participant
#'
#' data_type is the kebab-case type ID — e.g. "sleep", "steps",
#' "heart-rate-variability". See \code{names(GH_DATA_TYPES)} or
#' docs/providers/index.md for the full list.
#'
#' This function is the Google-Health shorthand for tb_fetch().
#' It always uses the google-health provider regardless of tb_get_provider().
#'
#' @param user_id    TokenBridge user ID
#' @param data_type  Data type ID (kebab-case). See names(GH_DATA_TYPES).
#' @param start_date "YYYY-MM-DD"
#' @param end_date   "YYYY-MM-DD"
#' @param token      Pre-fetched access token (optional). Pass when fetching
#'   multiple types for the same user to avoid repeated TokenBridge calls.
#' @param env_file   Path to .env file (default ".env")
#' @return data.frame, one row per data point
#' @export
gh_fetch <- function(user_id, data_type, start_date, end_date,
                     token = NULL, env_file = ".env") {
  .gh_validate_dates(start_date, end_date)
  if (!data_type %in% names(GH_DATA_TYPES))
    warning("'", data_type, "' is not in GH_DATA_TYPES. ",
            "See names(GH_DATA_TYPES) or docs/providers/index.md.", call. = FALSE)
  if (is.null(token))
    token <- tb_get_token(user_id, provider = "google-health", env_file = env_file)
  if (isTRUE(GH_DATA_TYPES[[data_type]] == "dailyRollup")) {
    .gh_fetch_daily_rollup(token, data_type, start_date, end_date)
  } else {
    .gh_fetch_datapoints(token, data_type, start_date, end_date)
  }
}

# ── Analysis helpers ───────────────────────────────────────────────────────────

#' Data completeness audit for multiple participants
#'
#' Fetches each requested data type for each participant and returns a
#' data.frame with one row per participant x data type.
#' Columns: user_id, data_type, n, days_with_data, coverage_pct, error.
#'
#' @param user_ids   Character vector of TokenBridge user IDs
#' @param start_date "YYYY-MM-DD"
#' @param end_date   "YYYY-MM-DD"
#' @param data_types Character vector of data type IDs to check.
#'   Defaults to c("sleep", "steps", "heart-rate-variability").
#'   Pass any subset of names(GH_DATA_TYPES).
#' @param env_file   Path to .env file (default ".env")
#' @return data.frame
#' @export
gh_data_completeness <- function(user_ids, start_date, end_date,
                                  data_types = c("sleep", "steps", "heart-rate-variability"),
                                  env_file = ".env") {
  .gh_validate_dates(start_date, end_date)
  period_days <- as.numeric(as.Date(end_date) - as.Date(start_date)) + 1L
  rows <- list()

  for (uid in user_ids) {
    token <- tryCatch(
      tb_get_token(uid, provider = "google-health", env_file = env_file),
      error = function(e) conditionMessage(e)
    )
    if (is.character(token) && !startsWith(token, "ya29.")) {
      # token fetch failed — record error for all types
      for (dtype in data_types) {
        rows <- c(rows, list(data.frame(
          user_id = uid, data_type = dtype, n = NA_integer_,
          days_with_data = NA_integer_, coverage_pct = NA_real_,
          error = token, stringsAsFactors = FALSE
        )))
      }
      next
    }

    for (dtype in data_types) {
      result <- tryCatch({
        df   <- gh_fetch(uid, dtype, start_date, end_date, token = token, env_file = env_file)
        days <- 0L
        if (nrow(df) && "startTime.seconds" %in% names(df)) {
          ts   <- suppressWarnings(as.numeric(df[["startTime.seconds"]]))
          days <- length(unique(as.Date(as.POSIXct(ts[!is.na(ts)], origin = "1970-01-01", tz = "UTC"))))
        }
        data.frame(
          user_id        = uid,
          data_type      = dtype,
          n              = nrow(df),
          days_with_data = days,
          coverage_pct   = if (period_days > 0) round(days / period_days * 100, 1) else NA_real_,
          error          = NA_character_,
          stringsAsFactors = FALSE
        )
      }, error = function(e) {
        data.frame(user_id = uid, data_type = dtype, n = NA_integer_,
                   days_with_data = NA_integer_, coverage_pct = NA_real_,
                   error = conditionMessage(e), stringsAsFactors = FALSE)
      })
      rows <- c(rows, list(result))
    }
  }
  do.call(rbind, rows)
}

# ── Internal ───────────────────────────────────────────────────────────────────

.gh_validate_dates <- function(start_date, end_date) {
  s <- tryCatch(as.Date(start_date), error = function(e) NA)
  e <- tryCatch(as.Date(end_date),   error = function(e) NA)
  if (is.na(s) || is.na(e))
    stop("Dates must be in YYYY-MM-DD format.", call. = FALSE)
  if (s > e)
    stop("start_date (", start_date, ") must not be after end_date (", end_date, ").",
         call. = FALSE)
}

.gh_fetch_datapoints <- function(token, data_type, start_date, end_date) {
  url        <- paste0("https://health.googleapis.com/v4/users/me/dataTypes/",
                       data_type, "/dataPoints")
  all_points <- list()
  page_token <- NULL

  repeat {
    query <- list(
      pageSize  = 1000,
      startTime = paste0(start_date, "T00:00:00Z"),
      endTime   = paste0(end_date,   "T23:59:59Z")
    )
    if (!is.null(page_token)) query$pageToken <- page_token

    resp <- httr::GET(
      url,
      httr::add_headers(Authorization = paste("Bearer", token)),
      query = query,
      httr::timeout(30)
    )

    if (httr::status_code(resp) != 200) {
      warning("Google Health API error for '", data_type, "': ",
              httr::content(resp)$error$message, call. = FALSE)
      return(data.frame())
    }

    body       <- httr::content(resp)
    page_token <- body$nextPageToken
    all_points <- c(all_points, body$dataPoints)

    if (is.null(page_token) || !nchar(page_token)) break
  }

  if (!length(all_points)) return(data.frame())

  rows     <- lapply(all_points, function(p) as.list(unlist(p)))
  all_cols <- unique(unlist(lapply(rows, names)))
  do.call(rbind, lapply(rows, function(r) {
    r[setdiff(all_cols, names(r))] <- NA
    as.data.frame(r[all_cols], stringsAsFactors = FALSE, check.names = FALSE)
  }))
}

.gh_fetch_daily_rollup <- function(token, data_type, start_date, end_date) {
  url  <- paste0("https://health.googleapis.com/v4/users/me/dataTypes/",
                 data_type, "/dataPoints:dailyRollUp")
  resp <- httr::POST(
    url,
    httr::add_headers(Authorization = paste("Bearer", token),
                      `Content-Type` = "application/json"),
    body   = list(startDate = start_date, endDate = end_date),
    encode = "json",
    httr::timeout(30)
  )

  if (httr::status_code(resp) != 200) {
    warning("Google Health API error for '", data_type, "' (dailyRollup): ",
            httr::content(resp)$error$message, call. = FALSE)
    return(data.frame())
  }

  rollup <- httr::content(resp)$dailyRollup
  if (!length(rollup)) return(data.frame())

  rows     <- lapply(rollup, function(p) as.list(unlist(p)))
  all_cols <- unique(unlist(lapply(rows, names)))
  do.call(rbind, lapply(rows, function(r) {
    r[setdiff(all_cols, names(r))] <- NA
    as.data.frame(r[all_cols], stringsAsFactors = FALSE, check.names = FALSE)
  }))
}

