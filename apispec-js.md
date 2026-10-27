# API Spec — JS/TS

Single-file reference for the JS/TS package, written to be pasted whole into
an LLM's context when wiring TokenBridge into another project.

**This package is token retrieval and auth-link generation only - that's the
entire scope, by design.** TokenBridge's job is OAuth token management; it
doesn't try to keep a JS wrapper in sync with every provider's data API. Get
a token, then call the provider's own API directly - see
[Provider Reference](providers/index.md) for each provider's API base URL
and official docs. (The Python/R packages additionally ship best-effort data
wrappers for providers already implemented there - see their API specs if
you need that instead of building it yourself.)

Raw file: https://raw.githubusercontent.com/jackmanners/tokenbridge/main/docs/apispec-js.md

---

## Setup

```bash
npm install "git+https://github.com/jackmanners/tokenbridge.git#path:js"
```

**.env** (read automatically) or real env vars - same keys as the Python/R packages:
```
TOKENBRIDGE_URL=https://xxx.supabase.co/functions/v1
TOKENBRIDGE_API_KEY=your-key
```

Requires Node ≥18 (uses the built-in `fetch` and `node:crypto`). Zero runtime dependencies.

## new TokenBridge(options?)

```ts
import { TokenBridge } from "tokenbridge";

const tb = new TokenBridge();
// or: new TokenBridge({ url, apiKey, envFile, provider })
```

All options optional — read from env if omitted. `provider` defaults to `"google-health"`, used by `authUrl()`/`authUrls()`/`getToken()` when not passed explicitly. Throws `TokenBridgeError` synchronously if `TOKENBRIDGE_URL`/`TOKENBRIDGE_API_KEY` can't be resolved.

### .authUrl(userId, provider?) → string

Returns `{TOKENBRIDGE_URL}/auth-start?provider={provider}&user_id={userId}&exp={exp}&sig={sig}`. `exp`/`sig` are an HMAC-SHA256 signature (keyed with `TOKENBRIDGE_API_KEY`, 7-day lifetime) over `{provider}:{userId}:{exp}` - `auth-start` verifies them before starting OAuth, so a link can't be forged or have its `userId` tampered with. Send the link to the participant to initiate OAuth.

```ts
console.log(tb.authUrl("p001", "withings"));
```

### .authUrls(userIds, provider?) → Record<string, string>

Batch version of `authUrl()`.

```ts
const links = tb.authUrls(["p001", "p002", "p003"], "withings");
```

### .getToken(userId, provider?) → Promise\<string\>

Returns a valid access token for `userId` + `provider` via the TokenBridge `/token` endpoint, auto-refreshing server-side if near expiry. Throws `TokenBridgeError` (message includes a re-auth link) if the participant hasn't authorised yet (HTTP 404) or their refresh token has expired (HTTP 401).

```ts
const token = await tb.getToken("p001", "withings");

// Now call the provider's own API directly:
const res = await fetch(
  `https://wbsapi.withings.net/v2/sleep?action=getsummary&startdateymd=${start}&enddateymd=${end}`,
  { headers: { Authorization: `Bearer ${token}` } },
);
```

## Errors

| Error | Cause |
|---|---|
| `TokenBridgeError: TOKENBRIDGE_URL is not set` | Missing env var / option |
| `TokenBridgeError: No token found for user '...'` | User not authorised — message contains auth URL |
| `TokenBridgeError: Token for '...' has expired ...` | Refresh token expired — user must re-authorise |
| `TokenBridgeError: TokenBridge error (...): ...` | Other non-2xx response from `/token` |
| Any error thrown by `fetch()` | Non-2xx from a provider API call you made yourself |

## Not included (by design)

No `fetch()`/data wrappers, no reports helper, no SleepScan integration. If you need those today, use the Python or R package, or call the relevant endpoints yourself - `/sleep-report` and SleepScan's own API are both plain HTTP, documented in the [Python API Spec](apispec-python.md).
