# TokenBridge

Centralised OAuth token management for health data research APIs.  
Handles the full OAuth flow, stores tokens in Supabase, and auto-refreshes before expiry.

## Supported providers

| Provider | Env prefix | Notes |
|---|---|---|
| `google-health` | `GOOGLE_HEALTH_` | Google Fit REST API scopes |
| `withings` | `WITHINGS_` | Stubbed and ready to configure |

---

## Setup

### 1. Supabase project

You need a Supabase project. The project reference for this instance is `dazucslvjgtfxjoocnei`.

Run the migration to create the required tables:

```bash
supabase db push
# or paste supabase/migrations/20240001_init.sql into the SQL editor
```

### 2. Google Cloud OAuth credentials

1. Go to [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials)
2. Create an **OAuth 2.0 Client ID** (type: Web application)
3. Add this **Authorized redirect URI**:
   ```
   https://dazucslvjgtfxjoocnei.supabase.co/functions/v1/auth-callback
   ```
4. Enable the **Fitness API** in [APIs & Services → Library](https://console.cloud.google.com/apis/library)

### 3. Deploy edge functions

```bash
supabase functions deploy auth-start
supabase functions deploy auth-callback
supabase functions deploy token
```

### 4. Set secrets

```bash
supabase secrets set \
  TOKENBRIDGE_API_KEY=<generate a strong random string> \
  GOOGLE_HEALTH_CLIENT_ID=<from step 2> \
  GOOGLE_HEALTH_CLIENT_SECRET=<from step 2>
```

---

## Usage

### Authorize a user

Open this URL in a browser (or send the user to it):

```
https://dazucslvjgtfxjoocnei.supabase.co/functions/v1/auth-start?provider=google-health&user_id=jack
```

The user completes Google's OAuth consent screen and lands on a success page.  
The token is stored automatically.

### Retrieve a valid token (from your scripts/apps)

```bash
curl -X POST \
  https://dazucslvjgtfxjoocnei.supabase.co/functions/v1/token \
  -H "Authorization: Bearer <TOKENBRIDGE_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"provider": "google-health", "user_id": "jack"}'
```

Response:

```json
{
  "access_token": "ya29.xxx",
  "expires_at": "2024-01-01T12:00:00.000Z",
  "scopes": ["https://www.googleapis.com/auth/fitness.activity.read", "..."],
  "provider": "google-health",
  "user_id": "jack",
  "refreshed": false
}
```

Tokens are auto-refreshed if they expire within 5 minutes. The `refreshed` flag tells you whether a refresh happened.

### Python example

```python
import requests, os

def get_token(provider: str, user_id: str) -> str:
    res = requests.post(
        "https://dazucslvjgtfxjoocnei.supabase.co/functions/v1/token",
        headers={"Authorization": f"Bearer {os.environ['TOKENBRIDGE_API_KEY']}"},
        json={"provider": provider, "user_id": user_id},
    )
    res.raise_for_status()
    return res.json()["access_token"]
```

---

## Adding a new provider

1. Add an entry to [`supabase/functions/_shared/providers.ts`](supabase/functions/_shared/providers.ts)
2. Add `<PROVIDER>_CLIENT_ID` and `<PROVIDER>_CLIENT_SECRET` to Supabase secrets
3. Register the callback URL with the provider:
   ```
   https://dazucslvjgtfxjoocnei.supabase.co/functions/v1/auth-callback
   ```

The three edge functions require no changes.

---

## Redeploying to a new Supabase project

1. Create a new Supabase project
2. Update `project_id` in `supabase/config.toml`
3. Update the callback URL in your OAuth app credentials
4. Run `supabase db push` and `supabase functions deploy`
5. Set secrets with `supabase secrets set`

---

## Security notes

- The `/token` endpoint is protected by `TOKENBRIDGE_API_KEY`. Keep this secret.
- The `/auth-start` and `/auth-callback` endpoints are public (required for OAuth).  
  `auth-start` is safe to expose — it only initiates a flow for a named `user_id`.
- Tokens are stored in plaintext in Postgres. Supabase encrypts data at rest.  
  For higher sensitivity, consider enabling [Supabase Vault](https://supabase.com/docs/guides/database/vault) to encrypt the `access_token` and `refresh_token` columns.
