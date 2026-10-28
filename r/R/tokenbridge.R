# TokenBridge platform client
#
# Auth-link generation and token retrieval only - this package does not wrap
# provider data APIs (see the Python package if you want that). Get a token,
# then call the provider's own API directly.
#
# Quick start:
#   library(tokenbridge)
#   tb_setup()                                       # once, to save credentials
#
#   tb_set_provider("google-health")                 # set default (optional - it's the default)
#
#   tb_auth_url("p001")                              # send link to participant
#
#   tok <- tb_get_token("p001")                      # then call the provider API yourself
#
# See the Platform docs for supported providers.
#
# Function prefix: tb_   (TokenBridge platform)

# ── Internal helpers ───────────────────────────────────────────────────────────

.tb_load_env <- function(env_file = ".env") {
  if (!file.exists(env_file)) return(invisible(NULL))
  for (line in readLines(env_file, warn = FALSE)) {
    if (grepl("^#", line) || !grepl("=", line)) next
    key <- trimws(sub("=.*",    "", line))
    val <- trimws(sub("[^=]*=", "", line))
    # strip surrounding quotes (single or double)
    val <- gsub('^["\']|["\']$', "", val)
    if (nchar(Sys.getenv(key)) == 0)
      do.call(Sys.setenv, setNames(list(val), key))
  }
}

.tb_env <- function(key) {
  val <- Sys.getenv(key)
  if (nchar(val) == 0)
    stop(key, " is not set - run tb_setup() first.", call. = FALSE)
  val
}

# Package-level environment for session state (default provider, etc.)
.tb_state <- new.env(parent = emptyenv())
.tb_state$provider <- "google-health"

# ── Provider default ───────────────────────────────────────────────────────────

#' Set the default provider for this R session
#'
#' Call once at the top of your script. All subsequent tb_auth_url(),
#' tb_auth_urls(), and tb_get_token() calls use this provider unless you
#' pass provider= explicitly. Can be changed mid-script to switch providers.
#'
#' @param provider Provider ID string, matching whatever your TokenBridge
#'   deployment has configured - e.g. "google-health", "withings", "oura".
#'   See the Platform docs for the full list for your deployment.
#' @return Invisibly returns the provider string
#' @export
tb_set_provider <- function(provider) {
  .tb_state$provider <- provider
  invisible(provider)
}

#' Get the current default provider
#'
#' @return Character string - the current default provider ID
#' @export
tb_get_provider <- function() {
  .tb_state$provider
}

# ── Setup ──────────────────────────────────────────────────────────────────────

#' Interactive setup: saves TokenBridge URL and API key to .env
#'
#' Run once before using the package. Saves credentials to an .env file
#' and loads them into the current R session.
#'
#' @param env_file Path to the .env file to write (default ".env")
#' @return Invisibly returns a list with url and api_key
#' @export
tb_setup <- function(env_file = ".env") {
  cat("\n── TokenBridge setup ────────────────────\n\n")

  default_url <- "https://YOUR_PROJECT_REF.supabase.co/functions/v1"
  url <- readline(paste0("TokenBridge URL [", default_url, "]: "))
  if (!nchar(trimws(url))) url <- default_url

  api_key <- readline("API key: ")
  if (!nchar(trimws(api_key))) stop("API key is required.", call. = FALSE)

  url     <- trimws(url)
  api_key <- trimws(api_key)

  lines <- character(0)
  if (file.exists(env_file)) {
    existing <- readLines(env_file, warn = FALSE)
    lines <- existing[!grepl("^(TOKENBRIDGE_URL|TOKENBRIDGE_API_KEY)=", existing)]
  }
  writeLines(c(lines,
               paste0("TOKENBRIDGE_URL=", url),
               paste0("TOKENBRIDGE_API_KEY=", api_key)),
             env_file)

  Sys.setenv(TOKENBRIDGE_URL = url, TOKENBRIDGE_API_KEY = api_key)

  cat("\n✓ Saved to", env_file, "\n\n")
  cat("Quick start:\n")
  cat("  tb_auth_url(\"p001\")                             # send to participant\n")
  cat("  tok <- tb_get_token(\"p001\")                      # then call the provider API yourself\n\n")
  invisible(list(url = url, api_key = api_key))
}

# ── Auth URL helpers ───────────────────────────────────────────────────────────

#' Return the auth URL for one participant to authorise their account
#'
#' Send this URL to the participant. Once they complete the OAuth flow,
#' their token is stored and you can fetch their data immediately.
#'
#' @param user_id  Unique identifier for this participant in TokenBridge
#' @param provider Health data provider. Defaults to tb_get_provider().
#' @param env_file Path to .env file (default ".env")
#' @return Character string - the auth URL
#' @export
tb_auth_url <- function(user_id, provider = tb_get_provider(), env_file = ".env") {
  .tb_load_env(env_file)
  paste0(.tb_env("TOKENBRIDGE_URL"),
         "/auth-start?provider=", provider,
         "&user_id=", user_id)
}

#' Return auth URLs for multiple participants at once
#'
#' @param user_ids Character vector of TokenBridge user IDs
#' @param provider Health data provider. Defaults to tb_get_provider().
#' @param env_file Path to .env file (default ".env")
#' @return Named character vector of auth URLs
#' @export
tb_auth_urls <- function(user_ids, provider = tb_get_provider(), env_file = ".env") {
  setNames(
    vapply(user_ids, tb_auth_url,
           FUN.VALUE = character(1),
           provider = provider, env_file = env_file),
    user_ids
  )
}

# ── Token management ───────────────────────────────────────────────────────────

#' Fetch a valid access token for a participant from TokenBridge
#'
#' TokenBridge refreshes automatically if the token is close to expiry.
#' Call the provider's own API directly with the result:
#' \code{tok <- tb_get_token("p001")}
#'
#' @param user_id  TokenBridge user ID
#' @param provider Health data provider. Defaults to tb_get_provider().
#' @param env_file Path to .env file (default ".env")
#' @return Character string - the access token
#' @export
tb_get_token <- function(user_id, provider = tb_get_provider(), env_file = ".env") {
  .tb_load_env(env_file)
  resp <- httr::POST(
    url    = paste0(.tb_env("TOKENBRIDGE_URL"), "/token"),
    httr::add_headers(Authorization = paste("Bearer", .tb_env("TOKENBRIDGE_API_KEY"))),
    body   = list(provider = provider, user_id = user_id),
    encode = "json",
    httr::timeout(15)
  )
  status <- httr::status_code(resp)
  if (status == 404) {
    auth_url <- tb_auth_url(user_id, provider = provider, env_file = env_file)
    stop("No token found for user '", user_id, "' (provider: ", provider, "). ",
         "Send them this link to authorise: ", auth_url, call. = FALSE)
  }
  if (status == 401)
    stop("Token for '", user_id, "' has expired and cannot be refreshed - ",
         "they need to re-authorise: ", tb_auth_url(user_id, provider, env_file),
         call. = FALSE)
  if (status != 200)
    stop("TokenBridge error (", status, "): ", httr::content(resp)$error, call. = FALSE)
  httr::content(resp)$access_token
}
