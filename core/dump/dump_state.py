#!/usr/bin/env python3
"""
State Dump - Google Ads

Phase A read-only state capture. NO MUTATIONS.

Produces immutable, timestamped snapshots of Google Ads account state.
Follows schema defined in core/schema/SCHEMA.md and FIELDS.md.

Usage:
    python audit/dump_state.py                    # Full dump
    python audit/dump_state.py --ads-only        # Google Ads only (default for A2)
    python audit/dump_state.py --merchant-only   # Merchant Center only (A3)
    python audit/dump_state.py --days 14         # Change history lookback (default: 14)

Output:
    snapshots/{TIMESTAMP}/
        _manifest.json
        _index.json
        raw/ads/...
        normalized/ads/...
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
CORE_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = CORE_DIR.parent

GOOGLE_ADS_API_VERSION = "v19"
MERCHANT_CENTER_API_VERSION = "v2.1"
CHANGE_HISTORY_DAYS = 14
PERFORMANCE_DAYS = 30
SNAPSHOT_VERSION = "A3.0"

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
    """Minimal Google Ads API client for read-only operations."""

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
        """Execute GAQL query and return all results (handles pagination)."""
        url = f"{self.base_url}/customers/{self.customer_id}/googleAds:search"
        all_results = []
        page_token = None

        while True:
            payload = {"query": query}
            if page_token:
                payload["pageToken"] = page_token

            response = requests.post(url, headers=self._headers(), json=payload)

            if response.status_code != 200:
                error_detail = response.text
                raise Exception(f"API error {response.status_code}: {error_detail}")

            data = response.json()
            results = data.get("results", [])
            all_results.extend(results)

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return all_results


# =============================================================================
# MERCHANT CENTER API CLIENT
# =============================================================================


class MerchantCenterClient:
    """Minimal Merchant Center API client for read-only operations."""

    def __init__(self, merchant_id: str, access_token: str):
        self.merchant_id = merchant_id
        self.access_token = access_token
        self.base_url = f"https://shoppingcontent.googleapis.com/content/{MERCHANT_CENTER_API_VERSION}"

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def list_products(self, max_results: int = 250) -> list:
        """List all products (handles pagination)."""
        url = f"{self.base_url}/{self.merchant_id}/products"
        all_products = []
        page_token = None

        while True:
            params = {"maxResults": max_results}
            if page_token:
                params["pageToken"] = page_token

            response = requests.get(url, headers=self._headers(), params=params)

            if response.status_code != 200:
                raise Exception(f"Merchant API error {response.status_code}: {response.text}")

            data = response.json()
            products = data.get("resources", [])
            all_products.extend(products)

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return all_products

    def list_product_statuses(self, max_results: int = 250) -> list:
        """List product statuses (includes disapproval reasons)."""
        url = f"{self.base_url}/{self.merchant_id}/productstatuses"
        all_statuses = []
        page_token = None

        while True:
            params = {"maxResults": max_results}
            if page_token:
                params["pageToken"] = page_token

            response = requests.get(url, headers=self._headers(), params=params)

            if response.status_code != 200:
                raise Exception(f"Merchant API error {response.status_code}: {response.text}")

            data = response.json()
            statuses = data.get("resources", [])
            all_statuses.extend(statuses)

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return all_statuses

    def get_account_status(self) -> dict:
        """Get account status including issues/warnings."""
        url = f"{self.base_url}/{self.merchant_id}/accountstatuses/{self.merchant_id}"

        response = requests.get(url, headers=self._headers())

        if response.status_code != 200:
            raise Exception(f"Merchant API error {response.status_code}: {response.text}")

        return response.json()


# =============================================================================
# DATA FETCHERS - RAW
# =============================================================================


def fetch_campaigns(client: GoogleAdsClient) -> dict:
    """Fetch all campaigns with full settings."""
    query = """
        SELECT
            campaign.resource_name,
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type,
            campaign.advertising_channel_sub_type,
            campaign.bidding_strategy_type,
            campaign.bidding_strategy,
            campaign.target_roas.target_roas,
            campaign.target_cpa.target_cpa_micros,
            campaign.maximize_conversions.target_cpa_micros,
            campaign.maximize_conversion_value.target_roas,
            campaign.campaign_budget,
            campaign.start_date,
            campaign.end_date,
            campaign.labels,
            campaign.network_settings.target_google_search,
            campaign.network_settings.target_search_network,
            campaign.network_settings.target_content_network,
            campaign.geo_target_type_setting.positive_geo_target_type,
            campaign.geo_target_type_setting.negative_geo_target_type,
            campaign.shopping_setting.merchant_id,
            campaign.shopping_setting.feed_label,
            campaign.url_expansion_opt_out,
            campaign_budget.id,
            campaign_budget.amount_micros,
            campaign_budget.delivery_method
        FROM campaign
        WHERE campaign.status != 'REMOVED'
        ORDER BY campaign.id
    """
    results = client.search(query)
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "account_id": client.customer_id,
        "count": len(results),
        "records": [r.get("campaign", {}) | {"budget": r.get("campaignBudget", {})} for r in results],
    }


def fetch_ad_groups(client: GoogleAdsClient) -> dict:
    """Fetch all ad groups."""
    query = """
        SELECT
            ad_group.resource_name,
            ad_group.id,
            ad_group.name,
            ad_group.campaign,
            ad_group.status,
            ad_group.type,
            ad_group.cpc_bid_micros,
            ad_group.target_cpa_micros,
            ad_group.target_roas,
            ad_group.labels
        FROM ad_group
        WHERE ad_group.status != 'REMOVED'
        ORDER BY ad_group.id
    """
    results = client.search(query)
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "count": len(results),
        "records": [r.get("adGroup", {}) for r in results],
    }


def fetch_keywords(client: GoogleAdsClient) -> dict:
    """Fetch all keywords (positive)."""
    query = """
        SELECT
            ad_group_criterion.resource_name,
            ad_group_criterion.criterion_id,
            ad_group_criterion.ad_group,
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            ad_group_criterion.status,
            ad_group_criterion.cpc_bid_micros,
            ad_group_criterion.quality_info.quality_score,
            ad_group_criterion.quality_info.creative_quality_score,
            ad_group_criterion.quality_info.post_click_quality_score,
            ad_group_criterion.quality_info.search_predicted_ctr,
            ad_group_criterion.labels
        FROM ad_group_criterion
        WHERE ad_group_criterion.type = 'KEYWORD'
            AND ad_group_criterion.status != 'REMOVED'
            AND ad_group_criterion.negative = FALSE
        ORDER BY ad_group_criterion.criterion_id
    """
    results = client.search(query)
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "count": len(results),
        "records": [r.get("adGroupCriterion", {}) for r in results],
    }


def fetch_campaign_negatives(client: GoogleAdsClient) -> dict:
    """Fetch campaign-level negative keywords."""
    query = """
        SELECT
            campaign_criterion.resource_name,
            campaign_criterion.criterion_id,
            campaign_criterion.campaign,
            campaign_criterion.keyword.text,
            campaign_criterion.keyword.match_type,
            campaign_criterion.negative
        FROM campaign_criterion
        WHERE campaign_criterion.type = 'KEYWORD'
            AND campaign_criterion.negative = TRUE
        ORDER BY campaign_criterion.criterion_id
    """
    results = client.search(query)
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "count": len(results),
        "records": [r.get("campaignCriterion", {}) for r in results],
    }


def fetch_adgroup_negatives(client: GoogleAdsClient) -> dict:
    """Fetch ad group-level negative keywords."""
    query = """
        SELECT
            ad_group_criterion.resource_name,
            ad_group_criterion.criterion_id,
            ad_group_criterion.ad_group,
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            ad_group_criterion.negative
        FROM ad_group_criterion
        WHERE ad_group_criterion.type = 'KEYWORD'
            AND ad_group_criterion.negative = TRUE
        ORDER BY ad_group_criterion.criterion_id
    """
    results = client.search(query)
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "count": len(results),
        "records": [r.get("adGroupCriterion", {}) for r in results],
    }


def fetch_ads(client: GoogleAdsClient) -> dict:
    """Fetch all ads (RSA focus)."""
    query = """
        SELECT
            ad_group_ad.resource_name,
            ad_group_ad.ad.id,
            ad_group_ad.ad_group,
            ad_group_ad.ad.type,
            ad_group_ad.status,
            ad_group_ad.ad.final_urls,
            ad_group_ad.ad.responsive_search_ad.headlines,
            ad_group_ad.ad.responsive_search_ad.descriptions,
            ad_group_ad.policy_summary.approval_status,
            ad_group_ad.policy_summary.review_status
        FROM ad_group_ad
        WHERE ad_group_ad.status != 'REMOVED'
        ORDER BY ad_group_ad.ad.id
    """
    results = client.search(query)
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "count": len(results),
        "records": [r.get("adGroupAd", {}) for r in results],
    }


def fetch_assets(client: GoogleAdsClient) -> dict:
    """Fetch account-level assets."""
    query = """
        SELECT
            asset.resource_name,
            asset.id,
            asset.type,
            asset.name,
            asset.sitelink_asset.link_text,
            asset.sitelink_asset.description1,
            asset.sitelink_asset.description2,
            asset.callout_asset.callout_text,
            asset.structured_snippet_asset.header,
            asset.structured_snippet_asset.values,
            asset.call_asset.phone_number,
            asset.policy_summary.approval_status
        FROM asset
        ORDER BY asset.id
    """
    results = client.search(query)
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "count": len(results),
        "records": [r.get("asset", {}) for r in results],
    }


def fetch_asset_links(client: GoogleAdsClient) -> dict:
    """Fetch asset → campaign/adgroup bindings."""
    # Campaign assets
    campaign_query = """
        SELECT
            campaign_asset.resource_name,
            campaign_asset.asset,
            campaign_asset.campaign,
            campaign_asset.field_type,
            campaign_asset.status
        FROM campaign_asset
        WHERE campaign_asset.status != 'REMOVED'
    """
    campaign_results = client.search(campaign_query)

    # Ad group assets
    adgroup_query = """
        SELECT
            ad_group_asset.resource_name,
            ad_group_asset.asset,
            ad_group_asset.ad_group,
            ad_group_asset.field_type,
            ad_group_asset.status
        FROM ad_group_asset
        WHERE ad_group_asset.status != 'REMOVED'
    """
    adgroup_results = client.search(adgroup_query)

    records = []
    for r in campaign_results:
        rec = r.get("campaignAsset", {})
        rec["level"] = "CAMPAIGN"
        records.append(rec)
    for r in adgroup_results:
        rec = r.get("adGroupAsset", {})
        rec["level"] = "ADGROUP"
        records.append(rec)

    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "count": len(records),
        "records": records,
    }


def fetch_change_history(client: GoogleAdsClient, days: int = 14) -> dict:
    """Fetch change history for last N days."""
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.utcnow().strftime("%Y-%m-%d")

    query = f"""
        SELECT
            change_event.change_date_time,
            change_event.change_resource_type,
            change_event.change_resource_name,
            change_event.resource_change_operation,
            change_event.changed_fields,
            change_event.old_resource,
            change_event.new_resource,
            change_event.user_email,
            change_event.client_type
        FROM change_event
        WHERE change_event.change_date_time >= '{start_date}'
            AND change_event.change_date_time <= '{end_date}'
        ORDER BY change_event.change_date_time DESC
        LIMIT 5000
    """
    results = client.search(query)
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "lookback_days": days,
        "count": len(results),
        "records": [r.get("changeEvent", {}) for r in results],
    }


def fetch_performance(client: GoogleAdsClient, days: int = 30) -> dict:
    """Fetch performance metrics by campaign and ad group."""
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    # By campaign
    campaign_query = f"""
        SELECT
            segments.date,
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value,
            metrics.all_conversions,
            metrics.all_conversions_value
        FROM campaign
        WHERE segments.date >= '{start_date}'
            AND segments.date <= '{end_date}'
        ORDER BY segments.date, campaign.id
    """
    campaign_results = client.search(campaign_query)

    # By ad group
    adgroup_query = f"""
        SELECT
            segments.date,
            campaign.id,
            ad_group.id,
            ad_group.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value
        FROM ad_group
        WHERE segments.date >= '{start_date}'
            AND segments.date <= '{end_date}'
        ORDER BY segments.date, ad_group.id
    """
    adgroup_results = client.search(adgroup_query)

    by_campaign = []
    for r in campaign_results:
        rec = {
            "date": r.get("segments", {}).get("date"),
            "campaign_id": r.get("campaign", {}).get("id"),
            "campaign_name": r.get("campaign", {}).get("name"),
            **r.get("metrics", {}),
        }
        by_campaign.append(rec)

    by_ad_group = []
    for r in adgroup_results:
        rec = {
            "date": r.get("segments", {}).get("date"),
            "campaign_id": r.get("campaign", {}).get("id"),
            "ad_group_id": r.get("adGroup", {}).get("id"),
            "ad_group_name": r.get("adGroup", {}).get("name"),
            **r.get("metrics", {}),
        }
        by_ad_group.append(rec)

    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "date_range": {"start": start_date, "end": end_date},
        "by_campaign": by_campaign,
        "by_ad_group": by_ad_group,
    }


# =============================================================================
# PMAX FETCHERS
# =============================================================================


def fetch_pmax_campaigns(client: GoogleAdsClient) -> dict:
    """Fetch Performance Max campaigns."""
    query = """
        SELECT
            campaign.resource_name,
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.bidding_strategy_type,
            campaign.target_roas.target_roas,
            campaign.maximize_conversion_value.target_roas,
            campaign.campaign_budget,
            campaign.shopping_setting.merchant_id,
            campaign.shopping_setting.feed_label,
            campaign.url_expansion_opt_out,
            campaign_budget.amount_micros
        FROM campaign
        WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX'
            AND campaign.status != 'REMOVED'
        ORDER BY campaign.id
    """
    results = client.search(query)
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "count": len(results),
        "records": [r.get("campaign", {}) | {"budget": r.get("campaignBudget", {})} for r in results],
    }


def fetch_asset_groups(client: GoogleAdsClient) -> dict:
    """Fetch PMax asset groups."""
    query = """
        SELECT
            asset_group.resource_name,
            asset_group.id,
            asset_group.campaign,
            asset_group.name,
            asset_group.status,
            asset_group.final_urls,
            asset_group.final_mobile_urls,
            asset_group.path1,
            asset_group.path2,
            asset_group.ad_strength
        FROM asset_group
        WHERE asset_group.status != 'REMOVED'
        ORDER BY asset_group.id
    """
    results = client.search(query)
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "count": len(results),
        "records": [r.get("assetGroup", {}) for r in results],
    }


def fetch_asset_group_assets(client: GoogleAdsClient) -> dict:
    """Fetch assets assigned to asset groups."""
    query = """
        SELECT
            asset_group_asset.resource_name,
            asset_group_asset.asset_group,
            asset_group_asset.asset,
            asset_group_asset.field_type,
            asset_group_asset.status
        FROM asset_group_asset
        WHERE asset_group_asset.status != 'REMOVED'
    """
    results = client.search(query)
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "count": len(results),
        "records": [r.get("assetGroupAsset", {}) for r in results],
    }


def fetch_listing_groups(client: GoogleAdsClient) -> dict:
    """Fetch PMax listing group filters."""
    query = """
        SELECT
            asset_group_listing_group_filter.resource_name,
            asset_group_listing_group_filter.asset_group,
            asset_group_listing_group_filter.id,
            asset_group_listing_group_filter.type,
            asset_group_listing_group_filter.case_value.product_brand.value,
            asset_group_listing_group_filter.case_value.product_category.category_id,
            asset_group_listing_group_filter.case_value.product_custom_attribute.value,
            asset_group_listing_group_filter.case_value.product_type.value,
            asset_group_listing_group_filter.parent_listing_group_filter
        FROM asset_group_listing_group_filter
    """
    results = client.search(query)
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "count": len(results),
        "records": [r.get("assetGroupListingGroupFilter", {}) for r in results],
    }


def fetch_pmax_campaign_assets(client: GoogleAdsClient) -> dict:
    """Fetch campaign-level assets for PMax."""
    query = """
        SELECT
            campaign_asset.resource_name,
            campaign_asset.asset,
            campaign_asset.campaign,
            campaign_asset.field_type,
            campaign_asset.status,
            campaign.advertising_channel_type
        FROM campaign_asset
        WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX'
            AND campaign_asset.status != 'REMOVED'
    """
    results = client.search(query)
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "count": len(results),
        "records": [r.get("campaignAsset", {}) for r in results],
    }


def fetch_url_expansion(client: GoogleAdsClient) -> dict:
    """Fetch URL expansion settings for PMax campaigns."""
    query = """
        SELECT
            campaign.resource_name,
            campaign.id,
            campaign.name,
            campaign.url_expansion_opt_out
        FROM campaign
        WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX'
            AND campaign.status != 'REMOVED'
    """
    results = client.search(query)
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "count": len(results),
        "records": [
            {
                "campaign_id": r.get("campaign", {}).get("id"),
                "campaign_name": r.get("campaign", {}).get("name"),
                "url_expansion_opt_out": r.get("campaign", {}).get("urlExpansionOptOut", False),
            }
            for r in results
        ],
    }


# =============================================================================
# MERCHANT CENTER FETCHERS - RAW
# =============================================================================


def fetch_merchant_products(client: MerchantCenterClient) -> dict:
    """Fetch all products from Merchant Center."""
    products = client.list_products()
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "merchant_id": client.merchant_id,
        "count": len(products),
        "records": products,
    }


def fetch_merchant_product_statuses(client: MerchantCenterClient) -> dict:
    """Fetch product statuses (approval, disapproval, warnings)."""
    statuses = client.list_product_statuses()
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "merchant_id": client.merchant_id,
        "count": len(statuses),
        "records": statuses,
    }


def fetch_merchant_account_issues(client: MerchantCenterClient) -> dict:
    """Fetch account-level issues and warnings."""
    status = client.get_account_status()
    issues = status.get("accountLevelIssues", [])
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "merchant_id": client.merchant_id,
        "account_id": status.get("accountId"),
        "count": len(issues),
        "records": issues,
    }


# =============================================================================
# NORMALIZERS
# =============================================================================


def extract_id(resource_name: str) -> str:
    """Extract ID from resource name like 'customers/123/campaigns/456' -> '456'."""
    if not resource_name:
        return ""
    return resource_name.split("/")[-1]


def normalize_campaigns(raw: dict) -> dict:
    """Normalize campaigns data."""
    records = []
    for r in raw.get("records", []):
        budget = r.get("budget", {})
        target_roas = (
            r.get("targetRoas", {}).get("targetRoas")
            or r.get("maximizeConversionValue", {}).get("targetRoas")
        )
        target_cpa_micros = (
            r.get("targetCpa", {}).get("targetCpaMicros")
            or r.get("maximizeConversions", {}).get("targetCpaMicros")
        )

        records.append({
            "id": r.get("id"),
            "name": r.get("name"),
            "type": r.get("advertisingChannelType", "UNKNOWN"),
            "status": r.get("status"),
            "bidding_strategy": r.get("biddingStrategyType"),
            "bidding_target": target_roas or (int(target_cpa_micros) / 1_000_000 if target_cpa_micros else None),
            "budget_id": budget.get("id"),
            "budget_amount_micros": budget.get("amountMicros"),
            "budget_delivery": budget.get("deliveryMethod", "STANDARD"),
            "start_date": r.get("startDate"),
            "end_date": r.get("endDate"),
            "labels": [extract_id(l) for l in r.get("labels", [])],
        })

    return {
        "extracted_at": raw.get("extracted_at"),
        "count": len(records),
        "records": records,
    }


def normalize_ad_groups(raw: dict) -> dict:
    """Normalize ad groups data."""
    records = []
    for r in raw.get("records", []):
        records.append({
            "id": r.get("id"),
            "campaign_id": extract_id(r.get("campaign", "")),
            "name": r.get("name"),
            "status": r.get("status"),
            "type": r.get("type", "UNKNOWN").replace("_STANDARD", ""),
            "cpc_bid_micros": r.get("cpcBidMicros"),
            "labels": [extract_id(l) for l in r.get("labels", [])],
        })

    return {
        "extracted_at": raw.get("extracted_at"),
        "count": len(records),
        "records": records,
    }


def normalize_keywords(raw: dict, ad_groups_raw: dict, validation_errors: list = None) -> dict:
    """Normalize keywords data.

    Args:
        raw: Raw keywords data from API
        ad_groups_raw: Raw ad groups data for campaign_id lookup
        validation_errors: List to append validation errors to (optional)

    Returns:
        Normalized keywords dict with campaign_id populated (null if unmapped)
    """
    # Build ad group -> campaign map
    ag_to_campaign = {}
    for ag in ad_groups_raw.get("records", []):
        ag_id = ag.get("id")
        campaign_id = extract_id(ag.get("campaign", ""))
        if ag_id:
            ag_to_campaign[str(ag_id)] = campaign_id

    records = []
    null_campaign_count = 0

    for r in raw.get("records", []):
        keyword = r.get("keyword", {})
        quality = r.get("qualityInfo", {})
        ad_group_id = extract_id(r.get("adGroup", ""))

        # Look up campaign_id, use None if not found
        campaign_id = ag_to_campaign.get(ad_group_id)
        if campaign_id is None and ad_group_id:
            null_campaign_count += 1
            if validation_errors is not None:
                validation_errors.append({
                    "type": "UNMAPPED_AD_GROUP",
                    "entity": "keyword",
                    "keyword_id": r.get("criterionId"),
                    "ad_group_id": ad_group_id,
                    "message": f"Keyword {r.get('criterionId')} has ad_group_id {ad_group_id} with no matching campaign"
                })

        records.append({
            "id": r.get("criterionId"),
            "ad_group_id": ad_group_id if ad_group_id else None,
            "campaign_id": campaign_id,
            "text": keyword.get("text"),
            "match_type": keyword.get("matchType"),
            "status": r.get("status"),
            "cpc_bid_micros": r.get("cpcBidMicros"),
            "quality_score": quality.get("qualityScore"),
            "expected_ctr": quality.get("searchPredictedCtr"),
            "ad_relevance": quality.get("creativeQualityScore"),
            "landing_page_exp": quality.get("postClickQualityScore"),
        })

    return {
        "extracted_at": raw.get("extracted_at"),
        "count": len(records),
        "null_campaign_ids": null_campaign_count,
        "records": records,
    }


def normalize_negatives(campaign_raw: dict, adgroup_raw: dict) -> dict:
    """Normalize and combine negative keywords."""
    records = []

    for r in campaign_raw.get("records", []):
        keyword = r.get("keyword", {})
        records.append({
            "id": r.get("criterionId"),
            "level": "CAMPAIGN",
            "campaign_id": extract_id(r.get("campaign", "")),
            "ad_group_id": None,
            "text": keyword.get("text"),
            "match_type": keyword.get("matchType"),
        })

    for r in adgroup_raw.get("records", []):
        keyword = r.get("keyword", {})
        records.append({
            "id": r.get("criterionId"),
            "level": "ADGROUP",
            "campaign_id": None,  # Would need lookup
            "ad_group_id": extract_id(r.get("adGroup", "")),
            "text": keyword.get("text"),
            "match_type": keyword.get("matchType"),
        })

    return {
        "extracted_at": campaign_raw.get("extracted_at"),
        "count": len(records),
        "records": records,
    }


def normalize_ads(raw: dict, ad_groups_raw: dict) -> dict:
    """Normalize ads data."""
    ag_to_campaign = {}
    for ag in ad_groups_raw.get("records", []):
        ag_id = ag.get("id")
        campaign_id = extract_id(ag.get("campaign", ""))
        if ag_id:
            ag_to_campaign[str(ag_id)] = campaign_id

    records = []
    for r in raw.get("records", []):
        ad = r.get("ad", {})
        rsa = ad.get("responsiveSearchAd", {})
        policy = r.get("policySummary", {})
        ad_group_id = extract_id(r.get("adGroup", ""))

        headlines = [h.get("text") for h in rsa.get("headlines", [])]
        descriptions = [d.get("text") for d in rsa.get("descriptions", [])]

        records.append({
            "id": ad.get("id"),
            "ad_group_id": ad_group_id,
            "campaign_id": ag_to_campaign.get(ad_group_id, ""),
            "type": "RSA" if ad.get("type") == "RESPONSIVE_SEARCH_AD" else ad.get("type"),
            "status": r.get("status"),
            "final_url": (ad.get("finalUrls") or [""])[0],
            "headlines": headlines,
            "descriptions": descriptions,
            "approval_status": policy.get("approvalStatus"),
        })

    return {
        "extracted_at": raw.get("extracted_at"),
        "count": len(records),
        "records": records,
    }


def normalize_assets(raw: dict, links_raw: dict) -> dict:
    """Normalize assets data."""
    # Build asset -> linked entities map
    asset_campaigns = {}
    asset_adgroups = {}
    for link in links_raw.get("records", []):
        asset_id = extract_id(link.get("asset", ""))
        if link.get("level") == "CAMPAIGN":
            campaign_id = extract_id(link.get("campaign", ""))
            asset_campaigns.setdefault(asset_id, []).append(campaign_id)
        else:
            adgroup_id = extract_id(link.get("adGroup", ""))
            asset_adgroups.setdefault(asset_id, []).append(adgroup_id)

    records = []
    for r in raw.get("records", []):
        asset_id = str(r.get("id"))
        asset_type = r.get("type", "UNKNOWN")

        # Extract text based on type
        text = None
        description = None
        url = None

        if asset_type == "SITELINK":
            sitelink = r.get("sitelinkAsset", {})
            text = sitelink.get("linkText")
            description = sitelink.get("description1")
            url = (sitelink.get("finalUrls") or [""])[0]
        elif asset_type == "CALLOUT":
            text = r.get("calloutAsset", {}).get("calloutText")
        elif asset_type == "STRUCTURED_SNIPPET":
            snippet = r.get("structuredSnippetAsset", {})
            text = snippet.get("header")
            description = ", ".join(snippet.get("values", []))
        elif asset_type == "CALL":
            text = r.get("callAsset", {}).get("phoneNumber")

        records.append({
            "id": asset_id,
            "type": asset_type,
            "name": r.get("name"),
            "text": text,
            "description": description,
            "url": url,
            "linked_campaigns": asset_campaigns.get(asset_id, []),
            "linked_ad_groups": asset_adgroups.get(asset_id, []),
            "approval_status": r.get("policySummary", {}).get("approvalStatus"),
        })

    return {
        "extracted_at": raw.get("extracted_at"),
        "count": len(records),
        "records": records,
    }


def normalize_change_history(raw: dict) -> dict:
    """Normalize change history data."""
    records = []
    for r in raw.get("records", []):
        records.append({
            "timestamp": r.get("changeDateTime"),
            "resource_type": r.get("changeResourceType"),
            "resource_id": extract_id(r.get("changeResourceName", "")),
            "resource_name": None,  # Would need lookup
            "operation": r.get("resourceChangeOperation"),
            "fields_changed": r.get("changedFields", []),
            "old_values": r.get("oldResource"),
            "new_values": r.get("newResource"),
            "actor": r.get("userEmail"),
            "source": r.get("clientType"),
        })

    return {
        "extracted_at": raw.get("extracted_at"),
        "lookback_days": raw.get("lookback_days"),
        "count": len(records),
        "records": records,
    }


def normalize_performance(raw: dict) -> dict:
    """Normalize performance data with derived metrics.

    Derived fields:
        - cost: cost_micros / 1,000,000
        - ctr: clicks / impressions
        - cpc: cost / clicks
        - conv_rate: conversions / clicks
        - cpa: cost / conversions (null if conversions == 0)
        - roas: conversion_value / cost (null if cost == 0)
        - value_per_conversion: conversion_value / conversions (null if conversions == 0)
        - cost_per_conversion: cost / conversions (null if conversions == 0)
    """
    def to_num(val, default=0):
        """Convert string/None to number."""
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def add_derived(rec: dict) -> dict:
        impressions = to_num(rec.get("impressions"), 0)
        clicks = to_num(rec.get("clicks"), 0)
        cost_micros = to_num(rec.get("costMicros") or rec.get("cost_micros"), 0)
        conversions = to_num(rec.get("conversions"), 0)
        conv_value = to_num(rec.get("conversionsValue") or rec.get("conversions_value"), 0)

        cost = cost_micros / 1_000_000

        return {
            **rec,
            "cost": round(cost, 2),
            "ctr": round(clicks / impressions, 4) if impressions > 0 else 0,
            "cpc": round(cost / clicks, 2) if clicks > 0 else 0,
            "conv_rate": round(conversions / clicks, 4) if clicks > 0 else 0,
            "cpa": round(cost / conversions, 2) if conversions > 0 else None,
            "roas": round(conv_value / cost, 2) if cost > 0 else None,
            "value_per_conversion": round(conv_value / conversions, 2) if conversions > 0 else None,
            "cost_per_conversion": round(cost / conversions, 2) if conversions > 0 else None,
        }

    return {
        "extracted_at": raw.get("extracted_at"),
        "date_range": raw.get("date_range"),
        "by_campaign": [add_derived(r) for r in raw.get("by_campaign", [])],
        "by_ad_group": [add_derived(r) for r in raw.get("by_ad_group", [])],
    }


def normalize_pmax_campaigns(raw: dict) -> dict:
    """Normalize PMax campaigns."""
    records = []
    for r in raw.get("records", []):
        budget = r.get("budget", {})
        target_roas = (
            r.get("targetRoas", {}).get("targetRoas")
            or r.get("maximizeConversionValue", {}).get("targetRoas")
        )
        shopping = r.get("shoppingSetting", {})

        records.append({
            "id": r.get("id"),
            "name": r.get("name"),
            "status": r.get("status"),
            "bidding_strategy": r.get("biddingStrategyType"),
            "target_roas": target_roas,
            "budget_amount_micros": budget.get("amountMicros"),
            "merchant_id": shopping.get("merchantId"),
            "url_expansion_enabled": not r.get("urlExpansionOptOut", False),
        })

    return {
        "extracted_at": raw.get("extracted_at"),
        "count": len(records),
        "records": records,
    }


def normalize_asset_groups(raw: dict, assets_raw: dict) -> dict:
    """Normalize asset groups with asset counts."""
    # Count assets per asset group
    ag_asset_counts = {}
    for a in assets_raw.get("records", []):
        ag_id = extract_id(a.get("assetGroup", ""))
        field_type = a.get("fieldType", "UNKNOWN")
        ag_asset_counts.setdefault(ag_id, {})
        ag_asset_counts[ag_id][field_type] = ag_asset_counts[ag_id].get(field_type, 0) + 1

    records = []
    for r in raw.get("records", []):
        ag_id = str(r.get("id"))
        records.append({
            "id": ag_id,
            "campaign_id": extract_id(r.get("campaign", "")),
            "name": r.get("name"),
            "status": r.get("status"),
            "final_url": (r.get("finalUrls") or [""])[0],
            "ad_strength": r.get("adStrength"),
            "asset_counts": ag_asset_counts.get(ag_id, {}),
        })

    return {
        "extracted_at": raw.get("extracted_at"),
        "count": len(records),
        "records": records,
    }


def normalize_listing_groups(raw: dict) -> dict:
    """Normalize listing groups."""
    records = []
    for r in raw.get("records", []):
        case_value = r.get("caseValue", {})
        records.append({
            "id": r.get("id"),
            "asset_group_id": extract_id(r.get("assetGroup", "")),
            "type": r.get("type"),
            "brand": case_value.get("productBrand", {}).get("value"),
            "category_id": case_value.get("productCategory", {}).get("categoryId"),
            "custom_attribute": case_value.get("productCustomAttribute", {}).get("value"),
            "product_type": case_value.get("productType", {}).get("value"),
            "parent_id": extract_id(r.get("parentListingGroupFilter", "")),
        })

    return {
        "extracted_at": raw.get("extracted_at"),
        "count": len(records),
        "records": records,
    }


# =============================================================================
# MERCHANT CENTER NORMALIZERS
# =============================================================================


def normalize_merchant_products(raw: dict, statuses_raw: dict, validation_errors: list = None) -> dict:
    """Normalize merchant products with status information.

    Args:
        raw: Raw products data from API
        statuses_raw: Raw product statuses for approval info
        validation_errors: List to append validation errors to (optional)

    Returns:
        Normalized products with approval status and issues
    """
    # Build product_id -> status map
    status_by_product = {}
    for s in statuses_raw.get("records", []):
        product_id = s.get("productId")
        if product_id:
            status_by_product[product_id] = s

    records = []
    disapproved_count = 0
    missing_status_count = 0

    for r in raw.get("records", []):
        product_id = r.get("id")
        offer_id = r.get("offerId")
        sku = r.get("mpn") or r.get("gtin") or offer_id

        # Get status info
        status_info = status_by_product.get(product_id, {})
        destinations = status_info.get("destinationStatuses", [])

        # Determine overall approval status
        approval_status = "UNKNOWN"
        disapproval_issues = []

        for dest in destinations:
            dest_status = dest.get("status", "").upper()
            if dest_status == "DISAPPROVED":
                approval_status = "DISAPPROVED"
                disapproved_count += 1
                break
            elif dest_status == "APPROVED":
                approval_status = "APPROVED"
            elif dest_status == "PENDING":
                if approval_status != "APPROVED":
                    approval_status = "PENDING"

        # Collect issues
        item_issues = status_info.get("itemLevelIssues", [])
        for issue in item_issues:
            if issue.get("servability") == "disapproved":
                disapproval_issues.append({
                    "code": issue.get("code"),
                    "description": issue.get("description"),
                    "detail": issue.get("detail"),
                })

        if not status_info and validation_errors is not None:
            missing_status_count += 1
            validation_errors.append({
                "type": "MISSING_PRODUCT_STATUS",
                "entity": "merchant_product",
                "product_id": product_id,
                "offer_id": offer_id,
                "message": f"Product {product_id} has no status information"
            })

        # Price handling
        price = r.get("price", {})
        price_value = price.get("value")
        price_currency = price.get("currency")

        records.append({
            "id": product_id,
            "offer_id": offer_id,
            "sku": sku,
            "title": r.get("title"),
            "description": r.get("description", "")[:500] if r.get("description") else None,
            "link": r.get("link"),
            "image_link": r.get("imageLink"),
            "price": float(price_value) if price_value else None,
            "currency": price_currency,
            "availability": r.get("availability"),
            "condition": r.get("condition"),
            "brand": r.get("brand"),
            "gtin": r.get("gtin"),
            "mpn": r.get("mpn"),
            "product_type": r.get("productTypes", [None])[0] if r.get("productTypes") else None,
            "google_product_category": r.get("googleProductCategory"),
            "approval_status": approval_status,
            "disapproval_issues": disapproval_issues if disapproval_issues else None,
            "channel": r.get("channel"),
            "content_language": r.get("contentLanguage"),
            "target_country": r.get("targetCountry"),
        })

    return {
        "extracted_at": raw.get("extracted_at"),
        "merchant_id": raw.get("merchant_id"),
        "count": len(records),
        "disapproved_count": disapproved_count,
        "missing_status_count": missing_status_count,
        "records": records,
    }


def normalize_merchant_product_status(statuses_raw: dict) -> dict:
    """Normalize product status summary for quick lookups."""
    records = []

    for s in statuses_raw.get("records", []):
        product_id = s.get("productId")
        destinations = s.get("destinationStatuses", [])
        item_issues = s.get("itemLevelIssues", [])

        # Determine destination statuses
        dest_summary = {}
        for dest in destinations:
            dest_name = dest.get("destination", "unknown")
            dest_summary[dest_name] = dest.get("status", "unknown")

        # Count issues by severity
        error_count = sum(1 for i in item_issues if i.get("servability") == "disapproved")
        warning_count = sum(1 for i in item_issues if i.get("servability") not in ["disapproved", None])

        records.append({
            "product_id": product_id,
            "destinations": dest_summary,
            "error_count": error_count,
            "warning_count": warning_count,
            "issues": [
                {
                    "code": i.get("code"),
                    "servability": i.get("servability"),
                    "description": i.get("description"),
                }
                for i in item_issues
            ] if item_issues else None,
        })

    return {
        "extracted_at": statuses_raw.get("extracted_at"),
        "merchant_id": statuses_raw.get("merchant_id"),
        "count": len(records),
        "records": records,
    }


# =============================================================================
# INDEX BUILDER
# =============================================================================


def build_index(
    campaigns_norm: dict,
    ad_groups_norm: dict,
    keywords_norm: dict,
    negatives_norm: dict,
    pmax_campaigns_norm: dict,
    ads_norm: dict = None,
    merchant_products_norm: dict = None,
) -> dict:
    """Build quick-lookup index with join-friendly lookups.

    Index structure:
        campaigns.by_id: {campaign_id: name}
        campaigns.by_type: {type: [campaign_ids]}
        campaigns.by_status: {status: [campaign_ids]}
        ads.campaigns_by_id: {campaign_id: {name, type, status}}
        ads.ad_groups_by_id: {ad_group_id: {name, campaign_id}}
        ads.keywords_by_id: {keyword_id: {text, ad_group_id, campaign_id}}
        totals: {campaigns, ad_groups, keywords, negatives}
    """
    # Campaigns by ID (simple name lookup)
    campaigns_by_id = {}
    campaigns_by_type = {}
    campaigns_by_status = {}

    # Join-friendly campaign lookup
    campaigns_full_by_id = {}

    for c in campaigns_norm.get("records", []):
        cid = str(c.get("id"))
        campaigns_by_id[cid] = c.get("name")
        ctype = c.get("type", "UNKNOWN")
        campaigns_by_type.setdefault(ctype, []).append(cid)
        status = c.get("status", "UNKNOWN")
        campaigns_by_status.setdefault(status, []).append(cid)
        # Full lookup
        campaigns_full_by_id[cid] = {
            "name": c.get("name"),
            "type": ctype,
            "status": status,
        }

    # PMax campaigns
    for c in pmax_campaigns_norm.get("records", []):
        cid = str(c.get("id"))
        campaigns_by_id[cid] = c.get("name")
        campaigns_by_type.setdefault("PMAX", []).append(cid)
        status = c.get("status", "UNKNOWN")
        campaigns_by_status.setdefault(status, []).append(cid)
        # Full lookup
        campaigns_full_by_id[cid] = {
            "name": c.get("name"),
            "type": "PERFORMANCE_MAX",
            "status": status,
        }

    # Ad groups by ID (join-friendly)
    ad_groups_by_id = {}
    for ag in ad_groups_norm.get("records", []):
        ag_id = str(ag.get("id"))
        ad_groups_by_id[ag_id] = {
            "name": ag.get("name"),
            "campaign_id": ag.get("campaign_id"),
        }

    # Keywords by ID (join-friendly)
    keywords_by_id = {}
    for kw in keywords_norm.get("records", []):
        kw_id = str(kw.get("id"))
        keywords_by_id[kw_id] = {
            "text": kw.get("text"),
            "ad_group_id": kw.get("ad_group_id"),
            "campaign_id": kw.get("campaign_id"),
        }

    # Merchant products lookups (if available)
    products_by_offer_id = {}
    products_by_sku = {}
    merchant_totals = {}

    if merchant_products_norm:
        for p in merchant_products_norm.get("records", []):
            offer_id = p.get("offer_id")
            sku = p.get("sku")
            product_info = {
                "id": p.get("id"),
                "title": p.get("title"),
                "brand": p.get("brand"),
                "price": p.get("price"),
                "approval_status": p.get("approval_status"),
            }
            if offer_id:
                products_by_offer_id[offer_id] = product_info
            if sku:
                products_by_sku[sku] = product_info

        merchant_totals = {
            "products": merchant_products_norm.get("count", 0),
            "disapproved": merchant_products_norm.get("disapproved_count", 0),
        }

    result = {
        "campaigns": {
            "by_id": campaigns_by_id,
            "by_type": campaigns_by_type,
            "by_status": campaigns_by_status,
        },
        "ads": {
            "campaigns_by_id": campaigns_full_by_id,
            "ad_groups_by_id": ad_groups_by_id,
            "keywords_by_id": keywords_by_id,
        },
        "totals": {
            "campaigns": campaigns_norm.get("count", 0) + pmax_campaigns_norm.get("count", 0),
            "ad_groups": ad_groups_norm.get("count", 0),
            "keywords": keywords_norm.get("count", 0),
            "negatives": negatives_norm.get("count", 0),
        },
    }

    # Add merchant section if data available
    if merchant_products_norm:
        result["merchant"] = {
            "products_by_offer_id": products_by_offer_id,
            "products_by_sku": products_by_sku,
        }
        result["totals"]["merchant_products"] = merchant_totals.get("products", 0)
        result["totals"]["merchant_disapproved"] = merchant_totals.get("disapproved", 0)

    return result


# =============================================================================
# MAIN
# =============================================================================


def write_json(path: Path, data: dict):
    """Write JSON file with pretty formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def main():
    start_time = time.time()
    extraction_started_utc = datetime.utcnow().isoformat() + "Z"

    print("=" * 60)
    print(f"STATE DUMP - GOOGLE ADS + MERCHANT CENTER  [v{SNAPSHOT_VERSION}]")
    print("=" * 60)
    print()

    # Parse args
    days = CHANGE_HISTORY_DAYS
    for i, arg in enumerate(sys.argv):
        if arg == "--days" and i + 1 < len(sys.argv):
            days = int(sys.argv[i + 1])

    # Load credentials
    if not load_env():
        print("ERROR: No .env file found")
        sys.exit(1)

    customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
    login_customer_id = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
    merchant_id = os.getenv("MERCHANT_CENTER_ID")

    if not customer_id:
        print("ERROR: GOOGLE_ADS_CUSTOMER_ID not set")
        sys.exit(1)

    print(f"Google Ads Customer ID: {customer_id}")
    print(f"Google Ads Login Customer ID: {login_customer_id or '(none)'}")
    print(f"Merchant Center ID: {merchant_id or '(none)'}")
    print(f"Change history: {days} days")
    print()

    # Authenticate
    print("Authenticating...")
    access_token = get_access_token()
    ads_client = GoogleAdsClient(customer_id, access_token, login_customer_id)
    merchant_client = MerchantCenterClient(merchant_id, access_token) if merchant_id else None
    print("OK")
    print()

    # Create snapshot directory
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H%M%SZ")
    snapshot_dir = PROJECT_ROOT / "snapshots" / timestamp
    raw_ads_dir = snapshot_dir / "raw" / "ads"
    raw_pmax_dir = snapshot_dir / "raw" / "pmax"
    raw_merchant_dir = snapshot_dir / "raw" / "merchant"
    norm_ads_dir = snapshot_dir / "normalized" / "ads"
    norm_pmax_dir = snapshot_dir / "normalized" / "pmax"
    norm_merchant_dir = snapshot_dir / "normalized" / "merchant"

    errors = []

    # ==========================================================================
    # FETCH RAW DATA - SEARCH
    # ==========================================================================
    print("Fetching Google Ads data...")

    print("  Campaigns...", end=" ", flush=True)
    try:
        raw_campaigns = fetch_campaigns(ads_client)
        print(f"{raw_campaigns['count']} records")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append({"file": "campaigns", "error": str(e)})
        raw_campaigns = {"extracted_at": datetime.utcnow().isoformat() + "Z", "count": 0, "records": []}

    print("  Ad Groups...", end=" ", flush=True)
    try:
        raw_ad_groups = fetch_ad_groups(ads_client)
        print(f"{raw_ad_groups['count']} records")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append({"file": "ad_groups", "error": str(e)})
        raw_ad_groups = {"extracted_at": datetime.utcnow().isoformat() + "Z", "count": 0, "records": []}

    print("  Keywords...", end=" ", flush=True)
    try:
        raw_keywords = fetch_keywords(ads_client)
        print(f"{raw_keywords['count']} records")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append({"file": "keywords", "error": str(e)})
        raw_keywords = {"extracted_at": datetime.utcnow().isoformat() + "Z", "count": 0, "records": []}

    print("  Campaign Negatives...", end=" ", flush=True)
    try:
        raw_campaign_negatives = fetch_campaign_negatives(ads_client)
        print(f"{raw_campaign_negatives['count']} records")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append({"file": "campaign_negatives", "error": str(e)})
        raw_campaign_negatives = {"extracted_at": datetime.utcnow().isoformat() + "Z", "count": 0, "records": []}

    print("  Ad Group Negatives...", end=" ", flush=True)
    try:
        raw_adgroup_negatives = fetch_adgroup_negatives(ads_client)
        print(f"{raw_adgroup_negatives['count']} records")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append({"file": "adgroup_negatives", "error": str(e)})
        raw_adgroup_negatives = {"extracted_at": datetime.utcnow().isoformat() + "Z", "count": 0, "records": []}

    print("  Ads...", end=" ", flush=True)
    try:
        raw_ads = fetch_ads(ads_client)
        print(f"{raw_ads['count']} records")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append({"file": "ads", "error": str(e)})
        raw_ads = {"extracted_at": datetime.utcnow().isoformat() + "Z", "count": 0, "records": []}

    print("  Assets...", end=" ", flush=True)
    try:
        raw_assets = fetch_assets(ads_client)
        print(f"{raw_assets['count']} records")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append({"file": "assets", "error": str(e)})
        raw_assets = {"extracted_at": datetime.utcnow().isoformat() + "Z", "count": 0, "records": []}

    print("  Asset Links...", end=" ", flush=True)
    try:
        raw_asset_links = fetch_asset_links(ads_client)
        print(f"{raw_asset_links['count']} records")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append({"file": "asset_links", "error": str(e)})
        raw_asset_links = {"extracted_at": datetime.utcnow().isoformat() + "Z", "count": 0, "records": []}

    print("  Change History...", end=" ", flush=True)
    try:
        raw_change_history = fetch_change_history(ads_client, days)
        print(f"{raw_change_history['count']} records")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append({"file": "change_history", "error": str(e)})
        raw_change_history = {"extracted_at": datetime.utcnow().isoformat() + "Z", "lookback_days": days, "count": 0, "records": []}

    print("  Performance...", end=" ", flush=True)
    try:
        raw_performance = fetch_performance(ads_client, PERFORMANCE_DAYS)
        print(f"{len(raw_performance.get('by_campaign', []))} campaign days, {len(raw_performance.get('by_ad_group', []))} ad group days")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append({"file": "performance", "error": str(e)})
        raw_performance = {"extracted_at": datetime.utcnow().isoformat() + "Z", "date_range": {}, "by_campaign": [], "by_ad_group": []}

    print()

    # ==========================================================================
    # FETCH RAW DATA - PMAX
    # ==========================================================================
    print("Fetching Performance Max data...")

    print("  PMax Campaigns...", end=" ", flush=True)
    try:
        raw_pmax_campaigns = fetch_pmax_campaigns(ads_client)
        print(f"{raw_pmax_campaigns['count']} records")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append({"file": "pmax_campaigns", "error": str(e)})
        raw_pmax_campaigns = {"extracted_at": datetime.utcnow().isoformat() + "Z", "count": 0, "records": []}

    print("  Asset Groups...", end=" ", flush=True)
    try:
        raw_asset_groups = fetch_asset_groups(ads_client)
        print(f"{raw_asset_groups['count']} records")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append({"file": "asset_groups", "error": str(e)})
        raw_asset_groups = {"extracted_at": datetime.utcnow().isoformat() + "Z", "count": 0, "records": []}

    print("  Asset Group Assets...", end=" ", flush=True)
    try:
        raw_asset_group_assets = fetch_asset_group_assets(ads_client)
        print(f"{raw_asset_group_assets['count']} records")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append({"file": "asset_group_assets", "error": str(e)})
        raw_asset_group_assets = {"extracted_at": datetime.utcnow().isoformat() + "Z", "count": 0, "records": []}

    print("  Listing Groups...", end=" ", flush=True)
    try:
        raw_listing_groups = fetch_listing_groups(ads_client)
        print(f"{raw_listing_groups['count']} records")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append({"file": "listing_groups", "error": str(e)})
        raw_listing_groups = {"extracted_at": datetime.utcnow().isoformat() + "Z", "count": 0, "records": []}

    print("  PMax Campaign Assets...", end=" ", flush=True)
    try:
        raw_pmax_campaign_assets = fetch_pmax_campaign_assets(ads_client)
        print(f"{raw_pmax_campaign_assets['count']} records")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append({"file": "pmax_campaign_assets", "error": str(e)})
        raw_pmax_campaign_assets = {"extracted_at": datetime.utcnow().isoformat() + "Z", "count": 0, "records": []}

    print("  URL Expansion...", end=" ", flush=True)
    try:
        raw_url_expansion = fetch_url_expansion(ads_client)
        print(f"{raw_url_expansion['count']} records")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append({"file": "url_expansion", "error": str(e)})
        raw_url_expansion = {"extracted_at": datetime.utcnow().isoformat() + "Z", "count": 0, "records": []}

    print()

    # ==========================================================================
    # FETCH RAW DATA - MERCHANT CENTER
    # ==========================================================================
    raw_merchant_products = {"extracted_at": datetime.utcnow().isoformat() + "Z", "count": 0, "records": []}
    raw_merchant_product_statuses = {"extracted_at": datetime.utcnow().isoformat() + "Z", "count": 0, "records": []}
    raw_merchant_account_issues = {"extracted_at": datetime.utcnow().isoformat() + "Z", "count": 0, "records": []}

    if merchant_client:
        print("Fetching Merchant Center data...")

        print("  Products...", end=" ", flush=True)
        try:
            raw_merchant_products = fetch_merchant_products(merchant_client)
            print(f"{raw_merchant_products['count']} records")
        except Exception as e:
            print(f"ERROR: {e}")
            errors.append({"file": "merchant_products", "error": str(e)})

        print("  Product Statuses...", end=" ", flush=True)
        try:
            raw_merchant_product_statuses = fetch_merchant_product_statuses(merchant_client)
            print(f"{raw_merchant_product_statuses['count']} records")
        except Exception as e:
            print(f"ERROR: {e}")
            errors.append({"file": "merchant_product_statuses", "error": str(e)})

        print("  Account Issues...", end=" ", flush=True)
        try:
            raw_merchant_account_issues = fetch_merchant_account_issues(merchant_client)
            print(f"{raw_merchant_account_issues['count']} issues")
        except Exception as e:
            print(f"ERROR: {e}")
            errors.append({"file": "merchant_account_issues", "error": str(e)})

        print()
    else:
        print("Skipping Merchant Center (no MERCHANT_CENTER_ID)")
        print()

    # ==========================================================================
    # WRITE RAW FILES
    # ==========================================================================
    print("Writing raw files...")

    write_json(raw_ads_dir / "campaigns.json", raw_campaigns)
    write_json(raw_ads_dir / "ad_groups.json", raw_ad_groups)
    write_json(raw_ads_dir / "keywords.json", raw_keywords)
    write_json(raw_ads_dir / "campaign_negatives.json", raw_campaign_negatives)
    write_json(raw_ads_dir / "adgroup_negatives.json", raw_adgroup_negatives)
    write_json(raw_ads_dir / "ads.json", raw_ads)
    write_json(raw_ads_dir / "assets.json", raw_assets)
    write_json(raw_ads_dir / "asset_links.json", raw_asset_links)
    write_json(raw_ads_dir / "change_history.json", raw_change_history)
    write_json(raw_ads_dir / "performance.json", raw_performance)

    write_json(raw_pmax_dir / "campaigns.json", raw_pmax_campaigns)
    write_json(raw_pmax_dir / "asset_groups.json", raw_asset_groups)
    write_json(raw_pmax_dir / "asset_group_assets.json", raw_asset_group_assets)
    write_json(raw_pmax_dir / "listing_groups.json", raw_listing_groups)
    write_json(raw_pmax_dir / "campaign_assets.json", raw_pmax_campaign_assets)
    write_json(raw_pmax_dir / "url_expansion.json", raw_url_expansion)

    # Write merchant files (if data available)
    if merchant_client and raw_merchant_products.get("count", 0) > 0:
        write_json(raw_merchant_dir / "products.json", raw_merchant_products)
        write_json(raw_merchant_dir / "product_statuses.json", raw_merchant_product_statuses)
        write_json(raw_merchant_dir / "account_issues.json", raw_merchant_account_issues)

    print(f"  Written to {raw_ads_dir}")
    print(f"  Written to {raw_pmax_dir}")
    if merchant_client:
        print(f"  Written to {raw_merchant_dir}")
    print()

    # ==========================================================================
    # NORMALIZE DATA
    # ==========================================================================
    print("Normalizing data...")

    validation_errors = []  # Track validation issues

    norm_campaigns = normalize_campaigns(raw_campaigns)
    norm_ad_groups = normalize_ad_groups(raw_ad_groups)
    norm_keywords = normalize_keywords(raw_keywords, raw_ad_groups, validation_errors)
    norm_negatives = normalize_negatives(raw_campaign_negatives, raw_adgroup_negatives)
    norm_ads = normalize_ads(raw_ads, raw_ad_groups)
    norm_assets = normalize_assets(raw_assets, raw_asset_links)
    norm_change_history = normalize_change_history(raw_change_history)
    norm_performance = normalize_performance(raw_performance)

    norm_pmax_campaigns = normalize_pmax_campaigns(raw_pmax_campaigns)
    norm_asset_groups = normalize_asset_groups(raw_asset_groups, raw_asset_group_assets)
    norm_listing_groups = normalize_listing_groups(raw_listing_groups)

    # Normalize Merchant Center data
    norm_merchant_products = {"extracted_at": None, "count": 0, "records": []}
    norm_merchant_product_status = {"extracted_at": None, "count": 0, "records": []}

    if merchant_client and raw_merchant_products.get("count", 0) > 0:
        norm_merchant_products = normalize_merchant_products(
            raw_merchant_products, raw_merchant_product_statuses, validation_errors
        )
        norm_merchant_product_status = normalize_merchant_product_status(raw_merchant_product_statuses)

    print("  Done")
    print()

    # ==========================================================================
    # WRITE NORMALIZED FILES
    # ==========================================================================
    print("Writing normalized files...")

    write_json(norm_ads_dir / "campaigns.json", norm_campaigns)
    write_json(norm_ads_dir / "ad_groups.json", norm_ad_groups)
    write_json(norm_ads_dir / "keywords.json", norm_keywords)
    write_json(norm_ads_dir / "negatives.json", norm_negatives)
    write_json(norm_ads_dir / "ads.json", norm_ads)
    write_json(norm_ads_dir / "assets.json", norm_assets)
    write_json(norm_ads_dir / "change_history.json", norm_change_history)
    write_json(norm_ads_dir / "performance.json", norm_performance)

    write_json(norm_pmax_dir / "campaigns.json", norm_pmax_campaigns)
    write_json(norm_pmax_dir / "asset_groups.json", norm_asset_groups)
    write_json(norm_pmax_dir / "listing_groups.json", norm_listing_groups)

    # Combine pmax assets into normalized (they share raw assets)
    norm_pmax_assets = {
        "extracted_at": raw_asset_group_assets.get("extracted_at"),
        "count": raw_asset_group_assets.get("count", 0),
        "records": [
            {
                "asset_group_id": extract_id(r.get("assetGroup", "")),
                "asset_id": extract_id(r.get("asset", "")),
                "field_type": r.get("fieldType"),
                "status": r.get("status"),
            }
            for r in raw_asset_group_assets.get("records", [])
        ],
    }
    write_json(norm_pmax_dir / "assets.json", norm_pmax_assets)

    # Write normalized merchant files (if data available)
    if merchant_client and norm_merchant_products.get("count", 0) > 0:
        write_json(norm_merchant_dir / "products.json", norm_merchant_products)
        write_json(norm_merchant_dir / "product_status.json", norm_merchant_product_status)

    print(f"  Written to {norm_ads_dir}")
    print(f"  Written to {norm_pmax_dir}")
    if merchant_client:
        print(f"  Written to {norm_merchant_dir}")
    print()

    # ==========================================================================
    # BUILD INDEX
    # ==========================================================================
    print("Building index...")
    index = build_index(
        norm_campaigns, norm_ad_groups, norm_keywords, norm_negatives, norm_pmax_campaigns,
        merchant_products_norm=norm_merchant_products if norm_merchant_products.get("count", 0) > 0 else None
    )
    write_json(snapshot_dir / "_index.json", index)
    print("  Done")
    print()

    # ==========================================================================
    # WRITE MANIFEST
    # ==========================================================================
    extraction_finished_utc = datetime.utcnow().isoformat() + "Z"
    duration = time.time() - start_time

    # Calculate file counts based on what was written
    raw_file_count = 16  # Ads + PMax base
    norm_file_count = 12  # Ads + PMax base
    if merchant_client and raw_merchant_products.get("count", 0) > 0:
        raw_file_count += 3  # products, product_statuses, account_issues
        norm_file_count += 2  # products, product_status

    manifest = {
        "snapshot_id": timestamp,
        "snapshot_version": SNAPSHOT_VERSION,
        "extraction_started_utc": extraction_started_utc,
        "extraction_finished_utc": extraction_finished_utc,
        "duration_seconds": round(duration, 2),
        "accounts": {
            "google_ads": {
                "customer_id": customer_id.replace("-", ""),
                "login_customer_id": login_customer_id.replace("-", "") if login_customer_id else None,
            },
            "merchant_center": {
                "merchant_id": merchant_id,
            } if merchant_id else None,
        },
        "api_versions": {
            "google_ads": GOOGLE_ADS_API_VERSION,
            "merchant_center": MERCHANT_CENTER_API_VERSION if merchant_id else None,
        },
        "file_counts": {
            "raw": raw_file_count,
            "normalized": norm_file_count,
        },
        "record_counts": {
            "raw": {
                "campaigns": raw_campaigns.get("count", 0),
                "ad_groups": raw_ad_groups.get("count", 0),
                "keywords": raw_keywords.get("count", 0),
                "campaign_negatives": raw_campaign_negatives.get("count", 0),
                "adgroup_negatives": raw_adgroup_negatives.get("count", 0),
                "ads": raw_ads.get("count", 0),
                "assets": raw_assets.get("count", 0),
                "asset_links": raw_asset_links.get("count", 0),
                "change_history": raw_change_history.get("count", 0),
                "pmax_campaigns": raw_pmax_campaigns.get("count", 0),
                "asset_groups": raw_asset_groups.get("count", 0),
                "asset_group_assets": raw_asset_group_assets.get("count", 0),
                "listing_groups": raw_listing_groups.get("count", 0),
                "merchant_products": raw_merchant_products.get("count", 0),
                "merchant_product_statuses": raw_merchant_product_statuses.get("count", 0),
                "merchant_account_issues": raw_merchant_account_issues.get("count", 0),
            },
            "normalized": {
                "campaigns": norm_campaigns.get("count", 0),
                "pmax_campaigns": norm_pmax_campaigns.get("count", 0),
                "ad_groups": norm_ad_groups.get("count", 0),
                "keywords": norm_keywords.get("count", 0),
                "negatives": norm_negatives.get("count", 0),
                "ads": norm_ads.get("count", 0),
                "assets": norm_assets.get("count", 0),
                "asset_groups": norm_asset_groups.get("count", 0),
                "listing_groups": norm_listing_groups.get("count", 0),
                "change_events": norm_change_history.get("count", 0),
                "merchant_products": norm_merchant_products.get("count", 0),
                "merchant_disapproved": norm_merchant_products.get("disapproved_count", 0),
            },
        },
        "validation": {
            "keywords_null_campaign_ids": norm_keywords.get("null_campaign_ids", 0),
            "merchant_missing_status": norm_merchant_products.get("missing_status_count", 0),
            "total_validation_errors": len(validation_errors),
        },
        "errors": errors,
    }

    write_json(snapshot_dir / "_manifest.json", manifest)

    # ==========================================================================
    # WRITE ERRORS.JSONL (if any validation errors)
    # ==========================================================================
    if validation_errors:
        errors_file = snapshot_dir / "errors.jsonl"
        with open(errors_file, "w", encoding="utf-8") as f:
            for err in validation_errors:
                f.write(json.dumps(err) + "\n")

    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print("=" * 60)
    print("SNAPSHOT COMPLETE")
    print("=" * 60)
    print()
    print(f"Location: {snapshot_dir}")
    print(f"Version:  {SNAPSHOT_VERSION}")
    print(f"Duration: {duration:.1f}s")
    print()

    print("Record counts (normalized):")
    for key, value in manifest["record_counts"]["normalized"].items():
        print(f"  {key}: {value}")
    print()

    # Validation summary
    print("Validation:")
    null_campaign_count = norm_keywords.get("null_campaign_ids", 0)
    total_keywords = norm_keywords.get("count", 0)
    if null_campaign_count > 0:
        print(f"  ⚠ Keywords with null campaign_id: {null_campaign_count}/{total_keywords}")
    else:
        print(f"  ✓ All {total_keywords} keywords have campaign_id mapped")

    # Merchant validation
    if merchant_client:
        merchant_count = norm_merchant_products.get("count", 0)
        disapproved_count = norm_merchant_products.get("disapproved_count", 0)
        if merchant_count > 0:
            if disapproved_count > 0:
                print(f"  ⚠ Merchant products disapproved: {disapproved_count}/{merchant_count}")
            else:
                print(f"  ✓ All {merchant_count} merchant products approved")

    if validation_errors:
        print(f"  ⚠ Validation errors written to errors.jsonl: {len(validation_errors)}")
    print()

    if errors:
        print(f"API ERRORS: {len(errors)} errors occurred")
        for e in errors:
            print(f"  - {e['file']}: {e['error'][:50]}...")
    else:
        print("No API errors.")

    print()
    print("Files written:")
    print(f"  {snapshot_dir}/_manifest.json")
    print(f"  {snapshot_dir}/_index.json")
    if validation_errors:
        print(f"  {snapshot_dir}/errors.jsonl")
    print(f"  {snapshot_dir}/raw/ads/ (10 files)")
    print(f"  {snapshot_dir}/raw/pmax/ (6 files)")
    if merchant_client and raw_merchant_products.get("count", 0) > 0:
        print(f"  {snapshot_dir}/raw/merchant/ (3 files)")
    print(f"  {snapshot_dir}/normalized/ads/ (8 files)")
    print(f"  {snapshot_dir}/normalized/pmax/ (4 files)")
    if merchant_client and norm_merchant_products.get("count", 0) > 0:
        print(f"  {snapshot_dir}/normalized/merchant/ (2 files)")


if __name__ == "__main__":
    main()
