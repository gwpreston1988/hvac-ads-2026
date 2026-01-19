#!/usr/bin/env python3
"""
Standalone diagnostic script to investigate Goodman listings in PMax merchant campaign.
Does NOT interfere with the main pipeline - reads only.

Usage: python diag/goodman_pmax_diagnostic.py
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")

# Configuration
CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
LOGIN_CUSTOMER_ID = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("GOOGLE_ADS_REFRESH_TOKEN")
MERCHANT_CENTER_ID = os.getenv("MERCHANT_CENTER_ID")

PMAX_CAMPAIGN_ID = "20815709270"  # Products merchant campaign


def get_access_token():
    """Exchange refresh token for access token."""
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": REFRESH_TOKEN,
            "grant_type": "refresh_token",
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]


def google_ads_query(access_token, query):
    """Execute GAQL query against Google Ads API."""
    url = f"https://googleads.googleapis.com/v19/customers/{CUSTOMER_ID}/googleAds:search"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": DEVELOPER_TOKEN,
        "Content-Type": "application/json",
    }
    if LOGIN_CUSTOMER_ID:
        headers["login-customer-id"] = LOGIN_CUSTOMER_ID

    response = requests.post(url, headers=headers, json={"query": query})
    if response.status_code != 200:
        print(f"API Error: {response.status_code}")
        print(response.text)
        return []

    data = response.json()
    return data.get("results", [])


def merchant_center_query(access_token, endpoint):
    """Query Merchant Center API."""
    url = f"https://shoppingcontent.googleapis.com/content/v2.1/{MERCHANT_CENTER_ID}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Merchant API Error: {response.status_code}")
        print(response.text)
        return {}

    return response.json()


def main():
    print("=" * 70)
    print("GOODMAN PMAX MERCHANT DIAGNOSTIC")
    print("=" * 70)

    access_token = get_access_token()
    print("\n✓ Authentication successful\n")

    # -------------------------------------------------------------------------
    # 1. Check PMax Campaign Status
    # -------------------------------------------------------------------------
    print("-" * 70)
    print("1. PMAX CAMPAIGN STATUS")
    print("-" * 70)

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.shopping_setting.merchant_id,
            campaign.shopping_setting.feed_label,
            campaign.shopping_setting.campaign_priority,
            campaign.bidding_strategy_type,
            campaign_budget.amount_micros
        FROM campaign
        WHERE campaign.id = {PMAX_CAMPAIGN_ID}
    """
    results = google_ads_query(access_token, query)

    if results:
        camp = results[0].get("campaign", {})
        budget = results[0].get("campaignBudget", {})
        print(f"Campaign: {camp.get('name')}")
        print(f"Status: {camp.get('status')}")
        print(f"Merchant ID: {camp.get('shoppingSetting', {}).get('merchantId')}")
        print(f"Feed Label: {camp.get('shoppingSetting', {}).get('feedLabel', 'Not set')}")
        print(f"Bidding: {camp.get('biddingStrategyType')}")
        print(f"Budget: ${int(budget.get('amountMicros', 0)) / 1_000_000:.2f}/day")
    else:
        print("ERROR: Campaign not found!")

    # -------------------------------------------------------------------------
    # 2. Check Asset Groups and Listing Filters
    # -------------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("2. ASSET GROUPS & LISTING FILTERS")
    print("-" * 70)

    query = f"""
        SELECT
            asset_group.id,
            asset_group.name,
            asset_group.status
        FROM asset_group
        WHERE campaign.id = {PMAX_CAMPAIGN_ID}
    """
    asset_groups = google_ads_query(access_token, query)

    for ag in asset_groups:
        ag_data = ag.get("assetGroup", {})
        ag_id = ag_data.get("id")
        print(f"\nAsset Group: {ag_data.get('name')} (ID: {ag_id})")
        print(f"  Status: {ag_data.get('status')}")

        # Get listing group filters for this asset group
        filter_query = f"""
            SELECT
                asset_group_listing_group_filter.id,
                asset_group_listing_group_filter.type,
                asset_group_listing_group_filter.case_value.product_brand.value,
                asset_group_listing_group_filter.case_value.product_type.value,
                asset_group_listing_group_filter.case_value.product_type.level,
                asset_group_listing_group_filter.case_value.product_item_id.value,
                asset_group_listing_group_filter.case_value.product_channel.channel,
                asset_group_listing_group_filter.case_value.product_custom_attribute.value,
                asset_group_listing_group_filter.case_value.product_custom_attribute.index
            FROM asset_group_listing_group_filter
            WHERE asset_group.id = {ag_id}
        """
        filters = google_ads_query(access_token, filter_query)

        brand_filters = []
        other_filters = []

        for f in filters:
            fdata = f.get("assetGroupListingGroupFilter", {})
            ftype = fdata.get("type")
            case_value = fdata.get("caseValue", {})

            if "productBrand" in case_value:
                brand = case_value["productBrand"].get("value", "ALL")
                brand_filters.append(brand)
            elif "productType" in case_value:
                pt = case_value["productType"]
                other_filters.append(f"Type L{pt.get('level')}: {pt.get('value')}")
            elif "productChannel" in case_value:
                other_filters.append(f"Channel: {case_value['productChannel'].get('channel')}")
            elif "productItemId" in case_value:
                other_filters.append(f"Item: {case_value['productItemId'].get('value')}")
            elif "productCustomAttribute" in case_value:
                attr = case_value["productCustomAttribute"]
                other_filters.append(f"Custom{attr.get('index')}: {attr.get('value')}")

        if brand_filters:
            print(f"  Brand Filters: {brand_filters}")
            if "Goodman" not in brand_filters and "goodman" not in [b.lower() for b in brand_filters]:
                print("  ⚠️  GOODMAN NOT IN BRAND FILTER!")
        else:
            print("  Brand Filters: None (all brands)")

        if other_filters:
            print(f"  Other Filters: {other_filters}")

    # -------------------------------------------------------------------------
    # 3. Check Brand Exclusions on Campaign
    # -------------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("3. BRAND EXCLUSIONS")
    print("-" * 70)

    query = f"""
        SELECT
            campaign_criterion.criterion_id,
            campaign_criterion.negative,
            campaign_criterion.type,
            campaign_criterion.keyword.text,
            campaign_criterion.keyword.match_type
        FROM campaign_criterion
        WHERE campaign.id = {PMAX_CAMPAIGN_ID}
          AND campaign_criterion.negative = TRUE
    """
    exclusions = google_ads_query(access_token, query)

    goodman_exclusion = False
    if exclusions:
        print(f"Found {len(exclusions)} negative criteria:")
        for ex in exclusions:
            crit = ex.get("campaignCriterion", {})
            ctype = crit.get("type")
            if ctype == "KEYWORD":
                kw = crit.get("keyword", {})
                text = kw.get("text", "")
                print(f"  - Negative Keyword: {text} ({kw.get('matchType')})")
                if "goodman" in text.lower():
                    goodman_exclusion = True
                    print("    ⚠️  GOODMAN EXCLUDED!")
            else:
                print(f"  - Type: {ctype}")
    else:
        print("No negative campaign criteria found.")

    # -------------------------------------------------------------------------
    # 4. Check Merchant Center Products - Goodman
    # -------------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("4. MERCHANT CENTER - GOODMAN PRODUCTS")
    print("-" * 70)

    products_data = merchant_center_query(access_token, "products")
    products = products_data.get("resources", [])

    goodman_products = []
    for p in products:
        brand = p.get("brand", "").lower()
        if "goodman" in brand:
            goodman_products.append(p)

    print(f"Total products in feed: {len(products)}")
    print(f"Goodman products found: {len(goodman_products)}")

    if goodman_products:
        print("\nGoodman Product Samples:")
        for p in goodman_products[:5]:
            print(f"  - {p.get('title', 'No title')[:60]}")
            print(f"    ID: {p.get('id')}")
            print(f"    Brand: {p.get('brand')}")
            print(f"    Availability: {p.get('availability')}")

    # -------------------------------------------------------------------------
    # 5. Check Product Statuses
    # -------------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("5. GOODMAN PRODUCT STATUSES")
    print("-" * 70)

    statuses_data = merchant_center_query(access_token, "productstatuses")
    statuses = statuses_data.get("resources", [])

    goodman_statuses = []
    for s in statuses:
        product_id = s.get("productId", "")
        # Find matching product
        for p in goodman_products:
            if p.get("id") == product_id or product_id in str(p.get("id", "")):
                goodman_statuses.append(s)
                break

    # Also check by title
    if not goodman_statuses:
        # Try different approach - check all statuses for Goodman
        print("Checking all product statuses for issues...")

    disapproved = []
    pending = []
    approved = []

    for s in statuses:
        dest_statuses = s.get("destinationStatuses", [])
        item_issues = s.get("itemLevelIssues", [])

        product_id = s.get("productId", "")

        # Check if this is a Goodman product
        is_goodman = False
        for p in goodman_products:
            if product_id in str(p.get("id", "")):
                is_goodman = True
                break

        if not is_goodman:
            continue

        for dest in dest_statuses:
            dest_name = dest.get("destination")
            status = dest.get("status")

            if dest_name in ["Shopping_ads", "SurfacesAcrossGoogle", "FreeListings"]:
                if status == "disapproved":
                    disapproved.append((product_id, dest_name, item_issues))
                elif status == "pending":
                    pending.append((product_id, dest_name))
                else:
                    approved.append((product_id, dest_name))

    print(f"\nGoodman Products - Shopping Ads Status:")
    print(f"  Approved: {len(approved)}")
    print(f"  Pending: {len(pending)}")
    print(f"  Disapproved: {len(disapproved)}")

    if disapproved:
        print("\nDisapproved Goodman Products:")
        for pid, dest, issues in disapproved[:5]:
            print(f"  - {pid}")
            print(f"    Destination: {dest}")
            if issues:
                for issue in issues[:3]:
                    print(f"    Issue: {issue.get('description', 'Unknown')}")
                    print(f"           {issue.get('detail', '')}")

    # -------------------------------------------------------------------------
    # 6. Check Shopping Performance Report
    # -------------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("6. SHOPPING PERFORMANCE (Last 30 days)")
    print("-" * 70)

    query = f"""
        SELECT
            segments.product_brand,
            segments.product_item_id,
            segments.product_title,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions
        FROM shopping_performance_view
        WHERE campaign.id = {PMAX_CAMPAIGN_ID}
          AND segments.date DURING LAST_30_DAYS
        ORDER BY metrics.impressions DESC
        LIMIT 50
    """
    perf = google_ads_query(access_token, query)

    goodman_perf = []
    other_brands = {}

    for row in perf:
        seg = row.get("segments", {})
        brand = seg.get("productBrand", "Unknown")
        metrics = row.get("metrics", {})

        if "goodman" in brand.lower():
            goodman_perf.append({
                "brand": brand,
                "item": seg.get("productItemId"),
                "title": seg.get("productTitle"),
                "impressions": metrics.get("impressions", 0),
                "clicks": metrics.get("clicks", 0),
            })
        else:
            other_brands[brand] = other_brands.get(brand, 0) + int(metrics.get("impressions", 0))

    print("\nBrand Impression Distribution:")
    for brand, impr in sorted(other_brands.items(), key=lambda x: -x[1])[:10]:
        print(f"  {brand}: {impr:,} impressions")

    if goodman_perf:
        print(f"\nGoodman Performance: {len(goodman_perf)} products with data")
        for p in goodman_perf[:5]:
            print(f"  - {p['title'][:50]}")
            print(f"    Impressions: {p['impressions']}, Clicks: {p['clicks']}")
    else:
        print("\n⚠️  NO GOODMAN IMPRESSIONS IN LAST 30 DAYS!")

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 70)

    issues = []

    if not goodman_products:
        issues.append("NO Goodman products in Merchant Center feed")

    if disapproved:
        issues.append(f"{len(disapproved)} Goodman products DISAPPROVED")

    if goodman_exclusion:
        issues.append("Goodman is EXCLUDED as negative keyword on campaign")

    if brand_filters and "Goodman" not in brand_filters:
        issues.append("Goodman not included in asset group brand filters")

    if not goodman_perf and goodman_products:
        issues.append("Goodman products exist but getting ZERO impressions")

    if issues:
        print("\n🚨 ISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    else:
        print("\n✓ No obvious issues found - may need deeper investigation")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
