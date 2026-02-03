# Phase B3.0: Advisory LLM Judge + HITL Review Pack

READ-ONLY governance layer for plan review with NO execution authority.

## Overview

The Review Pack system generates comprehensive advisory reports for proposed plans, combining:
1. **Deterministic checks** (pure Python, always runs)
2. **Optional LLM advisory** (Claude Sonnet, feature-flagged)
3. **HITL checklist** (deterministic, human review items)

**CRITICAL: This module has NO execution authority. All assessments are advisory only.**

## Components

- `llm_judge.py` - LLM advisory judge (optional, best-effort)
- `review_pack.py` - Review pack builder (deterministic + optional LLM)
- `cli_review_pack.py` - CLI entry point
- `bin/review_pack` - Shell wrapper

## Usage

### Basic Usage (LLM Disabled)

```bash
# Use latest plan and snapshot
bin/review_pack --latest-plan --latest-snapshot

# Use specific files
bin/review_pack --plan plans/runs/proposed_changes_*.json \
                --snapshot snapshots/2026-01-21T162735Z
```

### With LLM Advisory (Optional)

Enable in `.env`:
```bash
LLM_JUDGE_ENABLED=true
LLM_JUDGE_MODEL=claude-3-5-sonnet-20241022
```

Then run normally:
```bash
bin/review_pack --latest-plan --latest-snapshot
```

## Output Files

Generated in `diag/review_packs/<timestamp>/`:

- **review_pack.json** - Full review pack data
- **review_pack.md** - Human-readable summary

## Review Pack Structure

```json
{
  "version": "B3.0",
  "generated_at": "2026-01-22T21:18:59Z",
  "plan_id": "plan-...",
  "snapshot_id": "2026-01-21T162735Z",

  "deterministic_checks": {
    "plan_metadata": {...},
    "operation_summary": {...},
    "risk_flags": [...],
    "snapshot_provenance": {...}
  },

  "hitl_checklist": [
    {
      "item": "Verify plan intent matches business objective",
      "category": "INTENT",
      "required": true
    }
  ],

  "llm_advisory": {
    "advisory_only": true,
    "llm_enabled": false,
    "risk_assessment": {...},
    "sanity_checks": [...],
    "missing_evidence": [...],
    "recommended_human_checks": [...]
  }
}
```

## Risk Flags (Deterministic)

High-risk operation types (hardcoded):
- `set_campaign_budget`
- `set_bidding_strategy`
- `remove_keyword`
- `remove_ad`
- `pause_campaign`
- `pause_ad_group`

Medium-risk operation types:
- `set_keyword_bid`
- `add_negative_keyword`
- `update_ad_copy`

Volume thresholds:
- Medium-risk ops become HIGH if count > 10

## LLM Advisory (Optional)

When enabled, Claude Sonnet provides:
- Overall risk assessment (LOW/MEDIUM/HIGH)
- Sanity checks on operation patterns
- Missing evidence detection
- Recommended human checks

**Failure mode**: If LLM fails, review pack still generated without advisory.

## Docker/VM Usage

```bash
# From host
docker compose exec baseline bin/review_pack --latest-plan --latest-snapshot

# From inside container
bin/review_pack --latest-plan --latest-snapshot
```

## Safety Guarantees

1. **READ-ONLY**: Only reads snapshots/, plans/, reports/
2. **NO API CALLS**: Never queries live Google APIs
3. **ADVISORY ONLY**: Has NO execution authority
4. **BEST-EFFORT**: LLM failures don't block review pack generation
5. **FEATURE-FLAGGED**: LLM advisory disabled by default
6. **DETERMINISTIC CORE**: Always includes deterministic checks

## Integration with Apply Engine

The apply engine remains the ONLY component with execution authority. This review pack system:
- Does NOT block execution
- Does NOT approve/deny plans
- Does NOT modify apply engine behavior
- Provides advisory input for human review BEFORE execution

## Next Steps

After generating a review pack:
1. Review markdown summary: `cat diag/review_packs/<timestamp>/review_pack.md`
2. Complete HITL checklist manually
3. Use apply engine with approval guards: `bin/apply --plan <plan> --approve`
