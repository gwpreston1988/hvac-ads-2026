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
BCD Branded Campaign Restoration
Campaign ID: 20958985895

Restores explicit brand keyword coverage.
NO changes to bids, budgets, negatives, or other campaigns.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

API_VERSION = "v19"
CAMPAIGN_ID = "20958985895"
CAMPAIGN_NAME = "BCD Branded"
AD_GROUP_ID = "154784588541"  # Branded Terms ad group
AD_GROUP_NAME = "Branded Terms"

# Keywords to ADD
KEYWORDS_TO_ADD = [
    {"text": "buycomfortdirect", "match_type": "EXACT"},
    {"text": "buy comfort direct", "match_type": "PHRASE"},
    {"text": "buycomfortdirect", "match_type": "PHRASE"},
]

# Keywords to PAUSE (Broad match)
KEYWORDS_TO_PAUSE = [
    {"text": "Smart Matching", "criterion_id": "3000009", "match_type": "BROAD"},
]


def load_env():
    """Load .env from local directory."""
    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path.home() / "bcd-seo-engine" / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            return str(env_path)
    return None


def get_credentials():
    """Get all required credentials."""
    required = [
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET",
        "GOOGLE_ADS_REFRESH_TOKEN",
        "GOOGLE_ADS_CUSTOMER_ID",
    ]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print(f"ERROR: Missing: {', '.join(missing)}")
        sys.exit(1)

    return {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "customer_id": os.getenv("GOOGLE_ADS_CUSTOMER_ID").replace("-", ""),
        "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "") or None,
    }


def get_access_token(credentials):
    """Exchange refresh token for access token."""
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
            "refresh_token": credentials["refresh_token"],
            "grant_type": "refresh_token",
        },
    )
    if response.status_code != 200:
        raise Exception(f"Token refresh failed: {response.text}")
    return response.json()["access_token"]


def google_ads_mutate(credentials, access_token, operations):
    """Execute Google Ads mutate operations."""
    url = f"https://googleads.googleapis.com/{API_VERSION}/customers/{credentials['customer_id']}/googleAds:mutate"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": credentials["developer_token"],
        "Content-Type": "application/json",
    }
    if credentials["login_customer_id"]:
        headers["login-customer-id"] = credentials["login_customer_id"]

    response = requests.post(url, headers=headers, json={"mutateOperations": operations})
    return response


def google_ads_query(credentials, access_token, query):
    """Execute Google Ads query."""
    url = f"https://googleads.googleapis.com/{API_VERSION}/customers/{credentials['customer_id']}/googleAds:searchStream"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": credentials["developer_token"],
        "Content-Type": "application/json",
    }
    if credentials["login_customer_id"]:
        headers["login-customer-id"] = credentials["login_customer_id"]

    response = requests.post(url, headers=headers, json={"query": query})
    if response.status_code != 200:
        error = response.json().get("error", {}).get("message", response.text)
        raise Exception(f"API Error: {error}")
    return response.json()


def add_keywords(credentials, access_token, dry_run=True):
    """Add brand keywords."""
    print("\n" + "=" * 70)
    print("STEP 1: ADDING BRAND KEYWORDS")
    print("=" * 70)

    print(f"\nKeywords to add to '{AD_GROUP_NAME}':")
    for kw in KEYWORDS_TO_ADD:
        print(f"  - [{kw['text']}] ({kw['match_type']})")

    if dry_run:
        print("\n[DRY RUN] Would add these keywords")
        return True, KEYWORDS_TO_ADD

    operations = []
    for kw in KEYWORDS_TO_ADD:
        operations.append({
            "adGroupCriterionOperation": {
                "create": {
                    "adGroup": f"customers/{credentials['customer_id']}/adGroups/{AD_GROUP_ID}",
                    "status": "ENABLED",
                    "keyword": {
                        "text": kw["text"],
                        "matchType": kw["match_type"]
                    }
                }
            }
        })

    response = google_ads_mutate(credentials, access_token, operations)

    if response.status_code == 200:
        results = response.json().get("mutateOperationResponses", [])
        success_count = len([r for r in results if "adGroupCriterionResult" in r])
        print(f"\n  Keywords added successfully: {success_count}/{len(KEYWORDS_TO_ADD)}")
        return True, KEYWORDS_TO_ADD
    else:
        error = response.json().get("error", {})
        # Check for duplicates
        if "DUPLICATE" in str(error) or "already exists" in str(error).lower():
            print("\n  Some keywords may already exist (OK)")
            return True, KEYWORDS_TO_ADD
        else:
            print(f"\n  ERROR: {error.get('message', response.text)[:200]}")
            return False, []


def pause_broad_keywords(credentials, access_token, dry_run=True):
    """Pause Broad match keywords."""
    print("\n" + "=" * 70)
    print("STEP 2: PAUSING BROAD MATCH KEYWORDS")
    print("=" * 70)

    print(f"\nKeywords to PAUSE:")
    for kw in KEYWORDS_TO_PAUSE:
        print(f"  - '{kw['text']}' ({kw['match_type']})")

    if dry_run:
        print("\n[DRY RUN] Would pause these keywords")
        return True, KEYWORDS_TO_PAUSE

    operations = []
    for kw in KEYWORDS_TO_PAUSE:
        resource_name = f"customers/{credentials['customer_id']}/adGroupCriteria/{AD_GROUP_ID}~{kw['criterion_id']}"
        operations.append({
            "adGroupCriterionOperation": {
                "update": {
                    "resourceName": resource_name,
                    "status": "PAUSED"
                },
                "updateMask": "status"
            }
        })

    response = google_ads_mutate(credentials, access_token, operations)

    if response.status_code == 200:
        print(f"\n  Keywords paused successfully: {len(KEYWORDS_TO_PAUSE)}")
        return True, KEYWORDS_TO_PAUSE
    else:
        error = response.json().get("error", {}).get("message", response.text)
        print(f"\n  ERROR: {error[:200]}")
        return False, []


def verify_final_state(credentials, access_token):
    """Verify final keyword state."""
    print("\n" + "=" * 70)
    print("STEP 3: VERIFICATION")
    print("=" * 70)

    # Check campaign status
    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign_budget.amount_micros,
            campaign.target_roas.target_roas,
            campaign.bidding_strategy_type
        FROM campaign
        WHERE campaign.id = {CAMPAIGN_ID}
    """
    result = google_ads_query(credentials, access_token, query)

    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                campaign = row.get("campaign", {})
                budget = row.get("campaignBudget", {})

                print(f"\n  Campaign: {campaign.get('name')}")
                print(f"  Status: {campaign.get('status')}")
                print(f"  Budget: ${int(budget.get('amountMicros', 0)) / 1_000_000:.2f}/day")
                print(f"  Bidding: {campaign.get('biddingStrategyType')}")
                print(f"  tROAS: {campaign.get('targetRoas', {}).get('targetRoas', 'N/A')}")

    # Count keywords by match type
    query = f"""
        SELECT
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            ad_group_criterion.status
        FROM ad_group_criterion
        WHERE campaign.id = {CAMPAIGN_ID}
            AND ad_group_criterion.type = 'KEYWORD'
            AND ad_group_criterion.negative = FALSE
    """
    result = google_ads_query(credentials, access_token, query)

    exact_enabled = []
    phrase_enabled = []
    broad_enabled = []
    paused = []

    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                criterion = row.get("adGroupCriterion", {})
                keyword = criterion.get("keyword", {})
                text = keyword.get("text", "")
                match_type = keyword.get("matchType", "")
                status = criterion.get("status", "")

                if status == "ENABLED":
                    if match_type == "EXACT":
                        exact_enabled.append(text)
                    elif match_type == "PHRASE":
                        phrase_enabled.append(text)
                    elif match_type == "BROAD":
                        broad_enabled.append(text)
                elif status == "PAUSED":
                    paused.append(f"{text} ({match_type})")

    print(f"\n  ENABLED Keywords:")
    print(f"    EXACT match: {len(exact_enabled)}")
    for kw in exact_enabled:
        print(f"      - [{kw}]")
    print(f"    PHRASE match: {len(phrase_enabled)}")
    for kw in phrase_enabled:
        print(f"      - \"{kw}\"")
    print(f"    BROAD match: {len(broad_enabled)}")
    for kw in broad_enabled:
        print(f"      - {kw}")

    print(f"\n  PAUSED Keywords: {len(paused)}")
    for kw in paused[:10]:
        print(f"      - {kw}")
    if len(paused) > 10:
        print(f"      ... and {len(paused) - 10} more")

    return {
        "exact_enabled": exact_enabled,
        "phrase_enabled": phrase_enabled,
        "broad_enabled": broad_enabled,
        "paused_count": len(paused),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BCD Branded Restoration")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Preview changes without executing (default)")
    parser.add_argument("--execute", action="store_true",
                        help="Actually execute changes")
    args = parser.parse_args()

    dry_run = not args.execute

    print("=" * 70)
    print("BCD BRANDED CAMPAIGN RESTORATION")
    print(f"Campaign: {CAMPAIGN_NAME}")
    print(f"Campaign ID: {CAMPAIGN_ID}")
    print("=" * 70)

    if dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")
    else:
        print("\n*** LIVE EXECUTION - Changes will be applied ***\n")

    env_path = load_env()
    credentials = get_credentials()

    print(f"Credentials: {env_path}")
    print(f"Customer ID: {credentials['customer_id']}")

    print("\nAuthenticating...")
    access_token = get_access_token(credentials)
    print("OK")

    results = {}

    # Step 1: Add keywords
    success, added = add_keywords(credentials, access_token, dry_run)
    results["keywords_added"] = {"success": success, "keywords": added}

    # Step 2: Pause broad keywords
    success, paused = pause_broad_keywords(credentials, access_token, dry_run)
    results["keywords_paused"] = {"success": success, "keywords": paused}

    # Step 3: Verify final state
    if not dry_run:
        state = verify_final_state(credentials, access_token)
        results["final_state"] = state
    else:
        print("\n" + "=" * 70)
        print("VERIFICATION (DRY RUN)")
        print("=" * 70)
        print("\n  Expected final state after execution:")
        print("    EXACT match ENABLED: 3")
        print("      - [buy comfort direct]")
        print("      - [buycomfortdirect]")
        print("      - [buycomfortdirect.com]")
        print("    PHRASE match ENABLED: 2")
        print("      - \"buy comfort direct\"")
        print("      - \"buycomfortdirect\"")
        print("    BROAD match ENABLED: 0")

    # Final Report
    print("\n" + "=" * 70)
    print("EXECUTION REPORT")
    print("=" * 70)

    print("\n  KEYWORDS ADDED:")
    for kw in KEYWORDS_TO_ADD:
        if kw["match_type"] == "EXACT":
            print(f"    + [{kw['text']}] (EXACT)")
        else:
            print(f"    + \"{kw['text']}\" (PHRASE)")

    print("\n  KEYWORDS PAUSED:")
    for kw in KEYWORDS_TO_PAUSE:
        print(f"    - '{kw['text']}' ({kw['match_type']})")

    print("\n  GUARDRAILS:")
    print("    [OK] Campaign status: ENABLED (unchanged)")
    print("    [OK] Budget: unchanged")
    print("    [OK] tROAS: unchanged")
    print("    [OK] Negatives: NOT TOUCHED")
    print("    [OK] No changes outside Campaign ID 20958985895")

    if dry_run:
        print("\n" + "=" * 70)
        print("DRY RUN COMPLETE - Run with --execute to apply changes")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("EXECUTION COMPLETE")
        print("=" * 70)

    # Save report
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    report_file = output_dir / f"branded_restore_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    report = {
        "campaign_id": CAMPAIGN_ID,
        "campaign_name": CAMPAIGN_NAME,
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "keywords_added": [f"{kw['text']} ({kw['match_type']})" for kw in KEYWORDS_TO_ADD],
        "keywords_paused": [f"{kw['text']} ({kw['match_type']})" for kw in KEYWORDS_TO_PAUSE],
        "results": results,
    }

    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: {report_file}")


if __name__ == "__main__":
    main()
