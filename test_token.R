# test_token.R - personal dev script, not intended for end users.
#
# Checks that tokens are valid and data is fetchable for both Google Health
# and Withings providers. Prints a brief summary per provider.
#
# Requires the R package to be installed:
#   devtools::install_local("r", force = TRUE)
#
# Set TOKENBRIDGE_URL and TOKENBRIDGE_API_KEY in .env before running.

library(tokenbridge)

USER_ID <- "jackmanners"
END     <- format(Sys.Date(), "%Y-%m-%d")
START   <- format(Sys.Date() - 7, "%Y-%m-%d")

cat("TokenBridge:", Sys.getenv("TOKENBRIDGE_URL"), "\n")
cat("User:       ", USER_ID, "\n")
cat("Window:     ", START, "→", END, "\n\n")

checks <- list(
  list(provider = "google-health", data_type = "sleep"),
  list(provider = "withings",      data_type = "sleep-summary")
)

for (check in checks) {
  provider  <- check$provider
  data_type <- check$data_type

  tryCatch({
    tb_set_provider(provider)
    records <- tb_fetch(USER_ID, data_type, START, END)
    n       <- nrow(records)
    cat(sprintf("[OK]   %-20s  %d records\n", provider, n))

    if (n > 0) {
      if (provider == "withings") {
        latest <- records[which.max(records$startdate), ]
        start  <- format(as.POSIXct(latest$startdate, origin = "1970-01-01", tz = "UTC"), "%Y-%m-%d %H:%M")
        end    <- format(as.POSIXct(latest$enddate,   origin = "1970-01-01", tz = "UTC"), "%Y-%m-%d %H:%M")
        mins   <- latest$data[[1]]$total_sleep_time
        ahi    <- latest$data[[1]]$apnea_hypopnea_index
        cat(sprintf("       latest:   %s → %s\n", start, end))
        cat(sprintf("       asleep:   %s   AHI: %s\n",
                    if (!is.null(mins) && !is.na(mins))
                      sprintf("%dh %dm", mins %/% 3600L, (mins %% 3600L) %/% 60L)
                    else "n/a",
                    if (!is.null(ahi) && !is.na(ahi)) ahi else "n/a"))
      } else {
        latest <- records[which.max(records[["sleep.interval.endTime"]]), ]
        start  <- latest[["sleep.interval.startTime"]]
        end    <- latest[["sleep.interval.endTime"]]
        mins   <- suppressWarnings(as.integer(latest[["sleep.summary.minutesAsleep"]]))
        cat(sprintf("       latest:   %s → %s\n", start, end))
        cat(sprintf("       asleep:   %s\n",
                    if (!is.na(mins)) sprintf("%dh %dm", mins %/% 60L, mins %% 60L)
                    else "n/a"))
      }
    }

  }, error = function(e) {
    cat(sprintf("[FAIL] %-20s  %s\n", provider, conditionMessage(e)))
  })

  cat("\n")
}
