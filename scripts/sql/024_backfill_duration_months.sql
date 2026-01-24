-- Migration: Backfill duration_months for existing experience records
-- Date: 2026-01-24
-- Issue: HR Intelligence showing 0 years experience for all candidates
-- Reference: docs/ISSUE-HR-INTELLIGENCE-ACCURACY.md

-- This migration fixes the critical bug where duration_months was never
-- calculated during CV parsing, causing all candidates to show 0 years
-- of experience in HR Intelligence analysis.

BEGIN;

-- Step 1: Update all experience records where duration_months is NULL
-- Calculate based on start_date and end_date (or CURRENT_DATE for current jobs)
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

-- Step 2: Ensure minimum 1 month for valid records
-- (very short employment should still count as at least 1 month)
UPDATE candidate_experience
SET duration_months = 1
WHERE duration_months IS NOT NULL
  AND duration_months < 1
  AND start_date IS NOT NULL;

-- Step 3: Log results
DO $$
DECLARE
    updated_count INTEGER;
    null_count INTEGER;
    total_count INTEGER;
    avg_duration NUMERIC;
BEGIN
    SELECT COUNT(*) INTO total_count FROM candidate_experience;

    SELECT COUNT(*) INTO updated_count
    FROM candidate_experience
    WHERE duration_months IS NOT NULL;

    SELECT COUNT(*) INTO null_count
    FROM candidate_experience
    WHERE duration_months IS NULL;

    SELECT ROUND(AVG(duration_months)::NUMERIC, 1) INTO avg_duration
    FROM candidate_experience
    WHERE duration_months IS NOT NULL;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'DURATION_MONTHS BACKFILL COMPLETE';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Total experience records: %', total_count;
    RAISE NOTICE 'Records with duration_months: %', updated_count;
    RAISE NOTICE 'Records still NULL (missing start_date): %', null_count;
    RAISE NOTICE 'Average duration: % months', avg_duration;
    RAISE NOTICE '========================================';
END $$;

COMMIT;

-- Verification query (run after migration)
-- SELECT
--     c.last_name || ' ' || c.first_name as candidate,
--     COUNT(ce.id) as job_count,
--     SUM(ce.duration_months) as total_months,
--     ROUND(SUM(ce.duration_months) / 12.0, 1) as total_years
-- FROM candidates c
-- JOIN candidate_experience ce ON ce.candidate_id = c.id
-- WHERE ce.duration_months IS NOT NULL
-- GROUP BY c.id, c.last_name, c.first_name
-- ORDER BY total_months DESC
-- LIMIT 20;
