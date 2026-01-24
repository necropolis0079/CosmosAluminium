# Implementation Plan: HR Intelligence Accuracy Fix

**Date**: 2026-01-24
**Issue Reference**: `docs/ISSUE-HR-INTELLIGENCE-ACCURACY.md`
**Estimated Effort**: 4-6 hours
**Priority**: CRITICAL

---

## Overview

This plan addresses three interconnected issues that cause HR Intelligence to show incorrect experience data and produce inaccurate candidate rankings.

---

## Fix Summary

| Fix # | Issue | Solution | Files |
|-------|-------|----------|-------|
| 1 | duration_months not calculated | Calculate and insert during CV parsing | `db_writer.py` |
| 2 | Existing data has NULL duration | Migration script to backfill | New SQL migration |
| 3 | HR ranking with 0 experience | Will auto-fix after #1 and #2 | N/A |

---

## Phase 1: Fix duration_months Calculation

### 1.1 Update db_writer.py

**File**: `src/lcmgo_cagenai/parser/db_writer.py`
**Method**: `_insert_experience()`

**Changes Required**:

1. Add import at top of file:
```python
from dateutil.relativedelta import relativedelta
```

2. Add duration calculation function:
```python
def _calculate_duration_months(
    start_date: date | None,
    end_date: date | None,
    is_current: bool
) -> int | None:
    """
    Calculate experience duration in months.

    Args:
        start_date: Job start date
        end_date: Job end date (None if current)
        is_current: Whether this is current employment

    Returns:
        Duration in months, or None if start_date is missing
    """
    if not start_date:
        return None

    # Determine end date
    if is_current or end_date is None:
        calc_end = date.today()
    else:
        calc_end = end_date

    # Ensure end is after start
    if calc_end < start_date:
        # Swap dates (already handled elsewhere, but be safe)
        start_date, calc_end = calc_end, start_date

    # Calculate difference
    delta = relativedelta(calc_end, start_date)
    duration = (delta.years * 12) + delta.months

    # Minimum 1 month if dates are valid
    return max(duration, 1) if duration >= 0 else None
```

3. Modify `_insert_experience()` method:
```python
def _insert_experience(self, cursor: Any, candidate_id: UUID, experience: list) -> None:
    """Insert experience records."""
    for exp in experience:
        # ... existing validation code ...

        # Calculate duration
        duration_months = _calculate_duration_months(
            start_date,
            end_date,
            exp.is_current
        )

        cursor.execute(
            """
            INSERT INTO candidate_experience (
                candidate_id, company_name, company_name_normalized,
                company_industry, company_city, company_country,
                job_title, job_title_normalized, role_id,
                department, employment_type,
                start_date, end_date, is_current, duration_months,
                description, responsibilities, achievements, technologies_used,
                team_size, reports_to,
                raw_text, confidence_score
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s
            )
            """,
            (
                str(candidate_id),
                company_name,
                normalize_text(company_name) if company_name else None,
                exp.company_industry,
                exp.company_city,
                exp.company_country,
                job_title,
                normalize_text(job_title) if job_title else None,
                str(role_id) if role_id else None,
                exp.department,
                exp.employment_type,
                start_date,
                end_date,
                exp.is_current,
                duration_months,  # NEW
                description,
                responsibilities,
                achievements_str,
                technologies_str,
                exp.team_size,
                exp.reports_to,
                exp.raw_text,
                exp.confidence_score,
            ),
        )
```

### 1.2 Add Import Statement

At top of `db_writer.py`, add:
```python
from dateutil.relativedelta import relativedelta
```

Note: `python-dateutil` is already in Lambda layer dependencies.

---

## Phase 2: Backfill Existing Data

### 2.1 Create Migration Script

**File**: `scripts/sql/024_backfill_duration_months.sql`

```sql
-- Migration: Backfill duration_months for existing experience records
-- Date: 2026-01-24
-- Issue: HR Intelligence showing 0 years experience

BEGIN;

-- Update all experience records with calculated duration
UPDATE candidate_experience
SET duration_months = (
    CASE
        -- Current job: calculate from start to today
        WHEN is_current = true OR end_date IS NULL THEN
            (EXTRACT(YEAR FROM AGE(CURRENT_DATE, start_date)) * 12 +
             EXTRACT(MONTH FROM AGE(CURRENT_DATE, start_date)))::INTEGER
        -- Past job: calculate from start to end
        WHEN end_date IS NOT NULL AND start_date IS NOT NULL THEN
            (EXTRACT(YEAR FROM AGE(end_date, start_date)) * 12 +
             EXTRACT(MONTH FROM AGE(end_date, start_date)))::INTEGER
        ELSE NULL
    END
)
WHERE start_date IS NOT NULL
  AND duration_months IS NULL;

-- Ensure minimum 1 month for valid records
UPDATE candidate_experience
SET duration_months = 1
WHERE duration_months IS NOT NULL
  AND duration_months < 1
  AND start_date IS NOT NULL;

-- Log results
DO $$
DECLARE
    updated_count INTEGER;
    null_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO updated_count
    FROM candidate_experience
    WHERE duration_months IS NOT NULL;

    SELECT COUNT(*) INTO null_count
    FROM candidate_experience
    WHERE duration_months IS NULL;

    RAISE NOTICE 'Updated % experience records with duration_months', updated_count;
    RAISE NOTICE 'Remaining % records with NULL duration (missing start_date)', null_count;
END $$;

COMMIT;
```

### 2.2 Create Rollback Script

**File**: `scripts/sql/024_backfill_duration_months_rollback.sql`

```sql
-- Rollback: Reset duration_months (if needed)
-- WARNING: This will lose calculated duration data

BEGIN;

UPDATE candidate_experience
SET duration_months = NULL;

COMMIT;
```

---

## Phase 3: Verification

### 3.1 Post-Migration Verification Queries

**File**: `scripts/sql/verify_duration_fix.sql`

```sql
-- Verification queries for duration_months fix

-- 1. Check NULL count (should be minimal)
SELECT
    COUNT(*) FILTER (WHERE duration_months IS NOT NULL) as has_duration,
    COUNT(*) FILTER (WHERE duration_months IS NULL) as missing_duration,
    COUNT(*) as total
FROM candidate_experience;

-- 2. Sample of calculated durations
SELECT
    c.last_name || ' ' || c.first_name as candidate,
    ce.job_title,
    ce.start_date,
    ce.end_date,
    ce.is_current,
    ce.duration_months,
    ROUND(ce.duration_months / 12.0, 1) as years
FROM candidate_experience ce
JOIN candidates c ON ce.candidate_id = c.id
ORDER BY ce.duration_months DESC NULLS LAST
LIMIT 20;

-- 3. Total experience per candidate
SELECT
    c.last_name || ' ' || c.first_name as candidate,
    COUNT(ce.id) as job_count,
    SUM(ce.duration_months) as total_months,
    ROUND(SUM(ce.duration_months) / 12.0, 1) as total_years
FROM candidates c
JOIN candidate_experience ce ON ce.candidate_id = c.id
WHERE ce.duration_months IS NOT NULL
GROUP BY c.id, c.last_name, c.first_name
ORDER BY total_months DESC
LIMIT 20;

-- 4. Verify get_candidate_full_profile returns correct data
SELECT
    (profile->>'first_name') || ' ' || (profile->>'last_name') as name,
    profile->>'total_experience_years' as experience_years
FROM (
    SELECT get_candidate_full_profile(id) as profile
    FROM candidates
    LIMIT 10
) sub;
```

### 3.2 API Verification Test

After deployment, test with:
```bash
curl -X POST https://API_ENDPOINT/v1/test/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Λογιστές με 5+ χρόνια εμπειρία"}'
```

Expected: Candidates with 5+ years experience in results.

---

## Implementation Steps

### Step 1: Code Changes
1. [ ] Edit `db_writer.py` - add `_calculate_duration_months()` function
2. [ ] Edit `db_writer.py` - modify `_insert_experience()` to calculate and insert duration
3. [ ] Add import for `relativedelta`
4. [ ] Run syntax check: `python -m py_compile db_writer.py`

### Step 2: Build and Deploy Lambda
1. [ ] Build Lambda layer ZIP
2. [ ] Publish new layer version
3. [ ] Update cv-parser Lambda to use new layer
4. [ ] Update cv-processor Lambda to use new layer

### Step 3: Database Migration
1. [ ] Copy migration script to bastion
2. [ ] Run `024_backfill_duration_months.sql`
3. [ ] Verify with `verify_duration_fix.sql`

### Step 4: Verification Testing
1. [ ] Test CV upload - verify duration_months populated
2. [ ] Test HR Intelligence query - verify experience shows correctly
3. [ ] Compare results with external system

### Step 5: Git Commit
1. [ ] Stage all changes
2. [ ] Commit with message referencing issue
3. [ ] Push to GitLab and GitHub

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/lcmgo_cagenai/parser/db_writer.py` | MODIFY | Add duration calculation |
| `scripts/sql/024_backfill_duration_months.sql` | CREATE | Backfill migration |
| `scripts/sql/024_backfill_duration_months_rollback.sql` | CREATE | Rollback script |
| `scripts/sql/verify_duration_fix.sql` | CREATE | Verification queries |
| `docs/ISSUE-HR-INTELLIGENCE-ACCURACY.md` | CREATE | Issue documentation |
| `docs/IMPLEMENTATION-PLAN-HR-FIX.md` | CREATE | This plan |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Migration affects production data | Medium | High | Run in transaction, test on sample first |
| Duration calculation edge cases | Low | Medium | Add validation for negative/extreme values |
| Lambda deployment issues | Low | Medium | Keep previous layer version, can rollback |
| Overlapping experience miscounted | Medium | Low | Document as known limitation |

---

## Success Criteria

1. **Experience Calculation**: All experience records have `duration_months` populated
2. **Query Results**: "5+ years experience" queries return qualified candidates
3. **HR Analysis**: Candidates show correct experience years in analysis
4. **Ranking Accuracy**: Top candidates match external system ranking

---

## Post-Implementation

### Update Documentation
- [ ] Update `docs/PROGRESS.md` with session notes
- [ ] Update `CLAUDE.md` Last Session section
- [ ] Mark issue as resolved in documentation

### Future Improvements (Optional)
1. Add trigger on `candidate_experience` to auto-calculate duration on INSERT
2. Handle overlapping experience periods (don't double-count)
3. Add experience_years to candidate summary for faster queries
