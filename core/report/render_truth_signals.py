#!/usr/bin/env python3
"""
Phase B3.2: Render Google Recommendations Truth Signals to Markdown

READ-ONLY rendering function for report generation.
"""


def render_truth_signals_section(truth_signals: dict) -> str:
    """
    Render truth signals to markdown for report template.

    Args:
        truth_signals: Truth signals dict from extract_truth_signals()

    Returns:
        Markdown string for TRUTH_SIGNALS_SECTION placeholder
    """
    lines = []

    metadata = truth_signals.get("metadata", {})
    truth_sweep_available = metadata.get("truth_sweep_available", False)

    lines.append("**What This Section Shows:**  ")
    lines.append("Cross-checks between Google's own recommendations and current account state to identify optimization opportunities that Google flags but we haven't implemented.")
    lines.append("")

    if not truth_sweep_available:
        lines.append("**Status:** No truth sweep data available. Run `bin/truth_sweep` to collect Google's recommendations.")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"**Truth Sweep Data:** {metadata.get('truth_sweep_path', 'N/A')}")
    lines.append("")

    # RSA Asset Coverage
    rsa_signals = truth_signals.get("rsa_asset_coverage", [])
    if rsa_signals:
        lines.append("### RSA Asset Coverage Gaps")
        lines.append("")
        lines.append("| Ad Group | Headlines | Descriptions | Severity | Google Suggestions |")
        lines.append("|----------|-----------|--------------|----------|-------------------|")
        for signal in rsa_signals[:10]:  # Limit to 10 for report
            evidence = signal.get("evidence", {})
            current_h = evidence.get("current_headlines", 0)
            current_d = evidence.get("current_descriptions", 0)
            threshold_h = evidence.get("threshold_headlines", 8)
            threshold_d = evidence.get("threshold_descriptions", 3)
            severity = signal.get("severity", "UNKNOWN")

            google_suggestions = signal.get("google_suggestions", {})
            suggested_h = google_suggestions.get("suggested_headlines", [])
            suggested_d = google_suggestions.get("suggested_descriptions", [])

            suggestions_text = "None"
            if suggested_h or suggested_d:
                suggestions_text = f"{len(suggested_h)} headlines, {len(suggested_d)} descriptions"

            lines.append(f"| {signal.get('ad_name', 'N/A')} | {current_h}/{threshold_h} | {current_d}/{threshold_d} | {severity} | {suggestions_text} |")

        lines.append("")
        lines.append(f"**Total RSAs Below Threshold:** {len(rsa_signals)}")
        lines.append("")

        # Show example suggestions
        for signal in rsa_signals[:2]:
            google_suggestions = signal.get("google_suggestions", {})
            if google_suggestions:
                lines.append(f"**Example Suggestions for {signal.get('ad_name', 'N/A')}:**")
                lines.append("")
                suggested_h = google_suggestions.get("suggested_headlines", [])
                if suggested_h:
                    lines.append(f"- Headlines: {', '.join(f'`{h}`' for h in suggested_h[:3])}")
                suggested_d = google_suggestions.get("suggested_descriptions", [])
                if suggested_d:
                    lines.append(f"- Descriptions: {', '.join(f'`{d}`' for d in suggested_d[:2])}")
                lines.append("")
    else:
        lines.append("### RSA Asset Coverage")
        lines.append("")
        lines.append("✓ All RSAs meet or exceed thresholds (8 headlines, 3 descriptions)")
        lines.append("")

    # Keyword Recommendations
    keyword_signals = truth_signals.get("keyword_recommendations", [])
    if keyword_signals:
        lines.append("### Google Keyword Recommendations")
        lines.append("")

        # Group by type
        not_present = [s for s in keyword_signals if s["type"] == "GOOGLE_RECOMMENDS_KEYWORD_NOT_PRESENT"]
        blocked = [s for s in keyword_signals if s["type"] == "GOOGLE_RECOMMENDS_KEYWORD_BUT_NEGATIVE_BLOCKS"]

        if blocked:
            lines.append("#### ⚠ Keywords Blocked by Negatives")
            lines.append("")
            lines.append("| Keyword | Match Type | Estimated Weekly Searches |")
            lines.append("|---------|------------|---------------------------|")
            for signal in blocked[:10]:
                evidence = signal.get("evidence", {})
                keyword = evidence.get("recommended_keyword", "N/A")
                match_type = evidence.get("match_type", "UNKNOWN")
                weekly_searches = evidence.get("estimated_weekly_searches", "N/A")
                lines.append(f"| {keyword} | {match_type} | {weekly_searches} |")
            lines.append("")

        if not_present:
            lines.append("#### Keywords Not Present")
            lines.append("")
            lines.append("| Keyword | Match Type | Estimated Weekly Searches | Sample Search Terms |")
            lines.append("|---------|------------|---------------------------|--------------------|")
            for signal in not_present[:15]:
                evidence = signal.get("evidence", {})
                keyword = evidence.get("recommended_keyword", "N/A")
                match_type = evidence.get("match_type", "UNKNOWN")
                weekly_searches = evidence.get("estimated_weekly_searches", "N/A")
                search_terms = evidence.get("search_terms", [])
                sample_terms = ", ".join(st.get("text", "") for st in search_terms[:2])
                lines.append(f"| {keyword} | {match_type} | {weekly_searches} | {sample_terms} |")
            lines.append("")

        lines.append(f"**Total Keyword Recommendations:** {len(keyword_signals)} ({len(blocked)} blocked, {len(not_present)} missing)")
        lines.append("")
    else:
        lines.append("### Google Keyword Recommendations")
        lines.append("")
        lines.append("✓ No new keyword recommendations from Google")
        lines.append("")

    # Budget Recommendations
    budget_signals = truth_signals.get("budget_recommendations", [])
    if budget_signals:
        lines.append("### Google Budget Recommendations")
        lines.append("")
        lines.append("| Campaign | Current Daily | Recommended Daily | Increase | Status |")
        lines.append("|----------|---------------|-------------------|----------|--------|")
        for signal in budget_signals:
            evidence = signal.get("evidence", {})
            campaign_name = evidence.get("campaign_name", "Unknown")
            current = evidence.get("current_budget_daily", 0)
            recommended = evidence.get("recommended_budget_daily", 0)
            increase = evidence.get("budget_increase_daily", 0)
            status = evidence.get("campaign_status", "UNKNOWN")

            lines.append(f"| {campaign_name} | ${current:.2f} | ${recommended:.2f} | +${increase:.2f} | {status} |")
        lines.append("")
        lines.append(f"**Total Budget Increase Recommended:** ${sum(s.get('evidence', {}).get('budget_increase_daily', 0) for s in budget_signals):.2f}/day")
        lines.append("")
    else:
        lines.append("### Google Budget Recommendations")
        lines.append("")
        lines.append("✓ No budget increase recommendations from Google")
        lines.append("")

    # Merchant Clarifiers
    merchant_clarifiers = truth_signals.get("merchant_clarifiers", [])
    if merchant_clarifiers:
        lines.append("### Merchant Center Clarifier")
        lines.append("")
        for clarifier in merchant_clarifiers:
            lines.append(f"**{clarifier.get('message', 'N/A')}**")
            lines.append("")
            for detail in clarifier.get("details", []):
                lines.append(f"- {detail}")
            lines.append("")

            evidence = clarifier.get("evidence", {})
            if evidence:
                lines.append(f"- Products Checked: {evidence.get('total_products_checked', 0)}")
                lines.append(f"- Disapproved: {evidence.get('disapproved_count', 0)}")
                lines.append(f"- Approval Rate: {evidence.get('approval_rate', 'N/A')}")
                lines.append("")

                top_reasons = evidence.get("top_disapproval_reasons", [])
                if top_reasons:
                    lines.append("**Top Disapproval Reasons:**")
                    lines.append("")
                    for reason_obj in top_reasons:
                        reason = reason_obj.get("reason", "N/A")
                        count = reason_obj.get("count", 0)
                        lines.append(f"- {reason}: {count}")
                    lines.append("")

    return "\n".join(lines)
