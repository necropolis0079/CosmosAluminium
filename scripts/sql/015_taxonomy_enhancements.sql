-- =============================================================================
-- LCMGoCloud-CAGenAI - Task 1.4: Taxonomy Enhancements
-- =============================================================================
-- Session: 32 (2026-01-18)
-- Purpose:
--   1. Add columns for fuzzy matching, occurrence tracking, and alias management
--   2. Create taxonomy_feedback table for admin review workflow
--   3. Expand taxonomy entries based on unmatched items analysis
-- =============================================================================

-- =============================================================================
-- PART 1: SCHEMA ENHANCEMENTS
-- =============================================================================

-- Add fuzzy_aliases and tracking columns to skill_taxonomy
ALTER TABLE skill_taxonomy
ADD COLUMN IF NOT EXISTS fuzzy_aliases TEXT[],
ADD COLUMN IF NOT EXISTS occurrence_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS auto_generated BOOLEAN DEFAULT false;

-- Add fuzzy_aliases and tracking columns to software_taxonomy
ALTER TABLE software_taxonomy
ADD COLUMN IF NOT EXISTS fuzzy_aliases TEXT[],
ADD COLUMN IF NOT EXISTS occurrence_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;

-- Add fuzzy_aliases and tracking columns to role_taxonomy
ALTER TABLE role_taxonomy
ADD COLUMN IF NOT EXISTS fuzzy_aliases TEXT[],
ADD COLUMN IF NOT EXISTS occurrence_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;

-- Add fuzzy_aliases and tracking columns to certification_taxonomy
ALTER TABLE certification_taxonomy
ADD COLUMN IF NOT EXISTS fuzzy_aliases TEXT[],
ADD COLUMN IF NOT EXISTS occurrence_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;

-- Create trigram indexes for fuzzy matching (if not exists)
CREATE INDEX IF NOT EXISTS idx_skill_taxonomy_name_en_trgm ON skill_taxonomy USING gin (name_en gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_skill_taxonomy_name_el_trgm ON skill_taxonomy USING gin (name_el gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_software_taxonomy_name_trgm ON software_taxonomy USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_certification_taxonomy_name_en_trgm ON certification_taxonomy USING gin (name_en gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_certification_taxonomy_name_el_trgm ON certification_taxonomy USING gin (name_el gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_role_taxonomy_name_en_trgm ON role_taxonomy USING gin (name_en gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_role_taxonomy_name_el_trgm ON role_taxonomy USING gin (name_el gin_trgm_ops);

-- =============================================================================
-- PART 2: TAXONOMY FEEDBACK TABLE (Admin Review Workflow)
-- =============================================================================

CREATE TABLE IF NOT EXISTS taxonomy_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term_type VARCHAR(50) NOT NULL,  -- 'skill', 'software', 'certification', 'role'
    raw_term TEXT NOT NULL,
    normalized_term TEXT NOT NULL,
    candidate_id UUID REFERENCES candidates(id) ON DELETE SET NULL,
    correlation_id VARCHAR(100),

    -- Matching info
    suggested_canonical_id VARCHAR(100),
    suggested_taxonomy_id UUID,
    similarity_score DECIMAL(5,4),
    match_method VARCHAR(20),  -- 'fuzzy', 'semantic', 'llm', 'none'

    -- Review workflow
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'mapped', 'new_entry', 'rejected'
    mapped_to_canonical_id VARCHAR(100),
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,

    -- Metadata
    occurrence_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for taxonomy_feedback
CREATE INDEX IF NOT EXISTS idx_taxonomy_feedback_status ON taxonomy_feedback(term_type, status);
CREATE INDEX IF NOT EXISTS idx_taxonomy_feedback_term ON taxonomy_feedback(normalized_term);
CREATE INDEX IF NOT EXISTS idx_taxonomy_feedback_created ON taxonomy_feedback(created_at DESC);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS trg_taxonomy_feedback_updated ON taxonomy_feedback;
CREATE TRIGGER trg_taxonomy_feedback_updated
    BEFORE UPDATE ON taxonomy_feedback
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- View for admin dashboard: Top unmatched terms by frequency
CREATE OR REPLACE VIEW v_taxonomy_feedback_summary AS
SELECT
    term_type,
    normalized_term,
    COUNT(*) as total_occurrences,
    COUNT(DISTINCT candidate_id) as unique_candidates,
    MAX(similarity_score) as best_similarity,
    MAX(suggested_canonical_id) as suggested_mapping,
    MIN(created_at) as first_seen,
    MAX(created_at) as last_seen
FROM taxonomy_feedback
WHERE status = 'pending'
GROUP BY term_type, normalized_term
ORDER BY total_occurrences DESC;

COMMENT ON TABLE taxonomy_feedback IS 'Captures CV terms that could not be mapped to existing taxonomy for admin review (Task 1.4 Session 32)';

-- =============================================================================
-- PART 3: EXPANDED TAXONOMY ENTRIES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 3.1 EXPANDED SKILL TAXONOMY - General/Office/Business Skills
-- -----------------------------------------------------------------------------

INSERT INTO skill_taxonomy (canonical_id, name_en, name_el, category, subcategory, domain, aliases_en, aliases_el) VALUES
-- Customer Service & Sales
('SKILL_CUSTOMER_SERVICE', 'Customer Service', 'Εξυπηρέτηση Πελατών', 'soft', 'customer_relations', 'general',
 ARRAY['client service', 'customer support', 'customer care'],
 ARRAY['εξυπηρέτηση πελατών', 'υποστήριξη πελατών']),
('SKILL_SALES', 'Sales', 'Πωλήσεις', 'soft', 'sales', 'general',
 ARRAY['selling', 'sales skills', 'revenue generation'],
 ARRAY['πώληση', 'εμπορικές πωλήσεις']),
('SKILL_NEGOTIATION', 'Negotiation', 'Διαπραγμάτευση', 'soft', 'sales', 'general',
 ARRAY['negotiating', 'deal making'],
 ARRAY['διαπραγματεύσεις']),
('SKILL_MARKETING', 'Marketing', 'Μάρκετινγκ', 'soft', 'marketing', 'general',
 ARRAY['digital marketing', 'advertising'],
 ARRAY['διαφήμιση', 'προώθηση']),

-- Administrative & Organizational
('SKILL_ORGANIZATIONAL', 'Organizational Skills', 'Οργανωτικές Ικανότητες', 'soft', 'organizational', 'general',
 ARRAY['organization', 'planning', 'coordinating'],
 ARRAY['οργάνωση', 'διοργάνωση', 'οργανωτικότητα']),
('SKILL_ADMINISTRATIVE', 'Administrative Skills', 'Διοικητικές Ικανότητες', 'soft', 'administrative', 'general',
 ARRAY['admin skills', 'clerical', 'office administration'],
 ARRAY['διοίκηση', 'γραμματειακή υποστήριξη']),
('SKILL_SECRETARIAL', 'Secretarial Skills', 'Γραμματειακές Ικανότητες', 'soft', 'administrative', 'general',
 ARRAY['secretary', 'office support', 'typing'],
 ARRAY['γραμματεία', 'δακτυλογράφηση']),
('SKILL_DATA_ENTRY', 'Data Entry', 'Εισαγωγή Δεδομένων', 'technical', 'administrative', 'general',
 ARRAY['data input', 'typing'],
 ARRAY['καταχώρηση δεδομένων']),
('SKILL_FILING', 'Filing & Archiving', 'Αρχειοθέτηση', 'technical', 'administrative', 'general',
 ARRAY['document management', 'records management'],
 ARRAY['ταξινόμηση', 'αρχείο']),

-- Finance & Accounting
('SKILL_ACCOUNTING', 'Accounting', 'Λογιστική', 'technical', 'finance', 'general',
 ARRAY['bookkeeping', 'financial accounting'],
 ARRAY['λογιστικά', 'λογιστήριο']),
('SKILL_PAYROLL', 'Payroll', 'Μισθοδοσία', 'technical', 'finance', 'general',
 ARRAY['payroll processing', 'salary administration'],
 ARRAY['μισθολόγιο', 'πληρωμές προσωπικού']),
('SKILL_TAXATION', 'Taxation', 'Φορολογία', 'technical', 'finance', 'general',
 ARRAY['tax preparation', 'tax filing'],
 ARRAY['φόροι', 'φορολογικά']),
('SKILL_INVOICING', 'Invoicing', 'Τιμολόγηση', 'technical', 'finance', 'general',
 ARRAY['billing', 'invoice processing'],
 ARRAY['έκδοση τιμολογίων', 'χρέωση']),
('SKILL_BUDGETING', 'Budgeting', 'Προϋπολογισμός', 'technical', 'finance', 'general',
 ARRAY['budget planning', 'financial planning'],
 ARRAY['κατάρτιση προϋπολογισμού']),

-- HR & Personnel
('SKILL_HR_MANAGEMENT', 'Human Resources Management', 'Διαχείριση Ανθρώπινου Δυναμικού', 'soft', 'hr', 'general',
 ARRAY['HR', 'personnel management', 'people management'],
 ARRAY['διοίκηση προσωπικού', 'ανθρώπινο δυναμικό']),
('SKILL_RECRUITMENT', 'Recruitment', 'Προσλήψεις', 'soft', 'hr', 'general',
 ARRAY['hiring', 'talent acquisition', 'staffing'],
 ARRAY['στελέχωση', 'επιλογή προσωπικού']),
('SKILL_TRAINING', 'Training & Development', 'Εκπαίδευση', 'soft', 'hr', 'general',
 ARRAY['employee training', 'coaching'],
 ARRAY['κατάρτιση', 'επιμόρφωση']),

-- Communication & Interpersonal
('SKILL_COMMUNICATION', 'Communication Skills', 'Επικοινωνιακές Ικανότητες', 'soft', 'interpersonal', 'general',
 ARRAY['verbal communication', 'written communication'],
 ARRAY['επικοινωνία', 'εκφραστικότητα']),
('SKILL_PRESENTATION', 'Presentation Skills', 'Παρουσιάσεις', 'soft', 'interpersonal', 'general',
 ARRAY['public speaking', 'presenting'],
 ARRAY['παρουσίαση', 'δημόσιος λόγος']),
('SKILL_TEAMWORK', 'Teamwork', 'Ομαδική Εργασία', 'soft', 'interpersonal', 'general',
 ARRAY['team player', 'collaboration', 'cooperation'],
 ARRAY['ομαδικότητα', 'συνεργασία', 'ομαδικό πνεύμα']),

-- Problem Solving & Analytical
('SKILL_PROBLEM_SOLVING', 'Problem Solving', 'Επίλυση Προβλημάτων', 'soft', 'analytical', 'general',
 ARRAY['problem resolution', 'troubleshooting'],
 ARRAY['διαχείριση προβλημάτων', 'αντιμετώπιση προβλημάτων']),
('SKILL_CRITICAL_THINKING', 'Critical Thinking', 'Κριτική Σκέψη', 'soft', 'analytical', 'general',
 ARRAY['analytical thinking', 'logical reasoning'],
 ARRAY['αναλυτική σκέψη', 'λογική']),
('SKILL_DECISION_MAKING', 'Decision Making', 'Λήψη Αποφάσεων', 'soft', 'analytical', 'general',
 ARRAY['decision-making'],
 ARRAY['αποφασιστικότητα']),

-- Management & Leadership
('SKILL_PROJECT_MANAGEMENT', 'Project Management', 'Διαχείριση Έργων', 'soft', 'management', 'general',
 ARRAY['PM', 'project coordination'],
 ARRAY['διοίκηση έργων', 'συντονισμός έργων']),
('SKILL_LEADERSHIP', 'Leadership', 'Ηγετικές Ικανότητες', 'soft', 'management', 'general',
 ARRAY['team leadership', 'people leadership'],
 ARRAY['ηγεσία', 'καθοδήγηση']),
('SKILL_SUPERVISION', 'Supervision', 'Επίβλεψη', 'soft', 'management', 'general',
 ARRAY['supervising', 'oversight'],
 ARRAY['εποπτεία', 'επόπτης']),

-- IT & Technical
('SKILL_COMPUTER_LITERACY', 'Computer Literacy', 'Γνώση Η/Υ', 'technical', 'it', 'general',
 ARRAY['computer skills', 'PC skills', 'IT skills'],
 ARRAY['χειρισμός Η/Υ', 'υπολογιστές']),
('SKILL_INTERNET', 'Internet Skills', 'Χρήση Internet', 'technical', 'it', 'general',
 ARRAY['web browsing', 'online research'],
 ARRAY['διαδίκτυο', 'πλοήγηση']),
('SKILL_SOCIAL_MEDIA', 'Social Media', 'Μέσα Κοινωνικής Δικτύωσης', 'technical', 'it', 'general',
 ARRAY['social networking', 'Facebook', 'Instagram'],
 ARRAY['κοινωνικά δίκτυα']),

-- Languages (as skills)
('SKILL_ENGLISH', 'English Language', 'Αγγλικά', 'language', 'foreign_language', 'general',
 ARRAY['English', 'spoken English', 'written English'],
 ARRAY['αγγλικά', 'αγγλική γλώσσα']),
('SKILL_GERMAN', 'German Language', 'Γερμανικά', 'language', 'foreign_language', 'general',
 ARRAY['German', 'Deutsch'],
 ARRAY['γερμανικά', 'γερμανική γλώσσα']),
('SKILL_FRENCH', 'French Language', 'Γαλλικά', 'language', 'foreign_language', 'general',
 ARRAY['French', 'Français'],
 ARRAY['γαλλικά', 'γαλλική γλώσσα']),
('SKILL_ITALIAN', 'Italian Language', 'Ιταλικά', 'language', 'foreign_language', 'general',
 ARRAY['Italian', 'Italiano'],
 ARRAY['ιταλικά', 'ιταλική γλώσσα']),

-- Driving
('SKILL_DRIVING', 'Driving', 'Οδήγηση', 'technical', 'transportation', 'general',
 ARRAY['driver', 'vehicle operation'],
 ARRAY['οδηγός', 'δίπλωμα οδήγησης'])

ON CONFLICT (canonical_id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 3.2 EXPANDED SOFTWARE TAXONOMY
-- -----------------------------------------------------------------------------

INSERT INTO software_taxonomy (canonical_id, name, vendor, category, subcategory, aliases, versions) VALUES
-- Microsoft Office Suite
('SW_OFFICE_SUITE', 'Microsoft Office Suite', 'Microsoft', 'office', 'productivity_suite',
 ARRAY['MS Office', 'MS Office 2017', 'MS Office 2019', 'MS Office 2021', 'Office 365', 'Microsoft Office'],
 ARRAY['365', '2021', '2019', '2017', '2016', '2013', '2010']),
('SW_POWERPOINT', 'Microsoft PowerPoint', 'Microsoft', 'office', 'presentation',
 ARRAY['PowerPoint', 'PPT'],
 ARRAY['365', '2021', '2019']),
('SW_OUTLOOK', 'Microsoft Outlook', 'Microsoft', 'office', 'email',
 ARRAY['Outlook'],
 ARRAY['365', '2021', '2019']),
('SW_ACCESS', 'Microsoft Access', 'Microsoft', 'office', 'database',
 ARRAY['Access'],
 ARRAY['365', '2021', '2019']),

-- Adobe Creative Suite
('SW_PHOTOSHOP', 'Adobe Photoshop', 'Adobe', 'graphics', 'image_editing',
 ARRAY['Photoshop', 'PS'],
 ARRAY['CC 2024', 'CC 2023', 'CS6']),
('SW_ILLUSTRATOR', 'Adobe Illustrator', 'Adobe', 'graphics', 'vector_graphics',
 ARRAY['Illustrator', 'AI'],
 ARRAY['CC 2024', 'CC 2023']),
('SW_INDESIGN', 'Adobe InDesign', 'Adobe', 'graphics', 'desktop_publishing',
 ARRAY['InDesign'],
 ARRAY['CC 2024', 'CC 2023']),
('SW_ACROBAT', 'Adobe Acrobat', 'Adobe', 'office', 'pdf',
 ARRAY['Acrobat', 'Adobe Reader', 'PDF Reader'],
 ARRAY['DC', 'Pro', 'Reader']),
('SW_PREMIERE', 'Adobe Premiere Pro', 'Adobe', 'graphics', 'video_editing',
 ARRAY['Premiere'],
 ARRAY['CC 2024', 'CC 2023']),

-- Web Browsers
('SW_CHROME', 'Google Chrome', 'Google', 'browser', 'web_browser',
 ARRAY['Chrome'],
 ARRAY[]::TEXT[]),
('SW_FIREFOX', 'Mozilla Firefox', 'Mozilla', 'browser', 'web_browser',
 ARRAY['Firefox'],
 ARRAY[]::TEXT[]),
('SW_EDGE', 'Microsoft Edge', 'Microsoft', 'browser', 'web_browser',
 ARRAY['Edge'],
 ARRAY[]::TEXT[]),
('SW_IE', 'Internet Explorer', 'Microsoft', 'browser', 'web_browser',
 ARRAY['IE', 'Internet Explorer'],
 ARRAY['11', '10', '9']),

-- Accounting Software
('SW_SOFTONE', 'Soft1 ERP', 'SoftOne', 'erp', 'accounting',
 ARRAY['Soft1', 'SoftOne'],
 ARRAY[]::TEXT[]),
('SW_ENTERSOFT', 'Entersoft Business Suite', 'Entersoft', 'erp', 'accounting',
 ARRAY['Entersoft'],
 ARRAY[]::TEXT[]),
('SW_SINGULAR', 'Singular Logic', 'SingularLogic', 'erp', 'accounting',
 ARRAY['Singular', 'Galaxy', 'Control'],
 ARRAY[]::TEXT[]),
('SW_QUICKBOOKS', 'QuickBooks', 'Intuit', 'accounting', 'small_business',
 ARRAY['QB'],
 ARRAY['Online', 'Desktop']),

-- Communication
('SW_TEAMS', 'Microsoft Teams', 'Microsoft', 'communication', 'collaboration',
 ARRAY['Teams'],
 ARRAY[]::TEXT[]),
('SW_ZOOM', 'Zoom', 'Zoom', 'communication', 'video_conferencing',
 ARRAY['Zoom Meetings'],
 ARRAY[]::TEXT[]),
('SW_SKYPE', 'Skype', 'Microsoft', 'communication', 'video_conferencing',
 ARRAY['Skype for Business'],
 ARRAY[]::TEXT[]),

-- Project Management
('SW_TRELLO', 'Trello', 'Atlassian', 'project_management', 'task_management',
 ARRAY[]::TEXT[],
 ARRAY[]::TEXT[]),
('SW_ASANA', 'Asana', 'Asana', 'project_management', 'task_management',
 ARRAY[]::TEXT[],
 ARRAY[]::TEXT[]),
('SW_JIRA', 'Jira', 'Atlassian', 'project_management', 'issue_tracking',
 ARRAY[]::TEXT[],
 ARRAY['Cloud', 'Server']),

-- Other
('SW_GOOGLE_WORKSPACE', 'Google Workspace', 'Google', 'office', 'productivity_suite',
 ARRAY['Google Docs', 'Google Sheets', 'Google Drive', 'G Suite'],
 ARRAY[]::TEXT[]),
('SW_WINDOWS', 'Microsoft Windows', 'Microsoft', 'operating_system', 'desktop',
 ARRAY['Windows'],
 ARRAY['11', '10', '7']),
('SW_LINUX', 'Linux', 'Various', 'operating_system', 'desktop',
 ARRAY['Ubuntu', 'CentOS', 'Debian'],
 ARRAY[]::TEXT[])

ON CONFLICT (canonical_id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 3.3 EXPANDED CERTIFICATION TAXONOMY
-- -----------------------------------------------------------------------------

INSERT INTO certification_taxonomy (canonical_id, name_en, name_el, issuing_organization, category, industry, validity_period_months, renewal_required) VALUES
-- English Language Certifications
('CERT_PROFICIENCY_C2', 'Proficiency in English (C2)', 'Proficiency Αγγλικά (C2)', 'Cambridge / Michigan', 'language', 'general', NULL, false),
('CERT_ADVANCED_C1', 'Certificate of Advanced English (C1)', 'Advanced Αγγλικά (C1)', 'Cambridge', 'language', 'general', NULL, false),
('CERT_FIRST_B2', 'First Certificate in English (B2)', 'First Certificate Αγγλικά (B2)', 'Cambridge', 'language', 'general', NULL, false),
('CERT_LOWER_B1', 'Lower Certificate (B1)', 'Lower Αγγλικά (B1)', 'Cambridge / Michigan', 'language', 'general', NULL, false),
('CERT_IELTS', 'IELTS', 'IELTS', 'British Council', 'language', 'general', 24, true),
('CERT_TOEFL', 'TOEFL', 'TOEFL', 'ETS', 'language', 'general', 24, true),
('CERT_TOEIC', 'TOEIC', 'TOEIC', 'ETS', 'language', 'general', 24, true),

-- German Language Certifications
('CERT_GOETHE_C2', 'Goethe-Zertifikat C2', 'Goethe C2 Γερμανικά', 'Goethe Institut', 'language', 'general', NULL, false),
('CERT_GOETHE_C1', 'Goethe-Zertifikat C1', 'Goethe C1 Γερμανικά', 'Goethe Institut', 'language', 'general', NULL, false),
('CERT_GOETHE_B2', 'Goethe-Zertifikat B2', 'Goethe B2 Γερμανικά', 'Goethe Institut', 'language', 'general', NULL, false),
('CERT_GOETHE_B1', 'Goethe-Zertifikat B1', 'Goethe B1 Γερμανικά', 'Goethe Institut', 'language', 'general', NULL, false),

-- French Language Certifications
('CERT_DELF_B2', 'DELF B2', 'DELF B2 Γαλλικά', 'Ministère de l''Éducation nationale', 'language', 'general', NULL, false),
('CERT_DALF_C1', 'DALF C1', 'DALF C1 Γαλλικά', 'Ministère de l''Éducation nationale', 'language', 'general', NULL, false),
('CERT_SORBONNE_B2', 'Sorbonne B2', 'Sorbonne B2 Γαλλικά', 'Université Paris-Sorbonne', 'language', 'general', NULL, false),

-- Italian Language Certifications
('CERT_CELI_B2', 'CELI 3 (B2)', 'CELI 3 Ιταλικά (B2)', 'Università per Stranieri di Perugia', 'language', 'general', NULL, false),

-- Computer Certifications
('CERT_ECDL', 'ECDL/ICDL', 'ECDL/ICDL', 'ECDL Foundation', 'it', 'general', NULL, false),
('CERT_MOS', 'Microsoft Office Specialist', 'Microsoft Office Specialist', 'Microsoft', 'it', 'general', NULL, false),
('CERT_MCSE', 'Microsoft Certified Solutions Expert', 'MCSE', 'Microsoft', 'it', 'general', 36, true),
('CERT_COMPTIA_A', 'CompTIA A+', 'CompTIA A+', 'CompTIA', 'it', 'general', 36, true),

-- Accounting Certifications
('CERT_ACCOUNTANT', 'Certified Accountant', 'Πιστοποιημένος Λογιστής', 'ΟΕΕ', 'accounting', 'general', NULL, false),
('CERT_TAX_ACCOUNTANT', 'Tax Accountant License', 'Άδεια Φοροτεχνικού', 'ΟΕΕ', 'accounting', 'general', NULL, false),

-- Healthcare Certifications
('CERT_BLS', 'Basic Life Support (BLS)', 'Βασική Υποστήριξη Ζωής', 'AHA / ERC', 'healthcare', 'general', 24, true),
('CERT_AED', 'AED Certification', 'Πιστοποίηση AED', 'Various', 'healthcare', 'general', 24, true),

-- Project Management
('CERT_PMP', 'Project Management Professional', 'PMP', 'PMI', 'project_management', 'general', 36, true),
('CERT_PRINCE2', 'PRINCE2', 'PRINCE2', 'Axelos', 'project_management', 'general', NULL, false),
('CERT_SCRUM', 'Certified Scrum Master', 'Scrum Master', 'Scrum Alliance', 'project_management', 'general', 24, true),

-- HR Certifications
('CERT_SHRM', 'SHRM Certified Professional', 'SHRM-CP', 'SHRM', 'hr', 'general', 36, true),

-- Driver's Licenses (as certifications)
('CERT_DRIVER_B', 'Driver License Category B', 'Δίπλωμα Οδήγησης Β', 'Ministry of Transport', 'driving', 'general', NULL, false),
('CERT_DRIVER_C', 'Driver License Category C', 'Δίπλωμα Οδήγησης Γ', 'Ministry of Transport', 'driving', 'general', NULL, false),
('CERT_DRIVER_D', 'Driver License Category D', 'Δίπλωμα Οδήγησης Δ', 'Ministry of Transport', 'driving', 'general', NULL, false),
('CERT_ADR', 'ADR Certificate', 'Πιστοποιητικό ADR', 'Ministry of Transport', 'driving', 'general', 60, true)

ON CONFLICT (canonical_id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 3.4 EXPANDED ROLE TAXONOMY
-- -----------------------------------------------------------------------------

INSERT INTO role_taxonomy (canonical_id, name_en, name_el, category, department, experience_level, typical_experience_years_min, typical_experience_years_max) VALUES
-- Administrative
('ROLE_SECRETARY', 'Secretary', 'Γραμματέας', 'administrative', 'Administration', 'entry', 0, 3),
('ROLE_EXEC_SECRETARY', 'Executive Secretary', 'Γραμματέας Διεύθυνσης', 'administrative', 'Administration', 'mid', 2, 5),
('ROLE_RECEPTIONIST', 'Receptionist', 'Υπάλληλος Υποδοχής', 'administrative', 'Administration', 'entry', 0, 2),
('ROLE_OFFICE_MANAGER', 'Office Manager', 'Υπεύθυνος Γραφείου', 'administrative', 'Administration', 'mid', 3, 7),
('ROLE_ADMIN_ASSISTANT', 'Administrative Assistant', 'Διοικητικός Βοηθός', 'administrative', 'Administration', 'entry', 0, 3),

-- Finance & Accounting
('ROLE_ACCOUNTANT', 'Accountant', 'Λογιστής', 'finance', 'Finance', 'mid', 2, 5),
('ROLE_CHIEF_ACCOUNTANT', 'Chief Accountant', 'Προϊστάμενος Λογιστηρίου', 'finance', 'Finance', 'senior', 5, 10),
('ROLE_PAYROLL_CLERK', 'Payroll Clerk', 'Υπάλληλος Μισθοδοσίας', 'finance', 'Finance', 'entry', 1, 3),
('ROLE_FINANCIAL_ANALYST', 'Financial Analyst', 'Χρηματοοικονομικός Αναλυτής', 'finance', 'Finance', 'mid', 2, 5),
('ROLE_CASHIER', 'Cashier', 'Ταμίας', 'finance', 'Finance', 'entry', 0, 2),

-- Sales & Marketing
('ROLE_SALES_REP', 'Sales Representative', 'Πωλητής', 'sales', 'Sales', 'entry', 0, 3),
('ROLE_SALES_MANAGER', 'Sales Manager', 'Διευθυντής Πωλήσεων', 'sales', 'Sales', 'senior', 5, 10),
('ROLE_ACCOUNT_MANAGER', 'Account Manager', 'Υπεύθυνος Λογαριασμών', 'sales', 'Sales', 'mid', 2, 5),
('ROLE_MARKETING_SPECIALIST', 'Marketing Specialist', 'Ειδικός Μάρκετινγκ', 'marketing', 'Marketing', 'mid', 2, 5),
('ROLE_MARKETING_MANAGER', 'Marketing Manager', 'Διευθυντής Μάρκετινγκ', 'marketing', 'Marketing', 'senior', 5, 10),

-- Human Resources
('ROLE_HR_OFFICER', 'HR Officer', 'Υπεύθυνος Ανθρώπινου Δυναμικού', 'hr', 'Human Resources', 'mid', 2, 5),
('ROLE_HR_MANAGER', 'HR Manager', 'Διευθυντής Ανθρώπινου Δυναμικού', 'hr', 'Human Resources', 'senior', 5, 10),
('ROLE_RECRUITER', 'Recruiter', 'Υπεύθυνος Προσλήψεων', 'hr', 'Human Resources', 'mid', 2, 5),
('ROLE_TRAINING_COORDINATOR', 'Training Coordinator', 'Συντονιστής Εκπαίδευσης', 'hr', 'Human Resources', 'mid', 2, 5),

-- Customer Service
('ROLE_CUSTOMER_SERVICE_REP', 'Customer Service Representative', 'Υπάλληλος Εξυπηρέτησης Πελατών', 'customer_service', 'Customer Service', 'entry', 0, 2),
('ROLE_CALL_CENTER_AGENT', 'Call Center Agent', 'Υπάλληλος Τηλεφωνικού Κέντρου', 'customer_service', 'Customer Service', 'entry', 0, 2),
('ROLE_CUSTOMER_SERVICE_MANAGER', 'Customer Service Manager', 'Διευθυντής Εξυπηρέτησης Πελατών', 'customer_service', 'Customer Service', 'senior', 5, 10),

-- IT
('ROLE_IT_SUPPORT', 'IT Support Technician', 'Τεχνικός Υποστήριξης IT', 'it', 'IT', 'entry', 0, 3),
('ROLE_SYSTEM_ADMIN', 'System Administrator', 'Διαχειριστής Συστημάτων', 'it', 'IT', 'mid', 2, 5),
('ROLE_SOFTWARE_DEVELOPER', 'Software Developer', 'Προγραμματιστής', 'it', 'IT', 'mid', 2, 5),
('ROLE_DATA_ANALYST', 'Data Analyst', 'Αναλυτής Δεδομένων', 'it', 'IT', 'mid', 2, 5),

-- Operations & Logistics
('ROLE_LOGISTICS_COORDINATOR', 'Logistics Coordinator', 'Συντονιστής Logistics', 'logistics', 'Logistics', 'mid', 2, 5),
('ROLE_SUPPLY_CHAIN_MANAGER', 'Supply Chain Manager', 'Διευθυντής Εφοδιαστικής Αλυσίδας', 'logistics', 'Logistics', 'senior', 5, 10),
('ROLE_PROCUREMENT_OFFICER', 'Procurement Officer', 'Υπεύθυνος Προμηθειών', 'logistics', 'Procurement', 'mid', 2, 5),
('ROLE_WAREHOUSE_MANAGER', 'Warehouse Manager', 'Διευθυντής Αποθήκης', 'logistics', 'Warehouse', 'senior', 5, 10),

-- General
('ROLE_GENERAL_MANAGER', 'General Manager', 'Γενικός Διευθυντής', 'management', 'Management', 'executive', 10, 20),
('ROLE_OPERATIONS_MANAGER', 'Operations Manager', 'Διευθυντής Λειτουργιών', 'management', 'Operations', 'senior', 5, 10),
('ROLE_PROJECT_MANAGER', 'Project Manager', 'Διευθυντής Έργου', 'management', 'Project Management', 'senior', 5, 10),
('ROLE_CONSULTANT', 'Consultant', 'Σύμβουλος', 'consulting', 'Consulting', 'mid', 3, 7),
('ROLE_INTERN', 'Intern', 'Ασκούμενος', 'general', 'Various', 'entry', 0, 1),
('ROLE_TRAINEE', 'Trainee', 'Εκπαιδευόμενος', 'general', 'Various', 'entry', 0, 1)

ON CONFLICT (canonical_id) DO NOTHING;

-- =============================================================================
-- PART 4: UPDATE EXISTING ENTRIES WITH FUZZY ALIASES
-- =============================================================================

-- Update MS Office skill with common variations
UPDATE skill_taxonomy
SET fuzzy_aliases = ARRAY['ms office', 'msoffice', 'microsoft office suite', 'office suite', 'ms office 2017', 'ms office 2019', 'ms office 2021']
WHERE canonical_id = 'SKILL_MS_OFFICE';

-- Update AutoCAD skill with variations
UPDATE skill_taxonomy
SET fuzzy_aliases = ARRAY['auto cad', 'autocad 2d', 'autocad 3d', 'cad drawing']
WHERE canonical_id = 'SKILL_AUTOCAD';

-- Update SAP skill with variations
UPDATE skill_taxonomy
SET fuzzy_aliases = ARRAY['sap erp', 'sap r/3', 'sap hana', 'sap s4hana', 'sap system']
WHERE canonical_id = 'SKILL_SAP';

-- =============================================================================
-- PART 5: VERIFICATION QUERIES
-- =============================================================================

-- Comment out for production, uncomment to verify
/*
SELECT 'skill_taxonomy' as table_name, COUNT(*) as count FROM skill_taxonomy
UNION ALL
SELECT 'certification_taxonomy', COUNT(*) FROM certification_taxonomy
UNION ALL
SELECT 'role_taxonomy', COUNT(*) FROM role_taxonomy
UNION ALL
SELECT 'software_taxonomy', COUNT(*) FROM software_taxonomy;
*/

-- =============================================================================
-- MIGRATION COMPLETE
-- =============================================================================
COMMENT ON SCHEMA public IS 'Task 1.4 Taxonomy Enhancement completed - Session 32';
