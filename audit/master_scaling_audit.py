#!/usr/bin/env python3
"""
Master Scaling Audit - 6-Task Analysis
Quantifies Brand Leakage, Intent Mismatch, and Reclaimable Budget
"""

import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

import requests
from dotenv import load_dotenv

API_VERSION = "v19"

# Competitor brands (not our brands - leaking budget)
COMPETITOR_BRANDS = [
    "trane", "carrier", "lennox", "bryant", "york", "coleman", "tempstar",
    "payne", "heil", "armstrong", "nordyne", "maytag", "frigidaire",
    "bosch", "mitsubishi", "fujitsu", "lg", "samsung", "panasonic",
    "american standard", "comfortmaker", "arcoaire", "day & night"
]

# Parts modifiers (low-dollar intent vs unit sales)
PARTS_MODIFIERS = [
    "motor", "filter", "capacitor", "igniter", "belt", "blower", "coil",
    "valve", "sensor", "board", "relay", "fuse", "switch", "thermostat part",
    "flame sensor", "inducer", "transformer", "contactor", "fan blade",
    "compressor", "starter", "hard start", "run capacitor", "dual capacitor",
    "drain pan", "limit switch", "pressure switch", "roll out switch",
    "gas valve", "ignitor", "hot surface igniter", "pilot assembly"
]

# High-value unit terms (what we WANT to target)
UNIT_TERMS = [
    "furnace", "heat pump", "air conditioner", "ac unit", "hvac unit",
    "package unit", "air handler", "condenser", "split system",
    "central air", "mini split", "ductless"
]

# Technical spec patterns for model verification
TECH_SPECS = {
    "96% AFUE": ["96% afue", "96 afue", "96 efficiency", "high efficiency furnace", "96% efficiency"],
    "14.3 SEER2": ["14.3 seer", "14 seer2", "14.3 seer2", "heat pump replacement"],
    "tonnage": [r"\d+\s*ton", r"\d+\.?\d*\s*ton"]
}


def load_env():
    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path.home() / "BCD_SEO_Intelligence_Engine" / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            return
    print("WARNING: No .env file found")


def get_credentials():
    required = [
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET",
        "GOOGLE_ADS_REFRESH_TOKEN",
        "GOOGLE_ADS_CUSTOMER_ID",
    ]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print(f"ERROR: Missing: {', '.join(missing)}")
        sys.exit(1)

    return {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "customer_id": os.getenv("GOOGLE_ADS_CUSTOMER_ID").replace("-", ""),
        "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "") or None,
    }


def get_access_token(credentials):
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
            "refresh_token": credentials["refresh_token"],
            "grant_type": "refresh_token",
        },
    )
    if response.status_code != 200:
        raise Exception(f"Token refresh failed: {response.text}")
    return response.json()["access_token"]


def google_ads_query(credentials, access_token, query):
    url = f"https://googleads.googleapis.com/{API_VERSION}/customers/{credentials['customer_id']}/googleAds:searchStream"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": credentials["developer_token"],
        "Content-Type": "application/json",
    }
    if credentials["login_customer_id"]:
        headers["login-customer-id"] = credentials["login_customer_id"]
    response = requests.post(url, headers=headers, json={"query": query})
    if response.status_code != 200:
        error = response.json().get("error", {}).get("message", response.text)
        raise Exception(f"API Error: {error}")
    return response.json()


def load_brand_terms():
    config_path = Path(__file__).parent.parent / "configs" / "brand_terms.json"
    with open(config_path) as f:
        config = json.load(f)
    all_terms = set(config.get("brand_terms", []))
    for variants in config.get("brand_variants", {}).values():
        all_terms.update(variants)
    return list(all_terms)


def check_brand_match(term, brand_terms):
    term_lower = term.lower()
    for brand in brand_terms:
        pattern = r"\b" + re.escape(brand.lower()) + r"\b"
        if re.search(pattern, term_lower):
            return True, brand
    return False, None


def check_competitor_match(term):
    term_lower = term.lower()
    for competitor in COMPETITOR_BRANDS:
        if competitor in term_lower:
            return True, competitor
    return False, None


def check_parts_intent(term):
    term_lower = term.lower()
    for part in PARTS_MODIFIERS:
        if part in term_lower:
            return True, part
    return False, None


def is_unit_intent(term):
    term_lower = term.lower()
    for unit in UNIT_TERMS:
        if unit in term_lower:
            return True
    return False


# ============================================================================
# TASK 1: PMax Brand Leakage Analysis
# ============================================================================
def task1_pmax_brand_leakage(credentials, access_token, brand_terms, days=30):
    print("\n" + "=" * 70)
    print("TASK 1: PMax Brand Leakage Analysis")
    print("=" * 70)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Get PMax search term insights
    query = f"""
        SELECT
            campaign_search_term_insight.category_label,
            campaign.id,
            campaign.name
        FROM campaign_search_term_insight
        WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX'
            AND segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
    """

    try:
        result = google_ads_query(credentials, access_token, query)
        terms = []
        if result:
            for chunk in result:
                for row in chunk.get("results", []):
                    insight = row.get("campaignSearchTermInsight", {})
                    category = insight.get("categoryLabel", "")
                    if category:
                        terms.append(category)
    except Exception as e:
        print(f"  Error: {e}")
        terms = []

    # Get PMax campaign spend
    query = f"""
        SELECT
            campaign.name,
            metrics.cost_micros,
            metrics.conversions_value
        FROM campaign
        WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX'
            AND segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
    """
    result = google_ads_query(credentials, access_token, query)
    pmax_spend = 0
    pmax_value = 0
    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                metrics = row.get("metrics", {})
                pmax_spend += int(metrics.get("costMicros", 0)) / 1_000_000
                pmax_value += float(metrics.get("conversionsValue", 0))

    # Analyze brand leakage
    brand_matches = []
    brand_counts = defaultdict(int)

    for term in terms:
        is_brand, matched = check_brand_match(term, brand_terms)
        if is_brand:
            brand_matches.append({"term": term, "brand": matched})
            brand_counts[matched] += 1

    # Estimate brand leakage spend (proportional to term frequency)
    brand_ratio = len(brand_matches) / len(terms) if terms else 0
    estimated_brand_spend = pmax_spend * brand_ratio

    print(f"\nTotal PMax Spend (30d): ${pmax_spend:,.2f}")
    print(f"Total PMax Conv Value: ${pmax_value:,.2f}")
    print(f"PMax ROAS: {pmax_value/pmax_spend:.2f}" if pmax_spend > 0 else "N/A")
    print(f"\nTotal Search Terms: {len(terms)}")
    print(f"Brand Term Matches: {len(brand_matches)}")
    print(f"Brand Leakage Ratio: {brand_ratio:.1%}")
    print(f"\n*** ESTIMATED BRAND TAX: ${estimated_brand_spend:,.2f}/month ***")

    print("\nBrand Leakage by Brand:")
    for brand, count in sorted(brand_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {brand:<20} {count:>5} occurrences")

    return {
        "total_terms": len(terms),
        "brand_matches": len(brand_matches),
        "brand_terms_list": brand_matches,
        "brand_counts": dict(brand_counts),
        "pmax_spend": pmax_spend,
        "estimated_brand_spend": estimated_brand_spend
    }


# ============================================================================
# TASK 2: Branded Campaign Hardening Audit
# ============================================================================
def task2_branded_hardening(credentials, access_token, brand_terms, days=30):
    print("\n" + "=" * 70)
    print("TASK 2: Branded Campaign 'Hardening' Audit")
    print("=" * 70)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    query = f"""
        SELECT
            search_term_view.search_term,
            campaign.name,
            ad_group.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value,
            segments.search_term_match_type
        FROM search_term_view
        WHERE campaign.status = 'ENABLED'
            AND segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
        ORDER BY metrics.cost_micros DESC
    """

    result = google_ads_query(credentials, access_token, query)
    branded_terms = []

    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                stv = row.get("searchTermView", {})
                campaign = row.get("campaign", {})
                metrics = row.get("metrics", {})
                segments = row.get("segments", {})

                if "branded" in campaign.get("name", "").lower():
                    cost = int(metrics.get("costMicros", 0)) / 1_000_000
                    clicks = int(metrics.get("clicks", 0))
                    cpc = cost / clicks if clicks > 0 else 0

                    branded_terms.append({
                        "term": stv.get("searchTerm", ""),
                        "campaign": campaign.get("name"),
                        "impressions": int(metrics.get("impressions", 0)),
                        "clicks": clicks,
                        "cost": cost,
                        "cpc": cpc,
                        "conversions": float(metrics.get("conversions", 0)),
                        "conv_value": float(metrics.get("conversionsValue", 0)),
                        "match_type": segments.get("searchTermMatchType", "")
                    })

    # Find high CPC terms ($10+)
    high_cpc_terms = [t for t in branded_terms if t["cpc"] >= 10.0]
    very_high_cpc = [t for t in branded_terms if t["cpc"] >= 25.0]

    # Find competitor terms
    competitor_terms = []
    for t in branded_terms:
        is_comp, comp = check_competitor_match(t["term"])
        if is_comp:
            t["competitor"] = comp
            competitor_terms.append(t)

    # Find broad match terms (potential waste)
    broad_terms = [t for t in branded_terms if t["match_type"] == "BROAD"]

    print(f"\nTotal Branded Search Terms: {len(branded_terms)}")
    print(f"Total Branded Spend (30d): ${sum(t['cost'] for t in branded_terms):,.2f}")

    print(f"\n*** HIGH CPC TERMS ($10+): {len(high_cpc_terms)} ***")
    print("-" * 70)
    high_cpc_waste = 0
    for t in sorted(high_cpc_terms, key=lambda x: x["cpc"], reverse=True)[:15]:
        conv_rate = t["conversions"] / t["clicks"] if t["clicks"] > 0 else 0
        print(f"  ${t['cpc']:>6.2f} | {t['term'][:40]:<40} | Conv: {t['conversions']:.1f}")
        if t["conversions"] == 0:
            high_cpc_waste += t["cost"]

    print(f"\n*** $27+ CLICKS (CRITICAL): {len(very_high_cpc)} ***")
    for t in very_high_cpc:
        print(f"  >>> ${t['cpc']:.2f} - '{t['term']}' ({t['match_type']}) - Conv: {t['conversions']}")

    print(f"\n*** COMPETITOR TERMS TRIGGERING BRANDED: {len(competitor_terms)} ***")
    print("-" * 70)
    competitor_waste = sum(t["cost"] for t in competitor_terms if t["conversions"] == 0)
    for t in competitor_terms[:10]:
        print(f"  {t['competitor']:<15} | ${t['cost']:>6.2f} | {t['term'][:35]}")

    print(f"\n*** BROAD MATCH TERMS (HARDENING NEEDED): {len(broad_terms)} ***")
    broad_waste = sum(t["cost"] for t in broad_terms if t["conversions"] == 0)

    return {
        "high_cpc_terms": high_cpc_terms,
        "very_high_cpc": very_high_cpc,
        "competitor_terms": competitor_terms,
        "broad_terms": broad_terms,
        "high_cpc_waste": high_cpc_waste,
        "competitor_waste": competitor_waste,
        "broad_waste": broad_waste,
        "total_branded_spend": sum(t['cost'] for t in branded_terms)
    }


# ============================================================================
# TASK 3: Organic Cannibalization Check
# ============================================================================
def task3_organic_cannibalization(branded_terms):
    print("\n" + "=" * 70)
    print("TASK 3: Organic Cannibalization Check")
    print("=" * 70)

    # Identify pure brand terms that likely rank #1 organically
    pure_brand_terms = []
    for t in branded_terms:
        term_lower = t["term"].lower()
        if any(brand in term_lower for brand in ["buy comfort direct", "buycomfortdirect", "bcd"]):
            pure_brand_terms.append(t)

    organic_cannibalization_spend = sum(t["cost"] for t in pure_brand_terms)

    print(f"\nPure Brand Terms Identified: {len(pure_brand_terms)}")
    print(f"Pure Brand Spend (potential cannibalization): ${organic_cannibalization_spend:,.2f}")
    print("\nNOTE: Compare with GSC data for accurate organic position data")
    print("Terms likely ranking #1 organically (savings opportunity):")
    for t in pure_brand_terms[:10]:
        print(f"  '{t['term']}' - ${t['cost']:.2f}")

    return {
        "pure_brand_terms": pure_brand_terms,
        "potential_savings": organic_cannibalization_spend * 0.3  # 30% reduction estimate
    }


# ============================================================================
# TASK 4: Parts vs Units Intent Audit
# ============================================================================
def task4_parts_vs_units(credentials, access_token, days=30):
    print("\n" + "=" * 70)
    print("TASK 4: Parts vs Units Intent Audit")
    print("=" * 70)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Get all search terms
    query = f"""
        SELECT
            search_term_view.search_term,
            campaign.name,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value
        FROM search_term_view
        WHERE campaign.status = 'ENABLED'
            AND segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
    """

    result = google_ads_query(credentials, access_token, query)
    parts_terms = []
    unit_terms = []

    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                stv = row.get("searchTermView", {})
                metrics = row.get("metrics", {})
                term = stv.get("searchTerm", "")

                data = {
                    "term": term,
                    "cost": int(metrics.get("costMicros", 0)) / 1_000_000,
                    "conversions": float(metrics.get("conversions", 0)),
                    "conv_value": float(metrics.get("conversionsValue", 0))
                }

                is_parts, part_type = check_parts_intent(term)
                if is_parts:
                    data["part_type"] = part_type
                    parts_terms.append(data)
                elif is_unit_intent(term):
                    unit_terms.append(data)

    parts_spend = sum(t["cost"] for t in parts_terms)
    parts_no_conv = sum(t["cost"] for t in parts_terms if t["conversions"] == 0)
    unit_spend = sum(t["cost"] for t in unit_terms)

    print(f"\nPARTS INTENT ANALYSIS:")
    print(f"  Parts-related terms: {len(parts_terms)}")
    print(f"  Parts spend: ${parts_spend:,.2f}")
    print(f"  Parts spend with 0 conversions: ${parts_no_conv:,.2f}")

    print(f"\nUNIT INTENT ANALYSIS:")
    print(f"  Unit-related terms: {len(unit_terms)}")
    print(f"  Unit spend: ${unit_spend:,.2f}")

    print(f"\n*** BUDGET BLEEDING TO LOW-DOLLAR PARTS: ${parts_no_conv:,.2f} ***")

    print("\nTop Parts Terms (potential negatives):")
    for t in sorted(parts_terms, key=lambda x: x["cost"], reverse=True)[:15]:
        print(f"  ${t['cost']:>6.2f} | {t['term'][:45]} | Conv: {t['conversions']:.1f}")

    return {
        "parts_terms": parts_terms,
        "parts_spend": parts_spend,
        "parts_no_conv_spend": parts_no_conv,
        "unit_terms": unit_terms,
        "unit_spend": unit_spend
    }


# ============================================================================
# TASK 5: High-CPM 'Ego' Terms
# ============================================================================
def task5_ego_terms(credentials, access_token, days=90):
    print("\n" + "=" * 70)
    print("TASK 5: High-CPM 'Ego' Terms (High Impressions, 0% Conversion)")
    print("=" * 70)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    query = f"""
        SELECT
            search_term_view.search_term,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions
        FROM search_term_view
        WHERE campaign.status = 'ENABLED'
            AND metrics.impressions > 10
            AND segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
        ORDER BY metrics.impressions DESC
    """

    result = google_ads_query(credentials, access_token, query)
    ego_terms = []

    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                stv = row.get("searchTermView", {})
                metrics = row.get("metrics", {})

                conversions = float(metrics.get("conversions", 0))
                impressions = int(metrics.get("impressions", 0))
                clicks = int(metrics.get("clicks", 0))
                cost = int(metrics.get("costMicros", 0)) / 1_000_000

                conv_rate = conversions / clicks if clicks > 0 else 0

                if conversions == 0 and impressions > 20:
                    ego_terms.append({
                        "term": stv.get("searchTerm", ""),
                        "impressions": impressions,
                        "clicks": clicks,
                        "cost": cost,
                        "conv_rate": conv_rate
                    })

    ego_spend = sum(t["cost"] for t in ego_terms)

    print(f"\nHigh Impression / 0% Conversion Terms: {len(ego_terms)}")
    print(f"Ego Term Spend (90d): ${ego_spend:,.2f}")

    print("\n*** TOP EGO TERMS (IMPRESSION SHARE WASTED): ***")
    print("-" * 70)
    for t in sorted(ego_terms, key=lambda x: x["impressions"], reverse=True)[:20]:
        ctr = t["clicks"] / t["impressions"] * 100 if t["impressions"] > 0 else 0
        print(f"  {t['impressions']:>6} impr | ${t['cost']:>6.2f} | CTR {ctr:.1f}% | {t['term'][:40]}")

    return {
        "ego_terms": ego_terms,
        "ego_spend": ego_spend
    }


# ============================================================================
# TASK 6: Technical Logic Mapping
# ============================================================================
def task6_technical_mapping(credentials, access_token, days=30):
    print("\n" + "=" * 70)
    print("TASK 6: Technical Logic Mapping - Model to Spec Verification")
    print("=" * 70)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Target models and their specs
    model_specs = {
        "Goodman GR9S (96% AFUE)": {
            "patterns": ["gr9s", "goodman 96", "96 afue", "96% efficiency", "high efficiency furnace"],
            "found": []
        },
        "Rheem RP14 (14.3 SEER2)": {
            "patterns": ["rp14", "rheem 14", "14.3 seer", "14 seer2", "heat pump replacement"],
            "found": []
        },
        "Solace SGLX4 (AC/Tonnage)": {
            "patterns": ["sglx4", "solace", "4 ton ac", "3 ton ac", "5 ton ac"],
            "found": []
        }
    }

    query = f"""
        SELECT
            search_term_view.search_term,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions_value
        FROM search_term_view
        WHERE campaign.status = 'ENABLED'
            AND segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
    """

    result = google_ads_query(credentials, access_token, query)
    all_terms = []

    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                stv = row.get("searchTermView", {})
                metrics = row.get("metrics", {})
                term = stv.get("searchTerm", "").lower()
                all_terms.append({
                    "term": term,
                    "impressions": int(metrics.get("impressions", 0)),
                    "clicks": int(metrics.get("clicks", 0)),
                    "conv_value": float(metrics.get("conversionsValue", 0))
                })

                for model, data in model_specs.items():
                    for pattern in data["patterns"]:
                        if pattern in term:
                            data["found"].append({
                                "term": term,
                                "impressions": int(metrics.get("impressions", 0)),
                                "clicks": int(metrics.get("clicks", 0)),
                                "conv_value": float(metrics.get("conversionsValue", 0))
                            })
                            break

    print("\nTECHNICAL SPEC MAPPING RESULTS:")
    print("-" * 70)

    for model, data in model_specs.items():
        unique_terms = {t["term"]: t for t in data["found"]}
        print(f"\n{model}:")
        print(f"  Matching Terms Found: {len(unique_terms)}")
        if unique_terms:
            total_value = sum(t["conv_value"] for t in unique_terms.values())
            print(f"  Total Conversion Value: ${total_value:,.2f}")
            for term, t in list(unique_terms.items())[:5]:
                print(f"    - '{term}' ({t['impressions']} impr, ${t['conv_value']:.2f} value)")
        else:
            print(f"  ⚠️  NO MATCHING TERMS - CHECK AD TARGETING!")

    return model_specs


# ============================================================================
# MAIN AUDIT REPORT
# ============================================================================
def main():
    print("=" * 70)
    print("MASTER SCALING AUDIT - BUY COMFORT DIRECT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    load_env()
    credentials = get_credentials()
    access_token = get_access_token(credentials)
    brand_terms = load_brand_terms()

    # Execute all 6 tasks
    task1_results = task1_pmax_brand_leakage(credentials, access_token, brand_terms)
    task2_results = task2_branded_hardening(credentials, access_token, brand_terms)
    task3_results = task3_organic_cannibalization(task2_results.get("high_cpc_terms", []) + task2_results.get("competitor_terms", []))
    task4_results = task4_parts_vs_units(credentials, access_token)
    task5_results = task5_ego_terms(credentials, access_token)
    task6_results = task6_technical_mapping(credentials, access_token)

    # ============================================================================
    # UNIFIED SUMMARY REPORT
    # ============================================================================
    print("\n" + "=" * 70)
    print("UNIFIED AUDIT SUMMARY - RECLAIMABLE BUDGET")
    print("=" * 70)

    reclaimable = {
        "PMax Brand Leakage (Task 1)": task1_results["estimated_brand_spend"],
        "High CPC Waste - $10+ (Task 2)": task2_results["high_cpc_waste"],
        "Competitor Term Waste (Task 2)": task2_results["competitor_waste"],
        "Organic Cannibalization Est (Task 3)": task3_results["potential_savings"],
        "Parts Intent Waste (Task 4)": task4_results["parts_no_conv_spend"],
        "Ego Term Waste (Task 5)": task5_results["ego_spend"],
    }

    print("\n" + "-" * 70)
    print(f"{'Category':<45} {'Amount':>15}")
    print("-" * 70)

    total_reclaimable = 0
    for category, amount in reclaimable.items():
        print(f"{category:<45} ${amount:>14,.2f}")
        total_reclaimable += amount

    print("-" * 70)
    print(f"{'TOTAL RECLAIMABLE BUDGET (Monthly Est.)':<45} ${total_reclaimable:>14,.2f}")
    print("=" * 70)

    # Output CSVs
    output_dir = Path(__file__).parent.parent / "output"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Brand terms for PMax negative list
    brand_csv = output_dir / f"pmax_negative_brand_terms_{timestamp}.csv"
    with open(brand_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["search_term", "matched_brand"])
        for bt in task1_results["brand_terms_list"]:
            writer.writerow([bt["term"], bt["brand"]])
    print(f"\n✓ PMax Negative List ({len(task1_results['brand_terms_list'])} terms): {brand_csv}")

    # Exact match candidates
    exact_csv = output_dir / f"exact_match_hardening_{timestamp}.csv"
    with open(exact_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["search_term", "cpc", "cost", "conversions", "match_type", "issue"])
        for t in task2_results["high_cpc_terms"]:
            issue = "HIGH_CPC"
            if t.get("competitor"):
                issue = f"COMPETITOR:{t['competitor']}"
            writer.writerow([t["term"], t["cpc"], t["cost"], t["conversions"], t["match_type"], issue])
    print(f"✓ Exact Match Candidates ({len(task2_results['high_cpc_terms'])} terms): {exact_csv}")

    # Summary report
    summary_csv = output_dir / f"master_audit_summary_{timestamp}.csv"
    with open(summary_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "reclaimable_amount"])
        for cat, amt in reclaimable.items():
            writer.writerow([cat, amt])
        writer.writerow(["TOTAL", total_reclaimable])
    print(f"✓ Summary Report: {summary_csv}")

    print("\n" + "=" * 70)
    print("AUDIT COMPLETE")
    print("=" * 70)
    print(f"\n🎯 TOTAL RECLAIMABLE BUDGET: ${total_reclaimable:,.2f}/month")
    print(f"📊 Brand Terms for PMax Negatives: {len(task1_results['brand_terms_list'])}")
    print(f"🔧 Exact Match Candidates: {len(task2_results['high_cpc_terms'])}")
    print("=" * 70)


if __name__ == "__main__":
    main()
