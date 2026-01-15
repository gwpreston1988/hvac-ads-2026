#!/usr/bin/env python3
"""
BigCommerce Goodman Product SEO State Dump

Wrapper script for bc_brand_state_dump.py with --brand goodman.

USAGE:
    python seo/audit/bc_goodman_state_dump.py
    python seo/audit/bc_goodman_state_dump.py --dry-run

OUTPUTS:
    - reports/seo/goodman/state/goodman_seo_state_{timestamp}.json

READ-ONLY: This script does NOT modify any data in BigCommerce.
"""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    generic_script = script_dir / "bc_brand_state_dump.py"

    # Pass through any additional arguments (e.g., --dry-run)
    cmd = [sys.executable, str(generic_script), "--brand", "goodman"] + sys.argv[1:]
    sys.exit(subprocess.call(cmd))
