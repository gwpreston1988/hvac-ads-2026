# Change Plan Schema (Phase C1)

## Overview

This document defines the JSON schema for `proposed_changes.json` files used in the HVAC Ads change management pipeline.

**Key Principles:**
- **Snapshot-derived**: All plans reference a specific snapshot_id. No live API calls during plan generation.
- **Idempotent**: Operations have stable IDs and preconditions, making re-runs safe.
- **Reviewable**: Human-readable intents, before/after states, and risk assessments.
- **Guardrailed**: Explicit limits enforced at apply time (max ops, forbidden actions, etc.).
- **Auditable**: Full provenance chain from snapshot → plan → execution.
- **Machine-parseable**: All preconditions, evidence, and rollback instructions are structured for automated processing.

---

## File Locations

```
plans/
├── examples/
│   ├── proposed_changes_example_minimal.json
│   └── proposed_changes_example_full.json
└── runs/
    └── <plan_id>.json              # Generated plans go here
```

---

## Top-Level Structure

```json
{
  "plan_id": "string",
  "plan_version": "string",
  "created_utc": "ISO8601 timestamp",
  "snapshot_id": "string",
  "snapshot_version": "string",
  "sources": { ... },
  "mode": "DRY_RUN" | "APPLY",
  "plan_context": { ... },
  "guardrails": { ... },
  "summary": { ... },
  "operations": [ ... ],
  "approvals": { ... },
  "integrity": { ... }
}
```

---

## Field Definitions

### `plan_id` (required)
- **Type**: `string`
- **Format**: `plan-<snapshot_id>-<sequence>` or UUID
- **Description**: Unique identifier for this plan. Deterministic generation preferred for reproducibility.
- **Example**: `"plan-2026-01-15T202326Z-001"`

### `plan_version` (required)
- **Type**: `string`
- **Format**: Semantic version
- **Description**: Schema version of this plan format.
- **Example**: `"C1.1"`

### `created_utc` (required)
- **Type**: `string` (ISO8601)
- **Description**: UTC timestamp when this plan was generated.
- **Example**: `"2026-01-16T15:30:00Z"`

### `snapshot_id` (required)
- **Type**: `string`
- **Description**: Must match the `snapshots/<snapshot_id>/` directory name. Links plan to source data.
- **Example**: `"2026-01-15T202326Z"`

### `snapshot_version` (required)
- **Type**: `string`
- **Description**: From `_manifest.json` snapshot_version field. Ensures schema compatibility.
- **Example**: `"A3.0"`

### `sources` (required)
- **Type**: `object`
- **Description**: Account identifiers for audit trail.

```json
{
  "google_ads_customer_id": "9256598060",
  "google_ads_login_customer_id": "9256598060",
  "merchant_center_id": "5308355318"
}
```

### `mode` (required)
- **Type**: `enum`
- **Values**: `"DRY_RUN"` | `"APPLY"`
- **Description**: Execution mode. Plans are generated as `DRY_RUN` by default. Must be explicitly changed to `APPLY` after review.
- **Default**: `"DRY_RUN"`

---

## Plan Context Object

The `plan_context` object captures global parameters used during plan generation. This makes plans self-documenting and reproducible.

```json
{
  "plan_context": {
    "brand_terms_version": "2026-01-15",
    "brand_terms": ["buy comfort direct", "buycomfortdirect", "bcd", "comfort direct"],
    "manufacturer_brands": ["rheem", "goodman", "solace", "daikin", "ruud", "amana"],
    "thresholds": {
      "brand_cpc_max": 2.00,
      "roas_target": 4.0,
      "min_conversions_for_migration": 3,
      "min_clicks_for_analysis": 10
    },
    "lookback_days": 30,
    "planner_rules_applied": [
      "rule:brand_protection:add_brand_negative_to_pmax",
      "rule:brand_protection:remove_brand_from_pmax_assets",
      "rule:exact_match_migration:high_volume_brand_term"
    ],
    "notes": "Generated from snapshot 2026-01-15T202326Z with standard brand protection rules"
  }
}
```

### Plan Context Fields

| Field | Type | Description |
|-------|------|-------------|
| `brand_terms_version` | `string` | Version/date of brand terms list used |
| `brand_terms` | `array` | BCD brand terms used for classification |
| `manufacturer_brands` | `array` | Manufacturer brand names (rheem, goodman, etc.) |
| `thresholds` | `object` | Numeric thresholds used in decision logic |
| `lookback_days` | `integer` | Days of performance data considered |
| `planner_rules_applied` | `array` | Rule IDs that were evaluated |
| `notes` | `string` | Human-readable generation notes |

---

## Guardrails Object

The `guardrails` object defines enforceable limits that `apply_changes.py` MUST respect. Violation of any guardrail aborts execution.

```json
{
  "guardrails": {
    "max_total_ops": 50,
    "max_ops_by_type": {
      "ADS_SET_KEYWORD_STATUS": 20,
      "ADS_ADD_NEGATIVE_KEYWORD": 30,
      "ADS_UPDATE_BID_STRATEGY": 0,
      "ADS_UPDATE_BUDGET": 0
    },
    "forbid_budget_changes": true,
    "forbid_campaign_pause": true,
    "forbid_campaign_enable": false,
    "max_budget_pct_change": 0,
    "forbid_broad_match": true,
    "forbid_manufacturer_brand_negatives": true,
    "forbid_bid_strategy_changes": true,
    "forbid_conversion_goal_changes": true,
    "forbid_location_targeting_changes": true,
    "forbid_url_expansion_changes": true,
    "forbid_auto_apply_settings": true,
    "max_text_edit_chars": 100,
    "allowlist_campaign_ids": null,
    "blocklist_campaign_ids": [],
    "require_manual_approval_for_types": [
      "ADS_UPDATE_BID_STRATEGY",
      "ADS_SET_CAMPAIGN_STATUS",
      "ADS_REMOVE_ASSET",
      "MERCHANT_EXCLUDE_PRODUCT"
    ],
    "require_precondition_match": true,
    "abort_on_missing_entity": true,
    "abort_on_first_error": true,
    "max_risk_level": "MEDIUM"
  }
}
```

### Guardrail Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `max_total_ops` | `integer` | Maximum number of operations allowed in a single plan. |
| `max_ops_by_type` | `object` | Per-operation-type limits. Value of `0` forbids that type entirely. |
| `forbid_budget_changes` | `boolean` | If true, any budget modification aborts. |
| `forbid_campaign_pause` | `boolean` | If true, pausing campaigns is forbidden. |
| `forbid_campaign_enable` | `boolean` | If true, enabling campaigns is forbidden. |
| `max_budget_pct_change` | `number` | Maximum allowed percentage change to any budget (0 = no changes). |
| `forbid_broad_match` | `boolean` | If true, creating BROAD match keywords is forbidden. |
| `forbid_manufacturer_brand_negatives` | `boolean` | If true, adding manufacturer brand names (rheem, goodman, etc.) as negative keywords is forbidden. Protects PMax from losing manufacturer-branded traffic. |
| `forbid_bid_strategy_changes` | `boolean` | If true, changing bidding strategies is forbidden (separate from budget). |
| `forbid_conversion_goal_changes` | `boolean` | If true, changing conversion goals/actions is forbidden. |
| `forbid_location_targeting_changes` | `boolean` | If true, changing geo-targeting is forbidden. |
| `forbid_url_expansion_changes` | `boolean` | If true, changing PMax URL expansion settings is forbidden. |
| `forbid_auto_apply_settings` | `boolean` | If true, changing auto-apply recommendations is forbidden. |
| `max_text_edit_chars` | `integer` | Maximum characters that can be changed in a single text edit. Prevents "rewrite everything" accidents. |
| `allowlist_campaign_ids` | `array\|null` | If set, only these campaign IDs can be modified. Null = all allowed. |
| `blocklist_campaign_ids` | `array` | These campaign IDs cannot be modified under any circumstances. |
| `require_manual_approval_for_types` | `array` | Operation types requiring explicit approval before apply. |
| `require_precondition_match` | `boolean` | If true, precondition mismatches abort the operation. |
| `abort_on_missing_entity` | `boolean` | If true, missing entities (deleted since snapshot) abort. |
| `abort_on_first_error` | `boolean` | If true, first error stops all execution. If false, continues and reports. |
| `max_risk_level` | `enum` | Maximum allowed risk level. Operations exceeding this are skipped/aborted. |

---

## Risk Levels

Risk levels have a strict ordering and are enforced by the apply logic.

### Risk Level Ordering

```
LOW < MEDIUM < HIGH
```

### Risk Level Definitions

| Level | Numeric | Description | Examples |
|-------|---------|-------------|----------|
| `LOW` | 1 | Safe, easily reversible, minimal impact | Adding negative keywords, enabling paused brand keywords |
| `MEDIUM` | 2 | Moderate impact, may affect performance, reversible with effort | Removing/replacing PMax assets, changing match types, excluding products |
| `HIGH` | 3 | Significant impact, affects bidding/budget/campaign status | Changing bidding strategies, modifying budgets, pausing campaigns |

### Risk Enforcement Rules

1. If `op.risk.level` > `guardrails.max_risk_level`, the operation is **skipped** (or aborted if `abort_on_first_error` is true).
2. If `op.op_type` is in `guardrails.require_manual_approval_for_types`, then `approvals.operation_approvals[op_id].approved` MUST be `true` before execution.
3. Risk level is determined by `op_type` defaults but can be elevated by the planner based on context.

---

## Summary Object

Provides a quick overview for human review without reading all operations.

```json
{
  "summary": {
    "total_operations": 6,
    "operations_by_type": {
      "ADS_ADD_NEGATIVE_KEYWORD": 1,
      "ADS_SET_KEYWORD_MATCH_TYPE": 1,
      "ADS_SET_KEYWORD_STATUS": 1,
      "ADS_UPDATE_ASSET_TEXT": 1,
      "ADS_REMOVE_ASSET": 1,
      "MERCHANT_EXCLUDE_PRODUCT": 1
    },
    "operations_by_risk": {
      "LOW": 2,
      "MEDIUM": 4,
      "HIGH": 0
    },
    "estimated_api_calls": 6,
    "platforms_affected": ["GOOGLE_ADS", "MERCHANT_CENTER"],
    "campaigns_affected": ["20958985895", "20815709270"],
    "risk_score": "MEDIUM",
    "risk_summary": "4 medium-risk operations including PMax asset changes and product exclusion",
    "requires_approval": true,
    "approval_required_ops": ["op-004", "op-006"]
  }
}
```

---

## Operations Array

Each operation is an object describing a single atomic change.

### Operation Object Structure

```json
{
  "op_id": "string",
  "op_type": "enum",
  "entity_ref": "string",
  "entity": { ... },
  "intent": "string",
  "before": { ... },
  "after": { ... },
  "preconditions": [ ... ],
  "rollback": { ... },
  "risk": { ... },
  "evidence": [ ... ],
  "created_from_rule": "string",
  "approved": false,
  "approval_notes": null
}
```

### Operation Field Definitions

#### `op_id` (required)
- **Type**: `string`
- **Format**: `op-<sequence>` or deterministic hash
- **Description**: Unique, stable identifier for this operation within the plan.
- **Example**: `"op-001"`

#### `op_type` (required)
- **Type**: `enum`
- **Description**: The type of change being made.

**Supported Operation Types:**

| op_type | Platform | Default Risk | Description |
|---------|----------|--------------|-------------|
| `ADS_SET_KEYWORD_STATUS` | GOOGLE_ADS | LOW | Enable/pause/remove a keyword |
| `ADS_SET_KEYWORD_MATCH_TYPE` | GOOGLE_ADS | MEDIUM | Change keyword match type |
| `ADS_SET_KEYWORD_BID` | GOOGLE_ADS | MEDIUM | Update keyword-level bid |
| `ADS_ADD_NEGATIVE_KEYWORD` | GOOGLE_ADS | LOW | Add negative keyword (campaign or ad group level) |
| `ADS_REMOVE_NEGATIVE_KEYWORD` | GOOGLE_ADS | LOW | Remove a negative keyword |
| `ADS_UPDATE_ASSET_TEXT` | GOOGLE_ADS | MEDIUM | Modify PMax/RSA text asset |
| `ADS_REMOVE_ASSET` | GOOGLE_ADS | MEDIUM | Remove an asset from asset group |
| `ADS_ADD_ASSET` | GOOGLE_ADS | MEDIUM | Add new asset to asset group |
| `ADS_SET_CAMPAIGN_STATUS` | GOOGLE_ADS | HIGH | Enable/pause a campaign |
| `ADS_UPDATE_BID_STRATEGY` | GOOGLE_ADS | HIGH | Change bidding strategy |
| `ADS_UPDATE_BUDGET` | GOOGLE_ADS | HIGH | Modify campaign budget |
| `ADS_SET_AD_GROUP_STATUS` | GOOGLE_ADS | MEDIUM | Enable/pause an ad group |
| `MERCHANT_EXCLUDE_PRODUCT` | MERCHANT_CENTER | MEDIUM | Mark product excluded via supplemental feed |
| `MERCHANT_INCLUDE_PRODUCT` | MERCHANT_CENTER | MEDIUM | Remove exclusion from supplemental feed |
| `MERCHANT_UPDATE_ATTRIBUTE` | MERCHANT_CENTER | MEDIUM | Update product attribute via supplemental |

---

## Entity Reference (entity_ref)

Every operation MUST have a canonical `entity_ref` string for joins, lookups, and validation.

### Format

```
<platform>.<entity_type>:<entity_id>
```

### Examples

| Entity Type | entity_ref Example |
|-------------|-------------------|
| Campaign | `ads.campaign:20815709270` |
| Ad Group | `ads.ad_group:154321098765` |
| Keyword | `ads.keyword:701234567890` |
| Negative Keyword (new) | `ads.negative_keyword:new:20815709270:buy_comfort_direct` |
| Asset | `ads.asset:asset-12345678` |
| Asset Group | `ads.asset_group:ag-98765432` |
| Merchant Product | `merchant.product:online:en:US:SKU123` |
| Merchant Offer | `merchant.offer:PRD-12345` |

### Entity Object (metadata)

The `entity` object provides human-readable metadata alongside `entity_ref`:

```json
{
  "entity_ref": "ads.keyword:701234567890",
  "entity": {
    "platform": "GOOGLE_ADS",
    "entity_type": "KEYWORD",
    "entity_id": "701234567890",
    "entity_name": "buy comfort direct",
    "parent_refs": [
      "ads.customer:9256598060",
      "ads.campaign:20958985895",
      "ads.ad_group:154321098765"
    ]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `platform` | `enum` | `"GOOGLE_ADS"`, `"MERCHANT_CENTER"` |
| `entity_type` | `string` | `"CAMPAIGN"`, `"AD_GROUP"`, `"KEYWORD"`, `"NEGATIVE_KEYWORD"`, `"ASSET"`, `"ASSET_GROUP"`, `"PRODUCT"` |
| `entity_id` | `string` | The unique ID of the entity |
| `entity_name` | `string` | Human-readable name/text (for review) |
| `parent_refs` | `array` | Parent entity refs in hierarchy order |

---

## Preconditions (Machine-Parseable DSL)

Preconditions use a strict DSL that can be evaluated programmatically without parsing English.

### Precondition Structure

```json
{
  "path": "string",
  "op": "enum",
  "value": "any",
  "description": "string"
}
```

### Supported Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `EQUALS` | Exact match | `{"path": "status", "op": "EQUALS", "value": "ENABLED"}` |
| `NOT_EQUALS` | Not equal | `{"path": "status", "op": "NOT_EQUALS", "value": "REMOVED"}` |
| `IN` | Value in list | `{"path": "match_type", "op": "IN", "value": ["EXACT", "PHRASE"]}` |
| `NOT_IN` | Value not in list | `{"path": "match_type", "op": "NOT_IN", "value": ["BROAD"]}` |
| `CONTAINS` | String contains | `{"path": "text", "op": "CONTAINS", "value": "BCD"}` |
| `NOT_CONTAINS` | String does not contain | `{"path": "text", "op": "NOT_CONTAINS", "value": "discount"}` |
| `EXISTS` | Field exists and is not null | `{"path": "entity_id", "op": "EXISTS", "value": null}` |
| `NOT_EXISTS` | Field does not exist or is null | `{"path": "negative_keyword", "op": "NOT_EXISTS", "value": null}` |
| `GT` | Greater than | `{"path": "clicks", "op": "GT", "value": 10}` |
| `GTE` | Greater than or equal | `{"path": "conversions", "op": "GTE", "value": 3}` |
| `LT` | Less than | `{"path": "cpc", "op": "LT", "value": 5.00}` |
| `LTE` | Less than or equal | `{"path": "roas", "op": "LTE", "value": 2.0}` |
| `MATCHES` | Regex match | `{"path": "text", "op": "MATCHES", "value": "^[A-Z]{2,4}\\d+"}` |

### Path Syntax

Paths use dot notation to reference nested fields:
- `status` - Direct field on entity
- `campaign.status` - Field on parent campaign
- `campaign.bidding_strategy` - Nested parent field
- `ad_group.status` - Field on parent ad group

### Precondition Example

```json
"preconditions": [
  {
    "path": "status",
    "op": "EQUALS",
    "value": "ENABLED",
    "description": "Keyword must be enabled"
  },
  {
    "path": "match_type",
    "op": "EQUALS",
    "value": "PHRASE",
    "description": "Must be PHRASE match before changing to EXACT"
  },
  {
    "path": "campaign.bidding_strategy",
    "op": "EQUALS",
    "value": "MANUAL_CPC",
    "description": "Campaign must use Manual CPC bidding"
  }
]
```

---

## Evidence (Resolvable Pointers)

Evidence provides traceable links back to snapshot data. Each evidence entry is resolvable.

### Evidence Structure

```json
"evidence": [
  {
    "snapshot_path": "normalized/ads/keywords.json",
    "key": "id",
    "value": "701234567890",
    "field_path": "records[0]",
    "note": "Keyword identified as PHRASE match brand term"
  },
  {
    "snapshot_path": "normalized/ads/change_history.json",
    "key": "resource_id",
    "value": "customers/9256598060/adGroupCriteria/154321098765~701234567890",
    "field_path": null,
    "note": "Recent change detected"
  }
],
"evidence_query": "SELECT * FROM keywords WHERE campaign_id = '20958985895' AND match_type = 'PHRASE' AND text CONTAINS 'buy comfort'"
```

### Evidence Fields

| Field | Type | Description |
|-------|------|-------------|
| `snapshot_path` | `string` | Relative path within snapshot directory |
| `key` | `string` | Field name to match on |
| `value` | `string` | Value to match |
| `field_path` | `string\|null` | JSONPath or array index if known |
| `note` | `string` | Human-readable explanation |

### Evidence Query (optional)

The `evidence_query` field documents the logic used to find this entity. It's for debugging and audit, not execution.

---

## Rollback (Deterministic Structure)

Rollback instructions must be machine-executable, not prose.

### Rollback Types

| Type | Description | When to Use |
|------|-------------|-------------|
| `RESTORE_BEFORE` | Apply the `before` state values | Status changes, text edits, match type changes |
| `INVERSE_OP` | Execute the inverse operation | Adding/removing items |
| `DELETE_CREATED` | Delete the entity that was created | New keywords, new negatives |
| `MANUAL_REQUIRED` | Cannot be automatically rolled back | Complex asset operations |
| `NO_ROLLBACK` | No rollback needed (operation is inherently safe or no-op) | Read-only checks |

### Rollback Structure

```json
"rollback": {
  "type": "RESTORE_BEFORE",
  "data": {
    "status": "PAUSED",
    "match_type": "PHRASE"
  },
  "notes": "Restore keyword to PAUSED status and PHRASE match type"
}
```

### Rollback Examples

**Status Change:**
```json
"rollback": {
  "type": "RESTORE_BEFORE",
  "data": { "status": "PAUSED" },
  "notes": "Re-pause the keyword"
}
```

**New Negative Keyword:**
```json
"rollback": {
  "type": "DELETE_CREATED",
  "data": {
    "entity_ref": "ads.negative_keyword:new:20815709270:buy_comfort_direct"
  },
  "notes": "Remove the negative keyword that was added"
}
```

**Asset Removal (cannot auto-restore):**
```json
"rollback": {
  "type": "MANUAL_REQUIRED",
  "data": {
    "original_text": "Buy Comfort Direct - Best HVAC Deals"
  },
  "notes": "Asset removal cannot be undone; must recreate manually with original text"
}
```

---

## Risk Object

```json
"risk": {
  "level": "MEDIUM",
  "level_numeric": 2,
  "reasons": [
    "Match type change affects which queries trigger the keyword",
    "EXACT is more restrictive than PHRASE"
  ],
  "mitigations": [
    "Precondition verifies current match type before change",
    "Rollback restores PHRASE if needed"
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `level` | `enum` | `"LOW"`, `"MEDIUM"`, `"HIGH"` |
| `level_numeric` | `integer` | 1, 2, or 3 for comparisons |
| `reasons` | `array` | Why this risk level was assigned |
| `mitigations` | `array` | What safeguards are in place |

---

## Approvals Object

Tracks plan-level and operation-level approvals.

```json
{
  "approvals": {
    "plan_approved": false,
    "approved_by": null,
    "approved_at": null,
    "approval_notes": null,
    "operations_requiring_approval": ["op-004", "op-006"],
    "operation_approvals": {
      "op-004": {
        "approved": false,
        "approved_by": null,
        "approved_at": null,
        "notes": null
      },
      "op-006": {
        "approved": false,
        "approved_by": null,
        "approved_at": null,
        "notes": null
      }
    }
  }
}
```

### Approval Enforcement

1. If `mode == "APPLY"`, then `approvals.plan_approved` MUST be `true`.
2. For each `op_id` in `operations_requiring_approval`, the corresponding entry in `operation_approvals` must have `approved: true`.
3. `approved_by` should be a user identifier or "AUTO" for automated approvals.
4. `approved_at` should be an ISO8601 timestamp.

---

## Integrity Object

Optional hashes and checksums for verification.

```json
{
  "integrity": {
    "snapshot_manifest_hash": "sha256:abc123...",
    "plan_operations_hash": "sha256:def456...",
    "generated_by": "plan_changes.py",
    "generator_version": "C2.0"
  }
}
```

---

## Validation Rules

### Plan-Level Validation
1. `plan_id` must be unique and non-empty
2. `snapshot_id` must correspond to an existing snapshot directory
3. `snapshot_version` must match the snapshot's `_manifest.json`
4. `mode` must be `"DRY_RUN"` or `"APPLY"`
5. `guardrails.max_total_ops` must be >= `summary.total_operations`
6. All `op_type` values in operations must be valid enum values
7. No operation's `risk.level_numeric` may exceed the numeric value of `guardrails.max_risk_level`

### Operation-Level Validation
1. `op_id` must be unique within the plan
2. `op_type` must be a recognized operation type
3. `entity_ref` must follow the canonical format `<platform>.<entity_type>:<entity_id>`
4. `entity.entity_id` must match the ID in `entity_ref`
5. `before` and `after` must have at least one differing field (no no-op changes)
6. `preconditions` array must not be empty
7. All preconditions must have valid `op` operators
8. `risk.level` must be `"LOW"`, `"MEDIUM"`, or `"HIGH"`
9. `risk.level_numeric` must match `level` (1=LOW, 2=MEDIUM, 3=HIGH)
10. `evidence` array must have at least one entry with valid `snapshot_path`
11. `rollback.type` must be a valid rollback type

### Guardrail Enforcement (at apply time)
1. Total operations must not exceed `max_total_ops`
2. Operations per type must not exceed `max_ops_by_type` limits
3. If `forbid_budget_changes` is true, reject any `ADS_UPDATE_BUDGET` operations
4. If `forbid_campaign_pause` is true, reject any status change to PAUSED
5. If `forbid_broad_match` is true, reject any operation creating BROAD match
6. If `forbid_manufacturer_brand_negatives` is true, reject negatives containing manufacturer brands
7. If `allowlist_campaign_ids` is set, only those campaigns can be modified
8. If campaign is in `blocklist_campaign_ids`, reject all operations on it
9. Text edits must not exceed `max_text_edit_chars` in total character changes
10. Operations in `require_manual_approval_for_types` must have `approved: true`
11. If `require_precondition_match` is true, verify all preconditions before executing
12. If `abort_on_missing_entity` is true, fail if entity no longer exists

---

## Complete Operation Example

```json
{
  "op_id": "op-002",
  "op_type": "ADS_SET_KEYWORD_MATCH_TYPE",
  "entity_ref": "ads.keyword:701234567890",
  "entity": {
    "platform": "GOOGLE_ADS",
    "entity_type": "KEYWORD",
    "entity_id": "701234567890",
    "entity_name": "buy comfort direct",
    "parent_refs": [
      "ads.customer:9256598060",
      "ads.campaign:20958985895",
      "ads.ad_group:154321098765"
    ]
  },
  "intent": "Migrate high-performing brand keyword from PHRASE to EXACT match for tighter control",
  "before": {
    "text": "buy comfort direct",
    "match_type": "PHRASE",
    "status": "ENABLED"
  },
  "after": {
    "text": "buy comfort direct",
    "match_type": "EXACT",
    "status": "ENABLED"
  },
  "preconditions": [
    {
      "path": "match_type",
      "op": "EQUALS",
      "value": "PHRASE",
      "description": "Keyword must still be PHRASE match"
    },
    {
      "path": "status",
      "op": "EQUALS",
      "value": "ENABLED",
      "description": "Keyword must be enabled"
    },
    {
      "path": "campaign.bidding_strategy",
      "op": "EQUALS",
      "value": "MANUAL_CPC",
      "description": "Campaign must use Manual CPC bidding"
    }
  ],
  "rollback": {
    "type": "RESTORE_BEFORE",
    "data": {
      "match_type": "PHRASE"
    },
    "notes": "Revert match type from EXACT back to PHRASE"
  },
  "risk": {
    "level": "MEDIUM",
    "level_numeric": 2,
    "reasons": [
      "Match type change affects which queries trigger the keyword",
      "EXACT is more restrictive than PHRASE"
    ],
    "mitigations": [
      "Precondition verifies current match type",
      "Rollback restores PHRASE if needed"
    ]
  },
  "evidence": [
    {
      "snapshot_path": "normalized/ads/keywords.json",
      "key": "id",
      "value": "701234567890",
      "field_path": "records[0]",
      "note": "Branded keyword identified for exact match migration"
    }
  ],
  "evidence_query": "keywords WHERE campaign_id='20958985895' AND text CONTAINS 'buy comfort' AND match_type='PHRASE'",
  "created_from_rule": "rule:exact_match_migration:high_volume_brand_term",
  "approved": false,
  "approval_notes": null
}
```

---

## Execution Flow (Preview for C2/C3)

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. PLAN GENERATION (plan_changes.py)                                │
│    - Read snapshot data                                             │
│    - Apply rules to identify needed changes                         │
│    - Generate proposed_changes.json with mode: DRY_RUN              │
│    - Output to plans/runs/<plan_id>.json                            │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 2. HUMAN REVIEW                                                     │
│    - Review operations, intents, risk levels                        │
│    - Approve individual high-risk operations                        │
│    - Set plan_approved: true                                        │
│    - Change mode: "APPLY" when ready                                │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 3. APPLY CHANGES (apply_changes.py)                                 │
│    - Validate plan against guardrails                               │
│    - Check all preconditions against LIVE state                     │
│    - Execute operations in order                                    │
│    - Record results in execution log                                │
│    - Output execution_report.json                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| C1.0 | 2026-01-16 | Initial schema definition |
| C1.1 | 2026-01-16 | Added entity_ref canonical format, machine-parseable precondition DSL, resolvable evidence pointers, deterministic rollback types, plan_context, additional guardrails, risk level enforcement rules |
