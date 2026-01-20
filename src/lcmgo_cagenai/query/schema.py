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

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "field": self.field,
            "direction": self.direction.value
        }


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
# Expanded from D:\CA\Source\taxonomies\cv-taxonomy.json
GREEK_ALIASES = {
    # ==========================================================================
    # ROLES (from cv-taxonomy.json roles section)
    # ==========================================================================
    # Management
    "ceo": "ROLE_CEO",
    "διευθύνων σύμβουλος": "ROLE_CEO",
    "γενικός διευθυντής": "ROLE_DIRECTOR",
    "διευθυντής": "ROLE_DIRECTOR",
    "διευθυντης": "ROLE_DIRECTOR",
    "director": "ROLE_DIRECTOR",
    "manager": "ROLE_MANAGER",
    "προϊστάμενος": "ROLE_MANAGER",
    "προισταμενος": "ROLE_MANAGER",
    "υπεύθυνος": "ROLE_MANAGER",
    "υπευθυνος": "ROLE_MANAGER",
    "team leader": "ROLE_TEAM_LEAD",
    "επικεφαλής ομάδας": "ROLE_TEAM_LEAD",
    "supervisor": "ROLE_SUPERVISOR",
    "επόπτης": "ROLE_SUPERVISOR",
    # Accounting
    "cfo": "ROLE_CFO",
    "οικονομικός διευθυντής": "ROLE_CFO",
    "προϊστάμενος λογιστηρίου": "ROLE_ACCOUNTING_MANAGER",
    "υπεύθυνος λογιστηρίου": "ROLE_ACCOUNTING_MANAGER",
    "λογιστής α'": "ROLE_SENIOR_ACCOUNTANT",
    "senior accountant": "ROLE_SENIOR_ACCOUNTANT",
    "λογιστής": "ROLE_ACCOUNTANT",
    "λογιστης": "ROLE_ACCOUNTANT",
    "λογίστρια": "ROLE_ACCOUNTANT",
    "λογιστρια": "ROLE_ACCOUNTANT",
    "accountant": "ROLE_ACCOUNTANT",
    "υπάλληλος λογιστηρίου": "ROLE_ACCOUNTANT",
    "στέλεχος λογιστηρίου": "ROLE_ACCOUNTANT",
    "bookkeeper": "ROLE_ACCOUNTANT",
    "βοηθός λογιστή": "ROLE_JUNIOR_ACCOUNTANT",
    "junior accountant": "ROLE_JUNIOR_ACCOUNTANT",
    "υπεύθυνος μισθοδοσίας": "ROLE_PAYROLL_SPECIALIST",
    "payroll specialist": "ROLE_PAYROLL_SPECIALIST",
    # Sales
    "διευθυντής πωλήσεων": "ROLE_SALES_DIRECTOR",
    "sales director": "ROLE_SALES_DIRECTOR",
    "διευθυντής καταστήματος": "ROLE_STORE_MANAGER",
    "υπεύθυνος καταστήματος": "ROLE_STORE_MANAGER",
    "store manager": "ROLE_STORE_MANAGER",
    "πωλητής": "ROLE_SALES_REPRESENTATIVE",
    "πωλητης": "ROLE_SALES_REPRESENTATIVE",
    "πωλήτρια": "ROLE_SALES_REPRESENTATIVE",
    "sales representative": "ROLE_SALES_REPRESENTATIVE",
    "sales associate": "ROLE_SALES_REPRESENTATIVE",
    "sales consultant": "ROLE_SALES_REPRESENTATIVE",
    "sales executive": "ROLE_SALES_REPRESENTATIVE",
    "σύμβουλος πωλήσεων": "ROLE_SALES_REPRESENTATIVE",
    "ταμίας": "ROLE_CASHIER",
    "ταμιας": "ROLE_CASHIER",
    "cashier": "ROLE_CASHIER",
    "ταμείο": "ROLE_CASHIER",
    # Warehouse
    "αποθηκάριος": "ROLE_WAREHOUSE",
    "αποθηκαριος": "ROLE_WAREHOUSE",
    "warehouse": "ROLE_WAREHOUSE",
    "αποθήκη": "ROLE_WAREHOUSE",
    "warehouse worker": "ROLE_WAREHOUSE",
    "stock controller": "ROLE_WAREHOUSE",
    "forklift operator": "ROLE_WAREHOUSE",
    "χειριστής κλαρκ": "ROLE_WAREHOUSE",
    "κλαρκ": "ROLE_WAREHOUSE",
    "logistics": "ROLE_WAREHOUSE",
    # HR/Admin
    "hr director": "ROLE_HR_DIRECTOR",
    "διευθυντής hr": "ROLE_HR_DIRECTOR",
    "hr manager": "ROLE_HR_MANAGER",
    "υπεύθυνος hr": "ROLE_HR_MANAGER",
    "hr specialist": "ROLE_HR_SPECIALIST",
    "γραμματέας": "ROLE_SECRETARY",
    "γραμματεας": "ROLE_SECRETARY",
    "secretary": "ROLE_SECRETARY",
    "διοικητική υποστήριξη": "ROLE_ADMIN_ASSISTANT",
    "office manager": "ROLE_OFFICE_MANAGER",
    # Technical
    "μηχανικός": "ROLE_ENGINEER",
    "μηχανικος": "ROLE_ENGINEER",
    "engineer": "ROLE_ENGINEER",
    "ηλεκτρολόγος": "ROLE_ELECTRICIAN",
    "ηλεκτρολογος": "ROLE_ELECTRICIAN",
    "electrician": "ROLE_ELECTRICIAN",
    "τεχνικός": "ROLE_TECHNICIAN",
    "τεχνικος": "ROLE_TECHNICIAN",
    "technician": "ROLE_TECHNICIAN",
    "χειριστής": "ROLE_OPERATOR",
    "χειριστης": "ROLE_OPERATOR",
    "operator": "ROLE_OPERATOR",
    "οδηγός": "ROLE_DRIVER",
    "οδηγος": "ROLE_DRIVER",
    "driver": "ROLE_DRIVER",
    # Other
    "μάγειρας": "ROLE_COOK",
    "μαγειρας": "ROLE_COOK",
    "σερβιτόρος": "ROLE_WAITER",
    "σερβιτορος": "ROLE_WAITER",
    "καθαριστής": "ROLE_CLEANER",
    "καθαριστης": "ROLE_CLEANER",
    "φύλακας": "ROLE_SECURITY",
    "φυλακας": "ROLE_SECURITY",
    "security": "ROLE_SECURITY",
    # ==========================================================================
    # SOFTWARE (from cv-taxonomy.json software section)
    # ==========================================================================
    # SAP
    "sap": "SW_SAP",
    "σαπ": "SW_SAP",
    "sap erp": "SW_SAP",
    "sap s/4hana": "SW_SAP",
    "s/4hana": "SW_SAP",
    "sap business one": "SW_SAP",
    "sap b1": "SW_SAP",
    "sap mm": "SW_SAP",
    "sap sd": "SW_SAP",
    "sap fi": "SW_SAP",
    "sap co": "SW_SAP",
    "sap fico": "SW_SAP",
    "sap hr": "SW_SAP",
    "sap hcm": "SW_SAP",
    "sap wm": "SW_SAP",
    "sap pp": "SW_SAP",
    "χρήστης sap": "SW_SAP",
    # Greek ERP Systems
    "softone": "SW_SOFTONE",
    "soft1": "SW_SOFTONE",
    "soft 1": "SW_SOFTONE",
    "σοφτουαν": "SW_SOFTONE",
    "soft1 series": "SW_SOFTONE",
    "pylon": "SW_PYLON",
    "πάιλον": "SW_PYLON",
    "pylon erp": "SW_PYLON",
    "epsilon net pylon": "SW_PYLON",
    "entersoft": "SW_ENTERSOFT",
    "έντερσοφτ": "SW_ENTERSOFT",
    "entersoft erp": "SW_ENTERSOFT",
    "singular": "SW_SINGULAR",
    "singular logic": "SW_SINGULAR",
    "singularlogic": "SW_SINGULAR",
    "galaxy": "SW_SINGULAR",
    "atlantis": "SW_ATLANTIS",
    "odoo": "SW_ODOO",
    # ERP General
    "erp": "SW_ERP",
    "σύστημα erp": "SW_ERP",
    "erp system": "SW_ERP",
    "μηχανογράφηση": "SW_ERP",
    "εμπορικό πρόγραμμα": "SW_ERP",
    "λογιστικό πρόγραμμα": "SW_ERP",
    # Microsoft Office
    "excel": "SW_EXCEL",
    "ms excel": "SW_EXCEL",
    "εξελ": "SW_EXCEL",
    "spreadsheets": "SW_EXCEL",
    "λογιστικά φύλλα": "SW_EXCEL",
    "pivot tables": "SW_EXCEL",
    "vlookup": "SW_EXCEL",
    "excel vba": "SW_EXCEL",
    "macros": "SW_EXCEL",
    "word": "SW_WORD",
    "ms word": "SW_WORD",
    "επεξεργασία κειμένου": "SW_WORD",
    "access": "SW_ACCESS",
    "ms access": "SW_ACCESS",
    "ms office": "SW_OFFICE",
    "office": "SW_OFFICE",
    "office 365": "SW_OFFICE",
    "microsoft 365": "SW_OFFICE",
    "powerpoint": "SW_OFFICE",
    "outlook": "SW_OFFICE",
    "teams": "SW_OFFICE",
    "χρήση η/υ": "SW_OFFICE",
    "γνώσεις πληροφορικής": "SW_OFFICE",
    "πληροφορική": "SW_OFFICE",
    # Google
    "google docs": "SW_GOOGLE",
    "google sheets": "SW_GOOGLE",
    "google suite": "SW_GOOGLE",
    "g suite": "SW_GOOGLE",
    "google workspace": "SW_GOOGLE",
    # Design/CAD
    "autocad": "SW_AUTOCAD",
    "αυτοκαντ": "SW_AUTOCAD",
    "solidworks": "SW_SOLIDWORKS",
    "photoshop": "SW_PHOTOSHOP",
    # CRM
    "crm": "SW_CRM",
    "salesforce": "SW_SALESFORCE",
    # Oracle
    "oracle": "SW_ORACLE",
    "oracle erp": "SW_ORACLE",
    "netsuite": "SW_ORACLE",
    # ==========================================================================
    # SKILLS (from cv-taxonomy.json skills section)
    # ==========================================================================
    # Accounting Skills
    "mydata": "SKILL_MYDATA",
    "my data": "SKILL_MYDATA",
    "μυντατα": "SKILL_MYDATA",
    "ααδε mydata": "SKILL_MYDATA",
    "ηλεκτρονικά βιβλία": "SKILL_MYDATA",
    "ηλεκτρονική τιμολόγηση": "SKILL_MYDATA",
    "εργάνη": "SKILL_ERGANI",
    "εργανη": "SKILL_ERGANI",
    "ergani": "SKILL_ERGANI",
    "σύστημα εργάνη": "SKILL_ERGANI",
    "ψηφιακή κάρτα εργασίας": "SKILL_ERGANI",
    "φπα": "SKILL_VAT",
    "φ.π.α.": "SKILL_VAT",
    "vat": "SKILL_VAT",
    "δηλώσεις φπα": "SKILL_VAT",
    "ενδοκοινοτικές συναλλαγές": "SKILL_VAT",
    "vies": "SKILL_VAT",
    "intrastat": "SKILL_VAT",
    "μισθοδοσία": "SKILL_PAYROLL",
    "μισθοδοσια": "SKILL_PAYROLL",
    "payroll": "SKILL_PAYROLL",
    "απδ": "SKILL_PAYROLL",
    "απδ ικα": "SKILL_PAYROLL",
    "εφκα": "SKILL_PAYROLL",
    "e-εφκα": "SKILL_PAYROLL",
    "ασφαλιστικές εισφορές": "SKILL_PAYROLL",
    "βιβλία β'": "SKILL_BOOKS_B_CLASS",
    "βιβλία β": "SKILL_BOOKS_B_CLASS",
    "β κατηγορίας": "SKILL_BOOKS_B_CLASS",
    "απλογραφικά": "SKILL_BOOKS_B_CLASS",
    "έσοδα-έξοδα": "SKILL_BOOKS_B_CLASS",
    "βιβλία γ'": "SKILL_BOOKS_G_CLASS",
    "βιβλία γ": "SKILL_BOOKS_G_CLASS",
    "γ κατηγορίας": "SKILL_BOOKS_G_CLASS",
    "διπλογραφικά": "SKILL_BOOKS_G_CLASS",
    "γενική λογιστική": "SKILL_BOOKS_G_CLASS",
    "αναλυτική λογιστική": "SKILL_BOOKS_G_CLASS",
    "ισοζύγιο": "SKILL_BOOKS_G_CLASS",
    "ισολογισμός": "SKILL_BOOKS_G_CLASS",
    "τιμολόγηση": "SKILL_INVOICING",
    "τιμολογηση": "SKILL_INVOICING",
    "έκδοση τιμολογίων": "SKILL_INVOICING",
    "παραστατικά": "SKILL_INVOICING",
    "συμφωνία τραπεζών": "SKILL_BANK_RECONCILIATION",
    "τραπεζικοί λογαριασμοί": "SKILL_BANK_RECONCILIATION",
    "e-banking": "SKILL_BANK_RECONCILIATION",
    "web banking": "SKILL_BANK_RECONCILIATION",
    "πελάτες": "SKILL_RECEIVABLES_PAYABLES",
    "προμηθευτές": "SKILL_RECEIVABLES_PAYABLES",
    "εισπράξεις": "SKILL_RECEIVABLES_PAYABLES",
    "πληρωμές": "SKILL_RECEIVABLES_PAYABLES",
    "aging report": "SKILL_RECEIVABLES_PAYABLES",
    "φορολογικές δηλώσεις": "SKILL_TAX_DECLARATIONS",
    "φόροι": "SKILL_TAX_DECLARATIONS",
    "φμυ": "SKILL_TAX_DECLARATIONS",
    "ε3": "SKILL_TAX_DECLARATIONS",
    "ε1": "SKILL_TAX_DECLARATIONS",
    "ενφια": "SKILL_TAX_DECLARATIONS",
    # Sales/Retail Skills
    "πωλήσεις": "SKILL_SALES",
    "πωλησεις": "SKILL_SALES",
    "sales": "SKILL_SALES",
    "upselling": "SKILL_SALES",
    "cross-selling": "SKILL_SALES",
    "εξυπηρέτηση πελατών": "SKILL_CUSTOMER_SERVICE",
    "customer service": "SKILL_CUSTOMER_SERVICE",
    "customer care": "SKILL_CUSTOMER_SERVICE",
    "διαχείριση παραπόνων": "SKILL_CUSTOMER_SERVICE",
    "b2b": "SKILL_B2B_SALES",
    "χονδρική": "SKILL_B2B_SALES",
    "b2c": "SKILL_B2C_SALES",
    "λιανική": "SKILL_B2C_SALES",
    "retail": "SKILL_B2C_SALES",
    "διαχείριση αποθήκης": "SKILL_INVENTORY_MANAGEMENT",
    "αποθέματα": "SKILL_INVENTORY_MANAGEMENT",
    "stock management": "SKILL_INVENTORY_MANAGEMENT",
    "warehouse management": "SKILL_INVENTORY_MANAGEMENT",
    "απογραφή": "SKILL_INVENTORY_MANAGEMENT",
    "wms": "SKILL_INVENTORY_MANAGEMENT",
    "pos": "SKILL_CASH_REGISTER",
    "ταμειακή μηχανή": "SKILL_CASH_REGISTER",
    # Management Skills
    "διαχείριση ομάδας": "SKILL_TEAM_MANAGEMENT",
    "people management": "SKILL_TEAM_MANAGEMENT",
    "διαχείριση προσωπικού": "SKILL_TEAM_MANAGEMENT",
    "coaching": "SKILL_TEAM_MANAGEMENT",
    "mentoring": "SKILL_TEAM_MANAGEMENT",
    "ηγεσία": "SKILL_LEADERSHIP",
    "leadership": "SKILL_LEADERSHIP",
    "ηγετικές ικανότητες": "SKILL_LEADERSHIP",
    "πρόγραμμα εργασίας": "SKILL_SCHEDULING",
    "βάρδιες": "SKILL_SCHEDULING",
    "shift management": "SKILL_SCHEDULING",
    # Admin Skills
    "γραμματειακή υποστήριξη": "SKILL_OFFICE_ADMIN",
    "αρχειοθέτηση": "SKILL_OFFICE_ADMIN",
    "office management": "SKILL_OFFICE_ADMIN",
    "data entry": "SKILL_OFFICE_ADMIN",
    "καταχώρηση στοιχείων": "SKILL_OFFICE_ADMIN",
    # Technical/Manufacturing Skills
    "συγκόλληση": "SKILL_WELDING",
    "συγκολληση": "SKILL_WELDING",
    "welding": "SKILL_WELDING",
    "ηλεκτροσυγκόλληση": "SKILL_WELDING",
    "ηλεκτροσυγκολληση": "SKILL_WELDING",
    "tig": "SKILL_WELDING_TIG",
    "tig welding": "SKILL_WELDING_TIG",
    "mig": "SKILL_WELDING_MIG",
    "mig welding": "SKILL_WELDING_MIG",
    "mma": "SKILL_WELDING_MMA",
    "arc welding": "SKILL_WELDING_MMA",
    "cnc": "SKILL_CNC",
    "cnc programming": "SKILL_CNC",
    "τόρνος": "SKILL_LATHE",
    "τορνος": "SKILL_LATHE",
    "lathe": "SKILL_LATHE",
    "φρέζα": "SKILL_MILLING",
    "φρεζα": "SKILL_MILLING",
    "milling": "SKILL_MILLING",
    "plc": "SKILL_PLC",
    "plc programming": "SKILL_PLC",
    "siemens": "SKILL_PLC",
    "allen bradley": "SKILL_PLC",
    # Communication Skills
    "επικοινωνία": "SKILL_COMMUNICATION",
    "communication": "SKILL_COMMUNICATION",
    "επικοινωνιακές δεξιότητες": "SKILL_COMMUNICATION",
    "οργάνωση": "SKILL_ORGANIZATION",
    "organization": "SKILL_ORGANIZATION",
    "time management": "SKILL_TIME_MANAGEMENT",
    "διαχείριση χρόνου": "SKILL_TIME_MANAGEMENT",
    # ==========================================================================
    # EDUCATION LEVELS
    # ==========================================================================
    "απόφοιτος": "secondary",
    "αποφοιτος": "secondary",
    "απολυτήριο": "secondary",
    "λύκειο": "lyceum",
    "λυκειο": "lyceum",
    "γενικό λύκειο": "lyceum",
    "επαλ": "lyceum",
    "ιεκ": "iek",
    "δ.ιεκ": "iek",
    "ιδιωτικό ιεκ": "iek",
    "τει": "tei",
    "τ.ε.ι.": "tei",
    "πτυχίο": "bachelor",
    "πτυχιο": "bachelor",
    "πτυχιούχος": "bachelor",
    "bachelor": "bachelor",
    "μεταπτυχιακό": "master",
    "μεταπτυχιακο": "master",
    "master": "master",
    "mba": "master",
    "msc": "master",
    "διδακτορικό": "doctorate",
    "διδακτορικο": "doctorate",
    "phd": "doctorate",
    "doctorate": "doctorate",
    # ==========================================================================
    # DRIVING LICENSES
    # ==========================================================================
    "δίπλωμα": "B",
    "διπλωμα": "B",
    "δίπλωμα οδήγησης": "B",
    "άδεια οδήγησης": "B",
    "αδεια οδηγησης": "B",
    "κλαρκ": "forklift",
    "περονοφόρο": "forklift",
    "περονοφορο": "forklift",
    "ανυψωτικά": "forklift",
    "forklift": "forklift",
    "γερανός": "crane",
    "γερανος": "crane",
    "crane": "crane",
    # ==========================================================================
    # LANGUAGES
    # ==========================================================================
    "ελληνικά": "el",
    "ελληνικα": "el",
    "αγγλικά": "en",
    "αγγλικα": "en",
    "english": "en",
    "γερμανικά": "de",
    "γερμανικα": "de",
    "german": "de",
    "γαλλικά": "fr",
    "γαλλικα": "fr",
    "french": "fr",
    "ισπανικά": "es",
    "ισπανικα": "es",
    "spanish": "es",
    "ιταλικά": "it",
    "ιταλικα": "it",
    "italian": "it",
    "ρωσικά": "ru",
    "ρωσικα": "ru",
    "russian": "ru",
    "βουλγαρικά": "bg",
    "βουλγαρικα": "bg",
    "αλβανικά": "sq",
    "αλβανικα": "sq",
    # ==========================================================================
    # CERTIFICATIONS
    # ==========================================================================
    "iso": "CERT_ISO",
    "iso 9001": "CERT_ISO_9001",
    "iso 14001": "CERT_ISO_14001",
    "iso 22000": "CERT_ISO_22000",
    "haccp": "CERT_HACCP",
    "gdpr": "CERT_GDPR",
    "ασφαλείας": "CERT_SAFETY",
    "ασφαλειας": "CERT_SAFETY",
    "υγιεινή και ασφάλεια": "CERT_SAFETY",
    "πρώτες βοήθειες": "CERT_FIRST_AID",
    "πρωτες βοηθειες": "CERT_FIRST_AID",
    "first aid": "CERT_FIRST_AID",
    "πιστοποίηση": "CERT_GENERIC",
    "πιστοποιηση": "CERT_GENERIC",
    "ecdl": "CERT_ECDL",
    "icdl": "CERT_ECDL",
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
