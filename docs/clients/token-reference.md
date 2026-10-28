# Token API Reference

The interface every client library shares: generate a signed auth link, retrieve a token. This is the whole of the JavaScript package, and the auth/token half of Python and R. For the Python/R data-fetching convenience layer, see the [Data-Fetching Guide](data-fetching.md).

---

## Install

/// tab | Python

    :::bash
    pip install git+https://github.com/jackmanners/tokenbridge.git#subdirectory=python

///

/// tab | R

    :::r
    devtools::install_github("jackmanners/tokenbridge", subdir = "r")

///

/// tab | JavaScript

    :::bash
    npm install "git+https://github.com/jackmanners/tokenbridge.git#path:js"

///

## Configuration

All three read the same two environment variables, typically from a `.env` file:

| Variable | Description |
|---|---|
| `TOKENBRIDGE_URL` | Your deployment's base URL, e.g. `https://xxx.supabase.co/functions/v1` |
| `TOKENBRIDGE_API_KEY` | The API key you set during deployment |

/// tab | Python

    :::python
    from tokenbridge import TokenBridge
    tb = TokenBridge()   # reads .env; or pass url=, api_key= directly

///

/// tab | R

    :::r
    library(tokenbridge)
    tb_setup()   # interactive wizard, writes .env - run once

///

/// tab | JavaScript

    :::ts
    import { TokenBridge } from "tokenbridge";
    const tb = new TokenBridge();   // reads .env; or pass { url, apiKey }

///

---

## Generating an auth link

Returns a signed, time-limited URL - `.../auth-start?provider=...&user_id=...&exp=...&sig=...`. `exp`/`sig` are an HMAC-SHA256 signature (keyed with `TOKENBRIDGE_API_KEY`, 7-day lifetime) over `{provider}:{user_id}:{exp}`; `auth-start` verifies them before starting OAuth, so a link can't be forged or have its `user_id` tampered with. Send the link to the participant - once they complete OAuth, their token is stored and ready.

/// tab | Python

    :::python
    tb.auth_url(user_id, provider=None) -> str
    tb.auth_urls(user_ids, provider=None) -> dict[str, str]   # batch

    print(tb.auth_url("p001", provider="withings"))

///

/// tab | R

    :::r
    tb_auth_url(user_id, provider = tb_get_provider(), env_file = ".env")
    tb_auth_urls(user_ids, provider = tb_get_provider(), env_file = ".env")   # batch

    tb_auth_url("p001", provider = "withings")

///

/// tab | JavaScript

    :::ts
    tb.authUrl(userId: string, provider?: string): string
    tb.authUrls(userIds: string[], provider?: string): Record<string, string>   // batch

    console.log(tb.authUrl("p001", "withings"));

///

---

## Getting a token

Returns a valid access token for `user_id` + `provider`, auto-refreshing server-side if near expiry. Raises an error with a re-auth link baked into the message if the participant hasn't authorised yet, or if their refresh token has expired.

/// tab | Python

    :::python
    tb.get_token(user_id, provider=None, sleepscan=False) -> str

    token = tb.get_token("p001", provider="withings")

    # Call the provider's API directly with it:
    import requests
    resp = requests.get(
        "https://wbsapi.withings.net/v2/sleep",
        params={"action": "getsummary", "startdateymd": start, "enddateymd": end},
        headers={"Authorization": f"Bearer {token}"},
    )

///

/// tab | R

    :::r
    tb_get_token(user_id, provider = tb_get_provider(), env_file = ".env")

    tok <- tb_get_token("p001", provider = "withings")

    # Call the provider's API directly with it:
    resp <- httr::GET(
      "https://wbsapi.withings.net/v2/sleep",
      query = list(action = "getsummary", startdateymd = start, enddateymd = end),
      httr::add_headers(Authorization = paste("Bearer", tok))
    )

///

/// tab | JavaScript

    :::ts
    tb.getToken(userId: string, provider?: string): Promise<string>

    const token = await tb.getToken("p001", "withings");

    // Call the provider's API directly with it:
    const res = await fetch(
      `https://wbsapi.withings.net/v2/sleep?action=getsummary&startdateymd=${start}&enddateymd=${end}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );

///

Python's `get_token()` additionally takes a `sleepscan=True` option - an alternate Withings token source for participants registered through a separate system called SleepScan rather than TokenBridge's own OAuth flow. R has the equivalent on `wt_fetch()` instead (its token-layer `tb_get_token()` doesn't take it) - see the [Data-Fetching Guide](data-fetching.md#sleepscan) either way if that applies to your study.

---

## Errors

| Condition | Python | R | JavaScript |
|---|---|---|---|
| Missing config | `RuntimeError: TOKENBRIDGE_URL not set` | `stop("TOKENBRIDGE_URL is not set - run tb_setup() first.")` | `TokenBridgeError: TOKENBRIDGE_URL is not set` |
| Not yet authorised (404) | `RuntimeError: No token found for user '...'` (includes auth URL) | `stop("No token found for user '...'")` (includes auth URL) | `TokenBridgeError: No token found for user '...'` (includes auth URL) |
| Refresh token expired (401) | `RuntimeError: Token for '...' has expired` | `stop("Token for '...' has expired ...")` | `TokenBridgeError: Token for '...' has expired ...` |
| Other non-2xx from `/token` | `RuntimeError` with status + body | `stop("TokenBridge error (...): ...")` | `TokenBridgeError: TokenBridge error (...): ...` |
| Non-2xx calling the provider API yourself | `requests.HTTPError` | HTTP error from `httr::GET`/`POST` | Error thrown by `fetch()` |
