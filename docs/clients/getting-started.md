# Getting Started

Install a client library, connect it to an existing TokenBridge deployment, and onboard your first participant. If you're the one setting up the deployment itself, see [Platform → Deploying TokenBridge](../platform/deploying.md) first.

---

## Installation

/// tab | Python (bash)

    :::bash
    pip install git+https://github.com/jackmanners/tokenbridge.git#subdirectory=python

    Dependencies installed automatically: `requests`, `python-dotenv`.

///

/// tab | R

    :::r
    install.packages("devtools")
    devtools::install_github("jackmanners/tokenbridge", subdir = "r")

    Dependencies installed automatically: `httr`.

///

/// tab | JavaScript (bash)

    :::bash
    npm install "git+https://github.com/jackmanners/tokenbridge.git#path:js"

    Token retrieval only - no data-fetching layer, zero runtime dependencies. Requires Node ≥18.

///

---

## Configuration

Every client library needs two values to connect to your deployment:

| Variable | Description |
|---|---|
| `TOKENBRIDGE_URL` | Your deployment's base URL, e.g. `https://abcdef.supabase.co/functions/v1` |
| `TOKENBRIDGE_API_KEY` | The API key you set during deployment |

The recommended way to store these is in a `.env` file in your project directory. Run the setup wizard once:

/// tab | Python (bash)

    :::bash
    python -m tokenbridge

    # Requires Python 3.10+.
    # The wizard prompts for your URL and API key, verifies the connection, and saves them to `.env`.

///

/// tab | R

    :::r
    library(tokenbridge)
    tb_setup()

    # Requires R 4.0+.
    # Same as the Python wizard - prompts, verifies, saves to `.env`.

///

/// tab | JavaScript

    :::text
    # No setup wizard - create .env by hand:
    TOKENBRIDGE_URL=https://abcdef.supabase.co/functions/v1
    TOKENBRIDGE_API_KEY=your-api-key

///

!!! warning "Keep .env out of version control"
    Your `.env` file contains your API key. Make sure `.env` is in your `.gitignore`.
    This repo's [`.gitignore`](https://github.com/jackmanners/tokenbridge/blob/main/.gitignore) already excludes it, but make sure for repo clones.

### Manual configuration

If you prefer not to use `.env`, pass credentials directly:

/// tab | Python

    :::python
    from tokenbridge import TokenBridge

    tb = TokenBridge(
        url="https://abcdef.supabase.co/functions/v1",
        api_key="your-api-key",
    )

///

/// tab | R

    :::r
    Sys.setenv(
      TOKENBRIDGE_URL     = "https://abcdef.supabase.co/functions/v1",
      TOKENBRIDGE_API_KEY = "your-api-key"
    )
    library(tokenbridge)

///

/// tab | JavaScript

    :::ts
    import { TokenBridge } from "tokenbridge";

    const tb = new TokenBridge({
      url: "https://abcdef.supabase.co/functions/v1",
      apiKey: "your-api-key",
    });

///

---

## Onboarding participants

Each participant needs to authorise their account once. Generate a unique link for each person and send it to them (email, SMS, or embedded in a survey tool).

/// tab | Python

    :::python
    from tokenbridge import TokenBridge

    tb = TokenBridge()

    # Single participant
    url = tb.auth_url("participant-001")
    print(url)

    # Batch - returns {user_id: url}
    urls = tb.auth_urls(["p001", "p002", "p003", "p004"])
    for uid, url in urls.items():
        print(f"{uid}: {url}")

///

/// tab | R

    :::r
    # Single participant
    tb_auth_url("participant-001")

    # Batch - returns named character vector
    urls <- tb_auth_urls(c("p001", "p002", "p003", "p004"))
    for (uid in names(urls)) cat(uid, ":", urls[[uid]], "\n")

///

/// tab | JavaScript

    :::ts
    // Single participant
    const url = tb.authUrl("participant-001");
    console.log(url);

    // Batch - returns Record<user_id, url>
    const urls = tb.authUrls(["p001", "p002", "p003", "p004"]);
    for (const [uid, url] of Object.entries(urls)) console.log(`${uid}: ${url}`);

///

The participant:

1. Clicks the link
2. Signs in with their account (Google for Fitbit, Withings, or Oura)
3. Approves the requested permissions
4. Sees a success page - done

!!! note "Google Health / Fitbit"
    Participants must have the **Fitbit app** installed and signed in with the same Google account they use to authorise. Without this, there is no health data to access.

!!! note "Test mode warning"
    If your Google Cloud app is in Testing mode (the default for new deployments), participants will see an "unverified app" warning. They should click **Advanced → Go to [app name] (unsafe)** to proceed. This is expected - see [Platform Overview](../platform/overview.md#consent-screen-and-verification) for context.

---

## Getting a token

Once a participant has authorised, retrieve a token immediately:

/// tab | Python

    :::python
    token = tb.get_token("p001")

///

/// tab | R

    :::r
    tok <- tb_get_token("p001")

///

/// tab | JavaScript

    :::ts
    const token = await tb.getToken("p001");

///

That's the entire R and JavaScript packages - call the provider's API directly with the token from here. Python can either do the same, or use the built-in [Data-Fetching Guide](data-fetching.md) convenience layer:

```python
sleep = tb.fetch("p001", "sleep", "2026-05-01", "2026-06-18", token=token)
```

## Next steps

- [Token API Reference](token-reference.md) - exact signatures and errors for every function used above
- [Data-Fetching Guide](data-fetching.md) - Python's convenience layer, cohort auditing, reports, SleepScan
- [Examples](examples.md) - complete, realistic scripts
