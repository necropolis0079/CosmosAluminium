-- =============================================================================
-- Migration: 018_candidate_training.sql
-- Purpose: Add training/seminars section for Greek CVs (Σεμινάρια)
-- Date: 2026-01-19
-- Version: 1.0
-- =============================================================================

-- =============================================================================
-- TABLE: candidate_training
-- Purpose: Store training, seminars, workshops, CPE (Continuing Professional Education)
-- Distinct from certifications which are formal qualifications
-- =============================================================================

CREATE TABLE IF NOT EXISTS candidate_training (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign Key to candidate
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,

    -- Training details
    training_name VARCHAR(500) NOT NULL,           -- Name of training/seminar
    training_name_normalized VARCHAR(500),         -- Normalized for search

    -- Provider/Organization
    provider_name VARCHAR(255),                    -- Organization that provided the training
    provider_type VARCHAR(50),                     -- 'university', 'professional_body', 'company', 'online', 'government', 'other'

    -- Classification
    training_type VARCHAR(50) DEFAULT 'seminar',   -- 'seminar', 'workshop', 'course', 'webinar', 'conference', 'cpe', 'other'
    category VARCHAR(100),                         -- 'accounting', 'legal', 'hr', 'it', 'management', 'safety', 'technical', 'other'

    -- Duration
    duration_hours INTEGER,                        -- Duration in hours (if known)
    duration_days INTEGER,                         -- Duration in days (if known)

    -- Dates
    completion_date DATE,                          -- When completed
    start_date DATE,                               -- Start date (for longer courses)

    -- Additional info
    description TEXT,                              -- Description or topics covered
    skills_gained TEXT[],                          -- Skills learned (array)
    certificate_received BOOLEAN DEFAULT false,   -- Did they receive a certificate of attendance?

    -- Source tracking
    raw_text TEXT,                                 -- Original text from CV
    confidence DECIMAL(3,2) DEFAULT 0.0,          -- Extraction confidence 0.00-1.00

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- For finding training by candidate
CREATE INDEX IF NOT EXISTS idx_candidate_training_candidate
    ON candidate_training(candidate_id);

-- For searching by training name
CREATE INDEX IF NOT EXISTS idx_candidate_training_name_trgm
    ON candidate_training USING gin (training_name_normalized gin_trgm_ops);

-- For filtering by type
CREATE INDEX IF NOT EXISTS idx_candidate_training_type
    ON candidate_training(training_type);

-- For filtering by category
CREATE INDEX IF NOT EXISTS idx_candidate_training_category
    ON candidate_training(category);

-- For date-based queries
CREATE INDEX IF NOT EXISTS idx_candidate_training_completion
    ON candidate_training(completion_date DESC);

-- =============================================================================
-- TRIGGER: Auto-update updated_at
-- =============================================================================

DROP TRIGGER IF EXISTS trg_candidate_training_updated_at ON candidate_training;

CREATE TRIGGER trg_candidate_training_updated_at
    BEFORE UPDATE ON candidate_training
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- TRIGGER: Auto-normalize training_name
-- =============================================================================

CREATE OR REPLACE FUNCTION normalize_training_name()
RETURNS TRIGGER AS $$
BEGIN
    NEW.training_name_normalized := LOWER(TRIM(
        regexp_replace(
            unaccent(NEW.training_name),
            '[^a-zA-Z0-9\s]', '', 'g'
        )
    ));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_candidate_training_normalize ON candidate_training;

CREATE TRIGGER trg_candidate_training_normalize
    BEFORE INSERT OR UPDATE ON candidate_training
    FOR EACH ROW
    EXECUTE FUNCTION normalize_training_name();

-- =============================================================================
-- VIEW: Training summary by candidate
-- =============================================================================

CREATE OR REPLACE VIEW v_candidate_training_summary AS
SELECT
    c.id as candidate_id,
    c.first_name,
    c.last_name,
    COUNT(t.id) as total_training,
    COUNT(CASE WHEN t.training_type = 'seminar' THEN 1 END) as seminars,
    COUNT(CASE WHEN t.training_type = 'course' THEN 1 END) as courses,
    COUNT(CASE WHEN t.training_type = 'workshop' THEN 1 END) as workshops,
    COUNT(CASE WHEN t.certificate_received THEN 1 END) as with_certificate,
    SUM(COALESCE(t.duration_hours, 0)) as total_hours,
    array_agg(DISTINCT t.category) FILTER (WHERE t.category IS NOT NULL) as categories
FROM candidates c
LEFT JOIN candidate_training t ON c.id = t.candidate_id
GROUP BY c.id, c.first_name, c.last_name;

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE candidate_training IS
    'Training, seminars, workshops, and CPE (Continuing Professional Education) - distinct from formal certifications';

COMMENT ON COLUMN candidate_training.training_type IS
    'Type: seminar, workshop, course, webinar, conference, cpe, other';

COMMENT ON COLUMN candidate_training.category IS
    'Category: accounting, legal, hr, it, management, safety, technical, other';

COMMENT ON COLUMN candidate_training.certificate_received IS
    'Whether a certificate of attendance/completion was received (not a formal certification)';

-- =============================================================================
-- VERIFICATION
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'candidate_training') THEN
        RAISE EXCEPTION 'Table candidate_training was not created';
    END IF;

    RAISE NOTICE 'Migration 018_candidate_training.sql completed successfully';
END $$;
