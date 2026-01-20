-- ============================================================================
-- Rollback: 019_job_matching_rollback.sql
-- Description: Rollback job matching view and functions
-- Version: 1.0
-- Date: 2026-01-20
-- ============================================================================

-- Drop functions first (they depend on view)
DROP FUNCTION IF EXISTS get_candidate_full_profile(UUID);
DROP FUNCTION IF EXISTS match_candidates_relaxed(TEXT, NUMERIC, TEXT[], TEXT[], TEXT[], INTEGER);

-- Drop view
DROP VIEW IF EXISTS v_candidate_match_data;

-- Drop index
DROP INDEX IF EXISTS idx_candidate_experience_duration;

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Rollback 019_job_matching completed successfully';
    RAISE NOTICE 'Dropped view: v_candidate_match_data';
    RAISE NOTICE 'Dropped function: match_candidates_relaxed';
    RAISE NOTICE 'Dropped function: get_candidate_full_profile';
END $$;
