-- Migration: 022_fix_match_method_constraint.sql
-- Date: 2026-01-23
-- Description: Fix CHECK constraint on unmatched_taxonomy_items to include 'fuzzy_suggested'
-- Issue: ISSUE-011 - CV uploads failing with 25P02 error due to missing match_method value

-- The taxonomy_mapper.py produces 'fuzzy_suggested' when a fuzzy match is found
-- but confidence is below threshold. This value was missing from the CHECK constraint.

-- Drop the old constraint
ALTER TABLE unmatched_taxonomy_items DROP CONSTRAINT IF EXISTS valid_match_method;

-- Add the fixed constraint with 'fuzzy_suggested' included
ALTER TABLE unmatched_taxonomy_items ADD CONSTRAINT valid_match_method
  CHECK (match_method IN ('exact', 'substring', 'semantic', 'fuzzy', 'fuzzy_suggested', 'none', 'suggested'));

-- Verify the constraint
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname = 'valid_match_method';
