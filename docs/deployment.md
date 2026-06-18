# Deploying TokenBridge

This guide walks you through setting up your own TokenBridge instance from scratch.
**Total time: about 20–30 minutes.**

You will need:
- A [Supabase](https://supabase.com) account (free)
- A [Google Cloud](https://console.cloud.google.com) account (free)
- [Node.js](https://nodejs.org) installed (to run the Supabase CLI)

---

## Step 1 — Create a Supabase project

1. Go to [supabase.com](https://supabase.com) and sign in
2. Click **New project**, give it a name, choose a region close to you, set a database password, click **Create project**
3. Wait about a minute for it to provision
4. Go to **Project Settings → General** and copy your **Project reference ID** — it looks like `abcdefghijklmnop` (16 characters)

---

## Step 2 — Set up the database

1. In your Supabase dashboard, click **SQL Editor** in the left sidebar
2. Click **New query**
3. Open [`supabase/setup.sql`](supabase/setup.sql) from this repo, copy the entire contents, and paste it into the editor
4. Click **Run** — you should see "Success. No rows returned"

That's it for the database. The SQL creates two tables (`oauth_tokens` and `oauth_states`) that TokenBridge uses to store credentials.

---

## Step 3 — Set up Google Cloud

This is the most involved step, but you only do it once.

### 3a — Create a project and enable the API

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown at the top → **New project** → give it a name → **Create**
3. Go to **APIs & Services → Library**, search for **Google Health API**, click it, click **Enable**

### 3b — Configure the OAuth consent screen

1. Go to **APIs & Services → OAuth consent screen → Get Started**
2. Fill in:
   - **App name**: anything (e.g. "My Research Study")
   - **User support email**: your email
   - **Audience**: External
   - **Contact email**: your email
3. Click through to **Data access → Add or remove scopes**
4. Search for "googlehealth" and add all scopes that appear (they all start with `https://www.googleapis.com/auth/googlehealth`)
5. Save and continue through the remaining screens

> **Important:** Leave the app in **Testing** mode. This supports up to 100 participants without going through Google's verification process. Participants will see an "unverified app" warning — they click **Advanced → Continue** to proceed.

### 3c — Create OAuth credentials

1. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
2. Set **Application type** to **Web application**
3. Under **Authorised redirect URIs**, click **Add URI** and enter:
   ```
   https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-callback
   ```
   (replace `YOUR_PROJECT_REF` with the reference ID from Step 1)
4. Click **Create**
5. Copy the **Client ID** and **Client Secret** — keep these safe

### 3d — Add test users

1. Go to **OAuth consent screen → Audience → Test users → Add users**
2. Enter the Google account email of each participant who will join the study
3. Click **Save**

> Participants must have the **Fitbit app** installed and signed in with the same Google account. Without this, there is no health data to access.

---

## Step 4 — Update config.toml and deploy functions

Install the Supabase CLI:
```bash
npm install -g supabase
```

Edit [`supabase/config.toml`](supabase/config.toml) and replace `YOUR_PROJECT_REF` with your actual project reference ID:
```toml
project_id = "abcdefghijklmnop"
```

Then link and deploy:
```bash
supabase login
supabase link --project-ref YOUR_PROJECT_REF
supabase functions deploy auth-start auth-callback token webhook
```

---

## Step 5 — Set secrets

In your Supabase dashboard, go to **Project Settings → Edge Functions → Secrets** and add these four values:

| Secret name | Where to get it |
|---|---|
| `TOKENBRIDGE_API_KEY` | Make up a long random string — this is what your scripts use to authenticate |
| `GOOGLE_HEALTH_CLIENT_ID` | From Step 3c |
| `GOOGLE_HEALTH_CLIENT_SECRET` | From Step 3c |
| `WEBHOOK_SECRET` | Another random string — used to verify webhook callbacks |

To generate a random string:
```bash
# Mac / Linux
openssl rand -hex 32

# Windows PowerShell
-join ((48..57 + 65..90 + 97..122) | Get-Random -Count 32 | % {[char]$_})
```

---

## Step 6 — Test it

Open this URL in a browser (replace the placeholders):
```
https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-start?provider=google-health&user_id=test-user
```

You should be redirected to a Google sign-in page. After signing in and approving access, you'll see a success message.

Then test token retrieval:
```bash
curl -X POST https://YOUR_PROJECT_REF.supabase.co/functions/v1/token \
  -H "Authorization: Bearer YOUR_TOKENBRIDGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"provider": "google-health", "user_id": "test-user"}'
```

You should get back a JSON object with an `access_token`.

---

## Step 7 — Set up the client package

Copy `.env.example` to `.env` and fill in:
```
TOKENBRIDGE_URL=https://YOUR_PROJECT_REF.supabase.co/functions/v1
TOKENBRIDGE_API_KEY=your_key_from_step_5
```

Then run the setup wizard:
```bash
# Python
python -m tokenbridge

# R
library(tokenbridge)
tb_setup()
```

---

## Adding more participants

Send each participant their auth URL:
```python
from tokenbridge import TokenBridge
tb = TokenBridge()
print(tb.auth_url("participant-001"))
```
```r
library(tokenbridge)
tb_auth_url("participant-001")
```

They click the link, sign in with their Google account, and approve access. You can then fetch their data immediately.

Remember to add each participant's Google account email to the test users list in Google Cloud (Step 3d).

---

## Adding Withings support

1. Create an app at [developer.withings.com](https://developer.withings.com)
2. Set the redirect URI to `https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-callback`
3. Add `WITHINGS_CLIENT_ID` and `WITHINGS_CLIENT_SECRET` to Supabase secrets
4. Implement the Withings provider in the edge functions (see `supabase/functions/_shared/providers.ts`)

---

## Redeploying to a new Supabase project

1. Create a new project (Step 1)
2. Run the database setup (Step 2)
3. Update `project_id` in `supabase/config.toml`
4. Update the redirect URI in Google Cloud credentials (Step 3c)
5. Re-run Steps 4 and 5 with the new project ref
