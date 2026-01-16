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
PMax Brand Leakage Audit

Identifies brand search terms leaking into Performance Max campaigns.
Uses campaign_search_term_insight report for actual PMax search data.
Outputs CSV report and summary of brand spend waste.
"""

import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

# API version
API_VERSION = "v19"


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


def load_brand_terms():
    """Load brand terms from config file."""
    config_path = Path(__file__).parent.parent / "configs" / "brand_terms.json"

    if not config_path.exists():
        print(f"ERROR: Brand terms config not found: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    all_terms = set(config.get("brand_terms", []))
    for variants in config.get("brand_variants", {}).values():
        all_terms.update(variants)

    return list(all_terms), config


def check_brand_match(search_term, brand_terms):
    """Check if search term contains any brand terms."""
    term_lower = search_term.lower()

    for brand in brand_terms:
        pattern = r"\b" + re.escape(brand.lower()) + r"\b"
        if re.search(pattern, term_lower):
            return True, brand

    return False, None


def get_pmax_search_term_insights(credentials, access_token, days=30):
    """Pull search term insights from PMax campaigns using campaign_search_term_insight."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Use campaign_search_term_insight for PMax search data
    query = f"""
        SELECT
            campaign_search_term_insight.category_label,
            campaign.id,
            campaign.name
        FROM campaign_search_term_insight
        WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX'
            AND segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
    """

    print(f"Fetching PMax search term insights ({days} days)...")
    print("Using: campaign_search_term_insight report")

    try:
        result = google_ads_query(credentials, access_token, query)
        terms = []
        if result:
            for chunk in result:
                for row in chunk.get("results", []):
                    insight = row.get("campaignSearchTermInsight", {})
                    campaign = row.get("campaign", {})

                    category_label = insight.get("categoryLabel", "")
                    if category_label:
                        terms.append({
                            "search_term": category_label,
                            "campaign_id": campaign.get("id"),
                            "campaign_name": campaign.get("name"),
                            "source": "search_term_insight",
                        })
        return terms, "campaign_search_term_insight"
    except Exception as e:
        print(f"  campaign_search_term_insight failed: {e}")
        print("  Falling back to search_term_view...")

    # Fallback to search_term_view
    query = f"""
        SELECT
            search_term_view.search_term,
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions
        FROM search_term_view
        WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX'
            AND segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
        ORDER BY metrics.cost_micros DESC
    """

    result = google_ads_query(credentials, access_token, query)
    terms = []
    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                search_term = row.get("searchTermView", {}).get("searchTerm", "")
                campaign = row.get("campaign", {})
                metrics = row.get("metrics", {})

                terms.append({
                    "search_term": search_term,
                    "campaign_id": campaign.get("id"),
                    "campaign_name": campaign.get("name"),
                    "impressions": int(metrics.get("impressions", 0)),
                    "clicks": int(metrics.get("clicks", 0)),
                    "cost": int(metrics.get("costMicros", 0)) / 1_000_000,
                    "conversions": float(metrics.get("conversions", 0)),
                    "source": "search_term_view",
                })

    return terms, "search_term_view"


def get_pmax_search_categories(credentials, access_token, days=30):
    """Get PMax search categories with metrics."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Try getting search categories from asset_group_top_combination_view
    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            asset_group.id,
            asset_group.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value
        FROM asset_group
        WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX'
            AND segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
    """

    print("Fetching PMax asset group performance...")
    try:
        result = google_ads_query(credentials, access_token, query)
        asset_groups = []
        if result:
            for chunk in result:
                for row in chunk.get("results", []):
                    campaign = row.get("campaign", {})
                    ag = row.get("assetGroup", {})
                    metrics = row.get("metrics", {})

                    asset_groups.append({
                        "campaign_name": campaign.get("name"),
                        "asset_group": ag.get("name"),
                        "impressions": int(metrics.get("impressions", 0)),
                        "clicks": int(metrics.get("clicks", 0)),
                        "cost": int(metrics.get("costMicros", 0)) / 1_000_000,
                        "conversions": float(metrics.get("conversions", 0)),
                        "conv_value": float(metrics.get("conversionsValue", 0)),
                    })
        return asset_groups
    except Exception as e:
        print(f"  Asset group query failed: {e}")
        return []


def main():
    print("=" * 70)
    print("PMax Brand Leakage Audit")
    print("=" * 70)
    print()

    load_env()
    credentials = get_credentials()
    print(f"Customer ID: {credentials['customer_id']}")
    print()

    print("Authenticating...")
    access_token = get_access_token(credentials)
    print("OK")
    print()

    brand_terms, brand_config = load_brand_terms()
    print(f"Loaded {len(brand_terms)} brand terms")
    print()

    # Get PMax search term insights
    search_terms, source = get_pmax_search_term_insights(credentials, access_token, days=30)
    print(f"Found {len(search_terms)} search terms (source: {source})")
    print()

    # Get asset group performance for context
    asset_groups = get_pmax_search_categories(credentials, access_token, days=30)
    if asset_groups:
        print(f"Found {len(asset_groups)} asset groups")
        total_pmax_spend = sum(ag["cost"] for ag in asset_groups)
        print(f"Total PMax spend (30d): ${total_pmax_spend:,.2f}")
        print()

    # Analyze for brand leakage
    print("Analyzing for brand leakage...")
    results = []
    brand_leakage_count = 0

    for term in search_terms:
        is_brand, matched_brand = check_brand_match(term["search_term"], brand_terms)

        results.append({
            "search_term": term["search_term"],
            "campaign": term.get("campaign_name", ""),
            "impressions": term.get("impressions", "N/A"),
            "clicks": term.get("clicks", "N/A"),
            "cost": term.get("cost", "N/A"),
            "conversions": term.get("conversions", "N/A"),
            "is_brand_match": is_brand,
            "matched_brand": matched_brand or "",
            "source": term.get("source", ""),
        })

        if is_brand:
            brand_leakage_count += 1

    # Sort brand matches first
    results.sort(key=lambda x: (not x["is_brand_match"], str(x.get("cost", 0))), reverse=True)

    # Output CSV
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"pmax_brand_leakage_{timestamp}.csv"

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "search_term", "campaign", "impressions", "clicks",
            "cost", "conversions", "is_brand_match", "matched_brand", "source"
        ])
        writer.writeheader()
        writer.writerows(results)

    print(f"CSV written: {csv_path}")
    print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print(f"Data source: {source}")
    print(f"Total search terms analyzed: {len(results)}")
    print(f"Brand terms found: {brand_leakage_count}")
    print()

    # Brand matches
    brand_results = [r for r in results if r["is_brand_match"]]
    if brand_results:
        print("BRAND TERMS DETECTED IN PMAX:")
        print("-" * 70)
        for i, r in enumerate(brand_results[:20], 1):
            print(f"{i:2}. {r['search_term'][:50]:<50} ({r['matched_brand']})")
        print()

        # By brand breakdown
        print("LEAKAGE BY BRAND:")
        print("-" * 70)
        brand_count = {}
        for r in brand_results:
            brand = r["matched_brand"]
            brand_count[brand] = brand_count.get(brand, 0) + 1

        for brand, count in sorted(brand_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  {brand:<20} {count:>5} occurrences")

        print()
        print("RECOMMENDATION: Add these brand terms as negative keywords in PMax")
    else:
        print("No brand leakage detected in available search term data!")

    # Asset group summary
    if asset_groups:
        print()
        print("PMAX ASSET GROUP PERFORMANCE:")
        print("-" * 70)
        for ag in sorted(asset_groups, key=lambda x: x["cost"], reverse=True)[:10]:
            roas = ag["conv_value"] / ag["cost"] if ag["cost"] > 0 else 0
            print(f"  {ag['asset_group'][:30]:<30} ${ag['cost']:>8.2f}  ROAS: {roas:.2f}")

    print()
    print("=" * 70)
    print("AUDIT COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
