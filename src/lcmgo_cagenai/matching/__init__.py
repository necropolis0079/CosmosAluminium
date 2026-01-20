"""
Job Matching Module

Intelligent candidate matching that finds best matches even when
no candidate meets ALL criteria.
"""

from .job_matcher import JobMatcher, MatchResult, CandidateMatch
from .response_formatter import ResponseFormatter

__all__ = [
    "JobMatcher",
    "MatchResult",
    "CandidateMatch",
    "ResponseFormatter",
]
