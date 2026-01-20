# HR Intelligence Analyzer - Design Document

**Status**: Planned
**Version**: 1.0
**Created**: 2026-01-20 (Session 37)
**Author**: Claude Code

---

## 1. Overview

### 1.1 Purpose

The HR Intelligence Analyzer transforms raw candidate query results into actionable HR insights with structured analysis, comparison, ranking, and recommendations.

**Key Principle**: The system does NOT simply apply filters. It **analyzes, reasons, compares, and recommends** candidates with clear explanations suitable for HR decision-making.

### 1.2 Problem Statement

Current query system returns:
- Raw candidate lists
- Basic match percentages
- No comparison between candidates
- No business reasoning
- No actionable recommendations

HR users need:
- Intelligent analysis of each candidate
- Comparison against requirements AND each other
- Ranked recommendations with justification
- Interview focus points
- Gap identification

### 1.3 Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Scope** | All queries | Consistent UX, always get intelligent analysis |
| **Latency** | +3-8 seconds acceptable | Quality over speed for HR decisions |
| **Response Format** | Raw candidates + analysis | Flexibility for different use cases |
| **Language** | Match user's query language | Greek query → Greek response, English query → English response |

---

## 2. Architecture

### 2.1 System Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER QUERY                                         │
│                  "Λογιστές με SAP, 3+ χρόνια, Αγγλικά"                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         QUERY ROUTER                                         │
│  - Translate to structured filters                                          │
│  - Route to SQL or Job Matcher                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      SQL EXECUTION / JOB MATCHER                             │
│  - Execute query against PostgreSQL                                         │
│  - Apply relaxed matching if 0 results                                      │
│  - Return candidate list with basic data                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HR INTELLIGENCE ANALYZER (NEW)                            │
│                                                                              │
│  Input:                                                                      │
│  - Original query (for language detection)                                  │
│  - Extracted requirements                                                   │
│  - Candidate list with full profiles                                        │
│  - Relaxations applied (if any)                                             │
│                                                                              │
│  Processing:                                                                 │
│  - Single LLM call (Claude Sonnet 4.5)                                      │
│  - Comprehensive prompt with reasoning rules                                │
│  - Structured 5-section output                                              │
│                                                                              │
│  Output:                                                                     │
│  - Structured HR analysis report                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         API RESPONSE                                         │
│  {                                                                           │
│    "candidates": [...],           // Raw candidate data                     │
│    "hr_analysis": {               // NEW: Structured analysis               │
│      "request_analysis": {...},                                             │
│      "query_outcome": {...},                                                │
│      "criteria_expansion": {...},                                           │
│      "ranked_candidates": [...],                                            │
│      "hr_recommendation": {...}                                             │
│    }                                                                         │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Integration

```
src/lcmgo_cagenai/
├── query/
│   ├── query_router.py          # Existing - routes queries
│   └── sql_generator.py         # Existing - generates SQL
├── matching/
│   ├── job_matcher.py           # Existing - relaxed matching
│   └── response_formatter.py    # Existing - basic formatting
└── hr_intelligence/             # NEW MODULE
    ├── __init__.py
    ├── analyzer.py              # Main HR analysis logic
    ├── prompts.py               # LLM prompt templates
    └── schema.py                # Data structures
```

---

## 3. Data Structures

### 3.1 Input Data

```python
@dataclass
class HRAnalysisInput:
    """Input for HR Intelligence Analyzer"""
    original_query: str                    # User's natural language query
    query_language: str                    # "el" or "en" (detected)
    requirements: JobRequirements          # Extracted requirements
    candidates: list[CandidateProfile]     # Full candidate profiles
    relaxations_applied: list[str]         # List of relaxed criteria
    direct_result_count: int               # Results before relaxation
    total_result_count: int                # Results after relaxation
```

### 3.2 Output Data

```python
@dataclass
class HRAnalysisReport:
    """Structured HR analysis output"""

    # Section 1: Request Analysis
    request_analysis: RequestAnalysis

    # Section 2: Query Outcome
    query_outcome: QueryOutcome

    # Section 3: Criteria Expansion (if applicable)
    criteria_expansion: Optional[CriteriaExpansion]

    # Section 4: Ranked Candidates
    ranked_candidates: list[RankedCandidate]

    # Section 5: HR Recommendation
    hr_recommendation: HRRecommendation

    # Metadata
    analysis_language: str                 # "el" or "en"
    analysis_timestamp: datetime
    llm_model_used: str
    analysis_latency_ms: int


@dataclass
class RequestAnalysis:
    """Section 1: What the user is asking for"""
    summary: str                           # Brief description of request
    mandatory_criteria: list[str]          # Must-have requirements
    preferred_criteria: list[str]          # Nice-to-have requirements
    inferred_criteria: list[str]           # Implied but not stated


@dataclass
class QueryOutcome:
    """Section 2: Query results summary"""
    direct_matches: int                    # Exact criteria matches
    total_matches: int                     # After relaxation
    zero_results_reason: Optional[str]     # Why 0 direct results (if applicable)


@dataclass
class CriteriaExpansion:
    """Section 3: How criteria were relaxed"""
    relaxations: list[CriteriaRelaxation]
    business_logic: str                    # Why these relaxations make sense


@dataclass
class CriteriaRelaxation:
    """Single criteria relaxation"""
    original: str                          # "SAP ERP, 3+ years"
    relaxed_to: str                        # "Any ERP system, 2+ years"
    reasoning: str                         # "SAP is an ERP platform..."


@dataclass
class RankedCandidate:
    """Section 4: Individual candidate analysis"""
    rank: int                              # 1, 2, 3...
    candidate_id: str
    candidate_name: str

    # Evaluation dimensions
    role_relevance: EvaluationScore        # How well role matches
    skills_match: EvaluationScore          # Technical skills alignment
    experience_assessment: ExperienceAssessment
    language_proficiency: LanguageAssessment

    # Summary
    strengths: list[str]                   # What makes them suitable
    gaps: list[str]                        # Missing or uncertain areas
    risks: list[str]                       # Potential concerns
    overall_suitability: str               # "High", "Medium-High", "Medium", "Low"

    # Raw data reference
    match_percentage: float


@dataclass
class EvaluationScore:
    """Evaluation with evidence"""
    score: str                             # "High", "Medium", "Low"
    evidence: list[str]                    # Supporting data points
    confidence: str                        # "Confirmed", "Likely", "Uncertain"


@dataclass
class ExperienceAssessment:
    """Experience evaluation"""
    total_years: Optional[float]           # If known
    relevant_years: Optional[float]        # Years in relevant role
    assessment: str                        # "Exceeds", "Meets", "Below", "Unknown"
    notes: str                             # Additional context


@dataclass
class LanguageAssessment:
    """Language proficiency assessment"""
    languages: list[dict]                  # [{"code": "en", "level": "Professional"}]
    meets_requirement: bool
    notes: str


@dataclass
class HRRecommendation:
    """Section 5: Final recommendations"""
    top_candidates: list[str]              # Names of recommended candidates
    recommendation_summary: str            # Brief recommendation text
    interview_focus_points: list[str]      # What to validate in interviews
    additional_suggestions: list[str]      # Other advice
```

---

## 4. LLM Prompt Design

### 4.1 System Prompt (Greek Version)

```
ΡΟΛΟΣ: Είσαι Βοηθός HR Intelligence που αξιολογεί, συγκρίνει και κατατάσσει υποψηφίους.

ΔΕΝ εφαρμόζεις απλά φίλτρα.
ΑΝΑΛΥΕΙΣ, ΣΥΛΛΟΓΙΖΕΣΑΙ, ΣΥΓΚΡΙΝΕΙΣ και ΠΡΟΤΕΙΝΕΙΣ υποψηφίους με σαφείς εξηγήσεις κατάλληλες για αποφάσεις HR.

ΔΙΑΘΕΣΙΜΑ ΔΕΔΟΜΕΝΑ:
{candidate_profiles_json}

ΑΠΑΙΤΗΣΕΙΣ ΑΝΑΖΗΤΗΣΗΣ:
{requirements_json}

ΚΑΝΟΝΕΣ ΣΥΛΛΟΓΙΣΜΟΥ:

1. Αν τα αποτελέσματα είναι 0:
   - ΜΗΝ σταματάς
   - Εφάρμοσε ευφυή χαλάρωση κριτηρίων:
     * ERP αντί για συγκεκριμένο σύστημα
     * 2+ χρόνια αντί για 3+
     * Συναφής εμπειρία (π.χ. SAP FI ≈ ERP λογιστική)
   - Εξήγησε ποια κριτήρια χαλαρώθηκαν και γιατί

2. Αξιολόγηση Υποψηφίου:
   - Συνάφεια ρόλου
   - Έκθεση σε ERP/SAP
   - Χρόνια εμπειρίας (ρητά ή συναγόμενα)
   - Επάρκεια Αγγλικών
   - Συνολική καταλληλότητα

3. Σύγκριση:
   - Σύγκρινε υποψηφίους μεταξύ τους
   - Επισήμανε δυνατά σημεία και κενά
   - ΜΗΝ επιστρέφεις ακατέργαστες λίστες

4. Κατάταξη:
   - Παρέχε τους κορυφαίους υποψηφίους (Top 3-5)
   - Συμπερίλαβε σύντομη αιτιολόγηση ανά υποψήφιο

ΑΠΑΓΟΡΕΥΣΕΙΣ:
❌ ΜΗΝ επινοείς χρόνια εμπειρίας
❌ ΜΗΝ συμπεραίνεις "δεν υπάρχουν υποψήφιοι" χωρίς εναλλακτικές
❌ ΜΗΝ επιστρέφεις ακατέργαστες λίστες χωρίς ανάλυση

ΜΟΡΦΗ ΑΠΑΝΤΗΣΗΣ (JSON):
{response_schema}
```

### 4.2 System Prompt (English Version)

```
ROLE: You are an HR Intelligence Assistant that evaluates, compares, and ranks candidates.

You do NOT simply apply filters.
You ANALYZE, REASON, COMPARE, and RECOMMEND candidates with clear explanations suitable for HR decision-making.

AVAILABLE DATA:
{candidate_profiles_json}

SEARCH REQUIREMENTS:
{requirements_json}

REASONING RULES:

1. If results are 0:
   - Do NOT stop
   - Apply intelligent criteria relaxation:
     * ERP instead of specific system
     * 2+ years instead of 3+
     * Related experience (e.g., SAP FI ≈ ERP accounting)
   - Explain which criteria were relaxed and why

2. Candidate Evaluation:
   - Role relevance
   - ERP/SAP exposure
   - Years of experience (explicit or inferred)
   - English proficiency
   - Overall suitability

3. Comparison:
   - Compare candidates against each other
   - Highlight strengths and gaps
   - Do NOT return unprocessed lists

4. Ranking:
   - Provide top candidates (Top 3-5)
   - Include concise justification per candidate

PROHIBITIONS:
❌ Do NOT fabricate years of experience
❌ Do NOT conclude "no candidates available" without alternatives
❌ Do NOT return raw lists without analysis

RESPONSE FORMAT (JSON):
{response_schema}
```

### 4.3 Response Schema

```json
{
  "request_analysis": {
    "summary": "string",
    "mandatory_criteria": ["string"],
    "preferred_criteria": ["string"],
    "inferred_criteria": ["string"]
  },
  "query_outcome": {
    "direct_matches": "integer",
    "total_matches": "integer",
    "zero_results_reason": "string or null"
  },
  "criteria_expansion": {
    "relaxations": [
      {
        "original": "string",
        "relaxed_to": "string",
        "reasoning": "string"
      }
    ],
    "business_logic": "string"
  },
  "ranked_candidates": [
    {
      "rank": "integer",
      "candidate_id": "string",
      "candidate_name": "string",
      "role_relevance": {
        "score": "High|Medium|Low",
        "evidence": ["string"],
        "confidence": "Confirmed|Likely|Uncertain"
      },
      "skills_match": {
        "score": "High|Medium|Low",
        "evidence": ["string"],
        "confidence": "Confirmed|Likely|Uncertain"
      },
      "experience_assessment": {
        "total_years": "number or null",
        "relevant_years": "number or null",
        "assessment": "Exceeds|Meets|Below|Unknown",
        "notes": "string"
      },
      "language_proficiency": {
        "languages": [{"code": "string", "level": "string"}],
        "meets_requirement": "boolean",
        "notes": "string"
      },
      "strengths": ["string"],
      "gaps": ["string"],
      "risks": ["string"],
      "overall_suitability": "High|Medium-High|Medium|Medium-Low|Low"
    }
  ],
  "hr_recommendation": {
    "top_candidates": ["string"],
    "recommendation_summary": "string",
    "interview_focus_points": ["string"],
    "additional_suggestions": ["string"]
  }
}
```

---

## 5. API Changes

### 5.1 Request Format

No changes to request format. Analysis is automatic for all queries.

```json
POST /query
{
  "query": "Λογιστές με SAP, 3+ χρόνια, Αγγλικά",
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

    // Existing fields (unchanged)
    "translation": {...},
    "sql": {...},
    "results": [...],
    "result_count": 5,

    // NEW: HR Intelligence Analysis
    "hr_analysis": {
      "request_analysis": {
        "summary": "Αναζήτηση λογιστών με εμπειρία SAP/ERP, τουλάχιστον 3 χρόνια, με γνώση Αγγλικών",
        "mandatory_criteria": ["Λογιστικό background", "SAP/ERP εμπειρία", "Αγγλικά"],
        "preferred_criteria": ["≥3 χρόνια εμπειρίας"],
        "inferred_criteria": ["Γνώση Excel", "Εργασία σε εταιρικό περιβάλλον"]
      },
      "query_outcome": {
        "direct_matches": 0,
        "total_matches": 5,
        "zero_results_reason": "Δεν υπάρχουν υποψήφιοι με ακριβώς 3+ χρόνια τεκμηριωμένης εμπειρίας SAP"
      },
      "criteria_expansion": {
        "relaxations": [
          {
            "original": "SAP ERP, 3+ χρόνια",
            "relaxed_to": "Οποιοδήποτε ERP σύστημα, 2+ χρόνια",
            "reasoning": "Το SAP είναι πλατφόρμα ERP - η εμπειρία σε άλλα ERP (Singular, SoftOne) είναι μεταφερόμενη"
          }
        ],
        "business_logic": "Η λογιστική γνώση και η εξοικείωση με ERP συστήματα είναι πιο σημαντική από το συγκεκριμένο σύστημα"
      },
      "ranked_candidates": [
        {
          "rank": 1,
          "candidate_id": "uuid-1",
          "candidate_name": "Φαίη Νάτσιου",
          "role_relevance": {
            "score": "High",
            "evidence": ["Λογιστική εμπειρία", "Εργασία σε λογιστήριο"],
            "confidence": "Confirmed"
          },
          "skills_match": {
            "score": "High",
            "evidence": ["SAP ERP", "Microsoft Excel Advanced"],
            "confidence": "Confirmed"
          },
          "experience_assessment": {
            "total_years": null,
            "relevant_years": null,
            "assessment": "Unknown",
            "notes": "Απαιτείται επιβεβαίωση χρόνων εμπειρίας στη συνέντευξη"
          },
          "language_proficiency": {
            "languages": [{"code": "en", "level": "Professional"}],
            "meets_requirement": true,
            "notes": "Αγγλικά πιθανώς επαγγελματικού επιπέδου"
          },
          "strengths": [
            "SAP εμπειρία επιβεβαιωμένη",
            "Excel advanced",
            "Λογιστικό background"
          ],
          "gaps": [
            "Χρόνια εμπειρίας χρειάζονται επιβεβαίωση"
          ],
          "risks": [],
          "overall_suitability": "High"
        }
        // ... more candidates
      ],
      "hr_recommendation": {
        "top_candidates": ["Φαίη Νάτσιου", "Χαράλαμπος Γκιθώνας", "Ελένη-Παρασκευή Βακαλοπούλου"],
        "recommendation_summary": "Προτείνονται 3 υποψήφιοι με επιβεβαιωμένη εμπειρία SAP/ERP. Η Φαίη Νάτσιου είναι η καλύτερη επιλογή λόγω του συνδυασμού SAP + Excel.",
        "interview_focus_points": [
          "Επιβεβαίωση χρόνων εμπειρίας",
          "Βάθος γνώσεων SAP (modules used)",
          "Επίπεδο Αγγλικών (oral assessment)",
          "Εμπειρία σε λογιστικές εργασίες (closing, reporting)"
        ],
        "additional_suggestions": [
          "Ζητήστε παραδείγματα SAP transactions που χρησιμοποιούσαν",
          "Ελέγξτε για πιστοποιήσεις SAP αν υπάρχουν"
        ]
      },

      // Metadata
      "analysis_language": "el",
      "analysis_latency_ms": 4521
    },

    // Existing metadata
    "request_id": "abc123",
    "latency_ms": 7234,
    "cached": false
  }
}
```

---

## 6. Implementation Plan

### 6.1 Phase 1: Core Module (Priority: P0)

| Task | Description | Effort |
|------|-------------|--------|
| 1.1 | Create `hr_intelligence/` module structure | 1h |
| 1.2 | Implement `schema.py` with dataclasses | 2h |
| 1.3 | Implement `prompts.py` with Greek/English templates | 2h |
| 1.4 | Implement `analyzer.py` main logic | 4h |
| 1.5 | Language detection from query | 1h |

### 6.2 Phase 2: Integration (Priority: P0)

| Task | Description | Effort |
|------|-------------|--------|
| 2.1 | Integrate with `query/handler.py` | 2h |
| 2.2 | Enrich candidate profiles before analysis | 2h |
| 2.3 | Update API response format | 1h |
| 2.4 | Error handling and fallbacks | 2h |

### 6.3 Phase 3: Testing & Refinement (Priority: P1)

| Task | Description | Effort |
|------|-------------|--------|
| 3.1 | Unit tests for analyzer | 2h |
| 3.2 | Integration tests with real queries | 3h |
| 3.3 | Prompt refinement based on results | 4h |
| 3.4 | Performance optimization | 2h |

**Total Estimated Effort**: ~28 hours

---

## 7. Cost Analysis

### 7.1 Per-Query Cost

| Component | Model | Input Tokens | Output Tokens | Cost |
|-----------|-------|--------------|---------------|------|
| HR Analysis | Claude Sonnet 4.5 | ~3,000 | ~1,500 | ~$0.02 |
| (Existing) Query Translation | Claude Haiku | ~500 | ~200 | ~$0.001 |
| (Existing) SQL Execution | - | - | - | ~$0 |

**Total per query**: ~$0.02 (vs current ~$0.001)

### 7.2 Monthly Cost Projection

| Usage | Queries/Month | Additional Cost |
|-------|---------------|-----------------|
| Low | 1,000 | $20 |
| Medium | 5,000 | $100 |
| High | 10,000 | $200 |

### 7.3 Cost Optimization Options

1. **Cache analysis** for identical queries (24h TTL)
2. **Use Haiku for simple queries** (< 3 candidates)
3. **Optional analysis** via `"analyze": false` parameter (future)

---

## 8. Example Scenarios

### 8.1 Scenario: Zero Direct Results

**Query**: "Accountants with SAP, 5+ years, English, Athens"

**Direct Results**: 0

**HR Intelligence Response**:
```
📊 Query Outcome:
- Direct matches: 0
- Reason: No candidates have both 5+ years SAP AND Athens location confirmed

🔄 Criteria Relaxation:
- "5+ years" → "2+ years" (experience often underreported in CVs)
- "Athens only" → "Athens region or remote-capable"
- Reasoning: SAP skills are scarce; geographic flexibility recommended

📋 Recommended Candidates:
1. Candidate A (Larissa) - Strong SAP, available for relocation
2. Candidate B (Athens area) - 3 years ERP, SAP training
3. Candidate C (Remote) - 4 years SAP, English fluent

💡 HR Recommendation:
Consider remote work arrangements or relocation support to access
broader talent pool. All 3 candidates warrant interviews.
```

### 8.2 Scenario: Multiple Good Matches

**Query**: "Excel experts"

**Direct Results**: 15

**HR Intelligence Response**:
```
📊 Query Outcome:
- Direct matches: 15
- Analysis: Large pool with varying Excel proficiency levels

📋 Top 5 Ranked Candidates:
1. Ελένη Βακαλοπούλου - Excel Expert + SAP + Accounting
2. Βάγια Βαΐτση - Excel Advanced + MS Office Suite
3. Agoritsa Petalouda - Excel + Google Sheets + Data Analysis
...

💡 HR Recommendation:
Strong candidate pool. Top 3 have complementary skills.
Interview focus: Specific Excel functions used (VLOOKUP, Pivot, Macros)
```

---

## 9. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM hallucination (invented experience) | High | Strict prompt rules, JSON schema validation |
| Slow response times | Medium | Async processing, caching, timeout limits |
| Inconsistent language | Low | Explicit language detection, prompt enforcement |
| Cost overrun | Medium | Usage monitoring, optional analysis flag (future) |

---

## 10. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| User satisfaction | >80% positive | Feedback surveys |
| Analysis accuracy | >90% correct rankings | Manual review sample |
| Response time | <10 seconds total | P95 latency monitoring |
| Cost per query | <$0.05 | AWS cost tracking |

---

## 11. Future Enhancements

1. **Configurable analysis depth** - Quick vs Detailed mode
2. **Custom evaluation criteria** - Per-job posting weights
3. **Learning from feedback** - Improve rankings based on hiring outcomes
4. **Batch analysis** - Analyze multiple queries in one call
5. **Export to PDF** - Generate HR reports

---

## Appendix A: File Structure

```
src/lcmgo_cagenai/hr_intelligence/
├── __init__.py
│   └── exports: HRIntelligenceAnalyzer, HRAnalysisReport
│
├── analyzer.py
│   └── class HRIntelligenceAnalyzer
│       ├── analyze(input: HRAnalysisInput) -> HRAnalysisReport
│       ├── _detect_language(query: str) -> str
│       ├── _build_prompt(input, language) -> str
│       ├── _parse_response(llm_response) -> HRAnalysisReport
│       └── _validate_response(report) -> bool
│
├── prompts.py
│   └── SYSTEM_PROMPT_EL: str
│   └── SYSTEM_PROMPT_EN: str
│   └── RESPONSE_SCHEMA: dict
│   └── get_prompt(language: str) -> str
│
└── schema.py
    └── dataclasses: HRAnalysisInput, HRAnalysisReport,
        RequestAnalysis, QueryOutcome, CriteriaExpansion,
        RankedCandidate, EvaluationScore, HRRecommendation
```

---

## Appendix B: Integration Points

### B.1 Query Lambda Handler

```python
# lambda/query/handler.py

async def process_query(...):
    # Existing code...

    # After getting results
    if execute and len(results) > 0:
        # NEW: HR Intelligence Analysis
        from lcmgo_cagenai.hr_intelligence import HRIntelligenceAnalyzer

        analyzer = HRIntelligenceAnalyzer(llm_provider=llm)
        hr_report = await analyzer.analyze(
            HRAnalysisInput(
                original_query=user_query,
                requirements=route_result.translation,
                candidates=enriched_candidates,
                relaxations_applied=relaxations,
                direct_result_count=direct_count,
                total_result_count=len(results)
            )
        )

        response["hr_analysis"] = hr_report.to_dict()
```

### B.2 Candidate Profile Enrichment

Before analysis, enrich candidate data:

```python
async def enrich_candidates(candidate_ids: list[str]) -> list[CandidateProfile]:
    """Fetch full profiles for HR analysis"""
    profiles = []
    for cid in candidate_ids:
        profile = await get_candidate_full_profile(cid)  # Existing function
        profiles.append(profile)
    return profiles
```

---

**Document Status**: Ready for Implementation
**Next Steps**: Create `src/lcmgo_cagenai/hr_intelligence/` module
