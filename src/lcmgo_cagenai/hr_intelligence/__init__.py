"""
HR Intelligence Module - Unified candidate analysis and ranking.

This module provides intelligent HR analysis that transforms raw query results
into actionable insights with structured analysis, comparison, ranking, and
recommendations.

See docs/HR-INTELLIGENCE-UNIFIED.md for full specification.

Usage:
    from lcmgo_cagenai.hr_intelligence import HRIntelligenceAnalyzer, HRAnalysisInput

    analyzer = HRIntelligenceAnalyzer(llm_provider)
    report = await analyzer.analyze(HRAnalysisInput(
        original_query="Λογιστές με SAP",
        requirements=job_requirements,
        candidates=candidate_list,
        ...
    ))
"""

from .analyzer import HRIntelligenceAnalyzer, analyze_candidates_sync
from .formatter import format_api_response, format_compact_summary, format_text_report
from .schema import (
    AssessmentScore,
    CandidateEvidence,
    CandidateGap,
    CandidateProfile,
    CriteriaExpansion,
    CriteriaRelaxation,
    HRAnalysisInput,
    HRAnalysisReport,
    HRRecommendation,
    JobRequirements,
    LanguageRequirement,
    QueryOutcome,
    RankedCandidate,
    RequestAnalysis,
)

__all__ = [
    # Main class
    "HRIntelligenceAnalyzer",
    "analyze_candidates_sync",
    # Input types
    "HRAnalysisInput",
    "JobRequirements",
    "LanguageRequirement",
    "CandidateProfile",
    # Output types
    "HRAnalysisReport",
    "RequestAnalysis",
    "QueryOutcome",
    "CriteriaExpansion",
    "CriteriaRelaxation",
    "RankedCandidate",
    "CandidateEvidence",
    "CandidateGap",
    "AssessmentScore",
    "HRRecommendation",
    # Formatters
    "format_text_report",
    "format_api_response",
    "format_compact_summary",
]
