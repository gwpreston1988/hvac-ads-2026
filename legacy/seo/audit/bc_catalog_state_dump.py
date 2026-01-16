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
BigCommerce Full Catalog SEO State Dump

PURPOSE:
    Extract current SEO field values for ALL products in the BigCommerce catalog.
    This is a READ-ONLY extraction script - no mutations are performed.

INPUTS:
    - BigCommerce API credentials from .env (BIGCOMMERCE_STORE_HASH, BIGCOMMERCE_ACCESS_TOKEN)
    - Field allowlist from seo/configs/seo_fields_allowlist.json

OUTPUTS:
    - reports/seo/_shared/catalog_seo_state_{timestamp}.json
    - Contains: Full SEO field dump for every product, category, and brand

READ-ONLY: This script does NOT modify any data in BigCommerce.
"""

# TODO: Implementation pending
pass
