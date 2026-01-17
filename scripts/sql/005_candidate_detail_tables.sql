-- =============================================================================
-- LCMGoCloud-CAGenAI - Candidate Detail Tables
-- =============================================================================
-- Education, experience, skills, languages, certifications, licenses
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Candidate Education
-- -----------------------------------------------------------------------------
CREATE TABLE candidate_education (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,

    -- Institution
    institution_name VARCHAR(255) NOT NULL,
    institution_name_normalized VARCHAR(255),
    institution_type VARCHAR(50),
    institution_country VARCHAR(100),
    institution_city VARCHAR(100),

    -- Degree
    degree_level education_level,
    degree_title VARCHAR(255),
    degree_title_normalized VARCHAR(255),
    field_of_study education_field,
    field_of_study_detail VARCHAR(255),
    specialization VARCHAR(255),

    -- Dates
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN DEFAULT false,
    graduation_year INTEGER,

    -- Details
    grade_value VARCHAR(20),
    grade_scale VARCHAR(50),
    thesis_title TEXT,
    honors VARCHAR(255),

    -- Verification
    is_verified BOOLEAN DEFAULT false,
    verification_date DATE,
    verification_source VARCHAR(100),

    -- Raw
    raw_text TEXT,
    confidence_score NUMERIC(3,2),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_education_date_range CHECK (
        end_date IS NULL OR start_date IS NULL OR end_date >= start_date
    )
);

CREATE INDEX idx_candidate_education_candidate ON candidate_education(candidate_id);
CREATE INDEX idx_candidate_education_level ON candidate_education(degree_level);
CREATE INDEX idx_candidate_education_field ON candidate_education(field_of_study);
CREATE INDEX idx_candidate_education_institution ON candidate_education
    USING gin(institution_name_normalized gin_trgm_ops);

-- -----------------------------------------------------------------------------
-- Candidate Experience
-- -----------------------------------------------------------------------------
CREATE TABLE candidate_experience (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,

    -- Company
    company_name VARCHAR(255) NOT NULL,
    company_name_normalized VARCHAR(255),
    company_industry VARCHAR(100),
    company_size VARCHAR(50),
    company_country VARCHAR(100),
    company_city VARCHAR(100),

    -- Position
    job_title VARCHAR(255) NOT NULL,
    job_title_normalized VARCHAR(255),
    role_id UUID REFERENCES role_taxonomy(id),
    department VARCHAR(100),
    employment_type employment_type,

    -- Dates
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN DEFAULT false,
    duration_months INTEGER, -- Computed via trigger or application logic

    -- Details
    description TEXT,
    responsibilities TEXT[],
    achievements TEXT[],
    technologies_used TEXT[],
    team_size INTEGER,
    reports_to VARCHAR(100),

    -- Salary (optional)
    salary_amount NUMERIC(10,2),
    salary_currency VARCHAR(3),
    salary_period VARCHAR(20),

    -- Verification
    is_verified BOOLEAN DEFAULT false,
    linkedin_url VARCHAR(500),

    -- Raw
    raw_text TEXT,
    confidence_score NUMERIC(3,2),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_experience_date_range CHECK (
        end_date IS NULL OR start_date IS NULL OR end_date >= start_date
    )
);

CREATE INDEX idx_candidate_experience_candidate ON candidate_experience(candidate_id);
CREATE INDEX idx_candidate_experience_company ON candidate_experience
    USING gin(company_name_normalized gin_trgm_ops);
CREATE INDEX idx_candidate_experience_title ON candidate_experience
    USING gin(job_title_normalized gin_trgm_ops);
CREATE INDEX idx_candidate_experience_role ON candidate_experience(role_id);
CREATE INDEX idx_candidate_experience_current ON candidate_experience(candidate_id)
    WHERE is_current = true;
CREATE INDEX idx_candidate_experience_dates ON candidate_experience(start_date, end_date);

-- -----------------------------------------------------------------------------
-- Candidate Skills
-- -----------------------------------------------------------------------------
CREATE TABLE candidate_skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skill_taxonomy(id),

    -- Proficiency
    skill_level skill_level,
    years_of_experience NUMERIC(4,1),
    last_used_year INTEGER,

    -- Source
    source VARCHAR(50),
    source_context TEXT,
    confidence_score NUMERIC(3,2),

    -- Verification
    is_verified BOOLEAN DEFAULT false,
    verified_by UUID,
    verified_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_candidate_skill UNIQUE (candidate_id, skill_id)
);

CREATE INDEX idx_candidate_skills_candidate ON candidate_skills(candidate_id);
CREATE INDEX idx_candidate_skills_skill ON candidate_skills(skill_id);
CREATE INDEX idx_candidate_skills_level ON candidate_skills(skill_level);
CREATE INDEX idx_candidate_skills_years ON candidate_skills(years_of_experience DESC);

-- -----------------------------------------------------------------------------
-- Candidate Languages
-- -----------------------------------------------------------------------------
CREATE TABLE candidate_languages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,

    -- Language
    language_code VARCHAR(10) NOT NULL,
    language_name VARCHAR(100) NOT NULL,

    -- Proficiency
    proficiency_level language_proficiency DEFAULT 'unknown',
    reading_level language_proficiency,
    writing_level language_proficiency,
    speaking_level language_proficiency,
    listening_level language_proficiency,

    -- Certification
    certification_name VARCHAR(255),
    certification_score VARCHAR(50),
    certification_date DATE,
    certification_expiry DATE,

    -- Verification
    is_native BOOLEAN DEFAULT false,
    is_verified BOOLEAN DEFAULT false,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_candidate_language UNIQUE (candidate_id, language_code)
);

CREATE INDEX idx_candidate_languages_candidate ON candidate_languages(candidate_id);
CREATE INDEX idx_candidate_languages_code ON candidate_languages(language_code);
CREATE INDEX idx_candidate_languages_level ON candidate_languages(proficiency_level);

-- -----------------------------------------------------------------------------
-- Candidate Certifications
-- -----------------------------------------------------------------------------
CREATE TABLE candidate_certifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,

    -- Certification
    certification_name VARCHAR(255) NOT NULL,
    certification_name_normalized VARCHAR(255),
    certification_id_taxonomy UUID REFERENCES certification_taxonomy(id),
    issuing_organization VARCHAR(255),
    issuing_organization_normalized VARCHAR(255),

    -- Details
    credential_id VARCHAR(255),
    credential_url VARCHAR(500),

    -- Dates
    issue_date DATE,
    expiry_date DATE,
    is_current BOOLEAN DEFAULT true, -- Updated via trigger or application logic

    -- Verification
    is_verified BOOLEAN DEFAULT false,
    verification_url VARCHAR(500),

    -- Raw
    raw_text TEXT,
    confidence_score NUMERIC(3,2),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_candidate_certifications_candidate ON candidate_certifications(candidate_id);
CREATE INDEX idx_candidate_certifications_name ON candidate_certifications
    USING gin(certification_name_normalized gin_trgm_ops);
CREATE INDEX idx_candidate_certifications_taxonomy ON candidate_certifications(certification_id_taxonomy);
CREATE INDEX idx_candidate_certifications_current ON candidate_certifications(candidate_id)
    WHERE is_current = true;

-- -----------------------------------------------------------------------------
-- Candidate Driving Licenses
-- -----------------------------------------------------------------------------
CREATE TABLE candidate_driving_licenses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,

    license_category driving_license_category NOT NULL,
    issue_date DATE,
    expiry_date DATE,
    issuing_country VARCHAR(100) DEFAULT 'Greece',
    license_number VARCHAR(100),

    is_verified BOOLEAN DEFAULT false,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_candidate_license UNIQUE (candidate_id, license_category)
);

CREATE INDEX idx_candidate_driving_licenses_candidate ON candidate_driving_licenses(candidate_id);
CREATE INDEX idx_candidate_driving_licenses_category ON candidate_driving_licenses(license_category);

-- -----------------------------------------------------------------------------
-- Candidate Software
-- -----------------------------------------------------------------------------
CREATE TABLE candidate_software (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    software_id UUID NOT NULL REFERENCES software_taxonomy(id),

    proficiency_level skill_level,
    version_used VARCHAR(50),
    years_of_experience NUMERIC(4,1),
    last_used_year INTEGER,

    source VARCHAR(50),
    confidence_score NUMERIC(3,2),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_candidate_software UNIQUE (candidate_id, software_id)
);

CREATE INDEX idx_candidate_software_candidate ON candidate_software(candidate_id);
CREATE INDEX idx_candidate_software_software ON candidate_software(software_id);
