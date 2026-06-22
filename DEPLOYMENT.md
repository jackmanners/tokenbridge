# Deploying TokenBridge

TokenBridge is self-hosted. You run your own instance — your participant tokens never leave your infrastructure.

For a step-by-step setup walkthrough, see the [Basic Setup Guide](BASIC_QUICKSTART.md).
This page covers the architecture, configuration options, and anything you might need once you're running.

---

## What you're deploying

Three things work together:

**Supabase** hosts the database (token storage) and runs the edge functions (the OAuth flow and token API).
It's the only piece that needs to be publicly reachable — participants click a link to it, and your R/Python scripts call it to get tokens.

**Google Cloud** provides OAuth credentials. You register an app there once;
it tells Google where to send participants after they authorise (back to your Supabase function).

**The client package** (R or Python) runs on your machine. It talks to Supabase to get tokens, then uses them to call Google Health directly.

---

## What you need

- A [Supabase](https://supabase.com) account (free tier is fine)
- A [Google Cloud](https://console.cloud.google.com) account (free)
- R or Python on your local machine

---

## Edge functions

Four Deno/TypeScript functions run on Supabase:

| Function | Purpose |
|---|---|
| `auth-start` | Generates the Google OAuth URL and redirects the participant |
| `auth-callback` | Receives the OAuth code after authorisation, exchanges it for tokens, stores them |
| `token` | Called by your scripts — returns a valid access token (auto-refreshes if needed) |

The function code lives in [`supabase/functions/`](supabase/functions/).
Deploy via the [Supabase dashboard](https://supabase.com/dashboard) (Edge Functions → paste code) or the CLI (`supabase functions deploy`).

---

## Secrets

Set these in **Project Settings → Edge Functions → Secrets**:

| Secret | Description |
|---|---|
| `GOOGLE_HEALTH_CLIENT_ID` | From your Google Cloud OAuth credentials |
| `GOOGLE_HEALTH_CLIENT_SECRET` | From your Google Cloud OAuth credentials |
| `TOKENBRIDGE_API_KEY` | A secret you choose — your scripts use this to authenticate |

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

## CLI deployment (alternative to the dashboard)

If you have the Supabase CLI available:

```bash
supabase login
supabase link --project-ref YOUR_PROJECT_REF
supabase functions deploy auth-start auth-callback token
```

---

## Adding Withings support

1. Create an app at [developer.withings.com](https://developer.withings.com)
2. Set the redirect URI to `https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-callback`
3. Add `WITHINGS_CLIENT_ID` and `WITHINGS_CLIENT_SECRET` to Supabase secrets
4. Implement the Withings provider in `supabase/functions/_shared/providers.ts`
