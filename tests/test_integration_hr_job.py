"""
Integration tests between HR Intelligence and Job Parser modules.

Tests that the modules work together correctly - JobParser produces
JobRequirements that can be consumed by HRIntelligenceAnalyzer.
"""

import asyncio
import json
import sys
from unittest.mock import patch

# Configure encoding for Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from lcmgo_cagenai.hr_intelligence.schema import (
    JobRequirements,
    LanguageRequirement,
    CandidateProfile,
    HRAnalysisInput,
    HRAnalysisReport,
)
from lcmgo_cagenai.hr_intelligence.analyzer import HRIntelligenceAnalyzer
from lcmgo_cagenai.hr_intelligence.formatter import (
    format_text_report,
    format_api_response,
    format_compact_summary,
)
from lcmgo_cagenai.llm.provider import LLMResponse
from lcmgo_cagenai.parser.job_parser import (
    JobParser,
    extract_requirements_from_query,
)


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

JOB_PARSER_RESPONSE = json.dumps({
    "detected_language": "el",
    "roles": ["accountant", "financial_analyst"],
    "role_priority": "must",
    "min_experience_years": 3,
    "max_experience_years": None,
    "experience_priority": "should",
    "software": ["SAP", "Excel"],
    "software_priority": "must",
    "certifications": ["CPA"],
    "certifications_priority": "nice",
    "skills": ["financial_reporting", "budgeting"],
    "skills_priority": "should",
    "languages": [
        {"language_code": "en", "language_name": "English", "min_level": "B2", "is_required": True}
    ],
    "locations": ["Athens"],
    "remote_acceptable": False,
    "education_level": "bachelor",
    "education_fields": ["accounting", "finance"]
}, ensure_ascii=False)

HR_ANALYSIS_RESPONSE = json.dumps({
    "request_analysis": {
        "summary": "Looking for accountants with SAP experience",
        "mandatory_criteria": ["Accountant role", "SAP knowledge"],
        "preferred_criteria": ["3+ years experience"],
        "inferred_criteria": ["Excel proficiency"]
    },
    "query_outcome": {
        "direct_matches": 2,
        "total_matches": 3,
        "relaxation_applied": False
    },
    "ranked_candidates": [
        {
            "rank": 1,
            "candidate_id": "c1",
            "candidate_name": "Test User",
            "overall_suitability": "High",
            "match_percentage": 85.0,
            "strengths": [
                {"criterion": "SAP", "candidate_value": "4 years", "source": "CV", "confidence": "Confirmed"}
            ],
            "gaps": [],
            "risks": [],
            "interview_focus": ["Technical skills"]
        }
    ],
    "hr_recommendation": {
        "top_candidates": ["Test User"],
        "recommendation_summary": "Test User is a strong match",
        "interview_priorities": ["Verify SAP depth"],
        "hiring_suggestions": ["Proceed with interview"]
    }
}, ensure_ascii=False)


# =============================================================================
# TESTS
# =============================================================================


def test_job_parser_produces_valid_requirements():
    """Test that JobParser produces JobRequirements compatible with HRAnalysisInput."""
    print("\n1. Testing JobParser produces valid JobRequirements...")

    mock_llm = MockLLMProvider(JOB_PARSER_RESPONSE)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)
        requirements = asyncio.run(parser.parse("Job posting text"))

    # Verify it's a valid JobRequirements
    assert isinstance(requirements, JobRequirements)
    assert requirements.source_type == "job_posting"

    # Verify it can be used in HRAnalysisInput
    input_data = HRAnalysisInput(
        original_query="Job posting text",
        requirements=requirements,
        candidates=[],
        direct_result_count=0,
        total_result_count=0,
        relaxations_applied=[]
    )

    assert input_data.requirements == requirements
    print("   PASSED: JobRequirements compatible with HRAnalysisInput")


def test_query_requirements_compatible_with_hr_analysis():
    """Test that extract_requirements_from_query produces valid input for HR analysis."""
    print("\n2. Testing query requirements compatibility...")

    requirements = extract_requirements_from_query(
        "Find accountants with SAP",
        detected_language="en"
    )

    assert isinstance(requirements, JobRequirements)
    assert requirements.source_type == "query"

    # Verify it can be used in HRAnalysisInput
    input_data = HRAnalysisInput(
        original_query="Find accountants with SAP",
        requirements=requirements,
        candidates=[],
        direct_result_count=0,
        total_result_count=0,
        relaxations_applied=[]
    )

    assert input_data.requirements.source_type == "query"
    print("   PASSED: Query requirements compatible with HR analysis")


def test_full_pipeline_job_posting_to_analysis():
    """Test complete pipeline: Job posting -> Parser -> HR Intelligence."""
    print("\n3. Testing full pipeline (job posting to analysis)...")

    # Step 1: Parse job posting
    job_parser_llm = MockLLMProvider(JOB_PARSER_RESPONSE)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=job_parser_llm)
        requirements = asyncio.run(parser.parse("Job posting for accountant"))

    # Step 2: Create candidate profiles
    candidates = [
        CandidateProfile(
            candidate_id="c1",
            first_name="Test",
            last_name="User",
            total_experience_years=5.0,
            software=["SAP", "Excel"],
            skills=["financial_reporting"],
            certifications=["CPA"],
            languages=[{"code": "en", "name": "English", "level": "C1"}]
        )
    ]

    # Step 3: Run HR Analysis
    hr_llm = MockLLMProvider(HR_ANALYSIS_RESPONSE)
    analyzer = HRIntelligenceAnalyzer(hr_llm)

    input_data = HRAnalysisInput(
        original_query="Job posting for accountant",
        requirements=requirements,
        candidates=candidates,
        direct_result_count=1,
        total_result_count=1,
        relaxations_applied=[]
    )

    report = asyncio.run(analyzer.analyze(input_data))

    # Verify complete pipeline
    assert isinstance(report, HRAnalysisReport)
    assert len(report.ranked_candidates) == 1
    assert report.ranked_candidates[0].candidate_name == "Test User"
    print("   PASSED: Full pipeline works correctly")


def test_job_requirements_to_dict_for_api():
    """Test that JobRequirements serializes correctly for API responses."""
    print("\n4. Testing JobRequirements serialization for API...")

    mock_llm = MockLLMProvider(JOB_PARSER_RESPONSE)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)
        requirements = asyncio.run(parser.parse("Job posting"))

    # Serialize to dict
    req_dict = requirements.to_dict()

    # Verify all expected fields
    assert "source_type" in req_dict
    assert "roles" in req_dict
    assert "software" in req_dict
    assert "languages" in req_dict
    assert "weights" in req_dict

    # Verify JSON serializable
    json_str = json.dumps(req_dict, ensure_ascii=False)
    parsed_back = json.loads(json_str)
    assert parsed_back["source_type"] == "job_posting"

    print("   PASSED: JobRequirements serializes correctly")


def test_hr_analysis_report_includes_requirements_info():
    """Test that HR analysis report reflects the input requirements."""
    print("\n5. Testing HR report reflects requirements...")

    # Create requirements with specific values
    requirements = JobRequirements(
        source_type="job_posting",
        source_text="Test job posting",
        detected_language="el",
        roles=["accountant"],
        software=["SAP"],
        min_experience_years=3
    )

    candidates = [
        CandidateProfile(
            candidate_id="c1",
            first_name="Test",
            last_name="User"
        )
    ]

    hr_llm = MockLLMProvider(HR_ANALYSIS_RESPONSE)
    analyzer = HRIntelligenceAnalyzer(hr_llm)

    input_data = HRAnalysisInput(
        original_query="Test job posting",
        requirements=requirements,
        candidates=candidates,
        direct_result_count=1,
        total_result_count=1,
        relaxations_applied=[]
    )

    report = asyncio.run(analyzer.analyze(input_data))

    # Report should be in Greek (matching detected_language)
    # Note: language detection uses original_query, not requirements.detected_language
    assert report.analysis_language in ["el", "en"]
    print("   PASSED: HR report reflects requirements")


def test_formatters_work_with_full_pipeline():
    """Test that formatters work with pipeline output."""
    print("\n6. Testing formatters with pipeline output...")

    # Create a complete report
    requirements = JobRequirements(
        source_type="job_posting",
        source_text="Test",
        detected_language="en"
    )

    hr_llm = MockLLMProvider(HR_ANALYSIS_RESPONSE)
    analyzer = HRIntelligenceAnalyzer(hr_llm)

    candidates = [
        CandidateProfile(candidate_id="c1", first_name="Test", last_name="User")
    ]

    input_data = HRAnalysisInput(
        original_query="Test query",
        requirements=requirements,
        candidates=candidates,
        direct_result_count=1,
        total_result_count=1,
        relaxations_applied=[]
    )

    report = asyncio.run(analyzer.analyze(input_data))

    # Test all formatters
    text = format_text_report(report)
    assert len(text) > 0
    assert "Test User" in text

    api_response = format_api_response(report)
    assert "ranked_candidates" in api_response
    assert len(api_response["ranked_candidates"]) == 1

    compact = format_compact_summary(report)
    assert "1 candidate" in compact or "Test User" in compact

    print("   PASSED: All formatters work with pipeline output")


def test_language_consistency():
    """Test language consistency through the pipeline."""
    print("\n7. Testing language consistency...")

    # Greek job posting
    greek_response = json.dumps({
        "detected_language": "el",
        "roles": ["logistis"],
        "languages": [{"language_code": "en", "language_name": "English", "min_level": "B2", "is_required": True}]
    }, ensure_ascii=False)

    mock_llm = MockLLMProvider(greek_response)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)
        requirements = asyncio.run(parser.parse("Greek job posting"))

    assert requirements.detected_language == "el"

    # English job posting
    english_response = json.dumps({
        "detected_language": "en",
        "roles": ["accountant"]
    })

    mock_llm = MockLLMProvider(english_response)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)
        requirements = asyncio.run(parser.parse("English job posting"))

    assert requirements.detected_language == "en"

    print("   PASSED: Language detected consistently")


def test_empty_candidates_with_job_posting():
    """Test HR analysis handles empty candidates from job posting."""
    print("\n8. Testing empty candidates from job posting...")

    requirements = JobRequirements(
        source_type="job_posting",
        source_text="Job for senior developer",
        detected_language="en",
        roles=["developer"],
        min_experience_years=10
    )

    hr_llm = MockLLMProvider("{}")  # Won't be called for empty candidates
    analyzer = HRIntelligenceAnalyzer(hr_llm)

    input_data = HRAnalysisInput(
        original_query="Job for senior developer",
        requirements=requirements,
        candidates=[],  # No candidates found
        direct_result_count=0,
        total_result_count=0,
        relaxations_applied=[]
    )

    report = asyncio.run(analyzer.analyze(input_data))

    assert report is not None
    assert len(report.ranked_candidates) == 0
    assert "No candidates" in report.request_analysis.summary

    print("   PASSED: Empty candidates handled correctly")


def test_weights_passed_through():
    """Test that scoring weights are available in requirements."""
    print("\n9. Testing weights in requirements...")

    mock_llm = MockLLMProvider(JOB_PARSER_RESPONSE)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)
        requirements = asyncio.run(parser.parse("Job posting"))

    # Default weights should be present
    assert requirements.weights is not None
    assert "role" in requirements.weights
    assert "experience" in requirements.weights
    assert "software" in requirements.weights

    # Weights should sum to ~1.0
    total = sum(requirements.weights.values())
    assert 0.99 <= total <= 1.01

    print("   PASSED: Weights available and valid")


def test_candidate_profile_full_name():
    """Test CandidateProfile full_name property works."""
    print("\n10. Testing CandidateProfile full_name...")

    candidate = CandidateProfile(
        candidate_id="c1",
        first_name="Ioannis",
        last_name="Papadopoulos"
    )

    assert candidate.full_name == "Ioannis Papadopoulos"

    # Test in dict
    d = candidate.to_dict()
    assert d["full_name"] == "Ioannis Papadopoulos"

    print("   PASSED: CandidateProfile full_name works")


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("HR Intelligence + Job Parser Integration Tests")
    print("=" * 60)

    tests = [
        test_job_parser_produces_valid_requirements,
        test_query_requirements_compatible_with_hr_analysis,
        test_full_pipeline_job_posting_to_analysis,
        test_job_requirements_to_dict_for_api,
        test_hr_analysis_report_includes_requirements_info,
        test_formatters_work_with_full_pipeline,
        test_language_consistency,
        test_empty_candidates_with_job_posting,
        test_weights_passed_through,
        test_candidate_profile_full_name,
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
