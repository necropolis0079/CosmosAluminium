-- =============================================================================
-- LCMGoCloud-CAGenAI - Views
-- =============================================================================
-- Summary views for candidates, jobs, skills, consent, and dashboard
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Candidate Summary View
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_candidate_summary AS
SELECT
    c.id,
    c.first_name,
    c.last_name,
    c.full_name_search,
    c.email,
    c.phone,
    c.address_city,
    c.address_region,
    c.employment_status,
    c.availability_status,
    c.processing_status,
    c.quality_score,
    c.quality_level,
    c.cv_source,
    c.created_at,
    c.updated_at,

    -- Education
    (SELECT MAX(degree_level) FROM candidate_education WHERE candidate_id = c.id) AS highest_education,
    (SELECT COUNT(*) FROM candidate_education WHERE candidate_id = c.id) AS education_count,

    -- Experience
    calculate_total_experience(c.id) AS total_experience_months,
    (SELECT COUNT(*) FROM candidate_experience WHERE candidate_id = c.id) AS experience_count,
    (SELECT company_name FROM candidate_experience
     WHERE candidate_id = c.id AND is_current = true LIMIT 1) AS current_company,
    (SELECT job_title FROM candidate_experience
     WHERE candidate_id = c.id AND is_current = true LIMIT 1) AS current_title,

    -- Skills
    (SELECT COUNT(*) FROM candidate_skills WHERE candidate_id = c.id) AS skills_count,
    (SELECT array_agg(st.name_en ORDER BY cs.years_of_experience DESC NULLS LAST)
     FROM candidate_skills cs
     JOIN skill_taxonomy st ON cs.skill_id = st.id
     WHERE cs.candidate_id = c.id LIMIT 10) AS top_skills,

    -- Languages
    (SELECT array_agg(language_code) FROM candidate_languages
     WHERE candidate_id = c.id) AS languages,

    -- Certifications
    (SELECT COUNT(*) FROM candidate_certifications WHERE candidate_id = c.id) AS certifications_count

FROM candidates c
WHERE c.is_active = true;

-- -----------------------------------------------------------------------------
-- Job Summary View
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_job_summary AS
SELECT
    j.id,
    j.external_id,
    j.title,
    j.title_normalized,
    j.department,
    j.location_city,
    j.location_region,
    j.status,
    j.priority,
    j.employment_type,
    j.experience_level,
    j.salary_min,
    j.salary_max,
    j.salary_currency,
    j.positions_count,
    j.positions_filled,
    j.posted_at,
    j.closes_at,
    j.created_at,

    -- Skills count
    (SELECT COUNT(*) FROM job_skills WHERE job_id = j.id) AS required_skills_count,
    (SELECT COUNT(*) FROM job_skills WHERE job_id = j.id AND is_required = true) AS mandatory_skills_count,

    -- Match stats
    (SELECT COUNT(*) FROM job_matches WHERE job_id = j.id) AS total_matches,
    (SELECT COUNT(*) FROM job_matches WHERE job_id = j.id AND match_status = 'shortlisted') AS shortlisted_count,
    (SELECT AVG(overall_score) FROM job_matches WHERE job_id = j.id) AS avg_match_score

FROM jobs j;

-- -----------------------------------------------------------------------------
-- Skills Report View
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_skills_report AS
SELECT
    st.id,
    st.canonical_id,
    st.name_en,
    st.name_el,
    st.category,
    st.subcategory,
    st.domain,

    -- Candidate statistics
    COUNT(DISTINCT cs.candidate_id) AS candidate_count,
    ROUND(AVG(cs.years_of_experience)::NUMERIC, 1) AS avg_experience_years,

    -- Level distribution
    COUNT(*) FILTER (WHERE cs.skill_level = 'beginner') AS beginners,
    COUNT(*) FILTER (WHERE cs.skill_level = 'intermediate') AS intermediate,
    COUNT(*) FILTER (WHERE cs.skill_level = 'advanced') AS advanced,
    COUNT(*) FILTER (WHERE cs.skill_level = 'expert') AS experts,
    COUNT(*) FILTER (WHERE cs.skill_level = 'master') AS masters,

    -- Job demand
    (SELECT COUNT(DISTINCT job_id) FROM job_skills WHERE skill_id = st.id) AS jobs_requiring

FROM skill_taxonomy st
LEFT JOIN candidate_skills cs ON st.id = cs.skill_id
WHERE st.is_active = true
GROUP BY st.id, st.canonical_id, st.name_en, st.name_el, st.category, st.subcategory, st.domain;

-- -----------------------------------------------------------------------------
-- Consent Status View
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_consent_status AS
SELECT
    c.id AS candidate_id,
    c.email,
    c.first_name,
    c.last_name,
    c.created_at AS candidate_created_at,

    -- Consent status by type
    MAX(CASE WHEN cr.consent_type = 'data_processing' AND cr.status = 'granted' THEN 'granted' END) AS data_processing_consent,
    MAX(CASE WHEN cr.consent_type = 'cv_storage' AND cr.status = 'granted' THEN 'granted' END) AS cv_storage_consent,
    MAX(CASE WHEN cr.consent_type = 'email_communication' AND cr.status = 'granted' THEN 'granted' END) AS email_consent,
    MAX(CASE WHEN cr.consent_type = 'job_alerts' AND cr.status = 'granted' THEN 'granted' END) AS job_alerts_consent,

    -- Expiry dates
    MIN(CASE WHEN cr.status = 'granted' THEN cr.expires_at END) AS earliest_expiry,

    -- Overall status
    CASE
        WHEN EXISTS (SELECT 1 FROM consent_records
                    WHERE candidate_id = c.id
                    AND consent_type = 'data_processing'
                    AND status = 'granted'
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)) THEN 'compliant'
        ELSE 'non_compliant'
    END AS gdpr_status

FROM candidates c
LEFT JOIN consent_records cr ON c.id = cr.candidate_id
GROUP BY c.id, c.email, c.first_name, c.last_name, c.created_at;

-- -----------------------------------------------------------------------------
-- Dashboard Metrics View
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_dashboard_metrics AS
SELECT
    -- Candidates
    (SELECT COUNT(*) FROM candidates WHERE is_active = true) AS total_candidates,
    (SELECT COUNT(*) FROM candidates
     WHERE is_active = true AND created_at >= CURRENT_DATE - INTERVAL '30 days') AS new_candidates_30d,
    (SELECT COUNT(*) FROM candidates WHERE processing_status = 'pending') AS pending_processing,
    (SELECT COUNT(*) FROM candidates WHERE processing_status = 'failed') AS failed_processing,

    -- Jobs
    (SELECT COUNT(*) FROM jobs WHERE status = 'open') AS open_jobs,
    (SELECT COALESCE(SUM(positions_count - positions_filled), 0) FROM jobs WHERE status = 'open') AS open_positions,
    (SELECT COUNT(*) FROM jobs
     WHERE status = 'open' AND closes_at < CURRENT_DATE + INTERVAL '7 days') AS closing_soon_jobs,

    -- Matches
    (SELECT COUNT(*) FROM job_matches
     WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') AS matches_7d,
    (SELECT ROUND(AVG(overall_score)::NUMERIC, 4) FROM job_matches
     WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') AS avg_match_score_7d,

    -- Processing
    (SELECT ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))::NUMERIC, 2)
     FROM processing_jobs
     WHERE job_type = 'cv_processing'
     AND completed_at >= CURRENT_DATE - INTERVAL '7 days') AS avg_processing_time_sec,

    -- GDPR
    (SELECT COUNT(*) FROM data_subject_requests
     WHERE status IN ('pending', 'processing')) AS pending_dsr_requests,
    (SELECT COUNT(*) FROM consent_records
     WHERE status = 'granted'
     AND expires_at BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days') AS expiring_consents_30d,

    -- Timestamp
    CURRENT_TIMESTAMP AS generated_at;

-- -----------------------------------------------------------------------------
-- Match Details View
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_match_details AS
SELECT
    jm.id AS match_id,
    jm.job_id,
    jm.candidate_id,
    jm.overall_score,
    jm.skills_score,
    jm.experience_score,
    jm.education_score,
    jm.match_status,
    jm.match_source,
    jm.gap_severity,
    jm.rank_position,
    jm.created_at AS match_created_at,

    -- Job info
    j.title AS job_title,
    j.department AS job_department,
    j.location_city AS job_location,
    j.employment_type AS job_employment_type,

    -- Candidate info
    c.first_name,
    c.last_name,
    c.email AS candidate_email,
    c.address_city AS candidate_location,
    c.quality_score AS candidate_quality_score

FROM job_matches jm
JOIN jobs j ON jm.job_id = j.id
JOIN candidates c ON jm.candidate_id = c.id;
