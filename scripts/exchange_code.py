#!/usr/bin/env python3
"""
Quick OAuth code exchange - paste the auth code as argument.

Usage:
    python3 scripts/exchange_code.py "4/YOUR_AUTH_CODE_HERE"
"""

import sys
import requests

CLIENT_ID = "1070755483520-2tdobgljgts418rmpihsb67sddcshihi.apps.googleusercontent.com"
CLIENT_SECRET = "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"


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/exchange_code.py 'YOUR_AUTH_CODE'")
        sys.exit(1)

    auth_code = sys.argv[1].strip()
    print(f"Exchanging code: {auth_code[:20]}...")

    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        },
    )

    if response.status_code != 200:
        print(f"ERROR: {response.json()}")
        sys.exit(1)

    tokens = response.json()
    refresh_token = tokens.get("refresh_token")

    if not refresh_token:
        print("ERROR: No refresh token in response")
        print(f"Response: {tokens}")
        sys.exit(1)

    print()
    print("=" * 70)
    print("SUCCESS! Copy this REFRESH TOKEN to your .env:")
    print("=" * 70)
    print()
    print(refresh_token)
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
