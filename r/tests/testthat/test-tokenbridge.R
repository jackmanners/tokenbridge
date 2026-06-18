test_that("tb_auth_url contains user_id and provider", {
  # Set env vars directly so tb_auth_url doesn't need a .env file
  Sys.setenv(TOKENBRIDGE_URL = "https://test.supabase.co/functions/v1")
  on.exit(Sys.unsetenv("TOKENBRIDGE_URL"))

  url <- tb_auth_url("p001")
  expect_true(grepl("user_id=p001",        url))
  expect_true(grepl("provider=google-health", url))
  expect_true(grepl("auth-start",           url))
})

test_that("tb_auth_urls returns named character vector", {
  Sys.setenv(TOKENBRIDGE_URL = "https://test.supabase.co/functions/v1")
  on.exit(Sys.unsetenv("TOKENBRIDGE_URL"))

  urls <- tb_auth_urls(c("p001", "p002"))
  expect_equal(names(urls), c("p001", "p002"))
  expect_true(grepl("p001", urls["p001"]))
  expect_true(grepl("p002", urls["p002"]))
})

test_that("tb_setup writes to env file", {
  tmp <- tempfile(fileext = ".env")
  on.exit(unlink(tmp))

  # Simulate user input
  with_mocked_bindings(
    readline = function(prompt = "") {
      if (grepl("URL",     prompt)) return("https://custom.supabase.co/functions/v1")
      if (grepl("API key", prompt)) return("my-secret-key")
      return("")
    },
    {
      tb_setup(env_file = tmp)
    }
  )

  lines <- readLines(tmp)
  expect_true(any(grepl("TOKENBRIDGE_URL=https://custom", lines)))
  expect_true(any(grepl("TOKENBRIDGE_API_KEY=my-secret-key", lines)))
})

test_that("tb_get_token returns access token on success", {
  Sys.setenv(
    TOKENBRIDGE_URL     = "https://test.supabase.co/functions/v1",
    TOKENBRIDGE_API_KEY = "test-key"
  )
  on.exit({
    Sys.unsetenv("TOKENBRIDGE_URL")
    Sys.unsetenv("TOKENBRIDGE_API_KEY")
  })

  mock_resp <- list(
    status_code = 200,
    content     = list(access_token = "tok_abc123")
  )

  with_mocked_bindings(
    POST = function(...) {
      structure(mock_resp, class = "response")
    },
    status_code = function(r) r$status_code,
    content     = function(r, ...) r$content,
    .package    = "httr",
    {
      token <- tb_get_token("p001")
      expect_equal(token, "tok_abc123")
    }
  )
})

test_that("tb_token_status returns metadata without raw token", {
  Sys.setenv(
    TOKENBRIDGE_URL     = "https://test.supabase.co/functions/v1",
    TOKENBRIDGE_API_KEY = "test-key"
  )
  on.exit({
    Sys.unsetenv("TOKENBRIDGE_URL")
    Sys.unsetenv("TOKENBRIDGE_API_KEY")
  })

  mock_resp <- list(
    status_code = 200,
    content     = list(
      access_token = "tok_abc123",
      expires_at   = "2026-06-19T00:00:00Z",
      refreshed    = FALSE
    )
  )

  with_mocked_bindings(
    POST        = function(...) structure(mock_resp, class = "response"),
    status_code = function(r) r$status_code,
    content     = function(r, ...) r$content,
    .package    = "httr",
    {
      status <- tb_token_status("p001")
      expect_true("expires_at" %in% names(status))
      expect_true("refreshed"  %in% names(status))
      expect_false("access_token" %in% names(status))
    }
  )
})
