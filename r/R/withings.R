# Withings provider — stub
#
# Not yet implemented. The structure mirrors google_health.R so adding it
# later is straightforward: implement .wt_fetch against the Withings API
# and wire PROVIDER_ID = "withings" to the TokenBridge /token endpoint.
#
# Withings API docs: https://developer.withings.com/developer-guide/v3/
#
# Function prefix: wt_   (Withings)

#' Fetch sleep data from Withings (not yet implemented)
#' @export
wt_fetch_sleep <- function(user_id, start_date, end_date, env_file = ".env") {
  stop("Withings provider is not yet implemented.", call. = FALSE)
}

#' Fetch heart rate data from Withings (not yet implemented)
#' @export
wt_fetch_heart_rate <- function(user_id, start_date, end_date, env_file = ".env") {
  stop("Withings provider is not yet implemented.", call. = FALSE)
}

#' Generic fetch from Withings (not yet implemented)
#' @export
wt_fetch <- function(user_id, measure_type, start_date, end_date, env_file = ".env") {
  stop("Withings provider is not yet implemented.", call. = FALSE)
}
