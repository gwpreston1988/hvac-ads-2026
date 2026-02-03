# HVAC Ads Intelligence Platform

## Overview

Production pipeline for Google Ads and Merchant Center optimization with human-in-the-loop governance. Uses a 3-phase architecture that separates data capture, analysis, and execution for safety.

**Related repo:** [bcd-cockpit](https://github.com/gwpreston1988/bcd-cockpit) (Next.js frontend dashboard)

## Architecture

```
Phase A: DUMP (Live Reads)  →  Phase B: ANALYZE (Local Only)  →  Phase C: APPLY (Live Writes)
       ↓                              ↓                                  ↓
   snapshots/                    reports/                          Approved changes
   YYYY-MM-DDTHHMMSSZ/           plans/runs/                       with OTP verification
```

## CLI Commands

### Phase A: State Capture
```bash
bin/dump                    # Full dump (Ads + Merchant + GSC)
bin/dump --ads-only         # Google Ads only
bin/dump --merchant-only    # Merchant Center only
```

### Phase B: Analysis (Snapshot-Only)
```bash
bin/report --latest         # Generate monitoring report
bin/plan --latest           # Generate change proposals
bin/truth_sweep --latest    # Cross-check Google recommendations
bin/review_pack --latest    # Generate HITL approval package
```

### Phase C: Execution (Requires Approval)
```bash
bin/apply plans/runs/<plan>.json           # DRY_RUN (default)
bin/apply plans/runs/<plan>.json --execute # LIVE WRITES
```

## Directory Structure

```
hvac-ads-2026/
├── bin/                    # CLI entry points (use these!)
├── core/                   # Pipeline modules
│   ├── dump/               # Phase A: API reads
│   ├── report/             # Phase B: Report generation
│   ├── plan/               # Phase B: Change planning
│   ├── apply/              # Phase C: Change execution
│   ├── judge/              # Advisory LLM risk scoring
│   ├── mcp/                # MCP server tools
│   ├── configs/            # Pipeline configuration
│   └── schema/             # Data format specs
├── snapshots/              # Immutable state dumps (gitignored)
├── reports/                # Generated reports (gitignored)
├── plans/                  # Change proposals
│   ├── examples/           # Schema examples
│   └── runs/               # Generated plans (gitignored)
├── diag/                   # Diagnostics & governance
├── infra/gcp/              # GCE deployment scripts
└── legacy/                 # Quarantined old code - DO NOT USE
```

## Safety Model

1. **Phase A** is the ONLY place that reads from live APIs
2. **Phase B** works ONLY from local snapshot files (no API calls possible)
3. **Phase C** is the ONLY place that writes to live APIs
4. **All writes require human approval** via OTP verification
5. **DRY_RUN is always default** - must explicitly pass `--execute`

## Configuration

### Brand Terms (`core/configs/brand_terms.json`)
Used to detect brand leakage in PMax campaigns:
- rheem, goodman, solace, bcd, buy comfort direct

### Environment Variables
Required in `.env`:
```
GOOGLE_ADS_DEVELOPER_TOKEN
GOOGLE_ADS_CLIENT_ID
GOOGLE_ADS_CLIENT_SECRET
GOOGLE_ADS_REFRESH_TOKEN
GOOGLE_ADS_CUSTOMER_ID
GOOGLE_ADS_LOGIN_CUSTOMER_ID  # Optional (MCC)
MERCHANT_CENTER_ID
GSC_SITE_URL
```

## Key Files

| File | Purpose |
|------|---------|
| `core/dump/dump_state.py` | Extracts state from Google APIs |
| `core/report/generate_report.py` | Generates analysis reports |
| `core/plan/plan_changes.py` | Proposes optimizations |
| `core/apply/apply_changes.py` | Executes approved changes |
| `core/judge/llm_judge.py` | Advisory risk scoring |
| `core/schema/SCHEMA.md` | Snapshot data format |
| `core/schema/CHANGE_SCHEMA.md` | Plan/change format |

## Common Tasks

### Capture fresh snapshot
```bash
bin/dump
```

### Generate report from latest snapshot
```bash
bin/report --latest
# Output: reports/latest.md, reports/latest.json
```

### Generate optimization plan
```bash
bin/plan --latest
# Output: plans/runs/proposed_changes_*.json
```

### Review before applying
```bash
bin/review_pack --latest
# Output: diag/review_packs/review_pack_*.json
```

## Guardrails

- Scripts refuse to run without explicit `--latest` or `--snapshot` flag
- Report and Plan phases cannot make API calls (by design)
- Apply defaults to dry-run mode
- All operations include rollback instructions
- Audit trail logged for all actions
