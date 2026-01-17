"""
Dataclasses for Text-to-SQL query translation.

These models define the structure for translating natural language queries
into structured filters and SQL queries for the PostgreSQL v4.0 schema.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class QueryType(str, Enum):
    """Query type classification."""

    STRUCTURED = "structured"  # Can be directly translated to SQL
    SEMANTIC = "semantic"  # Requires vector search
    HYBRID = "hybrid"  # Combination of SQL and vector search
    CLARIFICATION = "clarification"  # Need more info from user


class FilterOperator(str, Enum):
    """SQL filter operators."""

    EQ = "eq"  # =
    NE = "ne"  # !=
    GT = "gt"  # >
    GTE = "gte"  # >=
    LT = "lt"  # <
    LTE = "lte"  # <=
    IN = "in"  # IN (...)
    NOT_IN = "not_in"  # NOT IN (...)
    CONTAINS = "contains"  # ILIKE '%value%'
    ANY = "any"  # = ANY(array) - at least one match
    ALL = "all"  # Must have ALL values
    IS_NULL = "is_null"  # IS NULL
    IS_NOT_NULL = "is_not_null"  # IS NOT NULL


class SortDirection(str, Enum):
    """Sort direction."""

    ASC = "asc"
    DESC = "desc"


@dataclass
class SortOrder:
    """Sort specification."""

    field: str
    direction: SortDirection = SortDirection.DESC


@dataclass
class FilterCondition:
    """Single filter condition."""

    field: str
    operator: FilterOperator
    value: Any
    param_type: str = "text"  # PostgreSQL type hint


@dataclass
class QueryTranslation:
    """
    Result of translating natural language to structured query.

    Contains extracted filters, confidence scores, and any
    clarification requests.
    """

    # Query classification
    query_type: QueryType
    confidence: float  # 0.0-1.0

    # Extracted filters (field -> {operator, value})
    filters: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Unknown terms that couldn't be mapped
    unknown_terms: list[str] = field(default_factory=list)

    # Clarification handling
    clarification_needed: bool = False
    clarification_question: str | None = None
    clarification_options: list[str] = field(default_factory=list)

    # Original query for context
    original_query: str = ""

    # Result controls
    sort: SortOrder | None = None
    limit: int = 50
    offset: int = 0

    # Semantic search fallback
    semantic_query: str | None = None

    # Debugging info
    reasoning: str | None = None
    model_used: str | None = None

    def has_filters(self) -> bool:
        """Check if any filters were extracted."""
        return len(self.filters) > 0

    def get_filter(self, field_name: str) -> dict[str, Any] | None:
        """Get filter for a specific field."""
        return self.filters.get(field_name)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result = {
            "query_type": self.query_type.value,
            "confidence": self.confidence,
            "filters": self.filters,
            "unknown_terms": self.unknown_terms,
            "clarification_needed": self.clarification_needed,
            "clarification_question": self.clarification_question,
            "clarification_options": self.clarification_options,
            "original_query": self.original_query,
            "limit": self.limit,
            "offset": self.offset,
        }

        if self.sort:
            result["sort"] = {
                "field": self.sort.field,
                "direction": self.sort.direction.value,
            }

        if self.semantic_query:
            result["semantic_query"] = self.semantic_query

        if self.reasoning:
            result["reasoning"] = self.reasoning

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueryTranslation":
        """Create from dict (e.g., parsed JSON)."""
        sort = None
        if data.get("sort"):
            sort = SortOrder(
                field=data["sort"]["field"],
                direction=SortDirection(data["sort"].get("direction", "desc")),
            )

        return cls(
            query_type=QueryType(data.get("query_type", "structured")),
            confidence=data.get("confidence", 0.0),
            filters=data.get("filters", {}),
            unknown_terms=data.get("unknown_terms", []),
            clarification_needed=data.get("clarification_needed", False),
            clarification_question=data.get("clarification_question"),
            clarification_options=data.get("clarification_options", []),
            original_query=data.get("original_query", ""),
            sort=sort,
            limit=data.get("limit", 50),
            offset=data.get("offset", 0),
            semantic_query=data.get("semantic_query"),
            reasoning=data.get("reasoning"),
        )


@dataclass
class SQLQuery:
    """
    Generated SQL query with parameters.

    Uses parameterized queries to prevent SQL injection.
    Parameters use $1, $2, etc. placeholder syntax (pg8000 format).
    """

    # The SQL query with $1, $2 placeholders
    query: str

    # Parameter values in order
    params: list[Any] = field(default_factory=list)

    # PostgreSQL types for parameters
    param_types: list[str] = field(default_factory=list)

    # Human-readable filter description
    filter_summary: str = ""

    # Tables involved in the query
    tables_used: list[str] = field(default_factory=list)

    # Debugging info
    generation_time_ms: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "query": self.query,
            "params": self.params,
            "param_types": self.param_types,
            "filter_summary": self.filter_summary,
            "tables_used": self.tables_used,
            "warnings": self.warnings,
        }


@dataclass
class RouteResult:
    """
    Result of query routing decision.

    Contains the route taken and the resulting query/translation.
    """

    query_type: QueryType
    translation: QueryTranslation

    # For structured/hybrid queries
    sql_query: SQLQuery | None = None

    # For semantic queries
    embedding_query: str | None = None

    # Execution metadata
    route_reason: str = ""
    fallback_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result = {
            "query_type": self.query_type.value,
            "translation": self.translation.to_dict(),
            "route_reason": self.route_reason,
            "fallback_used": self.fallback_used,
        }

        if self.sql_query:
            result["sql_query"] = self.sql_query.to_dict()

        if self.embedding_query:
            result["embedding_query"] = self.embedding_query

        return result


# Field mapping from filter names to database columns/tables
FILTER_FIELD_MAPPING = {
    # Direct candidate fields
    "location": {
        "table": "candidates",
        "column": "address_city",
        "type": "text",
        "join": None,
    },
    "region": {
        "table": "candidates",
        "column": "address_region",
        "type": "text",
        "join": None,
    },
    "country": {
        "table": "candidates",
        "column": "address_country",
        "type": "text",
        "join": None,
    },
    "nationality": {
        "table": "candidates",
        "column": "nationality",
        "type": "text",
        "join": None,
    },
    "gender": {
        "table": "candidates",
        "column": "gender",
        "type": "gender_type",
        "join": None,
    },
    "availability": {
        "table": "candidates",
        "column": "availability_status",
        "type": "availability_status_type",
        "join": None,
    },
    "willing_to_relocate": {
        "table": "candidates",
        "column": "willing_to_relocate",
        "type": "boolean",
        "join": None,
    },
    "military_status": {
        "table": "candidates",
        "column": "military_status",
        "type": "military_status_type",
        "join": None,
    },
    # Computed fields (subqueries)
    "experience_years": {
        "table": "candidate_experience",
        "column": "duration_months",
        "type": "numeric",
        "join": "subquery",
    },
    "age": {
        "table": "candidates",
        "column": "date_of_birth",
        "type": "date",
        "join": "computed",
    },
    # Related table fields
    "skill_ids": {
        "table": "candidate_skills",
        "column": "skill_id",
        "type": "text[]",
        "join": "skill_taxonomy",
    },
    "software_ids": {
        "table": "candidate_software",
        "column": "software_id",
        "type": "text[]",
        "join": "software_taxonomy",
    },
    "role_ids": {
        "table": "candidate_experience",
        "column": "role_id",
        "type": "text[]",
        "join": "role_taxonomy",
    },
    "education_level": {
        "table": "candidate_education",
        "column": "degree_level",
        "type": "education_level_type",
        "join": "exists",
    },
    "education_field": {
        "table": "candidate_education",
        "column": "field_of_study",
        "type": "education_field_type",
        "join": "exists",
    },
    "language_codes": {
        "table": "candidate_languages",
        "column": "language_code",
        "type": "text[]",
        "join": "exists",
    },
    "language_level": {
        "table": "candidate_languages",
        "column": "proficiency_level",
        "type": "language_proficiency_type",
        "join": "exists",
    },
    "certification_ids": {
        "table": "candidate_certifications",
        "column": "certification_id_taxonomy",
        "type": "text[]",
        "join": "certification_taxonomy",
    },
    "driving_licenses": {
        "table": "candidate_driving_licenses",
        "column": "license_category",
        "type": "driving_license_type[]",
        "join": "exists",
    },
}


# Greek aliases for taxonomy IDs
GREEK_ALIASES = {
    # Roles
    "λογιστής": "ROLE_ACCOUNTANT",
    "λογιστρια": "ROLE_ACCOUNTANT",
    "μηχανικός": "ROLE_ENGINEER",
    "μηχανικος": "ROLE_ENGINEER",
    "ηλεκτρολόγος": "ROLE_ELECTRICIAN",
    "ηλεκτρολογος": "ROLE_ELECTRICIAN",
    "τεχνικός": "ROLE_TECHNICIAN",
    "τεχνικος": "ROLE_TECHNICIAN",
    "χειριστής": "ROLE_OPERATOR",
    "χειριστης": "ROLE_OPERATOR",
    "αποθηκάριος": "ROLE_WAREHOUSE",
    "αποθηκαριος": "ROLE_WAREHOUSE",
    "οδηγός": "ROLE_DRIVER",
    "οδηγος": "ROLE_DRIVER",
    "γραμματέας": "ROLE_SECRETARY",
    "γραμματεας": "ROLE_SECRETARY",
    "διευθυντής": "ROLE_MANAGER",
    "διευθυντης": "ROLE_MANAGER",
    "πωλητής": "ROLE_SALES",
    "πωλητης": "ROLE_SALES",
    "μάγειρας": "ROLE_COOK",
    "μαγειρας": "ROLE_COOK",
    "σερβιτόρος": "ROLE_WAITER",
    "σερβιτορος": "ROLE_WAITER",
    "καθαριστής": "ROLE_CLEANER",
    "καθαριστης": "ROLE_CLEANER",
    "φύλακας": "ROLE_SECURITY",
    "φυλακας": "ROLE_SECURITY",
    # Software
    "sap": "SW_SAP",
    "σαπ": "SW_SAP",
    "softone": "SW_SOFTONE",
    "σοφτουαν": "SW_SOFTONE",
    "excel": "SW_EXCEL",
    "word": "SW_WORD",
    "autocad": "SW_AUTOCAD",
    "αυτοκαντ": "SW_AUTOCAD",
    "solidworks": "SW_SOLIDWORKS",
    "photoshop": "SW_PHOTOSHOP",
    "erp": "SW_ERP",
    "crm": "SW_CRM",
    # Skills
    "συγκόλληση": "SKILL_WELDING",
    "συγκολληση": "SKILL_WELDING",
    "tig": "SKILL_WELDING_TIG",
    "mig": "SKILL_WELDING_MIG",
    "mma": "SKILL_WELDING_MMA",
    "cnc": "SKILL_CNC",
    "τόρνος": "SKILL_LATHE",
    "τορνος": "SKILL_LATHE",
    "φρέζα": "SKILL_MILLING",
    "φρεζα": "SKILL_MILLING",
    "plc": "SKILL_PLC",
    "ηλεκτροσυγκόλληση": "SKILL_WELDING",
    "ηλεκτροσυγκολληση": "SKILL_WELDING",
    # Education levels
    "απόφοιτος": "secondary",
    "αποφοιτος": "secondary",
    "λύκειο": "lyceum",
    "λυκειο": "lyceum",
    "ιεκ": "iek",
    "τει": "tei",
    "πτυχίο": "bachelor",
    "πτυχιο": "bachelor",
    "μεταπτυχιακό": "master",
    "μεταπτυχιακο": "master",
    "διδακτορικό": "doctorate",
    "διδακτορικο": "doctorate",
    # Driving licenses
    "δίπλωμα": "B",
    "διπλωμα": "B",
    "κλαρκ": "forklift",
    "περονοφόρο": "forklift",
    "περονοφορο": "forklift",
    "γερανός": "crane",
    "γερανος": "crane",
    # Languages
    "ελληνικά": "el",
    "ελληνικα": "el",
    "αγγλικά": "en",
    "αγγλικα": "en",
    "γερμανικά": "de",
    "γερμανικα": "de",
    "γαλλικά": "fr",
    "γαλλικα": "fr",
    # Certifications
    "iso": "CERT_ISO",
    "ασφαλείας": "CERT_SAFETY",
    "ασφαλειας": "CERT_SAFETY",
    "πρώτες βοήθειες": "CERT_FIRST_AID",
    "πρωτες βοηθειες": "CERT_FIRST_AID",
    "πιστοποίηση": "CERT_GENERIC",
    "πιστοποιηση": "CERT_GENERIC",
}


# Greek location aliases
LOCATION_ALIASES = {
    "αθήνα": "Αθήνα",
    "αθηνα": "Αθήνα",
    "θεσσαλονίκη": "Θεσσαλονίκη",
    "θεσσαλονικη": "Θεσσαλονίκη",
    "πάτρα": "Πάτρα",
    "πατρα": "Πάτρα",
    "ηράκλειο": "Ηράκλειο",
    "ηρακλειο": "Ηράκλειο",
    "λάρισα": "Λάρισα",
    "λαρισα": "Λάρισα",
    "βόλος": "Βόλος",
    "βολος": "Βόλος",
    "ιωάννινα": "Ιωάννινα",
    "ιωαννινα": "Ιωάννινα",
    "χανιά": "Χανιά",
    "χανια": "Χανιά",
    "αλεξανδρούπολη": "Αλεξανδρούπολη",
    "αλεξανδρουπολη": "Αλεξανδρούπολη",
    "καβάλα": "Καβάλα",
    "καβαλα": "Καβάλα",
    "κομοτηνή": "Κομοτηνή",
    "κομοτηνη": "Κομοτηνή",
    "σέρρες": "Σέρρες",
    "σερρες": "Σέρρες",
    "δράμα": "Δράμα",
    "δραμα": "Δράμα",
    "ξάνθη": "Ξάνθη",
    "ξανθη": "Ξάνθη",
    "κοζάνη": "Κοζάνη",
    "κοζανη": "Κοζάνη",
    "τρίκαλα": "Τρίκαλα",
    "τρικαλα": "Τρίκαλα",
    "καρδίτσα": "Καρδίτσα",
    "καρδιτσα": "Καρδίτσα",
    "χαλκίδα": "Χαλκίδα",
    "χαλκιδα": "Χαλκίδα",
    "λαμία": "Λαμία",
    "λαμια": "Λαμία",
    "αλμυρός": "Αλμυρός",
    "αλμυρος": "Αλμυρός",
}


def normalize_greek(text: str) -> str:
    """
    Remove accents and normalize Greek text.

    Args:
        text: Greek text with accents

    Returns:
        Normalized text without accents
    """
    # Greek accent removal map
    accent_map = {
        "ά": "α",
        "έ": "ε",
        "ή": "η",
        "ί": "ι",
        "ό": "ο",
        "ύ": "υ",
        "ώ": "ω",
        "ϊ": "ι",
        "ϋ": "υ",
        "ΐ": "ι",
        "ΰ": "υ",
        "Ά": "Α",
        "Έ": "Ε",
        "Ή": "Η",
        "Ί": "Ι",
        "Ό": "Ο",
        "Ύ": "Υ",
        "Ώ": "Ω",
    }

    result = text
    for accented, plain in accent_map.items():
        result = result.replace(accented, plain)

    return result
