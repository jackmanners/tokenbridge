# Oura Ring API v2 provider
#
# Wraps https://api.ouraring.com/v2 — uses TokenBridge for auth,
# handles cursor-based pagination internally.
#
# Usage:
#
#   tb_set_provider("oura")
#   tb_fetch("p001", "sleep", start, end)          # canonical
#
#   ou_fetch("p001", "daily-activity", start, end)  # Oura shorthand
#
#   tok <- tb_get_token("p001", provider = "oura")
#   ou_fetch("p001", "sleep",           start, end, token = tok)
#   ou_fetch("p001", "daily-readiness", start, end, token = tok)
#
# Data type IDs: see names(OU_DATA_TYPES) or docs/providers/index.md
#
# Function prefix: ou_   (Oura)

# ── Data types reference ───────────────────────────────────────────────────────

#' All supported Oura data type IDs
#'
#' Named list describing the API path and date parameter format for each type.
#' Use \code{names(OU_DATA_TYPES)} to list all available type IDs.
#'
#' Full descriptions and field details: see
#' \url{https://cloud.ouraring.com/v2/docs}
#'
#' @export
OU_DATA_TYPES <- list(
  # Daily summaries
  "daily-activity"     = list(path = "daily_activity",           date_fmt = "date"),
  "daily-sleep"        = list(path = "daily_sleep",              date_fmt = "date"),
  "daily-readiness"    = list(path = "daily_readiness",          date_fmt = "date"),
  "daily-stress"       = list(path = "daily_stress",             date_fmt = "date"),
  "daily-spo2"         = list(path = "daily_spo2",               date_fmt = "date"),
  "daily-resilience"   = list(path = "daily_resilience",         date_fmt = "date"),
  "cardiovascular-age" = list(path = "daily_cardiovascular_age", date_fmt = "date"),
  # Detailed sessions
  "sleep"              = list(path = "sleep",                    date_fmt = "date"),
  "sleep-time"         = list(path = "sleep_time",               date_fmt = "date"),
  "workout"            = list(path = "workout",                  date_fmt = "date"),
  "session"            = list(path = "session",                  date_fmt = "date"),
  # Continuous streams
  "heartrate"          = list(path = "heartrate",                date_fmt = "datetime"),
  # Other
  "vo2-max"            = list(path = "vO2_max",                  date_fmt = "date"),
  "tag"                = list(path = "tag",                      date_fmt = "date"),
  "enhanced-tag"       = list(path = "enhanced_tag",             date_fmt = "date")
)

# ── Public API ─────────────────────────────────────────────────────────────────

#' Fetch Oura Ring data for a participant
#'
#' @param user_id    TokenBridge user ID
#' @param data_type  Data type ID (see \code{names(OU_DATA_TYPES)})
#' @param start_date "YYYY-MM-DD"
#' @param end_date   "YYYY-MM-DD"
#' @param token      Pre-fetched access token (skips TokenBridge round-trip)
#' @param env_file   Path to .env file (default ".env")
#' @return data.frame, one row per record
#' @export
ou_fetch <- function(user_id, data_type, start_date, end_date,
                     token = NULL, env_file = ".env") {
  .ou_validate_dates(start_date, end_date)

  if (!data_type %in% names(OU_DATA_TYPES)) {
    stop(
      "Unknown Oura data type: ", shQuote(data_type),
      ". Available: ", paste(names(OU_DATA_TYPES), collapse = ", "),
      call. = FALSE
    )
  }

  if (is.null(token)) {
    token <- tb_get_token(user_id, provider = "oura", env_file = env_file)
  }

  .ou_fetch_all(token, data_type, start_date, end_date)
}

# ── Internal ───────────────────────────────────────────────────────────────────

.ou_validate_dates <- function(start_date, end_date) {
  fmt <- "%Y-%m-%d"
  s <- tryCatch(as.Date(start_date, format = fmt), warning = function(w) NA)
  e <- tryCatch(as.Date(end_date,   format = fmt), warning = function(w) NA)

  if (is.na(s) || is.na(e) ||
      format(s, fmt) != start_date || format(e, fmt) != end_date) {
    stop("Dates must be YYYY-MM-DD format, got: ",
         shQuote(start_date), ", ", shQuote(end_date), call. = FALSE)
  }
  if (s > e) {
    stop("start_date (", start_date, ") must not be after end_date (", end_date, ")",
         call. = FALSE)
  }
}

.ou_to_iso_datetime <- function(date_str, end_of_day = FALSE) {
  d <- as.POSIXct(date_str, tz = "UTC")
  if (end_of_day) d <- d + 86399L
  format(d, "%Y-%m-%dT%H:%M:%S+00:00")
}

.ou_fetch_all <- function(token, data_type, start_date, end_date) {
  spec    <- OU_DATA_TYPES[[data_type]]
  url     <- paste0("https://api.ouraring.com/v2/usercollection/", spec$path)
  headers <- httr::add_headers(Authorization = paste("Bearer", token))

  if (spec$date_fmt == "datetime") {
    date_params <- list(
      start_datetime = .ou_to_iso_datetime(start_date),
      end_datetime   = .ou_to_iso_datetime(end_date, end_of_day = TRUE)
    )
  } else {
    date_params <- list(start_date = start_date, end_date = end_date)
  }

  all_records <- list()
  next_token  <- NULL

  repeat {
    params <- date_params
    if (!is.null(next_token)) params$next_token <- next_token

    resp <- httr::GET(url, headers, query = params)

    if (httr::status_code(resp) != 200L) {
      stop("Oura API HTTP error: ", httr::status_code(resp), call. = FALSE)
    }

    body        <- httr::content(resp, as = "parsed", type = "application/json")
    records     <- body$data %||% list()
    all_records <- c(all_records, records)
    next_token  <- body$next_token

    if (is.null(next_token)) break
  }

  if (length(all_records) == 0L) return(data.frame())

  as.data.frame(
    do.call(rbind, lapply(all_records, function(r) {
      as.data.frame(lapply(r, function(v) if (length(v) == 1) v else list(v)),
                    stringsAsFactors = FALSE)
    })),
    stringsAsFactors = FALSE
  )
}

`%||%` <- function(a, b) if (!is.null(a)) a else b
