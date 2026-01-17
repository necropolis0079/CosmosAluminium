"""
OpenSearch search module for vector similarity search and hybrid text search.

Provides:
- OpenSearchClient: Wrapper for OpenSearch operations
- INDEX_MAPPINGS: Pre-configured index mappings for candidates, jobs
- create_indices: Helper to create all required indices
"""

from .client import OpenSearchClient, get_client
from .mappings import (
    CANDIDATES_INDEX,
    CANDIDATES_MAPPING,
    INDEX_SETTINGS,
    JOBS_INDEX,
    JOBS_MAPPING,
)

__all__ = [
    "OpenSearchClient",
    "get_client",
    "INDEX_SETTINGS",
    "CANDIDATES_INDEX",
    "CANDIDATES_MAPPING",
    "JOBS_INDEX",
    "JOBS_MAPPING",
]
