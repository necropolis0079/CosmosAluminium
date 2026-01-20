"""
Unit tests for HR Intelligence module.

Tests cover:
- Schema dataclasses
- Prompt generation
- Language detection
- Response parsing
- Text formatting
"""

import json
import pytest
from datetime import datetime

from lcmgo_cagenai.hr_intelligence import (
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
    format_compact_summary,
    format_text_report,
)
from lcmgo_cagenai.hr_intelligence.prompts import (
    build_analysis_prompt,
    get_system_prompt,
    get_user_message,
)
from lcmgo_cagenai.hr_intelligence.schema import parse_hr_analysis_from_json
from lcmgo_cagenai.hr_intelligence.analyzer import HRIntelligenceAnalyzer


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_language_requirement():
    """Sample language requirement."""
    return LanguageRequirement(
        language_code="en",
        language_name="English",
        min_level="B2",
        is_required=True,
    )


@pytest.fixture
def sample_job_requirements(sample_language_requirement):
    """Sample job requirements."""
    return JobRequirements(
        source_type="query",
        source_text="Λογιστές με SAP, 3+ χρόνια, Αγγλικά",
        detected_language="el",
        roles=["accountant"],
        role_priority="must",
        min_experience_years=3.0,
        experience_priority="should",
        software=["SAP"],
        software_priority="must",
        languages=[sample_language_requirement],
    )


@pytest.fixture
def sample_candidate():
    """Sample candidate profile."""
    return CandidateProfile(
        candidate_id="test-uuid-123",
        first_name="Βάγια",
        last_name="Βαΐτση",
        email="vaitsi@example.com",
        total_experience_years=8.0,
        experience_entries=[
            {
                "role": "Accountant",
                "company": "ABC Corp",
                "start_date": "2016-01-01",
                "end_date": "2024-01-01",
                "duration_months": 96,
                "description": "Financial reporting and SAP",
            }
        ],
        roles=["accountant", "financial_analyst"],
        software=["SAP FI/CO", "Microsoft Excel"],
        skills=["financial_reporting", "budgeting"],
        certifications=["CPA"],
        languages=[{"code": "en", "name": "English", "level": "B2"}],
    )


@pytest.fixture
def sample_hr_report():
    """Sample HR analysis report."""
    return HRAnalysisReport(
        request_analysis=RequestAnalysis(
            summary="Αναζήτηση λογιστών με SAP εμπειρία",
            mandatory_criteria=["Λογιστικό background", "SAP εμπειρία"],
            preferred_criteria=["3+ χρόνια εμπειρίας"],
            inferred_criteria=["Excel γνώση"],
        ),
        query_outcome=QueryOutcome(
            direct_matches=0,
            total_matches=3,
            relaxation_applied=True,
            zero_results_reason="Δεν βρέθηκαν ακριβή αποτελέσματα",
        ),
        criteria_expansion=CriteriaExpansion(
            relaxations=[
                CriteriaRelaxation(
                    original="SAP ERP, 3+ χρόνια",
                    relaxed_to="Οποιοδήποτε ERP, 2+ χρόνια",
                    reasoning="Η ERP εμπειρία είναι μεταφερόμενη",
                )
            ],
            business_rationale="Λογιστική γνώση σημαντικότερη από συγκεκριμένο ERP",
        ),
        ranked_candidates=[
            RankedCandidate(
                rank=1,
                candidate_id="test-uuid-123",
                candidate_name="Βάγια Βαΐτση",
                overall_suitability="High",
                match_percentage=78.0,
                strengths=[
                    CandidateEvidence(
                        criterion="Λογιστική εμπειρία",
                        candidate_value="8 χρόνια",
                        source="CV, Εμπειρία",
                        confidence="Confirmed",
                    )
                ],
                gaps=[
                    CandidateGap(
                        criterion="SAP συγκεκριμένα",
                        gap_description="Έχει Softone",
                        severity="Minor",
                        mitigation="ERP μεταφερόμενη εμπειρία",
                    )
                ],
                role_match=AssessmentScore(score="High", evidence=["8 χρόνια λογιστική"]),
                interview_focus=["Βάθος ERP γνώσεων"],
            )
        ],
        hr_recommendation=HRRecommendation(
            top_candidates=["Βάγια Βαΐτση"],
            recommendation_summary="Εξαιρετική υποψήφια με ισχυρό background",
            interview_priorities=["ERP εμπειρία", "Αγγλικά επίπεδο"],
            hiring_suggestions=["Εξετάστε SAP training"],
        ),
        analysis_language="el",
        latency_ms=4500,
    )


@pytest.fixture
def sample_llm_response_json():
    """Sample LLM JSON response."""
    return {
        "request_analysis": {
            "summary": "Search for accountants with SAP experience",
            "mandatory_criteria": ["Accounting background", "SAP experience"],
            "preferred_criteria": ["3+ years experience"],
            "inferred_criteria": ["Excel knowledge"],
        },
        "query_outcome": {
            "direct_matches": 2,
            "total_matches": 5,
            "relaxation_applied": False,
            "zero_results_reason": None,
        },
        "criteria_expansion": None,
        "ranked_candidates": [
            {
                "rank": 1,
                "candidate_id": "uuid-1",
                "candidate_name": "John Doe",
                "overall_suitability": "High",
                "match_percentage": 85.0,
                "strengths": [
                    {
                        "criterion": "SAP experience",
                        "candidate_value": "5 years SAP FI/CO",
                        "source": "CV, Experience section",
                        "confidence": "Confirmed",
                    }
                ],
                "gaps": [],
                "risks": [],
                "role_match": {"score": "High", "evidence": ["Senior Accountant"], "notes": ""},
                "experience_match": {"score": "High", "evidence": ["8 years"], "notes": ""},
                "skills_match": {"score": "High", "evidence": ["SAP, Excel"], "notes": ""},
                "language_match": {"score": "High", "evidence": ["English C1"], "notes": ""},
                "interview_focus": ["Verify SAP modules used"],
            }
        ],
        "hr_recommendation": {
            "top_candidates": ["John Doe"],
            "recommendation_summary": "Strong candidate pool",
            "interview_priorities": ["Technical depth"],
            "hiring_suggestions": ["Schedule interviews"],
            "alternative_search": None,
        },
    }


# =============================================================================
# SCHEMA TESTS
# =============================================================================


class TestLanguageRequirement:
    """Tests for LanguageRequirement dataclass."""

    def test_creation(self, sample_language_requirement):
        """Test basic creation."""
        assert sample_language_requirement.language_code == "en"
        assert sample_language_requirement.language_name == "English"
        assert sample_language_requirement.min_level == "B2"
        assert sample_language_requirement.is_required is True

    def test_defaults(self):
        """Test default values."""
        req = LanguageRequirement(language_code="de", language_name="German")
        assert req.min_level is None
        assert req.is_required is True


class TestJobRequirements:
    """Tests for JobRequirements dataclass."""

    def test_creation(self, sample_job_requirements):
        """Test basic creation."""
        assert sample_job_requirements.source_type == "query"
        assert sample_job_requirements.detected_language == "el"
        assert "accountant" in sample_job_requirements.roles
        assert "SAP" in sample_job_requirements.software

    def test_to_dict(self, sample_job_requirements):
        """Test dictionary conversion."""
        d = sample_job_requirements.to_dict()
        assert d["source_type"] == "query"
        assert d["roles"] == ["accountant"]
        assert len(d["languages"]) == 1
        assert d["languages"][0]["language_code"] == "en"

    def test_default_weights(self, sample_job_requirements):
        """Test default weights are set."""
        assert sample_job_requirements.weights["role"] == 0.25
        assert sample_job_requirements.weights["experience"] == 0.30


class TestCandidateProfile:
    """Tests for CandidateProfile dataclass."""

    def test_full_name(self, sample_candidate):
        """Test full_name property."""
        assert sample_candidate.full_name == "Βάγια Βαΐτση"

    def test_to_dict(self, sample_candidate):
        """Test dictionary conversion."""
        d = sample_candidate.to_dict()
        assert d["candidate_id"] == "test-uuid-123"
        assert d["full_name"] == "Βάγια Βαΐτση"
        assert d["total_experience_years"] == 8.0


class TestHRAnalysisReport:
    """Tests for HRAnalysisReport dataclass."""

    def test_to_dict(self, sample_hr_report):
        """Test full report dictionary conversion."""
        d = sample_hr_report.to_dict()

        assert d["request_analysis"]["summary"] == "Αναζήτηση λογιστών με SAP εμπειρία"
        assert d["query_outcome"]["direct_matches"] == 0
        assert d["query_outcome"]["total_matches"] == 3
        assert d["criteria_expansion"] is not None
        assert len(d["ranked_candidates"]) == 1
        assert d["ranked_candidates"][0]["rank"] == 1
        assert d["analysis_language"] == "el"


class TestParseHRAnalysisFromJson:
    """Tests for JSON parsing function."""

    def test_parse_full_response(self, sample_llm_response_json):
        """Test parsing complete LLM response."""
        report = parse_hr_analysis_from_json(sample_llm_response_json)

        assert report.request_analysis.summary == "Search for accountants with SAP experience"
        assert report.query_outcome.direct_matches == 2
        assert report.criteria_expansion is None
        assert len(report.ranked_candidates) == 1
        assert report.ranked_candidates[0].candidate_name == "John Doe"
        assert report.ranked_candidates[0].match_percentage == 85.0

    def test_parse_with_criteria_expansion(self, sample_llm_response_json):
        """Test parsing response with criteria expansion."""
        sample_llm_response_json["criteria_expansion"] = {
            "relaxations": [
                {
                    "original": "SAP 5 years",
                    "relaxed_to": "Any ERP 3 years",
                    "reasoning": "Skills transfer",
                }
            ],
            "business_rationale": "ERP experience is transferable",
        }

        report = parse_hr_analysis_from_json(sample_llm_response_json)

        assert report.criteria_expansion is not None
        assert len(report.criteria_expansion.relaxations) == 1
        assert report.criteria_expansion.relaxations[0].original == "SAP 5 years"


# =============================================================================
# PROMPT TESTS
# =============================================================================


class TestPrompts:
    """Tests for prompt generation."""

    def test_get_system_prompt_greek(self):
        """Test Greek system prompt retrieval."""
        prompt = get_system_prompt("el")
        assert "ΡΟΛΟΣ:" in prompt
        assert "ΚΑΝΟΝΕΣ ΑΝΑΛΥΣΗΣ:" in prompt

    def test_get_system_prompt_english(self):
        """Test English system prompt retrieval."""
        prompt = get_system_prompt("en")
        assert "ROLE:" in prompt
        assert "ANALYSIS RULES:" in prompt

    def test_get_user_message_greek(self):
        """Test Greek user message."""
        msg = get_user_message("Λογιστές με SAP", "el")
        assert "Λογιστές με SAP" in msg
        assert "JSON" in msg

    def test_get_user_message_english(self):
        """Test English user message."""
        msg = get_user_message("Accountants with SAP", "en")
        assert "Accountants with SAP" in msg
        assert "JSON" in msg

    def test_build_analysis_prompt(self, sample_job_requirements, sample_candidate):
        """Test full prompt building."""
        requirements_json = json.dumps(sample_job_requirements.to_dict(), ensure_ascii=False)
        candidates_json = json.dumps([sample_candidate.to_dict()], ensure_ascii=False)

        prompt = build_analysis_prompt(
            requirements_json=requirements_json,
            candidates_json=candidates_json,
            direct_count=0,
            total_count=1,
            relaxation_applied=True,
            language="el",
        )

        assert "ΑΠΑΙΤΗΣΕΙΣ ΘΕΣΗΣ:" in prompt
        assert "ΔΙΑΘΕΣΙΜΟΙ ΥΠΟΨΗΦΙΟΙ:" in prompt
        assert "Βάγια" in prompt


# =============================================================================
# ANALYZER TESTS
# =============================================================================


class TestHRIntelligenceAnalyzer:
    """Tests for HRIntelligenceAnalyzer class."""

    def test_language_detection_greek(self):
        """Test Greek language detection."""
        # Create analyzer without LLM (we're only testing language detection)
        analyzer = HRIntelligenceAnalyzer.__new__(HRIntelligenceAnalyzer)

        assert analyzer._detect_language("Λογιστές με SAP εμπειρία") == "el"
        assert analyzer._detect_language("Μηχανικοί παραγωγής") == "el"

    def test_language_detection_english(self):
        """Test English language detection."""
        analyzer = HRIntelligenceAnalyzer.__new__(HRIntelligenceAnalyzer)

        assert analyzer._detect_language("Accountants with SAP") == "en"
        assert analyzer._detect_language("Production engineers") == "en"

    def test_language_detection_mixed(self):
        """Test mixed language (Greek dominant)."""
        analyzer = HRIntelligenceAnalyzer.__new__(HRIntelligenceAnalyzer)

        # Greek dominant
        assert analyzer._detect_language("Λογιστές με SAP experience") == "el"

        # English dominant
        assert analyzer._detect_language("Accountants in Αθήνα") == "en"

    def test_extract_json_direct(self):
        """Test direct JSON extraction."""
        analyzer = HRIntelligenceAnalyzer.__new__(HRIntelligenceAnalyzer)

        json_str = '{"key": "value"}'
        result = analyzer._extract_json(json_str)
        assert result == {"key": "value"}

    def test_extract_json_from_markdown(self):
        """Test JSON extraction from markdown code block."""
        analyzer = HRIntelligenceAnalyzer.__new__(HRIntelligenceAnalyzer)

        content = '''Here is the analysis:

```json
{"key": "value"}
```

That's the result.'''

        result = analyzer._extract_json(content)
        assert result == {"key": "value"}

    def test_extract_json_with_surrounding_text(self):
        """Test JSON extraction with surrounding text."""
        analyzer = HRIntelligenceAnalyzer.__new__(HRIntelligenceAnalyzer)

        content = 'The result is: {"key": "value"} and that is all.'
        result = analyzer._extract_json(content)
        assert result == {"key": "value"}


# =============================================================================
# FORMATTER TESTS
# =============================================================================


class TestFormatters:
    """Tests for response formatters."""

    def test_format_compact_summary_greek(self, sample_hr_report):
        """Test compact summary in Greek."""
        summary = format_compact_summary(sample_hr_report)
        assert "Βρέθηκαν" in summary
        assert "Βάγια Βαΐτση" in summary

    def test_format_compact_summary_english(self, sample_hr_report):
        """Test compact summary in English."""
        sample_hr_report.analysis_language = "en"
        summary = format_compact_summary(sample_hr_report)
        assert "Found" in summary
        assert "candidates" in summary

    def test_format_compact_summary_empty(self):
        """Test compact summary with no candidates."""
        report = HRAnalysisReport(
            request_analysis=RequestAnalysis(summary="Test"),
            query_outcome=QueryOutcome(direct_matches=0, total_matches=0),
            ranked_candidates=[],
            analysis_language="el",
        )
        summary = format_compact_summary(report)
        assert "Δεν βρέθηκαν" in summary

    def test_format_text_report_greek(self, sample_hr_report):
        """Test full text report in Greek."""
        text = format_text_report(sample_hr_report)

        assert "ΑΝΑΛΥΣΗ HR INTELLIGENCE" in text
        assert "ΑΝΑΛΥΣΗ ΑΙΤΗΜΑΤΟΣ" in text
        assert "ΑΠΟΤΕΛΕΣΜΑΤΑ ΑΝΑΖΗΤΗΣΗΣ" in text
        assert "ΚΑΤΑΤΑΞΗ ΥΠΟΨΗΦΙΩΝ" in text
        assert "ΣΥΣΤΑΣΗ HR" in text
        assert "Βάγια Βαΐτση" in text

    def test_format_text_report_english(self, sample_hr_report):
        """Test full text report in English."""
        sample_hr_report.analysis_language = "en"
        text = format_text_report(sample_hr_report)

        assert "HR INTELLIGENCE ANALYSIS" in text
        assert "REQUEST ANALYSIS" in text
        assert "QUERY OUTCOME" in text
        assert "RANKED CANDIDATES" in text
        assert "HR RECOMMENDATION" in text


# =============================================================================
# INTEGRATION TESTS (without actual LLM calls)
# =============================================================================


class TestHRAnalysisInput:
    """Tests for HRAnalysisInput dataclass."""

    def test_creation(self, sample_job_requirements, sample_candidate):
        """Test input creation."""
        input_data = HRAnalysisInput(
            original_query="Λογιστές με SAP",
            requirements=sample_job_requirements,
            candidates=[sample_candidate],
            direct_result_count=0,
            total_result_count=1,
            relaxations_applied=["experience"],
        )

        assert input_data.original_query == "Λογιστές με SAP"
        assert len(input_data.candidates) == 1
        assert "experience" in input_data.relaxations_applied
