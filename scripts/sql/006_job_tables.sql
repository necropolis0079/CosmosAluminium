-- =============================================================================
-- LCMGoCloud-CAGenAI - Job Tables
-- =============================================================================
-- Jobs, job_skills, job_certifications, job_languages
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Jobs Table
-- -----------------------------------------------------------------------------
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(100) UNIQUE,

    -- Basic Info
    title VARCHAR(255) NOT NULL,
    title_normalized VARCHAR(255),
    role_id UUID REFERENCES role_taxonomy(id),

    -- Organization
    department VARCHAR(100),
    location_city VARCHAR(100),
    location_region VARCHAR(100),
    location_country VARCHAR(100) DEFAULT 'Greece',

    -- Status
    status job_status DEFAULT 'draft',
    priority priority_level DEFAULT 'medium',

    -- Employment Details
    employment_type employment_type NOT NULL,
    contract_duration contract_duration,
    work_arrangement work_arrangement DEFAULT 'on_site',
    shift_type shift_type,

    -- Requirements
    experience_level experience_level,
    experience_years_min INTEGER,
    experience_years_max INTEGER,
    education_level_min education_level,

    -- Compensation
    salary_min NUMERIC(10,2),
    salary_max NUMERIC(10,2),
    salary_currency VARCHAR(3) DEFAULT 'EUR',
    salary_period VARCHAR(20) DEFAULT 'monthly',
    benefits TEXT[],

    -- Description
    description TEXT,
    responsibilities TEXT[],
    requirements TEXT[],
    nice_to_have TEXT[],

    -- Dates
    posted_at TIMESTAMP WITH TIME ZONE,
    closes_at TIMESTAMP WITH TIME ZONE,
    target_start_date DATE,

    -- Metrics
    positions_count INTEGER DEFAULT 1,
    positions_filled INTEGER DEFAULT 0,
    applications_count INTEGER DEFAULT 0,
    views_count INTEGER DEFAULT 0,

    -- Ownership
    hiring_manager_id UUID,
    recruiter_id UUID,
    created_by UUID,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_job_salary_range CHECK (
        salary_max IS NULL OR salary_min IS NULL OR salary_max >= salary_min
    ),
    CONSTRAINT valid_positions CHECK (positions_filled <= positions_count)
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_title ON jobs USING gin(title_normalized gin_trgm_ops);
CREATE INDEX idx_jobs_role ON jobs(role_id);
CREATE INDEX idx_jobs_location ON jobs(location_city, location_region);
CREATE INDEX idx_jobs_employment_type ON jobs(employment_type);
CREATE INDEX idx_jobs_posted ON jobs(posted_at DESC);
CREATE INDEX idx_jobs_active ON jobs(status) WHERE status = 'open';

-- -----------------------------------------------------------------------------
-- Job Skills
-- -----------------------------------------------------------------------------
CREATE TABLE job_skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skill_taxonomy(id),

    is_required BOOLEAN DEFAULT true,
    minimum_level skill_level,
    minimum_years NUMERIC(4,1),
    weight NUMERIC(3,2) DEFAULT 1.0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_job_skill UNIQUE (job_id, skill_id)
);

CREATE INDEX idx_job_skills_job ON job_skills(job_id);
CREATE INDEX idx_job_skills_skill ON job_skills(skill_id);
CREATE INDEX idx_job_skills_required ON job_skills(job_id) WHERE is_required = true;

-- -----------------------------------------------------------------------------
-- Job Certifications
-- -----------------------------------------------------------------------------
CREATE TABLE job_certifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    certification_id UUID NOT NULL REFERENCES certification_taxonomy(id),

    is_required BOOLEAN DEFAULT true,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_job_certification UNIQUE (job_id, certification_id)
);

CREATE INDEX idx_job_certifications_job ON job_certifications(job_id);
CREATE INDEX idx_job_certifications_cert ON job_certifications(certification_id);

-- -----------------------------------------------------------------------------
-- Job Languages
-- -----------------------------------------------------------------------------
CREATE TABLE job_languages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,

    language_code VARCHAR(10) NOT NULL,
    minimum_level language_proficiency,
    is_required BOOLEAN DEFAULT true,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_job_language UNIQUE (job_id, language_code)
);

CREATE INDEX idx_job_languages_job ON job_languages(job_id);
CREATE INDEX idx_job_languages_code ON job_languages(language_code);
