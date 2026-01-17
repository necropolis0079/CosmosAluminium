-- =============================================================================
-- LCMGoCloud-CAGenAI - Search & System Tables
-- =============================================================================
-- Saved searches, query history, users, api_keys, system_config
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Saved Searches
-- -----------------------------------------------------------------------------
CREATE TABLE saved_searches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,

    -- Search Details
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Query
    query_text TEXT,
    query_sql TEXT,
    query_parameters JSONB DEFAULT '{}',

    -- Filters
    filters JSONB DEFAULT '{}',

    -- Results
    last_result_count INTEGER,
    last_executed_at TIMESTAMP WITH TIME ZONE,

    -- Sharing
    is_public BOOLEAN DEFAULT false,
    shared_with UUID[] DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_saved_searches_user ON saved_searches(user_id);
CREATE INDEX idx_saved_searches_public ON saved_searches(is_public) WHERE is_public = true;

-- -----------------------------------------------------------------------------
-- Search Alerts
-- -----------------------------------------------------------------------------
CREATE TABLE search_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    saved_search_id UUID NOT NULL REFERENCES saved_searches(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,

    -- Alert Settings
    is_active BOOLEAN DEFAULT true,
    frequency alert_frequency DEFAULT 'daily',

    -- Delivery
    notify_email BOOLEAN DEFAULT true,
    notify_in_app BOOLEAN DEFAULT true,

    -- Tracking
    last_alert_at TIMESTAMP WITH TIME ZONE,
    last_new_matches INTEGER DEFAULT 0,
    total_alerts_sent INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_search_alerts_search ON search_alerts(saved_search_id);
CREATE INDEX idx_search_alerts_user ON search_alerts(user_id);
CREATE INDEX idx_search_alerts_active ON search_alerts(is_active) WHERE is_active = true;

-- -----------------------------------------------------------------------------
-- Query History
-- -----------------------------------------------------------------------------
CREATE TABLE query_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    session_id VARCHAR(100),

    -- Query
    query_text TEXT NOT NULL,
    query_type VARCHAR(50),

    -- Processing
    generated_sql TEXT,
    processing_time_ms INTEGER,

    -- Results
    result_count INTEGER,
    result_ids UUID[],

    -- Feedback
    user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 5),
    user_feedback TEXT,

    -- Metadata
    client_info JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_query_history_user ON query_history(user_id);
CREATE INDEX idx_query_history_session ON query_history(session_id);
CREATE INDEX idx_query_history_created ON query_history(created_at DESC);

-- -----------------------------------------------------------------------------
-- Users Table
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Identity
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) UNIQUE,

    -- Profile
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    display_name VARCHAR(200),
    avatar_url VARCHAR(500),

    -- Authentication (Cognito handles auth, this is for app-level data)
    cognito_sub VARCHAR(255) UNIQUE,
    auth_provider VARCHAR(50) DEFAULT 'cognito',

    -- Role
    role VARCHAR(50) DEFAULT 'user',
    permissions JSONB DEFAULT '{}',

    -- Status
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,

    -- Security
    last_login_at TIMESTAMP WITH TIME ZONE,
    last_login_ip INET,
    failed_login_count INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,

    -- Preferences
    preferences JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_cognito_sub ON users(cognito_sub);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = true;

-- -----------------------------------------------------------------------------
-- API Keys
-- -----------------------------------------------------------------------------
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Key Details
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(10) NOT NULL,

    -- Permissions
    scopes TEXT[] DEFAULT '{}',

    -- Rate Limits
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_day INTEGER DEFAULT 10000,

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Usage
    last_used_at TIMESTAMP WITH TIME ZONE,
    total_requests INTEGER DEFAULT 0,

    -- Expiry
    expires_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX idx_api_keys_active ON api_keys(is_active) WHERE is_active = true;

-- -----------------------------------------------------------------------------
-- System Config
-- -----------------------------------------------------------------------------
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    key VARCHAR(255) NOT NULL UNIQUE,
    value JSONB NOT NULL,

    description TEXT,
    is_sensitive BOOLEAN DEFAULT false,

    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_config_key ON system_config(key);

-- -----------------------------------------------------------------------------
-- Processing Jobs
-- -----------------------------------------------------------------------------
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Job Type
    job_type VARCHAR(100) NOT NULL,

    -- Reference
    reference_type VARCHAR(100),
    reference_id UUID,

    -- Status
    status VARCHAR(50) DEFAULT 'pending',

    -- Progress
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,

    -- Results
    result JSONB,
    error_message TEXT,
    error_details JSONB,

    -- Timing
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    created_by UUID REFERENCES users(id),
    metadata JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_processing_jobs_type ON processing_jobs(job_type);
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX idx_processing_jobs_reference ON processing_jobs(reference_type, reference_id);

-- -----------------------------------------------------------------------------
-- Notifications
-- -----------------------------------------------------------------------------
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Notification
    type notification_type NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT,

    -- Reference
    reference_type VARCHAR(100),
    reference_id UUID,
    action_url VARCHAR(500),

    -- Status
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMP WITH TIME ZONE,

    -- Delivery
    sent_email BOOLEAN DEFAULT false,
    email_sent_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_unread ON notifications(user_id, is_read) WHERE is_read = false;
CREATE INDEX idx_notifications_created ON notifications(created_at DESC);
