#!/usr/bin/env python3
"""
Review Pack Builder - Deterministic + Optional LLM Advisory

Generates a comprehensive review pack for proposed plans.

CRITICAL: This is READ-ONLY. No execution authority.
"""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.judge.llm_judge import run_llm_judge


# Operation type risk categorization (based on apply engine SUPPORTED_OP_TYPES)
# These match the actual op_type values from generated plans

# High-risk: Structural changes, removals, large-scale impacts
HIGH_RISK_OPS = {
    "ADS_SET_PMAX_BRAND_EXCLUSIONS",  # Affects PMax reach/queries
    "ADS_UPDATE_BID_STRATEGY",         # Changes bidding strategy
    "ADS_UPDATE_BUDGET",               # Budget changes
    "ADS_REMOVE_ASSET",                # Asset removal
    "MERCHANT_EXCLUDE_PRODUCT",        # Product exclusions
    "ADS_SET_KEYWORD_STATUS",          # Pause/enable keywords
}

# Medium-risk: Targeting/filtering changes with moderate impact
MEDIUM_RISK_OPS = {
    "ADS_ADD_NEGATIVE_KEYWORD",       # May block desired traffic
    "ADS_REMOVE_NEGATIVE_KEYWORD",    # May allow unwanted traffic
    "ADS_UPDATE_ASSET_TEXT",          # Ad copy changes
    "ADS_SET_KEYWORD_MATCH_TYPE",     # Match type changes
}

# Low-risk: Minimal impact or observational
LOW_RISK_OPS = set()  # No explicitly low-risk ops currently supported

# All known supported op types (from apply engine)
SUPPORTED_OP_TYPES = HIGH_RISK_OPS | MEDIUM_RISK_OPS


def build_review_pack(plan_path: str, snapshot_path: str, report_path: Optional[str] = None) -> dict:
    """
    Build comprehensive review pack for a proposed plan.

    Args:
        plan_path: Path to plan JSON
        snapshot_path: Path to snapshot directory
        report_path: Optional path to report JSON

    Returns:
        Review pack dict with deterministic checks + optional LLM advisory
    """
    plan_path = Path(plan_path)
    snapshot_path = Path(snapshot_path)
    report_path = Path(report_path) if report_path else None

    timestamp = datetime.now(timezone.utc)

    # Initialize review pack
    review_pack = {
        "version": "B3.0",
        "generated_at": timestamp.isoformat(),
        "plan_id": plan_path.stem,
        "snapshot_id": snapshot_path.name,
        "plan_path": str(plan_path),
        "snapshot_path": str(snapshot_path),
        "deterministic_checks": {},
        "hitl_checklist": [],
        "llm_advisory": None
    }

    # Load plan
    try:
        with open(plan_path) as f:
            plan_data = json.load(f)
    except Exception as e:
        review_pack["error"] = f"Failed to load plan: {e}"
        return review_pack

    # Load snapshot manifest
    manifest_path = snapshot_path / "_manifest.json"
    try:
        with open(manifest_path) as f:
            manifest_data = json.load(f)
    except Exception as e:
        manifest_data = {"error": str(e)}

    # Load report (optional)
    report_data = None
    if report_path and report_path.exists():
        try:
            with open(report_path) as f:
                report_data = json.load(f)
        except Exception:
            pass

    # Run deterministic checks
    review_pack["deterministic_checks"] = _run_deterministic_checks(
        plan_data, manifest_data, report_data
    )

    # Generate HITL checklist (deterministic)
    review_pack["hitl_checklist"] = _generate_hitl_checklist(
        plan_data, review_pack["deterministic_checks"]
    )

    # Run LLM judge (optional, best-effort)
    try:
        llm_result = run_llm_judge(str(plan_path), str(snapshot_path))
        if llm_result:
            review_pack["llm_advisory"] = llm_result
    except Exception as e:
        review_pack["llm_advisory"] = {
            "error": str(e),
            "advisory_only": True,
            "notes": ["LLM judge failed (non-blocking)"]
        }

    return review_pack


def _run_deterministic_checks(plan_data: dict, manifest_data: dict, report_data: Optional[dict]) -> dict:
    """
    Run deterministic checks (pure Python, no LLM).

    These are hard-coded risk heuristics based on actual plan schema.
    """
    checks = {
        "plan_metadata": {},
        "operation_summary": {},
        "risk_flags": [],
        "operation_evidence": [],
        "snapshot_provenance": {},
        "plan_risk_summary": {}
    }

    # Extract plan metadata (using correct field names from schema)
    checks["plan_metadata"] = {
        "plan_id": plan_data.get("plan_id", "unknown"),
        "plan_version": plan_data.get("plan_version", "unknown"),
        "created_utc": plan_data.get("created_utc", "unknown"),
        "mode": plan_data.get("mode", "unknown"),
        "snapshot_id": plan_data.get("snapshot_id", "unknown")
    }

    # Use plan's own summary if available (more accurate)
    operations = plan_data.get("operations", [])
    plan_summary = plan_data.get("summary", {})

    if plan_summary and "operations_by_type" in plan_summary:
        # Use plan's pre-computed summary
        op_types_dict = plan_summary["operations_by_type"]
        op_types = Counter(op_types_dict)
    else:
        # Fallback: extract from operations (FIX: use "op_type" not "operation_type")
        op_types = Counter(op.get("op_type", "UNKNOWN") for op in operations)

    checks["operation_summary"] = {
        "total": len(operations),
        "by_type": dict(op_types),
        "top_types": op_types.most_common(10)
    }

    # Use plan's risk assessment if available
    if plan_summary:
        checks["plan_risk_summary"] = {
            "risk_score": plan_summary.get("risk_score", "UNKNOWN"),
            "operations_by_risk": plan_summary.get("operations_by_risk", {}),
            "requires_approval": plan_summary.get("requires_approval", False),
            "risk_summary": plan_summary.get("risk_summary", "")
        }

    # Deterministic risk flags
    for op_type, count in op_types.items():
        # CRITICAL: Unknown op types are HIGH risk
        if op_type == "UNKNOWN" or op_type not in SUPPORTED_OP_TYPES:
            checks["risk_flags"].append({
                "severity": "HIGH",
                "type": op_type,
                "count": count,
                "reason": f"UNKNOWN_OP_TYPE: '{op_type}' not in supported types",
                "detail": f"Supported: {', '.join(sorted(SUPPORTED_OP_TYPES))}"
            })
        elif op_type in HIGH_RISK_OPS:
            checks["risk_flags"].append({
                "severity": "HIGH",
                "type": op_type,
                "count": count,
                "reason": f"High-risk operation type: {op_type}"
            })
        elif op_type in MEDIUM_RISK_OPS:
            if count > 10:  # Medium risk becomes high if volume is large
                checks["risk_flags"].append({
                    "severity": "HIGH",
                    "type": op_type,
                    "count": count,
                    "reason": f"High volume of medium-risk ops: {count} {op_type}"
                })
            else:
                checks["risk_flags"].append({
                    "severity": "MEDIUM",
                    "type": op_type,
                    "count": count,
                    "reason": f"Medium-risk operation type: {op_type}"
                })

    # Extract evidence from operations
    for op in operations:
        op_id = op.get("op_id", "unknown")
        op_type = op.get("op_type", "UNKNOWN")
        entity = op.get("entity", {})

        evidence_item = {
            "op_id": op_id,
            "op_type": op_type,
            "entity_ref": op.get("entity_ref"),
            "entity_type": entity.get("entity_type"),
            "entity_name": entity.get("entity_name"),
            "campaign_type": entity.get("campaign_type"),
            "intent": op.get("intent", ""),
            "risk_level": op.get("risk", {}).get("level", "UNKNOWN")
        }

        # Extract op-specific details
        if op_type == "ADS_SET_PMAX_BRAND_EXCLUSIONS":
            params = op.get("params", {})
            after = op.get("after", {})
            evidence_item["campaign_id"] = params.get("campaign_id")
            evidence_item["brand_list_name"] = after.get("brand_list_name")
            evidence_item["brands_count"] = len(after.get("brands", []))
            evidence_item["brands"] = after.get("brands", [])

        checks["operation_evidence"].append(evidence_item)

    # Snapshot provenance
    checks["snapshot_provenance"] = {
        "snapshot_id": manifest_data.get("snapshot_id", "unknown"),
        "version": manifest_data.get("version", "unknown"),
        "timestamp": manifest_data.get("timestamp", "unknown"),
        "surfaces": list(manifest_data.get("surfaces_collected", {}).keys())
    }

    # Phase B3.2: Extract truth signals from report (if available)
    if report_data and "truth_signals_google_recommendations" in report_data:
        truth_signals = report_data["truth_signals_google_recommendations"]
        checks["truth_signals"] = {
            "available": True,
            "metadata": truth_signals.get("metadata", {}),
            "rsa_asset_coverage_count": len(truth_signals.get("rsa_asset_coverage", [])),
            "keyword_recommendations_count": len(truth_signals.get("keyword_recommendations", [])),
            "budget_recommendations_count": len(truth_signals.get("budget_recommendations", [])),
            "merchant_clarifiers_count": len(truth_signals.get("merchant_clarifiers", [])),
            "total_signals": sum(
                len(truth_signals.get(k, []))
                for k in ["rsa_asset_coverage", "keyword_recommendations", "budget_recommendations", "merchant_clarifiers"]
            )
        }
    else:
        checks["truth_signals"] = {
            "available": False,
            "note": "Truth signals not available in report. Run bin/truth_sweep and bin/report to populate."
        }

    return checks


def _generate_hitl_checklist(plan_data: dict, deterministic_checks: dict) -> list:
    """
    Generate Human-In-The-Loop checklist (deterministic).

    Returns list of checklist items for human review, tailored to operation types.
    """
    checklist = []

    # Always include these base checks
    checklist.append({
        "item": "Verify plan intent matches business objective",
        "category": "INTENT",
        "required": True
    })

    checklist.append({
        "item": "Review snapshot provenance and freshness",
        "category": "DATA",
        "required": True
    })

    # Add checks based on actual operation types (from plan schema)
    op_summary = deterministic_checks.get("operation_summary", {})
    op_types = set(op_summary.get("by_type", {}).keys())
    operation_evidence = deterministic_checks.get("operation_evidence", [])

    # PMax brand exclusions checks
    if "ADS_SET_PMAX_BRAND_EXCLUSIONS" in op_types:
        checklist.append({
            "item": "Confirm protected manufacturer brands (Rheem, Goodman, Solace, etc.) are NOT excluded",
            "category": "PMAX_BRAND_EXCLUSIONS",
            "required": True
        })

        checklist.append({
            "item": "Verify campaign_id matches intended PMax campaign",
            "category": "PMAX_BRAND_EXCLUSIONS",
            "required": True
        })

        # Extract brand count from evidence
        pmax_ops = [e for e in operation_evidence if e.get("op_type") == "ADS_SET_PMAX_BRAND_EXCLUSIONS"]
        if pmax_ops:
            brands_count = pmax_ops[0].get("brands_count", 0)
            checklist.append({
                "item": f"Review {brands_count} brand terms being excluded - ensure no critical terms blocked",
                "category": "PMAX_BRAND_EXCLUSIONS",
                "required": True
            })

    # Budget/bidding checks
    if "ADS_UPDATE_BUDGET" in op_types:
        checklist.append({
            "item": "Verify budget changes align with monthly spend targets and budget utilization constraints",
            "category": "BUDGET",
            "required": True
        })

    if "ADS_UPDATE_BID_STRATEGY" in op_types:
        checklist.append({
            "item": "Confirm bidding strategy changes won't disrupt Smart Bidding learning phase (requires 30-50 conversions)",
            "category": "BIDDING",
            "required": True
        })

        checklist.append({
            "item": "Review tROAS target changes and historical performance implications",
            "category": "BIDDING",
            "required": True
        })

    # Keyword checks
    if "ADS_SET_KEYWORD_STATUS" in op_types:
        checklist.append({
            "item": "Review paused/enabled keywords - ensure no unintended brand term blocks",
            "category": "KEYWORDS",
            "required": True
        })

    if "ADS_ADD_NEGATIVE_KEYWORD" in op_types:
        checklist.append({
            "item": "Ensure negative keywords won't block manufacturer brand traffic (protected terms)",
            "category": "KEYWORDS",
            "required": True
        })

        checklist.append({
            "item": "Verify negative keywords won't block high-converting search terms",
            "category": "KEYWORDS",
            "required": True
        })

    # Asset checks
    if "ADS_REMOVE_ASSET" in op_types or "ADS_UPDATE_ASSET_TEXT" in op_types:
        checklist.append({
            "item": "Review asset changes - confirm updated copy aligns with brand guidelines",
            "category": "ASSETS",
            "required": True
        })

    # Merchant Center checks
    if "MERCHANT_EXCLUDE_PRODUCT" in op_types:
        checklist.append({
            "item": "Verify product exclusions align with inventory/compliance issues",
            "category": "MERCHANT",
            "required": True
        })

    # Risk-based checks
    risk_flags = deterministic_checks.get("risk_flags", [])
    high_risk_flags = [f for f in risk_flags if f["severity"] == "HIGH"]
    unknown_ops = [f for f in risk_flags if "UNKNOWN_OP_TYPE" in f.get("reason", "")]

    if unknown_ops:
        checklist.append({
            "item": "CRITICAL: Unknown operation types detected - manual review REQUIRED before execution",
            "category": "UNKNOWN_OP",
            "required": True
        })

    if high_risk_flags:
        checklist.append({
            "item": f"HIGH RISK DETECTED ({len(high_risk_flags)} flags) - Double-check all operations before execution",
            "category": "RISK",
            "required": True
        })

    # Guardrail checks
    guardrails = plan_data.get("guardrails", {})
    if guardrails.get("require_manual_approval_for_types"):
        approval_types = guardrails["require_manual_approval_for_types"]
        matching_types = [t for t in approval_types if t in op_types]
        if matching_types:
            checklist.append({
                "item": f"Manual approval REQUIRED for: {', '.join(matching_types)}",
                "category": "APPROVAL",
                "required": True
            })

    # Always include safety check
    checklist.append({
        "item": "Confirm apply engine safeguards are enabled (max_ops, forbid flags, abort_on_error)",
        "category": "SAFETY",
        "required": True
    })

    return checklist


def write_review_pack(review_pack: dict, output_dir: Path) -> dict:
    """
    Write review pack to disk.

    Args:
        review_pack: Review pack dict
        output_dir: Output directory

    Returns:
        Dict with file paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON
    json_path = output_dir / "review_pack.json"
    with open(json_path, "w") as f:
        json.dump(review_pack, f, indent=2)

    # Write markdown summary (optional, deterministic only)
    md_path = output_dir / "review_pack.md"
    with open(md_path, "w") as f:
        f.write(_generate_markdown_summary(review_pack))

    return {
        "json": str(json_path),
        "markdown": str(md_path)
    }


def _generate_markdown_summary(review_pack: dict) -> str:
    """Generate deterministic markdown summary (no LLM prose)."""
    lines = []
    lines.append("# Plan Review Pack")
    lines.append("")
    lines.append(f"**Generated:** {review_pack['generated_at']}")
    lines.append(f"**Plan ID:** {review_pack['plan_id']}")
    lines.append(f"**Snapshot ID:** {review_pack['snapshot_id']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Deterministic checks
    lines.append("## Deterministic Checks")
    lines.append("")

    det_checks = review_pack.get("deterministic_checks", {})
    plan_meta = det_checks.get("plan_metadata", {})
    op_summary = det_checks.get("operation_summary", {})
    risk_flags = det_checks.get("risk_flags", [])

    lines.append("### Plan Metadata")
    lines.append("")
    lines.append(f"- Plan ID: {plan_meta.get('plan_id', 'unknown')}")
    lines.append(f"- Plan Version: {plan_meta.get('plan_version', 'unknown')}")
    lines.append(f"- Created: {plan_meta.get('created_utc', 'unknown')}")
    lines.append(f"- Mode: {plan_meta.get('mode', 'unknown')}")
    lines.append(f"- Total Operations: {plan_meta.get('total_operations', 0)}")
    lines.append("")

    # Plan risk summary (from planner)
    plan_risk = det_checks.get("plan_risk_summary", {})
    if plan_risk and plan_risk.get("risk_score"):
        lines.append("### Plan Risk Assessment (from Planner)")
        lines.append("")
        lines.append(f"- **Risk Score:** {plan_risk.get('risk_score', 'UNKNOWN')}")
        lines.append(f"- **Risk Summary:** {plan_risk.get('risk_summary', 'N/A')}")
        lines.append(f"- **Requires Approval:** {plan_risk.get('requires_approval', False)}")
        ops_by_risk = plan_risk.get("operations_by_risk", {})
        if ops_by_risk:
            lines.append(f"- **Operations by Risk:** LOW:{ops_by_risk.get('LOW', 0)}, MED:{ops_by_risk.get('MEDIUM', 0)}, HIGH:{ops_by_risk.get('HIGH', 0)}")
        lines.append("")

    lines.append("### Operation Summary")
    lines.append("")
    lines.append("| Operation Type | Count |")
    lines.append("|----------------|-------|")
    for op_type, count in op_summary.get("top_types", []):
        lines.append(f"| {op_type} | {count} |")
    lines.append("")

    # Operation evidence
    operation_evidence = det_checks.get("operation_evidence", [])
    if operation_evidence:
        lines.append("### Operation Evidence")
        lines.append("")
        for i, ev in enumerate(operation_evidence, 1):
            lines.append(f"**Operation {i}: {ev.get('op_type', 'UNKNOWN')}**")
            lines.append("")
            lines.append(f"- Op ID: `{ev.get('op_id', 'N/A')}`")
            lines.append(f"- Entity: {ev.get('entity_name', 'N/A')} ({ev.get('entity_type', 'N/A')})")
            if ev.get("campaign_type"):
                lines.append(f"- Campaign Type: {ev.get('campaign_type')}")
            lines.append(f"- Risk Level: **{ev.get('risk_level', 'UNKNOWN')}**")
            lines.append(f"- Intent: {ev.get('intent', 'N/A')}")

            # Op-specific details
            if ev.get('op_type') == 'ADS_SET_PMAX_BRAND_EXCLUSIONS':
                lines.append(f"- Campaign ID: `{ev.get('campaign_id', 'N/A')}`")
                lines.append(f"- Brand List: {ev.get('brand_list_name', 'N/A')}")
                lines.append(f"- Brands: {ev.get('brands_count', 0)} terms")
                brands = ev.get('brands', [])
                if brands:
                    lines.append(f"  - Terms: {', '.join(brands[:5])}")
                    if len(brands) > 5:
                        lines.append(f"  - (+ {len(brands) - 5} more)")

            lines.append("")

    # Risk flags
    if risk_flags:
        lines.append("### Risk Flags")
        lines.append("")
        lines.append("| Severity | Type | Count | Reason |")
        lines.append("|----------|------|-------|--------|")
        for flag in risk_flags:
            severity = flag["severity"]
            op_type = flag.get("type", "N/A")
            count = flag.get("count", 0)
            reason = flag["reason"]
            lines.append(f"| **{severity}** | {op_type} | {count} | {reason} |")
        lines.append("")

        # Show details for unknown ops
        unknown_flags = [f for f in risk_flags if "UNKNOWN_OP_TYPE" in f.get("reason", "")]
        if unknown_flags:
            lines.append("**CRITICAL: Unknown Operation Types Detected**")
            lines.append("")
            for flag in unknown_flags:
                lines.append(f"- {flag.get('detail', 'No details')}")
            lines.append("")
    else:
        lines.append("### Risk Flags")
        lines.append("")
        lines.append("No risk flags detected.")
        lines.append("")

    # Phase B3.2: Truth signals summary
    truth_signals = det_checks.get("truth_signals", {})
    if truth_signals.get("available"):
        lines.append("### Truth Signals (Google Recommendations)")
        lines.append("")
        lines.append("| Signal Type | Count |")
        lines.append("|-------------|-------|")
        lines.append(f"| RSA Asset Coverage Issues | {truth_signals.get('rsa_asset_coverage_count', 0)} |")
        lines.append(f"| Keyword Recommendations | {truth_signals.get('keyword_recommendations_count', 0)} |")
        lines.append(f"| Budget Recommendations | {truth_signals.get('budget_recommendations_count', 0)} |")
        lines.append(f"| Merchant Clarifiers | {truth_signals.get('merchant_clarifiers_count', 0)} |")
        lines.append(f"| **Total Signals** | **{truth_signals.get('total_signals', 0)}** |")
        lines.append("")

        metadata = truth_signals.get("metadata", {})
        if metadata.get("truth_sweep_available"):
            lines.append(f"Truth sweep data: `{metadata.get('truth_sweep_path', 'N/A')}`")
        else:
            lines.append("Truth sweep data: Not available")
        lines.append("")
    else:
        lines.append("### Truth Signals (Google Recommendations)")
        lines.append("")
        lines.append("Truth signals not available. Run `bin/truth_sweep` and `bin/report` to populate.")
        lines.append("")

    # HITL Checklist
    lines.append("---")
    lines.append("")
    lines.append("## Human Review Checklist")
    lines.append("")

    hitl_checklist = review_pack.get("hitl_checklist", [])
    for i, item in enumerate(hitl_checklist, 1):
        required = " **[REQUIRED]**" if item.get("required") else ""
        lines.append(f"{i}. [{item['category']}] {item['item']}{required}")
    lines.append("")

    # LLM Advisory (if present)
    lines.append("---")
    lines.append("")
    lines.append("## LLM Advisory (Optional)")
    lines.append("")

    llm_advisory = review_pack.get("llm_advisory")
    if llm_advisory and llm_advisory.get("llm_enabled"):
        risk_assessment = llm_advisory.get("risk_assessment", {})
        lines.append(f"**Overall Risk:** {risk_assessment.get('overall_risk', 'UNKNOWN')}")
        lines.append("")

        risk_reasons = risk_assessment.get("risk_reasons", [])
        if risk_reasons:
            lines.append("**Risk Reasons:**")
            for reason in risk_reasons:
                lines.append(f"- {reason}")
            lines.append("")

        # Embed full JSON for transparency
        lines.append("**Full LLM Response (JSON):**")
        lines.append("```json")
        lines.append(json.dumps(llm_advisory, indent=2))
        lines.append("```")
        lines.append("")
    else:
        lines.append("LLM advisory disabled or unavailable.")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*This review pack is advisory only and has no execution authority.*")
    lines.append("")

    return "\n".join(lines)
