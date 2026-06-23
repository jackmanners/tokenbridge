# Deploying TokenBridge

TokenBridge is self-hosted. You run your own instance — your participant tokens never leave your infrastructure.

For a step-by-step setup walkthrough, see the [Setup Guide](basic-quickstart.md).
This page covers the architecture, configuration options, and anything you might need once you're running.

---

## What you're deploying

Three things work together:

**Supabase** hosts the database (token storage) and runs the edge functions (the OAuth flow and token API).
It's the only piece that needs to be publicly reachable — participants click a link to it, and your scripts call it to get tokens.

**Provider OAuth apps** (Google Cloud, Withings, Oura, etc.) provide OAuth credentials. You register an app with each provider once; it tells the provider where to redirect participants after they authorise.

**The client package** (R or Python) runs on your machine. It talks to Supabase to get tokens, then uses them to call the provider API directly.

---

## What you need

- A [Supabase](https://supabase.com) account (free tier is fine)
- An OAuth app for each provider you want to support (see [Setup Guide](basic-quickstart.md))
- R or Python on your local machine

---

## Edge functions

Four Deno/TypeScript functions run on Supabase:

| Function | Purpose |
|---|---|
| `auth-start` | Generates the provider OAuth URL and redirects the participant |
| `auth-callback` | Receives the OAuth code after authorisation, exchanges it for tokens, stores them |
| `token` | Called by your scripts — returns a valid access token, auto-refreshes if needed |
| `token-keepalive` | Called weekly by GitHub Actions — proactively refreshes tokens before they expire |

The function code lives in [`supabase/functions/`](https://github.com/jackmanners/tokenbridge/tree/main/supabase/functions).
Deploy via the CLI (`supabase functions deploy`) — the functions share code via `_shared/` so they must be bundled by the CLI, not pasted into the dashboard.

---

## Secrets

Set these in **Project Settings → Edge Functions → Secrets**.

**Core (required):**

| Secret | Description |
|---|---|
| `TOKENBRIDGE_API_KEY` | A secret you choose — your scripts use this to authenticate with the `/token` endpoint |

**Per provider — add the pair for each provider you enable:**

| Secret | Description |
|---|---|
| `GOOGLE_HEALTH_CLIENT_ID` | From your Google Cloud OAuth credentials |
| `GOOGLE_HEALTH_CLIENT_SECRET` | From your Google Cloud OAuth credentials |
| `WITHINGS_CLIENT_ID` | From your Withings developer app |
| `WITHINGS_CLIENT_SECRET` | From your Withings developer app |
| `OURA_CLIENT_ID` | From your Oura developer app |
| `OURA_CLIENT_SECRET` | From your Oura developer app |

---

## Google OAuth

### Consent screen and verification

When setting up the OAuth consent screen, leave the **Data Access** page empty — do not add any scopes there.

The edge functions request health scopes directly in the OAuth URL at runtime. Declaring them in the console is what triggers Google's verification requirement for restricted scopes. Leaving Data Access empty bypasses this, and the app works for up to 100 participants with no review process.

Participants will see an "unverified app" warning during authorisation — tell them to click **Advanced → Continue**. This is expected.

### Testing vs Production mode

| Mode | Who can authorise | Setup |
|---|---|---|
| Testing | Only accounts you manually add to the user list | Default for new apps |
| Production | Any Google account | Audience → Publish app |

Production is recommended — it removes the need to pre-register every participant's email.
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

- **`deploy-functions.yml`** — redeploys edge functions automatically on every push to `main` that touches `supabase/functions/`
- **`token-keepalive.yml`** — runs every Monday, refreshes any tokens that haven't been refreshed in 80+ days

Both require `SUPABASE_ACCESS_TOKEN`, `SUPABASE_PROJECT_REF`, and `TOKENBRIDGE_API_KEY` as repository secrets.

---

## Token refresh

Tokens are refreshed automatically in two ways:

- **On-demand:** when your script calls `tb_get_token()`, the `/token` function checks expiry and refreshes if the token is within 5 minutes of expiring.
- **Proactive (keepalive):** the weekly GitHub Actions job refreshes tokens that haven't been touched in 80 days, keeping refresh tokens alive even during long gaps between data collection.

This ensures participants never need to re-authorise due to token expiry during a study, as long as the weekly job is running.
