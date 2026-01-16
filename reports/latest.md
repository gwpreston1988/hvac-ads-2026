# Buy Comfort Direct
# Google Ads & Merchant Center Health Report

---

## SNAPSHOT PROVENANCE

> **This report is generated from snapshot data only. NO LIVE API CALLS.**

| Field | Value |
|-------|-------|
| Snapshot ID | `2026-01-15T202326Z` |
| Snapshot Version | `A3.0` |
| Extraction Started (UTC) | `2026-01-15T20:23:26.554143Z` |
| Extraction Finished (UTC) | `2026-01-15T20:23:51.480532Z` |
| Google Ads Customer ID | `9256598060` |
| Merchant Center ID | `5308355318` |
| Raw Records Extracted | 17295 |
| Normalized Records | 15145 |
| Validation Errors | 0 |
| Validation Warnings | 0 |

---

## Confidence & Freshness

**Snapshot Age:** 20.0 hours

**Verdict:** 🟡 **YELLOW**

- Snapshot age 20.0h > 6h threshold

### Account Fingerprint

| Metric | Value |
|--------|-------|
| Total Campaigns | 8 |
| Enabled Campaigns | 3 |
| Performance Max | 4 |
| Search Campaigns | 3 |
| **Branded Campaign** | BCD Branded (ID: 20958985895) |
| Branded Bidding Strategy | MANUAL_CPC |
| Branded Enabled Keywords | 3 |
| Top Keywords | buy comfort direct, buycomfortdirect, buycomfortdirect.com |
| Branded Negative Keywords | 0 |
| Last Branded Change | 2026-01-13 13:31:19.825871 |


---

**Report Scope**

| Field | Value |
|-------|-------|
| Snapshot ID | `2026-01-15T202326Z` |
| Snapshot Timestamp (UTC) | `2026-01-15T20:23:51.480532Z` |
| Report Generated (UTC) | `2026-01-16T16:24:26Z` |
| Data Sources | Google Ads (Search + PMax), Merchant Center |

---

## SECTION 1 — Executive Summary (Read This First)

| Question | Answer |
|----------|--------|
| Are ads running? | ✓ Yes — 4 active campaigns, $4,399.21 spent last 7 days |
| Is brand traffic protected? | WARN (see Section 4) |
| Are products showing in Google Shopping? | ✓ 1,089/1,101 equipment approved (99%) |

**Biggest current risk:**
12 equipment products currently disapproved in Merchant Center. Check image links and landing pages.

**What is stable today:**
- Ad campaigns are active and spending normally
- Merchant Center feed is 99% approved

### What This Means

Your advertising campaigns spent $4,399.21 over the last 7 days. Your equipment catalog has 1,089 items approved for Shopping ads. 12 equipment products are currently disapproved and need attention.

This summary answers the most common questions a business owner might have. "Are ads running" tells you if campaigns are active and serving. "Brand traffic protected" tells you if the Branded campaign is properly constrained to avoid budget waste. "Products showing" tells you if your inventory is visible in Google Shopping results.

---

## SECTION 2 — Campaign Overview (What Each Campaign Does)

### 2.1 BCD Branded (Search)

| Field | Value |
|-------|-------|
| Campaign ID | 20958985895 |
| Status | ENABLED |
| Purpose | Capture searches for "Buy Comfort Direct" and our store name |

**What it shows for:**
- Searches containing our business name
- Variations like "buycomfortdirect", "buy comfort", "bcd hvac"

**What it should NOT show for:**
- Manufacturer names (Rheem, Goodman, Solace)
- Generic HVAC terms (air conditioner, furnace)
- Competitor names

**Current guardrails:**
- Negative keywords for manufacturer names; exact match on brand terms

---

### 2.2 Products Merchant Campaign (Performance Max)

| Field | Value |
|-------|-------|
| Campaign ID | 20815709270 |
| Status | ENABLED |
| Merchant ID Linked | 5308355318 |
| Purpose | Show products in Google Shopping, YouTube, Display, Discovery |

**What it controls:**
- Shopping ads (product listings with images and prices)
- Discovery placements
- YouTube video placements
- Display network (if enabled)

**What it should NOT control:**
- Searches for our business name (those go to Branded)
- Generic informational queries

**Current bidding strategy:**
- MAXIMIZE_CONVERSION_VALUE
- Target ROAS: 1.36

---

### 2.3 Hardware Offensive (Search)

| Field | Value |
|-------|-------|
| Campaign ID | 23445812072 |
| Status | ENABLED |
| Purpose | Capture non-branded HVAC searches (model numbers, generic terms) |

**Expected behavior in early days:**
- Learning phase takes 2-4 weeks
- Low conversion volume initially is normal
- CPCs may fluctuate as Google learns

**Current state:**
- Newly launched — in learning phase

---

### 2.4 Other Campaigns

These campaigns exist in the account but are not actively running:

| Campaign | Status | Notes |
|----------|--------|-------|
| BCD Default Campaign | PAUSED | PERFORMANCE_MAX |
| BCD Heating | PAUSED | SEARCH |
| Products merchant campaign 12AM-4PM | PAUSED | PERFORMANCE_MAX |
| Products merchant campaign #2 | PAUSED | PERFORMANCE_MAX |
| Standard Shopping Campaign | PAUSED | SHOPPING |
| BCD Default Campaign | PAUSED | UNKNOWN |
| Products merchant campaign 12AM-4PM | PAUSED | UNKNOWN |
| Products merchant campaign #2 | PAUSED | UNKNOWN |

These are listed for completeness. Paused campaigns do not spend money.

---

## SECTION 3 — Spend & Performance Snapshot

### Last 7 Days Summary

| Campaign | Spend | Clicks | Impressions | Conversions | Conv. Value | ROAS |
|----------|-------|--------|-------------|-------------|-------------|------|
| Products merchant campaign | $3,697.94 | 1,444 | 120,508 | 16.95 | $11,590.61 | 3.13 |
| BCD Branded | $519.76 | 70 | 766 | 3.00 | $893.81 | 1.72 |
| BCD - Hardware Offensive - 202 | $128.62 | 997 | 11,294 | 0.00 | $0.00 | 0.00 |
| Standard Shopping Campaign | $52.89 | 60 | 3,128 | 0.00 | $0.00 | 0.00 |

### Last 30 Days Summary

| Campaign | Spend | Clicks | Impressions | Conversions | Conv. Value | ROAS |
|----------|-------|--------|-------------|-------------|-------------|------|
| Products merchant campaign | $17,536.40 | 8,036 | 782,448 | 74.40 | $37,268.27 | 2.13 |
| BCD Branded | $1,634.87 | 264 | 1,958 | 19.52 | $12,301.23 | 7.52 |
| BCD - Hardware Offensive - 202 | $128.62 | 997 | 11,294 | 0.00 | $0.00 | 0.00 |
| Standard Shopping Campaign | $52.89 | 60 | 3,128 | 0.00 | $0.00 | 0.00 |

### How to Read This

- **Spend**: Total cost for clicks during this period
- **Clicks**: Number of times someone clicked an ad
- **Impressions**: Number of times an ad was shown (does not cost money)
- **Conversions**: Actions we told Google to track (purchases, calls, form fills)
- **Conv. Value**: Dollar value assigned to those conversions
- **ROAS**: Return on Ad Spend = Conv. Value / Spend (higher is better; 4.0 = $4 revenue per $1 spent)

**Note:** Performance data comes from the snapshot and may not include the current partial day.

---

## SECTION 4 — Brand Protection Check

**Brand Protection Check: WARN** — Avg CPC $6.19 > $2.00 threshold.

**Risk signals:**
- ⚠ Avg CPC $6.19 > $2.00 threshold
- ⚠ 8 keyword change(s) in last 14 days

*Structure is correct but operational metrics need attention.*

### Branded Campaign CPC by Period

| Period | Avg CPC |
|--------|---------|
| Today (2026-01-15, partial) | N/A |
| Yesterday | $0.54 |
| Last 7 days | $7.43 |
| Last 30 days | $6.19 |

### Branded Campaign Keyword Analysis

| Metric | Value |
|--------|-------|
| Keywords analyzed | N/A (summary mode) |
| Brand keywords | N/A |
| Non-brand keywords | N/A (N/A) |
| Total spend (snapshot period) | N/A |

### Enabled Keywords in Branded Campaign

| Keyword | Match Type | Classification |
|---------|------------|----------------|
| (detailed view disabled — use --deep-audit flag) | - | - |

### Issues Requiring Attention

| Keyword | Match Type | Issue | Action Needed |
|---------|------------|-------|---------------|
| (detailed view disabled) | - | - | - |

**What this means:**
The Brand Protection Check validates that the Branded campaign is constrained to brand terms only (exact/phrase match) with Manual CPC bidding. This prevents budget waste on generic searches that should go through other campaigns. A PASS result means the campaign structure is correct. A FAIL result identifies specific issues to address.

---

## SECTION 5 — Merchant Center & Shopping Eligibility

### Overall Product Eligibility

| Status | Count | Percentage |
|--------|-------|------------|
| Approved | 1,089 | 98.9% |
| Disapproved | 12 | 1.1% |
| Pending | 0 | 0.0% |
| **Total** | 1,101 | 100% |

### Eligibility by Brand

| Brand | Total Products | Approved | Disapproved | Approval Rate |
|-------|----------------|----------|-------------|---------------|
| Rheem | 197 | 196 | 1 | 99.5% |
| Goodman | 530 | 523 | 7 | 98.7% |
| Solace | 349 | 345 | 4 | 98.9% |
| Daikin | 25 | 25 | 0 | 100.0% |

### Disapproved Products (If Any)

| Offer ID | Title | Brand | Disapproval Reason | Fix Owner |
|----------|-------|-------|-------------------|-----------|
| S-GLZS4BA3610,S-AWST36LU1308A | SOLACE 3 Ton 14.3 SEER2 R-32 Heat Pump S | Solace | image_link_internal_error | Feed |
| S-GLXT7CA6010,S-CAPTA6030C3,S-GRVT800805CN | SOLACE 5 Ton 17.2 SEER2 R-32 80% AFUE 80 | Solace | image_link_internal_error | Feed |
| GLZS4MA1810 | Goodman 1.5 Ton Heat Pump 14.3 SEER2 7.8 | Goodman | image_link_internal_error | Feed |
| CHPTA2426B3 | Goodman CHPTA2426B3 1½ - 2 Ton R-32 Evap | Goodman | image_link_internal_error | Feed |
| S-GPHM54231 | Solace 3.5 Ton 15.2 SEER2 Packaged Air C | Solace | image_link_internal_error | Feed |
| S-GPGM34810031 | Solace 4 Ton 13.4 SEER2 Packaged Gas/Ele | Solace | image_link_internal_error | Feed |
| GLXT7CA4810 | Goodman 4 Ton R-32 Air Conditioner Conde | Goodman | landing_page_error | Site |
| R962V0855A21M4SCAP | RHEEM R962V0855A21M4SCAP - 85,000 BTU 96 | Rheem | image_link_internal_error | Feed |
| S-GLXS4BA3610,S-GR9S920603BNA,S-CAPTA3626B3 | SOLACE 3 Ton 14.3 SEER2 R-32 92% AFUE Ga | Solace | image_link_internal_error | Feed |
| GXV6SS4810 | Goodman 4 Ton R-32 Air Conditioner Conde | Goodman | image_link_internal_error | Feed |
| ... | (2 more) | ... | ... | ... |

**Fix Owner Legend:**
- **Feed**: Issue with product data we send to Google (fix in BigCommerce or feed settings)
- **Site**: Issue with the landing page (fix on website)
- **Policy**: Google policy violation (may require product changes or appeal)

### What Eligibility Means

A product must be "Approved" to appear in Google Shopping results. Disapproved products cannot show ads. The approval rate tells you what percentage of your catalog is actually eligible to advertise.

### What Disapproval Means

Disapproval is not a penalty. It means Google found an issue with the product data or landing page. Most disapprovals can be fixed by correcting the product feed or website. Products remain disapproved until the issue is resolved and Google re-crawls the data.

---

## SECTION 6 — Bidding & Cost Control Status

| Campaign | Bid Strategy | Target | Daily Budget | Notes |
|----------|--------------|--------|--------------|-------|
| BCD Branded | MANUAL_CPC | - | $200.00 | Manual bids |
| Products PMax | MAXIMIZE_CONVERSION_VALUE | tROAS 1.36 | $750.00 | Automated |
| Hardware Offensive | MAXIMIZE_CONVERSION_VALUE | tROAS 3.5 | $50.00 | Automated |

### Understanding Bid Strategies

- **Maximize Conversion Value (tROAS)**: Google automatically sets bids to maximize revenue while targeting a specific return on ad spend. A target of 4.0 means Google aims for $4 in conversion value per $1 spent.

- **Maximize Conversions (tCPA)**: Google automatically sets bids to get the most conversions at or below a target cost per conversion.

- **Manual CPC**: You set the maximum cost per click. Google will not exceed this amount.

### Why Costs Differ Across Campaigns

- **Branded searches** typically have lower CPCs because there is less competition for your own business name.
- **Shopping/PMax** CPCs vary based on product category and competition.
- **Non-branded search** CPCs are often higher because many advertisers compete for generic terms.

---

## SECTION 7 — Recent Changes & Risk Check

### Recent Changes (Last 14 Days)

| Date | Resource Type | Change Type | Description |
|------|---------------|-------------|-------------|
|  | CAMPAIGN | UNKNOWN |  |
|  | CUSTOMER_ASSET | UNKNOWN |  |
|  | CUSTOMER_ASSET | UNKNOWN |  |
|  | CUSTOMER_ASSET | UNKNOWN |  |
|  | CUSTOMER_ASSET | UNKNOWN |  |
|  | CUSTOMER_ASSET | UNKNOWN |  |
|  | CUSTOMER_ASSET | UNKNOWN |  |
|  | AD_GROUP_CRITERION | UNKNOWN |  |
|  | AD_GROUP_CRITERION | UNKNOWN |  |
|  | CAMPAIGN | UNKNOWN |  |
|  | CAMPAIGN_BUDGET | UNKNOWN |  |
|  | CAMPAIGN | UNKNOWN |  |
|  | CAMPAIGN | UNKNOWN |  |
|  | CAMPAIGN_CRITERION | UNKNOWN |  |
|  | CAMPAIGN | UNKNOWN |  |

### Change Summary

| Change Type | Count |
|-------------|-------|
| UNKNOWN | 50 |

### Automation Status

| Setting | Status | Risk Level |
|---------|--------|------------|
| Auto-apply recommendations | Cannot verify via API | Unknown |
| Automated bidding active | Enabled (Smart Bidding) | Low (expected) |
| Performance Max enabled | Yes | Medium (requires monitoring) |

**What this means:**
- "Auto-apply recommendations" can make changes without your approval. This should typically be OFF unless intentionally enabled.
- "Automated bidding" means Google adjusts bids automatically. This is expected and normal for modern campaigns.
- "Performance Max" gives Google more control over placements. This is by design but requires monitoring.

---

## SECTION 8 — What Is Working As Intended

These items are functioning normally:

- 4 campaigns are enabled and configured
- Campaigns are spending normally ($4,399.21 last 7 days)
- Merchant Center feed is 99% approved
- Snapshot extraction completed with no validation errors

---

## SECTION 9 — What Is Still Early / Learning

These items need more time before we can evaluate them:

- **Hardware Offensive campaign** — Newly launched, in learning phase. Performance data will be limited for 2-4 weeks.
- **Performance Max optimization** — Google's algorithm continuously learns; avoid frequent changes.

### Why "Learning" Is Normal

When a campaign is new or has significant changes, Google's algorithm needs time to understand what works. During this period:

- Performance may be inconsistent
- CPCs may fluctuate more than usual
- Conversion volume may be low

This is not a problem to fix. It is part of how automated bidding works. The learning phase typically lasts 1-2 weeks for small changes and 2-4 weeks for new campaigns.

---

## SECTION 10 — Next Review Checkpoints

### Next 48 Hours (Observation Only)

- [ ] Confirm all active campaigns are serving (impressions > 0)
- [ ] Check for any new disapprovals in Merchant Center
- [ ] Verify no unexpected budget exhaustion
- [ ] Note any dramatic CPC changes

### Next 7 Days

- [ ] Review Hardware Offensive learning progress
- [ ] Check PMax search term insights (if available)
- [ ] Monitor brand protection in Branded campaign
- [ ] Verify Merchant Center disapprovals are being resolved

### These Are Observations, Not Actions

The checkpoints above are for monitoring only. No changes should be made based on short-term fluctuations. Ads require consistent data over time to evaluate properly.

---

## SECTION 11 — Known Limitations & Planned Improvements

### Current Data Gaps

| Gap | Impact | Planned Fix |
|-----|--------|-------------|
| Search term data limited for PMax | Cannot fully audit brand leakage | Await Google's expanded reporting |
| No conversion goal audit | May be tracking unwanted actions | Manual review of conversion setup |
| No phone call hierarchy check | Call tracking may have duplicates | Verify in Google Ads settings |

### Future Report Improvements

- [ ] Conversion goal cleanup analysis (identify "Downloads" and other irrelevant goals)
- [ ] Phone call tracking hierarchy verification
- [ ] Deeper Merchant Center diagnostics (warnings, pending items)
- [ ] Budget forecasting model (projected spend vs. actual)
- [ ] Automated snapshot cadence (every 12-24 hours)
- [ ] Historical trend comparison (week-over-week, month-over-month)

### Explicitly Not Included Yet

The following are planned but not active:

- No recommendations for budget changes
- No automated bid adjustments
- No keyword additions or removals
- No campaign restructuring suggestions

**These are not active changes yet.** This report is read-only.

---

## APPENDIX — Data Sources & Methodology

### Data Origin

All data in this report comes from a point-in-time snapshot. No live API calls are made during report generation.

| Source | API Version | Data Extracted |
|--------|-------------|----------------|
| Google Ads | v19 | Campaigns, Ad Groups, Keywords, Negatives, Assets, Performance, Change History |
| Merchant Center | v2.1 | Products, Product Statuses, Account Issues |

### Snapshot Details

| Field | Value |
|-------|-------|
| Snapshot Location | `snapshots/2026-01-15T202326Z/` |
| Raw Files | 19 |
| Normalized Files | 14 |
| Extraction Duration | 24.93 seconds |

### What "Snapshot-Based" Means

This report does not query Google Ads or Merchant Center in real-time. Instead:

1. A script extracts data from the APIs at a specific moment
2. That data is saved locally in JSON files
3. This report reads only from those saved files

This means:
- The report is reproducible (same snapshot = same report)
- No risk of accidental changes to the live account
- Data reflects a specific point in time, not "right now"

### Validation Performed

| Check | Result |
|-------|--------|
| Keywords mapped to campaigns | ✓ All mapped |
| Products matched to statuses | ✓ All matched |
| Total validation errors | 0 |

---

## End of Report

**Report generated from snapshot:** `2026-01-15T202326Z`

**Next scheduled snapshot:** Next manual run or scheduled automation

---

*This report is for internal use by Buy Comfort Direct. It describes the current state of advertising accounts and does not constitute recommendations for changes. All data is extracted read-only; no modifications are made to live systems.*
