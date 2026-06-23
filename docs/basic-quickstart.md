# Setup Guide

Two phases:

1. **Backend** - Supabase project + edge functions (once, ~10 min)
2. **Providers** - OAuth app per data source (10–15 min each, add as many as you need)

---

## Part 1 - Backend setup

### 1. Create a Supabase project (~5 min)

1. Sign up at [supabase.com](https://supabase.com) and create a new project
2. Give it a name, choose a region near you, set a database password
3. Wait about a minute for it to provision
4. Go to **Project Settings → General** and copy your **Project reference ID** (looks like `abcdefghijklmnop`)

**Set up the database:**

1. In the left sidebar, click **SQL Editor → New query**
2. Open [`supabase/setup.sql`](https://github.com/jackmanners/tokenbridge/blob/main/supabase/setup.sql) from the repo, copy everything, paste and run it
3. You should see "Success. No rows returned"

---

### 2. Deploy the edge functions (~5 min)

The functions use shared code so they must be deployed via the Supabase CLI. This is a one-time step - after this, pushing to `main` deploys automatically.

```bash
npm install -g supabase
supabase login
supabase link --project-ref YOUR_PROJECT_REF
supabase functions deploy auth-start auth-callback token token-keepalive --no-verify-jwt
```

If you don't have Node/npm, see the [Supabase CLI docs](https://supabase.com/docs/guides/cli) for alternative install methods.
Alternatively, you can deploy functions one at a time from the Supabase web dashboard.

---

### 3. Set core secrets (~1 min)

In your Supabase dashboard, go to **Project Settings → Edge Functions → Secrets** and add:

| Secret name | Value |
|---|---|
| `TOKENBRIDGE_API_KEY` | Make up a long random password - you'll use this in the client packages |

To generate one: `openssl rand -hex 32`

---

### 4. Set up GitHub Actions (optional)

Two workflows live in `.github/workflows/`:

- **`deploy-functions.yml`** - redeploys edge functions automatically whenever you push changes to `supabase/functions/`
- **`token-keepalive.yml`** - runs weekly to proactively refresh tokens before they expire

Both need these repository secrets (**Settings → Secrets → Actions**):

| Secret name | Value |
|---|---|
| `SUPABASE_ACCESS_TOKEN` | From [supabase.com/dashboard/account/tokens](https://supabase.com/dashboard/account/tokens) |
| `SUPABASE_PROJECT_REF` | Your project reference ID from Step 1 |
| `TOKENBRIDGE_API_KEY` | Same value as the Supabase secret above |

---

## Part 2 - Provider setup

Add one or more providers. Each requires its own OAuth app and two secrets in Supabase.
See the [Providers section](providers/index.md) for detailed setup instructions per provider, including which data types are available and any special notes or limitations.

## Next steps

The backend is set up. To start pulling data, see [Basic Access via TokenBridge](basic-access.md) - it shows the full flow (auth link → token request → API call) using plain HTTP requests.

If you'd prefer a Python or R wrapper, see [Client packages](../python/index.md).
