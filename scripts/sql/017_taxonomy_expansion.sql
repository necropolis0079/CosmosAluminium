-- =============================================================================
-- Migration: 017_taxonomy_expansion.sql
-- Purpose: Expand taxonomy tables with ~255 new entries for all departments
-- Date: 2026-01-19
-- Version: 1.0
-- Departments: Manufacturing, Accounting, IT, HR, Marketing, Warehouse, Sales, Security
-- =============================================================================

-- =============================================================================
-- SKILL_TAXONOMY EXPANSION (~80 new entries)
-- =============================================================================

INSERT INTO skill_taxonomy (canonical_id, name_en, name_el, category, aliases)
VALUES
-- MANUFACTURING SKILLS
('machine_operation', 'Machine Operation', 'Χειρισμός Μηχανημάτων', 'manufacturing', ARRAY['machine operator', 'μηχανήματα']),
('cnc_operation', 'CNC Operation', 'Χειρισμός CNC', 'manufacturing', ARRAY['cnc machining', 'cnc operator']),
('cnc_programming', 'CNC Programming', 'Προγραμματισμός CNC', 'manufacturing', ARRAY['cnc programmer']),
('plc_programming', 'PLC Programming', 'Προγραμματισμός PLC', 'manufacturing', ARRAY['plc', 'programmable logic']),
('welding', 'Welding', 'Συγκόλληση', 'manufacturing', ARRAY['welder', 'συγκολλητής']),
('welding_mig', 'MIG Welding', 'Συγκόλληση MIG', 'manufacturing', ARRAY['mig welder']),
('welding_tig', 'TIG Welding', 'Συγκόλληση TIG', 'manufacturing', ARRAY['tig welder']),
('quality_control', 'Quality Control', 'Ποιοτικός Έλεγχος', 'manufacturing', ARRAY['qc', 'quality assurance', 'qa']),
('assembly', 'Assembly', 'Συναρμολόγηση', 'manufacturing', ARRAY['assembly line', 'assembler']),
('production_planning', 'Production Planning', 'Προγραμματισμός Παραγωγής', 'manufacturing', ARRAY['production scheduler']),
('lean_manufacturing', 'Lean Manufacturing', 'Λιτή Παραγωγή', 'manufacturing', ARRAY['lean production']),
('5s_methodology', '5S Methodology', 'Μεθοδολογία 5S', 'manufacturing', ARRAY['5s']),
('kaizen', 'Kaizen', 'Kaizen', 'manufacturing', ARRAY['continuous improvement']),
('six_sigma_skill', 'Six Sigma', 'Six Sigma', 'manufacturing', ARRAY['6sigma']),
('spc', 'Statistical Process Control', 'Στατιστικός Έλεγχος Διεργασιών', 'manufacturing', ARRAY['statistical control']),
('preventive_maintenance', 'Preventive Maintenance', 'Προληπτική Συντήρηση', 'manufacturing', ARRAY['maintenance']),
('blueprint_reading', 'Blueprint Reading', 'Ανάγνωση Σχεδίων', 'manufacturing', ARRAY['technical drawings']),
('metal_fabrication', 'Metal Fabrication', 'Μεταλλοκατασκευές', 'manufacturing', ARRAY['metalwork']),
('packaging_skill', 'Packaging', 'Συσκευασία', 'manufacturing', ARRAY['packing']),

-- ACCOUNTING SKILLS
('financial_reporting', 'Financial Reporting', 'Χρηματοοικονομική Αναφορά', 'accounting', ARRAY['financial statements']),
('budgeting', 'Budgeting', 'Προϋπολογισμός', 'accounting', ARRAY['budget planning']),
('cost_accounting', 'Cost Accounting', 'Κοστολόγηση', 'accounting', ARRAY['costing']),
('tax_preparation', 'Tax Preparation', 'Φορολογική Προετοιμασία', 'accounting', ARRAY['φορολογία', 'taxation']),
('payroll', 'Payroll', 'Μισθοδοσία', 'accounting', ARRAY['payroll processing']),
('accounts_payable', 'Accounts Payable', 'Πληρωτέοι Λογαριασμοί', 'accounting', ARRAY['ap', 'creditors']),
('accounts_receivable', 'Accounts Receivable', 'Εισπρακτέοι Λογαριασμοί', 'accounting', ARRAY['ar', 'debtors']),
('bank_reconciliation', 'Bank Reconciliation', 'Τραπεζική Συμφωνία', 'accounting', ARRAY['reconciliation']),
('ifrs', 'IFRS', 'ΔΠΧΑ', 'accounting', ARRAY['international financial reporting standards']),
('greek_gaap', 'Greek GAAP', 'ΕΛΠ', 'accounting', ARRAY['ελληνικά λογιστικά πρότυπα']),
('vat_compliance', 'VAT Compliance', 'Συμμόρφωση ΦΠΑ', 'accounting', ARRAY['vat', 'φπα']),
('mydata', 'myDATA', 'myDATA', 'accounting', ARRAY['ηλεκτρονικά βιβλία']),
('invoicing', 'Invoicing', 'Τιμολόγηση', 'accounting', ARRAY['billing']),
('general_ledger', 'General Ledger', 'Γενικό Καθολικό', 'accounting', ARRAY['gl']),
('audit_preparation', 'Audit Preparation', 'Προετοιμασία Ελέγχου', 'accounting', ARRAY['audit']),

-- IT SKILLS
('network_administration', 'Network Administration', 'Διαχείριση Δικτύων', 'it', ARRAY['network admin', 'networking']),
('system_administration', 'System Administration', 'Διαχείριση Συστημάτων', 'it', ARRAY['sysadmin']),
('database_administration', 'Database Administration', 'Διαχείριση Βάσεων Δεδομένων', 'it', ARRAY['dba']),
('cybersecurity', 'Cybersecurity', 'Κυβερνοασφάλεια', 'it', ARRAY['security', 'infosec']),
('helpdesk_support', 'Helpdesk Support', 'Υποστήριξη Helpdesk', 'it', ARRAY['it support', 'technical support']),
('cloud_computing', 'Cloud Computing', 'Υπολογιστικό Νέφος', 'it', ARRAY['cloud']),
('virtualization', 'Virtualization', 'Εικονικοποίηση', 'it', ARRAY['virtual machines']),
('python', 'Python', 'Python', 'programming', ARRAY['python programming']),
('sql_skill', 'SQL', 'SQL', 'programming', ARRAY['structured query language']),
('javascript', 'JavaScript', 'JavaScript', 'programming', ARRAY['js']),
('java', 'Java', 'Java', 'programming', ARRAY['java programming']),
('csharp_dotnet', 'C# / .NET', 'C# / .NET', 'programming', ARRAY['c sharp', 'dotnet']),
('api_development', 'API Development', 'Ανάπτυξη API', 'programming', ARRAY['rest api', 'api design']),
('devops', 'DevOps', 'DevOps', 'it', ARRAY['dev ops']),
('web_development', 'Web Development', 'Ανάπτυξη Ιστοσελίδων', 'programming', ARRAY['web dev']),

-- HR SKILLS
('recruitment', 'Recruitment', 'Προσλήψεις', 'hr', ARRAY['recruiting', 'hiring']),
('talent_acquisition', 'Talent Acquisition', 'Απόκτηση Ταλέντων', 'hr', ARRAY['ta']),
('employee_relations', 'Employee Relations', 'Εργασιακές Σχέσεις', 'hr', ARRAY['er']),
('performance_management', 'Performance Management', 'Διαχείριση Απόδοσης', 'hr', ARRAY['performance review']),
('training_development', 'Training & Development', 'Εκπαίδευση & Ανάπτυξη', 'hr', ARRAY['l&d', 'learning']),
('compensation_benefits', 'Compensation & Benefits', 'Αμοιβές & Παροχές', 'hr', ARRAY['comp & ben', 'c&b']),
('labor_law_greece', 'Greek Labor Law', 'Ελληνικό Εργατικό Δίκαιο', 'hr', ARRAY['εργατικό δίκαιο']),
('onboarding', 'Onboarding', 'Ένταξη Εργαζομένων', 'hr', ARRAY['new hire orientation']),
('gdpr_skill', 'GDPR', 'GDPR', 'hr', ARRAY['data protection']),

-- MARKETING SKILLS
('digital_marketing', 'Digital Marketing', 'Ψηφιακό Μάρκετινγκ', 'marketing', ARRAY['online marketing']),
('seo', 'SEO', 'SEO', 'marketing', ARRAY['search engine optimization']),
('sem_ppc', 'SEM / PPC', 'SEM / PPC', 'marketing', ARRAY['google ads', 'paid search']),
('content_marketing', 'Content Marketing', 'Μάρκετινγκ Περιεχομένου', 'marketing', ARRAY['content strategy']),
('social_media_marketing', 'Social Media Marketing', 'Μάρκετινγκ Κοινωνικών Δικτύων', 'marketing', ARRAY['smm']),
('email_marketing', 'Email Marketing', 'Email Marketing', 'marketing', ARRAY['email campaigns']),
('brand_management', 'Brand Management', 'Διαχείριση Επωνυμίας', 'marketing', ARRAY['branding']),
('market_research', 'Market Research', 'Έρευνα Αγοράς', 'marketing', ARRAY['market analysis']),
('copywriting', 'Copywriting', 'Copywriting', 'marketing', ARRAY['content writing']),
('lead_generation_skill', 'Lead Generation', 'Δημιουργία Leads', 'marketing', ARRAY['lead gen']),

-- WAREHOUSE SKILLS
('inventory_management', 'Inventory Management', 'Διαχείριση Αποθέματος', 'warehouse', ARRAY['stock management']),
('stock_control', 'Stock Control', 'Έλεγχος Αποθέματος', 'warehouse', ARRAY['inventory control']),
('order_picking', 'Order Picking', 'Picking Παραγγελιών', 'warehouse', ARRAY['picking', 'pick and pack']),
('goods_receipt', 'Goods Receipt', 'Παραλαβή Εμπορευμάτων', 'warehouse', ARRAY['receiving']),
('shipping_receiving', 'Shipping & Receiving', 'Αποστολές & Παραλαβές', 'warehouse', ARRAY['shipping']),
('fifo_lifo', 'FIFO/LIFO', 'FIFO/LIFO', 'warehouse', ARRAY['first in first out']),
('cycle_counting', 'Cycle Counting', 'Κυκλική Καταμέτρηση', 'warehouse', ARRAY['cycle count']),
('rf_scanning', 'RF Scanning', 'RF Scanning', 'warehouse', ARRAY['barcode scanning']),
('logistics', 'Logistics', 'Εφοδιαστική', 'warehouse', ARRAY['logistics management']),
('supply_chain', 'Supply Chain', 'Εφοδιαστική Αλυσίδα', 'warehouse', ARRAY['scm']),
('distribution', 'Distribution', 'Διανομή', 'warehouse', ARRAY['distribution management']),
('dispatching', 'Dispatching', 'Αποστολή', 'warehouse', ARRAY['dispatch']),
('warehouse_layout', 'Warehouse Layout', 'Διάταξη Αποθήκης', 'warehouse', ARRAY['warehouse organization']),

-- SALES SKILLS
('b2b_sales', 'B2B Sales', 'Πωλήσεις B2B', 'sales', ARRAY['business to business']),
('b2c_sales', 'B2C Sales', 'Πωλήσεις B2C', 'sales', ARRAY['retail sales']),
('account_management', 'Account Management', 'Διαχείριση Λογαριασμών', 'sales', ARRAY['account manager']),
('key_account_management', 'Key Account Management', 'Διαχείριση Κύριων Λογαριασμών', 'sales', ARRAY['kam']),
('business_development', 'Business Development', 'Ανάπτυξη Επιχειρήσεων', 'sales', ARRAY['biz dev']),
('sales_forecasting', 'Sales Forecasting', 'Πρόβλεψη Πωλήσεων', 'sales', ARRAY['forecasting']),
('pipeline_management', 'Pipeline Management', 'Διαχείριση Pipeline', 'sales', ARRAY['sales pipeline']),
('territory_management', 'Territory Management', 'Διαχείριση Περιοχής', 'sales', ARRAY['territory']),
('solution_selling', 'Solution Selling', 'Πώληση Λύσεων', 'sales', ARRAY['consultative selling']),
('contract_negotiation', 'Contract Negotiation', 'Διαπραγμάτευση Συμβολαίων', 'sales', ARRAY['negotiation']),

-- SECURITY SKILLS
('physical_security', 'Physical Security', 'Φυσική Ασφάλεια', 'security', ARRAY['site security']),
('access_control_skill', 'Access Control', 'Έλεγχος Πρόσβασης', 'security', ARRAY['entry control']),
('cctv_monitoring', 'CCTV Monitoring', 'Παρακολούθηση CCTV', 'security', ARRAY['surveillance']),
('patrol', 'Patrol Operations', 'Περιπολίες', 'security', ARRAY['patrolling']),
('incident_response', 'Incident Response', 'Αντιμετώπιση Περιστατικών', 'security', ARRAY['incident management']),
('emergency_procedures', 'Emergency Procedures', 'Διαδικασίες Έκτακτης Ανάγκης', 'security', ARRAY['emergency response']),
('fire_safety_skill', 'Fire Safety', 'Πυρασφάλεια', 'security', ARRAY['fire prevention']),
('loss_prevention', 'Loss Prevention', 'Πρόληψη Απωλειών', 'security', ARRAY['lp']),
('evacuation', 'Evacuation Procedures', 'Διαδικασίες Εκκένωσης', 'security', ARRAY['emergency evacuation'])

ON CONFLICT (canonical_id) DO UPDATE SET
    name_en = EXCLUDED.name_en,
    name_el = EXCLUDED.name_el,
    category = EXCLUDED.category,
    aliases = EXCLUDED.aliases,
    updated_at = CURRENT_TIMESTAMP;

-- =============================================================================
-- SOFT_SKILL_TAXONOMY EXPANSION (~15 new entries)
-- =============================================================================

INSERT INTO soft_skill_taxonomy (canonical_id, name_en, name_el, category, aliases)
VALUES
('communication', 'Communication', 'Επικοινωνία', 'interpersonal', ARRAY['verbal communication', 'written communication']),
('teamwork', 'Teamwork', 'Ομαδικότητα', 'interpersonal', ARRAY['collaboration', 'team player']),
('leadership', 'Leadership', 'Ηγεσία', 'leadership', ARRAY['team leadership', 'leading']),
('problem_solving', 'Problem Solving', 'Επίλυση Προβλημάτων', 'analytical', ARRAY['troubleshooting']),
('time_management', 'Time Management', 'Διαχείριση Χρόνου', 'organizational', ARRAY['prioritization']),
('attention_to_detail', 'Attention to Detail', 'Προσοχή στη Λεπτομέρεια', 'analytical', ARRAY['detail oriented']),
('adaptability', 'Adaptability', 'Προσαρμοστικότητα', 'personal', ARRAY['flexibility', 'versatility']),
('critical_thinking', 'Critical Thinking', 'Κριτική Σκέψη', 'analytical', ARRAY['analytical thinking']),
('negotiation', 'Negotiation', 'Διαπραγμάτευση', 'interpersonal', ARRAY['negotiating']),
('presentation_skills', 'Presentation Skills', 'Δεξιότητες Παρουσίασης', 'communication', ARRAY['presenting']),
('conflict_resolution', 'Conflict Resolution', 'Επίλυση Συγκρούσεων', 'interpersonal', ARRAY['mediation']),
('coaching', 'Coaching', 'Coaching', 'leadership', ARRAY['employee coaching']),
('mentoring', 'Mentoring', 'Mentoring', 'leadership', ARRAY['mentorship']),
('creativity', 'Creativity', 'Δημιουργικότητα', 'personal', ARRAY['creative thinking', 'innovation']),
('stress_management', 'Stress Management', 'Διαχείριση Άγχους', 'personal', ARRAY['working under pressure'])

ON CONFLICT (canonical_id) DO UPDATE SET
    name_en = EXCLUDED.name_en,
    name_el = EXCLUDED.name_el,
    category = EXCLUDED.category,
    aliases = EXCLUDED.aliases,
    updated_at = CURRENT_TIMESTAMP;

-- =============================================================================
-- SOFTWARE_TAXONOMY EXPANSION (~80 new entries)
-- =============================================================================

INSERT INTO software_taxonomy (canonical_id, name_en, name_el, vendor, category, aliases)
VALUES
-- MANUFACTURING SOFTWARE
('autocad', 'AutoCAD', 'AutoCAD', 'Autodesk', 'cad', ARRAY['auto cad']),
('solidworks', 'SolidWorks', 'SolidWorks', 'Dassault', 'cad', ARRAY['solid works']),
('sap_pp', 'SAP PP', 'SAP PP', 'SAP', 'erp', ARRAY['sap production planning']),
('mes', 'MES', 'MES', NULL, 'manufacturing', ARRAY['manufacturing execution system']),
('scada', 'SCADA', 'SCADA', NULL, 'manufacturing', ARRAY['supervisory control']),
('cad_cam', 'CAD/CAM', 'CAD/CAM', NULL, 'manufacturing', ARRAY['computer aided design']),

-- ACCOUNTING SOFTWARE
('sap_fico', 'SAP FI/CO', 'SAP FI/CO', 'SAP', 'erp', ARRAY['sap finance', 'sap controlling']),
('softone', 'Softone', 'Softone', 'Softone', 'erp', ARRAY['soft one']),
('singular', 'Singular', 'Singular', 'SingularLogic', 'erp', ARRAY['singularlogic']),
('galaxy', 'Galaxy', 'Galaxy', 'SingularLogic', 'erp', ARRAY['galaxy erp']),
('epsilon_net', 'Epsilon Net', 'Epsilon Net', 'Epsilon Net', 'erp', ARRAY['epsilon']),
('pylon', 'Pylon', 'Pylon', 'Pylon', 'erp', ARRAY['pylon erp']),
('atlantis', 'Atlantis', 'Atlantis', 'Altec', 'erp', ARRAY['atlantis erp']),
('ergani', 'Ergani', 'Εργάνη', 'Greek Government', 'government', ARRAY['εργανη']),
('taxisnet', 'TAXISnet', 'TAXISnet', 'Greek Government', 'government', ARRAY['taxis']),

-- IT SOFTWARE
('windows_server', 'Windows Server', 'Windows Server', 'Microsoft', 'os', ARRAY['win server']),
('linux', 'Linux', 'Linux', NULL, 'os', ARRAY['ubuntu', 'centos', 'rhel', 'debian']),
('vmware', 'VMware', 'VMware', 'VMware', 'virtualization', ARRAY['vsphere', 'esxi']),
('aws', 'AWS', 'AWS', 'Amazon', 'cloud', ARRAY['amazon web services']),
('azure', 'Azure', 'Azure', 'Microsoft', 'cloud', ARRAY['microsoft azure']),
('gcp', 'Google Cloud', 'Google Cloud', 'Google', 'cloud', ARRAY['google cloud platform']),
('docker', 'Docker', 'Docker', 'Docker', 'devops', ARRAY['containerization']),
('kubernetes', 'Kubernetes', 'Kubernetes', NULL, 'devops', ARRAY['k8s']),
('jira', 'Jira', 'Jira', 'Atlassian', 'project_management', ARRAY['atlassian jira']),
('postgresql', 'PostgreSQL', 'PostgreSQL', NULL, 'database', ARRAY['postgres']),
('mysql', 'MySQL', 'MySQL', 'Oracle', 'database', ARRAY['my sql']),
('mongodb', 'MongoDB', 'MongoDB', 'MongoDB', 'database', ARRAY['mongo']),
('git', 'Git', 'Git', NULL, 'devops', ARRAY['github', 'gitlab', 'bitbucket']),
('jenkins', 'Jenkins', 'Jenkins', NULL, 'devops', ARRAY['jenkins ci']),
('terraform', 'Terraform', 'Terraform', 'HashiCorp', 'devops', ARRAY['tf']),
('ansible', 'Ansible', 'Ansible', 'Red Hat', 'devops', ARRAY['ansible automation']),

-- HR SOFTWARE
('workday', 'Workday', 'Workday', 'Workday', 'hrms', ARRAY['workday hcm']),
('sap_successfactors', 'SAP SuccessFactors', 'SAP SuccessFactors', 'SAP', 'hrms', ARRAY['successfactors']),
('bamboohr', 'BambooHR', 'BambooHR', 'BambooHR', 'hrms', ARRAY['bamboo hr']),
('linkedin_recruiter', 'LinkedIn Recruiter', 'LinkedIn Recruiter', 'LinkedIn', 'recruitment', ARRAY['linkedin talent']),
('ats', 'ATS', 'ATS', NULL, 'recruitment', ARRAY['applicant tracking system']),

-- MARKETING SOFTWARE
('google_analytics', 'Google Analytics', 'Google Analytics', 'Google', 'analytics', ARRAY['ga', 'ga4']),
('google_ads', 'Google Ads', 'Google Ads', 'Google', 'advertising', ARRAY['adwords']),
('facebook_ads', 'Facebook Ads', 'Facebook Ads', 'Meta', 'advertising', ARRAY['meta ads']),
('hubspot', 'HubSpot', 'HubSpot', 'HubSpot', 'marketing', ARRAY['hub spot']),
('mailchimp', 'Mailchimp', 'Mailchimp', 'Mailchimp', 'email', ARRAY['mail chimp']),
('hootsuite', 'Hootsuite', 'Hootsuite', 'Hootsuite', 'social', ARRAY['hoot suite']),
('canva', 'Canva', 'Canva', 'Canva', 'design', ARRAY['canva design']),
('photoshop', 'Adobe Photoshop', 'Adobe Photoshop', 'Adobe', 'design', ARRAY['ps', 'photoshop']),
('illustrator', 'Adobe Illustrator', 'Adobe Illustrator', 'Adobe', 'design', ARRAY['ai', 'illustrator']),
('indesign', 'Adobe InDesign', 'Adobe InDesign', 'Adobe', 'design', ARRAY['indesign']),
('premiere_pro', 'Adobe Premiere Pro', 'Adobe Premiere Pro', 'Adobe', 'video', ARRAY['premiere']),
('wordpress', 'WordPress', 'WordPress', 'WordPress', 'cms', ARRAY['wp']),
('semrush', 'SEMrush', 'SEMrush', 'SEMrush', 'seo', ARRAY['sem rush']),
('ahrefs', 'Ahrefs', 'Ahrefs', 'Ahrefs', 'seo', ARRAY['ahrefs seo']),

-- WAREHOUSE SOFTWARE
('wms', 'WMS', 'WMS', NULL, 'warehouse', ARRAY['warehouse management system']),
('sap_wm', 'SAP WM/EWM', 'SAP WM/EWM', 'SAP', 'warehouse', ARRAY['sap warehouse']),
('sap_mm', 'SAP MM', 'SAP MM', 'SAP', 'erp', ARRAY['sap materials management']),
('oracle_wms', 'Oracle WMS', 'Oracle WMS', 'Oracle', 'warehouse', ARRAY['oracle warehouse']),
('barcode_systems', 'Barcode Systems', 'Συστήματα Barcode', NULL, 'warehouse', ARRAY['barcode scanner']),
('tms', 'TMS', 'TMS', NULL, 'logistics', ARRAY['transport management system']),

-- SALES SOFTWARE
('salesforce', 'Salesforce', 'Salesforce', 'Salesforce', 'crm', ARRAY['sfdc']),
('hubspot_crm', 'HubSpot CRM', 'HubSpot CRM', 'HubSpot', 'crm', ARRAY['hubspot sales']),
('dynamics_365', 'Microsoft Dynamics 365', 'Microsoft Dynamics 365', 'Microsoft', 'crm', ARRAY['dynamics crm']),
('zoho_crm', 'Zoho CRM', 'Zoho CRM', 'Zoho', 'crm', ARRAY['zoho']),
('pipedrive', 'Pipedrive', 'Pipedrive', 'Pipedrive', 'crm', ARRAY['pipe drive']),
('linkedin_sales', 'LinkedIn Sales Navigator', 'LinkedIn Sales Navigator', 'LinkedIn', 'sales', ARRAY['sales navigator']),

-- SECURITY SOFTWARE
('cctv_software', 'CCTV Software', 'Λογισμικό CCTV', NULL, 'security', ARRAY['video management']),
('access_control_systems', 'Access Control Systems', 'Συστήματα Ελέγχου Πρόσβασης', NULL, 'security', ARRAY['access management']),
('visitor_management', 'Visitor Management Systems', 'Συστήματα Διαχείρισης Επισκεπτών', NULL, 'security', ARRAY['visitor tracking']),

-- GENERAL SOFTWARE
('excel_advanced', 'Excel Advanced', 'Excel Προχωρημένο', 'Microsoft', 'office', ARRAY['pivot tables', 'vlookup', 'macros']),
('power_bi', 'Power BI', 'Power BI', 'Microsoft', 'analytics', ARRAY['powerbi']),
('sap_business_one', 'SAP Business One', 'SAP Business One', 'SAP', 'erp', ARRAY['sap b1']),
('oracle_financials', 'Oracle Financials', 'Oracle Financials', 'Oracle', 'erp', ARRAY['oracle finance']),
('quickbooks', 'QuickBooks', 'QuickBooks', 'Intuit', 'accounting', ARRAY['quick books']),
('navision', 'Navision', 'Navision', 'Microsoft', 'erp', ARRAY['nav', 'dynamics nav']),
('servicenow', 'ServiceNow', 'ServiceNow', 'ServiceNow', 'itsm', ARRAY['service now']),
('confluence', 'Confluence', 'Confluence', 'Atlassian', 'documentation', ARRAY['atlassian confluence']),
('slack', 'Slack', 'Slack', 'Salesforce', 'communication', ARRAY['slack messaging']),
('teams', 'Microsoft Teams', 'Microsoft Teams', 'Microsoft', 'communication', ARRAY['ms teams'])

ON CONFLICT (canonical_id) DO UPDATE SET
    name_en = EXCLUDED.name_en,
    name_el = EXCLUDED.name_el,
    vendor = EXCLUDED.vendor,
    category = EXCLUDED.category,
    aliases = EXCLUDED.aliases,
    updated_at = CURRENT_TIMESTAMP;

-- =============================================================================
-- CERTIFICATION_TAXONOMY EXPANSION (~50 new entries)
-- =============================================================================

INSERT INTO certification_taxonomy (canonical_id, name_en, name_el, issuer, category, aliases)
VALUES
-- MANUFACTURING CERTIFICATIONS
('iso_9001', 'ISO 9001', 'ISO 9001', 'ISO', 'quality', ARRAY['quality management']),
('iso_14001', 'ISO 14001', 'ISO 14001', 'ISO', 'quality', ARRAY['environmental management']),
('iso_45001', 'ISO 45001', 'ISO 45001', 'ISO', 'safety', ARRAY['ohsas 18001', 'occupational safety']),
('six_sigma_green_belt', 'Six Sigma Green Belt', 'Six Sigma Green Belt', NULL, 'quality', ARRAY['green belt']),
('six_sigma_black_belt', 'Six Sigma Black Belt', 'Six Sigma Black Belt', NULL, 'quality', ARRAY['black belt']),
('lean_certified', 'Lean Certification', 'Πιστοποίηση Lean', NULL, 'quality', ARRAY['lean practitioner']),
('welding_certification', 'Welding Certification', 'Πιστοποίηση Συγκολλητή', NULL, 'technical', ARRAY['certified welder']),

-- ACCOUNTING CERTIFICATIONS
('acca', 'ACCA', 'ACCA', 'ACCA', 'accounting', ARRAY['association of chartered certified accountants']),
('soel_cpa', 'SOEL CPA', 'ΣΟΕΛ', 'ΣΟΕΛ', 'accounting', ARRAY['ορκωτός ελεγκτής', 'certified public accountant greece']),
('accountant_class_a', 'Accountant Class A', 'Λογιστής Α'' Τάξης', 'OEE', 'accounting', ARRAY['α τάξης', 'class a accountant']),
('accountant_class_b', 'Accountant Class B', 'Λογιστής Β'' Τάξης', 'OEE', 'accounting', ARRAY['β τάξης', 'class b accountant']),
('accountant_class_c', 'Accountant Class C', 'Λογιστής Γ'' Τάξης', 'OEE', 'accounting', ARRAY['γ τάξης', 'class c accountant']),
('oee_member', 'OEE Member', 'Μέλος ΟΕΕ', 'OEE', 'professional', ARRAY['οικονομικό επιμελητήριο']),
('cma', 'CMA', 'CMA', 'IMA', 'accounting', ARRAY['certified management accountant']),
('cfa', 'CFA', 'CFA', 'CFA Institute', 'finance', ARRAY['chartered financial analyst']),

-- IT CERTIFICATIONS
('aws_cloud_practitioner', 'AWS Cloud Practitioner', 'AWS Cloud Practitioner', 'AWS', 'cloud', ARRAY['clf-c01']),
('aws_solutions_architect', 'AWS Solutions Architect', 'AWS Solutions Architect', 'AWS', 'cloud', ARRAY['saa-c03']),
('aws_developer', 'AWS Developer', 'AWS Developer', 'AWS', 'cloud', ARRAY['dva-c02']),
('azure_fundamentals', 'Azure Fundamentals', 'Azure Fundamentals', 'Microsoft', 'cloud', ARRAY['az-900']),
('azure_administrator', 'Azure Administrator', 'Azure Administrator', 'Microsoft', 'cloud', ARRAY['az-104']),
('ccna', 'CCNA', 'CCNA', 'Cisco', 'networking', ARRAY['cisco certified network associate']),
('ccnp', 'CCNP', 'CCNP', 'Cisco', 'networking', ARRAY['cisco certified network professional']),
('comptia_a_plus', 'CompTIA A+', 'CompTIA A+', 'CompTIA', 'it', ARRAY['a plus', 'a+']),
('comptia_network_plus', 'CompTIA Network+', 'CompTIA Network+', 'CompTIA', 'networking', ARRAY['network plus', 'n+']),
('comptia_security_plus', 'CompTIA Security+', 'CompTIA Security+', 'CompTIA', 'security', ARRAY['security plus', 's+']),
('itil_foundation', 'ITIL Foundation', 'ITIL Foundation', 'Axelos', 'it', ARRAY['itil v4']),
('cissp', 'CISSP', 'CISSP', 'ISC2', 'security', ARRAY['certified information systems security professional']),
('ceh', 'CEH', 'CEH', 'EC-Council', 'security', ARRAY['certified ethical hacker']),
('rhcsa', 'RHCSA', 'RHCSA', 'Red Hat', 'linux', ARRAY['red hat certified system administrator']),
('vmware_vcp', 'VMware VCP', 'VMware VCP', 'VMware', 'virtualization', ARRAY['vmware certified professional']),
('pmp', 'PMP', 'PMP', 'PMI', 'project_management', ARRAY['project management professional']),

-- HR CERTIFICATIONS
('shrm_cp', 'SHRM-CP', 'SHRM-CP', 'SHRM', 'hr', ARRAY['shrm certified professional']),
('shrm_scp', 'SHRM-SCP', 'SHRM-SCP', 'SHRM', 'hr', ARRAY['shrm senior certified professional']),
('cipd', 'CIPD', 'CIPD', 'CIPD', 'hr', ARRAY['chartered institute of personnel and development']),
('gdpr_certification', 'GDPR Certification', 'Πιστοποίηση GDPR', NULL, 'compliance', ARRAY['data protection certification']),

-- MARKETING CERTIFICATIONS
('google_analytics_cert', 'Google Analytics Certified', 'Google Analytics Certified', 'Google', 'marketing', ARRAY['ga certified']),
('google_ads_cert', 'Google Ads Certified', 'Google Ads Certified', 'Google', 'marketing', ARRAY['adwords certified']),
('hubspot_inbound_cert', 'HubSpot Inbound Marketing', 'HubSpot Inbound Marketing', 'HubSpot', 'marketing', ARRAY['inbound certified']),
('facebook_blueprint', 'Facebook Blueprint', 'Facebook Blueprint', 'Meta', 'marketing', ARRAY['meta blueprint']),

-- WAREHOUSE CERTIFICATIONS
('apics_cpim', 'APICS CPIM', 'APICS CPIM', 'APICS', 'supply_chain', ARRAY['certified in planning and inventory management']),
('apics_cscp', 'APICS CSCP', 'APICS CSCP', 'APICS', 'supply_chain', ARRAY['certified supply chain professional']),
('adr_dangerous_goods', 'ADR Dangerous Goods', 'ADR Επικίνδυνα Εμπορεύματα', NULL, 'safety', ARRAY['adr certification', 'hazmat']),

-- SECURITY CERTIFICATIONS
('security_guard_license', 'Security Guard License', 'Άδεια Φύλακα', 'Greek Government', 'security', ARRAY['άδεια προσωπικού ασφαλείας']),
('first_aid', 'First Aid', 'Πρώτες Βοήθειες', NULL, 'safety', ARRAY['first aid certified', 'πρώτες βοήθειες']),
('cpr_aed', 'CPR/AED', 'CPR/AED', NULL, 'safety', ARRAY['cpr certified', 'καρδιοαναπνευστική αναζωογόνηση']),
('fire_safety_cert', 'Fire Safety Certificate', 'Πιστοποιητικό Πυρασφάλειας', NULL, 'safety', ARRAY['fire warden', 'πυροπροστασία']),
('haccp', 'HACCP', 'HACCP', NULL, 'safety', ARRAY['food safety', 'hazard analysis']),
('close_protection', 'Close Protection', 'Προστασία Προσώπων', NULL, 'security', ARRAY['bodyguard', 'vip protection']),

-- PROFESSIONAL REGISTRATIONS (Greek)
('tee_mechanical', 'TEE Mechanical Engineer', 'ΤΕΕ Μηχανολόγος Μηχανικός', 'TEE', 'professional', ARRAY['τεε', 'μηχανολόγος']),
('tee_electrical', 'TEE Electrical Engineer', 'ΤΕΕ Ηλεκτρολόγος Μηχανικός', 'TEE', 'professional', ARRAY['τεε', 'ηλεκτρολόγος']),
('tee_civil', 'TEE Civil Engineer', 'ΤΕΕ Πολιτικός Μηχανικός', 'TEE', 'professional', ARRAY['τεε', 'πολιτικός μηχανικός']),
('electrical_license_a', 'Electrical License A', 'Άδεια Ηλεκτρολόγου Α''', NULL, 'technical', ARRAY['ηλεκτρολόγος α ειδικότητας'])

ON CONFLICT (canonical_id) DO UPDATE SET
    name_en = EXCLUDED.name_en,
    name_el = EXCLUDED.name_el,
    issuer = EXCLUDED.issuer,
    category = EXCLUDED.category,
    aliases = EXCLUDED.aliases,
    updated_at = CURRENT_TIMESTAMP;

-- =============================================================================
-- ROLE_TAXONOMY EXPANSION (~30 new entries)
-- =============================================================================

INSERT INTO role_taxonomy (canonical_id, name_en, name_el, department, level, aliases)
VALUES
-- MANUFACTURING ROLES
('production_manager', 'Production Manager', 'Διευθυντής Παραγωγής', 'manufacturing', 'manager', ARRAY['plant manager']),
('production_supervisor', 'Production Supervisor', 'Επόπτης Παραγωγής', 'manufacturing', 'supervisor', ARRAY['line supervisor']),
('machine_operator', 'Machine Operator', 'Χειριστής Μηχανημάτων', 'manufacturing', 'operator', ARRAY['operator']),
('quality_engineer', 'Quality Engineer', 'Μηχανικός Ποιότητας', 'manufacturing', 'engineer', ARRAY['qa engineer']),
('maintenance_technician', 'Maintenance Technician', 'Τεχνικός Συντήρησης', 'manufacturing', 'technician', ARRAY['maintenance engineer']),

-- ACCOUNTING ROLES
('accountant', 'Accountant', 'Λογιστής', 'accounting', 'professional', ARRAY['λογιστής']),
('senior_accountant', 'Senior Accountant', 'Ανώτερος Λογιστής', 'accounting', 'senior', ARRAY['sr accountant']),
('accounting_manager', 'Accounting Manager', 'Διευθυντής Λογιστηρίου', 'accounting', 'manager', ARRAY['finance manager']),
('payroll_specialist', 'Payroll Specialist', 'Ειδικός Μισθοδοσίας', 'accounting', 'specialist', ARRAY['payroll administrator']),

-- IT ROLES
('it_manager', 'IT Manager', 'Διευθυντής IT', 'it', 'manager', ARRAY['it director']),
('system_administrator', 'System Administrator', 'Διαχειριστής Συστημάτων', 'it', 'administrator', ARRAY['sysadmin']),
('network_engineer', 'Network Engineer', 'Μηχανικός Δικτύων', 'it', 'engineer', ARRAY['network admin']),
('software_developer', 'Software Developer', 'Προγραμματιστής', 'it', 'developer', ARRAY['developer', 'programmer']),
('helpdesk_technician', 'Helpdesk Technician', 'Τεχνικός Helpdesk', 'it', 'technician', ARRAY['it support']),

-- HR ROLES
('hr_manager', 'HR Manager', 'Διευθυντής HR', 'hr', 'manager', ARRAY['hr director']),
('recruiter', 'Recruiter', 'Recruiter', 'hr', 'specialist', ARRAY['talent acquisition']),
('hr_generalist', 'HR Generalist', 'HR Generalist', 'hr', 'generalist', ARRAY['hr specialist']),

-- MARKETING ROLES
('marketing_manager', 'Marketing Manager', 'Διευθυντής Marketing', 'marketing', 'manager', ARRAY['marketing director']),
('digital_marketing_specialist', 'Digital Marketing Specialist', 'Ειδικός Digital Marketing', 'marketing', 'specialist', ARRAY['digital marketer']),
('content_creator', 'Content Creator', 'Δημιουργός Περιεχομένου', 'marketing', 'specialist', ARRAY['content writer']),
('graphic_designer', 'Graphic Designer', 'Γραφίστας', 'marketing', 'specialist', ARRAY['designer']),

-- WAREHOUSE ROLES
('warehouse_manager', 'Warehouse Manager', 'Διευθυντής Αποθήκης', 'warehouse', 'manager', ARRAY['logistics manager']),
('warehouse_supervisor', 'Warehouse Supervisor', 'Επόπτης Αποθήκης', 'warehouse', 'supervisor', ARRAY['shift supervisor']),
('forklift_operator', 'Forklift Operator', 'Χειριστής Κλαρκ', 'warehouse', 'operator', ARRAY['κλαρκιστας']),
('inventory_clerk', 'Inventory Clerk', 'Υπάλληλος Αποθέματος', 'warehouse', 'clerk', ARRAY['stock clerk']),

-- SALES ROLES
('sales_manager', 'Sales Manager', 'Διευθυντής Πωλήσεων', 'sales', 'manager', ARRAY['sales director']),
('sales_representative', 'Sales Representative', 'Πωλητής', 'sales', 'representative', ARRAY['sales rep', 'πωλητής']),
('account_executive', 'Account Executive', 'Account Executive', 'sales', 'executive', ARRAY['ae']),
('key_account_manager', 'Key Account Manager', 'Key Account Manager', 'sales', 'manager', ARRAY['kam']),

-- SECURITY ROLES
('security_manager', 'Security Manager', 'Διευθυντής Ασφαλείας', 'security', 'manager', ARRAY['security director']),
('security_guard', 'Security Guard', 'Φύλακας', 'security', 'guard', ARRAY['security officer', 'φυλακας']),
('security_supervisor', 'Security Supervisor', 'Επόπτης Ασφαλείας', 'security', 'supervisor', ARRAY['shift leader'])

ON CONFLICT (canonical_id) DO UPDATE SET
    name_en = EXCLUDED.name_en,
    name_el = EXCLUDED.name_el,
    department = EXCLUDED.department,
    level = EXCLUDED.level,
    aliases = EXCLUDED.aliases,
    updated_at = CURRENT_TIMESTAMP;

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
BEGIN
    SELECT COUNT(*) INTO skill_count FROM skill_taxonomy;
    SELECT COUNT(*) INTO soft_skill_count FROM soft_skill_taxonomy;
    SELECT COUNT(*) INTO cert_count FROM certification_taxonomy;
    SELECT COUNT(*) INTO software_count FROM software_taxonomy;
    SELECT COUNT(*) INTO role_count FROM role_taxonomy;

    RAISE NOTICE 'Taxonomy counts after expansion:';
    RAISE NOTICE '  skill_taxonomy: %', skill_count;
    RAISE NOTICE '  soft_skill_taxonomy: %', soft_skill_count;
    RAISE NOTICE '  certification_taxonomy: %', cert_count;
    RAISE NOTICE '  software_taxonomy: %', software_count;
    RAISE NOTICE '  role_taxonomy: %', role_count;
    RAISE NOTICE '  TOTAL: %', skill_count + soft_skill_count + cert_count + software_count + role_count;

    RAISE NOTICE 'Migration 017_taxonomy_expansion.sql completed successfully';
END $$;
