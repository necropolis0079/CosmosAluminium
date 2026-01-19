-- =============================================================================
-- Migration: 017_taxonomy_expansion_fixed.sql
-- Purpose: Expand taxonomy tables with ~255 new entries for all departments
-- Date: 2026-01-19
-- Version: 1.1 (Fixed column names to match actual schema)
-- =============================================================================

-- =============================================================================
-- SKILL_TAXONOMY EXPANSION
-- Using correct columns: canonical_id, name_en, name_el, category (enum), aliases_en
-- Category enum values: technical, soft, language, certification, tool, methodology, domain, other
-- =============================================================================

INSERT INTO skill_taxonomy (canonical_id, name_en, name_el, category, aliases_en)
VALUES
-- MANUFACTURING SKILLS (category: technical)
('machine_operation', 'Machine Operation', 'Χειρισμός Μηχανημάτων', 'technical', ARRAY['machine operator', 'μηχανήματα']),
('cnc_operation', 'CNC Operation', 'Χειρισμός CNC', 'technical', ARRAY['cnc machining', 'cnc operator']),
('cnc_programming', 'CNC Programming', 'Προγραμματισμός CNC', 'technical', ARRAY['cnc programmer']),
('plc_programming', 'PLC Programming', 'Προγραμματισμός PLC', 'technical', ARRAY['plc', 'programmable logic']),
('welding_general', 'Welding', 'Συγκόλληση', 'technical', ARRAY['welder', 'συγκολλητής']),
('welding_mig', 'MIG Welding', 'Συγκόλληση MIG', 'technical', ARRAY['mig welder']),
('welding_tig', 'TIG Welding', 'Συγκόλληση TIG', 'technical', ARRAY['tig welder']),
('quality_control', 'Quality Control', 'Ποιοτικός Έλεγχος', 'technical', ARRAY['qc', 'quality assurance', 'qa']),
('assembly_skill', 'Assembly', 'Συναρμολόγηση', 'technical', ARRAY['assembly line', 'assembler']),
('production_planning', 'Production Planning', 'Προγραμματισμός Παραγωγής', 'technical', ARRAY['production scheduler']),
('lean_manufacturing', 'Lean Manufacturing', 'Λιτή Παραγωγή', 'methodology', ARRAY['lean production']),
('5s_methodology', '5S Methodology', 'Μεθοδολογία 5S', 'methodology', ARRAY['5s']),
('kaizen', 'Kaizen', 'Kaizen', 'methodology', ARRAY['continuous improvement']),
('six_sigma_skill', 'Six Sigma', 'Six Sigma', 'methodology', ARRAY['6sigma']),
('spc', 'Statistical Process Control', 'Στατιστικός Έλεγχος Διεργασιών', 'technical', ARRAY['statistical control']),
('preventive_maintenance', 'Preventive Maintenance', 'Προληπτική Συντήρηση', 'technical', ARRAY['maintenance']),
('blueprint_reading', 'Blueprint Reading', 'Ανάγνωση Σχεδίων', 'technical', ARRAY['technical drawings']),
('metal_fabrication', 'Metal Fabrication', 'Μεταλλοκατασκευές', 'technical', ARRAY['metalwork']),
('packaging_skill', 'Packaging', 'Συσκευασία', 'technical', ARRAY['packing']),

-- ACCOUNTING SKILLS (category: domain)
('financial_reporting', 'Financial Reporting', 'Χρηματοοικονομική Αναφορά', 'domain', ARRAY['financial statements']),
('budgeting', 'Budgeting', 'Προϋπολογισμός', 'domain', ARRAY['budget planning']),
('cost_accounting', 'Cost Accounting', 'Κοστολόγηση', 'domain', ARRAY['costing']),
('tax_preparation', 'Tax Preparation', 'Φορολογική Προετοιμασία', 'domain', ARRAY['φορολογία', 'taxation']),
('payroll_skill', 'Payroll', 'Μισθοδοσία', 'domain', ARRAY['payroll processing']),
('accounts_payable', 'Accounts Payable', 'Πληρωτέοι Λογαριασμοί', 'domain', ARRAY['ap', 'creditors']),
('accounts_receivable', 'Accounts Receivable', 'Εισπρακτέοι Λογαριασμοί', 'domain', ARRAY['ar', 'debtors']),
('bank_reconciliation', 'Bank Reconciliation', 'Τραπεζική Συμφωνία', 'domain', ARRAY['reconciliation']),
('ifrs', 'IFRS', 'ΔΠΧΑ', 'domain', ARRAY['international financial reporting standards']),
('greek_gaap', 'Greek GAAP', 'ΕΛΠ', 'domain', ARRAY['ελληνικά λογιστικά πρότυπα']),
('vat_compliance', 'VAT Compliance', 'Συμμόρφωση ΦΠΑ', 'domain', ARRAY['vat', 'φπα']),
('mydata_skill', 'myDATA', 'myDATA', 'domain', ARRAY['ηλεκτρονικά βιβλία']),
('invoicing', 'Invoicing', 'Τιμολόγηση', 'domain', ARRAY['billing']),
('general_ledger', 'General Ledger', 'Γενικό Καθολικό', 'domain', ARRAY['gl']),
('audit_preparation', 'Audit Preparation', 'Προετοιμασία Ελέγχου', 'domain', ARRAY['audit']),

-- IT SKILLS (category: technical)
('network_administration', 'Network Administration', 'Διαχείριση Δικτύων', 'technical', ARRAY['network admin', 'networking']),
('system_administration', 'System Administration', 'Διαχείριση Συστημάτων', 'technical', ARRAY['sysadmin']),
('database_administration', 'Database Administration', 'Διαχείριση Βάσεων Δεδομένων', 'technical', ARRAY['dba']),
('cybersecurity', 'Cybersecurity', 'Κυβερνοασφάλεια', 'technical', ARRAY['security', 'infosec']),
('helpdesk_support', 'Helpdesk Support', 'Υποστήριξη Helpdesk', 'technical', ARRAY['it support', 'technical support']),
('cloud_computing', 'Cloud Computing', 'Υπολογιστικό Νέφος', 'technical', ARRAY['cloud']),
('virtualization', 'Virtualization', 'Εικονικοποίηση', 'technical', ARRAY['virtual machines']),
('python_skill', 'Python', 'Python', 'technical', ARRAY['python programming']),
('sql_skill', 'SQL', 'SQL', 'technical', ARRAY['structured query language']),
('javascript_skill', 'JavaScript', 'JavaScript', 'technical', ARRAY['js']),
('java_skill', 'Java', 'Java', 'technical', ARRAY['java programming']),
('csharp_dotnet', 'C# / .NET', 'C# / .NET', 'technical', ARRAY['c sharp', 'dotnet']),
('api_development', 'API Development', 'Ανάπτυξη API', 'technical', ARRAY['rest api', 'api design']),
('devops_skill', 'DevOps', 'DevOps', 'technical', ARRAY['dev ops']),
('web_development', 'Web Development', 'Ανάπτυξη Ιστοσελίδων', 'technical', ARRAY['web dev']),

-- HR SKILLS (category: domain)
('recruitment', 'Recruitment', 'Προσλήψεις', 'domain', ARRAY['recruiting', 'hiring']),
('talent_acquisition', 'Talent Acquisition', 'Απόκτηση Ταλέντων', 'domain', ARRAY['ta']),
('employee_relations', 'Employee Relations', 'Εργασιακές Σχέσεις', 'domain', ARRAY['er']),
('performance_management', 'Performance Management', 'Διαχείριση Απόδοσης', 'domain', ARRAY['performance review']),
('training_development', 'Training & Development', 'Εκπαίδευση & Ανάπτυξη', 'domain', ARRAY['l&d', 'learning']),
('compensation_benefits', 'Compensation & Benefits', 'Αμοιβές & Παροχές', 'domain', ARRAY['comp & ben', 'c&b']),
('labor_law_greece', 'Greek Labor Law', 'Ελληνικό Εργατικό Δίκαιο', 'domain', ARRAY['εργατικό δίκαιο']),
('onboarding_skill', 'Onboarding', 'Ένταξη Εργαζομένων', 'domain', ARRAY['new hire orientation']),
('gdpr_skill', 'GDPR', 'GDPR', 'domain', ARRAY['data protection']),

-- MARKETING SKILLS (category: domain)
('digital_marketing', 'Digital Marketing', 'Ψηφιακό Μάρκετινγκ', 'domain', ARRAY['online marketing']),
('seo_skill', 'SEO', 'SEO', 'technical', ARRAY['search engine optimization']),
('sem_ppc', 'SEM / PPC', 'SEM / PPC', 'technical', ARRAY['google ads', 'paid search']),
('content_marketing', 'Content Marketing', 'Μάρκετινγκ Περιεχομένου', 'domain', ARRAY['content strategy']),
('social_media_marketing', 'Social Media Marketing', 'Μάρκετινγκ Κοινωνικών Δικτύων', 'domain', ARRAY['smm']),
('email_marketing', 'Email Marketing', 'Email Marketing', 'domain', ARRAY['email campaigns']),
('brand_management', 'Brand Management', 'Διαχείριση Επωνυμίας', 'domain', ARRAY['branding']),
('market_research', 'Market Research', 'Έρευνα Αγοράς', 'domain', ARRAY['market analysis']),
('copywriting', 'Copywriting', 'Copywriting', 'domain', ARRAY['content writing']),
('lead_generation_skill', 'Lead Generation', 'Δημιουργία Leads', 'domain', ARRAY['lead gen']),

-- WAREHOUSE SKILLS (category: technical)
('inventory_management', 'Inventory Management', 'Διαχείριση Αποθέματος', 'technical', ARRAY['stock management']),
('stock_control', 'Stock Control', 'Έλεγχος Αποθέματος', 'technical', ARRAY['inventory control']),
('order_picking', 'Order Picking', 'Picking Παραγγελιών', 'technical', ARRAY['picking', 'pick and pack']),
('goods_receipt', 'Goods Receipt', 'Παραλαβή Εμπορευμάτων', 'technical', ARRAY['receiving']),
('shipping_receiving', 'Shipping & Receiving', 'Αποστολές & Παραλαβές', 'technical', ARRAY['shipping']),
('fifo_lifo', 'FIFO/LIFO', 'FIFO/LIFO', 'methodology', ARRAY['first in first out']),
('cycle_counting', 'Cycle Counting', 'Κυκλική Καταμέτρηση', 'technical', ARRAY['cycle count']),
('barcode_scanning', 'Barcode Scanning', 'Σάρωση Barcode', 'technical', ARRAY['barcode']),
('wms_operation', 'WMS Operation', 'Λειτουργία WMS', 'technical', ARRAY['warehouse management system']),
('rf_scanning', 'RF Scanning', 'Σάρωση RF', 'technical', ARRAY['rf guns', 'rf devices']),
('packaging_warehouse', 'Warehouse Packaging', 'Συσκευασία Αποθήκης', 'technical', ARRAY['packing']),
('loading_unloading', 'Loading/Unloading', 'Φόρτωση/Εκφόρτωση', 'technical', ARRAY['loading dock']),
('route_planning', 'Route Planning', 'Σχεδιασμός Διαδρομών', 'technical', ARRAY['routing']),

-- SALES SKILLS (category: domain)
('b2b_sales', 'B2B Sales', 'Πωλήσεις B2B', 'domain', ARRAY['business to business']),
('b2c_sales', 'B2C Sales', 'Πωλήσεις B2C', 'domain', ARRAY['business to consumer']),
('account_management', 'Account Management', 'Διαχείριση Λογαριασμών', 'domain', ARRAY['account manager']),
('sales_negotiation', 'Sales Negotiation', 'Διαπραγμάτευση Πωλήσεων', 'soft', ARRAY['negotiation']),
('crm_usage', 'CRM Usage', 'Χρήση CRM', 'tool', ARRAY['customer relationship management']),
('sales_forecasting', 'Sales Forecasting', 'Πρόβλεψη Πωλήσεων', 'domain', ARRAY['forecasting']),
('cold_calling', 'Cold Calling', 'Cold Calling', 'domain', ARRAY['telemarketing']),
('proposal_writing', 'Proposal Writing', 'Σύνταξη Προτάσεων', 'domain', ARRAY['rfp']),
('pricing_strategy', 'Pricing Strategy', 'Στρατηγική Τιμολόγησης', 'domain', ARRAY['pricing']),
('territory_management', 'Territory Management', 'Διαχείριση Περιοχής', 'domain', ARRAY['territory']),

-- SECURITY SKILLS (category: technical)
('access_control_skill', 'Access Control', 'Έλεγχος Πρόσβασης', 'technical', ARRAY['access management']),
('cctv_monitoring', 'CCTV Monitoring', 'Παρακολούθηση CCTV', 'technical', ARRAY['surveillance']),
('patrol_procedures', 'Patrol Procedures', 'Διαδικασίες Περιπολίας', 'technical', ARRAY['patrol']),
('incident_reporting', 'Incident Reporting', 'Αναφορά Συμβάντων', 'technical', ARRAY['incident management']),
('emergency_response', 'Emergency Response', 'Απόκριση Έκτακτης Ανάγκης', 'technical', ARRAY['emergency procedures']),
('fire_safety', 'Fire Safety', 'Πυρασφάλεια', 'technical', ARRAY['fire prevention']),
('first_aid_skill', 'First Aid', 'Πρώτες Βοήθειες', 'technical', ARRAY['cpr']),
('crowd_control', 'Crowd Control', 'Έλεγχος Πλήθους', 'technical', ARRAY['crowd management']),
('physical_security', 'Physical Security', 'Φυσική Ασφάλεια', 'technical', ARRAY['security']),

-- GENERAL SKILLS
('forklift_operation', 'Forklift Operation', 'Χειρισμός Περονοφόρου', 'technical', ARRAY['forklift driver', 'κλαρκ']),
('crane_operation', 'Crane Operation', 'Χειρισμός Γερανού', 'technical', ARRAY['crane operator', 'γερανός'])
ON CONFLICT (canonical_id) DO UPDATE SET
    name_en = EXCLUDED.name_en,
    name_el = EXCLUDED.name_el,
    aliases_en = EXCLUDED.aliases_en;

-- =============================================================================
-- SOFT_SKILL_TAXONOMY EXPANSION
-- Using correct columns: canonical_id, name_en, name_el, category, aliases_en
-- =============================================================================

INSERT INTO soft_skill_taxonomy (canonical_id, name_en, name_el, category, aliases_en)
VALUES
('communication_skill', 'Communication', 'Επικοινωνία', 'interpersonal', ARRAY['communicative']),
('teamwork_skill', 'Teamwork', 'Ομαδικότητα', 'interpersonal', ARRAY['team player', 'collaboration']),
('leadership_skill', 'Leadership', 'Ηγεσία', 'management', ARRAY['leading', 'team lead']),
('problem_solving_skill', 'Problem Solving', 'Επίλυση Προβλημάτων', 'analytical', ARRAY['troubleshooting']),
('critical_thinking', 'Critical Thinking', 'Κριτική Σκέψη', 'analytical', ARRAY['analysis']),
('time_management_skill', 'Time Management', 'Διαχείριση Χρόνου', 'organizational', ARRAY['punctuality']),
('adaptability_skill', 'Adaptability', 'Προσαρμοστικότητα', 'personal', ARRAY['flexible', 'flexibility']),
('attention_to_detail', 'Attention to Detail', 'Προσοχή στη Λεπτομέρεια', 'personal', ARRAY['detail oriented']),
('work_under_pressure', 'Work Under Pressure', 'Εργασία Υπό Πίεση', 'personal', ARRAY['stress management']),
('initiative_skill', 'Initiative', 'Πρωτοβουλία', 'personal', ARRAY['proactive']),
('reliability_skill', 'Reliability', 'Αξιοπιστία', 'personal', ARRAY['dependable']),
('customer_service_skill', 'Customer Service', 'Εξυπηρέτηση Πελατών', 'interpersonal', ARRAY['customer oriented']),
('conflict_resolution', 'Conflict Resolution', 'Επίλυση Συγκρούσεων', 'interpersonal', ARRAY['mediation']),
('creativity_skill', 'Creativity', 'Δημιουργικότητα', 'analytical', ARRAY['creative thinking']),
('emotional_intelligence', 'Emotional Intelligence', 'Συναισθηματική Νοημοσύνη', 'interpersonal', ARRAY['eq'])
ON CONFLICT (canonical_id) DO UPDATE SET
    name_en = EXCLUDED.name_en,
    name_el = EXCLUDED.name_el,
    aliases_en = EXCLUDED.aliases_en;

-- =============================================================================
-- SOFTWARE_TAXONOMY EXPANSION
-- Using correct columns: canonical_id, name, vendor, category, aliases
-- =============================================================================

INSERT INTO software_taxonomy (canonical_id, name, vendor, category, aliases)
VALUES
-- ERP Systems
('sap_erp', 'SAP ERP', 'SAP', 'erp', ARRAY['sap', 'sap r/3']),
('oracle_erp', 'Oracle ERP', 'Oracle', 'erp', ARRAY['oracle e-business']),
('ms_dynamics', 'Microsoft Dynamics', 'Microsoft', 'erp', ARRAY['dynamics 365', 'ax', 'nav']),
('softone_erp', 'SoftOne', 'SoftOne', 'erp', ARRAY['soft1']),
('entersoft_erp', 'Entersoft', 'Entersoft', 'erp', ARRAY['entersoft business suite']),
('atlantis_erp', 'Atlantis ERP', 'Atlantis', 'erp', ARRAY['atlantis']),
('pylon_erp', 'Pylon', 'Epsilon Net', 'erp', ARRAY['epsilon pylon']),

-- CAD Software
('autocad', 'AutoCAD', 'Autodesk', 'cad', ARRAY['acad']),
('solidworks', 'SolidWorks', 'Dassault', 'cad', ARRAY['solid works']),
('inventor', 'Inventor', 'Autodesk', 'cad', ARRAY['autodesk inventor']),
('catia', 'CATIA', 'Dassault', 'cad', ARRAY['catia v5']),
('fusion360', 'Fusion 360', 'Autodesk', 'cad', ARRAY['fusion']),
('creo', 'PTC Creo', 'PTC', 'cad', ARRAY['pro/engineer', 'creo parametric']),

-- Office Software
('ms_excel', 'Microsoft Excel', 'Microsoft', 'office', ARRAY['excel', 'spreadsheet']),
('ms_word', 'Microsoft Word', 'Microsoft', 'office', ARRAY['word']),
('ms_powerpoint', 'Microsoft PowerPoint', 'Microsoft', 'office', ARRAY['powerpoint', 'ppt']),
('ms_outlook', 'Microsoft Outlook', 'Microsoft', 'office', ARRAY['outlook', 'email']),
('ms_teams', 'Microsoft Teams', 'Microsoft', 'office', ARRAY['teams']),
('google_sheets', 'Google Sheets', 'Google', 'office', ARRAY['gsheets']),
('google_docs', 'Google Docs', 'Google', 'office', ARRAY['gdocs']),

-- Accounting Software
('mydata_software', 'myDATA', 'AADE', 'accounting', ARRAY['ηλεκτρονικά βιβλία aade']),
('ergani', 'ERGANI', 'Ministry of Labor', 'accounting', ARRAY['εργάνη']),
('taxisnet', 'TAXISnet', 'AADE', 'accounting', ARRAY['taxis']),
('galaxy', 'Galaxy', 'Galaxy', 'accounting', ARRAY['galaxy erp']),
('singular', 'Singular', 'Singular Logic', 'accounting', ARRAY['singular logic']),

-- Database
('mysql_db', 'MySQL', 'Oracle', 'database', ARRAY['mysql database']),
('postgresql', 'PostgreSQL', 'PostgreSQL', 'database', ARRAY['postgres']),
('mssql', 'Microsoft SQL Server', 'Microsoft', 'database', ARRAY['sql server']),
('oracle_db', 'Oracle Database', 'Oracle', 'database', ARRAY['oracle db']),
('mongodb', 'MongoDB', 'MongoDB', 'database', ARRAY['mongo']),

-- WMS
('sap_ewm', 'SAP EWM', 'SAP', 'wms', ARRAY['extended warehouse management']),
('manhattan_wms', 'Manhattan WMS', 'Manhattan Associates', 'wms', ARRAY['manhattan']),
('infor_wms', 'Infor WMS', 'Infor', 'wms', ARRAY['infor warehouse']),

-- CRM
('salesforce', 'Salesforce', 'Salesforce', 'crm', ARRAY['sfdc']),
('hubspot', 'HubSpot', 'HubSpot', 'crm', ARRAY['hubspot crm']),
('zoho_crm', 'Zoho CRM', 'Zoho', 'crm', ARRAY['zoho']),

-- Design
('adobe_photoshop', 'Adobe Photoshop', 'Adobe', 'design', ARRAY['photoshop', 'ps']),
('adobe_illustrator', 'Adobe Illustrator', 'Adobe', 'design', ARRAY['illustrator', 'ai']),
('adobe_indesign', 'Adobe InDesign', 'Adobe', 'design', ARRAY['indesign']),
('canva', 'Canva', 'Canva', 'design', ARRAY['canva design']),
('figma', 'Figma', 'Figma', 'design', ARRAY['figma design']),

-- BI Tools
('power_bi', 'Power BI', 'Microsoft', 'analytics', ARRAY['powerbi']),
('tableau', 'Tableau', 'Salesforce', 'analytics', ARRAY['tableau desktop']),
('qlik', 'Qlik Sense', 'Qlik', 'analytics', ARRAY['qlikview']),

-- Project Management
('jira', 'Jira', 'Atlassian', 'project_management', ARRAY['jira software']),
('trello', 'Trello', 'Atlassian', 'project_management', ARRAY['trello board']),
('asana', 'Asana', 'Asana', 'project_management', ARRAY['asana pm']),
('ms_project', 'Microsoft Project', 'Microsoft', 'project_management', ARRAY['ms project'])
ON CONFLICT (canonical_id) DO UPDATE SET
    name = EXCLUDED.name,
    vendor = EXCLUDED.vendor,
    category = EXCLUDED.category,
    aliases = EXCLUDED.aliases;

-- =============================================================================
-- CERTIFICATION_TAXONOMY EXPANSION
-- Using correct columns: canonical_id, name_en, name_el, issuing_organization, category, aliases
-- =============================================================================

INSERT INTO certification_taxonomy (canonical_id, name_en, name_el, issuing_organization, category, aliases)
VALUES
-- Greek Accounting Certifications
('logistis_a', 'Accountant Class A', 'Λογιστής Α Τάξης', 'ΟΕΕ', 'accounting', ARRAY['λογιστής α', 'class a accountant']),
('logistis_b', 'Accountant Class B', 'Λογιστής Β Τάξης', 'ΟΕΕ', 'accounting', ARRAY['λογιστής β', 'class b accountant']),
('logistis_g', 'Accountant Class C', 'Λογιστής Γ Τάξης', 'ΟΕΕ', 'accounting', ARRAY['λογιστής γ', 'class c accountant']),
('soel_cert', 'SOEL Membership', 'Μέλος ΣΟΕΛ', 'ΣΟΕΛ', 'accounting', ARRAY['σοελ', 'certified auditor']),

-- Manufacturing Certifications
('iso_9001_cert', 'ISO 9001 Auditor', 'Επιθεωρητής ISO 9001', 'ISO', 'quality', ARRAY['quality management']),
('iso_14001_cert', 'ISO 14001 Auditor', 'Επιθεωρητής ISO 14001', 'ISO', 'quality', ARRAY['environmental management']),
('iso_45001_cert', 'ISO 45001 Auditor', 'Επιθεωρητής ISO 45001', 'ISO', 'safety', ARRAY['occupational health safety']),
('six_sigma_green', 'Six Sigma Green Belt', 'Six Sigma Green Belt', 'ASQ', 'quality', ARRAY['green belt']),
('six_sigma_black', 'Six Sigma Black Belt', 'Six Sigma Black Belt', 'ASQ', 'quality', ARRAY['black belt']),
('welding_en287', 'Welding Certificate EN 287-1', 'Πιστοποίηση Συγκολλητή EN 287-1', 'TÜV', 'technical', ARRAY['en 287', 'welder cert']),

-- IT Certifications
('aws_solutions_architect', 'AWS Solutions Architect', 'AWS Solutions Architect', 'Amazon', 'cloud', ARRAY['aws sa']),
('aws_developer', 'AWS Developer', 'AWS Developer', 'Amazon', 'cloud', ARRAY['aws dev']),
('azure_fundamentals', 'Azure Fundamentals', 'Azure Fundamentals', 'Microsoft', 'cloud', ARRAY['az-900']),
('azure_administrator', 'Azure Administrator', 'Azure Administrator', 'Microsoft', 'cloud', ARRAY['az-104']),
('ccna', 'Cisco CCNA', 'Cisco CCNA', 'Cisco', 'networking', ARRAY['ccna routing switching']),
('comptia_a', 'CompTIA A+', 'CompTIA A+', 'CompTIA', 'it', ARRAY['a plus']),
('comptia_network', 'CompTIA Network+', 'CompTIA Network+', 'CompTIA', 'networking', ARRAY['network plus']),
('comptia_security', 'CompTIA Security+', 'CompTIA Security+', 'CompTIA', 'security', ARRAY['security plus']),
('itil_foundation', 'ITIL Foundation', 'ITIL Foundation', 'AXELOS', 'it', ARRAY['itil v4']),
('pmp_cert', 'PMP', 'PMP', 'PMI', 'project_management', ARRAY['project management professional']),
('scrum_master', 'Certified Scrum Master', 'Certified Scrum Master', 'Scrum Alliance', 'project_management', ARRAY['csm']),

-- Safety Certifications
('osha_10', 'OSHA 10-Hour', 'OSHA 10 Ωρών', 'OSHA', 'safety', ARRAY['osha 10']),
('osha_30', 'OSHA 30-Hour', 'OSHA 30 Ωρών', 'OSHA', 'safety', ARRAY['osha 30']),
('first_aid_cert', 'First Aid Certificate', 'Πιστοποίηση Πρώτων Βοηθειών', 'Red Cross', 'safety', ARRAY['first aid', 'πρώτες βοήθειες']),
('fire_safety_cert', 'Fire Safety Certificate', 'Πιστοποίηση Πυρασφάλειας', 'Various', 'safety', ARRAY['fire warden']),
('health_safety_officer', 'Health & Safety Officer', 'Τεχνικός Ασφαλείας', 'Ministry of Labor', 'safety', ARRAY['τεχνικός ασφάλειας', 'hse']),

-- Greek Educational Certifications
('tee_diploma', 'TEE Diploma', 'Δίπλωμα ΤΕΕ', 'TEE', 'vocational', ARRAY['τεε', 'technical school']),
('oee_membership', 'OEE Membership', 'Μέλος ΟΕΕ', 'ΟΕΕ', 'accounting', ARRAY['οεε', 'economic chamber']),
('tee_membership', 'TEE Membership', 'Μέλος ΤΕΕ', 'ΤΕΕ', 'engineering', ARRAY['technical chamber']),
('ecdl_cert', 'ECDL', 'ECDL', 'ECDL Foundation', 'it', ARRAY['european computer driving licence']),

-- Marketing Certifications
('google_ads_cert', 'Google Ads Certification', 'Πιστοποίηση Google Ads', 'Google', 'marketing', ARRAY['adwords']),
('google_analytics_cert', 'Google Analytics Certification', 'Πιστοποίηση Google Analytics', 'Google', 'marketing', ARRAY['ga cert']),
('facebook_blueprint', 'Meta Blueprint', 'Meta Blueprint', 'Meta', 'marketing', ARRAY['facebook blueprint']),
('hubspot_inbound', 'HubSpot Inbound', 'HubSpot Inbound', 'HubSpot', 'marketing', ARRAY['inbound marketing']),

-- HR Certifications
('shrm_cp', 'SHRM-CP', 'SHRM-CP', 'SHRM', 'hr', ARRAY['shrm certified professional']),
('cipd', 'CIPD', 'CIPD', 'CIPD', 'hr', ARRAY['chartered institute personnel development']),

-- Forklift and Equipment
('forklift_license', 'Forklift License', 'Άδεια Χειριστή Περονοφόρου', 'Ministry of Labor', 'equipment', ARRAY['δίπλωμα κλαρκ', 'forklift cert']),
('crane_license', 'Crane Operator License', 'Άδεια Γερανοδηγού', 'Ministry of Labor', 'equipment', ARRAY['γερανός', 'crane cert'])
ON CONFLICT (canonical_id) DO UPDATE SET
    name_en = EXCLUDED.name_en,
    name_el = EXCLUDED.name_el,
    issuing_organization = EXCLUDED.issuing_organization,
    category = EXCLUDED.category,
    aliases = EXCLUDED.aliases;

-- =============================================================================
-- ROLE_TAXONOMY EXPANSION
-- Using correct columns: canonical_id, name_en, name_el, department, experience_level, aliases_en
-- experience_level enum: entry, junior, mid, senior, lead, manager, director, executive
-- =============================================================================

INSERT INTO role_taxonomy (canonical_id, name_en, name_el, department, experience_level, aliases_en)
VALUES
-- Manufacturing Roles
('production_manager', 'Production Manager', 'Διευθυντής Παραγωγής', 'manufacturing', 'manager', ARRAY['plant manager']),
('production_supervisor', 'Production Supervisor', 'Επόπτης Παραγωγής', 'manufacturing', 'senior', ARRAY['line supervisor']),
('machine_operator', 'Machine Operator', 'Χειριστής Μηχανημάτων', 'manufacturing', 'mid', ARRAY['operator']),
('cnc_operator', 'CNC Operator', 'Χειριστής CNC', 'manufacturing', 'mid', ARRAY['cnc machinist']),
('quality_inspector', 'Quality Inspector', 'Επιθεωρητής Ποιότητας', 'manufacturing', 'mid', ARRAY['qc inspector']),
('quality_engineer', 'Quality Engineer', 'Μηχανικός Ποιότητας', 'manufacturing', 'mid', ARRAY['quality assurance engineer']),
('maintenance_technician', 'Maintenance Technician', 'Τεχνικός Συντήρησης', 'manufacturing', 'mid', ARRAY['maintenance mechanic']),
('welder_role', 'Welder', 'Συγκολλητής', 'manufacturing', 'mid', ARRAY['welding technician']),
('assembly_worker', 'Assembly Worker', 'Εργάτης Συναρμολόγησης', 'manufacturing', 'entry', ARRAY['assembler']),
('production_planner', 'Production Planner', 'Υπεύθυνος Προγραμματισμού Παραγωγής', 'manufacturing', 'senior', ARRAY['scheduler']),

-- Accounting Roles
('financial_controller', 'Financial Controller', 'Οικονομικός Διευθυντής', 'accounting', 'director', ARRAY['controller']),
('chief_accountant', 'Chief Accountant', 'Προϊστάμενος Λογιστηρίου', 'accounting', 'senior', ARRAY['head accountant']),
('accountant_role', 'Accountant', 'Λογιστής', 'accounting', 'mid', ARRAY['bookkeeper']),
('junior_accountant', 'Junior Accountant', 'Βοηθός Λογιστή', 'accounting', 'junior', ARRAY['accounting assistant']),
('payroll_specialist', 'Payroll Specialist', 'Υπεύθυνος Μισθοδοσίας', 'accounting', 'mid', ARRAY['payroll administrator']),
('tax_accountant', 'Tax Accountant', 'Φορολογικός Σύμβουλος', 'accounting', 'senior', ARRAY['tax specialist']),
('financial_analyst', 'Financial Analyst', 'Οικονομικός Αναλυτής', 'accounting', 'mid', ARRAY['finance analyst']),

-- IT Roles
('it_manager', 'IT Manager', 'Διευθυντής IT', 'it', 'manager', ARRAY['it director']),
('system_administrator', 'System Administrator', 'Διαχειριστής Συστημάτων', 'it', 'mid', ARRAY['sysadmin']),
('network_engineer', 'Network Engineer', 'Μηχανικός Δικτύων', 'it', 'mid', ARRAY['network administrator']),
('software_developer', 'Software Developer', 'Προγραμματιστής', 'it', 'mid', ARRAY['developer', 'programmer']),
('helpdesk_technician', 'Helpdesk Technician', 'Τεχνικός Helpdesk', 'it', 'junior', ARRAY['it support']),
('database_administrator', 'Database Administrator', 'Διαχειριστής Βάσεων Δεδομένων', 'it', 'senior', ARRAY['dba']),

-- HR Roles
('hr_manager', 'HR Manager', 'Διευθυντής Ανθρώπινου Δυναμικού', 'hr', 'manager', ARRAY['hr director']),
('hr_specialist', 'HR Specialist', 'Υπεύθυνος HR', 'hr', 'mid', ARRAY['hr generalist']),
('recruiter', 'Recruiter', 'Υπεύθυνος Προσλήψεων', 'hr', 'mid', ARRAY['talent acquisition']),
('training_coordinator', 'Training Coordinator', 'Συντονιστής Εκπαίδευσης', 'hr', 'mid', ARRAY['training specialist']),
('hr_assistant', 'HR Assistant', 'Βοηθός HR', 'hr', 'junior', ARRAY['hr admin']),

-- Warehouse Roles
('warehouse_manager', 'Warehouse Manager', 'Διευθυντής Αποθήκης', 'warehouse', 'manager', ARRAY['logistics manager']),
('warehouse_supervisor', 'Warehouse Supervisor', 'Επόπτης Αποθήκης', 'warehouse', 'senior', ARRAY['shift supervisor']),
('forklift_operator', 'Forklift Operator', 'Χειριστής Κλαρκ', 'warehouse', 'mid', ARRAY['forklift driver']),
('warehouse_worker', 'Warehouse Worker', 'Εργάτης Αποθήκης', 'warehouse', 'entry', ARRAY['warehouse associate']),
('inventory_clerk', 'Inventory Clerk', 'Υπάλληλος Αποθέματος', 'warehouse', 'junior', ARRAY['stock clerk']),
('shipping_coordinator', 'Shipping Coordinator', 'Συντονιστής Αποστολών', 'warehouse', 'mid', ARRAY['logistics coordinator'])
ON CONFLICT (canonical_id) DO UPDATE SET
    name_en = EXCLUDED.name_en,
    name_el = EXCLUDED.name_el,
    department = EXCLUDED.department,
    experience_level = EXCLUDED.experience_level,
    aliases_en = EXCLUDED.aliases_en;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

DO $$
DECLARE
    skill_count INTEGER;
    soft_skill_count INTEGER;
    cert_count INTEGER;
    software_count INTEGER;
    role_count INTEGER;
    total_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO skill_count FROM skill_taxonomy;
    SELECT COUNT(*) INTO soft_skill_count FROM soft_skill_taxonomy;
    SELECT COUNT(*) INTO cert_count FROM certification_taxonomy;
    SELECT COUNT(*) INTO software_count FROM software_taxonomy;
    SELECT COUNT(*) INTO role_count FROM role_taxonomy;

    total_count := skill_count + soft_skill_count + cert_count + software_count + role_count;

    RAISE NOTICE 'Taxonomy counts after expansion:';
    RAISE NOTICE '  skill_taxonomy: %', skill_count;
    RAISE NOTICE '  soft_skill_taxonomy: %', soft_skill_count;
    RAISE NOTICE '  certification_taxonomy: %', cert_count;
    RAISE NOTICE '  software_taxonomy: %', software_count;
    RAISE NOTICE '  role_taxonomy: %', role_count;
    RAISE NOTICE '  TOTAL: %', total_count;
    RAISE NOTICE 'Migration 017_taxonomy_expansion_fixed.sql completed successfully';
END $$;
