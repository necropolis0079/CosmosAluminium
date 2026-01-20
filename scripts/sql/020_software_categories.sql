-- ============================================================================
-- Migration: 020_software_categories.sql
-- Description: Software categories, certification skill inference, and domain mappings
-- Version: 1.0
-- Date: 2026-01-20
-- ============================================================================

-- ============================================================================
-- TABLE: software_categories
-- Maps generic software categories to specific software names
-- ============================================================================

CREATE TABLE IF NOT EXISTS software_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_name TEXT NOT NULL UNIQUE,  -- e.g., "ERP", "Office", "CRM"
    category_name_el TEXT,               -- Greek name
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABLE: software_category_members
-- Links software taxonomy entries to categories
-- ============================================================================

CREATE TABLE IF NOT EXISTS software_category_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id UUID NOT NULL REFERENCES software_categories(id),
    software_id UUID REFERENCES software_taxonomy(id),
    software_name TEXT NOT NULL,         -- Can include entries not in taxonomy
    software_name_variations TEXT[],     -- Alternative names/spellings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category_id, software_name)
);

-- ============================================================================
-- TABLE: certification_skill_inference
-- Maps certifications to implied skills (e.g., ECDL → Office)
-- ============================================================================

CREATE TABLE IF NOT EXISTS certification_skill_inference (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    certification_name TEXT NOT NULL,
    certification_variations TEXT[],     -- Alternative names
    inferred_skill_category TEXT NOT NULL,  -- "office", "erp", "programming", etc.
    inferred_skills TEXT[],              -- Specific skills implied
    confidence TEXT DEFAULT 'high',      -- high, medium, low
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(certification_name)
);

-- ============================================================================
-- INSERT: Software Categories
-- ============================================================================

INSERT INTO software_categories (category_name, category_name_el, description) VALUES
    ('ERP', 'ERP Συστήματα', 'Enterprise Resource Planning systems'),
    ('Office', 'Εφαρμογές Γραφείου', 'Microsoft Office and similar productivity suites'),
    ('Accounting', 'Λογιστικά Προγράμματα', 'Accounting and financial software'),
    ('CRM', 'CRM Συστήματα', 'Customer Relationship Management'),
    ('Database', 'Βάσεις Δεδομένων', 'Database management systems'),
    ('CAD', 'Σχεδιαστικά', 'Computer-Aided Design software'),
    ('Programming', 'Προγραμματισμός', 'Programming languages and IDEs'),
    ('HR', 'Διαχείριση Προσωπικού', 'HR management systems'),
    ('eCommerce', 'Ηλεκτρονικό Εμπόριο', 'E-commerce platforms'),
    ('Cloud', 'Cloud Υπηρεσίες', 'Cloud services and platforms'),
    ('Analytics', 'Αναλυτικά Εργαλεία', 'Business Intelligence and Analytics')
ON CONFLICT (category_name) DO NOTHING;

-- ============================================================================
-- INSERT: ERP Systems (Greek and International)
-- ============================================================================

INSERT INTO software_category_members (category_id, software_name, software_name_variations) VALUES
    -- Greek ERP Systems
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'SoftOne', ARRAY['Soft One', 'Soft1', 'SoftOne ERP', 'Soft One ERP', 'Softone']),
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'Singular', ARRAY['Singular Logic', 'SingularLogic', 'Singular ERP']),
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'Galaxy', ARRAY['Galaxy ERP', 'Entersoft Galaxy', 'Galaxy Cosmos']),
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'Atlantis', ARRAY['Atlantis ERP', 'Altec Atlantis', 'Atlantis II']),
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'Entersoft', ARRAY['Entersoft ERP', 'Entersoft Business Suite']),
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'Pylon', ARRAY['Pylon ERP', 'Epsilon Net Pylon', 'Epsilon Pylon']),
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'Pegasus', ARRAY['Pegasus ERP', 'Pegasus Opera']),
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'Unisoft', ARRAY['Unisoft ERP']),
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'Noval', ARRAY['Noval ERP']),
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'Computing', ARRAY['Computing ERP']),
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'Data Communication', ARRAY['Data Communication ERP', 'DC ERP']),
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'Megasoft', ARRAY['Megasoft ERP', 'PRISMA Win']),
    -- International ERP Systems
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'SAP', ARRAY['SAP ERP', 'SAP R/3', 'SAP S/4HANA', 'SAP Business One', 'SAP B1']),
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'Oracle ERP', ARRAY['Oracle', 'Oracle Cloud', 'Oracle ERP Cloud', 'Oracle Financials']),
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'Microsoft Dynamics', ARRAY['Dynamics 365', 'Dynamics NAV', 'Navision', 'Dynamics AX', 'Axapta', 'MS Dynamics']),
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'NetSuite', ARRAY['Oracle NetSuite']),
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'Odoo', ARRAY['Odoo ERP', 'OpenERP']),
    ((SELECT id FROM software_categories WHERE category_name = 'ERP'), 'Sage', ARRAY['Sage ERP', 'Sage X3', 'Sage 50', 'Sage 100'])
ON CONFLICT (category_id, software_name) DO NOTHING;

-- ============================================================================
-- INSERT: Office Suite Software
-- ============================================================================

INSERT INTO software_category_members (category_id, software_name, software_name_variations) VALUES
    ((SELECT id FROM software_categories WHERE category_name = 'Office'), 'Microsoft Office', ARRAY['MS Office', 'Office Suite', 'Office 365', 'Microsoft 365', 'M365']),
    ((SELECT id FROM software_categories WHERE category_name = 'Office'), 'Microsoft Excel', ARRAY['Excel', 'MS Excel', 'Excel Spreadsheet']),
    ((SELECT id FROM software_categories WHERE category_name = 'Office'), 'Microsoft Word', ARRAY['Word', 'MS Word']),
    ((SELECT id FROM software_categories WHERE category_name = 'Office'), 'Microsoft PowerPoint', ARRAY['PowerPoint', 'PPT', 'MS PowerPoint']),
    ((SELECT id FROM software_categories WHERE category_name = 'Office'), 'Microsoft Outlook', ARRAY['Outlook', 'MS Outlook']),
    ((SELECT id FROM software_categories WHERE category_name = 'Office'), 'Microsoft Access', ARRAY['Access', 'MS Access']),
    ((SELECT id FROM software_categories WHERE category_name = 'Office'), 'Google Workspace', ARRAY['G Suite', 'Google Docs', 'Google Sheets', 'Google Slides']),
    ((SELECT id FROM software_categories WHERE category_name = 'Office'), 'LibreOffice', ARRAY['Libre Office', 'OpenOffice', 'Open Office'])
ON CONFLICT (category_id, software_name) DO NOTHING;

-- ============================================================================
-- INSERT: Accounting Software
-- ============================================================================

INSERT INTO software_category_members (category_id, software_name, software_name_variations) VALUES
    ((SELECT id FROM software_categories WHERE category_name = 'Accounting'), 'SoftOne', ARRAY['Soft One', 'SoftOne Accounting']),
    ((SELECT id FROM software_categories WHERE category_name = 'Accounting'), 'Singular', ARRAY['Singular Logic Accounting']),
    ((SELECT id FROM software_categories WHERE category_name = 'Accounting'), 'Galaxy', ARRAY['Galaxy Accounting', 'Entersoft']),
    ((SELECT id FROM software_categories WHERE category_name = 'Accounting'), 'Epsilon', ARRAY['Epsilon Net', 'Epsilon Accounting']),
    ((SELECT id FROM software_categories WHERE category_name = 'Accounting'), 'PRISMA Win', ARRAY['Prisma', 'Megasoft PRISMA']),
    ((SELECT id FROM software_categories WHERE category_name = 'Accounting'), 'KEFALAIO', ARRAY['Κεφάλαιο', 'Kefalaio']),
    ((SELECT id FROM software_categories WHERE category_name = 'Accounting'), 'QuickBooks', ARRAY['QB', 'Quickbooks']),
    ((SELECT id FROM software_categories WHERE category_name = 'Accounting'), 'Xero', ARRAY['Xero Accounting']),
    ((SELECT id FROM software_categories WHERE category_name = 'Accounting'), 'MYOB', ARRAY['Mind Your Own Business'])
ON CONFLICT (category_id, software_name) DO NOTHING;

-- ============================================================================
-- INSERT: Certification → Skill Inference
-- ============================================================================

INSERT INTO certification_skill_inference (certification_name, certification_variations, inferred_skill_category, inferred_skills, confidence, notes) VALUES
    -- Office/Computer Skills Certifications
    ('ECDL', ARRAY['European Computer Driving Licence', 'ECDL Foundation', 'ECDL Core', 'ECDL Advanced', 'Πιστοποιητικό ECDL', 'ECDL Certificate'],
     'office', ARRAY['Microsoft Excel', 'Microsoft Word', 'Microsoft PowerPoint', 'Microsoft Outlook', 'Microsoft Office', 'Computer Literacy'], 'high',
     'ECDL certifies proficiency in Microsoft Office applications'),

    ('ICDL', ARRAY['International Computer Driving Licence', 'ICDL Foundation'],
     'office', ARRAY['Microsoft Excel', 'Microsoft Word', 'Microsoft PowerPoint', 'Microsoft Outlook', 'Microsoft Office'], 'high',
     'ICDL is the international version of ECDL'),

    ('MOS', ARRAY['Microsoft Office Specialist', 'MOS Certification', 'Microsoft Certified'],
     'office', ARRAY['Microsoft Excel', 'Microsoft Word', 'Microsoft PowerPoint', 'Microsoft Office'], 'high',
     'Official Microsoft certification for Office proficiency'),

    ('IC3', ARRAY['Internet and Computing Core Certification'],
     'office', ARRAY['Microsoft Office', 'Computer Literacy', 'Internet Usage'], 'medium',
     'General computing competency certification'),

    -- Accounting Certifications
    ('ACCA', ARRAY['Association of Chartered Certified Accountants'],
     'accounting', ARRAY['Financial Accounting', 'Management Accounting', 'Financial Reporting'], 'high',
     'International accounting qualification'),

    ('CPA', ARRAY['Certified Public Accountant', 'Λογιστής Α Τάξης', 'Λογιστής Α Τάξεως'],
     'accounting', ARRAY['Accounting', 'Tax', 'Auditing', 'Financial Reporting'], 'high',
     'Professional accounting certification'),

    ('CIMA', ARRAY['Chartered Institute of Management Accountants'],
     'accounting', ARRAY['Management Accounting', 'Business Strategy', 'Financial Analysis'], 'high',
     'Management accounting qualification'),

    ('ΟΕΕ', ARRAY['Οικονομικό Επιμελητήριο Ελλάδος', 'OEE', 'Μέλος ΟΕΕ'],
     'accounting', ARRAY['Greek Accounting Standards', 'Tax Compliance'], 'high',
     'Greek Economic Chamber membership'),

    ('ΣΟΕΛ', ARRAY['Σώμα Ορκωτών Ελεγκτών Λογιστών', 'SOEL', 'Ορκωτός Λογιστής'],
     'accounting', ARRAY['Auditing', 'Financial Reporting', 'Greek Accounting'], 'high',
     'Greek certified auditor qualification'),

    -- ERP Certifications
    ('SAP Certification', ARRAY['SAP Certified', 'SAP Professional', 'SAP Consultant'],
     'erp', ARRAY['SAP', 'ERP'], 'high',
     'SAP professional certification'),

    -- Language Certifications that imply language skills
    ('TOEFL', ARRAY['Test of English as a Foreign Language'],
     'language', ARRAY['English'], 'high',
     'English proficiency test'),

    ('IELTS', ARRAY['International English Language Testing System'],
     'language', ARRAY['English'], 'high',
     'English proficiency test'),

    ('Cambridge', ARRAY['Cambridge English', 'FCE', 'CAE', 'CPE', 'First Certificate', 'Proficiency'],
     'language', ARRAY['English'], 'high',
     'Cambridge English qualification'),

    ('Goethe', ARRAY['Goethe-Zertifikat', 'Goethe Institut'],
     'language', ARRAY['German'], 'high',
     'German language certification'),

    ('DELF', ARRAY['Diplôme dÉtudes en Langue Française', 'DALF'],
     'language', ARRAY['French'], 'high',
     'French language certification')

ON CONFLICT (certification_name) DO NOTHING;

-- ============================================================================
-- FUNCTION: get_category_software
-- Returns all software names that belong to a category
-- ============================================================================

CREATE OR REPLACE FUNCTION get_category_software(p_category_name TEXT)
RETURNS TEXT[] AS $$
DECLARE
    result TEXT[];
BEGIN
    SELECT array_agg(DISTINCT sw)
    INTO result
    FROM (
        -- Get main software names
        SELECT software_name AS sw
        FROM software_category_members scm
        JOIN software_categories sc ON scm.category_id = sc.id
        WHERE LOWER(sc.category_name) = LOWER(p_category_name)

        UNION ALL

        -- Get variations
        SELECT UNNEST(software_name_variations) AS sw
        FROM software_category_members scm
        JOIN software_categories sc ON scm.category_id = sc.id
        WHERE LOWER(sc.category_name) = LOWER(p_category_name)
    ) subq;

    RETURN COALESCE(result, ARRAY[]::TEXT[]);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: check_software_category_match
-- Checks if candidate has ANY software from a category
-- ============================================================================

CREATE OR REPLACE FUNCTION check_software_category_match(
    p_candidate_software TEXT[],
    p_required_category TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    category_software TEXT[];
BEGIN
    -- Get all software in the category
    category_software := get_category_software(p_required_category);

    -- Check if any candidate software matches (case-insensitive)
    RETURN EXISTS (
        SELECT 1
        FROM unnest(p_candidate_software) cs, unnest(category_software) cat
        WHERE LOWER(cs) LIKE '%' || LOWER(cat) || '%'
           OR LOWER(cat) LIKE '%' || LOWER(cs) || '%'
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: get_certification_implied_skills
-- Returns skills implied by a certification
-- ============================================================================

CREATE OR REPLACE FUNCTION get_certification_implied_skills(p_cert_name TEXT)
RETURNS TEXT[] AS $$
DECLARE
    result TEXT[];
BEGIN
    SELECT inferred_skills
    INTO result
    FROM certification_skill_inference csi
    WHERE LOWER(p_cert_name) LIKE '%' || LOWER(certification_name) || '%'
       OR EXISTS (
           SELECT 1 FROM unnest(certification_variations) cv
           WHERE LOWER(p_cert_name) LIKE '%' || LOWER(cv) || '%'
       )
    LIMIT 1;

    RETURN COALESCE(result, ARRAY[]::TEXT[]);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: expand_candidate_skills
-- Returns candidate software with implied skills from certifications
-- ============================================================================

CREATE OR REPLACE FUNCTION expand_candidate_skills(
    p_candidate_software TEXT[],
    p_candidate_certifications TEXT[]
)
RETURNS TEXT[] AS $$
DECLARE
    all_skills TEXT[] := p_candidate_software;
    cert TEXT;
    implied TEXT[];
BEGIN
    -- Add implied skills from certifications
    IF p_candidate_certifications IS NOT NULL THEN
        FOREACH cert IN ARRAY p_candidate_certifications LOOP
            implied := get_certification_implied_skills(cert);
            IF implied IS NOT NULL THEN
                all_skills := array_cat(all_skills, implied);
            END IF;
        END LOOP;
    END IF;

    -- Return unique values
    RETURN ARRAY(SELECT DISTINCT UNNEST(all_skills));
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- UPDATE FUNCTION: match_candidates_relaxed (v2)
-- Now includes category matching and certification inference
-- ============================================================================

CREATE OR REPLACE FUNCTION match_candidates_relaxed(
    p_role TEXT DEFAULT NULL,
    p_min_experience NUMERIC DEFAULT NULL,
    p_software TEXT[] DEFAULT NULL,
    p_languages TEXT[] DEFAULT NULL,
    p_certifications TEXT[] DEFAULT NULL,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    candidate_id UUID,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    address_city TEXT,
    total_experience_years NUMERIC,
    match_score NUMERIC,
    matched_criteria JSONB,
    roles TEXT[],
    software TEXT[],
    languages TEXT[],
    certifications TEXT[],
    skills TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    WITH
    -- Expand candidate skills to include implied skills from certifications
    expanded_candidates AS (
        SELECT
            v.*,
            expand_candidate_skills(v.software, v.certifications_en) AS expanded_software
        FROM v_candidate_match_data v
    ),
    scored_candidates AS (
        SELECT
            v.id,
            v.first_name,
            v.last_name,
            v.email,
            v.phone,
            v.address_city,
            v.total_experience_years,
            v.roles_en,
            v.roles_el,
            v.software,
            v.expanded_software,
            v.languages,
            v.certifications_en,
            v.certifications_el,
            v.skills_en,
            v.skills_el,
            -- Calculate match score (0-1 scale)
            (
                -- Role match (25%)
                CASE
                    WHEN p_role IS NULL THEN 0
                    WHEN EXISTS (
                        SELECT 1 FROM unnest(v.roles_en) r
                        WHERE LOWER(r) LIKE '%' || LOWER(p_role) || '%'
                    ) THEN 0.25
                    WHEN EXISTS (
                        SELECT 1 FROM unnest(v.roles_el) r
                        WHERE LOWER(r) LIKE '%' || LOWER(p_role) || '%'
                    ) THEN 0.25
                    ELSE 0
                END +
                -- Experience match (35%)
                CASE
                    WHEN p_min_experience IS NULL THEN 0
                    WHEN v.total_experience_years >= p_min_experience THEN 0.35
                    WHEN v.total_experience_years >= p_min_experience * 0.7 THEN 0.20
                    WHEN v.total_experience_years >= p_min_experience * 0.5 THEN 0.10
                    ELSE 0
                END +
                -- Software match (20%) - NOW includes category matching and implied skills
                CASE
                    WHEN p_software IS NULL OR array_length(p_software, 1) IS NULL THEN 0
                    -- Check direct match with expanded software (includes certification-implied)
                    WHEN EXISTS (
                        SELECT 1 FROM unnest(v.expanded_software) sw, unnest(p_software) ps
                        WHERE LOWER(sw) LIKE '%' || LOWER(ps) || '%'
                           OR LOWER(ps) LIKE '%' || LOWER(sw) || '%'
                    ) THEN 0.20
                    -- Check category match (ERP matches SoftOne, Singular, etc.)
                    WHEN EXISTS (
                        SELECT 1 FROM unnest(p_software) ps
                        WHERE check_software_category_match(v.expanded_software, ps)
                    ) THEN 0.18  -- Slightly lower for category match
                    ELSE 0
                END +
                -- Language match (10%)
                CASE
                    WHEN p_languages IS NULL OR array_length(p_languages, 1) IS NULL THEN 0
                    WHEN v.languages::text[] && p_languages THEN 0.10
                    ELSE 0
                END +
                -- Certification match (10%)
                CASE
                    WHEN p_certifications IS NULL OR array_length(p_certifications, 1) IS NULL THEN 0
                    WHEN v.certifications_en::text[] && p_certifications THEN 0.10
                    WHEN v.certifications_el::text[] && p_certifications THEN 0.10
                    ELSE 0
                END
            )::NUMERIC AS calc_score,
            -- Track which criteria matched
            jsonb_build_object(
                'role', CASE
                    WHEN p_role IS NULL THEN NULL
                    WHEN EXISTS (SELECT 1 FROM unnest(v.roles_en) r WHERE LOWER(r) LIKE '%' || LOWER(p_role) || '%') THEN true
                    WHEN EXISTS (SELECT 1 FROM unnest(v.roles_el) r WHERE LOWER(r) LIKE '%' || LOWER(p_role) || '%') THEN true
                    ELSE false
                END,
                'experience', CASE
                    WHEN p_min_experience IS NULL THEN NULL
                    ELSE v.total_experience_years >= p_min_experience
                END,
                'experience_years', v.total_experience_years,
                'software', CASE
                    WHEN p_software IS NULL THEN NULL
                    ELSE (
                        EXISTS (
                            SELECT 1 FROM unnest(v.expanded_software) sw, unnest(p_software) ps
                            WHERE LOWER(sw) LIKE '%' || LOWER(ps) || '%'
                               OR LOWER(ps) LIKE '%' || LOWER(sw) || '%'
                        )
                        OR EXISTS (
                            SELECT 1 FROM unnest(p_software) ps
                            WHERE check_software_category_match(v.expanded_software, ps)
                        )
                    )
                END,
                'software_found', (
                    SELECT array_agg(DISTINCT sw) FROM unnest(v.expanded_software) sw, unnest(p_software) ps
                    WHERE LOWER(sw) LIKE '%' || LOWER(ps) || '%'
                       OR LOWER(ps) LIKE '%' || LOWER(sw) || '%'
                ),
                'languages', CASE
                    WHEN p_languages IS NULL THEN NULL
                    ELSE v.languages::text[] && p_languages
                END,
                'certifications', CASE
                    WHEN p_certifications IS NULL THEN NULL
                    ELSE (v.certifications_en::text[] && p_certifications OR v.certifications_el::text[] && p_certifications)
                END
            ) AS criteria_matched
        FROM expanded_candidates v
        WHERE
            -- At least one criterion must match
            (p_role IS NULL OR
                EXISTS (SELECT 1 FROM unnest(v.roles_en) r WHERE LOWER(r) LIKE '%' || LOWER(p_role) || '%') OR
                EXISTS (SELECT 1 FROM unnest(v.roles_el) r WHERE LOWER(r) LIKE '%' || LOWER(p_role) || '%')
            ) OR
            (p_min_experience IS NULL OR v.total_experience_years >= p_min_experience * 0.5) OR
            (p_software IS NULL OR EXISTS (
                SELECT 1 FROM unnest(v.expanded_software) sw, unnest(p_software) ps
                WHERE LOWER(sw) LIKE '%' || LOWER(ps) || '%'
                   OR LOWER(ps) LIKE '%' || LOWER(sw) || '%'
            ) OR EXISTS (
                SELECT 1 FROM unnest(p_software) ps
                WHERE check_software_category_match(v.expanded_software, ps)
            )) OR
            (p_languages IS NULL OR v.languages::text[] && p_languages) OR
            (p_certifications IS NULL OR v.certifications_en::text[] && p_certifications OR v.certifications_el::text[] && p_certifications)
    )
    SELECT
        sc.id,
        sc.first_name::text,
        sc.last_name::text,
        sc.email::text,
        sc.phone::text,
        sc.address_city::text,
        sc.total_experience_years,
        sc.calc_score,
        sc.criteria_matched,
        sc.roles_en::text[],
        sc.expanded_software::text[],  -- Return expanded software
        sc.languages::text[],
        sc.certifications_en::text[],
        sc.skills_en::text[]
    FROM scored_candidates sc
    WHERE sc.calc_score > 0
    ORDER BY sc.calc_score DESC, sc.total_experience_years DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT SELECT ON software_categories TO PUBLIC;
GRANT SELECT ON software_category_members TO PUBLIC;
GRANT SELECT ON certification_skill_inference TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_category_software TO PUBLIC;
GRANT EXECUTE ON FUNCTION check_software_category_match TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_certification_implied_skills TO PUBLIC;
GRANT EXECUTE ON FUNCTION expand_candidate_skills TO PUBLIC;

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Migration 020_software_categories.sql completed successfully';
    RAISE NOTICE 'Created tables: software_categories, software_category_members, certification_skill_inference';
    RAISE NOTICE 'Created functions: get_category_software, check_software_category_match, get_certification_implied_skills, expand_candidate_skills';
    RAISE NOTICE 'Updated function: match_candidates_relaxed (v2 with category matching)';

    -- Test ERP category
    RAISE NOTICE 'Test ERP category: %', get_category_software('ERP');

    -- Test Office category
    RAISE NOTICE 'Test Office category: %', get_category_software('Office');

    -- Test ECDL inference
    RAISE NOTICE 'Test ECDL inference: %', get_certification_implied_skills('ECDL');
END $$;
