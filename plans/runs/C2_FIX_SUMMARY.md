# Phase C2 Fix Summary

**Date:** 2026-01-16
**Fixed by:** plan_changes.py update
**Snapshot:** 2026-01-15T202326Z

## Problem

The previous plan (`proposed_changes_2026-01-15T202326Z_2026-01-16T154728Z.json`) incorrectly proposed **pausing 3 brand keywords** in the Branded campaign:

- `buy comfort direct`
- `buycomfortdirect`
- `buycomfortdirect.com`

These are **core BCD brand terms** and should NEVER be paused.

## Root Cause

**Key mismatch in config loading** (`plan_changes.py` lines 1094-1101):

```python
# BROKEN CODE - looked for wrong keys
brand_terms = brand_config.get("primary", []) + brand_config.get("variants", [])
```

But `configs/brand_terms.json` uses the key `"brand_terms"`:

```json
{
  "brand_terms": ["rheem", "goodman", "solace", "bcd", "buy comfort direct", ...],
  "brand_variants": {...}
}
```

**Result:** Brand terms list loaded as empty (0 terms), causing Rule S2 to classify all keywords as "non-brand" and propose pausing them.

## Fixes Applied

### 1. Fixed brand_terms config loading

```python
# Extract brand terms from correct key - supports both "brand_terms" and legacy "primary"/"variants"
brand_terms = []
if "brand_terms" in brand_config:
    brand_terms = brand_config.get("brand_terms", [])
elif "primary" in brand_config:
    brand_terms = brand_config.get("primary", []) + brand_config.get("variants", [])

# Also add brand variants from brand_variants if present
brand_variants = brand_config.get("brand_variants", {})
for variant_list in brand_variants.values():
    brand_terms.extend(variant_list)
```

### 2. Added ABORT on missing/empty brand_terms

The planner now **refuses to run** if `configs/brand_terms.json` is missing or contains no brand terms:

```
======================================================================
ABORT: Empty brand_terms configuration
======================================================================
Config file exists but contains no brand terms: ...

The planner requires a non-empty 'brand_terms' array. Without this,
the planner cannot distinguish brand keywords from non-brand keywords
and may incorrectly propose pausing critical brand terms.
```

### 3. Added safeguard in Rule S2

Rule S2 now:
- Double-checks `brand_terms` is non-empty before processing
- Logs which brand keywords were **protected** (not paused)
- Returns early with ERROR if `brand_terms` is empty

### 4. Added guardrail enforcement for manufacturer brand negatives

`add_operation()` now explicitly blocks any `ADS_ADD_NEGATIVE_KEYWORD` operation that would add a manufacturer brand (Rheem, Goodman, Solace, etc.) as a negative keyword:

```python
if op.get("op_type") == "ADS_ADD_NEGATIVE_KEYWORD":
    kw_text = op.get("after", {}).get("text", "")
    if contains_manufacturer_brand(kw_text):
        # BLOCKED - do not add this operation
        return
```

## Results

### Before Fix (WRONG)
```
Total operations: 3
Operations by type:
  ADS_SET_KEYWORD_STATUS: 3   <- WRONG: Pausing brand keywords!
Risk score: MEDIUM
```

### After Fix (CORRECT)
```
Total operations: 0
Findings:
  [INFO] Protected 3 brand keyword(s) in Branded campaign (not proposed for pause):
         buy comfort direct, buycomfortdirect, buycomfortdirect.com
  [INFO] 12 disapproved products found; 0 in discontinued list
Risk score: LOW
```

## Verification

The corrected plan now shows:
- **0 operations** for Branded keywords (correct - no pauses)
- **12 brand terms loaded** from config (vs 0 before)
- **INFO finding** explicitly confirms brand keywords were protected

## Files Changed

- `plans/plan_changes.py` - Fixed brand_terms loading, added abort checks, added safeguards

## Lesson Learned

**Config loading must be validated and fail-fast.** Silent failures (empty list instead of error) can cause the planner to generate dangerous operations. Always:

1. Validate required config files exist
2. Validate required fields are non-empty
3. Abort with explicit error message rather than proceeding with defaults
4. Log what was loaded so issues are immediately visible
