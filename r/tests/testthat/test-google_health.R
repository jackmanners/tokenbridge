# Helper — build a minimal Google Health API response
.mock_gh_response <- function(points = list(), next_page = NULL) {
  body <- list(dataPoints = points)
  if (!is.null(next_page)) body$nextPageToken <- next_page
  structure(
    list(status_code = 200, content = body),
    class = "response"
  )
}

.make_point <- function(start_s, end_s, extra = list()) {
  pt <- list(
    startTime = list(seconds = as.character(start_s), nanos = 0),
    endTime   = list(seconds = as.character(end_s),   nanos = 0)
  )
  c(pt, extra)
}

test_that("gh_fetch_sleep returns data.frame", {
  start_s <- as.numeric(as.POSIXct("2026-05-10 00:00:00", tz = "UTC"))

  with_mocked_bindings(
    GET         = function(...) .mock_gh_response(list(.make_point(start_s, start_s + 28800))),
    status_code = function(r, ...) r$status_code,
    content     = function(r, ...) r$content,
    .package    = "httr",
    {
      df <- gh_fetch_sleep("p001", "2026-05-01", "2026-05-31",
                           token = "tok_test")
      expect_s3_class(df, "data.frame")
      expect_equal(nrow(df), 1L)
    }
  )
})

test_that("gh_fetch_sleep returns empty data.frame when no data", {
  with_mocked_bindings(
    GET         = function(...) .mock_gh_response(),
    status_code = function(r, ...) r$status_code,
    content     = function(r, ...) r$content,
    .package    = "httr",
    {
      df <- gh_fetch_sleep("p001", "2026-05-01", "2026-05-31",
                           token = "tok_test")
      expect_s3_class(df, "data.frame")
      expect_equal(nrow(df), 0L)
    }
  )
})

test_that("gh_fetch filters points outside study window", {
  inside  <- as.numeric(as.POSIXct("2026-05-10 00:00:00", tz = "UTC"))
  outside <- as.numeric(as.POSIXct("2026-03-01 00:00:00", tz = "UTC"))

  with_mocked_bindings(
    GET = function(...) .mock_gh_response(list(
      .make_point(inside,  inside  + 3600),
      .make_point(outside, outside + 3600)
    )),
    status_code = function(r, ...) r$status_code,
    content     = function(r, ...) r$content,
    .package    = "httr",
    {
      df <- gh_fetch("p001", "sleep", "2026-05-01", "2026-05-31",
                     token = "tok_test")
      expect_equal(nrow(df), 1L)
    }
  )
})

test_that("gh_summary returns expected structure", {
  with_mocked_bindings(
    GET         = function(...) .mock_gh_response(),
    status_code = function(r, ...) r$status_code,
    content     = function(r, ...) r$content,
    .package    = "httr",
    {
      # Mock tb_get_token so we don't need real credentials
      with_mocked_bindings(
        tb_get_token = function(...) "tok_test",
        {
          s <- gh_summary("p001", "2026-05-01", "2026-05-31")
          expect_true("sleep"            %in% names(s))
          expect_true("respiratory_rate" %in% names(s))
          expect_equal(s$period_days, 31L)
          expect_equal(s$sleep$n, 0L)
          expect_equal(s$sleep$coverage_pct, 0)
        }
      )
    }
  )
})

test_that("gh_data_completeness returns data.frame with expected columns", {
  with_mocked_bindings(
    gh_summary = function(uid, ...) list(
      user_id      = uid,
      period_days  = 31L,
      sleep        = list(n = 5L, days_with_data = 5L, coverage_pct = 16.1),
      respiratory_rate = list(n = 4L, days_with_data = 4L, coverage_pct = 12.9)
    ),
    {
      df <- gh_data_completeness(c("p001", "p002"), "2026-05-01", "2026-05-31")
      expect_s3_class(df, "data.frame")
      expect_true(all(c("user_id", "data_type", "n", "coverage_pct") %in% names(df)))
      expect_equal(nrow(df), 4L)  # 2 users × 2 data types
    }
  )
})
