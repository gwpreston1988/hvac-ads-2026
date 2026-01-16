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
Automated Budget Balancer

Monitors ROAS across campaigns and recommends budget shifts.
Logic: If Non-Branded campaign hits target ROAS, shift budget from Branded.

Run daily to track diminishing returns curve.
"""

import csv
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

# API version
API_VERSION = "v19"

# Configuration
TARGET_ROAS = 4.0  # Target ROAS to trigger budget shift
SHIFT_PERCENT = 0.05  # 5% budget shift per day
MIN_BRANDED_BUDGET_PERCENT = 0.30  # Never go below 30% of original branded budget
LOOKBACK_DAYS = 30  # Days to calculate ROAS

# Campaign patterns
BRANDED_PATTERNS = ["branded", "brand", "bcd branded"]
NONBRANDED_PATTERNS = ["non-brand", "nonbrand", "generic", "category"]
PMAX_PATTERNS = ["performance_max", "pmax", "merchant"]


def load_env():
    """Load .env from local directory or fallback locations."""
    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path.home() / "BCD_SEO_Intelligence_Engine" / ".env",
        Path(__file__).parent.parent.parent / "apps" / "api" / ".env",
        Path(__file__).parent.parent.parent / ".env",
    ]

    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"Loaded credentials from: {env_path}")
            return

    print("WARNING: No .env file found")


def get_credentials():
    """Get Google Ads credentials from environment."""
    required = [
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET",
        "GOOGLE_ADS_REFRESH_TOKEN",
        "GOOGLE_ADS_CUSTOMER_ID",
    ]

    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
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


def google_ads_query(credentials, access_token, query):
    """Execute Google Ads query via REST API."""
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
        raise Exception(f"API Error ({response.status_code}): {error}")

    return response.json()


def classify_campaign(campaign_name):
    """Classify campaign type based on name patterns."""
    name_lower = campaign_name.lower()

    if any(p in name_lower for p in BRANDED_PATTERNS):
        return "branded"
    elif any(p in name_lower for p in NONBRANDED_PATTERNS):
        return "nonbranded"
    elif any(p in name_lower for p in PMAX_PATTERNS):
        return "pmax"
    else:
        return "other"


def get_campaign_performance(credentials, access_token, days=7):
    """Get campaign performance metrics."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type,
            campaign_budget.amount_micros,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value,
            metrics.impressions,
            metrics.clicks
        FROM campaign
        WHERE campaign.status = 'ENABLED'
            AND segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
    """

    print(f"Fetching campaign performance ({days} days)...")
    result = google_ads_query(credentials, access_token, query)

    campaigns = {}

    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                campaign = row.get("campaign", {})
                budget = row.get("campaignBudget", {})
                metrics = row.get("metrics", {})

                campaign_id = campaign.get("id")
                if campaign_id not in campaigns:
                    campaigns[campaign_id] = {
                        "id": campaign_id,
                        "name": campaign.get("name"),
                        "status": campaign.get("status"),
                        "channel_type": campaign.get("advertisingChannelType"),
                        "daily_budget": int(budget.get("amountMicros", 0)) / 1_000_000,
                        "cost": 0,
                        "conversions": 0,
                        "conv_value": 0,
                        "impressions": 0,
                        "clicks": 0,
                    }

                # Aggregate metrics
                campaigns[campaign_id]["cost"] += int(metrics.get("costMicros", 0)) / 1_000_000
                campaigns[campaign_id]["conversions"] += float(metrics.get("conversions", 0))
                campaigns[campaign_id]["conv_value"] += float(metrics.get("conversionsValue", 0))
                campaigns[campaign_id]["impressions"] += int(metrics.get("impressions", 0))
                campaigns[campaign_id]["clicks"] += int(metrics.get("clicks", 0))

    # Calculate derived metrics and classify
    for c in campaigns.values():
        c["roas"] = c["conv_value"] / c["cost"] if c["cost"] > 0 else 0
        c["cpa"] = c["cost"] / c["conversions"] if c["conversions"] > 0 else 0
        c["ctr"] = c["clicks"] / c["impressions"] if c["impressions"] > 0 else 0
        c["conv_rate"] = c["conversions"] / c["clicks"] if c["clicks"] > 0 else 0
        c["type"] = classify_campaign(c["name"])

    return list(campaigns.values())


def load_budget_history():
    """Load historical budget tracking data."""
    history_path = Path(__file__).parent.parent / "output" / "budget_history.json"

    if history_path.exists():
        with open(history_path) as f:
            return json.load(f)

    return {"entries": [], "original_budgets": {}}


def save_budget_history(history):
    """Save budget tracking data."""
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    history_path = output_dir / "budget_history.json"
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2, default=str)


def calculate_recommendation(campaigns, history):
    """Calculate budget shift recommendation based on ROAS."""
    branded = [c for c in campaigns if c["type"] == "branded"]
    nonbranded = [c for c in campaigns if c["type"] == "nonbranded"]
    pmax = [c for c in campaigns if c["type"] == "pmax"]

    # Aggregate by type
    def aggregate(camp_list):
        if not camp_list:
            return {"cost": 0, "conv_value": 0, "conversions": 0, "budget": 0, "roas": 0}

        total = {
            "cost": sum(c["cost"] for c in camp_list),
            "conv_value": sum(c["conv_value"] for c in camp_list),
            "conversions": sum(c["conversions"] for c in camp_list),
            "budget": sum(c["daily_budget"] for c in camp_list),
        }
        total["roas"] = total["conv_value"] / total["cost"] if total["cost"] > 0 else 0
        return total

    branded_agg = aggregate(branded)
    nonbranded_agg = aggregate(nonbranded)
    pmax_agg = aggregate(pmax)

    # Store original budgets if first run
    if not history.get("original_budgets"):
        history["original_budgets"] = {
            "branded": branded_agg["budget"],
            "nonbranded": nonbranded_agg["budget"],
            "pmax": pmax_agg["budget"],
        }

    recommendation = {
        "date": datetime.now().isoformat(),
        "branded": branded_agg,
        "nonbranded": nonbranded_agg,
        "pmax": pmax_agg,
        "action": "hold",
        "shift_amount": 0,
        "reason": "",
    }

    # Decision logic
    if nonbranded_agg["roas"] >= TARGET_ROAS and branded_agg["budget"] > 0:
        # Non-branded hitting target - consider shifting from branded
        original_branded = history["original_budgets"].get("branded", branded_agg["budget"])
        min_branded = original_branded * MIN_BRANDED_BUDGET_PERCENT

        if branded_agg["budget"] > min_branded:
            shift_amount = branded_agg["budget"] * SHIFT_PERCENT
            recommendation["action"] = "shift_to_nonbranded"
            recommendation["shift_amount"] = shift_amount
            recommendation["reason"] = f"Non-branded ROAS ({nonbranded_agg['roas']:.2f}) >= target ({TARGET_ROAS})"
        else:
            recommendation["action"] = "hold"
            recommendation["reason"] = f"Branded budget at minimum threshold ({MIN_BRANDED_BUDGET_PERCENT:.0%})"

    elif pmax_agg["roas"] >= TARGET_ROAS and branded_agg["budget"] > 0:
        # PMax hitting target - consider shifting
        original_branded = history["original_budgets"].get("branded", branded_agg["budget"])
        min_branded = original_branded * MIN_BRANDED_BUDGET_PERCENT

        if branded_agg["budget"] > min_branded:
            shift_amount = branded_agg["budget"] * SHIFT_PERCENT
            recommendation["action"] = "shift_to_pmax"
            recommendation["shift_amount"] = shift_amount
            recommendation["reason"] = f"PMax ROAS ({pmax_agg['roas']:.2f}) >= target ({TARGET_ROAS})"
        else:
            recommendation["action"] = "hold"
            recommendation["reason"] = f"Branded budget at minimum threshold"

    elif nonbranded_agg["roas"] < TARGET_ROAS * 0.8:
        # Non-branded underperforming - consider pulling back
        recommendation["action"] = "review_nonbranded"
        recommendation["reason"] = f"Non-branded ROAS ({nonbranded_agg['roas']:.2f}) below threshold"

    else:
        recommendation["action"] = "hold"
        recommendation["reason"] = "Current allocation optimal"

    return recommendation


def main():
    print("=" * 70)
    print("Budget Balancer - ROAS Optimization")
    print("=" * 70)
    print()
    print(f"Configuration:")
    print(f"  Target ROAS: {TARGET_ROAS}")
    print(f"  Shift percentage: {SHIFT_PERCENT:.0%}")
    print(f"  Min branded budget: {MIN_BRANDED_BUDGET_PERCENT:.0%}")
    print(f"  Lookback period: {LOOKBACK_DAYS} days")
    print()

    load_env()
    credentials = get_credentials()
    print(f"Customer ID: {credentials['customer_id']}")
    print()

    print("Authenticating...")
    access_token = get_access_token(credentials)
    print("OK")
    print()

    # Get campaign performance
    campaigns = get_campaign_performance(credentials, access_token, days=LOOKBACK_DAYS)
    print(f"Found {len(campaigns)} active campaigns")
    print()

    # Load history
    history = load_budget_history()

    # Calculate recommendation
    recommendation = calculate_recommendation(campaigns, history)

    # Add to history
    history["entries"].append(recommendation)
    save_budget_history(history)

    # Output CSV
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    campaigns_csv = output_dir / f"campaign_performance_{timestamp}.csv"
    with open(campaigns_csv, "w", newline="") as f:
        if campaigns:
            writer = csv.DictWriter(f, fieldnames=campaigns[0].keys())
            writer.writeheader()
            writer.writerows(campaigns)
    print(f"Campaign performance CSV: {campaigns_csv}")
    print()

    # Summary
    print("=" * 70)
    print("CURRENT PERFORMANCE")
    print("=" * 70)
    print()

    # By campaign type
    for ctype in ["branded", "nonbranded", "pmax", "other"]:
        type_campaigns = [c for c in campaigns if c["type"] == ctype]
        if type_campaigns:
            total_cost = sum(c["cost"] for c in type_campaigns)
            total_value = sum(c["conv_value"] for c in type_campaigns)
            total_conv = sum(c["conversions"] for c in type_campaigns)
            total_budget = sum(c["daily_budget"] for c in type_campaigns)
            roas = total_value / total_cost if total_cost > 0 else 0

            print(f"{ctype.upper()}:")
            print(f"  Campaigns: {len(type_campaigns)}")
            print(f"  Daily Budget: ${total_budget:,.2f}")
            print(f"  Spend ({LOOKBACK_DAYS}d): ${total_cost:,.2f}")
            print(f"  Conversions: {total_conv:.0f}")
            print(f"  ROAS: {roas:.2f}")
            print()

    # Individual campaigns
    print("CAMPAIGN DETAILS:")
    print("-" * 70)
    print(f"{'Campaign':<35} {'Type':<12} {'Budget':<10} {'ROAS':<8}")
    print("-" * 70)
    for c in sorted(campaigns, key=lambda x: x["cost"], reverse=True):
        name_short = c["name"][:33]
        print(f"{name_short:<35} {c['type']:<12} ${c['daily_budget']:<9.2f} {c['roas']:<8.2f}")
    print()

    # Recommendation
    print("=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)
    print()
    print(f"Action: {recommendation['action'].upper()}")
    print(f"Reason: {recommendation['reason']}")

    if recommendation["shift_amount"] > 0:
        print()
        print(f"Suggested shift: ${recommendation['shift_amount']:,.2f}/day")
        print()
        print("To implement:")
        print("  1. Reduce Branded campaign budget by shift amount")
        print("  2. Increase target campaign budget by shift amount")
        print("  3. Monitor for 3-5 days before next adjustment")
        print()
        print("WARNING: This is a recommendation only. Manual review required.")

    # Diminishing returns check
    if len(history["entries"]) >= 3:
        recent = history["entries"][-3:]
        if all(e["action"] == "hold" for e in recent):
            print()
            print("NOTE: Budget allocation appears optimized (3+ consecutive 'hold' recommendations)")

    print()
    print("=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
