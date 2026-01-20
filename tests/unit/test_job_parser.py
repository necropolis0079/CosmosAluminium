"""
Unit tests for Job Posting Parser.

Tests the JobParser class that extracts structured JobRequirements
from unstructured job posting text.
"""

import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Configure encoding for Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from lcmgo_cagenai.hr_intelligence.schema import JobRequirements, LanguageRequirement
from lcmgo_cagenai.llm.provider import LLMResponse
from lcmgo_cagenai.parser.job_parser import (
    JobParser,
    extract_requirements_from_query,
    parse_job_posting_sync,
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


SAMPLE_GREEK_JOB_POSTING = """
ΘΕΣΗ ΕΡΓΑΣΙΑΣ: Λογιστής

Ζητείται Λογιστής Α' Τάξης για λογιστήριο βιομηχανικής εταιρείας.

Απαραίτητα προσόντα:
- Πτυχίο ΑΕΙ/ΤΕΙ Οικονομικής κατεύθυνσης
- Άδεια Λογιστή Α' Τάξης
- Εμπειρία τουλάχιστον 3 ετών σε αντίστοιχη θέση
- Άριστη γνώση SAP ERP
- Πολύ καλή γνώση Excel
- Αγγλικά επίπεδο B2 τουλάχιστον

Επιθυμητά προσόντα:
- Μεταπτυχιακό σε Χρηματοοικονομικά
- Γνώση Γερμανικών

Τοποθεσία: Αθήνα
"""

SAMPLE_ENGLISH_JOB_POSTING = """
JOB TITLE: Senior Software Engineer

We are looking for a Senior Software Engineer to join our team.

Requirements:
- Bachelor's degree in Computer Science or related field
- 5+ years of experience in software development
- Strong knowledge of Python and JavaScript
- Experience with AWS services
- Fluent English (required)

Nice to have:
- Master's degree
- Experience with Docker and Kubernetes
- German language skills

Location: Remote acceptable
"""

VALID_GREEK_RESPONSE = json.dumps({
    "detected_language": "el",
    "roles": ["accountant"],
    "role_priority": "must",
    "min_experience_years": 3,
    "max_experience_years": None,
    "experience_priority": "must",
    "software": ["SAP", "Excel"],
    "software_priority": "must",
    "certifications": ["CPA_A_CLASS"],
    "certifications_priority": "must",
    "skills": ["financial_reporting", "accounting"],
    "skills_priority": "should",
    "languages": [
        {
            "language_code": "en",
            "language_name": "English",
            "min_level": "B2",
            "is_required": True
        },
        {
            "language_code": "de",
            "language_name": "German",
            "min_level": None,
            "is_required": False
        }
    ],
    "locations": ["Athens"],
    "remote_acceptable": False,
    "education_level": "bachelor",
    "education_fields": ["accounting", "finance"]
}, ensure_ascii=False)

VALID_ENGLISH_RESPONSE = json.dumps({
    "detected_language": "en",
    "roles": ["software_engineer"],
    "role_priority": "must",
    "min_experience_years": 5,
    "max_experience_years": None,
    "experience_priority": "must",
    "software": ["Python", "JavaScript", "AWS"],
    "software_priority": "must",
    "certifications": [],
    "certifications_priority": "nice",
    "skills": ["software_development"],
    "skills_priority": "must",
    "languages": [
        {
            "language_code": "en",
            "language_name": "English",
            "min_level": "C1",
            "is_required": True
        },
        {
            "language_code": "de",
            "language_name": "German",
            "min_level": None,
            "is_required": False
        }
    ],
    "locations": [],
    "remote_acceptable": True,
    "education_level": "bachelor",
    "education_fields": ["computer_science"]
}, ensure_ascii=False)


# =============================================================================
# TESTS
# =============================================================================


class TestJobParserInit:
    """Test JobParser initialization."""

    def test_default_init(self):
        """Test default initialization."""
        with patch.object(JobParser, '_load_prompt', return_value="test prompt"):
            parser = JobParser(llm_provider=MockLLMProvider())
            assert parser.prompt_version == "v1.0.0"

    def test_custom_prompt_version(self):
        """Test custom prompt version."""
        with patch.object(JobParser, '_load_prompt', return_value="test prompt"):
            parser = JobParser(prompt_version="v2.0.0", llm_provider=MockLLMProvider())
            assert parser.prompt_version == "v2.0.0"


class TestJobParserParse:
    """Test JobParser.parse method."""

    @pytest.mark.asyncio
    async def test_parse_greek_job_posting(self):
        """Test parsing Greek job posting."""
        mock_llm = MockLLMProvider(VALID_GREEK_RESPONSE)

        with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
            parser = JobParser(llm_provider=mock_llm)
            result = await parser.parse(SAMPLE_GREEK_JOB_POSTING)

        assert isinstance(result, JobRequirements)
        assert result.source_type == "job_posting"
        assert result.detected_language == "el"
        assert "accountant" in result.roles
        assert result.min_experience_years == 3
        assert "SAP" in result.software
        assert len(result.languages) == 2

    @pytest.mark.asyncio
    async def test_parse_english_job_posting(self):
        """Test parsing English job posting."""
        mock_llm = MockLLMProvider(VALID_ENGLISH_RESPONSE)

        with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
            parser = JobParser(llm_provider=mock_llm)
            result = await parser.parse(SAMPLE_ENGLISH_JOB_POSTING)

        assert isinstance(result, JobRequirements)
        assert result.source_type == "job_posting"
        assert result.detected_language == "en"
        assert "software_engineer" in result.roles
        assert result.min_experience_years == 5
        assert result.remote_acceptable is True

    @pytest.mark.asyncio
    async def test_parse_empty_text_raises(self):
        """Test that empty text raises ValueError."""
        mock_llm = MockLLMProvider("{}")

        with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
            parser = JobParser(llm_provider=mock_llm)

            with pytest.raises(ValueError, match="Job posting text is required"):
                await parser.parse("")

            with pytest.raises(ValueError, match="Job posting text is required"):
                await parser.parse("   ")

    @pytest.mark.asyncio
    async def test_parse_stores_source_text(self):
        """Test that original source text is stored."""
        mock_llm = MockLLMProvider(VALID_ENGLISH_RESPONSE)

        with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
            parser = JobParser(llm_provider=mock_llm)
            result = await parser.parse(SAMPLE_ENGLISH_JOB_POSTING)

        assert result.source_text == SAMPLE_ENGLISH_JOB_POSTING


class TestJobParserJsonExtraction:
    """Test JSON extraction from LLM responses."""

    def test_extract_direct_json(self):
        """Test extracting direct JSON."""
        mock_llm = MockLLMProvider()

        with patch.object(JobParser, '_load_prompt', return_value="test"):
            parser = JobParser(llm_provider=mock_llm)

        content = '{"detected_language": "en", "roles": ["test"]}'
        result = parser._extract_json(content)

        assert result is not None
        assert result["detected_language"] == "en"

    def test_extract_json_from_markdown(self):
        """Test extracting JSON from markdown code block."""
        mock_llm = MockLLMProvider()

        with patch.object(JobParser, '_load_prompt', return_value="test"):
            parser = JobParser(llm_provider=mock_llm)

        content = '```json\n{"detected_language": "el"}\n```'
        result = parser._extract_json(content)

        assert result is not None
        assert result["detected_language"] == "el"

    def test_extract_json_with_surrounding_text(self):
        """Test extracting JSON surrounded by text."""
        mock_llm = MockLLMProvider()

        with patch.object(JobParser, '_load_prompt', return_value="test"):
            parser = JobParser(llm_provider=mock_llm)

        content = 'Here is the result: {"roles": ["engineer"]} done.'
        result = parser._extract_json(content)

        assert result is not None
        assert result["roles"] == ["engineer"]

    def test_extract_json_invalid_returns_none(self):
        """Test that invalid JSON returns None."""
        mock_llm = MockLLMProvider()

        with patch.object(JobParser, '_load_prompt', return_value="test"):
            parser = JobParser(llm_provider=mock_llm)

        result = parser._extract_json("not json at all")
        assert result is None


class TestJobParserBuildRequirements:
    """Test building JobRequirements from parsed data."""

    def test_build_with_all_fields(self):
        """Test building with all fields populated."""
        mock_llm = MockLLMProvider()

        with patch.object(JobParser, '_load_prompt', return_value="test"):
            parser = JobParser(llm_provider=mock_llm)

        data = {
            "detected_language": "el",
            "roles": ["accountant", "financial_analyst"],
            "role_priority": "must",
            "min_experience_years": 3,
            "max_experience_years": 7,
            "experience_priority": "should",
            "software": ["SAP", "Excel"],
            "software_priority": "must",
            "certifications": ["CPA"],
            "certifications_priority": "nice",
            "skills": ["budgeting", "reporting"],
            "skills_priority": "should",
            "languages": [
                {
                    "language_code": "en",
                    "language_name": "English",
                    "min_level": "B2",
                    "is_required": True
                }
            ],
            "locations": ["Athens", "Thessaloniki"],
            "remote_acceptable": False,
            "education_level": "master",
            "education_fields": ["finance", "accounting"]
        }

        result = parser._build_requirements(data, "source text")

        assert result.source_type == "job_posting"
        assert result.source_text == "source text"
        assert result.detected_language == "el"
        assert len(result.roles) == 2
        assert result.min_experience_years == 3
        assert result.max_experience_years == 7
        assert len(result.software) == 2
        assert len(result.languages) == 1
        assert result.languages[0].language_code == "en"
        assert result.education_level == "master"

    def test_build_with_minimal_fields(self):
        """Test building with minimal fields."""
        mock_llm = MockLLMProvider()

        with patch.object(JobParser, '_load_prompt', return_value="test"):
            parser = JobParser(llm_provider=mock_llm)

        data = {
            "detected_language": "en"
        }

        result = parser._build_requirements(data, "test")

        assert result.source_type == "job_posting"
        assert result.detected_language == "en"
        assert result.roles == []
        assert result.software == []
        assert result.languages == []
        assert result.remote_acceptable is True  # Default


class TestSyncWrapper:
    """Test synchronous wrapper function."""

    def test_parse_job_posting_sync(self):
        """Test synchronous parsing wrapper."""
        mock_llm = MockLLMProvider(VALID_ENGLISH_RESPONSE)

        with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
            result = parse_job_posting_sync(
                SAMPLE_ENGLISH_JOB_POSTING,
                llm_provider=mock_llm
            )

        assert isinstance(result, JobRequirements)
        assert result.detected_language == "en"


class TestExtractRequirementsFromQuery:
    """Test utility function for query-based requirements."""

    def test_creates_query_type_requirements(self):
        """Test creating requirements from query."""
        result = extract_requirements_from_query(
            "Find accountants with SAP",
            detected_language="en"
        )

        assert result.source_type == "query"
        assert result.source_text == "Find accountants with SAP"
        assert result.detected_language == "en"

    def test_default_language_is_english(self):
        """Test default language."""
        result = extract_requirements_from_query("test query")

        assert result.detected_language == "en"


class TestLanguageRequirementParsing:
    """Test parsing of language requirements."""

    def test_parses_multiple_languages(self):
        """Test parsing multiple language requirements."""
        mock_llm = MockLLMProvider()

        with patch.object(JobParser, '_load_prompt', return_value="test"):
            parser = JobParser(llm_provider=mock_llm)

        data = {
            "detected_language": "el",
            "languages": [
                {
                    "language_code": "en",
                    "language_name": "English",
                    "min_level": "B2",
                    "is_required": True
                },
                {
                    "language_code": "de",
                    "language_name": "German",
                    "min_level": "A2",
                    "is_required": False
                },
                {
                    "language_code": "fr",
                    "language_name": "French",
                    "min_level": None,
                    "is_required": False
                }
            ]
        }

        result = parser._build_requirements(data, "test")

        assert len(result.languages) == 3
        assert result.languages[0].language_code == "en"
        assert result.languages[0].is_required is True
        assert result.languages[1].language_code == "de"
        assert result.languages[1].is_required is False
        assert result.languages[2].min_level is None

    def test_handles_empty_languages(self):
        """Test handling empty languages list."""
        mock_llm = MockLLMProvider()

        with patch.object(JobParser, '_load_prompt', return_value="test"):
            parser = JobParser(llm_provider=mock_llm)

        data = {
            "detected_language": "en",
            "languages": []
        }

        result = parser._build_requirements(data, "test")

        assert result.languages == []


class TestJobRequirementsToDict:
    """Test JobRequirements serialization."""

    def test_to_dict_complete(self):
        """Test full serialization."""
        req = JobRequirements(
            source_type="job_posting",
            source_text="Test posting",
            detected_language="el",
            roles=["accountant"],
            software=["SAP"],
            languages=[
                LanguageRequirement(
                    language_code="en",
                    language_name="English",
                    min_level="B2",
                    is_required=True
                )
            ]
        )

        d = req.to_dict()

        assert d["source_type"] == "job_posting"
        assert d["detected_language"] == "el"
        assert "accountant" in d["roles"]
        assert len(d["languages"]) == 1
        assert d["languages"][0]["language_code"] == "en"
