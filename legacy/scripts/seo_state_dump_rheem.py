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
BigCommerce Rheem Product Full State Dump

READ-ONLY extraction of ALL Rheem products with ALL subresources.
No mutations. No summaries. Full export only.
"""

import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

STORE_HASH = os.getenv("BIGCOMMERCE_STORE_HASH")
ACCESS_TOKEN = os.getenv("BIGCOMMERCE_ACCESS_TOKEN")
BASE_URL = f"https://api.bigcommerce.com/stores/{STORE_HASH}/v3"
BASE_URL_V2 = f"https://api.bigcommerce.com/stores/{STORE_HASH}/v2"

HEADERS = {
    "X-Auth-Token": ACCESS_TOKEN,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Output directory
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_BASE = Path(__file__).parent.parent / "reports" / "seo" / "rheem" / "state" / TIMESTAMP
RAW_DIR = OUTPUT_BASE / "raw"
NORM_DIR = OUTPUT_BASE / "normalized"
INDEX_DIR = OUTPUT_BASE / "indexes"
LOG_DIR = OUTPUT_BASE / "logs"

# Manifest tracking
manifest = {
    "start_time": datetime.now().isoformat(),
    "end_time": None,
    "brand": "RHEEM",
    "total_products_exported": 0,
    "pagination_details": {},
    "endpoints_called": [],
    "warnings": [],
}
errors = []


def setup_dirs():
    """Create output directories."""
    for d in [RAW_DIR, NORM_DIR, INDEX_DIR, LOG_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def log_error(endpoint, params, status, response_snippet, attempts):
    """Log an error to errors list."""
    errors.append({
        "timestamp": datetime.now().isoformat(),
        "endpoint": endpoint,
        "params": params,
        "http_status": status,
        "response_snippet": str(response_snippet)[:500],
        "retry_attempts": attempts,
    })


def api_get(endpoint, params=None, base_url=None, retries=3):
    """Make GET request with retries."""
    url = f"{base_url or BASE_URL}{endpoint}"
    manifest["endpoints_called"].append(endpoint)

    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=60)

            if resp.status_code == 429:  # Rate limit
                wait = int(resp.headers.get("X-Rate-Limit-Time-Reset-Ms", 1000)) / 1000
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait + 1)
                continue

            if resp.status_code >= 400:
                if attempt == retries - 1:
                    log_error(endpoint, params, resp.status_code, resp.text, retries)
                    return None
                time.sleep(2 ** attempt)
                continue

            return resp.json()
        except Exception as e:
            if attempt == retries - 1:
                log_error(endpoint, params, 0, str(e), retries)
                return None
            time.sleep(2 ** attempt)

    return None


def paginate_all(endpoint, params=None, base_url=None, key="data"):
    """Paginate through all results."""
    params = params or {}
    params["limit"] = 250
    params["page"] = 1
    all_items = []

    page_details = {"endpoint": endpoint, "pages_fetched": 0, "page_size": 250, "total_items": 0}

    while True:
        result = api_get(endpoint, params, base_url)
        if not result:
            break

        items = result.get(key, result) if isinstance(result, dict) else result
        if not items:
            break

        if isinstance(items, list):
            all_items.extend(items)
            page_details["pages_fetched"] += 1
            page_details["total_items"] = len(all_items)

            # Check for more pages
            meta = result.get("meta", {}).get("pagination", {})
            if meta.get("current_page", 1) >= meta.get("total_pages", 1):
                break
            if len(items) < params["limit"]:
                break

            params["page"] += 1
        else:
            all_items.append(items)
            break

    manifest["pagination_details"][endpoint] = page_details
    return all_items


def write_jsonl(filepath, items):
    """Write items as newline-delimited JSON."""
    with open(filepath, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, separators=(",", ":"), ensure_ascii=False) + "\n")


def write_json(filepath, data):
    """Write data as JSON."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def write_csv(filepath, rows, fieldnames=None):
    """Write rows as CSV."""
    if not rows:
        return
    if not fieldnames:
        fieldnames = list(rows[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    print("=" * 70)
    print("BigCommerce RHEEM Full State Dump")
    print("=" * 70)
    print(f"Store Hash: {STORE_HASH}")
    print(f"Output: {OUTPUT_BASE}")
    print()

    setup_dirs()

    # =========================================================================
    # STEP 1: Get all brands to find Rheem brand_id
    # =========================================================================
    print("[1/8] Fetching brands...")
    brands = paginate_all("/catalog/brands")
    write_jsonl(RAW_DIR / "brands.jsonl", brands)
    print(f"  Total brands: {len(brands)}")

    rheem_brand = None
    for b in brands:
        if b.get("name", "").lower() == "rheem":
            rheem_brand = b
            break

    if not rheem_brand:
        print("ERROR: Rheem brand not found!")
        manifest["warnings"].append("Rheem brand not found in brands list")
        # Try to continue with name-based filtering
        rheem_brand_id = None
    else:
        rheem_brand_id = rheem_brand["id"]
        print(f"  Rheem brand_id: {rheem_brand_id}")

    # =========================================================================
    # STEP 2: Get all categories for reference
    # =========================================================================
    print("\n[2/8] Fetching categories...")
    categories = paginate_all("/catalog/categories")
    write_jsonl(RAW_DIR / "categories.jsonl", categories)
    print(f"  Total categories: {len(categories)}")

    # Build category path index
    cat_by_id = {c["id"]: c for c in categories}

    def get_category_path(cat_id):
        path_parts = []
        current = cat_by_id.get(cat_id)
        while current:
            path_parts.insert(0, current.get("name", ""))
            parent_id = current.get("parent_id", 0)
            current = cat_by_id.get(parent_id) if parent_id else None
        return " > ".join(path_parts)

    category_index = {str(c["id"]): {"id": c["id"], "name": c["name"], "path": get_category_path(c["id"])} for c in categories}
    write_json(INDEX_DIR / "index_category_id_to_path.json", category_index)

    # =========================================================================
    # STEP 3: Get all Rheem products
    # =========================================================================
    print("\n[3/8] Fetching Rheem products...")

    if rheem_brand_id:
        products = paginate_all("/catalog/products", {"brand_id": rheem_brand_id, "include": "variants,images,custom_fields,bulk_pricing_rules,primary_image,modifiers,options"})
    else:
        # Fallback: get all products and filter by name
        all_products = paginate_all("/catalog/products", {"include": "variants,images,custom_fields,bulk_pricing_rules,primary_image,modifiers,options"})
        products = [p for p in all_products if "rheem" in p.get("name", "").lower()]

    print(f"  Rheem products found: {len(products)}")
    manifest["total_products_exported"] = len(products)

    if not products:
        print("WARNING: No Rheem products found!")
        manifest["warnings"].append("No Rheem products found")

    # Write raw products
    write_jsonl(RAW_DIR / "products.jsonl", products)

    # =========================================================================
    # STEP 4: Fetch subresources for each product
    # =========================================================================
    print("\n[4/8] Fetching product subresources...")

    all_variants = []
    all_images = []
    all_custom_fields = []
    all_metafields = []
    all_modifiers = []
    all_options = []
    all_bulk_pricing = []
    all_videos = []
    all_reviews = []
    all_product_categories = []

    for i, product in enumerate(products):
        pid = product["id"]
        if (i + 1) % 50 == 0 or i == 0:
            print(f"  Processing product {i+1}/{len(products)} (id={pid})...")

        # Variants (may already be included)
        variants = product.get("variants", [])
        if not variants:
            v_resp = api_get(f"/catalog/products/{pid}/variants")
            if v_resp:
                variants = v_resp.get("data", [])
        for v in variants:
            v["product_id"] = pid
            all_variants.append(v)

        # Images (may already be included)
        images = product.get("images", [])
        if not images:
            img_resp = api_get(f"/catalog/products/{pid}/images")
            if img_resp:
                images = img_resp.get("data", [])
        for img in images:
            img["product_id"] = pid
            all_images.append(img)

        # Custom fields (may already be included)
        cfields = product.get("custom_fields", [])
        if not cfields:
            cf_resp = api_get(f"/catalog/products/{pid}/custom-fields")
            if cf_resp:
                cfields = cf_resp.get("data", [])
        for cf in cfields:
            cf["product_id"] = pid
            all_custom_fields.append(cf)

        # Metafields (always need separate call)
        mf_resp = api_get(f"/catalog/products/{pid}/metafields")
        if mf_resp:
            metafields = mf_resp.get("data", [])
            for mf in metafields:
                mf["product_id"] = pid
                all_metafields.append(mf)

        # Modifiers
        modifiers = product.get("modifiers", [])
        if not modifiers:
            mod_resp = api_get(f"/catalog/products/{pid}/modifiers")
            if mod_resp:
                modifiers = mod_resp.get("data", [])
        for mod in modifiers:
            mod["product_id"] = pid
            all_modifiers.append(mod)

        # Options
        options = product.get("options", [])
        if not options:
            opt_resp = api_get(f"/catalog/products/{pid}/options")
            if opt_resp:
                options = opt_resp.get("data", [])
        for opt in options:
            opt["product_id"] = pid
            all_options.append(opt)

        # Bulk pricing rules
        bulk = product.get("bulk_pricing_rules", [])
        if not bulk:
            bulk_resp = api_get(f"/catalog/products/{pid}/bulk-pricing-rules")
            if bulk_resp:
                bulk = bulk_resp.get("data", [])
        for b in bulk:
            b["product_id"] = pid
            all_bulk_pricing.append(b)

        # Videos (v2 endpoint)
        vid_resp = api_get(f"/products/{pid}/videos", base_url=BASE_URL_V2)
        if vid_resp and isinstance(vid_resp, list):
            for vid in vid_resp:
                vid["product_id"] = pid
                all_videos.append(vid)

        # Reviews (v3 endpoint)
        rev_resp = api_get(f"/catalog/products/{pid}/reviews")
        if rev_resp:
            reviews = rev_resp.get("data", [])
            for r in reviews:
                r["product_id"] = pid
                all_reviews.append(r)

        # Category assignments
        cats = product.get("categories", [])
        for cat_id in cats:
            all_product_categories.append({
                "product_id": pid,
                "category_id": cat_id,
                "category_path": category_index.get(str(cat_id), {}).get("path", ""),
            })

    # Write raw subresources
    print("\n[5/8] Writing raw subresources...")
    write_jsonl(RAW_DIR / "variants.jsonl", all_variants)
    write_jsonl(RAW_DIR / "images.jsonl", all_images)
    write_jsonl(RAW_DIR / "custom_fields.jsonl", all_custom_fields)
    write_jsonl(RAW_DIR / "metafields.jsonl", all_metafields)
    write_jsonl(RAW_DIR / "modifiers.jsonl", all_modifiers)
    write_jsonl(RAW_DIR / "options.jsonl", all_options)
    write_jsonl(RAW_DIR / "bulk_pricing.jsonl", all_bulk_pricing)
    write_jsonl(RAW_DIR / "videos.jsonl", all_videos)
    write_jsonl(RAW_DIR / "reviews.jsonl", all_reviews)

    print(f"  Variants: {len(all_variants)}")
    print(f"  Images: {len(all_images)}")
    print(f"  Custom fields: {len(all_custom_fields)}")
    print(f"  Metafields: {len(all_metafields)}")
    print(f"  Modifiers: {len(all_modifiers)}")
    print(f"  Options: {len(all_options)}")
    print(f"  Bulk pricing rules: {len(all_bulk_pricing)}")
    print(f"  Videos: {len(all_videos)}")
    print(f"  Reviews: {len(all_reviews)}")

    # =========================================================================
    # STEP 6: Create normalized CSVs
    # =========================================================================
    print("\n[6/8] Creating normalized CSVs...")

    # Products flat CSV
    product_flat_fields = [
        "id", "name", "sku", "type", "availability", "condition", "is_visible",
        "price", "sale_price", "cost_price", "retail_price", "map_price", "calculated_price",
        "inventory_tracking", "inventory_level", "inventory_warning_level",
        "brand_id", "upc", "mpn", "gtin",
        "weight", "width", "height", "depth",
        "page_title", "meta_description", "meta_keywords", "search_keywords",
        "custom_url", "date_created", "date_modified",
        "description", "warranty", "bin_picking_number", "layout_file",
        "categories", "related_products",
    ]

    flat_rows = []
    for p in products:
        row = {}
        for f in product_flat_fields:
            val = p.get(f, "")
            if isinstance(val, (list, dict)):
                val = json.dumps(val)
            row[f] = val
        # Add custom_url path if nested
        if isinstance(p.get("custom_url"), dict):
            row["custom_url"] = p["custom_url"].get("url", "")
        flat_rows.append(row)

    write_csv(NORM_DIR / "products_flat.csv", flat_rows, product_flat_fields)

    # Variants CSV
    variant_fields = ["product_id", "id", "sku", "price", "sale_price", "cost_price",
                      "inventory_level", "weight", "width", "height", "depth",
                      "upc", "mpn", "gtin", "option_values", "image_url"]
    variant_rows = []
    for v in all_variants:
        row = {f: v.get(f, "") for f in variant_fields}
        if isinstance(v.get("option_values"), list):
            row["option_values"] = json.dumps(v["option_values"])
        variant_rows.append(row)
    write_csv(NORM_DIR / "products_variants.csv", variant_rows, variant_fields)

    # Images CSV
    image_fields = ["product_id", "id", "url_standard", "url_thumbnail", "url_tiny", "url_zoom",
                    "description", "sort_order", "is_thumbnail", "date_modified"]
    image_rows = [{f: img.get(f, "") for f in image_fields} for img in all_images]
    write_csv(NORM_DIR / "products_images.csv", image_rows, image_fields)

    # Custom fields CSV
    cf_fields = ["product_id", "id", "name", "value"]
    cf_rows = [{f: cf.get(f, "") for f in cf_fields} for cf in all_custom_fields]
    write_csv(NORM_DIR / "products_custom_fields.csv", cf_rows, cf_fields)

    # Metafields CSV
    mf_fields = ["product_id", "id", "key", "value", "namespace", "permission_set",
                 "resource_type", "resource_id", "description", "date_created", "date_modified"]
    mf_rows = [{f: mf.get(f, "") for f in mf_fields} for mf in all_metafields]
    write_csv(NORM_DIR / "products_metafields.csv", mf_rows, mf_fields)

    # Categories CSV
    write_csv(NORM_DIR / "products_categories.csv", all_product_categories,
              ["product_id", "category_id", "category_path"])

    # Modifiers CSV
    mod_fields = ["product_id", "id", "name", "display_name", "type", "required", "sort_order", "config", "option_values"]
    mod_rows = []
    for m in all_modifiers:
        row = {f: m.get(f, "") for f in mod_fields}
        if isinstance(m.get("config"), dict):
            row["config"] = json.dumps(m["config"])
        if isinstance(m.get("option_values"), list):
            row["option_values"] = json.dumps(m["option_values"])
        mod_rows.append(row)
    write_csv(NORM_DIR / "products_modifiers.csv", mod_rows, mod_fields)

    # Options CSV
    opt_fields = ["product_id", "id", "name", "display_name", "type", "sort_order", "option_values"]
    opt_rows = []
    for o in all_options:
        row = {f: o.get(f, "") for f in opt_fields}
        if isinstance(o.get("option_values"), list):
            row["option_values"] = json.dumps(o["option_values"])
        opt_rows.append(row)
    write_csv(NORM_DIR / "products_options.csv", opt_rows, opt_fields)

    print(f"  products_flat.csv: {len(flat_rows)} rows")
    print(f"  products_variants.csv: {len(variant_rows)} rows")
    print(f"  products_images.csv: {len(image_rows)} rows")
    print(f"  products_custom_fields.csv: {len(cf_rows)} rows")
    print(f"  products_metafields.csv: {len(mf_rows)} rows")
    print(f"  products_categories.csv: {len(all_product_categories)} rows")
    print(f"  products_modifiers.csv: {len(mod_rows)} rows")
    print(f"  products_options.csv: {len(opt_rows)} rows")

    # =========================================================================
    # STEP 7: Create indexes
    # =========================================================================
    print("\n[7/8] Creating indexes...")

    # Index by ID
    index_by_id = {str(p["id"]): {"id": p["id"], "name": p["name"], "sku": p.get("sku", "")} for p in products}
    write_json(INDEX_DIR / "index_products_by_id.json", index_by_id)

    # Index by SKU
    index_by_sku = {}
    for p in products:
        sku = p.get("sku", "")
        if sku:
            index_by_sku[sku] = {"id": p["id"], "name": p["name"], "sku": sku}
    write_json(INDEX_DIR / "index_products_by_sku.json", index_by_sku)

    # Index by URL
    index_by_url = {}
    for p in products:
        url = p.get("custom_url", {})
        if isinstance(url, dict):
            url = url.get("url", "")
        if url:
            index_by_url[url] = {"id": p["id"], "name": p["name"], "url": url}
    write_json(INDEX_DIR / "index_products_by_url.json", index_by_url)

    print(f"  index_products_by_id.json: {len(index_by_id)} entries")
    print(f"  index_products_by_sku.json: {len(index_by_sku)} entries")
    print(f"  index_products_by_url.json: {len(index_by_url)} entries")
    print(f"  index_category_id_to_path.json: {len(category_index)} entries")

    # =========================================================================
    # STEP 8: Write logs and manifest
    # =========================================================================
    print("\n[8/8] Writing logs...")

    manifest["end_time"] = datetime.now().isoformat()
    manifest["counts"] = {
        "products": len(products),
        "variants": len(all_variants),
        "images": len(all_images),
        "custom_fields": len(all_custom_fields),
        "metafields": len(all_metafields),
        "modifiers": len(all_modifiers),
        "options": len(all_options),
        "bulk_pricing_rules": len(all_bulk_pricing),
        "videos": len(all_videos),
        "reviews": len(all_reviews),
        "product_categories": len(all_product_categories),
        "brands": len(brands),
        "categories": len(categories),
    }

    write_json(LOG_DIR / "run_manifest.json", manifest)
    write_jsonl(LOG_DIR / "errors.jsonl", errors)

    # Completeness checklist
    checklist = []
    checklist.append("COMPLETENESS CHECKLIST - RHEEM STATE DUMP")
    checklist.append("=" * 50)
    checklist.append("")
    checklist.append("A) PRODUCT CORE")
    checklist.append(f"   [{'X' if products else ' '}] Products exported: {len(products)}")
    checklist.append(f"   [{'X' if all([p.get('name') for p in products]) else ' '}] Names present")
    checklist.append(f"   [{'X' if all([p.get('sku') for p in products]) else ' '}] SKUs present")
    checklist.append(f"   [{'X' if all([p.get('price') is not None for p in products]) else ' '}] Prices present")
    checklist.append(f"   [{'X' if any([p.get('meta_description') for p in products]) else ' '}] Meta descriptions (some)")
    checklist.append(f"   [{'X' if any([p.get('page_title') for p in products]) else ' '}] Page titles (some)")
    checklist.append("")
    checklist.append("B) PRODUCT RELATIONSHIPS")
    checklist.append(f"   [{'X' if all_variants else ' '}] Variants: {len(all_variants)}")
    checklist.append(f"   [{'X' if all_images else ' '}] Images: {len(all_images)}")
    checklist.append(f"   [{'X' if True else ' '}] Metafields: {len(all_metafields)} (may be empty if none set)")
    checklist.append(f"   [{'X' if True else ' '}] Custom fields: {len(all_custom_fields)}")
    checklist.append(f"   [{'X' if True else ' '}] Modifiers: {len(all_modifiers)}")
    checklist.append(f"   [{'X' if True else ' '}] Options: {len(all_options)}")
    checklist.append(f"   [{'X' if True else ' '}] Videos: {len(all_videos)}")
    checklist.append(f"   [{'X' if True else ' '}] Reviews: {len(all_reviews)}")
    checklist.append(f"   [{'X' if all_product_categories else ' '}] Category assignments: {len(all_product_categories)}")
    checklist.append("")
    checklist.append("C) SEO/INDEXING FIELDS")
    has_urls = sum(1 for p in products if p.get("custom_url"))
    has_meta = sum(1 for p in products if p.get("meta_description"))
    has_title = sum(1 for p in products if p.get("page_title"))
    has_keywords = sum(1 for p in products if p.get("search_keywords"))
    checklist.append(f"   [{'X' if has_urls else ' '}] custom_url present: {has_urls}/{len(products)}")
    checklist.append(f"   [{'X' if has_meta else ' '}] meta_description present: {has_meta}/{len(products)}")
    checklist.append(f"   [{'X' if has_title else ' '}] page_title present: {has_title}/{len(products)}")
    checklist.append(f"   [{'X' if has_keywords else ' '}] search_keywords present: {has_keywords}/{len(products)}")
    checklist.append("")
    checklist.append("D) STORE/GLOBAL CONTEXT")
    checklist.append(f"   [{'X' if brands else ' '}] Brands list: {len(brands)}")
    checklist.append(f"   [{'X' if categories else ' '}] Categories list: {len(categories)}")
    checklist.append(f"   [{'X' if category_index else ' '}] Category path index built")
    checklist.append("")
    checklist.append("ERRORS")
    checklist.append(f"   Total errors logged: {len(errors)}")
    if errors:
        checklist.append("   See logs/errors.jsonl for details")
    checklist.append("")
    checklist.append("STATUS: " + ("COMPLETE" if products and not errors else "COMPLETE WITH WARNINGS" if products else "FAILED"))

    with open(LOG_DIR / "completeness_checklist.txt", "w") as f:
        f.write("\n".join(checklist))

    print(f"  run_manifest.json written")
    print(f"  errors.jsonl: {len(errors)} errors")
    print(f"  completeness_checklist.txt written")

    # Final output
    print()
    print("=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Output directory: {OUTPUT_BASE}")
    print()


if __name__ == "__main__":
    main()
