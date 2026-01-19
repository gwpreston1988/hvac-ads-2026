# Buy Comfort Direct
# Google Ads & Merchant Center Health Report

---

## SNAPSHOT PROVENANCE

> **This report is generated from snapshot data only. NO LIVE API CALLS.**

| Field | Value |
|-------|-------|
| Snapshot ID | `2026-01-19T194619Z` |
| Snapshot Version | `A3.0` |
| Extraction Started (UTC) | `2026-01-19T19:46:19.430482Z` |
| Extraction Finished (UTC) | `2026-01-19T19:46:42.699853Z` |
| Google Ads Customer ID | `9256598060` |
| Merchant Center ID | `5308355318` |
| Raw Records Extracted | 18484 |
| Normalized Records | 16334 |
| Validation Errors | 0 |
| Validation Warnings | 0 |

---

## Recent Out-of-Band Change (Recorded)

> **Note:** The following change was executed outside the baseline apply engine and is recorded here for provenance.

| Field | Value |
|-------|-------|
| Timestamp (UTC) | `2026-01-19T19:39:19Z` |
| Campaign | Products merchant campaign (ID: 20815709270) |
| Asset Group | 6483780791 |
| Action | Restructure listing group filters |
| Before | 22 filters (hvac parts supplies L1 subdivision with L2 subcategories) |
| After | 5 filters (INCLUDE: goodman 1, rheem, solace; EXCLUDE: everything else) |
| Reason | Goodman products were not showing in Shopping due to incorrect product type filters |
| Status | ✓ System reconciled to current state via fresh snapshot |

**API Notes (for future pipeline integration):**
- `listingSource: "SHOPPING"` required on CREATE operations
- CREATEs must precede REMOVEs in atomic mutate calls
- Delete leaves before subdivision parents
- Always maintain "everything else" child under root for tree validity

---

## Confidence & Freshness

**Snapshot Age:** 1 minutes

**Verdict:** 🟢 **GREEN**

- Snapshot fresh and validated

### Account Fingerprint

| Metric | Value |
|--------|-------|
| Total Campaigns | 8 |
| Enabled Campaigns | 3 |
| Performance Max | 4 |
| Search Campaigns | 3 |
| **Branded Campaign** | BCD Branded (ID: 20958985895) |
| Branded Bidding Strategy | MAXIMIZE_CONVERSIONS |
| Branded Enabled Keywords | 3 |
| Top Keywords | buy comfort direct, buycomfortdirect, buycomfortdirect.com |
| Branded Negative Keywords | 0 |
| Last Branded Change | 2026-01-16 19:51:21.482369 |


---

**Report Scope**

| Field | Value |
|-------|-------|
| Snapshot ID | `2026-01-19T194619Z` |
| Snapshot Timestamp (UTC) | `2026-01-19T19:46:42.699853Z` |
| Report Generated (UTC) | `2026-01-19T19:48:25Z` |
| Data Sources | Google Ads (Search + PMax), Merchant Center |

---

## SECTION 1 — Executive Summary (Read This First)

| Question | Answer |
|----------|--------|
| Are ads running? | ✓ Yes — 4 active campaigns, $5,292.66 spent last 7 days |
| Is brand traffic protected? | FAIL (see Section 4) |
| Are products showing in Google Shopping? | ✓ 1,101/1,101 equipment approved (100%) |

**Biggest current risk:**
No urgent issues detected. Continue monitoring per checkpoints below.

**What is stable today:**
- Ad campaigns are active and spending normally
- Merchant Center feed is 100% approved

### What This Means

Your advertising campaigns spent $5,292.66 over the last 7 days. Your equipment catalog has 1,101 items approved for Shopping ads.

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
| Products merchant campaign | $4,492.69 | 2,309 | 186,982 | 25.31 | $26,853.86 | 5.98 |
| BCD Branded | $423.23 | 68 | 831 | 4.00 | $1,743.40 | 4.12 |
| BCD - Hardware Offensive - 202 | $323.85 | 2,742 | 30,838 | 0.00 | $0.00 | 0.00 |
| Standard Shopping Campaign | $52.89 | 60 | 3,128 | 0.00 | $0.00 | 0.00 |

### Last 30 Days Summary

| Campaign | Spend | Clicks | Impressions | Conversions | Conv. Value | ROAS |
|----------|-------|--------|-------------|-------------|-------------|------|
| Products merchant campaign | $17,729.37 | 7,540 | 709,597 | 74.94 | $48,719.53 | 2.75 |
| BCD Branded | $1,406.14 | 242 | 1,804 | 17.66 | $12,364.38 | 8.79 |
| BCD - Hardware Offensive - 202 | $325.61 | 2,795 | 31,455 | 0.00 | $0.00 | 0.00 |
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

**Brand Protection Check: FAIL** — Smart bidding (MAXIMIZE_CONVERSIONS) — must be MANUAL_CPC.

**Issues (fix required):**
- ❌ Smart bidding (MAXIMIZE_CONVERSIONS) — must be MANUAL_CPC


### Branded Campaign CPC by Period

| Period | Avg CPC |
|--------|---------|
| Today (2026-01-19, partial) | N/A |
| Yesterday | $1.64 |
| Last 7 days | $6.22 |
| Last 30 days | $5.81 |

### Branded Campaign Keyword Analysis

| Metric | Value |
|--------|-------|
| Keywords analyzed | 3 enabled keywords |
| Brand keywords | 3/3 keywords |
| Non-brand keywords | 0 non-brand keywords (0.0%) |
| Total spend (snapshot period) | $1406.14 total |

### Enabled Keywords in Branded Campaign

| Keyword | Match Type | Classification |
|---------|------------|----------------|
| buy comfort direct | PHRASE | ✓ Brand |
| buycomfortdirect | PHRASE | ✓ Brand |
| buycomfortdirect.com | EXACT | ✓ Brand |

### Issues Requiring Attention

| Keyword | Match Type | Issue | Action Needed |
|---------|------------|-------|---------------|
| (no issues detected) | - | - | - |

**What this means:**
The Brand Protection Check validates that the Branded campaign is constrained to brand terms only (exact/phrase match) with Manual CPC bidding. This prevents budget waste on generic searches that should go through other campaigns. A PASS result means the campaign structure is correct. A FAIL result identifies specific issues to address.

---

## SECTION 5 — Merchant Center & Shopping Eligibility

### Overall Product Eligibility

| Status | Count | Percentage |
|--------|-------|------------|
| Approved | 1,101 | 100.0% |
| Disapproved | 0 | 0.0% |
| Pending | 0 | 0.0% |
| **Total** | 1,101 | 100% |

### Eligibility by Brand

| Brand | Total Products | Approved | Disapproved | Approval Rate |
|-------|----------------|----------|-------------|---------------|
| Rheem | 197 | 197 | 0 | 100.0% |
| Goodman | 530 | 530 | 0 | 100.0% |
| Solace | 349 | 349 | 0 | 100.0% |
| Daikin | 25 | 25 | 0 | 100.0% |

### Disapproved Products (If Any)

| Offer ID | Title | Brand | Disapproval Reason | Fix Owner |
|----------|-------|-------|-------------------|-----------|
| (none) | - | - | - | - |

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
| BCD Branded | MAXIMIZE_CONVERSIONS | tCPA $70.83 | $200.00 | Automated |
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
|  | AD_GROUP_CRITERION | UNKNOWN |  |
|  | AD_GROUP_CRITERION | UNKNOWN |  |
|  | AD_GROUP_CRITERION | UNKNOWN |  |
|  | CAMPAIGN | UNKNOWN |  |
|  | CAMPAIGN_CRITERION | UNKNOWN |  |
|  | AD_GROUP_CRITERION | UNKNOWN |  |
|  | AD | UNKNOWN |  |
|  | AD | UNKNOWN |  |
|  | CAMPAIGN_BUDGET | UNKNOWN |  |
|  | CAMPAIGN | UNKNOWN |  |
|  | CUSTOMER_ASSET | UNKNOWN |  |
|  | CUSTOMER_ASSET | UNKNOWN |  |
|  | CUSTOMER_ASSET | UNKNOWN |  |
|  | CUSTOMER_ASSET | UNKNOWN |  |
|  | CUSTOMER_ASSET | UNKNOWN |  |

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
- Campaigns are spending normally ($5,292.66 last 7 days)
- Merchant Center feed is 100% approved
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
| Snapshot Location | `snapshots/2026-01-19T194619Z/` |
| Raw Files | 21 |
| Normalized Files | 15 |
| Extraction Duration | 23.27 seconds |

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

**Report generated from snapshot:** `2026-01-19T194619Z`

**Next scheduled snapshot:** Next manual run or scheduled automation

---

*This report is for internal use by Buy Comfort Direct. It describes the current state of advertising accounts and does not constitute recommendations for changes. All data is extracted read-only; no modifications are made to live systems.*
