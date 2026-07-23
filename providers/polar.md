# Polar (`polar`)

**API base:** `https://www.polaraccesslink.com/v3`
**Auth:** OAuth 2.0 (no PKCE), scope `accesslink.read_all`, client credentials sent via HTTP Basic auth (not in the request body)
**Backend:** Polar watches and H-series HR straps, synced via Polar Flow
**Response envelope:** Bare JSON array (no wrapper), or `404` if there's no data for the requested range

## Key differences from other providers

- **Access tokens never expire.** Polar has no refresh flow — a token stays valid until the user revokes access in Polar Flow.
- **New users must be registered** with AccessLink via `POST /v3/users` before any data endpoint works. TokenBridge's `auth-callback` does this automatically right after the OAuth token exchange (see `postTokenExchange` in `supabase/functions/_shared/providers.ts`). If registration fails, the callback returns a 502 with the error rather than silently storing a token that won't work.
- **28-day cap per request.** Polar doesn't allow arbitrarily long date ranges. `fetch()` transparently chunks longer ranges into sequential ≤28-day requests and concatenates results — this is invisible to callers.
- **Modern endpoints, not the transaction model.** Polar's docs describe an older transaction-based pull flow (create → list → fetch → commit) which they now recommend against for new integrations. TokenBridge uses the newer flat `GET .../sleep?from=...&to=...` style endpoints instead.

## Data types

| Type ID | Endpoint | Description |
|---|---|---|
| `sleep` | `/users/sleep` | Sleep stages (light, deep, REM), interruptions, sleep score |
| `activity` | `/users/activities` | Daily activity summary (steps, calories, activity zones) |
| `nightly-recharge` | `/users/nightly-recharge` | Nightly recharge / ANS charge score |
| `exercise` | `/exercises` | Individual training sessions with HR and lap data |

## Known limitations

- Date ranges longer than 28 days require multiple requests — handled automatically, but be aware of the added latency for long backfills.
- `exercise` sessions are not scoped by `/users/{id}`, only by app-wide `/exercises` — Polar's own API design, not a TokenBridge limitation.
- No refresh token is stored — don't rely on `expires_at` for Polar; it will be `null`.

## Setup

**Requires:** A Polar developer account and a participant's Polar account synced via Polar Flow.

**Create a Polar app:**

1. Sign up at [polar.com/en/developers](https://www.polar.com/en/developers) and register an AccessLink application
2. Under **Callback URL**, add `https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-callback`
3. Save and copy the **Client ID** and **Client Secret**

**Add secrets to Supabase** (Project Settings → Edge Functions → Secrets):

| Secret name | Value |
|---|---|
| `POLAR_CLIENT_ID` | Client ID from above |
| `POLAR_CLIENT_SECRET` | Client Secret from above |

**Test** — visit this URL, you should be redirected to Polar authorisation:

`https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-start?provider=polar&user_id=test`
