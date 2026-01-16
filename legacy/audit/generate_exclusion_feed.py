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
Generate Merchant Center Exclusion Feed

Pulls all products from Merchant Center and creates a supplemental feed
that excludes everything EXCEPT the allowed brands from Shopping ads.

Outputs:
  - output/merchant_supplemental/exclusions_latest.tsv (local)
  - Uploads to GCS bucket for Merchant Center to fetch

Usage:
    python audit/generate_exclusion_feed.py           # Generate and upload
    python audit/generate_exclusion_feed.py --dry-run # Generate only, no upload
"""

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# =============================================================================
# CONFIGURATION - Edit these to control what shows in Shopping ads
# =============================================================================

ALLOWED_BRANDS = [
    "goodman",
    "rheem",
    "solace",
    "daikin",
]

# GCS settings
GCS_BUCKET = "bcd-merchant-feeds"
GCS_PATH = "merchant/supplemental/exclusions_latest.tsv"
GCS_HISTORY_PATH = "merchant/supplemental/history"

# =============================================================================


def load_env():
    """Load environment variables."""
    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path.home() / "hvac-ads-2026" / ".env",
        Path.home() / "bcd-seo-engine" / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            return True
    return False


def get_access_token():
    """Get OAuth access token."""
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
            "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
            "grant_type": "refresh_token",
        },
    )
    if response.status_code != 200:
        print(f"ERROR: Token refresh failed: {response.text}")
        sys.exit(1)
    return response.json()["access_token"]


def get_all_products(merchant_id, access_token):
    """Fetch all products from Merchant Center."""
    url = f"https://merchantapi.googleapis.com/products/v1beta/accounts/{merchant_id}/products"
    headers = {"Authorization": f"Bearer {access_token}"}

    products = []
    next_token = None
    page = 1

    while True:
        params = {"pageSize": 250}
        if next_token:
            params["pageToken"] = next_token

        print(f"  Fetching page {page}...", end=" ", flush=True)
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"\nERROR: API request failed: {response.text}")
            sys.exit(1)

        data = response.json()
        batch = data.get("products", [])

        for product in batch:
            attrs = product.get("attributes", {})
            products.append({
                "id": product.get("offerId", ""),
                "brand": attrs.get("brand", ""),
                "title": attrs.get("title", ""),
            })

        print(f"got {len(batch)}")

        next_token = data.get("nextPageToken")
        if not next_token:
            break
        page += 1

    return products


def should_exclude(product):
    """Check if product should be excluded from Shopping ads."""
    brand = product.get("brand", "")
    brand_lower = brand.lower().strip() if brand else ""

    # If brand matches any allowed brand, DON'T exclude (show it)
    for allowed in ALLOWED_BRANDS:
        if allowed.lower() in brand_lower:
            return False

    # Otherwise, exclude it
    return True


def upload_to_gcs(local_path, gcs_path):
    """Upload file to GCS using gsutil."""
    import subprocess

    full_gcs_path = f"gs://{GCS_BUCKET}/{gcs_path}"

    result = subprocess.run(
        ["gsutil", "cp", str(local_path), full_gcs_path],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"ERROR uploading to GCS: {result.stderr}")
        return False

    return True


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("MERCHANT CENTER EXCLUSION FEED GENERATOR")
    print("=" * 60)
    print()

    print(f"Allowed brands: {', '.join(ALLOWED_BRANDS)}")
    print(f"Mode: {'DRY RUN (no upload)' if dry_run else 'GENERATE + UPLOAD'}")
    print()

    # Load credentials
    if not load_env():
        print("ERROR: No .env file found")
        sys.exit(1)

    merchant_id = os.getenv("MERCHANT_CENTER_ID")
    if not merchant_id:
        print("ERROR: MERCHANT_CENTER_ID not set")
        sys.exit(1)

    print(f"Merchant ID: {merchant_id}")
    print()

    # Get access token
    print("Authenticating...")
    access_token = get_access_token()
    print("OK")
    print()

    # Fetch all products
    print("Fetching products from Merchant Center:")
    products = get_all_products(merchant_id, access_token)
    print(f"\nTotal products: {len(products)}")
    print()

    # Categorize products
    to_exclude = []
    to_show = []

    for product in products:
        if should_exclude(product):
            to_exclude.append(product)
        else:
            to_show.append(product)

    # Summary
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Products to SHOW in Shopping ads:    {len(to_show):>5}")
    print(f"Products to EXCLUDE from Shopping:   {len(to_exclude):>5}")
    print()

    # Brand breakdown of what will show
    brand_counts = {}
    for p in to_show:
        b = p.get("brand") or "(no brand)"
        brand_counts[b] = brand_counts.get(b, 0) + 1

    print("SHOWING by brand:")
    for brand, count in sorted(brand_counts.items(), key=lambda x: -x[1]):
        print(f"  {brand}: {count}")
    print()

    # Generate exclusion feed
    output_dir = Path(__file__).parent.parent / "output" / "merchant_supplemental"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Main file
    tsv_path = output_dir / "exclusions_latest.tsv"
    with open(tsv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["id", "excluded_destination"])
        for product in to_exclude:
            writer.writerow([product["id"], "Shopping_ads"])

    print(f"Generated: {tsv_path}")
    print(f"  {len(to_exclude)} products excluded")
    print()

    # History file
    history_dir = output_dir / "history"
    history_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    history_path = history_dir / f"exclusions_{today}.tsv"

    import shutil
    shutil.copy(tsv_path, history_path)
    print(f"History: {history_path}")
    print()

    # Update manifest
    manifest_path = output_dir / "manifest.json"
    manifest = {
        "feed_name": "Brand Exclusions - Shopping Ads",
        "description": f"Excludes non-{'/'.join(ALLOWED_BRANDS)} products from Shopping ads",
        "gcs_bucket": GCS_BUCKET,
        "gcs_project": "bcd-literature-library",
        "files": {
            "latest": {
                "gcs_path": f"gs://{GCS_BUCKET}/{GCS_PATH}",
                "public_url": f"https://storage.googleapis.com/{GCS_BUCKET}/{GCS_PATH}",
                "format": "TSV",
                "columns": ["id", "excluded_destination"]
            },
            "history": {
                "gcs_path": f"gs://{GCS_BUCKET}/{GCS_HISTORY_PATH}/",
                "pattern": "exclusions_YYYY-MM-DD.tsv"
            }
        },
        "merchant_center": {
            "account_id": merchant_id,
            "feed_type": "supplemental",
            "input_method": "FETCH",
            "fetch_schedule": "manual"
        },
        "allowed_brands": ALLOWED_BRANDS,
        "exclusion_count": len(to_exclude),
        "show_count": len(to_show),
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "refresh_command": "python audit/generate_exclusion_feed.py"
    }

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest: {manifest_path}")
    print()

    # Upload to GCS
    if dry_run:
        print("DRY RUN - Skipping GCS upload")
        print(f"  Would upload to: gs://{GCS_BUCKET}/{GCS_PATH}")
    else:
        print("Uploading to GCS...")

        # Upload latest
        if upload_to_gcs(tsv_path, GCS_PATH):
            print(f"  ✓ Uploaded: gs://{GCS_BUCKET}/{GCS_PATH}")
        else:
            print("  ✗ Upload failed")
            sys.exit(1)

        # Upload history
        history_gcs_path = f"{GCS_HISTORY_PATH}/exclusions_{today}.tsv"
        if upload_to_gcs(history_path, history_gcs_path):
            print(f"  ✓ Uploaded: gs://{GCS_BUCKET}/{history_gcs_path}")

        print()
        print("=" * 60)
        print("DONE!")
        print("=" * 60)
        print()
        print("Next step: Trigger a feed fetch in Merchant Center")
        print("  1. Go to Merchant Center > Products > Feeds")
        print("  2. Find your supplemental feed")
        print("  3. Click 'Fetch now' to pull the updated exclusions")
        print()
        print(f"Public URL: https://storage.googleapis.com/{GCS_BUCKET}/{GCS_PATH}")


if __name__ == "__main__":
    main()
