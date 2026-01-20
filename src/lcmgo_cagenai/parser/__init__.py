"""
Parser module for LCMGoCloud-CAGenAI.

Parses extracted CV text and job postings into structured data using Claude Sonnet 4.5.
Includes taxonomy mapping, database writing, and OpenSearch indexing.

See docs/08-BACKEND-FEATURES.md for architecture details.
See docs/HR-INTELLIGENCE-UNIFIED.md for job parsing details.
"""

from .cv_parser import CVParser, parse_cv
from .db_writer import DatabaseWriter, WriteVerification
from .job_parser import JobParser, extract_requirements_from_query, parse_job_posting_sync
from .schema import (
    CVCompletenessAudit,
    ParsedCertification,
    ParsedCV,
    ParsedDrivingLicense,
    ParsedEducation,
    ParsedExperience,
    ParsedLanguage,
    ParsedPersonal,
    ParsedSkill,
)
from .search_indexer import SearchIndexer
from .taxonomy_mapper import TaxonomyMapper
from .validators import ValidationResult, validate_contact_info, validate_email, validate_phone

__all__ = [
    # CV parser
    "CVParser",
    "parse_cv",
    # Job parser (Phase 2)
    "JobParser",
    "parse_job_posting_sync",
    "extract_requirements_from_query",
    # Schema
    "ParsedCV",
    "ParsedPersonal",
    "ParsedEducation",
    "ParsedExperience",
    "ParsedSkill",
    "ParsedLanguage",
    "ParsedCertification",
    "ParsedDrivingLicense",
    "CVCompletenessAudit",  # Task 1.3 - CV Completeness Audit
    # Support classes
    "TaxonomyMapper",
    "DatabaseWriter",
    "WriteVerification",  # Task 1.2 - Post-write verification
    "SearchIndexer",
    # Validators - Task 1.7
    "ValidationResult",
    "validate_email",
    "validate_phone",
    "validate_contact_info",
]
