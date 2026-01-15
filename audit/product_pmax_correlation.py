#!/usr/bin/env python3
"""
Product-PMax Correlation - Phase 1.3

Joins Merchant Center product data with PMax shopping performance
to identify which products are driving brand leakage spend.

Output:
- output/product_pmax_performance_YYYYMMDD.csv
- output/top_brand_leakage_products_YYYYMMDD.csv
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

API_VERSION = "v19"

# Brand terms
BRAND_TERMS = [
    "rheem", "goodman", "solace", "daikin", "amana", "ruud",
    "buy comfort direct", "buycomfortdirect", "bcd"
]


def load_env():
    """Load .env from local directory (working creds)."""
    env_paths = [
        Path(__file__).parent.parent / ".env",     # hvac-ads-2026 (working)
        Path.home() / "bcd-seo-engine" / ".env",   # Fallback
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"Loaded credentials from: {env_path}")
            return
    print("WARNING: No .env file found")


def get_credentials():
    """Get all required credentials."""
    required = [
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET",
        "GOOGLE_ADS_REFRESH_TOKEN",
        "GOOGLE_ADS_CUSTOMER_ID",
        "MERCHANT_CENTER_ID",
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
        error = response.json().get("error", {}).get("message", response.text)
        raise Exception(f"API Error: {error}")
    return response.json()


def get_merchant_products(credentials, access_token):
    """Fetch products from Merchant Center using new Merchant API."""
    merchant_id = credentials["merchant_id"]
    # New Merchant API endpoint (replacing deprecated Content API)
    url = f"https://merchantapi.googleapis.com/products/v1beta/accounts/{merchant_id}/products"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    products = {}
    next_page_token = None

    while True:
        params = {"pageSize": 250}
        if next_page_token:
            params["pageToken"] = next_page_token

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            error = response.json().get("error", {}).get("message", response.text)
            raise Exception(f"Merchant API Error: {error}")

        data = response.json()
        # New API returns 'products' with nested 'attributes'
        for product in data.get("products", []):
            offer_id = product.get("offerId", "")
            attrs = product.get("attributes", {})
            products[offer_id] = {
                "offer_id": offer_id,
                "title": attrs.get("title", ""),
                "brand": attrs.get("brand", ""),
                "price": attrs.get("price", {}).get("amountMicros", 0) / 1_000_000 if attrs.get("price") else "0",
                "gtin": attrs.get("gtin", ""),
                "mpn": attrs.get("mpn", ""),
            }

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    return products


def get_shopping_product_performance(credentials, access_token, days=30):
    """Get PMax shopping product performance from Google Ads."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Query shopping_product_performance_view for PMax
    query = f"""
        SELECT
            segments.product_item_id,
            segments.product_title,
            segments.product_brand,
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
        ORDER BY metrics.cost_micros DESC
    """

    print(f"Fetching PMax shopping performance ({days} days)...")
    result = google_ads_query(credentials, access_token, query)

    products = {}
    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                segments = row.get("segments", {})
                metrics = row.get("metrics", {})
                campaign = row.get("campaign", {})

                product_id = segments.get("productItemId", "")
                if not product_id:
                    continue

                if product_id not in products:
                    products[product_id] = {
                        "product_id": product_id,
                        "product_title": segments.get("productTitle", ""),
                        "product_brand": segments.get("productBrand", ""),
                        "campaign": campaign.get("name", ""),
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

    return products


def check_brand_in_title(title):
    """Check if title contains brand terms."""
    if not title:
        return False, None
    title_lower = title.lower()
    for brand in BRAND_TERMS:
        if brand in title_lower:
            return True, brand
    return False, None


def correlate_data(merchant_products, pmax_products):
    """Correlate Merchant Center products with PMax performance."""
    correlated = []

    for product_id, pmax_data in pmax_products.items():
        # Try to match with Merchant Center
        merchant_data = merchant_products.get(product_id, {})

        # Use PMax title if no Merchant match
        title = merchant_data.get("title") or pmax_data.get("product_title", "")
        brand = merchant_data.get("brand") or pmax_data.get("product_brand", "")

        # Check for brand in title
        has_brand, matched_brand = check_brand_in_title(title)

        # Calculate metrics
        roas = pmax_data["conv_value"] / pmax_data["cost"] if pmax_data["cost"] > 0 else 0
        cpc = pmax_data["cost"] / pmax_data["clicks"] if pmax_data["clicks"] > 0 else 0

        correlated.append({
            "product_id": product_id,
            "title": title,
            "brand": brand,
            "price": merchant_data.get("price", ""),
            "gtin": merchant_data.get("gtin", ""),
            "mpn": merchant_data.get("mpn", ""),
            "campaign": pmax_data["campaign"],
            "impressions": pmax_data["impressions"],
            "clicks": pmax_data["clicks"],
            "cost": pmax_data["cost"],
            "conversions": pmax_data["conversions"],
            "conv_value": pmax_data["conv_value"],
            "roas": roas,
            "cpc": cpc,
            "has_brand_in_title": has_brand,
            "matched_brand": matched_brand or "",
            "in_merchant_center": bool(merchant_data),
        })

    return correlated


def main():
    print("=" * 70)
    print("Product-PMax Correlation - Phase 1")
    print("=" * 70)
    print()

    load_env()
    credentials = get_credentials()
    print(f"Google Ads Customer ID: {credentials['customer_id']}")
    print(f"Merchant Center ID: {credentials['merchant_id']}")
    print()

    print("Authenticating...")
    access_token = get_access_token(credentials)
    print("OK")
    print()

    # Get Merchant Center products
    print("Fetching Merchant Center products...")
    try:
        merchant_products = get_merchant_products(credentials, access_token)
        print(f"  Retrieved {len(merchant_products)} products from Merchant Center")
    except Exception as e:
        print(f"  WARNING: Could not fetch Merchant Center data: {e}")
        print("  Continuing with PMax data only...")
        merchant_products = {}
    print()

    # Get PMax shopping performance
    pmax_products = get_shopping_product_performance(credentials, access_token, days=30)
    print(f"  Retrieved {len(pmax_products)} products from PMax")
    print()

    # Correlate data
    print("Correlating data...")
    correlated = correlate_data(merchant_products, pmax_products)

    # Sort by cost (highest spend first)
    correlated.sort(key=lambda x: x["cost"], reverse=True)

    # Output directory
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Write full correlation CSV
    full_csv = output_dir / f"product_pmax_performance_{timestamp}.csv"
    with open(full_csv, "w", newline="") as f:
        if correlated:
            writer = csv.DictWriter(f, fieldnames=correlated[0].keys())
            writer.writeheader()
            writer.writerows(correlated)
    print(f"\nFull performance CSV: {full_csv}")

    # Filter to brand-titled products (brand leakage sources)
    brand_leakage = [p for p in correlated if p["has_brand_in_title"]]
    brand_leakage.sort(key=lambda x: x["cost"], reverse=True)

    brand_csv = output_dir / f"top_brand_leakage_products_{timestamp}.csv"
    with open(brand_csv, "w", newline="") as f:
        if brand_leakage:
            writer = csv.DictWriter(f, fieldnames=brand_leakage[0].keys())
            writer.writeheader()
            writer.writerows(brand_leakage)
    print(f"Brand leakage products CSV: {brand_csv}")

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()

    total_products = len(correlated)
    total_spend = sum(p["cost"] for p in correlated)
    brand_products = len(brand_leakage)
    brand_spend = sum(p["cost"] for p in brand_leakage)

    print(f"Total Products in PMax: {total_products}")
    print(f"Total PMax Spend (30d): ${total_spend:,.2f}")
    print()
    print(f"Products with Brand in Title: {brand_products}")
    print(f"Brand-Titled Product Spend: ${brand_spend:,.2f}")
    print(f"Brand Spend Ratio: {brand_spend/total_spend*100:.1f}%" if total_spend > 0 else "N/A")
    print()

    # Top 10 brand leakage products
    print("=" * 70)
    print("TOP 10 BRAND LEAKAGE PRODUCTS (Smoking Guns)")
    print("=" * 70)
    print()
    print(f"{'Rank':<5} {'Spend':>10} {'Brand':>10} {'ROAS':>8} Title")
    print("-" * 70)

    for i, p in enumerate(brand_leakage[:10], 1):
        title_short = p["title"][:40] if p["title"] else "[No Title]"
        print(f"{i:<5} ${p['cost']:>9,.2f} {p['matched_brand']:>10} {p['roas']:>8.2f} {title_short}")

    print()
    print("-" * 70)
    top10_spend = sum(p["cost"] for p in brand_leakage[:10])
    print(f"TOP 10 TOTAL SPEND: ${top10_spend:,.2f}")
    print()

    # Brand breakdown
    print("BRAND LEAKAGE BY BRAND:")
    print("-" * 70)
    brand_totals = {}
    for p in brand_leakage:
        b = p["matched_brand"]
        if b not in brand_totals:
            brand_totals[b] = {"count": 0, "spend": 0}
        brand_totals[b]["count"] += 1
        brand_totals[b]["spend"] += p["cost"]

    for brand, data in sorted(brand_totals.items(), key=lambda x: x[1]["spend"], reverse=True):
        print(f"  {brand:<15} {data['count']:>5} products  ${data['spend']:>10,.2f}")

    print()
    print("=" * 70)
    print("CORRELATION COMPLETE")
    print("=" * 70)
    print()
    print("NEXT STEPS:")
    print("  1. Review Top 10 products - these are your 'Smoking Guns'")
    print("  2. Consider removing brand names from titles to reduce leakage")
    print("  3. Use product IDs to create negative product lists if needed")


if __name__ == "__main__":
    main()
