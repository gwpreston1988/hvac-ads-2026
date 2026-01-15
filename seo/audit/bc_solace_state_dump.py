#!/usr/bin/env python3
"""
BigCommerce Solace Product SEO State Dump

Wrapper script for bc_brand_state_dump.py with --brand solace.

USAGE:
    python seo/audit/bc_solace_state_dump.py
    python seo/audit/bc_solace_state_dump.py --dry-run

OUTPUTS:
    - reports/seo/solace/state/solace_seo_state_{timestamp}.json

READ-ONLY: This script does NOT modify any data in BigCommerce.
"""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    generic_script = script_dir / "bc_brand_state_dump.py"

    # Pass through any additional arguments (e.g., --dry-run)
    cmd = [sys.executable, str(generic_script), "--brand", "solace"] + sys.argv[1:]
    sys.exit(subprocess.call(cmd))
