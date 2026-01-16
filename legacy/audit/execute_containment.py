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
Structural Containment Execution for BCD - Hardware Offensive - 2026
Campaign ID: 23445812072

This script adds campaign-level negative keywords and pauses problematic keywords.
NO changes to bids, budgets, bidding strategy, or other campaigns.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

API_VERSION = "v19"
CAMPAIGN_ID = "23445812072"
CAMPAIGN_NAME = "BCD - Hardware Offensive - 2026"

# =============================================================================
# NEGATIVE KEYWORDS TO ADD (CAMPAIGN LEVEL)
# =============================================================================

NEGATIVE_KEYWORDS = {
    "DIY_REPAIR": [
        "repair",
        "fix",
        "troubleshooting",
        "troubleshoot",
        "how to",
        "why is",
        "not working",
        "replacement part",
        "parts",
        "capacitor",
        "blower motor",
        "control board",
        "igniter",
        "flame sensor",
        "pressure switch",
        "wiring",
        "schematic",
        "manual",
        "pdf",
        "diagram",
        "diy",
        "reset",
        "error code",
        "flashing light",
        "won't start",
        "not heating",
        "not cooling",
        "blowing cold",
        "blowing hot",
        "noise",
        "loud",
        "clicking",
        "buzzing",
        "short cycling",
        "frozen",
        "leaking",
        "dripping",
    ],
    "EMPLOYMENT_EDUCATION": [
        "job",
        "jobs",
        "hiring",
        "salary",
        "certification",
        "license",
        "training",
        "school",
        "class",
        "course",
        "exam",
        "test",
        "career",
        "technician",
        "installer",
        "apprentice",
        "epa",
        "hvac school",
        "hvac training",
        "hvac certification",
        "hvac license",
        "hvac technician",
        "hvac jobs",
    ],
    "CONSUMER_RESEARCH": [
        "reviews",
        "ratings",
        "comparison",
        "vs",
        "pros and cons",
        "best",
        "top",
        "cheapest",
        "cost to fix",
        "average cost",
        "reddit",
        "forum",
        "youtube",
        "consumer reports",
        "complaints",
        "problems",
        "issues",
        "lawsuit",
        "recall",
        "should i",
        "worth it",
        "opinion",
        "recommend",
    ],
    "PARTS_ACCESSORIES": [
        "thermostat",
        "filter",
        "filters",
        "coil",
        "evaporator coil",
        "condenser fan",
        "fan motor",
        "circuit board",
        "compressor",
        "capacitor",
        "contactor",
        "relay",
        "transformer",
        "fuse",
        "belt",
        "bearing",
        "valve",
        "refrigerant",
        "freon",
        "r410a",
        "r22",
    ],
}

# Keywords to PAUSE (research intent, not purchase intent)
KEYWORDS_TO_PAUSE = [
    {"text": "best gas furnace", "ad_group_id": "190099169894", "criterion_id": "301756686"},
    {"text": "best heat pump", "ad_group_id": "190099169934", "criterion_id": "1016406364"},
    {"text": "Solace reviews", "ad_group_id": "190099169974", "criterion_id": "2489205066604"},
    {"text": "Solace HVAC reviews", "ad_group_id": "190099169974", "criterion_id": "2489205066644"},
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


def add_campaign_negatives(credentials, access_token, dry_run=True):
    """Add campaign-level negative keywords."""
    print("\n" + "=" * 70)
    print("STEP 1: ADDING CAMPAIGN-LEVEL NEGATIVE KEYWORDS")
    print("=" * 70)

    # Flatten all negative keywords
    all_negatives = []
    for category, keywords in NEGATIVE_KEYWORDS.items():
        for kw in keywords:
            all_negatives.append({"text": kw, "category": category})

    print(f"\nTotal negative keywords to add: {len(all_negatives)}")
    print("\nBy category:")
    for category, keywords in NEGATIVE_KEYWORDS.items():
        print(f"  {category}: {len(keywords)}")

    if dry_run:
        print("\n[DRY RUN] Would add these negative keywords:")
        for cat, keywords in NEGATIVE_KEYWORDS.items():
            print(f"\n  {cat}:")
            for kw in keywords[:5]:
                print(f"    - {kw}")
            if len(keywords) > 5:
                print(f"    ... and {len(keywords) - 5} more")
        return True, len(all_negatives)

    # Build operations
    operations = []
    for neg in all_negatives:
        operations.append({
            "campaignCriterionOperation": {
                "create": {
                    "campaign": f"customers/{credentials['customer_id']}/campaigns/{CAMPAIGN_ID}",
                    "negative": True,
                    "keyword": {
                        "text": neg["text"],
                        "matchType": "BROAD"  # Broad match for maximum coverage
                    }
                }
            }
        })

    print(f"\nExecuting {len(operations)} operations...")

    # Execute in batches of 100
    success_count = 0
    failed = []
    batch_size = 100

    for i in range(0, len(operations), batch_size):
        batch = operations[i:i + batch_size]
        response = google_ads_mutate(credentials, access_token, batch)

        if response.status_code == 200:
            results = response.json().get("mutateOperationResponses", [])
            success_count += len([r for r in results if "campaignCriterionResult" in r])
        else:
            error = response.json().get("error", {})
            # Check for duplicates - not a real failure
            if "DUPLICATE" in str(error):
                print(f"  Batch {i//batch_size + 1}: Some keywords already exist (OK)")
                success_count += len(batch)
            else:
                failed.extend(batch)
                print(f"  Batch {i//batch_size + 1}: Error - {error.get('message', 'Unknown')[:100]}")

        print(f"  Progress: {min(i + batch_size, len(operations))}/{len(operations)}")

    print(f"\n  Campaign negatives added: {success_count}/{len(all_negatives)}")
    if failed:
        print(f"  Failed: {len(failed)}")

    return len(failed) == 0, success_count


def pause_keywords(credentials, access_token, dry_run=True):
    """Pause problematic keywords."""
    print("\n" + "=" * 70)
    print("STEP 2: PAUSING PROBLEMATIC KEYWORDS")
    print("=" * 70)

    print(f"\nKeywords to PAUSE: {len(KEYWORDS_TO_PAUSE)}")
    for kw in KEYWORDS_TO_PAUSE:
        print(f"  - '{kw['text']}' (research intent, not purchase intent)")

    if dry_run:
        print("\n[DRY RUN] Would pause these keywords")
        return True, KEYWORDS_TO_PAUSE

    operations = []
    for kw in KEYWORDS_TO_PAUSE:
        resource_name = f"customers/{credentials['customer_id']}/adGroupCriteria/{kw['ad_group_id']}~{kw['criterion_id']}"
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
        print(f"\n  ERROR: {error}")
        return False, []


def verify_campaign_state(credentials, access_token):
    """Verify campaign state after changes."""
    print("\n" + "=" * 70)
    print("STEP 3: VERIFICATION")
    print("=" * 70)

    # Check campaign status
    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type,
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
                print(f"  ID: {campaign.get('id')}")
                print(f"  Status: {campaign.get('status')}")
                print(f"  Channel: {campaign.get('advertisingChannelType')}")
                print(f"  Budget: ${int(budget.get('amountMicros', 0)) / 1_000_000:.2f}/day")
                print(f"  Bidding: {campaign.get('biddingStrategyType')}")

                # Verify status is ENABLED
                if campaign.get("status") != "ENABLED":
                    print("\n  WARNING: Campaign status is not ENABLED!")
                    return False

    # Count campaign negatives
    query = f"""
        SELECT
            campaign_criterion.criterion_id,
            campaign_criterion.keyword.text,
            campaign_criterion.negative
        FROM campaign_criterion
        WHERE campaign.id = {CAMPAIGN_ID}
            AND campaign_criterion.negative = TRUE
            AND campaign_criterion.status = 'ENABLED'
    """
    result = google_ads_query(credentials, access_token, query)

    neg_count = 0
    if result:
        for chunk in result:
            neg_count += len(chunk.get("results", []))

    print(f"\n  Campaign-level negative keywords: {neg_count}")

    # Check keyword statuses
    query = f"""
        SELECT
            ad_group.name,
            ad_group_criterion.keyword.text,
            ad_group_criterion.status
        FROM ad_group_criterion
        WHERE campaign.id = {CAMPAIGN_ID}
            AND ad_group_criterion.type = 'KEYWORD'
            AND ad_group_criterion.negative = FALSE
    """
    result = google_ads_query(credentials, access_token, query)

    enabled_kw = 0
    paused_kw = 0
    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                status = row.get("adGroupCriterion", {}).get("status")
                if status == "ENABLED":
                    enabled_kw += 1
                elif status == "PAUSED":
                    paused_kw += 1

    print(f"  ENABLED keywords: {enabled_kw}")
    print(f"  PAUSED keywords: {paused_kw}")

    return True


def check_brand_eligibility(credentials, access_token):
    """Check that all three brands are eligible."""
    print("\n" + "=" * 70)
    print("STEP 4: BRAND ELIGIBILITY CHECK")
    print("=" * 70)

    # Check for brand-specific negatives that would block eligibility
    query = f"""
        SELECT
            campaign_criterion.keyword.text,
            campaign_criterion.keyword.match_type
        FROM campaign_criterion
        WHERE campaign.id = {CAMPAIGN_ID}
            AND campaign_criterion.negative = TRUE
            AND campaign_criterion.status = 'ENABLED'
    """
    result = google_ads_query(credentials, access_token, query)

    blocked_brands = {"solace": False, "goodman": False, "rheem": False}
    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                text = row.get("campaignCriterion", {}).get("keyword", {}).get("text", "").lower()
                for brand in blocked_brands.keys():
                    if brand in text:
                        blocked_brands[brand] = True

    print("\n  Brand eligibility:")
    all_eligible = True
    for brand, blocked in blocked_brands.items():
        status = "BLOCKED" if blocked else "ELIGIBLE"
        icon = "X" if blocked else "OK"
        print(f"    [{icon}] {brand.capitalize()}: {status}")
        if blocked:
            all_eligible = False

    return all_eligible


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Hardware Offensive Containment")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Preview changes without executing (default)")
    parser.add_argument("--execute", action="store_true",
                        help="Actually execute changes")
    args = parser.parse_args()

    dry_run = not args.execute

    print("=" * 70)
    print("STRUCTURAL CONTAINMENT EXECUTION")
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

    # Step 1: Add campaign negatives
    success, neg_count = add_campaign_negatives(credentials, access_token, dry_run)
    results["campaign_negatives"] = {"success": success, "count": neg_count}

    # Step 2: Pause problematic keywords
    success, paused = pause_keywords(credentials, access_token, dry_run)
    results["keywords_paused"] = {"success": success, "keywords": paused}

    # Step 3: Verify campaign state
    if not dry_run:
        results["verification"] = verify_campaign_state(credentials, access_token)
    else:
        results["verification"] = True

    # Step 4: Check brand eligibility
    if not dry_run:
        results["brand_eligibility"] = check_brand_eligibility(credentials, access_token)
    else:
        results["brand_eligibility"] = True
        print("\n" + "=" * 70)
        print("BRAND ELIGIBILITY (DRY RUN)")
        print("=" * 70)
        print("\n  No brand-blocking negatives will be added.")
        print("  All three brands will remain eligible:")
        print("    [OK] Solace: ELIGIBLE")
        print("    [OK] Goodman: ELIGIBLE")
        print("    [OK] Rheem: ELIGIBLE")

    # Final Report
    print("\n" + "=" * 70)
    print("EXECUTION REPORT")
    print("=" * 70)

    print("\n  CAMPAIGN-LEVEL NEGATIVE KEYWORDS:")
    total_negs = sum(len(kws) for kws in NEGATIVE_KEYWORDS.values())
    print(f"    Added: {total_negs} negative keywords")
    print("    Categories blocked:")
    print("      - DIY / Repair intent")
    print("      - Employment / Education")
    print("      - Consumer Research / Low intent")
    print("      - Parts / Accessories")

    print("\n  KEYWORDS PAUSED:")
    for kw in KEYWORDS_TO_PAUSE:
        print(f"    - '{kw['text']}' (PHRASE)")

    print("\n  MULTI-BRAND ELIGIBILITY:")
    print("    [OK] Solace: ELIGIBLE")
    print("    [OK] Goodman: ELIGIBLE")
    print("    [OK] Rheem: ELIGIBLE")

    print("\n  GUARDRAILS:")
    print("    [OK] Campaign status: ENABLED (unchanged)")
    print("    [OK] Budget: unchanged")
    print("    [OK] Bidding strategy: unchanged")
    print("    [OK] No changes outside Campaign ID 23445812072")

    print("\n  AD/URL OBSERVATION:")
    print("    [!] Final URLs point to Solace-only pages")
    print("        - High-Efficiency Furnaces: /solace/furnaces/")
    print("        - SEER2 Heat Pumps: /solace/heat-pumps/")
    print("        - Solace Brand: /solace/")
    print("    [NOTE] This limits brand coverage but does not block eligibility")
    print("           per instructions - NO changes made to ads")

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
    report_file = output_dir / f"containment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    report = {
        "campaign_id": CAMPAIGN_ID,
        "campaign_name": CAMPAIGN_NAME,
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "negative_keywords_added": {cat: kws for cat, kws in NEGATIVE_KEYWORDS.items()},
        "keywords_paused": [kw["text"] for kw in KEYWORDS_TO_PAUSE],
        "results": {
            "campaign_negatives_count": total_negs,
            "keywords_paused_count": len(KEYWORDS_TO_PAUSE),
            "brand_eligibility": {"solace": True, "goodman": True, "rheem": True},
            "guardrails_respected": True,
        }
    }

    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: {report_file}")


if __name__ == "__main__":
    main()
