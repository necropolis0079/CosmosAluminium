-- =============================================================================
-- Migration: 016_unmatched_cv_data.sql
-- Purpose: Create table to capture unmapped CV data (zero data loss policy)
-- Date: 2026-01-19
-- Version: 1.0
-- =============================================================================

-- =============================================================================
-- TABLE: unmatched_cv_data
-- Purpose: Capture any CV data that cannot be mapped to existing structure
-- =============================================================================

CREATE TABLE IF NOT EXISTS unmatched_cv_data (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign Key to candidate
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,

    -- Classification attempt by LLM
    suggested_section VARCHAR(50) NOT NULL,
    -- Values: 'personal', 'experience', 'education', 'skill', 'soft_skill',
    --         'software', 'certification', 'license', 'language', 'other'

    -- The data itself
    field_name VARCHAR(255) NOT NULL,       -- What the LLM named this field
    field_value TEXT NOT NULL,               -- The actual value from CV
    field_value_normalized TEXT,             -- Normalized version (lowercase, trimmed)

    -- Context for review
    source_text TEXT,                        -- Original text snippet from CV
    extraction_confidence DECIMAL(3,2),      -- 0.00 to 1.00
    llm_reasoning TEXT,                      -- Why LLM couldn't map it

    -- Review workflow
    review_status VARCHAR(20) DEFAULT 'pending',
    -- Values: 'pending', 'reviewed', 'added_to_taxonomy', 'mapped', 'discarded'
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,

    -- If mapped after review, where did it go?
    mapped_to_table VARCHAR(50),
    mapped_to_id UUID,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- For finding unreviewed items
CREATE INDEX IF NOT EXISTS idx_unmatched_cv_data_review_status
    ON unmatched_cv_data(review_status, created_at);

-- For finding items by candidate
CREATE INDEX IF NOT EXISTS idx_unmatched_cv_data_candidate
    ON unmatched_cv_data(candidate_id);

-- For finding items by suggested section
CREATE INDEX IF NOT EXISTS idx_unmatched_cv_data_section
    ON unmatched_cv_data(suggested_section);

-- For searching field names
CREATE INDEX IF NOT EXISTS idx_unmatched_cv_data_field_name
    ON unmatched_cv_data(field_name);

-- For full-text search on values (using trigram)
CREATE INDEX IF NOT EXISTS idx_unmatched_cv_data_value_trgm
    ON unmatched_cv_data USING gin (field_value_normalized gin_trgm_ops);

-- =============================================================================
-- TRIGGER: Auto-update updated_at
-- =============================================================================

-- Drop trigger if exists (for idempotency)
DROP TRIGGER IF EXISTS trg_unmatched_cv_data_updated_at ON unmatched_cv_data;

CREATE TRIGGER trg_unmatched_cv_data_updated_at
    BEFORE UPDATE ON unmatched_cv_data
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- TRIGGER: Auto-normalize field_value
-- =============================================================================

CREATE OR REPLACE FUNCTION normalize_unmatched_field_value()
RETURNS TRIGGER AS $$
BEGIN
    NEW.field_value_normalized := LOWER(TRIM(NEW.field_value));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_unmatched_cv_data_normalize ON unmatched_cv_data;

CREATE TRIGGER trg_unmatched_cv_data_normalize
    BEFORE INSERT OR UPDATE ON unmatched_cv_data
    FOR EACH ROW
    EXECUTE FUNCTION normalize_unmatched_field_value();

-- =============================================================================
-- VIEW: Pending review items grouped by section
-- =============================================================================

CREATE OR REPLACE VIEW v_unmatched_cv_data_summary AS
SELECT
    suggested_section,
    field_name,
    COUNT(*) as occurrence_count,
    COUNT(DISTINCT candidate_id) as candidate_count,
    AVG(extraction_confidence) as avg_confidence,
    MIN(created_at) as first_seen,
    MAX(created_at) as last_seen
FROM unmatched_cv_data
WHERE review_status = 'pending'
GROUP BY suggested_section, field_name
ORDER BY occurrence_count DESC;

-- =============================================================================
-- VIEW: Unmatched data with candidate info
-- =============================================================================

CREATE OR REPLACE VIEW v_unmatched_cv_data_detail AS
SELECT
    u.id,
    u.candidate_id,
    c.first_name,
    c.last_name,
    u.suggested_section,
    u.field_name,
    u.field_value,
    u.extraction_confidence,
    u.llm_reasoning,
    u.review_status,
    u.created_at
FROM unmatched_cv_data u
JOIN candidates c ON u.candidate_id = c.id
ORDER BY u.created_at DESC;

-- =============================================================================
-- ALTER: Add raw_cv_json to candidates table
-- =============================================================================

ALTER TABLE candidates
ADD COLUMN IF NOT EXISTS raw_cv_json JSONB;

-- Index for JSON queries (if needed later)
CREATE INDEX IF NOT EXISTS idx_candidates_raw_cv_json
    ON candidates USING gin (raw_cv_json);

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE unmatched_cv_data IS
    'Captures CV data that could not be mapped to existing tables. Zero data loss policy.';

COMMENT ON COLUMN unmatched_cv_data.suggested_section IS
    'LLM best guess for which section this belongs to: personal, skill, certification, etc.';

COMMENT ON COLUMN unmatched_cv_data.field_name IS
    'The field name as interpreted by LLM (e.g., father_name, blood_type)';

COMMENT ON COLUMN unmatched_cv_data.field_value IS
    'The actual value extracted from the CV';

COMMENT ON COLUMN unmatched_cv_data.llm_reasoning IS
    'LLM explanation of why it could not map this to existing structure';

COMMENT ON COLUMN unmatched_cv_data.review_status IS
    'Workflow status: pending, reviewed, added_to_taxonomy, mapped, discarded';

COMMENT ON COLUMN candidates.raw_cv_json IS
    'Complete parsed CV data as JSON backup. Ensures zero data loss.';

-- =============================================================================
-- GRANT PERMISSIONS (if using separate roles)
-- =============================================================================

-- Uncomment if needed:
-- GRANT SELECT, INSERT, UPDATE ON unmatched_cv_data TO app_role;
-- GRANT SELECT ON v_unmatched_cv_data_summary TO app_role;
-- GRANT SELECT ON v_unmatched_cv_data_detail TO app_role;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

DO $$
BEGIN
    -- Verify table exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'unmatched_cv_data') THEN
        RAISE EXCEPTION 'Table unmatched_cv_data was not created';
    END IF;

    -- Verify column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'candidates' AND column_name = 'raw_cv_json'
    ) THEN
        RAISE EXCEPTION 'Column raw_cv_json was not added to candidates';
    END IF;

    RAISE NOTICE 'Migration 016_unmatched_cv_data.sql completed successfully';
END $$;
