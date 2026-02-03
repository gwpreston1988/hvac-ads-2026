#!/usr/bin/env python3
"""
CLI for Review Pack Generation

Usage:
  bin/review_pack --latest-plan --latest-snapshot
  bin/review_pack --plan <path> --snapshot <path>
  bin/review_pack --plan <path> --snapshot <path> --report <path>
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.judge.review_pack import build_review_pack, write_review_pack


def find_latest_plan(plans_dir: Path) -> Path:
    """Find most recent plan file."""
    # Check both plans/ and plans/runs/ directories
    plan_files = []
    plan_files.extend(plans_dir.glob("proposed_changes_*.json"))
    plan_files.extend((plans_dir / "runs").glob("proposed_changes_*.json"))

    if not plan_files:
        raise FileNotFoundError(f"No plan files found in {plans_dir} or {plans_dir}/runs")
    return max(plan_files, key=lambda p: p.stat().st_mtime)


def find_latest_snapshot(snapshots_dir: Path) -> Path:
    """Find most recent snapshot directory."""
    snapshot_dirs = [d for d in snapshots_dir.iterdir() if d.is_dir()]
    if not snapshot_dirs:
        raise FileNotFoundError(f"No snapshot directories found in {snapshots_dir}")
    return max(snapshot_dirs, key=lambda d: d.stat().st_mtime)


def find_latest_report(reports_dir: Path) -> Path:
    """Find most recent report JSON (prioritize latest.json)."""
    # Check for latest.json first
    latest_json = reports_dir / "latest.json"
    if latest_json.exists():
        return latest_json

    # Fall back to BCD_Report_*.json pattern
    report_files = list(reports_dir.glob("BCD_Report_*.json"))
    if not report_files:
        return None
    return max(report_files, key=lambda p: p.stat().st_mtime)


def main():
    parser = argparse.ArgumentParser(
        description="Generate advisory review pack for proposed plan"
    )
    parser.add_argument("--plan", help="Path to plan JSON file")
    parser.add_argument("--snapshot", help="Path to snapshot directory")
    parser.add_argument("--report", help="Path to report JSON (optional)")
    parser.add_argument(
        "--latest-plan",
        action="store_true",
        help="Use most recent plan from plans/ directory"
    )
    parser.add_argument(
        "--latest-snapshot",
        action="store_true",
        help="Use most recent snapshot from snapshots/ directory"
    )

    args = parser.parse_args()

    # Load environment
    load_dotenv()

    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent

    print("=" * 70)
    print("REVIEW PACK GENERATOR - Advisory Plan Review")
    print("=" * 70)
    print()

    # Determine plan path
    if args.latest_plan:
        plans_dir = project_root / "plans"
        try:
            plan_path = find_latest_plan(plans_dir)
            print(f"Using latest plan: {plan_path.name}")
        except FileNotFoundError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
    elif args.plan:
        plan_path = Path(args.plan)
        if not plan_path.exists():
            print(f"ERROR: Plan file not found: {plan_path}")
            sys.exit(1)
    else:
        print("ERROR: Must specify --plan or --latest-plan")
        parser.print_help()
        sys.exit(1)

    # Determine snapshot path
    if args.latest_snapshot:
        snapshots_dir = project_root / "snapshots"
        try:
            snapshot_path = find_latest_snapshot(snapshots_dir)
            print(f"Using latest snapshot: {snapshot_path.name}")
        except FileNotFoundError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
    elif args.snapshot:
        snapshot_path = Path(args.snapshot)
        if not snapshot_path.exists():
            print(f"ERROR: Snapshot directory not found: {snapshot_path}")
            sys.exit(1)
    else:
        print("ERROR: Must specify --snapshot or --latest-snapshot")
        parser.print_help()
        sys.exit(1)

    # Determine report path (optional)
    report_path = None
    if args.report:
        report_path = Path(args.report)
        if not report_path.exists():
            print(f"WARNING: Report file not found: {report_path}")
            report_path = None
    else:
        # Try to find latest report
        reports_dir = project_root / "reports"
        if reports_dir.exists():
            report_path = find_latest_report(reports_dir)
            if report_path:
                print(f"Using latest report: {report_path.name}")

    print()
    print("-" * 70)
    print("Building review pack...")
    print("-" * 70)
    print()

    # Build review pack
    try:
        review_pack = build_review_pack(
            plan_path=str(plan_path),
            snapshot_path=str(snapshot_path),
            report_path=str(report_path) if report_path else None
        )
    except Exception as e:
        print(f"ERROR: Failed to build review pack: {e}")
        sys.exit(1)

    # Create output directory
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    output_dir = project_root / "diag" / "review_packs" / timestamp

    # Write review pack
    try:
        file_paths = write_review_pack(review_pack, output_dir)
    except Exception as e:
        print(f"ERROR: Failed to write review pack: {e}")
        sys.exit(1)

    print("=" * 70)
    print("REVIEW PACK COMPLETE")
    print("=" * 70)
    print()
    print(f"Output directory: {output_dir}")
    print()
    print("Files generated:")
    print(f"  - {file_paths['json']}")
    print(f"  - {file_paths['markdown']}")
    print()

    # Display summary
    det_checks = review_pack.get("deterministic_checks", {})
    op_summary = det_checks.get("operation_summary", {})
    risk_flags = det_checks.get("risk_flags", [])

    print("Summary:")
    print(f"  Total Operations: {op_summary.get('total', 0)}")
    print(f"  Risk Flags: {len(risk_flags)}")
    if risk_flags:
        high_risk = [f for f in risk_flags if f["severity"] == "HIGH"]
        if high_risk:
            print(f"    ⚠ HIGH RISK: {len(high_risk)} flags")

    llm_advisory = review_pack.get("llm_advisory")
    if llm_advisory and llm_advisory.get("llm_enabled"):
        risk_level = llm_advisory.get("risk_assessment", {}).get("overall_risk", "UNKNOWN")
        print(f"  LLM Risk Assessment: {risk_level}")
    else:
        print("  LLM Advisory: Disabled")

    print()
    print("Next steps:")
    print("  1. Review the markdown summary:")
    print(f"     cat {file_paths['markdown']}")
    print("  2. Complete HITL checklist before execution")
    print("  3. Use apply engine with approval guards")
    print()


if __name__ == "__main__":
    main()
