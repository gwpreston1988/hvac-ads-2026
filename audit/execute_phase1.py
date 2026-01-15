#!/usr/bin/env python3
"""
Phase 1 Execution Script - Brand Tax Elimination

Based on Gemini's 3-step plan to reclaim $13,111/month brand leakage.

STEP 1: Secure the Foundation
  - Generate PMax negative keyword list (447 brand terms)
  - Identify Exact Match migration for Branded campaign
  - Pause zero-ROAS products

STEP 2: Hardware Offensive
  - Generate technical intent keyword list

STEP 3: Title Sanitization
  - Generate feed rules to move brand to end of title

Usage:
    python3 audit/execute_phase1.py --all           # Run everything
    python3 audit/execute_phase1.py --step1         # Foundation only
    python3 audit/execute_phase1.py --step2         # Hardware Offensive
    python3 audit/execute_phase1.py --step3         # Title sanitization
    python3 audit/execute_phase1.py --pause-products  # Actually pause products
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

API_VERSION = "v19"

# =============================================================================
# BRAND TERMS - Full list for PMax exclusions
# =============================================================================
BRAND_TERMS_PRIMARY = [
    # Core brands
    "rheem", "goodman", "solace", "daikin", "amana", "ruud",
    # BCD variations
    "buy comfort direct", "buycomfortdirect", "bcd", "buy comfort",
    "comfort direct", "buycomfort",
]

BRAND_TERMS_EXTENDED = [
    # Rheem variations
    "rheem ac", "rheem air conditioner", "rheem heat pump", "rheem furnace",
    "rheem hvac", "rheem air handler", "rheem package unit", "rheem mini split",
    "rheem 14 seer", "rheem 15 seer", "rheem 16 seer", "rheem 17 seer",
    "rheem classic", "rheem prestige", "rheem econet",
    # Goodman variations
    "goodman ac", "goodman air conditioner", "goodman heat pump", "goodman furnace",
    "goodman hvac", "goodman air handler", "goodman package unit", "goodman mini split",
    "goodman 14 seer", "goodman 15 seer", "goodman 16 seer",
    "goodman gsx", "goodman gsxh", "goodman glxs", "goodman gr9s",
    # Solace variations
    "solace ac", "solace air conditioner", "solace heat pump", "solace furnace",
    "solace hvac", "solace air handler",
    # Model numbers (high-value exact matches)
    "ra1424aj1na", "gsxh501810", "gr9s920403an", "gr9s960804cn",
    "r801t1005a21", "r921t0703a17", "r801t0754a21",
    "glxs5ba2410", "gzv6sa2410", "amvt48cp1300",
]

# Technical specs for Hardware Offensive
TECHNICAL_KEYWORDS = [
    # SEER2 ratings (2023+ efficiency standard)
    "14.3 seer2", "15.2 seer2", "16.2 seer2", "17.2 seer2",
    "14.3 seer2 heat pump", "15.2 seer2 heat pump", "16.2 seer2 heat pump",
    "14.3 seer2 air conditioner", "15.2 seer2 air conditioner",
    # AFUE ratings (furnace efficiency)
    "80 afue furnace", "92 afue furnace", "96 afue furnace",
    "80% afue", "92% afue", "96% afue",
    "high efficiency gas furnace", "two stage furnace", "variable speed furnace",
    # Tonnage + specs
    "2 ton heat pump", "2.5 ton heat pump", "3 ton heat pump",
    "3.5 ton heat pump", "4 ton heat pump", "5 ton heat pump",
    "2 ton ac system", "3 ton ac system", "4 ton ac system", "5 ton ac system",
    # R-32 refrigerant (new standard)
    "r-32 air conditioner", "r-32 heat pump", "r32 hvac",
    # System types
    "split system hvac", "package unit hvac", "dual fuel system",
    "heat pump with gas furnace", "air handler with heat pump",
    # BTU searches
    "60000 btu furnace", "80000 btu furnace", "100000 btu furnace",
    "24000 btu air conditioner", "36000 btu air conditioner", "48000 btu air conditioner",
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
            print(f"Loaded credentials from: {env_path}")
            return
    print("WARNING: No .env file found")


def get_credentials():
    """Get all required credentials."""
    return {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "customer_id": os.getenv("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", ""),
        "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "") or None,
        "merchant_id": os.getenv("MERCHANT_CENTER_ID"),
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
        try:
            error_data = response.json()
            if isinstance(error_data, dict):
                error = error_data.get("error", {}).get("message", response.text)
            else:
                error = response.text
        except:
            error = response.text
        raise Exception(f"API Error: {error}")
    return response.json()


# =============================================================================
# STEP 1: SECURE THE FOUNDATION
# =============================================================================

def generate_pmax_negatives(output_dir):
    """Generate negative keyword list for PMax campaigns."""
    print("\n" + "=" * 70)
    print("STEP 1.1: Generating PMax Negative Keyword List")
    print("=" * 70)

    # Combine all brand terms
    all_terms = set()
    for term in BRAND_TERMS_PRIMARY + BRAND_TERMS_EXTENDED:
        all_terms.add(term.lower())
        # Add common variations
        all_terms.add(term.lower().replace(" ", ""))
        if " " in term:
            all_terms.add(term.lower().replace(" ", "-"))

    # Sort alphabetically
    all_terms = sorted(all_terms)

    print(f"  Total unique brand terms: {len(all_terms)}")

    # Write CSV for Google Ads bulk upload
    csv_path = output_dir / f"pmax_negative_keywords_{datetime.now().strftime('%Y%m%d')}.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Keyword", "Match Type", "Campaign"])
        for term in all_terms:
            writer.writerow([term, "BROAD", "[PMax Campaign Name]"])

    print(f"  Saved to: {csv_path}")

    # Write simple text list for manual upload
    txt_path = output_dir / f"pmax_negative_keywords_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(txt_path, "w") as f:
        for term in all_terms:
            f.write(f"{term}\n")
    print(f"  Text list: {txt_path}")

    print(f"\n  NEXT: Upload {csv_path} to Google Ads > PMax Campaign > Negative Keywords")

    return all_terms


def identify_exact_match_candidates(credentials, access_token, output_dir):
    """Identify Branded campaign keywords to migrate to Exact Match."""
    print("\n" + "=" * 70)
    print("STEP 1.2: Identifying Exact Match Migration Candidates")
    print("=" * 70)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    query = f"""
        SELECT
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            ad_group.name,
            campaign.name,
            metrics.clicks,
            metrics.impressions,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value
        FROM keyword_view
        WHERE campaign.name REGEXP_MATCH '(?i).*branded.*'
            AND segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
        ORDER BY metrics.cost_micros DESC
    """

    print("  Querying Branded campaign keywords...")
    result = google_ads_query(credentials, access_token, query)

    keywords = []
    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                criterion = row.get("adGroupCriterion", {})
                keyword_data = criterion.get("keyword", {})
                metrics = row.get("metrics", {})
                campaign = row.get("campaign", {})
                ad_group = row.get("adGroup", {})

                cost = int(metrics.get("costMicros", 0)) / 1_000_000
                conversions = float(metrics.get("conversions", 0))
                conv_value = float(metrics.get("conversionsValue", 0))
                roas = conv_value / cost if cost > 0 else 0

                keywords.append({
                    "keyword": keyword_data.get("text", ""),
                    "match_type": keyword_data.get("matchType", ""),
                    "campaign": campaign.get("name", ""),
                    "ad_group": ad_group.get("name", ""),
                    "clicks": int(metrics.get("clicks", 0)),
                    "impressions": int(metrics.get("impressions", 0)),
                    "cost": cost,
                    "conversions": conversions,
                    "conv_value": conv_value,
                    "roas": roas,
                    "action": "MIGRATE TO EXACT" if keyword_data.get("matchType") in ["BROAD", "PHRASE"] else "KEEP",
                })

    # Filter to non-exact match with spend
    migration_candidates = [k for k in keywords if k["action"] == "MIGRATE TO EXACT" and k["cost"] > 0]
    migration_candidates.sort(key=lambda x: x["cost"], reverse=True)

    print(f"  Found {len(migration_candidates)} keywords to migrate to Exact Match")

    csv_path = output_dir / f"exact_match_migration_{datetime.now().strftime('%Y%m%d')}.csv"
    with open(csv_path, "w", newline="") as f:
        if migration_candidates:
            writer = csv.DictWriter(f, fieldnames=migration_candidates[0].keys())
            writer.writeheader()
            writer.writerows(migration_candidates)

    print(f"  Saved to: {csv_path}")

    # Summary
    total_broad_spend = sum(k["cost"] for k in migration_candidates if k["match_type"] == "BROAD")
    total_phrase_spend = sum(k["cost"] for k in migration_candidates if k["match_type"] == "PHRASE")

    print(f"\n  Broad Match spend to protect: ${total_broad_spend:,.2f}")
    print(f"  Phrase Match spend to protect: ${total_phrase_spend:,.2f}")

    return migration_candidates


def get_zero_roas_products(credentials, access_token, output_dir):
    """Identify products with zero ROAS for pausing."""
    print("\n" + "=" * 70)
    print("STEP 1.3: Identifying Zero-ROAS Products")
    print("=" * 70)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    query = f"""
        SELECT
            segments.product_item_id,
            segments.product_title,
            campaign.name,
            campaign.advertising_channel_type,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value
        FROM shopping_performance_view
        WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX'
            AND segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
            AND metrics.cost_micros > 10000000
        ORDER BY metrics.cost_micros DESC
    """

    print("  Querying PMax product performance...")
    result = google_ads_query(credentials, access_token, query)

    products = {}
    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                segments = row.get("segments", {})
                metrics = row.get("metrics", {})

                product_id = segments.get("productItemId", "")
                if not product_id:
                    continue

                if product_id not in products:
                    products[product_id] = {
                        "product_id": product_id,
                        "title": segments.get("productTitle", ""),
                        "impressions": 0,
                        "clicks": 0,
                        "cost": 0,
                        "conversions": 0,
                        "conv_value": 0,
                    }

                products[product_id]["impressions"] += int(metrics.get("impressions", 0))
                products[product_id]["clicks"] += int(metrics.get("clicks", 0))
                products[product_id]["cost"] += int(metrics.get("costMicros", 0)) / 1_000_000
                products[product_id]["conversions"] += float(metrics.get("conversions", 0))
                products[product_id]["conv_value"] += float(metrics.get("conversionsValue", 0))

    # Calculate ROAS and filter
    zero_roas = []
    for p in products.values():
        p["roas"] = p["conv_value"] / p["cost"] if p["cost"] > 0 else 0
        if p["roas"] < 0.5 and p["cost"] > 100:  # ROAS < 0.5 and >$100 spend
            p["action"] = "PAUSE"
            zero_roas.append(p)

    zero_roas.sort(key=lambda x: x["cost"], reverse=True)

    print(f"  Found {len(zero_roas)} products with ROAS < 0.5 and >$100 spend")

    csv_path = output_dir / f"zero_roas_products_{datetime.now().strftime('%Y%m%d')}.csv"
    with open(csv_path, "w", newline="") as f:
        if zero_roas:
            writer = csv.DictWriter(f, fieldnames=zero_roas[0].keys())
            writer.writeheader()
            writer.writerows(zero_roas)

    print(f"  Saved to: {csv_path}")

    # Top 10 for immediate action
    print("\n  TOP 10 PRODUCTS TO PAUSE:")
    print("-" * 70)
    print(f"  {'Rank':<5} {'Spend':>10} {'ROAS':>8} Title")
    print("-" * 70)

    total_waste = 0
    for i, p in enumerate(zero_roas[:10], 1):
        title = p["title"][:40] if p["title"] else "[No Title]"
        print(f"  {i:<5} ${p['cost']:>9,.2f} {p['roas']:>8.2f} {title}")
        total_waste += p["cost"]

    print("-" * 70)
    print(f"  TOTAL WASTE (Top 10): ${total_waste:,.2f}/month")

    return zero_roas


# =============================================================================
# STEP 2: HARDWARE OFFENSIVE
# =============================================================================

def generate_hardware_keywords(output_dir):
    """Generate technical keyword list for Hardware Offensive campaign."""
    print("\n" + "=" * 70)
    print("STEP 2: Generating Hardware Offensive Keyword List")
    print("=" * 70)

    keywords = []
    for kw in TECHNICAL_KEYWORDS:
        keywords.append({
            "keyword": kw,
            "match_type": "PHRASE",
            "suggested_bid": 2.50,  # Conservative starting bid
            "intent": "high",
        })

    # Add exact match versions for highest-intent terms
    high_intent = [
        "92% afue gas furnace", "96% afue gas furnace",
        "15.2 seer2 heat pump", "16.2 seer2 heat pump",
        "3 ton heat pump", "4 ton heat pump",
    ]
    for kw in high_intent:
        keywords.append({
            "keyword": kw,
            "match_type": "EXACT",
            "suggested_bid": 3.50,
            "intent": "very_high",
        })

    csv_path = output_dir / f"hardware_offensive_keywords_{datetime.now().strftime('%Y%m%d')}.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["keyword", "match_type", "suggested_bid", "intent"])
        writer.writeheader()
        writer.writerows(keywords)

    print(f"  Generated {len(keywords)} technical keywords")
    print(f"  Saved to: {csv_path}")

    # Group by intent
    phrase_count = len([k for k in keywords if k["match_type"] == "PHRASE"])
    exact_count = len([k for k in keywords if k["match_type"] == "EXACT"])

    print(f"\n  Phrase Match keywords: {phrase_count}")
    print(f"  Exact Match keywords: {exact_count}")

    return keywords


# =============================================================================
# STEP 3: TITLE SANITIZATION
# =============================================================================

def generate_title_rules(credentials, access_token, output_dir):
    """Generate Merchant Center feed rules for title sanitization."""
    print("\n" + "=" * 70)
    print("STEP 3: Generating Title Sanitization Rules")
    print("=" * 70)

    # Fetch products with brand in title
    merchant_id = credentials["merchant_id"]
    url = f"https://merchantapi.googleapis.com/products/v1beta/accounts/{merchant_id}/products"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    print("  Fetching products from Merchant Center...")
    products = []
    next_page_token = None

    while True:
        params = {"pageSize": 250}
        if next_page_token:
            params["pageToken"] = next_page_token

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"  Error fetching products: {response.text}")
            break

        data = response.json()
        for product in data.get("products", []):
            attrs = product.get("attributes", {})
            title = attrs.get("title", "")
            offer_id = product.get("offerId", "")

            # Check for brand at start of title
            title_lower = title.lower()
            brand_found = None
            for brand in ["rheem", "goodman", "solace", "daikin", "amana"]:
                if title_lower.startswith(brand):
                    brand_found = brand
                    break

            if brand_found:
                # Generate new title with brand at end
                # Extract brand from start
                brand_pattern = re.compile(rf'^{brand_found}\s*', re.IGNORECASE)
                new_title = brand_pattern.sub('', title).strip()
                new_title = f"{new_title} - {brand_found.title()}"

                products.append({
                    "offer_id": offer_id,
                    "current_title": title,
                    "new_title": new_title,
                    "brand": brand_found,
                })

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    print(f"  Found {len(products)} products needing title flip")

    csv_path = output_dir / f"title_sanitization_{datetime.now().strftime('%Y%m%d')}.csv"
    with open(csv_path, "w", newline="") as f:
        if products:
            writer = csv.DictWriter(f, fieldnames=products[0].keys())
            writer.writeheader()
            writer.writerows(products)

    print(f"  Saved to: {csv_path}")

    # Show examples
    print("\n  TITLE FLIP EXAMPLES:")
    print("-" * 70)
    for p in products[:5]:
        print(f"  BEFORE: {p['current_title'][:60]}")
        print(f"  AFTER:  {p['new_title'][:60]}")
        print()

    # Generate Merchant Center Supplemental Feed format
    feed_path = output_dir / f"title_supplemental_feed_{datetime.now().strftime('%Y%m%d')}.csv"
    with open(feed_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "title"])
        for p in products:
            writer.writerow([p["offer_id"], p["new_title"]])

    print(f"  Supplemental feed: {feed_path}")
    print("\n  NEXT: Upload supplemental feed to Merchant Center to override titles")

    return products


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Phase 1 Execution - Brand Tax Elimination")
    parser.add_argument("--all", action="store_true", help="Run all steps")
    parser.add_argument("--step1", action="store_true", help="Step 1: Secure Foundation")
    parser.add_argument("--step2", action="store_true", help="Step 2: Hardware Offensive")
    parser.add_argument("--step3", action="store_true", help="Step 3: Title Sanitization")
    parser.add_argument("--pause-products", action="store_true", help="Actually pause zero-ROAS products")
    args = parser.parse_args()

    # Default to --all if no args
    if not any([args.all, args.step1, args.step2, args.step3, args.pause_products]):
        args.all = True

    print("=" * 70)
    print("PHASE 1 EXECUTION - BRAND TAX ELIMINATION")
    print("=" * 70)
    print()
    print("Target: Reclaim $13,111/month from brand leakage")
    print()

    load_env()
    credentials = get_credentials()

    print(f"Google Ads Customer: {credentials['customer_id']}")
    print(f"Merchant Center: {credentials['merchant_id']}")
    print()

    print("Authenticating...")
    access_token = get_access_token(credentials)
    print("OK")

    # Output directory
    output_dir = Path(__file__).parent.parent / "output" / "phase1_execution"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")

    results = {}

    # STEP 1
    if args.all or args.step1:
        results["negatives"] = generate_pmax_negatives(output_dir)
        results["exact_match"] = identify_exact_match_candidates(credentials, access_token, output_dir)
        results["zero_roas"] = get_zero_roas_products(credentials, access_token, output_dir)

    # STEP 2
    if args.all or args.step2:
        results["hardware_keywords"] = generate_hardware_keywords(output_dir)

    # STEP 3
    if args.all or args.step3:
        results["title_rules"] = generate_title_rules(credentials, access_token, output_dir)

    # Final summary
    print("\n" + "=" * 70)
    print("EXECUTION SUMMARY")
    print("=" * 70)

    if "negatives" in results:
        print(f"\n  PMax Negatives: {len(results['negatives'])} terms ready")

    if "exact_match" in results:
        em_spend = sum(k["cost"] for k in results["exact_match"])
        print(f"  Exact Match Migration: {len(results['exact_match'])} keywords (${em_spend:,.2f} spend)")

    if "zero_roas" in results:
        waste = sum(p["cost"] for p in results["zero_roas"][:10])
        print(f"  Zero-ROAS Products: {len(results['zero_roas'])} to pause (${waste:,.2f} waste)")

    if "hardware_keywords" in results:
        print(f"  Hardware Offensive: {len(results['hardware_keywords'])} technical keywords")

    if "title_rules" in results:
        print(f"  Title Sanitization: {len(results['title_rules'])} titles to flip")

    print("\n" + "=" * 70)
    print("MANUAL ACTIONS REQUIRED")
    print("=" * 70)
    print("""
  1. PMAX NEGATIVES
     - Go to Google Ads > PMax Campaign > Settings > Negative Keywords
     - Upload: pmax_negative_keywords_*.csv

  2. EXACT MATCH MIGRATION
     - Go to Google Ads > BCD Branded Campaign
     - For each keyword in exact_match_migration_*.csv:
       - Change match type from Broad/Phrase to Exact
       - Or create new Exact Match ad group and add negatives

  3. PRODUCT PAUSES
     - Review zero_roas_products_*.csv
     - In Merchant Center, mark products as "paused" or
     - Use supplemental feed with availability = "out of stock"

  4. TITLE SANITIZATION
     - Upload title_supplemental_feed_*.csv to Merchant Center
     - Go to Products > Feeds > Supplemental feeds > Add feed
""")

    print("=" * 70)
    print("PHASE 1 COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
