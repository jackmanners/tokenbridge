# Withings API provider
#
# Wraps https://wbsapi.withings.net/ - uses TokenBridge for auth,
# handles pagination and date conversion internally.
#
# Usage:
#
#   tb_set_provider("withings")
#   tb_fetch("p001", "sleep-summary", start, end)   # canonical
#
#   wt_fetch("p001", "activity", start, end)         # Withings shorthand
#
#   tok <- tb_get_token("p001", provider = "withings")
#   wt_fetch("p001", "sleep-summary", start, end, token = tok)
#   wt_fetch("p001", "weight",        start, end, token = tok)
#
# Data type IDs: see names(WT_DATA_TYPES) or docs/providers/index.md
#
# Function prefix: wt_   (Withings)

# ── Data types reference ───────────────────────────────────────────────────────

#' All supported Withings data type IDs
#'
#' Named list describing fetch configuration for each type.
#' Use \code{names(WT_DATA_TYPES)} to list all available type IDs.
#'
#' Full descriptions and field details: see
#' \url{https://developer.withings.com/api-reference/}
#'
#' @export
#  Withings only returns a minimal default field set unless data_fields is
#  explicitly passed - full lists per endpoint (v2/sleep API reference), so
#  sleep-summary/sleep-detail return every available metric rather than
#  silently omitting AHI, HRV, respiration rate, etc.
.WT_SLEEP_GET_FIELDS <- paste(c(
  "hr", "rr", "snoring", "sdnn_1", "rmssd", "hrv_quality", "mvt_score",
  "chest_movement_rate", "withings_index", "breathing_sounds"
), collapse = ",")

.WT_SLEEP_SUMMARY_FIELDS <- paste(c(
  "total_timeinbed", "total_sleep_time", "asleepduration", "lightsleepduration",
  "remsleepduration", "deepsleepduration", "sleep_efficiency", "sleep_latency",
  "wakeup_latency", "wakeupduration", "wakeupcount", "waso", "nb_rem_episodes",
  "breathing_disturbances_intensity", "apnea_hypopnea_index", "withings_index",
  "durationtosleep", "durationtowakeup", "out_of_bed_count", "hr_average", "hr_min",
  "hr_max", "rr_average", "rr_min", "rr_max", "breathing_quality_assessment", "snoring",
  "snoringepisodecount", "sleep_score", "night_events", "mvt_score_avg",
  "mvt_active_duration", "rmssd_start_avg", "rmssd_end_avg",
  "chest_movement_rate_wellness_average", "chest_movement_rate_wellness_min",
  "chest_movement_rate_wellness_max", "breathing_sounds",
  "breathing_sounds_episode_count", "chest_movement_rate_average",
  "chest_movement_rate_min", "chest_movement_rate_max",
  "core_body_temperature_min", "core_body_temperature_max",
  "core_body_temperature_avg", "core_body_temperature_status"
), collapse = ",")

WT_DATA_TYPES <- list(
  # Sleep
  "sleep-summary" = list(endpoint = "/v2/sleep",   action = "getsummary", date_fmt = "ymd",  result_key = "series", data_fields = .WT_SLEEP_SUMMARY_FIELDS),
  "sleep-detail"  = list(endpoint = "/v2/sleep",   action = "get",        date_fmt = "unix", result_key = "series", data_fields = .WT_SLEEP_GET_FIELDS),
  # Activity
  "activity"      = list(endpoint = "/v2/measure", action = "getactivity",date_fmt = "ymd",  result_key = "activities"),
  "workouts"      = list(endpoint = "/v2/measure", action = "getworkouts",date_fmt = "ymd",  result_key = "series"),
  # Body measurements (via /measure getmeas)
  "weight"         = list(endpoint = "/measure", action = "getmeas", date_fmt = "unix", result_key = "measuregrps", meastype = 1L),
  "height"         = list(endpoint = "/measure", action = "getmeas", date_fmt = "unix", result_key = "measuregrps", meastype = 4L),
  "fat-ratio"      = list(endpoint = "/measure", action = "getmeas", date_fmt = "unix", result_key = "measuregrps", meastype = 6L),
  "fat-mass"       = list(endpoint = "/measure", action = "getmeas", date_fmt = "unix", result_key = "measuregrps", meastype = 8L),
  "blood-pressure" = list(endpoint = "/measure", action = "getmeas", date_fmt = "unix", result_key = "measuregrps", meastypes = "9,10"),
  "heart-rate"     = list(endpoint = "/measure", action = "getmeas", date_fmt = "unix", result_key = "measuregrps", meastype = 11L),
  "spo2"           = list(endpoint = "/measure", action = "getmeas", date_fmt = "unix", result_key = "measuregrps", meastype = 54L),
  "muscle-mass"    = list(endpoint = "/measure", action = "getmeas", date_fmt = "unix", result_key = "measuregrps", meastype = 76L),
  "bone-mass"      = list(endpoint = "/measure", action = "getmeas", date_fmt = "unix", result_key = "measuregrps", meastype = 88L),
  # ECG
  "ecg"           = list(endpoint = "/v2/heart", action = "list", date_fmt = "unix", result_key = "series")
)

# Human-readable labels for measure types (used in decode step)
.WT_MEASTYPE_LABELS <- c(
  "1"  = "weight_kg",
  "4"  = "height_m",
  "5"  = "fat_free_mass_kg",
  "6"  = "fat_ratio_pct",
  "8"  = "fat_mass_kg",
  "9"  = "diastolic_bp_mmhg",
  "10" = "systolic_bp_mmhg",
  "11" = "heart_rate_bpm",
  "12" = "temperature_c",
  "54" = "spo2_pct",
  "76" = "muscle_mass_kg",
  "88" = "bone_mass_kg"
)

# ── Public API ─────────────────────────────────────────────────────────────────

#' Fetch Withings data for a participant
#'
#' @param user_id    TokenBridge user ID
#' @param data_type  Data type ID (see \code{names(WT_DATA_TYPES)})
#' @param start_date "YYYY-MM-DD"
#' @param end_date   "YYYY-MM-DD"
#' @param token      Pre-fetched access token (skips TokenBridge round-trip)
#' @param sleepscan  If \code{TRUE}, resolve the Withings token via SleepScan using
#'   \code{user_id} as the lookup key (email, Withings user ID as integer, or
#'   SleepScan participant ID). Takes priority over \code{token=}.
#'   Requires \code{SLEEPSCAN_API_KEY} in the environment or \code{sleepscan_key=}.
#' @param sleepscan_key  SleepScan API key. Falls back to \code{SLEEPSCAN_API_KEY} env var.
#' @param env_file   Path to .env file (default ".env")
#' @return data.frame, one row per record
#' @export
wt_fetch <- function(user_id, data_type, start_date, end_date,
                     token         = NULL,
                     sleepscan     = NULL,
                     sleepscan_key = NULL,
                     env_file      = ".env") {
  .wt_validate_dates(start_date, end_date)

  if (!data_type %in% names(WT_DATA_TYPES)) {
    stop(
      "Unknown Withings data type: ", shQuote(data_type),
      ". Available: ", paste(names(WT_DATA_TYPES), collapse = ", "),
      call. = FALSE
    )
  }

  if (isTRUE(sleepscan)) {
    token <- .wt_sleepscan_token(user_id, sleepscan_key)
  } else if (is.null(token)) {
    token <- tb_get_token(user_id, provider = "withings", env_file = env_file)
  }

  .wt_fetch_all(token, data_type, start_date, end_date)
}

# ── Internal ───────────────────────────────────────────────────────────────────

.wt_sleepscan_token <- function(sleepscan, sleepscan_key = NULL) {
  key <- sleepscan_key %||% Sys.getenv("SLEEPSCAN_API_KEY")
  if (!nchar(key))
    stop("sleepscan= requires SLEEPSCAN_API_KEY in environment or sleepscan_key= argument.",
         call. = FALSE)
  client <- ss_client(key)
  if (is.numeric(sleepscan)) {
    ss_get_token(client, withings_user_id = as.integer(sleepscan))
  } else if (grepl("@", sleepscan, fixed = TRUE)) {
    ss_get_token(client, email = sleepscan)
  } else {
    ss_get_token(client, participant_id = sleepscan)
  }
}

.wt_validate_dates <- function(start_date, end_date) {
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

.wt_to_unix <- function(date_str, end_of_day = FALSE) {
  d <- as.POSIXct(date_str, tz = "UTC")
  if (end_of_day) d <- d + 86399L  # 23:59:59
  as.integer(d)
}

.wt_decode_measuregrps <- function(grps) {
  rows <- lapply(grps, function(grp) {
    row <- list(
      grpid    = grp$grpid,
      date     = grp$date,
      category = grp$category
    )
    for (m in grp$measures) {
      actual_val <- m$value * (10 ^ m$unit)
      col <- .WT_MEASTYPE_LABELS[as.character(m$type)]
      col <- if (is.na(col)) paste0("type_", m$type) else col
      row[[col]] <- round(actual_val, 6)
    }
    row
  })
  if (length(rows) == 0L) return(data.frame())
  do.call(dplyr_bind_rows_fallback, list(rows))
}

# Fallback row-binder that doesn't require dplyr
dplyr_bind_rows_fallback <- function(rows) {
  all_keys <- unique(unlist(lapply(rows, names)))
  mat <- lapply(rows, function(r) {
    lapply(setNames(all_keys, all_keys), function(k) {
      if (!is.null(r[[k]])) r[[k]] else NA
    })
  })
  as.data.frame(do.call(rbind, lapply(mat, as.data.frame, stringsAsFactors = FALSE)),
                stringsAsFactors = FALSE)
}

.wt_fetch_all <- function(token, data_type, start_date, end_date) {
  spec       <- WT_DATA_TYPES[[data_type]]
  base_url   <- "https://wbsapi.withings.net"
  url        <- paste0(base_url, spec$endpoint)
  result_key <- spec$result_key
  headers    <- httr::add_headers(Authorization = paste("Bearer", token))

  # Date params
  if (spec$date_fmt == "ymd") {
    date_params <- list(startdateymd = start_date, enddateymd = end_date)
  } else {
    date_params <- list(
      startdate = .wt_to_unix(start_date),
      enddate   = .wt_to_unix(end_date, end_of_day = TRUE)
    )
  }

  # Extra params (meastype / meastypes for getmeas, data_fields for sleep)
  extra <- list()
  if (!is.null(spec$meastype))    extra$meastype    <- spec$meastype
  if (!is.null(spec$meastypes))   extra$meastypes   <- spec$meastypes
  if (!is.null(spec$data_fields)) extra$data_fields <- spec$data_fields

  all_records <- list()
  offset      <- NULL

  repeat {
    params <- c(list(action = spec$action), date_params, extra)
    if (!is.null(offset)) params$offset <- offset

    resp <- httr::GET(url, headers, query = params)

    if (httr::status_code(resp) != 200L) {
      stop("Withings API HTTP error: ", httr::status_code(resp), call. = FALSE)
    }

    body <- httr::content(resp, as = "parsed", type = "application/json")

    wt_status <- body$status %||% -1L
    if (wt_status != 0L) {
      stop("Withings API error (status ", wt_status, "): ",
           body$error %||% "unknown", call. = FALSE)
    }

    data <- body$body
    page_records <- data[[result_key]] %||% list()

    if (result_key == "measuregrps") {
      decoded <- .wt_decode_measuregrps(page_records)
      all_records <- c(all_records, list(decoded))
    } else {
      all_records <- c(all_records, page_records)
    }

    if (isTRUE(data$more)) {
      offset <- data$offset
    } else {
      break
    }
  }

  if (length(all_records) == 0L) return(data.frame())

  if (result_key == "measuregrps") {
    do.call(rbind, all_records)
  } else {
    as.data.frame(
      do.call(rbind, lapply(all_records, function(r) {
        as.data.frame(lapply(r, function(v) if (length(v) == 1) v else list(v)),
                      stringsAsFactors = FALSE)
      })),
      stringsAsFactors = FALSE
    )
  }
}

# Null-coalescing operator (if not already defined)
`%||%` <- function(a, b) if (!is.null(a)) a else b
