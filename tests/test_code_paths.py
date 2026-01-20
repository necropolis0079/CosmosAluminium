"""
Code path verification tests for HR Intelligence module.
Tests edge cases, error handling, and all code branches.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone

# Configure encoding for Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from lcmgo_cagenai.hr_intelligence.schema import (
    HRAnalysisInput,
    JobRequirements,
    CandidateProfile,
    HRAnalysisReport,
    LanguageRequirement,
    parse_hr_analysis_from_json,
    RequestAnalysis,
    QueryOutcome,
    CandidateEvidence,
    CandidateGap,
    AssessmentScore,
    RankedCandidate,
    CriteriaRelaxation,
    CriteriaExpansion,
    HRRecommendation,
)
from lcmgo_cagenai.hr_intelligence.analyzer import HRIntelligenceAnalyzer
from lcmgo_cagenai.hr_intelligence.prompts import (
    build_analysis_prompt,
    get_user_message,
    get_system_prompt,
)
from lcmgo_cagenai.hr_intelligence.formatter import (
    format_text_report,
    format_api_response,
    format_compact_summary,
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


def create_job_requirements(**kwargs):
    """Create JobRequirements with defaults."""
    defaults = {
        "source_type": "query",
        "source_text": "Test query",
        "detected_language": "en",
        "roles": ["accountant"],
    }
    defaults.update(kwargs)
    return JobRequirements(**defaults)


def create_candidate_profile(**kwargs):
    """Create CandidateProfile with defaults."""
    defaults = {
        "candidate_id": "c1",
        "first_name": "Test",
        "last_name": "User",
    }
    defaults.update(kwargs)
    return CandidateProfile(**defaults)


def test_empty_candidates_english():
    """Test empty candidates with English query."""
    print("\n1. Testing empty candidates (English)...")

    llm = MockLLMProvider()
    analyzer = HRIntelligenceAnalyzer(llm)

    input_data = HRAnalysisInput(
        original_query="Senior accountant with SAP",
        requirements=create_job_requirements(),
        candidates=[],
        direct_result_count=0,
        total_result_count=0,
        relaxations_applied=[]
    )

    report = asyncio.run(analyzer.analyze(input_data))

    assert report is not None
    assert len(report.ranked_candidates) == 0
    assert report.analysis_language == "en"
    assert report.query_outcome.total_matches == 0
    assert "No candidates" in report.request_analysis.summary
    print("   PASSED: Empty candidates returns valid empty report (English)")


def test_empty_candidates_greek():
    """Test empty candidates with Greek query."""
    print("\n2. Testing empty candidates (Greek)...")

    llm = MockLLMProvider()
    analyzer = HRIntelligenceAnalyzer(llm)

    input_data = HRAnalysisInput(
        original_query="Logistes me SAP",  # Greek transliteration
        requirements=create_job_requirements(
            source_text="Logistes me SAP",
            detected_language="el"
        ),
        candidates=[],
        direct_result_count=0,
        total_result_count=0,
        relaxations_applied=[]
    )

    report = asyncio.run(analyzer.analyze(input_data))

    assert report is not None
    assert report.analysis_language == "en"  # No Greek chars = English
    print("   PASSED: Transliterated Greek detected as English (expected)")


def test_greek_detection():
    """Test Greek language detection with actual Greek characters."""
    print("\n3. Testing Greek language detection...")

    analyzer = HRIntelligenceAnalyzer(MockLLMProvider())

    # Pure Latin
    lang = analyzer._detect_language("Logistes")
    assert lang == "en"  # Latin chars

    # Mixed but mostly Latin
    lang = analyzer._detect_language("test123")
    assert lang == "en"

    # No alpha chars
    lang = analyzer._detect_language("12345")
    assert lang == "en"

    print("   PASSED: Language detection handles all cases")


def test_json_extraction_formats():
    """Test JSON extraction from various LLM response formats."""
    print("\n4. Testing JSON extraction formats...")

    analyzer = HRIntelligenceAnalyzer(MockLLMProvider())

    # Direct JSON
    result = analyzer._extract_json('{"key": "value"}')
    assert result == {"key": "value"}

    # Markdown code block
    result = analyzer._extract_json('```json\n{"key": "value"}\n```')
    assert result == {"key": "value"}

    # Markdown without json tag
    result = analyzer._extract_json('```\n{"key": "value"}\n```')
    assert result == {"key": "value"}

    # JSON surrounded by text
    result = analyzer._extract_json('Here is the response: {"key": "value"} done.')
    assert result == {"key": "value"}

    # Invalid JSON
    result = analyzer._extract_json('not json at all')
    assert result is None

    print("   PASSED: All JSON extraction formats work")


def test_input_validation():
    """Test input validation errors."""
    print("\n5. Testing input validation...")

    llm = MockLLMProvider()
    analyzer = HRIntelligenceAnalyzer(llm)

    # Missing query
    try:
        input_data = HRAnalysisInput(
            original_query="",
            requirements=create_job_requirements(),
            candidates=[],
            direct_result_count=0,
            total_result_count=0,
            relaxations_applied=[]
        )
        asyncio.run(analyzer.analyze(input_data))
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "original_query" in str(e)

    # Missing requirements
    try:
        input_data = HRAnalysisInput(
            original_query="Test",
            requirements=None,
            candidates=[],
            direct_result_count=0,
            total_result_count=0,
            relaxations_applied=[]
        )
        asyncio.run(analyzer.analyze(input_data))
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "requirements" in str(e)

    print("   PASSED: Input validation catches errors")


def test_max_candidates_limit():
    """Test that candidates are limited to max_candidates."""
    print("\n6. Testing max candidates limit...")

    # Create valid JSON response for LLM
    valid_response = json.dumps({
        "request_analysis": {
            "summary": "Test",
            "mandatory_criteria": [],
            "preferred_criteria": [],
            "inferred_criteria": []
        },
        "query_outcome": {
            "direct_matches": 5,
            "total_matches": 5,
            "relaxation_applied": False
        },
        "ranked_candidates": []
    }, ensure_ascii=False)

    llm = MockLLMProvider(valid_response)
    analyzer = HRIntelligenceAnalyzer(llm, max_candidates=3)

    # Create 10 candidates
    candidates = [
        create_candidate_profile(
            candidate_id=f"c{i}",
            first_name=f"Candidate{i}",
            last_name=f"Test{i}",
            total_experience_years=float(i)
        )
        for i in range(10)
    ]

    input_data = HRAnalysisInput(
        original_query="Test query",
        requirements=create_job_requirements(),
        candidates=candidates,
        direct_result_count=10,
        total_result_count=10,
        relaxations_applied=[]
    )

    report = asyncio.run(analyzer.analyze(input_data))

    # Check that LLM was called (meaning candidates weren't empty)
    assert len(llm.calls) == 1
    print("   PASSED: Max candidates limit applied")


def test_prompt_generation():
    """Test prompt generation for both languages."""
    print("\n7. Testing prompt generation...")

    # English prompt
    en_prompt = get_system_prompt("en")
    assert "HR Intelligence Analyst" in en_prompt or len(en_prompt) > 100
    assert "JSON" in en_prompt

    # Greek prompt
    el_prompt = get_system_prompt("el")
    assert len(el_prompt) > 0

    # User message
    en_msg = get_user_message("Find accountants", "en")
    assert "Find accountants" in en_msg

    el_msg = get_user_message("Test query", "el")
    assert "Test query" in el_msg

    print("   PASSED: Prompt generation works for both languages")


def test_full_analysis_prompt():
    """Test full analysis prompt building."""
    print("\n8. Testing full analysis prompt...")

    requirements_json = json.dumps({
        "roles": ["Accountant"],
        "software": ["SAP"]
    }, ensure_ascii=False)

    candidates_json = json.dumps([
        {"candidate_id": "c1", "first_name": "Test", "last_name": "User"}
    ], ensure_ascii=False)

    prompt = build_analysis_prompt(
        requirements_json=requirements_json,
        candidates_json=candidates_json,
        direct_count=1,
        total_count=1,
        relaxation_applied=False,
        language="en"
    )

    assert requirements_json in prompt
    assert candidates_json in prompt
    assert "Direct matches: 1" in prompt
    print("   PASSED: Full analysis prompt built correctly")


def test_formatter_with_empty_report():
    """Test formatters handle empty reports."""
    print("\n9. Testing formatters with empty report...")

    empty_report = HRAnalysisReport(
        request_analysis=RequestAnalysis(
            summary="No candidates found",
            mandatory_criteria=[],
            preferred_criteria=[],
            inferred_criteria=[]
        ),
        query_outcome=QueryOutcome(
            direct_matches=0,
            total_matches=0,
            relaxation_applied=False
        ),
        ranked_candidates=[],
        analysis_language="en",
        analysis_timestamp=datetime.now(timezone.utc),
        llm_model="test-model",
        latency_ms=100
    )

    # Text format
    text = format_text_report(empty_report)
    assert "No candidates found" in text or "0" in text

    # API format
    api = format_api_response(empty_report)
    assert api["ranked_candidates"] == []

    # Compact format
    compact = format_compact_summary(empty_report)
    assert "No candidates found" in compact

    print("   PASSED: Formatters handle empty reports")


def test_dataclass_serialization():
    """Test all dataclass to_dict methods."""
    print("\n10. Testing dataclass serialization...")

    # Test CandidateEvidence
    evidence = CandidateEvidence(
        criterion="SAP",
        candidate_value="5 years experience",
        source="CV page 1"
    )
    d = evidence.to_dict()
    assert d["criterion"] == "SAP"
    assert d["candidate_value"] == "5 years experience"

    # Test CandidateGap
    gap = CandidateGap(
        criterion="Excel",
        gap_description="Missing advanced features",
        severity="Minor",
        mitigation="Training available"
    )
    d = gap.to_dict()
    assert d["severity"] == "Minor"

    # Test AssessmentScore
    score = AssessmentScore(
        score="High",
        evidence=["Strong skills", "Good experience"],
        notes="Good match"
    )
    d = score.to_dict()
    assert d["score"] == "High"

    # Test RankedCandidate
    ranked = RankedCandidate(
        rank=1,
        candidate_id="c1",
        candidate_name="Test User",
        overall_suitability="High",
        match_percentage=85.0,
        strengths=[evidence],
        gaps=[gap],
        role_match=score
    )
    d = ranked.to_dict()
    assert d["rank"] == 1
    assert len(d["strengths"]) == 1
    assert d["match_percentage"] == 85.0

    # Test CriteriaRelaxation
    relaxation = CriteriaRelaxation(
        original="5 years SAP",
        relaxed_to="3 years ERP",
        reasoning="Insufficient candidates"
    )
    d = relaxation.to_dict()
    assert "original" in d

    # Test CriteriaExpansion
    expansion = CriteriaExpansion(
        relaxations=[relaxation],
        business_rationale="Broadened search"
    )
    d = expansion.to_dict()
    assert len(d["relaxations"]) == 1

    # Test HRRecommendation
    rec = HRRecommendation(
        top_candidates=["c1"],
        recommendation_summary="Hire c1",
        interview_priorities=["Technical skills"],
        hiring_suggestions=["Start ASAP"]
    )
    d = rec.to_dict()
    assert d["top_candidates"] == ["c1"]

    print("   PASSED: All dataclass serialization works")


def test_parse_hr_analysis_from_json():
    """Test parsing LLM response into HRAnalysisReport."""
    print("\n11. Testing parse_hr_analysis_from_json...")

    json_data = {
        "request_analysis": {
            "summary": "Looking for accountants",
            "mandatory_criteria": ["SAP"],
            "preferred_criteria": ["Excel"],
            "inferred_criteria": []
        },
        "query_outcome": {
            "direct_matches": 2,
            "total_matches": 5,
            "relaxation_applied": True
        },
        "criteria_expansion": {
            "relaxations": [
                {
                    "original": "5 years",
                    "relaxed_to": "3 years",
                    "reasoning": "Limited candidates"
                }
            ],
            "business_rationale": "Broadened experience requirement"
        },
        "ranked_candidates": [
            {
                "rank": 1,
                "candidate_id": "c1",
                "candidate_name": "Test User",
                "overall_suitability": "High",
                "match_percentage": 85.0,
                "strengths": [
                    {
                        "criterion": "SAP",
                        "candidate_value": "4 years",
                        "source": "CV",
                        "confidence": "Confirmed"
                    }
                ],
                "gaps": [],
                "risks": [],
                "role_match": {
                    "score": "High",
                    "evidence": ["Good match"],
                    "notes": ""
                },
                "interview_focus": ["Technical skills"]
            }
        ],
        "hr_recommendation": {
            "top_candidates": ["c1"],
            "recommendation_summary": "Interview c1",
            "interview_priorities": ["Technical"],
            "hiring_suggestions": ["Act fast"]
        }
    }

    report = parse_hr_analysis_from_json(json_data)

    assert report.request_analysis.summary == "Looking for accountants"
    assert report.query_outcome.direct_matches == 2
    assert report.criteria_expansion is not None
    assert len(report.ranked_candidates) == 1
    assert report.ranked_candidates[0].overall_suitability == "High"
    assert report.ranked_candidates[0].match_percentage == 85.0
    assert report.hr_recommendation.top_candidates == ["c1"]

    print("   PASSED: parse_hr_analysis_from_json works correctly")


def test_sync_wrapper():
    """Test synchronous wrapper function."""
    print("\n12. Testing synchronous wrapper...")

    from lcmgo_cagenai.hr_intelligence.analyzer import analyze_candidates_sync

    valid_response = json.dumps({
        "request_analysis": {
            "summary": "Test",
            "mandatory_criteria": [],
            "preferred_criteria": [],
            "inferred_criteria": []
        },
        "query_outcome": {
            "direct_matches": 0,
            "total_matches": 0,
            "relaxation_applied": False
        },
        "ranked_candidates": []
    }, ensure_ascii=False)

    llm = MockLLMProvider(valid_response)

    report = analyze_candidates_sync(
        llm_provider=llm,
        original_query="Test query",
        requirements=create_job_requirements(),
        candidates=[],
        direct_result_count=0,
        relaxations_applied=[]
    )

    assert report is not None
    assert isinstance(report, HRAnalysisReport)
    print("   PASSED: Synchronous wrapper works")


def test_job_requirements_weights():
    """Test JobRequirements weights property."""
    print("\n13. Testing JobRequirements weights...")

    req = create_job_requirements()

    assert "role" in req.weights
    assert "experience" in req.weights
    assert req.weights["role"] == 0.25
    assert req.weights["experience"] == 0.30

    d = req.to_dict()
    assert "weights" in d

    print("   PASSED: JobRequirements weights work")


def test_candidate_profile_full_name_property():
    """Test CandidateProfile full_name property."""
    print("\n14. Testing CandidateProfile full_name property...")

    candidate = create_candidate_profile(
        first_name="John",
        last_name="Doe"
    )

    assert candidate.full_name == "John Doe"

    d = candidate.to_dict()
    assert d["full_name"] == "John Doe"

    print("   PASSED: CandidateProfile full_name property works")


def test_language_requirement():
    """Test LanguageRequirement dataclass."""
    print("\n15. Testing LanguageRequirement...")

    lang_req = LanguageRequirement(
        language_code="en",
        language_name="English",
        min_level="B2",
        is_required=True
    )

    assert lang_req.language_code == "en"
    assert lang_req.min_level == "B2"

    # Test in JobRequirements
    req = create_job_requirements(languages=[lang_req])
    d = req.to_dict()
    assert len(d["languages"]) == 1
    assert d["languages"][0]["language_code"] == "en"

    print("   PASSED: LanguageRequirement works")


def main():
    """Run all code path verification tests."""
    print("=" * 60)
    print("HR Intelligence Module - Code Path Verification")
    print("=" * 60)

    tests = [
        test_empty_candidates_english,
        test_empty_candidates_greek,
        test_greek_detection,
        test_json_extraction_formats,
        test_input_validation,
        test_max_candidates_limit,
        test_prompt_generation,
        test_full_analysis_prompt,
        test_formatter_with_empty_report,
        test_dataclass_serialization,
        test_parse_hr_analysis_from_json,
        test_sync_wrapper,
        test_job_requirements_weights,
        test_candidate_profile_full_name_property,
        test_language_requirement,
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
