#!/usr/bin/env python3
"""
Phase C2: Plan Changes Generator

################################################################################
# PLANNER IS SNAPSHOT-ONLY. NO LIVE API CALLS.
# This script reads ONLY from local snapshot files. It does NOT connect to
# Google Ads, Merchant Center, or any external APIs.
################################################################################

Usage:
    python plans/plan_changes.py --snapshot <path>    # Explicit snapshot path
    python plans/plan_changes.py --latest             # Use most recent snapshot
    python plans/plan_changes.py --latest --ruleset safety --max-ops 50

Rulesets:
    safety   - Conservative rules for brand protection (default)
    strategy - Performance optimization rules (future)
    all      - All rules enabled (future)
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
CORE_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = CORE_DIR.parent
SNAPSHOTS_DIR = PROJECT_ROOT / "snapshots"
PLANS_DIR = PROJECT_ROOT / "plans"
RUNS_DIR = PLANS_DIR / "runs"
CONFIGS_DIR = CORE_DIR / "configs"

# Campaign IDs (from _index.json convention)
BRANDED_CAMPAIGN_ID = "20958985895"
PMAX_CAMPAIGN_ID = "20815709270"

# Default brand terms (used if configs/brand_terms.json not found)
DEFAULT_BRAND_TERMS = [
    "buy comfort direct",
    "buycomfortdirect",
    "buycomfortdirect.com",
    "buy comfort",
    "comfort direct",
    "bcd",
    "bcd hvac",
]

# Manufacturer brands (should NOT appear in BCD brand campaign assets)
MANUFACTURER_BRANDS = [
    "rheem", "goodman", "solace", "daikin", "ruud", "amana",
]

# Default guardrails (SAFE values)
DEFAULT_GUARDRAILS = {
    "max_total_ops": 50,
    "max_ops_by_type": {
        "ADS_SET_KEYWORD_STATUS": 20,
        "ADS_ADD_NEGATIVE_KEYWORD": 20,
        "ADS_SET_KEYWORD_MATCH_TYPE": 10,
        "ADS_UPDATE_ASSET_TEXT": 5,
        "ADS_REMOVE_ASSET": 5,
        "ADS_SET_PMAX_BRAND_EXCLUSIONS": 5,
        "MERCHANT_EXCLUDE_PRODUCT": 10,
        "ADS_UPDATE_BID_STRATEGY": 0,
        "ADS_UPDATE_BUDGET": 0,
    },
    "forbid_budget_changes": True,
    "forbid_campaign_pause": True,
    "forbid_campaign_enable": False,
    "max_budget_pct_change": 0,
    "forbid_broad_match": True,
    "forbid_manufacturer_brand_negatives": True,
    "forbid_bid_strategy_changes": True,
    "forbid_conversion_goal_changes": True,
    "forbid_location_targeting_changes": True,
    "forbid_url_expansion_changes": True,
    "forbid_auto_apply_settings": True,
    "max_text_edit_chars": 100,
    "allowlist_campaign_ids": None,
    "blocklist_campaign_ids": [],
    "require_manual_approval_for_types": [
        "ADS_REMOVE_ASSET",
        "MERCHANT_EXCLUDE_PRODUCT",
    ],
    "require_precondition_match": True,
    "abort_on_missing_entity": True,
    "abort_on_first_error": False,
    "max_risk_level": "MEDIUM",
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def get_utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


def get_utc_timestamp() -> str:
    """Get current UTC timestamp string."""
    return get_utc_now().strftime("%Y-%m-%dT%H%M%SZ")


def load_json(path: Path) -> dict:
    """Load JSON file, return empty dict if not found."""
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return json.load(f)


def load_json_required(path: Path) -> dict:
    """Load JSON file, raise error if not found."""
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    with open(path, "r") as f:
        return json.load(f)


def find_latest_snapshot() -> Path:
    """Find the most recent snapshot folder."""
    if not SNAPSHOTS_DIR.exists():
        raise FileNotFoundError(f"Snapshots directory not found: {SNAPSHOTS_DIR}")
    snapshots = [d for d in SNAPSHOTS_DIR.iterdir() if d.is_dir() and d.name[0].isdigit()]
    if not snapshots:
        raise FileNotFoundError("No snapshot folders found")
    snapshots.sort(key=lambda x: x.name, reverse=True)
    return snapshots[0]


def stable_hash(*args) -> str:
    """Generate a stable hash from arguments for deterministic op_id."""
    combined = "|".join(str(a) for a in args)
    return hashlib.sha256(combined.encode()).hexdigest()[:12]


def make_entity_ref(platform: str, entity_type: str, entity_id: str) -> str:
    """Create canonical entity_ref string."""
    platform_prefix = "ads" if platform == "GOOGLE_ADS" else "merchant"
    return f"{platform_prefix}.{entity_type.lower()}:{entity_id}"


def is_brand_term(text: str, brand_terms: list) -> bool:
    """Check if text is/contains a brand term."""
    text_lower = text.lower().strip()
    for term in brand_terms:
        if term.lower() in text_lower:
            return True
    return False


def contains_manufacturer_brand(text: str) -> bool:
    """Check if text contains a manufacturer brand name."""
    text_lower = text.lower()
    for brand in MANUFACTURER_BRANDS:
        if brand.lower() in text_lower:
            return True
    return False


def risk_to_numeric(level: str) -> int:
    """Convert risk level to numeric value."""
    return {"LOW": 1, "MEDIUM": 2, "HIGH": 3}.get(level, 0)


# =============================================================================
# SNAPSHOT LOADER
# =============================================================================


class SnapshotLoader:
    """Loads all data from a snapshot folder."""

    REQUIRED_FILES = [
        "_manifest.json",
        "normalized/ads/campaigns.json",
        "normalized/ads/keywords.json",
    ]

    def __init__(self, snapshot_path: Path):
        self.snapshot_path = snapshot_path
        self.snapshot_id = snapshot_path.name

        if not self.snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot not found: {self.snapshot_path}")

        # Check required files
        missing = []
        for rel_path in self.REQUIRED_FILES:
            if not (self.snapshot_path / rel_path).exists():
                missing.append(rel_path)
        if missing:
            raise FileNotFoundError(
                f"Missing required files:\n" + "\n".join(f"  - {f}" for f in missing)
            )

        # Load all files
        self.manifest = load_json_required(self.snapshot_path / "_manifest.json")
        self.index = load_json(self.snapshot_path / "_index.json")

        # Ads data
        self.campaigns = load_json(self.snapshot_path / "normalized/ads/campaigns.json")
        self.ad_groups = load_json(self.snapshot_path / "normalized/ads/ad_groups.json")
        self.keywords = load_json(self.snapshot_path / "normalized/ads/keywords.json")
        self.negatives = load_json(self.snapshot_path / "normalized/ads/negatives.json")
        self.ads = load_json(self.snapshot_path / "normalized/ads/ads.json")
        self.assets = load_json(self.snapshot_path / "normalized/ads/assets.json")

        # PMax data
        self.pmax_campaigns = load_json(self.snapshot_path / "normalized/pmax/campaigns.json")
        self.asset_groups = load_json(self.snapshot_path / "normalized/pmax/asset_groups.json")

        # Merchant data
        self.merchant_products = load_json(self.snapshot_path / "normalized/merchant/products.json")
        self.merchant_status = load_json(self.snapshot_path / "normalized/merchant/product_status.json")

    def get_campaign_by_id(self, campaign_id: str) -> dict:
        """Get campaign info by ID."""
        for c in self.campaigns.get("records", []):
            if str(c.get("id")) == str(campaign_id):
                return c
        for c in self.pmax_campaigns.get("records", []):
            if str(c.get("id")) == str(campaign_id):
                return c
        return {}

    def get_campaign_name(self, campaign_id: str) -> str:
        """Get campaign name from index."""
        by_id = self.index.get("campaigns", {}).get("by_id", {})
        return by_id.get(str(campaign_id), "Unknown")


# =============================================================================
# PLAN BUILDER
# =============================================================================


class PlanBuilder:
    """Builds a proposed changes plan from snapshot data."""

    def __init__(
        self,
        loader: SnapshotLoader,
        brand_terms: list,
        max_ops: int = 50,
        ruleset: str = "safety",
    ):
        self.loader = loader
        self.brand_terms = brand_terms
        self.max_ops = max_ops
        self.ruleset = ruleset

        # Plan state
        self.operations = []
        self.findings = []  # Non-actionable findings (warnings)
        self.op_counter = 0

        # Load discontinued SKUs
        self.discontinued_skus = self._load_discontinued_skus()

    def _load_discontinued_skus(self) -> set:
        """Load discontinued SKUs from config file."""
        skus_file = CONFIGS_DIR / "discontinued_skus.txt"
        if not skus_file.exists():
            return set()
        with open(skus_file, "r") as f:
            return {line.strip() for line in f if line.strip() and not line.startswith("#")}

    def _next_op_id(self, op_type: str, entity_ref: str, rule_id: str) -> str:
        """Generate stable, deterministic op_id."""
        self.op_counter += 1
        hash_part = stable_hash(op_type, entity_ref, rule_id)
        return f"op-{self.op_counter:03d}-{hash_part}"

    def add_finding(self, rule_id: str, level: str, message: str, entity_ref: str = None):
        """Add a non-actionable finding (warning/info)."""
        self.findings.append({
            "rule_id": rule_id,
            "level": level,
            "message": message,
            "entity_ref": entity_ref,
        })

    def add_operation(self, op: dict):
        """Add an operation to the plan with guardrail enforcement."""
        # GUARDRAIL: forbid_manufacturer_brand_negatives
        # Never add negative keywords for manufacturer brands (Rheem, Goodman, etc.)
        if op.get("op_type") == "ADS_ADD_NEGATIVE_KEYWORD":
            kw_text = op.get("after", {}).get("text", "")
            if contains_manufacturer_brand(kw_text):
                self.add_finding(
                    "guardrail:forbid_manufacturer_brand_negatives",
                    "WARNING",
                    f"BLOCKED: Cannot add manufacturer brand as negative keyword: '{kw_text}'",
                    op.get("entity_ref"),
                )
                return  # Do NOT add this operation

        if len(self.operations) < self.max_ops:
            self.operations.append(op)
        else:
            self.add_finding(
                "planner:max_ops_reached",
                "WARNING",
                f"Max operations ({self.max_ops}) reached; additional ops skipped",
            )

    def build_plan(self) -> dict:
        """Build the complete plan."""
        # Run all enabled rules
        if self.ruleset in ("safety", "all"):
            self._run_safety_rules()

        # Build plan structure
        manifest = self.loader.manifest
        accounts = manifest.get("accounts", {})
        google_ads = accounts.get("google_ads", {})
        merchant = accounts.get("merchant_center", {})

        plan = {
            "plan_id": f"plan-{self.loader.snapshot_id}-{get_utc_timestamp()}",
            "plan_version": "C1.1",
            "created_utc": get_utc_now().isoformat(),
            "snapshot_id": self.loader.snapshot_id,
            "snapshot_version": manifest.get("snapshot_version", "UNKNOWN"),
            "sources": {
                "google_ads_customer_id": google_ads.get("customer_id", "UNKNOWN"),
                "google_ads_login_customer_id": google_ads.get("login_customer_id", google_ads.get("customer_id", "UNKNOWN")),
                "merchant_center_id": merchant.get("merchant_id", "N/A") if merchant else "N/A",
            },
            "mode": "DRY_RUN",
            "plan_context": self._build_plan_context(),
            "guardrails": self._build_guardrails(),
            "summary": self._build_summary(),
            "operations": self.operations,
            "approvals": self._build_approvals(),
            "integrity": {
                "snapshot_manifest_hash": None,
                "plan_operations_hash": None,
                "generated_by": "plan_changes.py",
                "generator_version": "C2.0",
            },
        }

        return plan

    def _build_plan_context(self) -> dict:
        """Build plan context with parameters used."""
        rules_applied = []
        if self.ruleset in ("safety", "all"):
            rules_applied.extend([
                "rule:S1:broad_match_in_branded",
                "rule:S2:non_brand_in_branded",
                "rule:S3:branded_bidding_strategy",
                "rule:S4:manufacturer_brand_in_assets",
                "rule:S5:merchant_disapproved",
            ])

        return {
            "brand_terms_version": get_utc_now().strftime("%Y-%m-%d"),
            "brand_terms": self.brand_terms,
            "manufacturer_brands": MANUFACTURER_BRANDS,
            "thresholds": {
                "brand_cpc_max": 2.00,
                "roas_target": 4.0,
            },
            "lookback_days": 30,
            "planner_rules_applied": rules_applied,
            "notes": f"Generated with ruleset={self.ruleset}, max_ops={self.max_ops}",
        }

    def _build_guardrails(self) -> dict:
        """Build guardrails with safe defaults."""
        guardrails = DEFAULT_GUARDRAILS.copy()
        guardrails["max_total_ops"] = self.max_ops
        return guardrails

    def _build_summary(self) -> dict:
        """Build summary statistics."""
        ops_by_type = {}
        ops_by_risk = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        campaigns_affected = set()
        platforms_affected = set()

        for op in self.operations:
            op_type = op.get("op_type")
            ops_by_type[op_type] = ops_by_type.get(op_type, 0) + 1

            risk_level = op.get("risk", {}).get("level", "LOW")
            ops_by_risk[risk_level] = ops_by_risk.get(risk_level, 0) + 1

            platform = op.get("entity", {}).get("platform")
            if platform:
                platforms_affected.add(platform)

            parent_refs = op.get("entity", {}).get("parent_refs", [])
            for ref in parent_refs:
                if "campaign:" in ref:
                    campaigns_affected.add(ref.split(":")[-1])

        # Determine overall risk
        if ops_by_risk["HIGH"] > 0:
            risk_score = "HIGH"
        elif ops_by_risk["MEDIUM"] > 0:
            risk_score = "MEDIUM"
        else:
            risk_score = "LOW"

        # Identify ops requiring approval
        approval_types = DEFAULT_GUARDRAILS["require_manual_approval_for_types"]
        approval_required_ops = [
            op["op_id"] for op in self.operations
            if op.get("op_type") in approval_types
        ]

        # Build risk summary
        risk_parts = []
        if ops_by_risk["HIGH"] > 0:
            risk_parts.append(f"{ops_by_risk['HIGH']} high-risk")
        if ops_by_risk["MEDIUM"] > 0:
            risk_parts.append(f"{ops_by_risk['MEDIUM']} medium-risk")
        if ops_by_risk["LOW"] > 0:
            risk_parts.append(f"{ops_by_risk['LOW']} low-risk")
        risk_summary = "; ".join(risk_parts) if risk_parts else "No operations"

        # Add findings summary
        if self.findings:
            finding_counts = {}
            for f in self.findings:
                level = f["level"]
                finding_counts[level] = finding_counts.get(level, 0) + 1
            findings_str = ", ".join(f"{v} {k}" for k, v in finding_counts.items())
            risk_summary += f" | Findings: {findings_str}"

        return {
            "total_operations": len(self.operations),
            "total_findings": len(self.findings),
            "operations_by_type": ops_by_type,
            "operations_by_risk": ops_by_risk,
            "estimated_api_calls": len(self.operations),
            "platforms_affected": sorted(platforms_affected),
            "campaigns_affected": sorted(campaigns_affected),
            "risk_score": risk_score,
            "risk_summary": risk_summary,
            "requires_approval": len(approval_required_ops) > 0,
            "approval_required_ops": approval_required_ops,
            "findings": self.findings,
        }

    def _build_approvals(self) -> dict:
        """Build approvals structure."""
        approval_types = DEFAULT_GUARDRAILS["require_manual_approval_for_types"]
        approval_required_ops = [
            op["op_id"] for op in self.operations
            if op.get("op_type") in approval_types
        ]

        operation_approvals = {}
        for op_id in approval_required_ops:
            operation_approvals[op_id] = {
                "approved": False,
                "approved_by": None,
                "approved_at": None,
                "notes": None,
            }

        return {
            "plan_approved": False,
            "approved_by": None,
            "approved_at": None,
            "approval_notes": None,
            "operations_requiring_approval": approval_required_ops,
            "operation_approvals": operation_approvals,
        }

    # =========================================================================
    # SAFETY RULES
    # =========================================================================

    def _run_safety_rules(self):
        """Run all safety rules."""
        self._rule_s1_broad_match_in_branded()
        self._rule_s2_non_brand_in_branded()
        self._rule_s3_branded_bidding_strategy()
        self._rule_s4_manufacturer_brand_in_assets()
        self._rule_s5_merchant_disapproved()
        self._rule_s6_pmax_brand_exclusions()

    def _rule_s1_broad_match_in_branded(self):
        """
        Rule S1: Flag any enabled BROAD match keywords in Branded campaign.
        Action: WARNING only (no operation proposed).
        """
        rule_id = "rule:S1:broad_match_in_branded"
        keywords = self.loader.keywords.get("records", [])

        for kw in keywords:
            if str(kw.get("campaign_id")) != BRANDED_CAMPAIGN_ID:
                continue
            if kw.get("status") != "ENABLED":
                continue
            if kw.get("match_type") != "BROAD":
                continue

            entity_ref = make_entity_ref("GOOGLE_ADS", "keyword", str(kw.get("id")))
            self.add_finding(
                rule_id,
                "WARNING",
                f"BROAD match keyword in Branded campaign: '{kw.get('text')}' - consider changing to EXACT/PHRASE",
                entity_ref,
            )

    def _rule_s2_non_brand_in_branded(self):
        """
        Rule S2: Detect non-brand keywords enabled in Branded campaign.
        Action: Propose ADS_SET_KEYWORD_STATUS to PAUSED (MEDIUM risk).

        CRITICAL SAFEGUARD: This rule MUST NEVER propose pausing brand keywords.
        The brand_terms list must be validated non-empty before this rule runs.
        """
        rule_id = "rule:S2:non_brand_in_branded"
        keywords = self.loader.keywords.get("records", [])
        branded_campaign = self.loader.get_campaign_by_id(BRANDED_CAMPAIGN_ID)

        if not branded_campaign:
            self.add_finding(rule_id, "ERROR", f"Branded campaign {BRANDED_CAMPAIGN_ID} not found")
            return

        # CRITICAL: Double-check brand_terms is non-empty before processing
        if not self.brand_terms:
            self.add_finding(
                rule_id,
                "ERROR",
                "ABORT: brand_terms list is empty - cannot safely determine non-brand keywords"
            )
            return

        brand_keywords_skipped = []
        for kw in keywords:
            if str(kw.get("campaign_id")) != BRANDED_CAMPAIGN_ID:
                continue
            if kw.get("status") != "ENABLED":
                continue

            kw_text = kw.get("text", "")

            # CRITICAL SAFEGUARD: Never propose pausing brand keywords
            if is_brand_term(kw_text, self.brand_terms):
                brand_keywords_skipped.append(kw_text)
                continue  # This is a brand term - DO NOT PAUSE

            # Non-brand keyword in Branded campaign -> propose pause
            kw_id = str(kw.get("id"))
            ad_group_id = str(kw.get("ad_group_id", ""))
            entity_ref = make_entity_ref("GOOGLE_ADS", "keyword", kw_id)
            op_id = self._next_op_id("ADS_SET_KEYWORD_STATUS", entity_ref, rule_id)

            op = {
                "op_id": op_id,
                "op_type": "ADS_SET_KEYWORD_STATUS",
                "entity_ref": entity_ref,
                "entity": {
                    "platform": "GOOGLE_ADS",
                    "entity_type": "KEYWORD",
                    "entity_id": kw_id,
                    "entity_name": kw_text,
                    "parent_refs": [
                        f"ads.customer:{self.loader.manifest.get('accounts', {}).get('google_ads', {}).get('customer_id', '')}",
                        f"ads.campaign:{BRANDED_CAMPAIGN_ID}",
                        f"ads.ad_group:{ad_group_id}",
                    ],
                },
                "intent": f"Pause non-brand keyword '{kw_text}' in Branded campaign to maintain brand purity",
                "before": {
                    "text": kw_text,
                    "match_type": kw.get("match_type"),
                    "status": "ENABLED",
                },
                "after": {
                    "text": kw_text,
                    "match_type": kw.get("match_type"),
                    "status": "PAUSED",
                },
                "preconditions": [
                    {
                        "path": "status",
                        "op": "EQUALS",
                        "value": "ENABLED",
                        "description": "Keyword must still be enabled",
                    },
                    {
                        "path": "campaign.id",
                        "op": "EQUALS",
                        "value": BRANDED_CAMPAIGN_ID,
                        "description": "Keyword must be in Branded campaign",
                    },
                ],
                "rollback": {
                    "type": "RESTORE_BEFORE",
                    "data": {"status": "ENABLED"},
                    "notes": "Re-enable keyword if rollback needed",
                },
                "risk": {
                    "level": "MEDIUM",
                    "level_numeric": 2,
                    "reasons": [
                        "Non-brand keyword in Branded campaign dilutes brand protection",
                        "Pausing may reduce impressions for this term",
                    ],
                    "mitigations": [
                        "Keyword can be re-enabled via rollback",
                        "Term may be better served by Offensive campaign",
                    ],
                },
                "evidence": [
                    {
                        "snapshot_path": "normalized/ads/keywords.json",
                        "key": "id",
                        "value": kw_id,
                        "field_path": None,
                        "note": f"Keyword '{kw_text}' is not a recognized brand term",
                    },
                ],
                "evidence_query": f"keywords WHERE campaign_id='{BRANDED_CAMPAIGN_ID}' AND status='ENABLED' AND text NOT IN brand_terms",
                "created_from_rule": rule_id,
                "approved": False,
                "approval_notes": None,
            }

            self.add_operation(op)

        # Log brand keywords that were correctly protected (not paused)
        if brand_keywords_skipped:
            self.add_finding(
                rule_id,
                "INFO",
                f"Protected {len(brand_keywords_skipped)} brand keyword(s) in Branded campaign (not proposed for pause): {', '.join(sorted(set(brand_keywords_skipped))[:5])}"
            )

    def _rule_s3_branded_bidding_strategy(self):
        """
        Rule S3: Detect Branded campaign bidding strategy not MANUAL_CPC.
        Action: HIGH risk finding only (no operation proposed).
        """
        rule_id = "rule:S3:branded_bidding_strategy"
        branded_campaign = self.loader.get_campaign_by_id(BRANDED_CAMPAIGN_ID)

        if not branded_campaign:
            self.add_finding(rule_id, "ERROR", f"Branded campaign {BRANDED_CAMPAIGN_ID} not found")
            return

        bidding_strategy = branded_campaign.get("bidding_strategy", "UNKNOWN")
        if bidding_strategy != "MANUAL_CPC":
            entity_ref = make_entity_ref("GOOGLE_ADS", "campaign", BRANDED_CAMPAIGN_ID)
            self.add_finding(
                rule_id,
                "HIGH",
                f"Branded campaign uses {bidding_strategy} instead of MANUAL_CPC - manual intervention required",
                entity_ref,
            )

    def _rule_s4_manufacturer_brand_in_assets(self):
        """
        Rule S4: Detect Branded campaign assets containing manufacturer brands.
        Action: Propose ADS_UPDATE_ASSET_TEXT (MEDIUM risk).
        """
        rule_id = "rule:S4:manufacturer_brand_in_assets"
        assets = self.loader.assets.get("records", [])

        # Find assets linked to Branded campaign
        for asset in assets:
            # Check if asset is linked to Branded campaign
            linked_campaigns = asset.get("linked_campaign_ids", [])
            if BRANDED_CAMPAIGN_ID not in [str(c) for c in linked_campaigns]:
                # Also check if campaign_id is directly on the asset
                if str(asset.get("campaign_id", "")) != BRANDED_CAMPAIGN_ID:
                    continue

            asset_type = asset.get("asset_type", "")
            if asset_type not in ("SITELINK", "CALLOUT", "STRUCTURED_SNIPPET", "HEADLINE", "DESCRIPTION"):
                continue

            text_fields = []
            if asset.get("text"):
                text_fields.append(("text", asset["text"]))
            if asset.get("headline"):
                text_fields.append(("headline", asset["headline"]))
            if asset.get("description"):
                text_fields.append(("description", asset["description"]))
            if asset.get("description1"):
                text_fields.append(("description1", asset["description1"]))
            if asset.get("description2"):
                text_fields.append(("description2", asset["description2"]))

            for field_name, text in text_fields:
                if not contains_manufacturer_brand(text):
                    continue

                # Found manufacturer brand in Branded campaign asset
                asset_id = str(asset.get("id", asset.get("resource_name", "")))
                entity_ref = make_entity_ref("GOOGLE_ADS", "asset", asset_id)
                op_id = self._next_op_id("ADS_UPDATE_ASSET_TEXT", entity_ref, rule_id)

                # Generate generic replacement text
                original_text = text
                new_text = self._generate_generic_cta(text)

                if len(new_text) > len(original_text) + 50:
                    # Replacement too different, just flag
                    self.add_finding(
                        rule_id,
                        "WARNING",
                        f"Asset contains manufacturer brand but replacement would be too different: '{text[:50]}...'",
                        entity_ref,
                    )
                    continue

                op = {
                    "op_id": op_id,
                    "op_type": "ADS_UPDATE_ASSET_TEXT",
                    "entity_ref": entity_ref,
                    "entity": {
                        "platform": "GOOGLE_ADS",
                        "entity_type": "ASSET",
                        "entity_id": asset_id,
                        "entity_name": original_text[:50],
                        "parent_refs": [
                            f"ads.customer:{self.loader.manifest.get('accounts', {}).get('google_ads', {}).get('customer_id', '')}",
                            f"ads.campaign:{BRANDED_CAMPAIGN_ID}",
                        ],
                    },
                    "intent": f"Remove manufacturer brand reference from Branded campaign asset",
                    "before": {
                        "asset_type": asset_type,
                        field_name: original_text,
                    },
                    "after": {
                        "asset_type": asset_type,
                        field_name: new_text,
                    },
                    "preconditions": [
                        {
                            "path": field_name,
                            "op": "CONTAINS",
                            "value": self._find_manufacturer_brand(text),
                            "description": "Asset must still contain manufacturer brand",
                        },
                    ],
                    "rollback": {
                        "type": "RESTORE_BEFORE",
                        "data": {field_name: original_text},
                        "notes": "Restore original text",
                    },
                    "risk": {
                        "level": "MEDIUM",
                        "level_numeric": 2,
                        "reasons": [
                            "Modifying asset text affects ad copy",
                            "Manufacturer brands should not appear in BCD Branded campaign",
                        ],
                        "mitigations": [
                            "Rollback restores original text",
                            "Generic CTA maintains ad relevance",
                        ],
                    },
                    "evidence": [
                        {
                            "snapshot_path": "normalized/ads/assets.json",
                            "key": "id",
                            "value": asset_id,
                            "field_path": None,
                            "note": f"Asset {field_name} contains manufacturer brand",
                        },
                    ],
                    "evidence_query": f"assets WHERE linked_campaign_ids CONTAINS '{BRANDED_CAMPAIGN_ID}' AND text CONTAINS manufacturer_brand",
                    "created_from_rule": rule_id,
                    "approved": False,
                    "approval_notes": None,
                }

                self.add_operation(op)

    def _find_manufacturer_brand(self, text: str) -> str:
        """Find which manufacturer brand is in the text."""
        text_lower = text.lower()
        for brand in MANUFACTURER_BRANDS:
            if brand.lower() in text_lower:
                return brand
        return ""

    def _generate_generic_cta(self, text: str) -> str:
        """Generate a generic CTA by removing manufacturer brands."""
        result = text
        for brand in MANUFACTURER_BRANDS:
            # Case-insensitive replacement
            import re
            pattern = re.compile(re.escape(brand), re.IGNORECASE)
            result = pattern.sub("Premium", result)

        # Clean up any double spaces
        result = " ".join(result.split())
        return result

    def _rule_s5_merchant_disapproved(self):
        """
        Rule S5: Detect disapproved Merchant products.
        Action: Propose MERCHANT_EXCLUDE_PRODUCT only if in discontinued_skus.txt.
        """
        rule_id = "rule:S5:merchant_disapproved"
        products = self.loader.merchant_products.get("records", [])
        status_records = self.loader.merchant_status.get("records", [])

        # Build status lookup
        status_by_offer = {}
        for s in status_records:
            offer_id = s.get("offer_id")
            if offer_id:
                status_by_offer[offer_id] = s

        disapproved_count = 0
        excluded_count = 0

        for product in products:
            approval = product.get("approval_status", "")
            if approval != "DISAPPROVED":
                continue

            disapproved_count += 1
            offer_id = product.get("offer_id", "")
            title = product.get("title", "")[:80]

            # Check if in discontinued SKUs list
            if offer_id not in self.discontinued_skus:
                # Just a finding, no action
                continue

            # Propose exclusion for discontinued SKU
            product_id = product.get("id", offer_id)
            entity_ref = make_entity_ref("MERCHANT_CENTER", "product", product_id)
            op_id = self._next_op_id("MERCHANT_EXCLUDE_PRODUCT", entity_ref, rule_id)
            excluded_count += 1

            merchant_id = self.loader.manifest.get("accounts", {}).get("merchant_center", {}).get("merchant_id", "")

            op = {
                "op_id": op_id,
                "op_type": "MERCHANT_EXCLUDE_PRODUCT",
                "entity_ref": entity_ref,
                "entity": {
                    "platform": "MERCHANT_CENTER",
                    "entity_type": "PRODUCT",
                    "entity_id": product_id,
                    "entity_name": title,
                    "parent_refs": [
                        f"merchant.account:{merchant_id}",
                    ],
                },
                "intent": f"Exclude discontinued product '{title}' from Shopping/PMax",
                "before": {
                    "offer_id": offer_id,
                    "title": title,
                    "approval_status": "DISAPPROVED",
                    "excluded": False,
                },
                "after": {
                    "offer_id": offer_id,
                    "excluded": True,
                    "exclusion_reason": "DISCONTINUED_AND_DISAPPROVED",
                },
                "preconditions": [
                    {
                        "path": "offer_id",
                        "op": "EXISTS",
                        "value": None,
                        "description": "Product must exist in Merchant Center",
                    },
                    {
                        "path": "approval_status",
                        "op": "EQUALS",
                        "value": "DISAPPROVED",
                        "description": "Product must still be disapproved",
                    },
                ],
                "rollback": {
                    "type": "RESTORE_BEFORE",
                    "data": {"excluded": False},
                    "notes": "Remove exclusion from supplemental feed",
                },
                "risk": {
                    "level": "MEDIUM",
                    "level_numeric": 2,
                    "reasons": [
                        "Excluding products reduces Shopping inventory",
                        "Product is discontinued per configs/discontinued_skus.txt",
                    ],
                    "mitigations": [
                        "Only excludes products in discontinued list",
                        "Rollback removes exclusion",
                    ],
                },
                "evidence": [
                    {
                        "snapshot_path": "normalized/merchant/products.json",
                        "key": "offer_id",
                        "value": offer_id,
                        "field_path": None,
                        "note": f"Product disapproved and in discontinued SKUs list",
                    },
                ],
                "evidence_query": f"products WHERE approval_status='DISAPPROVED' AND offer_id IN discontinued_skus",
                "created_from_rule": rule_id,
                "approved": False,
                "approval_notes": None,
            }

            self.add_operation(op)

        # Add summary finding for disapproved products
        if disapproved_count > 0:
            self.add_finding(
                rule_id,
                "INFO",
                f"{disapproved_count} disapproved products found; {excluded_count} in discontinued list (proposed for exclusion)",
            )

    def _rule_s6_pmax_brand_exclusions(self):
        """
        Rule S6: Propose brand exclusions for PMax campaigns.

        PMax campaigns do NOT support standard negative keywords (Google API returns
        OPERATION_NOT_PERMITTED_FOR_CONTEXT for UBERVERSAL campaigns).

        Instead, brand protection is achieved via Brand Exclusion Lists.
        This rule proposes ADS_SET_PMAX_BRAND_EXCLUSIONS for each PMax campaign
        that does not have brand exclusions configured.

        Action: Propose ADS_SET_PMAX_BRAND_EXCLUSIONS (MEDIUM risk).
        """
        rule_id = "rule:S6:pmax_brand_exclusions"

        # CRITICAL: Require brand_terms to be non-empty
        if not self.brand_terms:
            self.add_finding(
                rule_id,
                "WARNING",
                "brand_terms list is empty - cannot propose PMax brand exclusions",
            )
            return

        # Load PMax campaigns
        pmax_campaigns = self.loader.pmax_campaigns.get("records", [])

        if not pmax_campaigns:
            self.add_finding(rule_id, "INFO", "No PMax campaigns found")
            return

        # Load existing brand exclusions from snapshot
        brand_exclusions = {}
        try:
            brand_excl_path = self.loader.snapshot_dir / "normalized" / "pmax" / "brand_exclusions.json"
            if brand_excl_path.exists():
                with open(brand_excl_path) as f:
                    brand_excl_data = json.load(f)
                    for crit in brand_excl_data.get("pmax_negative_criteria", []):
                        cid = str(crit.get("campaign_id", ""))
                        if cid:
                            brand_exclusions.setdefault(cid, []).append(crit)
        except Exception:
            pass  # Continue without exclusion data

        customer_id = self.loader.manifest.get("accounts", {}).get("google_ads", {}).get("customer_id", "")
        ops_proposed = 0

        for campaign in pmax_campaigns:
            campaign_id = str(campaign.get("id", ""))
            campaign_name = campaign.get("name", "")
            campaign_status = campaign.get("status", "")

            # Only propose for ENABLED campaigns
            if campaign_status != "ENABLED":
                continue

            # Check if already has brand exclusions
            existing_exclusions = brand_exclusions.get(campaign_id, [])
            if existing_exclusions:
                self.add_finding(
                    rule_id,
                    "INFO",
                    f"PMax campaign '{campaign_name}' already has {len(existing_exclusions)} negative criteria configured",
                )
                continue

            # Propose brand exclusions for this campaign
            entity_ref = make_entity_ref("GOOGLE_ADS", "campaign", campaign_id)
            op_id = self._next_op_id("ADS_SET_PMAX_BRAND_EXCLUSIONS", entity_ref, rule_id)

            # Filter out manufacturer brands from brand_terms (they should NOT be excluded)
            safe_brand_terms = [
                term for term in self.brand_terms
                if not any(mfg.lower() in term.lower() for mfg in MANUFACTURER_BRANDS)
            ]

            if not safe_brand_terms:
                self.add_finding(
                    rule_id,
                    "WARNING",
                    f"No safe brand terms to exclude for '{campaign_name}' (all terms contain manufacturer brands)",
                )
                continue

            op = {
                "op_id": op_id,
                "op_type": "ADS_SET_PMAX_BRAND_EXCLUSIONS",
                "entity_ref": entity_ref,
                "entity": {
                    "platform": "GOOGLE_ADS",
                    "entity_type": "CAMPAIGN",
                    "entity_id": campaign_id,
                    "entity_name": campaign_name,
                    "campaign_type": "PERFORMANCE_MAX",
                    "parent_refs": [
                        f"ads.customer:{customer_id}",
                    ],
                },
                "intent": f"Set brand exclusions for PMax campaign '{campaign_name}' to protect BCD branded traffic",
                "before": {
                    "brand_list_id": None,
                    "brands": [],
                },
                "after": {
                    "brand_list_id": "auto",
                    "brand_list_name": f"BCD Brand Exclusions - {campaign_name}",
                    "brands": safe_brand_terms,
                },
                "params": {
                    "campaign_id": campaign_id,
                    "action": "SET",
                    "brand_list_id": None,
                    "brand_list_name": f"BCD Brand Exclusions - {campaign_name}",
                    "brands": safe_brand_terms,
                },
                "preconditions": [
                    {
                        "path": "advertising_channel_type",
                        "op": "EQUALS",
                        "value": "PERFORMANCE_MAX",
                        "description": "Campaign must be Performance Max",
                    },
                    {
                        "path": "status",
                        "op": "EQUALS",
                        "value": "ENABLED",
                        "description": "Campaign must be enabled",
                    },
                ],
                "rollback": {
                    "type": "RESTORE_BEFORE",
                    "data": {"brands": []},
                    "notes": "Remove brand exclusion list from campaign",
                },
                "risk": {
                    "level": "MEDIUM",
                    "level_numeric": 2,
                    "reasons": [
                        "Brand exclusions affect which search queries trigger PMax ads",
                        "May reduce PMax reach for brand-related queries (desired behavior)",
                    ],
                    "mitigations": [
                        "Brand terms are from verified config file",
                        "Manufacturer brands are excluded from exclusion list",
                        "Rollback removes the brand exclusion list",
                    ],
                },
                "evidence": [
                    {
                        "snapshot_path": "normalized/pmax/campaigns.json",
                        "key": "id",
                        "value": campaign_id,
                        "field_path": None,
                        "note": f"PMax campaign without brand exclusions",
                    },
                    {
                        "snapshot_path": "core/configs/brand_terms.json",
                        "key": "brand_terms",
                        "value": safe_brand_terms,
                        "field_path": None,
                        "note": "Brand terms to exclude (manufacturer brands filtered out)",
                    },
                ],
                "evidence_query": f"pmax_campaigns WHERE status='ENABLED' AND brand_exclusions IS NULL",
                "created_from_rule": rule_id,
                "approved": False,
                "approval_notes": None,
            }

            self.add_operation(op)
            ops_proposed += 1

        if ops_proposed > 0:
            self.add_finding(
                rule_id,
                "INFO",
                f"Proposed {ops_proposed} PMax brand exclusion operation(s) for {len(safe_brand_terms)} brand terms",
            )


# =============================================================================
# SUMMARY WRITER
# =============================================================================


def write_summary(plan: dict, findings: list, output_path: Path):
    """Write a human-readable plan summary markdown file."""
    lines = []
    lines.append("# Plan Summary")
    lines.append("")
    lines.append(f"**Plan ID:** `{plan['plan_id']}`")
    lines.append(f"**Snapshot ID:** `{plan['snapshot_id']}`")
    lines.append(f"**Created:** {plan['created_utc']}")
    lines.append(f"**Mode:** {plan['mode']}")
    lines.append("")

    # Summary stats
    summary = plan["summary"]
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- **Total Operations:** {summary['total_operations']}")
    lines.append(f"- **Total Findings:** {summary['total_findings']}")
    lines.append(f"- **Risk Score:** {summary['risk_score']}")
    lines.append(f"- **Requires Approval:** {'Yes' if summary['requires_approval'] else 'No'}")
    lines.append("")

    # Operations by type
    if summary["operations_by_type"]:
        lines.append("## Operations by Type")
        lines.append("")
        lines.append("| Type | Count |")
        lines.append("|------|-------|")
        for op_type, count in sorted(summary["operations_by_type"].items()):
            lines.append(f"| {op_type} | {count} |")
        lines.append("")

    # Operations by risk
    lines.append("## Operations by Risk Level")
    lines.append("")
    lines.append("| Risk | Count |")
    lines.append("|------|-------|")
    for level in ["HIGH", "MEDIUM", "LOW"]:
        count = summary["operations_by_risk"].get(level, 0)
        if count > 0:
            lines.append(f"| {level} | {count} |")
    lines.append("")

    # Approval required
    if summary["approval_required_ops"]:
        lines.append("## Operations Requiring Approval")
        lines.append("")
        for op_id in summary["approval_required_ops"]:
            # Find the operation
            for op in plan["operations"]:
                if op["op_id"] == op_id:
                    lines.append(f"- **{op_id}** ({op['op_type']}): {op['intent'][:60]}...")
                    break
        lines.append("")

    # Top findings
    if findings:
        lines.append("## Findings (Top 10)")
        lines.append("")
        lines.append("| Level | Rule | Message |")
        lines.append("|-------|------|---------|")
        for f in findings[:10]:
            msg = f["message"][:60] + "..." if len(f["message"]) > 60 else f["message"]
            lines.append(f"| {f['level']} | {f['rule_id'].split(':')[-1]} | {msg} |")
        lines.append("")

    # Campaigns affected
    if summary["campaigns_affected"]:
        lines.append("## Campaigns Affected")
        lines.append("")
        for cid in summary["campaigns_affected"]:
            lines.append(f"- {cid}")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated by plan_changes.py at {get_utc_now().isoformat()}*")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))


# =============================================================================
# CLI
# =============================================================================


def print_usage():
    """Print usage information."""
    print("""
Usage: python plans/plan_changes.py [OPTIONS]

REQUIRED (one of):
    --snapshot <path>    Path to snapshot folder
    --latest             Use the most recent snapshot

OPTIONAL:
    --ruleset <name>     Rule set to apply: safety|strategy|all (default: safety)
    --max-ops <n>        Maximum operations to generate (default: 50)

Examples:
    python plans/plan_changes.py --latest
    python plans/plan_changes.py --snapshot snapshots/2026-01-15T202326Z
    python plans/plan_changes.py --latest --ruleset safety --max-ops 20

This script reads ONLY from local snapshot files. NO LIVE API CALLS.
""")


def parse_args():
    """Parse command line arguments."""
    snapshot_path = None
    use_latest = False
    ruleset = "safety"
    max_ops = 50

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--snapshot" and i + 1 < len(sys.argv):
            snapshot_path = Path(sys.argv[i + 1])
            i += 2
        elif arg == "--latest":
            use_latest = True
            i += 1
        elif arg == "--ruleset" and i + 1 < len(sys.argv):
            ruleset = sys.argv[i + 1]
            i += 2
        elif arg == "--max-ops" and i + 1 < len(sys.argv):
            max_ops = int(sys.argv[i + 1])
            i += 2
        elif arg in ("--help", "-h"):
            print_usage()
            sys.exit(0)
        else:
            print(f"ERROR: Unknown argument: {arg}")
            print_usage()
            sys.exit(1)

    return snapshot_path, use_latest, ruleset, max_ops


def main():
    print("=" * 70)
    print("PLAN GENERATION - Phase C2 (SNAPSHOT-ONLY)")
    print("=" * 70)
    print()

    # Parse args
    snapshot_path, use_latest, ruleset, max_ops = parse_args()

    # Validate: must have --snapshot or --latest
    if not snapshot_path and not use_latest:
        print("ERROR: Must specify --snapshot <path> or --latest")
        print()
        print_usage()
        sys.exit(1)

    # Validate ruleset
    if ruleset not in ("safety", "strategy", "all"):
        print(f"ERROR: Invalid ruleset '{ruleset}'. Must be: safety|strategy|all")
        sys.exit(1)

    # Resolve snapshot path
    if use_latest:
        try:
            snapshot_path = find_latest_snapshot()
            print(f"--latest resolved to: {snapshot_path}")
        except FileNotFoundError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
    else:
        if not snapshot_path.is_absolute():
            snapshot_path = PROJECT_ROOT / snapshot_path

    print(f"Snapshot path: {snapshot_path}")
    print(f"Ruleset: {ruleset}")
    print(f"Max ops: {max_ops}")
    print()

    # Load snapshot
    print("Loading snapshot data...")
    try:
        loader = SnapshotLoader(snapshot_path)
        print(f"  Loaded snapshot: {loader.snapshot_id}")
    except FileNotFoundError as e:
        print(f"  ERROR: {e}")
        sys.exit(1)
    print()

    # Load brand terms - CRITICAL: brand_terms MUST be non-empty
    brand_terms_path = CONFIGS_DIR / "brand_terms.json"
    if not brand_terms_path.exists():
        print("=" * 70)
        print("ABORT: Missing required config file")
        print("=" * 70)
        print(f"File not found: {brand_terms_path}")
        print()
        print("The planner requires configs/brand_terms.json to exist with a")
        print("non-empty 'brand_terms' array. Without this, the planner cannot")
        print("distinguish brand keywords from non-brand keywords and may")
        print("incorrectly propose pausing critical brand terms.")
        print()
        print("Create the file with at minimum:")
        print('  {"brand_terms": ["buy comfort direct", "buycomfortdirect", "bcd"]}')
        sys.exit(1)

    brand_config = load_json(brand_terms_path)

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

    # De-duplicate and lowercase
    brand_terms = list(set(t.lower().strip() for t in brand_terms if t.strip()))

    # CRITICAL: Abort if brand_terms is empty
    if not brand_terms:
        print("=" * 70)
        print("ABORT: Empty brand_terms configuration")
        print("=" * 70)
        print(f"Config file exists but contains no brand terms: {brand_terms_path}")
        print()
        print("The planner requires a non-empty 'brand_terms' array. Without this,")
        print("the planner cannot distinguish brand keywords from non-brand keywords")
        print("and may incorrectly propose pausing critical brand terms.")
        print()
        print("Ensure configs/brand_terms.json has a non-empty 'brand_terms' array:")
        print('  {"brand_terms": ["buy comfort direct", "buycomfortdirect", "bcd"]}')
        sys.exit(1)

    print(f"Loaded {len(brand_terms)} brand terms from config:")
    for term in sorted(brand_terms)[:10]:
        print(f"  - {term}")
    if len(brand_terms) > 10:
        print(f"  ... and {len(brand_terms) - 10} more")
    print()

    # Build plan
    print("Running planner rules...")
    builder = PlanBuilder(loader, brand_terms, max_ops=max_ops, ruleset=ruleset)
    plan = builder.build_plan()
    print(f"  Generated {len(plan['operations'])} operations")
    print(f"  Generated {len(builder.findings)} findings")
    print()

    # Ensure output directory exists
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    # Write plan JSON
    plan_filename = f"proposed_changes_{loader.snapshot_id}_{get_utc_timestamp()}.json"
    plan_path = RUNS_DIR / plan_filename
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2)
    print(f"Plan JSON: {plan_path}")

    # Write summary
    summary_filename = plan_filename.replace(".json", "_summary.md")
    summary_path = RUNS_DIR / summary_filename
    write_summary(plan, builder.findings, summary_path)
    print(f"Plan summary: {summary_path}")
    print()

    # Print summary to stdout
    print("=" * 70)
    print("PLAN SUMMARY")
    print("=" * 70)
    summary = plan["summary"]
    print(f"Plan ID:          {plan['plan_id']}")
    print(f"Snapshot:         {plan['snapshot_id']}")
    print(f"Mode:             {plan['mode']}")
    print(f"Total operations: {summary['total_operations']}")
    print(f"Total findings:   {summary['total_findings']}")
    print(f"Risk score:       {summary['risk_score']}")
    print(f"Requires approval: {'Yes' if summary['requires_approval'] else 'No'}")
    print()

    if summary["operations_by_type"]:
        print("Operations by type:")
        for op_type, count in sorted(summary["operations_by_type"].items()):
            print(f"  {op_type}: {count}")
        print()

    if builder.findings:
        print("Findings:")
        for f in builder.findings[:5]:
            print(f"  [{f['level']}] {f['rule_id'].split(':')[-1]}: {f['message'][:70]}")
        if len(builder.findings) > 5:
            print(f"  ... and {len(builder.findings) - 5} more")
        print()

    print("Done.")


if __name__ == "__main__":
    main()
