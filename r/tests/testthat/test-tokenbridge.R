test_that("tb_auth_url contains user_id and provider", {
  Sys.setenv(TOKENBRIDGE_URL = "https://test.supabase.co/functions/v1")
  on.exit(Sys.unsetenv("TOKENBRIDGE_URL"))

  url <- tb_auth_url("p001")
  expect_true(grepl("user_id=p001",          url))
  expect_true(grepl("provider=google-health", url))
  expect_true(grepl("auth-start",             url))
})

test_that("tb_auth_url uses custom provider", {
  Sys.setenv(TOKENBRIDGE_URL = "https://test.supabase.co/functions/v1")
  on.exit(Sys.unsetenv("TOKENBRIDGE_URL"))

  url <- tb_auth_url("p001", provider = "withings")
  expect_true(grepl("provider=withings", url))
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
    POST        = function(...) structure(mock_resp, class = "response"),
    status_code = function(r) r$status_code,
    content     = function(r, ...) r$content,
    .package    = "httr",
    {
      token <- tb_get_token("p001")
      expect_equal(token, "tok_abc123")
    }
  )
})

test_that("tb_get_token raises on 404 with auth URL in message", {
  Sys.setenv(
    TOKENBRIDGE_URL     = "https://test.supabase.co/functions/v1",
    TOKENBRIDGE_API_KEY = "test-key"
  )
  on.exit({
    Sys.unsetenv("TOKENBRIDGE_URL")
    Sys.unsetenv("TOKENBRIDGE_API_KEY")
  })

  mock_resp <- list(
    status_code = 404,
    content     = list(error = "not found")
  )

  with_mocked_bindings(
    POST        = function(...) structure(mock_resp, class = "response"),
    status_code = function(r) r$status_code,
    content     = function(r, ...) r$content,
    .package    = "httr",
    {
      expect_error(
        tb_get_token("unknown"),
        regexp = "auth-start"  # auth URL should appear in error message
      )
    }
  )
})

test_that("tb_get_token raises on 401 with re-auth message", {
  Sys.setenv(
    TOKENBRIDGE_URL     = "https://test.supabase.co/functions/v1",
    TOKENBRIDGE_API_KEY = "test-key"
  )
  on.exit({
    Sys.unsetenv("TOKENBRIDGE_URL")
    Sys.unsetenv("TOKENBRIDGE_API_KEY")
  })

  mock_resp <- list(
    status_code = 401,
    content     = list(error = "refresh failed")
  )

  with_mocked_bindings(
    POST        = function(...) structure(mock_resp, class = "response"),
    status_code = function(r) r$status_code,
    content     = function(r, ...) r$content,
    .package    = "httr",
    {
      expect_error(
        tb_get_token("p001"),
        regexp = "re-authorise|re-auth"
      )
    }
  )
})
