# Client Libraries

A client library is how your research script talks to a TokenBridge instance - it is not TokenBridge itself. If someone in your lab has already deployed an instance, you only need one of these; see [Platform](../platform/overview.md) if you're the one setting it up.

**TokenBridge's job is OAuth token management: run the flow, store tokens, refresh them before they expire, hand one back on request.** Every client library wraps that - auth-link generation and token retrieval - identically. Python and R additionally wrap some providers' data endpoints as a convenience; that layer is maintained more slowly than the core token API, so treat the provider's own API reference as the source of truth once you're past token retrieval.

## Choosing a language

| | Python | R | JS/TS |
|---|---|---|---|
| Auth links + token retrieval | ✓ | ✓ | ✓ |
| Data-fetching convenience layer | ✓ (6 providers) | ✓ (3 providers) | — |
| Install | `pip install git+https://github.com/jackmanners/tokenbridge.git#subdirectory=python` | `devtools::install_github("jackmanners/tokenbridge", subdir = "r")` | `npm install "git+https://github.com/jackmanners/tokenbridge.git#path:js"` |

If you just need a token to call a provider API yourself - a backend job, a different language entirely - any of the three works the same way; JS/TS is the leanest for that.

## Where to go next

- [Getting Started](getting-started.md) - install, configure, onboard your first participant, get a token
- [Token API Reference](token-reference.md) - `auth_url`, `auth_urls`, `get_token`, and errors, side by side for all three languages
- [Data-Fetching Guide](data-fetching.md) - the Python/R convenience layer, if you want it
- [Examples](examples.md) - complete, realistic scripts
