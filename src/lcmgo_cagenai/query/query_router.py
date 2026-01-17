"""
Query Router - Routes queries based on confidence and type.

Determines whether to use SQL, vector search, or request clarification
based on the translation confidence and query type.
"""

import logging
from typing import Any

from .query_translator import QueryTranslator
from .schema import (
    QueryTranslation,
    QueryType,
    RouteResult,
    SQLQuery,
)
from .sql_generator import SQLGenerator

logger = logging.getLogger(__name__)


class QueryRouter:
    """
    Routes natural language queries to appropriate handlers.

    Confidence thresholds:
    - >= 0.8: High confidence, proceed with SQL
    - 0.5-0.8: Moderate confidence, proceed with warning
    - < 0.5: Low confidence, request clarification

    Example:
        router = QueryRouter()
        result = await router.route("λογιστής με SAP, 5+ χρόνια")
        if result.query_type == QueryType.STRUCTURED:
            # Execute SQL
            execute(result.sql_query.query, result.sql_query.params)
        elif result.query_type == QueryType.CLARIFICATION:
            # Ask user for clarification
            ask_user(result.translation.clarification_question)
    """

    # Confidence thresholds
    HIGH_CONFIDENCE = 0.8
    MODERATE_CONFIDENCE = 0.5

    def __init__(
        self,
        region: str = "eu-north-1",
        translator: QueryTranslator | None = None,
        sql_generator: SQLGenerator | None = None,
    ):
        """
        Initialize query router.

        Args:
            region: AWS region for Bedrock
            translator: Optional pre-configured translator
            sql_generator: Optional pre-configured SQL generator
        """
        self.region = region
        self.translator = translator or QueryTranslator(region=region)
        self.sql_generator = sql_generator or SQLGenerator()

    async def route(
        self,
        user_query: str,
        context: dict[str, Any] | None = None,
    ) -> RouteResult:
        """
        Route a natural language query.

        Args:
            user_query: User's natural language query
            context: Optional context (previous queries, preferences)

        Returns:
            RouteResult with routing decision and query/translation
        """
        logger.info(f"Routing query: {user_query[:100]}...")

        # Translate query
        translation = await self.translator.translate(user_query, context)

        # Route based on translation
        return self._route_translation(translation)

    def _route_translation(self, translation: QueryTranslation) -> RouteResult:
        """
        Route based on translation result.

        Args:
            translation: QueryTranslation from translator

        Returns:
            RouteResult with appropriate response
        """
        # Check for explicit clarification request
        if translation.clarification_needed or translation.confidence < self.MODERATE_CONFIDENCE:
            return self._route_clarification(translation)

        # Route by query type
        if translation.query_type == QueryType.STRUCTURED:
            return self._route_structured(translation)

        elif translation.query_type == QueryType.SEMANTIC:
            return self._route_semantic(translation)

        elif translation.query_type == QueryType.HYBRID:
            return self._route_hybrid(translation)

        elif translation.query_type == QueryType.CLARIFICATION:
            return self._route_clarification(translation)

        # Default to structured if we have filters
        if translation.has_filters():
            return self._route_structured(translation)

        # Fallback to semantic
        return self._route_semantic(translation)

    def _route_structured(self, translation: QueryTranslation) -> RouteResult:
        """Route to SQL generation."""
        logger.info(
            f"Routing to SQL: confidence={translation.confidence:.2f}, "
            f"filters={len(translation.filters)}"
        )

        # Generate SQL
        sql_query = self.sql_generator.generate(translation)

        # Log warning for moderate confidence
        if translation.confidence < self.HIGH_CONFIDENCE:
            logger.warning(
                f"Moderate confidence SQL query: {translation.confidence:.2f}"
            )

        return RouteResult(
            query_type=QueryType.STRUCTURED,
            translation=translation,
            sql_query=sql_query,
            route_reason=f"Structured query with {len(translation.filters)} filters "
                        f"(confidence: {translation.confidence:.2f})",
        )

    def _route_semantic(self, translation: QueryTranslation) -> RouteResult:
        """Route to vector search."""
        logger.info(
            f"Routing to semantic search: confidence={translation.confidence:.2f}"
        )

        # Use semantic_query or original query for embedding
        embedding_query = translation.semantic_query or translation.original_query

        return RouteResult(
            query_type=QueryType.SEMANTIC,
            translation=translation,
            embedding_query=embedding_query,
            route_reason=f"Semantic query for vector search "
                        f"(confidence: {translation.confidence:.2f})",
        )

    def _route_hybrid(self, translation: QueryTranslation) -> RouteResult:
        """Route to hybrid SQL + vector search."""
        logger.info(
            f"Routing to hybrid search: confidence={translation.confidence:.2f}"
        )

        # Generate SQL for structured filters
        sql_query = None
        if translation.has_filters():
            sql_query = self.sql_generator.generate(translation)

        # Use semantic_query or original query for embedding
        embedding_query = translation.semantic_query or translation.original_query

        return RouteResult(
            query_type=QueryType.HYBRID,
            translation=translation,
            sql_query=sql_query,
            embedding_query=embedding_query,
            route_reason=f"Hybrid query: {len(translation.filters)} filters + semantic "
                        f"(confidence: {translation.confidence:.2f})",
        )

    def _route_clarification(self, translation: QueryTranslation) -> RouteResult:
        """Route to clarification request."""
        logger.info(
            f"Routing to clarification: confidence={translation.confidence:.2f}"
        )

        # Build clarification question if not provided
        question = translation.clarification_question
        if not question:
            if not translation.has_filters():
                question = "Δεν κατάλαβα την αναζήτηση. Μπορείτε να δώσετε περισσότερες λεπτομέρειες;"
            elif translation.unknown_terms:
                terms = ", ".join(translation.unknown_terms[:3])
                question = f"Δεν αναγνώρισα: {terms}. Μπορείτε να διευκρινίσετε;"
            else:
                question = "Μπορείτε να διευκρινίσετε την αναζήτησή σας;"

        # Update translation with question
        translation.clarification_question = question
        translation.clarification_needed = True

        return RouteResult(
            query_type=QueryType.CLARIFICATION,
            translation=translation,
            route_reason=f"Low confidence ({translation.confidence:.2f}), "
                        f"requesting clarification",
        )


# Convenience function for simple usage
async def route_query(
    user_query: str,
    region: str = "eu-north-1",
    context: dict[str, Any] | None = None,
) -> RouteResult:
    """
    Route natural language query.

    Args:
        user_query: User's natural language query
        region: AWS region for Bedrock
        context: Optional context

    Returns:
        RouteResult with routing decision
    """
    router = QueryRouter(region=region)
    return await router.route(user_query, context)
