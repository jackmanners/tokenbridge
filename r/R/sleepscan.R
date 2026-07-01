# SleepScan token source for TokenBridge Withings data fetching
#
# Retrieves Withings access tokens via the SleepScan API, then fetches data
# using the same Withings internals as wt_fetch().
#
# Usage:
#
#   ss <- ss_client("your-sleepscan-api-key")
#
#   # Fetch data directly
#   df <- ss_fetch(ss, "sleep-summary", "2024-01-01", "2024-03-31",
#                  email = "participant@example.com")
#   df <- ss_fetch(ss, "blood-pressure", "2024-01-01", "2024-03-31",
#                  withings_user_id = 12345678L)
#
#   # Or retrieve just the Withings token
#   token <- ss_get_token(ss, email = "participant@example.com")
#   df    <- wt_fetch("p001", "sleep-summary", "2024-01-01", "2024-03-31", token = token)
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
    url    <- paste0(client$base_url, "/token/by-email")
    params <- list(email = email)
  } else if (!is.null(withings_user_id)) {
    url    <- paste0(client$base_url, "/token/by-withings-id")
    params <- list(withings_user_id = withings_user_id)
  } else if (!is.null(participant_id)) {
    url    <- paste0(client$base_url, "/token/by-participant")
    params <- list(participant_id = participant_id)
  } else {
    stop("Provide one of: email, withings_user_id, or participant_id", call. = FALSE)
  }

  resp <- httr::GET(
    url,
    httr::add_headers("X-API-Key" = client$api_key),
    query = params
  )

  if (httr::status_code(resp) != 200L) {
    stop("SleepScan API error (HTTP ", httr::status_code(resp), "): ",
         httr::content(resp, as = "text", encoding = "UTF-8"),
         call. = FALSE)
  }

  body <- httr::content(resp, as = "parsed", type = "application/json")
  body$access_token
}

#' Fetch Withings data using a SleepScan-managed token
#'
#' Retrieves a Withings access token from SleepScan then calls the Withings
#' API directly. Returns the same data frame as \code{wt_fetch()}.
#'
#' Exactly one of \code{email}, \code{withings_user_id}, or \code{participant_id}
#' must be provided.
#'
#' @param client         A SleepScan client from \code{ss_client()}.
#' @param data_type      Withings data type ID (see \code{names(WT_DATA_TYPES)}).
#' @param start_date     "YYYY-MM-DD"
#' @param end_date       "YYYY-MM-DD"
#' @param email          Participant email address.
#' @param withings_user_id Withings user ID (integer).
#' @param participant_id SleepScan participant ID.
#' @return data.frame, one row per record.
#' @export
ss_fetch <- function(client,
                     data_type,
                     start_date,
                     end_date,
                     email            = NULL,
                     withings_user_id = NULL,
                     participant_id   = NULL) {
  stopifnot(inherits(client, "SleepScanClient"))

  if (!data_type %in% names(WT_DATA_TYPES)) {
    stop(
      "Unknown Withings data type: ", shQuote(data_type),
      ". Available: ", paste(names(WT_DATA_TYPES), collapse = ", "),
      call. = FALSE
    )
  }

  .wt_validate_dates(start_date, end_date)

  token <- ss_get_token(
    client,
    email            = email,
    withings_user_id = withings_user_id,
    participant_id   = participant_id
  )

  .wt_fetch_all(token, data_type, start_date, end_date)
}
