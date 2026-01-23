-- =============================================================================
-- CV Quality Warnings Table
-- Session 46: CV Quality Check Feature
--
-- Stores quality warnings detected during CV parsing:
-- - Date range errors (auto-fixed)
-- - Contact issues (email/phone validation)
-- - Missing critical/optional fields
-- - Spelling suspects (LLM detected)
-- - OCR artifacts
-- - Taxonomy mismatches
-- =============================================================================

-- Warning severity enum
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'warning_severity') THEN
        CREATE TYPE warning_severity AS ENUM ('info', 'warning', 'error');
    END IF;
END$$;

-- Warning category enum
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'warning_category') THEN
        CREATE TYPE warning_category AS ENUM (
            'date_error',         -- Date range invalid (end < start)
            'contact_issue',      -- Email/phone validation warning
            'missing_critical',   -- Missing name, contact, etc.
            'missing_optional',   -- Missing location, DOB, etc.
            'spelling_suspect',   -- Potential spelling error (LLM detected)
            'format_issue',       -- Formatting problem
            'data_quality',       -- General data quality issue
            'taxonomy_mismatch',  -- Term not in taxonomy
            'ocr_artifact'        -- OCR error detected
        );
    END IF;
END$$;

-- Quality warnings table
CREATE TABLE IF NOT EXISTS cv_quality_warnings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    correlation_id VARCHAR(100),

    -- Warning details
    category warning_category NOT NULL,
    severity warning_severity NOT NULL DEFAULT 'warning',
    field_name VARCHAR(100),          -- Which field has the issue
    section VARCHAR(50),              -- Which CV section (experience, education, etc.)

    -- Messages (bilingual)
    message TEXT NOT NULL,            -- English message
    message_greek TEXT,               -- Greek message

    -- Values
    original_value TEXT,              -- The original problematic value
    suggested_value TEXT,             -- Suggested correction (if any)

    -- Flags
    was_auto_fixed BOOLEAN DEFAULT false,  -- Was this automatically corrected?
    llm_detected BOOLEAN DEFAULT false,    -- Was this detected by LLM?
    is_acknowledged BOOLEAN DEFAULT false, -- Has user seen/dismissed this?

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Add warning counts to candidates table
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'candidates' AND column_name = 'warnings_count'
    ) THEN
        ALTER TABLE candidates ADD COLUMN warnings_count INTEGER DEFAULT 0;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'candidates' AND column_name = 'errors_count'
    ) THEN
        ALTER TABLE candidates ADD COLUMN errors_count INTEGER DEFAULT 0;
    END IF;
END$$;

-- Function to update warning counts on candidates table
CREATE OR REPLACE FUNCTION update_candidate_warning_counts()
RETURNS TRIGGER AS $$
DECLARE
    v_candidate_id UUID;
    v_warnings INTEGER;
    v_errors INTEGER;
BEGIN
    -- Get the candidate_id from the affected row
    IF TG_OP = 'DELETE' THEN
        v_candidate_id := OLD.candidate_id;
    ELSE
        v_candidate_id := NEW.candidate_id;
    END IF;

    -- Count warnings and errors for this candidate
    SELECT
        COUNT(*) FILTER (WHERE severity IN ('info', 'warning')),
        COUNT(*) FILTER (WHERE severity = 'error')
    INTO v_warnings, v_errors
    FROM cv_quality_warnings
    WHERE candidate_id = v_candidate_id;

    -- Update candidates table
    UPDATE candidates
    SET
        warnings_count = v_warnings,
        errors_count = v_errors
    WHERE id = v_candidate_id;

    RETURN NULL; -- For AFTER trigger
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic count updates
DROP TRIGGER IF EXISTS trg_update_warning_counts ON cv_quality_warnings;
CREATE TRIGGER trg_update_warning_counts
AFTER INSERT OR DELETE OR UPDATE OF severity ON cv_quality_warnings
FOR EACH ROW
EXECUTE FUNCTION update_candidate_warning_counts();

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_cv_quality_warnings_candidate
    ON cv_quality_warnings(candidate_id);

CREATE INDEX IF NOT EXISTS idx_cv_quality_warnings_correlation
    ON cv_quality_warnings(correlation_id);

CREATE INDEX IF NOT EXISTS idx_cv_quality_warnings_category
    ON cv_quality_warnings(category);

CREATE INDEX IF NOT EXISTS idx_cv_quality_warnings_severity
    ON cv_quality_warnings(severity);

CREATE INDEX IF NOT EXISTS idx_cv_quality_warnings_unacknowledged
    ON cv_quality_warnings(candidate_id)
    WHERE is_acknowledged = false;

-- View for candidate warnings summary
CREATE OR REPLACE VIEW v_candidate_warnings_summary AS
SELECT
    candidate_id,
    COUNT(*) AS total_warnings,
    COUNT(*) FILTER (WHERE severity = 'error') AS error_count,
    COUNT(*) FILTER (WHERE severity = 'warning') AS warning_count,
    COUNT(*) FILTER (WHERE severity = 'info') AS info_count,
    COUNT(*) FILTER (WHERE was_auto_fixed) AS auto_fixed_count,
    COUNT(*) FILTER (WHERE llm_detected) AS llm_detected_count,
    COUNT(*) FILTER (WHERE NOT is_acknowledged) AS unacknowledged_count,
    array_agg(DISTINCT category) AS categories
FROM cv_quality_warnings
GROUP BY candidate_id;

-- Comments
COMMENT ON TABLE cv_quality_warnings IS 'Stores quality warnings detected during CV parsing';
COMMENT ON COLUMN cv_quality_warnings.was_auto_fixed IS 'True if issue was automatically corrected during parsing';
COMMENT ON COLUMN cv_quality_warnings.llm_detected IS 'True if issue was detected by LLM (spelling, OCR artifacts)';
COMMENT ON COLUMN cv_quality_warnings.is_acknowledged IS 'True if user has dismissed/acknowledged this warning';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON cv_quality_warnings TO PUBLIC;
GRANT SELECT ON v_candidate_warnings_summary TO PUBLIC;

-- Log migration
DO $$
BEGIN
    RAISE NOTICE 'Migration 023_cv_quality_warnings.sql completed successfully';
END$$;
