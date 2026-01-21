"""
HR Intelligence Analyzer - Main analysis logic.

This module provides the core HRIntelligenceAnalyzer class that transforms
candidate query results into actionable HR insights using Claude Sonnet.

See docs/HR-INTELLIGENCE-UNIFIED.md for full specification.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

from ..llm.provider import BedrockProvider, LLMRequest, LLMResponse, ModelType
from .prompts import RESPONSE_SCHEMA, build_analysis_prompt, get_user_message
from .schema import (
    CandidateProfile,
    HRAnalysisInput,
    HRAnalysisReport,
    JobRequirements,
    QueryOutcome,
    RequestAnalysis,
    parse_hr_analysis_from_json,
)

logger = logging.getLogger(__name__)


class HRIntelligenceAnalyzer:
    """
    HR Intelligence Analyzer that evaluates, compares, and ranks candidates.

    Uses Claude Sonnet 4.5 to transform raw query results into actionable
    HR insights with structured analysis, comparison, ranking, and
    recommendations.

    Example:
        llm = BedrockProvider()
        analyzer = HRIntelligenceAnalyzer(llm)

        report = await analyzer.analyze(HRAnalysisInput(
            original_query="Λογιστές με SAP",
            requirements=job_requirements,
            candidates=candidate_list,
            direct_result_count=0,
            total_result_count=5,
        ))

        print(report.to_dict())
    """

    # Greek character patterns for language detection
    GREEK_PATTERN = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF]")

    def __init__(
        self,
        llm_provider: BedrockProvider,
        model: ModelType = ModelType.CLAUDE_SONNET,
        max_candidates: int = 10,
    ):
        """
        Initialize the HR Intelligence Analyzer.

        Args:
            llm_provider: BedrockProvider instance for LLM calls
            model: Model to use (default: Claude Sonnet 4.5)
            max_candidates: Maximum candidates to analyze (default: 10)
        """
        self.llm = llm_provider
        self.model = model
        self.max_candidates = max_candidates

    async def analyze(self, input_data: HRAnalysisInput) -> HRAnalysisReport:
        """
        Perform HR intelligence analysis on candidates.

        Args:
            input_data: HRAnalysisInput with query, requirements, and candidates

        Returns:
            HRAnalysisReport with full analysis

        Raises:
            ValueError: If input validation fails
            RuntimeError: If LLM call fails
        """
        start_time = time.time()

        # Validate input
        self._validate_input(input_data)

        # Detect language from original query
        language = self._detect_language(input_data.original_query)
        logger.info(f"Detected language: {language}")

        # Limit candidates to max
        candidates_to_analyze = input_data.candidates[: self.max_candidates]
        if len(input_data.candidates) > self.max_candidates:
            logger.warning(
                f"Limiting analysis to {self.max_candidates} candidates "
                f"(received {len(input_data.candidates)})"
            )

        # Handle empty candidates case
        if not candidates_to_analyze:
            return self._create_empty_report(input_data, language, start_time)

        # Build prompt
        system_prompt = self._build_prompt(
            input_data.requirements,
            candidates_to_analyze,
            input_data.direct_result_count,
            len(candidates_to_analyze),
            input_data.direct_result_count == 0 and len(input_data.relaxations_applied) > 0,
            language,
        )

        user_message = get_user_message(input_data.original_query, language)

        # Call LLM
        try:
            response = await self._call_llm(system_prompt, user_message)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise RuntimeError(f"HR analysis failed: {e}") from e

        # Parse response
        try:
            report = self._parse_response(response, language)
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.warning(f"Raw response (first 2000 chars): {response.content[:2000]}")
            # Return fallback report instead of failing
            logger.info("Using fallback report due to parse failure")
            report = self._create_fallback_report(
                input_data, candidates_to_analyze, language, start_time, str(e)
            )

        # Add metadata
        report.analysis_language = language
        report.analysis_timestamp = datetime.now(timezone.utc)
        report.llm_model = self.model.value
        report.latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"HR analysis completed in {report.latency_ms}ms, "
            f"ranked {len(report.ranked_candidates)} candidates"
        )

        return report

    def _validate_input(self, input_data: HRAnalysisInput) -> None:
        """Validate input data."""
        if not input_data.original_query:
            raise ValueError("original_query is required")
        if not input_data.requirements:
            raise ValueError("requirements is required")

    def _detect_language(self, text: str) -> str:
        """
        Detect language from text.

        Args:
            text: Input text to analyze

        Returns:
            "el" for Greek, "en" for English
        """
        # Count Greek characters
        greek_chars = len(self.GREEK_PATTERN.findall(text))
        total_alpha = sum(1 for c in text if c.isalpha())

        if total_alpha == 0:
            return "en"  # Default to English for non-alphabetic

        greek_ratio = greek_chars / total_alpha

        # If more than 30% Greek characters, treat as Greek
        return "el" if greek_ratio > 0.3 else "en"

    def _build_prompt(
        self,
        requirements: JobRequirements,
        candidates: list[CandidateProfile],
        direct_count: int,
        total_count: int,
        relaxation_applied: bool,
        language: str,
    ) -> str:
        """Build the system prompt with all data."""
        # Convert requirements to JSON
        requirements_json = json.dumps(requirements.to_dict(), ensure_ascii=False, indent=2)

        # Convert candidates to JSON
        candidates_data = [c.to_dict() for c in candidates]
        candidates_json = json.dumps(candidates_data, ensure_ascii=False, indent=2)

        return build_analysis_prompt(
            requirements_json=requirements_json,
            candidates_json=candidates_json,
            direct_count=direct_count,
            total_count=total_count,
            relaxation_applied=relaxation_applied,
            language=language,
        )

    async def _call_llm(self, system_prompt: str, user_message: str) -> LLMResponse:
        """Make the LLM API call."""
        request = LLMRequest(
            prompt=user_message,
            model=self.model,
            max_tokens=8192,  # Large output for detailed analysis
            temperature=0.1,  # Low temperature for consistency
            system=system_prompt,
        )

        logger.debug(f"Calling LLM with {len(system_prompt)} char system prompt")

        response = await self.llm.complete(request)

        logger.info(
            f"LLM response: {response.input_tokens} input, "
            f"{response.output_tokens} output tokens, "
            f"{response.latency_ms:.0f}ms"
        )

        return response

    def _parse_response(self, response: LLMResponse, language: str) -> HRAnalysisReport:
        """Parse LLM response into HRAnalysisReport."""
        content = response.content.strip()

        # Try to extract JSON from response
        json_data = self._extract_json(content)

        if not json_data:
            raise ValueError("Could not extract JSON from LLM response")

        # Parse into report
        report = parse_hr_analysis_from_json(json_data)

        return report

    def _extract_json(self, content: str) -> dict[str, Any] | None:
        """
        Extract JSON from LLM response content.

        Handles various formats:
        - Pure JSON
        - JSON wrapped in markdown code blocks
        - JSON with surrounding text
        - JSON with common formatting issues
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
                # Try to repair and parse
                repaired = self._repair_json(json_match.group(1))
                if repaired:
                    return repaired

        # Try to find JSON object by braces
        brace_start = content.find("{")
        brace_end = content.rfind("}")
        if brace_start != -1 and brace_end != -1:
            json_str = content[brace_start : brace_end + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Try to repair and parse
                repaired = self._repair_json(json_str)
                if repaired:
                    return repaired

        return None

    def _repair_json(self, json_str: str) -> dict[str, Any] | None:
        """
        Attempt to repair common JSON formatting issues.
        """
        try:
            # Remove trailing commas before ] or }
            repaired = re.sub(r',\s*([}\]])', r'\1', json_str)
            # Remove control characters except newlines and tabs
            repaired = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', repaired)
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

        try:
            # More aggressive: try to extract just the outer object
            # Find balanced braces
            depth = 0
            start = None
            for i, c in enumerate(json_str):
                if c == '{':
                    if depth == 0:
                        start = i
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0 and start is not None:
                        try:
                            return json.loads(json_str[start:i+1])
                        except json.JSONDecodeError:
                            pass
        except Exception:
            pass

        return None

    def _create_empty_report(
        self,
        input_data: HRAnalysisInput,
        language: str,
        start_time: float,
    ) -> HRAnalysisReport:
        """Create report for empty candidates case."""
        if language == "el":
            summary = "Δεν βρέθηκαν υποψήφιοι που να ταιριάζουν με τα κριτήρια"
            no_results_reason = "Δεν υπάρχουν υποψήφιοι στη βάση που να ταιριάζουν με τα κριτήρια αναζήτησης"
            recommendation = "Δοκιμάστε να χαλαρώσετε τα κριτήρια αναζήτησης ή να αναζητήσετε με διαφορετικούς όρους"
        else:
            summary = "No candidates found matching the criteria"
            no_results_reason = "No candidates in the database match the search criteria"
            recommendation = "Try relaxing the search criteria or searching with different terms"

        return HRAnalysisReport(
            request_analysis=RequestAnalysis(
                summary=summary,
                mandatory_criteria=[],
                preferred_criteria=[],
                inferred_criteria=[],
            ),
            query_outcome=QueryOutcome(
                direct_matches=0,
                total_matches=0,
                relaxation_applied=False,
                zero_results_reason=no_results_reason,
            ),
            criteria_expansion=None,
            ranked_candidates=[],
            hr_recommendation=input_data.requirements and self._build_empty_recommendation(
                recommendation, language
            ),
            analysis_language=language,
            analysis_timestamp=datetime.now(timezone.utc),
            llm_model=self.model.value,
            latency_ms=int((time.time() - start_time) * 1000),
        )

    def _create_fallback_report(
        self,
        input_data: HRAnalysisInput,
        candidates: list[CandidateProfile],
        language: str,
        start_time: float,
        error_msg: str,
    ) -> HRAnalysisReport:
        """Create a fallback report when LLM response parsing fails."""
        from .schema import HRRecommendation, RankedCandidate, CandidateEvaluation

        if language == "el":
            summary = f"Βρέθηκαν {len(candidates)} υποψήφιοι (απλοποιημένη ανάλυση)"
            note = "Σημείωση: Η λεπτομερής ανάλυση δεν ήταν διαθέσιμη"
        else:
            summary = f"Found {len(candidates)} candidates (simplified analysis)"
            note = "Note: Detailed analysis was not available"

        # Create basic ranked candidates from the input
        ranked = []
        for i, candidate in enumerate(candidates[:5]):  # Top 5
            ranked.append(RankedCandidate(
                rank=i + 1,
                candidate_id=candidate.candidate_id,
                name=candidate.name,
                suitability="Μέτρια" if language == "el" else "Medium",
                evaluation=CandidateEvaluation(
                    strengths=[],
                    gaps=[],
                    overall_comment=note,
                ),
                match_score=50,  # Default score
            ))

        return HRAnalysisReport(
            request_analysis=RequestAnalysis(
                summary=summary,
                mandatory_criteria=[],
                preferred_criteria=[],
                inferred_criteria=[],
            ),
            query_outcome=QueryOutcome(
                direct_matches=input_data.direct_result_count,
                total_matches=len(candidates),
                relaxation_applied=len(input_data.relaxations_applied) > 0,
                zero_results_reason=None,
            ),
            criteria_expansion=None,
            ranked_candidates=ranked,
            hr_recommendation=HRRecommendation(
                top_candidates=[c.name for c in candidates[:3]],
                recommendation_summary=summary,
                interview_priorities=[],
                hiring_suggestions=[note],
                alternative_search=None,
            ),
            analysis_language=language,
            analysis_timestamp=datetime.now(timezone.utc),
            llm_model=self.model.value,
            latency_ms=int((time.time() - start_time) * 1000),
        )

    def _build_empty_recommendation(self, summary: str, language: str) -> Any:
        """Build recommendation for empty results."""
        from .schema import HRRecommendation

        if language == "el":
            return HRRecommendation(
                top_candidates=[],
                recommendation_summary=summary,
                interview_priorities=[],
                hiring_suggestions=[
                    "Επεκτείνετε τα κριτήρια αναζήτησης",
                    "Εξετάστε υποψηφίους με μεταφερόμενες δεξιότητες",
                ],
                alternative_search="Δοκιμάστε αναζήτηση με λιγότερα κριτήρια",
            )
        else:
            return HRRecommendation(
                top_candidates=[],
                recommendation_summary=summary,
                interview_priorities=[],
                hiring_suggestions=[
                    "Expand search criteria",
                    "Consider candidates with transferable skills",
                ],
                alternative_search="Try searching with fewer criteria",
            )


# =============================================================================
# SYNCHRONOUS WRAPPER
# =============================================================================


def analyze_candidates_sync(
    llm_provider: BedrockProvider,
    original_query: str,
    requirements: JobRequirements,
    candidates: list[CandidateProfile],
    direct_result_count: int = 0,
    relaxations_applied: list[str] | None = None,
) -> HRAnalysisReport:
    """
    Synchronous wrapper for HR analysis.

    For use in non-async contexts like Lambda handlers.

    Args:
        llm_provider: BedrockProvider instance
        original_query: User's original query
        requirements: JobRequirements object
        candidates: List of CandidateProfile objects
        direct_result_count: Number of direct matches
        relaxations_applied: List of relaxed criteria

    Returns:
        HRAnalysisReport
    """
    import asyncio

    analyzer = HRIntelligenceAnalyzer(llm_provider)

    input_data = HRAnalysisInput(
        original_query=original_query,
        requirements=requirements,
        candidates=candidates,
        direct_result_count=direct_result_count,
        total_result_count=len(candidates),
        relaxations_applied=relaxations_applied or [],
    )

    # Run async in sync context
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(analyzer.analyze(input_data))
    finally:
        loop.close()
