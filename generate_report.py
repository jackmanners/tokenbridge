"""Generate a sleep/BP report for a participant.

Usage:
    python generate_report.py <user_id> [options]

Examples:
    python generate_report.py p001
    python generate_report.py p001 --template sleep-bp
    python generate_report.py p001 --start 2026-06-01 --end 2026-07-01
    python generate_report.py p@lab.com --sleepscan
    python generate_report.py p001 --output reports/p001_june.html
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import requests
from tokenbridge import TokenBridge


def main():
    parser = argparse.ArgumentParser(description="Generate a TokenBridge health report.")
    parser.add_argument("user_id",                    help="Participant ID (or email/Withings ID with --sleepscan)")
    parser.add_argument("--template", default="full",
                        choices=["full", "sleep-bp", "bp"],
                        help="Report template (default: full)")
    parser.add_argument("--start",    default=None,   help="Start date YYYY-MM-DD (default: 90 days ago)")
    parser.add_argument("--end",      default=None,   help="End date YYYY-MM-DD (default: today)")
    parser.add_argument("--sleepscan", action="store_true",
                        help="Resolve Withings token via SleepScan instead of TokenBridge")
    parser.add_argument("--output",   default=None,   help="Output file path (default: report_<user_id>.html)")
    args = parser.parse_args()

    end   = args.end   or date.today().isoformat()
    start = args.start or (date.today() - timedelta(days=90)).isoformat()
    out   = Path(args.output) if args.output else Path(f"report_{args.user_id}.html")

    tb  = TokenBridge()
    tok = tb.get_token(args.user_id, provider="withings", sleepscan=args.sleepscan)

    def fetch(data_type):
        return tb.fetch(args.user_id, data_type, start, end,
                        provider="withings", token=tok)

    # Fetch only what the chosen template needs
    data = {}
    if args.template in ("full", "sleep-bp"):
        print(f"Fetching sleep-summary ({start} → {end})...")
        data["withings-summary"] = fetch("sleep-summary")
        print(f"  {len(data['withings-summary'])} records")

    if args.template in ("sleep-bp", "bp"):
        print(f"Fetching blood-pressure ({start} → {end})...")
        data["withings-bp"] = fetch("blood-pressure")
        print(f"  {len(data['withings-bp'])} records")

    print(f"Generating report (template: {args.template})...")
    resp = requests.post(
        f"{tb.url}/sleep-report",
        headers={"Authorization": f"Bearer {tb.api_key}"},
        json={"label": args.user_id, "template": args.template, "data": data},
    )
    resp.raise_for_status()

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(resp.content)
    print(f"Report saved to {out}")


if __name__ == "__main__":
    main()
