#!/usr/bin/env python3
"""
STANDALONE SCRIPT - Does NOT touch the existing pipeline.

Restructures PMax listing group filters to show ONLY equipment brands:
  - goodman 1 (INCLUDED)
  - rheem (INCLUDED)
  - solace (INCLUDED)
  - Everything else (EXCLUDED) - blocks parts/supplies

Usage: python diag/fix_listing_groups_equipment_only.py
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# Configuration
CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
LOGIN_CUSTOMER_ID = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("GOOGLE_ADS_REFRESH_TOKEN")

PMAX_CAMPAIGN_ID = "20815709270"
ASSET_GROUP_ID = "6483780791"

# Equipment brand product types to INCLUDE
EQUIPMENT_BRANDS = ["goodman 1", "rheem", "solace"]


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
        print(f"Query Error: {response.status_code}")
        print(response.text)
        return []
    return response.json().get("results", [])


def google_ads_mutate(access_token, operations):
    """Execute mutate operations on asset_group_listing_group_filter."""
    url = f"https://googleads.googleapis.com/v19/customers/{CUSTOMER_ID}/assetGroupListingGroupFilters:mutate"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": DEVELOPER_TOKEN,
        "Content-Type": "application/json",
    }
    if LOGIN_CUSTOMER_ID:
        headers["login-customer-id"] = LOGIN_CUSTOMER_ID

    payload = {"operations": operations}
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        print(f"Mutate Error: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        return None

    return response.json()


def get_current_filters(access_token):
    """Get all current listing group filters with hierarchy info."""
    query = f"""
        SELECT
            asset_group_listing_group_filter.resource_name,
            asset_group_listing_group_filter.id,
            asset_group_listing_group_filter.type,
            asset_group_listing_group_filter.parent_listing_group_filter,
            asset_group_listing_group_filter.case_value.product_type.value,
            asset_group_listing_group_filter.case_value.product_type.level
        FROM asset_group_listing_group_filter
        WHERE asset_group.id = {ASSET_GROUP_ID}
    """
    results = google_ads_query(access_token, query)

    filters = []
    for r in results:
        f = r.get("assetGroupListingGroupFilter", {})
        filters.append({
            "resource_name": f.get("resourceName"),
            "id": f.get("id"),
            "type": f.get("type"),
            "parent": f.get("parentListingGroupFilter"),
            "product_type_value": f.get("caseValue", {}).get("productType", {}).get("value"),
            "product_type_level": f.get("caseValue", {}).get("productType", {}).get("level"),
        })

    return filters


def build_atomic_operations(filters, root_resource_name, asset_group_resource_name):
    """
    Build atomic operations that maintain tree validity:
    1. CREATE new brand filters + new "everything else" EXCLUDED
    2. REMOVE old L2 filters (leaves under hvac parts supplies)
    3. REMOVE old hvac parts supplies SUBDIVISION
    4. REMOVE old L1 "everything else" INCLUDED

    Order matters! Creates go first, then removes from leaves to parents.
    """
    operations = []

    # STEP 1: CREATE new structure first
    # Create UNIT_INCLUDED for each equipment brand
    for brand in EQUIPMENT_BRANDS:
        operations.append({
            "create": {
                "assetGroup": asset_group_resource_name,
                "parentListingGroupFilter": root_resource_name,
                "type": "UNIT_INCLUDED",
                "listingSource": "SHOPPING",
                "caseValue": {
                    "productType": {
                        "level": "LEVEL1",
                        "value": brand
                    }
                }
            }
        })

    # Create UNIT_EXCLUDED for "Everything else" (no value = everything else)
    operations.append({
        "create": {
            "assetGroup": asset_group_resource_name,
            "parentListingGroupFilter": root_resource_name,
            "type": "UNIT_EXCLUDED",
            "listingSource": "SHOPPING",
            "caseValue": {
                "productType": {
                    "level": "LEVEL1"
                    # No value means "everything else"
                }
            }
        }
    })

    # STEP 2: Build delete operations (leaves first, then parents)
    # Find the hvac parts supplies subdivision
    hvac_parts_subdivision = None
    old_l1_everything_else = None
    l2_filters = []

    for f in filters:
        if f["parent"] is None:
            # This is root, skip
            continue
        elif f["type"] == "SUBDIVISION" and f.get("product_type_value") == "hvac parts supplies":
            hvac_parts_subdivision = f
        elif f["type"] == "UNIT_INCLUDED" and f.get("product_type_level") == "LEVEL1" and f.get("product_type_value") is None:
            old_l1_everything_else = f
        elif f.get("product_type_level") == "LEVEL2":
            l2_filters.append(f)

    # Remove L2 filters first (children of hvac parts supplies)
    for f in l2_filters:
        operations.append({"remove": f["resource_name"]})

    # Remove hvac parts supplies subdivision
    if hvac_parts_subdivision:
        operations.append({"remove": hvac_parts_subdivision["resource_name"]})

    # Remove old L1 everything else
    if old_l1_everything_else:
        operations.append({"remove": old_l1_everything_else["resource_name"]})

    return operations


def main():
    timestamp = datetime.now(timezone.utc).isoformat()
    print("=" * 80)
    print("LISTING GROUP RESTRUCTURE: EQUIPMENT BRANDS ONLY")
    print(f"Timestamp: {timestamp}")
    print("=" * 80)

    access_token = get_access_token()
    print("\n✓ Authentication successful")

    # Step 1: Get current filters
    print("\n" + "-" * 80)
    print("STEP 1: Analyzing current listing group structure")
    print("-" * 80)

    filters = get_current_filters(access_token)
    print(f"Found {len(filters)} existing filters")

    root_filter = None
    for f in filters:
        if f["parent"] is None:
            root_filter = f
            print(f"  ROOT: {f['resource_name']} (ID: {f['id']})")
        else:
            pt_val = f.get("product_type_value", "Everything else")
            print(f"  {f['type']}: {pt_val} (ID: {f['id']})")

    if not root_filter:
        print("\nERROR: No root filter found!")
        return

    # Step 2: Build atomic operations
    print("\n" + "-" * 80)
    print("STEP 2: Building atomic restructure operations")
    print("-" * 80)

    asset_group_resource = f"customers/{CUSTOMER_ID}/assetGroups/{ASSET_GROUP_ID}"
    operations = build_atomic_operations(
        filters,
        root_filter["resource_name"],
        asset_group_resource
    )

    creates = [op for op in operations if "create" in op]
    removes = [op for op in operations if "remove" in op]

    print(f"Operations to execute atomically:")
    print(f"  - {len(creates)} CREATE operations (new equipment brand filters)")
    print(f"  - {len(removes)} REMOVE operations (old parts filters)")

    print("\nCREATE operations:")
    for op in creates:
        create_data = op.get("create", {})
        case_val = create_data.get("caseValue", {}).get("productType", {})
        brand = case_val.get("value", "Everything else")
        ftype = create_data.get("type")
        print(f"  + {ftype}: {brand}")

    print("\nREMOVE operations:")
    for op in removes:
        resource = op.get("remove", "")
        filter_id = resource.split("~")[-1] if "~" in resource else resource
        # Find matching filter for display
        for f in filters:
            if f["resource_name"] == resource:
                pt_val = f.get("product_type_value", "Everything else")
                print(f"  - {f['type']}: {pt_val} (ID: {filter_id})")
                break

    # Step 3: Execute atomic operation
    print("\n" + "-" * 80)
    print("STEP 3: Executing atomic restructure")
    print("-" * 80)

    result = google_ads_mutate(access_token, operations)
    if result:
        print(f"\n✓ Successfully executed {len(operations)} operations")
        created_resources = result.get("results", [])
        print(f"  Created {len([r for r in created_resources if r.get('resourceName')])} new filters")
    else:
        print("\n✗ Operation failed!")
        return

    # Step 4: Verify new structure
    print("\n" + "-" * 80)
    print("STEP 4: Verifying new structure")
    print("-" * 80)

    new_filters = get_current_filters(access_token)
    print(f"Total filters now: {len(new_filters)}")

    included_brands = []
    excluded = []

    for f in new_filters:
        pt_val = f.get("product_type_value", "Everything else")
        if f["type"] == "UNIT_INCLUDED":
            included_brands.append(pt_val)
        elif f["type"] == "UNIT_EXCLUDED":
            excluded.append(pt_val)

    print("\nNew structure:")
    print("  INCLUDED product types:")
    for b in included_brands:
        print(f"    ✓ {b}")

    print("  EXCLUDED product types:")
    for e in excluded:
        print(f"    ✗ {e}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY - CHANGES MADE")
    print("=" * 80)

    summary = {
        "timestamp": timestamp,
        "campaign_id": PMAX_CAMPAIGN_ID,
        "asset_group_id": ASSET_GROUP_ID,
        "action": "restructure_listing_groups",
        "operations": {
            "creates": len(creates),
            "removes": len(removes)
        },
        "before": {
            "total_filters": len(filters),
            "structure": "hvac parts supplies (L1 SUBDIVISION) with L2 subcategories"
        },
        "after": {
            "total_filters": len(new_filters),
            "included": EQUIPMENT_BRANDS,
            "excluded": ["Everything else (all other product types)"]
        },
        "effect": "PMax will now show ONLY Goodman, Rheem, Solace equipment. Parts/supplies excluded."
    }

    print(json.dumps(summary, indent=2))

    # Save summary for reference
    summary_path = Path(__file__).parent / "listing_group_change_log.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n✓ Change log saved to: {summary_path}")

    print("\n" + "=" * 80)
    print("INTEGRATION NOTES (for adding to main pipeline later)")
    print("=" * 80)
    print("""
KEY API PATTERNS USED:

1. QUERY listing group filters:
   ```
   SELECT asset_group_listing_group_filter.resource_name,
          asset_group_listing_group_filter.id,
          asset_group_listing_group_filter.type,
          asset_group_listing_group_filter.parent_listing_group_filter,
          asset_group_listing_group_filter.case_value.product_type.value,
          asset_group_listing_group_filter.case_value.product_type.level
   FROM asset_group_listing_group_filter
   WHERE asset_group.id = {ASSET_GROUP_ID}
   ```

2. ATOMIC MUTATE (creates before removes to maintain valid tree):
   ```
   POST /v19/customers/{customer_id}/assetGroupListingGroupFilters:mutate
   {
     "operations": [
       // CREATEs first
       {"create": {...}},
       {"create": {...}},
       // REMOVEs second (leaves first, then parents)
       {"remove": "customers/.../assetGroupListingGroupFilters/..."},
       {"remove": "customers/.../assetGroupListingGroupFilters/..."}
     ]
   }
   ```

3. CREATE filter structure:
   ```
   {
     "create": {
       "assetGroup": "customers/{cid}/assetGroups/{ag_id}",
       "parentListingGroupFilter": "customers/{cid}/assetGroupListingGroupFilters/{root_id}",
       "type": "UNIT_INCLUDED",  // or UNIT_EXCLUDED
       "caseValue": {
         "productType": {
           "level": "LEVEL1",
           "value": "goodman 1"  // omit value for "Everything else"
         }
       }
     }
   }
   ```

4. CRITICAL: Tree must be valid after operation completes
   - CREATEs processed before REMOVEs in same atomic call
   - Delete leaves before parents
   - Never delete ROOT
   - Always maintain an "everything else" child for SUBDIVISION nodes
""")


if __name__ == "__main__":
    main()
