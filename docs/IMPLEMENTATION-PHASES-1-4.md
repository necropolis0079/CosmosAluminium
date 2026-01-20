# HR Intelligence System - Implementation Documentation

**Document Version**: 1.1
**Created**: 2026-01-20 (Session 39)
**Last Updated**: 2026-01-20 (Session 40 - Phase 5 Testing)
**Status**: ALL PHASES COMPLETE (1-5)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Phase 1: HR Intelligence Core](#2-phase-1-hr-intelligence-core)
3. [Phase 2: Job Posting Parser](#3-phase-2-job-posting-parser)
4. [Phase 3: Query Lambda Integration](#4-phase-3-query-lambda-integration)
5. [Phase 4: Dynamic Taxonomy Aliases](#5-phase-4-dynamic-taxonomy-aliases)
6. [Test Coverage Summary](#6-test-coverage-summary)
7. [File Inventory](#7-file-inventory)
8. [Git Commit History](#8-git-commit-history)
9. [API Reference](#9-api-reference)
10. [Rollback Procedures](#10-rollback-procedures)

---

## 1. Executive Summary

### 1.1 What Was Built

A complete HR Intelligence system that provides intelligent candidate analysis and ranking for recruitment queries. The system:

- **Analyzes job requirements** from natural language queries or job postings
- **Evaluates candidates** against requirements with evidence-based scoring
- **Ranks candidates** by suitability with detailed gap analysis
- **Provides HR recommendations** for interviews and hiring decisions
- **Supports Greek and English** with automatic language detection
- **Loads taxonomy dynamically** from PostgreSQL for self-updating queries

### 1.2 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER INPUT                                  │
│                                                                          │
│  NL Query: "Λογιστές με SAP"    OR    Job Posting: "Ζητείται Λογιστής"  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PHASE 4: DYNAMIC TAXONOMY                             │
│                                                                          │
│  DynamicAliasLoader → Load aliases from PostgreSQL taxonomy tables      │
│  - Skill, role, software, certification taxonomies                      │
│  - TTL-based caching (60 min default)                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PHASE 2: JOB PARSER                                   │
│                                                                          │
│  JobParser.parse(text) → JobRequirements                                │
│  - Extract roles, skills, experience, languages, education              │
│  - Detect language (Greek/English)                                      │
│  - Set priority levels (must/should/nice)                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 PHASE 1: HR INTELLIGENCE CORE                            │
│                                                                          │
│  HRIntelligenceAnalyzer.analyze(input) → HRAnalysisReport               │
│  - Evaluate candidates against requirements                             │
│  - Rank by suitability with evidence                                    │
│  - Generate gap analysis and risks                                      │
│  - Provide HR recommendations                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 PHASE 3: QUERY LAMBDA INTEGRATION                        │
│                                                                          │
│  Query Handler → SQL Execution → HR Analysis → API Response             │
│  - Automatic analysis when execute=True                                 │
│  - Candidate profile enrichment from SQL results                        │
│  - Error handling with graceful fallback                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         API RESPONSE                                     │
│                                                                          │
│  {                                                                       │
│    "results": [...],           // Raw candidates                        │
│    "hr_analysis": {            // Phase 1 output                        │
│      "ranked_candidates": [...],                                        │
│      "hr_recommendation": {...}                                         │
│    }                                                                     │
│  }                                                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Implementation Timeline

| Phase | Description | Commit | Status |
|-------|-------------|--------|--------|
| 1 | HR Intelligence Core | `ba0e38e` | ✅ Complete |
| 2 | Job Posting Parser | `45e5de8` | ✅ Complete |
| 3 | Query Lambda Integration | `68b63b4` | ✅ Complete |
| 4 | Dynamic Taxonomy Aliases | `525b420` | ✅ Complete |

---

## 2. Phase 1: HR Intelligence Core

### 2.1 Purpose

Provide intelligent candidate analysis and ranking using Claude Sonnet 4.5 via Amazon Bedrock.

### 2.2 Module Structure

```
src/lcmgo_cagenai/hr_intelligence/
├── __init__.py          # Module exports (65 lines)
├── schema.py            # 13 dataclasses (350 lines)
├── analyzer.py          # HRIntelligenceAnalyzer class (280 lines)
├── prompt_builder.py    # LLM prompt construction (200 lines)
└── formatter.py         # Output formatters (180 lines)
```

### 2.3 Key Components

#### 2.3.1 Data Structures (schema.py)

| Dataclass | Purpose | Key Fields |
|-----------|---------|------------|
| `JobRequirements` | Input requirements | roles, software, skills, experience, priorities |
| `CandidateProfile` | Candidate data | name, experience, skills, software, certifications |
| `HRAnalysisInput` | Analysis input | query, requirements, candidates, counts |
| `HRAnalysisReport` | Analysis output | request_analysis, ranked_candidates, recommendation |
| `RankedCandidate` | Single candidate | rank, match_percentage, strengths, gaps, risks |
| `CandidateEvidence` | Evidence item | criterion, value, source, confidence |
| `CandidateGap` | Gap item | criterion, description, severity, mitigation |
| `HRRecommendation` | Final recommendation | top_candidates, summary, priorities, suggestions |

#### 2.3.2 HRIntelligenceAnalyzer (analyzer.py)

```python
class HRIntelligenceAnalyzer:
    """Main analyzer class using Claude Sonnet."""

    MODEL = ModelType.CLAUDE_SONNET
    MAX_CANDIDATES = 10
    MAX_TOKENS = 4096

    async def analyze(self, input_data: HRAnalysisInput) -> HRAnalysisReport:
        """Analyze candidates and generate HR report."""

    def _detect_language(self, text: str) -> str:
        """Detect Greek vs English (30% Greek char threshold)."""

    def _parse_response(self, content: str) -> HRAnalysisReport:
        """Parse LLM JSON response into dataclasses."""
```

#### 2.3.3 Formatters (formatter.py)

| Function | Output | Use Case |
|----------|--------|----------|
| `format_text_report(report)` | Human-readable text | Console display |
| `format_api_response(report)` | JSON dict | API responses |
| `format_compact_summary(report)` | One-line string | Logging, summaries |

### 2.4 LLM Prompt Structure

The prompt includes:
1. **System context**: HR analyst role, language instruction
2. **Requirements section**: Mandatory vs preferred criteria
3. **Candidate data**: Full profiles with experience, skills, etc.
4. **Output schema**: Exact JSON structure expected
5. **Rules**: Evidence requirements, no hallucination, always suggest alternatives

### 2.5 Scoring Weights

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| Role Match | 30% | Primary fit indicator |
| Experience | 25% | Critical for senior roles |
| Skills | 20% | Technical capabilities |
| Software | 15% | Tool proficiency |
| Certifications | 10% | Nice-to-have qualifications |

---

## 3. Phase 2: Job Posting Parser

### 3.1 Purpose

Extract structured job requirements from unstructured job posting text (Greek or English).

### 3.2 Module Structure

```
src/lcmgo_cagenai/parser/job_parser.py    # Main parser (311 lines)
prompts/job_parsing/v1.0.0.txt            # Extraction prompt (120 lines)
```

### 3.3 Key Components

#### 3.3.1 JobParser Class

```python
class JobParser:
    """Parse job postings using Claude Sonnet."""

    MODEL = ModelType.CLAUDE_SONNET
    MAX_RETRIES = 2
    MAX_TOKENS = 4096

    async def parse(self, job_posting_text: str) -> JobRequirements:
        """Parse job posting into structured requirements."""

    def _extract_json(self, content: str) -> dict | None:
        """Extract JSON from LLM response (multiple fallback methods)."""

    def _build_requirements(self, data: dict, source_text: str) -> JobRequirements:
        """Build JobRequirements from parsed JSON."""
```

#### 3.3.2 JSON Extraction Methods

1. **Direct parse**: Try `json.loads(content)` first
2. **Markdown block**: Extract from ```json...``` blocks
3. **Brace matching**: Find outermost `{...}` in text

#### 3.3.3 Extraction Fields

| Field | Type | Description |
|-------|------|-------------|
| `roles` | list[str] | Job role categories |
| `min_experience_years` | int | Minimum experience |
| `max_experience_years` | int | Maximum experience (if specified) |
| `software` | list[str] | Required software tools |
| `certifications` | list[str] | Required certifications |
| `skills` | list[str] | Required skills |
| `languages` | list[LanguageRequirement] | Language requirements with levels |
| `locations` | list[str] | Work locations |
| `remote_acceptable` | bool | Remote work allowed |
| `education_level` | str | Minimum education |
| `education_fields` | list[str] | Relevant fields of study |

#### 3.3.4 Priority Mapping

| Greek Term | English Term | Priority |
|------------|--------------|----------|
| απαραίτητο | required | must |
| απαραίτητα | required | must |
| επιθυμητό | preferred | nice |
| επιθυμητά | preferred | nice |
| (default) | (default) | should |

### 3.4 Utility Functions

```python
def parse_job_posting_sync(text: str, ...) -> JobRequirements:
    """Synchronous wrapper for Lambda handlers."""

def extract_requirements_from_query(query_text: str, ...) -> JobRequirements:
    """Create minimal JobRequirements from query text."""
```

---

## 4. Phase 3: Query Lambda Integration

### 4.1 Purpose

Integrate HR Intelligence into the query Lambda handler so every executed query automatically includes HR analysis.

### 4.2 Changes to Query Handler

**File**: `lambda/query/handler.py`

#### 4.2.1 New Parameter

```python
# New parameter added to handler
include_hr_analysis = body.get("include_hr_analysis", True)  # Default: enabled
```

#### 4.2.2 Integration Flow

```python
# After SQL execution returns candidates
if execute and include_hr_analysis:
    candidates_to_analyze = result.get("results", [])

    # Handle job matching fallback candidates
    if result.get("fallback_used") and result.get("job_matching"):
        candidates_to_analyze = result["job_matching"].get("candidates", [])

    if candidates_to_analyze:
        hr_analysis = run_hr_intelligence(
            user_query=user_query,
            candidates=candidates_to_analyze,
            translation=result.get("translation", {}),
            direct_count=...,
            total_count=...,
            relaxation_applied=...,
        )
        if hr_analysis:
            result["hr_analysis"] = hr_analysis
```

#### 4.2.3 New Function: run_hr_intelligence()

```python
def run_hr_intelligence(
    user_query: str,
    candidates: list[dict],
    translation: dict,
    direct_count: int,
    total_count: int,
    relaxation_applied: bool,
) -> dict | None:
    """
    Run HR Intelligence analysis on candidates.

    1. Import HR Intelligence modules
    2. Convert raw dicts to CandidateProfile objects
    3. Create JobRequirements from translation filters
    4. Run HRIntelligenceAnalyzer.analyze()
    5. Return formatted API response
    """
```

#### 4.2.4 Candidate Profile Mapping

| SQL Result Field | CandidateProfile Field |
|------------------|------------------------|
| `candidate_id` / `id` | `candidate_id` |
| `first_name` | `first_name` |
| `last_name` | `last_name` |
| `email` | `email` |
| `total_experience_years` | `total_experience_years` |
| `roles` | `roles` |
| `skills` | `skills` |
| `soft_skills` | `soft_skills` |
| `software` | `software` |
| `certifications` | `certifications` |
| `languages` | `languages` |
| `education` | `education` |
| `city` / `current_location` / `location` | `city` |
| `region` | `region` |
| `experience_entries` | `experience_entries` |

#### 4.2.5 Error Handling

- If HR Intelligence import fails: Log warning, return None
- If no candidates: Log info, skip analysis
- If analysis fails: Log error with traceback, set `hr_analysis_error` in response
- **Graceful fallback**: Raw candidates always returned even if HR analysis fails

### 4.3 API Response Structure

```json
{
  "statusCode": 200,
  "body": {
    "query_type": "structured",
    "original_query": "Λογιστές με SAP",
    "translation": { ... },
    "sql": { ... },
    "results": [ /* raw candidates */ ],
    "result_count": 5,

    "hr_analysis": {
      "request_analysis": {
        "summary": "...",
        "mandatory_criteria": [...],
        "preferred_criteria": [...],
        "inferred_criteria": [...]
      },
      "query_outcome": {
        "direct_matches": 5,
        "total_matches": 5,
        "relaxation_applied": false
      },
      "ranked_candidates": [
        {
          "rank": 1,
          "candidate_id": "uuid",
          "candidate_name": "...",
          "overall_suitability": "High",
          "match_percentage": 85.0,
          "strengths": [...],
          "gaps": [...],
          "risks": [...],
          "interview_focus": [...]
        }
      ],
      "hr_recommendation": {
        "top_candidates": [...],
        "recommendation_summary": "...",
        "interview_priorities": [...],
        "hiring_suggestions": [...]
      },
      "analysis_language": "el",
      "latency_ms": 3500
    },

    "request_id": "abc123",
    "latency_ms": 5200
  }
}
```

---

## 5. Phase 4: Dynamic Taxonomy Aliases

### 5.1 Purpose

Load taxonomy aliases dynamically from PostgreSQL instead of using static hardcoded dictionaries. This allows queries to automatically use the latest taxonomy data without code changes.

### 5.2 Module Structure

```
src/lcmgo_cagenai/query/dynamic_aliases.py    # Main module (450 lines)
tests/unit/test_dynamic_aliases.py            # Unit tests (400 lines)
```

### 5.3 Key Components

#### 5.3.1 AliasEntry Dataclass

```python
@dataclass
class AliasEntry:
    """Single alias mapping entry."""
    canonical_id: str           # e.g., "ACCOUNTANT"
    source_table: str           # "skill_taxonomy", "role_taxonomy", etc.
    source_language: str        # "en", "el", or "both"
    match_type: str             # "name_en", "alias_el", "abbreviation", etc.
    primary_name: str           # Display name
    confidence: float = 1.0     # 1.0 for names, 0.95 for aliases, 0.98 for abbreviations
    category: str | None = None # Category/department if available
```

#### 5.3.2 AliasCache

```python
@dataclass
class AliasCache:
    """Cache container with TTL checking."""
    aliases: dict[str, AliasEntry]
    loaded_at: datetime | None
    entry_count: int

    def is_stale(self, ttl_minutes: int) -> bool:
        """Check if cache needs refresh."""
```

#### 5.3.3 DynamicAliasLoader

```python
class DynamicAliasLoader:
    """Load and cache taxonomy aliases from PostgreSQL."""

    DEFAULT_TTL_MINUTES = 60

    def __init__(
        self,
        db_secret_arn: str,
        cache_ttl_minutes: int = 60,
        region: str = "eu-north-1",
    ):
        pass

    async def load_all(self) -> dict[str, AliasEntry]:
        """Load all aliases from all taxonomy tables."""

    async def reload(self) -> dict[str, AliasEntry]:
        """Force reload, ignoring cache."""

    async def reload_if_stale(self) -> bool:
        """Reload only if cache expired."""

    def get_cached(self) -> dict[str, AliasEntry]:
        """Get current cache without loading."""
```

#### 5.3.4 Taxonomy Tables Loaded

| Table | Fields Used | Alias Types |
|-------|-------------|-------------|
| `skill_taxonomy` | canonical_id, name_en, name_el, aliases_en, aliases_el, category | name_en, name_el, alias_en, alias_el |
| `role_taxonomy` | canonical_id, name_en, name_el, aliases_en, aliases_el, department | name_en, name_el, alias_en, alias_el |
| `software_taxonomy` | canonical_id, name, aliases, category | name, alias |
| `certification_taxonomy` | canonical_id, name_en, name_el, aliases, abbreviations, issuing_organization | name_en, name_el, alias, abbreviation |

#### 5.3.5 Confidence Levels

| Match Type | Confidence | Rationale |
|------------|------------|-----------|
| Primary name (name_en, name_el) | 1.0 | Exact canonical match |
| Abbreviation | 0.98 | High confidence standard abbreviations |
| Alias | 0.95 | Alternate names, slightly less certain |

#### 5.3.6 Normalization

```python
def normalize_text(text: str) -> str:
    """
    Normalize for matching:
    1. NFD Unicode decomposition
    2. Remove combining marks (accents)
    3. Lowercase
    4. Strip whitespace

    Example: "Λογιστής" → "λογιστης"
    """
```

#### 5.3.7 Utility Functions

```python
def load_aliases_sync(db_secret_arn: str, ...) -> dict[str, AliasEntry]:
    """Synchronous wrapper for Lambda handlers."""

def get_global_loader(db_secret_arn: str, ...) -> DynamicAliasLoader:
    """Get/create global singleton for Lambda warm starts."""
```

### 5.4 Caching Strategy

- **TTL**: 60 minutes by default (configurable)
- **Scope**: Per-loader instance or global singleton
- **Refresh**: Automatic on `load_all()` if stale, or manual via `reload()`
- **Cold Start**: First Lambda invocation loads from DB (~2-5 seconds)
- **Warm Start**: Subsequent invocations use cached data (0ms)

### 5.5 Error Handling

- **Individual table failure**: Log warning, continue with other tables
- **All tables fail**: Return empty dict (graceful degradation)
- **Connection failure**: Retry with new connection on next call

---

## 6. Test Coverage Summary

### 6.1 Test Files

| File | Tests | Description |
|------|-------|-------------|
| `tests/unit/test_hr_intelligence.py` | 27 | HR Intelligence unit tests |
| `tests/test_code_paths.py` | 15 | HR Intelligence code paths |
| `tests/unit/test_job_parser.py` | 18 | Job parser unit tests |
| `tests/test_job_parser_paths.py` | 20 | Job parser code paths |
| `tests/test_integration_hr_job.py` | 10 | HR + Job Parser integration |
| `tests/test_integration_query_hr.py` | 10 | Query + HR integration |
| `tests/unit/test_dynamic_aliases.py` | 27 | Dynamic aliases unit tests |
| `tests/test_e2e_hr_intelligence.py` | 10 | **Phase 5: E2E tests** |
| **Total** | **140** | All tests passing |

### 6.2 Test Categories

| Category | Count | Purpose |
|----------|-------|---------|
| Unit Tests | 72 | Individual component testing |
| Code Path Tests | 35 | Edge cases, error handling |
| Integration Tests | 23 | Cross-module workflows |
| E2E Tests | 10 | End-to-end scenarios |

### 6.3 Phase 5 E2E Test Scenarios

| Test | Description |
|------|-------------|
| Greek Job Posting Flow | Job posting → parse → analyze → format (Greek) |
| English Job Posting Flow | Job posting → parse → analyze → format (English) |
| Greek Natural Query | Natural language query in Greek |
| English Natural Query | Natural language query in English |
| No Candidates Scenario | Handles empty results gracefully |
| Relaxation Scenario | Criteria relaxation when no direct matches |
| Mixed Language Candidates | Greek/English candidate names |
| API Response Serialization | JSON serializable output verification |
| Large Candidate List | >10 candidates handled with limit |
| Special Characters | Greek names with accents, hyphens |

### 6.4 Running Tests

```bash
# All tests (140 total)
cd D:\CA\repo
python -m pytest tests/ --override-ini="addopts=" -v

# E2E tests only
python tests/test_e2e_hr_intelligence.py

# Unit tests only
python -m pytest tests/unit/ --override-ini="addopts=" -v
```

---

## 7. File Inventory

### 7.1 Phase 1 Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/lcmgo_cagenai/hr_intelligence/__init__.py` | 65 | Module exports |
| `src/lcmgo_cagenai/hr_intelligence/schema.py` | 350 | 13 dataclasses |
| `src/lcmgo_cagenai/hr_intelligence/analyzer.py` | 280 | Main analyzer |
| `src/lcmgo_cagenai/hr_intelligence/prompt_builder.py` | 200 | Prompt construction |
| `src/lcmgo_cagenai/hr_intelligence/formatter.py` | 180 | Output formatters |
| `prompts/hr_analysis/v1.0.0.txt` | 150 | LLM prompt template |

### 7.2 Phase 2 Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/lcmgo_cagenai/parser/job_parser.py` | 311 | Job posting parser |
| `prompts/job_parsing/v1.0.0.txt` | 120 | Extraction prompt |

### 7.3 Phase 3 Files

| File | Lines Changed | Purpose |
|------|---------------|---------|
| `lambda/query/handler.py` | +150 | HR Intelligence integration |

### 7.4 Phase 4 Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/lcmgo_cagenai/query/dynamic_aliases.py` | 450 | Dynamic alias loader |
| `src/lcmgo_cagenai/query/__init__.py` | +15 | New exports |

### 7.5 Test Files

| File | Lines | Tests |
|------|-------|-------|
| `tests/unit/test_hr_intelligence.py` | 600 | 27 |
| `tests/test_code_paths.py` | 650 | 15 |
| `tests/unit/test_job_parser.py` | 490 | 18 |
| `tests/test_job_parser_paths.py` | 520 | 20 |
| `tests/test_integration_hr_job.py` | 490 | 10 |
| `tests/test_integration_query_hr.py` | 580 | 10 |
| `tests/unit/test_dynamic_aliases.py` | 400 | 4+ |

---

## 8. Git Commit History

### 8.1 Phase Commits

| Commit | Date | Description |
|--------|------|-------------|
| `ba0e38e` | 2026-01-20 | feat: Implement HR Intelligence module (Phase 1) |
| `87df6fa` | 2026-01-20 | fix: Resolve test failures and add code path verification tests |
| `45e5de8` | 2026-01-20 | feat: Implement Phase 2 - Job Posting Parser |
| `9da65fd` | 2026-01-20 | test: Add comprehensive test suite for Phase 1 & 2 |
| `68b63b4` | 2026-01-20 | feat: Implement Phase 3 - Query Lambda Integration with HR Intelligence |
| `525b420` | 2026-01-20 | feat: Implement Phase 4 - Dynamic Taxonomy Aliases |

### 8.2 Rollback Commands

```bash
# Rollback to before Phase 4
git checkout 68b63b4

# Rollback to before Phase 3
git checkout 9da65fd

# Rollback to before Phase 2
git checkout ba0e38e

# Rollback to before Phase 1 (pre-implementation)
git checkout 2d36f11
```

---

## 9. API Reference

### 9.1 HR Intelligence Analyzer

```python
from lcmgo_cagenai.hr_intelligence import (
    HRIntelligenceAnalyzer,
    HRAnalysisInput,
    JobRequirements,
    CandidateProfile,
    format_api_response,
)

# Create analyzer
analyzer = HRIntelligenceAnalyzer(llm_provider)

# Prepare input
input_data = HRAnalysisInput(
    original_query="Λογιστές με SAP",
    requirements=JobRequirements(
        source_type="query",
        source_text="...",
        detected_language="el",
        roles=["accountant"],
        software=["SAP"],
    ),
    candidates=[
        CandidateProfile(
            candidate_id="...",
            first_name="...",
            last_name="...",
            software=["SAP", "Excel"],
        ),
    ],
    direct_result_count=5,
    total_result_count=5,
    relaxations_applied=[],
)

# Run analysis
report = await analyzer.analyze(input_data)

# Format output
api_dict = format_api_response(report)
```

### 9.2 Job Parser

```python
from lcmgo_cagenai.parser import JobParser, parse_job_posting_sync

# Async usage
parser = JobParser(llm_provider=provider)
requirements = await parser.parse(job_posting_text)

# Sync usage
requirements = parse_job_posting_sync(job_posting_text)
```

### 9.3 Dynamic Alias Loader

```python
from lcmgo_cagenai.query import DynamicAliasLoader, get_global_loader

# Create loader
loader = DynamicAliasLoader(
    db_secret_arn="arn:aws:secretsmanager:...",
    cache_ttl_minutes=60,
)

# Load all aliases
aliases = await loader.load_all()

# Lookup
entry = aliases.get(normalize_text("λογιστής"))
if entry:
    print(f"Canonical: {entry.canonical_id}")  # "ACCOUNTANT"

# Global singleton for Lambda
loader = get_global_loader(db_secret_arn="...")
```

---

## 10. Rollback Procedures

### 10.1 Code Rollback

```bash
# View current state
git log --oneline -10

# Rollback to specific commit
git checkout <commit_hash>

# Create rollback branch
git checkout -b rollback-to-<version>
```

### 10.2 Lambda Rollback

```bash
# List Lambda versions
aws lambda list-versions-by-function \
  --function-name lcmgo-cagenai-prod-query \
  --region eu-north-1

# Rollback to previous version
aws lambda update-alias \
  --function-name lcmgo-cagenai-prod-query \
  --name prod \
  --function-version <previous_version> \
  --region eu-north-1
```

### 10.3 Layer Rollback

```bash
# Current layer: v51
# Previous stable: v41

aws lambda update-function-configuration \
  --function-name lcmgo-cagenai-prod-query \
  --layers arn:aws:lambda:eu-north-1:132934401449:layer:lcmgo-cagenai-prod-lcmgo-package:41 \
  --region eu-north-1
```

### 10.4 Database Rollback

No database schema changes in Phases 1-4. Rollback not required.

---

## Appendix A: Dependencies

### Python Packages (in Lambda layer)

| Package | Version | Purpose |
|---------|---------|---------|
| `boto3` | (AWS runtime) | AWS SDK |
| `pg8000` | Latest | PostgreSQL driver |
| `opensearch-py` | Latest | OpenSearch client |

### AWS Services

| Service | Resource | Purpose |
|---------|----------|---------|
| Lambda | lcmgo-cagenai-prod-query | Query processing |
| Bedrock | Claude Sonnet 4.5 | HR analysis, job parsing |
| RDS | PostgreSQL 15 | Taxonomy tables |
| Secrets Manager | db-credentials | Database auth |

---

## Appendix B: Configuration

### Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `DB_SECRET_ARN` | `arn:aws:...` | Database credentials |
| `AWS_REGION_NAME` | `eu-north-1` | AWS region |
| `QUERY_CACHE_TABLE` | `lcmgo-cagenai-prod-query-cache` | DynamoDB cache |

### Tunable Parameters

| Parameter | Default | Location |
|-----------|---------|----------|
| HR Analysis max candidates | 10 | `analyzer.py:MAX_CANDIDATES` |
| HR Analysis max tokens | 4096 | `analyzer.py:MAX_TOKENS` |
| Job Parser max tokens | 4096 | `job_parser.py:MAX_TOKENS` |
| Alias cache TTL | 60 min | `dynamic_aliases.py:DEFAULT_TTL_MINUTES` |
| Greek detection threshold | 30% | `analyzer.py:_detect_language()` |

---

*Document generated: 2026-01-20*
*Author: Claude Code (Session 39)*
