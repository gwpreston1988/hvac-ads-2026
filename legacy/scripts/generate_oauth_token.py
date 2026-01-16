#!/usr/bin/env python3

################################################################################
# LEGACY CODE - DO NOT USE
################################################################################
# This script is NOT part of the baseline pipeline. It has been quarantined in
# the legacy/ folder and should not be used for production operations.
#
# The baseline pipeline uses ONLY:
#   - core/dump/dump_state.py     (Phase A: live reads)
#   - core/report/generate_report.py  (Phase B: snapshot-only reports)
#   - core/plan/plan_changes.py   (Phase C: snapshot-only planning)
#   - core/apply/apply_changes.py (Phase C: live writes - with approval)
#
# If you need functionality from this script, consider:
#   1. Extracting it into a new core/ module with proper guardrails
#   2. Using it as reference for implementing new pipeline features
#   3. Consulting the team before running any legacy code
#
# Last quarantine date: 2026-01-16
################################################################################


"""
OAuth Token Generator for Google Ads + Merchant Center

Generates a refresh token with both scopes:
- https://www.googleapis.com/auth/adwords (Google Ads)
- https://www.googleapis.com/auth/content (Merchant Center)

Usage:
1. Run this script
2. Open the URL in your browser
3. Authorize the app
4. Paste the authorization code back here
5. Copy the new refresh token to your .env
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

# Scopes needed for both Google Ads and Merchant Center
SCOPES = [
    "https://www.googleapis.com/auth/adwords",
    "https://www.googleapis.com/auth/content",
]


def load_env():
    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path.home() / "BCD_SEO_Intelligence_Engine" / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"Loaded credentials from: {env_path}")
            return env_path
    print("ERROR: No .env file found")
    sys.exit(1)


def main():
    print("=" * 70)
    print("OAuth Token Generator - Google Ads + Merchant Center")
    print("=" * 70)
    print()

    env_path = load_env()

    client_id = os.getenv("GOOGLE_ADS_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("ERROR: Missing GOOGLE_ADS_CLIENT_ID or GOOGLE_ADS_CLIENT_SECRET")
        sys.exit(1)

    print(f"Client ID: {client_id[:20]}...")
    print()

    # Step 1: Generate authorization URL
    auth_params = {
        "client_id": client_id,
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "scope": " ".join(SCOPES),
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",  # Force consent to get new refresh token
    }

    auth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(auth_params)}"

    print("=" * 70)
    print("STEP 1: Open this URL in your browser and authorize:")
    print("=" * 70)
    print()
    print(auth_url)
    print()
    print("=" * 70)
    print()

    # Step 2: Get authorization code from user
    auth_code = input("STEP 2: Paste the authorization code here: ").strip()

    if not auth_code:
        print("ERROR: No authorization code provided")
        sys.exit(1)

    # Step 3: Exchange code for tokens
    print()
    print("Exchanging authorization code for tokens...")

    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        },
    )

    if token_response.status_code != 200:
        print(f"ERROR: Token exchange failed: {token_response.text}")
        sys.exit(1)

    tokens = token_response.json()
    refresh_token = tokens.get("refresh_token")
    access_token = tokens.get("access_token")

    if not refresh_token:
        print("ERROR: No refresh token received. Make sure you used prompt=consent")
        print(f"Response: {tokens}")
        sys.exit(1)

    print()
    print("=" * 70)
    print("SUCCESS! New tokens generated.")
    print("=" * 70)
    print()
    print("NEW REFRESH TOKEN (copy this to your .env):")
    print("-" * 70)
    print(refresh_token)
    print("-" * 70)
    print()
    print(f"Update your .env file: {env_path}")
    print("Replace the GOOGLE_ADS_REFRESH_TOKEN value with the token above.")
    print()

    # Verify token works for both APIs
    print("Verifying token works...")

    # Test Google Ads
    test_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )

    if test_response.status_code == 200:
        print("  ✓ Token refresh works")

        # Check scopes
        token_info = requests.get(
            f"https://oauth2.googleapis.com/tokeninfo?access_token={test_response.json()['access_token']}"
        )
        if token_info.status_code == 200:
            scopes = token_info.json().get("scope", "").split()
            print(f"  ✓ Authorized scopes: {', '.join(scopes)}")

            if "https://www.googleapis.com/auth/content" in scopes:
                print("  ✓ Merchant Center scope included!")
            else:
                print("  ⚠ Merchant Center scope NOT included")

            if "https://www.googleapis.com/auth/adwords" in scopes:
                print("  ✓ Google Ads scope included!")
            else:
                print("  ⚠ Google Ads scope NOT included")
    else:
        print(f"  ✗ Token test failed: {test_response.text}")

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
