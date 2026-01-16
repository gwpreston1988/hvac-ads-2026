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
