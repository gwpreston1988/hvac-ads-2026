#!/usr/bin/env python3
"""
Phase C3: Apply Changes Engine

################################################################################
# SAFETY-CRITICAL COMPONENT
################################################################################
#
# This script executes approved change plans against live APIs.
# Default behavior is DRY_RUN (no mutations).
#
# NEVER:
#   - Infer intent
#   - Modify plans
#   - Generate plans
#   - Guess preconditions
#   - Run without explicit confirmation
#
# ALWAYS:
#   - Validate all inputs
#   - Check all preconditions
#   - Log all actions
#   - Abort on any error (by default)
#   - Leave an audit trail
#
################################################################################

Usage:
    bin/apply plans/runs/<plan>.json               # DRY_RUN (default)
    bin/apply plans/runs/<plan>.json --execute     # LIVE WRITES (dangerous)

Output:
    plans/runs/<plan_id>.results.json
    plans/runs/<plan_id>.results.md
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests
from dotenv import load_dotenv

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
CORE_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = CORE_DIR.parent
SNAPSHOTS_DIR = PROJECT_ROOT / "snapshots"
PLANS_DIR = PROJECT_ROOT / "plans"

GOOGLE_ADS_API_VERSION = "v19"
APPLY_VERSION = "C3.0"

# Supported operation types (v1)
SUPPORTED_OP_TYPES = {
    "ADS_SET_KEYWORD_STATUS",
    "ADS_ADD_NEGATIVE_KEYWORD",
    "ADS_REMOVE_NEGATIVE_KEYWORD",
    "ADS_UPDATE_ASSET_TEXT",
    "MERCHANT_EXCLUDE_PRODUCT",
    "ADS_SET_PMAX_BRAND_EXCLUSIONS",
}

# Manufacturer brands that must NOT be added to exclusion lists
MANUFACTURER_BRANDS = {
    "rheem", "goodman", "solace", "daikin", "ruud", "amana",
}

# Risk level mapping
RISK_LEVELS = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}

# =============================================================================
# CREDENTIAL LOADING
# =============================================================================


def load_env():
    """Load environment variables from .env file."""
    env_paths = [
        PROJECT_ROOT / ".env",
        Path.home() / "hvac-ads-2026" / ".env",
        Path.home() / "bcd-seo-engine" / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            return True
    return False


def get_access_token():
    """Get OAuth access token via refresh token."""
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
            "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
            "grant_type": "refresh_token",
        },
    )
    if response.status_code != 200:
        raise Exception(f"Token refresh failed: {response.text}")
    return response.json()["access_token"]


# =============================================================================
# GOOGLE ADS API CLIENT
# =============================================================================


class GoogleAdsClient:
    """Google Ads API client for read and write operations."""

    def __init__(self, customer_id: str, access_token: str, login_customer_id: str = None):
        self.customer_id = customer_id.replace("-", "")
        self.access_token = access_token
        self.login_customer_id = login_customer_id.replace("-", "") if login_customer_id else None
        self.base_url = f"https://googleads.googleapis.com/{GOOGLE_ADS_API_VERSION}"

    def _headers(self):
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "developer-token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
            "Content-Type": "application/json",
        }
        if self.login_customer_id:
            headers["login-customer-id"] = self.login_customer_id
        return headers

    def search(self, query: str) -> list:
        """Execute GAQL query and return all results."""
        url = f"{self.base_url}/customers/{self.customer_id}/googleAds:search"
        all_results = []
        page_token = None

        while True:
            payload = {"query": query}
            if page_token:
                payload["pageToken"] = page_token

            response = requests.post(url, headers=self._headers(), json=payload)

            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")

            data = response.json()
            results = data.get("results", [])
            all_results.extend(results)

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return all_results

    def mutate(self, operations: list) -> dict:
        """Execute mutations and return results."""
        url = f"{self.base_url}/customers/{self.customer_id}/googleAds:mutate"
        payload = {"mutateOperations": operations}

        response = requests.post(url, headers=self._headers(), json=payload)

        if response.status_code != 200:
            raise Exception(f"Mutate error {response.status_code}: {response.text}")

        return response.json()


# =============================================================================
# PLAN VALIDATOR
# =============================================================================


class PlanValidator:
    """Validates plan structure and guardrails."""

    def __init__(self, plan: dict):
        self.plan = plan
        self.errors = []
        self.warnings = []

    def validate_structure(self) -> bool:
        """Validate required top-level fields exist."""
        required_fields = [
            "plan_id", "plan_version", "created_utc", "snapshot_id",
            "snapshot_version", "sources", "mode", "guardrails",
            "summary", "operations"
        ]
        for field in required_fields:
            if field not in self.plan:
                self.errors.append(f"Missing required field: {field}")

        return len(self.errors) == 0

    def validate_mode(self, execute_mode: bool) -> bool:
        """Validate plan mode vs execution mode."""
        plan_mode = self.plan.get("mode", "")

        if execute_mode:
            # --execute requires plan mode to be APPLY
            if plan_mode != "APPLY":
                self.errors.append(
                    f"Cannot execute: plan mode is '{plan_mode}', must be 'APPLY'. "
                    "Change mode to 'APPLY' and set plan_approved: true first."
                )
                return False

            # Check plan approval
            approvals = self.plan.get("approvals", {})
            if not approvals.get("plan_approved", False):
                self.errors.append(
                    "Cannot execute: plan_approved is not true. "
                    "Review and approve the plan first."
                )
                return False

        return len(self.errors) == 0

    def validate_snapshot_exists(self) -> bool:
        """Validate snapshot directory exists."""
        snapshot_id = self.plan.get("snapshot_id", "")
        snapshot_path = SNAPSHOTS_DIR / snapshot_id

        if not snapshot_path.exists():
            self.errors.append(
                f"Snapshot not found: {snapshot_path}. "
                "Cannot apply plan without source snapshot."
            )
            return False

        # Verify snapshot version matches
        manifest_path = snapshot_path / "_manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)
            expected_version = self.plan.get("snapshot_version", "")
            actual_version = manifest.get("snapshot_version", "")
            if expected_version and actual_version and expected_version != actual_version:
                self.errors.append(
                    f"Snapshot version mismatch: plan expects '{expected_version}', "
                    f"snapshot has '{actual_version}'."
                )
                return False

        return len(self.errors) == 0

    def validate_guardrails(self) -> bool:
        """Validate operations against guardrails."""
        guardrails = self.plan.get("guardrails", {})
        operations = self.plan.get("operations", [])
        summary = self.plan.get("summary", {})

        # Check max_total_ops
        max_total = guardrails.get("max_total_ops", 0)
        if len(operations) > max_total:
            self.errors.append(
                f"Guardrail violation: {len(operations)} operations exceed "
                f"max_total_ops limit of {max_total}."
            )

        # Check max_ops_by_type
        max_by_type = guardrails.get("max_ops_by_type", {})
        ops_by_type = {}
        for op in operations:
            op_type = op.get("op_type", "UNKNOWN")
            ops_by_type[op_type] = ops_by_type.get(op_type, 0) + 1

        for op_type, count in ops_by_type.items():
            limit = max_by_type.get(op_type, float("inf"))
            if count > limit:
                self.errors.append(
                    f"Guardrail violation: {count} {op_type} operations exceed "
                    f"max_ops_by_type limit of {limit}."
                )

        # Check forbidden operation types
        if guardrails.get("forbid_budget_changes", False):
            if "ADS_UPDATE_BUDGET" in ops_by_type:
                self.errors.append("Guardrail violation: forbid_budget_changes is true but plan contains ADS_UPDATE_BUDGET operations.")

        if guardrails.get("forbid_bid_strategy_changes", False):
            if "ADS_UPDATE_BID_STRATEGY" in ops_by_type:
                self.errors.append("Guardrail violation: forbid_bid_strategy_changes is true but plan contains ADS_UPDATE_BID_STRATEGY operations.")

        # Check max_risk_level
        max_risk = guardrails.get("max_risk_level", "HIGH")
        max_risk_numeric = RISK_LEVELS.get(max_risk, 3)
        for op in operations:
            op_risk = op.get("risk", {}).get("level_numeric", 0)
            if op_risk > max_risk_numeric:
                self.errors.append(
                    f"Guardrail violation: operation {op.get('op_id')} has risk level "
                    f"{op.get('risk', {}).get('level')} which exceeds max_risk_level of {max_risk}."
                )

        # Check operation approvals for types requiring manual approval
        require_approval_types = guardrails.get("require_manual_approval_for_types", [])
        approvals = self.plan.get("approvals", {})
        op_approvals = approvals.get("operation_approvals", {})

        for op in operations:
            op_id = op.get("op_id")
            op_type = op.get("op_type")
            if op_type in require_approval_types:
                op_approval = op_approvals.get(op_id, {})
                if not op_approval.get("approved", False):
                    self.errors.append(
                        f"Guardrail violation: operation {op_id} ({op_type}) requires "
                        f"manual approval but is not approved."
                    )

        # Check for unsupported operation types
        for op in operations:
            op_type = op.get("op_type", "UNKNOWN")
            if op_type not in SUPPORTED_OP_TYPES:
                self.errors.append(
                    f"Unsupported operation type: {op_type} in operation {op.get('op_id')}. "
                    f"Supported types: {', '.join(sorted(SUPPORTED_OP_TYPES))}"
                )

        # Check blocklist
        blocklist = guardrails.get("blocklist_campaign_ids", [])
        for op in operations:
            parent_refs = op.get("entity", {}).get("parent_refs", [])
            for ref in parent_refs:
                if ref.startswith("ads.campaign:"):
                    campaign_id = ref.split(":")[-1]
                    if campaign_id in blocklist:
                        self.errors.append(
                            f"Guardrail violation: operation {op.get('op_id')} targets "
                            f"blocklisted campaign {campaign_id}."
                        )

        # Check allowlist
        allowlist = guardrails.get("allowlist_campaign_ids")
        if allowlist is not None:  # Only enforce if explicitly set
            for op in operations:
                parent_refs = op.get("entity", {}).get("parent_refs", [])
                campaign_id = None
                for ref in parent_refs:
                    if ref.startswith("ads.campaign:"):
                        campaign_id = ref.split(":")[-1]
                        break
                if campaign_id and campaign_id not in allowlist:
                    self.errors.append(
                        f"Guardrail violation: operation {op.get('op_id')} targets "
                        f"campaign {campaign_id} which is not in allowlist."
                    )

        return len(self.errors) == 0

    def get_errors(self) -> list:
        return self.errors

    def get_warnings(self) -> list:
        return self.warnings


# =============================================================================
# PRECONDITION CHECKER
# =============================================================================


class PreconditionChecker:
    """Checks operation preconditions against live state."""

    def __init__(self, ads_client: GoogleAdsClient):
        self.ads_client = ads_client
        self.cache = {}

    def check_preconditions(self, op: dict) -> tuple[bool, list]:
        """Check all preconditions for an operation. Returns (passed, mismatches)."""
        preconditions = op.get("preconditions", [])
        mismatches = []

        if not preconditions:
            return True, []

        # Get live entity state
        entity = op.get("entity", {})
        entity_type = entity.get("entity_type", "")
        entity_id = entity.get("entity_id", "")

        live_state = self._fetch_live_state(entity)
        if live_state is None:
            # Entity not found
            mismatches.append({
                "path": "entity",
                "op": "EXISTS",
                "expected": True,
                "actual": None,
                "description": "Entity no longer exists"
            })
            return False, mismatches

        # Check each precondition
        for pc in preconditions:
            path = pc.get("path", "")
            operator = pc.get("op", "")
            expected = pc.get("value")
            description = pc.get("description", "")

            actual = self._get_value_at_path(live_state, path)
            passed = self._evaluate_precondition(actual, operator, expected)

            if not passed:
                mismatches.append({
                    "path": path,
                    "op": operator,
                    "expected": expected,
                    "actual": actual,
                    "description": description
                })

        return len(mismatches) == 0, mismatches

    def _fetch_live_state(self, entity: dict) -> Optional[dict]:
        """Fetch live state for an entity."""
        entity_type = entity.get("entity_type", "")
        entity_id = entity.get("entity_id", "")

        # Check cache
        cache_key = f"{entity_type}:{entity_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Fetch based on entity type
        try:
            if entity_type == "KEYWORD":
                state = self._fetch_keyword(entity_id, entity)
            elif entity_type == "NEGATIVE_KEYWORD":
                state = self._fetch_negative_keyword(entity_id, entity)
            elif entity_type == "CAMPAIGN":
                state = self._fetch_campaign(entity_id)
            elif entity_type == "ASSET":
                state = self._fetch_asset(entity_id, entity)
            elif entity_type == "PRODUCT":
                # Merchant products - would need merchant API
                state = {"exists": True}  # Placeholder for DRY_RUN
            else:
                state = None

            self.cache[cache_key] = state
            return state
        except Exception as e:
            return None

    def _fetch_keyword(self, keyword_id: str, entity: dict) -> Optional[dict]:
        """Fetch keyword state from Google Ads."""
        # Extract campaign and ad group from parent refs
        parent_refs = entity.get("parent_refs", [])
        campaign_id = None
        ad_group_id = None
        for ref in parent_refs:
            if ref.startswith("ads.campaign:"):
                campaign_id = ref.split(":")[-1]
            elif ref.startswith("ads.ad_group:"):
                ad_group_id = ref.split(":")[-1]

        if not ad_group_id:
            return None

        query = f"""
            SELECT
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                campaign.id,
                campaign.bidding_strategy_type
            FROM ad_group_criterion
            WHERE ad_group_criterion.criterion_id = {keyword_id}
        """

        results = self.ads_client.search(query)
        if not results:
            return None

        r = results[0]
        agc = r.get("adGroupCriterion", {})
        campaign = r.get("campaign", {})

        return {
            "id": str(agc.get("criterionId", "")),
            "text": agc.get("keyword", {}).get("text", ""),
            "match_type": agc.get("keyword", {}).get("matchType", ""),
            "status": agc.get("status", ""),
            "campaign": {
                "id": str(campaign.get("id", "")),
                "bidding_strategy": campaign.get("biddingStrategyType", "")
            }
        }

    def _fetch_negative_keyword(self, keyword_id: str, entity: dict) -> Optional[dict]:
        """Fetch negative keyword state."""
        parent_refs = entity.get("parent_refs", [])
        campaign_id = None
        for ref in parent_refs:
            if ref.startswith("ads.campaign:"):
                campaign_id = ref.split(":")[-1]

        if keyword_id == "new":
            # New negative - check if it exists by text
            text = entity.get("entity_name", "")
            query = f"""
                SELECT
                    campaign_criterion.criterion_id,
                    campaign_criterion.keyword.text,
                    campaign_criterion.negative
                FROM campaign_criterion
                WHERE campaign.id = {campaign_id}
                AND campaign_criterion.type = 'KEYWORD'
                AND campaign_criterion.negative = true
            """
            results = self.ads_client.search(query)
            for r in results:
                cc = r.get("campaignCriterion", {})
                if cc.get("keyword", {}).get("text", "").lower() == text.lower():
                    return {"exists": True, "text": text}
            return {"exists": False, "text": text, "negative_keyword": {"text": None}}

        return {"exists": True}

    def _fetch_campaign(self, campaign_id: str) -> Optional[dict]:
        """Fetch campaign state."""
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.bidding_strategy_type,
                campaign.advertising_channel_type
            FROM campaign
            WHERE campaign.id = {campaign_id}
        """

        results = self.ads_client.search(query)
        if not results:
            return None

        c = results[0].get("campaign", {})
        return {
            "id": str(c.get("id", "")),
            "name": c.get("name", ""),
            "status": c.get("status", ""),
            "bidding_strategy": c.get("biddingStrategyType", ""),
            "advertising_channel_type": c.get("advertisingChannelType", "")
        }

    def _fetch_asset(self, asset_id: str, entity: dict) -> Optional[dict]:
        """Fetch asset state."""
        # Assets are complex - for now return placeholder
        return {
            "exists": True,
            "asset_type": "HEADLINE",
            "text": entity.get("entity_name", "")
        }

    def _get_value_at_path(self, state: dict, path: str) -> Any:
        """Get value at dot-notation path."""
        if not state or not path:
            return None

        parts = path.split(".")
        current = state

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None

        return current

    def _evaluate_precondition(self, actual: Any, operator: str, expected: Any) -> bool:
        """Evaluate a precondition."""
        if operator == "EQUALS":
            return actual == expected
        elif operator == "NOT_EQUALS":
            return actual != expected
        elif operator == "IN":
            return actual in expected if expected else False
        elif operator == "NOT_IN":
            return actual not in expected if expected else True
        elif operator == "CONTAINS":
            if actual is None:
                return False
            return expected.lower() in str(actual).lower()
        elif operator == "NOT_CONTAINS":
            if actual is None:
                return True
            return expected.lower() not in str(actual).lower()
        elif operator == "EXISTS":
            return actual is not None
        elif operator == "NOT_EXISTS":
            return actual is None
        elif operator == "GT":
            return actual > expected if actual is not None else False
        elif operator == "GTE":
            return actual >= expected if actual is not None else False
        elif operator == "LT":
            return actual < expected if actual is not None else False
        elif operator == "LTE":
            return actual <= expected if actual is not None else False
        elif operator == "MATCHES":
            if actual is None:
                return False
            return bool(re.match(expected, str(actual)))
        else:
            return False


# =============================================================================
# OPERATION EXECUTORS
# =============================================================================


class OperationExecutor:
    """Executes individual operations against live APIs."""

    def __init__(self, ads_client: GoogleAdsClient, dry_run: bool = True):
        self.ads_client = ads_client
        self.dry_run = dry_run

    def execute(self, op: dict) -> dict:
        """Execute an operation and return result."""
        op_type = op.get("op_type", "")
        op_id = op.get("op_id", "")

        result = {
            "op_id": op_id,
            "op_type": op_type,
            "status": "PENDING",
            "dry_run": self.dry_run,
            "api_request": None,
            "api_response": None,
            "mutation_id": None,
            "error": None,
            "executed_at": None
        }

        try:
            if op_type == "ADS_SET_KEYWORD_STATUS":
                result = self._execute_set_keyword_status(op, result)
            elif op_type == "ADS_ADD_NEGATIVE_KEYWORD":
                result = self._execute_add_negative_keyword(op, result)
            elif op_type == "ADS_REMOVE_NEGATIVE_KEYWORD":
                result = self._execute_remove_negative_keyword(op, result)
            elif op_type == "ADS_UPDATE_ASSET_TEXT":
                result = self._execute_update_asset_text(op, result)
            elif op_type == "MERCHANT_EXCLUDE_PRODUCT":
                result = self._execute_merchant_exclude_product(op, result)
            elif op_type == "ADS_SET_PMAX_BRAND_EXCLUSIONS":
                result = self._execute_set_pmax_brand_exclusions(op, result)
            else:
                result["status"] = "UNSUPPORTED"
                result["error"] = f"Unsupported operation type: {op_type}"

        except Exception as e:
            result["status"] = "FAILED"
            result["error"] = str(e)

        result["executed_at"] = datetime.now(timezone.utc).isoformat()
        return result

    def _execute_set_keyword_status(self, op: dict, result: dict) -> dict:
        """Execute keyword status change."""
        entity = op.get("entity", {})
        entity_id = entity.get("entity_id", "")
        after = op.get("after", {})
        new_status = after.get("status", "")

        # Get ad group from parent refs
        parent_refs = entity.get("parent_refs", [])
        ad_group_id = None
        for ref in parent_refs:
            if ref.startswith("ads.ad_group:"):
                ad_group_id = ref.split(":")[-1]
                break

        if not ad_group_id:
            result["status"] = "FAILED"
            result["error"] = "Cannot determine ad_group_id from parent_refs"
            return result

        # Build mutation
        resource_name = f"customers/{self.ads_client.customer_id}/adGroupCriteria/{ad_group_id}~{entity_id}"

        mutation = {
            "adGroupCriterionOperation": {
                "update": {
                    "resourceName": resource_name,
                    "status": new_status
                },
                "updateMask": "status"
            }
        }

        result["api_request"] = mutation

        if self.dry_run:
            result["status"] = "DRY_RUN_SUCCESS"
            result["api_response"] = {"dry_run": True, "would_update": resource_name}
        else:
            # Execute mutation
            response = self.ads_client.mutate([mutation])
            result["api_response"] = response
            result["status"] = "SUCCESS"
            results = response.get("mutateOperationResponses", [])
            if results:
                result["mutation_id"] = results[0].get("adGroupCriterionResult", {}).get("resourceName")

        return result

    def _execute_add_negative_keyword(self, op: dict, result: dict) -> dict:
        """Execute adding a negative keyword."""
        entity = op.get("entity", {})
        after = op.get("after", {})

        # Get campaign from parent refs
        parent_refs = entity.get("parent_refs", [])
        campaign_id = None
        for ref in parent_refs:
            if ref.startswith("ads.campaign:"):
                campaign_id = ref.split(":")[-1]
                break

        if not campaign_id:
            result["status"] = "FAILED"
            result["error"] = "Cannot determine campaign_id from parent_refs"
            return result

        # GUARDRAIL: Block negative keywords on Performance Max campaigns
        campaign_type = self._get_campaign_type(campaign_id)
        if campaign_type == "PERFORMANCE_MAX":
            result["status"] = "FAILED"
            result["error"] = (
                "PMax campaigns do not support campaign-level negative keywords. "
                "Use Brand Exclusions (brand_list) instead."
            )
            return result

        text = after.get("text", entity.get("entity_name", ""))
        match_type = after.get("match_type", "EXACT")

        # Build mutation
        campaign_resource = f"customers/{self.ads_client.customer_id}/campaigns/{campaign_id}"

        mutation = {
            "campaignCriterionOperation": {
                "create": {
                    "campaign": campaign_resource,
                    "negative": True,
                    "keyword": {
                        "text": text,
                        "matchType": match_type
                    }
                }
            }
        }

        result["api_request"] = mutation

        if self.dry_run:
            result["status"] = "DRY_RUN_SUCCESS"
            result["api_response"] = {"dry_run": True, "would_create": f"negative keyword '{text}' in campaign {campaign_id}"}
        else:
            response = self.ads_client.mutate([mutation])
            result["api_response"] = response
            result["status"] = "SUCCESS"
            results = response.get("mutateOperationResponses", [])
            if results:
                result["mutation_id"] = results[0].get("campaignCriterionResult", {}).get("resourceName")

        return result

    def _execute_remove_negative_keyword(self, op: dict, result: dict) -> dict:
        """Execute removing a negative keyword."""
        entity = op.get("entity", {})
        entity_id = entity.get("entity_id", "")

        # Get campaign from parent refs
        parent_refs = entity.get("parent_refs", [])
        campaign_id = None
        for ref in parent_refs:
            if ref.startswith("ads.campaign:"):
                campaign_id = ref.split(":")[-1]
                break

        if not campaign_id:
            result["status"] = "FAILED"
            result["error"] = "Cannot determine campaign_id from parent_refs"
            return result

        resource_name = f"customers/{self.ads_client.customer_id}/campaignCriteria/{campaign_id}~{entity_id}"

        mutation = {
            "campaignCriterionOperation": {
                "remove": resource_name
            }
        }

        result["api_request"] = mutation

        if self.dry_run:
            result["status"] = "DRY_RUN_SUCCESS"
            result["api_response"] = {"dry_run": True, "would_remove": resource_name}
        else:
            response = self.ads_client.mutate([mutation])
            result["api_response"] = response
            result["status"] = "SUCCESS"

        return result

    def _execute_update_asset_text(self, op: dict, result: dict) -> dict:
        """Execute asset text update."""
        # Asset updates are complex - this is a simplified version
        entity = op.get("entity", {})
        after = op.get("after", {})
        new_text = after.get("text", "")

        result["api_request"] = {
            "operation": "UPDATE_ASSET_TEXT",
            "entity_id": entity.get("entity_id"),
            "new_text": new_text
        }

        if self.dry_run:
            result["status"] = "DRY_RUN_SUCCESS"
            result["api_response"] = {
                "dry_run": True,
                "would_update_text": f"Asset {entity.get('entity_id')} → '{new_text}'"
            }
        else:
            # Real implementation would use Asset service
            result["status"] = "NOT_IMPLEMENTED"
            result["error"] = "Asset text updates require Asset service implementation"

        return result

    def _execute_merchant_exclude_product(self, op: dict, result: dict) -> dict:
        """Execute merchant product exclusion."""
        entity = op.get("entity", {})
        after = op.get("after", {})
        offer_id = after.get("offer_id", entity.get("entity_id", ""))

        result["api_request"] = {
            "operation": "MERCHANT_EXCLUDE_PRODUCT",
            "offer_id": offer_id,
            "exclusion_reason": after.get("exclusion_reason", "MANUAL")
        }

        if self.dry_run:
            result["status"] = "DRY_RUN_SUCCESS"
            result["api_response"] = {
                "dry_run": True,
                "would_exclude": f"Product {offer_id} from Shopping/PMax feeds"
            }
        else:
            # Real implementation would update supplemental feed
            result["status"] = "NOT_IMPLEMENTED"
            result["error"] = "Merchant product exclusion requires supplemental feed implementation"

        return result

    def _execute_set_pmax_brand_exclusions(self, op: dict, result: dict) -> dict:
        """Execute setting brand exclusions for a PMax campaign.

        Brand exclusions are implemented via brand lists attached to campaigns.
        This operation creates or updates a brand list and attaches it to the campaign.

        GUARDRAILS:
        1. Campaign must be PERFORMANCE_MAX type
        2. Manufacturer brands (rheem, goodman, etc.) must NOT be in exclusion list
           unless override_manufacturer_exclusions is set
        """
        entity = op.get("entity", {})
        params = op.get("params", {})
        approvals = op.get("approvals", {})

        campaign_id = params.get("campaign_id") or entity.get("entity_id", "")
        action = params.get("action", "SET")
        brands = params.get("brands", [])
        brand_list_name = params.get("brand_list_name", "BCD Brand Exclusions")

        # GUARDRAIL 1: Verify campaign is PERFORMANCE_MAX
        campaign_type = self._get_campaign_type(campaign_id)
        if campaign_type != "PERFORMANCE_MAX":
            result["status"] = "FAILED"
            result["error"] = (
                f"ADS_SET_PMAX_BRAND_EXCLUSIONS only allowed on PERFORMANCE_MAX campaigns. "
                f"Campaign {campaign_id} is type: {campaign_type}"
            )
            return result

        # GUARDRAIL 2: Check for manufacturer brands in exclusion list
        override_manufacturers = approvals.get("override_manufacturer_exclusions", False)
        if not override_manufacturers:
            manufacturer_found = []
            for brand in brands:
                brand_lower = brand.lower()
                for mfg in MANUFACTURER_BRANDS:
                    if mfg.lower() in brand_lower:
                        manufacturer_found.append(f"{brand} (contains {mfg})")
                        break

            if manufacturer_found:
                result["status"] = "FAILED"
                result["error"] = (
                    f"Manufacturer brands cannot be added to exclusion list: {', '.join(manufacturer_found)}. "
                    f"Set approvals.override_manufacturer_exclusions=true to override."
                )
                return result

        # Build the API request info
        result["api_request"] = {
            "operation": "SET_PMAX_BRAND_EXCLUSIONS",
            "campaign_id": campaign_id,
            "action": action,
            "brand_list_name": brand_list_name,
            "brands": brands,
            "brand_count": len(brands),
        }

        if self.dry_run:
            result["status"] = "DRY_RUN_SUCCESS"
            result["api_response"] = {
                "dry_run": True,
                "would_create_brand_list": brand_list_name,
                "would_attach_to_campaign": campaign_id,
                "brands_to_exclude": brands,
                "brand_count": len(brands),
                "note": "Brand exclusions use Google Ads Brand List API (account-level resource)"
            }
        else:
            # Real implementation notes:
            # 1. Check if brand list already exists: GET /brandLists
            # 2. Create brand list if needed: POST /brandLists
            # 3. Add brands to list: POST /brandLists/{id}:addBrands
            # 4. Attach list to campaign via CampaignCriterion with brand_list type
            #
            # Note: Brand lists require brands to exist in Google's verified brand database.
            # Arbitrary strings may not be accepted.
            result["status"] = "NOT_IMPLEMENTED"
            result["error"] = (
                "Brand exclusion API implementation pending. "
                "Requires: BrandListService (account-level) + CampaignCriterionService (brand_list type). "
                "Note: Google requires brands to exist in their verified database."
            )

        return result

    def _get_campaign_type(self, campaign_id: str) -> Optional[str]:
        """Get campaign type from Google Ads API.

        Returns campaign advertising_channel_type (e.g., SEARCH, PERFORMANCE_MAX).
        """
        try:
            query = f"""
                SELECT
                    campaign.id,
                    campaign.advertising_channel_type
                FROM campaign
                WHERE campaign.id = {campaign_id}
            """
            results = self.ads_client.search(query)
            if results:
                campaign = results[0].get("campaign", {})
                return campaign.get("advertisingChannelType")
            return None
        except Exception:
            return None


# =============================================================================
# RESULTS WRITER
# =============================================================================


class ResultsWriter:
    """Writes execution results to files."""

    def __init__(self, plan: dict, output_dir: Path):
        self.plan = plan
        self.output_dir = output_dir
        self.plan_id = plan.get("plan_id", "unknown")

    def write_results(self, results: dict):
        """Write results to JSON and markdown files."""
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Write JSON
        json_path = self.output_dir / f"{self.plan_id}.results.json"
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2)

        # Write markdown
        md_path = self.output_dir / f"{self.plan_id}.results.md"
        with open(md_path, "w") as f:
            f.write(self._generate_markdown(results))

        return json_path, md_path

    def _generate_markdown(self, results: dict) -> str:
        """Generate markdown summary of results."""
        lines = []
        lines.append(f"# Execution Results: {self.plan_id}")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| Plan ID | `{results.get('plan_id')}` |")
        lines.append(f"| Snapshot ID | `{results.get('snapshot_id')}` |")
        lines.append(f"| Execution Mode | `{results.get('execution_mode')}` |")
        lines.append(f"| Started | `{results.get('start_utc')}` |")
        lines.append(f"| Finished | `{results.get('end_utc')}` |")
        lines.append(f"| Duration | `{results.get('duration_seconds', 0):.2f}s` |")
        lines.append("")

        # Counts
        summary = results.get("summary", {})
        lines.append("## Operation Counts")
        lines.append("")
        lines.append(f"| Status | Count |")
        lines.append("|--------|-------|")
        for status, count in summary.get("by_status", {}).items():
            lines.append(f"| {status} | {count} |")
        lines.append("")

        # Guardrail confirmations
        lines.append("## Guardrail Confirmations")
        lines.append("")
        guardrails = results.get("guardrail_confirmations", {})
        for name, confirmed in guardrails.items():
            emoji = "PASS" if confirmed else "FAIL"
            lines.append(f"- [{emoji}] {name}")
        lines.append("")

        # Operation details
        lines.append("## Operation Details")
        lines.append("")
        for op_result in results.get("operation_results", []):
            op_id = op_result.get("op_id", "?")
            op_type = op_result.get("op_type", "?")
            status = op_result.get("status", "?")
            error = op_result.get("error", "")

            emoji = "SUCCESS" if "SUCCESS" in status else "FAILED" if status == "FAILED" else "INFO"
            lines.append(f"### {op_id}: {op_type}")
            lines.append("")
            lines.append(f"- **Status:** {emoji} {status}")
            lines.append(f"- **Dry Run:** {op_result.get('dry_run', True)}")
            if error:
                lines.append(f"- **Error:** {error}")
            if op_result.get("mutation_id"):
                lines.append(f"- **Mutation ID:** `{op_result.get('mutation_id')}`")
            lines.append("")

        # Abort info if applicable
        if results.get("aborted"):
            lines.append("## ABORTED")
            lines.append("")
            lines.append(f"**Reason:** {results.get('abort_reason', 'Unknown')}")
            lines.append("")

        return "\n".join(lines)


# =============================================================================
# MAIN APPLY ENGINE
# =============================================================================


class ApplyEngine:
    """Main orchestrator for plan execution."""

    def __init__(self, plan_path: Path, execute_mode: bool = False):
        self.plan_path = plan_path
        self.execute_mode = execute_mode
        self.dry_run = not execute_mode
        self.plan = None
        self.results = {
            "plan_id": None,
            "snapshot_id": None,
            "execution_mode": "DRY_RUN" if self.dry_run else "APPLY",
            "start_utc": None,
            "end_utc": None,
            "duration_seconds": 0,
            "aborted": False,
            "abort_reason": None,
            "guardrail_confirmations": {},
            "precondition_results": {},
            "operation_results": [],
            "rollback_data": [],
            "summary": {
                "total_operations": 0,
                "by_status": {}
            }
        }

    def run(self) -> dict:
        """Execute the full apply workflow."""
        self.results["start_utc"] = datetime.now(timezone.utc).isoformat()
        start_time = datetime.now(timezone.utc)

        try:
            # Step 1: Load plan
            self._load_plan()

            # Step 2: Validate plan
            self._validate_plan()

            # Step 3: Check if empty
            if self._check_empty_plan():
                return self._finalize_results(start_time)

            # Step 4: Initialize API clients (for precondition checks)
            ads_client = self._init_api_clients()

            # Step 5: Re-verify preconditions
            self._verify_preconditions(ads_client)

            # Step 6: Execute operations
            self._execute_operations(ads_client)

        except AbortException as e:
            self.results["aborted"] = True
            self.results["abort_reason"] = str(e)
            print(f"\nABORTED: {e}")

        except Exception as e:
            self.results["aborted"] = True
            self.results["abort_reason"] = f"Unexpected error: {str(e)}"
            print(f"\nERROR: {e}")

        return self._finalize_results(start_time)

    def _load_plan(self):
        """Load plan from file."""
        print(f"Loading plan: {self.plan_path}")

        if not self.plan_path.exists():
            raise AbortException(f"Plan file not found: {self.plan_path}")

        with open(self.plan_path) as f:
            self.plan = json.load(f)

        self.results["plan_id"] = self.plan.get("plan_id", "unknown")
        self.results["snapshot_id"] = self.plan.get("snapshot_id", "unknown")
        print(f"  Plan ID: {self.results['plan_id']}")
        print(f"  Snapshot ID: {self.results['snapshot_id']}")
        print(f"  Mode: {self.plan.get('mode')}")
        print(f"  Operations: {len(self.plan.get('operations', []))}")

    def _validate_plan(self):
        """Validate plan structure and guardrails."""
        print("\nValidating plan...")

        validator = PlanValidator(self.plan)

        # Structure validation
        if not validator.validate_structure():
            raise AbortException(f"Plan validation failed:\n  " + "\n  ".join(validator.get_errors()))
        self.results["guardrail_confirmations"]["structure_valid"] = True
        print("  [PASS] Structure valid")

        # Mode validation
        if not validator.validate_mode(self.execute_mode):
            raise AbortException(f"Mode validation failed:\n  " + "\n  ".join(validator.get_errors()))
        self.results["guardrail_confirmations"]["mode_valid"] = True
        print("  [PASS] Mode valid")

        # Snapshot exists
        if not validator.validate_snapshot_exists():
            raise AbortException(f"Snapshot validation failed:\n  " + "\n  ".join(validator.get_errors()))
        self.results["guardrail_confirmations"]["snapshot_exists"] = True
        print("  [PASS] Snapshot exists")

        # Guardrails
        if not validator.validate_guardrails():
            raise AbortException(f"Guardrail validation failed:\n  " + "\n  ".join(validator.get_errors()))
        self.results["guardrail_confirmations"]["guardrails_satisfied"] = True
        print("  [PASS] Guardrails satisfied")

    def _check_empty_plan(self) -> bool:
        """Check if plan has no operations."""
        operations = self.plan.get("operations", [])
        if not operations:
            print("\nNo operations to apply.")
            self.results["summary"]["total_operations"] = 0
            self.results["summary"]["by_status"]["NO_OPERATIONS"] = 0
            return True
        return False

    def _init_api_clients(self) -> GoogleAdsClient:
        """Initialize API clients."""
        print("\nInitializing API clients...")

        if not load_env():
            raise AbortException("Failed to load environment variables")

        access_token = get_access_token()
        sources = self.plan.get("sources", {})
        customer_id = sources.get("google_ads_customer_id", os.getenv("GOOGLE_ADS_CUSTOMER_ID", ""))
        login_customer_id = sources.get("google_ads_login_customer_id", os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID"))

        ads_client = GoogleAdsClient(customer_id, access_token, login_customer_id)
        print("  [OK] Google Ads client initialized")

        return ads_client

    def _verify_preconditions(self, ads_client: GoogleAdsClient):
        """Verify all preconditions against live state."""
        print("\nVerifying preconditions...")

        guardrails = self.plan.get("guardrails", {})
        require_match = guardrails.get("require_precondition_match", True)
        abort_on_missing = guardrails.get("abort_on_missing_entity", True)

        checker = PreconditionChecker(ads_client)
        operations = self.plan.get("operations", [])

        all_passed = True
        for op in operations:
            op_id = op.get("op_id", "?")
            passed, mismatches = checker.check_preconditions(op)

            self.results["precondition_results"][op_id] = {
                "passed": passed,
                "mismatches": mismatches
            }

            if passed:
                print(f"  [{op_id}] PASS")
            else:
                print(f"  [{op_id}] FAIL - {len(mismatches)} mismatch(es)")
                for m in mismatches:
                    print(f"      {m['path']}: expected {m['expected']}, got {m['actual']}")
                all_passed = False

                # Check for entity not found
                if any(m.get("path") == "entity" for m in mismatches):
                    if abort_on_missing:
                        raise AbortException(f"Entity not found for operation {op_id} (abort_on_missing_entity=true)")

        if not all_passed and require_match:
            raise AbortException("Precondition mismatches detected (require_precondition_match=true)")

        self.results["guardrail_confirmations"]["preconditions_verified"] = all_passed

    def _execute_operations(self, ads_client: GoogleAdsClient):
        """Execute all operations."""
        mode_str = "DRY_RUN" if self.dry_run else "LIVE EXECUTION"
        print(f"\nExecuting operations ({mode_str})...")

        guardrails = self.plan.get("guardrails", {})
        abort_on_first_error = guardrails.get("abort_on_first_error", True)

        executor = OperationExecutor(ads_client, dry_run=self.dry_run)
        operations = self.plan.get("operations", [])

        for op in operations:
            op_id = op.get("op_id", "?")
            op_type = op.get("op_type", "?")

            print(f"  [{op_id}] {op_type}...", end=" ")

            # Skip if preconditions failed and we're in strict mode
            pc_result = self.results["precondition_results"].get(op_id, {})
            if not pc_result.get("passed", True):
                result = {
                    "op_id": op_id,
                    "op_type": op_type,
                    "status": "SKIPPED",
                    "dry_run": self.dry_run,
                    "error": "Precondition check failed",
                    "executed_at": datetime.now(timezone.utc).isoformat()
                }
                self.results["operation_results"].append(result)
                print("SKIPPED (precondition failed)")
                continue

            # Execute operation
            result = executor.execute(op)
            self.results["operation_results"].append(result)

            # Store rollback data
            if op.get("rollback"):
                self.results["rollback_data"].append({
                    "op_id": op_id,
                    "rollback": op["rollback"]
                })

            status = result.get("status", "UNKNOWN")
            if "SUCCESS" in status:
                print(status)
            else:
                print(f"{status} - {result.get('error', '')}")

                if status == "FAILED" and abort_on_first_error:
                    raise AbortException(f"Operation {op_id} failed (abort_on_first_error=true)")

    def _finalize_results(self, start_time: datetime) -> dict:
        """Finalize and return results."""
        end_time = datetime.now(timezone.utc)
        self.results["end_utc"] = end_time.isoformat()
        self.results["duration_seconds"] = (end_time - start_time).total_seconds()

        # Compute summary
        by_status = {}
        for r in self.results["operation_results"]:
            status = r.get("status", "UNKNOWN")
            by_status[status] = by_status.get(status, 0) + 1

        self.results["summary"]["total_operations"] = len(self.results["operation_results"])
        self.results["summary"]["by_status"] = by_status

        return self.results


class AbortException(Exception):
    """Raised when execution must abort."""
    pass


# =============================================================================
# CLI
# =============================================================================


def print_usage():
    print("""
Usage: bin/apply <plan_path> [OPTIONS]

ARGUMENTS:
    plan_path           Path to plan JSON file (required)

OPTIONS:
    --execute           Execute operations for real (DANGEROUS)
                        Without this flag, runs in DRY_RUN mode

EXAMPLES:
    bin/apply plans/runs/plan-2026-01-15.json           # DRY_RUN
    bin/apply plans/runs/plan-2026-01-15.json --execute # LIVE WRITES

DRY_RUN MODE (default):
    - Validates plan
    - Checks preconditions against live state
    - Simulates execution
    - Writes results files
    - NO actual API mutations

EXECUTE MODE (--execute):
    - Requires plan.mode == "APPLY"
    - Requires plan_approved == true
    - Requires all operation approvals
    - Makes REAL API mutations
    - Writes results files

SAFETY:
    - Never runs without explicit plan path
    - Never modifies plans
    - Never guesses intent
    - Always aborts on validation failure
    - Always writes audit trail
""")


def main():
    print("=" * 70)
    print("APPLY ENGINE - Phase C3")
    print("=" * 70)
    print()

    # Parse args
    plan_path = None
    execute_mode = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--execute":
            execute_mode = True
        elif arg in ("--help", "-h"):
            print_usage()
            sys.exit(0)
        elif not arg.startswith("-"):
            plan_path = Path(arg)
        else:
            print(f"Unknown option: {arg}")
            print_usage()
            sys.exit(1)
        i += 1

    # Validate required arg
    if not plan_path:
        print("ERROR: Plan path is required")
        print_usage()
        sys.exit(1)

    # Print mode warning
    if execute_mode:
        print("=" * 70)
        print("WARNING: EXECUTE MODE - LIVE API WRITES ENABLED")
        print("=" * 70)
        print()
    else:
        print("Running in DRY_RUN mode (no actual changes)")
        print()

    # Run engine
    engine = ApplyEngine(plan_path, execute_mode)
    results = engine.run()

    # Write results
    print("\nWriting results...")
    output_dir = plan_path.parent
    writer = ResultsWriter(engine.plan or {"plan_id": "unknown"}, output_dir)
    json_path, md_path = writer.write_results(results)
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")

    # Print final summary
    print()
    print("=" * 70)
    print("EXECUTION SUMMARY")
    print("=" * 70)
    summary = results.get("summary", {})
    print(f"Total operations: {summary.get('total_operations', 0)}")
    for status, count in summary.get("by_status", {}).items():
        print(f"  {status}: {count}")

    if results.get("aborted"):
        print()
        print(f"ABORTED: {results.get('abort_reason')}")
        sys.exit(1)

    print()
    print("Done.")
    sys.exit(0)


if __name__ == "__main__":
    main()
