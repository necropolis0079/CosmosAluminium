-- =============================================================================
-- Migration 014: Unmatched Taxonomy Items Table
-- =============================================================================
-- Version: 1.0
-- Created: 2026-01-18 (Session 28)
-- Purpose: Capture CV items that couldn't be mapped to existing taxonomy
--          to prevent silent data loss and enable taxonomy expansion
-- =============================================================================

-- Enum for item types
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'unmatched_item_type') THEN
        CREATE TYPE unmatched_item_type AS ENUM (
            'skill',
            'software',
            'certification',
            'role',
            'education_field',
            'language',
            'other'
        );
    END IF;
END$$;

-- Enum for review status
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'unmatched_review_status') THEN
        CREATE TYPE unmatched_review_status AS ENUM (
            'pending',
            'mapped',
            'new_taxonomy',
            'rejected',
            'duplicate'
        );
    END IF;
END$$;

-- Main table for capturing unmatched items
CREATE TABLE IF NOT EXISTS unmatched_taxonomy_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Source reference
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    document_id UUID REFERENCES candidate_documents(id) ON DELETE SET NULL,
    correlation_id VARCHAR(100),

    -- Item details
    item_type unmatched_item_type NOT NULL,
    raw_value TEXT NOT NULL,
    normalized_value TEXT NOT NULL,
    source_context TEXT,                    -- Surrounding text from CV for context
    source_section VARCHAR(50),             -- 'skills', 'experience', 'education', etc.

    -- Semantic matching info (for suggested matches below threshold)
    suggested_taxonomy_id UUID,
    suggested_canonical_id VARCHAR(100),
    semantic_similarity DECIMAL(5,4),
    match_method VARCHAR(50) DEFAULT 'none', -- 'exact', 'substring', 'semantic', 'fuzzy', 'none'

    -- Review workflow
    review_status unmatched_review_status DEFAULT 'pending',
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,

    -- Resolution (after review)
    mapped_to_taxonomy_id UUID,
    mapped_to_canonical_id VARCHAR(100),
    created_taxonomy_entry BOOLEAN DEFAULT false,

    -- Metadata
    occurrence_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_similarity CHECK (
        semantic_similarity IS NULL OR
        (semantic_similarity >= 0 AND semantic_similarity <= 1)
    ),
    CONSTRAINT valid_match_method CHECK (
        match_method IN ('exact', 'substring', 'semantic', 'fuzzy', 'fuzzy_suggested', 'none', 'suggested')
    )
);

-- =============================================================================
-- Indexes
-- =============================================================================

-- Primary query patterns
CREATE INDEX IF NOT EXISTS idx_unmatched_type_status
    ON unmatched_taxonomy_items(item_type, review_status);

CREATE INDEX IF NOT EXISTS idx_unmatched_candidate
    ON unmatched_taxonomy_items(candidate_id);

CREATE INDEX IF NOT EXISTS idx_unmatched_correlation
    ON unmatched_taxonomy_items(correlation_id);

-- For deduplication and aggregation
CREATE INDEX IF NOT EXISTS idx_unmatched_normalized
    ON unmatched_taxonomy_items(normalized_value);

CREATE INDEX IF NOT EXISTS idx_unmatched_normalized_type
    ON unmatched_taxonomy_items(item_type, normalized_value);

-- For dashboard queries
CREATE INDEX IF NOT EXISTS idx_unmatched_created
    ON unmatched_taxonomy_items(created_at DESC);

-- Partial index for pending items (most common query)
CREATE INDEX IF NOT EXISTS idx_unmatched_pending
    ON unmatched_taxonomy_items(item_type, created_at DESC)
    WHERE review_status = 'pending';

-- =============================================================================
-- Trigger for updated_at
-- =============================================================================

-- Drop trigger if exists (for idempotency)
DROP TRIGGER IF EXISTS trg_unmatched_items_updated ON unmatched_taxonomy_items;

CREATE TRIGGER trg_unmatched_items_updated
    BEFORE UPDATE ON unmatched_taxonomy_items
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- =============================================================================
-- Unique constraint to prevent exact duplicates
-- =============================================================================

-- Composite unique constraint: same candidate, type, and normalized value
CREATE UNIQUE INDEX IF NOT EXISTS idx_unmatched_unique_per_candidate
    ON unmatched_taxonomy_items(candidate_id, item_type, normalized_value)
    WHERE review_status = 'pending';

-- =============================================================================
-- Views for admin dashboard
-- =============================================================================

-- Summary of pending unmatched items (grouped by normalized value)
CREATE OR REPLACE VIEW v_unmatched_items_summary AS
SELECT
    item_type,
    normalized_value,
    COUNT(*) as total_occurrences,
    COUNT(DISTINCT candidate_id) as unique_candidates,
    MAX(semantic_similarity) as best_similarity,
    MAX(suggested_canonical_id) as suggested_mapping,
    array_agg(DISTINCT source_section) FILTER (WHERE source_section IS NOT NULL) as source_sections,
    MIN(created_at) as first_seen,
    MAX(created_at) as last_seen
FROM unmatched_taxonomy_items
WHERE review_status = 'pending'
GROUP BY item_type, normalized_value
ORDER BY total_occurrences DESC, last_seen DESC;

-- Recent unmatched items (for monitoring)
CREATE OR REPLACE VIEW v_unmatched_recent AS
SELECT
    id,
    candidate_id,
    correlation_id,
    item_type,
    raw_value,
    normalized_value,
    semantic_similarity,
    suggested_canonical_id,
    match_method,
    created_at
FROM unmatched_taxonomy_items
WHERE review_status = 'pending'
ORDER BY created_at DESC
LIMIT 100;

-- Statistics per item type
CREATE OR REPLACE VIEW v_unmatched_stats AS
SELECT
    item_type,
    review_status,
    COUNT(*) as count,
    COUNT(DISTINCT candidate_id) as unique_candidates,
    AVG(semantic_similarity) FILTER (WHERE semantic_similarity IS NOT NULL) as avg_similarity,
    COUNT(*) FILTER (WHERE semantic_similarity >= 0.7) as near_matches,
    COUNT(*) FILTER (WHERE semantic_similarity < 0.5 OR semantic_similarity IS NULL) as no_matches
FROM unmatched_taxonomy_items
GROUP BY item_type, review_status
ORDER BY item_type, review_status;

-- =============================================================================
-- Function to increment occurrence count for existing unmatched items
-- =============================================================================

CREATE OR REPLACE FUNCTION upsert_unmatched_item(
    p_candidate_id UUID,
    p_item_type unmatched_item_type,
    p_raw_value TEXT,
    p_normalized_value TEXT,
    p_source_context TEXT DEFAULT NULL,
    p_source_section VARCHAR(50) DEFAULT NULL,
    p_suggested_taxonomy_id UUID DEFAULT NULL,
    p_suggested_canonical_id VARCHAR(100) DEFAULT NULL,
    p_semantic_similarity DECIMAL(5,4) DEFAULT NULL,
    p_match_method VARCHAR(50) DEFAULT 'none',
    p_correlation_id VARCHAR(100) DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_id UUID;
BEGIN
    -- Try to update existing pending item
    UPDATE unmatched_taxonomy_items
    SET
        occurrence_count = occurrence_count + 1,
        updated_at = CURRENT_TIMESTAMP,
        -- Update similarity if new one is better
        semantic_similarity = GREATEST(COALESCE(semantic_similarity, 0), COALESCE(p_semantic_similarity, 0)),
        suggested_canonical_id = COALESCE(p_suggested_canonical_id, suggested_canonical_id),
        suggested_taxonomy_id = COALESCE(p_suggested_taxonomy_id, suggested_taxonomy_id)
    WHERE candidate_id = p_candidate_id
      AND item_type = p_item_type
      AND normalized_value = p_normalized_value
      AND review_status = 'pending'
    RETURNING id INTO v_id;

    -- If no existing item, insert new
    IF v_id IS NULL THEN
        INSERT INTO unmatched_taxonomy_items (
            candidate_id, correlation_id, item_type,
            raw_value, normalized_value, source_context, source_section,
            suggested_taxonomy_id, suggested_canonical_id, semantic_similarity,
            match_method
        ) VALUES (
            p_candidate_id, p_correlation_id, p_item_type,
            p_raw_value, p_normalized_value, p_source_context, p_source_section,
            p_suggested_taxonomy_id, p_suggested_canonical_id, p_semantic_similarity,
            p_match_method
        )
        RETURNING id INTO v_id;
    END IF;

    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Comments
-- =============================================================================

COMMENT ON TABLE unmatched_taxonomy_items IS
    'Captures CV items that could not be mapped to existing taxonomy for manual review and taxonomy expansion. Prevents silent data loss.';

COMMENT ON COLUMN unmatched_taxonomy_items.raw_value IS
    'Original value as extracted from CV (before normalization)';

COMMENT ON COLUMN unmatched_taxonomy_items.normalized_value IS
    'Normalized value (lowercase, trimmed, Greek accent normalization)';

COMMENT ON COLUMN unmatched_taxonomy_items.semantic_similarity IS
    'Best semantic similarity score to existing taxonomy (0-1). NULL if no semantic matching attempted.';

COMMENT ON COLUMN unmatched_taxonomy_items.suggested_canonical_id IS
    'Suggested taxonomy canonical_id if semantic_similarity >= 0.6 but < threshold';

COMMENT ON FUNCTION upsert_unmatched_item IS
    'Insert or update unmatched taxonomy item. Updates occurrence_count if already exists.';

-- =============================================================================
-- Grant permissions (adjust role names as needed)
-- =============================================================================

-- Lambda execution role needs INSERT and SELECT
-- Admin users need full access for review workflow

-- Done
SELECT 'Migration 014_unmatched_items.sql completed successfully' as status;
