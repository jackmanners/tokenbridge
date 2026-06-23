# Using TokenBridge Without the Packages

If you'd rather not use the Python or R packages - or you're working in another language - you can drive the whole flow with plain HTTP. TokenBridge is just a few REST endpoints.

This page shows the minimal code to get from zero to a valid access token. What you do with it after that is up to you.

------------------------------------------------------------------------

## What you need

- Your TokenBridge deployment URL: `https://YOUR_PROJECT_REF.supabase.co/functions/v1`
- Your `TOKENBRIDGE_API_KEY`
- A provider set up (see [Setup Guide](basic-quickstart.md))

------------------------------------------------------------------------

## Step 1 - Onboard a participant

Generate an auth link and send it to them. This is just a URL - you can print it, email it, put it in a Qualtrics survey, whatever.

/// tab | Python

```         
:::python
TOKENBRIDGE_URL = "https://YOUR_PROJECT_REF.supabase.co/functions/v1"

user_id  = "p001"
provider = "google-health"   # or "withings", "oura"

auth_url = f"{TOKENBRIDGE_URL}/auth-start?provider={provider}&user_id={user_id}"
print(auth_url)
```

///

/// tab | R

```         
:::r
TOKENBRIDGE_URL <- "https://YOUR_PROJECT_REF.supabase.co/functions/v1"

user_id  <- "p001"
provider <- "google-health"   # or "withings", "oura"

auth_url <- paste0(TOKENBRIDGE_URL, "/auth-start?provider=", provider, "&user_id=", user_id)
cat(auth_url, "\n")
```

///

The participant clicks the link, signs in, approves access, and sees a success page. TokenBridge stores their token automatically. You don't need to do anything else on your end.

------------------------------------------------------------------------

## Step 2 - Get an access token

Once a participant has authorised, call the `/token` endpoint. TokenBridge handles refresh automatically - you always get back a usable token.

/// tab \| Python

```         
:::python
import requests

TOKENBRIDGE_URL = "https://YOUR_PROJECT_REF.supabase.co/functions/v1"
API_KEY         = "your-tokenbridge-api-key"

resp = requests.post(
    f"{TOKENBRIDGE_URL}/token",
    headers={"x-api-key": API_KEY},
    json={"user_id": "p001", "provider": "google-health"},
)
resp.raise_for_status()

access_token = resp.json()["access_token"]
```

///

/// tab \| R

```         
:::r
library(httr)

TOKENBRIDGE_URL <- "https://YOUR_PROJECT_REF.supabase.co/functions/v1"
API_KEY         <- "your-tokenbridge-api-key"

resp <- POST(
  paste0(TOKENBRIDGE_URL, "/token"),
  add_headers("x-api-key" = API_KEY),
  body   = list(user_id = "p001", provider = "google-health"),
  encode = "json"
)
stop_for_status(resp)

access_token <- content(resp)$access_token
```

///

That's it. From here you call the provider API directly using the token as a Bearer credential.

------------------------------------------------------------------------

## Step 3 - Call the provider API

Pass the token in an `Authorization: Bearer` header. Minimal example for each provider:

/// tab \| Google Health

```         
:::python
import requests

r = requests.get(
    "https://health.googleapis.com/v4/users/me/dataTypes/sleep/dataPoints",
    headers={"Authorization": f"Bearer {access_token}"},
)
print(r.json())

See the [Google Health API docs](https://developers.google.com/health/api) for the full endpoint list.
```

///

/// tab \| Withings

```         
:::python
import requests

r = requests.post(
    "https://wbsapi.withings.net/v2/measure",
    headers={"Authorization": f"Bearer {access_token}"},
    data={
        "action":       "getactivity",
        "startdateymd": "2026-05-01",
        "enddateymd":   "2026-06-18",
    },
)
print(r.json())   # {"status": 0, "body": {"activities": [...]}}

All Withings endpoints use POST with an `action` parameter. Status 0 = success.
```

///

/// tab \| Oura

```         
:::python
import requests

r = requests.get(
    "https://api.ouraring.com/v2/usercollection/daily_sleep",
    headers={"Authorization": f"Bearer {access_token}"},
    params={"start_date": "2026-05-01", "end_date": "2026-06-18"},
)
print(r.json())   # {"data": [...], "next_token": null}

Paginate using `next_token` if present in the response.
```

///

------------------------------------------------------------------------

## Token response format

The `/token` endpoint returns:

``` json
{
  "access_token": "ya29.xxxx",
  "expires_at": "2026-06-23T05:00:00.000Z"
}
```

`expires_at` is informational - TokenBridge refreshes automatically on the next call if the token is expired or close to expiry.