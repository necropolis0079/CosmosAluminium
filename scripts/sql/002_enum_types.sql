-- =============================================================================
-- LCMGoCloud-CAGenAI - Enum Types
-- =============================================================================
-- All enum types used across the database schema
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Candidate Enums
-- -----------------------------------------------------------------------------

-- Employment status
CREATE TYPE employment_status AS ENUM (
    'employed',
    'unemployed',
    'self_employed',
    'student',
    'retired',
    'unknown'
);

-- Availability status
CREATE TYPE availability_status AS ENUM (
    'immediate',
    'one_week',
    'two_weeks',
    'one_month',
    'three_months',
    'not_available',
    'unknown'
);

-- Gender
CREATE TYPE gender_type AS ENUM (
    'male',
    'female',
    'other',
    'prefer_not_to_say',
    'unknown'
);

-- Marital status
CREATE TYPE marital_status AS ENUM (
    'single',
    'married',
    'divorced',
    'widowed',
    'civil_partnership',
    'unknown'
);

-- Military status (Greece-specific)
CREATE TYPE military_status AS ENUM (
    'completed',
    'exempt',
    'pending',
    'not_applicable',
    'unknown'
);

-- Driving license category
CREATE TYPE driving_license_category AS ENUM (
    'A', 'A1', 'A2', 'AM',
    'B', 'B1', 'BE',
    'C', 'C1', 'CE', 'C1E',
    'D', 'D1', 'DE', 'D1E',
    'forklift',
    'crane',
    'other'
);

-- CV source
CREATE TYPE cv_source AS ENUM (
    'website',
    'linkedin',
    'indeed',
    'kariera',
    'skywalker',
    'referral',
    'job_fair',
    'email',
    'walk_in',
    'agency',
    'internal',
    'other'
);

-- CV processing status
CREATE TYPE cv_processing_status AS ENUM (
    'pending',
    'processing',
    'parsed',
    'enriched',
    'indexed',
    'failed',
    'duplicate',
    'archived'
);

-- Quality score level
CREATE TYPE quality_level AS ENUM (
    'excellent',
    'good',
    'fair',
    'poor',
    'insufficient'
);

-- -----------------------------------------------------------------------------
-- Education Enums
-- -----------------------------------------------------------------------------

-- Education level
CREATE TYPE education_level AS ENUM (
    'primary',
    'secondary',
    'lyceum',
    'vocational',
    'iek',
    'tei',
    'bachelor',
    'master',
    'doctorate',
    'postdoc',
    'professional_cert',
    'other'
);

-- Education field
CREATE TYPE education_field AS ENUM (
    'engineering_mechanical',
    'engineering_electrical',
    'engineering_civil',
    'engineering_chemical',
    'engineering_industrial',
    'engineering_computer',
    'engineering_other',
    'computer_science',
    'information_technology',
    'business_administration',
    'economics',
    'finance',
    'accounting',
    'marketing',
    'human_resources',
    'law',
    'chemistry',
    'physics',
    'mathematics',
    'biology',
    'environmental_science',
    'agriculture',
    'medicine',
    'nursing',
    'psychology',
    'sociology',
    'languages',
    'arts',
    'architecture',
    'other'
);

-- -----------------------------------------------------------------------------
-- Skills Enums
-- -----------------------------------------------------------------------------

-- Skill category
CREATE TYPE skill_category AS ENUM (
    'technical',
    'soft',
    'language',
    'certification',
    'tool',
    'methodology',
    'domain',
    'other'
);

-- Skill level
CREATE TYPE skill_level AS ENUM (
    'beginner',
    'intermediate',
    'advanced',
    'expert',
    'master'
);

-- Language proficiency (CEFR)
CREATE TYPE language_proficiency AS ENUM (
    'A1', 'A2',
    'B1', 'B2',
    'C1', 'C2',
    'native',
    'unknown'
);

-- -----------------------------------------------------------------------------
-- Job Enums
-- -----------------------------------------------------------------------------

-- Job status
CREATE TYPE job_status AS ENUM (
    'draft',
    'open',
    'on_hold',
    'filled',
    'cancelled',
    'expired'
);

-- Employment type
CREATE TYPE employment_type AS ENUM (
    'full_time',
    'part_time',
    'contract',
    'temporary',
    'internship',
    'seasonal',
    'freelance'
);

-- Contract duration
CREATE TYPE contract_duration AS ENUM (
    'permanent',
    'fixed_term_3m',
    'fixed_term_6m',
    'fixed_term_12m',
    'fixed_term_other',
    'project_based'
);

-- Work arrangement
CREATE TYPE work_arrangement AS ENUM (
    'on_site',
    'remote',
    'hybrid',
    'flexible'
);

-- Shift type
CREATE TYPE shift_type AS ENUM (
    'day',
    'evening',
    'night',
    'rotating',
    'flexible',
    'split'
);

-- Experience level
CREATE TYPE experience_level AS ENUM (
    'entry',
    'junior',
    'mid',
    'senior',
    'lead',
    'manager',
    'director',
    'executive'
);

-- Priority level
CREATE TYPE priority_level AS ENUM (
    'low',
    'medium',
    'high',
    'urgent',
    'critical'
);

-- -----------------------------------------------------------------------------
-- Matching Enums
-- -----------------------------------------------------------------------------

-- Match status
CREATE TYPE match_status AS ENUM (
    'new',
    'reviewed',
    'shortlisted',
    'contacted',
    'interviewing',
    'offered',
    'hired',
    'rejected',
    'withdrawn'
);

-- Match source
CREATE TYPE match_source AS ENUM (
    'automatic',
    'manual',
    'search',
    'recommendation',
    'referral'
);

-- Gap severity
CREATE TYPE gap_severity AS ENUM (
    'none',
    'minor',
    'moderate',
    'significant',
    'critical'
);

-- Training recommendation type
CREATE TYPE training_type AS ENUM (
    'online_course',
    'certification',
    'workshop',
    'on_the_job',
    'mentoring',
    'formal_education',
    'self_study'
);

-- -----------------------------------------------------------------------------
-- GDPR Enums
-- -----------------------------------------------------------------------------

-- Consent type
CREATE TYPE consent_type AS ENUM (
    'data_processing',
    'cv_storage',
    'email_communication',
    'sms_communication',
    'job_alerts',
    'marketing',
    'third_party_sharing',
    'analytics'
);

-- Consent status
CREATE TYPE consent_status AS ENUM (
    'granted',
    'denied',
    'withdrawn',
    'expired',
    'pending'
);

-- Data request type
CREATE TYPE data_request_type AS ENUM (
    'access',
    'rectification',
    'erasure',
    'portability',
    'restriction',
    'objection'
);

-- Data request status
CREATE TYPE data_request_status AS ENUM (
    'pending',
    'processing',
    'completed',
    'rejected',
    'expired'
);

-- -----------------------------------------------------------------------------
-- System Enums
-- -----------------------------------------------------------------------------

-- Audit action
CREATE TYPE audit_action AS ENUM (
    'create',
    'read',
    'update',
    'delete',
    'export',
    'import',
    'search',
    'match',
    'login',
    'logout'
);

-- Notification type
CREATE TYPE notification_type AS ENUM (
    'new_match',
    'search_alert',
    'application_update',
    'system_alert',
    'consent_reminder',
    'data_expiry',
    'job_update'
);

-- Alert frequency
CREATE TYPE alert_frequency AS ENUM (
    'immediate',
    'daily',
    'weekly',
    'monthly',
    'disabled'
);

-- Integration type
CREATE TYPE integration_type AS ENUM (
    'hris',
    'job_board',
    'email',
    'calendar',
    'sso',
    'erp',
    'other'
);
