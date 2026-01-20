"""
SQL Generator - Template-based SQL generation from structured filters.

Converts QueryTranslation filters into parameterized PostgreSQL queries.
Uses templates (no LLM) for deterministic, secure SQL generation.
"""

import logging
import time
from typing import Any

from .schema import (
    FILTER_FIELD_MAPPING,
    FilterOperator,
    QueryTranslation,
    SortDirection,
    SQLQuery,
)

logger = logging.getLogger(__name__)

# Value translation mappings for normalized database values
EDUCATION_LEVEL_MAPPING = {
    # University level (ΑΕΙ)
    "university": ["bachelor", "master", "doctorate", "phd"],
    "aei": ["bachelor", "master", "doctorate", "phd"],
    "αει": ["bachelor", "master", "doctorate", "phd"],
    "πανεπιστήμιο": ["bachelor", "master", "doctorate", "phd"],
    "πτυχίο αει": ["bachelor", "master", "doctorate", "phd"],
    "πτυχιο αει": ["bachelor", "master", "doctorate", "phd"],
    # TEI level
    "tei": ["tei", "bachelor"],
    "τει": ["tei", "bachelor"],
    "τεχνολογικό": ["tei", "bachelor"],
    # Specific degrees
    "bachelor": ["bachelor"],
    "πτυχίο": ["bachelor", "tei"],
    "master": ["master"],
    "μεταπτυχιακό": ["master"],
    "msc": ["master"],
    "mba": ["master"],
    "phd": ["doctorate", "phd"],
    "διδακτορικό": ["doctorate", "phd"],
    "doctorate": ["doctorate", "phd"],
    # High school
    "lyceum": ["lyceum"],
    "λύκειο": ["lyceum"],
    "high school": ["lyceum"],
    # Vocational
    "vocational": ["vocational", "iek"],
    "iek": ["iek", "vocational"],
    "ιεκ": ["iek", "vocational"],
    "επαγγελματική": ["vocational", "iek"],
}

LANGUAGE_CODE_MAPPING = {
    # English
    "english": "en",
    "αγγλικά": "en",
    "αγγλικα": "en",
    "en": "en",
    # Greek
    "greek": "el",
    "ελληνικά": "el",
    "ελληνικα": "el",
    "el": "el",
    # German
    "german": "de",
    "γερμανικά": "de",
    "γερμανικα": "de",
    "de": "de",
    # French
    "french": "fr",
    "γαλλικά": "fr",
    "γαλλικα": "fr",
    "fr": "fr",
    # Italian
    "italian": "it",
    "ιταλικά": "it",
    "ιταλικα": "it",
    "it": "it",
    # Spanish
    "spanish": "es",
    "ισπανικά": "es",
    "ισπανικα": "es",
    "es": "es",
    # Bulgarian
    "bulgarian": "bg",
    "βουλγαρικά": "bg",
    "βουλγαρικα": "bg",
    "bg": "bg",
    # Albanian
    "albanian": "sq",
    "αλβανικά": "sq",
    "αλβανικα": "sq",
    "sq": "sq",
    # Russian
    "russian": "ru",
    "ρωσικά": "ru",
    "ρωσικα": "ru",
    "ru": "ru",
    # Turkish
    "turkish": "tr",
    "τουρκικά": "tr",
    "τουρκικα": "tr",
    "tr": "tr",
    # Chinese
    "chinese": "zh",
    "κινεζικά": "zh",
    "κινεζικα": "zh",
    "zh": "zh",
}


def translate_education_level(value: str) -> list[str]:
    """Translate education level to database enum values."""
    return EDUCATION_LEVEL_MAPPING.get(value.lower(), [value.lower()])


def translate_language_code(value: str) -> str:
    """Translate language name to ISO code."""
    return LANGUAGE_CODE_MAPPING.get(value.lower(), value.lower())


class SQLGenerator:
    """
    Template-based SQL generator for candidate search.

    Converts structured filters into parameterized PostgreSQL queries.
    Uses $1, $2, ... placeholders for pg8000 compatibility.

    Example:
        generator = SQLGenerator()
        sql = generator.generate(translation)
        # sql.query = "SELECT ... WHERE ... $1 ..."
        # sql.params = [value1, value2, ...]
    """

    # Base SELECT clause for candidate queries
    BASE_SELECT = """
SELECT DISTINCT
    c.id,
    c.first_name,
    c.last_name,
    c.email,
    c.phone,
    c.address_city,
    c.address_region,
    c.availability_status,
    c.created_at,
    c.updated_at
FROM candidates c
"""

    # Default WHERE clause (only active candidates)
    BASE_WHERE = "WHERE c.is_active = true"

    def __init__(self):
        """Initialize SQL generator."""
        self.param_counter = 0
        self.params: list[Any] = []
        self.param_types: list[str] = []
        self.tables_used: list[str] = ["candidates"]
        self.warnings: list[str] = []

    def generate(self, translation: QueryTranslation) -> SQLQuery:
        """
        Generate SQL query from QueryTranslation.

        Args:
            translation: QueryTranslation with filters

        Returns:
            SQLQuery with parameterized query and values
        """
        start = time.time()

        # Reset state
        self.param_counter = 0
        self.params = []
        self.param_types = []
        self.tables_used = ["candidates"]
        self.warnings = []

        # Build WHERE clauses
        where_clauses = []
        filter_descriptions = []

        for field, condition in translation.filters.items():
            clause = self._build_filter_clause(field, condition)
            if clause:
                where_clauses.append(clause)
                filter_descriptions.append(
                    self._describe_filter(field, condition)
                )

        # Build ORDER BY
        order_by = self._build_order_by(translation)

        # Build LIMIT/OFFSET
        limit_clause = self._build_limit(translation)

        # Assemble query
        query_parts = [self.BASE_SELECT, self.BASE_WHERE]

        if where_clauses:
            query_parts.append("  AND " + "\n  AND ".join(where_clauses))

        if order_by:
            query_parts.append(order_by)

        query_parts.append(limit_clause)

        query = "\n".join(query_parts)

        generation_time = (time.time() - start) * 1000

        return SQLQuery(
            query=query,
            params=self.params,
            param_types=self.param_types,
            filter_summary=" | ".join(filter_descriptions) if filter_descriptions else "No filters",
            tables_used=list(set(self.tables_used)),
            generation_time_ms=generation_time,
            warnings=self.warnings,
        )

    def _next_param(self, value: Any, param_type: str = "text") -> str:
        """
        Get next parameter placeholder and store value.

        Args:
            value: Parameter value
            param_type: PostgreSQL type

        Returns:
            Placeholder string ($1, $2, etc.)
        """
        self.param_counter += 1
        self.params.append(value)
        self.param_types.append(param_type)
        return f"${self.param_counter}"

    def _build_filter_clause(
        self,
        field: str,
        condition: dict[str, Any],
    ) -> str | None:
        """
        Build SQL WHERE clause for a single filter.

        Args:
            field: Filter field name
            condition: {operator, value} dict

        Returns:
            SQL clause string or None
        """
        operator = condition.get("operator", "eq")
        value = condition.get("value")

        if value is None:
            return None

        # Get field mapping
        mapping = FILTER_FIELD_MAPPING.get(field)
        if not mapping:
            self.warnings.append(f"Unknown field: {field}")
            return None

        # Route to appropriate builder
        join_type = mapping.get("join")

        if join_type is None:
            # Direct column on candidates table
            return self._build_direct_clause(field, mapping, operator, value)

        elif join_type == "subquery":
            # Computed field via subquery
            return self._build_subquery_clause(field, mapping, operator, value)

        elif join_type == "computed":
            # Computed from existing column (e.g., age from date_of_birth)
            return self._build_computed_clause(field, mapping, operator, value)

        elif join_type == "exists":
            # Simple EXISTS subquery
            return self._build_exists_clause(field, mapping, operator, value)

        elif join_type.endswith("_taxonomy"):
            # Taxonomy join (skill_taxonomy, software_taxonomy, etc.)
            return self._build_taxonomy_clause(field, mapping, operator, value)

        self.warnings.append(f"Unknown join type for {field}: {join_type}")
        return None

    def _build_direct_clause(
        self,
        field: str,
        mapping: dict,
        operator: str,
        value: Any,
    ) -> str:
        """Build clause for direct candidate column."""
        column = mapping["column"]
        param_type = mapping["type"]

        if operator == FilterOperator.EQ.value:
            placeholder = self._next_param(value, param_type)
            return f"c.{column} = {placeholder}"

        elif operator == FilterOperator.NE.value:
            placeholder = self._next_param(value, param_type)
            return f"c.{column} != {placeholder}"

        elif operator == FilterOperator.CONTAINS.value:
            placeholder = self._next_param(f"%{value}%", "text")
            return f"c.{column} ILIKE {placeholder}"

        elif operator == FilterOperator.GT.value:
            placeholder = self._next_param(value, param_type)
            return f"c.{column} > {placeholder}"

        elif operator == FilterOperator.GTE.value:
            placeholder = self._next_param(value, param_type)
            return f"c.{column} >= {placeholder}"

        elif operator == FilterOperator.LT.value:
            placeholder = self._next_param(value, param_type)
            return f"c.{column} < {placeholder}"

        elif operator == FilterOperator.LTE.value:
            placeholder = self._next_param(value, param_type)
            return f"c.{column} <= {placeholder}"

        elif operator == FilterOperator.IN.value:
            if not isinstance(value, list):
                value = [value]
            placeholder = self._next_param(value, f"{param_type}[]")
            return f"c.{column} = ANY({placeholder})"

        elif operator == FilterOperator.NOT_IN.value:
            if not isinstance(value, list):
                value = [value]
            placeholder = self._next_param(value, f"{param_type}[]")
            return f"c.{column} != ALL({placeholder})"

        elif operator == FilterOperator.IS_NULL.value:
            return f"c.{column} IS NULL"

        elif operator == FilterOperator.IS_NOT_NULL.value:
            return f"c.{column} IS NOT NULL"

        self.warnings.append(f"Unsupported operator for {field}: {operator}")
        return None

    def _build_subquery_clause(
        self,
        field: str,
        mapping: dict,
        operator: str,
        value: Any,
    ) -> str:
        """Build clause with subquery (e.g., experience_years)."""
        self.tables_used.append(mapping["table"])

        if field == "experience_years":
            # Calculate total experience in years from duration_months
            subquery = """(
    SELECT COALESCE(SUM(duration_months), 0) / 12.0
    FROM candidate_experience
    WHERE candidate_id = c.id
)"""
            if operator == FilterOperator.GTE.value:
                placeholder = self._next_param(value, "numeric")
                return f"{subquery} >= {placeholder}"

            elif operator == FilterOperator.GT.value:
                placeholder = self._next_param(value, "numeric")
                return f"{subquery} > {placeholder}"

            elif operator == FilterOperator.LTE.value:
                placeholder = self._next_param(value, "numeric")
                return f"{subquery} <= {placeholder}"

            elif operator == FilterOperator.LT.value:
                placeholder = self._next_param(value, "numeric")
                return f"{subquery} < {placeholder}"

            elif operator == FilterOperator.EQ.value:
                placeholder = self._next_param(value, "numeric")
                return f"{subquery} = {placeholder}"

            elif operator == "between":
                if isinstance(value, list) and len(value) >= 2:
                    p1 = self._next_param(value[0], "numeric")
                    p2 = self._next_param(value[1], "numeric")
                    return f"{subquery} BETWEEN {p1} AND {p2}"

        self.warnings.append(f"Unknown subquery field: {field}")
        return None

    def _build_computed_clause(
        self,
        field: str,
        mapping: dict,
        operator: str,
        value: Any,
    ) -> str:
        """Build clause for computed fields (e.g., age)."""
        if field == "age":
            # Calculate age from date_of_birth
            age_expr = "EXTRACT(YEAR FROM AGE(c.date_of_birth))"

            if operator == FilterOperator.GTE.value:
                placeholder = self._next_param(value, "integer")
                return f"{age_expr} >= {placeholder}"

            elif operator == FilterOperator.LTE.value:
                placeholder = self._next_param(value, "integer")
                return f"{age_expr} <= {placeholder}"

            elif operator == "between":
                if isinstance(value, list) and len(value) >= 2:
                    p1 = self._next_param(value[0], "integer")
                    p2 = self._next_param(value[1], "integer")
                    return f"{age_expr} BETWEEN {p1} AND {p2}"

        self.warnings.append(f"Unknown computed field: {field}")
        return None

    def _build_exists_clause(
        self,
        field: str,
        mapping: dict,
        operator: str,
        value: Any,
    ) -> str:
        """Build EXISTS subquery for related tables."""
        table = mapping["table"]
        column = mapping["column"]
        self.tables_used.append(table)

        if not isinstance(value, list):
            value = [value]

        # Translate values for specific fields
        if field == "education_level":
            # Translate education level names to database enum values
            translated = []
            for v in value:
                translated.extend(translate_education_level(str(v)))
            value = list(set(translated))  # Remove duplicates
            logger.debug(f"Translated education_level: {value}")

        elif field == "language_codes":
            # Translate language names to ISO codes
            value = [translate_language_code(str(v)) for v in value]
            logger.debug(f"Translated language_codes: {value}")

        # Cast enum columns to text for comparison
        # degree_level is an enum type
        column_expr = f"{column}::text" if field == "education_level" else column

        if operator == FilterOperator.ANY.value:
            # At least one of the values
            placeholder = self._next_param(value, "text[]")
            return f"""EXISTS (
    SELECT 1 FROM {table}
    WHERE candidate_id = c.id
      AND {column_expr} = ANY({placeholder})
)"""

        elif operator == FilterOperator.ALL.value:
            # Must have ALL values
            placeholder = self._next_param(value, "text[]")
            count_placeholder = self._next_param(len(value), "integer")
            return f"""(
    SELECT COUNT(DISTINCT {column_expr})
    FROM {table}
    WHERE candidate_id = c.id
      AND {column_expr} = ANY({placeholder})
) = {count_placeholder}"""

        elif operator in (FilterOperator.EQ.value, FilterOperator.IN.value):
            # Single value or list
            placeholder = self._next_param(value, "text[]")
            return f"""EXISTS (
    SELECT 1 FROM {table}
    WHERE candidate_id = c.id
      AND {column_expr} = ANY({placeholder})
)"""

        elif operator == FilterOperator.CONTAINS.value:
            # ILIKE search for partial matches (e.g., language codes)
            search_value = value[0] if len(value) == 1 else value[0]
            placeholder = self._next_param(f"%{search_value}%", "text")
            return f"""EXISTS (
    SELECT 1 FROM {table}
    WHERE candidate_id = c.id
      AND {column} ILIKE {placeholder}
)"""

        self.warnings.append(f"Unsupported operator for {field}: {operator}")
        return None

    def _build_taxonomy_clause(
        self,
        field: str,
        mapping: dict,
        operator: str,
        value: Any,
    ) -> str:
        """Build clause with taxonomy join."""
        table = mapping["table"]
        join_type = mapping["join"]
        self.tables_used.append(table)

        if not isinstance(value, list):
            value = [value]

        # Determine taxonomy table name
        taxonomy_table = join_type  # e.g., "skill_taxonomy"
        self.tables_used.append(taxonomy_table)

        # Build alias based on field type
        if field == "skill_ids":
            alias = "cs"
            taxonomy_alias = "st"
            join_column = "skill_id"
        elif field == "software_ids":
            alias = "csw"
            taxonomy_alias = "swt"
            join_column = "software_id"
        elif field == "role_ids":
            alias = "ce"
            taxonomy_alias = "rt"
            join_column = "role_id"
        elif field == "certification_ids":
            alias = "cc"
            taxonomy_alias = "ct"
            join_column = "certification_id_taxonomy"
        else:
            self.warnings.append(f"Unknown taxonomy field: {field}")
            return None

        # Determine which name columns to use based on taxonomy table
        # software_taxonomy has 'name', others have 'name_en' and 'name_el'
        # Also search canonical_id to handle both SW_EXCEL and Excel patterns
        if taxonomy_table == "software_taxonomy":
            name_condition_template = f"({taxonomy_alias}.name ILIKE {{placeholder}} OR {taxonomy_alias}.canonical_id ILIKE {{placeholder}})"
        else:
            name_condition_template = f"({taxonomy_alias}.name_en ILIKE {{placeholder}} OR {taxonomy_alias}.name_el ILIKE {{placeholder}} OR {taxonomy_alias}.canonical_id ILIKE {{placeholder}})"

        if operator == FilterOperator.CONTAINS.value:
            # For contains, search by name (case-insensitive) instead of canonical_id
            # This handles searches like "SAP" or "Excel" by name
            search_value = value[0] if isinstance(value, list) and len(value) == 1 else value
            if isinstance(search_value, str):
                placeholder = self._next_param(f"%{search_value}%", "text")
                name_condition = name_condition_template.format(placeholder=placeholder)

                # Special handling for role_ids: also search job_title directly
                # because many records have NULL role_id
                if field == "role_ids":
                    job_title_placeholder = self._next_param(f"%{search_value}%", "text")
                    return f"""EXISTS (
    SELECT 1 FROM {table} {alias}
    LEFT JOIN {taxonomy_table} {taxonomy_alias} ON {alias}.{join_column} = {taxonomy_alias}.id
    WHERE {alias}.candidate_id = c.id
      AND ({name_condition} OR {alias}.job_title ILIKE {job_title_placeholder} OR {alias}.job_title_normalized ILIKE {job_title_placeholder})
)"""

                return f"""EXISTS (
    SELECT 1 FROM {table} {alias}
    JOIN {taxonomy_table} {taxonomy_alias} ON {alias}.{join_column} = {taxonomy_alias}.id
    WHERE {alias}.candidate_id = c.id
      AND {name_condition}
)"""
            # Fall through to ANY for non-string values

        placeholder = self._next_param(value, "text[]")

        if operator in (FilterOperator.ANY.value, FilterOperator.CONTAINS.value, FilterOperator.IN.value, FilterOperator.EQ.value):
            # Search by name match (case-insensitive) for text values
            if isinstance(value, list) and all(isinstance(v, str) for v in value):
                # Build OR conditions for each search term
                conditions = []
                job_title_conditions = []
                for v in value:
                    p = self._next_param(f"%{v}%", "text")
                    name_condition = name_condition_template.format(placeholder=p)
                    conditions.append(name_condition)
                    # For role_ids, also search job_title directly
                    if field == "role_ids":
                        jtp = self._next_param(f"%{v}%", "text")
                        job_title_conditions.append(f"({alias}.job_title ILIKE {jtp} OR {alias}.job_title_normalized ILIKE {jtp})")

                or_clause = " OR ".join(conditions)

                # Special handling for role_ids: use LEFT JOIN and also search job_title
                if field == "role_ids" and job_title_conditions:
                    job_title_or = " OR ".join(job_title_conditions)
                    return f"""EXISTS (
    SELECT 1 FROM {table} {alias}
    LEFT JOIN {taxonomy_table} {taxonomy_alias} ON {alias}.{join_column} = {taxonomy_alias}.id
    WHERE {alias}.candidate_id = c.id
      AND (({or_clause}) OR ({job_title_or}))
)"""

                return f"""EXISTS (
    SELECT 1 FROM {table} {alias}
    JOIN {taxonomy_table} {taxonomy_alias} ON {alias}.{join_column} = {taxonomy_alias}.id
    WHERE {alias}.candidate_id = c.id
      AND ({or_clause})
)"""
            else:
                # Fallback to canonical_id match for non-string values
                return f"""EXISTS (
    SELECT 1 FROM {table} {alias}
    JOIN {taxonomy_table} {taxonomy_alias} ON {alias}.{join_column} = {taxonomy_alias}.id
    WHERE {alias}.candidate_id = c.id
      AND {taxonomy_alias}.canonical_id = ANY({placeholder})
)"""

        elif operator == FilterOperator.ALL.value:
            count_placeholder = self._next_param(len(value), "integer")
            return f"""(
    SELECT COUNT(DISTINCT {taxonomy_alias}.canonical_id)
    FROM {table} {alias}
    JOIN {taxonomy_table} {taxonomy_alias} ON {alias}.{join_column} = {taxonomy_alias}.id
    WHERE {alias}.candidate_id = c.id
      AND {taxonomy_alias}.canonical_id = ANY({placeholder})
) = {count_placeholder}"""

        self.warnings.append(f"Unsupported operator for {field}: {operator}")
        return None

    def _build_order_by(self, translation: QueryTranslation) -> str:
        """Build ORDER BY clause."""
        if not translation.sort:
            # Default sort by updated_at DESC
            return "ORDER BY c.updated_at DESC"

        field = translation.sort.field
        direction = "ASC" if translation.sort.direction == SortDirection.ASC else "DESC"

        # Map sort field to column
        sort_mapping = {
            "experience_years": "(SELECT COALESCE(SUM(duration_months), 0) FROM candidate_experience WHERE candidate_id = c.id)",
            "created_at": "c.created_at",
            "updated_at": "c.updated_at",
            "first_name": "c.first_name",
            "last_name": "c.last_name",
            "location": "c.address_city",
        }

        sort_column = sort_mapping.get(field, "c.updated_at")
        return f"ORDER BY {sort_column} {direction}"

    def _build_limit(self, translation: QueryTranslation) -> str:
        """Build LIMIT/OFFSET clause."""
        limit = min(translation.limit, 100)  # Cap at 100
        offset = translation.offset

        placeholder_limit = self._next_param(limit, "integer")

        if offset > 0:
            placeholder_offset = self._next_param(offset, "integer")
            return f"LIMIT {placeholder_limit} OFFSET {placeholder_offset}"

        return f"LIMIT {placeholder_limit}"

    def _describe_filter(
        self,
        field: str,
        condition: dict[str, Any],
    ) -> str:
        """Generate human-readable description of filter."""
        operator = condition.get("operator", "eq")
        value = condition.get("value")

        op_descriptions = {
            "eq": "=",
            "ne": "!=",
            "gt": ">",
            "gte": ">=",
            "lt": "<",
            "lte": "<=",
            "contains": "contains",
            "any": "has any of",
            "all": "has all of",
            "in": "in",
            "not_in": "not in",
        }

        op_desc = op_descriptions.get(operator, operator)

        if isinstance(value, list):
            value_str = ", ".join(str(v) for v in value[:3])
            if len(value) > 3:
                value_str += f" (+{len(value) - 3} more)"
        else:
            value_str = str(value)

        return f"{field} {op_desc} {value_str}"


# Convenience function for simple usage
def generate_sql(translation: QueryTranslation) -> SQLQuery:
    """
    Generate SQL from QueryTranslation.

    Args:
        translation: QueryTranslation with filters

    Returns:
        SQLQuery with parameterized query
    """
    generator = SQLGenerator()
    return generator.generate(translation)
