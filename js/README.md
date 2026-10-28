# tokenbridge (JavaScript)

JavaScript client for [TokenBridge](https://github.com/jackmanners/tokenbridge) - OAuth token management for research.

**Token retrieval and auth-link generation only.** This package doesn't wrap provider data APIs the way the Python package does - get a token, then call the provider's own API directly. See the [Client Libraries docs](https://jackmanners.github.io/tokenbridge/clients/) for why, and for links to each provider's API reference.

## Install

```bash
npm install "git+https://github.com/jackmanners/tokenbridge.git#path:js"
```

## Setup

Create a `.env` file (or set these as real env vars - whichever your framework already does):

```
TOKENBRIDGE_URL=https://xxx.supabase.co/functions/v1
TOKENBRIDGE_API_KEY=your-key
```

## Usage

```ts
import { TokenBridge } from "tokenbridge";

const tb = new TokenBridge(); // reads TOKENBRIDGE_URL + TOKENBRIDGE_API_KEY from .env

// Send each participant their auth link - they click once to authorise
console.log(tb.authUrl("p001", "withings"));
const links = tb.authUrls(["p001", "p002", "p003"], "withings"); // batch

// Get a token, then call the provider's API yourself
const token = await tb.getToken("p001", "withings");
const res = await fetch("https://wbsapi.withings.net/v2/sleep?action=getsummary&...", {
  headers: { Authorization: `Bearer ${token}` },
});
```

## Documentation

[jackmanners.github.io/tokenbridge](https://jackmanners.github.io/tokenbridge)
