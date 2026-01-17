-- =============================================================================
-- LCMGoCloud-CAGenAI - Initial Data
-- =============================================================================
-- Skills taxonomy, soft skills, certifications, system config
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Technical Skills - Manufacturing Domain
-- -----------------------------------------------------------------------------
INSERT INTO skill_taxonomy (canonical_id, name_en, name_el, category, subcategory, domain, aliases_en, aliases_el) VALUES
-- Welding
('SKILL_WELDING_TIG', 'TIG Welding', 'Συγκόλληση TIG', 'technical', 'welding', 'manufacturing', ARRAY['GTAW', 'argon welding', 'tungsten inert gas'], ARRAY['συγκόλληση αργκόν', 'συγκόλληση βολφραμίου']),
('SKILL_WELDING_MIG', 'MIG Welding', 'Συγκόλληση MIG', 'technical', 'welding', 'manufacturing', ARRAY['GMAW', 'MAG welding', 'wire welding'], ARRAY['συγκόλληση MAG', 'συγκόλληση σύρματος']),
('SKILL_WELDING_STICK', 'Stick Welding', 'Ηλεκτροσυγκόλληση', 'technical', 'welding', 'manufacturing', ARRAY['SMAW', 'arc welding', 'manual metal arc'], ARRAY['ηλεκτροκόλληση', 'συγκόλληση τόξου']),
('SKILL_WELDING_SPOT', 'Spot Welding', 'Συγκόλληση Σημείου', 'technical', 'welding', 'manufacturing', ARRAY['resistance welding'], ARRAY['πονταρισμα']),

-- CNC & Machining
('SKILL_CNC_OPERATION', 'CNC Operation', 'Χειρισμός CNC', 'technical', 'machining', 'manufacturing', ARRAY['CNC machinist', 'CNC operator'], ARRAY['χειριστής CNC', 'τορναδόρος CNC']),
('SKILL_CNC_PROGRAMMING', 'CNC Programming', 'Προγραμματισμός CNC', 'technical', 'machining', 'manufacturing', ARRAY['G-code', 'NC programming'], ARRAY['προγραμματισμός κέντρων']),
('SKILL_LATHE', 'Lathe Operation', 'Τόρνευση', 'technical', 'machining', 'manufacturing', ARRAY['turning', 'lathe work'], ARRAY['τορναδόρος', 'τόρνος']),
('SKILL_MILLING', 'Milling', 'Φρεζάρισμα', 'technical', 'machining', 'manufacturing', ARRAY['milling machine', 'vertical milling'], ARRAY['φρέζα', 'κοπτικά']),

-- Aluminium Specific
('SKILL_EXTRUSION', 'Aluminium Extrusion', 'Διέλαση Αλουμινίου', 'technical', 'metal_forming', 'manufacturing', ARRAY['extrusion operator', 'press operator'], ARRAY['χειριστής πρέσας', 'διέλαση']),
('SKILL_ANODIZING', 'Anodizing', 'Ανοδίωση', 'technical', 'surface_treatment', 'manufacturing', ARRAY['anodization', 'surface treatment'], ARRAY['ηλεκτροχρωματισμός']),
('SKILL_POWDER_COATING', 'Powder Coating', 'Ηλεκτροστατική Βαφή', 'technical', 'surface_treatment', 'manufacturing', ARRAY['electrostatic painting'], ARRAY['βαφή πούδρας', 'ηλεκτροστατικό']),

-- Quality & Inspection
('SKILL_QUALITY_INSPECTION', 'Quality Inspection', 'Έλεγχος Ποιότητας', 'technical', 'quality', 'manufacturing', ARRAY['QC', 'quality control', 'inspection'], ARRAY['ποιοτικός έλεγχος', 'QC']),
('SKILL_DIMENSIONAL_INSPECTION', 'Dimensional Inspection', 'Διαστασιακός Έλεγχος', 'technical', 'quality', 'manufacturing', ARRAY['metrology', 'measuring'], ARRAY['μετρολογία']),
('SKILL_BLUEPRINT_READING', 'Blueprint Reading', 'Ανάγνωση Σχεδίων', 'technical', 'design', 'manufacturing', ARRAY['technical drawings', 'engineering drawings'], ARRAY['τεχνικά σχέδια', 'ανάγνωση σχεδίων']),

-- Maintenance
('SKILL_INDUSTRIAL_MAINTENANCE', 'Industrial Maintenance', 'Βιομηχανική Συντήρηση', 'technical', 'maintenance', 'manufacturing', ARRAY['equipment maintenance', 'machine maintenance'], ARRAY['συντήρηση μηχανημάτων']),
('SKILL_ELECTRICAL_MAINTENANCE', 'Electrical Maintenance', 'Ηλεκτρολογική Συντήρηση', 'technical', 'maintenance', 'manufacturing', ARRAY['electrical repairs'], ARRAY['ηλεκτρολογικές επισκευές']),
('SKILL_HYDRAULICS', 'Hydraulics', 'Υδραυλικά', 'technical', 'maintenance', 'manufacturing', ARRAY['hydraulic systems'], ARRAY['υδραυλικά συστήματα']),
('SKILL_PNEUMATICS', 'Pneumatics', 'Πνευματικά', 'technical', 'maintenance', 'manufacturing', ARRAY['pneumatic systems'], ARRAY['πνευματικά συστήματα']),

-- Safety
('SKILL_WORKPLACE_SAFETY', 'Workplace Safety', 'Ασφάλεια Εργασίας', 'technical', 'safety', 'manufacturing', ARRAY['OHS', 'health and safety'], ARRAY['υγεία και ασφάλεια', 'ΥΑΕ']),
('SKILL_FORKLIFT', 'Forklift Operation', 'Χειρισμός Περονοφόρου', 'technical', 'logistics', 'manufacturing', ARRAY['forklift driver', 'lift truck'], ARRAY['κλαρκ', 'ανυψωτικό']),

-- Software/Tools
('SKILL_AUTOCAD', 'AutoCAD', 'AutoCAD', 'tool', 'cad', 'manufacturing', ARRAY['CAD', 'drafting'], ARRAY['σχεδίαση CAD']),
('SKILL_SOLIDWORKS', 'SolidWorks', 'SolidWorks', 'tool', 'cad', 'manufacturing', ARRAY['3D CAD'], ARRAY['3D σχεδίαση']),
('SKILL_SAP', 'SAP', 'SAP', 'tool', 'erp', 'business', ARRAY['SAP ERP'], ARRAY['σύστημα SAP']),
('SKILL_MS_OFFICE', 'Microsoft Office', 'Microsoft Office', 'tool', 'office', 'business', ARRAY['Excel', 'Word', 'Office Suite'], ARRAY['οφις']);

-- -----------------------------------------------------------------------------
-- Soft Skills
-- -----------------------------------------------------------------------------
INSERT INTO soft_skill_taxonomy (canonical_id, name_en, name_el, category, aliases_en, aliases_el, behavioral_indicators) VALUES
('SOFT_TEAMWORK', 'Teamwork', 'Ομαδικότητα', 'interpersonal', ARRAY['team player', 'collaborative', 'cooperation'], ARRAY['ομαδικό πνεύμα', 'συνεργασία'], ARRAY['Works well in groups', 'Supports colleagues', 'Shares knowledge']),
('SOFT_COMMUNICATION', 'Communication', 'Επικοινωνία', 'interpersonal', ARRAY['communicator', 'verbal skills'], ARRAY['επικοινωνιακές ικανότητες'], ARRAY['Clear verbal expression', 'Active listening', 'Written communication']),
('SOFT_LEADERSHIP', 'Leadership', 'Ηγεσία', 'leadership', ARRAY['leader', 'management', 'supervisory'], ARRAY['ηγετικές ικανότητες', 'διοίκηση'], ARRAY['Motivates others', 'Takes initiative', 'Delegates effectively']),
('SOFT_PROBLEM_SOLVING', 'Problem Solving', 'Επίλυση Προβλημάτων', 'cognitive', ARRAY['analytical', 'critical thinking'], ARRAY['αναλυτική σκέψη', 'κριτική σκέψη'], ARRAY['Identifies root causes', 'Proposes solutions', 'Logical reasoning']),
('SOFT_TIME_MANAGEMENT', 'Time Management', 'Διαχείριση Χρόνου', 'organizational', ARRAY['punctual', 'deadline-oriented'], ARRAY['συνέπεια', 'οργάνωση'], ARRAY['Meets deadlines', 'Prioritizes tasks', 'Efficient work']),
('SOFT_ADAPTABILITY', 'Adaptability', 'Προσαρμοστικότητα', 'personal', ARRAY['flexible', 'versatile'], ARRAY['ευελιξία', 'ευπροσάρμοστος'], ARRAY['Handles change well', 'Learns quickly', 'Open to new methods']),
('SOFT_ATTENTION_TO_DETAIL', 'Attention to Detail', 'Προσοχή στη Λεπτομέρεια', 'cognitive', ARRAY['meticulous', 'thorough', 'detail-oriented'], ARRAY['σχολαστικότητα', 'λεπτομερής'], ARRAY['Catches errors', 'Quality focused', 'Precise work']),
('SOFT_STRESS_MANAGEMENT', 'Stress Management', 'Διαχείριση Άγχους', 'personal', ARRAY['works under pressure', 'calm'], ARRAY['ψυχραιμία', 'αντοχή σε πίεση'], ARRAY['Stays calm under pressure', 'Meets tight deadlines', 'Resilient']);

-- -----------------------------------------------------------------------------
-- Role Taxonomy - Manufacturing
-- -----------------------------------------------------------------------------
INSERT INTO role_taxonomy (canonical_id, name_en, name_el, category, department, experience_level, typical_experience_years_min, typical_experience_years_max) VALUES
('ROLE_CNC_OPERATOR', 'CNC Operator', 'Χειριστής CNC', 'production', 'Manufacturing', 'mid', 2, 5),
('ROLE_CNC_PROGRAMMER', 'CNC Programmer', 'Προγραμματιστής CNC', 'production', 'Manufacturing', 'senior', 5, 10),
('ROLE_WELDER', 'Welder', 'Συγκολλητής', 'production', 'Manufacturing', 'mid', 2, 8),
('ROLE_QUALITY_INSPECTOR', 'Quality Inspector', 'Ελεγκτής Ποιότητας', 'quality', 'Quality Control', 'mid', 2, 5),
('ROLE_MAINTENANCE_TECH', 'Maintenance Technician', 'Τεχνικός Συντήρησης', 'maintenance', 'Maintenance', 'mid', 3, 7),
('ROLE_PRODUCTION_SUPERVISOR', 'Production Supervisor', 'Επόπτης Παραγωγής', 'management', 'Manufacturing', 'lead', 5, 10),
('ROLE_EXTRUSION_OPERATOR', 'Extrusion Operator', 'Χειριστής Διέλασης', 'production', 'Manufacturing', 'mid', 2, 5),
('ROLE_ANODIZER', 'Anodizer', 'Τεχνικός Ανοδίωσης', 'production', 'Surface Treatment', 'mid', 2, 5),
('ROLE_WAREHOUSE_WORKER', 'Warehouse Worker', 'Εργάτης Αποθήκης', 'logistics', 'Warehouse', 'entry', 0, 2),
('ROLE_FORKLIFT_OPERATOR', 'Forklift Operator', 'Χειριστής Περονοφόρου', 'logistics', 'Warehouse', 'entry', 1, 3),
('ROLE_INDUSTRIAL_ELECTRICIAN', 'Industrial Electrician', 'Βιομηχανικός Ηλεκτρολόγος', 'maintenance', 'Maintenance', 'mid', 3, 8);

-- -----------------------------------------------------------------------------
-- Certification Taxonomy
-- -----------------------------------------------------------------------------
INSERT INTO certification_taxonomy (canonical_id, name_en, name_el, issuing_organization, category, industry, validity_period_months, renewal_required) VALUES
('CERT_WELDING_EN_287', 'EN 287 Welder Qualification', 'Πιστοποίηση Συγκολλητή EN 287', 'TÜV / Lloyd''s', 'welding', 'manufacturing', 24, true),
('CERT_ISO_9001_AUDITOR', 'ISO 9001 Internal Auditor', 'Εσωτερικός Επιθεωρητής ISO 9001', 'TÜV / Bureau Veritas', 'quality', 'general', 36, true),
('CERT_FORKLIFT', 'Forklift License', 'Άδεια Χειριστή Περονοφόρου', 'ΟΑΕΔ / Ιδιωτικό Κέντρο', 'safety', 'logistics', 60, true),
('CERT_FIRST_AID', 'First Aid Certificate', 'Πιστοποίηση Πρώτων Βοηθειών', 'Red Cross / ΕΚΑΒ', 'safety', 'general', 24, true),
('CERT_ELECTRICAL_A', 'Electrician License A', 'Άδεια Ηλεκτρολόγου Α', 'Υπουργείο Ανάπτυξης', 'electrical', 'manufacturing', NULL, false),
('CERT_FIRE_SAFETY', 'Fire Safety Certificate', 'Πιστοποίηση Πυρασφάλειας', 'Fire Department', 'safety', 'general', 12, true),
('CERT_CRANE_OPERATOR', 'Crane Operator License', 'Άδεια Χειριστή Γερανού', 'ΟΑΕΔ / Ιδιωτικό Κέντρο', 'safety', 'manufacturing', 60, true);

-- -----------------------------------------------------------------------------
-- Software Taxonomy
-- -----------------------------------------------------------------------------
INSERT INTO software_taxonomy (canonical_id, name, vendor, category, subcategory, aliases, versions) VALUES
('SW_AUTOCAD', 'AutoCAD', 'Autodesk', 'cad', '2d_cad', ARRAY['ACAD'], ARRAY['2023', '2024', 'LT']),
('SW_SOLIDWORKS', 'SolidWorks', 'Dassault Systèmes', 'cad', '3d_cad', ARRAY['SW'], ARRAY['2023', '2024']),
('SW_SAP_ERP', 'SAP ERP', 'SAP', 'erp', 'enterprise', ARRAY['SAP', 'SAP R/3'], ARRAY['S/4HANA', 'ECC']),
('SW_EXCEL', 'Microsoft Excel', 'Microsoft', 'office', 'spreadsheet', ARRAY['Excel'], ARRAY['365', '2021', '2019']),
('SW_WORD', 'Microsoft Word', 'Microsoft', 'office', 'word_processor', ARRAY['Word'], ARRAY['365', '2021', '2019']);

-- -----------------------------------------------------------------------------
-- System Configuration
-- -----------------------------------------------------------------------------
INSERT INTO system_config (key, value, description) VALUES
('schema_version', '"4.0"', 'Database schema version'),
('greek_regions', '[
    {"code": "ATT", "name_en": "Attica", "name_el": "Αττική"},
    {"code": "CMC", "name_en": "Central Macedonia", "name_el": "Κεντρική Μακεδονία"},
    {"code": "WMC", "name_en": "Western Macedonia", "name_el": "Δυτική Μακεδονία"},
    {"code": "EMC", "name_en": "Eastern Macedonia and Thrace", "name_el": "Ανατολική Μακεδονία και Θράκη"},
    {"code": "EPI", "name_en": "Epirus", "name_el": "Ήπειρος"},
    {"code": "THE", "name_en": "Thessaly", "name_el": "Θεσσαλία"},
    {"code": "ION", "name_en": "Ionian Islands", "name_el": "Ιόνια Νησιά"},
    {"code": "WGR", "name_en": "Western Greece", "name_el": "Δυτική Ελλάδα"},
    {"code": "CGR", "name_en": "Central Greece", "name_el": "Στερεά Ελλάδα"},
    {"code": "PEL", "name_en": "Peloponnese", "name_el": "Πελοπόννησος"},
    {"code": "NAE", "name_en": "North Aegean", "name_el": "Βόρειο Αιγαίο"},
    {"code": "SAE", "name_en": "South Aegean", "name_el": "Νότιο Αιγαίο"},
    {"code": "CRE", "name_en": "Crete", "name_el": "Κρήτη"}
]', 'Greek administrative regions'),
('cv_processing_config', '{
    "max_file_size_mb": 10,
    "allowed_extensions": ["pdf", "doc", "docx"],
    "ocr_confidence_threshold": 0.7,
    "duplicate_threshold": 0.85
}', 'CV processing configuration'),
('query_router_config', '{
    "confidence_threshold": 0.7,
    "max_results_default": 20,
    "enable_greeklish_detection": true
}', 'Query router configuration'),
('gdpr_config', '{
    "default_consent_expiry_days": 730,
    "data_retention_days": 1095,
    "dsr_response_days": 30
}', 'GDPR compliance configuration');

-- -----------------------------------------------------------------------------
-- Data Retention Policies
-- -----------------------------------------------------------------------------
INSERT INTO data_retention_policies (name, description, data_type, retention_days, action) VALUES
('Inactive Candidates', 'Archive candidates with no activity for 2 years', 'candidate', 730, 'archive'),
('Query History', 'Delete query history older than 1 year', 'query_history', 365, 'delete'),
('Audit Logs', 'Archive audit logs older than 3 years', 'audit_log', 1095, 'archive'),
('Expired Consents', 'Anonymize data for expired consents', 'consent', 30, 'anonymize');
