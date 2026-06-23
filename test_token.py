"""
test_token.py - personal dev script, not intended for end users.

Fetches sleep and respiratory rate for a single user and prints a preview.
Requires the Python package to be installed:
    cd python && pip install -e .

Set TOKENBRIDGE_URL and TOKENBRIDGE_API_KEY in .env before running.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))

from tokenbridge import TokenBridge, GoogleHealth

USER_ID    = "your_user_id"
START_DATE = "2026-05-01"
END_DATE   = "2026-06-18"

tb = TokenBridge()
gh = GoogleHealth(tb)

print(f"Fetching sleep for {USER_ID} ({START_DATE} → {END_DATE}) ...")
sleep = gh.fetch_sleep(USER_ID, START_DATE, END_DATE)
print(f"  {len(sleep)} sessions")
if sleep:
    print("  Keys:", list(sleep[0].keys())[:6], "...")

print(f"\nFetching respiratory rate for {USER_ID} ...")
rr = gh.fetch_respiratory_rate(USER_ID, START_DATE, END_DATE)
print(f"  {len(rr)} measurements")
if rr:
    print("  Keys:", list(rr[0].keys())[:6], "...")

print(f"\nSummary:")
s = gh.summary(USER_ID, START_DATE, END_DATE)
print(f"  Sleep:  {s['sleep']['n']} sessions, {s['sleep']['coverage_pct']}% coverage")
print(f"  RR:     {s['respiratory_rate']['n']} measurements, "
      f"{s['respiratory_rate']['coverage_pct']}% coverage")
