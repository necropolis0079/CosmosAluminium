-- Migration: 021_comprehensive_taxonomy.sql
-- Description: Comprehensive taxonomy for manufacturing/aluminum company
-- Covers 11 departments with roles, skills, certifications, and software
-- Date: 2026-01-20

-- ============================================================================
-- PART 1: ROLE TAXONOMY
-- ============================================================================

-- 1. Διοίκηση & Στρατηγική (Management & Strategy)
INSERT INTO role_taxonomy (canonical_id, name_el, name_en, category, department) VALUES
('ROLE_CEO', 'Διευθύνων Σύμβουλος', 'Chief Executive Officer (CEO)', 'management', 'executive'),
('ROLE_GENERAL_MANAGER', 'Γενικός Διευθυντής', 'General Manager', 'management', 'executive'),
('ROLE_MANAGING_DIRECTOR', 'Διευθύνων Εταίρος', 'Managing Director', 'management', 'executive'),
('ROLE_COO', 'Διευθυντής Λειτουργιών', 'Chief Operating Officer (COO)', 'management', 'executive'),
('ROLE_STRATEGY_DIRECTOR', 'Διευθυντής Στρατηγικής', 'Strategy Director', 'management', 'strategy'),
('ROLE_BIZ_DEV_MANAGER', 'Διευθυντής Επιχειρηματικής Ανάπτυξης', 'Business Development Manager', 'management', 'business_development'),
('ROLE_BIZ_DEV_EXECUTIVE', 'Στέλεχος Επιχειρηματικής Ανάπτυξης', 'Business Development Executive', 'management', 'business_development'),
('ROLE_BOARD_SECRETARY', 'Γραμματέας ΔΣ', 'Board Secretary', 'management', 'executive'),
('ROLE_CORP_GOVERNANCE', 'Υπεύθυνος Εταιρικής Διακυβέρνησης', 'Corporate Governance Officer', 'management', 'compliance'),
('ROLE_INTERNAL_AUDITOR', 'Εσωτερικός Ελεγκτής', 'Internal Auditor', 'audit', 'audit'),
('ROLE_INTERNAL_AUDIT_MGR', 'Διευθυντής Εσωτερικού Ελέγχου', 'Internal Audit Manager', 'audit', 'audit')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, category = EXCLUDED.category, department = EXCLUDED.department;

-- 2. Οικονομικά & Διοικητική Υποστήριξη (Finance & Admin)
INSERT INTO role_taxonomy (canonical_id, name_el, name_en, category, department) VALUES
('ROLE_CFO', 'Οικονομικός Διευθυντής', 'Chief Financial Officer (CFO)', 'finance', 'finance'),
('ROLE_FINANCE_DIRECTOR', 'Διευθυντής Οικονομικών', 'Finance Director', 'finance', 'finance'),
('ROLE_FINANCE_MANAGER', 'Οικονομικός Διευθυντής', 'Finance Manager', 'finance', 'finance'),
('ROLE_ACCOUNTING_MANAGER', 'Προϊστάμενος Λογιστηρίου', 'Accounting Manager', 'finance', 'accounting'),
('ROLE_SENIOR_ACCOUNTANT', 'Λογιστής Α Τάξης', 'Senior Accountant', 'finance', 'accounting'),
('ROLE_ACCOUNTANT', 'Λογιστής', 'Accountant', 'finance', 'accounting'),
('ROLE_ACCOUNTANT_B', 'Λογιστής Β Τάξης', 'Accountant Class B', 'finance', 'accounting'),
('ROLE_ACCOUNTANT_C', 'Λογιστής Γ Τάξης', 'Junior Accountant', 'finance', 'accounting'),
('ROLE_ASSISTANT_ACCOUNTANT', 'Βοηθός Λογιστή', 'Assistant Accountant', 'finance', 'accounting'),
('ROLE_CONTROLLER', 'Controller', 'Controller', 'finance', 'finance'),
('ROLE_COST_ACCOUNTANT', 'Κοστολόγος', 'Cost Accountant', 'finance', 'accounting'),
('ROLE_FINANCIAL_ANALYST', 'Οικονομικός Αναλυτής', 'Financial Analyst', 'finance', 'finance'),
('ROLE_TREASURY_MANAGER', 'Διευθυντής Ταμειακής Διαχείρισης', 'Treasury Manager', 'finance', 'treasury'),
('ROLE_TREASURER', 'Ταμίας', 'Treasurer', 'finance', 'treasury'),
('ROLE_AP_SPECIALIST', 'Υπεύθυνος Πληρωμών Προμηθευτών', 'Accounts Payable Specialist', 'finance', 'accounting'),
('ROLE_AR_SPECIALIST', 'Υπεύθυνος Εισπράξεων', 'Accounts Receivable Specialist', 'finance', 'accounting'),
('ROLE_CREDIT_CONTROLLER', 'Υπεύθυνος Πιστωτικού Ελέγχου', 'Credit Controller', 'finance', 'credit'),
('ROLE_CREDIT_ANALYST', 'Αναλυτής Πιστώσεων', 'Credit Analyst', 'finance', 'credit'),
('ROLE_TAX_SPECIALIST', 'Φορολογικός Σύμβουλος', 'Tax Specialist', 'finance', 'tax'),
('ROLE_PAYROLL_SPECIALIST', 'Υπεύθυνος Μισθοδοσίας', 'Payroll Specialist', 'finance', 'payroll'),
('ROLE_LEGAL_COUNSEL', 'Νομικός Σύμβουλος', 'Legal Counsel', 'legal', 'legal'),
('ROLE_LEGAL_MANAGER', 'Διευθυντής Νομικού Τμήματος', 'Legal Manager', 'legal', 'legal'),
('ROLE_CONTRACTS_SPECIALIST', 'Υπεύθυνος Συμβάσεων', 'Contracts Specialist', 'legal', 'legal'),
('ROLE_ADMIN_MANAGER', 'Διευθυντής Διοικητικών Υπηρεσιών', 'Administrative Manager', 'admin', 'admin'),
('ROLE_OFFICE_MANAGER', 'Υπεύθυνος Γραφείου', 'Office Manager', 'admin', 'admin'),
('ROLE_EXECUTIVE_SECRETARY', 'Εκτελεστική Γραμματέας', 'Executive Secretary', 'admin', 'admin'),
('ROLE_ADMIN_ASSISTANT', 'Διοικητικός Βοηθός', 'Administrative Assistant', 'admin', 'admin'),
('ROLE_RECEPTIONIST', 'Ρεσεψιονίστ', 'Receptionist', 'admin', 'admin'),
('ROLE_FACILITIES_MANAGER', 'Διευθυντής Εγκαταστάσεων', 'Facilities Manager', 'admin', 'facilities')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, category = EXCLUDED.category, department = EXCLUDED.department;

-- 3. Ανθρώπινο Δυναμικό (HR)
INSERT INTO role_taxonomy (canonical_id, name_el, name_en, category, department) VALUES
('ROLE_HR_DIRECTOR', 'Διευθυντής Ανθρώπινου Δυναμικού', 'HR Director', 'hr', 'hr'),
('ROLE_HR_MANAGER', 'Διευθυντής HR', 'HR Manager', 'hr', 'hr'),
('ROLE_HR_BUSINESS_PARTNER', 'HR Business Partner', 'HR Business Partner', 'hr', 'hr'),
('ROLE_HR_GENERALIST', 'HR Generalist', 'HR Generalist', 'hr', 'hr'),
('ROLE_HR_SPECIALIST', 'Στέλεχος Ανθρώπινου Δυναμικού', 'HR Specialist', 'hr', 'hr'),
('ROLE_HR_ASSISTANT', 'Βοηθός Ανθρώπινου Δυναμικού', 'HR Assistant', 'hr', 'hr'),
('ROLE_RECRUITMENT_MANAGER', 'Διευθυντής Προσλήψεων', 'Recruitment Manager', 'hr', 'recruitment'),
('ROLE_RECRUITER', 'Στέλεχος Προσλήψεων', 'Recruiter', 'hr', 'recruitment'),
('ROLE_TALENT_ACQUISITION', 'Υπεύθυνος Απόκτησης Ταλέντων', 'Talent Acquisition Specialist', 'hr', 'recruitment'),
('ROLE_TRAINING_MANAGER', 'Διευθυντής Εκπαίδευσης', 'Training Manager', 'hr', 'training'),
('ROLE_LD_SPECIALIST', 'Υπεύθυνος Εκπαίδευσης & Ανάπτυξης', 'Learning & Development Specialist', 'hr', 'training'),
('ROLE_HS_MANAGER', 'Διευθυντής Υγείας & Ασφάλειας', 'Health & Safety Manager', 'hr', 'health_safety'),
('ROLE_HS_OFFICER', 'Τεχνικός Ασφαλείας', 'Health & Safety Officer', 'hr', 'health_safety'),
('ROLE_EHS_MANAGER', 'Διευθυντής EHS', 'EHS Manager', 'hr', 'health_safety'),
('ROLE_OCCUPATIONAL_DOCTOR', 'Ιατρός Εργασίας', 'Occupational Health Doctor', 'hr', 'health_safety')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, category = EXCLUDED.category, department = EXCLUDED.department;

-- 4. Πωλήσεις & Εμπορική Λειτουργία (Sales & Commercial)
INSERT INTO role_taxonomy (canonical_id, name_el, name_en, category, department) VALUES
('ROLE_SALES_DIRECTOR', 'Εμπορικός Διευθυντής', 'Sales Director', 'sales', 'sales'),
('ROLE_SALES_MANAGER', 'Διευθυντής Πωλήσεων', 'Sales Manager', 'sales', 'sales'),
('ROLE_REGIONAL_SALES_MGR', 'Περιφερειακός Διευθυντής Πωλήσεων', 'Regional Sales Manager', 'sales', 'sales'),
('ROLE_B2B_SALES_MANAGER', 'Διευθυντής Πωλήσεων B2B', 'B2B Sales Manager', 'sales', 'sales'),
('ROLE_EXPORT_MANAGER', 'Διευθυντής Εξαγωγών', 'Export Manager', 'sales', 'export'),
('ROLE_INTERNATIONAL_SALES', 'Στέλεχος Διεθνών Πωλήσεων', 'International Sales Executive', 'sales', 'export'),
('ROLE_KEY_ACCOUNT_MGR', 'Διευθυντής Στρατηγικών Πελατών', 'Key Account Manager', 'sales', 'sales'),
('ROLE_ACCOUNT_MANAGER', 'Υπεύθυνος Λογαριασμών', 'Account Manager', 'sales', 'sales'),
('ROLE_SALES_REPRESENTATIVE', 'Πωλητής', 'Sales Representative', 'sales', 'sales'),
('ROLE_SALES_EXECUTIVE', 'Στέλεχος Πωλήσεων', 'Sales Executive', 'sales', 'sales'),
('ROLE_INSIDE_SALES', 'Στέλεχος Εσωτερικών Πωλήσεων', 'Inside Sales Representative', 'sales', 'sales'),
('ROLE_SALES_SUPPORT', 'Υποστήριξη Πωλήσεων', 'Sales Support', 'sales', 'sales'),
('ROLE_SALES_COORDINATOR', 'Συντονιστής Πωλήσεων', 'Sales Coordinator', 'sales', 'sales'),
('ROLE_COMMERCIAL_ANALYST', 'Εμπορικός Αναλυτής', 'Commercial Analyst', 'sales', 'sales'),
('ROLE_PRICING_ANALYST', 'Αναλυτής Τιμολόγησης', 'Pricing Analyst', 'sales', 'sales'),
('ROLE_TENDER_SPECIALIST', 'Υπεύθυνος Διαγωνισμών', 'Tender Specialist', 'sales', 'sales')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, category = EXCLUDED.category, department = EXCLUDED.department;

-- 5. Marketing & Επικοινωνία
INSERT INTO role_taxonomy (canonical_id, name_el, name_en, category, department) VALUES
('ROLE_CMO', 'Διευθυντής Marketing', 'Chief Marketing Officer (CMO)', 'marketing', 'marketing'),
('ROLE_MARKETING_DIRECTOR', 'Διευθυντής Marketing', 'Marketing Director', 'marketing', 'marketing'),
('ROLE_MARKETING_MANAGER', 'Marketing Manager', 'Marketing Manager', 'marketing', 'marketing'),
('ROLE_BRAND_MANAGER', 'Brand Manager', 'Brand Manager', 'marketing', 'marketing'),
('ROLE_PRODUCT_MANAGER', 'Product Manager', 'Product Manager', 'marketing', 'product'),
('ROLE_DIGITAL_MARKETING_MGR', 'Διευθυντής Digital Marketing', 'Digital Marketing Manager', 'marketing', 'digital_marketing'),
('ROLE_DIGITAL_MARKETING', 'Στέλεχος Digital Marketing', 'Digital Marketing Specialist', 'marketing', 'digital_marketing'),
('ROLE_SOCIAL_MEDIA_MGR', 'Social Media Manager', 'Social Media Manager', 'marketing', 'digital_marketing'),
('ROLE_CONTENT_MANAGER', 'Content Manager', 'Content Manager', 'marketing', 'marketing'),
('ROLE_SEO_SPECIALIST', 'SEO Specialist', 'SEO Specialist', 'marketing', 'digital_marketing'),
('ROLE_MARKETING_COORDINATOR', 'Συντονιστής Marketing', 'Marketing Coordinator', 'marketing', 'marketing'),
('ROLE_EVENTS_MANAGER', 'Υπεύθυνος Εκθέσεων & Εκδηλώσεων', 'Events Manager', 'marketing', 'events'),
('ROLE_PR_MANAGER', 'Υπεύθυνος Δημοσίων Σχέσεων', 'PR Manager', 'marketing', 'communications'),
('ROLE_COMMUNICATIONS_MGR', 'Υπεύθυνος Επικοινωνίας', 'Communications Manager', 'marketing', 'communications'),
('ROLE_GRAPHIC_DESIGNER', 'Γραφίστας', 'Graphic Designer', 'marketing', 'creative'),
('ROLE_TECHNICAL_WRITER', 'Τεχνικός Συγγραφέας', 'Technical Writer', 'marketing', 'creative')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, category = EXCLUDED.category, department = EXCLUDED.department;

-- 6. Παραγωγή (Production/Operations)
INSERT INTO role_taxonomy (canonical_id, name_el, name_en, category, department) VALUES
('ROLE_PLANT_DIRECTOR', 'Διευθυντής Εργοστασίου', 'Plant Director', 'production', 'production'),
('ROLE_PRODUCTION_DIRECTOR', 'Διευθυντής Παραγωγής', 'Production Director', 'production', 'production'),
('ROLE_PRODUCTION_MANAGER', 'Διευθυντής Παραγωγής', 'Production Manager', 'production', 'production'),
('ROLE_OPERATIONS_MANAGER', 'Διευθυντής Λειτουργιών', 'Operations Manager', 'production', 'operations'),
('ROLE_SHIFT_SUPERVISOR', 'Προϊστάμενος Βάρδιας', 'Shift Supervisor', 'production', 'production'),
('ROLE_PRODUCTION_SUPERVISOR', 'Προϊστάμενος Παραγωγής', 'Production Supervisor', 'production', 'production'),
('ROLE_LINE_LEADER', 'Υπεύθυνος Γραμμής Παραγωγής', 'Production Line Leader', 'production', 'production'),
('ROLE_PRODUCTION_PLANNER', 'Προγραμματιστής Παραγωγής', 'Production Planner', 'production', 'planning'),
('ROLE_PLANNING_MANAGER', 'Διευθυντής Προγραμματισμού', 'Planning Manager', 'production', 'planning'),
('ROLE_MACHINE_OPERATOR', 'Χειριστής Μηχανημάτων', 'Machine Operator', 'production', 'production'),
('ROLE_CNC_OPERATOR', 'Χειριστής CNC', 'CNC Operator', 'production', 'production'),
('ROLE_EXTRUSION_OPERATOR', 'Χειριστής Διέλασης', 'Extrusion Operator', 'production', 'extrusion'),
('ROLE_ANODIZING_OPERATOR', 'Χειριστής Ανοδίωσης', 'Anodizing Operator', 'production', 'anodizing'),
('ROLE_PAINTING_OPERATOR', 'Χειριστής Βαφείου', 'Painting/Coating Operator', 'production', 'painting'),
('ROLE_ASSEMBLY_OPERATOR', 'Χειριστής Συναρμολόγησης', 'Assembly Operator', 'production', 'assembly'),
('ROLE_PRODUCTION_TECHNICIAN', 'Τεχνικός Παραγωγής', 'Production Technician', 'production', 'production'),
('ROLE_PRODUCTION_WORKER', 'Εργάτης Παραγωγής', 'Production Worker', 'production', 'production'),
('ROLE_MAINTENANCE_MANAGER', 'Διευθυντής Συντήρησης', 'Maintenance Manager', 'production', 'maintenance'),
('ROLE_MAINTENANCE_SUPERVISOR', 'Προϊστάμενος Συντήρησης', 'Maintenance Supervisor', 'production', 'maintenance'),
('ROLE_MAINTENANCE_TECHNICIAN', 'Τεχνικός Συντήρησης', 'Maintenance Technician', 'production', 'maintenance'),
('ROLE_ELECTRICIAN', 'Ηλεκτρολόγος', 'Electrician', 'production', 'maintenance'),
('ROLE_MECHANIC', 'Μηχανικός Συντήρησης', 'Mechanic', 'production', 'maintenance'),
('ROLE_INDUSTRIAL_ENGINEER', 'Βιομηχανικός Μηχανικός', 'Industrial Engineer', 'production', 'engineering'),
('ROLE_PROCESS_ENGINEER', 'Μηχανικός Διεργασιών', 'Process Engineer', 'production', 'engineering'),
('ROLE_LEAN_SPECIALIST', 'Ειδικός Lean Manufacturing', 'Lean Specialist', 'production', 'continuous_improvement'),
('ROLE_CI_MANAGER', 'Διευθυντής Συνεχούς Βελτίωσης', 'Continuous Improvement Manager', 'production', 'continuous_improvement'),
('ROLE_ENERGY_MANAGER', 'Διευθυντής Ενέργειας', 'Energy Manager', 'production', 'energy')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, category = EXCLUDED.category, department = EXCLUDED.department;

-- 7. Εφοδιαστική Αλυσίδα & Logistics (Supply Chain)
INSERT INTO role_taxonomy (canonical_id, name_el, name_en, category, department) VALUES
('ROLE_SCM_DIRECTOR', 'Διευθυντής Εφοδιαστικής Αλυσίδας', 'Supply Chain Director', 'supply_chain', 'supply_chain'),
('ROLE_SCM_MANAGER', 'Διευθυντής Supply Chain', 'Supply Chain Manager', 'supply_chain', 'supply_chain'),
('ROLE_PROCUREMENT_DIRECTOR', 'Διευθυντής Προμηθειών', 'Procurement Director', 'supply_chain', 'procurement'),
('ROLE_PROCUREMENT_MANAGER', 'Διευθυντής Αγορών', 'Procurement Manager', 'supply_chain', 'procurement'),
('ROLE_BUYER', 'Αγοραστής', 'Buyer', 'supply_chain', 'procurement'),
('ROLE_SENIOR_BUYER', 'Senior Buyer', 'Senior Buyer', 'supply_chain', 'procurement'),
('ROLE_STRATEGIC_BUYER', 'Στρατηγικός Αγοραστής', 'Strategic Buyer', 'supply_chain', 'procurement'),
('ROLE_PURCHASING_ASSISTANT', 'Βοηθός Προμηθειών', 'Purchasing Assistant', 'supply_chain', 'procurement'),
('ROLE_LOGISTICS_MANAGER', 'Διευθυντής Logistics', 'Logistics Manager', 'supply_chain', 'logistics'),
('ROLE_LOGISTICS_COORDINATOR', 'Συντονιστής Logistics', 'Logistics Coordinator', 'supply_chain', 'logistics'),
('ROLE_TRANSPORT_MANAGER', 'Διευθυντής Μεταφορών', 'Transport Manager', 'supply_chain', 'transport'),
('ROLE_FLEET_MANAGER', 'Διευθυντής Στόλου', 'Fleet Manager', 'supply_chain', 'transport'),
('ROLE_WAREHOUSE_MANAGER', 'Διευθυντής Αποθήκης', 'Warehouse Manager', 'supply_chain', 'warehouse'),
('ROLE_WAREHOUSE_SUPERVISOR', 'Προϊστάμενος Αποθήκης', 'Warehouse Supervisor', 'supply_chain', 'warehouse'),
('ROLE_WAREHOUSE_CLERK', 'Υπάλληλος Αποθήκης', 'Warehouse Clerk', 'supply_chain', 'warehouse'),
('ROLE_FORKLIFT_OPERATOR', 'Χειριστής Κλαρκ', 'Forklift Operator', 'supply_chain', 'warehouse'),
('ROLE_INVENTORY_SPECIALIST', 'Υπεύθυνος Αποθεμάτων', 'Inventory Specialist', 'supply_chain', 'inventory'),
('ROLE_DEMAND_PLANNER', 'Demand Planner', 'Demand Planner', 'supply_chain', 'planning'),
('ROLE_SOP_MANAGER', 'Διευθυντής S&OP', 'S&OP Manager', 'supply_chain', 'planning'),
('ROLE_CUSTOMER_SERVICE_MGR', 'Διευθυντής Εξυπηρέτησης Πελατών', 'Customer Service Manager', 'supply_chain', 'customer_service'),
('ROLE_CUSTOMER_SERVICE_REP', 'Εκπρόσωπος Εξυπηρέτησης Πελατών', 'Customer Service Representative', 'supply_chain', 'customer_service'),
('ROLE_ORDER_MANAGER', 'Υπεύθυνος Παραγγελιών', 'Order Manager', 'supply_chain', 'orders'),
('ROLE_ORDER_PROCESSOR', 'Υπάλληλος Παραγγελιών', 'Order Processor', 'supply_chain', 'orders'),
('ROLE_DISPATCH_COORDINATOR', 'Συντονιστής Αποστολών', 'Dispatch Coordinator', 'supply_chain', 'logistics'),
('ROLE_IMPORT_EXPORT_SPEC', 'Υπεύθυνος Εισαγωγών-Εξαγωγών', 'Import/Export Specialist', 'supply_chain', 'customs'),
('ROLE_CUSTOMS_SPECIALIST', 'Εκτελωνιστής', 'Customs Specialist', 'supply_chain', 'customs')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, category = EXCLUDED.category, department = EXCLUDED.department;

-- 8. Ποιότητα, Περιβάλλον & Συμμόρφωση (Quality & Compliance)
INSERT INTO role_taxonomy (canonical_id, name_el, name_en, category, department) VALUES
('ROLE_QUALITY_DIRECTOR', 'Διευθυντής Ποιότητας', 'Quality Director', 'quality', 'quality'),
('ROLE_QA_MANAGER', 'Διευθυντής Διασφάλισης Ποιότητας', 'Quality Assurance Manager', 'quality', 'quality_assurance'),
('ROLE_QC_MANAGER', 'Διευθυντής Ελέγχου Ποιότητας', 'Quality Control Manager', 'quality', 'quality_control'),
('ROLE_QA_ENGINEER', 'Μηχανικός Διασφάλισης Ποιότητας', 'Quality Assurance Engineer', 'quality', 'quality_assurance'),
('ROLE_QC_INSPECTOR', 'Επιθεωρητής Ποιότητας', 'Quality Control Inspector', 'quality', 'quality_control'),
('ROLE_QC_TECHNICIAN', 'Τεχνικός Ποιότητας', 'Quality Control Technician', 'quality', 'quality_control'),
('ROLE_LAB_MANAGER', 'Διευθυντής Εργαστηρίου', 'Laboratory Manager', 'quality', 'laboratory'),
('ROLE_LAB_TECHNICIAN', 'Τεχνικός Εργαστηρίου', 'Laboratory Technician', 'quality', 'laboratory'),
('ROLE_ISO_COORDINATOR', 'Συντονιστής ISO', 'ISO Coordinator', 'quality', 'quality_assurance'),
('ROLE_AUDITOR', 'Επιθεωρητής', 'Auditor', 'quality', 'audit'),
('ROLE_DOCUMENT_CONTROLLER', 'Υπεύθυνος Τεκμηρίωσης', 'Document Controller', 'quality', 'quality_assurance'),
('ROLE_ENVIRONMENTAL_MGR', 'Διευθυντής Περιβάλλοντος', 'Environmental Manager', 'quality', 'environment'),
('ROLE_ENVIRONMENTAL_ENG', 'Μηχανικός Περιβάλλοντος', 'Environmental Engineer', 'quality', 'environment'),
('ROLE_SUSTAINABILITY_MGR', 'Διευθυντής Βιωσιμότητας', 'Sustainability Manager', 'quality', 'sustainability'),
('ROLE_COMPLIANCE_MANAGER', 'Διευθυντής Κανονιστικής Συμμόρφωσης', 'Compliance Manager', 'quality', 'compliance'),
('ROLE_COMPLIANCE_OFFICER', 'Υπεύθυνος Συμμόρφωσης', 'Compliance Officer', 'quality', 'compliance'),
('ROLE_REGULATORY_SPECIALIST', 'Ειδικός Κανονιστικών Θεμάτων', 'Regulatory Affairs Specialist', 'quality', 'compliance'),
('ROLE_CAPA_COORDINATOR', 'Συντονιστής CAPA', 'CAPA Coordinator', 'quality', 'quality_assurance'),
('ROLE_COMPLAINTS_HANDLER', 'Υπεύθυνος Παραπόνων', 'Complaints Handler', 'quality', 'quality_assurance')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, category = EXCLUDED.category, department = EXCLUDED.department;

-- 9. R&D / Τεχνικό / Μηχανολογικό
INSERT INTO role_taxonomy (canonical_id, name_el, name_en, category, department) VALUES
('ROLE_CTO', 'Τεχνικός Διευθυντής', 'Chief Technology Officer (CTO)', 'engineering', 'engineering'),
('ROLE_RD_DIRECTOR', 'Διευθυντής Έρευνας & Ανάπτυξης', 'R&D Director', 'engineering', 'rd'),
('ROLE_RD_MANAGER', 'Διευθυντής R&D', 'R&D Manager', 'engineering', 'rd'),
('ROLE_RD_ENGINEER', 'Μηχανικός Έρευνας & Ανάπτυξης', 'R&D Engineer', 'engineering', 'rd'),
('ROLE_TECHNICAL_DIRECTOR', 'Τεχνικός Διευθυντής', 'Technical Director', 'engineering', 'engineering'),
('ROLE_TECHNICAL_MANAGER', 'Τεχνικός Διευθυντής', 'Technical Manager', 'engineering', 'engineering'),
('ROLE_ENGINEERING_MANAGER', 'Διευθυντής Μηχανολογικού', 'Engineering Manager', 'engineering', 'engineering'),
('ROLE_MECHANICAL_ENGINEER', 'Μηχανολόγος Μηχανικός', 'Mechanical Engineer', 'engineering', 'mechanical'),
('ROLE_DESIGN_ENGINEER', 'Μηχανικός Σχεδιασμού', 'Design Engineer', 'engineering', 'design'),
('ROLE_CAD_DESIGNER', 'Σχεδιαστής CAD', 'CAD Designer', 'engineering', 'design'),
('ROLE_TOOL_DESIGNER', 'Σχεδιαστής Εργαλείων/Μητρών', 'Tool/Die Designer', 'engineering', 'tooling'),
('ROLE_DIE_MAKER', 'Κατασκευαστής Μητρών', 'Die Maker', 'engineering', 'tooling'),
('ROLE_PRODUCT_DEVELOPER', 'Υπεύθυνος Ανάπτυξης Προϊόντων', 'Product Developer', 'engineering', 'product_development'),
('ROLE_NPD_MANAGER', 'Διευθυντής Ανάπτυξης Νέων Προϊόντων', 'New Product Development Manager', 'engineering', 'product_development'),
('ROLE_TECH_SUPPORT_MGR', 'Διευθυντής Τεχνικής Υποστήριξης', 'Technical Support Manager', 'engineering', 'tech_support'),
('ROLE_TECH_SUPPORT_ENG', 'Μηχανικός Τεχνικής Υποστήριξης', 'Technical Support Engineer', 'engineering', 'tech_support'),
('ROLE_APPLICATION_ENG', 'Μηχανικός Εφαρμογών', 'Application Engineer', 'engineering', 'applications'),
('ROLE_FIELD_SERVICE_ENG', 'Μηχανικός Πεδίου', 'Field Service Engineer', 'engineering', 'field_service'),
('ROLE_STRUCTURAL_ENGINEER', 'Πολιτικός Μηχανικός', 'Structural Engineer', 'engineering', 'civil'),
('ROLE_PROJECT_ENGINEER', 'Μηχανικός Έργων', 'Project Engineer', 'engineering', 'projects'),
('ROLE_ELECTRICAL_ENGINEER', 'Ηλεκτρολόγος Μηχανικός', 'Electrical Engineer', 'engineering', 'electrical'),
('ROLE_AUTOMATION_ENGINEER', 'Μηχανικός Αυτοματισμού', 'Automation Engineer', 'engineering', 'automation'),
('ROLE_METALLURGIST', 'Μεταλλουργός', 'Metallurgist', 'engineering', 'materials'),
('ROLE_MATERIALS_ENGINEER', 'Μηχανικός Υλικών', 'Materials Engineer', 'engineering', 'materials')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, category = EXCLUDED.category, department = EXCLUDED.department;

-- 10. IT / Ψηφιακός Μετασχηματισμός
INSERT INTO role_taxonomy (canonical_id, name_el, name_en, category, department) VALUES
('ROLE_CIO', 'Διευθυντής Πληροφορικής', 'Chief Information Officer (CIO)', 'it', 'it'),
('ROLE_IT_DIRECTOR', 'Διευθυντής IT', 'IT Director', 'it', 'it'),
('ROLE_IT_MANAGER', 'Διευθυντής Πληροφορικής', 'IT Manager', 'it', 'it'),
('ROLE_IT_SUPERVISOR', 'Προϊστάμενος IT', 'IT Supervisor', 'it', 'it'),
('ROLE_SYSADMIN', 'Διαχειριστής Συστημάτων', 'Systems Administrator', 'it', 'infrastructure'),
('ROLE_NETWORK_ADMIN', 'Διαχειριστής Δικτύου', 'Network Administrator', 'it', 'infrastructure'),
('ROLE_IT_SUPPORT', 'Τεχνικός Υποστήριξης IT', 'IT Support Specialist', 'it', 'support'),
('ROLE_HELPDESK', 'Τεχνικός Helpdesk', 'Helpdesk Technician', 'it', 'support'),
('ROLE_ERP_MANAGER', 'Διευθυντής ERP', 'ERP Manager', 'it', 'erp'),
('ROLE_ERP_CONSULTANT', 'Σύμβουλος ERP', 'ERP Consultant', 'it', 'erp'),
('ROLE_ERP_SPECIALIST', 'Ειδικός ERP', 'ERP Specialist', 'it', 'erp'),
('ROLE_SOFTWARE_DEVELOPER', 'Προγραμματιστής', 'Software Developer', 'it', 'development'),
('ROLE_SENIOR_DEVELOPER', 'Senior Προγραμματιστής', 'Senior Software Developer', 'it', 'development'),
('ROLE_DATA_ANALYST', 'Αναλυτής Δεδομένων', 'Data Analyst', 'it', 'data'),
('ROLE_BI_ANALYST', 'Business Intelligence Analyst', 'Business Intelligence Analyst', 'it', 'data'),
('ROLE_BI_DEVELOPER', 'BI Developer', 'BI Developer', 'it', 'data'),
('ROLE_DATABASE_ADMIN', 'Διαχειριστής Βάσεων Δεδομένων', 'Database Administrator', 'it', 'data'),
('ROLE_CYBERSECURITY_MGR', 'Διευθυντής Κυβερνοασφάλειας', 'Cybersecurity Manager', 'it', 'security'),
('ROLE_SECURITY_ANALYST', 'Αναλυτής Ασφάλειας', 'Security Analyst', 'it', 'security'),
('ROLE_DPO', 'Υπεύθυνος Προστασίας Δεδομένων', 'Data Protection Officer (DPO)', 'it', 'security'),
('ROLE_DIGITAL_TRANSFORM_MGR', 'Διευθυντής Ψηφιακού Μετασχηματισμού', 'Digital Transformation Manager', 'it', 'digital'),
('ROLE_PROJECT_MANAGER_IT', 'Project Manager IT', 'IT Project Manager', 'it', 'projects')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, category = EXCLUDED.category, department = EXCLUDED.department;

-- 11. After Sales / Εξυπηρέτηση
INSERT INTO role_taxonomy (canonical_id, name_el, name_en, category, department) VALUES
('ROLE_AFTERSALES_DIRECTOR', 'Διευθυντής After Sales', 'After Sales Director', 'service', 'after_sales'),
('ROLE_AFTERSALES_MANAGER', 'Διευθυντής Εξυπηρέτησης', 'After Sales Manager', 'service', 'after_sales'),
('ROLE_SERVICE_MANAGER', 'Διευθυντής Service', 'Service Manager', 'service', 'service'),
('ROLE_WARRANTY_SPECIALIST', 'Υπεύθυνος Εγγυήσεων', 'Warranty Specialist', 'service', 'warranty'),
('ROLE_SPARE_PARTS_MGR', 'Διευθυντής Ανταλλακτικών', 'Spare Parts Manager', 'service', 'spare_parts'),
('ROLE_SERVICE_TECHNICIAN', 'Τεχνικός Service', 'Service Technician', 'service', 'service'),
('ROLE_INSTALLATION_TECH', 'Τεχνικός Τοποθέτησης', 'Installation Technician', 'service', 'installation'),
('ROLE_PARTNER_MANAGER', 'Διευθυντής Συνεργατών', 'Partner Manager', 'service', 'partners'),
('ROLE_DEALER_SUPPORT', 'Υποστήριξη Συνεργατών', 'Dealer Support Specialist', 'service', 'partners')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, category = EXCLUDED.category, department = EXCLUDED.department;

-- ============================================================================
-- PART 2: SKILL TAXONOMY (Hard Skills)
-- ============================================================================

-- Finance & Accounting Skills
INSERT INTO skill_taxonomy (canonical_id, name_el, name_en, category, domain) VALUES
('SKILL_ACCOUNTING', 'Λογιστική', 'Accounting', 'domain', 'finance'),
('SKILL_FINANCIAL_ANALYSIS', 'Χρηματοοικονομική Ανάλυση', 'Financial Analysis', 'domain', 'finance'),
('SKILL_BUDGETING', 'Κατάρτιση Προϋπολογισμού', 'Budgeting', 'domain', 'finance'),
('SKILL_FORECASTING', 'Προβλέψεις', 'Forecasting', 'domain', 'finance'),
('SKILL_COSTING', 'Κοστολόγηση', 'Costing', 'domain', 'finance'),
('SKILL_COST_ACCOUNTING', 'Αναλυτική Λογιστική', 'Cost Accounting', 'domain', 'finance'),
('SKILL_MONTH_CLOSE', 'Κλείσιμο Μήνα', 'Month-End Close', 'domain', 'finance'),
('SKILL_YEAR_CLOSE', 'Κλείσιμο Έτους', 'Year-End Close', 'domain', 'finance'),
('SKILL_FINANCIAL_REPORTING', 'Χρηματοοικονομικές Αναφορές', 'Financial Reporting', 'domain', 'finance'),
('SKILL_VAT', 'ΦΠΑ', 'VAT', 'domain', 'finance'),
('SKILL_TAX_COMPLIANCE', 'Φορολογική Συμμόρφωση', 'Tax Compliance', 'domain', 'finance'),
('SKILL_TAX_FILING', 'Υποβολή Δηλώσεων', 'Tax Filing', 'domain', 'finance'),
('SKILL_PAYROLL', 'Μισθοδοσία', 'Payroll Processing', 'domain', 'finance'),
('SKILL_AP', 'Πληρωτέοι Λογαριασμοί', 'Accounts Payable', 'domain', 'finance'),
('SKILL_AR', 'Εισπρακτέοι Λογαριασμοί', 'Accounts Receivable', 'domain', 'finance'),
('SKILL_CREDIT_CONTROL', 'Πιστωτικός Έλεγχος', 'Credit Control', 'domain', 'finance'),
('SKILL_CASH_MANAGEMENT', 'Διαχείριση Ταμείου', 'Cash Management', 'domain', 'finance'),
('SKILL_BANK_RECONCILIATION', 'Τραπεζική Συμφωνία', 'Bank Reconciliation', 'domain', 'finance'),
('SKILL_FIXED_ASSETS', 'Πάγια Περιουσιακά Στοιχεία', 'Fixed Assets Management', 'domain', 'finance'),
('SKILL_IFRS', 'ΔΠΧΑ', 'IFRS', 'domain', 'finance'),
('SKILL_GREEK_GAAP', 'Ελληνικά Λογιστικά Πρότυπα', 'Greek GAAP (ELP)', 'domain', 'finance'),
('SKILL_AUDIT', 'Εσωτερικός Έλεγχος', 'Internal Audit', 'domain', 'finance'),
('SKILL_CONTROLLING', 'Controlling', 'Controlling', 'domain', 'finance')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, domain = EXCLUDED.domain;

-- HR Skills
INSERT INTO skill_taxonomy (canonical_id, name_el, name_en, category, domain) VALUES
('SKILL_RECRUITMENT', 'Στελέχωση', 'Recruitment', 'domain', 'hr'),
('SKILL_INTERVIEWING', 'Συνεντεύξεις', 'Interviewing', 'domain', 'hr'),
('SKILL_ONBOARDING', 'Ενσωμάτωση Προσωπικού', 'Onboarding', 'domain', 'hr'),
('SKILL_PERFORMANCE_MGMT', 'Διαχείριση Απόδοσης', 'Performance Management', 'domain', 'hr'),
('SKILL_TRAINING_DELIVERY', 'Παροχή Εκπαίδευσης', 'Training Delivery', 'domain', 'hr'),
('SKILL_TNA', 'Ανάλυση Εκπαιδευτικών Αναγκών', 'Training Needs Analysis', 'domain', 'hr'),
('SKILL_EMPLOYEE_RELATIONS', 'Εργασιακές Σχέσεις', 'Employee Relations', 'domain', 'hr'),
('SKILL_LABOR_LAW', 'Εργατική Νομοθεσία', 'Labor Law', 'domain', 'hr'),
('SKILL_COMPENSATION', 'Αμοιβές & Παροχές', 'Compensation & Benefits', 'domain', 'hr'),
('SKILL_HRIS', 'Συστήματα HRIS', 'HRIS Systems', 'tool', 'hr'),
('SKILL_WORKPLACE_SAFETY', 'Ασφάλεια Εργασίας', 'Workplace Safety', 'domain', 'safety'),
('SKILL_RISK_ASSESSMENT', 'Εκτίμηση Κινδύνων', 'Risk Assessment', 'domain', 'safety'),
('SKILL_INCIDENT_INVESTIGATION', 'Διερεύνηση Συμβάντων', 'Incident Investigation', 'domain', 'safety')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, domain = EXCLUDED.domain;

-- Sales & Marketing Skills
INSERT INTO skill_taxonomy (canonical_id, name_el, name_en, category, domain) VALUES
('SKILL_B2B_SALES', 'Πωλήσεις B2B', 'B2B Sales', 'domain', 'sales'),
('SKILL_KEY_ACCOUNT', 'Διαχείριση Στρατηγικών Πελατών', 'Key Account Management', 'domain', 'sales'),
('SKILL_NEGOTIATION', 'Διαπραγματεύσεις', 'Negotiation', 'domain', 'sales'),
('SKILL_TENDER_MGMT', 'Διαχείριση Διαγωνισμών', 'Tender Management', 'domain', 'sales'),
('SKILL_PRICING', 'Τιμολόγηση', 'Pricing', 'domain', 'sales'),
('SKILL_QUOTING', 'Σύνταξη Προσφορών', 'Quotation Preparation', 'domain', 'sales'),
('SKILL_CRM', 'Διαχείριση Πελατειακών Σχέσεων', 'CRM', 'tool', 'sales'),
('SKILL_EXPORT', 'Εξαγωγές', 'Export', 'domain', 'sales'),
('SKILL_INCOTERMS', 'Incoterms', 'Incoterms', 'domain', 'logistics'),
('SKILL_DIGITAL_MARKETING', 'Ψηφιακό Marketing', 'Digital Marketing', 'domain', 'marketing'),
('SKILL_SEO', 'SEO', 'SEO', 'technical', 'marketing'),
('SKILL_SEM', 'SEM', 'SEM (Google Ads)', 'technical', 'marketing'),
('SKILL_SOCIAL_MEDIA', 'Social Media Marketing', 'Social Media Marketing', 'domain', 'marketing'),
('SKILL_CONTENT_CREATION', 'Δημιουργία Περιεχομένου', 'Content Creation', 'domain', 'marketing'),
('SKILL_COPYWRITING', 'Συγγραφή Κειμένων', 'Copywriting', 'domain', 'marketing'),
('SKILL_EMAIL_MARKETING', 'Email Marketing', 'Email Marketing', 'domain', 'marketing'),
('SKILL_MARKET_RESEARCH', 'Έρευνα Αγοράς', 'Market Research', 'domain', 'marketing'),
('SKILL_BRAND_MGMT', 'Διαχείριση Brand', 'Brand Management', 'domain', 'marketing'),
('SKILL_TRADE_SHOWS', 'Οργάνωση Εκθέσεων', 'Trade Show Management', 'domain', 'marketing')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, domain = EXCLUDED.domain;

-- Production & Manufacturing Skills
INSERT INTO skill_taxonomy (canonical_id, name_el, name_en, category, domain) VALUES
('SKILL_PRODUCTION_PLANNING', 'Προγραμματισμός Παραγωγής', 'Production Planning', 'domain', 'production'),
('SKILL_CAPACITY_PLANNING', 'Προγραμματισμός Δυναμικότητας', 'Capacity Planning', 'domain', 'production'),
('SKILL_MRP', 'MRP', 'MRP', 'methodology', 'production'),
('SKILL_SHIFT_MGMT', 'Διαχείριση Βαρδιών', 'Shift Management', 'domain', 'production'),
('SKILL_EXTRUSION', 'Διέλαση Αλουμινίου', 'Aluminum Extrusion', 'technical', 'manufacturing'),
('SKILL_ANODIZING', 'Ανοδίωση', 'Anodizing', 'technical', 'manufacturing'),
('SKILL_POWDER_COATING', 'Ηλεκτροστατική Βαφή', 'Powder Coating', 'technical', 'manufacturing'),
('SKILL_THERMAL_BREAK', 'Θερμοδιακοπή', 'Thermal Break Assembly', 'technical', 'manufacturing'),
('SKILL_CNC_MACHINING', 'Κατεργασία CNC', 'CNC Machining', 'technical', 'manufacturing'),
('SKILL_ASSEMBLY', 'Συναρμολόγηση', 'Assembly', 'technical', 'manufacturing'),
('SKILL_MACHINE_OPERATION', 'Χειρισμός Μηχανημάτων', 'Machine Operation', 'technical', 'manufacturing'),
('SKILL_PREVENTIVE_MAINT', 'Προληπτική Συντήρηση', 'Preventive Maintenance', 'technical', 'maintenance'),
('SKILL_CORRECTIVE_MAINT', 'Διορθωτική Συντήρηση', 'Corrective Maintenance', 'technical', 'maintenance'),
('SKILL_TPM', 'Ολική Παραγωγική Συντήρηση', 'TPM', 'methodology', 'maintenance'),
('SKILL_LEAN', 'Lean Manufacturing', 'Lean Manufacturing', 'methodology', 'production'),
('SKILL_SIX_SIGMA', 'Six Sigma', 'Six Sigma', 'methodology', 'quality'),
('SKILL_KAIZEN', 'Kaizen', 'Kaizen', 'methodology', 'production'),
('SKILL_5S', '5S', '5S', 'methodology', 'production'),
('SKILL_SMED', 'SMED', 'SMED', 'methodology', 'production'),
('SKILL_VALUE_STREAM', 'Χαρτογράφηση Αξίας', 'Value Stream Mapping', 'methodology', 'production'),
('SKILL_OEE', 'OEE', 'OEE', 'methodology', 'production'),
('SKILL_PLC_PROGRAMMING', 'Προγραμματισμός PLC', 'PLC Programming', 'technical', 'automation'),
('SKILL_PNEUMATICS', 'Πνευματικά Συστήματα', 'Pneumatics', 'technical', 'maintenance'),
('SKILL_HYDRAULICS', 'Υδραυλικά Συστήματα', 'Hydraulics', 'technical', 'maintenance'),
('SKILL_WELDING', 'Συγκόλληση', 'Welding', 'technical', 'manufacturing'),
('SKILL_ELECTRICAL_MAINT', 'Ηλεκτρική Συντήρηση', 'Electrical Maintenance', 'technical', 'maintenance'),
('SKILL_ENERGY_MGMT', 'Διαχείριση Ενέργειας', 'Energy Management', 'domain', 'energy')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, domain = EXCLUDED.domain;

-- Supply Chain & Logistics Skills
INSERT INTO skill_taxonomy (canonical_id, name_el, name_en, category, domain) VALUES
('SKILL_PROCUREMENT', 'Προμήθειες', 'Procurement', 'domain', 'supply_chain'),
('SKILL_SUPPLIER_MGMT', 'Διαχείριση Προμηθευτών', 'Supplier Management', 'domain', 'supply_chain'),
('SKILL_SUPPLIER_EVAL', 'Αξιολόγηση Προμηθευτών', 'Supplier Evaluation', 'domain', 'supply_chain'),
('SKILL_CONTRACT_NEGOTIATION', 'Διαπραγμάτευση Συμβάσεων', 'Contract Negotiation', 'domain', 'supply_chain'),
('SKILL_INVENTORY_MGMT', 'Διαχείριση Αποθεμάτων', 'Inventory Management', 'domain', 'supply_chain'),
('SKILL_WAREHOUSE_OPS', 'Λειτουργίες Αποθήκης', 'Warehouse Operations', 'domain', 'logistics'),
('SKILL_WMS', 'Συστήματα WMS', 'WMS', 'tool', 'logistics'),
('SKILL_LOGISTICS', 'Logistics', 'Logistics', 'domain', 'logistics'),
('SKILL_TRANSPORT_PLANNING', 'Προγραμματισμός Μεταφορών', 'Transport Planning', 'domain', 'logistics'),
('SKILL_ROUTE_OPTIMIZATION', 'Βελτιστοποίηση Δρομολογίων', 'Route Optimization', 'domain', 'logistics'),
('SKILL_CUSTOMS', 'Εκτελωνισμός', 'Customs Clearance', 'domain', 'logistics'),
('SKILL_DEMAND_PLANNING', 'Σχεδιασμός Ζήτησης', 'Demand Planning', 'domain', 'supply_chain'),
('SKILL_SOP', 'S&OP', 'S&OP', 'methodology', 'supply_chain'),
('SKILL_ORDER_MGMT', 'Διαχείριση Παραγγελιών', 'Order Management', 'domain', 'supply_chain'),
('SKILL_FORKLIFT', 'Χειρισμός Περονοφόρου', 'Forklift Operation', 'technical', 'logistics')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, domain = EXCLUDED.domain;

-- Quality & Compliance Skills
INSERT INTO skill_taxonomy (canonical_id, name_el, name_en, category, domain) VALUES
('SKILL_QMS', 'Συστήματα Διαχείρισης Ποιότητας', 'Quality Management Systems', 'domain', 'quality'),
('SKILL_ISO_9001', 'ISO 9001', 'ISO 9001', 'certification', 'quality'),
('SKILL_ISO_14001', 'ISO 14001', 'ISO 14001', 'certification', 'environment'),
('SKILL_ISO_45001', 'ISO 45001', 'ISO 45001', 'certification', 'safety'),
('SKILL_IATF_16949', 'IATF 16949', 'IATF 16949', 'certification', 'quality'),
('SKILL_INTERNAL_AUDIT', 'Εσωτερική Επιθεώρηση', 'Internal Auditing', 'domain', 'quality'),
('SKILL_PROCESS_AUDIT', 'Επιθεώρηση Διεργασιών', 'Process Auditing', 'domain', 'quality'),
('SKILL_SPC', 'Στατιστικός Έλεγχος Διεργασιών', 'SPC', 'methodology', 'quality'),
('SKILL_FMEA', 'FMEA', 'FMEA', 'methodology', 'quality'),
('SKILL_8D', '8D Methodology', '8D Problem Solving', 'methodology', 'quality'),
('SKILL_ROOT_CAUSE', 'Ανάλυση Βασικής Αιτίας', 'Root Cause Analysis', 'methodology', 'quality'),
('SKILL_CAPA', 'CAPA', 'CAPA', 'methodology', 'quality'),
('SKILL_MEASUREMENT', 'Μετρολογία', 'Metrology', 'technical', 'quality'),
('SKILL_CALIBRATION', 'Διακρίβωση', 'Calibration', 'technical', 'quality'),
('SKILL_TESTING', 'Δοκιμές Υλικών', 'Material Testing', 'technical', 'quality'),
('SKILL_TRACEABILITY', 'Ιχνηλασιμότητα', 'Traceability', 'domain', 'quality'),
('SKILL_DOCUMENT_CONTROL', 'Έλεγχος Εγγράφων', 'Document Control', 'domain', 'quality'),
('SKILL_REACH_ROHS', 'REACH/RoHS', 'REACH/RoHS Compliance', 'domain', 'compliance'),
('SKILL_WASTE_MGMT', 'Διαχείριση Αποβλήτων', 'Waste Management', 'domain', 'environment'),
('SKILL_ENVIRONMENTAL_MGMT', 'Περιβαλλοντική Διαχείριση', 'Environmental Management', 'domain', 'environment')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, domain = EXCLUDED.domain;

-- Engineering & Technical Skills
INSERT INTO skill_taxonomy (canonical_id, name_el, name_en, category, domain) VALUES
('SKILL_MECHANICAL_DESIGN', 'Μηχανολογικός Σχεδιασμός', 'Mechanical Design', 'technical', 'engineering'),
('SKILL_CAD', 'Σχεδίαση CAD', 'CAD Design', 'tool', 'engineering'),
('SKILL_3D_MODELING', 'Τρισδιάστατη Μοντελοποίηση', '3D Modeling', 'technical', 'engineering'),
('SKILL_TECHNICAL_DRAWING', 'Τεχνικό Σχέδιο', 'Technical Drawing', 'technical', 'engineering'),
('SKILL_DIE_DESIGN', 'Σχεδιασμός Μητρών', 'Die Design', 'technical', 'engineering'),
('SKILL_TOOL_DESIGN', 'Σχεδιασμός Εργαλείων', 'Tool Design', 'technical', 'engineering'),
('SKILL_FEA', 'Ανάλυση Πεπερασμένων Στοιχείων', 'FEA', 'technical', 'engineering'),
('SKILL_THERMAL_ANALYSIS', 'Θερμική Ανάλυση', 'Thermal Analysis', 'technical', 'engineering'),
('SKILL_PRODUCT_DEV', 'Ανάπτυξη Προϊόντων', 'Product Development', 'domain', 'engineering'),
('SKILL_PROTOTYPING', 'Κατασκευή Πρωτοτύπων', 'Prototyping', 'technical', 'engineering'),
('SKILL_PROJECT_MGMT', 'Διαχείριση Έργων', 'Project Management', 'domain', 'management'),
('SKILL_TECHNICAL_SPECS', 'Τεχνικές Προδιαγραφές', 'Technical Specifications', 'technical', 'engineering'),
('SKILL_ELECTRICAL_DESIGN', 'Ηλεκτρολογικός Σχεδιασμός', 'Electrical Design', 'technical', 'engineering'),
('SKILL_AUTOMATION', 'Αυτοματισμοί', 'Automation', 'technical', 'automation'),
('SKILL_SCADA', 'SCADA', 'SCADA', 'tool', 'automation'),
('SKILL_METALLURGY', 'Μεταλλουργία', 'Metallurgy', 'technical', 'materials'),
('SKILL_MATERIALS_SCIENCE', 'Επιστήμη Υλικών', 'Materials Science', 'technical', 'materials'),
('SKILL_SURFACE_TREATMENT', 'Επιφανειακή Κατεργασία', 'Surface Treatment', 'technical', 'manufacturing')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, domain = EXCLUDED.domain;

-- IT Skills
INSERT INTO skill_taxonomy (canonical_id, name_el, name_en, category, domain) VALUES
('SKILL_ERP_IMPLEMENTATION', 'Υλοποίηση ERP', 'ERP Implementation', 'technical', 'it'),
('SKILL_ERP_ADMIN', 'Διαχείριση ERP', 'ERP Administration', 'technical', 'it'),
('SKILL_CRM_ADMIN', 'Διαχείριση CRM', 'CRM Administration', 'technical', 'it'),
('SKILL_DATABASE_ADMIN', 'Διαχείριση Βάσεων Δεδομένων', 'Database Administration', 'technical', 'it'),
('SKILL_NETWORK_ADMIN', 'Διαχείριση Δικτύων', 'Network Administration', 'technical', 'it'),
('SKILL_SERVER_ADMIN', 'Διαχείριση Servers', 'Server Administration', 'technical', 'it'),
('SKILL_CLOUD_MGMT', 'Διαχείριση Cloud', 'Cloud Management', 'technical', 'it'),
('SKILL_CYBERSECURITY', 'Κυβερνοασφάλεια', 'Cybersecurity', 'technical', 'security'),
('SKILL_DATA_PROTECTION', 'Προστασία Δεδομένων', 'Data Protection', 'domain', 'security'),
('SKILL_GDPR', 'GDPR', 'GDPR', 'domain', 'compliance'),
('SKILL_BI', 'Business Intelligence', 'Business Intelligence', 'technical', 'data'),
('SKILL_DATA_ANALYSIS', 'Ανάλυση Δεδομένων', 'Data Analysis', 'technical', 'data'),
('SKILL_SQL', 'SQL', 'SQL', 'technical', 'data'),
('SKILL_PROGRAMMING', 'Προγραμματισμός', 'Programming', 'technical', 'it'),
('SKILL_IT_SUPPORT', 'Τεχνική Υποστήριξη', 'IT Support', 'domain', 'it'),
('SKILL_HELPDESK', 'Helpdesk', 'Helpdesk Support', 'domain', 'it')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en, domain = EXCLUDED.domain;

-- ============================================================================
-- PART 3: CERTIFICATION TAXONOMY
-- ============================================================================

-- Accounting & Finance Certifications
INSERT INTO certification_taxonomy (canonical_id, name_en, name_el, category, issuing_organization) VALUES
('CERT_OEE_A', 'Greek Accountant License Class A', 'Άδεια Λογιστή Α Τάξης', 'accounting', 'ΟΕΕ'),
('CERT_OEE_B', 'Greek Accountant License Class B', 'Άδεια Λογιστή Β Τάξης', 'accounting', 'ΟΕΕ'),
('CERT_OEE_C', 'Greek Accountant License Class C', 'Άδεια Λογιστή Γ Τάξης', 'accounting', 'ΟΕΕ'),
('CERT_SOEL', 'SOEL Member', 'Μέλος ΣΟΕΛ', 'accounting', 'ΣΟΕΛ'),
('CERT_ACCA', 'ACCA', 'ACCA', 'accounting', 'ACCA'),
('CERT_CPA', 'CPA', 'CPA', 'accounting', 'AICPA'),
('CERT_CMA', 'CMA', 'CMA', 'accounting', 'IMA'),
('CERT_CIA', 'CIA', 'CIA', 'accounting', 'IIA'),
('CERT_CFA', 'CFA', 'CFA', 'finance', 'CFA Institute'),
('CERT_FRM', 'FRM', 'FRM', 'finance', 'GARP')
ON CONFLICT (canonical_id) DO UPDATE SET name_en = EXCLUDED.name_en, name_el = EXCLUDED.name_el, issuing_organization = EXCLUDED.issuing_organization;

-- Quality & Audit Certifications
INSERT INTO certification_taxonomy (canonical_id, name_en, name_el, category, issuing_organization) VALUES
('CERT_ISO_9001_LA', 'ISO 9001 Lead Auditor', 'ISO 9001 Lead Auditor', 'quality', 'IRCA'),
('CERT_ISO_9001_IA', 'ISO 9001 Internal Auditor', 'ISO 9001 Internal Auditor', 'quality', 'Various'),
('CERT_ISO_14001_LA', 'ISO 14001 Lead Auditor', 'ISO 14001 Lead Auditor', 'quality', 'IRCA'),
('CERT_ISO_14001_IA', 'ISO 14001 Internal Auditor', 'ISO 14001 Internal Auditor', 'quality', 'Various'),
('CERT_ISO_45001_LA', 'ISO 45001 Lead Auditor', 'ISO 45001 Lead Auditor', 'quality', 'IRCA'),
('CERT_ISO_45001_IA', 'ISO 45001 Internal Auditor', 'ISO 45001 Internal Auditor', 'quality', 'Various'),
('CERT_IATF_16949_LA', 'IATF 16949 Lead Auditor', 'IATF 16949 Lead Auditor', 'quality', 'IATF'),
('CERT_SIX_SIGMA_GB', 'Six Sigma Green Belt', 'Six Sigma Green Belt', 'quality', 'ASQ'),
('CERT_SIX_SIGMA_BB', 'Six Sigma Black Belt', 'Six Sigma Black Belt', 'quality', 'ASQ'),
('CERT_SIX_SIGMA_MBB', 'Six Sigma Master Black Belt', 'Six Sigma Master Black Belt', 'quality', 'ASQ'),
('CERT_LEAN_PRACTITIONER', 'Lean Practitioner', 'Lean Practitioner', 'quality', 'Various'),
('CERT_CQE', 'Certified Quality Engineer', 'Certified Quality Engineer', 'quality', 'ASQ'),
('CERT_CQA', 'Certified Quality Auditor', 'Certified Quality Auditor', 'quality', 'ASQ'),
('CERT_CMQ', 'Certified Manager of Quality', 'Certified Manager of Quality', 'quality', 'ASQ')
ON CONFLICT (canonical_id) DO UPDATE SET name_en = EXCLUDED.name_en, name_el = EXCLUDED.name_el, issuing_organization = EXCLUDED.issuing_organization;

-- Health & Safety Certifications
INSERT INTO certification_taxonomy (canonical_id, name_en, name_el, category, issuing_organization) VALUES
('CERT_TECH_SAFETY', 'Safety Technician', 'Τεχνικός Ασφαλείας', 'safety', 'ΥΠΕΡΓ'),
('CERT_NEBOSH', 'NEBOSH', 'NEBOSH', 'safety', 'NEBOSH'),
('CERT_IOSH', 'IOSH Managing Safely', 'IOSH Managing Safely', 'safety', 'IOSH'),
('CERT_OSHA_30', 'OSHA 30', 'OSHA 30', 'safety', 'OSHA'),
('CERT_FIRST_AID', 'First Aid', 'Πρώτες Βοήθειες', 'safety', 'Ελληνικός Ερυθρός Σταυρός'),
('CERT_FIRE_SAFETY', 'Fire Safety', 'Πυρασφάλεια', 'safety', 'Various')
ON CONFLICT (canonical_id) DO UPDATE SET name_en = EXCLUDED.name_en, name_el = EXCLUDED.name_el, issuing_organization = EXCLUDED.issuing_organization;

-- HR Certifications
INSERT INTO certification_taxonomy (canonical_id, name_en, name_el, category, issuing_organization) VALUES
('CERT_SHRM_CP', 'SHRM-CP', 'SHRM-CP', 'hr', 'SHRM'),
('CERT_SHRM_SCP', 'SHRM-SCP', 'SHRM-SCP', 'hr', 'SHRM'),
('CERT_PHR', 'PHR', 'PHR', 'hr', 'HRCI'),
('CERT_SPHR', 'SPHR', 'SPHR', 'hr', 'HRCI'),
('CERT_CIPD', 'CIPD', 'CIPD', 'hr', 'CIPD')
ON CONFLICT (canonical_id) DO UPDATE SET name_en = EXCLUDED.name_en, name_el = EXCLUDED.name_el, issuing_organization = EXCLUDED.issuing_organization;

-- Project Management Certifications
INSERT INTO certification_taxonomy (canonical_id, name_en, name_el, category, issuing_organization) VALUES
('CERT_PMP', 'PMP', 'PMP', 'pm', 'PMI'),
('CERT_CAPM', 'CAPM', 'CAPM', 'pm', 'PMI'),
('CERT_PRINCE2_F', 'PRINCE2 Foundation', 'PRINCE2 Foundation', 'pm', 'Axelos'),
('CERT_PRINCE2_P', 'PRINCE2 Practitioner', 'PRINCE2 Practitioner', 'pm', 'Axelos'),
('CERT_SCRUM_MASTER', 'Certified Scrum Master', 'Certified Scrum Master', 'pm', 'Scrum Alliance'),
('CERT_AGILE', 'PMI-ACP', 'PMI-ACP', 'pm', 'PMI')
ON CONFLICT (canonical_id) DO UPDATE SET name_en = EXCLUDED.name_en, name_el = EXCLUDED.name_el, issuing_organization = EXCLUDED.issuing_organization;

-- IT & Cybersecurity Certifications
INSERT INTO certification_taxonomy (canonical_id, name_en, name_el, category, issuing_organization) VALUES
('CERT_ECDL', 'ECDL/ICDL', 'ECDL/ICDL', 'it', 'ICDL Foundation'),
('CERT_MOS', 'Microsoft Office Specialist', 'Microsoft Office Specialist', 'it', 'Microsoft'),
('CERT_MCSE', 'MCSE', 'MCSE', 'it', 'Microsoft'),
('CERT_CCNA', 'CCNA', 'CCNA', 'it', 'Cisco'),
('CERT_CCNP', 'CCNP', 'CCNP', 'it', 'Cisco'),
('CERT_AWS_SA', 'AWS Solutions Architect', 'AWS Solutions Architect', 'it', 'Amazon'),
('CERT_AWS_DEV', 'AWS Developer', 'AWS Developer', 'it', 'Amazon'),
('CERT_AZURE', 'Azure Administrator', 'Azure Administrator', 'it', 'Microsoft'),
('CERT_CISSP', 'CISSP', 'CISSP', 'it', 'ISC2'),
('CERT_CISM', 'CISM', 'CISM', 'it', 'ISACA'),
('CERT_CISA', 'CISA', 'CISA', 'it', 'ISACA'),
('CERT_COMPTIA_SEC', 'CompTIA Security+', 'CompTIA Security+', 'it', 'CompTIA'),
('CERT_COMPTIA_NET', 'CompTIA Network+', 'CompTIA Network+', 'it', 'CompTIA'),
('CERT_ITIL', 'ITIL Foundation', 'ITIL Foundation', 'it', 'Axelos'),
('CERT_COBIT', 'COBIT', 'COBIT', 'it', 'ISACA'),
('CERT_SAP_CONSULTANT', 'SAP Certified Consultant', 'SAP Certified Consultant', 'it', 'SAP'),
('CERT_ORACLE', 'Oracle Certified Professional', 'Oracle Certified Professional', 'it', 'Oracle'),
('CERT_DPO', 'Certified DPO', 'Certified DPO', 'it', 'Various')
ON CONFLICT (canonical_id) DO UPDATE SET name_en = EXCLUDED.name_en, name_el = EXCLUDED.name_el, issuing_organization = EXCLUDED.issuing_organization;

-- Supply Chain Certifications
INSERT INTO certification_taxonomy (canonical_id, name_en, name_el, category, issuing_organization) VALUES
('CERT_CSCP', 'CSCP', 'CSCP', 'supply_chain', 'ASCM'),
('CERT_CPIM', 'CPIM', 'CPIM', 'supply_chain', 'ASCM'),
('CERT_CLTD', 'CLTD', 'CLTD', 'supply_chain', 'ASCM'),
('CERT_CPSM', 'CPSM', 'CPSM', 'supply_chain', 'ISM'),
('CERT_CPP', 'CPP', 'CPP', 'supply_chain', 'ISM'),
('CERT_CIPS', 'CIPS', 'CIPS', 'supply_chain', 'CIPS')
ON CONFLICT (canonical_id) DO UPDATE SET name_en = EXCLUDED.name_en, name_el = EXCLUDED.name_el, issuing_organization = EXCLUDED.issuing_organization;

-- Engineering Certifications
INSERT INTO certification_taxonomy (canonical_id, name_en, name_el, category, issuing_organization) VALUES
('CERT_TEE', 'TEE Member', 'Μέλος ΤΕΕ', 'engineering', 'ΤΕΕ'),
('CERT_PE', 'Professional Engineer', 'Professional Engineer', 'engineering', 'NCEES'),
('CERT_AUTOCAD_CERT', 'AutoCAD Certified', 'AutoCAD Certified', 'engineering', 'Autodesk'),
('CERT_SOLIDWORKS', 'CSWP', 'CSWP', 'engineering', 'SolidWorks'),
('CERT_WELDING_IWE', 'IWE', 'IWE', 'engineering', 'IIW'),
('CERT_WELDING_IWT', 'IWT', 'IWT', 'engineering', 'IIW'),
('CERT_NDT', 'NDT Certification', 'NDT Certification', 'engineering', 'ASNT'),
('CERT_CMRP', 'CMRP', 'CMRP', 'engineering', 'SMRP')
ON CONFLICT (canonical_id) DO UPDATE SET name_en = EXCLUDED.name_en, name_el = EXCLUDED.name_el, issuing_organization = EXCLUDED.issuing_organization;

-- Driving & Equipment Licenses
INSERT INTO certification_taxonomy (canonical_id, name_en, name_el, category, issuing_organization) VALUES
('CERT_FORKLIFT', 'Forklift Operator License', 'Άδεια Χειριστή Περονοφόρου', 'license', 'Various'),
('CERT_CRANE', 'Crane Operator License', 'Άδεια Χειριστή Γερανού', 'license', 'Various'),
('CERT_ADR', 'ADR', 'ADR', 'license', 'UN'),
('CERT_DRIVING_B', 'Driving License B', 'Δίπλωμα Οδήγησης Β', 'license', 'ΥΠΜΕ'),
('CERT_DRIVING_C', 'Driving License C', 'Δίπλωμα Οδήγησης Γ', 'license', 'ΥΠΜΕ'),
('CERT_DRIVING_CE', 'Driving License C+E', 'Δίπλωμα Οδήγησης C+E', 'license', 'ΥΠΜΕ')
ON CONFLICT (canonical_id) DO UPDATE SET name_en = EXCLUDED.name_en, name_el = EXCLUDED.name_el, issuing_organization = EXCLUDED.issuing_organization;

-- ============================================================================
-- PART 4: SOFTWARE TAXONOMY
-- ============================================================================

-- ERP Systems
INSERT INTO software_taxonomy (canonical_id, name, category) VALUES
('SW_SAP', 'SAP', 'erp'),
('SW_SAP_B1', 'SAP Business One', 'erp'),
('SW_SAP_S4HANA', 'SAP S/4HANA', 'erp'),
('SW_ORACLE_ERP', 'Oracle ERP', 'erp'),
('SW_MS_DYNAMICS', 'Microsoft Dynamics', 'erp'),
('SW_NAVISION', 'Navision', 'erp'),
('SW_SOFTONE', 'SoftOne', 'erp'),
('SW_SINGULAR', 'Singular', 'erp'),
('SW_GALAXY', 'Galaxy', 'erp'),
('SW_ATLANTIS', 'Atlantis', 'erp'),
('SW_PYLON', 'Pylon', 'erp'),
('SW_MEGASOFT', 'Megasoft', 'erp'),
('SW_ENTERSOFT', 'Entersoft', 'erp'),
('SW_PRISMA_WIN', 'PRISMA Win', 'erp'),
('SW_DATA_COMM', 'Data Communication', 'erp'),
('SW_COMPUTING', 'Computing', 'erp'),
('SW_NOVAL', 'Noval', 'erp'),
('SW_UNISOFT', 'Unisoft', 'erp'),
('SW_ODOO', 'Odoo', 'erp'),
('SW_NETSUITE', 'NetSuite', 'erp')
ON CONFLICT (canonical_id) DO UPDATE SET name = EXCLUDED.name;

-- Accounting Software
INSERT INTO software_taxonomy (canonical_id, name, category) VALUES
('SW_EPSILON_NET', 'Epsilon Net', 'accounting'),
('SW_PEGASUS', 'Pegasus', 'accounting'),
('SW_KEFALAIO', 'Κεφάλαιο', 'accounting'),
('SW_ATLANTIS_ACC', 'Atlantis Accounting', 'accounting'),
('SW_MYDATA', 'myDATA', 'accounting'),
('SW_TAXISNET', 'TAXISnet', 'accounting'),
('SW_ERGANI', 'ΕΡΓΑΝΗ', 'accounting')
ON CONFLICT (canonical_id) DO UPDATE SET name = EXCLUDED.name;

-- Office & Productivity
INSERT INTO software_taxonomy (canonical_id, name, category) VALUES
('SW_MS_OFFICE', 'Microsoft Office', 'office'),
('SW_EXCEL', 'Microsoft Excel', 'office'),
('SW_WORD', 'Microsoft Word', 'office'),
('SW_POWERPOINT', 'Microsoft PowerPoint', 'office'),
('SW_OUTLOOK', 'Microsoft Outlook', 'office'),
('SW_ACCESS', 'Microsoft Access', 'office'),
('SW_OFFICE_365', 'Microsoft 365', 'office'),
('SW_GOOGLE_WORKSPACE', 'Google Workspace', 'office'),
('SW_GOOGLE_SHEETS', 'Google Sheets', 'office'),
('SW_GOOGLE_DOCS', 'Google Docs', 'office'),
('SW_LIBREOFFICE', 'LibreOffice', 'office')
ON CONFLICT (canonical_id) DO UPDATE SET name = EXCLUDED.name;

-- CRM Systems
INSERT INTO software_taxonomy (canonical_id, name, category) VALUES
('SW_SALESFORCE', 'Salesforce', 'crm'),
('SW_HUBSPOT', 'HubSpot', 'crm'),
('SW_MS_DYNAMICS_CRM', 'Microsoft Dynamics CRM', 'crm'),
('SW_ZOHO_CRM', 'Zoho CRM', 'crm'),
('SW_PIPEDRIVE', 'Pipedrive', 'crm'),
('SW_VTIGER', 'vTiger', 'crm')
ON CONFLICT (canonical_id) DO UPDATE SET name = EXCLUDED.name;

-- HR & Payroll Systems
INSERT INTO software_taxonomy (canonical_id, name, category) VALUES
('SW_WORKDAY', 'Workday', 'hr'),
('SW_SAP_SUCCESSFACTORS', 'SAP SuccessFactors', 'hr'),
('SW_BAMBOOHR', 'BambooHR', 'hr'),
('SW_ERGANI_SW', 'ΕΡΓΑΝΗ', 'hr'),
('SW_EPSILONHR', 'Epsilon HR', 'hr'),
('SW_SOFTONE_HR', 'SoftOne HR', 'hr')
ON CONFLICT (canonical_id) DO UPDATE SET name = EXCLUDED.name;

-- WMS & Logistics
INSERT INTO software_taxonomy (canonical_id, name, category) VALUES
('SW_SAP_WM', 'SAP WM', 'wms'),
('SW_SAP_EWM', 'SAP EWM', 'wms'),
('SW_ORACLE_WMS', 'Oracle WMS', 'wms'),
('SW_MANHATTAN_WMS', 'Manhattan WMS', 'wms'),
('SW_QLIK_LOGISTICS', 'Qlik Logistics', 'wms'),
('SW_SOFTONE_WMS', 'SoftOne WMS', 'wms')
ON CONFLICT (canonical_id) DO UPDATE SET name = EXCLUDED.name;

-- CAD & Engineering
INSERT INTO software_taxonomy (canonical_id, name, category) VALUES
('SW_AUTOCAD', 'AutoCAD', 'cad'),
('SW_SOLIDWORKS', 'SolidWorks', 'cad'),
('SW_INVENTOR', 'Autodesk Inventor', 'cad'),
('SW_CATIA', 'CATIA', 'cad'),
('SW_CREO', 'PTC Creo', 'cad'),
('SW_NX', 'Siemens NX', 'cad'),
('SW_REVIT', 'Revit', 'cad'),
('SW_SKETCHUP', 'SketchUp', 'cad'),
('SW_RHINO', 'Rhino', 'cad'),
('SW_ANSYS', 'ANSYS', 'cad'),
('SW_ABAQUS', 'Abaqus', 'cad'),
('SW_MASTERCAM', 'Mastercam', 'cad'),
('SW_HYPERMILL', 'hyperMILL', 'cad'),
('SW_DELCAM', 'Delcam', 'cad')
ON CONFLICT (canonical_id) DO UPDATE SET name = EXCLUDED.name;

-- MES & Production
INSERT INTO software_taxonomy (canonical_id, name, category) VALUES
('SW_SAP_MES', 'SAP MES', 'production'),
('SW_SIEMENS_MES', 'Siemens Opcenter', 'production'),
('SW_ROCKWELL_MES', 'Rockwell MES', 'production'),
('SW_IGNITION', 'Ignition', 'production'),
('SW_WONDERWARE', 'Wonderware', 'production'),
('SW_WINCC', 'WinCC', 'production')
ON CONFLICT (canonical_id) DO UPDATE SET name = EXCLUDED.name;

-- Business Intelligence
INSERT INTO software_taxonomy (canonical_id, name, category) VALUES
('SW_POWER_BI', 'Power BI', 'bi'),
('SW_TABLEAU', 'Tableau', 'bi'),
('SW_QLIK', 'Qlik Sense', 'bi'),
('SW_SAP_BO', 'SAP BusinessObjects', 'bi'),
('SW_LOOKER', 'Looker', 'bi'),
('SW_CRYSTAL_REPORTS', 'Crystal Reports', 'bi')
ON CONFLICT (canonical_id) DO UPDATE SET name = EXCLUDED.name;

-- Digital Marketing
INSERT INTO software_taxonomy (canonical_id, name, category) VALUES
('SW_GOOGLE_ADS', 'Google Ads', 'marketing'),
('SW_META_ADS', 'Meta Ads', 'marketing'),
('SW_GOOGLE_ANALYTICS', 'Google Analytics', 'marketing'),
('SW_SEMRUSH', 'SEMrush', 'marketing'),
('SW_AHREFS', 'Ahrefs', 'marketing'),
('SW_MAILCHIMP', 'Mailchimp', 'marketing'),
('SW_HOOTSUITE', 'Hootsuite', 'marketing'),
('SW_WORDPRESS', 'WordPress', 'marketing'),
('SW_SHOPIFY', 'Shopify', 'marketing'),
('SW_CANVA', 'Canva', 'marketing'),
('SW_ADOBE_CC', 'Adobe Creative Cloud', 'marketing'),
('SW_PHOTOSHOP', 'Adobe Photoshop', 'marketing'),
('SW_ILLUSTRATOR', 'Adobe Illustrator', 'marketing'),
('SW_INDESIGN', 'Adobe InDesign', 'marketing'),
('SW_PREMIERE', 'Adobe Premiere', 'marketing')
ON CONFLICT (canonical_id) DO UPDATE SET name = EXCLUDED.name;

-- Database & Development
INSERT INTO software_taxonomy (canonical_id, name, category) VALUES
('SW_SQL_SERVER', 'SQL Server', 'database'),
('SW_ORACLE_DB', 'Oracle Database', 'database'),
('SW_MYSQL', 'MySQL', 'database'),
('SW_POSTGRESQL', 'PostgreSQL', 'database'),
('SW_MONGODB', 'MongoDB', 'database'),
('SW_PYTHON', 'Python', 'programming'),
('SW_JAVA', 'Java', 'programming'),
('SW_CSHARP', 'C#', 'programming'),
('SW_JAVASCRIPT', 'JavaScript', 'programming'),
('SW_VBA', 'VBA', 'programming'),
('SW_R', 'R', 'programming')
ON CONFLICT (canonical_id) DO UPDATE SET name = EXCLUDED.name;

-- IT Infrastructure
INSERT INTO software_taxonomy (canonical_id, name, category) VALUES
('SW_WINDOWS_SERVER', 'Windows Server', 'it'),
('SW_LINUX', 'Linux', 'it'),
('SW_VMWARE', 'VMware', 'it'),
('SW_HYPER_V', 'Hyper-V', 'it'),
('SW_ACTIVE_DIRECTORY', 'Active Directory', 'it'),
('SW_EXCHANGE', 'Microsoft Exchange', 'it'),
('SW_SHAREPOINT', 'SharePoint', 'it'),
('SW_TEAMS', 'Microsoft Teams', 'collaboration'),
('SW_SLACK', 'Slack', 'collaboration'),
('SW_ZOOM', 'Zoom', 'collaboration'),
('SW_JIRA', 'Jira', 'pm'),
('SW_ASANA', 'Asana', 'pm'),
('SW_MONDAY', 'Monday.com', 'pm'),
('SW_TRELLO', 'Trello', 'pm'),
('SW_MS_PROJECT', 'Microsoft Project', 'pm')
ON CONFLICT (canonical_id) DO UPDATE SET name = EXCLUDED.name;

-- ============================================================================
-- PART 5: SOFT SKILL TAXONOMY
-- ============================================================================

INSERT INTO soft_skill_taxonomy (canonical_id, name_el, name_en, category) VALUES
('SS_LEADERSHIP', 'Ηγεσία', 'Leadership', 'management'),
('SS_TEAM_MGMT', 'Διαχείριση Ομάδας', 'Team Management', 'management'),
('SS_DECISION_MAKING', 'Λήψη Αποφάσεων', 'Decision Making', 'management'),
('SS_STRATEGIC_THINKING', 'Στρατηγική Σκέψη', 'Strategic Thinking', 'management'),
('SS_CHANGE_MGMT', 'Διαχείριση Αλλαγής', 'Change Management', 'management'),
('SS_COMMUNICATION', 'Επικοινωνία', 'Communication', 'interpersonal'),
('SS_PRESENTATION', 'Παρουσιάσεις', 'Presentation Skills', 'interpersonal'),
('SS_NEGOTIATION', 'Διαπραγμάτευση', 'Negotiation', 'interpersonal'),
('SS_CUSTOMER_SERVICE', 'Εξυπηρέτηση Πελατών', 'Customer Service', 'interpersonal'),
('SS_CONFLICT_RESOLUTION', 'Επίλυση Συγκρούσεων', 'Conflict Resolution', 'interpersonal'),
('SS_TEAMWORK', 'Ομαδικότητα', 'Teamwork', 'interpersonal'),
('SS_PROBLEM_SOLVING', 'Επίλυση Προβλημάτων', 'Problem Solving', 'analytical'),
('SS_CRITICAL_THINKING', 'Κριτική Σκέψη', 'Critical Thinking', 'analytical'),
('SS_ANALYTICAL', 'Αναλυτική Ικανότητα', 'Analytical Skills', 'analytical'),
('SS_ATTENTION_DETAIL', 'Προσοχή στη Λεπτομέρεια', 'Attention to Detail', 'analytical'),
('SS_TIME_MGMT', 'Διαχείριση Χρόνου', 'Time Management', 'self'),
('SS_ORGANIZATION', 'Οργάνωση', 'Organization', 'self'),
('SS_PRIORITIZATION', 'Ιεράρχηση Προτεραιοτήτων', 'Prioritization', 'self'),
('SS_SELF_MOTIVATION', 'Αυτοκίνητρο', 'Self-Motivation', 'self'),
('SS_ADAPTABILITY', 'Προσαρμοστικότητα', 'Adaptability', 'self'),
('SS_STRESS_MGMT', 'Διαχείριση Άγχους', 'Stress Management', 'self'),
('SS_MULTITASKING', 'Πολυδιεργασία', 'Multitasking', 'self'),
('SS_CREATIVITY', 'Δημιουργικότητα', 'Creativity', 'innovation'),
('SS_INNOVATION', 'Καινοτομία', 'Innovation', 'innovation'),
('SS_INITIATIVE', 'Πρωτοβουλία', 'Initiative', 'innovation'),
('SS_CONTINUOUS_LEARNING', 'Συνεχής Μάθηση', 'Continuous Learning', 'development'),
('SS_MENTORING', 'Καθοδήγηση', 'Mentoring', 'development'),
('SS_COACHING', 'Coaching', 'Coaching', 'development')
ON CONFLICT (canonical_id) DO UPDATE SET name_el = EXCLUDED.name_el, name_en = EXCLUDED.name_en;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Migration 021_comprehensive_taxonomy.sql completed successfully';
    RAISE NOTICE 'Added: Roles for 11 departments (~180 roles)';
    RAISE NOTICE 'Added: Skills across all categories (~150 skills)';
    RAISE NOTICE 'Added: Certifications (~70 certifications)';
    RAISE NOTICE 'Added: Software applications (~130 applications)';
    RAISE NOTICE 'Added: Soft skills (~28 soft skills)';
END $$;
