"""
Job Posting Parser using Claude Sonnet for structured extraction.

Parses job posting text into JobRequirements format compatible with
HR Intelligence analysis. Supports Greek and English job postings.

See docs/HR-INTELLIGENCE-UNIFIED.md for architecture details.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from ..hr_intelligence.schema import JobRequirements, LanguageRequirement
from ..llm.provider import BedrockProvider, LLMRequest, LLMResponse, ModelType

logger = logging.getLogger(__name__)

# Prompt template location
PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "job_parsing"
DEFAULT_PROMPT_VERSION = "v1.0.0"


class JobParser:
    """
    Job Posting Parser using Claude Sonnet for structured extraction.

    Extracts structured job requirements from unstructured job posting text
    including roles, experience, software, certifications, skills, languages,
    education, and location requirements.

    Example:
        parser = JobParser()
        requirements = await parser.parse(job_posting_text)
    """

    MODEL = ModelType.CLAUDE_SONNET
    MAX_RETRIES = 2
    MAX_TOKENS = 4096

    def __init__(
        self,
        region: str = "eu-north-1",
        prompt_version: str = DEFAULT_PROMPT_VERSION,
        llm_provider: BedrockProvider | None = None,
    ):
        """
        Initialize Job Parser.

        Args:
            region: AWS region for Bedrock
            prompt_version: Prompt template version to use
            llm_provider: Optional BedrockProvider instance (for testing)
        """
        self.provider = llm_provider or BedrockProvider(region=region)
        self.prompt_version = prompt_version
        self._prompt_template: str | None = None

    @property
    def prompt_template(self) -> str:
        """Load prompt template lazily."""
        if self._prompt_template is None:
            self._prompt_template = self._load_prompt()
        return self._prompt_template

    def _load_prompt(self) -> str:
        """
        Load prompt template from file.

        Returns:
            Prompt template string
        """
        # Check environment variable for prompt path
        prompt_path = os.environ.get("JOB_PARSING_PROMPT_PATH")

        if prompt_path:
            path = Path(prompt_path)
            logger.info(f"Using prompt from env var: {path}")
        else:
            path = PROMPTS_DIR / f"{self.prompt_version}.txt"
            logger.info(f"Using prompt from package: {path}")

        if not path.exists():
            raise FileNotFoundError(f"Job parsing prompt not found: {path}")

        return path.read_text(encoding="utf-8")

    async def parse(self, job_posting_text: str) -> JobRequirements:
        """
        Parse job posting text into JobRequirements.

        Args:
            job_posting_text: Raw job posting text (Greek or English)

        Returns:
            JobRequirements object with extracted requirements

        Raises:
            ValueError: If parsing fails
            RuntimeError: If LLM call fails
        """
        if not job_posting_text or not job_posting_text.strip():
            raise ValueError("Job posting text is required")

        # Build prompt with job posting
        prompt = self.prompt_template.replace("{job_posting_text}", job_posting_text)

        # Call LLM
        request = LLMRequest(
            prompt=prompt,
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            temperature=0.1,  # Low temperature for consistent extraction
        )

        logger.info(f"Parsing job posting ({len(job_posting_text)} chars)")

        try:
            response = await self.provider.complete(request)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise RuntimeError(f"Job parsing failed: {e}") from e

        logger.info(
            f"LLM response: {response.input_tokens} input, "
            f"{response.output_tokens} output tokens, "
            f"{response.latency_ms:.0f}ms"
        )

        # Parse response
        try:
            requirements = self._parse_response(response, job_posting_text)
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Raw response: {response.content[:500]}")
            raise ValueError(f"Failed to parse job requirements: {e}") from e

        return requirements

    def _parse_response(
        self, response: LLMResponse, source_text: str
    ) -> JobRequirements:
        """
        Parse LLM response into JobRequirements.

        Args:
            response: LLM response
            source_text: Original job posting text

        Returns:
            JobRequirements object
        """
        content = response.content.strip()

        # Extract JSON from response
        json_data = self._extract_json(content)
        if not json_data:
            raise ValueError("Could not extract JSON from LLM response")

        # Build JobRequirements from parsed data
        return self._build_requirements(json_data, source_text)

    def _extract_json(self, content: str) -> dict[str, Any] | None:
        """
        Extract JSON from LLM response content.

        Handles various formats:
        - Pure JSON
        - JSON wrapped in markdown code blocks
        - JSON with surrounding text
        """
        # Try direct parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to find JSON in markdown code block
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object by braces
        brace_start = content.find("{")
        brace_end = content.rfind("}")
        if brace_start != -1 and brace_end != -1:
            try:
                return json.loads(content[brace_start : brace_end + 1])
            except json.JSONDecodeError:
                pass

        return None

    def _build_requirements(
        self, data: dict[str, Any], source_text: str
    ) -> JobRequirements:
        """
        Build JobRequirements from parsed JSON data.

        Args:
            data: Parsed JSON data
            source_text: Original job posting text

        Returns:
            JobRequirements object
        """
        # Parse language requirements
        languages = []
        for lang_data in data.get("languages", []):
            if isinstance(lang_data, dict):
                languages.append(
                    LanguageRequirement(
                        language_code=lang_data.get("language_code", ""),
                        language_name=lang_data.get("language_name", ""),
                        min_level=lang_data.get("min_level"),
                        is_required=lang_data.get("is_required", True),
                    )
                )

        # Build JobRequirements
        return JobRequirements(
            source_type="job_posting",
            source_text=source_text,
            detected_language=data.get("detected_language", "en"),
            roles=data.get("roles", []),
            role_priority=data.get("role_priority", "must"),
            min_experience_years=data.get("min_experience_years"),
            max_experience_years=data.get("max_experience_years"),
            experience_priority=data.get("experience_priority", "should"),
            software=data.get("software", []),
            software_priority=data.get("software_priority", "should"),
            certifications=data.get("certifications", []),
            certifications_priority=data.get("certifications_priority", "nice"),
            skills=data.get("skills", []),
            skills_priority=data.get("skills_priority", "should"),
            languages=languages,
            locations=data.get("locations", []),
            remote_acceptable=data.get("remote_acceptable", True),
            education_level=data.get("education_level"),
            education_fields=data.get("education_fields", []),
        )


# =============================================================================
# SYNCHRONOUS WRAPPER
# =============================================================================


def parse_job_posting_sync(
    job_posting_text: str,
    region: str = "eu-north-1",
    llm_provider: BedrockProvider | None = None,
) -> JobRequirements:
    """
    Synchronous wrapper for job posting parsing.

    For use in non-async contexts like Lambda handlers.

    Args:
        job_posting_text: Raw job posting text
        region: AWS region for Bedrock
        llm_provider: Optional BedrockProvider instance

    Returns:
        JobRequirements object
    """
    import asyncio

    parser = JobParser(region=region, llm_provider=llm_provider)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(parser.parse(job_posting_text))
    finally:
        loop.close()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def extract_requirements_from_query(
    query_text: str,
    detected_language: str = "en",
) -> JobRequirements:
    """
    Create JobRequirements from a natural language query.

    This is a simple wrapper that creates JobRequirements with source_type="query"
    for queries that have already been translated by the QueryTranslator.

    Args:
        query_text: Original user query
        detected_language: Detected language code

    Returns:
        JobRequirements with source_type="query"
    """
    return JobRequirements(
        source_type="query",
        source_text=query_text,
        detected_language=detected_language,
    )
