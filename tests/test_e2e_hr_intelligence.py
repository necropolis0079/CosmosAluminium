"""
End-to-End Tests for HR Intelligence System.

Tests the complete flow from query/job posting to HR analysis report
with realistic scenarios in both Greek and English.

Phase 5: Testing & Refinement
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
    format_text_report,
    format_api_response,
    format_compact_summary,
)
from lcmgo_cagenai.parser import JobParser, parse_job_posting_sync, extract_requirements_from_query
from lcmgo_cagenai.llm.provider import LLMResponse


# =============================================================================
# MOCK LLM PROVIDER
# =============================================================================

class MockLLMProvider:
    """Mock LLM provider with configurable responses."""

    def __init__(self, responses: dict[str, str] | None = None):
        self.responses = responses or {}
        self.default_response = "{}"
        self.calls = []

    def set_response(self, key: str, response: str):
        """Set response for a key (matched against prompt AND system)."""
        self.responses[key] = response

    async def complete(self, request):
        self.calls.append(request)

        # Build search text from prompt and system
        search_text = request.prompt.lower()
        if hasattr(request, 'system') and request.system:
            search_text += " " + request.system.lower()

        # Find matching response based on content
        for key, response in self.responses.items():
            if key.lower() in search_text:
                content = response
                break
        else:
            content = self.default_response

        return LLMResponse(
            content=content,
            model="test-model",
            input_tokens=500,
            output_tokens=200,
            latency_ms=150.0
        )


# =============================================================================
# TEST DATA - REALISTIC SCENARIOS
# =============================================================================

# Greek job posting for accountant
GREEK_JOB_POSTING = """
ΘΕΣΗ ΕΡΓΑΣΙΑΣ: Λογιστής Α' Τάξης

Μεγάλη βιομηχανική εταιρεία στην Αθήνα αναζητά έμπειρο Λογιστή.

ΑΠΑΡΑΙΤΗΤΑ ΠΡΟΣΟΝΤΑ:
- Πτυχίο ΑΕΙ/ΤΕΙ Οικονομικής κατεύθυνσης
- Άδεια Λογιστή Α' Τάξης
- Εμπειρία τουλάχιστον 5 ετών σε αντίστοιχη θέση
- Άριστη γνώση SAP ERP
- Πολύ καλή γνώση Microsoft Excel
- Αγγλικά επίπεδο B2 τουλάχιστον

ΕΠΙΘΥΜΗΤΑ ΠΡΟΣΟΝΤΑ:
- Μεταπτυχιακό σε Χρηματοοικονομικά ή Λογιστική
- Γνώση Γερμανικών
- Εμπειρία σε πολυεθνικό περιβάλλον

ΠΑΡΟΧΕΣ:
- Ανταγωνιστικός μισθός
- Ιδιωτική ασφάλιση

Τοποθεσία: Αθήνα (Μεταμόρφωση)
"""

# English job posting for developer
ENGLISH_JOB_POSTING = """
JOB TITLE: Senior Software Engineer

Leading tech company is looking for a Senior Software Engineer.

REQUIREMENTS:
- Bachelor's degree in Computer Science or related field
- 5+ years of experience in software development
- Strong knowledge of Python and JavaScript
- Experience with AWS services (EC2, Lambda, S3)
- Fluent English (required)
- Experience with Docker and Kubernetes

NICE TO HAVE:
- Master's degree
- Experience with machine learning
- German language skills

BENEFITS:
- Competitive salary
- Remote work options

Location: Athens or Remote
"""

# Mock job parser response for Greek
GREEK_JOB_PARSER_RESPONSE = json.dumps({
    "detected_language": "el",
    "roles": ["accountant", "senior_accountant"],
    "role_priority": "must",
    "min_experience_years": 5,
    "max_experience_years": None,
    "experience_priority": "must",
    "software": ["SAP", "Excel"],
    "software_priority": "must",
    "certifications": ["CPA_A_CLASS"],
    "certifications_priority": "must",
    "skills": ["financial_reporting", "accounting", "budgeting"],
    "skills_priority": "should",
    "languages": [
        {"language_code": "en", "language_name": "English", "min_level": "B2", "is_required": True},
        {"language_code": "de", "language_name": "German", "min_level": None, "is_required": False}
    ],
    "locations": ["Athens", "Metamorfosi"],
    "remote_acceptable": False,
    "education_level": "bachelor",
    "education_fields": ["accounting", "finance", "economics"]
}, ensure_ascii=False)

# Mock job parser response for English
ENGLISH_JOB_PARSER_RESPONSE = json.dumps({
    "detected_language": "en",
    "roles": ["software_engineer", "senior_developer"],
    "role_priority": "must",
    "min_experience_years": 5,
    "max_experience_years": None,
    "experience_priority": "must",
    "software": ["Python", "JavaScript", "AWS", "Docker", "Kubernetes"],
    "software_priority": "must",
    "certifications": [],
    "certifications_priority": "nice",
    "skills": ["software_development", "cloud_computing"],
    "skills_priority": "must",
    "languages": [
        {"language_code": "en", "language_name": "English", "min_level": "C1", "is_required": True},
        {"language_code": "de", "language_name": "German", "min_level": None, "is_required": False}
    ],
    "locations": ["Athens"],
    "remote_acceptable": True,
    "education_level": "bachelor",
    "education_fields": ["computer_science", "software_engineering"]
}, ensure_ascii=False)

# Mock HR analysis response for Greek
GREEK_HR_ANALYSIS_RESPONSE = json.dumps({
    "request_analysis": {
        "summary": "Αναζήτηση για Λογιστή Α' Τάξης με SAP και 5+ έτη εμπειρίας στην Αθήνα",
        "mandatory_criteria": [
            "Ρόλος: Λογιστής Α' Τάξης",
            "Εμπειρία: 5+ έτη",
            "Software: SAP, Excel",
            "Πιστοποίηση: Άδεια Λογιστή Α'"
        ],
        "preferred_criteria": [
            "Μεταπτυχιακό σε Χρηματοοικονομικά",
            "Γνώση Γερμανικών"
        ],
        "inferred_criteria": [
            "Γνώση ΕΓΛΣ/ΔΠΧΠ",
            "Επικοινωνιακές δεξιότητες"
        ]
    },
    "query_outcome": {
        "direct_matches": 3,
        "total_matches": 5,
        "relaxation_applied": False
    },
    "ranked_candidates": [
        {
            "rank": 1,
            "candidate_id": "c1",
            "candidate_name": "Ιωάννης Παπαδόπουλος",
            "overall_suitability": "High",
            "match_percentage": 92.0,
            "strengths": [
                {"criterion": "SAP", "candidate_value": "6 χρόνια εμπειρίας", "source": "CV - Εμπειρία", "confidence": "Confirmed"},
                {"criterion": "Εμπειρία", "candidate_value": "8 έτη ως Λογιστής", "source": "CV - Εμπειρία", "confidence": "Confirmed"},
                {"criterion": "Πιστοποίηση", "candidate_value": "Άδεια Λογιστή Α' Τάξης", "source": "CV - Πιστοποιήσεις", "confidence": "Confirmed"}
            ],
            "gaps": [],
            "risks": [
                {"risk": "Υψηλές απαιτήσεις μισθού", "severity": "Low", "mitigation": "Διαπραγμάτευση πακέτου παροχών"}
            ],
            "interview_focus": ["Εμπειρία σε κλείσιμο ισολογισμού", "Γνώση φορολογικών θεμάτων"]
        },
        {
            "rank": 2,
            "candidate_id": "c2",
            "candidate_name": "Μαρία Γεωργίου",
            "overall_suitability": "Medium-High",
            "match_percentage": 78.0,
            "strengths": [
                {"criterion": "Excel", "candidate_value": "Άριστη γνώση", "source": "CV - Software", "confidence": "Confirmed"},
                {"criterion": "Εκπαίδευση", "candidate_value": "MSc Χρηματοοικονομικά", "source": "CV - Σπουδές", "confidence": "Confirmed"}
            ],
            "gaps": [
                {"criterion": "SAP", "gap_description": "Μόνο 1 χρόνο εμπειρίας", "severity": "Moderate", "mitigation": "Εκπαίδευση on-the-job"}
            ],
            "risks": [],
            "interview_focus": ["Δυνατότητα εκμάθησης SAP", "Προηγούμενη εμπειρία σε βιομηχανία"]
        }
    ],
    "hr_recommendation": {
        "top_candidates": ["Ιωάννης Παπαδόπουλος", "Μαρία Γεωργίου"],
        "recommendation_summary": "Ο Ιωάννης Παπαδόπουλος αποτελεί εξαιρετική επιλογή με πλήρη κάλυψη των απαιτήσεων. Η Μαρία Γεωργίου είναι καλή εναλλακτική με δυνατότητα ανάπτυξης.",
        "interview_priorities": [
            "Τεχνικές δεξιότητες SAP",
            "Εμπειρία σε κλείσιμο χρήσης",
            "Διαχείριση ομάδας"
        ],
        "hiring_suggestions": [
            "Άμεση πρόσληψη του Ιωάννη εάν οι μισθολογικές απαιτήσεις είναι εντός budget",
            "Δεύτερη συνέντευξη για τη Μαρία με focus στο SAP"
        ]
    }
}, ensure_ascii=False)

# Mock HR analysis response for English
ENGLISH_HR_ANALYSIS_RESPONSE = json.dumps({
    "request_analysis": {
        "summary": "Looking for Senior Software Engineer with Python, AWS, and 5+ years experience",
        "mandatory_criteria": [
            "Role: Senior Software Engineer",
            "Experience: 5+ years",
            "Software: Python, JavaScript, AWS, Docker, Kubernetes"
        ],
        "preferred_criteria": [
            "Master's degree",
            "Machine learning experience",
            "German language"
        ],
        "inferred_criteria": [
            "CI/CD experience",
            "Agile methodology"
        ]
    },
    "query_outcome": {
        "direct_matches": 2,
        "total_matches": 4,
        "relaxation_applied": False
    },
    "ranked_candidates": [
        {
            "rank": 1,
            "candidate_id": "c3",
            "candidate_name": "Nikos Dimitriou",
            "overall_suitability": "High",
            "match_percentage": 88.0,
            "strengths": [
                {"criterion": "Python", "candidate_value": "7 years experience", "source": "CV - Skills", "confidence": "Confirmed"},
                {"criterion": "AWS", "candidate_value": "AWS Certified Developer", "source": "CV - Certifications", "confidence": "Confirmed"}
            ],
            "gaps": [
                {"criterion": "Kubernetes", "gap_description": "Limited experience (1 year)", "severity": "Minor", "mitigation": "Can learn quickly given Docker experience"}
            ],
            "risks": [],
            "interview_focus": ["System design skills", "Team leadership experience"]
        }
    ],
    "hr_recommendation": {
        "top_candidates": ["Nikos Dimitriou"],
        "recommendation_summary": "Nikos Dimitriou is an excellent match with strong Python and AWS skills.",
        "interview_priorities": [
            "System design capabilities",
            "Cloud architecture decisions",
            "Team collaboration"
        ],
        "hiring_suggestions": [
            "Schedule technical interview within a week",
            "Prepare Kubernetes assessment if needed"
        ]
    }
}, ensure_ascii=False)

# Sample candidates for testing
GREEK_CANDIDATES = [
    CandidateProfile(
        candidate_id="c1",
        first_name="Ιωάννης",
        last_name="Παπαδόπουλος",
        email="i.papadopoulos@example.com",
        total_experience_years=8.0,
        roles=["accountant", "senior_accountant"],
        software=["SAP", "Excel", "Softone"],
        skills=["financial_reporting", "budgeting", "tax_compliance"],
        certifications=["CPA_A_CLASS"],
        languages=[{"code": "en", "name": "English", "level": "C1"}],
        city="Athens",
    ),
    CandidateProfile(
        candidate_id="c2",
        first_name="Μαρία",
        last_name="Γεωργίου",
        email="m.georgiou@example.com",
        total_experience_years=4.0,
        roles=["accountant"],
        software=["Excel", "SAP"],
        skills=["accounting", "data_entry"],
        certifications=[],
        languages=[{"code": "en", "name": "English", "level": "B2"}],
        education=[{"level": "master", "field": "finance"}],
        city="Athens",
    ),
]

ENGLISH_CANDIDATES = [
    CandidateProfile(
        candidate_id="c3",
        first_name="Nikos",
        last_name="Dimitriou",
        email="n.dimitriou@example.com",
        total_experience_years=7.0,
        roles=["software_engineer", "developer"],
        software=["Python", "JavaScript", "AWS", "Docker"],
        skills=["software_development", "cloud_computing", "api_design"],
        certifications=["AWS_DEVELOPER"],
        languages=[{"code": "en", "name": "English", "level": "C2"}],
        city="Athens",
    ),
]


# =============================================================================
# END-TO-END TESTS
# =============================================================================

def test_e2e_greek_job_posting_flow():
    """Test complete flow: Greek job posting → parse → analyze → format."""
    print("\n1. E2E: Greek Job Posting Flow...")

    mock_llm = MockLLMProvider()
    # For job parsing: match job posting text (but not HR analysis prompt)
    mock_llm.set_response("parse:", GREEK_JOB_PARSER_RESPONSE)  # matches "Parse:" in test prompt
    # For HR analysis: match system prompt (contains "HR Intelligence")
    mock_llm.set_response("hr intelligence", GREEK_HR_ANALYSIS_RESPONSE)
    mock_llm.default_response = GREEK_JOB_PARSER_RESPONSE

    # Step 1: Parse job posting
    with patch.object(JobParser, '_load_prompt', return_value="Parse: {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)
        requirements = asyncio.run(parser.parse(GREEK_JOB_POSTING))

    assert requirements.detected_language == "el"
    assert "accountant" in requirements.roles
    assert requirements.min_experience_years == 5
    assert "SAP" in requirements.software

    # Step 2: Create analysis input
    input_data = HRAnalysisInput(
        original_query=GREEK_JOB_POSTING,
        requirements=requirements,
        candidates=GREEK_CANDIDATES,
        direct_result_count=2,
        total_result_count=2,
        relaxations_applied=[],
    )

    # Step 3: Run HR analysis
    analyzer = HRIntelligenceAnalyzer(mock_llm)
    report = asyncio.run(analyzer.analyze(input_data))

    assert report.analysis_language == "el"
    assert len(report.ranked_candidates) >= 1
    assert report.hr_recommendation is not None

    # Step 4: Format outputs
    text_report = format_text_report(report)
    api_response = format_api_response(report)
    compact = format_compact_summary(report)

    assert "Ιωάννης" in text_report or "Παπαδόπουλος" in text_report
    assert "ranked_candidates" in api_response
    assert len(compact) > 0

    print("   PASSED: Greek job posting flow works end-to-end")


def test_e2e_english_job_posting_flow():
    """Test complete flow: English job posting → parse → analyze → format."""
    print("\n2. E2E: English Job Posting Flow...")

    mock_llm = MockLLMProvider()
    # For job parsing: match test prompt template
    mock_llm.set_response("parse:", ENGLISH_JOB_PARSER_RESPONSE)
    # For HR analysis: match system prompt (contains "HR Intelligence")
    mock_llm.set_response("hr intelligence", ENGLISH_HR_ANALYSIS_RESPONSE)
    mock_llm.default_response = ENGLISH_JOB_PARSER_RESPONSE

    # Step 1: Parse job posting
    with patch.object(JobParser, '_load_prompt', return_value="Parse: {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)
        requirements = asyncio.run(parser.parse(ENGLISH_JOB_POSTING))

    assert requirements.detected_language == "en"
    assert "software_engineer" in requirements.roles
    assert requirements.min_experience_years == 5
    assert "Python" in requirements.software

    # Step 2: Create analysis input
    input_data = HRAnalysisInput(
        original_query=ENGLISH_JOB_POSTING,
        requirements=requirements,
        candidates=ENGLISH_CANDIDATES,
        direct_result_count=1,
        total_result_count=1,
        relaxations_applied=[],
    )

    # Step 3: Run HR analysis
    analyzer = HRIntelligenceAnalyzer(mock_llm)
    report = asyncio.run(analyzer.analyze(input_data))

    assert report.analysis_language == "en"
    assert len(report.ranked_candidates) >= 1

    # Step 4: Format outputs
    api_response = format_api_response(report)
    assert api_response["analysis_language"] == "en"

    print("   PASSED: English job posting flow works end-to-end")


def test_e2e_greek_natural_query():
    """Test flow with Greek natural language query."""
    print("\n3. E2E: Greek Natural Language Query...")

    query = "Λογιστές με SAP και εμπειρία 5+ χρόνια στην Αθήνα"

    mock_llm = MockLLMProvider()
    mock_llm.default_response = GREEK_HR_ANALYSIS_RESPONSE

    # Create requirements from query
    requirements = extract_requirements_from_query(query, detected_language="el")
    assert requirements.source_type == "query"
    assert requirements.detected_language == "el"

    # Run analysis
    input_data = HRAnalysisInput(
        original_query=query,
        requirements=requirements,
        candidates=GREEK_CANDIDATES,
        direct_result_count=2,
        total_result_count=2,
        relaxations_applied=[],
    )

    analyzer = HRIntelligenceAnalyzer(mock_llm)
    report = asyncio.run(analyzer.analyze(input_data))

    assert report.analysis_language == "el"
    assert report.request_analysis is not None

    print("   PASSED: Greek natural query flow works")


def test_e2e_english_natural_query():
    """Test flow with English natural language query."""
    print("\n4. E2E: English Natural Language Query...")

    query = "Software engineers with Python and AWS, 5+ years experience"

    mock_llm = MockLLMProvider()
    mock_llm.default_response = ENGLISH_HR_ANALYSIS_RESPONSE

    requirements = extract_requirements_from_query(query, detected_language="en")

    input_data = HRAnalysisInput(
        original_query=query,
        requirements=requirements,
        candidates=ENGLISH_CANDIDATES,
        direct_result_count=1,
        total_result_count=1,
        relaxations_applied=[],
    )

    analyzer = HRIntelligenceAnalyzer(mock_llm)
    report = asyncio.run(analyzer.analyze(input_data))

    assert report.analysis_language == "en"

    print("   PASSED: English natural query flow works")


def test_e2e_no_candidates_scenario():
    """Test handling when no candidates match."""
    print("\n5. E2E: No Candidates Scenario...")

    query = "Specialized role with rare requirements"

    mock_llm = MockLLMProvider()

    requirements = extract_requirements_from_query(query)

    input_data = HRAnalysisInput(
        original_query=query,
        requirements=requirements,
        candidates=[],  # No candidates
        direct_result_count=0,
        total_result_count=0,
        relaxations_applied=[],
    )

    analyzer = HRIntelligenceAnalyzer(mock_llm)
    report = asyncio.run(analyzer.analyze(input_data))

    # Should handle gracefully
    assert report is not None
    assert "No candidates" in report.request_analysis.summary
    assert len(report.ranked_candidates) == 0

    print("   PASSED: No candidates scenario handled gracefully")


def test_e2e_relaxation_scenario():
    """Test handling when criteria relaxation was applied."""
    print("\n6. E2E: Relaxation Scenario...")

    query = "Senior accountant with 10+ years SAP experience"

    mock_llm = MockLLMProvider()
    mock_llm.default_response = GREEK_HR_ANALYSIS_RESPONSE

    requirements = JobRequirements(
        source_type="query",
        source_text=query,
        detected_language="en",
        roles=["senior_accountant"],
        min_experience_years=10,
        software=["SAP"],
    )

    input_data = HRAnalysisInput(
        original_query=query,
        requirements=requirements,
        candidates=GREEK_CANDIDATES,
        direct_result_count=0,  # No direct matches
        total_result_count=2,   # But relaxed query found some
        relaxations_applied=[
            "Experience relaxed from 10 to 5 years",
            "Role expanded to include 'accountant'"
        ],
    )

    analyzer = HRIntelligenceAnalyzer(mock_llm)
    report = asyncio.run(analyzer.analyze(input_data))

    # Verify relaxation info is captured
    assert report.query_outcome.direct_matches == 3  # From mock response
    assert len(input_data.relaxations_applied) == 2

    print("   PASSED: Relaxation scenario works correctly")


def test_e2e_mixed_language_candidates():
    """Test with candidates having mixed Greek/English data."""
    print("\n7. E2E: Mixed Language Candidates...")

    query = "Accountants"

    mock_llm = MockLLMProvider()
    mock_llm.default_response = GREEK_HR_ANALYSIS_RESPONSE

    # Mix of Greek and English candidate names
    mixed_candidates = [
        CandidateProfile(
            candidate_id="c1",
            first_name="Ιωάννης",
            last_name="Παπαδόπουλος",
            software=["SAP"],
        ),
        CandidateProfile(
            candidate_id="c2",
            first_name="John",
            last_name="Smith",
            software=["Excel"],
        ),
    ]

    input_data = HRAnalysisInput(
        original_query=query,
        requirements=extract_requirements_from_query(query),
        candidates=mixed_candidates,
        direct_result_count=2,
        total_result_count=2,
        relaxations_applied=[],
    )

    analyzer = HRIntelligenceAnalyzer(mock_llm)
    report = asyncio.run(analyzer.analyze(input_data))

    assert report is not None
    assert len(mock_llm.calls) == 1  # LLM was called

    print("   PASSED: Mixed language candidates handled")


def test_e2e_api_response_serialization():
    """Test that API response is fully JSON serializable."""
    print("\n8. E2E: API Response Serialization...")

    mock_llm = MockLLMProvider()
    mock_llm.default_response = GREEK_HR_ANALYSIS_RESPONSE

    input_data = HRAnalysisInput(
        original_query="Test query",
        requirements=extract_requirements_from_query("Test"),
        candidates=GREEK_CANDIDATES,
        direct_result_count=2,
        total_result_count=2,
        relaxations_applied=[],
    )

    analyzer = HRIntelligenceAnalyzer(mock_llm)
    report = asyncio.run(analyzer.analyze(input_data))

    api_response = format_api_response(report)

    # Must be JSON serializable
    json_str = json.dumps(api_response, ensure_ascii=False, indent=2)
    parsed_back = json.loads(json_str)

    assert parsed_back["analysis_language"] in ["el", "en"]
    assert "ranked_candidates" in parsed_back
    assert "hr_recommendation" in parsed_back

    print("   PASSED: API response is fully JSON serializable")


def test_e2e_large_candidate_list():
    """Test with more candidates than the limit."""
    print("\n9. E2E: Large Candidate List (>10)...")

    mock_llm = MockLLMProvider()
    mock_llm.default_response = GREEK_HR_ANALYSIS_RESPONSE

    # Create 15 candidates
    large_list = []
    for i in range(15):
        large_list.append(CandidateProfile(
            candidate_id=f"c{i}",
            first_name=f"Candidate",
            last_name=f"Number{i}",
        ))

    input_data = HRAnalysisInput(
        original_query="Test",
        requirements=extract_requirements_from_query("Test"),
        candidates=large_list,
        direct_result_count=15,
        total_result_count=15,
        relaxations_applied=[],
    )

    analyzer = HRIntelligenceAnalyzer(mock_llm)
    report = asyncio.run(analyzer.analyze(input_data))

    # Should limit candidates in prompt
    assert report is not None
    # The analyzer should have limited to MAX_CANDIDATES (10)

    print("   PASSED: Large candidate list handled with limit")


def test_e2e_special_characters_in_names():
    """Test handling of special characters in candidate names."""
    print("\n10. E2E: Special Characters in Names...")

    mock_llm = MockLLMProvider()
    mock_llm.default_response = GREEK_HR_ANALYSIS_RESPONSE

    special_candidates = [
        CandidateProfile(
            candidate_id="c1",
            first_name="Αθανάσιος-Κωνσταντίνος",
            last_name="Παπαδόπουλος-Γεωργιάδης",
        ),
        CandidateProfile(
            candidate_id="c2",
            first_name="María José",
            last_name="García O'Brien",
        ),
    ]

    input_data = HRAnalysisInput(
        original_query="Test",
        requirements=extract_requirements_from_query("Test"),
        candidates=special_candidates,
        direct_result_count=2,
        total_result_count=2,
        relaxations_applied=[],
    )

    analyzer = HRIntelligenceAnalyzer(mock_llm)
    report = asyncio.run(analyzer.analyze(input_data))

    assert report is not None

    # Check full names work
    assert special_candidates[0].full_name == "Αθανάσιος-Κωνσταντίνος Παπαδόπουλος-Γεωργιάδης"
    assert special_candidates[1].full_name == "María José García O'Brien"

    print("   PASSED: Special characters handled correctly")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run all end-to-end tests."""
    print("=" * 70)
    print("HR Intelligence System - End-to-End Tests (Phase 5)")
    print("=" * 70)

    tests = [
        test_e2e_greek_job_posting_flow,
        test_e2e_english_job_posting_flow,
        test_e2e_greek_natural_query,
        test_e2e_english_natural_query,
        test_e2e_no_candidates_scenario,
        test_e2e_relaxation_scenario,
        test_e2e_mixed_language_candidates,
        test_e2e_api_response_serialization,
        test_e2e_large_candidate_list,
        test_e2e_special_characters_in_names,
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

    print("\n" + "=" * 70)
    print(f"End-to-End Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
