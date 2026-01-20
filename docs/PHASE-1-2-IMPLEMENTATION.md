# HR Intelligence System - Phase 1 & 2 Implementation

**Document Version**: 1.0
**Created**: 2026-01-20 (Session 38-39)
**Status**: COMPLETED & TESTED

---

## Table of Contents

1. [Overview](#1-overview)
2. [Phase 1: HR Intelligence Core](#2-phase-1-hr-intelligence-core)
3. [Phase 2: Job Posting Parser](#3-phase-2-job-posting-parser)
4. [Test Coverage](#4-test-coverage)
5. [File Summary](#5-file-summary)
6. [Usage Examples](#6-usage-examples)
7. [API Reference](#7-api-reference)

---

## 1. Overview

### 1.1 Purpose

The HR Intelligence System provides intelligent candidate analysis and ranking for recruitment queries. It transforms raw candidate data into actionable HR insights with:

- Structured analysis of job requirements
- Evidence-based candidate evaluation
- Gap analysis and risk assessment
- Bilingual support (Greek/English)
- Interview recommendations

### 1.2 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INPUT                               │
│                                                                  │
│  Natural Language Query          OR          Job Posting Text    │
│  "Λογιστές με SAP"                          "Ζητείται Λογιστής..." │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 2: JOB PARSER                           │
│                                                                  │
│  JobParser.parse(text) → JobRequirements                        │
│  - Extracts roles, skills, experience, languages                │
│  - Detects language (Greek/English)                             │
│  - Sets priority levels (must/should/nice)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 PHASE 1: HR INTELLIGENCE CORE                    │
│                                                                  │
│  HRIntelligenceAnalyzer.analyze(input) → HRAnalysisReport       │
│  - Evaluates candidates against requirements                    │
│  - Ranks by suitability                                         │
│  - Generates evidence-based analysis                            │
│  - Provides HR recommendations                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FORMATTED OUTPUT                            │
│                                                                  │
│  - format_text_report() → Human-readable text                   │
│  - format_api_response() → JSON for API                         │
│  - format_compact_summary() → One-line summary                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM Model | Claude Sonnet 4.5 | Balance of quality and cost |
| Language Detection | Greek character ratio >30% | Simple, reliable for Greek/English |
| JSON Extraction | Multiple fallback methods | Handle various LLM response formats |
| Async/Sync | Both supported | Async for Lambda, sync wrapper for convenience |
| Bilingual | Auto-detect, respond in same | Natural user experience |

---

## 2. Phase 1: HR Intelligence Core

### 2.1 Module Structure

```
src/lcmgo_cagenai/hr_intelligence/
├── __init__.py          # Module exports
├── schema.py            # Data structures (15+ dataclasses)
├── analyzer.py          # Main HRIntelligenceAnalyzer class
├── prompts.py           # Bilingual LLM prompts
└── formatter.py         # Response formatting utilities
```

### 2.2 Data Structures (schema.py)

#### Input Structures

```python
@dataclass
class LanguageRequirement:
    language_code: str      # "en", "el", "de"
    language_name: str      # "English", "Greek"
    min_level: str | None   # "A1" to "C2"
    is_required: bool       # True = must have

@dataclass
class JobRequirements:
    source_type: Literal["query", "job_posting"]
    source_text: str
    detected_language: str  # "el" or "en"
    roles: list[str]
    role_priority: str      # "must" | "should" | "nice"
    min_experience_years: float | None
    max_experience_years: float | None
    software: list[str]
    certifications: list[str]
    skills: list[str]
    languages: list[LanguageRequirement]
    locations: list[str]
    remote_acceptable: bool
    education_level: str | None
    education_fields: list[str]
    weights: dict[str, float]  # Scoring weights

@dataclass
class CandidateProfile:
    candidate_id: str
    first_name: str
    last_name: str
    email: str | None
    total_experience_years: float | None
    experience_entries: list[dict]
    roles: list[str]
    software: list[str]
    skills: list[str]
    certifications: list[str]
    languages: list[dict]
    education: list[dict]
    city: str | None

    @property
    def full_name(self) -> str

@dataclass
class HRAnalysisInput:
    original_query: str
    requirements: JobRequirements
    candidates: list[CandidateProfile]
    relaxations_applied: list[str]
    direct_result_count: int
    total_result_count: int
```

#### Output Structures

```python
@dataclass
class RequestAnalysis:
    summary: str
    mandatory_criteria: list[str]
    preferred_criteria: list[str]
    inferred_criteria: list[str]

@dataclass
class QueryOutcome:
    direct_matches: int
    total_matches: int
    relaxation_applied: bool
    zero_results_reason: str | None

@dataclass
class CriteriaRelaxation:
    original: str
    relaxed_to: str
    reasoning: str

@dataclass
class CriteriaExpansion:
    relaxations: list[CriteriaRelaxation]
    business_rationale: str

@dataclass
class CandidateEvidence:
    criterion: str
    candidate_value: str
    source: str
    confidence: str  # "Confirmed" | "Likely" | "Uncertain"

@dataclass
class CandidateGap:
    criterion: str
    gap_description: str
    severity: str  # "Minor" | "Moderate" | "Major"
    mitigation: str | None

@dataclass
class AssessmentScore:
    score: str  # "High" | "Medium" | "Low"
    evidence: list[str]
    notes: str

@dataclass
class RankedCandidate:
    rank: int
    candidate_id: str
    candidate_name: str
    overall_suitability: str
    match_percentage: float
    strengths: list[CandidateEvidence]
    gaps: list[CandidateGap]
    risks: list[str]
    role_match: AssessmentScore | None
    experience_match: AssessmentScore | None
    skills_match: AssessmentScore | None
    language_match: AssessmentScore | None
    interview_focus: list[str]

@dataclass
class HRRecommendation:
    top_candidates: list[str]
    recommendation_summary: str
    interview_priorities: list[str]
    hiring_suggestions: list[str]
    alternative_search: str | None

@dataclass
class HRAnalysisReport:
    request_analysis: RequestAnalysis
    query_outcome: QueryOutcome
    criteria_expansion: CriteriaExpansion | None
    ranked_candidates: list[RankedCandidate]
    hr_recommendation: HRRecommendation
    analysis_language: str
    analysis_timestamp: datetime
    llm_model: str
    latency_ms: int
```

### 2.3 Main Analyzer (analyzer.py)

```python
class HRIntelligenceAnalyzer:
    """
    HR Intelligence Analyzer that evaluates, compares, and ranks candidates.
    Uses Claude Sonnet 4.5 via Amazon Bedrock.
    """

    GREEK_PATTERN = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF]")

    def __init__(
        self,
        llm_provider: BedrockProvider,
        model: ModelType = ModelType.CLAUDE_SONNET,
        max_candidates: int = 10,
    )

    async def analyze(self, input_data: HRAnalysisInput) -> HRAnalysisReport:
        """Perform HR intelligence analysis on candidates."""

    def _detect_language(self, text: str) -> str:
        """Detect language: 'el' for Greek, 'en' for English."""

    def _extract_json(self, content: str) -> dict | None:
        """Extract JSON from LLM response (handles multiple formats)."""

    def _create_empty_report(...) -> HRAnalysisReport:
        """Create report for empty candidates case."""

# Synchronous wrapper
def analyze_candidates_sync(
    llm_provider: BedrockProvider,
    original_query: str,
    requirements: JobRequirements,
    candidates: list[CandidateProfile],
    direct_result_count: int = 0,
    relaxations_applied: list[str] | None = None,
) -> HRAnalysisReport
```

### 2.4 Prompts (prompts.py)

The module contains bilingual prompts for Greek and English:

```python
SYSTEM_PROMPT_EL = """
ΡΟΛΟΣ: Είσαι Ειδικός HR Intelligence...
"""

SYSTEM_PROMPT_EN = """
ROLE: You are an HR Intelligence Specialist...
"""

RESPONSE_SCHEMA = {
    # JSON schema for LLM response validation
}

def get_system_prompt(language: str) -> str
def get_user_message(query: str, language: str) -> str
def build_analysis_prompt(...) -> str
```

### 2.5 Formatters (formatter.py)

```python
def format_text_report(report: HRAnalysisReport) -> str:
    """Format as human-readable text with sections."""

def format_api_response(
    report: HRAnalysisReport,
    include_text_summary: bool = False
) -> dict:
    """Format for JSON API response."""

def format_compact_summary(report: HRAnalysisReport) -> str:
    """One-line summary for logging."""
```

---

## 3. Phase 2: Job Posting Parser

### 3.1 Module Location

```
src/lcmgo_cagenai/parser/
├── __init__.py          # Updated with JobParser exports
└── job_parser.py        # NEW: Job posting parser

prompts/job_parsing/
└── v1.0.0.txt           # NEW: Extraction prompt
```

### 3.2 JobParser Class (job_parser.py)

```python
class JobParser:
    """
    Job Posting Parser using Claude Sonnet for structured extraction.
    Extracts JobRequirements from unstructured job posting text.
    """

    MODEL = ModelType.CLAUDE_SONNET
    MAX_RETRIES = 2
    MAX_TOKENS = 4096

    def __init__(
        self,
        region: str = "eu-north-1",
        prompt_version: str = "v1.0.0",
        llm_provider: BedrockProvider | None = None,
    )

    async def parse(self, job_posting_text: str) -> JobRequirements:
        """Parse job posting text into JobRequirements."""

    def _extract_json(self, content: str) -> dict | None:
        """Extract JSON from LLM response."""

    def _build_requirements(self, data: dict, source_text: str) -> JobRequirements:
        """Build JobRequirements from parsed JSON."""

# Synchronous wrapper
def parse_job_posting_sync(
    job_posting_text: str,
    region: str = "eu-north-1",
    llm_provider: BedrockProvider | None = None,
) -> JobRequirements

# Utility for query-based requirements
def extract_requirements_from_query(
    query_text: str,
    detected_language: str = "en",
) -> JobRequirements
```

### 3.3 Extraction Prompt (prompts/job_parsing/v1.0.0.txt)

The prompt extracts:

| Field | Description | Example |
|-------|-------------|---------|
| roles | Job titles | ["accountant", "financial_analyst"] |
| experience | Years required | min: 3, max: 7 |
| software | Tools/systems | ["SAP", "Excel"] |
| certifications | Professional certs | ["CPA", "ACCA"] |
| skills | Technical skills | ["financial_reporting"] |
| languages | Language requirements | [{code: "en", level: "B2"}] |
| education | Degree requirements | "bachelor", ["accounting"] |
| locations | Work locations | ["Athens"] |
| remote_acceptable | Remote work | true/false |

Priority mapping:
- "απαραίτητο", "required", "must have" → "must"
- "επιθυμητό", "preferred" → "nice"
- Default → "should"

### 3.4 Module Exports

Updated `parser/__init__.py`:

```python
from .job_parser import (
    JobParser,
    parse_job_posting_sync,
    extract_requirements_from_query,
)

__all__ = [
    # CV parser (existing)
    "CVParser",
    "parse_cv",
    # Job parser (Phase 2)
    "JobParser",
    "parse_job_posting_sync",
    "extract_requirements_from_query",
    # ... other exports
]
```

---

## 4. Test Coverage

### 4.1 Test Summary

| Test Suite | File | Tests | Status |
|------------|------|-------|--------|
| HR Intelligence Unit | `tests/unit/test_hr_intelligence.py` | 27 | PASSED |
| Job Parser Unit | `tests/unit/test_job_parser.py` | 18 | PASSED |
| HR Intelligence Code Paths | `tests/test_code_paths.py` | 15 | PASSED |
| Job Parser Code Paths | `tests/test_job_parser_paths.py` | 20 | PASSED |
| Integration | `tests/test_integration_hr_job.py` | 10 | PASSED |
| **TOTAL** | | **90** | **ALL PASSED** |

### 4.2 Unit Test Coverage

#### HR Intelligence (27 tests)

```
TestLanguageRequirement
  - test_creation
  - test_defaults

TestJobRequirements
  - test_creation
  - test_to_dict
  - test_default_weights

TestCandidateProfile
  - test_full_name
  - test_to_dict

TestHRAnalysisReport
  - test_to_dict

TestParseHRAnalysisFromJson
  - test_parse_full_response
  - test_parse_with_criteria_expansion

TestPrompts
  - test_get_system_prompt_greek
  - test_get_system_prompt_english
  - test_get_user_message_greek
  - test_get_user_message_english
  - test_build_analysis_prompt

TestHRIntelligenceAnalyzer
  - test_language_detection_greek
  - test_language_detection_english
  - test_language_detection_mixed
  - test_extract_json_direct
  - test_extract_json_from_markdown
  - test_extract_json_with_surrounding_text

TestFormatters
  - test_format_compact_summary_greek
  - test_format_compact_summary_english
  - test_format_compact_summary_empty
  - test_format_text_report_greek
  - test_format_text_report_english

TestHRAnalysisInput
  - test_creation
```

#### Job Parser (18 tests)

```
TestJobParserInit
  - test_default_init
  - test_custom_prompt_version

TestJobParserParse
  - test_parse_greek_job_posting
  - test_parse_english_job_posting
  - test_parse_empty_text_raises
  - test_parse_stores_source_text

TestJobParserJsonExtraction
  - test_extract_direct_json
  - test_extract_json_from_markdown
  - test_extract_json_with_surrounding_text
  - test_extract_json_invalid_returns_none

TestJobParserBuildRequirements
  - test_build_with_all_fields
  - test_build_with_minimal_fields

TestSyncWrapper
  - test_parse_job_posting_sync

TestExtractRequirementsFromQuery
  - test_creates_query_type_requirements
  - test_default_language_is_english

TestLanguageRequirementParsing
  - test_parses_multiple_languages
  - test_handles_empty_languages

TestJobRequirementsToDict
  - test_to_dict_complete
```

### 4.3 Code Path Tests

Tests cover:
- Empty candidates handling
- Error handling (LLM failures, malformed JSON)
- Input validation
- Default value assignment
- Prompt template loading and caching
- Language detection edge cases
- JSON extraction variations
- Serialization

### 4.4 Integration Tests

Tests cover:
- JobParser → JobRequirements → HRAnalysisInput pipeline
- Full end-to-end workflow
- Cross-module compatibility
- Language consistency
- Serialization for API
- Empty results handling
- Scoring weights availability

---

## 5. File Summary

### 5.1 Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/lcmgo_cagenai/hr_intelligence/__init__.py` | 65 | Module exports |
| `src/lcmgo_cagenai/hr_intelligence/schema.py` | 549 | Data structures |
| `src/lcmgo_cagenai/hr_intelligence/analyzer.py` | 393 | Main analyzer |
| `src/lcmgo_cagenai/hr_intelligence/prompts.py` | ~400 | LLM prompts |
| `src/lcmgo_cagenai/hr_intelligence/formatter.py` | 281 | Formatters |
| `src/lcmgo_cagenai/parser/job_parser.py` | 230 | Job parser |
| `prompts/job_parsing/v1.0.0.txt` | 120 | Extraction prompt |
| `tests/unit/test_hr_intelligence.py` | 450 | Unit tests |
| `tests/unit/test_job_parser.py` | 380 | Unit tests |
| `tests/test_code_paths.py` | 658 | Code path tests |
| `tests/test_job_parser_paths.py` | 520 | Code path tests |
| `tests/test_integration_hr_job.py` | 350 | Integration tests |

### 5.2 Files Modified

| File | Changes |
|------|---------|
| `src/lcmgo_cagenai/parser/__init__.py` | Added JobParser exports |

### 5.3 Git Commits

| Commit | Description |
|--------|-------------|
| `ba0e38e` | feat: Implement Phase 1 - HR Intelligence Core |
| `87df6fa` | fix: Resolve test failures and add code path verification |
| `45e5de8` | feat: Implement Phase 2 - Job Posting Parser |
| `9da65fd` | test: Add comprehensive test suite for Phase 1 & 2 |

---

## 6. Usage Examples

### 6.1 Basic HR Analysis

```python
from lcmgo_cagenai.hr_intelligence import (
    HRIntelligenceAnalyzer,
    HRAnalysisInput,
    JobRequirements,
    CandidateProfile,
)
from lcmgo_cagenai.llm.provider import BedrockProvider

# Initialize
llm = BedrockProvider(region="eu-north-1")
analyzer = HRIntelligenceAnalyzer(llm)

# Create requirements
requirements = JobRequirements(
    source_type="query",
    source_text="Accountants with SAP",
    detected_language="en",
    roles=["accountant"],
    software=["SAP"],
    min_experience_years=3,
)

# Create candidate profiles
candidates = [
    CandidateProfile(
        candidate_id="c1",
        first_name="John",
        last_name="Doe",
        total_experience_years=5.0,
        software=["SAP", "Excel"],
        certifications=["CPA"],
    )
]

# Run analysis
input_data = HRAnalysisInput(
    original_query="Accountants with SAP",
    requirements=requirements,
    candidates=candidates,
    direct_result_count=1,
    total_result_count=1,
)

report = await analyzer.analyze(input_data)
```

### 6.2 Parse Job Posting

```python
from lcmgo_cagenai.parser import JobParser, parse_job_posting_sync

# Async usage
parser = JobParser()
requirements = await parser.parse("""
Ζητείται Λογιστής Α' Τάξης με:
- 5+ χρόνια εμπειρία
- Άριστη γνώση SAP
- Αγγλικά επίπεδο B2
""")

# Sync usage
requirements = parse_job_posting_sync(job_posting_text)
```

### 6.3 Full Pipeline

```python
from lcmgo_cagenai.parser import JobParser
from lcmgo_cagenai.hr_intelligence import (
    HRIntelligenceAnalyzer,
    HRAnalysisInput,
    format_text_report,
)

# Step 1: Parse job posting
parser = JobParser()
requirements = await parser.parse(job_posting_text)

# Step 2: Get candidates from database
candidates = get_candidates_from_db(requirements)

# Step 3: Run HR analysis
analyzer = HRIntelligenceAnalyzer(llm)
report = await analyzer.analyze(HRAnalysisInput(
    original_query=job_posting_text,
    requirements=requirements,
    candidates=candidates,
    direct_result_count=len(candidates),
    total_result_count=len(candidates),
))

# Step 4: Format output
text_report = format_text_report(report)
print(text_report)
```

---

## 7. API Reference

### 7.1 HR Intelligence Module

```python
# Main exports
from lcmgo_cagenai.hr_intelligence import (
    # Main class
    HRIntelligenceAnalyzer,
    analyze_candidates_sync,

    # Input types
    HRAnalysisInput,
    JobRequirements,
    LanguageRequirement,
    CandidateProfile,

    # Output types
    HRAnalysisReport,
    RequestAnalysis,
    QueryOutcome,
    CriteriaExpansion,
    CriteriaRelaxation,
    RankedCandidate,
    CandidateEvidence,
    CandidateGap,
    AssessmentScore,
    HRRecommendation,

    # Formatters
    format_text_report,
    format_api_response,
    format_compact_summary,
)
```

### 7.2 Job Parser Module

```python
# Main exports
from lcmgo_cagenai.parser import (
    JobParser,
    parse_job_posting_sync,
    extract_requirements_from_query,
)
```

### 7.3 Key Methods

| Method | Input | Output |
|--------|-------|--------|
| `HRIntelligenceAnalyzer.analyze()` | `HRAnalysisInput` | `HRAnalysisReport` |
| `JobParser.parse()` | `str` (job posting) | `JobRequirements` |
| `format_text_report()` | `HRAnalysisReport` | `str` |
| `format_api_response()` | `HRAnalysisReport` | `dict` |
| `format_compact_summary()` | `HRAnalysisReport` | `str` |

---

## Appendix: Running Tests

```bash
# Run all unit tests
py -m pytest tests/unit -v

# Run code path tests
py tests/test_code_paths.py
py tests/test_job_parser_paths.py

# Run integration tests
py tests/test_integration_hr_job.py

# Run everything
py -m pytest tests/ -v
```

---

**Document Status**: Complete
**Next Phase**: Phase 3 - Query Lambda Integration
