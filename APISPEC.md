# TokenBridge — API Spec (AI-friendly)

**TokenBridge's primary job is OAuth token management: run the OAuth flow,
store tokens, refresh them before they expire, hand one back on request.**
The Python/R packages also wrap provider data endpoints as a convenience,
and we try to keep those in step with each provider's own API - but that's
a secondary priority maintained more slowly than the token layer, so it can
lag behind a provider's recent changes. When in doubt, or for anything not
already covered, call the provider's API directly with the token.

Full, language-specific, single-file specs (each one written to be pasted
whole into an LLM's context when wiring TokenBridge into another project):

- [Python](docs/apispec-python.md) — token retrieval + a data-fetching convenience layer, kept up with provider routes on a best-effort basis (maintained more slowly than the token layer)
- [R](docs/apispec-r.md) — same shape as Python, narrower provider coverage
- [JS/TS](docs/apispec-js.md) — token retrieval only, nothing else

For the data itself: [Provider Reference](docs/providers/index.md) links
each provider's API base URL and official docs.
