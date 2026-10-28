# SleepScan token source - an alternate Withings token source for
# participants registered through SleepScan rather than TokenBridge's own
# OAuth flow.
#
# Usage:
#
#   ss    <- ss_client("your-sleepscan-api-key")
#   token <- ss_get_token(ss, email = "participant@example.com")
#   # or: ss_get_token(ss, withings_user_id = 12345678L)
#   # or: ss_get_token(ss, participant_id = "SS-P001")
#
#   # Call the Withings API directly with the token
#
# Function prefix: ss_   (SleepScan)

# ── Constructor ────────────────────────────────────────────────────────────────

#' Create a SleepScan client
#'
#' @param api_key  SleepScan API key (sent as X-API-Key header).
#' @param base_url SleepScan API base URL. Defaults to \code{https://sleepscan.app/api}.
#' @return A SleepScan client object for use with \code{ss_get_token()} and \code{ss_fetch()}.
#' @export
ss_client <- function(api_key, base_url = "https://sleepscan.app/api") {
  structure(
    list(
      api_key  = api_key,
      base_url = sub("/+$", "", base_url)
    ),
    class = "SleepScanClient"
  )
}

# ── Public API ─────────────────────────────────────────────────────────────────

#' Retrieve a Withings access token via SleepScan
#'
#' Exactly one of \code{email}, \code{withings_user_id}, or \code{participant_id}
#' must be provided.
#'
#' @param client         A SleepScan client from \code{ss_client()}.
#' @param email          Participant email address.
#' @param withings_user_id Withings user ID (integer).
#' @param participant_id SleepScan participant ID.
#' @return Withings access token string.
#' @export
ss_get_token <- function(client,
                         email            = NULL,
                         withings_user_id = NULL,
                         participant_id   = NULL) {
  stopifnot(inherits(client, "SleepScanClient"))

  if (!is.null(email)) {
    url <- paste0(client$base_url, "/withings-access-token/by-email/",
                  utils::URLencode(email, reserved = TRUE))
  } else if (!is.null(withings_user_id)) {
    url <- paste0(client$base_url, "/withings-access-token/by-withings-user-id/",
                  withings_user_id)
  } else if (!is.null(participant_id)) {
    url <- paste0(client$base_url, "/withings-access-token/by-participant-id/",
                  utils::URLencode(as.character(participant_id), reserved = TRUE))
  } else {
    stop("Provide one of: email, withings_user_id, or participant_id", call. = FALSE)
  }

  resp <- httr::GET(
    url,
    httr::add_headers("X-API-Key" = client$api_key)
  )

  if (httr::status_code(resp) != 200L) {
    stop("SleepScan API error (HTTP ", httr::status_code(resp), "): ",
         httr::content(resp, as = "text", encoding = "UTF-8"),
         call. = FALSE)
  }

  body <- httr::content(resp, as = "parsed", type = "application/json")
  body$access_token
}
