# Setup Guide

Two phases:

1. **Backend** — Supabase project + edge functions (once, ~10 min)
2. **Providers** — OAuth app per data source (10–15 min each, add as many as you need)

---

## Part 1 — Backend setup

### 1. Create a Supabase project (~5 min)

1. Sign up at [supabase.com](https://supabase.com) and create a new project
2. Give it a name, choose a region near you, set a database password
3. Wait about a minute for it to provision
4. Go to **Project Settings → General** and copy your **Project reference ID**
   (looks like `abcdefghijklmnop`)

**Set up the database:**

1. In the left sidebar, click **SQL Editor → New query**
2. Open [`supabase/setup.sql`](https://github.com/jackmanners/tokenbridge/blob/main/supabase/setup.sql) from the repo, copy everything, paste and run it
3. You should see "Success. No rows returned"

---

### 2. Deploy the edge functions (~5 min)

The functions use shared code so they must be deployed via the Supabase CLI.
This is a one-time step — after this, pushing to `main` deploys automatically.

```bash
npm install -g supabase
supabase login
supabase link --project-ref YOUR_PROJECT_REF
supabase functions deploy auth-start auth-callback token token-keepalive --no-verify-jwt
```

If you don't have Node/npm, see the [Supabase CLI docs](https://supabase.com/docs/guides/cli) for alternative install methods.

---

### 3. Set core secrets (~1 min)

In your Supabase dashboard, go to **Project Settings → Edge Functions → Secrets** and add:

| Secret name | Value |
|---|---|
| `TOKENBRIDGE_API_KEY` | Make up a long random password — you'll use this in the client packages |

To generate one: `openssl rand -hex 32`

---

### 4. Set up GitHub Actions (optional but recommended)

Two workflows live in `.github/workflows/`:

- **`deploy-functions.yml`** — redeploys edge functions automatically whenever you push changes to `supabase/functions/`
- **`token-keepalive.yml`** — runs weekly to proactively refresh tokens before they expire

Both need these repository secrets (**Settings → Secrets → Actions**):

| Secret name | Value |
|---|---|
| `SUPABASE_ACCESS_TOKEN` | From [supabase.com/dashboard/account/tokens](https://supabase.com/dashboard/account/tokens) |
| `SUPABASE_PROJECT_REF` | Your project reference ID from Step 1 |
| `TOKENBRIDGE_API_KEY` | Same value as the Supabase secret above |

---

## Part 2 — Provider setup

Add one or more providers. Each requires its own OAuth app and two secrets in Supabase.

=== "Google Health (Fitbit)"

    **Requires:** A Google Cloud project. Data comes from Fitbit devices linked to a Google account.

    **Create a project and enable the API:**

    1. Go to [console.cloud.google.com](https://console.cloud.google.com), sign in, create a new project
    2. Go to **APIs & Services → Library**, search **Google Health API**, enable it

    **Configure the consent screen:**

    1. Go to **APIs & Services → OAuth consent screen → Get Started**
    2. Fill in your app name and email, set Audience to **External**, click through
    3. On the **Data access** step — leave it completely empty
    4. When asked about publishing status, choose **Production**

    **Create credentials:**

    1. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
    2. Application type: **Web application**
    3. Under **Authorised redirect URIs**, add:
       ```
       https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-callback
       ```
    4. Click **Create** and copy the **Client ID** and **Client Secret**

    **Add secrets to Supabase** (**Project Settings → Edge Functions → Secrets**):

    | Secret name | Value |
    |---|---|
    | `GOOGLE_HEALTH_CLIENT_ID` | Client ID from above |
    | `GOOGLE_HEALTH_CLIENT_SECRET` | Client Secret from above |

    **Test:**
    ```
    https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-start?provider=google-health&user_id=test
    ```
    You should be redirected to a Google sign-in page.

    !!! note
        Participants will see an "unverified app" warning — tell them to click **Advanced → Continue**.
        This goes away once Google verifies your app (optional for small studies).

=== "Withings"

    **Requires:** A Withings developer account. Data comes from Withings devices
    (scales, blood pressure monitors, sleep mats, activity trackers).

    **Create a Withings app:**

    1. Sign up at [developer.withings.com](https://developer.withings.com) and go to your [Dashboard](https://developer.withings.com/dashboard/)
    2. Click **Create an application**
    3. Fill in app name and description
    4. Under **Callback URL**, add:
       ```
       https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-callback
       ```
    5. Save and copy the **Client ID** and **Consumer Secret**

    **Add secrets to Supabase** (**Project Settings → Edge Functions → Secrets**):

    | Secret name | Value |
    |---|---|
    | `WITHINGS_CLIENT_ID` | Client ID from above |
    | `WITHINGS_CLIENT_SECRET` | Consumer Secret from above |

    **Test:**
    ```
    https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-start?provider=withings&user_id=test
    ```
    You should be redirected to the Withings authorisation page.

=== "Oura"

    **Requires:** An Oura developer account. Data comes from Oura Ring devices.

    **Create an Oura app:**

    1. Sign in at [cloud.ouraring.com](https://cloud.ouraring.com) and go to **My Apps → Create New App**
    2. Fill in your app name and description
    3. Under **Redirect URIs**, add:
       ```
       https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-callback
       ```
    4. Save and copy the **Client ID** and **Client Secret**

    **Add secrets to Supabase** (**Project Settings → Edge Functions → Secrets**):

    | Secret name | Value |
    |---|---|
    | `OURA_CLIENT_ID` | Client ID from above |
    | `OURA_CLIENT_SECRET` | Client Secret from above |

    **Test:**
    ```
    https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-start?provider=oura&user_id=test
    ```
    You should be redirected to the Oura authorisation page.

---

## Part 3 — Install the client package

=== "Python"

    ```bash
    pip install git+https://github.com/jackmanners/tokenbridge.git#subdirectory=python
    python -m tokenbridge
    # When prompted:
    #   URL:     https://YOUR_PROJECT_REF.supabase.co/functions/v1
    #   API key: the TOKENBRIDGE_API_KEY you set in Step 3
    ```

=== "R"

    ```r
    install.packages("devtools")
    devtools::install_github("jackmanners/tokenbridge", subdir = "r")

    library(tokenbridge)
    tb_setup()
    # When prompted:
    #   URL:     https://YOUR_PROJECT_REF.supabase.co/functions/v1
    #   API key: the TOKENBRIDGE_API_KEY you set in Step 3
    ```

---

## Part 4 — Basic usage

```r
library(tokenbridge)

# Generate auth links for participants and send them
links <- tb_auth_urls(c("p001", "p002", "p003"))
for (id in names(links)) cat(id, "->", links[[id]], "\n")

# Withings or Oura participants get provider-specific links
wt_links <- tb_auth_urls(c("p001", "p002"), provider = "withings")
ou_links  <- tb_auth_urls(c("p001", "p002"), provider = "oura")

# Fetch data (once participants have authorised)
sleep <- tb_fetch("p001", "sleep", "2026-05-01", "2026-06-18")

# Provider-specific fetchers
activity <- wt_fetch("p001", "activity",      "2026-05-01", "2026-06-18")
readiness <- ou_fetch("p001", "daily-readiness", "2026-05-01", "2026-06-18")

# Audit data coverage
gh_data_completeness(c("p001", "p002", "p003"), "2026-05-01", "2026-06-18")
```

For full package documentation see the [Python reference](../python/reference.md) and [R reference](../r/reference.md).
