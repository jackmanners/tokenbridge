"""
test_token.py - personal dev script, not intended for end users.

Checks that tokens are valid and data is fetchable for both Google Health
and Withings providers. Prints a brief summary per provider.

Requires the Python package to be installed:
    cd python && pip install -e .

Set TOKENBRIDGE_URL and TOKENBRIDGE_API_KEY in .env before running.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))

from datetime import date, datetime, timedelta, timezone
from tokenbridge import TokenBridge

USER_ID = "jackmanners"
END     = date.today().isoformat()
START   = (date.today() - timedelta(days=7)).isoformat()

tb = TokenBridge()
print(f"TokenBridge: {tb.url}")
print(f"User:        {USER_ID}")
print(f"Window:      {START} → {END}\n")

for provider, data_type in (("google-health", "sleep"), ("withings", "sleep-summary")):
    try:
        records = tb.fetch(USER_ID, data_type, START, END, provider=provider)
        print(f"[OK]   {provider:20s}  {len(records)} records")

        if records:
            if provider == "withings":
                latest = max(records, key=lambda r: r.get("startdate", 0))
                start  = datetime.fromtimestamp(latest["startdate"], timezone.utc).strftime("%Y-%m-%d %H:%M")
                end    = datetime.fromtimestamp(latest["enddate"],   timezone.utc).strftime("%Y-%m-%d %H:%M")
                d      = latest.get("data") or {}
                mins    = d.get("total_sleep_time")
                ahi    = d.get("apnea_hypopnea_index")
                print(f"       latest:   {start} → {end}")
                print(f"       asleep: {f'{mins//3600}h {(mins%3600)//3600}m' if mins is not None else 'n/a'}"
                      f"   AHI: {ahi if ahi is not None else 'n/a'}")
            else:
                latest = max(records, key=lambda r: r.get("sleep.interval.endTime", ""))
                start  = latest.get("sleep.interval.startTime", "n/a")
                end    = latest.get("sleep.interval.endTime",   "n/a")
                mins   = latest.get("sleep.summary.minutesAsleep")
                print(f"       latest:   {start} → {end}")
                print(f"       asleep:   {f'{int(mins)//60}h {int(mins)%60}m' if mins else 'n/a'}")

    except Exception as e:
        print(f"[FAIL] {provider:20s}  {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"       {e.response.text[:300]}")
    print()
