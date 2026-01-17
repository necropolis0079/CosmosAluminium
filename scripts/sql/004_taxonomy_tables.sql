-- =============================================================================
-- LCMGoCloud-CAGenAI - Taxonomy Tables
-- =============================================================================
-- Skills, roles, certifications, and software taxonomies
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Skill Taxonomy
-- -----------------------------------------------------------------------------
CREATE TABLE skill_taxonomy (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Identification
    canonical_id VARCHAR(100) NOT NULL UNIQUE,

    -- Names
    name_en VARCHAR(255) NOT NULL,
    name_el VARCHAR(255),

    -- Classification
    category skill_category NOT NULL,
    subcategory VARCHAR(100),
    domain VARCHAR(100),

    -- Hierarchy
    parent_skill_id UUID REFERENCES skill_taxonomy(id),
    skill_level INTEGER DEFAULT 0,

    -- Aliases
    aliases_en TEXT[] DEFAULT '{}',
    aliases_el TEXT[] DEFAULT '{}',

    -- Related
    related_skills UUID[] DEFAULT '{}',
    required_for_roles UUID[] DEFAULT '{}',

    -- Metadata
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT true,

    -- Search (populated via trigger)
    search_vector tsvector,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_skill_taxonomy_canonical ON skill_taxonomy(canonical_id);
CREATE INDEX idx_skill_taxonomy_category ON skill_taxonomy(category);
CREATE INDEX idx_skill_taxonomy_domain ON skill_taxonomy(domain);
CREATE INDEX idx_skill_taxonomy_parent ON skill_taxonomy(parent_skill_id);
CREATE INDEX idx_skill_taxonomy_search ON skill_taxonomy USING gin(search_vector);
CREATE INDEX idx_skill_taxonomy_aliases_en ON skill_taxonomy USING gin(aliases_en);
CREATE INDEX idx_skill_taxonomy_aliases_el ON skill_taxonomy USING gin(aliases_el);

-- -----------------------------------------------------------------------------
-- Soft Skill Taxonomy
-- -----------------------------------------------------------------------------
CREATE TABLE soft_skill_taxonomy (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    canonical_id VARCHAR(100) NOT NULL UNIQUE,

    name_en VARCHAR(255) NOT NULL,
    name_el VARCHAR(255),

    category VARCHAR(100),

    aliases_en TEXT[] DEFAULT '{}',
    aliases_el TEXT[] DEFAULT '{}',

    description TEXT,
    behavioral_indicators TEXT[],

    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_soft_skill_taxonomy_canonical ON soft_skill_taxonomy(canonical_id);
CREATE INDEX idx_soft_skill_taxonomy_category ON soft_skill_taxonomy(category);

-- -----------------------------------------------------------------------------
-- Role Taxonomy
-- -----------------------------------------------------------------------------
CREATE TABLE role_taxonomy (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    canonical_id VARCHAR(100) NOT NULL UNIQUE,

    -- Names
    name_en VARCHAR(255) NOT NULL,
    name_el VARCHAR(255),

    -- Classification
    category VARCHAR(100),
    department VARCHAR(100),

    -- Hierarchy
    parent_role_id UUID REFERENCES role_taxonomy(id),
    experience_level experience_level,

    -- Aliases
    aliases_en TEXT[] DEFAULT '{}',
    aliases_el TEXT[] DEFAULT '{}',

    -- Requirements
    typical_skills UUID[] DEFAULT '{}',
    required_education education_level[],
    typical_experience_years_min INTEGER,
    typical_experience_years_max INTEGER,

    -- Metadata
    description TEXT,
    responsibilities TEXT[],
    is_active BOOLEAN DEFAULT true,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_role_taxonomy_canonical ON role_taxonomy(canonical_id);
CREATE INDEX idx_role_taxonomy_category ON role_taxonomy(category);
CREATE INDEX idx_role_taxonomy_parent ON role_taxonomy(parent_role_id);
CREATE INDEX idx_role_taxonomy_level ON role_taxonomy(experience_level);

-- -----------------------------------------------------------------------------
-- Certification Taxonomy
-- -----------------------------------------------------------------------------
CREATE TABLE certification_taxonomy (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    canonical_id VARCHAR(100) NOT NULL UNIQUE,

    name_en VARCHAR(255) NOT NULL,
    name_el VARCHAR(255),

    -- Issuer
    issuing_organization VARCHAR(255),
    issuer_country VARCHAR(100),

    -- Classification
    category VARCHAR(100),
    industry VARCHAR(100),

    -- Aliases
    aliases TEXT[] DEFAULT '{}',
    abbreviations TEXT[] DEFAULT '{}',

    -- Details
    description TEXT,
    validity_period_months INTEGER,
    renewal_required BOOLEAN DEFAULT false,

    -- Related
    related_skills UUID[] DEFAULT '{}',
    prerequisite_certs UUID[] DEFAULT '{}',

    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_certification_taxonomy_canonical ON certification_taxonomy(canonical_id);
CREATE INDEX idx_certification_taxonomy_category ON certification_taxonomy(category);
CREATE INDEX idx_certification_taxonomy_issuer ON certification_taxonomy(issuing_organization);

-- -----------------------------------------------------------------------------
-- Software Taxonomy
-- -----------------------------------------------------------------------------
CREATE TABLE software_taxonomy (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    canonical_id VARCHAR(100) NOT NULL UNIQUE,

    name VARCHAR(255) NOT NULL,
    vendor VARCHAR(255),

    category VARCHAR(100),
    subcategory VARCHAR(100),

    aliases TEXT[] DEFAULT '{}',
    versions TEXT[] DEFAULT '{}',

    description TEXT,
    is_active BOOLEAN DEFAULT true,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_software_taxonomy_canonical ON software_taxonomy(canonical_id);
CREATE INDEX idx_software_taxonomy_category ON software_taxonomy(category);
CREATE INDEX idx_software_taxonomy_vendor ON software_taxonomy(vendor);
