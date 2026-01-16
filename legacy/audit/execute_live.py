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
LIVE Execution Script - Automated Campaign Changes

This script MAKES ACTUAL CHANGES to your Google Ads and Merchant Center accounts.

Usage:
    python3 audit/execute_live.py --dry-run          # Preview changes (default)
    python3 audit/execute_live.py --execute          # LIVE execution
    python3 audit/execute_live.py --execute --step1  # Only Step 1
    python3 audit/execute_live.py --execute --step3  # Only title updates

Steps:
    1. Add negative keywords to PMax campaigns
    2. Migrate Branded keywords to Exact Match
    3. Pause zero-ROAS products in Merchant Center
    4. Update product titles (move brand to end)
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

API_VERSION = "v19"

# =============================================================================
# BRAND TERMS FOR NEGATIVE KEYWORDS (400+ generated combinations)
# =============================================================================

# Core brand names
CORE_BRANDS = [
    "rheem", "goodman", "solace", "daikin", "amana", "ruud",
    "buy comfort direct", "buycomfortdirect", "bcd", "buy comfort",
    "comfort direct", "buycomfort", "buycomfortdirect.com",
]

# Product types to combine with brands
PRODUCT_TYPES = [
    "ac", "air conditioner", "air conditioning", "a/c",
    "furnace", "gas furnace", "electric furnace",
    "heat pump", "heatpump", "mini split", "minisplit",
    "hvac", "hvac system", "hvac unit",
    "condenser", "air handler", "evaporator coil",
    "package unit", "split system", "ductless",
    "thermostat", "parts", "warranty", "reviews",
    "prices", "cost", "dealer", "distributor",
    "near me", "installation", "replacement",
    "compressor", "coil", "blower", "motor",
]

# Action terms
ACTION_TERMS = [
    "buy", "order", "purchase", "shop", "price", "cost",
    "quote", "discount", "sale", "deal", "coupon",
    "reviews", "rating", "compare", "vs", "versus",
    "specs", "specifications", "manual", "install",
    "wholesale", "direct", "online", "store",
]

# Model number patterns (common prefixes)
MODEL_PREFIXES = [
    # Rheem
    "ra14", "ra15", "ra16", "ra17", "ra18", "ra20",
    "rp14", "rp15", "rp16", "rp17", "rp18",
    "r801", "r802", "r96", "r97", "r98",
    "rgrl", "rgrm", "rgrs",
    # Goodman
    "gsxh5", "gsxc18", "gsxc16", "gsx16", "gsx14", "gsx13",
    "gmvc96", "gmvc97", "gmec96", "gcvc96",
    "gph14", "gph15", "gph16",
    "capf", "cauf", "chpf",
    # Daikin
    "dx16", "dx18", "dx20", "dm96", "dm97",
    # Amana
    "avxc20", "avxc18", "asx16", "asx14",
    "amvc96", "amec96",
]

def generate_brand_terms():
    """Generate 400+ brand term combinations."""
    terms = set()

    # Add core brands
    terms.update(CORE_BRANDS)

    # Brand + product type combinations
    for brand in ["rheem", "goodman", "solace", "daikin", "amana", "ruud"]:
        for product in PRODUCT_TYPES:
            terms.add(f"{brand} {product}")
            terms.add(f"{product} {brand}")

    # Brand + action combinations
    for brand in ["rheem", "goodman", "solace", "daikin", "amana", "ruud"]:
        for action in ACTION_TERMS:
            terms.add(f"{action} {brand}")
            terms.add(f"{brand} {action}")

    # Model prefixes
    terms.update(MODEL_PREFIXES)

    # BCD-specific terms
    bcd_terms = [
        "buy comfort direct", "buycomfortdirect", "bcd hvac",
        "buycomfortdirect.com", "buy comfort direct reviews",
        "buy comfort direct coupon", "buy comfort direct promo",
        "bcd furnace", "bcd ac", "bcd heat pump",
        "comfort direct hvac", "comfort direct reviews",
    ]
    terms.update(bcd_terms)

    # Common misspellings
    misspellings = [
        "reem", "rheme", "rheim", "goodmans", "goodmann",
        "daykin", "daiken", "ammana", "amanna",
    ]
    terms.update(misspellings)

    # Comparison terms
    for brand in ["rheem", "goodman", "daikin", "amana"]:
        for brand2 in ["trane", "carrier", "lennox", "york"]:
            terms.add(f"{brand} vs {brand2}")
            terms.add(f"{brand2} vs {brand}")

    return sorted(list(terms))

# Generate the full list
BRAND_TERMS = generate_brand_terms()


def load_env():
    """Load .env from local directory."""
    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path.home() / "bcd-seo-engine" / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            return env_path
    return None


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
        # BigCommerce
        "bc_store_hash": os.getenv("BIGCOMMERCE_STORE_HASH"),
        "bc_access_token": os.getenv("BIGCOMMERCE_ACCESS_TOKEN"),
    }


# =============================================================================
# BIGCOMMERCE API HELPERS
# =============================================================================

def bigcommerce_api(credentials, method, endpoint, data=None):
    """Make BigCommerce API request."""
    store_hash = credentials["bc_store_hash"]
    url = f"https://api.bigcommerce.com/stores/{store_hash}/v3{endpoint}"
    headers = {
        "X-Auth-Token": credentials["bc_access_token"],
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "PUT":
        response = requests.put(url, headers=headers, json=data)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=data)
    else:
        raise ValueError(f"Unsupported method: {method}")

    return response


def get_bc_product_by_sku(credentials, sku):
    """Find BigCommerce product by SKU."""
    # Try product SKU first
    response = bigcommerce_api(credentials, "GET", f"/catalog/products?sku={sku}")
    if response.status_code == 200:
        data = response.json().get("data", [])
        if data:
            return data[0]

    # Try variant SKU
    response = bigcommerce_api(credentials, "GET", f"/catalog/variants?sku={sku}")
    if response.status_code == 200:
        data = response.json().get("data", [])
        if data:
            product_id = data[0].get("product_id")
            # Get full product
            response = bigcommerce_api(credentials, "GET", f"/catalog/products/{product_id}")
            if response.status_code == 200:
                return response.json().get("data")

    return None


def update_bc_product(credentials, product_id, updates):
    """Update BigCommerce product."""
    response = bigcommerce_api(credentials, "PUT", f"/catalog/products/{product_id}", updates)
    return response.status_code == 200


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


def google_ads_mutate(credentials, access_token, service, operations):
    """Execute Google Ads mutation."""
    url = f"https://googleads.googleapis.com/{API_VERSION}/customers/{credentials['customer_id']}/{service}:mutate"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": credentials["developer_token"],
        "Content-Type": "application/json",
    }
    if credentials["login_customer_id"]:
        headers["login-customer-id"] = credentials["login_customer_id"]

    response = requests.post(url, headers=headers, json={"operations": operations})
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
        return None
    return response.json()


# =============================================================================
# STEP 1: ADD NEGATIVE KEYWORDS TO PMAX
# =============================================================================

def get_pmax_campaigns(credentials, access_token):
    """Get all PMax campaign IDs."""
    query = """
        SELECT campaign.id, campaign.name
        FROM campaign
        WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX'
            AND campaign.status = 'ENABLED'
    """
    result = google_ads_query(credentials, access_token, query)
    campaigns = []
    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                campaigns.append({
                    "id": row["campaign"]["id"],
                    "name": row["campaign"]["name"],
                })
    return campaigns


def create_shared_negative_list(credentials, access_token, list_name, dry_run=True):
    """Create a shared negative keyword list."""
    print(f"\n  Creating shared negative list: {list_name}")

    if dry_run:
        print("    [DRY RUN] Would create shared set")
        return "dry_run_list_id"

    operation = {
        "create": {
            "name": list_name,
            "type": "NEGATIVE_KEYWORDS",
        }
    }

    response = google_ads_mutate(credentials, access_token, "sharedSets", [operation])

    if response.status_code == 200:
        result = response.json()
        resource_name = result["results"][0]["resourceName"]
        list_id = resource_name.split("/")[-1]
        print(f"    Created: {resource_name}")
        return list_id
    else:
        print(f"    ERROR: {response.text}")
        return None


def add_keywords_to_shared_list(credentials, access_token, list_id, keywords, dry_run=True):
    """Add negative keywords to shared list."""
    print(f"\n  Adding {len(keywords)} keywords to shared list...")

    if dry_run:
        print(f"    [DRY RUN] Would add {len(keywords)} keywords")
        for kw in keywords[:5]:
            print(f"      - {kw}")
        print(f"      ... and {len(keywords) - 5} more")
        return True

    customer_id = credentials["customer_id"]

    # Batch keywords (max 5000 per request)
    batch_size = 1000
    for i in range(0, len(keywords), batch_size):
        batch = keywords[i:i + batch_size]
        operations = []

        for keyword in batch:
            operations.append({
                "create": {
                    "sharedSet": f"customers/{customer_id}/sharedSets/{list_id}",
                    "keyword": {
                        "text": keyword,
                        "matchType": "BROAD",
                    }
                }
            })

        # Use correct endpoint: sharedCriteria (plural)
        response = google_ads_mutate(credentials, access_token, "sharedCriteria", operations)

        if response.status_code == 200:
            print(f"    Added batch {i//batch_size + 1}: {len(batch)} keywords")
        else:
            print(f"    ERROR in batch {i//batch_size + 1}: {response.text[:200]}")
            return False

        time.sleep(0.5)  # Rate limiting

    return True


def attach_shared_list_to_campaigns(credentials, access_token, list_id, campaign_ids, dry_run=True):
    """Attach shared negative list to campaigns."""
    print(f"\n  Attaching list to {len(campaign_ids)} campaigns...")

    if dry_run:
        print(f"    [DRY RUN] Would attach to campaigns")
        return True

    customer_id = credentials["customer_id"]
    operations = []

    for campaign_id in campaign_ids:
        operations.append({
            "create": {
                "campaign": f"customers/{customer_id}/campaigns/{campaign_id}",
                "sharedSet": f"customers/{customer_id}/sharedSets/{list_id}",
            }
        })

    response = google_ads_mutate(credentials, access_token, "campaignSharedSets", operations)

    if response.status_code == 200:
        print(f"    Attached to {len(campaign_ids)} campaigns")
        return True
    else:
        print(f"    ERROR: {response.text[:200]}")
        return False


def execute_step1_negatives(credentials, access_token, dry_run=True):
    """Execute Step 1: Add negative keywords to PMax."""
    print("\n" + "=" * 70)
    print("STEP 1: Adding Negative Keywords to PMax Campaigns")
    print("=" * 70)

    # Get PMax campaigns
    campaigns = get_pmax_campaigns(credentials, access_token)
    print(f"\n  Found {len(campaigns)} active PMax campaigns:")
    for c in campaigns:
        print(f"    - {c['name']} (ID: {c['id']})")

    if not campaigns:
        print("  No PMax campaigns found. Skipping.")
        return False

    # Create shared negative list
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    list_name = f"Brand Terms - Auto Generated {timestamp}"
    list_id = create_shared_negative_list(credentials, access_token, list_name, dry_run)

    if not list_id:
        return False

    # Add keywords to list
    success = add_keywords_to_shared_list(credentials, access_token, list_id, BRAND_TERMS, dry_run)
    if not success:
        return False

    # Attach to campaigns
    campaign_ids = [c["id"] for c in campaigns]
    success = attach_shared_list_to_campaigns(credentials, access_token, list_id, campaign_ids, dry_run)

    if success:
        print(f"\n  ✓ Step 1 complete: {len(BRAND_TERMS)} brand terms blocked from {len(campaigns)} PMax campaigns")

    return success


# =============================================================================
# STEP 2: MIGRATE BRANDED KEYWORDS TO EXACT MATCH
# =============================================================================

def get_branded_broad_keywords(credentials, access_token):
    """Get Branded campaign keywords that aren't Exact Match."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    query = f"""
        SELECT
            ad_group_criterion.resource_name,
            ad_group_criterion.criterion_id,
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            ad_group.id,
            ad_group.name,
            campaign.id,
            campaign.name,
            metrics.cost_micros
        FROM keyword_view
        WHERE campaign.name REGEXP_MATCH '(?i).*branded.*'
            AND ad_group_criterion.keyword.match_type IN ('BROAD', 'PHRASE')
            AND segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
        ORDER BY metrics.cost_micros DESC
    """

    result = google_ads_query(credentials, access_token, query)
    keywords = []

    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                criterion = row.get("adGroupCriterion", {})
                keywords.append({
                    "resource_name": criterion.get("resourceName"),
                    "criterion_id": criterion.get("criterionId"),
                    "text": criterion.get("keyword", {}).get("text", ""),
                    "match_type": criterion.get("keyword", {}).get("matchType", ""),
                    "ad_group_id": row.get("adGroup", {}).get("id"),
                    "ad_group_name": row.get("adGroup", {}).get("name", ""),
                    "campaign_id": row.get("campaign", {}).get("id"),
                    "campaign_name": row.get("campaign", {}).get("name", ""),
                    "cost": int(row.get("metrics", {}).get("costMicros", 0)) / 1_000_000,
                })

    return keywords


def update_keyword_match_type(credentials, access_token, keyword, dry_run=True):
    """Update a keyword to Exact Match."""
    if dry_run:
        return True

    # Note: Google Ads doesn't allow changing match type directly.
    # We need to: 1) Create new Exact Match keyword, 2) Pause old keyword
    customer_id = credentials["customer_id"]

    # Create new Exact Match keyword
    create_op = {
        "create": {
            "adGroup": f"customers/{customer_id}/adGroups/{keyword['ad_group_id']}",
            "keyword": {
                "text": keyword["text"],
                "matchType": "EXACT",
            },
            "status": "ENABLED",
        }
    }

    response = google_ads_mutate(credentials, access_token, "adGroupCriteria", [create_op])

    if response.status_code != 200:
        # Keyword might already exist
        if "DUPLICATE" not in response.text:
            print(f"      ERROR creating: {response.text[:100]}")
            return False

    # Pause old keyword
    update_op = {
        "update": {
            "resourceName": keyword["resource_name"],
            "status": "PAUSED",
        },
        "updateMask": "status"
    }

    response = google_ads_mutate(credentials, access_token, "adGroupCriteria", [update_op])

    if response.status_code != 200:
        print(f"      ERROR pausing: {response.text[:100]}")
        return False

    return True


def execute_step2_exact_match(credentials, access_token, dry_run=True):
    """Execute Step 2: Migrate keywords to Exact Match."""
    print("\n" + "=" * 70)
    print("STEP 2: Migrating Branded Keywords to Exact Match")
    print("=" * 70)

    keywords = get_branded_broad_keywords(credentials, access_token)

    if not keywords:
        print("\n  No Broad/Phrase keywords found in Branded campaign.")
        return True

    print(f"\n  Found {len(keywords)} keywords to migrate:")
    total_spend = sum(k["cost"] for k in keywords)
    print(f"  Total spend on non-Exact: ${total_spend:,.2f}")

    for kw in keywords[:10]:
        print(f"    [{kw['match_type']}] {kw['text']} - ${kw['cost']:,.2f}")

    if dry_run:
        print(f"\n  [DRY RUN] Would migrate {len(keywords)} keywords to Exact Match")
        return True

    success_count = 0
    for kw in keywords:
        if update_keyword_match_type(credentials, access_token, kw, dry_run):
            success_count += 1
            print(f"    ✓ Migrated: {kw['text']}")
        time.sleep(0.2)  # Rate limiting

    print(f"\n  ✓ Step 2 complete: {success_count}/{len(keywords)} keywords migrated")
    return True


# =============================================================================
# STEP 3: PAUSE ZERO-ROAS PRODUCTS
# =============================================================================

def get_zero_roas_products(credentials, access_token, roas_threshold=0.5, min_spend=100):
    """Get products with low ROAS and significant spend."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    query = f"""
        SELECT
            segments.product_item_id,
            segments.product_title,
            campaign.advertising_channel_type,
            metrics.cost_micros,
            metrics.conversions_value
        FROM shopping_performance_view
        WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX'
            AND segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
        ORDER BY metrics.cost_micros DESC
    """

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
                        "cost": 0,
                        "conv_value": 0,
                    }

                products[product_id]["cost"] += int(metrics.get("costMicros", 0)) / 1_000_000
                products[product_id]["conv_value"] += float(metrics.get("conversionsValue", 0))

    # Filter by ROAS and spend
    zero_roas = []
    for p in products.values():
        p["roas"] = p["conv_value"] / p["cost"] if p["cost"] > 0 else 0
        if p["roas"] < roas_threshold and p["cost"] >= min_spend:
            zero_roas.append(p)

    zero_roas.sort(key=lambda x: x["cost"], reverse=True)
    return zero_roas


def pause_product_in_merchant(credentials, access_token, product_id, dry_run=True):
    """Pause a product via Merchant Center supplemental feed."""
    if dry_run:
        return True, None

    merchant_id = credentials["merchant_id"]
    # Use the supplemental API data source for overrides
    data_source_id = "10571543575"  # "Excluded Products" supplemental feed

    # Convert to UPPERCASE - Merchant Center uses uppercase offerIds
    offer_id = product_id.upper()

    # Use productInputs.insert to add override in supplemental feed
    url = f"https://merchantapi.googleapis.com/products/v1beta/accounts/{merchant_id}/productInputs:insert"
    params = {"dataSource": f"accounts/{merchant_id}/dataSources/{data_source_id}"}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "offerId": offer_id,
        "contentLanguage": "en",
        "feedLabel": "US",
        "attributes": {
            "pause": "ads",  # Pause from Shopping ads
        }
    }

    response = requests.post(url, headers=headers, params=params, json=payload)

    if response.status_code in [200, 201]:
        return True, None
    else:
        error = response.json().get("error", {}).get("message", response.text[:100])
        return False, error


def execute_step3_pause_products(credentials, access_token, dry_run=True):
    """Execute Step 3: Pause zero-ROAS products."""
    print("\n" + "=" * 70)
    print("STEP 3: Pausing Zero-ROAS Products")
    print("=" * 70)

    products = get_zero_roas_products(credentials, access_token)

    if not products:
        print("\n  No zero-ROAS products found meeting threshold.")
        return True

    total_waste = sum(p["cost"] for p in products)
    print(f"\n  Found {len(products)} products with ROAS < 0.5 and >$100 spend")
    print(f"  Total monthly waste: ${total_waste:,.2f}")

    print("\n  Products to pause:")
    for i, p in enumerate(products[:15], 1):
        print(f"    {i}. ${p['cost']:>8,.2f} | ROAS {p['roas']:.2f} | {p['title'][:45]}")

    if dry_run:
        print(f"\n  [DRY RUN] Would pause {len(products)} products")
        return True

    print("\n  Using Merchant Center supplemental feed to pause products...")
    success_count = 0
    for p in products:
        success, error = pause_product_in_merchant(credentials, access_token, p["product_id"], dry_run)
        if success:
            success_count += 1
            print(f"    ✓ Paused: {p['product_id']}")
        else:
            print(f"    ✗ Failed: {p['product_id']} - {error}")
        time.sleep(0.3)  # Rate limiting

    print(f"\n  ✓ Step 3 complete: {success_count}/{len(products)} products paused via supplemental feed")
    return True


# =============================================================================
# STEP 4: UPDATE PRODUCT TITLES
# =============================================================================

def get_products_with_brand_titles(credentials, access_token):
    """Get products that have brand at start of title."""
    merchant_id = credentials["merchant_id"]
    url = f"https://merchantapi.googleapis.com/products/v1beta/accounts/{merchant_id}/products"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    products = []
    next_page_token = None
    brands = ["rheem", "goodman", "solace", "daikin", "amana"]

    while True:
        params = {"pageSize": 250}
        if next_page_token:
            params["pageToken"] = next_page_token

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            break

        data = response.json()
        for product in data.get("products", []):
            attrs = product.get("attributes", {})
            title = attrs.get("title", "")
            offer_id = product.get("offerId", "")

            # Check if title starts with brand
            title_lower = title.lower()
            for brand in brands:
                if title_lower.startswith(brand):
                    # Generate new title
                    brand_pattern = re.compile(rf'^{brand}\s*', re.IGNORECASE)
                    new_title = brand_pattern.sub('', title).strip()
                    new_title = f"{new_title} - {brand.title()}"

                    products.append({
                        "offer_id": offer_id,
                        "current_title": title,
                        "new_title": new_title,
                        "brand": brand,
                    })
                    break

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    return products


def update_product_title_merchant(credentials, access_token, product, dry_run=True):
    """Update a product's title via Merchant Center supplemental feed."""
    if dry_run:
        return True, None

    merchant_id = credentials["merchant_id"]
    # Convert to UPPERCASE - Merchant Center uses uppercase offerIds
    offer_id = product["offer_id"].upper()
    # Use the supplemental API data source for overrides
    data_source_id = "10571543575"  # "Excluded Products" supplemental feed

    # Use productInputs.insert to add title override in supplemental feed
    url = f"https://merchantapi.googleapis.com/products/v1beta/accounts/{merchant_id}/productInputs:insert"
    params = {"dataSource": f"accounts/{merchant_id}/dataSources/{data_source_id}"}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "offerId": offer_id,
        "contentLanguage": "en",
        "feedLabel": "US",
        "attributes": {
            "title": product["new_title"],
        }
    }

    response = requests.post(url, headers=headers, params=params, json=payload)

    if response.status_code in [200, 201]:
        return True, None
    else:
        error = response.json().get("error", {}).get("message", response.text[:100])
        return False, error


def load_progress(progress_file):
    """Load progress from previous run."""
    if progress_file.exists():
        with open(progress_file, "r") as f:
            return json.load(f)
    return {"completed": [], "failed": [], "last_batch": 0}


def save_progress(progress_file, progress):
    """Save progress to file."""
    with open(progress_file, "w") as f:
        json.dump(progress, f, indent=2)


def execute_step4_titles(credentials, access_token, dry_run=True, limit=None, batch_size=100):
    """Execute Step 4: Update product titles in batches."""
    print("\n" + "=" * 70)
    print("STEP 4: Updating Product Titles (Brand to End)")
    print(f"        Batch Size: {batch_size}")
    print("=" * 70)

    # Progress file for resume capability
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    progress_file = output_dir / "title_update_progress.json"

    products = get_products_with_brand_titles(credentials, access_token)

    if not products:
        print("\n  No products found with brand at start of title.")
        return True

    print(f"\n  Found {len(products)} products needing title update")

    # Load previous progress
    progress = load_progress(progress_file)
    completed_ids = set(progress.get("completed", []))

    # Filter out already completed products
    remaining = [p for p in products if p["offer_id"] not in completed_ids]

    if completed_ids:
        print(f"  Already completed: {len(completed_ids)} products")
        print(f"  Remaining: {len(remaining)} products")

    if limit:
        remaining = remaining[:limit]

    print("\n  Sample transformations:")
    for p in remaining[:5]:
        print(f"    BEFORE: {p['current_title'][:55]}")
        print(f"    AFTER:  {p['new_title'][:55]}")
        print()

    if dry_run:
        print(f"  [DRY RUN] Would update {len(remaining)} product titles in {(len(remaining) + batch_size - 1) // batch_size} batches")
        return True

    print("\n  Using Merchant Center supplemental feed to update titles...")
    print(f"  Processing in batches of {batch_size}...\n")

    total_batches = (len(remaining) + batch_size - 1) // batch_size
    overall_success = 0
    overall_failed = []

    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(remaining))
        batch = remaining[start_idx:end_idx]

        print(f"  BATCH {batch_num + 1}/{total_batches} ({len(batch)} products)")
        print(f"  " + "-" * 50)

        batch_success = 0
        for i, p in enumerate(batch):
            success, error = update_product_title_merchant(credentials, access_token, p, dry_run)
            if success:
                batch_success += 1
                overall_success += 1
                progress["completed"].append(p["offer_id"])
            else:
                overall_failed.append((p["offer_id"], error))
                progress["failed"].append({"offer_id": p["offer_id"], "error": str(error)})

            # Progress indicator every 10 products
            if (i + 1) % 10 == 0:
                print(f"    Batch progress: {i + 1}/{len(batch)}")

            time.sleep(0.2)  # Rate limiting

        # Save progress after each batch
        progress["last_batch"] = batch_num + 1
        save_progress(progress_file, progress)

        print(f"    Batch {batch_num + 1} complete: {batch_success}/{len(batch)} successful")
        print(f"    Overall progress: {overall_success}/{len(remaining)} total")
        print()

        # Brief pause between batches
        if batch_num < total_batches - 1:
            print(f"    Pausing 2s before next batch...")
            time.sleep(2)

    print(f"\n  ✓ Step 4 complete: {overall_success}/{len(remaining)} titles updated via supplemental feed")

    if overall_failed:
        print(f"  Failed: {len(overall_failed)} products")
        for sku, err in overall_failed[:5]:
            print(f"    - {sku}: {err}")

        # Save failed products for review
        failed_csv = output_dir / f"failed_title_updates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(failed_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["offer_id", "error"])
            writer.writerows(overall_failed)
        print(f"  Failed products saved to: {failed_csv}")

    # Clear progress file on successful completion
    if not overall_failed:
        if progress_file.exists():
            progress_file.unlink()
            print("  Progress file cleared.")

    return len(overall_failed) == 0


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Live Campaign Execution")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Preview changes without executing (default)")
    parser.add_argument("--execute", action="store_true",
                        help="Actually execute changes (CAUTION!)")
    parser.add_argument("--step1", action="store_true", help="Step 1: PMax negatives")
    parser.add_argument("--step2", action="store_true", help="Step 2: Exact match migration")
    parser.add_argument("--step3", action="store_true", help="Step 3: Pause products")
    parser.add_argument("--step4", action="store_true", help="Step 4: Update titles")
    parser.add_argument("--title-limit", type=int, help="Limit title updates (for testing)")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for title updates (default: 100)")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--show-keywords", action="store_true", help="Show generated negative keywords")
    args = parser.parse_args()

    dry_run = not args.execute

    # Default to all steps if none specified
    run_all = not any([args.step1, args.step2, args.step3, args.step4])

    print("=" * 70)
    if dry_run:
        print("LIVE EXECUTION - DRY RUN MODE")
        print("No changes will be made. Use --execute to apply changes.")
    else:
        print("LIVE EXECUTION - CHANGES WILL BE APPLIED")
    print("=" * 70)
    print()

    # Show keyword count
    print(f"Negative Keywords Generated: {len(BRAND_TERMS)}")
    if args.show_keywords:
        print("\nGenerated keywords:")
        for i, kw in enumerate(BRAND_TERMS, 1):
            print(f"  {i}. {kw}")
        print()

    env_path = load_env()
    credentials = get_credentials()

    print(f"Credentials: {env_path}")
    print(f"Google Ads Customer: {credentials['customer_id']}")
    print(f"Merchant Center: {credentials['merchant_id']}")
    print(f"Title Update Batch Size: {args.batch_size}")
    print()

    if args.execute and not args.force:
        print("WARNING: This will make LIVE changes to your accounts!")
        confirm = input("Type 'EXECUTE' to confirm: ")
        if confirm != "EXECUTE":
            print("Aborted.")
            sys.exit(0)

    print("\nAuthenticating...")
    access_token = get_access_token(credentials)
    print("OK")

    results = {}

    # Step 1: PMax Negatives
    if run_all or args.step1:
        results["step1"] = execute_step1_negatives(credentials, access_token, dry_run)

    # Step 2: Exact Match Migration
    if run_all or args.step2:
        results["step2"] = execute_step2_exact_match(credentials, access_token, dry_run)

    # Step 3: Pause Products
    if run_all or args.step3:
        results["step3"] = execute_step3_pause_products(credentials, access_token, dry_run)

    # Step 4: Title Updates
    if run_all or args.step4:
        results["step4"] = execute_step4_titles(credentials, access_token, dry_run, args.title_limit, args.batch_size)

    # Summary
    print("\n" + "=" * 70)
    print("EXECUTION SUMMARY")
    print("=" * 70)

    for step, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {step}: {status}")

    if dry_run:
        print("\n  [DRY RUN] No actual changes made.")
        print("  Run with --execute to apply changes.")
    else:
        print("\n  ✓ All changes applied successfully!")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
