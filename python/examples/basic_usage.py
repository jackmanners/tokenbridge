"""
Basic usage example.

Run after setup:
    python -m tokenbridge          # one-time setup
    python examples/basic_usage.py
"""

from tokenbridge import TokenBridge, GoogleHealth

# ── 1. Connect ────────────────────────────────────────────────────────────────

tb = TokenBridge()          # reads .env automatically
gh = GoogleHealth(tb)       # Google Health API wrapper

# ── 2. Onboard a new participant ──────────────────────────────────────────────

# Generate a link to send to one participant
url = tb.auth_url("participant-001")
print(f"Send this link to participant-001:\n  {url}\n")

# Or generate links for everyone at once
participants = ["p001", "p002", "p003"]
urls = tb.auth_urls(participants)
for pid, link in urls.items():
    print(f"  {pid}: {link}")

# ── 3. Check token status ─────────────────────────────────────────────────────

status = tb.token_status("p001")
print(f"\nToken expires: {status['expires_at']}")
print(f"Refreshed on this call: {status['refreshed']}")

# ── 4. Fetch data ─────────────────────────────────────────────────────────────

START = "2026-05-01"
END   = "2026-06-18"

sleep = gh.fetch_sleep("p001", START, END)
rr    = gh.fetch_respiratory_rate("p001", START, END)
hr    = gh.fetch_heart_rate("p001", START, END)

print(f"\nSleep sessions:          {len(sleep)}")
print(f"Respiratory rate points: {len(rr)}")
print(f"Resting heart rate days: {len(hr)}")

# Convert to pandas if available
try:
    import pandas as pd
    df_sleep = pd.DataFrame(sleep)
    print(f"\nSleep columns: {list(df_sleep.columns)}")
except ImportError:
    pass

# ── 5. Summary and audit ──────────────────────────────────────────────────────

# Single participant summary
s = gh.summary("p001", START, END)
print(f"\nSummary for p001 ({s['period_days']} days):")
print(f"  Sleep: {s['sleep']['n']} sessions, "
      f"{s['sleep']['coverage_pct']}% coverage")
print(f"  RR:    {s['respiratory_rate']['n']} measurements, "
      f"{s['respiratory_rate']['coverage_pct']}% coverage")

# Data completeness audit across all participants
audit = gh.data_completeness(participants, START, END)
print("\nData completeness audit:")
for row in audit:
    print(f"  {row['user_id']:10}  {row['data_type']:20}  "
          f"{row['coverage_pct']:5.1f}%  ({row['n']} records)")
