"""
CV Parser module for LCMGoCloud-CAGenAI.

Parses extracted CV text into structured data using Claude Sonnet 4.5.
Includes taxonomy mapping, database writing, and OpenSearch indexing.

See docs/08-BACKEND-FEATURES.md for architecture details.
"""

from .cv_parser import CVParser, parse_cv
from .db_writer import DatabaseWriter, WriteVerification
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

__all__ = [
    # Main parser
    "CVParser",
    "parse_cv",
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
]
