-- =============================================================================
-- LCMGoCloud-CAGenAI - Triggers
-- =============================================================================
-- Auto-update timestamps, name normalization, etc.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Updated At Triggers
-- -----------------------------------------------------------------------------

CREATE TRIGGER tr_candidates_updated_at
    BEFORE UPDATE ON candidates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_skill_taxonomy_updated_at
    BEFORE UPDATE ON skill_taxonomy
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_soft_skill_taxonomy_updated_at
    BEFORE UPDATE ON soft_skill_taxonomy
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_role_taxonomy_updated_at
    BEFORE UPDATE ON role_taxonomy
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_certification_taxonomy_updated_at
    BEFORE UPDATE ON certification_taxonomy
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_software_taxonomy_updated_at
    BEFORE UPDATE ON software_taxonomy
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_candidate_education_updated_at
    BEFORE UPDATE ON candidate_education
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_candidate_experience_updated_at
    BEFORE UPDATE ON candidate_experience
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_candidate_skills_updated_at
    BEFORE UPDATE ON candidate_skills
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_candidate_languages_updated_at
    BEFORE UPDATE ON candidate_languages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_candidate_certifications_updated_at
    BEFORE UPDATE ON candidate_certifications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_job_matches_updated_at
    BEFORE UPDATE ON job_matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_saved_searches_updated_at
    BEFORE UPDATE ON saved_searches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_search_alerts_updated_at
    BEFORE UPDATE ON search_alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_system_config_updated_at
    BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_processing_jobs_updated_at
    BEFORE UPDATE ON processing_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_consent_records_updated_at
    BEFORE UPDATE ON consent_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_data_subject_requests_updated_at
    BEFORE UPDATE ON data_subject_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_data_retention_policies_updated_at
    BEFORE UPDATE ON data_retention_policies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- -----------------------------------------------------------------------------
-- Name Normalization Triggers
-- -----------------------------------------------------------------------------

CREATE TRIGGER tr_candidates_normalize_names
    BEFORE INSERT OR UPDATE OF first_name, last_name ON candidates
    FOR EACH ROW EXECUTE FUNCTION normalize_candidate_names();

CREATE TRIGGER tr_jobs_normalize_title
    BEFORE INSERT OR UPDATE OF title ON jobs
    FOR EACH ROW EXECUTE FUNCTION normalize_job_title();

CREATE TRIGGER tr_education_normalize_names
    BEFORE INSERT OR UPDATE OF institution_name, degree_title ON candidate_education
    FOR EACH ROW EXECUTE FUNCTION normalize_education_names();

CREATE TRIGGER tr_experience_normalize_names
    BEFORE INSERT OR UPDATE OF company_name, job_title ON candidate_experience
    FOR EACH ROW EXECUTE FUNCTION normalize_experience_names();

CREATE TRIGGER tr_certifications_normalize_names
    BEFORE INSERT OR UPDATE OF certification_name, issuing_organization ON candidate_certifications
    FOR EACH ROW EXECUTE FUNCTION normalize_certification_names();

-- -----------------------------------------------------------------------------
-- GDPR Triggers
-- -----------------------------------------------------------------------------

CREATE TRIGGER tr_dsr_set_deadline
    BEFORE INSERT ON data_subject_requests
    FOR EACH ROW EXECUTE FUNCTION set_gdpr_deadline();

-- -----------------------------------------------------------------------------
-- Search Vector Triggers
-- -----------------------------------------------------------------------------

CREATE TRIGGER tr_skill_taxonomy_search_vector
    BEFORE INSERT OR UPDATE OF name_en, name_el, aliases_en, aliases_el ON skill_taxonomy
    FOR EACH ROW EXECUTE FUNCTION update_skill_taxonomy_search_vector();
