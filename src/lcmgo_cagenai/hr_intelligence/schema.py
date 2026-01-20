"""
Data structures for HR Intelligence analysis.

These dataclasses define the input and output formats for HR analysis,
matching the specification in docs/HR-INTELLIGENCE-UNIFIED.md.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


# =============================================================================
# INPUT STRUCTURES
# =============================================================================


@dataclass
class LanguageRequirement:
    """Single language requirement."""

    language_code: str  # "en", "el", "de"
    language_name: str  # "English", "Greek", "German"
    min_level: str | None = None  # "A1" to "C2" or None
    is_required: bool = True  # True = must have, False = nice to have


@dataclass
class JobRequirements:
    """
    Unified requirements format for HR Intelligence.

    Used by both Query Translator and Job Posting Parser output.
    """

    # Source information
    source_type: Literal["query", "job_posting"]
    source_text: str  # Original input
    detected_language: str  # "el" or "en"

    # Role requirements
    roles: list[str] = field(default_factory=list)  # ["accountant", "financial_analyst"]
    role_priority: str = "must"  # "must" | "should" | "nice"

    # Experience requirements
    min_experience_years: float | None = None  # 3.0
    max_experience_years: float | None = None  # None = no upper limit
    experience_priority: str = "should"

    # Technical requirements
    software: list[str] = field(default_factory=list)  # ["SAP", "Excel"]
    software_priority: str = "should"
    certifications: list[str] = field(default_factory=list)  # ["CPA", "ACCA"]
    certifications_priority: str = "nice"
    skills: list[str] = field(default_factory=list)  # ["financial_reporting", "budgeting"]
    skills_priority: str = "should"

    # Language requirements
    languages: list[LanguageRequirement] = field(default_factory=list)

    # Location requirements
    locations: list[str] = field(default_factory=list)  # ["Athens", "Thessaloniki"]
    remote_acceptable: bool = True

    # Education requirements
    education_level: str | None = None  # "bachelor", "master", etc.
    education_fields: list[str] = field(default_factory=list)  # ["accounting", "finance"]

    # Computed weights for scoring
    weights: dict[str, float] = field(default_factory=lambda: {
        "role": 0.25,
        "experience": 0.30,
        "software": 0.20,
        "skills": 0.10,
        "language": 0.10,
        "certification": 0.05,
    })

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "source_type": self.source_type,
            "source_text": self.source_text,
            "detected_language": self.detected_language,
            "roles": self.roles,
            "role_priority": self.role_priority,
            "min_experience_years": self.min_experience_years,
            "max_experience_years": self.max_experience_years,
            "experience_priority": self.experience_priority,
            "software": self.software,
            "software_priority": self.software_priority,
            "certifications": self.certifications,
            "certifications_priority": self.certifications_priority,
            "skills": self.skills,
            "skills_priority": self.skills_priority,
            "languages": [
                {
                    "language_code": lang.language_code,
                    "language_name": lang.language_name,
                    "min_level": lang.min_level,
                    "is_required": lang.is_required,
                }
                for lang in self.languages
            ],
            "locations": self.locations,
            "remote_acceptable": self.remote_acceptable,
            "education_level": self.education_level,
            "education_fields": self.education_fields,
            "weights": self.weights,
        }


@dataclass
class CandidateProfile:
    """
    Full candidate profile for HR analysis.

    Contains all relevant data from PostgreSQL needed for evaluation.
    """

    candidate_id: str
    first_name: str
    last_name: str
    email: str | None = None

    # Experience
    total_experience_years: float | None = None
    experience_entries: list[dict[str, Any]] = field(default_factory=list)
    # Each entry: {role, company, start_date, end_date, duration_months, description}

    # Skills and qualifications
    roles: list[str] = field(default_factory=list)  # Role categories
    software: list[str] = field(default_factory=list)  # Software names
    skills: list[str] = field(default_factory=list)  # Hard skills
    soft_skills: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)

    # Languages
    languages: list[dict[str, str]] = field(default_factory=list)
    # Each: {code, name, level}

    # Education
    education: list[dict[str, Any]] = field(default_factory=list)
    # Each: {level, field, institution, graduation_year}

    # Location
    city: str | None = None
    region: str | None = None

    # Raw CV data for reference
    raw_cv_json: dict[str, Any] | None = None

    @property
    def full_name(self) -> str:
        """Get full name."""
        return f"{self.first_name} {self.last_name}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "candidate_id": self.candidate_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "email": self.email,
            "total_experience_years": self.total_experience_years,
            "experience_entries": self.experience_entries,
            "roles": self.roles,
            "software": self.software,
            "skills": self.skills,
            "soft_skills": self.soft_skills,
            "certifications": self.certifications,
            "languages": self.languages,
            "education": self.education,
            "city": self.city,
            "region": self.region,
        }


@dataclass
class HRAnalysisInput:
    """Input for HR Intelligence Analyzer."""

    original_query: str  # User's natural language query
    requirements: JobRequirements  # Extracted requirements
    candidates: list[CandidateProfile]  # Full candidate profiles
    relaxations_applied: list[str] = field(default_factory=list)  # List of relaxed criteria
    direct_result_count: int = 0  # Results before relaxation
    total_result_count: int = 0  # Results after relaxation


# =============================================================================
# OUTPUT STRUCTURES
# =============================================================================


@dataclass
class RequestAnalysis:
    """Section 1: Understanding the request."""

    summary: str  # Brief description
    mandatory_criteria: list[str] = field(default_factory=list)  # Must-have
    preferred_criteria: list[str] = field(default_factory=list)  # Nice-to-have
    inferred_criteria: list[str] = field(default_factory=list)  # Implied but not stated

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "mandatory_criteria": self.mandatory_criteria,
            "preferred_criteria": self.preferred_criteria,
            "inferred_criteria": self.inferred_criteria,
        }


@dataclass
class QueryOutcome:
    """Section 2: What the query found."""

    direct_matches: int  # Exact criteria matches
    total_matches: int  # After relaxation
    relaxation_applied: bool = False
    zero_results_reason: str | None = None  # Why 0 direct (if applicable)

    def to_dict(self) -> dict[str, Any]:
        return {
            "direct_matches": self.direct_matches,
            "total_matches": self.total_matches,
            "relaxation_applied": self.relaxation_applied,
            "zero_results_reason": self.zero_results_reason,
        }


@dataclass
class CriteriaRelaxation:
    """Single criterion relaxation."""

    original: str  # "SAP ERP, 5+ years"
    relaxed_to: str  # "Any ERP, 3+ years"
    reasoning: str  # "SAP skills transfer to other ERPs"

    def to_dict(self) -> dict[str, Any]:
        return {
            "original": self.original,
            "relaxed_to": self.relaxed_to,
            "reasoning": self.reasoning,
        }


@dataclass
class CriteriaExpansion:
    """Section 3: How criteria were relaxed."""

    relaxations: list[CriteriaRelaxation] = field(default_factory=list)
    business_rationale: str = ""  # Why these relaxations make sense

    def to_dict(self) -> dict[str, Any]:
        return {
            "relaxations": [r.to_dict() for r in self.relaxations],
            "business_rationale": self.business_rationale,
        }


@dataclass
class CandidateEvidence:
    """Evidence of qualification."""

    criterion: str  # "SAP experience"
    candidate_value: str  # "SAP FI/CO, 4 years"
    source: str  # "CV page 1, Experience section"
    confidence: str = "Confirmed"  # "Confirmed" | "Likely" | "Uncertain"

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion": self.criterion,
            "candidate_value": self.candidate_value,
            "source": self.source,
            "confidence": self.confidence,
        }


@dataclass
class CandidateGap:
    """Missing qualification."""

    criterion: str  # "5+ years experience"
    gap_description: str  # "Has 3 years (2 below requirement)"
    severity: str = "Moderate"  # "Minor" | "Moderate" | "Major"
    mitigation: str | None = None  # "Strong SAP skills may compensate"

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion": self.criterion,
            "gap_description": self.gap_description,
            "severity": self.severity,
            "mitigation": self.mitigation,
        }


@dataclass
class AssessmentScore:
    """Evaluation score with evidence."""

    score: str  # "High" | "Medium" | "Low"
    evidence: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "evidence": self.evidence,
            "notes": self.notes,
        }


@dataclass
class RankedCandidate:
    """Section 4: Individual candidate analysis."""

    rank: int  # 1, 2, 3...
    candidate_id: str
    candidate_name: str

    # Match assessment
    overall_suitability: str  # "High" | "Medium-High" | "Medium" | "Medium-Low" | "Low"
    match_percentage: float = 0.0  # 0-100

    # What they have
    strengths: list[CandidateEvidence] = field(default_factory=list)

    # What's missing
    gaps: list[CandidateGap] = field(default_factory=list)

    # Concerns
    risks: list[str] = field(default_factory=list)

    # Detailed assessments
    role_match: AssessmentScore | None = None
    experience_match: AssessmentScore | None = None
    skills_match: AssessmentScore | None = None
    language_match: AssessmentScore | None = None

    # HR notes
    interview_focus: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "candidate_id": self.candidate_id,
            "candidate_name": self.candidate_name,
            "overall_suitability": self.overall_suitability,
            "match_percentage": self.match_percentage,
            "strengths": [s.to_dict() for s in self.strengths],
            "gaps": [g.to_dict() for g in self.gaps],
            "risks": self.risks,
            "role_match": self.role_match.to_dict() if self.role_match else None,
            "experience_match": self.experience_match.to_dict() if self.experience_match else None,
            "skills_match": self.skills_match.to_dict() if self.skills_match else None,
            "language_match": self.language_match.to_dict() if self.language_match else None,
            "interview_focus": self.interview_focus,
        }


@dataclass
class HRRecommendation:
    """Section 5: Final recommendations."""

    top_candidates: list[str] = field(default_factory=list)  # Names in order
    recommendation_summary: str = ""  # 2-3 sentence summary
    interview_priorities: list[str] = field(default_factory=list)  # What to validate
    hiring_suggestions: list[str] = field(default_factory=list)  # Additional advice
    alternative_search: str | None = None  # If results poor, suggest different search

    def to_dict(self) -> dict[str, Any]:
        return {
            "top_candidates": self.top_candidates,
            "recommendation_summary": self.recommendation_summary,
            "interview_priorities": self.interview_priorities,
            "hiring_suggestions": self.hiring_suggestions,
            "alternative_search": self.alternative_search,
        }


@dataclass
class HRAnalysisReport:
    """Complete HR analysis output."""

    # Section 1: Request Analysis
    request_analysis: RequestAnalysis

    # Section 2: Query Outcome
    query_outcome: QueryOutcome

    # Section 3: Criteria Expansion (if relaxation applied)
    criteria_expansion: CriteriaExpansion | None = None

    # Section 4: Ranked Candidates
    ranked_candidates: list[RankedCandidate] = field(default_factory=list)

    # Section 5: HR Recommendation
    hr_recommendation: HRRecommendation = field(default_factory=HRRecommendation)

    # Metadata
    analysis_language: str = "el"  # "el" or "en"
    analysis_timestamp: datetime = field(default_factory=_utc_now)
    llm_model: str = "claude-sonnet-4-5"
    latency_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "request_analysis": self.request_analysis.to_dict(),
            "query_outcome": self.query_outcome.to_dict(),
            "criteria_expansion": self.criteria_expansion.to_dict() if self.criteria_expansion else None,
            "ranked_candidates": [c.to_dict() for c in self.ranked_candidates],
            "hr_recommendation": self.hr_recommendation.to_dict(),
            "analysis_language": self.analysis_language,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "llm_model": self.llm_model,
            "latency_ms": self.latency_ms,
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def parse_hr_analysis_from_json(data: dict[str, Any]) -> HRAnalysisReport:
    """
    Parse LLM JSON response into HRAnalysisReport.

    Args:
        data: Dictionary from LLM JSON response

    Returns:
        HRAnalysisReport with all sections populated
    """
    # Parse request_analysis
    ra_data = data.get("request_analysis", {})
    request_analysis = RequestAnalysis(
        summary=ra_data.get("summary", ""),
        mandatory_criteria=ra_data.get("mandatory_criteria", []),
        preferred_criteria=ra_data.get("preferred_criteria", []),
        inferred_criteria=ra_data.get("inferred_criteria", []),
    )

    # Parse query_outcome
    qo_data = data.get("query_outcome", {})
    query_outcome = QueryOutcome(
        direct_matches=qo_data.get("direct_matches", 0),
        total_matches=qo_data.get("total_matches", 0),
        relaxation_applied=qo_data.get("relaxation_applied", False),
        zero_results_reason=qo_data.get("zero_results_reason"),
    )

    # Parse criteria_expansion (optional)
    criteria_expansion = None
    ce_data = data.get("criteria_expansion")
    if ce_data:
        relaxations = [
            CriteriaRelaxation(
                original=r.get("original", ""),
                relaxed_to=r.get("relaxed_to", ""),
                reasoning=r.get("reasoning", ""),
            )
            for r in ce_data.get("relaxations", [])
        ]
        criteria_expansion = CriteriaExpansion(
            relaxations=relaxations,
            business_rationale=ce_data.get("business_rationale", ""),
        )

    # Parse ranked_candidates
    ranked_candidates = []
    for rc_data in data.get("ranked_candidates", []):
        # Parse strengths
        strengths = [
            CandidateEvidence(
                criterion=s.get("criterion", ""),
                candidate_value=s.get("candidate_value", ""),
                source=s.get("source", ""),
                confidence=s.get("confidence", "Confirmed"),
            )
            for s in rc_data.get("strengths", [])
        ]

        # Parse gaps
        gaps = [
            CandidateGap(
                criterion=g.get("criterion", ""),
                gap_description=g.get("gap_description", ""),
                severity=g.get("severity", "Moderate"),
                mitigation=g.get("mitigation"),
            )
            for g in rc_data.get("gaps", [])
        ]

        # Parse assessment scores
        def parse_score(score_data: dict | None) -> AssessmentScore | None:
            if not score_data:
                return None
            return AssessmentScore(
                score=score_data.get("score", "Medium"),
                evidence=score_data.get("evidence", []),
                notes=score_data.get("notes", ""),
            )

        ranked_candidates.append(
            RankedCandidate(
                rank=rc_data.get("rank", 0),
                candidate_id=rc_data.get("candidate_id", ""),
                candidate_name=rc_data.get("candidate_name", ""),
                overall_suitability=rc_data.get("overall_suitability", "Medium"),
                match_percentage=rc_data.get("match_percentage", 0.0),
                strengths=strengths,
                gaps=gaps,
                risks=rc_data.get("risks", []),
                role_match=parse_score(rc_data.get("role_match")),
                experience_match=parse_score(rc_data.get("experience_match")),
                skills_match=parse_score(rc_data.get("skills_match")),
                language_match=parse_score(rc_data.get("language_match")),
                interview_focus=rc_data.get("interview_focus", []),
            )
        )

    # Parse hr_recommendation
    hr_data = data.get("hr_recommendation", {})
    hr_recommendation = HRRecommendation(
        top_candidates=hr_data.get("top_candidates", []),
        recommendation_summary=hr_data.get("recommendation_summary", ""),
        interview_priorities=hr_data.get("interview_priorities", []),
        hiring_suggestions=hr_data.get("hiring_suggestions", []),
        alternative_search=hr_data.get("alternative_search"),
    )

    return HRAnalysisReport(
        request_analysis=request_analysis,
        query_outcome=query_outcome,
        criteria_expansion=criteria_expansion,
        ranked_candidates=ranked_candidates,
        hr_recommendation=hr_recommendation,
        analysis_language=data.get("analysis_language", "el"),
    )
