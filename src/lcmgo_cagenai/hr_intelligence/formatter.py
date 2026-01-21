"""
Response formatter for HR Intelligence analysis.

Provides utilities to format HRAnalysisReport into various output formats
including human-readable text and structured API responses.
"""

from typing import Any

from .schema import HRAnalysisReport, RankedCandidate


def format_text_report(report: HRAnalysisReport) -> str:
    """
    Format HRAnalysisReport as human-readable text.

    Produces a formatted Greek or English text report suitable for
    display in chat interfaces or logging.

    Args:
        report: HRAnalysisReport to format

    Returns:
        Formatted text string
    """
    is_greek = report.analysis_language == "el"

    lines = []

    # Header
    if is_greek:
        lines.append("=" * 60)
        lines.append("ΑΝΑΛΥΣΗ HR INTELLIGENCE")
        lines.append("=" * 60)
    else:
        lines.append("=" * 60)
        lines.append("HR INTELLIGENCE ANALYSIS")
        lines.append("=" * 60)

    lines.append("")

    # Section 1: Request Analysis
    ra = report.request_analysis
    if is_greek:
        lines.append("## 1. ΑΝΑΛΥΣΗ ΑΙΤΗΜΑΤΟΣ")
        lines.append(f"Σύνοψη: {ra.summary}")
        if ra.mandatory_criteria:
            lines.append(f"Υποχρεωτικά: {', '.join(ra.mandatory_criteria)}")
        if ra.preferred_criteria:
            lines.append(f"Επιθυμητά: {', '.join(ra.preferred_criteria)}")
        if ra.inferred_criteria:
            lines.append(f"Υπονοούμενα: {', '.join(ra.inferred_criteria)}")
    else:
        lines.append("## 1. REQUEST ANALYSIS")
        lines.append(f"Summary: {ra.summary}")
        if ra.mandatory_criteria:
            lines.append(f"Mandatory: {', '.join(ra.mandatory_criteria)}")
        if ra.preferred_criteria:
            lines.append(f"Preferred: {', '.join(ra.preferred_criteria)}")
        if ra.inferred_criteria:
            lines.append(f"Inferred: {', '.join(ra.inferred_criteria)}")

    lines.append("")

    # Section 2: Query Outcome
    qo = report.query_outcome
    if is_greek:
        lines.append("## 2. ΑΠΟΤΕΛΕΣΜΑΤΑ ΑΝΑΖΗΤΗΣΗΣ")
        lines.append(f"Άμεσα αποτελέσματα: {qo.direct_matches}")
        lines.append(f"Συνολικά αποτελέσματα: {qo.total_matches}")
        if qo.relaxation_applied:
            lines.append("Χαλάρωση κριτηρίων: Ναι")
        if qo.zero_results_reason:
            lines.append(f"Αιτία 0 αποτελεσμάτων: {qo.zero_results_reason}")
    else:
        lines.append("## 2. QUERY OUTCOME")
        lines.append(f"Direct matches: {qo.direct_matches}")
        lines.append(f"Total matches: {qo.total_matches}")
        if qo.relaxation_applied:
            lines.append("Relaxation applied: Yes")
        if qo.zero_results_reason:
            lines.append(f"Zero results reason: {qo.zero_results_reason}")

    lines.append("")

    # Section 3: Criteria Expansion (if applicable)
    ce = report.criteria_expansion
    if ce and ce.relaxations:
        if is_greek:
            lines.append("## 3. ΧΑΛΑΡΩΣΗ ΚΡΙΤΗΡΙΩΝ")
            for r in ce.relaxations:
                lines.append(f"  • {r.original} → {r.relaxed_to}")
                lines.append(f"    Λόγος: {r.reasoning}")
            if ce.business_rationale:
                lines.append(f"Επιχειρηματική λογική: {ce.business_rationale}")
        else:
            lines.append("## 3. CRITERIA RELAXATION")
            for r in ce.relaxations:
                lines.append(f"  • {r.original} → {r.relaxed_to}")
                lines.append(f"    Reason: {r.reasoning}")
            if ce.business_rationale:
                lines.append(f"Business rationale: {ce.business_rationale}")

        lines.append("")

    # Section 4: Ranked Candidates
    if is_greek:
        lines.append("## 4. ΚΑΤΑΤΑΞΗ ΥΠΟΨΗΦΙΩΝ")
    else:
        lines.append("## 4. RANKED CANDIDATES")

    lines.append("")

    for rc in report.ranked_candidates:
        lines.extend(_format_candidate(rc, is_greek))
        lines.append("")

    # Section 5: HR Recommendation
    hr = report.hr_recommendation
    if is_greek:
        lines.append("## 5. ΣΥΣΤΑΣΗ HR")
        if hr.top_candidates:
            lines.append(f"Κορυφαίοι υποψήφιοι: {', '.join(hr.top_candidates)}")
        lines.append(f"Σύνοψη: {hr.recommendation_summary}")
        if hr.interview_priorities:
            lines.append("Προτεραιότητες συνέντευξης:")
            for p in hr.interview_priorities:
                lines.append(f"  • {p}")
        if hr.hiring_suggestions:
            lines.append("Προτάσεις πρόσληψης:")
            for s in hr.hiring_suggestions:
                lines.append(f"  • {s}")
        if hr.alternative_search:
            lines.append(f"Εναλλακτική αναζήτηση: {hr.alternative_search}")
    else:
        lines.append("## 5. HR RECOMMENDATION")
        if hr.top_candidates:
            lines.append(f"Top candidates: {', '.join(hr.top_candidates)}")
        lines.append(f"Summary: {hr.recommendation_summary}")
        if hr.interview_priorities:
            lines.append("Interview priorities:")
            for p in hr.interview_priorities:
                lines.append(f"  • {p}")
        if hr.hiring_suggestions:
            lines.append("Hiring suggestions:")
            for s in hr.hiring_suggestions:
                lines.append(f"  • {s}")
        if hr.alternative_search:
            lines.append(f"Alternative search: {hr.alternative_search}")

    lines.append("")

    # Footer
    if is_greek:
        lines.append("-" * 60)
        lines.append(f"Ανάλυση: {report.latency_ms}ms | Μοντέλο: {report.llm_model}")
    else:
        lines.append("-" * 60)
        lines.append(f"Analysis: {report.latency_ms}ms | Model: {report.llm_model}")

    return "\n".join(lines)


def _format_candidate(rc: RankedCandidate, is_greek: bool) -> list[str]:
    """Format a single ranked candidate."""
    lines = []

    # Header with rank and name
    suitability_emoji = _get_suitability_emoji(rc.overall_suitability)

    if is_greek:
        lines.append(f"### {rc.rank}. {rc.candidate_name}")
        lines.append(f"Καταλληλότητα: {rc.overall_suitability} {suitability_emoji} ({rc.match_percentage:.0f}%)")
    else:
        lines.append(f"### {rc.rank}. {rc.candidate_name}")
        lines.append(f"Suitability: {rc.overall_suitability} {suitability_emoji} ({rc.match_percentage:.0f}%)")

    # Strengths
    if rc.strengths:
        if is_greek:
            lines.append("Πλεονεκτήματα:")
        else:
            lines.append("Strengths:")
        for s in rc.strengths:
            conf_icon = "✓" if s.confidence == "Confirmed" else "~" if s.confidence == "Likely" else "?"
            lines.append(f"  {conf_icon} {s.criterion}: {s.candidate_value}")

    # Gaps
    if rc.gaps:
        if is_greek:
            lines.append("Κενά:")
        else:
            lines.append("Gaps:")
        for g in rc.gaps:
            sev_icon = "!" if g.severity == "Major" else "•" if g.severity == "Moderate" else "·"
            lines.append(f"  {sev_icon} {g.criterion}: {g.gap_description}")
            if g.mitigation:
                lines.append(f"    → {g.mitigation}")

    # Risks
    if rc.risks:
        if is_greek:
            lines.append("Κίνδυνοι:")
        else:
            lines.append("Risks:")
        for r in rc.risks:
            lines.append(f"  ⚠ {r}")

    # Interview focus
    if rc.interview_focus:
        if is_greek:
            lines.append("Εστίαση συνέντευξης:")
        else:
            lines.append("Interview focus:")
        for f in rc.interview_focus:
            lines.append(f"  → {f}")

    return lines


def _get_suitability_emoji(suitability: str) -> str:
    """Get emoji for suitability level."""
    mapping = {
        "High": "⭐⭐⭐",
        "Medium-High": "⭐⭐½",
        "Medium": "⭐⭐",
        "Medium-Low": "⭐½",
        "Low": "⭐",
    }
    return mapping.get(suitability, "")


def format_api_response(
    report: HRAnalysisReport,
    include_text_summary: bool = False,
) -> dict[str, Any]:
    """
    Format HRAnalysisReport for API response.

    Args:
        report: HRAnalysisReport to format
        include_text_summary: If True, include formatted text summary

    Returns:
        Dictionary ready for JSON serialization
    """
    result = report.to_dict()

    # Add recommendation field to each ranked candidate for frontend tab categorization
    # TOP 5 candidates by rank → "interview" (recommended for interview)
    # Remaining candidates → "consider" (worth considering)
    ranked_candidates = result.get("ranked_candidates", [])
    for i, rc in enumerate(ranked_candidates):
        rank = rc.get("rank", i + 1)
        suitability = rc.get("overall_suitability", "").lower()
        match_pct = rc.get("match_percentage", 0)

        # Top 5 candidates always go to "interview" tab
        # OR any candidate with High suitability / >=70% match
        if rank <= 5 or suitability in ("high", "υψηλή") or match_pct >= 70:
            rc["recommendation"] = "interview"
        else:
            rc["recommendation"] = "consider"

    if include_text_summary:
        result["text_summary"] = format_text_report(report)

    return result


def format_compact_summary(report: HRAnalysisReport) -> str:
    """
    Format a compact one-line summary of the analysis.

    Useful for logging or quick display.

    Args:
        report: HRAnalysisReport to summarize

    Returns:
        Compact summary string
    """
    is_greek = report.analysis_language == "el"
    num_candidates = len(report.ranked_candidates)

    if num_candidates == 0:
        if is_greek:
            return "Δεν βρέθηκαν υποψήφιοι"
        return "No candidates found"

    top_names = [rc.candidate_name for rc in report.ranked_candidates[:3]]
    top_str = ", ".join(top_names)

    if is_greek:
        return f"Βρέθηκαν {num_candidates} υποψήφιοι. Κορυφαίοι: {top_str}"
    return f"Found {num_candidates} candidates. Top: {top_str}"
