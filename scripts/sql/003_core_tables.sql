-- =============================================================================
-- LCMGoCloud-CAGenAI - Core Tables
-- =============================================================================
-- Primary tables: candidates, candidate_documents
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Candidates Table
-- -----------------------------------------------------------------------------
CREATE TABLE candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(100) UNIQUE,

    -- Personal Information
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    first_name_normalized VARCHAR(100),
    last_name_normalized VARCHAR(100),
    full_name_search VARCHAR(250) GENERATED ALWAYS AS (
        COALESCE(first_name_normalized, first_name) || ' ' ||
        COALESCE(last_name_normalized, last_name)
    ) STORED,

    email VARCHAR(255),
    email_secondary VARCHAR(255),
    phone VARCHAR(50),
    phone_secondary VARCHAR(50),

    date_of_birth DATE,
    gender gender_type DEFAULT 'unknown',
    marital_status marital_status DEFAULT 'unknown',
    nationality VARCHAR(100),

    -- Address
    address_street VARCHAR(255),
    address_city VARCHAR(100),
    address_region VARCHAR(100),
    address_postal_code VARCHAR(20),
    address_country VARCHAR(100) DEFAULT 'Greece',

    -- Status
    employment_status employment_status DEFAULT 'unknown',
    availability_status availability_status DEFAULT 'unknown',
    availability_date DATE,
    military_status military_status DEFAULT 'unknown',

    -- Preferences
    willing_to_relocate BOOLEAN DEFAULT false,
    relocation_regions TEXT[],
    expected_salary_min NUMERIC(10,2),
    expected_salary_max NUMERIC(10,2),
    salary_currency VARCHAR(3) DEFAULT 'EUR',
    preferred_employment_types employment_type[] DEFAULT '{}',
    preferred_work_arrangements work_arrangement[] DEFAULT '{}',

    -- Source & Processing
    cv_source cv_source,
    cv_source_detail VARCHAR(255),
    processing_status cv_processing_status DEFAULT 'pending',
    quality_score NUMERIC(3,2),
    quality_level quality_level,

    -- Raw Data
    raw_cv_text TEXT,
    parsed_cv_json JSONB,
    enrichment_data JSONB,

    -- Metadata
    notes TEXT,
    tags TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    is_duplicate BOOLEAN DEFAULT false,
    duplicate_of_id UUID REFERENCES candidates(id),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP WITH TIME ZONE,
    archived_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT valid_salary_range CHECK (
        expected_salary_max IS NULL OR
        expected_salary_min IS NULL OR
        expected_salary_max >= expected_salary_min
    ),
    CONSTRAINT valid_email CHECK (
        email IS NULL OR email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    )
);

-- Candidate indexes
CREATE INDEX idx_candidates_email ON candidates(email);
CREATE INDEX idx_candidates_phone ON candidates(phone);
CREATE INDEX idx_candidates_name_search ON candidates USING gin(full_name_search gin_trgm_ops);
CREATE INDEX idx_candidates_city ON candidates(address_city);
CREATE INDEX idx_candidates_region ON candidates(address_region);
CREATE INDEX idx_candidates_status ON candidates(processing_status);
CREATE INDEX idx_candidates_quality ON candidates(quality_score DESC);
CREATE INDEX idx_candidates_created ON candidates(created_at DESC);
CREATE INDEX idx_candidates_active ON candidates(is_active) WHERE is_active = true;
CREATE INDEX idx_candidates_tags ON candidates USING gin(tags);
CREATE INDEX idx_candidates_parsed_json ON candidates USING gin(parsed_cv_json);

-- -----------------------------------------------------------------------------
-- Candidate Documents Table
-- -----------------------------------------------------------------------------
CREATE TABLE candidate_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,

    -- Document Info
    document_type VARCHAR(50) NOT NULL, -- 'cv', 'cover_letter', 'certificate', 'portfolio'
    file_name VARCHAR(255) NOT NULL,
    file_extension VARCHAR(10) NOT NULL,
    file_size_bytes INTEGER,
    mime_type VARCHAR(100),

    -- Storage
    s3_bucket VARCHAR(255) NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    s3_version_id VARCHAR(100),

    -- Processing
    is_primary BOOLEAN DEFAULT false,
    is_processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMP WITH TIME ZONE,
    extraction_method VARCHAR(50), -- 'native', 'ocr', 'hybrid'
    extraction_confidence NUMERIC(3,2),
    page_count INTEGER,
    language_detected VARCHAR(10),

    -- Metadata
    checksum_sha256 VARCHAR(64),
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_candidate_documents_candidate ON candidate_documents(candidate_id);
CREATE INDEX idx_candidate_documents_primary ON candidate_documents(candidate_id, is_primary)
    WHERE is_primary = true;
CREATE INDEX idx_candidate_documents_type ON candidate_documents(document_type);
