"""
Query Translator using Claude Haiku for NL → structured filters.

Translates natural language HR queries (Greek/English) into structured
filters that can be converted to SQL.
"""

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from ..llm.provider import BedrockProvider, LLMRequest, ModelType
from .schema import (
    GREEK_ALIASES,
    LOCATION_ALIASES,
    FilterOperator,
    QueryTranslation,
    QueryType,
    SortDirection,
    SortOrder,
    normalize_greek,
)

logger = logging.getLogger(__name__)

# Prompt template location
PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "prompts" / "query_translation"
DEFAULT_PROMPT_VERSION = "v1.0.0"


class QueryTranslator:
    """
    Query translator using Claude Haiku for fast NL parsing.

    Converts natural language queries like "λογιστής με SAP, 5+ χρόνια, Αθήνα"
    into structured filters that can be converted to SQL.

    Example:
        translator = QueryTranslator()
        result = await translator.translate("λογιστής με Softone, 5+ χρόνια")
    """

    MODEL = ModelType.CLAUDE_HAIKU
    MAX_RETRIES = 2
    MAX_TOKENS = 1024
    RETRY_DELAYS = [0.5, 1.0, 2.0]

    def __init__(
        self,
        region: str = "eu-north-1",
        prompt_version: str = DEFAULT_PROMPT_VERSION,
    ):
        """
        Initialize query translator.

        Args:
            region: AWS region for Bedrock
            prompt_version: Prompt template version to use
        """
        self.provider = BedrockProvider(region=region)
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
        prompt_path = os.environ.get("QUERY_TRANSLATION_PROMPT_PATH")

        if prompt_path:
            path = Path(prompt_path)
        else:
            path = PROMPTS_DIR / f"{self.prompt_version}.txt"

        if path.exists():
            return path.read_text(encoding="utf-8")

        # Fallback to embedded prompt
        logger.warning(f"Prompt file not found: {path}, using embedded prompt")
        return self._get_embedded_prompt()

    def _get_embedded_prompt(self) -> str:
        """Get embedded fallback prompt."""
        return """You are an HR query translator. Convert natural language to JSON filters.

FIELDS: location, experience_years, skill_ids, software_ids, role_ids, education_level, language_codes, driving_licenses

OPERATORS: eq, gte, lte, contains, any, all

OUTPUT: Return ONLY valid JSON:
{
  "query_type": "structured|clarification",
  "confidence": 0.0-1.0,
  "filters": {"field": {"operator": "op", "value": "val"}},
  "unknown_terms": [],
  "clarification_needed": false,
  "clarification_question": null,
  "reasoning": "explanation"
}

QUERY:
"""

    async def translate(
        self,
        user_query: str,
        context: dict[str, Any] | None = None,
    ) -> QueryTranslation:
        """
        Translate natural language query to structured filters.

        Args:
            user_query: User's natural language query
            context: Optional context (previous queries, user preferences)

        Returns:
            QueryTranslation with extracted filters
        """
        logger.info(f"Translating query: {user_query[:100]}...")

        # Normalize query for better matching
        normalized_query = user_query.strip()

        # Build prompt
        prompt = f"{self.prompt_template}\n{normalized_query}"

        # Call Claude Haiku with retries
        raw_json = None
        last_error = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = await self.provider.complete(
                    LLMRequest(
                        prompt=prompt,
                        model=self.MODEL,
                        max_tokens=self.MAX_TOKENS,
                        temperature=0.0,
                    )
                )

                # Extract JSON from response
                raw_json = self._extract_json(response.content)

                if raw_json:
                    logger.info(
                        f"Query translated: "
                        f"tokens_in={response.input_tokens}, "
                        f"tokens_out={response.output_tokens}, "
                        f"latency={response.latency_ms:.0f}ms"
                    )
                    break

            except Exception as e:
                last_error = e
                logger.warning(f"Translation attempt {attempt + 1} failed: {e}")

                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(self.RETRY_DELAYS[attempt])

        # If LLM failed, use regex fallback
        if not raw_json:
            logger.warning("LLM translation failed, using regex fallback")
            return self._regex_fallback(normalized_query, str(last_error))

        # Build QueryTranslation from JSON
        return self._build_translation(raw_json, normalized_query)

    def _extract_json(self, response_text: str) -> dict[str, Any] | None:
        """
        Extract JSON object from Claude response.

        Args:
            response_text: Raw response from Claude

        Returns:
            Parsed JSON dict or None
        """
        # Try direct parse first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Extract from markdown code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object
        brace_match = re.search(r"\{[\s\S]*\}", response_text)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def _build_translation(
        self,
        data: dict[str, Any],
        original_query: str,
    ) -> QueryTranslation:
        """
        Build QueryTranslation from extracted JSON.

        Args:
            data: JSON data from Claude
            original_query: Original user query

        Returns:
            QueryTranslation instance
        """
        # Parse query type
        try:
            query_type = QueryType(data.get("query_type", "structured"))
        except ValueError:
            query_type = QueryType.STRUCTURED

        # Parse sort
        sort = None
        if data.get("sort"):
            sort_data = data["sort"]
            try:
                direction = SortDirection(sort_data.get("direction", "desc"))
            except ValueError:
                direction = SortDirection.DESC
            sort = SortOrder(
                field=sort_data.get("field", "experience_years"),
                direction=direction,
            )

        # Validate and normalize filters
        filters = self._validate_filters(data.get("filters", {}))

        return QueryTranslation(
            query_type=query_type,
            confidence=min(max(data.get("confidence", 0.5), 0.0), 1.0),
            filters=filters,
            unknown_terms=data.get("unknown_terms", []),
            clarification_needed=data.get("clarification_needed", False),
            clarification_question=data.get("clarification_question"),
            clarification_options=data.get("clarification_options", []),
            original_query=original_query,
            sort=sort,
            limit=data.get("limit", 50),
            offset=data.get("offset", 0),
            semantic_query=data.get("semantic_query"),
            reasoning=data.get("reasoning"),
            model_used=self.MODEL.value,
        )

    def _validate_filters(
        self,
        filters: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        """
        Validate and normalize filter structure.

        Args:
            filters: Raw filters from LLM

        Returns:
            Validated filters dict
        """
        validated = {}

        for field, condition in filters.items():
            if not isinstance(condition, dict):
                # Convert simple value to eq condition
                validated[field] = {
                    "operator": FilterOperator.EQ.value,
                    "value": condition,
                }
                continue

            # Validate operator
            operator = condition.get("operator", "eq")
            try:
                FilterOperator(operator)
            except ValueError:
                logger.warning(f"Invalid operator '{operator}' for field '{field}'")
                operator = "eq"

            # Normalize value
            value = condition.get("value")
            if value is not None:
                validated[field] = {
                    "operator": operator,
                    "value": value,
                }

        return validated

    def _regex_fallback(
        self,
        query: str,
        error_msg: str,
    ) -> QueryTranslation:
        """
        Regex-based fallback when LLM fails.

        Args:
            query: Original query
            error_msg: Error message from LLM

        Returns:
            QueryTranslation with basic extraction
        """
        filters = {}
        unknown_terms = []
        query_lower = query.lower()
        query_normalized = normalize_greek(query_lower)

        # Extract experience years
        exp_match = re.search(r"(\d+)\+?\s*(?:χρόνια|years?|ετ[ωη])", query_lower)
        if exp_match:
            filters["experience_years"] = {
                "operator": FilterOperator.GTE.value,
                "value": int(exp_match.group(1)),
            }

        # Extract location
        for alias, canonical in LOCATION_ALIASES.items():
            if alias in query_normalized:
                filters["location"] = {
                    "operator": FilterOperator.CONTAINS.value,
                    "value": canonical,
                }
                break

        # Extract roles from Greek aliases
        role_ids = []
        for alias, canonical_id in GREEK_ALIASES.items():
            if canonical_id.startswith("ROLE_") and alias in query_normalized:
                role_ids.append(canonical_id)

        if role_ids:
            filters["role_ids"] = {
                "operator": FilterOperator.ANY.value,
                "value": role_ids,
            }

        # Extract software from aliases
        software_ids = []
        for alias, canonical_id in GREEK_ALIASES.items():
            if canonical_id.startswith("SW_") and alias in query_normalized:
                software_ids.append(canonical_id)

        if software_ids:
            filters["software_ids"] = {
                "operator": FilterOperator.ANY.value,
                "value": software_ids,
            }

        # Extract skills from aliases
        skill_ids = []
        for alias, canonical_id in GREEK_ALIASES.items():
            if canonical_id.startswith("SKILL_") and alias in query_normalized:
                skill_ids.append(canonical_id)

        if skill_ids:
            filters["skill_ids"] = {
                "operator": FilterOperator.ANY.value,
                "value": skill_ids,
            }

        # Extract driving licenses
        license_match = re.search(
            r"(?:δίπλωμα|άδεια|license).*?([ABCD]\'?|forklift|κλαρκ|γερανός)",
            query_lower,
        )
        if license_match:
            license_val = license_match.group(1).strip("'").upper()
            if "κλαρκ" in license_val.lower() or "forklift" in license_val.lower():
                license_val = "forklift"
            elif "γερανός" in license_val.lower():
                license_val = "crane"
            filters["driving_licenses"] = {
                "operator": FilterOperator.ANY.value,
                "value": [license_val],
            }

        # Calculate confidence based on matches
        confidence = 0.3 + (0.1 * len(filters))
        confidence = min(confidence, 0.7)  # Cap at 0.7 for fallback

        return QueryTranslation(
            query_type=QueryType.STRUCTURED if filters else QueryType.SEMANTIC,
            confidence=confidence,
            filters=filters,
            unknown_terms=unknown_terms,
            clarification_needed=len(filters) == 0,
            clarification_question="Δεν κατάλαβα την αναζήτηση. Μπορείτε να διευκρινίσετε;" if not filters else None,
            original_query=query,
            semantic_query=query if not filters else None,
            reasoning=f"Regex fallback due to LLM error: {error_msg[:100]}",
            model_used="regex_fallback",
        )


# Convenience function for simple usage
async def translate_query(
    user_query: str,
    region: str = "eu-north-1",
    context: dict[str, Any] | None = None,
) -> QueryTranslation:
    """
    Translate natural language query to structured filters.

    Args:
        user_query: User's natural language query
        region: AWS region for Bedrock
        context: Optional context

    Returns:
        QueryTranslation with extracted filters
    """
    translator = QueryTranslator(region=region)
    return await translator.translate(user_query, context)
