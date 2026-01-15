# HVAC Ads 2026 - Audit & Optimization Tracker

## Overview
Standalone Google Ads audit and optimization tools for Buy Comfort Direct HVAC campaigns.

## Audit Scripts

### 1. PMax Brand Leakage (`audit/pmax_brand_leakage.py`)
```bash
python audit/pmax_brand_leakage.py
```
- Uses `campaign_search_term_insight` report for actual PMax search data
- Falls back to `search_term_view` if needed
- Flags brand terms using `configs/brand_terms.json`
- Shows asset group performance with ROAS
- Outputs: `output/pmax_brand_leakage_*.csv`

### 2. Keyword Conflicts & Exact Match Migration (`audit/keyword_conflicts.py`)
```bash
python audit/keyword_conflicts.py
```
- Pulls `search_term_view` for Branded campaign (last 30 days)
- Identifies high-converting technical terms (model numbers)
- Analyzes match types (Broad/Phrase → Exact migration candidates)
- Scores candidates based on: conversions, ROAS, conv rate, technical patterns
- Outputs:
  - `output/exact_match_candidates_*.csv`
  - `output/branded_search_terms_*.csv`

### 3. Budget Balancer (`audit/budget_balancer.py`)
```bash
python audit/budget_balancer.py
```
- Monitors Conversion Value / Cost (ROAS) across campaigns
- Recommends 5% budget shifts when Non-Branded/PMax hits target ROAS (4.0)
- Tracks history to detect diminishing returns
- Maintains minimum branded budget threshold (30%)
- Outputs:
  - `output/campaign_performance_*.csv`
  - `output/budget_history.json` (persistent tracking)

---

## Audit Results

### Brand Leakage Audit
| Date | Source | Terms Found | Brand Matches | Notes |
|------|--------|-------------|---------------|-------|
| _pending_ | | | | |

### Exact Match Migration
| Date | Candidates | Technical Terms | Est. Savings | Notes |
|------|------------|-----------------|--------------|-------|
| _pending_ | | | | |

### Budget Balancer
| Date | Action | Shift Amount | Reason | Notes |
|------|--------|--------------|--------|-------|
| _pending_ | | | | |

---

## Technical Term Patterns (for Exact Match)

Regex patterns used to identify model numbers:
- `[A-Z]{2,4}[0-9]{2,}[A-Z]*` - Model numbers (RA1424AJ1NA, GSXH501810)
- `ra\d+` - Rheem model prefixes
- `gsx[a-z]*\d+` - Goodman model prefixes
- `rg[a-z]*\d+` - Rheem gas furnace models
- `\d+\s*(ton|seer|btu)` - HVAC specifications

---

## Model-to-Image Mapping

### Rheem
| Model | SKU | Image URL | Status |
|-------|-----|-----------|--------|
| | | | |

### Goodman
| Model | SKU | Image URL | Status |
|-------|-----|-----------|--------|
| | | | |

### Solace
| Model | SKU | Image URL | Status |
|-------|-----|-----------|--------|
| | | | |

---

## Migration Progress

### Phase 1: Audit & Analysis
- [ ] Run PMax brand leakage audit
- [ ] Run exact match migration audit
- [ ] Run budget balancer baseline
- [ ] Document findings

### Phase 2: Cleanup
- [ ] Add brand terms as negative keywords in PMax
- [ ] Create Exact Match ad groups for top candidates
- [ ] Add Exact Match negatives to Broad/Phrase groups
- [ ] Review branded bid strategy

### Phase 3: Optimization
- [ ] Implement budget shift recommendations
- [ ] Monitor Impression Share improvement
- [ ] Track ROAS changes post-migration
- [ ] Adjust target ROAS thresholds

---

## Configuration

### Brand Terms (`configs/brand_terms.json`)
Primary terms:
- rheem, goodman, solace, bcd, buy comfort direct, buycomfortdirect, buy comfort, comfort direct

Variants:
- Rheem: rheem, ruud
- Goodman: goodman, amana, daikin
- Solace: solace, solace air

### Budget Balancer Settings
```python
TARGET_ROAS = 4.0           # Trigger threshold
SHIFT_PERCENT = 0.05        # 5% per shift
MIN_BRANDED_BUDGET = 0.30   # Never below 30%
LOOKBACK_DAYS = 30          # ROAS calculation window
```

### Credentials
Scripts load from (in order):
1. `hvac-ads-2026/.env` (local)
2. `~/BCD_SEO_Intelligence_Engine/.env`
3. `../apps/api/.env`
4. `../.env` (project root)

Required env vars:
- `GOOGLE_ADS_DEVELOPER_TOKEN`
- `GOOGLE_ADS_CLIENT_ID`
- `GOOGLE_ADS_CLIENT_SECRET`
- `GOOGLE_ADS_REFRESH_TOKEN`
- `GOOGLE_ADS_CUSTOMER_ID`
- `GOOGLE_ADS_LOGIN_CUSTOMER_ID` (optional)
