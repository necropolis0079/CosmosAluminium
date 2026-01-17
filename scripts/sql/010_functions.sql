-- =============================================================================
-- LCMGoCloud-CAGenAI - Functions
-- =============================================================================
-- Greek text normalization, experience calculation, quality scoring, etc.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Greek Text Normalization
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION normalize_greek_text(input_text TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN unaccent(lower(input_text));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Normalize name function
CREATE OR REPLACE FUNCTION normalize_name(input_name TEXT)
RETURNS TEXT AS $$
BEGIN
    IF input_name IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN regexp_replace(
        unaccent(lower(trim(input_name))),
        '[^a-zα-ωά-ώ0-9 ]',
        '',
        'gi'
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- -----------------------------------------------------------------------------
-- Calculate Total Experience
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION calculate_total_experience(p_candidate_id UUID)
RETURNS INTEGER AS $$
DECLARE
    total_months INTEGER;
BEGIN
    SELECT COALESCE(SUM(duration_months), 0)
    INTO total_months
    FROM candidate_experience
    WHERE candidate_id = p_candidate_id;

    RETURN total_months;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- Quality Score Calculation
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION calculate_cv_quality_score(p_candidate_id UUID)
RETURNS NUMERIC AS $$
DECLARE
    score NUMERIC := 0;
    has_email BOOLEAN;
    has_phone BOOLEAN;
    education_count INTEGER;
    experience_count INTEGER;
    skills_count INTEGER;
BEGIN
    -- Get candidate data
    SELECT
        email IS NOT NULL,
        phone IS NOT NULL
    INTO has_email, has_phone
    FROM candidates
    WHERE id = p_candidate_id;

    -- Count related records
    SELECT COUNT(*) INTO education_count
    FROM candidate_education WHERE candidate_id = p_candidate_id;

    SELECT COUNT(*) INTO experience_count
    FROM candidate_experience WHERE candidate_id = p_candidate_id;

    SELECT COUNT(*) INTO skills_count
    FROM candidate_skills WHERE candidate_id = p_candidate_id;

    -- Calculate score (0-1)
    IF has_email THEN score := score + 0.15; END IF;
    IF has_phone THEN score := score + 0.10; END IF;
    IF education_count > 0 THEN score := score + 0.20; END IF;
    IF experience_count > 0 THEN score := score + 0.30; END IF;
    IF skills_count >= 5 THEN score := score + 0.25;
    ELSIF skills_count > 0 THEN score := score + 0.15; END IF;

    RETURN LEAST(score, 1.0);
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- Find Similar Candidates (Duplicate Detection)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION find_similar_candidates(
    p_email VARCHAR,
    p_phone VARCHAR,
    p_first_name VARCHAR,
    p_last_name VARCHAR,
    p_threshold NUMERIC DEFAULT 0.8
)
RETURNS TABLE (
    candidate_id UUID,
    similarity_score NUMERIC,
    match_type VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        CASE
            WHEN c.email = p_email THEN 1.0
            WHEN c.phone = p_phone THEN 0.95
            ELSE similarity(
                c.full_name_search,
                normalize_name(p_first_name || ' ' || p_last_name)
            )::NUMERIC
        END AS sim_score,
        CASE
            WHEN c.email = p_email THEN 'email'::VARCHAR
            WHEN c.phone = p_phone THEN 'phone'::VARCHAR
            ELSE 'name'::VARCHAR
        END AS match_type
    FROM candidates c
    WHERE
        (p_email IS NOT NULL AND c.email = p_email)
        OR (p_phone IS NOT NULL AND c.phone = p_phone)
        OR similarity(
            c.full_name_search,
            normalize_name(p_first_name || ' ' || p_last_name)
        ) >= p_threshold
    ORDER BY sim_score DESC;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- Update Updated At (Trigger Function)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- Normalize Candidate Names (Trigger Function)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION normalize_candidate_names()
RETURNS TRIGGER AS $$
BEGIN
    NEW.first_name_normalized = normalize_name(NEW.first_name);
    NEW.last_name_normalized = normalize_name(NEW.last_name);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- Normalize Job Title (Trigger Function)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION normalize_job_title()
RETURNS TRIGGER AS $$
BEGIN
    NEW.title_normalized = normalize_greek_text(NEW.title);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- Normalize Institution Names (Trigger Function)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION normalize_education_names()
RETURNS TRIGGER AS $$
BEGIN
    NEW.institution_name_normalized = normalize_greek_text(NEW.institution_name);
    IF NEW.degree_title IS NOT NULL THEN
        NEW.degree_title_normalized = normalize_greek_text(NEW.degree_title);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- Normalize Experience Names (Trigger Function)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION normalize_experience_names()
RETURNS TRIGGER AS $$
BEGIN
    NEW.company_name_normalized = normalize_greek_text(NEW.company_name);
    NEW.job_title_normalized = normalize_greek_text(NEW.job_title);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- Normalize Certification Names (Trigger Function)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION normalize_certification_names()
RETURNS TRIGGER AS $$
BEGIN
    NEW.certification_name_normalized = normalize_greek_text(NEW.certification_name);
    IF NEW.issuing_organization IS NOT NULL THEN
        NEW.issuing_organization_normalized = normalize_greek_text(NEW.issuing_organization);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- Set GDPR Deadline (Trigger Function)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_gdpr_deadline()
RETURNS TRIGGER AS $$
BEGIN
    -- GDPR requires response within 30 days
    IF NEW.deadline_at IS NULL THEN
        NEW.deadline_at = NEW.submitted_at + INTERVAL '30 days';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- Update Skill Taxonomy Search Vector (Trigger Function)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_skill_taxonomy_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('simple', NEW.name_en), 'A') ||
        setweight(to_tsvector('simple', COALESCE(NEW.name_el, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(array_to_string(NEW.aliases_en, ' '), '')), 'B') ||
        setweight(to_tsvector('simple', COALESCE(array_to_string(NEW.aliases_el, ' '), '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
