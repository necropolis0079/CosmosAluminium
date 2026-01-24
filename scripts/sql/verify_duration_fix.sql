-- Verification queries for duration_months fix
-- Run these after the migration to verify the fix worked correctly
-- Date: 2026-01-24

\echo '========================================='
\echo '1. DURATION_MONTHS COVERAGE CHECK'
\echo '========================================='
SELECT
    COUNT(*) FILTER (WHERE duration_months IS NOT NULL) as has_duration,
    COUNT(*) FILTER (WHERE duration_months IS NULL) as missing_duration,
    COUNT(*) as total,
    ROUND(COUNT(*) FILTER (WHERE duration_months IS NOT NULL)::numeric /
          NULLIF(COUNT(*), 0) * 100, 1) as coverage_percent
FROM candidate_experience;

\echo ''
\echo '========================================='
\echo '2. SAMPLE OF CALCULATED DURATIONS'
\echo '========================================='
SELECT
    c.last_name || ' ' || c.first_name as candidate,
    ce.job_title,
    ce.company_name,
    ce.start_date,
    ce.end_date,
    ce.is_current,
    ce.duration_months,
    ROUND(ce.duration_months / 12.0, 1) as years
FROM candidate_experience ce
JOIN candidates c ON ce.candidate_id = c.id
WHERE ce.duration_months IS NOT NULL
ORDER BY ce.duration_months DESC NULLS LAST
LIMIT 20;

\echo ''
\echo '========================================='
\echo '3. TOTAL EXPERIENCE PER CANDIDATE'
\echo '========================================='
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

\echo ''
\echo '========================================='
\echo '4. CANDIDATES WITH 3+ YEARS ACCOUNTING'
\echo '========================================='
SELECT
    c.last_name || ' ' || c.first_name as candidate,
    SUM(ce.duration_months) as accounting_months,
    ROUND(SUM(ce.duration_months) / 12.0, 1) as accounting_years
FROM candidates c
JOIN candidate_experience ce ON ce.candidate_id = c.id
WHERE ce.duration_months IS NOT NULL
  AND (ce.job_title ILIKE '%λογιστ%' OR ce.job_title ILIKE '%accountant%')
GROUP BY c.id, c.last_name, c.first_name
HAVING SUM(ce.duration_months) >= 36
ORDER BY accounting_months DESC;

\echo ''
\echo '========================================='
\echo '5. VERIFY get_candidate_full_profile'
\echo '========================================='
SELECT
    (profile->>'first_name') || ' ' || (profile->>'last_name') as name,
    profile->>'total_experience_years' as experience_years
FROM (
    SELECT get_candidate_full_profile(id) as profile
    FROM candidates
    LIMIT 10
) sub;

\echo ''
\echo '========================================='
\echo 'VERIFICATION COMPLETE'
\echo '========================================='
