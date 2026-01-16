# Core Pipeline

This folder contains the **baseline pipeline** for Google Ads and Merchant Center management. These are the ONLY scripts that should be used for production operations.

## Directory Structure

```
core/
├── dump/           Phase A: Live state capture
│   └── dump_state.py
├── report/         Phase B: Snapshot-only reporting
│   ├── generate_report.py
│   └── TEMPLATE.md
├── plan/           Phase C1: Snapshot-only planning
│   └── plan_changes.py
├── apply/          Phase C2: Live change execution (TODO)
│   └── apply_changes.py
├── configs/        Pipeline configuration
│   ├── brand_terms.json
│   └── discontinued_skus.txt
└── schema/         Data format specifications
    ├── SCHEMA.md
    ├── FIELDS.md
    └── CHANGE_SCHEMA.md
```

## Pipeline Phases

### Phase A: Dump (`dump/dump_state.py`)

**Purpose:** Capture current state from live APIs into immutable snapshots.

**Behavior:**
- Makes READ-ONLY API calls to Google Ads and Merchant Center
- Outputs timestamped snapshot folder to `snapshots/YYYY-MM-DDTHHMMSSZ/`
- Generates both `raw/` (API responses) and `normalized/` (clean JSON) data
- Creates `_manifest.json` with provenance and `_index.json` for quick lookups

**Stopping Point:** After dump completes, you have a complete offline copy of account state.

### Phase B: Report (`report/generate_report.py`)

**Purpose:** Analyze snapshot data and generate monitoring reports.

**Behavior:**
- Reads ONLY from local snapshot files (NO API CALLS)
- Requires explicit `--latest` or `--snapshot` flag
- Outputs `reports/latest.md` and `reports/latest.json`
- Includes: account fingerprint, brand protection status, data quality metrics

**Stopping Point:** After report completes, review the report to understand current state.

### Phase C1: Plan (`plan/plan_changes.py`)

**Purpose:** Propose changes based on safety rules and snapshot analysis.

**Behavior:**
- Reads ONLY from local snapshot files (NO API CALLS)
- Requires explicit `--latest` or `--snapshot` flag
- Requires non-empty `configs/brand_terms.json` (fails fast if missing)
- Outputs DRY_RUN plan JSON to `plans/runs/`
- Plan includes: operations, preconditions, rollback data, evidence

**Safety Rules (S1-S5):**
- S1: Flag BROAD match keywords in Branded campaign
- S2: Flag non-brand keywords in Branded campaign
- S3: Check Branded bidding strategy is MANUAL_CPC
- S4: Flag manufacturer brands in Branded assets
- S5: Flag disapproved Merchant products (propose exclusion if in discontinued list)

**Stopping Point:** After plan completes, review the plan JSON before proceeding.

### Phase C2: Apply (`apply/apply_changes.py`) - TODO

**Purpose:** Execute approved change plans.

**Behavior (planned):**
- Reads plan JSON and verifies all preconditions
- Makes WRITE API calls to Google Ads / Merchant Center
- Defaults to `--dry-run` mode (no actual changes)
- Requires `--execute` flag and plan approval to apply
- Logs all operations with rollback data

**Stopping Point:** After apply completes, verify changes in Google Ads UI.

## Safety Model

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│  Phase A    │     │  Phase B & C1   │     │  Phase C2   │
│   DUMP      │────▶│  REPORT & PLAN  │────▶│   APPLY     │
│ (live read) │     │ (snapshot-only) │     │ (live write)│
└─────────────┘     └─────────────────┘     └─────────────┘
      │                     │                      │
      ▼                     ▼                      ▼
  snapshots/           reports/               Google Ads
                       plans/runs/            Merchant Center
```

**Key Principles:**
1. **Explicit over implicit:** No silent defaults; always require flags
2. **Snapshot isolation:** Report and Plan cannot access live APIs
3. **Fail fast:** Missing configs abort immediately with clear error
4. **DRY_RUN first:** Plans are proposals, not actions
5. **Rollback ready:** Every operation includes undo instructions

## Configuration Files

### `configs/brand_terms.json`

BCD brand terms used for keyword classification. **REQUIRED** for planning.

```json
{
  "brand_terms": ["buy comfort direct", "buycomfortdirect", "bcd", ...],
  "brand_variants": {
    "rheem": ["rheem", "ruud"],
    "goodman": ["goodman", "amana", "daikin"],
    ...
  }
}
```

### `configs/discontinued_skus.txt`

SKUs to auto-exclude from Shopping when disapproved. One per line.

```
# Discontinued SKUs - one per line
SKU12345
SKU67890
```

## Schema Documentation

See `schema/` for data format specifications:

- **SCHEMA.md:** Snapshot structure and file organization
- **FIELDS.md:** Normalized field definitions per entity type
- **CHANGE_SCHEMA.md:** Plan/operation JSON format
