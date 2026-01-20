"""
Comprehensive code path verification tests for Job Posting Parser.

Tests edge cases, error handling, and all code branches.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

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

    def __init__(self, response_content: str = "{}", should_fail: bool = False):
        self.response_content = response_content
        self.should_fail = should_fail
        self.calls = []

    async def complete(self, request):
        self.calls.append(request)
        if self.should_fail:
            raise Exception("LLM API Error")
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

MINIMAL_VALID_RESPONSE = json.dumps({
    "detected_language": "en",
    "roles": [],
    "software": [],
    "certifications": [],
    "skills": [],
    "languages": [],
    "locations": [],
    "education_fields": []
}, ensure_ascii=False)

FULL_GREEK_RESPONSE = json.dumps({
    "detected_language": "el",
    "roles": ["accountant", "financial_analyst"],
    "role_priority": "must",
    "min_experience_years": 5,
    "max_experience_years": 10,
    "experience_priority": "must",
    "software": ["SAP", "Excel", "Softone"],
    "software_priority": "must",
    "certifications": ["CPA", "ACCA"],
    "certifications_priority": "should",
    "skills": ["financial_reporting", "budgeting", "tax_compliance"],
    "skills_priority": "should",
    "languages": [
        {"language_code": "en", "language_name": "English", "min_level": "C1", "is_required": True},
        {"language_code": "de", "language_name": "German", "min_level": "B1", "is_required": False}
    ],
    "locations": ["Athens", "Thessaloniki"],
    "remote_acceptable": False,
    "education_level": "master",
    "education_fields": ["accounting", "finance", "economics"]
}, ensure_ascii=False)

MALFORMED_JSON_RESPONSE = "This is not JSON at all"

JSON_IN_MARKDOWN_RESPONSE = """
Here is the extracted data:

```json
{
  "detected_language": "en",
  "roles": ["engineer"],
  "software": ["Python"]
}
```

That's all the requirements found.
"""

JSON_WITH_TEXT_RESPONSE = """
After analyzing the job posting, I found:
{"detected_language": "el", "roles": ["developer"], "software": ["Java"]}
These are the main requirements.
"""


# =============================================================================
# TESTS
# =============================================================================


def test_prompt_template_loading():
    """Test that prompt template loads correctly."""
    print("\n1. Testing prompt template loading...")

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=MockLLMProvider())
        template = parser.prompt_template

        assert "{job_posting_text}" in template
        print("   PASSED: Prompt template loads correctly")


def test_prompt_template_caching():
    """Test that prompt template is cached after first load."""
    print("\n2. Testing prompt template caching...")

    load_count = 0

    def mock_load(self):
        nonlocal load_count
        load_count += 1
        return "cached template {job_posting_text}"

    with patch.object(JobParser, '_load_prompt', mock_load):
        parser = JobParser(llm_provider=MockLLMProvider())

        # Access template multiple times
        _ = parser.prompt_template
        _ = parser.prompt_template
        _ = parser.prompt_template

        assert load_count == 1
        print("   PASSED: Prompt template is cached (loaded once)")


def test_parse_with_minimal_response():
    """Test parsing with minimal valid response."""
    print("\n3. Testing parse with minimal response...")

    mock_llm = MockLLMProvider(MINIMAL_VALID_RESPONSE)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)
        result = asyncio.run(parser.parse("Simple job posting"))

    assert result.source_type == "job_posting"
    assert result.detected_language == "en"
    assert result.roles == []
    assert result.software == []
    print("   PASSED: Minimal response parsed correctly")


def test_parse_with_full_greek_response():
    """Test parsing with complete Greek job posting response."""
    print("\n4. Testing parse with full Greek response...")

    mock_llm = MockLLMProvider(FULL_GREEK_RESPONSE)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)
        result = asyncio.run(parser.parse("Greek job posting text"))

    assert result.detected_language == "el"
    assert len(result.roles) == 2
    assert result.min_experience_years == 5
    assert result.max_experience_years == 10
    assert len(result.software) == 3
    assert len(result.certifications) == 2
    assert len(result.languages) == 2
    assert result.languages[0].min_level == "C1"
    assert result.education_level == "master"
    print("   PASSED: Full Greek response parsed correctly")


def test_parse_with_json_in_markdown():
    """Test parsing JSON embedded in markdown code block."""
    print("\n5. Testing parse with JSON in markdown...")

    mock_llm = MockLLMProvider(JSON_IN_MARKDOWN_RESPONSE)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)
        result = asyncio.run(parser.parse("Job posting"))

    assert result.detected_language == "en"
    assert "engineer" in result.roles
    assert "Python" in result.software
    print("   PASSED: JSON in markdown extracted correctly")


def test_parse_with_json_surrounded_by_text():
    """Test parsing JSON surrounded by explanatory text."""
    print("\n6. Testing parse with JSON surrounded by text...")

    mock_llm = MockLLMProvider(JSON_WITH_TEXT_RESPONSE)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)
        result = asyncio.run(parser.parse("Job posting"))

    assert result.detected_language == "el"
    assert "developer" in result.roles
    print("   PASSED: JSON with surrounding text extracted correctly")


def test_parse_with_malformed_json():
    """Test parsing fails gracefully with malformed JSON."""
    print("\n7. Testing parse with malformed JSON...")

    mock_llm = MockLLMProvider(MALFORMED_JSON_RESPONSE)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)

        try:
            asyncio.run(parser.parse("Job posting"))
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Failed to parse" in str(e) or "Could not extract" in str(e)

    print("   PASSED: Malformed JSON raises ValueError")


def test_parse_with_llm_failure():
    """Test parsing handles LLM API failure."""
    print("\n8. Testing parse with LLM failure...")

    mock_llm = MockLLMProvider(should_fail=True)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)

        try:
            asyncio.run(parser.parse("Job posting"))
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "Job parsing failed" in str(e)

    print("   PASSED: LLM failure raises RuntimeError")


def test_parse_with_empty_string():
    """Test parsing rejects empty string."""
    print("\n9. Testing parse with empty string...")

    mock_llm = MockLLMProvider(MINIMAL_VALID_RESPONSE)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)

        try:
            asyncio.run(parser.parse(""))
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "required" in str(e).lower()

    print("   PASSED: Empty string raises ValueError")


def test_parse_with_whitespace_only():
    """Test parsing rejects whitespace-only string."""
    print("\n10. Testing parse with whitespace only...")

    mock_llm = MockLLMProvider(MINIMAL_VALID_RESPONSE)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)

        try:
            asyncio.run(parser.parse("   \n\t  "))
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "required" in str(e).lower()

    print("   PASSED: Whitespace-only string raises ValueError")


def test_llm_receives_job_posting_text():
    """Test that LLM receives the job posting text in prompt."""
    print("\n11. Testing LLM receives job posting text...")

    mock_llm = MockLLMProvider(MINIMAL_VALID_RESPONSE)
    job_text = "Senior Developer needed with Python skills"

    with patch.object(JobParser, '_load_prompt', return_value="PROMPT: {job_posting_text} END"):
        parser = JobParser(llm_provider=mock_llm)
        asyncio.run(parser.parse(job_text))

    assert len(mock_llm.calls) == 1
    assert job_text in mock_llm.calls[0].prompt
    print("   PASSED: LLM receives job posting in prompt")


def test_source_text_preserved():
    """Test that original source text is preserved in result."""
    print("\n12. Testing source text preservation...")

    mock_llm = MockLLMProvider(MINIMAL_VALID_RESPONSE)
    original_text = "Original job posting with special chars: @#$%"

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)
        result = asyncio.run(parser.parse(original_text))

    assert result.source_text == original_text
    print("   PASSED: Source text preserved correctly")


def test_default_values_when_fields_missing():
    """Test default values when LLM response misses fields."""
    print("\n13. Testing default values for missing fields...")

    sparse_response = json.dumps({
        "detected_language": "en"
        # All other fields missing
    })

    mock_llm = MockLLMProvider(sparse_response)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)
        result = asyncio.run(parser.parse("Job posting"))

    # Check defaults
    assert result.roles == []
    assert result.role_priority == "must"  # Default
    assert result.min_experience_years is None
    assert result.software == []
    assert result.software_priority == "should"  # Default
    assert result.certifications_priority == "nice"  # Default
    assert result.remote_acceptable is True  # Default
    assert result.languages == []
    print("   PASSED: Default values applied correctly")


def test_language_requirement_parsing():
    """Test detailed language requirement parsing."""
    print("\n14. Testing language requirement parsing...")

    response = json.dumps({
        "detected_language": "el",
        "languages": [
            {"language_code": "en", "language_name": "English", "min_level": "C2", "is_required": True},
            {"language_code": "de", "language_name": "German", "min_level": None, "is_required": False},
            {"language_code": "fr", "language_name": "French"}  # Missing fields
        ]
    })

    mock_llm = MockLLMProvider(response)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)
        result = asyncio.run(parser.parse("Job posting"))

    assert len(result.languages) == 3

    # First language - all fields
    assert result.languages[0].language_code == "en"
    assert result.languages[0].min_level == "C2"
    assert result.languages[0].is_required is True

    # Second language - explicit None
    assert result.languages[1].min_level is None
    assert result.languages[1].is_required is False

    # Third language - missing fields use defaults
    assert result.languages[2].language_code == "fr"
    assert result.languages[2].is_required is True  # Default

    print("   PASSED: Language requirements parsed correctly")


def test_sync_wrapper_function():
    """Test synchronous wrapper function."""
    print("\n15. Testing synchronous wrapper...")

    mock_llm = MockLLMProvider(FULL_GREEK_RESPONSE)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        result = parse_job_posting_sync("Job posting", llm_provider=mock_llm)

    assert isinstance(result, JobRequirements)
    assert result.detected_language == "el"
    print("   PASSED: Sync wrapper works correctly")


def test_extract_requirements_from_query():
    """Test query-based requirements creation."""
    print("\n16. Testing extract_requirements_from_query...")

    result = extract_requirements_from_query(
        "Find accountants with SAP experience",
        detected_language="en"
    )

    assert result.source_type == "query"
    assert result.source_text == "Find accountants with SAP experience"
    assert result.detected_language == "en"
    # Other fields should be empty/default
    assert result.roles == []
    assert result.software == []
    print("   PASSED: Query requirements created correctly")


def test_extract_requirements_greek_query():
    """Test query-based requirements with Greek."""
    print("\n17. Testing extract_requirements_from_query (Greek)...")

    result = extract_requirements_from_query(
        "Logistes me SAP",
        detected_language="el"
    )

    assert result.source_type == "query"
    assert result.detected_language == "el"
    print("   PASSED: Greek query requirements created correctly")


def test_job_requirements_to_dict():
    """Test JobRequirements serialization."""
    print("\n18. Testing JobRequirements.to_dict()...")

    mock_llm = MockLLMProvider(FULL_GREEK_RESPONSE)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)
        result = asyncio.run(parser.parse("Job posting"))

    d = result.to_dict()

    assert d["source_type"] == "job_posting"
    assert d["detected_language"] == "el"
    assert len(d["roles"]) == 2
    assert len(d["languages"]) == 2
    assert d["languages"][0]["language_code"] == "en"
    assert "weights" in d
    print("   PASSED: to_dict() serialization works")


def test_json_extraction_edge_cases():
    """Test JSON extraction with various edge cases."""
    print("\n19. Testing JSON extraction edge cases...")

    mock_llm = MockLLMProvider()

    with patch.object(JobParser, '_load_prompt', return_value="test"):
        parser = JobParser(llm_provider=mock_llm)

    # Nested braces
    content = '{"roles": ["test"], "data": {"nested": true}}'
    result = parser._extract_json(content)
    assert result is not None
    assert result["roles"] == ["test"]

    # Empty object
    content = '{}'
    result = parser._extract_json(content)
    assert result == {}

    # Markdown without json tag
    content = '```\n{"key": "value"}\n```'
    result = parser._extract_json(content)
    assert result == {"key": "value"}

    # JSON with newlines
    content = '{\n  "roles": ["developer"],\n  "software": ["Python"]\n}'
    result = parser._extract_json(content)
    assert result is not None
    assert result["roles"] == ["developer"]

    # JSON with unicode
    content = '{"roles": ["Logistis"], "location": "Athens"}'
    result = parser._extract_json(content)
    assert result is not None
    assert result["location"] == "Athens"

    print("   PASSED: JSON extraction handles edge cases")


def test_priority_field_defaults():
    """Test that priority fields have correct defaults."""
    print("\n20. Testing priority field defaults...")

    response = json.dumps({
        "detected_language": "en",
        "roles": ["developer"]
        # All priority fields missing
    })

    mock_llm = MockLLMProvider(response)

    with patch.object(JobParser, '_load_prompt', return_value="test {job_posting_text}"):
        parser = JobParser(llm_provider=mock_llm)
        result = asyncio.run(parser.parse("Job posting"))

    assert result.role_priority == "must"
    assert result.experience_priority == "should"
    assert result.software_priority == "should"
    assert result.certifications_priority == "nice"
    assert result.skills_priority == "should"
    print("   PASSED: Priority defaults are correct")


def main():
    """Run all code path verification tests."""
    print("=" * 60)
    print("Job Parser - Code Path Verification Tests")
    print("=" * 60)

    tests = [
        test_prompt_template_loading,
        test_prompt_template_caching,
        test_parse_with_minimal_response,
        test_parse_with_full_greek_response,
        test_parse_with_json_in_markdown,
        test_parse_with_json_surrounded_by_text,
        test_parse_with_malformed_json,
        test_parse_with_llm_failure,
        test_parse_with_empty_string,
        test_parse_with_whitespace_only,
        test_llm_receives_job_posting_text,
        test_source_text_preserved,
        test_default_values_when_fields_missing,
        test_language_requirement_parsing,
        test_sync_wrapper_function,
        test_extract_requirements_from_query,
        test_extract_requirements_greek_query,
        test_job_requirements_to_dict,
        test_json_extraction_edge_cases,
        test_priority_field_defaults,
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
