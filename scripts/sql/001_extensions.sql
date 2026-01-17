-- =============================================================================
-- LCMGoCloud-CAGenAI - PostgreSQL Extensions Setup
-- =============================================================================
-- Run as superuser (cagenai_admin)
-- Database: cagenai
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";       -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pg_trgm";         -- Trigram similarity search (Greek names)
CREATE EXTENSION IF NOT EXISTS "unaccent";        -- Accent-insensitive search (Greek)
CREATE EXTENSION IF NOT EXISTS "btree_gin";       -- GIN index support for scalars

-- Note: pg_stat_statements is already enabled via RDS parameter group

-- Verify extensions
SELECT extname, extversion FROM pg_extension ORDER BY extname;
