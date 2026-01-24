# HR Intelligence Accuracy Issues

**Date**: 2026-01-24
**Status**: Analysis Complete, Implementation Pending
**Priority**: CRITICAL
**Affects**: Candidate matching, experience filtering, HR analysis accuracy

---

## Executive Summary

Comparison testing between our HR Intelligence system and an external system revealed that our system produces significantly less accurate results. The external system correctly identified top candidates with 17-30 years of accounting experience, while our system showed "0 years" for the same candidates and failed to rank them appropriately.

---

## Issue Discovery

### Test Case: Accountant Position Search

**Job Requirements:**
- Πτυχίο λογιστικής ή συναφούς κλάδου
- Προϋπηρεσία τουλάχιστον 3 ετών
- Γνώση ελληνικής φορολογικής νομοθεσίας
- Γνώση ERP και λογιστικής μηχανογράφησης

### Results Comparison

| Candidate | Our System | External System | Actual (DB) |
|-----------|------------|-----------------|-------------|
| ΤΣΑΜΗ ΣΠΥΡΙΔΟΥΛΑ | 62%, **0 years** | 12 years | **7.8 years** |
| ΒΑΙΤΣΗ ΒΑΙΑ | 55%, **0 years** | 6.8 years | **6.4 years** |
| ΔΗΜΟΠΟΥΛΟΥ ΜΑΡΙΑ | **Not shown** | 19.5 years | **17 years** |
| ΘΕΟΧΑΡΗ ΓΕΩΡΓΙΑ | 53% | 7.8 years | **6.5 years** |

### Key Findings

1. **Experience = 0 for all candidates** - Critical data loss
2. **Top candidates missing** - ΔΗΜΟΠΟΥΛΟΥ (17 years) not in results
3. **Incorrect ranking** - Lower experience candidates ranked higher

---

## Root Cause Analysis

### Issue #1: duration_months Not Calculated (CRITICAL)

**Location**: `src/lcmgo_cagenai/parser/db_writer.py` - `_insert_experience()` method

**Problem**: The `duration_months` field in `candidate_experience` table is never populated during CV parsing.

**Current Code Flow**:
```
CV Parsed → experience has start_date, end_date
         → _insert_experience() called
         → INSERT INTO candidate_experience(...)
         → duration_months = NULL (not included in INSERT)
```

**Impact**:
- All experience records have `duration_months = NULL`
- SQL `SUM(duration_months) / 12.0` returns NULL → COALESCE to 0
- `total_experience_years = 0` for ALL candidates
- Experience-based queries ("5+ years") return 0 results

**Evidence** (from database check):
```sql
-- All duration_months are NULL
SELECT duration_months FROM candidate_experience LIMIT 10;
-- Result: NULL, NULL, NULL, ...
```

### Issue #2: HR Intelligence Ranking Algorithm

**Location**: `src/lcmgo_cagenai/hr_intelligence/analyzer.py`

**Problem**: The analyzer receives `total_experience_years = 0` for all candidates, making experience-based ranking impossible.

**Current Weights**:
```python
weights = {
    "role": 0.25,
    "experience": 0.30,  # 30% weight, but always 0!
    "software": 0.20,
    "skills": 0.10,
    "language": 0.10,
    "certification": 0.05,
}
```

**Impact**: 30% of scoring weight is effectively zeroed out.

### Issue #3: Certifications Not Linked

**Location**: `src/lcmgo_cagenai/parser/db_writer.py` - `_insert_certifications()`

**Problem**: Professional certifications from education (e.g., "Master από Ινστιτούτο Ορκωτών Ελεγκτών") are stored as education, not as certifications.

**Example**:
- ΒΑΙΤΣΗ ΒΑΙΑ has "Μεταπτυχιακός Επαγγελματικός Τίτλος Κατάρτισης Ελεγκτών Λογιστών" from Ινστιτούτο Σώματος Ορκωτών Ελεγκτών
- This should map to certification "Greek Accountant License" but appears only as education

**Impact**: 5% of scoring (certification weight) is diminished.

---

## Detailed Code Analysis

### 1. Experience Duration Calculation

**File**: `src/lcmgo_cagenai/parser/db_writer.py`
**Method**: `_insert_experience()` (lines 918-989)

**Current Implementation**:
```python
def _insert_experience(self, cursor: Any, candidate_id: UUID, experience: list) -> None:
    for exp in experience:
        # ... date validation ...

        cursor.execute(
            """
            INSERT INTO candidate_experience (
                candidate_id, company_name, ...,
                start_date, end_date, is_current,
                description, ...
                -- NO duration_months!
            ) VALUES (...)
            """,
            (
                str(candidate_id),
                company_name,
                start_date,      # ← Has date
                end_date,        # ← Has date
                exp.is_current,
                description,
                # ← duration_months MISSING!
            ),
        )
```

**Required Fix**: Calculate `duration_months` from dates before INSERT.

### 2. SQL Queries Expecting duration_months

**File**: `scripts/sql/019_job_matching.sql`
**Function**: `get_candidate_full_profile()` (lines 288-374)

```sql
'total_experience_years', (
    SELECT COALESCE(SUM(duration_months) / 12.0, 0)
    FROM candidate_experience
    WHERE candidate_id = c.id
)
```

This SQL is correct but returns 0 because all `duration_months` are NULL.

### 3. Experience Filter in SQL Generator

**File**: `src/lcmgo_cagenai/query/sql_generator.py`
**Method**: `_build_subquery_clause()` (around line 370)

```python
# Experience years filter
if filter_type == "experience_years":
    subquery = f"""
        SELECT 1 FROM candidate_experience ce
        WHERE ce.candidate_id = c.id
        GROUP BY ce.candidate_id
        HAVING SUM(ce.duration_months) / 12.0 >= {value}
    """
```

Returns 0 results because `SUM(NULL) = NULL`.

---

## Database Verification

### Actual Experience Data (calculated from dates):

```sql
WITH exp_calc AS (
    SELECT
        c.last_name || ' ' || c.first_name as name,
        SUM(
            EXTRACT(YEAR FROM AGE(COALESCE(e.end_date, CURRENT_DATE), e.start_date)) * 12 +
            EXTRACT(MONTH FROM AGE(COALESCE(e.end_date, CURRENT_DATE), e.start_date))
        ) as total_months
    FROM candidates c
    JOIN candidate_experience e ON e.candidate_id = c.id
    WHERE e.start_date IS NOT NULL
      AND (e.job_title ILIKE '%λογιστ%' OR e.job_title ILIKE '%accountant%')
    GROUP BY c.id, c.last_name, c.first_name
)
SELECT name, ROUND(total_months / 12.0, 1) as years
FROM exp_calc
WHERE total_months >= 36
ORDER BY total_months DESC;
```

**Results**:
| Candidate | Accounting Experience |
|-----------|----------------------|
| Παυλοπούλου-Καραμούρτου Ξανθή | 30.6 years |
| Αποστόλου Ευδοξία | 25.8 years |
| Δημοπούλου Μαρία | 17.0 years |
| Τζαστούδη Δέσποινα | 15.7 years |
| ΕΥΠΡΑΞΙΑΔΗ ΑΓΛΑΙΑ | 11.0 years |
| Φλώρου Γεωργία | 10.8 years |
| Τσάμη Σπυριδούλα | 7.8 years |
| Τσιάκα Μαρία | 7.7 years |
| ΣΙΜΑΤΟΣ ΔΗΜΗΤΡΗΣ | 7.1 years |
| Θεοχάρη Γεωργία | 6.5 years |
| Βαΐτση Βάγια | 6.4 years |

**These candidates exist and have significant experience, but our system shows 0.**

---

## Affected Components

| Component | File | Impact |
|-----------|------|--------|
| CV Parser | `db_writer.py` | `duration_months` not written |
| Query Handler | `lambda/query/handler.py` | Enrichment gets 0 experience |
| SQL Generator | `sql_generator.py` | Experience filters fail |
| HR Intelligence | `analyzer.py` | Incorrect scoring |
| PostgreSQL Function | `019_job_matching.sql` | Returns 0 for experience |

---

## Testing Validation

### Before Fix (Current State)
```
Query: "Λογιστής με 3+ χρόνια εμπειρία"
Results: 0 candidates (should be 13+)

Query: "Accountants with Singular experience"
Results: Shows candidates but all have "0 years experience"
```

### After Fix (Expected)
```
Query: "Λογιστής με 3+ χρόνια εμπειρία"
Results: 13 candidates ranked by experience

Query: "Accountants with Singular experience"
Results: Candidates with correct experience years
```

---

## Related Documentation

- `docs/HR-INTELLIGENCE-UNIFIED.md` - HR Intelligence design
- `docs/PHASE-1-2-IMPLEMENTATION.md` - Original implementation
- `docs/Validation/README.md` - Validation tasks overview
- `scripts/sql/019_job_matching.sql` - PostgreSQL functions

---

## References

- Session 46 comparison testing
- External system results for validation
- Database queries for verification
