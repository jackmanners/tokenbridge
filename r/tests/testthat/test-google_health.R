# Helpers
.mock_gh_response <- function(points = list(), next_page = NULL) {
  body <- list(dataPoints = points)
  if (!is.null(next_page)) body$nextPageToken <- next_page
  structure(
    list(status_code = 200, content = body),
    class = "response"
  )
}

.make_point <- function(start_s, end_s) {
  list(
    startTime = list(seconds = as.character(start_s), nanos = 0),
    endTime   = list(seconds = as.character(end_s),   nanos = 0)
  )
}

# ── Date validation ───────────────────────────────────────────────────────────

test_that(".gh_validate_dates rejects bad format", {
  expect_error(.gh_validate_dates("01-05-2026", "2026-05-31"), regexp = "YYYY-MM-DD")
})

test_that(".gh_validate_dates rejects end before start", {
  expect_error(.gh_validate_dates("2026-06-01", "2026-05-01"), regexp = "start_date|before")
})

test_that(".gh_validate_dates accepts same-day range", {
  expect_silent(.gh_validate_dates("2026-05-01", "2026-05-01"))
})

test_that(".gh_validate_dates accepts valid range", {
  expect_silent(.gh_validate_dates("2026-05-01", "2026-05-31"))
})

# ── gh_fetch ──────────────────────────────────────────────────────────────────

test_that("gh_fetch returns data.frame", {
  start_s <- as.numeric(as.POSIXct("2026-05-10 00:00:00", tz = "UTC"))

  with_mocked_bindings(
    GET         = function(...) .mock_gh_response(list(.make_point(start_s, start_s + 28800))),
    status_code = function(r, ...) r$status_code,
    content     = function(r, ...) r$content,
    .package    = "httr",
    {
      df <- gh_fetch("p001", "sleep", "2026-05-01", "2026-05-31", token = "tok_test")
      expect_s3_class(df, "data.frame")
      expect_equal(nrow(df), 1L)
    }
  )
})

test_that("gh_fetch returns empty data.frame when no data", {
  with_mocked_bindings(
    GET         = function(...) .mock_gh_response(),
    status_code = function(r, ...) r$status_code,
    content     = function(r, ...) r$content,
    .package    = "httr",
    {
      df <- gh_fetch("p001", "sleep", "2026-05-01", "2026-05-31", token = "tok_test")
      expect_s3_class(df, "data.frame")
      expect_equal(nrow(df), 0L)
    }
  )
})

test_that("gh_fetch raises on bad date format", {
  expect_error(
    gh_fetch("p001", "sleep", "not-a-date", "2026-05-31", token = "tok_test"),
    regexp = "YYYY-MM-DD"
  )
})

test_that("gh_fetch raises when end before start", {
  expect_error(
    gh_fetch("p001", "sleep", "2026-06-01", "2026-05-01", token = "tok_test"),
    regexp = "start_date|before"
  )
})

# ── gh_data_completeness ──────────────────────────────────────────────────────

test_that("gh_data_completeness returns data.frame with expected columns", {
  with_mocked_bindings(
    GET         = function(...) .mock_gh_response(),
    status_code = function(r, ...) r$status_code,
    content     = function(r, ...) r$content,
    .package    = "httr",
    {
      with_mocked_bindings(
        tb_get_token = function(...) "tok_test",
        {
          df <- gh_data_completeness(c("p001", "p002"), "2026-05-01", "2026-05-31")
          expect_s3_class(df, "data.frame")
          expect_true(all(c("user_id", "data_type", "n", "coverage_pct") %in% names(df)))
          # default 3 types × 2 users = 6 rows
          expect_equal(nrow(df), 6L)
        }
      )
    }
  )
})

test_that("gh_data_completeness respects custom data_types", {
  with_mocked_bindings(
    GET         = function(...) .mock_gh_response(),
    status_code = function(r, ...) r$status_code,
    content     = function(r, ...) r$content,
    .package    = "httr",
    {
      with_mocked_bindings(
        tb_get_token = function(...) "tok_test",
        {
          df <- gh_data_completeness(
            c("p001", "p002"), "2026-05-01", "2026-05-31",
            data_types = c("sleep", "steps")
          )
          expect_equal(nrow(df), 4L)  # 2 users × 2 types
          expect_true(all(df$data_type %in% c("sleep", "steps")))
        }
      )
    }
  )
})
