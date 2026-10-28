# Client Libraries

A client library is how your research script talks to a TokenBridge instance - it is not TokenBridge itself. If someone in your lab has already deployed an instance, you only need one of these; see [Platform](../platform/overview.md) if you're the one setting it up.

**TokenBridge's job is OAuth token management: run the flow, store tokens, refresh them before they expire, hand one back on request.** Every client library wraps that - auth-link generation and token retrieval - identically. Python additionally wraps provider data endpoints (and renders reports) as a convenience; that layer is maintained more slowly than the core token API, so treat the provider's own API reference as the source of truth once you're past token retrieval. R and JavaScript are token-only, by design - lean, with nothing extra to keep in sync against providers' own APIs.

## Choosing a language

| | Python | R | JavaScript |
|---|---|---|---|
| Auth links + token retrieval | ✓ | ✓ | ✓ |
| Data-fetching convenience layer | ✓ (6 providers) | — | — |
| Report generation | ✓ | — | — |
| Install | `pip install git+https://github.com/jackmanners/tokenbridge.git#subdirectory=python` | `devtools::install_github("jackmanners/tokenbridge", subdir = "r")` | `npm install "git+https://github.com/jackmanners/tokenbridge.git#path:js"` |

If you just need a token to call a provider API yourself - a backend job, a different language entirely, or you'd simply rather not add the data-fetching layer's maintenance surface - any of the three works the same way for that; R and JavaScript are the leanest.

## Where to go next

- [Getting Started](getting-started.md) - install, configure, onboard your first participant, get a token
- [Token API Reference](token-reference.md) - `auth_url`, `auth_urls`, `get_token`, and errors, side by side for all three languages
- [Data-Fetching Guide](data-fetching.md) - Python's provider data layer and report generation
- [Examples](examples.md) - complete, realistic scripts
