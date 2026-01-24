-- Rollback: Reset duration_months (if needed)
-- WARNING: This will lose calculated duration data
-- Only use if the migration caused issues

BEGIN;

UPDATE candidate_experience
SET duration_months = NULL;

RAISE NOTICE 'Reset all duration_months to NULL';

COMMIT;
