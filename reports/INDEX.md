# Reports Index

**Last Updated:** January 14, 2026

---

## Quick Links — Latest Reports

| Report | Date | Description |
|--------|------|-------------|
| [📊 Google Ads State Report](google_ads_state_report_20260114.md) | Jan 14 | Full account health check — campaigns, Merchant Center, conversions |
| [📈 PMax Bid Strategy Report](pmax_bid_strategy_report_20260114.md) | Jan 14 | 30-day PMax performance, bid changes, daily/hourly breakdown |

---

## Google Ads Reports

### Account Level
| File | Description |
|------|-------------|
| [bidding_audit_report_20260113.txt](account_level/bidding_audit_report_20260113.txt) | Bidding strategy audit |
| [campaign_performance_20260109.csv](account_level/campaign_performance_20260109_133039.csv) | Campaign metrics export |
| [master_audit_summary_20260109.csv](account_level/master_audit_summary_20260109_133429.csv) | Full audit summary |
| [keyword_conflicts_20260108.csv](account_level/keyword_conflicts_20260108_153010.csv) | Keyword conflict analysis |

### Branded Campaign
| File | Description |
|------|-------------|
| [branded_search_state_dump.json](branded/branded_search_state_dump.json) | Full branded campaign state |
| [branded_search_terms_20260109.csv](branded/search_terms/branded_search_terms_20260109_133038.csv) | Search term report |
| [exact_match_candidates_20260109.csv](branded/exact_match/exact_match_candidates_20260109_133038.csv) | Exact match migration candidates |

### PMax / Products Merchant
| File | Description |
|------|-------------|
| [pmax_and_merchant_state_dump.json](pmax_products_merchant/pmax_and_merchant_state_dump.json) | Full PMax + Merchant state |
| [pmax_asset_groups_full_dump.json](pmax_products_merchant/pmax_asset_groups_full_dump.json) | All asset groups |
| [pmax_listing_groups_full_dump.json](pmax_products_merchant/pmax_listing_groups_full_dump.json) | Product listing groups |
| [pmax_brand_leakage_20260109.csv](pmax_products_merchant/brand_leakage/pmax_brand_leakage_20260109_140108.csv) | Brand term leakage |
| [product_pmax_performance_20260109.csv](pmax_products_merchant/product_performance/product_pmax_performance_20260109_141857.csv) | Product-level performance |

### Hardware Offensive
| File | Description |
|------|-------------|
| [hardware_offensive_state_dump.json](hardware_offensive/state_dumps/hardware_offensive_state_dump.json) | Full campaign state |
| [bidding_audit_report_20260113.txt](hardware_offensive/bidding_audit_report_20260113.txt) | Bidding audit |

---

## Merchant Center Reports

| File | Description |
|------|-------------|
| [merchant_feed_audit_20260109.csv](merchant_feed/merchant_feed_audit_20260109_141811.csv) | Feed audit with issues |
| [products_with_brand_titles_20260109.csv](merchant_feed/products_with_brand_titles_20260109_141811.csv) | Title analysis |

---

## BigCommerce SEO Reports

### Rheem
| File | Description |
|------|-------------|
| [seo_execution_log_20260113.csv](seo/rheem/state/seo_execution_log_20260113_170323.csv) | SEO field update log (204 products) |
| [products_flat.csv](seo/rheem/state/20260113_163426/normalized/products_flat.csv) | Full product export |

### Goodman
| File | Description |
|------|-------------|
| [seo_execution_log_20260113.csv](seo/goodman/state/seo_execution_log_20260113_170858.csv) | SEO field update log (528 products) |

### Solace
| File | Description |
|------|-------------|
| [seo_execution_log_20260113.csv](seo/solace/state/seo_execution_log_20260113_171656.csv) | SEO field update log (455 products) |

### Image Alt Text
| File | Description |
|------|-------------|
| [run_manifest_20260114.json](seo/image_alt_text/run_manifest_20260114_131023.json) | Alt text audit manifest |
| [alt_text_execution_log_20260114.csv](seo/image_alt_text/alt_text_execution_log_20260114_131023.csv) | Alt text execution log |

---

## Folder Structure

```
reports/
├── INDEX.md                          ← YOU ARE HERE
├── google_ads_state_report_20260114.md
├── pmax_bid_strategy_report_20260114.md
│
├── account_level/                    ← Account-wide audits
├── branded/                          ← BCD Branded campaign
├── pmax_products_merchant/           ← PMax + Shopping
├── hardware_offensive/               ← Hardware Offensive campaign
├── merchant_feed/                    ← Google Merchant Center
│
└── seo/                              ← BigCommerce SEO
    ├── rheem/
    ├── goodman/
    ├── solace/
    └── image_alt_text/
```

---

## Report Naming Convention

Files follow this pattern:
```
{report_type}_{YYYYMMDD}_{HHMMSS}.{ext}
```

Example: `seo_execution_log_20260113_170323.csv`
- Type: `seo_execution_log`
- Date: January 13, 2026
- Time: 5:03:23 PM
- Format: CSV
