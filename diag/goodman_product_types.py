#!/usr/bin/env python3
"""
Follow-up diagnostic: Check Goodman product types vs listing group filters.
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
MERCHANT_CENTER_ID = os.getenv("MERCHANT_CENTER_ID")


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


def main():
    access_token = get_access_token()
    print("=" * 70)
    print("GOODMAN PRODUCT TYPE ANALYSIS")
    print("=" * 70)

    # Get full product details from Merchant Center
    url = f"https://shoppingcontent.googleapis.com/content/v2.1/{MERCHANT_CENTER_ID}/products"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    products = response.json().get("resources", [])

    print("\n--- ALL PRODUCTS WITH THEIR PRODUCT TYPES ---\n")

    for p in products:
        brand = p.get("brand", "Unknown")
        title = p.get("title", "No title")[:50]
        product_type = p.get("productTypes", ["Not set"])
        google_product_category = p.get("googleProductCategory", "Not set")

        is_goodman = "goodman" in brand.lower()
        marker = ">>> " if is_goodman else "    "

        print(f"{marker}{brand}: {title}")
        print(f"      Product Type: {product_type}")
        print(f"      Google Category: {google_product_category}")
        print()

    print("\n" + "=" * 70)
    print("COMPARISON WITH LISTING GROUP FILTERS")
    print("=" * 70)

    print("""
Current Listing Group Filters (from asset group):
  - Type LEVEL1: hvac parts supplies
  - Type LEVEL2: april aire filter cabinets, aprilaire zoning, collars,
                 condensation pumps, copper fittings, drain pans, filters,
                 motors, registers and grilles, etc.

These are all PARTS/ACCESSORIES categories!

If Goodman products have different productTypes (like "air conditioners"
or "hvac systems"), they won't match these filters and won't show.

SOLUTION OPTIONS:
1. Add Goodman's product types to the listing group filters
2. Create a separate asset group for equipment with appropriate filters
3. Remove the restrictive listing group filters to include all products
""")


if __name__ == "__main__":
    main()
