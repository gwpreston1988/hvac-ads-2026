#!/usr/bin/env python3
"""
Query the full listing group filter structure for the PMax campaign.
Shows exactly what's configured and what needs to change.
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
LOGIN_CUSTOMER_ID = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("GOOGLE_ADS_REFRESH_TOKEN")

PMAX_CAMPAIGN_ID = "20815709270"
ASSET_GROUP_ID = "6483780791"


def get_access_token():
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
    return response.json().get("results", [])


def main():
    access_token = get_access_token()

    print("=" * 80)
    print("LISTING GROUP FILTER STRUCTURE")
    print("=" * 80)

    # Get all listing group filters with full details
    query = f"""
        SELECT
            asset_group_listing_group_filter.resource_name,
            asset_group_listing_group_filter.id,
            asset_group_listing_group_filter.type,
            asset_group_listing_group_filter.parent_listing_group_filter,
            asset_group_listing_group_filter.case_value.product_type.value,
            asset_group_listing_group_filter.case_value.product_type.level,
            asset_group_listing_group_filter.case_value.product_brand.value,
            asset_group_listing_group_filter.case_value.product_channel.channel,
            asset_group_listing_group_filter.case_value.product_condition.condition,
            asset_group_listing_group_filter.case_value.product_item_id.value
        FROM asset_group_listing_group_filter
        WHERE asset_group.id = {ASSET_GROUP_ID}
    """

    results = google_ads_query(access_token, query)

    # Organize by type
    filters_by_type = {}
    product_types_included = []
    product_types_excluded = []

    print(f"\nFound {len(results)} listing group filters\n")

    for r in results:
        f = r.get("assetGroupListingGroupFilter", {})
        fid = f.get("id")
        ftype = f.get("type")  # UNIT_INCLUDED, UNIT_EXCLUDED, SUBDIVISION
        case_value = f.get("caseValue", {})

        # Extract what this filter is for
        filter_desc = None
        if "productType" in case_value:
            pt = case_value["productType"]
            level = pt.get("level", "?")
            value = pt.get("value", "Everything else")
            filter_desc = f"ProductType L{level}: {value}"

            if ftype == "UNIT_INCLUDED":
                product_types_included.append(value)
            elif ftype == "UNIT_EXCLUDED":
                product_types_excluded.append(value)

        elif "productBrand" in case_value:
            filter_desc = f"Brand: {case_value['productBrand'].get('value', 'All')}"
        elif "productChannel" in case_value:
            filter_desc = f"Channel: {case_value['productChannel'].get('channel')}"
        elif "productCondition" in case_value:
            filter_desc = f"Condition: {case_value['productCondition'].get('condition')}"
        elif "productItemId" in case_value:
            filter_desc = f"Item: {case_value['productItemId'].get('value')}"
        else:
            filter_desc = "Root/All Products"

        if ftype not in filters_by_type:
            filters_by_type[ftype] = []
        filters_by_type[ftype].append({"id": fid, "desc": filter_desc})

    # Print organized view
    print("-" * 80)
    print("FILTER TYPES:")
    print("-" * 80)

    for ftype, filters in sorted(filters_by_type.items()):
        print(f"\n{ftype} ({len(filters)} filters):")
        for f in filters[:30]:  # Limit output
            print(f"  - {f['desc']} (ID: {f['id']})")
        if len(filters) > 30:
            print(f"  ... and {len(filters) - 30} more")

    # Summary
    print("\n" + "=" * 80)
    print("CURRENT CONFIGURATION SUMMARY")
    print("=" * 80)

    print("\nProduct Types INCLUDED:")
    for pt in sorted(set(product_types_included)):
        print(f"  ✓ {pt}")

    if product_types_excluded:
        print("\nProduct Types EXCLUDED:")
        for pt in sorted(set(product_types_excluded)):
            print(f"  ✗ {pt}")

    # What's missing
    print("\n" + "=" * 80)
    print("REQUIRED CHANGES FOR EQUIPMENT BRANDS")
    print("=" * 80)

    print("""
CURRENT STATE:
  - Only 'hvac parts supplies' and its L2 subcategories are included
  - Equipment brands (goodman 1, rheem, solace) are NOT in the filters

PRODUCTS IN YOUR FEED BY TYPE:
  - goodman 1     → Goodman AC units, systems (6 products)
  - rheem         → Rheem systems (2 products)
  - rheem > air handlers → Rheem air handlers (1 product)
  - solace        → Solace systems (6 products)
  - hvac parts supplies → Parts/accessories (7 products)

TO SHOW EQUIPMENT BRANDS (NO PARTS):
  You need to REPLACE the current listing group filters:

  REMOVE:
    - All 'hvac parts supplies' filters (L1 and L2)

  ADD:
    - ProductType L1: goodman 1    (UNIT_INCLUDED)
    - ProductType L1: rheem        (UNIT_INCLUDED)
    - ProductType L1: solace       (UNIT_INCLUDED)

  This can be done in Google Ads UI:
    1. Go to PMax campaign > Asset Groups > Products merchant campaign
    2. Click "Edit listing groups"
    3. Remove 'hvac parts supplies' subdivision
    4. Add new subdivisions for: goodman 1, rheem, solace
""")


if __name__ == "__main__":
    main()
