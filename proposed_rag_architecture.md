# Proposed RAG Architecture - HVAC Ads Intelligence Platform

## Vision
Convert the current Google Ads audit scripts into an intelligent RAG pipeline with:
- Hybrid retrieval (semantic + deterministic)
- Dashboard + LLM chat interface
- **Multi-platform plugin architecture** for extensible data source integration

---

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                        │
│                                                                              │
│  ┌─────────────────────────────┐  ┌───────────────────────────────────────┐ │
│  │       DASHBOARD             │  │         LLM PROMPT AREA               │ │
│  │                             │  │                                       │ │
│  │  ┌─────────┐ ┌─────────┐   │  │  "Why did PMax spend increase on     │ │
│  │  │  ROAS   │ │ Budget  │   │  │   brand terms last week?"            │ │
│  │  │ Trends  │ │  Util   │   │  │                                       │ │
│  │  └─────────┘ └─────────┘   │  │  ┌─────────────────────────────────┐ │ │
│  │                             │  │  │                                 │ │ │
│  │  ┌─────────┐ ┌─────────┐   │  │  │  [Ask anything about your biz] │ │ │
│  │  │  Brand  │ │ Product │   │  │  │                                 │ │ │
│  │  │ Leakage │ │  Perf   │   │  │  └─────────────────────────────────┘ │ │
│  │  └─────────┘ └─────────┘   │  │                                       │ │
│  │                             │  │  Example queries:                    │ │
│  │  ┌─────────┐ ┌─────────┐   │  │  • Which products are wasting budget?│ │
│  │  │ Exclus- │ │ Campaign│   │  │  • Compare ad spend vs NetSuite rev  │ │
│  │  │  ions   │ │  Health │   │  │  • SEMrush keyword gaps vs our ads   │ │
│  │  └─────────┘ └─────────┘   │  │  • BigCommerce inventory vs ad promo │ │
│  └─────────────────────────────┘  └───────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API / BACKEND                                      │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         RAG ORCHESTRATOR                              │   │
│  │                                                                       │   │
│  │  1. Parse user query                                                  │   │
│  │  2. Route to appropriate plugin(s)                                    │   │
│  │  3. Determine retrieval strategy (semantic vs deterministic vs both) │   │
│  │  4. Fetch & merge context from multiple sources                       │   │
│  │  5. Generate LLM response with citations                              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│              ┌───────────────────────┼───────────────────────┐              │
│              ▼                       ▼                       ▼              │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐   │
│  │   DETERMINISTIC     │ │      SEMANTIC       │ │   PLUGIN ROUTER     │   │
│  │    RETRIEVAL        │ │     RETRIEVAL       │ │                     │   │
│  │                     │ │                     │ │  Routes queries to  │   │
│  │ • SQL queries       │ │ • Vector similarity │ │  appropriate data   │   │
│  │ • Exact matches     │ │ • Embedding search  │ │  source plugins     │   │
│  │ • Aggregations      │ │ • Fuzzy matching    │ │                     │   │
│  │ • Time series       │ │ • Semantic clusters │ │                     │   │
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PLUGIN LAYER (Connectors)                             │
│                                                                              │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐   │
│  │  GOOGLE ADS   │ │   MERCHANT    │ │  BIGCOMMERCE  │ │   NETSUITE    │   │
│  │    PLUGIN     │ │    CENTER     │ │    PLUGIN     │ │    PLUGIN     │   │
│  │               │ │    PLUGIN     │ │               │ │               │   │
│  │ • Campaigns   │ │               │ │ • Products    │ │ • Orders      │   │
│  │ • Keywords    │ │ • Products    │ │ • Inventory   │ │ • Revenue     │   │
│  │ • Search terms│ │ • Exclusions  │ │ • Orders      │ │ • Customers   │   │
│  │ • Performance │ │ • Feed status │ │ • Categories  │ │ • Invoices    │   │
│  │ • Budgets     │ │ • Diagnostics │ │ • Pricing     │ │ • GL Data     │   │
│  └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘   │
│                                                                              │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐   │
│  │    SEMRUSH    │ │    FUTURE     │ │    FUTURE     │ │    FUTURE     │   │
│  │    PLUGIN     │ │    PLUGIN     │ │    PLUGIN     │ │    PLUGIN     │   │
│  │               │ │               │ │               │ │               │   │
│  │ • Keywords    │ │ • Meta Ads?   │ │ • Shopify?    │ │ • Custom?     │   │
│  │ • Competitors │ │ • Bing Ads?   │ │ • Amazon?     │ │               │   │
│  │ • Rankings    │ │ • TikTok?     │ │ • Klaviyo?    │ │               │   │
│  │ • Backlinks   │ │               │ │               │ │               │   │
│  │ • Domain data │ │               │ │               │ │               │   │
│  └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                         │
│                                                                              │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐   │
│  │   STRUCTURED DB     │ │    VECTOR STORE     │ │   CACHE LAYER       │   │
│  │   (PostgreSQL)      │ │    (Chroma/Pine)    │ │   (Redis)           │   │
│  │                     │ │                     │ │                     │   │
│  │ • Campaign metrics  │ │ • Search terms      │ │ • API responses     │   │
│  │ • Product data      │ │ • Product titles    │ │ • Rate limiting     │   │
│  │ • Historical ROAS   │ │ • Query embeddings  │ │ • Session state     │   │
│  │ • Budget history    │ │ • Ad copy           │ │ • Real-time data    │   │
│  │ • Exclusion lists   │ │ • SEO content       │ │                     │   │
│  │ • Cross-platform IDs│ │ • Competitor data   │ │                     │   │
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Plugin Architecture

### Base Plugin Interface
```python
class BasePlugin:
    """All platform connectors implement this interface"""

    name: str                    # e.g., "google_ads", "netsuite"
    description: str             # Human-readable description
    capabilities: list[str]      # e.g., ["read", "write", "sync"]

    def authenticate(self) -> bool
    def test_connection(self) -> bool
    def get_schema(self) -> dict          # Available data/endpoints
    def query(self, query: str) -> dict   # Natural language query
    def fetch(self, endpoint: str, params: dict) -> dict
    def sync_to_db(self) -> bool          # Sync data to local DB
```

### Platform Plugins

| Plugin | Data Available | Use Cases |
|--------|---------------|-----------|
| **Google Ads** | Campaigns, keywords, search terms, performance, budgets | Ad optimization, budget allocation, keyword analysis |
| **Merchant Center** | Products, feed status, exclusions, diagnostics | Product visibility, feed health, Shopping ads |
| **BigCommerce** | Products, inventory, orders, customers, pricing | Inventory sync, pricing strategy, product performance |
| **NetSuite** | Orders, revenue, customers, invoices, GL | Revenue attribution, ROAS validation, financial reporting |
| **SEMrush** | Keywords, competitors, rankings, backlinks, domain data | Competitive analysis, keyword gaps, SEO/SEM alignment |

### Cross-Platform Query Examples

| Query | Plugins Used | Data Joined |
|-------|--------------|-------------|
| "Which products have high ad spend but low NetSuite revenue?" | Google Ads + NetSuite | Ad cost vs actual revenue |
| "Show me SEMrush keyword opportunities not in our campaigns" | SEMrush + Google Ads | Keyword gap analysis |
| "Products out of stock in BigCommerce still running ads" | BigCommerce + Google Ads | Inventory vs ad status |
| "Compare our branded search share vs competitors" | SEMrush + Google Ads | Competitive positioning |
| "Top margin products not getting ad impressions" | NetSuite + Merchant Center | Profit vs visibility |

---

## Current Repository State

### Directory Structure
```
hvac-ads-2026/
├── audit/                          # Main scripts
│   ├── pmax_brand_leakage.py       ✅ Core - PMax brand term detection
│   ├── keyword_conflicts.py        ✅ Core - Exact match migration candidates
│   ├── budget_balancer.py          ✅ Core - ROAS-based budget rebalancing
│   ├── generate_exclusion_feed.py  ✅ New - Merchant Center exclusions → GCS
│   ├── master_scaling_audit.py     ✅ Analysis - 6-task deep audit
│   ├── product_pmax_correlation.py ✅ Analysis - MC + PMax correlation
│   ├── execute_branded_restore.py  ⚠️ One-time fix - Archive candidate
│   ├── execute_containment.py      ⚠️ One-time fix - Archive candidate
│   ├── execute_phase1.py           ⚠️ One-time fix - Archive candidate
│   └── execute_live.py             ⚠️ One-time fix - Archive candidate
│
├── configs/
│   └── brand_terms.json            # Brand term configuration
│
├── scripts/
│   ├── generate_oauth_token.py     # OAuth utility
│   ├── exchange_code.py            # OAuth utility
│   └── seo_state_dump_rheem.py     # Misplaced SEO script
│
├── seo/                            # Separate SEO concern
│   ├── README.md
│   ├── audit/
│   └── configs/
│
├── docs/
│   └── merchant_center_integration_plan.md
│
├── output/
│   └── merchant_supplemental/
│       ├── exclusions_latest.tsv   # Current exclusion feed
│       ├── manifest.json           # Feed metadata
│       └── history/                # Historical feeds
│
├── reports/                        # Generated reports
│   ├── INDEX.md
│   ├── account_level/
│   ├── branded/
│   ├── hardware_offensive/
│   ├── merchant_feed/
│   ├── pmax_products_merchant/
│   └── seo/
│
├── CLAUDE.md                       # Project instructions (outdated)
├── .env                            # Credentials
└── proposed_rag_architecture.md    # This file
```

### Active Scripts Summary

| Script | Purpose | Data Sources |
|--------|---------|--------------|
| `pmax_brand_leakage.py` | Detect brand terms in PMax search queries | Google Ads API |
| `keyword_conflicts.py` | Find Broad→Exact migration candidates | Google Ads API |
| `budget_balancer.py` | Recommend budget shifts based on ROAS | Google Ads API |
| `generate_exclusion_feed.py` | Generate MC exclusion feed, upload to GCS | Merchant Center API |
| `master_scaling_audit.py` | Deep audit: leakage, intent, budget waste | Google Ads + MC APIs |
| `product_pmax_correlation.py` | Correlate products with PMax performance | Google Ads + MC APIs |

### Current Data Flow
```
Google Ads API ──┐
                 ├──▶ Python Scripts ──▶ CSV Reports ──▶ Manual Review
Merchant Center ─┘

                 ┌──▶ GCS Bucket ──▶ MC Supplemental Feed
                 │
generate_exclusion_feed.py
```

---

## Design Decisions Needed

### 1. Frontend Framework
| Option | Pros | Cons |
|--------|------|------|
| **Streamlit** | Fast to build, Python-native, good for data | Less polished, limited customization |
| **Next.js/React** | Professional UI, flexible, production-ready | More work, separate codebase |
| **Gradio** | Simple, good for LLM interfaces | Limited dashboard capabilities |

### 2. LLM Provider
| Option | Pros | Cons |
|--------|------|------|
| **Claude API** | Best reasoning, already using Anthropic | Cost |
| **OpenAI** | Good, well-documented | Different vendor |
| **Local (Ollama)** | Free, private | Lower quality, requires GPU |

### 3. Vector Store
| Option | Pros | Cons |
|--------|------|------|
| **Chroma** | Simple, local, free | Not production-scale |
| **Pinecone** | Hosted, scalable | Cost, external dependency |
| **pgvector** | Integrated with PostgreSQL | More setup |

### 4. Deployment
| Option | Pros | Cons |
|--------|------|------|
| **Local only** | Simple, no cost | Not accessible remotely |
| **GCP Cloud Run** | Already using GCS, scalable | Cost, complexity |
| **Vercel + Supabase** | Easy deployment, good DX | Multiple services |

---

## Potential LLM Capabilities

### Query Types to Support

**Diagnostic:**
- "Why did ROAS drop last week?"
- "Which campaigns are underperforming?"
- "What's causing brand leakage in PMax?"

**Recommendations:**
- "How should I reallocate budget?"
- "Which products should I exclude from Shopping?"
- "What negative keywords should I add?"

**Data Retrieval:**
- "Show me top 10 products by ROAS"
- "List all brand terms appearing in PMax"
- "What's our spend on non-branded search terms?"

**Actions (Future):**
- "Pause all products with zero conversions"
- "Add these negative keywords to PMax"
- "Update the exclusion feed"

---

## Implementation Phases

### Phase 1: Data Foundation
- [ ] Set up PostgreSQL for structured data
- [ ] Create data sync jobs (Google Ads → DB)
- [ ] Set up vector store for semantic search
- [ ] Index search terms, product titles, ad copy

### Phase 2: RAG Pipeline
- [ ] Build query router (semantic vs deterministic)
- [ ] Implement retrieval functions
- [ ] Set up LLM integration with context injection
- [ ] Create response formatter with citations

### Phase 3: Frontend
- [ ] Build dashboard with key metrics
- [ ] Implement LLM chat interface
- [ ] Add visualization components
- [ ] Connect to backend API

### Phase 4: Actions & Automation
- [ ] Add write capabilities (with approval flow)
- [ ] Scheduled data refreshes
- [ ] Alert system for anomalies
- [ ] Automated recommendations

---

## Open Questions

1. **Scope:** Start with read-only insights or include write actions?
2. **Real-time vs Cached:** How fresh does the data need to be?
3. **Multi-tenant:** Just BCD or potential for other clients?
4. **Budget:** Cloud costs acceptable or prefer local-first?
5. **Timeline:** MVP in days/weeks or longer-term project?

---

## References

- Current CLAUDE.md: Original 3-script audit vision
- Merchant Center exclusion feed: Working, uploads to GCS
- Google Ads API: v19 (current)
- Merchant Center API: products/v1beta
