# Direct HTTP API Reference

TokenBridge is a small set of HTTP endpoints. The [Client Libraries](../clients/index.md) wrap them, but nothing stops you calling them directly - to build a client in another language, or to avoid a dependency entirely.

This page shows the minimal code to get from zero to a valid access token. What you do with it after that is up to you.

------------------------------------------------------------------------

## What you need

- Your TokenBridge deployment URL: `https://YOUR_PROJECT_REF.supabase.co/functions/v1`
- Your `TOKENBRIDGE_API_KEY`
- A provider set up (see [Deploying TokenBridge](deploying.md))

------------------------------------------------------------------------

## Step 1 - Onboard a participant

Generate an auth link and send it to them - by email, SMS, or embedded in a survey tool such as Qualtrics:

```
https://YOUR_PROJECT_REF.supabase.co/functions/v1/auth-start?provider=google-health&user_id=p001
```

`provider` is any configured provider ID (`google-health`, `withings`, `oura`, ...); `user_id` is whatever identifier you use for this participant. Nothing else is required - see [Platform → Security model](overview.md#security-model) for what that does and doesn't protect against, and generate links from a trusted source if that matters for your study.

The participant clicks the link, signs in, approves access, and sees a success page. TokenBridge stores their token automatically. You don't need to do anything else on your end.

------------------------------------------------------------------------

## Step 2 - Get an access token

Once a participant has authorised, call the `/token` endpoint. TokenBridge handles refresh automatically - you always get back a usable token.

/// tab | Python

    :::python
    import requests

    TOKENBRIDGE_URL = "https://YOUR_PROJECT_REF.supabase.co/functions/v1"
    API_KEY         = "your-tokenbridge-api-key"

    resp = requests.post(
        f"{TOKENBRIDGE_URL}/token",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"user_id": "p001", "provider": "google-health"},
    )
    resp.raise_for_status()

    access_token = resp.json()["access_token"]

///

/// tab | R

    :::r
    library(httr)

    TOKENBRIDGE_URL <- "https://YOUR_PROJECT_REF.supabase.co/functions/v1"
    API_KEY         <- "your-tokenbridge-api-key"

    resp <- POST(
      paste0(TOKENBRIDGE_URL, "/token"),
      add_headers(Authorization = paste("Bearer", API_KEY)),
      body   = list(user_id = "p001", provider = "google-health"),
      encode = "json"
    )
    stop_for_status(resp)

    access_token <- content(resp)$access_token

///

/// tab | Node.js

    :::javascript
    const TOKENBRIDGE_URL = "https://YOUR_PROJECT_REF.supabase.co/functions/v1";
    const API_KEY = "your-tokenbridge-api-key";

    const resp = await fetch(`${TOKENBRIDGE_URL}/token`, {
      method: "POST",
      headers: { Authorization: `Bearer ${API_KEY}`, "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: "p001", provider: "google-health" }),
    });

    const { access_token } = await resp.json();

///

That's it. From here you call the provider API directly using the token as a Bearer credential.

------------------------------------------------------------------------

## Step 3 - Call the provider API

Pass the token in an `Authorization: Bearer` header. Minimal example for each provider:

/// tab | Google Health

    :::python
    import requests

    r = requests.get(
        "https://health.googleapis.com/v4/users/me/dataTypes/sleep/dataPoints",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    print(r.json())

See the [Google Health API docs](https://developers.google.com/health/api) for the full endpoint list.

///

/// tab | Withings

    :::python
    import requests

    r = requests.get(
        "https://wbsapi.withings.net/v2/measure",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "action":       "getactivity",
            "startdateymd": "2026-05-01",
            "enddateymd":   "2026-06-18",
        },
    )
    print(r.json())   # {"status": 0, "body": {"activities": [...]}}

Every Withings endpoint takes an `action` parameter. Status 0 = success.

///

/// tab | Oura

    :::python
    import requests

    r = requests.get(
        "https://api.ouraring.com/v2/usercollection/daily_sleep",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"start_date": "2026-05-01", "end_date": "2026-06-18"},
    )
    print(r.json())   # {"data": [...], "next_token": null}

Paginate using `next_token` if present in the response.

///

------------------------------------------------------------------------

## Token response format

The `/token` endpoint returns:

``` json
{
  "access_token": "ya29.xxxx",
  "expires_at": "2026-06-23T05:00:00.000Z",
  "scopes": ["https://www.googleapis.com/auth/googlehealth.sleep.readonly"],
  "provider": "google-health",
  "user_id": "p001",
  "refreshed": false
}
```

`expires_at` is informational - TokenBridge refreshes automatically on the next call if the token is expired or close to expiry. `refreshed` tells you whether this call triggered a refresh. Some providers add extra fields here too - e.g. Withings adds `userid`, Strava adds `athlete_id`.

A 404 means the participant hasn't authorised yet; a 401 means their refresh token has expired and they need to re-authorise. Both responses include a `hint`/`error` field - see [`token/index.ts`](https://github.com/jackmanners/tokenbridge/blob/main/supabase/functions/token/index.ts) for the exact shape.