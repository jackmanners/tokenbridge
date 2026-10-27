# JS/TS Package

The `tokenbridge` JS/TS package is token retrieval and auth-link generation
only - there's no data-fetching layer here. Get a token, then call the
provider's own API directly.

## Installation

```bash
npm install "git+https://github.com/jackmanners/tokenbridge.git#path:js"
```

Requires Node ≥18. Zero runtime dependencies.

## Quick start

```ts
import { TokenBridge } from "tokenbridge";

const tb = new TokenBridge(); // reads TOKENBRIDGE_URL + TOKENBRIDGE_API_KEY from .env

// Onboard
console.log(tb.authUrl("p001", "withings"));

// Get a token, then call the provider's API yourself
const token = await tb.getToken("p001", "withings");
const res = await fetch("https://wbsapi.withings.net/v2/sleep?action=getsummary&...", {
  headers: { Authorization: `Bearer ${token}` },
});
```

## See also

- [Getting Started](../getting-started.md)
- [API Spec](../apispec-js.md) — full reference
- [Providers](../providers/index.md) — provider API base URLs and official docs
