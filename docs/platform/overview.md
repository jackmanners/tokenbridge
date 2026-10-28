# Platform Overview

TokenBridge is self-hosted - you run your own Supabase instance and tokens stay in your own database. This page covers the architecture, security model, and config options. For a step-by-step walkthrough, see [Deploying TokenBridge](deploying.md).

This is the platform: the thing you deploy once per lab or study. The [Client Libraries](../clients/index.md) (Python, R, JavaScript) are separate, optional packages that talk to it - you don't need to touch this page again once your instance is running, unless you're changing its configuration.

---

## What you're deploying

Two things work together:

**Supabase** hosts the database (token storage) and runs the edge functions (the OAuth flow and token API).
It's the only piece that needs to be publicly reachable - participants click a link to it, and your scripts call it to get tokens.

**Provider OAuth apps** (Google Cloud, Withings, Oura, etc.) provide OAuth credentials. You register an app with each provider once; it tells the provider where to redirect participants after they authorise.

Your scripts call the `/token` endpoint to get a valid access token, then use it to call the provider API directly - no auth logic needed in your analysis code.

---

## What you need

- A [Supabase](https://supabase.com) account (free tier is fine)
- An OAuth app for each provider you want to support (see [Providers](providers/index.md))

---

## Edge functions

Six Deno/TypeScript functions run on Supabase:

| Function | Purpose |
|---|---|
| `auth-start` | Verifies the signed auth link, generates the provider OAuth URL, redirects the participant |
| `auth-callback` | Receives the OAuth code after authorisation, exchanges it for tokens, stores them |
| `token` | Called by your scripts - returns a valid access token, auto-refreshes if needed |
| `token-keepalive` | Called weekly by GitHub Actions - proactively refreshes tokens before they expire |
| `sleep-report` | Renders a stored report template with participant data into a self-contained HTML file |
| `template-manager` | CRUD for report templates (`report_templates` table) used by `sleep-report` |

The function code lives in [`supabase/functions/`](https://github.com/jackmanners/tokenbridge/tree/main/supabase/functions).
Deploy via the CLI (`supabase functions deploy ... --import-map supabase/functions/deno.json`) - the functions share code via `_shared/` so they must be bundled by the CLI, not pasted into the dashboard. The `--import-map` flag resolves the `@supabase/supabase-js` import; without it, deploying without Docker running locally fails with a bundling error.

---

## Secrets

Set these in **Project Settings → Edge Functions → Secrets**.

**Core (required):**

| Secret | Description |
|---|---|
| `TOKENBRIDGE_API_KEY` | A secret you choose - your scripts use this to authenticate with the `/token` endpoint |

**Per provider - add the pair for each provider you enable:** `{PROVIDER}_CLIENT_ID` and `{PROVIDER}_CLIENT_SECRET`, e.g. `WITHINGS_CLIENT_ID` / `WITHINGS_CLIENT_SECRET`. Full list with doc links for every supported provider: [`.env.example`](https://github.com/jackmanners/tokenbridge/blob/main/.env.example) and [Provider Reference](providers/index.md).

---

## Google OAuth

### Consent screen and verification

When setting up the OAuth consent screen, leave the **Data Access** page empty - do not add any scopes there.

The edge functions request health scopes directly in the OAuth URL at runtime. Declaring them in the console is what triggers Google's verification requirement for restricted scopes. Leaving Data Access empty bypasses this, and the app works for up to 100 participants with no review process.

Participants will see an "unverified app" warning during authorisation - tell them to click **Advanced → Continue**. This is expected.

### Testing vs Production mode

| Mode | Who can authorise | Setup |
|---|---|---|
| Testing | Only accounts you manually add to the user list | Default for new apps |
| Production | Any Google account | Audience → Publish app |

Production is recommended - it removes the need to pre-register every participant's email.
Both modes have a 100-participant cap for unverified apps using restricted scopes.
If your study exceeds 100 participants, you will need to go through Google's verification process.

### Redirect URI

Set this in your Google Cloud credentials (**Authorised redirect URIs**):
```
https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-callback
```

---

## Automatic deployment

Two GitHub Actions workflows keep your deployment up to date:

- **`deploy-functions.yml`** - redeploys edge functions automatically on every push to `main` that touches `supabase/functions/`
- **`token-keepalive.yml`** - runs every Monday, refreshes any tokens that haven't been refreshed in 80+ days

Both require `SUPABASE_ACCESS_TOKEN`, `SUPABASE_PROJECT_REF`, and `TOKENBRIDGE_API_KEY` as repository secrets.

---

## Token refresh

Tokens are refreshed automatically in two ways:

- **On-demand:** when your script calls `/token`, the function checks expiry and refreshes if the token is within 5 minutes of expiring.
- **Proactive (keepalive):** the weekly GitHub Actions job refreshes tokens that haven't been touched in 80 days, keeping refresh tokens alive even during long gaps between data collection.

This ensures participants never need to re-authorise due to token expiry during a study, as long as the weekly job is running.

---

## Security model

- **No direct database access.** `oauth_states`, `oauth_tokens`, `data_availability`, and `report_templates` all have Row Level Security enabled with no policies - every real read/write goes through a service-role edge function, so the public (anon) Supabase key can't read stored tokens even if it leaks.
- **Signed auth links.** `auth-start` requires an HMAC-SHA256 signature (keyed with `TOKENBRIDGE_API_KEY`, 7-day lifetime) over `provider:user_id:exp`, generated for you by `auth_url()`/`tb_auth_url()`/`authUrl()`. A bare URL with a guessed `user_id` is rejected - this is what stops someone starting an OAuth flow under an arbitrary participant ID.
- **One API key gates every data-moving endpoint.** `/token`, `/sleep-report`, and `template-manager` all require `Authorization: Bearer $TOKENBRIDGE_API_KEY`. Treat it like a password - it's shared across every participant in the deployment, not scoped per-participant.
