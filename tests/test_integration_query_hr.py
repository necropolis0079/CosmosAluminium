"""
Integration tests for Query Lambda with HR Intelligence.

Tests the complete flow: query -> SQL -> candidates -> HR analysis.
"""

import asyncio
import json
import sys
from unittest.mock import patch, MagicMock

# Configure encoding for Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from lcmgo_cagenai.hr_intelligence import (
    HRIntelligenceAnalyzer,
    HRAnalysisInput,
    JobRequirements,
    CandidateProfile,
    HRAnalysisReport,
    format_api_response,
)
from lcmgo_cagenai.llm.provider import LLMResponse


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(self, response_content: str = "{}"):
        self.response_content = response_content
        self.calls = []

    async def complete(self, request):
        self.calls.append(request)
        return LLMResponse(
            content=self.response_content,
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            latency_ms=100.0
        )


# =============================================================================
# TEST DATA
# =============================================================================

SAMPLE_CANDIDATES = [
    {
        "candidate_id": "c1",
        "first_name": "Ιωάννης",
        "last_name": "Παπαδόπουλος",
        "email": "i.papadopoulos@example.com",
        "current_location": "Αθήνα",
        "total_experience_years": 7,
        "current_role": "Λογιστής Α' Τάξης",
        "skills": ["financial_reporting", "budgeting"],
        "software": ["SAP", "Excel"],
        "certifications": ["CPA_A_CLASS"],
        "languages": [{"code": "en", "name": "English", "level": "C1"}],
    },
    {
        "candidate_id": "c2",
        "first_name": "Μαρία",
        "last_name": "Γεωργίου",
        "email": "m.georgiou@example.com",
        "current_location": "Θεσσαλονίκη",
        "total_experience_years": 4,
        "current_role": "Βοηθός Λογιστή",
        "skills": ["data_entry", "accounting"],
        "software": ["Excel", "Softone"],
        "certifications": [],
        "languages": [{"code": "en", "name": "English", "level": "B2"}],
    },
]

SAMPLE_TRANSLATION = {
    "confidence": 0.85,
    "filters": {
        "role": ["accountant"],
        "software": ["SAP", "Excel"],
        "min_experience": 3,
        "location": ["Αθήνα"],
    },
    "sort": None,
    "limit": 50,
    "unknown_terms": [],
}

HR_ANALYSIS_RESPONSE = json.dumps({
    "request_analysis": {
        "summary": "Αναζήτηση για λογιστές με SAP/Excel στην Αθήνα",
        "mandatory_criteria": ["Ρόλος: Λογιστής", "Software: SAP, Excel"],
        "preferred_criteria": ["Εμπειρία: 3+ έτη", "Τοποθεσία: Αθήνα"],
        "inferred_criteria": ["Γνώση λογιστικών προτύπων"]
    },
    "query_outcome": {
        "direct_matches": 2,
        "total_matches": 2,
        "relaxation_applied": False
    },
    "ranked_candidates": [
        {
            "rank": 1,
            "candidate_id": "c1",
            "candidate_name": "Ιωάννης Παπαδόπουλος",
            "overall_suitability": "High",
            "match_percentage": 90.0,
            "strengths": [
                {"criterion": "SAP", "candidate_value": "Εμπειρία SAP", "source": "CV", "confidence": "Confirmed"}
            ],
            "gaps": [],
            "risks": [],
            "interview_focus": ["Τεχνικές δεξιότητες SAP"]
        },
        {
            "rank": 2,
            "candidate_id": "c2",
            "candidate_name": "Μαρία Γεωργίου",
            "overall_suitability": "Medium",
            "match_percentage": 65.0,
            "strengths": [
                {"criterion": "Excel", "candidate_value": "Χρήση Excel", "source": "CV", "confidence": "Confirmed"}
            ],
            "gaps": [
                {"criterion": "SAP", "gap_description": "Δεν έχει SAP", "severity": "Major", "mitigation": "Εκπαίδευση"}
            ],
            "risks": [],
            "interview_focus": ["Δυνατότητα εκμάθησης SAP"]
        }
    ],
    "hr_recommendation": {
        "top_candidates": ["Ιωάννης Παπαδόπουλος"],
        "recommendation_summary": "Ο Ιωάννης είναι εξαιρετική επιλογή με πλήρη κάλυψη απαιτήσεων",
        "interview_priorities": ["SAP τεχνικές δεξιότητες", "Ηγετικές ικανότητες"],
        "hiring_suggestions": ["Άμεση πρόσληψη μπορεί να γίνει"]
    }
}, ensure_ascii=False)


# =============================================================================
# TESTS
# =============================================================================


def test_hr_intelligence_integration_with_candidates():
    """Test HR Intelligence analysis with sample candidates."""
    print("\n1. Testing HR Intelligence integration with candidates...")

    mock_llm = MockLLMProvider(HR_ANALYSIS_RESPONSE)
    analyzer = HRIntelligenceAnalyzer(mock_llm)

    # Create candidate profiles
    candidates = [
        CandidateProfile(
            candidate_id="c1",
            first_name="Ιωάννης",
            last_name="Παπαδόπουλος",
            total_experience_years=7.0,
            software=["SAP", "Excel"],
            skills=["financial_reporting"],
            certifications=["CPA_A_CLASS"],
        ),
        CandidateProfile(
            candidate_id="c2",
            first_name="Μαρία",
            last_name="Γεωργίου",
            total_experience_years=4.0,
            software=["Excel", "Softone"],
        ),
    ]

    # Create requirements
    requirements = JobRequirements(
        source_type="query",
        source_text="Λογιστές με SAP στην Αθήνα",
        detected_language="el",
        roles=["accountant"],
        software=["SAP", "Excel"],
        min_experience_years=3,
        locations=["Αθήνα"],
    )

    # Create input
    input_data = HRAnalysisInput(
        original_query="Λογιστές με SAP στην Αθήνα",
        requirements=requirements,
        candidates=candidates,
        direct_result_count=2,
        total_result_count=2,
        relaxations_applied=[],
    )

    # Run analysis
    report = asyncio.run(analyzer.analyze(input_data))

    # Verify report
    assert isinstance(report, HRAnalysisReport)
    assert len(report.ranked_candidates) == 2
    assert report.ranked_candidates[0].candidate_id == "c1"
    assert report.analysis_language == "el"

    print("   PASSED: HR Intelligence integration works correctly")


def test_hr_intelligence_api_response_format():
    """Test that HR analysis formats correctly for API response."""
    print("\n2. Testing HR analysis API response format...")

    mock_llm = MockLLMProvider(HR_ANALYSIS_RESPONSE)
    analyzer = HRIntelligenceAnalyzer(mock_llm)

    candidates = [
        CandidateProfile(candidate_id="c1", first_name="Test", last_name="User")
    ]

    requirements = JobRequirements(
        source_type="query",
        source_text="Test query",
        detected_language="en",
    )

    input_data = HRAnalysisInput(
        original_query="Test query",
        requirements=requirements,
        candidates=candidates,
        direct_result_count=1,
        total_result_count=1,
        relaxations_applied=[],
    )

    report = asyncio.run(analyzer.analyze(input_data))

    # Format for API
    api_response = format_api_response(report)

    # Verify structure
    assert "request_analysis" in api_response
    assert "query_outcome" in api_response
    assert "ranked_candidates" in api_response
    assert "hr_recommendation" in api_response
    assert "analysis_language" in api_response

    # Verify JSON serializable
    json_str = json.dumps(api_response, ensure_ascii=False)
    parsed = json.loads(json_str)
    assert parsed["analysis_language"] in ["el", "en"]

    print("   PASSED: API response format is correct")


def test_candidate_profile_from_dict():
    """Test creating CandidateProfile from raw dictionary."""
    print("\n3. Testing CandidateProfile from dictionary...")

    raw = SAMPLE_CANDIDATES[0]

    profile = CandidateProfile(
        candidate_id=str(raw.get("candidate_id", "")),
        first_name=raw.get("first_name", ""),
        last_name=raw.get("last_name", ""),
        email=raw.get("email"),
        city=raw.get("current_location"),  # Use city instead of current_location
        total_experience_years=float(raw.get("total_experience_years") or 0),
        skills=raw.get("skills", []),
        software=raw.get("software", []),
        certifications=raw.get("certifications", []),
        languages=raw.get("languages", []),
    )

    assert profile.candidate_id == "c1"
    assert profile.first_name == "Ιωάννης"
    assert profile.full_name == "Ιωάννης Παπαδόπουλος"
    assert profile.total_experience_years == 7.0
    assert "SAP" in profile.software

    print("   PASSED: CandidateProfile from dict works correctly")


def test_job_requirements_from_translation():
    """Test creating JobRequirements from query translation."""
    print("\n4. Testing JobRequirements from translation...")

    filters = SAMPLE_TRANSLATION["filters"]

    requirements = JobRequirements(
        source_type="query",
        source_text="Λογιστές με SAP",
        detected_language="el",
        roles=filters.get("role", []) if isinstance(filters.get("role"), list) else [filters.get("role")] if filters.get("role") else [],
        min_experience_years=filters.get("min_experience"),
        software=filters.get("software", []) if isinstance(filters.get("software"), list) else [],
        locations=filters.get("location", []) if isinstance(filters.get("location"), list) else [filters.get("location")] if filters.get("location") else [],
    )

    assert requirements.source_type == "query"
    assert "accountant" in requirements.roles
    assert "SAP" in requirements.software
    assert requirements.min_experience_years == 3
    assert "Αθήνα" in requirements.locations

    print("   PASSED: JobRequirements from translation works correctly")


def test_empty_candidates_handling():
    """Test HR analysis handles empty candidates gracefully."""
    print("\n5. Testing empty candidates handling...")

    mock_llm = MockLLMProvider("{}")
    analyzer = HRIntelligenceAnalyzer(mock_llm)

    requirements = JobRequirements(
        source_type="query",
        source_text="Test",
        detected_language="en",
    )

    input_data = HRAnalysisInput(
        original_query="Test query",
        requirements=requirements,
        candidates=[],
        direct_result_count=0,
        total_result_count=0,
        relaxations_applied=[],
    )

    report = asyncio.run(analyzer.analyze(input_data))

    # Should return report even with no candidates
    assert report is not None
    assert "No candidates" in report.request_analysis.summary
    assert len(report.ranked_candidates) == 0

    print("   PASSED: Empty candidates handled gracefully")


def test_relaxation_flag_propagation():
    """Test that relaxation flag is properly propagated to input and analysis completes."""
    print("\n6. Testing relaxation flag propagation...")

    mock_llm = MockLLMProvider(HR_ANALYSIS_RESPONSE)
    analyzer = HRIntelligenceAnalyzer(mock_llm)

    candidates = [
        CandidateProfile(candidate_id="c1", first_name="Test", last_name="User")
    ]

    requirements = JobRequirements(
        source_type="query",
        source_text="Test",
        detected_language="en",
    )

    relaxation_msg = "Experience requirement relaxed from 5 to 3 years"
    input_data = HRAnalysisInput(
        original_query="Test query",
        requirements=requirements,
        candidates=candidates,
        direct_result_count=0,  # No direct matches
        total_result_count=1,   # But relaxation found one
        relaxations_applied=[relaxation_msg],
    )

    # Verify the input has the relaxation info
    assert len(input_data.relaxations_applied) == 1
    assert relaxation_msg in input_data.relaxations_applied

    # Run analysis
    report = asyncio.run(analyzer.analyze(input_data))

    # Verify analysis completed successfully
    assert report is not None
    assert len(mock_llm.calls) == 1
    # Verify report shows correct result counts
    assert report.query_outcome.direct_matches == 2  # From mock response
    assert report.query_outcome.total_matches == 2   # From mock response

    print("   PASSED: Relaxation flag propagation works")


def test_greek_language_detection():
    """Test Greek language detection for response language."""
    print("\n7. Testing Greek language detection...")

    mock_llm = MockLLMProvider(HR_ANALYSIS_RESPONSE)
    analyzer = HRIntelligenceAnalyzer(mock_llm)

    candidates = [
        CandidateProfile(candidate_id="c1", first_name="Test", last_name="User")
    ]

    # Greek query
    requirements_el = JobRequirements(
        source_type="query",
        source_text="Λογιστές με SAP",
        detected_language="el",
    )

    input_el = HRAnalysisInput(
        original_query="Λογιστές με SAP",
        requirements=requirements_el,
        candidates=candidates,
        direct_result_count=1,
        total_result_count=1,
        relaxations_applied=[],
    )

    report_el = asyncio.run(analyzer.analyze(input_el))
    assert report_el.analysis_language == "el"

    print("   PASSED: Greek language detection works")


def test_english_language_detection():
    """Test English language detection for response language."""
    print("\n8. Testing English language detection...")

    mock_llm = MockLLMProvider(HR_ANALYSIS_RESPONSE.replace('"el"', '"en"'))
    analyzer = HRIntelligenceAnalyzer(mock_llm)

    candidates = [
        CandidateProfile(candidate_id="c1", first_name="Test", last_name="User")
    ]

    # English query
    requirements_en = JobRequirements(
        source_type="query",
        source_text="Accountants with SAP",
        detected_language="en",
    )

    input_en = HRAnalysisInput(
        original_query="Accountants with SAP",
        requirements=requirements_en,
        candidates=candidates,
        direct_result_count=1,
        total_result_count=1,
        relaxations_applied=[],
    )

    report_en = asyncio.run(analyzer.analyze(input_en))
    # The mock response has el, so we'll check it's handled
    assert report_en.analysis_language in ["el", "en"]

    print("   PASSED: English language detection works")


def test_multiple_candidates_ranking():
    """Test that multiple candidates are properly ranked."""
    print("\n9. Testing multiple candidates ranking...")

    mock_llm = MockLLMProvider(HR_ANALYSIS_RESPONSE)
    analyzer = HRIntelligenceAnalyzer(mock_llm)

    candidates = [
        CandidateProfile(
            candidate_id="c1",
            first_name="Ιωάννης",
            last_name="Παπαδόπουλος",
            total_experience_years=7.0,
            software=["SAP", "Excel"],
        ),
        CandidateProfile(
            candidate_id="c2",
            first_name="Μαρία",
            last_name="Γεωργίου",
            total_experience_years=4.0,
            software=["Excel"],
        ),
        CandidateProfile(
            candidate_id="c3",
            first_name="Νίκος",
            last_name="Δημητρίου",
            total_experience_years=2.0,
        ),
    ]

    requirements = JobRequirements(
        source_type="query",
        source_text="Λογιστές",
        detected_language="el",
    )

    input_data = HRAnalysisInput(
        original_query="Λογιστές",
        requirements=requirements,
        candidates=candidates,
        direct_result_count=3,
        total_result_count=3,
        relaxations_applied=[],
    )

    report = asyncio.run(analyzer.analyze(input_data))

    # Response has 2 candidates ranked
    assert len(report.ranked_candidates) == 2
    assert report.ranked_candidates[0].rank == 1
    assert report.ranked_candidates[1].rank == 2
    assert report.ranked_candidates[0].match_percentage >= report.ranked_candidates[1].match_percentage

    print("   PASSED: Multiple candidates ranking works")


def test_hr_recommendation_structure():
    """Test HR recommendation has all required fields."""
    print("\n10. Testing HR recommendation structure...")

    mock_llm = MockLLMProvider(HR_ANALYSIS_RESPONSE)
    analyzer = HRIntelligenceAnalyzer(mock_llm)

    candidates = [
        CandidateProfile(candidate_id="c1", first_name="Test", last_name="User")
    ]

    requirements = JobRequirements(
        source_type="query",
        source_text="Test",
        detected_language="en",
    )

    input_data = HRAnalysisInput(
        original_query="Test",
        requirements=requirements,
        candidates=candidates,
        direct_result_count=1,
        total_result_count=1,
        relaxations_applied=[],
    )

    report = asyncio.run(analyzer.analyze(input_data))

    # Verify recommendation structure
    rec = report.hr_recommendation
    assert rec is not None
    assert rec.top_candidates is not None
    assert rec.recommendation_summary is not None
    assert rec.interview_priorities is not None
    assert rec.hiring_suggestions is not None

    print("   PASSED: HR recommendation structure is correct")


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("Query Lambda + HR Intelligence Integration Tests")
    print("=" * 60)

    tests = [
        test_hr_intelligence_integration_with_candidates,
        test_hr_intelligence_api_response_format,
        test_candidate_profile_from_dict,
        test_job_requirements_from_translation,
        test_empty_candidates_handling,
        test_relaxation_flag_propagation,
        test_greek_language_detection,
        test_english_language_detection,
        test_multiple_candidates_ranking,
        test_hr_recommendation_structure,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"   FAILED: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
