"""
python -m tokenbridge — interactive setup wizard.

Prompts for your TokenBridge URL and API key, verifies the connection,
and saves both values to .env in the current directory.
"""

import sys
from pathlib import Path

import requests

ENV_FILE        = Path(".env")
DEFAULT_URL     = "https://YOUR_PROJECT_REF.supabase.co/functions/v1"


def _prompt(message: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value  = input(f"{message}{suffix}: ").strip()
    return value or default


def _save(url: str, api_key: str) -> None:
    """Write values to .env, preserving any other keys that may already be there."""
    lines = []
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            key = line.split("=")[0].strip()
            if key not in ("TOKENBRIDGE_URL", "TOKENBRIDGE_API_KEY"):
                lines.append(line)
    lines += [
        f"TOKENBRIDGE_URL={url}",
        f"TOKENBRIDGE_API_KEY={api_key}",
    ]
    ENV_FILE.write_text("\n".join(lines) + "\n")


def main() -> None:
    print("\n── TokenBridge setup ────────────────────────────────────────\n")

    url     = _prompt("TokenBridge URL", DEFAULT_URL)
    api_key = _prompt("API key")
    if not api_key:
        sys.exit("API key is required.")

    print("\nVerifying connection...", end=" ", flush=True)
    try:
        resp = requests.post(
            f"{url.rstrip('/')}/token",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"provider": "google-health", "user_id": "__probe__"},
            timeout=10,
        )
        if resp.status_code == 401:
            print("FAILED\n")
            sys.exit("Invalid API key.")
        # 404 = user not found — that's fine, it means the server and key are good
        print("OK")
    except requests.RequestException as e:
        print("FAILED\n")
        sys.exit(f"Could not reach {url}\n{e}")

    _save(url, api_key)
    print(f"\n✓ Saved to {ENV_FILE.resolve()}\n")
    print("Usage:\n")
    print("    from tokenbridge import TokenBridge")
    print("    tb = TokenBridge()")
    print()
    print("    # Send this URL to a participant to authorise their account:")
    print('    print(tb.auth_url("participant-001"))')
    print()
    print("    # Once they have authorised, fetch their data:")
    print('    sleep = tb.fetch_sleep("participant-001", "2026-05-01", "2026-06-18")')
    print('    rr    = tb.fetch_respiratory_rate("participant-001", "2026-05-01", "2026-06-18")')
    print()


if __name__ == "__main__":
    main()
