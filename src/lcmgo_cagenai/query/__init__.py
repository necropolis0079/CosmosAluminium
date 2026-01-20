"""
Text-to-SQL Query Module.

Translates natural language HR queries (Greek/English) into optimized
PostgreSQL queries. Uses Claude Haiku for fast query translation and
template-based SQL generation for deterministic results.

Example usage:
    from lcmgo_cagenai.query import route_query, QueryType

    # Route a Greek query
    result = await route_query("λογιστής με Softone, 5+ χρόνια, Αθήνα")

    if result.query_type == QueryType.STRUCTURED:
        # Execute generated SQL
        rows = await db.fetch(result.sql_query.query, *result.sql_query.params)

    elif result.query_type == QueryType.CLARIFICATION:
        # Ask user for more info
        print(result.translation.clarification_question)

Benefits:
- 54% cost reduction vs RAG ($0.012 vs $0.025 per query)
- Deterministic results (same query = same results)
- Explainable (shows exact SQL and reasoning)
- Bilingual Greek/English support

See docs/14-LLM-ABSTRACTION.md for full specification.
"""

from .dynamic_aliases import (
    AliasCache,
    AliasEntry,
    DynamicAliasLoader,
    get_global_loader,
    load_aliases_sync,
    normalize_text,
)
from .query_router import QueryRouter, route_query
from .query_translator import QueryTranslator, translate_query
from .schema import (
    FILTER_FIELD_MAPPING,
    GREEK_ALIASES,
    LOCATION_ALIASES,
    FilterCondition,
    FilterOperator,
    QueryTranslation,
    QueryType,
    RouteResult,
    SortDirection,
    SortOrder,
    SQLQuery,
    normalize_greek,
)
from .sql_generator import SQLGenerator, generate_sql

__all__ = [
    # Core classes
    "QueryTranslator",
    "SQLGenerator",
    "QueryRouter",
    # Dynamic aliases (Phase 4)
    "DynamicAliasLoader",
    "AliasEntry",
    "AliasCache",
    # Convenience functions
    "translate_query",
    "generate_sql",
    "route_query",
    "load_aliases_sync",
    "get_global_loader",
    # Dataclasses
    "QueryTranslation",
    "SQLQuery",
    "RouteResult",
    "FilterCondition",
    "SortOrder",
    # Enums
    "QueryType",
    "FilterOperator",
    "SortDirection",
    # Utilities
    "normalize_greek",
    "normalize_text",
    # Mappings (static - for fallback)
    "FILTER_FIELD_MAPPING",
    "GREEK_ALIASES",
    "LOCATION_ALIASES",
]
