# Buy Comfort Direct
# Google Ads & Merchant Center Health Report

---

## SNAPSHOT PROVENANCE

> **This report is generated from snapshot data only. NO LIVE API CALLS.**

| Field | Value |
|-------|-------|
| Snapshot ID | `{{PROV_SNAPSHOT_ID}}` |
| Snapshot Version | `{{PROV_SNAPSHOT_VERSION}}` |
| Extraction Started (UTC) | `{{PROV_EXTRACTION_STARTED}}` |
| Extraction Finished (UTC) | `{{PROV_EXTRACTION_FINISHED}}` |
| Google Ads Customer ID | `{{PROV_GOOGLE_ADS_CUSTOMER_ID}}` |
| Merchant Center ID | `{{PROV_MERCHANT_ID}}` |
| Raw Records Extracted | {{PROV_RAW_RECORDS}} |
| Normalized Records | {{PROV_NORMALIZED_RECORDS}} |
| Validation Errors | {{PROV_VALIDATION_ERRORS}} |
| Validation Warnings | {{PROV_VALIDATION_WARNINGS}} |

---

{{OUT_OF_BAND_CHANGES_SECTION}}

## Confidence & Freshness

**Snapshot Age:** {{CONF_SNAPSHOT_AGE}}

**Verdict:** {{CONF_VERDICT_EMOJI}} **{{CONF_VERDICT}}**

{{CONF_REASONS}}

### Account Fingerprint

| Metric | Value |
|--------|-------|
| Total Campaigns | {{FP_TOTAL_CAMPAIGNS}} |
| Enabled Campaigns | {{FP_ENABLED_CAMPAIGNS}} |
| Performance Max | {{FP_PMAX_CAMPAIGNS}} |
| Search Campaigns | {{FP_SEARCH_CAMPAIGNS}} |
| **Branded Campaign** | {{FP_BRANDED_NAME}} (ID: {{FP_BRANDED_ID}}) |
| Branded Bidding Strategy | {{FP_BRANDED_BIDDING}} |
| Branded Enabled Keywords | {{FP_BRANDED_KEYWORD_COUNT}} |
| Top Keywords | {{FP_BRANDED_KEYWORDS}} |
| Branded Negative Keywords | {{FP_BRANDED_NEGATIVE_COUNT}} |
| Last Branded Change | {{FP_BRANDED_LAST_CHANGE}} |
{{FP_BRANDED_WARNING}}

---

**Report Scope**

| Field | Value |
|-------|-------|
| Snapshot ID | `{{SNAPSHOT_ID}}` |
| Snapshot Timestamp (UTC) | `{{SNAPSHOT_TIMESTAMP}}` |
| Report Generated (UTC) | `{{REPORT_GENERATED}}` |
| Data Sources | Google Ads (Search + PMax), Merchant Center |

---

## SECTION 1 — Executive Summary (Read This First)

| Question | Answer |
|----------|--------|
| Are ads running? | {{ADS_RUNNING_STATUS}} |
| Is brand traffic protected? | {{BRAND_PROTECTION_STATUS}} (see Section 4) |
| Are products showing in Google Shopping? | {{SHOPPING_ELIGIBILITY_STATUS}} |

**Biggest current risk:**
{{BIGGEST_RISK_SENTENCE}}

**What is stable today:**
- {{STABLE_ITEM_1}}
- {{STABLE_ITEM_2}}

### What This Means

{{EXECUTIVE_SUMMARY_EXPLANATION}}

This summary answers the most common questions a business owner might have. "Are ads running" tells you if campaigns are active and serving. "Brand traffic protected" tells you if the Branded campaign is properly constrained to avoid budget waste. "Products showing" tells you if your inventory is visible in Google Shopping results.

---

## SECTION 2 — Campaign Overview (What Each Campaign Does)

### 2.1 BCD Branded (Search)

| Field | Value |
|-------|-------|
| Campaign ID | {{BRANDED_CAMPAIGN_ID}} |
| Status | {{BRANDED_CAMPAIGN_STATUS}} |
| Purpose | Capture searches for "Buy Comfort Direct" and our store name |

**What it shows for:**
- Searches containing our business name
- Variations like "buycomfortdirect", "buy comfort", "bcd hvac"

**What it should NOT show for:**
- Manufacturer names (Rheem, Goodman, Solace)
- Generic HVAC terms (air conditioner, furnace)
- Competitor names

**Current guardrails:**
- {{BRANDED_GUARDRAILS}}

---

### 2.2 Products Merchant Campaign (Performance Max)

| Field | Value |
|-------|-------|
| Campaign ID | {{PMAX_CAMPAIGN_ID}} |
| Status | {{PMAX_CAMPAIGN_STATUS}} |
| Merchant ID Linked | {{PMAX_MERCHANT_ID}} |
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
- {{PMAX_BIDDING_STRATEGY}}
- Target ROAS: {{PMAX_TARGET_ROAS}}

---

### 2.3 Hardware Offensive (Search)

| Field | Value |
|-------|-------|
| Campaign ID | {{OFFENSIVE_CAMPAIGN_ID}} |
| Status | {{OFFENSIVE_CAMPAIGN_STATUS}} |
| Purpose | Capture non-branded HVAC searches (model numbers, generic terms) |

**Expected behavior in early days:**
- Learning phase takes 2-4 weeks
- Low conversion volume initially is normal
- CPCs may fluctuate as Google learns

**Current state:**
- {{OFFENSIVE_CURRENT_STATE}}

---

### 2.4 Other Campaigns

These campaigns exist in the account but are not actively running:

| Campaign | Status | Notes |
|----------|--------|-------|
{{OTHER_CAMPAIGNS_TABLE}}

These are listed for completeness. Paused campaigns do not spend money.

---

## SECTION 3 — Spend & Performance Snapshot

### Last 7 Days Summary

| Campaign | Spend | Clicks | Impressions | Conversions | Conv. Value | ROAS |
|----------|-------|--------|-------------|-------------|-------------|------|
{{LAST_7_DAYS_TABLE}}

### Last 30 Days Summary

| Campaign | Spend | Clicks | Impressions | Conversions | Conv. Value | ROAS |
|----------|-------|--------|-------------|-------------|-------------|------|
{{LAST_30_DAYS_TABLE}}

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

{{BRAND_PROTECTION_VERDICT}}

### Branded Campaign CPC by Period

| Period | Avg CPC |
|--------|---------|
{{BRANDED_CPC_TABLE}}

### Branded Campaign Keyword Analysis

| Metric | Value |
|--------|-------|
| Keywords analyzed | {{BRANDED_TOTAL_TERMS}} |
| Brand keywords | {{BRANDED_BRAND_PERCENT}} |
| Non-brand keywords | {{BRANDED_NONBRAND_SPEND}} ({{BRANDED_NONBRAND_PERCENT}}) |
| Total spend (snapshot period) | {{BRANDED_BRAND_SPEND}} |

### Enabled Keywords in Branded Campaign

| Keyword | Match Type | Classification |
|---------|------------|----------------|
{{TOP_BRAND_QUERIES_TABLE}}

### Issues Requiring Attention

| Keyword | Match Type | Issue | Action Needed |
|---------|------------|-------|---------------|
{{NONBRAND_IN_BRANDED_TABLE}}

**What this means:**
The Brand Protection Check validates that the Branded campaign is constrained to brand terms only (exact/phrase match) with Manual CPC bidding. This prevents budget waste on generic searches that should go through other campaigns. A PASS result means the campaign structure is correct. A FAIL result identifies specific issues to address.

---

## SECTION 5 — Merchant Center & Shopping Eligibility

### Overall Product Eligibility

| Status | Count | Percentage |
|--------|-------|------------|
| Approved | {{MC_APPROVED_COUNT}} | {{MC_APPROVED_PERCENT}} |
| Disapproved | {{MC_DISAPPROVED_COUNT}} | {{MC_DISAPPROVED_PERCENT}} |
| Pending | {{MC_PENDING_COUNT}} | {{MC_PENDING_PERCENT}} |
| **Total** | {{MC_TOTAL_COUNT}} | 100% |

### Eligibility by Brand

| Brand | Total Products | Approved | Disapproved | Approval Rate |
|-------|----------------|----------|-------------|---------------|
{{MC_BY_BRAND_TABLE}}

### Disapproved Products (If Any)

| Offer ID | Title | Brand | Disapproval Reason | Fix Owner |
|----------|-------|-------|-------------------|-----------|
{{MC_DISAPPROVED_TABLE}}

**Fix Owner Legend:**
- **Feed**: Issue with product data we send to Google (fix in BigCommerce or feed settings)
- **Site**: Issue with the landing page (fix on website)
- **Policy**: Google policy violation (may require product changes or appeal)

### What Eligibility Means

A product must be "Approved" to appear in Google Shopping results. Disapproved products cannot show ads. The approval rate tells you what percentage of your catalog is actually eligible to advertise.

### What Disapproval Means

Disapproval is not a penalty. It means Google found an issue with the product data or landing page. Most disapprovals can be fixed by correcting the product feed or website. Products remain disapproved until the issue is resolved and Google re-crawls the data.

---

## SECTION 5B — Organic Visibility (Search Console)

{{GSC_SECTION}}

---

## SECTION 5C — Google Recommendations Truth Signals

{{TRUTH_SIGNALS_SECTION}}

---

## SECTION 6 — Bidding & Cost Control Status

| Campaign | Bid Strategy | Target | Daily Budget | Notes |
|----------|--------------|--------|--------------|-------|
{{BIDDING_TABLE}}

### Understanding Bid Strategies

- **Maximize Conversion Value (tROAS)**: Google automatically sets bids to maximize revenue while targeting a specific return on ad spend. A target of 4.0 means Google aims for $4 in conversion value per $1 spent.

- **Maximize Conversions (tCPA)**: Google automatically sets bids to get the most conversions at or below a target cost per conversion.

- **Manual CPC**: You set the maximum cost per click. Google will not exceed this amount.

### Why Costs Differ Across Campaigns

- **Branded searches** typically have lower CPCs because there is less competition for your own business name.
- **Shopping/PMax** CPCs vary based on product category and competition.
- **Non-branded search** CPCs are often higher because many advertisers compete for generic terms.

---

{{BUDGET_INTELLIGENCE_SECTION}}

## SECTION 7 — Recent Changes & Risk Check

### Recent Changes (Last {{CHANGE_HISTORY_DAYS}} Days)

| Date | Resource Type | Change Type | Description |
|------|---------------|-------------|-------------|
{{RECENT_CHANGES_TABLE}}

### Change Summary

| Change Type | Count |
|-------------|-------|
{{CHANGE_SUMMARY_TABLE}}

### Automation Status

| Setting | Status | Risk Level |
|---------|--------|------------|
| Auto-apply recommendations | {{AUTO_APPLY_STATUS}} | {{AUTO_APPLY_RISK}} |
| Automated bidding active | {{AUTO_BIDDING_STATUS}} | {{AUTO_BIDDING_RISK}} |
| Performance Max enabled | {{PMAX_ENABLED_STATUS}} | {{PMAX_RISK}} |

**What this means:**
- "Auto-apply recommendations" can make changes without your approval. This should typically be OFF unless intentionally enabled.
- "Automated bidding" means Google adjusts bids automatically. This is expected and normal for modern campaigns.
- "Performance Max" gives Google more control over placements. This is by design but requires monitoring.

---

## SECTION 8 — What Is Working As Intended

These items are functioning normally:

{{WORKING_AS_INTENDED_LIST}}

---

## SECTION 9 — What Is Still Early / Learning

These items need more time before we can evaluate them:

{{STILL_LEARNING_LIST}}

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
| Google Ads | {{GOOGLE_ADS_API_VERSION}} | Campaigns, Ad Groups, Keywords, Negatives, Assets, Performance, Change History |
| Merchant Center | {{MERCHANT_CENTER_API_VERSION}} | Products, Product Statuses, Account Issues |

### Snapshot Details

| Field | Value |
|-------|-------|
| Snapshot Location | `snapshots/{{SNAPSHOT_ID}}/` |
| Raw Files | {{RAW_FILE_COUNT}} |
| Normalized Files | {{NORMALIZED_FILE_COUNT}} |
| Extraction Duration | {{EXTRACTION_DURATION}} seconds |

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
| Keywords mapped to campaigns | {{KEYWORDS_MAPPED_STATUS}} |
| Products matched to statuses | {{PRODUCTS_MATCHED_STATUS}} |
| Total validation errors | {{TOTAL_VALIDATION_ERRORS}} |

---

## End of Report

**Report generated from snapshot:** `{{SNAPSHOT_ID}}`

**Next scheduled snapshot:** {{NEXT_SNAPSHOT_TIME}}

---

*This report is for internal use by Buy Comfort Direct. It describes the current state of advertising accounts and does not constitute recommendations for changes. All data is extracted read-only; no modifications are made to live systems.*
