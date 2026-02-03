#!/usr/bin/env python3
"""
LLM Judge - Advisory Risk Assessment (READ-ONLY)

This module calls Claude Sonnet to provide advisory commentary on proposed plans.

CRITICAL: This is ADVISORY ONLY. The LLM has NO execution authority.
"""

import json
import os
from pathlib import Path
from typing import Optional

# Feature flag
LLM_JUDGE_ENABLED = os.getenv("LLM_JUDGE_ENABLED", "false").lower() == "true"
LLM_JUDGE_MODEL = os.getenv("LLM_JUDGE_MODEL", "claude-3-5-sonnet-20241022")


def run_llm_judge(plan_path: str, snapshot_path: str) -> dict:
    """
    Run LLM advisory judge on a proposed plan.

    Args:
        plan_path: Path to plan JSON file
        snapshot_path: Path to snapshot directory

    Returns:
        Advisory JSON dict (best-effort, never blocks execution)
    """
    plan_path = Path(plan_path)
    snapshot_path = Path(snapshot_path)

    # Base response structure (returned even if LLM disabled/fails)
    response = {
        "version": "J1",
        "plan_id": plan_path.stem,
        "snapshot_id": snapshot_path.name,
        "advisory_only": True,
        "llm_enabled": LLM_JUDGE_ENABLED,
        "risk_assessment": {
            "overall_risk": "UNKNOWN",
            "risk_reasons": []
        },
        "sanity_checks": [],
        "missing_evidence": [],
        "recommended_human_checks": [],
        "notes": []
    }

    # If LLM disabled, return early with flag
    if not LLM_JUDGE_ENABLED:
        response["notes"].append("LLM judge disabled (LLM_JUDGE_ENABLED=false)")
        return response

    # Load plan
    try:
        with open(plan_path) as f:
            plan_data = json.load(f)
    except Exception as e:
        response["notes"].append(f"Failed to load plan: {e}")
        return response

    # Load snapshot manifest
    manifest_path = snapshot_path / "_manifest.json"
    try:
        with open(manifest_path) as f:
            manifest_data = json.load(f)
    except Exception as e:
        response["notes"].append(f"Failed to load snapshot manifest: {e}")
        manifest_data = {}

    # Load snapshot index (optional)
    index_path = snapshot_path / "_index.json"
    index_data = {}
    if index_path.exists():
        try:
            with open(index_path) as f:
                index_data = json.load(f)
        except Exception:
            pass

    # Build evidence bundle for LLM
    evidence = _build_evidence_bundle(plan_data, manifest_data, index_data)

    # Call LLM (best-effort)
    try:
        llm_response = _call_claude_judge(evidence)
        if llm_response:
            response.update(llm_response)
    except Exception as e:
        response["notes"].append(f"LLM call failed (non-blocking): {e}")

    return response


def _build_evidence_bundle(plan_data: dict, manifest_data: dict, index_data: dict) -> dict:
    """Build evidence bundle from plan + snapshot for LLM."""
    # Extract plan operations summary
    ops_by_type = {}
    total_ops = 0

    for op in plan_data.get("operations", []):
        op_type = op.get("operation_type", "UNKNOWN")
        if op_type not in ops_by_type:
            ops_by_type[op_type] = 0
        ops_by_type[op_type] += 1
        total_ops += 1

    # Extract snapshot summary
    snapshot_summary = {
        "id": manifest_data.get("snapshot_id", "unknown"),
        "version": manifest_data.get("version", "unknown"),
        "timestamp": manifest_data.get("timestamp", "unknown"),
        "surfaces": list(manifest_data.get("surfaces_collected", {}).keys())
    }

    # Extract entity counts from index
    entity_counts = {}
    if index_data:
        entity_counts = {
            "campaigns": len(index_data.get("campaigns", [])),
            "ad_groups": len(index_data.get("ad_groups", [])),
            "keywords": len(index_data.get("keywords", []))
        }

    return {
        "plan_summary": {
            "plan_id": plan_data.get("plan_id", "unknown"),
            "total_operations": total_ops,
            "operations_by_type": ops_by_type
        },
        "snapshot_summary": snapshot_summary,
        "entity_counts": entity_counts
    }


def _call_claude_judge(evidence: dict) -> Optional[dict]:
    """
    Call Claude Sonnet for advisory assessment.

    Returns None if call fails (best-effort).
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    # Build prompt
    prompt = _build_judge_prompt(evidence)

    # Call Claude API
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model=LLM_JUDGE_MODEL,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Parse JSON response
        response_text = message.content[0].text
        return json.loads(response_text)

    except Exception:
        # Best-effort: if LLM fails, return None
        return None


def _build_judge_prompt(evidence: dict) -> str:
    """Build prompt for Claude judge."""
    plan_summary = evidence["plan_summary"]
    snapshot_summary = evidence["snapshot_summary"]
    entity_counts = evidence["entity_counts"]

    prompt = f"""You are an advisory judge reviewing a proposed Google Ads plan. You have NO execution authority - you are advisory only.

EVIDENCE BUNDLE:

Plan Summary:
- Plan ID: {plan_summary['plan_id']}
- Total Operations: {plan_summary['total_operations']}
- Operations by Type: {json.dumps(plan_summary['operations_by_type'], indent=2)}

Snapshot Context:
- Snapshot ID: {snapshot_summary['id']}
- Version: {snapshot_summary['version']}
- Timestamp: {snapshot_summary['timestamp']}
- Surfaces: {', '.join(snapshot_summary['surfaces'])}

Entity Counts:
{json.dumps(entity_counts, indent=2)}

TASK:

Provide an advisory risk assessment. Consider:
1. Overall risk level (LOW/MEDIUM/HIGH) based on operation types and volume
2. Sanity checks (do the ops match expected patterns?)
3. Missing evidence (what data would help validate this plan?)
4. Recommended human checks before execution

CRITICAL: Return ONLY valid JSON in this exact structure:

{{
  "risk_assessment": {{
    "overall_risk": "LOW|MEDIUM|HIGH",
    "risk_reasons": ["reason 1", "reason 2"]
  }},
  "sanity_checks": [
    {{"check": "check_name", "status": "PASS|WARN|FAIL", "evidence": "explanation"}}
  ],
  "missing_evidence": ["missing_item_1", "missing_item_2"],
  "recommended_human_checks": ["check_1", "check_2"],
  "notes": ["note_1", "note_2"]
}}

NO PROSE. ONLY JSON.
"""
    return prompt
