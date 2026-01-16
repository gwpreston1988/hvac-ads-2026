# SEO Domain - BigCommerce Catalog Management

## Overview

This domain handles BigCommerce SEO state dumps and controlled updates for the Buy Comfort Direct catalog.

## Philosophy

1. **Extraction first** - Dump current state from BigCommerce API before any analysis
2. **Analysis second** - Compare state against rules, identify gaps and opportunities
3. **Proposals third** - Generate change proposals as reviewable artifacts
4. **Apply only when explicitly requested** - No mutations without explicit user approval

## Directory Structure

```
seo/
├── audit/                    # Extraction and analysis scripts
├── configs/                  # Configuration files
│   ├── templates/            # Reusable templates
│   ├── seo_fields_allowlist.json
│   ├── rheem_product_filters.json
│   └── slug_rules.json
└── README.md

reports/seo/
├── rheem/
│   ├── state/                # Raw state dumps from BigCommerce
│   ├── analysis/             # Gap analysis and coverage reports
│   └── proposals/            # Generated change proposals (review before apply)
└── _shared/                  # Cross-brand shared reports
```

## Scripts

| Script | Purpose | Output Location |
|--------|---------|-----------------|
| `bc_rheem_state_dump.py` | Extract Rheem product SEO fields | `reports/seo/rheem/state/` |
| `bc_catalog_state_dump.py` | Full catalog SEO state extraction | `reports/seo/_shared/` |
| `bc_seo_field_coverage.py` | Analyze SEO field coverage | `reports/seo/rheem/analysis/` |

## Credentials

Scripts use BigCommerce credentials from `.env`:
- `BIGCOMMERCE_STORE_HASH`
- `BIGCOMMERCE_ACCESS_TOKEN`
- `BIGCOMMERCE_CLIENT_ID`

## Usage

```bash
# Step 1: Extract current state
python seo/audit/bc_rheem_state_dump.py

# Step 2: Analyze coverage
python seo/audit/bc_seo_field_coverage.py

# Step 3: Review proposals in reports/seo/rheem/proposals/
# Step 4: Apply only when explicitly requested
```
