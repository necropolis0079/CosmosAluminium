# HR Intelligence System - Unified Design Document

**Status**: Approved for Implementation
**Version**: 2.0
**Created**: 2026-01-20 (Session 38)
**Supersedes**: `HR-INTELLIGENCE-ANALYZER.md`, `JOB-MATCHING-SIMPLE.md`

---

## 1. Executive Summary

This document defines the **unified HR Intelligence system** that merges two previously separate designs:
- HR Intelligence Analyzer (comprehensive analysis for all queries)
- Job Matching Simple (relaxed matching when 0 strict results)

**Key Decision**: Single module handles both use cases, eliminating 80% code duplication.

### 1.1 What This System Does

```
INPUT                           OUTPUT
─────                           ──────
"λογιστές με SAP, 5+ χρόνια"    → Ranked candidates with:
        OR                         • Match analysis
Job posting text                   • Strengths/gaps per candidate
        OR                         • Evidence from CV
Ad-hoc search query                • HR recommendations
                                   • Interview focus points
```

### 1.2 Key Capabilities

| Capability | Description |
|------------|-------------|
| **Intelligent Ranking** | Ranks candidates by fit, not just filter match |
| **Gap Analysis** | Shows what each candidate has vs. missing |
| **Criteria Relaxation** | When 0 exact matches, finds best partial matches |
| **Evidence-Based** | All claims reference specific CV data |
| **Bilingual** | Greek query → Greek response, English → English |
| **Actionable** | Interview focus points, hiring recommendations |

---

## 2. Architecture

### 2.1 System Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INPUT                                      │
│                                                                              │
│  Option A: Natural Language Query                                           │
│  "Λογιστές με SAP, 3+ χρόνια, Αγγλικά"                                      │
│                                                                              │
│  Option B: Job Posting Text                                                 │
│  "Ζητείται Λογιστής με εμπειρία σε SAP ERP..."                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE 1: INPUT PROCESSING                            │
│                                                                              │
│  ┌─────────────────────┐    ┌─────────────────────┐                         │
│  │  Query Translator   │    │  Job Posting Parser │                         │
│  │  (existing)         │    │  (NEW - Task 2.2)   │                         │
│  │                     │    │                     │                         │
│  │  NL → Structured    │    │  Text → JobReqs     │                         │
│  └──────────┬──────────┘    └──────────┬──────────┘                         │
│             │                          │                                     │
│             └──────────┬───────────────┘                                     │
│                        ▼                                                     │
│              ┌─────────────────────┐                                        │
│              │  JobRequirements    │                                        │
│              │  (unified format)   │                                        │
│              └─────────────────────┘                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE 2: CANDIDATE RETRIEVAL                         │
│                                                                              │
│  Step 2a: Strict Query (existing SQL)                                       │
│  ────────────────────────────────────                                       │
│  Execute exact-match SQL query                                              │
│  Results: N candidates (may be 0)                                           │
│                                                                              │
│  Step 2b: Relaxed Query (if N == 0)                                         │
│  ─────────────────────────────────                                          │
│  Execute match_candidates_relaxed() function                                │
│  - OR logic instead of AND                                                  │
│  - Partial matching scores                                                  │
│  Results: Top 10 partial matches                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE 3: HR INTELLIGENCE                             │
│                                                                              │
│  Single Claude Sonnet 4.5 Call                                              │
│  ────────────────────────────────                                           │
│                                                                              │
│  Input:                                                                      │
│  - Original query/job posting (for language detection)                      │
│  - Extracted requirements (JobRequirements)                                 │
│  - Candidate profiles (full data from PostgreSQL)                           │
│  - Relaxations applied (if any)                                             │
│  - Result counts (direct vs total)                                          │
│                                                                              │
│  Processing:                                                                 │
│  - Analyze each candidate against requirements                              │
│  - Compare candidates against each other                                    │
│  - Rank by overall suitability                                              │
│  - Generate evidence-based explanations                                     │
│                                                                              │
│  Output:                                                                     │
│  - HRAnalysisReport (structured JSON)                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE 4: API RESPONSE                                │
│                                                                              │
│  {                                                                           │
│    "candidates": [...],              // Raw candidate data                  │
│    "result_count": 5,                                                       │
│    "relaxation_applied": true,                                              │
│    "hr_analysis": {                  // NEW: Structured analysis            │
│      "request_analysis": {...},                                             │
│      "query_outcome": {...},                                                │
│      "criteria_expansion": {...},    // Only if relaxation applied          │
│      "ranked_candidates": [...],                                            │
│      "hr_recommendation": {...}                                             │
│    }                                                                         │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Module Structure

```
src/lcmgo_cagenai/
├── query/
│   ├── query_router.py           # Existing - routes queries
│   ├── query_translator.py       # Existing - NL to structured
│   ├── sql_generator.py          # Existing - generates SQL
│   └── dynamic_aliases.py        # NEW (Task 2.1) - DB-driven aliases
│
├── parser/
│   ├── cv_parser.py              # Existing - CV parsing
│   └── job_parser.py             # NEW (Task 2.2) - Job posting parser
│
├── matching/
│   └── job_matcher.py            # Existing - relaxed SQL matching
│
└── hr_intelligence/              # NEW - UNIFIED MODULE
    ├── __init__.py               # Exports: HRIntelligence, HRAnalysisReport
    ├── analyzer.py               # Main analysis logic
    ├── schema.py                 # Data structures
    ├── prompts.py                # LLM prompts (Greek/English)
    └── formatter.py              # Response formatting
```

---

## 3. Data Structures

### 3.1 Input: JobRequirements (Unified)

Used by both Query Translator and Job Posting Parser output.

```python
@dataclass
class JobRequirements:
    """Unified requirements format for HR Intelligence."""

    # Source information
    source_type: Literal["query", "job_posting"]
    source_text: str                           # Original input
    detected_language: str                     # "el" or "en"

    # Role requirements
    roles: list[str]                           # ["accountant", "financial_analyst"]
    role_priority: str                         # "must" | "should" | "nice"

    # Experience requirements
    min_experience_years: float | None         # 3.0
    max_experience_years: float | None         # None = no upper limit
    experience_priority: str

    # Technical requirements
    software: list[str]                        # ["SAP", "Excel"]
    software_priority: str
    certifications: list[str]                  # ["CPA", "ACCA"]
    certifications_priority: str
    skills: list[str]                          # ["financial_reporting", "budgeting"]
    skills_priority: str

    # Language requirements
    languages: list[LanguageRequirement]       # [{"code": "en", "min_level": "B2"}]

    # Location requirements
    locations: list[str]                       # ["Athens", "Thessaloniki"]
    remote_acceptable: bool

    # Education requirements
    education_level: str | None                # "bachelor", "master", etc.
    education_fields: list[str]                # ["accounting", "finance"]

    # Computed weights for scoring
    weights: dict[str, float]                  # {"role": 0.25, "experience": 0.30, ...}


@dataclass
class LanguageRequirement:
    """Single language requirement."""
    language_code: str                         # "en", "el", "de"
    language_name: str                         # "English", "Greek"
    min_level: str | None                      # "A1" to "C2" or None
    is_required: bool                          # True = must have, False = nice to have
```

### 3.2 Output: HRAnalysisReport

```python
@dataclass
class HRAnalysisReport:
    """Complete HR analysis output."""

    # Section 1: Request Analysis
    request_analysis: RequestAnalysis

    # Section 2: Query Outcome
    query_outcome: QueryOutcome

    # Section 3: Criteria Expansion (if relaxation applied)
    criteria_expansion: CriteriaExpansion | None

    # Section 4: Ranked Candidates
    ranked_candidates: list[RankedCandidate]

    # Section 5: HR Recommendation
    hr_recommendation: HRRecommendation

    # Metadata
    analysis_language: str                     # "el" or "en"
    analysis_timestamp: datetime
    llm_model: str
    latency_ms: int


@dataclass
class RequestAnalysis:
    """Section 1: Understanding the request."""
    summary: str                               # Brief description
    mandatory_criteria: list[str]              # Must-have
    preferred_criteria: list[str]              # Nice-to-have
    inferred_criteria: list[str]               # Implied but not stated


@dataclass
class QueryOutcome:
    """Section 2: What the query found."""
    direct_matches: int                        # Exact criteria matches
    total_matches: int                         # After relaxation
    relaxation_applied: bool
    zero_results_reason: str | None            # Why 0 direct (if applicable)


@dataclass
class CriteriaExpansion:
    """Section 3: How criteria were relaxed."""
    relaxations: list[CriteriaRelaxation]
    business_rationale: str                    # Why these relaxations make sense


@dataclass
class CriteriaRelaxation:
    """Single criterion relaxation."""
    original: str                              # "SAP ERP, 5+ years"
    relaxed_to: str                            # "Any ERP, 3+ years"
    reasoning: str                             # "SAP skills transfer to other ERPs"


@dataclass
class RankedCandidate:
    """Section 4: Individual candidate analysis."""
    rank: int                                  # 1, 2, 3...
    candidate_id: str
    candidate_name: str

    # Match assessment
    overall_suitability: str                   # "High" | "Medium-High" | "Medium" | "Low"
    match_percentage: float                    # 0-100

    # What they have
    strengths: list[CandidateEvidence]

    # What's missing
    gaps: list[CandidateGap]

    # Concerns
    risks: list[str]

    # Detailed assessments
    role_match: AssessmentScore
    experience_match: AssessmentScore
    skills_match: AssessmentScore
    language_match: AssessmentScore

    # HR notes
    interview_focus: list[str]                 # What to verify in interview


@dataclass
class CandidateEvidence:
    """Evidence of qualification."""
    criterion: str                             # "SAP experience"
    candidate_value: str                       # "SAP FI/CO, 4 years"
    source: str                                # "CV page 1, Experience section"
    confidence: str                            # "Confirmed" | "Likely" | "Uncertain"


@dataclass
class CandidateGap:
    """Missing qualification."""
    criterion: str                             # "5+ years experience"
    gap_description: str                       # "Has 3 years (2 below requirement)"
    severity: str                              # "Minor" | "Moderate" | "Major"
    mitigation: str | None                     # "Strong SAP skills may compensate"


@dataclass
class AssessmentScore:
    """Evaluation score with evidence."""
    score: str                                 # "High" | "Medium" | "Low"
    evidence: list[str]
    notes: str


@dataclass
class HRRecommendation:
    """Section 5: Final recommendations."""
    top_candidates: list[str]                  # Names in order
    recommendation_summary: str                # 2-3 sentence summary
    interview_priorities: list[str]            # What to validate
    hiring_suggestions: list[str]              # Additional advice
    alternative_search: str | None             # If results poor, suggest different search
```

---

## 4. LLM Prompt Design

### 4.1 System Prompt (Greek)

```
ΡΟΛΟΣ: Είσαι Ειδικός HR Intelligence που αξιολογεί, συγκρίνει και κατατάσσει υποψηφίους.

ΔΕΝ είσαι απλό φίλτρο. ΑΝΑΛΥΕΙΣ, ΣΥΛΛΟΓΙΖΕΣΑΙ, ΣΥΓΚΡΙΝΕΙΣ και ΠΡΟΤΕΙΝΕΙΣ με τεκμηριωμένες εξηγήσεις.

═══════════════════════════════════════════════════════════════════════════════
ΑΠΑΙΤΗΣΕΙΣ ΘΕΣΗΣ:
{requirements_json}

ΔΙΑΘΕΣΙΜΟΙ ΥΠΟΨΗΦΙΟΙ:
{candidates_json}

ΠΛΗΡΟΦΟΡΙΕΣ ΑΝΑΖΗΤΗΣΗΣ:
- Άμεσα αποτελέσματα: {direct_count}
- Συνολικά αποτελέσματα: {total_count}
- Χαλάρωση κριτηρίων: {relaxation_applied}
═══════════════════════════════════════════════════════════════════════════════

ΚΑΝΟΝΕΣ ΑΝΑΛΥΣΗΣ:

1. ΚΑΤΑΝΟΗΣΗ ΑΙΤΗΜΑΤΟΣ
   • Διαχώρισε τα ΥΠΟΧΡΕΩΤΙΚΑ από τα ΕΠΙΘΥΜΗΤΑ κριτήρια
   • Αναγνώρισε ΥΠΟΝΟΟΥΜΕΝΑ κριτήρια (π.χ. "λογιστής" → γνώση Excel πιθανή)

2. ΑΞΙΟΛΟΓΗΣΗ ΥΠΟΨΗΦΙΩΝ
   Για κάθε υποψήφιο:
   • Τι ΕΧΕΙ που ταιριάζει (με αναφορά σε CV)
   • Τι ΔΕΝ ΕΧΕΙ (με σοβαρότητα: μικρό/μέτριο/μεγάλο κενό)
   • Τι είναι ΑΒΕΒΑΙΟ (χρειάζεται επιβεβαίωση)

3. ΣΥΓΚΡΙΣΗ ΜΕΤΑΞΥ ΥΠΟΨΗΦΙΩΝ
   • Ποιος είναι ΚΑΛΥΤΕΡΟΣ και γιατί
   • Ποιος έχει ΜΟΝΑΔΙΚΑ πλεονεκτήματα
   • Ποιος έχει ΜΕΓΑΛΥΤΕΡΑ κενά

4. ΚΑΤΑΤΑΞΗ
   • Υψηλή Καταλληλότητα: ≥70% κάλυψη κριτηρίων
   • Μέτρια Καταλληλότητα: 40-70% κάλυψη
   • Χαμηλή Καταλληλότητα: <40% κάλυψη

5. ΧΑΛΑΡΩΣΗ ΚΡΙΤΗΡΙΩΝ (αν direct_count == 0)
   • Εξήγησε ΠΟΙΑ κριτήρια χαλαρώθηκαν
   • Εξήγησε ΓΙΑΤΙ είναι λογικό (π.χ. "Softone ≈ SAP = ERP συστήματα")
   • ΜΗΝ χαλαρώσεις υποχρεωτικά κριτήρια πλήρως

ΑΠΑΓΟΡΕΥΣΕΙΣ:
❌ ΜΗΝ επινοείς δεδομένα που δεν υπάρχουν στο CV
❌ ΜΗΝ λες "δεν υπάρχουν υποψήφιοι" χωρίς εναλλακτικές
❌ ΜΗΝ επιστρέφεις ακατέργαστες λίστες χωρίς ανάλυση
❌ ΜΗΝ αγνοείς κενά - πάντα αναφέρονται

ΜΟΡΦΗ ΑΠΑΝΤΗΣΗΣ:
{response_schema_json}
```

### 4.2 System Prompt (English)

```
ROLE: You are an HR Intelligence Specialist who evaluates, compares, and ranks candidates.

You are NOT a simple filter. You ANALYZE, REASON, COMPARE, and RECOMMEND with evidence-based explanations.

═══════════════════════════════════════════════════════════════════════════════
JOB REQUIREMENTS:
{requirements_json}

AVAILABLE CANDIDATES:
{candidates_json}

SEARCH INFORMATION:
- Direct matches: {direct_count}
- Total matches: {total_count}
- Relaxation applied: {relaxation_applied}
═══════════════════════════════════════════════════════════════════════════════

ANALYSIS RULES:

1. REQUEST UNDERSTANDING
   • Separate MANDATORY from PREFERRED criteria
   • Identify IMPLIED criteria (e.g., "accountant" → likely knows Excel)

2. CANDIDATE EVALUATION
   For each candidate:
   • What they HAVE that matches (with CV reference)
   • What they DON'T HAVE (with severity: minor/moderate/major gap)
   • What is UNCERTAIN (needs verification)

3. CROSS-CANDIDATE COMPARISON
   • Who is BEST and why
   • Who has UNIQUE advantages
   • Who has BIGGEST gaps

4. RANKING
   • High Suitability: ≥70% criteria coverage
   • Medium Suitability: 40-70% coverage
   • Low Suitability: <40% coverage

5. CRITERIA RELAXATION (if direct_count == 0)
   • Explain WHICH criteria were relaxed
   • Explain WHY it's reasonable (e.g., "Softone ≈ SAP = ERP systems")
   • Do NOT fully relax mandatory criteria

PROHIBITIONS:
❌ Do NOT invent data not in the CV
❌ Do NOT say "no candidates" without alternatives
❌ Do NOT return raw lists without analysis
❌ Do NOT ignore gaps - always mention them

RESPONSE FORMAT:
{response_schema_json}
```

---

## 5. API Integration

### 5.1 Request Format (No Changes)

```json
POST /v1/query
{
  "query": "Λογιστές με SAP, 3+ χρόνια, Αγγλικά",
  "execute": true,
  "limit": 50
}
```

Or with job posting:

```json
POST /v1/query
{
  "job_posting": "Ζητείται Λογιστής Α' Τάξης με εμπειρία σε SAP ERP...",
  "execute": true,
  "limit": 50
}
```

### 5.2 Response Format (Enhanced)

```json
{
  "statusCode": 200,
  "body": {
    "query_type": "structured",
    "original_query": "Λογιστές με SAP, 3+ χρόνια, Αγγλικά",

    "translation": {
      "roles": ["accountant"],
      "software": ["SAP"],
      "min_experience_years": 3,
      "languages": [{"code": "en"}]
    },

    "sql": "SELECT ... FROM candidates ...",

    "results": [
      {"candidate_id": "uuid-1", "name": "Βάγια Βαΐτση", ...},
      {"candidate_id": "uuid-2", "name": "Φαίη Νάτσιου", ...}
    ],
    "result_count": 5,
    "direct_result_count": 0,
    "relaxation_applied": true,

    "hr_analysis": {
      "request_analysis": {
        "summary": "Αναζήτηση λογιστών με ERP εμπειρία και Αγγλικά",
        "mandatory_criteria": ["Λογιστικό background", "ERP εμπειρία"],
        "preferred_criteria": ["3+ χρόνια εμπειρίας", "SAP συγκεκριμένα"],
        "inferred_criteria": ["Excel γνώση", "Οργανωτικές ικανότητες"]
      },

      "query_outcome": {
        "direct_matches": 0,
        "total_matches": 5,
        "relaxation_applied": true,
        "zero_results_reason": "Κανένας υποψήφιος δεν έχει ακριβώς 3+ χρόνια τεκμηριωμένης SAP εμπειρίας"
      },

      "criteria_expansion": {
        "relaxations": [
          {
            "original": "SAP ERP, 3+ χρόνια",
            "relaxed_to": "Οποιοδήποτε ERP, 2+ χρόνια",
            "reasoning": "Softone, Singular, SAP είναι όλα ERP - η εμπειρία μεταφέρεται"
          }
        ],
        "business_rationale": "Η λογιστική γνώση και η εξοικείωση με ERP είναι σημαντικότερες από το συγκεκριμένο σύστημα"
      },

      "ranked_candidates": [
        {
          "rank": 1,
          "candidate_id": "uuid-1",
          "candidate_name": "Βάγια Βαΐτση",
          "overall_suitability": "High",
          "match_percentage": 78,

          "strengths": [
            {
              "criterion": "Λογιστική εμπειρία",
              "candidate_value": "8 χρόνια σε λογιστήριο",
              "source": "CV, Επαγγελματική Εμπειρία",
              "confidence": "Confirmed"
            },
            {
              "criterion": "ERP γνώση",
              "candidate_value": "Softone ERP",
              "source": "CV, Δεξιότητες Software",
              "confidence": "Confirmed"
            }
          ],

          "gaps": [
            {
              "criterion": "SAP συγκεκριμένα",
              "gap_description": "Έχει Softone, όχι SAP",
              "severity": "Minor",
              "mitigation": "Τα ERP έχουν παρόμοια λογική - εύκολη μετάβαση"
            }
          ],

          "risks": [],

          "role_match": {"score": "High", "evidence": ["Λογίστρια", "8 χρόνια"], "notes": ""},
          "experience_match": {"score": "High", "evidence": ["8 χρόνια > 3 ζητούμενα"], "notes": ""},
          "skills_match": {"score": "Medium-High", "evidence": ["ERP ναι, SAP όχι"], "notes": ""},
          "language_match": {"score": "High", "evidence": ["Αγγλικά: Άριστα"], "notes": ""},

          "interview_focus": [
            "Επιβεβαίωση βάθους ERP γνώσης",
            "Διάθεση για εκπαίδευση σε SAP"
          ]
        }
      ],

      "hr_recommendation": {
        "top_candidates": ["Βάγια Βαΐτση", "Φαίη Νάτσιου", "Ιφιγένεια Βλιώρα"],
        "recommendation_summary": "Η Βάγια Βαΐτση είναι η καλύτερη επιλογή με 78% κάλυψη. Έχει ισχυρό λογιστικό background και ERP εμπειρία. Η μόνη απόκλιση είναι το συγκεκριμένο σύστημα (Softone vs SAP).",
        "interview_priorities": [
          "Βάθος ERP γνώσεων (modules, workflows)",
          "Διάθεση και ικανότητα για SAP training",
          "Επίπεδο Αγγλικών (oral assessment)"
        ],
        "hiring_suggestions": [
          "Εξετάστε SAP training budget για την επιλεγμένη υποψήφια",
          "Οι 2 πρώτες υποψήφιες αξίζουν συνέντευξη"
        ],
        "alternative_search": null
      },

      "analysis_language": "el",
      "analysis_timestamp": "2026-01-20T14:30:00Z",
      "llm_model": "claude-sonnet-4-5",
      "latency_ms": 4521
    },

    "request_id": "req-abc123",
    "total_latency_ms": 7234
  }
}
```

---

## 6. Implementation Plan

### 6.1 Phase 1: HR Intelligence Core (Priority: P0)

| Task | Description | Files | Hours |
|------|-------------|-------|-------|
| 1.1 | Create module structure | `hr_intelligence/__init__.py` | 0.5h |
| 1.2 | Define data structures | `hr_intelligence/schema.py` | 2h |
| 1.3 | Create LLM prompts | `hr_intelligence/prompts.py` | 2h |
| 1.4 | Implement analyzer | `hr_intelligence/analyzer.py` | 6h |
| 1.5 | Response formatting | `hr_intelligence/formatter.py` | 2h |
| 1.6 | Language detection | In `analyzer.py` | 1h |
| 1.7 | Unit tests | `tests/unit/test_hr_intelligence.py` | 3h |
| **Subtotal** | | | **16.5h** |

### 6.2 Phase 2: Job Posting Parser (Priority: P0)

| Task | Description | Files | Hours |
|------|-------------|-------|-------|
| 2.1 | Job parser module | `parser/job_parser.py` | 4h |
| 2.2 | Job parser prompt | `prompts/job_parsing/v1.0.0.txt` | 1h |
| 2.3 | Integration with HR Intelligence | Updates to `query/handler.py` | 2h |
| 2.4 | Unit tests | `tests/unit/test_job_parser.py` | 2h |
| **Subtotal** | | | **9h** |

### 6.3 Phase 3: Query Lambda Integration (Priority: P0)

| Task | Description | Files | Hours |
|------|-------------|-------|-------|
| 3.1 | Update query handler | `lambda/query/handler.py` | 3h |
| 3.2 | Candidate profile enrichment | New function in handler | 2h |
| 3.3 | Error handling & fallbacks | In handler | 1h |
| 3.4 | Integration tests | `tests/integration/test_hr_query.py` | 3h |
| **Subtotal** | | | **9h** |

### 6.4 Phase 4: Dynamic Taxonomy Aliases (Priority: P1, Parallel)

| Task | Description | Files | Hours |
|------|-------------|-------|-------|
| 4.1 | Dynamic alias loader | `query/dynamic_aliases.py` | 3h |
| 4.2 | Update query translator | `query/query_translator.py` | 2h |
| 4.3 | Caching layer | In `dynamic_aliases.py` | 1h |
| 4.4 | Tests | `tests/unit/test_dynamic_aliases.py` | 1h |
| **Subtotal** | | | **7h** |

### 6.5 Phase 5: Testing & Refinement (Priority: P1)

| Task | Description | Hours |
|------|-------------|-------|
| 5.1 | End-to-end testing with real CVs | 4h |
| 5.2 | Prompt refinement based on results | 3h |
| 5.3 | Performance optimization | 2h |
| 5.4 | Documentation updates | 2h |
| **Subtotal** | | **11h** |

### Total Effort

| Phase | Hours |
|-------|-------|
| Phase 1: HR Intelligence Core | 16.5h |
| Phase 2: Job Posting Parser | 9h |
| Phase 3: Query Lambda Integration | 9h |
| Phase 4: Dynamic Taxonomy (parallel) | 7h |
| Phase 5: Testing & Refinement | 11h |
| **Total** | **52.5h** |

---

## 7. Cost Analysis

### 7.1 Per-Query Cost

| Component | Model | Tokens | Cost |
|-----------|-------|--------|------|
| Query Translation | Claude Haiku | ~700 | $0.001 |
| SQL Execution | PostgreSQL | - | $0.000 |
| HR Intelligence | Claude Sonnet 4.5 | ~4,000 | $0.015 |
| **Total** | | | **~$0.016/query** |

### 7.2 Monthly Projections

| Usage Level | Queries/Month | HR Analysis Cost |
|-------------|---------------|------------------|
| Low | 1,000 | $16 |
| Medium | 5,000 | $80 |
| High | 10,000 | $160 |

### 7.3 Cost Optimization Options

1. **Caching**: Cache analysis for identical queries (24h TTL)
2. **Haiku for simple**: Use Haiku when < 3 candidates
3. **Optional flag**: Future `"analyze": false` to skip analysis

---

## 8. Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `src/lcmgo_cagenai/hr_intelligence/__init__.py` | Module exports |
| `src/lcmgo_cagenai/hr_intelligence/schema.py` | Data structures |
| `src/lcmgo_cagenai/hr_intelligence/analyzer.py` | Main analysis logic |
| `src/lcmgo_cagenai/hr_intelligence/prompts.py` | LLM prompts |
| `src/lcmgo_cagenai/hr_intelligence/formatter.py` | Response formatting |
| `src/lcmgo_cagenai/parser/job_parser.py` | Job posting parser |
| `src/lcmgo_cagenai/query/dynamic_aliases.py` | DB-driven aliases |
| `prompts/job_parsing/v1.0.0.txt` | Job parsing prompt |
| `tests/unit/test_hr_intelligence.py` | Unit tests |
| `tests/unit/test_job_parser.py` | Unit tests |
| `tests/integration/test_hr_query.py` | Integration tests |

### Modified Files

| File | Changes |
|------|---------|
| `lambda/query/handler.py` | Add HR Intelligence integration |
| `src/lcmgo_cagenai/query/query_translator.py` | Support dynamic aliases |
| `src/lcmgo_cagenai/query/__init__.py` | Export new modules |
| `src/lcmgo_cagenai/parser/__init__.py` | Export JobParser |

---

## 9. Success Criteria

| Metric | Target |
|--------|--------|
| Analysis accuracy | >85% correct rankings (manual review) |
| Response time | <10 seconds P95 |
| User satisfaction | >80% positive feedback |
| Zero-result recovery | >90% of 0-result queries get useful alternatives |
| Cost per query | <$0.05 |

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM hallucination | High | Strict schema validation, evidence requirements |
| Slow response | Medium | Caching, async processing, timeout limits |
| Inconsistent language | Low | Explicit language detection, prompt enforcement |
| Cost overrun | Medium | Usage monitoring, optional analysis flag |
| Schema changes | Medium | Version prompts, backward compatibility |

---

## 11. Migration from Old Designs

### 11.1 Deprecated Documents

The following documents are **SUPERSEDED** by this unified design:

| Document | Status |
|----------|--------|
| `docs/HR-INTELLIGENCE-ANALYZER.md` | **DEPRECATED** - Keep for reference |
| `docs/JOB-MATCHING-SIMPLE.md` | **DEPRECATED** - Keep for reference |
| `docs/IDEAS-MULTI-PERSPECTIVE-EVALUATION.md` | **DEPRECATED** - Over-engineered |

### 11.2 Existing Code Reuse

| Existing Code | Reuse Strategy |
|---------------|----------------|
| `matching/job_matcher.py` | Keep `match_candidates_relaxed()` SQL function |
| `scripts/sql/019_job_matching.sql` | Keep, already deployed |
| `query/query_translator.py` | Enhance with dynamic aliases |

---

## Appendix A: Example Scenarios

### A.1 Scenario: Direct Matches Found

**Input**: "Excel experts"
**Direct Results**: 15 candidates

**HR Analysis Summary**:
- No relaxation needed
- Top 5 ranked by Excel proficiency + complementary skills
- Interview focus: Specific Excel functions (VBA, Pivot, etc.)

### A.2 Scenario: Zero Direct Results

**Input**: "SAP accountants with 5+ years and German"
**Direct Results**: 0

**HR Analysis Summary**:
- Relaxation: SAP → Any ERP, 5+ → 3+, German optional
- 3 candidates found with partial match
- Clear explanation of what's missing per candidate
- Suggestion: "Consider relaxing German requirement"

### A.3 Scenario: Job Posting Input

**Input**: Full job posting text (500 words)
**Extracted Requirements**: Role, experience, software, languages, certifications

**HR Analysis Summary**:
- Requirements parsed and prioritized
- Candidates matched against all criteria
- Suitability scores with evidence
- Interview guide based on job requirements

---

## Appendix B: Prompt Response Schema (JSON)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["request_analysis", "query_outcome", "ranked_candidates", "hr_recommendation"],
  "properties": {
    "request_analysis": {
      "type": "object",
      "required": ["summary", "mandatory_criteria", "preferred_criteria"],
      "properties": {
        "summary": {"type": "string"},
        "mandatory_criteria": {"type": "array", "items": {"type": "string"}},
        "preferred_criteria": {"type": "array", "items": {"type": "string"}},
        "inferred_criteria": {"type": "array", "items": {"type": "string"}}
      }
    },
    "query_outcome": {
      "type": "object",
      "required": ["direct_matches", "total_matches"],
      "properties": {
        "direct_matches": {"type": "integer"},
        "total_matches": {"type": "integer"},
        "relaxation_applied": {"type": "boolean"},
        "zero_results_reason": {"type": ["string", "null"]}
      }
    },
    "criteria_expansion": {
      "type": ["object", "null"],
      "properties": {
        "relaxations": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["original", "relaxed_to", "reasoning"],
            "properties": {
              "original": {"type": "string"},
              "relaxed_to": {"type": "string"},
              "reasoning": {"type": "string"}
            }
          }
        },
        "business_rationale": {"type": "string"}
      }
    },
    "ranked_candidates": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["rank", "candidate_id", "candidate_name", "overall_suitability", "strengths", "gaps"],
        "properties": {
          "rank": {"type": "integer"},
          "candidate_id": {"type": "string"},
          "candidate_name": {"type": "string"},
          "overall_suitability": {"enum": ["High", "Medium-High", "Medium", "Medium-Low", "Low"]},
          "match_percentage": {"type": "number", "minimum": 0, "maximum": 100},
          "strengths": {"type": "array"},
          "gaps": {"type": "array"},
          "risks": {"type": "array", "items": {"type": "string"}},
          "interview_focus": {"type": "array", "items": {"type": "string"}}
        }
      }
    },
    "hr_recommendation": {
      "type": "object",
      "required": ["top_candidates", "recommendation_summary"],
      "properties": {
        "top_candidates": {"type": "array", "items": {"type": "string"}},
        "recommendation_summary": {"type": "string"},
        "interview_priorities": {"type": "array", "items": {"type": "string"}},
        "hiring_suggestions": {"type": "array", "items": {"type": "string"}},
        "alternative_search": {"type": ["string", "null"]}
      }
    }
  }
}
```

---

**Document Status**: Approved for Implementation
**Next Step**: Begin Phase 1 - Create `hr_intelligence/` module
