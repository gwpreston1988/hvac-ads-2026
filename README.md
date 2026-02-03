# HVAC Ads Intelligence Platform

**Automated Google Ads & Merchant Center optimization pipeline with human-in-the-loop governance.**

A production-grade system for managing paid advertising campaigns with full audit trails, snapshot-based analysis, and safe change execution.

## Key Features

- **Snapshot-Based Architecture** — All analysis runs on immutable point-in-time data captures, never live APIs
- **3-Phase Pipeline** — Clear separation between data capture (READ), analysis (LOCAL), and execution (WRITE)
- **Human-in-the-Loop** — OTP-verified approval required before any live changes
- **Multi-Platform Integration** — Google Ads, Merchant Center, and Search Console in unified snapshots
- **Review Packs** — Generated governance packages with risk scoring and rollback instructions
- **Truth Sweep** — Cross-validation against Google's own recommendations API

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HVAC Ads Pipeline                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Phase A: DUMP          Phase B: ANALYZE         Phase C: EXECUTE          │
│   ─────────────          ───────────────          ────────────────          │
│                                                                             │
│   ┌───────────┐          ┌───────────┐           ┌───────────┐             │
│   │ Google    │          │ Reports   │           │ Apply     │             │
│   │ Ads API   │──READ───▶│ Plans     │───APPROVE─▶│ Changes   │──WRITE──▶  │
│   │ Merchant  │          │ Truth     │    (OTP)  │ Rollback  │             │
│   │ GSC       │          │ Sweep     │           │ Audit Log │             │
│   └───────────┘          └───────────┘           └───────────┘             │
│         │                      │                       │                    │
│         ▼                      ▼                       ▼                    │
│   snapshots/              reports/                plans/runs/               │
│   YYYY-MM-DDTHHMMSSZ/     latest.json             *.results.json            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.12 |
| **APIs** | Google Ads API v19, Merchant Center API v2.1, Search Console API |
| **Infrastructure** | Docker, GCP Compute Engine |
| **Frontend** | [bcd-cockpit](https://github.com/gwpreston1988/bcd-cockpit) (Next.js 14) |
| **Auth** | OAuth 2.0 / Service Account |

## Quick Start

```bash
# Phase A: Capture current state (LIVE READS)
bin/dump

# Phase B: Generate monitoring report (SNAPSHOT-ONLY)
bin/report --latest

# Phase C1: Generate change plan (SNAPSHOT-ONLY)
bin/plan --latest

# Phase C2: Apply changes (LIVE WRITES - requires approval)
bin/apply plans/runs/<plan>.json --execute
```

## The 3-Phase Safety Model

### Phase A: Dump (Live Reads)

```bash
bin/dump                    # Full dump (Ads + Merchant + GSC)
bin/dump --ads-only         # Google Ads only
bin/dump --merchant-only    # Merchant Center only
```

- **What it does:** Captures current state from Google APIs
- **Output:** `snapshots/YYYY-MM-DDTHHMMSSZ/` with raw and normalized JSON
- **API calls:** READ-ONLY (no mutations)
- **Contains:** Campaigns, ad groups, keywords, products, performance metrics

### Phase B: Report & Plan (Snapshot-Only)

```bash
bin/report --latest                    # Generate analysis report
bin/plan --latest                      # Generate change proposals
bin/truth_sweep --latest               # Cross-check with Google recommendations
```

- **What it does:** Analyzes snapshot data, identifies optimizations
- **Output:** `reports/latest.json`, `plans/runs/*.json`
- **API calls:** NONE (reads only from local files)
- **Guarantees:** Cannot accidentally modify live account

### Phase C: Apply (Live Writes)

```bash
bin/apply plans/runs/<plan>.json           # DRY_RUN (default)
bin/apply plans/runs/<plan>.json --execute # LIVE WRITES
```

- **What it does:** Executes approved change plans
- **API calls:** WRITE (makes actual changes)
- **Requires:** Human approval via OTP verification
- **Includes:** Precondition checks, rollback data, audit logging

## Safety Guardrails

| Guardrail | Description |
|-----------|-------------|
| **Explicit flags** | Scripts refuse to run without `--latest` or `--snapshot` |
| **Snapshot isolation** | Report and Plan phases cannot make API calls |
| **DRY_RUN default** | Apply always defaults to dry-run mode |
| **Plan approval** | Plans must be reviewed before execution |
| **Preconditions** | Apply verifies state before each operation |
| **Rollback data** | Every change includes undo instructions |
| **Audit trail** | All actions logged with timestamps |

## Directory Structure

```
hvac-ads-2026/
├── bin/                    # CLI entry points
│   ├── dump                # → core/dump/dump_state.py
│   ├── report              # → core/report/generate_report.py
│   ├── plan                # → core/plan/plan_changes.py
│   ├── apply               # → core/apply/apply_changes.py
│   ├── review_pack         # → generate HITL review packages
│   └── truth_sweep         # → cross-check Google recommendations
│
├── core/                   # Pipeline modules
│   ├── dump/               # Phase A: State capture
│   ├── report/             # Phase B: Report generation
│   ├── plan/               # Phase C1: Change planning
│   ├── apply/              # Phase C2: Change execution
│   ├── judge/              # Advisory LLM judge (risk scoring)
│   ├── mcp/                # MCP server tools
│   ├── configs/            # Pipeline configuration
│   └── schema/             # Data format specifications
│
├── snapshots/              # Immutable state dumps
│   └── YYYY-MM-DDTHHMMSSZ/ # Timestamped folders
│       ├── _manifest.json  # Extraction metadata
│       ├── raw/            # Raw API responses
│       └── normalized/     # Cleaned, structured data
│
├── reports/                # Generated analysis
│   ├── latest.md           # Human-readable report
│   └── latest.json         # Machine-readable report
│
├── plans/                  # Change proposals
│   ├── examples/           # Schema examples
│   └── runs/               # Generated plans
│
├── diag/                   # Diagnostics & governance
│   ├── review_packs/       # HITL approval packages
│   └── truth_sweep/        # Google recommendations cross-check
│
├── infra/                  # Infrastructure
│   └── gcp/                # GCE deployment scripts
│
└── legacy/                 # Quarantined old code
```

## Deployment

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.template .env
# Edit .env with your credentials

# Run snapshot capture
bin/dump
```

### Docker

```bash
docker build -t hvac-ads-2026 .
docker run --env-file .env hvac-ads-2026 bin/dump
```

### GCP Compute Engine

```bash
# Create VM with service account
./infra/gcp/create_vm.sh

# Bootstrap dependencies
./infra/gcp/bootstrap_vm.sh

# Run smoke tests
./infra/gcp/smoke_tests.sh
```

## Environment Variables

Required in `.env`:

```bash
# Google Ads
GOOGLE_ADS_DEVELOPER_TOKEN=...
GOOGLE_ADS_CLIENT_ID=...
GOOGLE_ADS_CLIENT_SECRET=...
GOOGLE_ADS_REFRESH_TOKEN=...
GOOGLE_ADS_CUSTOMER_ID=...
GOOGLE_ADS_LOGIN_CUSTOMER_ID=...    # Optional (MCC)

# Merchant Center
MERCHANT_CENTER_ID=...

# Search Console
GSC_SITE_URL=https://...
```

## Related Projects

- [bcd-cockpit](https://github.com/gwpreston1988/bcd-cockpit) — Read-only monitoring dashboard (Next.js frontend)

## License

Private - All rights reserved
