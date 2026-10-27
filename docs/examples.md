# Examples

Three worked examples showing TokenBridge in realistic use. See [Getting Started](getting-started.md) for the step-by-step basics these build on.

---

## Cohort onboarding and compliance check (R)

A study with 50 participants. Generate each person's auth link, send it out, then check back weekly on who has actually synced data.

```r
library(tokenbridge)

participants <- c("p001", "p002", "p003")  # from your recruitment spreadsheet

# Onboarding - send each link by email/SMS
links <- tb_auth_urls(participants)
for (uid in names(links)) cat(uid, ":", links[[uid]], "\n")

# A week later - who's actually syncing?
audit <- gh_data_completeness(
  participants,
  start_date = "2026-05-01", end_date = "2026-06-18",
  data_types = c("sleep", "steps", "heart-rate-variability")
)

non_responders <- unique(audit$user_id[audit$coverage_pct == 0])
print(non_responders)  # follow up with these participants
```

`gh_data_completeness()` returns one row per participant per data type, with `coverage_pct` - the share of days in range that have at least one record. A participant who authorised but never opened the Fitbit app shows up here with `coverage_pct == 0`, distinct from one who never clicked the link at all (absent from `oauth_tokens` entirely).

---

## Sleep + blood pressure report for a clinician (Python)

A participant has been wearing a Withings sleep mat and using a Withings BP cuff for three months. Generate a single HTML report combining both, ready to attach to an email.

```python
import requests
from tokenbridge import TokenBridge
from tokenbridge.providers.withings import _fetch_all

tb = TokenBridge()
token = tb.get_token("p001", provider="withings")

sleep = _fetch_all(token, "sleep-summary",  "2026-01-01", "2026-03-31")
bp    = _fetch_all(token, "blood-pressure", "2026-01-01", "2026-03-31")

resp = requests.post(
    f"{tb.url}/sleep-report",
    headers={"Authorization": f"Bearer {tb.api_key}"},
    json={
        "label": "P001",
        "template": "sleep-bp",
        "data": {"withings-summary": sleep, "withings-bp": bp},
    },
)
open("p001_report.html", "wb").write(resp.content)
```

The result is a single, self-contained HTML file - no server round-trips needed to view it, and it opens fine as an email attachment. See [Reports](reports.md) for the available templates and how to write your own.

---

## Scheduled token refresh for a backend job (JS/TS)

A Node service that needs a fresh Withings token every night to pull the latest readings into your own database - no interactive participant flow, just a scheduled job hitting the provider API directly.

```ts
import { TokenBridge } from "tokenbridge";

const tb = new TokenBridge();

async function syncParticipant(userId: string) {
  const token = await tb.getToken(userId, "withings");

  // Params per the Withings API reference - https://developer.withings.com/api-reference/
  const res = await fetch("https://wbsapi.withings.net/measure", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: new URLSearchParams({ action: "getmeas", meastype: "1", startdate: "...", enddate: "..." }),
  });
  const { body } = await res.json();

  // ... persist body.measuregrps to your own store
}

for (const userId of ["p001", "p002", "p003"]) {
  await syncParticipant(userId);
}
```

`getToken()` refreshes transparently if the stored token is near expiry, so this can run on a plain cron schedule without any token-management logic of its own. This is the pattern the JS/TS package is built for - see its [API Spec](apispec-js.md).
