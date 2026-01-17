-- =============================================================================
-- LCMGoCloud-CAGenAI - GDPR & Compliance Tables
-- =============================================================================
-- Consent records, data subject requests, audit log, data retention
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Consent Records
-- -----------------------------------------------------------------------------
CREATE TABLE consent_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,

    -- Consent Type
    consent_type consent_type NOT NULL,

    -- Status
    status consent_status NOT NULL,

    -- Details
    consent_text TEXT,
    consent_version VARCHAR(50),

    -- Source
    ip_address INET,
    user_agent TEXT,
    collection_method VARCHAR(100),

    -- Dates
    granted_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    withdrawn_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_consent_records_candidate ON consent_records(candidate_id);
CREATE INDEX idx_consent_records_type ON consent_records(consent_type);
CREATE INDEX idx_consent_records_status ON consent_records(status);
CREATE INDEX idx_consent_records_expiry ON consent_records(expires_at) WHERE status = 'granted';

-- -----------------------------------------------------------------------------
-- Data Subject Requests (GDPR)
-- -----------------------------------------------------------------------------
CREATE TABLE data_subject_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID REFERENCES candidates(id) ON DELETE SET NULL,

    -- Request Details
    request_type data_request_type NOT NULL,
    status data_request_status DEFAULT 'pending',

    -- Requester
    requester_email VARCHAR(255) NOT NULL,
    requester_name VARCHAR(255),
    requester_verification_method VARCHAR(100),
    is_verified BOOLEAN DEFAULT false,

    -- Processing
    assigned_to UUID,
    processed_by UUID,

    -- Response
    response_notes TEXT,
    response_file_url VARCHAR(500),

    -- Dates
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deadline_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dsr_candidate ON data_subject_requests(candidate_id);
CREATE INDEX idx_dsr_status ON data_subject_requests(status);
CREATE INDEX idx_dsr_deadline ON data_subject_requests(deadline_at)
    WHERE status IN ('pending', 'processing');

-- -----------------------------------------------------------------------------
-- Audit Log
-- -----------------------------------------------------------------------------
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Actor
    user_id UUID,
    user_email VARCHAR(255),
    ip_address INET,
    user_agent TEXT,

    -- Action
    action audit_action NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,

    -- Details
    details JSONB,
    old_values JSONB,
    new_values JSONB,

    -- Metadata
    request_id VARCHAR(100),
    session_id VARCHAR(100),
    correlation_id VARCHAR(100),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created ON audit_log(created_at DESC);
CREATE INDEX idx_audit_log_correlation ON audit_log(correlation_id);

-- -----------------------------------------------------------------------------
-- Data Retention Policies
-- -----------------------------------------------------------------------------
CREATE TABLE data_retention_policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Policy Details
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Scope
    data_type VARCHAR(100) NOT NULL,

    -- Retention Rules
    retention_days INTEGER NOT NULL,
    action VARCHAR(50) NOT NULL,

    -- Conditions
    conditions JSONB,

    -- Status
    is_active BOOLEAN DEFAULT true,
    last_executed_at TIMESTAMP WITH TIME ZONE,
    next_execution_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_retention_policies_type ON data_retention_policies(data_type);
CREATE INDEX idx_retention_policies_active ON data_retention_policies(is_active) WHERE is_active = true;
