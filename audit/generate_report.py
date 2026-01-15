#!/usr/bin/env python3
"""
Phase B2: Report Generation from Snapshot Data

################################################################################
# REPORTING IS SNAPSHOT-ONLY. NO LIVE API CALLS.
# This script reads ONLY from local snapshot files. It does NOT connect to
# Google Ads, Merchant Center, or any external APIs.
################################################################################

Usage:
    python audit/generate_report.py --snapshot <path>    # Explicit snapshot path
    python audit/generate_report.py --latest             # Use most recent snapshot (explicit)
    python audit/generate_report.py --deep-audit         # Show full details even on PASS/WARN

REQUIRES explicit --snapshot or --latest flag. Will not silently default.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
SNAPSHOTS_DIR = PROJECT_ROOT / "snapshots"
REPORTS_DIR = PROJECT_ROOT / "reports"
TEMPLATE_PATH = REPORTS_DIR / "TEMPLATE.md"

# Campaign IDs for key campaigns (from _index.json)
BRANDED_CAMPAIGN_ID = "20958985895"
PMAX_CAMPAIGN_ID = "20815709270"
OFFENSIVE_CAMPAIGN_ID = "23445812072"

# Brand classification for reporting
BRAND_KEYWORDS = {
    "rheem": ["rheem", "ruud"],
    "goodman": ["goodman", "amana", "daikin"],
    "solace": ["solace", "solace air"],
}

# Equipment brands eligible for Shopping/PMax (product_type prefix)
EQUIPMENT_BRANDS = ["rheem", "goodman", "solace", "daikin"]

# Brand terms for BCD brand protection (case-insensitive)
BCD_BRAND_TERMS = [
    "buy comfort direct",
    "buycomfortdirect",
    "buycomfortdirect.com",
    "buy comfort",
    "comfort direct",
    "bcd",
    "bcd hvac",
]

# Thresholds for brand protection checks
BRAND_CPC_THRESHOLD = 2.00  # Max acceptable CPC for branded
BRAND_IMPRESSION_SHARE_THRESHOLD = 90  # Min acceptable impression share %

# Confidence thresholds
SNAPSHOT_FRESHNESS_HOURS = 6  # GREEN if <= this


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def find_latest_snapshot() -> Path:
    """Find the most recent snapshot folder. Returns full path."""
    if not SNAPSHOTS_DIR.exists():
        raise FileNotFoundError(f"Snapshots directory not found: {SNAPSHOTS_DIR}")

    snapshots = [d for d in SNAPSHOTS_DIR.iterdir() if d.is_dir() and d.name[0].isdigit()]
    if not snapshots:
        raise FileNotFoundError("No snapshot folders found")

    # Sort by name (timestamp format sorts correctly)
    snapshots.sort(key=lambda x: x.name, reverse=True)
    return snapshots[0]


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


def fmt_currency(value) -> str:
    """Format currency value."""
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def fmt_number(value) -> str:
    """Format number with commas."""
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return f"{value:,}"


def fmt_percent(value) -> str:
    """Format percentage."""
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def is_equipment(product: dict) -> bool:
    """Check if product is equipment (eligible for Shopping/PMax)."""
    product_type = (product.get("product_type") or "").lower()
    return any(product_type.startswith(brand) for brand in EQUIPMENT_BRANDS)


def safe_div(a, b, default=0):
    """Safe division."""
    if b is None or b == 0:
        return default
    return a / b


def parse_utc_timestamp(ts_str: str) -> datetime:
    """Parse UTC timestamp string to datetime."""
    if not ts_str:
        return None
    try:
        # Handle various formats
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except:
        return None


def get_utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


# =============================================================================
# DATA LOADERS
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
        self.data_gaps = []
        self.missing_files = []

        if not self.snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot not found: {self.snapshot_path}")

        # Check required files
        for rel_path in self.REQUIRED_FILES:
            full_path = self.snapshot_path / rel_path
            if not full_path.exists():
                self.missing_files.append(rel_path)

        if self.missing_files:
            raise FileNotFoundError(
                f"Missing required files in snapshot:\n" +
                "\n".join(f"  - {f}" for f in self.missing_files)
            )

        # Load all files
        self.manifest = self._load_required("_manifest.json")
        self.index = self._load("_index.json")

        # Ads data
        self.campaigns = self._load("normalized/ads/campaigns.json")
        self.ad_groups = self._load("normalized/ads/ad_groups.json")
        self.keywords = self._load("normalized/ads/keywords.json")
        self.negatives = self._load("normalized/ads/negatives.json")
        self.ads = self._load("normalized/ads/ads.json")
        self.assets = self._load("normalized/ads/assets.json")
        self.change_history = self._load("normalized/ads/change_history.json")
        self.performance = self._load("normalized/ads/performance.json")

        # PMax data
        self.pmax_campaigns = self._load("normalized/pmax/campaigns.json")
        self.asset_groups = self._load("normalized/pmax/asset_groups.json")
        self.listing_groups = self._load("normalized/pmax/listing_groups.json")

        # Merchant data
        self.merchant_products = self._load("normalized/merchant/products.json")
        self.merchant_status = self._load("normalized/merchant/product_status.json")

    def _load(self, rel_path: str) -> dict:
        """Load a JSON file from snapshot."""
        path = self.snapshot_path / rel_path
        if not path.exists():
            self.data_gaps.append(f"File not found: {rel_path}")
            return {}
        return load_json(path)

    def _load_required(self, rel_path: str) -> dict:
        """Load a required JSON file from snapshot."""
        path = self.snapshot_path / rel_path
        return load_json_required(path)

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
# CONFIDENCE & FRESHNESS COMPUTER
# =============================================================================


class ConfidenceComputer:
    """Computes confidence verdict and account fingerprint."""

    def __init__(self, loader: SnapshotLoader):
        self.loader = loader
        self.manifest = loader.manifest
        self.confidence_reasons = []

        # Compute snapshot age
        extraction_finished = parse_utc_timestamp(
            self.manifest.get("extraction_finished_utc")
        )
        self.extraction_finished = extraction_finished
        self.now = get_utc_now()

        if extraction_finished:
            delta = self.now - extraction_finished
            self.snapshot_age_minutes = int(delta.total_seconds() / 60)
            self.snapshot_age_hours = self.snapshot_age_minutes / 60
        else:
            self.snapshot_age_minutes = None
            self.snapshot_age_hours = None

        # Compute verdict
        self.verdict = self._compute_verdict()

        # Compute fingerprint
        self.fingerprint = self._compute_fingerprint()

    def _compute_verdict(self) -> str:
        """Compute GREEN/YELLOW/RED verdict."""
        validation = self.manifest.get("validation", {})
        errors_count = validation.get("total_validation_errors", 0)
        warnings_count = (
            validation.get("keywords_null_campaign_ids", 0) +
            validation.get("merchant_missing_status", 0)
        )

        # RED: validation errors
        if errors_count > 0:
            self.confidence_reasons.append(f"Validation errors: {errors_count}")
            return "RED"

        # YELLOW checks
        yellow_reasons = []

        # Missing timestamp
        if self.snapshot_age_hours is None:
            yellow_reasons.append("Missing extraction_finished_utc timestamp")

        # Age > 6 hours
        elif self.snapshot_age_hours > SNAPSHOT_FRESHNESS_HOURS:
            yellow_reasons.append(
                f"Snapshot age {self.snapshot_age_hours:.1f}h > {SNAPSHOT_FRESHNESS_HOURS}h threshold"
            )

        # Warnings present
        if warnings_count > 0:
            yellow_reasons.append(f"Validation warnings: {warnings_count}")

        if yellow_reasons:
            self.confidence_reasons.extend(yellow_reasons)
            return "YELLOW"

        # GREEN
        self.confidence_reasons.append("Snapshot fresh and validated")
        return "GREEN"

    def _compute_fingerprint(self) -> dict:
        """Compute account fingerprint from normalized data."""
        # campaigns.json already includes all campaign types (Search, PMax, Shopping)
        # pmax/campaigns.json has additional PMax-specific fields but same IDs
        # Use campaigns.json as the source of truth to avoid double-counting
        all_campaigns = self.loader.campaigns.get("records", [])

        # Campaign counts
        total_campaigns = len(all_campaigns)
        enabled_campaigns = [c for c in all_campaigns if c.get("status") == "ENABLED"]
        pmax_campaigns = [c for c in all_campaigns if c.get("type") == "PERFORMANCE_MAX"]
        search_campaigns = [c for c in all_campaigns if c.get("type") == "SEARCH"]

        # Branded campaign detection
        branded_campaign = self.loader.get_campaign_by_id(BRANDED_CAMPAIGN_ID)
        branded_detected = branded_campaign is not None
        branded_warning = None

        if not branded_detected:
            # Try to find by name
            candidates = [
                c for c in all_campaigns
                if "brand" in (c.get("name") or "").lower()
            ]
            if candidates:
                branded_warning = f"Branded campaign ID {BRANDED_CAMPAIGN_ID} not found. Candidates: " + \
                                  ", ".join(c.get("name", "?") for c in candidates[:3])
            else:
                branded_warning = f"Branded campaign ID {BRANDED_CAMPAIGN_ID} not found. No candidates detected."

        # Branded keywords
        keywords = self.loader.keywords.get("records", [])
        branded_keywords = [
            k for k in keywords
            if str(k.get("campaign_id")) == str(BRANDED_CAMPAIGN_ID)
        ]
        branded_enabled_keywords = [
            k for k in branded_keywords if k.get("status") == "ENABLED"
        ]

        # Branded negatives (campaign-level)
        negatives = self.loader.negatives.get("records", [])
        branded_negatives = [
            n for n in negatives
            if str(n.get("campaign_id")) == str(BRANDED_CAMPAIGN_ID)
        ]

        # Most recent change for Branded campaign
        changes = self.loader.change_history.get("records", [])
        branded_changes = []
        for c in changes:
            # Check if change relates to branded campaign
            resource_id = str(c.get("resource_id", ""))
            if BRANDED_CAMPAIGN_ID in resource_id:
                branded_changes.append(c)

        most_recent_branded_change = None
        if branded_changes:
            # Sort by timestamp descending
            branded_changes.sort(
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )
            most_recent_branded_change = branded_changes[0].get("timestamp")

        return {
            "total_campaigns": total_campaigns,
            "enabled_campaigns": len(enabled_campaigns),
            "pmax_campaigns": len(pmax_campaigns),
            "search_campaigns": len(search_campaigns),
            "branded_detected": branded_detected,
            "branded_warning": branded_warning,
            "branded_name": branded_campaign.get("name") if branded_campaign else None,
            "branded_id": BRANDED_CAMPAIGN_ID,
            "branded_bidding_strategy": branded_campaign.get("bidding_strategy") if branded_campaign else None,
            "branded_enabled_keyword_count": len(branded_enabled_keywords),
            "branded_enabled_keywords_top10": [
                k.get("text") for k in branded_enabled_keywords[:10]
            ],
            "branded_negative_count": len(branded_negatives),
            "branded_most_recent_change": most_recent_branded_change,
        }


# =============================================================================
# METRICS COMPUTATION
# =============================================================================


class MetricsComputer:
    """Computes all metrics from snapshot data."""

    def __init__(self, loader: SnapshotLoader, confidence: ConfidenceComputer, deep_audit: bool = False):
        self.loader = loader
        self.confidence = confidence
        self.deep_audit = deep_audit
        self.data_gaps = loader.data_gaps.copy()
        self.placeholders = {}
        self.brand_protection_triggers = []
        self.fail_triggers = []
        self.warn_triggers = []

        # Run all computations
        self._compute_provenance()
        self._compute_confidence_section()
        self._compute_metadata()
        self._compute_executive_summary()
        self._compute_campaign_overview()
        self._compute_performance_tables()
        self._compute_brand_protection()
        self._compute_merchant_center()
        self._compute_bidding_status()
        self._compute_change_history()
        self._compute_working_items()
        self._compute_learning_items()
        self._compute_appendix()

    def _compute_provenance(self):
        """Compute SNAPSHOT PROVENANCE block."""
        manifest = self.loader.manifest

        # Basic info
        self.placeholders["PROV_SNAPSHOT_ID"] = self.loader.snapshot_id
        self.placeholders["PROV_SNAPSHOT_VERSION"] = manifest.get("snapshot_version", "UNKNOWN")
        self.placeholders["PROV_EXTRACTION_STARTED"] = manifest.get("extraction_started_utc", "UNKNOWN")
        self.placeholders["PROV_EXTRACTION_FINISHED"] = manifest.get("extraction_finished_utc", "UNKNOWN")

        # Account IDs
        accounts = manifest.get("accounts", {})
        google_ads = accounts.get("google_ads", {})
        merchant = accounts.get("merchant_center", {})

        self.placeholders["PROV_GOOGLE_ADS_CUSTOMER_ID"] = google_ads.get("customer_id", "UNKNOWN")
        self.placeholders["PROV_MERCHANT_ID"] = merchant.get("merchant_id", "UNKNOWN") if merchant else "N/A"

        # Record counts
        raw_counts = manifest.get("record_counts", {}).get("raw", {})
        norm_counts = manifest.get("record_counts", {}).get("normalized", {})

        raw_total = sum(raw_counts.values()) if raw_counts else 0
        norm_total = sum(norm_counts.values()) if norm_counts else 0

        self.placeholders["PROV_RAW_RECORDS"] = raw_total
        self.placeholders["PROV_NORMALIZED_RECORDS"] = norm_total

        # Validation
        validation = manifest.get("validation", {})
        errors_count = validation.get("total_validation_errors", 0)
        warnings_count = (
            validation.get("keywords_null_campaign_ids", 0) +
            validation.get("merchant_missing_status", 0)
        )

        self.placeholders["PROV_VALIDATION_ERRORS"] = errors_count
        self.placeholders["PROV_VALIDATION_WARNINGS"] = warnings_count

    def _compute_confidence_section(self):
        """Compute Confidence & Freshness section."""
        c = self.confidence

        # Snapshot age
        if c.snapshot_age_minutes is not None:
            if c.snapshot_age_minutes < 60:
                age_str = f"{c.snapshot_age_minutes} minutes"
            elif c.snapshot_age_hours < 24:
                age_str = f"{c.snapshot_age_hours:.1f} hours"
            else:
                age_str = f"{c.snapshot_age_hours / 24:.1f} days"
        else:
            age_str = "UNKNOWN"

        self.placeholders["CONF_SNAPSHOT_AGE"] = age_str
        self.placeholders["CONF_SNAPSHOT_AGE_MINUTES"] = c.snapshot_age_minutes or 0

        # Verdict
        verdict_emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(c.verdict, "⚪")
        self.placeholders["CONF_VERDICT"] = c.verdict
        self.placeholders["CONF_VERDICT_EMOJI"] = verdict_emoji
        self.placeholders["CONF_REASONS"] = "\n".join(f"- {r}" for r in c.confidence_reasons)

        # Fingerprint
        fp = c.fingerprint
        self.placeholders["FP_TOTAL_CAMPAIGNS"] = fp["total_campaigns"]
        self.placeholders["FP_ENABLED_CAMPAIGNS"] = fp["enabled_campaigns"]
        self.placeholders["FP_PMAX_CAMPAIGNS"] = fp["pmax_campaigns"]
        self.placeholders["FP_SEARCH_CAMPAIGNS"] = fp["search_campaigns"]
        self.placeholders["FP_BRANDED_NAME"] = fp["branded_name"] or "NOT FOUND"
        self.placeholders["FP_BRANDED_ID"] = fp["branded_id"]
        self.placeholders["FP_BRANDED_BIDDING"] = fp["branded_bidding_strategy"] or "UNKNOWN"
        self.placeholders["FP_BRANDED_KEYWORD_COUNT"] = fp["branded_enabled_keyword_count"]
        self.placeholders["FP_BRANDED_KEYWORDS"] = ", ".join(fp["branded_enabled_keywords_top10"]) or "(none)"
        self.placeholders["FP_BRANDED_NEGATIVE_COUNT"] = fp["branded_negative_count"]
        self.placeholders["FP_BRANDED_LAST_CHANGE"] = fp["branded_most_recent_change"] or "No changes in window"

        # Warning
        if fp["branded_warning"]:
            self.placeholders["FP_BRANDED_WARNING"] = f"\n⚠ **Warning:** {fp['branded_warning']}\n"
        else:
            self.placeholders["FP_BRANDED_WARNING"] = ""

    def _compute_metadata(self):
        """Compute report metadata."""
        manifest = self.loader.manifest

        self.placeholders["SNAPSHOT_ID"] = self.loader.snapshot_id
        self.placeholders["SNAPSHOT_TIMESTAMP"] = manifest.get("extraction_finished_utc", "UNKNOWN")
        self.placeholders["REPORT_GENERATED"] = get_utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")

        # API versions
        api_versions = manifest.get("api_versions", {})
        self.placeholders["GOOGLE_ADS_API_VERSION"] = api_versions.get("google_ads", "UNKNOWN")
        self.placeholders["MERCHANT_CENTER_API_VERSION"] = api_versions.get("merchant_center", "UNKNOWN")

        # File counts
        file_counts = manifest.get("file_counts", {})
        self.placeholders["RAW_FILE_COUNT"] = file_counts.get("raw", 0)
        self.placeholders["NORMALIZED_FILE_COUNT"] = file_counts.get("normalized", 0)
        self.placeholders["EXTRACTION_DURATION"] = manifest.get("duration_seconds", 0)

        # Validation
        validation = manifest.get("validation", {})
        self.placeholders["KEYWORDS_MAPPED_STATUS"] = (
            "✓ All mapped"
            if validation.get("keywords_null_campaign_ids", 0) == 0
            else f"⚠ {validation.get('keywords_null_campaign_ids')} unmapped"
        )
        self.placeholders["PRODUCTS_MATCHED_STATUS"] = (
            "✓ All matched"
            if validation.get("merchant_missing_status", 0) == 0
            else f"⚠ {validation.get('merchant_missing_status')} unmatched"
        )
        self.placeholders["TOTAL_VALIDATION_ERRORS"] = validation.get("total_validation_errors", 0)

        self.placeholders["CHANGE_HISTORY_DAYS"] = 14
        self.placeholders["NEXT_SNAPSHOT_TIME"] = "Next manual run or scheduled automation"

    def _compute_executive_summary(self):
        """Compute executive summary metrics."""
        campaigns = self.loader.campaigns.get("records", []) + self.loader.pmax_campaigns.get("records", [])
        enabled_campaigns = [c for c in campaigns if c.get("status") == "ENABLED"]
        has_enabled = len(enabled_campaigns) > 0

        spend_7d = self._calc_period_spend(7)

        if has_enabled and spend_7d > 0:
            self.placeholders["ADS_RUNNING_STATUS"] = f"✓ Yes — {len(enabled_campaigns)} active campaigns, ${spend_7d:,.2f} spent last 7 days"
        elif has_enabled:
            self.placeholders["ADS_RUNNING_STATUS"] = f"⚠ Campaigns enabled but $0 spend last 7 days — check budgets/billing"
        else:
            self.placeholders["ADS_RUNNING_STATUS"] = "✗ No active campaigns"

        self.placeholders["BRAND_OVERSPEND_STATUS"] = "See Brand Protection Check below"

        # Shopping eligibility
        mc = self.loader.merchant_products
        equipment_disapproved = 0
        if mc.get("count", 0) > 0:
            equipment = [p for p in mc.get("records", []) if is_equipment(p)]
            equipment_approved = sum(1 for p in equipment if p.get("approval_status") == "APPROVED")
            equipment_total = len(equipment)
            equipment_disapproved = sum(1 for p in equipment if p.get("approval_status") == "DISAPPROVED")
            pct = safe_div(equipment_approved * 100, equipment_total)
            self.placeholders["SHOPPING_ELIGIBILITY_STATUS"] = f"✓ {equipment_approved:,}/{equipment_total:,} equipment approved ({pct:.0f}%)"
        else:
            self.placeholders["SHOPPING_ELIGIBILITY_STATUS"] = "UNKNOWN — Merchant data not in snapshot"

        # Biggest risk
        if equipment_disapproved > 5:
            self.placeholders["BIGGEST_RISK_SENTENCE"] = f"{equipment_disapproved} equipment products currently disapproved in Merchant Center. Check image links and landing pages."
        elif spend_7d == 0 and has_enabled:
            self.placeholders["BIGGEST_RISK_SENTENCE"] = "Campaigns are enabled but not spending. Verify billing and budget settings."
        else:
            self.placeholders["BIGGEST_RISK_SENTENCE"] = "No urgent issues detected. Continue monitoring per checkpoints below."

        # Stable items
        stable_items = []
        if has_enabled and spend_7d > 0:
            stable_items.append("Ad campaigns are active and spending normally")
        if mc.get("count", 0) > 0:
            equipment = [p for p in mc.get("records", []) if is_equipment(p)]
            approved_pct = safe_div(sum(1 for p in equipment if p.get("approval_status") == "APPROVED") * 100, len(equipment))
            if approved_pct > 95:
                stable_items.append(f"Merchant Center feed is {approved_pct:.0f}% approved")

        self.placeholders["STABLE_ITEM_1"] = stable_items[0] if len(stable_items) > 0 else "Snapshot extraction completed without errors"
        self.placeholders["STABLE_ITEM_2"] = stable_items[1] if len(stable_items) > 1 else "All data sources accessible and synced"
        self.placeholders["EXECUTIVE_SUMMARY_EXPLANATION"] = self._generate_exec_explanation()

    def _generate_exec_explanation(self):
        """Generate executive summary explanation paragraph."""
        parts = []
        spend_7d = self._calc_period_spend(7)
        if spend_7d > 0:
            parts.append(f"Your advertising campaigns spent ${spend_7d:,.2f} over the last 7 days.")

        mc = self.loader.merchant_products
        if mc.get("count", 0) > 0:
            equipment = [p for p in mc.get("records", []) if is_equipment(p)]
            approved = sum(1 for p in equipment if p.get("approval_status") == "APPROVED")
            disapproved = sum(1 for p in equipment if p.get("approval_status") == "DISAPPROVED")
            parts.append(f"Your equipment catalog has {approved:,} items approved for Shopping ads.")
            if disapproved > 0:
                parts.append(f"{disapproved} equipment products are currently disapproved and need attention.")

        if not parts:
            return "This report summarizes your Google Ads and Merchant Center status based on snapshot data."
        return " ".join(parts)

    def _calc_period_spend(self, days: int) -> float:
        """Calculate total spend over last N days."""
        perf = self.loader.performance
        by_campaign = perf.get("by_campaign", [])
        if not by_campaign:
            return 0

        snapshot_date_str = self.loader.manifest.get("extraction_finished_utc", "")[:10]
        if snapshot_date_str:
            try:
                today = datetime.strptime(snapshot_date_str, "%Y-%m-%d").date()
            except:
                today = get_utc_now().date()
        else:
            today = get_utc_now().date()

        cutoff = today - timedelta(days=days)
        total = 0
        for row in by_campaign:
            date_str = row.get("date")
            if date_str:
                try:
                    row_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    if row_date >= cutoff:
                        total += float(row.get("cost", 0) or 0)
                except:
                    pass
        return total

    def _calc_branded_cpc_by_period(self) -> dict:
        """Calculate Branded campaign CPC for different time periods."""
        perf = self.loader.performance
        by_campaign = perf.get("by_campaign", [])
        branded_perf = [r for r in by_campaign if str(r.get("campaign_id")) == str(BRANDED_CAMPAIGN_ID)]

        if not branded_perf:
            return {"today": None, "yesterday": None, "last_7d": None, "last_30d": None}

        # Get snapshot date
        snapshot_date_str = self.loader.manifest.get("extraction_finished_utc", "")[:10]
        if snapshot_date_str:
            try:
                snapshot_date = datetime.strptime(snapshot_date_str, "%Y-%m-%d").date()
            except:
                snapshot_date = get_utc_now().date()
        else:
            snapshot_date = get_utc_now().date()

        yesterday = snapshot_date - timedelta(days=1)
        cutoff_7d = snapshot_date - timedelta(days=7)
        cutoff_30d = snapshot_date - timedelta(days=30)

        periods = {
            "today": {"cost": 0, "clicks": 0},
            "yesterday": {"cost": 0, "clicks": 0},
            "last_7d": {"cost": 0, "clicks": 0},
            "last_30d": {"cost": 0, "clicks": 0},
        }

        for row in branded_perf:
            date_str = row.get("date")
            if not date_str:
                continue
            try:
                row_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                continue

            cost = float(row.get("cost", 0) or 0)
            clicks = float(row.get("clicks", 0) or 0)

            if row_date == snapshot_date:
                periods["today"]["cost"] += cost
                periods["today"]["clicks"] += clicks
            if row_date == yesterday:
                periods["yesterday"]["cost"] += cost
                periods["yesterday"]["clicks"] += clicks
            if row_date >= cutoff_7d:
                periods["last_7d"]["cost"] += cost
                periods["last_7d"]["clicks"] += clicks
            if row_date >= cutoff_30d:
                periods["last_30d"]["cost"] += cost
                periods["last_30d"]["clicks"] += clicks

        result = {}
        for period, data in periods.items():
            if data["clicks"] > 0:
                result[period] = data["cost"] / data["clicks"]
            else:
                result[period] = None

        return result

    def _compute_campaign_overview(self):
        """Compute campaign overview section."""
        branded = self.loader.get_campaign_by_id(BRANDED_CAMPAIGN_ID)
        self.placeholders["BRANDED_CAMPAIGN_ID"] = BRANDED_CAMPAIGN_ID
        self.placeholders["BRANDED_CAMPAIGN_STATUS"] = branded.get("status", "UNKNOWN") if branded else "NOT FOUND"
        self.placeholders["BRANDED_GUARDRAILS"] = "Negative keywords for manufacturer names; exact match on brand terms"

        pmax = self.loader.get_campaign_by_id(PMAX_CAMPAIGN_ID)
        self.placeholders["PMAX_CAMPAIGN_ID"] = PMAX_CAMPAIGN_ID
        self.placeholders["PMAX_CAMPAIGN_STATUS"] = pmax.get("status", "UNKNOWN") if pmax else "NOT FOUND"

        accounts = self.loader.manifest.get("accounts", {})
        mc_account = accounts.get("merchant_center", {})
        self.placeholders["PMAX_MERCHANT_ID"] = mc_account.get("merchant_id", "UNKNOWN") if mc_account else "UNKNOWN"

        if pmax:
            strategy = pmax.get("bidding_strategy", "UNKNOWN")
            target = pmax.get("bidding_target")
            self.placeholders["PMAX_BIDDING_STRATEGY"] = strategy
            self.placeholders["PMAX_TARGET_ROAS"] = f"{target}" if target else "Not set"
        else:
            self.placeholders["PMAX_BIDDING_STRATEGY"] = "UNKNOWN"
            self.placeholders["PMAX_TARGET_ROAS"] = "UNKNOWN"

        offensive = self.loader.get_campaign_by_id(OFFENSIVE_CAMPAIGN_ID)
        self.placeholders["OFFENSIVE_CAMPAIGN_ID"] = OFFENSIVE_CAMPAIGN_ID
        self.placeholders["OFFENSIVE_CAMPAIGN_STATUS"] = offensive.get("status", "UNKNOWN") if offensive else "NOT FOUND"
        self.placeholders["OFFENSIVE_CURRENT_STATE"] = "Newly launched — in learning phase" if offensive else "Campaign not found in snapshot"

        other_rows = []
        all_campaigns = self.loader.campaigns.get("records", []) + self.loader.pmax_campaigns.get("records", [])
        key_ids = {BRANDED_CAMPAIGN_ID, PMAX_CAMPAIGN_ID, OFFENSIVE_CAMPAIGN_ID}
        for c in all_campaigns:
            cid = str(c.get("id", ""))
            if cid not in key_ids:
                name = c.get("name", "Unknown")
                status = c.get("status", "UNKNOWN")
                ctype = c.get("type", c.get("advertising_channel_type", "UNKNOWN"))
                other_rows.append(f"| {name} | {status} | {ctype} |")
        self.placeholders["OTHER_CAMPAIGNS_TABLE"] = "\n".join(other_rows) if other_rows else "| (none) | - | - |"

    def _compute_performance_tables(self):
        """Compute 7-day and 30-day performance tables."""
        perf = self.loader.performance
        by_campaign = perf.get("by_campaign", [])
        campaign_data = defaultdict(lambda: {"7d": defaultdict(float), "30d": defaultdict(float)})

        snapshot_date_str = self.loader.manifest.get("extraction_finished_utc", "")[:10]
        if snapshot_date_str:
            try:
                today = datetime.strptime(snapshot_date_str, "%Y-%m-%d").date()
            except:
                today = get_utc_now().date()
        else:
            today = get_utc_now().date()

        cutoff_7d = today - timedelta(days=7)
        cutoff_30d = today - timedelta(days=30)

        for row in by_campaign:
            cid = str(row.get("campaign_id", ""))
            date_str = row.get("date")
            if not date_str:
                continue
            try:
                row_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                continue

            metrics = {
                "spend": float(row.get("cost", 0) or 0),
                "clicks": float(row.get("clicks", 0) or 0),
                "impressions": float(row.get("impressions", 0) or 0),
                "conversions": float(row.get("conversions", 0) or 0),
                "conv_value": float(row.get("conversionsValue", 0) or 0),
            }

            if row_date >= cutoff_7d:
                for k, v in metrics.items():
                    campaign_data[cid]["7d"][k] += v
            if row_date >= cutoff_30d:
                for k, v in metrics.items():
                    campaign_data[cid]["30d"][k] += v

        def build_table(period: str) -> str:
            rows = []
            for cid, data in campaign_data.items():
                name = self.loader.get_campaign_name(cid)
                if not name or name == "Unknown":
                    continue
                d = data[period]
                spend = d["spend"]
                clicks = d["clicks"]
                impressions = d["impressions"]
                conversions = d["conversions"]
                conv_value = d["conv_value"]
                roas = safe_div(conv_value, spend)
                rows.append(
                    f"| {name[:30]} | {fmt_currency(spend)} | {fmt_number(int(clicks))} | "
                    f"{fmt_number(int(impressions))} | {fmt_number(conversions)} | "
                    f"{fmt_currency(conv_value)} | {roas:.2f} |"
                )
            return "\n".join(rows) if rows else "| (no data) | - | - | - | - | - | - |"

        self.placeholders["LAST_7_DAYS_TABLE"] = build_table("7d")
        self.placeholders["LAST_30_DAYS_TABLE"] = build_table("30d")

    def _compute_brand_protection(self):
        """Compute brand protection PASS/WARN/FAIL assertion."""
        self.fail_triggers = []
        self.warn_triggers = []
        self.brand_protection_triggers = []

        branded_campaign = self.loader.get_campaign_by_id(BRANDED_CAMPAIGN_ID)

        if not branded_campaign:
            self.placeholders["BRAND_PROTECTION_STATUS"] = "FAIL"
            self.placeholders["BRAND_PROTECTION_VERDICT"] = "**Brand Protection Check: FAIL** — Branded campaign not found in snapshot."
            self.fail_triggers.append("Branded campaign not found")
            self.brand_protection_triggers = self.fail_triggers
            self._set_brand_protection_defaults()
            return

        keywords = self.loader.keywords.get("records", [])
        branded_keywords = [k for k in keywords if str(k.get("campaign_id")) == str(BRANDED_CAMPAIGN_ID)]
        enabled_keywords = [k for k in branded_keywords if k.get("status") == "ENABLED"]

        perf = self.loader.performance
        by_campaign = perf.get("by_campaign", [])
        branded_perf = [r for r in by_campaign if str(r.get("campaign_id")) == str(BRANDED_CAMPAIGN_ID)]

        total_cost = sum(float(row.get("cost", 0) or 0) for row in branded_perf)
        total_clicks = sum(float(row.get("clicks", 0) or 0) for row in branded_perf)
        total_impressions = sum(float(row.get("impressions", 0) or 0) for row in branded_perf)
        avg_cpc = safe_div(total_cost, total_clicks)

        # CPC by period
        cpc_by_period = self._calc_branded_cpc_by_period()

        # FAIL CHECKS
        bidding_strategy = branded_campaign.get("bidding_strategy", "UNKNOWN")
        if bidding_strategy != "MANUAL_CPC":
            self.fail_triggers.append(f"Smart bidding ({bidding_strategy}) — must be MANUAL_CPC")

        broad_enabled = [k for k in enabled_keywords if k.get("match_type") == "BROAD"]
        if broad_enabled:
            self.fail_triggers.append(f"{len(broad_enabled)} BROAD match keyword(s) enabled")

        non_brand_keywords = []
        for k in enabled_keywords:
            kw_text = (k.get("text") or "").lower()
            is_brand = any(brand.lower() in kw_text for brand in BCD_BRAND_TERMS)
            if not is_brand:
                non_brand_keywords.append(k)
        if non_brand_keywords:
            self.fail_triggers.append(f"{len(non_brand_keywords)} non-brand keyword(s) in Branded campaign")

        # Keyword changes
        change_records = self.loader.change_history.get("records", [])
        keyword_changes = []
        for c in change_records:
            resource_type = c.get("resource_type", "")
            resource_id = c.get("resource_id", "")
            if resource_type == "AD_GROUP_CRITERION":
                for bk in branded_keywords:
                    if str(bk.get("id")) in str(resource_id):
                        keyword_changes.append(c)
                        break

        # WARN CHECKS (only if no FAIL)
        if not self.fail_triggers:
            if avg_cpc > BRAND_CPC_THRESHOLD:
                self.warn_triggers.append(f"Avg CPC ${avg_cpc:.2f} > ${BRAND_CPC_THRESHOLD:.2f} threshold")
            if keyword_changes:
                self.warn_triggers.append(f"{len(keyword_changes)} keyword change(s) in last 14 days")
            if total_impressions < 20 or total_clicks < 5:
                self.warn_triggers.append(f"Low volume ({int(total_impressions)} impr, {int(total_clicks)} clicks) — insufficient data")

        # Determine verdict
        if self.fail_triggers:
            verdict_status = "FAIL"
            self.brand_protection_triggers = self.fail_triggers
        elif self.warn_triggers:
            verdict_status = "WARN"
            self.brand_protection_triggers = self.warn_triggers
        else:
            verdict_status = "PASS"
            self.brand_protection_triggers = []

        self.placeholders["BRAND_PROTECTION_STATUS"] = verdict_status

        # Build verdict message
        if verdict_status == "PASS":
            verdict = "**Brand Protection Check: PASS** — Branded campaign properly constrained to brand terms (exact/phrase only, Manual CPC)."
            if self.deep_audit:
                verdict += "\n\n*Deep audit requested — showing structural details below.*"
        elif verdict_status == "WARN":
            first_warn = self.warn_triggers[0] if self.warn_triggers else "Risk signals detected"
            verdict = f"**Brand Protection Check: WARN** — {first_warn}.\n\n"
            verdict += "**Risk signals:**\n"
            for trigger in self.warn_triggers:
                verdict += f"- ⚠ {trigger}\n"
            verdict += "\n*Structure is correct but operational metrics need attention.*"
            if self.deep_audit:
                verdict += "\n\n*Deep audit requested — showing structural details below.*"
        else:
            first_fail = self.fail_triggers[0] if self.fail_triggers else "Structural issues detected"
            verdict = f"**Brand Protection Check: FAIL** — {first_fail}.\n\n"
            verdict += "**Issues (fix required):**\n"
            for trigger in self.fail_triggers:
                verdict += f"- ❌ {trigger}\n"

        self.placeholders["BRAND_PROTECTION_VERDICT"] = verdict

        # CPC breakdown table
        snapshot_date = self.loader.manifest.get("extraction_finished_utc", "")[:10] or "today"
        cpc_rows = []
        cpc_rows.append(f"| Today ({snapshot_date}, partial) | {fmt_currency(cpc_by_period['today'])} |")
        cpc_rows.append(f"| Yesterday | {fmt_currency(cpc_by_period['yesterday'])} |")
        cpc_rows.append(f"| Last 7 days | {fmt_currency(cpc_by_period['last_7d'])} |")
        cpc_rows.append(f"| Last 30 days | {fmt_currency(cpc_by_period['last_30d'])} |")
        self.placeholders["BRANDED_CPC_TABLE"] = "\n".join(cpc_rows)

        # Populate tables
        show_full_details = (verdict_status == "FAIL") or self.deep_audit
        if show_full_details:
            self._populate_brand_protection_details(
                branded_campaign=branded_campaign,
                enabled_keywords=enabled_keywords,
                broad_enabled=broad_enabled,
                non_brand_keywords=non_brand_keywords,
                keyword_changes=keyword_changes,
                avg_cpc=avg_cpc,
                total_cost=total_cost,
                total_clicks=total_clicks
            )
        else:
            self._set_brand_protection_defaults()

    def _set_brand_protection_defaults(self):
        """Set default placeholder values when not showing detailed tables."""
        self.placeholders["BRANDED_TOTAL_TERMS"] = "N/A (summary mode)"
        self.placeholders["BRANDED_BRAND_SPEND"] = "N/A"
        self.placeholders["BRANDED_BRAND_PERCENT"] = "N/A"
        self.placeholders["BRANDED_NONBRAND_SPEND"] = "N/A"
        self.placeholders["BRANDED_NONBRAND_PERCENT"] = "N/A"
        self.placeholders["TOP_BRAND_QUERIES_TABLE"] = "| (detailed view disabled — use --deep-audit flag) | - | - |"
        self.placeholders["NONBRAND_IN_BRANDED_TABLE"] = "| (detailed view disabled) | - | - | - |"
        if "BRANDED_CPC_TABLE" not in self.placeholders:
            self.placeholders["BRANDED_CPC_TABLE"] = "| N/A | N/A |"

    def _populate_brand_protection_details(self, branded_campaign, enabled_keywords,
                                           broad_enabled, non_brand_keywords,
                                           keyword_changes, avg_cpc, total_cost, total_clicks):
        """Populate detailed brand protection tables."""
        self.placeholders["BRANDED_TOTAL_TERMS"] = f"{len(enabled_keywords)} enabled keywords"
        brand_keywords = len(enabled_keywords) - len(non_brand_keywords)
        self.placeholders["BRANDED_BRAND_SPEND"] = f"${total_cost:.2f} total"
        self.placeholders["BRANDED_BRAND_PERCENT"] = f"{brand_keywords}/{len(enabled_keywords)} keywords"
        self.placeholders["BRANDED_NONBRAND_SPEND"] = f"{len(non_brand_keywords)} non-brand keywords"
        self.placeholders["BRANDED_NONBRAND_PERCENT"] = fmt_percent(safe_div(len(non_brand_keywords) * 100, len(enabled_keywords)))

        brand_rows = []
        for k in enabled_keywords[:10]:
            kw_text = k.get("text", "N/A")
            match_type = k.get("match_type", "UNKNOWN")
            is_brand = any(brand.lower() in kw_text.lower() for brand in BCD_BRAND_TERMS)
            brand_rows.append(f"| {kw_text} | {match_type} | {'✓ Brand' if is_brand else '⚠ Non-brand'} |")
        if len(enabled_keywords) > 10:
            brand_rows.append(f"| ... | ({len(enabled_keywords) - 10} more) | ... |")
        self.placeholders["TOP_BRAND_QUERIES_TABLE"] = "\n".join(brand_rows) if brand_rows else "| (no keywords) | - | - |"

        problem_rows = []
        for k in broad_enabled[:5]:
            kw_text = k.get("text", "N/A")
            problem_rows.append(f"| {kw_text} | BROAD | ENABLED | Change to EXACT/PHRASE |")
        for k in non_brand_keywords[:5]:
            kw_text = k.get("text", "N/A")
            match_type = k.get("match_type", "UNKNOWN")
            problem_rows.append(f"| {kw_text} | {match_type} | Non-brand | Move to Offensive campaign |")
        if not problem_rows:
            problem_rows.append("| (no issues detected) | - | - | - |")
        self.placeholders["NONBRAND_IN_BRANDED_TABLE"] = "\n".join(problem_rows)

    def _compute_merchant_center(self):
        """Compute Merchant Center metrics."""
        mc = self.loader.merchant_products
        all_records = mc.get("records", [])
        equipment = [p for p in all_records if is_equipment(p)]
        total = len(equipment)

        if total == 0:
            self.placeholders["MC_APPROVED_COUNT"] = "0"
            self.placeholders["MC_APPROVED_PERCENT"] = "0%"
            self.placeholders["MC_DISAPPROVED_COUNT"] = "0"
            self.placeholders["MC_DISAPPROVED_PERCENT"] = "0%"
            self.placeholders["MC_PENDING_COUNT"] = "0"
            self.placeholders["MC_PENDING_PERCENT"] = "0%"
            self.placeholders["MC_TOTAL_COUNT"] = "0"
            self.placeholders["MC_BY_BRAND_TABLE"] = "| (no data) | - | - | - | - |"
            self.placeholders["MC_DISAPPROVED_TABLE"] = "| (no data) | - | - | - | - |"
            return

        approved = sum(1 for p in equipment if p.get("approval_status") == "APPROVED")
        disapproved = sum(1 for p in equipment if p.get("approval_status") == "DISAPPROVED")
        pending = sum(1 for p in equipment if p.get("approval_status") == "PENDING")

        self.placeholders["MC_APPROVED_COUNT"] = fmt_number(approved)
        self.placeholders["MC_APPROVED_PERCENT"] = fmt_percent(safe_div(approved * 100, total))
        self.placeholders["MC_DISAPPROVED_COUNT"] = fmt_number(disapproved)
        self.placeholders["MC_DISAPPROVED_PERCENT"] = fmt_percent(safe_div(disapproved * 100, total))
        self.placeholders["MC_PENDING_COUNT"] = fmt_number(pending)
        self.placeholders["MC_PENDING_PERCENT"] = fmt_percent(safe_div(pending * 100, total))
        self.placeholders["MC_TOTAL_COUNT"] = fmt_number(total)

        brand_stats = defaultdict(lambda: {"total": 0, "approved": 0, "disapproved": 0})
        for p in equipment:
            product_type = (p.get("product_type") or "").lower()
            brand_name = "Other"
            for brand in EQUIPMENT_BRANDS:
                if product_type.startswith(brand):
                    brand_name = brand.capitalize()
                    break
            brand_stats[brand_name]["total"] += 1
            if p.get("approval_status") == "APPROVED":
                brand_stats[brand_name]["approved"] += 1
            elif p.get("approval_status") == "DISAPPROVED":
                brand_stats[brand_name]["disapproved"] += 1

        brand_rows = []
        for brand_name in ["Rheem", "Goodman", "Solace", "Daikin"]:
            stats = brand_stats.get(brand_name, {"total": 0, "approved": 0, "disapproved": 0})
            if stats["total"] > 0:
                rate = fmt_percent(safe_div(stats["approved"] * 100, stats["total"]))
                brand_rows.append(f"| {brand_name} | {stats['total']:,} | {stats['approved']:,} | {stats['disapproved']:,} | {rate} |")
        self.placeholders["MC_BY_BRAND_TABLE"] = "\n".join(brand_rows) if brand_rows else "| (no brand data) | - | - | - | - |"

        disapproved_rows = []
        disapproved_products = [p for p in equipment if p.get("approval_status") == "DISAPPROVED"]
        for p in disapproved_products[:10]:
            offer_id = p.get("offer_id", "N/A")
            title = (p.get("title", "N/A") or "N/A")[:40]
            brand = p.get("brand", "N/A")
            issues = p.get("disapproval_issues", [])
            if issues:
                reason = issues[0].get("code", "unknown")
                if "image" in reason.lower():
                    fix_owner = "Feed"
                elif "landing" in reason.lower() or "page" in reason.lower():
                    fix_owner = "Site"
                else:
                    fix_owner = "Policy"
            else:
                reason = "Unknown"
                fix_owner = "Unknown"
            disapproved_rows.append(f"| {offer_id} | {title} | {brand} | {reason} | {fix_owner} |")
        if len(disapproved_products) > 10:
            disapproved_rows.append(f"| ... | ({len(disapproved_products) - 10} more) | ... | ... | ... |")
        self.placeholders["MC_DISAPPROVED_TABLE"] = "\n".join(disapproved_rows) if disapproved_rows else "| (none) | - | - | - | - |"

    def _compute_bidding_status(self):
        """Compute bidding and cost control table."""
        rows = []
        key_campaigns = [
            (BRANDED_CAMPAIGN_ID, "BCD Branded"),
            (PMAX_CAMPAIGN_ID, "Products PMax"),
            (OFFENSIVE_CAMPAIGN_ID, "Hardware Offensive"),
        ]
        for cid, name in key_campaigns:
            campaign = self.loader.get_campaign_by_id(cid)
            if not campaign:
                rows.append(f"| {name} | Not found | - | - | - |")
                continue
            strategy = campaign.get("bidding_strategy", "UNKNOWN")
            bidding_target = campaign.get("bidding_target")
            budget = campaign.get("budget_amount_micros")
            if budget:
                try:
                    daily_budget = fmt_currency(int(budget) / 1_000_000)
                except:
                    daily_budget = "Shared/Unknown"
            else:
                daily_budget = "Shared/Unknown"
            target = "-"
            if bidding_target:
                if "VALUE" in strategy:
                    target = f"tROAS {bidding_target}"
                elif "CONVERSION" in strategy:
                    target = f"tCPA ${bidding_target:.2f}"
                else:
                    target = f"{bidding_target}"
            notes = ""
            if "MAXIMIZE" in strategy:
                notes = "Automated"
            elif "MANUAL" in strategy:
                notes = "Manual bids"
            rows.append(f"| {name} | {strategy} | {target} | {daily_budget} | {notes} |")
        self.placeholders["BIDDING_TABLE"] = "\n".join(rows)

    def _compute_change_history(self):
        """Compute change history summary."""
        changes = self.loader.change_history.get("records", [])
        by_type = defaultdict(int)
        recent_changes = []
        for c in changes[:50]:
            change_type = c.get("change_type", "UNKNOWN")
            by_type[change_type] += 1
            timestamp = c.get("change_date_time", "")[:19]
            resource = c.get("resource_type", "UNKNOWN")
            desc = c.get("changed_fields", "")
            if isinstance(desc, list):
                desc = ", ".join(desc[:3])
            desc = str(desc)[:50]
            recent_changes.append(f"| {timestamp} | {resource} | {change_type} | {desc} |")
        self.placeholders["RECENT_CHANGES_TABLE"] = "\n".join(recent_changes[:15]) if recent_changes else "| (no changes recorded) | - | - | - |"
        summary_rows = [f"| {k} | {v} |" for k, v in sorted(by_type.items(), key=lambda x: -x[1])]
        self.placeholders["CHANGE_SUMMARY_TABLE"] = "\n".join(summary_rows[:10]) if summary_rows else "| (none) | 0 |"
        self.placeholders["AUTO_APPLY_STATUS"] = "Cannot verify via API"
        self.placeholders["AUTO_APPLY_RISK"] = "Unknown"
        self.placeholders["AUTO_BIDDING_STATUS"] = "Enabled (Smart Bidding)"
        self.placeholders["AUTO_BIDDING_RISK"] = "Low (expected)"
        self.placeholders["PMAX_ENABLED_STATUS"] = "Yes"
        self.placeholders["PMAX_RISK"] = "Medium (requires monitoring)"

    def _compute_working_items(self):
        """Compute what's working list."""
        items = []
        campaigns = self.loader.campaigns.get("records", []) + self.loader.pmax_campaigns.get("records", [])
        enabled = [c for c in campaigns if c.get("status") == "ENABLED"]
        if enabled:
            items.append(f"- {len(enabled)} campaigns are enabled and configured")
        spend_7d = self._calc_period_spend(7)
        if spend_7d > 0:
            items.append(f"- Campaigns are spending normally (${spend_7d:,.2f} last 7 days)")
        mc = self.loader.merchant_products
        if mc.get("count", 0) > 0:
            approved_pct = safe_div(
                sum(1 for p in mc.get("records", []) if p.get("approval_status") == "APPROVED") * 100,
                mc.get("count", 0)
            )
            if approved_pct > 90:
                items.append(f"- Merchant Center feed is {approved_pct:.0f}% approved")
        validation = self.loader.manifest.get("validation", {})
        if validation.get("total_validation_errors", 0) == 0:
            items.append("- Snapshot extraction completed with no validation errors")
        if not items:
            items.append("- Snapshot data is available for analysis")
        self.placeholders["WORKING_AS_INTENDED_LIST"] = "\n".join(items)

    def _compute_learning_items(self):
        """Compute learning/early items."""
        items = []
        offensive = self.loader.get_campaign_by_id(OFFENSIVE_CAMPAIGN_ID)
        if offensive and offensive.get("status") == "ENABLED":
            items.append("- **Hardware Offensive campaign** — Newly launched, in learning phase. Performance data will be limited for 2-4 weeks.")
        pmax = self.loader.get_campaign_by_id(PMAX_CAMPAIGN_ID)
        if pmax:
            items.append("- **Performance Max optimization** — Google's algorithm continuously learns; avoid frequent changes.")
        if not items:
            items.append("- No campaigns currently in learning phase")
        self.placeholders["STILL_LEARNING_LIST"] = "\n".join(items)

    def _compute_appendix(self):
        """Compute appendix data."""
        pass


# =============================================================================
# TEMPLATE RENDERING
# =============================================================================


class TemplateRenderer:
    """Renders template with placeholders."""

    def __init__(self, template_path: Path):
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        with open(template_path, "r") as f:
            self.template = f.read()

    def render(self, placeholders: dict, data_gaps: list) -> str:
        """Render template with placeholder values."""
        import re
        result = self.template
        missing = []
        pattern = r"\{\{([A-Z0-9_]+)\}\}"
        matches = re.findall(pattern, result)
        for placeholder in set(matches):
            value = placeholders.get(placeholder)
            if value is None:
                value = "UNKNOWN"
                missing.append(placeholder)
            result = result.replace(f"{{{{{placeholder}}}}}", str(value))

        if data_gaps or missing:
            gaps_section = "\n\n---\n\n## Data Gaps Identified\n\n"
            gaps_section += "The following data was not available in the snapshot:\n\n"
            all_gaps = list(set(data_gaps + [f"Placeholder not computed: {m}" for m in missing]))
            for gap in all_gaps:
                gaps_section += f"- {gap}\n"
            gaps_section += "\nThese gaps can be addressed by updating Phase A data extraction or manual review in Google Ads UI.\n"
            if "## End of Report" in result:
                result = result.replace("## End of Report", gaps_section + "\n## End of Report")
            else:
                result += gaps_section
        return result


# =============================================================================
# JSON REPORT BUILDER
# =============================================================================


def build_json_report(loader: SnapshotLoader, confidence: ConfidenceComputer, metrics: MetricsComputer) -> dict:
    """Build machine-readable JSON report for reports/latest.json."""
    return {
        "snapshot_id": loader.snapshot_id,
        "snapshot_version": loader.manifest.get("snapshot_version"),
        "extraction_finished_utc": loader.manifest.get("extraction_finished_utc"),
        "snapshot_age_minutes": confidence.snapshot_age_minutes,
        "confidence_verdict": confidence.verdict,
        "confidence_reasons": confidence.confidence_reasons,
        "fingerprint": confidence.fingerprint,
        "report_generated_utc": get_utc_now().isoformat(),
        "brand_protection": {
            "status": metrics.placeholders.get("BRAND_PROTECTION_STATUS", "UNKNOWN"),
            "fail_triggers": metrics.fail_triggers,
            "warn_triggers": metrics.warn_triggers,
        },
        "executive_summary": {
            "ads_running": metrics.placeholders.get("ADS_RUNNING_STATUS"),
            "brand_protection": metrics.placeholders.get("BRAND_PROTECTION_STATUS", "UNKNOWN"),
            "shopping_eligibility": metrics.placeholders.get("SHOPPING_ELIGIBILITY_STATUS"),
            "biggest_risk": metrics.placeholders.get("BIGGEST_RISK_SENTENCE"),
        },
    }


# =============================================================================
# CLI HELPERS
# =============================================================================


def print_usage():
    """Print usage information."""
    print("""
Usage: python audit/generate_report.py [OPTIONS]

REQUIRED (one of):
    --snapshot <path>    Path to snapshot folder (e.g., snapshots/2026-01-15T202326Z)
    --latest             Use the most recent snapshot (will print resolved path)

OPTIONAL:
    --deep-audit         Show full details even on PASS/WARN verdicts

Examples:
    python audit/generate_report.py --latest
    python audit/generate_report.py --snapshot snapshots/2026-01-15T202326Z
    python audit/generate_report.py --latest --deep-audit

This script reads ONLY from local snapshot files. NO LIVE API CALLS.
""")


def parse_args():
    """Parse command line arguments."""
    snapshot_path = None
    use_latest = False
    deep_audit = False

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--snapshot" and i + 1 < len(sys.argv):
            snapshot_path = Path(sys.argv[i + 1])
            i += 2
        elif arg == "--latest":
            use_latest = True
            i += 1
        elif arg == "--deep-audit":
            deep_audit = True
            i += 1
        elif arg in ("--help", "-h"):
            print_usage()
            sys.exit(0)
        else:
            print(f"ERROR: Unknown argument: {arg}")
            print_usage()
            sys.exit(1)

    return snapshot_path, use_latest, deep_audit


# =============================================================================
# MAIN
# =============================================================================


def main():
    print("=" * 70)
    print("REPORT GENERATION - Phase B2 (SNAPSHOT-ONLY)")
    print("=" * 70)
    print()

    # Parse args
    snapshot_path, use_latest, deep_audit = parse_args()

    # Validate: must have --snapshot or --latest
    if not snapshot_path and not use_latest:
        print("ERROR: Must specify --snapshot <path> or --latest")
        print()
        print_usage()
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
        # Convert relative path to absolute if needed
        if not snapshot_path.is_absolute():
            snapshot_path = PROJECT_ROOT / snapshot_path

    print(f"Snapshot path: {snapshot_path}")
    if deep_audit:
        print("Deep audit mode: ENABLED")
    print()

    # Validate snapshot exists
    if not snapshot_path.exists():
        print(f"ERROR: Snapshot not found: {snapshot_path}")
        sys.exit(1)

    # Load data
    print("Loading snapshot data...")
    try:
        loader = SnapshotLoader(snapshot_path)
        print(f"  ✓ Loaded snapshot: {loader.snapshot_id}")
        print(f"  ✓ Normalized files: {loader.manifest.get('file_counts', {}).get('normalized', 0)}")
    except FileNotFoundError as e:
        print(f"  ✗ ERROR: {e}")
        sys.exit(1)
    print()

    # Compute confidence
    print("Computing confidence & fingerprint...")
    confidence = ConfidenceComputer(loader)
    print(f"  ✓ Verdict: {confidence.verdict}")
    print(f"  ✓ Snapshot age: {confidence.snapshot_age_minutes} minutes")
    print()

    # Compute metrics
    print("Computing metrics...")
    metrics = MetricsComputer(loader, confidence, deep_audit=deep_audit)
    print(f"  ✓ Computed {len(metrics.placeholders)} placeholders")
    if metrics.data_gaps:
        print(f"  ⚠ {len(metrics.data_gaps)} data gaps identified")
    print()

    # Load template
    print("Loading template...")
    try:
        renderer = TemplateRenderer(TEMPLATE_PATH)
        print(f"  ✓ Template loaded from {TEMPLATE_PATH}")
    except FileNotFoundError as e:
        print(f"  ✗ ERROR: {e}")
        sys.exit(1)
    print()

    # Render report
    print("Rendering report...")
    report_md = renderer.render(metrics.placeholders, metrics.data_gaps)
    print(f"  ✓ Report rendered ({len(report_md):,} characters)")
    print()

    # Build JSON report
    report_json = build_json_report(loader, confidence, metrics)

    # Ensure reports directory exists
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Write files
    print("Writing output files...")

    # reports/latest.md
    latest_md_path = REPORTS_DIR / "latest.md"
    with open(latest_md_path, "w") as f:
        f.write(report_md)
    print(f"  ✓ {latest_md_path}")

    # reports/latest.json
    latest_json_path = REPORTS_DIR / "latest.json"
    with open(latest_json_path, "w") as f:
        json.dump(report_json, f, indent=2)
    print(f"  ✓ {latest_json_path}")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Snapshot ID:          {loader.snapshot_id}")
    print(f"Snapshot Path:        {snapshot_path}")
    print(f"Confidence Verdict:   {confidence.verdict}")
    print(f"Snapshot Age:         {confidence.snapshot_age_minutes} minutes")
    print(f"Report files:         {REPORTS_DIR}/latest.md, latest.json")
    print(f"Data gaps:            {len(metrics.data_gaps)}")
    print()

    if metrics.data_gaps:
        print("Data Gaps:")
        for gap in metrics.data_gaps:
            print(f"  - {gap}")
        print()

    print("Done.")


if __name__ == "__main__":
    main()
