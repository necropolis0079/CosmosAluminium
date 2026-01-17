-- =============================================================================
-- LCMGoCloud-CAGenAI - Matching & Gap Analysis Tables
-- =============================================================================
-- Job matches and gap analysis
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Job Matches
-- -----------------------------------------------------------------------------
CREATE TABLE job_matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,

    -- Scores
    overall_score NUMERIC(5,4),
    skills_score NUMERIC(5,4),
    experience_score NUMERIC(5,4),
    education_score NUMERIC(5,4),
    location_score NUMERIC(5,4),
    salary_score NUMERIC(5,4),

    -- Status
    match_status match_status DEFAULT 'new',
    match_source match_source DEFAULT 'automatic',

    -- Gap Analysis
    gap_severity gap_severity DEFAULT 'none',
    missing_skills UUID[],
    missing_certifications UUID[],

    -- Ranking
    rank_position INTEGER,

    -- Notes
    match_explanation TEXT,
    reviewer_notes TEXT,

    -- Workflow
    reviewed_by UUID,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    shortlisted_at TIMESTAMP WITH TIME ZONE,
    contacted_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_job_candidate_match UNIQUE (job_id, candidate_id)
);

CREATE INDEX idx_job_matches_job ON job_matches(job_id);
CREATE INDEX idx_job_matches_candidate ON job_matches(candidate_id);
CREATE INDEX idx_job_matches_score ON job_matches(overall_score DESC);
CREATE INDEX idx_job_matches_status ON job_matches(match_status);
CREATE INDEX idx_job_matches_job_score ON job_matches(job_id, overall_score DESC);

-- -----------------------------------------------------------------------------
-- Gap Analysis
-- -----------------------------------------------------------------------------
CREATE TABLE gap_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID NOT NULL REFERENCES job_matches(id) ON DELETE CASCADE,

    -- Gap Type
    gap_type VARCHAR(50) NOT NULL,
    gap_item_id UUID,
    gap_item_name VARCHAR(255),

    -- Details
    required_level VARCHAR(50),
    current_level VARCHAR(50),
    gap_severity gap_severity,

    -- Recommendation
    training_type training_type,
    training_recommendation TEXT,
    estimated_duration_weeks INTEGER,
    estimated_cost NUMERIC(10,2),

    -- Priority
    is_critical BOOLEAN DEFAULT false,
    priority_order INTEGER,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_gap_analysis_match ON gap_analysis(match_id);
CREATE INDEX idx_gap_analysis_type ON gap_analysis(gap_type);
CREATE INDEX idx_gap_analysis_severity ON gap_analysis(gap_severity);
