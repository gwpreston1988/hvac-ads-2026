# Merchant Center API Integration Plan
## Hybrid Approach: Scripts First, MCP Server Later

**Project**: Buy Comfort Direct - PMax Optimization
**Date**: 2026-01-09
**Goal**: Connect Merchant Center API to identify product-level brand leakage and optimize PMax performance

---

## Context

### Current State
- **Revenue**: $175K/month
- **Ad Spend**: ~$21,000/month (12% overhead)
- **PMax ROAS**: 3.74x
- **Identified Issue**: 447 brand terms leaking into PMax (~$2,066/month waste)
- **Gap**: No visibility into which *products* are causing brand term triggers

### Why Merchant Center API?
PMax is fed by the Merchant Center product feed. Connecting to the Merchant Center API allows us to:
1. See which products trigger for which search terms
2. Identify products with brand names in titles causing leakage
3. Optimize product data to improve targeting
4. Calculate product-level ROAS

### Why Hybrid Approach?
Using an LLM (Claude) to execute API calls creates a choice:
- **Standard API (Scripts)**: Write Python → Execute → Read output files
- **MCP Server**: Direct tool calls from LLM → Structured response

We choose **scripts first** because:
1. Don't yet know which queries are most valuable
2. Scripts allow rapid iteration
3. MCP requires upfront investment - should validate need first
4. Once patterns emerge, convert high-value queries to MCP tools

---

## Phase 1: Merchant Center API Discovery (Scripts)

### Objective
Validate which Merchant Center data is actionable for PMax optimization

### Step 1.1 - API Authentication Setup
- [ ] Add `MERCHANT_CENTER_ID` to `.env`
- [ ] Verify OAuth credentials work with Content API for Shopping
- [ ] Test basic product listing pull
- [ ] Confirm same OAuth client works for both Ads API and Merchant API

### Step 1.2 - Product Feed Audit Script
**File**: `audit/merchant_feed_audit.py`

**Queries to implement**:
```
- List all products with status (approved/disapproved/pending)
- Extract product titles, brands, GTINs, custom labels
- Identify products with brand names in titles (Rheem, Goodman, Solace)
- Flag products missing key attributes (GTIN, MPN, condition)
- Count products by category/product type
```

**Output**: `output/merchant_feed_audit_YYYYMMDD.csv`

### Step 1.3 - Cross-Reference with PMax Data
**File**: `audit/product_pmax_correlation.py`

**Logic**:
```
- Match Merchant Center product IDs → PMax shopping_product_performance
- Identify which products trigger brand search terms
- Calculate product-level ROAS from PMax
- Flag products driving brand leakage
- Identify products with high impressions but low conversions
```

**Output**:
- `output/product_performance_YYYYMMDD.csv`
- `output/brand_leakage_by_product_YYYYMMDD.csv`

### Deliverables Phase 1
| Deliverable | Purpose |
|-------------|---------|
| Product inventory CSV with brand flags | See which products have brand terms |
| Product performance CSV with PMax metrics | Product-level ROAS |
| Brand leakage by product report | Pinpoint leakage sources |

---

## Phase 2: Pattern Identification

### Objective
Identify repeated, high-value queries worth automating via MCP

### Analysis Questions
1. Which queries do you run daily/weekly?
2. Which require real-time answers vs batch reports?
3. What decisions do these queries inform?
4. Are there conversational queries that scripts can't handle well?

### Expected High-Value Patterns
| Query Type | Frequency | Real-time? | MCP Candidate? |
|------------|-----------|------------|----------------|
| "Which products are disapproved?" | Daily | Yes | Yes |
| "Show brand leakage by product" | Weekly | Yes | Yes |
| "Product ROAS ranking" | Weekly | Yes | Yes |
| "What's triggering for 'rheem furnace'?" | Ad-hoc | Yes | Yes |
| "Full feed audit" | Monthly | No | No (batch) |
| "Export all products to CSV" | Monthly | No | No (batch) |

### Decision Criteria for MCP
**Build MCP if**:
- 3+ queries are asked repeatedly in conversation
- Queries need real-time, not batch, responses
- Script round-trip (write → execute → read) creates friction

**Stay with scripts if**:
- Queries are infrequent or one-time
- Output needs to be saved/shared as files
- Logic is complex and evolving rapidly

---

## Phase 3: MCP Server Build (If Validated)

### Objective
Convert validated high-value queries into MCP tools for direct LLM access

### Step 3.1 - MCP Server Scaffold
```
Directory Structure:
mcp-google-ads/
├── src/
│   ├── index.ts           # MCP server entry point
│   ├── auth.ts            # OAuth token management
│   ├── tools/
│   │   ├── merchant.ts    # Merchant Center tools
│   │   ├── ads.ts         # Google Ads tools
│   │   └── correlation.ts # Cross-API tools
│   └── types.ts           # TypeScript interfaces
├── package.json
├── tsconfig.json
└── README.md
```

### Step 3.2 - Tool Definitions

**Example: Brand Leakage Products Tool**
```typescript
{
  name: "get_brand_leakage_products",
  description: "Returns products causing brand term triggers in PMax",
  parameters: {
    brand: {
      type: "string",
      enum: ["rheem", "goodman", "solace", "daikin", "amana", "ruud", "all"],
      description: "Filter by brand or 'all' for all brands"
    },
    min_spend: {
      type: "number",
      description: "Minimum spend threshold in dollars"
    },
    limit: {
      type: "number",
      description: "Maximum products to return",
      default: 20
    }
  }
}
```

**Example: Product Status Tool**
```typescript
{
  name: "get_product_status",
  description: "Get approval status of products in Merchant Center",
  parameters: {
    status_filter: {
      type: "string",
      enum: ["approved", "disapproved", "pending", "all"]
    },
    brand_filter: {
      type: "string",
      description: "Optional brand to filter by"
    }
  }
}
```

**Example: Search Term to Product Tool**
```typescript
{
  name: "find_products_for_search_term",
  description: "Find which products trigger for a given search term",
  parameters: {
    search_term: {
      type: "string",
      description: "The search term to investigate"
    }
  }
}
```

### Step 3.3 - Claude Code Integration

**File**: `.mcp.json` (in project root)
```json
{
  "mcpServers": {
    "google-ads": {
      "command": "node",
      "args": ["./mcp-google-ads/dist/index.js"],
      "env": {
        "GOOGLE_ADS_CUSTOMER_ID": "${GOOGLE_ADS_CUSTOMER_ID}",
        "GOOGLE_ADS_DEVELOPER_TOKEN": "${GOOGLE_ADS_DEVELOPER_TOKEN}",
        "MERCHANT_CENTER_ID": "${MERCHANT_CENTER_ID}",
        "GOOGLE_ADS_CLIENT_ID": "${GOOGLE_ADS_CLIENT_ID}",
        "GOOGLE_ADS_CLIENT_SECRET": "${GOOGLE_ADS_CLIENT_SECRET}",
        "GOOGLE_ADS_REFRESH_TOKEN": "${GOOGLE_ADS_REFRESH_TOKEN}"
      }
    }
  }
}
```

### Step 3.4 - OAuth Token Management
```typescript
// auth.ts - Token refresh logic
class GoogleAuthManager {
  private accessToken: string | null = null;
  private tokenExpiry: Date | null = null;

  async getAccessToken(): Promise<string> {
    if (this.accessToken && this.tokenExpiry && this.tokenExpiry > new Date()) {
      return this.accessToken;
    }
    return this.refreshToken();
  }

  private async refreshToken(): Promise<string> {
    // Use refresh_token to get new access_token
    // Cache for ~55 minutes (tokens expire in 60)
  }
}
```

---

## Timeline & Decision Gates

| Phase | Duration | Gate Criteria |
|-------|----------|---------------|
| **Phase 1** | 1-2 sessions | Scripts produce actionable insights |
| **Phase 2** | 1 session | 3+ queries identified as MCP candidates |
| **Phase 3** | 2-3 sessions | MCP server deployed, tools tested |

### Go/No-Go Decision Points

**After Phase 1**:
- ✅ Proceed if: Scripts reveal product-level insights that inform decisions
- ❌ Stop if: Merchant Center data doesn't correlate with PMax performance

**After Phase 2**:
- ✅ Proceed to MCP if: Clear patterns of repeated conversational queries
- ❌ Stay with scripts if: Queries are varied/complex, batch outputs preferred

---

## Technical Requirements

### Phase 1 (Scripts)
| Requirement | Status |
|-------------|--------|
| Python 3.x | ✅ Installed (3.12.1) |
| `requests` library | ✅ Installed |
| `python-dotenv` | ✅ Installed |
| Google Ads API access | ✅ Working |
| Merchant Center API access | ⏳ Needs verification |
| OAuth credentials | ✅ In .env |

### Phase 3 (MCP)
| Requirement | Status |
|-------------|--------|
| Node.js 18+ | ⏳ Check |
| TypeScript | ⏳ Install |
| `@modelcontextprotocol/sdk` | ⏳ Install |
| OAuth2 client library | ⏳ Install |

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Merchant API requires separate OAuth consent | Medium | High | Test auth in Phase 1.1 before building |
| MCP adds complexity without value | Medium | Medium | Phase 2 validates before building |
| Token refresh in MCP is complex | Medium | Medium | Use refresh token flow, cache access tokens |
| Over-engineering | High | Medium | Scripts remain primary, MCP supplements |
| API rate limits | Low | Low | Implement exponential backoff |

---

## API Reference

### Merchant Center Content API
- **Base URL**: `https://shoppingcontent.googleapis.com/content/v2.1`
- **Auth**: OAuth 2.0 (same client as Ads API)
- **Key Endpoints**:
  - `GET /products` - List all products
  - `GET /products/{productId}` - Get single product
  - `GET /productstatuses` - Get product approval statuses
  - `GET /reports/search` - Query performance data

### Google Ads API (for correlation)
- **Resource**: `shopping_product_performance_view`
- **Fields**: product_item_id, impressions, clicks, cost_micros, conversions_value
- **Join Key**: `product_item_id` matches Merchant Center `offerId`

---

## Questions for Review

1. Does the phased approach make sense given the goal of PMax optimization?
2. Are there Merchant Center API endpoints missing that would help identify brand leakage?
3. Should the MCP server combine Google Ads + Merchant Center, or keep separate?
4. Any experience with OAuth token management in long-running MCP servers?
5. Is there value in also connecting Google Search Console for organic cannibalization data?
6. Should we consider BigQuery export for historical analysis instead of real-time API calls?

---

## Appendix: Current Audit Findings

### Brand Leakage Summary (from 2026-01-09 audit)
| Metric | Value |
|--------|-------|
| Total PMax Spend (30d) | $21,656 |
| Brand Terms in PMax | 447 |
| Estimated Brand Tax | $2,066/month |

### Brand Distribution
| Brand | Occurrences |
|-------|-------------|
| Rheem | 197 |
| Goodman | 142 |
| Daikin | 52 |
| Ruud | 34 |
| Amana | 17 |

### Files Generated
- `output/pmax_negative_brand_terms_20260109_133429.csv` (447 terms)
- `output/exact_match_hardening_20260109_133429.csv` (9 terms)
- `output/master_audit_summary_20260109_133429.csv`
