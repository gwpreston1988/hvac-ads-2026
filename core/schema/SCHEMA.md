# Snapshot Schema Definition

## Overview

This document defines the complete file structure and purpose of each snapshot produced by `dump_state.py`. Snapshots are immutable, timestamped captures of Google Ads and Merchant Center state.

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
    │   └── merchant/
    │       ├── products.json
    │       ├── product_statuses.json
    │       └── account_issues.json
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
        └── merchant/
            ├── products.json
            └── issues.json
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

## Field Definitions

See [FIELDS.md](./FIELDS.md) for complete field-level specifications.
