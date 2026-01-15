#!/usr/bin/env python3
"""
Keyword Conflicts & Exact Match Migration Audit

1. Finds overlaps between Branded Search keywords and PMax search terms
2. Analyzes Branded campaign search terms for high-converting technical terms
3. Recommends migration from Broad/Phrase to Exact match structure
"""

import csv
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

# API version
API_VERSION = "v19"

# Campaign name patterns
BRANDED_CAMPAIGN_PATTERNS = ["branded", "brand", "bcd branded"]


def load_env():
    """Load .env from local directory or fallback locations."""
    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path.home() / "BCD_SEO_Intelligence_Engine" / ".env",
        Path(__file__).parent.parent.parent / "apps" / "api" / ".env",
        Path(__file__).parent.parent.parent / ".env",
    ]

    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"Loaded credentials from: {env_path}")
            return

    print("WARNING: No .env file found")


def get_credentials():
    """Get Google Ads credentials from environment."""
    required = [
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET",
        "GOOGLE_ADS_REFRESH_TOKEN",
        "GOOGLE_ADS_CUSTOMER_ID",
    ]

    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
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
    """Exchange refresh token for access token."""
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
    """Execute Google Ads query via REST API."""
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
        raise Exception(f"API Error ({response.status_code}): {error}")

    return response.json()


def is_technical_term(search_term):
    """
    Identify technical/model number terms that should be exact match.
    Patterns: model numbers, SKUs, part numbers, specific dimensions
    """
    patterns = [
        r"\b[A-Z]{2,4}[0-9]{2,}[A-Z]*\b",  # Model numbers like RA1424AJ1NA,!"GSXH501810
        r"\b[0-9]{5,}\b",  # Long numeric codes
        r"\b[A-Z]+[0-9]+[A-Z]+[0-9]+\b",  # Alternating letter-number patterns
        r"\b\d+\s*(ton|seer|btu)\b",  # HVAC specifications
        r"\b\d+k?\s*btu\b",  # BTU ratings
        r"\bra\d+\b",  # Rheem model prefixes
        r"\bgsx[a-z]*\d+\b",  # Goodman model prefixes
        r"\brg[a-z]*\d+\b",  # Rheem gas furnace models
    ]

    term_lower = search_term.lower()
    for pattern in patterns:
        if re.search(pattern, term_lower, re.IGNORECASE):
            return True

    return False


def get_branded_search_terms(credentials, access_token, days=30):
    """Get search terms from Branded Search campaigns with metrics."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    query = f"""
        SELECT
            search_term_view.search_term,
            campaign.id,
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
        ORDER BY metrics.conversions DESC, metrics.cost_micros DESC
    """

    print(f"Fetching search terms from all campaigns ({days} days)...")
    result = google_ads_query(credentials, access_token, query)

    branded_terms = []
    other_terms = []

    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                search_term_view = row.get("searchTermView", {})
                campaign = row.get("campaign", {})
                ad_group = row.get("adGroup", {})
                metrics = row.get("metrics", {})
                segments = row.get("segments", {})

                campaign_name = campaign.get("name", "").lower()
                is_branded = any(p in campaign_name for p in BRANDED_CAMPAIGN_PATTERNS)

                term_data = {
                    "search_term": search_term_view.get("searchTerm", ""),
                    "campaign_id": campaign.get("id"),
                    "campaign_name": campaign.get("name"),
                    "ad_group": ad_group.get("name"),
                    "impressions": int(metrics.get("impressions", 0)),
                    "clicks": int(metrics.get("clicks", 0)),
                    "cost": int(metrics.get("costMicros", 0)) / 1_000_000,
                    "conversions": float(metrics.get("conversions", 0)),
                    "conv_value": float(metrics.get("conversionsValue", 0)),
                    "match_type": segments.get("searchTermMatchType", "UNSPECIFIED"),
                }

                if is_branded:
                    branded_terms.append(term_data)
                else:
                    other_terms.append(term_data)

    return branded_terms, other_terms


def get_branded_keywords(credentials, access_token):
    """Get keywords from Branded campaigns with match types."""
    query = """
        SELECT
            campaign.id,
            campaign.name,
            ad_group.id,
            ad_group.name,
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions
        FROM keyword_view
        WHERE campaign.status = 'ENABLED'
            AND ad_group.status = 'ENABLED'
            AND ad_group_criterion.status = 'ENABLED'
            AND segments.date DURING LAST_30_DAYS
    """

    print("Fetching keywords from campaigns...")
    result = google_ads_query(credentials, access_token, query)

    keywords = {"branded": [], "other": []}

    if result:
        for chunk in result:
            for row in chunk.get("results", []):
                campaign = row.get("campaign", {})
                ad_group = row.get("adGroup", {})
                criterion = row.get("adGroupCriterion", {}).get("keyword", {})
                metrics = row.get("metrics", {})

                campaign_name = campaign.get("name", "").lower()
                is_branded = any(p in campaign_name for p in BRANDED_CAMPAIGN_PATTERNS)

                kw_data = {
                    "keyword": criterion.get("text", ""),
                    "match_type": criterion.get("matchType", ""),
                    "campaign_id": campaign.get("id"),
                    "campaign_name": campaign.get("name"),
                    "ad_group": ad_group.get("name"),
                    "impressions": int(metrics.get("impressions", 0)),
                    "clicks": int(metrics.get("clicks", 0)),
                    "cost": int(metrics.get("costMicros", 0)) / 1_000_000,
                    "conversions": float(metrics.get("conversions", 0)),
                }

                if is_branded:
                    keywords["branded"].append(kw_data)
                else:
                    keywords["other"].append(kw_data)

    return keywords


def analyze_exact_match_candidates(branded_terms):
    """
    Analyze branded search terms for exact match migration candidates.
    Criteria:
    - High conversion rate
    - Technical terms (model numbers)
    - Currently served by Broad or Phrase match
    """
    candidates = []

    for term in branded_terms:
        conv_rate = term["conversions"] / term["clicks"] if term["clicks"] > 0 else 0
        cpc = term["cost"] / term["clicks"] if term["clicks"] > 0 else 0
        roas = term["conv_value"] / term["cost"] if term["cost"] > 0 else 0

        is_technical = is_technical_term(term["search_term"])
        is_broad_or_phrase = term["match_type"] in ["BROAD", "PHRASE", "NEAR_EXACT"]

        # Score based on performance
        score = 0
        reasons = []

        if term["conversions"] >= 1:
            score += 30
            reasons.append(f"{term['conversions']:.0f} conversions")

        if conv_rate >= 0.05:  # 5%+ conversion rate
            score += 25
            reasons.append(f"{conv_rate:.1%} conv rate")

        if is_technical:
            score += 20
            reasons.append("technical term")

        if roas >= 3.0:
            score += 15
            reasons.append(f"ROAS {roas:.1f}")

        if is_broad_or_phrase:
            score += 10
            reasons.append(f"currently {term['match_type']}")

        if score >= 30:  # Threshold for recommendation
            candidates.append({
                "search_term": term["search_term"],
                "campaign": term["campaign_name"],
                "ad_group": term["ad_group"],
                "current_match": term["match_type"],
                "impressions": term["impressions"],
                "clicks": term["clicks"],
                "cost": term["cost"],
                "conversions": term["conversions"],
                "conv_value": term["conv_value"],
                "conv_rate": conv_rate,
                "cpc": cpc,
                "roas": roas,
                "is_technical": is_technical,
                "score": score,
                "reasons": ", ".join(reasons),
            })

    # Sort by score (highest first)
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates


def main():
    print("=" * 70)
    print("Keyword Conflicts & Exact Match Migration Audit")
    print("=" * 70)
    print()

    load_env()
    credentials = get_credentials()
    print(f"Customer ID: {credentials['customer_id']}")
    print()

    print("Authenticating...")
    access_token = get_access_token(credentials)
    print("OK")
    print()

    # Get branded search terms
    branded_terms, other_terms = get_branded_search_terms(credentials, access_token, days=30)
    print(f"Found {len(branded_terms)} branded campaign search terms")
    print(f"Found {len(other_terms)} other campaign search terms")
    print()

    # Get keywords
    keywords = get_branded_keywords(credentials, access_token)
    print(f"Found {len(keywords['branded'])} branded keywords")
    print()

    # Analyze exact match candidates
    print("Analyzing exact match migration candidates...")
    candidates = analyze_exact_match_candidates(branded_terms)
    print(f"Found {len(candidates)} candidates for exact match migration")
    print()

    # Output directory
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Write exact match candidates CSV
    candidates_csv = output_dir / f"exact_match_candidates_{timestamp}.csv"
    with open(candidates_csv, "w", newline="") as f:
        if candidates:
            writer = csv.DictWriter(f, fieldnames=candidates[0].keys())
            writer.writeheader()
            writer.writerows(candidates)
    print(f"Exact match candidates CSV: {candidates_csv}")

    # Write all branded search terms CSV
    branded_csv = output_dir / f"branded_search_terms_{timestamp}.csv"
    with open(branded_csv, "w", newline="") as f:
        if branded_terms:
            writer = csv.DictWriter(f, fieldnames=branded_terms[0].keys())
            writer.writeheader()
            writer.writerows(branded_terms)
    print(f"Branded search terms CSV: {branded_csv}")
    print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()

    # Branded campaign stats
    if branded_terms:
        total_spend = sum(t["cost"] for t in branded_terms)
        total_conv = sum(t["conversions"] for t in branded_terms)
        total_value = sum(t["conv_value"] for t in branded_terms)
        overall_roas = total_value / total_spend if total_spend > 0 else 0

        print("BRANDED CAMPAIGN PERFORMANCE (30 days):")
        print("-" * 70)
        print(f"  Total search terms: {len(branded_terms)}")
        print(f"  Total spend: ${total_spend:,.2f}")
        print(f"  Total conversions: {total_conv:.0f}")
        print(f"  Overall ROAS: {overall_roas:.2f}")
        print()

    # Exact match candidates
    if candidates:
        print("TOP EXACT MATCH MIGRATION CANDIDATES:")
        print("-" * 70)
        print(f"{'Search Term':<40} {'Conv':<6} {'ROAS':<8} {'Score':<6} Reasons")
        print("-" * 70)
        for c in candidates[:15]:
            term_short = c["search_term"][:38]
            print(f"{term_short:<40} {c['conversions']:<6.0f} {c['roas']:<8.2f} {c['score']:<6} {c['reasons']}")
        print()

        # Technical terms breakdown
        technical = [c for c in candidates if c["is_technical"]]
        if technical:
            print(f"TECHNICAL/MODEL TERMS FOUND: {len(technical)}")
            print("-" * 70)
            for c in technical[:10]:
                print(f"  {c['search_term'][:50]}")
            print()

        # Match type distribution
        print("CURRENT MATCH TYPE DISTRIBUTION:")
        print("-" * 70)
        match_types = {}
        for c in candidates:
            mt = c["current_match"]
            match_types[mt] = match_types.get(mt, 0) + 1
        for mt, count in sorted(match_types.items()):
            print(f"  {mt:<15} {count:>5} terms")
        print()

        # Potential savings estimate
        broad_phrase = [c for c in candidates if c["current_match"] in ["BROAD", "PHRASE"]]
        if broad_phrase:
            current_spend = sum(c["cost"] for c in broad_phrase)
            # Estimate 15-25% CPC reduction with exact match
            potential_savings = current_spend * 0.20
            print("ESTIMATED SAVINGS:")
            print("-" * 70)
            print(f"  Current spend on Broad/Phrase candidates: ${current_spend:,.2f}")
            print(f"  Est. savings with Exact Match (20% CPC reduction): ${potential_savings:,.2f}")
            print()

    print("RECOMMENDATIONS:")
    print("-" * 70)
    print("1. Add top candidates as Exact Match keywords in new ad groups")
    print("2. Prioritize technical terms (model numbers) for exact match")
    print("3. Add Exact Match negatives to existing Broad/Phrase ad groups")
    print("4. Monitor Impression Share improvement after migration")
    print()

    print("=" * 70)
    print("AUDIT COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
