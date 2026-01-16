# HVAC Ads 2026

Google Ads and Merchant Center audit, optimization, and automation tools for Buy Comfort Direct HVAC campaigns.

## Overview

This repo provides a **3-phase pipeline** for managing Google Ads and Merchant Center accounts safely and reproducibly:

```
Phase A: DUMP      Phase B: REPORT/PLAN     Phase C: APPLY
─────────────────────────────────────────────────────────────
  Live API    →    Snapshot Files    →     Live API
   (READ)           (READ-ONLY)            (WRITE)
```

**Safety Model:**
- Phase A (`dump`) is the ONLY place that reads from live APIs
- Phase B (`report`) and C1 (`plan`) work ONLY from local snapshots
- Phase C2 (`apply`) is the ONLY place that writes to live APIs
- All scripts require explicit flags - no silent defaults

## Quick Start

```bash
# Phase A: Capture current state (LIVE READS)
bin/dump

# Phase B: Generate monitoring report (SNAPSHOT-ONLY)
bin/report --latest

# Phase C1: Generate change plan (SNAPSHOT-ONLY)
bin/plan --latest

# Phase C2: Apply changes (LIVE WRITES - not yet implemented)
bin/apply plans/runs/<plan>.json --dry-run
```

## Directory Structure

```
hvac-ads-2026/
├── bin/                    # CLI wrappers (use these!)
│   ├── dump                # → core/dump/dump_state.py
│   ├── report              # → core/report/generate_report.py
│   ├── plan                # → core/plan/plan_changes.py
│   └── apply               # → core/apply/apply_changes.py
│
├── core/                   # Baseline pipeline (production-ready)
│   ├── dump/               # Phase A: State capture
│   ├── report/             # Phase B: Report generation
│   ├── plan/               # Phase C1: Change planning
│   ├── apply/              # Phase C2: Change execution
│   ├── configs/            # Pipeline configuration
│   └── schema/             # Data format specifications
│
├── snapshots/              # Immutable state dumps (Phase A output)
│   └── YYYY-MM-DDTHHMMSSZ/ # Timestamped snapshot folders
│
├── reports/                # Generated reports (Phase B output)
│   ├── latest.md           # Most recent report
│   ├── latest.json         # Machine-readable report
│   └── monitoring/         # Historical monitoring reports
│
├── plans/                  # Change plans (Phase C1 output)
│   ├── examples/           # Schema examples
│   └── runs/               # Generated plan files
│
└── legacy/                 # QUARANTINED - Do not use
    ├── audit/              # Old audit scripts
    ├── scripts/            # Old utility scripts
    ├── seo/                # Old SEO scripts
    ├── docs/               # Old documentation
    ├── reports/            # Old report files
    └── README.md           # Why these are quarantined
```

## The 3-Phase Model

### Phase A: Dump (Live Reads)

```bash
bin/dump                    # Full dump (Ads + Merchant)
bin/dump --ads-only         # Google Ads only
bin/dump --merchant-only    # Merchant Center only
```

- **What it does:** Captures current state from Google Ads and Merchant Center APIs
- **Output:** `snapshots/YYYY-MM-DDTHHMMSSZ/` folder with raw and normalized JSON
- **API calls:** READ-ONLY (no mutations)

### Phase B: Report (Snapshot-Only)

```bash
bin/report --latest                    # Use most recent snapshot
bin/report --snapshot snapshots/...    # Explicit snapshot path
bin/report --latest --deep-audit       # Show full details
```

- **What it does:** Analyzes snapshot data, generates monitoring report
- **Output:** `reports/latest.md` and `reports/latest.json`
- **API calls:** NONE (reads only from local files)

### Phase C1: Plan (Snapshot-Only)

```bash
bin/plan --latest                      # Use most recent snapshot
bin/plan --snapshot snapshots/...      # Explicit snapshot path
bin/plan --latest --max-ops 20         # Limit operations
```

- **What it does:** Analyzes snapshot, proposes changes based on safety rules
- **Output:** `plans/runs/proposed_changes_*.json`
- **API calls:** NONE (reads only from local files)
- **Mode:** Always DRY_RUN (plans require approval before execution)

### Phase C2: Apply (Live Writes)

```bash
bin/apply plans/runs/<plan>.json           # DRY_RUN (default)
bin/apply plans/runs/<plan>.json --execute # LIVE WRITES
```

- **What it does:** Executes approved change plans
- **API calls:** WRITE (makes actual changes to Google Ads/Merchant)
- **Status:** NOT YET IMPLEMENTED - plans must be applied manually

## Safety Guardrails

1. **Explicit flags required:** Scripts refuse to run without `--latest` or `--snapshot`
2. **Snapshot isolation:** Report and Plan phases cannot make API calls
3. **DRY_RUN default:** Apply always defaults to dry-run mode
4. **Plan approval:** Plans must be reviewed and approved before execution
5. **Preconditions:** Apply verifies all preconditions before each operation
6. **Rollback data:** Each operation includes rollback instructions

## Configuration

Key configuration files in `core/configs/`:

- `brand_terms.json` - BCD brand keywords (required for planning)
- `discontinued_skus.txt` - SKUs to auto-exclude from shopping

## Environment Variables

Required in `.env`:

```bash
GOOGLE_ADS_DEVELOPER_TOKEN=...
GOOGLE_ADS_CLIENT_ID=...
GOOGLE_ADS_CLIENT_SECRET=...
GOOGLE_ADS_REFRESH_TOKEN=...
GOOGLE_ADS_CUSTOMER_ID=...
GOOGLE_ADS_LOGIN_CUSTOMER_ID=...  # Optional (MCC)
MERCHANT_CENTER_ID=...            # For Merchant Center access
```

## Legacy Code

The `legacy/` folder contains old scripts that have been quarantined. These scripts:
- May make unexpected API calls
- Are not part of the baseline pipeline
- Should NOT be used for production operations

See `legacy/README.md` for details.
