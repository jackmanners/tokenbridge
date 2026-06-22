# TokenBridge — Basic Setup Guide

This guide sets up a complete TokenBridge deployment: a hosted token manager
your whole study can share, plus the R package to fetch data from it.

You will need free accounts on [Supabase](https://supabase.com) and
[Google Cloud](https://console.cloud.google.com). No credit card required for either.

---

## 1. Supabase — create a project (~5 min)

1. Sign up at https://supabase.com and create a new project
2. Give it a name, choose a region near you, set a database password
3. Wait about a minute for it to provision
4. Go to **Project Settings → General** and copy your **Project reference ID**
   (looks like `abcdefghijklmnop`)

**Set up the database:**

1. In the left sidebar, click **SQL Editor → New query**
2. Open [`supabase/setup.sql`](supabase/setup.sql) from this repo, copy everything, paste and run it
3. You should see "Success. No rows returned"

---

## 2. Google Cloud — set up OAuth (~10 min)

**Create a project and enable the API:**

1. Go to https://console.cloud.google.com, sign in, create a new project
2. Go to **APIs & Services → Library**, search **Google Health API**, enable it

**Configure the consent screen:**

1. Go to **APIs & Services → OAuth consent screen → Get Started**
2. Fill in your app name and email, set Audience to **External**, click through
3. On the **Data access** step — leave it completely empty, don't add anything
4. When asked about publishing status, choose **Production**

**Create credentials:**

1. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
2. Application type: **Web application**
3. Under **Authorised redirect URIs**, add:
   ```
   https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-callback
   ```
   (replace `YOUR_PROJECT_REF` with your Supabase project reference from Step 1)
4. Click **Create** and copy the **Client ID** and **Client Secret**

---

## 3. Deploy the edge functions (~5 min)

The functions use shared code so they need to be deployed via the Supabase CLI rather than copy-pasting.
This is a one-time setup — after this, pushing to `main` deploys automatically.

Install the CLI and deploy:

```bash
npm install -g supabase
supabase login
supabase link --project-ref YOUR_PROJECT_REF
supabase functions deploy auth-start auth-callback token --no-verify-jwt
```

If you don't have Node/npm, ask whoever manages your IT to run this once, or see the
[Supabase CLI docs](https://supabase.com/docs/guides/cli) for alternative install methods.

---

## 4. Set secrets (~2 min)

In your Supabase dashboard, go to **Project Settings → Edge Functions → Secrets**
and add these four:

| Secret name | Value |
|---|---|
| `GOOGLE_HEALTH_CLIENT_ID` | Client ID from Step 2 |
| `GOOGLE_HEALTH_CLIENT_SECRET` | Client Secret from Step 2 |
| `TOKENBRIDGE_API_KEY` | Make up a long random password — you'll use this in R |

To generate a random string on Mac/Linux: `openssl rand -hex 32`

---

## 5. Test it

Open this URL in a browser (replace the placeholders):

```
https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-start?provider=google-health&user_id=test
```

You should be redirected to a Google sign-in page. After signing in you'll see a success message.

If that works, your deployment is running correctly.

---

## 6. Set up the R package

Install R and RStudio: https://posit.co/download/rstudio-desktop/

Then in RStudio:

```r
install.packages("devtools")
devtools::install_github("jackmanners/tokenbridge", subdir = "r")

library(tokenbridge)
tb_setup()
# When prompted:
#   URL:     https://YOUR_PROJECT_REF.supabase.co/functions/v1
#   API key: the TOKENBRIDGE_API_KEY you set in Step 4
```

---

## 7. Basic usage

```r
library(tokenbridge)

# Generate auth links for participants and send them
links <- tb_auth_urls(c("p001", "p002", "p003"))
for (id in names(links)) cat(id, "->", links[[id]], "\n")

# Check who has connected
for (id in c("p001", "p002", "p003")) {
  status <- tryCatch(tb_token_status(id), error = function(e) NULL)
  cat(id, if (is.null(status)) "NOT connected" else "connected", "\n")
}

# Fetch data
sleep <- tb_fetch("p001", "sleep", "2026-05-01", "2026-06-18")
write.csv(sleep, "p001_sleep.csv", row.names = FALSE)

# Check data coverage across everyone
gh_data_completeness(c("p001", "p002", "p003"), "2026-05-01", "2026-06-18")
```

Participants will see an "unverified app" warning when they click their link —
tell them to click **Advanced → Continue**. This is expected.

For full package documentation see the [R reference](https://jackmanners.github.io/tokenbridge/r/reference/).
