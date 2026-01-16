#!/usr/bin/env python3

################################################################################
# LEGACY CODE - DO NOT USE
################################################################################
# This script is NOT part of the baseline pipeline. It has been quarantined in
# the legacy/ folder and should not be used for production operations.
#
# The baseline pipeline uses ONLY:
#   - core/dump/dump_state.py     (Phase A: live reads)
#   - core/report/generate_report.py  (Phase B: snapshot-only reports)
#   - core/plan/plan_changes.py   (Phase C: snapshot-only planning)
#   - core/apply/apply_changes.py (Phase C: live writes - with approval)
#
# If you need functionality from this script, consider:
#   1. Extracting it into a new core/ module with proper guardrails
#   2. Using it as reference for implementing new pipeline features
#   3. Consulting the team before running any legacy code
#
# Last quarantine date: 2026-01-16
################################################################################


"""
BigCommerce Rheem Product SEO State Dump

Wrapper script for bc_brand_state_dump.py with --brand rheem.

USAGE:
    python seo/audit/bc_rheem_state_dump.py
    python seo/audit/bc_rheem_state_dump.py --dry-run

OUTPUTS:
    - reports/seo/rheem/state/rheem_seo_state_{timestamp}.json

READ-ONLY: This script does NOT modify any data in BigCommerce.
"""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    generic_script = script_dir / "bc_brand_state_dump.py"

    # Pass through any additional arguments (e.g., --dry-run)
    cmd = [sys.executable, str(generic_script), "--brand", "rheem"] + sys.argv[1:]
    sys.exit(subprocess.call(cmd))
