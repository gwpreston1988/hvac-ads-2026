# Snapshot Schema Definition

## Overview

This document defines the complete file structure and purpose of each snapshot produced by `dump_state.py`. Snapshots are immutable, timestamped captures of Google Ads, Merchant Center, and Google Search Console state.

---

## Directory Structure

```
snapshots/
└── {TIMESTAMP}/                          # ISO 8601: YYYY-MM-DDTHHMMSSZ
    ├── _manifest.json                    # Snapshot metadata
    ├── _index.json                       # ID lookups and quick references
    │
    ├── raw/                              # Exact API responses (minimal transformation)
    │   ├── ads/
    │   │   ├── campaigns.json
    │   │   ├── ad_groups.json
    │   │   ├── keywords.json
    │   │   ├── campaign_negatives.json
    │   │   ├── adgroup_negatives.json
    │   │   ├── ads.json
    │   │   ├── assets.json
    │   │   ├── asset_links.json
    │   │   ├── change_history.json
    │   │   └── performance.json
    │   │
    │   ├── pmax/
    │   │   ├── campaigns.json
    │   │   ├── asset_groups.json
    │   │   ├── asset_group_assets.json
    │   │   ├── listing_groups.json
    │   │   ├── campaign_assets.json
    │   │   └── url_expansion.json
    │   │
    │   ├── merchant/
    │   │   ├── products.json
    │   │   ├── product_statuses.json
    │   │   └── account_issues.json
    │   │
    │   └── gsc/                          # Google Search Console
    │       ├── sites.json                # Verified sites
    │       └── search_analytics.json     # Raw search analytics (last 30 days)
    │
    └── normalized/                       # Flattened, consistent representations
        ├── ads/
        │   ├── campaigns.json
        │   ├── ad_groups.json
        │   ├── keywords.json
        │   ├── negatives.json            # Combined campaign + adgroup negatives
        │   ├── ads.json
        │   ├── assets.json
        │   ├── change_history.json
        │   └── performance.json
        │
        ├── pmax/
        │   ├── campaigns.json
        │   ├── asset_groups.json
        │   ├── assets.json
        │   └── listing_groups.json
        │
        ├── merchant/
        │   ├── products.json
        │   └── issues.json
        │
        └── gsc/                          # Google Search Console (aggregated)
            ├── queries.json              # Top queries by impressions
            ├── pages.json                # Top pages by impressions
            └── summary.json              # Overall stats
```

---

## File Purposes

### Metadata Files

| File | Purpose |
|------|---------|
| `_manifest.json` | Snapshot metadata: timestamp, duration, API versions, error count, account IDs |
| `_index.json` | Quick lookups: campaign ID→name map, product ID→brand map, counts by status |

### Google Ads — Search Campaigns

| File | Purpose |
|------|---------|
| `raw/ads/campaigns.json` | All campaigns (Search, Display, Shopping) with settings, budgets, bidding |
| `raw/ads/ad_groups.json` | All ad groups with status, targeting settings, default bids |
| `raw/ads/keywords.json` | All keywords with match type, status, bids, quality score |
| `raw/ads/campaign_negatives.json` | Campaign-level negative keywords |
| `raw/ads/adgroup_negatives.json` | Ad group-level negative keywords |
| `raw/ads/ads.json` | All ads (RSA) with headlines, descriptions, final URLs |
| `raw/ads/assets.json` | Account-level assets: sitelinks, callouts, structured snippets, calls |
| `raw/ads/asset_links.json` | Asset → campaign/adgroup bindings |
| `raw/ads/change_history.json` | Change events for last 14 days |
| `raw/ads/performance.json` | Metrics: clicks, cost, conversions, ROAS by campaign/adgroup/day |

### Google Ads — Performance Max

| File | Purpose |
|------|---------|
| `raw/pmax/campaigns.json` | PMax campaign settings, status, budgets, goals |
| `raw/pmax/asset_groups.json` | Asset groups with audience signals, final URLs |
| `raw/pmax/asset_group_assets.json` | Assets assigned to each asset group |
| `raw/pmax/listing_groups.json` | Product listing group tree (Shopping targeting) |
| `raw/pmax/campaign_assets.json` | Campaign-level assets for PMax |
| `raw/pmax/url_expansion.json` | URL expansion settings per campaign |

### Merchant Center

| File | Purpose |
|------|---------|
| `raw/merchant/products.json` | All products with attributes: title, brand, price, GTIN, availability |
| `raw/merchant/product_statuses.json` | Eligibility per destination: Shopping, Free Listings, status reasons |
| `raw/merchant/account_issues.json` | Account-level issues and warnings |

### Google Search Console

| File | Purpose |
|------|---------|
| `raw/gsc/sites.json` | Verified sites in GSC account |
| `raw/gsc/search_analytics.json` | Raw search analytics data (last 30 days) with all dimensions |
| `normalized/gsc/queries.json` | Top queries aggregated across all dimensions |
| `normalized/gsc/pages.json` | Top landing pages aggregated across all dimensions |
| `normalized/gsc/summary.json` | Overall stats: total clicks, impressions, avg CTR, avg position |

**Note:** GSC data is READ-ONLY. The dump phase retrieves organic search data for correlation with paid campaigns. No indexing writes or mutations are performed.

---

## Top-Level JSON Structures

### _manifest.json

```json
{
  "snapshot_id": "2026-01-15T143052Z",
  "created_at": "2026-01-15T14:30:52.123456Z",
  "duration_seconds": 47.3,
  "accounts": {
    "google_ads": {
      "customer_id": "1234567890",
      "login_customer_id": "9876543210"
    },
    "merchant_center": {
      "account_id": "5308355318"
    }
  },
  "api_versions": {
    "google_ads": "v19",
    "merchant_center": "v1beta"
  },
  "file_counts": {
    "raw": 16,
    "normalized": 12
  },
  "record_counts": {
    "campaigns": 5,
    "ad_groups": 42,
    "keywords": 387,
    "products": 1763
  },
  "errors": []
}
```

### _index.json

```json
{
  "campaigns": {
    "by_id": {
      "123456789": "Branded - Exact Match",
      "234567890": "Non-Branded - Search",
      "345678901": "PMax - Shopping"
    },
    "by_type": {
      "SEARCH": ["123456789", "234567890"],
      "PERFORMANCE_MAX": ["345678901"]
    },
    "by_status": {
      "ENABLED": ["123456789", "345678901"],
      "PAUSED": ["234567890"]
    }
  },
  "products": {
    "by_brand": {
      "Goodman": 479,
      "Rheem": 199,
      "Solace": 406,
      "Daikin": 25,
      "_other": 654
    },
    "by_status": {
      "eligible": 1109,
      "excluded": 654,
      "disapproved": 0
    }
  },
  "totals": {
    "campaigns": 5,
    "ad_groups": 42,
    "keywords": 387,
    "negatives": 156,
    "products": 1763
  }
}
```

---

## Normalized File Structures

Normalized files flatten nested API responses into consistent, queryable formats. Each record includes:
- Original resource ID
- Human-readable name/title
- Status (using consistent enum values)
- Key metrics where applicable

### normalized/ads/campaigns.json

```json
{
  "extracted_at": "2026-01-15T14:30:52Z",
  "count": 5,
  "records": [
    {
      "id": "123456789",
      "name": "Branded - Exact Match",
      "type": "SEARCH",
      "status": "ENABLED",
      "bidding_strategy": "TARGET_ROAS",
      "bidding_target": 4.0,
      "budget_id": "111111111",
      "budget_amount_micros": 50000000,
      "budget_delivery": "STANDARD",
      "start_date": "2024-01-01",
      "end_date": null,
      "labels": ["branded", "exact-match"]
    }
  ]
}
```

### normalized/ads/keywords.json

```json
{
  "extracted_at": "2026-01-15T14:30:52Z",
  "count": 387,
  "records": [
    {
      "id": "kw_123456789",
      "ad_group_id": "ag_111111111",
      "campaign_id": "123456789",
      "text": "goodman furnace",
      "match_type": "EXACT",
      "status": "ENABLED",
      "cpc_bid_micros": 2500000,
      "quality_score": 8,
      "expected_ctr": "ABOVE_AVERAGE",
      "ad_relevance": "AVERAGE",
      "landing_page_exp": "ABOVE_AVERAGE"
    }
  ]
}
```

### normalized/merchant/products.json

```json
{
  "extracted_at": "2026-01-15T14:30:52Z",
  "count": 1763,
  "records": [
    {
      "id": "?"
      "offer_id": "?"
      "title": "Goodman 3 Ton 14 SEER Air Conditioner",
      "brand": "Goodman",
      "gtin": "123456789012",
      "mpn": "GSX140361",
      "price_amount": "1299.00",
      "price_currency": "USD",
      "availability": "in_stock",
      "condition": "new",
      "product_type": "HVAC > Air Conditioners > Split Systems",
      "custom_labels": {
        "0": "equipment",
        "1": "goodman",
        "2": "ac"
      },
      "destinations": {
        "Shopping_ads": "eligible",
        "Free_listings": "eligible"
      },
      "issues": []
    }
  ]
}
```

---

## Raw vs Normalized

| Aspect | Raw | Normalized |
|--------|-----|------------|
| **Purpose** | Audit trail, debugging | Analysis, reporting |
| **Structure** | Mirrors API response | Flattened, consistent |
| **Fields** | All returned by API | Curated subset |
| **IDs** | Full resource names | Short IDs only |
| **Enums** | API values | Standardized values |
| **Nesting** | Preserved | Flattened |

---

---

## Diagnostic Provenance Files

These files exist outside the snapshot structure and provide operational provenance for changes made outside the baseline pipeline.

### diag/out_of_band_ledger.jsonl

**Purpose:** Append-only ledger of changes made to Google Ads via manual API calls or other tools outside the baseline apply engine. Used by the report generator to show reconciliation status.

**Location:** `diag/out_of_band_ledger.jsonl` (project root, not inside snapshots)

**Format:** JSON Lines (one JSON object per line)

**Entry Structure:**

```json
{
  "timestamp": "2026-01-19T19:39:19Z",
  "action": "restructure_listing_groups",
  "campaign_id": "20815709270",
  "campaign_name": "Products merchant campaign",
  "asset_group_id": "6483780791",
  "before": "22 filters (hvac parts supplies L1 subdivision with L2 subcategories)",
  "after": "5 filters (INCLUDE: goodman 1, rheem, solace; EXCLUDE: everything else)",
  "reason": "Goodman products were not showing in Shopping due to incorrect product type filters",
  "executed_by": "manual_api_call",
  "reconciled_snapshot_id": "2026-01-19T194619Z"
}
```

**Field Definitions:**

| Field | Required | Description |
|-------|----------|-------------|
| `timestamp` | Yes | ISO 8601 UTC timestamp when change was executed |
| `action` | Yes | Short identifier for the change type |
| `campaign_id` | No | Campaign ID affected (if applicable) |
| `campaign_name` | No | Human-readable campaign name |
| `asset_group_id` | No | Asset group ID affected (if applicable) |
| `before` | No | Description of state before change |
| `after` | No | Description of state after change |
| `reason` | No | Why the change was made |
| `executed_by` | No | How the change was executed (e.g., "manual_api_call", "diag_script") |
| `reconciled_snapshot_id` | No | Snapshot ID that captured state after this change |

**Usage Notes:**

- This file is **not part of snapshots** — it tracks operational provenance separately
- Entries should be **appended**, never deleted or overwritten
- The report generator reads the last 10 entries and shows reconciliation status
- A change is considered "reconciled" if:
  - `reconciled_snapshot_id` is explicitly set, OR
  - The current snapshot's `extraction_finished_utc` is after the change `timestamp`

---

## Field Definitions

See [FIELDS.md](./FIELDS.md) for complete field-level specifications.
