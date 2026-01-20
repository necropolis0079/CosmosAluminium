-- ============================================================================
-- Migration: 019_job_matching.sql
-- Description: Job matching view and function for intelligent candidate search
-- Version: 1.0
-- Date: 2026-01-20
-- ============================================================================

-- ============================================================================
-- VIEW: v_candidate_match_data
-- Aggregates all candidate data needed for matching
-- ============================================================================

CREATE OR REPLACE VIEW v_candidate_match_data AS
SELECT
    c.id,
    c.first_name,
    c.last_name,
    c.email,
    c.phone,
    c.address_city,
    c.address_region,
    c.availability_status,
    c.created_at,
    c.updated_at,

    -- Total experience in years
    COALESCE((
        SELECT SUM(duration_months) / 12.0
        FROM candidate_experience
        WHERE candidate_id = c.id
    ), 0) AS total_experience_years,

    -- Roles array (English names)
    COALESCE((
        SELECT array_agg(DISTINCT rt.name_en)
        FROM candidate_experience ce
        JOIN role_taxonomy rt ON ce.role_id = rt.id
        WHERE ce.candidate_id = c.id
    ), ARRAY[]::TEXT[]) AS roles_en,

    -- Roles array (Greek names)
    COALESCE((
        SELECT array_agg(DISTINCT rt.name_el)
        FROM candidate_experience ce
        JOIN role_taxonomy rt ON ce.role_id = rt.id
        WHERE ce.candidate_id = c.id
    ), ARRAY[]::TEXT[]) AS roles_el,

    -- Software array
    COALESCE((
        SELECT array_agg(DISTINCT st.name)
        FROM candidate_software cs
        JOIN software_taxonomy st ON cs.software_id = st.id
        WHERE cs.candidate_id = c.id
    ), ARRAY[]::TEXT[]) AS software,

    -- Languages array
    COALESCE((
        SELECT array_agg(DISTINCT language_code)
        FROM candidate_languages
        WHERE candidate_id = c.id
    ), ARRAY[]::TEXT[]) AS languages,

    -- Certifications array (English)
    COALESCE((
        SELECT array_agg(DISTINCT ct.name_en)
        FROM candidate_certifications cc
        JOIN certification_taxonomy ct ON cc.certification_id_taxonomy = ct.id
        WHERE cc.candidate_id = c.id
    ), ARRAY[]::TEXT[]) AS certifications_en,

    -- Certifications array (Greek)
    COALESCE((
        SELECT array_agg(DISTINCT ct.name_el)
        FROM candidate_certifications cc
        JOIN certification_taxonomy ct ON cc.certification_id_taxonomy = ct.id
        WHERE cc.candidate_id = c.id
    ), ARRAY[]::TEXT[]) AS certifications_el,

    -- Skills array (English)
    COALESCE((
        SELECT array_agg(DISTINCT skt.name_en)
        FROM candidate_skills csk
        JOIN skill_taxonomy skt ON csk.skill_id = skt.id
        WHERE csk.candidate_id = c.id
    ), ARRAY[]::TEXT[]) AS skills_en,

    -- Skills array (Greek)
    COALESCE((
        SELECT array_agg(DISTINCT skt.name_el)
        FROM candidate_skills csk
        JOIN skill_taxonomy skt ON csk.skill_id = skt.id
        WHERE csk.candidate_id = c.id
    ), ARRAY[]::TEXT[]) AS skills_el,

    -- Education level
    (
        SELECT MAX(
            CASE degree_level::text
                WHEN 'phd' THEN 5
                WHEN 'masters' THEN 4
                WHEN 'bachelors' THEN 3
                WHEN 'associate' THEN 2
                WHEN 'high_school' THEN 1
                ELSE 0
            END
        )
        FROM candidate_education
        WHERE candidate_id = c.id
    ) AS education_level_rank

FROM candidates c
WHERE c.is_active = true;

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_candidate_experience_duration
ON candidate_experience(candidate_id, duration_months);

-- ============================================================================
-- FUNCTION: match_candidates_relaxed
-- Finds candidates matching ANY criteria with weighted scoring
-- ============================================================================

CREATE OR REPLACE FUNCTION match_candidates_relaxed(
    p_role TEXT DEFAULT NULL,
    p_min_experience NUMERIC DEFAULT NULL,
    p_software TEXT[] DEFAULT NULL,
    p_languages TEXT[] DEFAULT NULL,
    p_certifications TEXT[] DEFAULT NULL,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    candidate_id UUID,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    address_city TEXT,
    total_experience_years NUMERIC,
    match_score NUMERIC,
    matched_criteria JSONB,
    roles TEXT[],
    software TEXT[],
    languages TEXT[],
    certifications TEXT[],
    skills TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    WITH scored_candidates AS (
        SELECT
            v.id,
            v.first_name,
            v.last_name,
            v.email,
            v.phone,
            v.address_city,
            v.total_experience_years,
            v.roles_en,
            v.roles_el,
            v.software,
            v.languages,
            v.certifications_en,
            v.certifications_el,
            v.skills_en,
            v.skills_el,
            -- Calculate match score (0-1 scale)
            (
                -- Role match (25%)
                CASE
                    WHEN p_role IS NULL THEN 0
                    WHEN EXISTS (
                        SELECT 1 FROM unnest(v.roles_en) r
                        WHERE LOWER(r) LIKE '%' || LOWER(p_role) || '%'
                    ) THEN 0.25
                    WHEN EXISTS (
                        SELECT 1 FROM unnest(v.roles_el) r
                        WHERE LOWER(r) LIKE '%' || LOWER(p_role) || '%'
                    ) THEN 0.25
                    ELSE 0
                END +
                -- Experience match (35%)
                CASE
                    WHEN p_min_experience IS NULL THEN 0
                    WHEN v.total_experience_years >= p_min_experience THEN 0.35
                    WHEN v.total_experience_years >= p_min_experience * 0.7 THEN 0.20  -- Partial credit
                    WHEN v.total_experience_years >= p_min_experience * 0.5 THEN 0.10
                    ELSE 0
                END +
                -- Software match (20%) - uses partial matching for flexibility
                -- Matches "Excel" to "Microsoft Excel", "SAP" to "SAP ERP", etc.
                CASE
                    WHEN p_software IS NULL OR array_length(p_software, 1) IS NULL THEN 0
                    WHEN EXISTS (
                        SELECT 1 FROM unnest(v.software) sw, unnest(p_software) ps
                        WHERE LOWER(sw) LIKE '%' || LOWER(ps) || '%'
                           OR LOWER(ps) LIKE '%' || LOWER(sw) || '%'
                    ) THEN 0.20
                    ELSE 0
                END +
                -- Language match (10%)
                CASE
                    WHEN p_languages IS NULL OR array_length(p_languages, 1) IS NULL THEN 0
                    WHEN v.languages::text[] && p_languages THEN 0.10
                    ELSE 0
                END +
                -- Certification match (10%)
                CASE
                    WHEN p_certifications IS NULL OR array_length(p_certifications, 1) IS NULL THEN 0
                    WHEN v.certifications_en::text[] && p_certifications THEN 0.10
                    WHEN v.certifications_el::text[] && p_certifications THEN 0.10
                    ELSE 0
                END
            )::NUMERIC AS calc_score,
            -- Track which criteria matched
            jsonb_build_object(
                'role', CASE
                    WHEN p_role IS NULL THEN NULL
                    WHEN EXISTS (SELECT 1 FROM unnest(v.roles_en) r WHERE LOWER(r) LIKE '%' || LOWER(p_role) || '%') THEN true
                    WHEN EXISTS (SELECT 1 FROM unnest(v.roles_el) r WHERE LOWER(r) LIKE '%' || LOWER(p_role) || '%') THEN true
                    ELSE false
                END,
                'experience', CASE
                    WHEN p_min_experience IS NULL THEN NULL
                    ELSE v.total_experience_years >= p_min_experience
                END,
                'experience_years', v.total_experience_years,
                'software', CASE
                    WHEN p_software IS NULL THEN NULL
                    ELSE EXISTS (
                        SELECT 1 FROM unnest(v.software) sw, unnest(p_software) ps
                        WHERE LOWER(sw) LIKE '%' || LOWER(ps) || '%'
                           OR LOWER(ps) LIKE '%' || LOWER(sw) || '%'
                    )
                END,
                'languages', CASE
                    WHEN p_languages IS NULL THEN NULL
                    ELSE v.languages::text[] && p_languages
                END,
                'certifications', CASE
                    WHEN p_certifications IS NULL THEN NULL
                    ELSE (v.certifications_en::text[] && p_certifications OR v.certifications_el::text[] && p_certifications)
                END
            ) AS criteria_matched
        FROM v_candidate_match_data v
        WHERE
            -- At least one criterion must match (relaxed)
            (p_role IS NULL OR
                EXISTS (SELECT 1 FROM unnest(v.roles_en) r WHERE LOWER(r) LIKE '%' || LOWER(p_role) || '%') OR
                EXISTS (SELECT 1 FROM unnest(v.roles_el) r WHERE LOWER(r) LIKE '%' || LOWER(p_role) || '%')
            ) OR
            (p_min_experience IS NULL OR v.total_experience_years >= p_min_experience * 0.5) OR
            (p_software IS NULL OR EXISTS (
                SELECT 1 FROM unnest(v.software) sw, unnest(p_software) ps
                WHERE LOWER(sw) LIKE '%' || LOWER(ps) || '%'
                   OR LOWER(ps) LIKE '%' || LOWER(sw) || '%'
            )) OR
            (p_languages IS NULL OR v.languages::text[] && p_languages) OR
            (p_certifications IS NULL OR v.certifications_en::text[] && p_certifications OR v.certifications_el::text[] && p_certifications)
    )
    SELECT
        sc.id,
        sc.first_name::text,
        sc.last_name::text,
        sc.email::text,
        sc.phone::text,
        sc.address_city::text,
        sc.total_experience_years,
        sc.calc_score,
        sc.criteria_matched,
        sc.roles_en::text[],
        sc.software::text[],
        sc.languages::text[],
        sc.certifications_en::text[],
        sc.skills_en::text[]
    FROM scored_candidates sc
    WHERE sc.calc_score > 0  -- Only return candidates with at least some match
    ORDER BY sc.calc_score DESC, sc.total_experience_years DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: get_candidate_full_profile
-- Returns complete candidate data for LLM analysis
-- ============================================================================

CREATE OR REPLACE FUNCTION get_candidate_full_profile(p_candidate_id UUID)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'id', c.id,
        'name', c.first_name || ' ' || c.last_name,
        'email', c.email,
        'phone', c.phone,
        'city', c.address_city,
        'region', c.address_region,
        'experience', (
            SELECT jsonb_agg(jsonb_build_object(
                'company', ce.company_name,
                'role', rt.name_el,
                'role_en', rt.name_en,
                'duration_months', ce.duration_months,
                'start_date', ce.start_date,
                'end_date', ce.end_date,
                'description', ce.description
            ) ORDER BY ce.start_date DESC)
            FROM candidate_experience ce
            LEFT JOIN role_taxonomy rt ON ce.role_id = rt.id
            WHERE ce.candidate_id = c.id
        ),
        'education', (
            SELECT jsonb_agg(jsonb_build_object(
                'institution', ced.institution_name,
                'degree', ced.degree_title,
                'field', ced.field_of_study,
                'level', ced.degree_level,
                'graduation_year', ced.graduation_year
            ) ORDER BY ced.graduation_year DESC NULLS LAST)
            FROM candidate_education ced
            WHERE ced.candidate_id = c.id
        ),
        'skills', (
            SELECT jsonb_agg(jsonb_build_object(
                'name', st.name_el,
                'name_en', st.name_en,
                'level', cs.skill_level
            ))
            FROM candidate_skills cs
            JOIN skill_taxonomy st ON cs.skill_id = st.id
            WHERE cs.candidate_id = c.id
        ),
        'software', (
            SELECT jsonb_agg(jsonb_build_object(
                'name', swt.name,
                'level', csw.proficiency_level
            ))
            FROM candidate_software csw
            JOIN software_taxonomy swt ON csw.software_id = swt.id
            WHERE csw.candidate_id = c.id
        ),
        'languages', (
            SELECT jsonb_agg(jsonb_build_object(
                'code', cl.language_code,
                'level', cl.proficiency_level
            ))
            FROM candidate_languages cl
            WHERE cl.candidate_id = c.id
        ),
        'certifications', (
            SELECT jsonb_agg(jsonb_build_object(
                'name', ct.name_el,
                'name_en', ct.name_en,
                'issuer', cc.issuing_organization,
                'date', cc.issue_date
            ))
            FROM candidate_certifications cc
            JOIN certification_taxonomy ct ON cc.certification_id_taxonomy = ct.id
            WHERE cc.candidate_id = c.id
        ),
        'total_experience_years', (
            SELECT COALESCE(SUM(duration_months) / 12.0, 0)
            FROM candidate_experience
            WHERE candidate_id = c.id
        )
    ) INTO result
    FROM candidates c
    WHERE c.id = p_candidate_id;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT ON v_candidate_match_data TO PUBLIC;
GRANT EXECUTE ON FUNCTION match_candidates_relaxed TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_candidate_full_profile TO PUBLIC;

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Migration 019_job_matching.sql completed successfully';
    RAISE NOTICE 'Created view: v_candidate_match_data';
    RAISE NOTICE 'Created function: match_candidates_relaxed';
    RAISE NOTICE 'Created function: get_candidate_full_profile';
END $$;
