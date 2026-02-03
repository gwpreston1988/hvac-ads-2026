#!/usr/bin/env python3
"""
Phase B3.2: Google Recommendations Truth Signals (READ-ONLY)

Extracts deterministic truth signals from Google's own recommendations
and cross-checks them against baseline snapshot data.

CRITICAL: This is READ-ONLY. No mutations, no plan generation in this module.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Optional


def extract_truth_signals(
    snapshot_path: Path,
    truth_sweep_path: Optional[Path] = None
) -> dict:
    """
    Extract truth signals from Google recommendations and snapshot data.

    Args:
        snapshot_path: Path to snapshot directory
        truth_sweep_path: Optional path to truth sweep output directory

    Returns:
        Dict with truth signals categorized by type
    """
    signals = {
        "rsa_asset_coverage": [],
        "keyword_recommendations": [],
        "budget_recommendations": [],
        "merchant_clarifiers": [],
        "metadata": {
            "snapshot_id": snapshot_path.name,
            "truth_sweep_available": truth_sweep_path is not None,
            "truth_sweep_path": str(truth_sweep_path) if truth_sweep_path else None
        }
    }

    # Load truth sweep data (optional)
    ads_recs = None
    merchant_issues = None

    if truth_sweep_path and truth_sweep_path.exists():
        ads_recs_path = truth_sweep_path / "ads_recommendations_normalized.json"
        if ads_recs_path.exists():
            try:
                with open(ads_recs_path) as f:
                    ads_recs = json.load(f)
            except Exception:
                pass

        merchant_path = truth_sweep_path / "merchant_issues_normalized.json"
        if merchant_path.exists():
            try:
                with open(merchant_path) as f:
                    merchant_issues = json.load(f)
            except Exception:
                pass

    # Load snapshot data
    snapshot_ads_path = snapshot_path / "normalized" / "ads"
    snapshot_pmax_path = snapshot_path / "normalized" / "pmax"

    # Signal 1: RSA Asset Coverage
    signals["rsa_asset_coverage"] = _check_rsa_asset_coverage(
        snapshot_ads_path, ads_recs
    )

    # Signal 2: Keyword Recommendation Cross-Check
    signals["keyword_recommendations"] = _check_keyword_recommendations(
        snapshot_ads_path, ads_recs
    )

    # Signal 3: Budget Recommendation Evidence
    signals["budget_recommendations"] = _check_budget_recommendations(
        snapshot_ads_path, snapshot_pmax_path, ads_recs
    )

    # Signal 4: Merchant Clarifiers
    signals["merchant_clarifiers"] = _check_merchant_clarifiers(
        merchant_issues
    )

    return signals


def _check_rsa_asset_coverage(ads_path: Path, ads_recs: Optional[dict]) -> list:
    """Check RSA asset coverage (headlines/descriptions)."""
    signals = []

    # Load ads from snapshot
    ads_file = ads_path / "ads.json"
    if not ads_file.exists():
        return signals

    try:
        with open(ads_file) as f:
            ads_data = json.load(f)
    except Exception:
        return signals

    ads = ads_data.get("ads", [])

    # Check each RSA
    for ad in ads:
        if ad.get("type") != "RESPONSIVE_SEARCH_AD":
            continue

        rsa = ad.get("responsive_search_ad", {})
        headlines = rsa.get("headlines", [])
        descriptions = rsa.get("descriptions", [])

        headline_count = len(headlines)
        description_count = len(descriptions)

        # Thresholds: 8 headlines, 3 descriptions
        if headline_count < 8 or description_count < 3:
            signal = {
                "type": "RSA_ASSET_COVERAGE_LOW",
                "severity": "MEDIUM" if headline_count >= 5 and description_count >= 2 else "HIGH",
                "ad_id": ad.get("id"),
                "ad_name": ad.get("name", "N/A"),
                "ad_group_id": ad.get("ad_group_id"),
                "campaign_id": ad.get("campaign_id"),
                "evidence": {
                    "current_headlines": headline_count,
                    "current_descriptions": description_count,
                    "threshold_headlines": 8,
                    "threshold_descriptions": 3,
                    "headlines_needed": max(0, 8 - headline_count),
                    "descriptions_needed": max(0, 3 - description_count)
                }
            }

            # Add Google suggestions if available
            if ads_recs:
                google_suggestions = _find_rsa_suggestions(ad.get("id"), ads_recs)
                if google_suggestions:
                    signal["google_suggestions"] = google_suggestions

            signals.append(signal)

    return signals


def _find_rsa_suggestions(ad_id: str, ads_recs: dict) -> Optional[dict]:
    """Find RSA suggestions from Google recommendations."""
    by_type = ads_recs.get("by_type", {})
    rsa_recs = by_type.get("RESPONSIVE_SEARCH_AD_IMPROVE_AD_STRENGTH", {})

    for example in rsa_recs.get("examples", []):
        examples_data = example.get("examples", {})
        if examples_data.get("suggested_headlines") or examples_data.get("suggested_descriptions"):
            return {
                "suggested_headlines": examples_data.get("suggested_headlines", []),
                "suggested_descriptions": examples_data.get("suggested_descriptions", [])
            }

    return None


def _check_keyword_recommendations(ads_path: Path, ads_recs: Optional[dict]) -> list:
    """Check keyword recommendations from Google against existing keywords."""
    signals = []

    if not ads_recs:
        return signals

    # Load existing keywords
    keywords_file = ads_path / "keywords.json"
    negatives_file = ads_path / "negative_keywords.json"

    existing_keywords = []
    existing_negatives = []

    if keywords_file.exists():
        try:
            with open(keywords_file) as f:
                kw_data = json.load(f)
                existing_keywords = kw_data.get("keywords", [])
        except Exception:
            pass

    if negatives_file.exists():
        try:
            with open(negatives_file) as f:
                neg_data = json.load(f)
                existing_negatives = neg_data.get("negative_keywords", [])
        except Exception:
            pass

    # Extract Google's keyword recommendations
    by_type = ads_recs.get("by_type", {})
    keyword_recs = by_type.get("KEYWORD", {})

    for rec_example in keyword_recs.get("examples", []):
        examples_data = rec_example.get("examples", {})
        keyword_text = examples_data.get("keyword_text")
        match_type = examples_data.get("keyword_match_type", "UNKNOWN")

        if not keyword_text:
            continue

        # Normalize for comparison
        keyword_text_lower = keyword_text.lower()

        # Check if already present
        already_present = any(
            kw.get("text", "").lower() == keyword_text_lower
            for kw in existing_keywords
        )

        # Check if blocked by negative
        blocked_by_negative = any(
            neg.get("text", "").lower() == keyword_text_lower
            for neg in existing_negatives
        )

        # Get related search terms from Google
        full_rec = rec_example.get("keyword_recommendation", {})
        search_terms = full_rec.get("search_terms", [])

        if blocked_by_negative:
            signal = {
                "type": "GOOGLE_RECOMMENDS_KEYWORD_BUT_NEGATIVE_BLOCKS",
                "severity": "HIGH",
                "evidence": {
                    "recommended_keyword": keyword_text,
                    "match_type": match_type,
                    "blocked_by_negative": True,
                    "search_terms": search_terms[:5] if search_terms else [],
                    "estimated_weekly_searches": sum(
                        int(st.get("estimated_weekly_search_count", 0))
                        for st in search_terms[:10]
                    ) if search_terms else None
                }
            }
            signals.append(signal)

        elif not already_present:
            signal = {
                "type": "GOOGLE_RECOMMENDS_KEYWORD_NOT_PRESENT",
                "severity": "MEDIUM",
                "evidence": {
                    "recommended_keyword": keyword_text,
                    "match_type": match_type,
                    "search_terms": search_terms[:5] if search_terms else [],
                    "estimated_weekly_searches": sum(
                        int(st.get("estimated_weekly_search_count", 0))
                        for st in search_terms[:10]
                    ) if search_terms else None,
                    "recommended_cpc_bid": examples_data.get("recommended_cpc_bid_micros")
                }
            }
            signals.append(signal)

    return signals


def _check_budget_recommendations(
    ads_path: Path,
    pmax_path: Path,
    ads_recs: Optional[dict]
) -> list:
    """Check budget recommendations from Google."""
    signals = []

    if not ads_recs:
        return signals

    # Load campaigns
    campaigns = []

    ads_campaigns_file = ads_path / "campaigns.json"
    if ads_campaigns_file.exists():
        try:
            with open(ads_campaigns_file) as f:
                camp_data = json.load(f)
                campaigns.extend(camp_data.get("campaigns", []))
        except Exception:
            pass

    pmax_campaigns_file = pmax_path / "campaigns.json"
    if pmax_campaigns_file.exists():
        try:
            with open(pmax_campaigns_file) as f:
                camp_data = json.load(f)
                campaigns.extend(camp_data.get("campaigns", []))
        except Exception:
            pass

    # Build campaign lookup
    campaigns_by_id = {str(c.get("id")): c for c in campaigns}

    # Extract budget recommendations
    by_type = ads_recs.get("by_type", {})
    budget_recs = by_type.get("CAMPAIGN_BUDGET", {})

    for rec_example in budget_recs.get("examples", []):
        examples_data = rec_example.get("examples", {})
        current_micros = examples_data.get("current_budget_micros")
        recommended_micros = examples_data.get("recommended_budget_micros")
        increase_micros = examples_data.get("budget_increase_micros")

        if not current_micros or not recommended_micros:
            continue

        # Extract campaign_id from resource_name if possible
        resource_name = rec_example.get("resource_name", "")
        # Format: customers/{customer_id}/recommendations/{rec_id}
        # Budget recs don't directly reference campaign in resource_name
        # We'd need to parse campaign_budget_recommendation.campaign field

        budget_rec_detail = rec_example.get("campaign_budget_recommendation", {})
        campaign_resource = budget_rec_detail.get("campaign", "")
        campaign_id = campaign_resource.split("/")[-1] if campaign_resource else None

        campaign = campaigns_by_id.get(campaign_id) if campaign_id else None

        signal = {
            "type": "GOOGLE_RECOMMENDS_BUDGET_INCREASE",
            "severity": "MEDIUM",
            "evidence": {
                "current_budget_micros": current_micros,
                "recommended_budget_micros": recommended_micros,
                "budget_increase_micros": increase_micros,
                "current_budget_daily": current_micros / 1_000_000,
                "recommended_budget_daily": recommended_micros / 1_000_000,
                "budget_increase_daily": increase_micros / 1_000_000,
                "campaign_id": campaign_id,
                "campaign_name": campaign.get("name") if campaign else "Unknown"
            }
        }

        # Add budget utilization if campaign found
        if campaign:
            # This would need to be joined from report metrics
            # For now, just note it's available
            signal["evidence"]["campaign_status"] = campaign.get("status")
            signal["evidence"]["bidding_strategy"] = campaign.get("bidding_strategy_type")

        signals.append(signal)

    return signals


def _check_merchant_clarifiers(merchant_issues: Optional[dict]) -> list:
    """Generate merchant clarifiers about approval vs serving."""
    clarifiers = []

    clarifier = {
        "type": "MERCHANT_APPROVAL_VS_SERVING_CLARIFIER",
        "severity": "INFO",
        "message": "merchant_disapproved = 0 means feed approvals, NOT serving guarantees",
        "details": [
            "Product approval in Merchant Center means feed passes quality checks",
            "Actual serving depends on: listing group filters, budget, bids, competition",
            "Use GSC + Shopping campaigns to diagnose serving issues"
        ]
    }

    if merchant_issues:
        total_products = merchant_issues.get("total_products_checked", 0)
        disapproved = merchant_issues.get("disapproved_count", 0)

        clarifier["evidence"] = {
            "total_products_checked": total_products,
            "disapproved_count": disapproved,
            "approval_rate": f"{((total_products - disapproved) / total_products * 100):.1f}%" if total_products > 0 else "N/A"
        }

        # Add top disapproval reasons if any
        if disapproved > 0:
            top_reasons = merchant_issues.get("top_disapproval_reasons", [])
            if top_reasons:
                clarifier["evidence"]["top_disapproval_reasons"] = [
                    {"reason": reason, "count": count}
                    for reason, count in top_reasons[:3]
                ]

    clarifiers.append(clarifier)

    return clarifiers
