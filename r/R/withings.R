# Withings provider — stub
#
# Auth is wired (the edge functions handle the OAuth flow).
# Data fetching is not yet implemented.
#
# Withings API: https://developer.withings.com/developer-guide/v3/

#' Fetch Withings data for a participant (not yet implemented)
#'
#' @param user_id    TokenBridge user ID
#' @param data_type  Data type ID
#' @param start_date "YYYY-MM-DD"
#' @param end_date   "YYYY-MM-DD"
#' @param token      Pre-fetched access token (optional)
#' @param env_file   Path to .env file (default ".env")
#' @export
wt_fetch <- function(user_id, data_type, start_date, end_date,
                     token = NULL, env_file = ".env") {
  stop("Withings data fetching is not yet implemented.", call. = FALSE)
}
