-- SA Healthcare Professionals Extended Schema
-- Enhanced table structure with comprehensive HPCSA validation and indexing

-- Drop existing table if it exists (for development)
-- DROP TABLE IF EXISTS sa_healthcare_professionals;

-- Create comprehensive healthcare professionals table
CREATE TABLE IF NOT EXISTS sa_healthcare_professionals (
    -- Primary identification
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hpcsa_number VARCHAR(20) NOT NULL UNIQUE,
    
    -- Personal information
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    middle_names VARCHAR(200),
    maiden_name VARCHAR(100),
    
    -- Contact information
    email VARCHAR(255),
    phone_primary VARCHAR(20),
    phone_secondary VARCHAR(20),
    
    -- Professional information
    registration_category VARCHAR(10) NOT NULL, -- MP, DP, etc.
    registration_status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, SUSPENDED, CANCELLED
    specialization VARCHAR(200),
    sub_specialization VARCHAR(200),
    
    -- Geographic information
    province_code VARCHAR(5) NOT NULL,
    practice_city VARCHAR(100),
    practice_address TEXT,
    practice_postal_code VARCHAR(10),
    
    -- Registration details
    initial_registration_date DATE,
    current_registration_date DATE,
    registration_expiry_date DATE,
    
    -- Qualifications
    primary_qualification VARCHAR(200),
    additional_qualifications TEXT, -- JSON array of qualifications
    
    -- Practice information
    practice_type VARCHAR(50), -- PRIVATE, PUBLIC, ACADEMIC, etc.
    practice_name VARCHAR(200),
    hospital_affiliations TEXT, -- JSON array of hospital affiliations
    
    -- Compliance and validation
    hpcsa_validation_status VARCHAR(20) DEFAULT 'PENDING', -- VALIDATED, PENDING, FAILED
    hpcsa_validation_date DATETIME,
    hpcsa_validation_details TEXT,
    
    -- System fields
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    
    -- Audit fields
    is_active BOOLEAN DEFAULT 1,
    is_deleted BOOLEAN DEFAULT 0,
    deleted_at DATETIME,
    deleted_by VARCHAR(100),
    
    -- Additional metadata
    metadata TEXT, -- JSON field for additional data
    notes TEXT,
    
    -- Constraints
    CONSTRAINT chk_hpcsa_format CHECK (
        hpcsa_number REGEXP '^[A-Z]{1,3}[0-9]{6,8}$'
    ),
    CONSTRAINT chk_registration_category CHECK (
        registration_category IN ('MP', 'DP', 'DT', 'PS', 'RP', 'RT', 'OT', 'PT', 'SP', 'AU', 'OP', 'CP', 'PO', 'CH')
    ),
    CONSTRAINT chk_province_code CHECK (
        province_code IN ('GP', 'WC', 'KZN', 'EC', 'FS', 'LP', 'MP', 'NW', 'NC')
    ),
    CONSTRAINT chk_registration_status CHECK (
        registration_status IN ('ACTIVE', 'SUSPENDED', 'CANCELLED', 'EXPIRED', 'PENDING')
    ),
    CONSTRAINT chk_validation_status CHECK (
        hpcsa_validation_status IN ('VALIDATED', 'PENDING', 'FAILED', 'EXPIRED')
    )
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_hpcsa_professionals_hpcsa_number ON sa_healthcare_professionals(hpcsa_number);
CREATE INDEX IF NOT EXISTS idx_hpcsa_professionals_name ON sa_healthcare_professionals(last_name, first_name);
CREATE INDEX IF NOT EXISTS idx_hpcsa_professionals_category ON sa_healthcare_professionals(registration_category);
CREATE INDEX IF NOT EXISTS idx_hpcsa_professionals_province ON sa_healthcare_professionals(province_code);
CREATE INDEX IF NOT EXISTS idx_hpcsa_professionals_status ON sa_healthcare_professionals(registration_status);
CREATE INDEX IF NOT EXISTS idx_hpcsa_professionals_validation ON sa_healthcare_professionals(hpcsa_validation_status);
CREATE INDEX IF NOT EXISTS idx_hpcsa_professionals_specialization ON sa_healthcare_professionals(specialization);
CREATE INDEX IF NOT EXISTS idx_hpcsa_professionals_active ON sa_healthcare_professionals(is_active, is_deleted);
CREATE INDEX IF NOT EXISTS idx_hpcsa_professionals_email ON sa_healthcare_professionals(email);
CREATE INDEX IF NOT EXISTS idx_hpcsa_professionals_created ON sa_healthcare_professionals(created_at);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_hpcsa_professionals_category_province ON sa_healthcare_professionals(registration_category, province_code);
CREATE INDEX IF NOT EXISTS idx_hpcsa_professionals_status_validation ON sa_healthcare_professionals(registration_status, hpcsa_validation_status);
CREATE INDEX IF NOT EXISTS idx_hpcsa_professionals_active_category ON sa_healthcare_professionals(is_active, registration_category) WHERE is_deleted = 0;

-- Create trigger to update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS trg_hpcsa_professionals_updated_at
    AFTER UPDATE ON sa_healthcare_professionals
    FOR EACH ROW
BEGIN
    UPDATE sa_healthcare_professionals 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;

-- Create trigger for soft delete
CREATE TRIGGER IF NOT EXISTS trg_hpcsa_professionals_soft_delete
    AFTER UPDATE OF is_deleted ON sa_healthcare_professionals
    FOR EACH ROW
    WHEN NEW.is_deleted = 1 AND OLD.is_deleted = 0
BEGIN
    UPDATE sa_healthcare_professionals 
    SET deleted_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;

-- Create lookup table for registration categories
CREATE TABLE IF NOT EXISTS sa_hpcsa_registration_categories (
    code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert registration categories
INSERT OR IGNORE INTO sa_hpcsa_registration_categories (code, name, description) VALUES
('MP', 'Medical Practitioner', 'Qualified medical doctors'),
('DP', 'Dental Practitioner', 'Qualified dentists'),
('DT', 'Dental Therapist', 'Dental therapy professionals'),
('PS', 'Medical Specialist', 'Medical specialists in various fields'),
('RP', 'Radiographer', 'Medical imaging professionals'),
('RT', 'Radiation Therapist', 'Radiation therapy professionals'),
('OT', 'Occupational Therapist', 'Occupational therapy professionals'),
('PT', 'Physiotherapist', 'Physiotherapy professionals'),
('SP', 'Speech-Language Pathologist', 'Speech and language therapy professionals'),
('AU', 'Audiologist', 'Hearing and balance professionals'),
('OP', 'Optometrist', 'Eye care professionals'),
('CP', 'Clinical Psychologist', 'Clinical psychology professionals'),
('PO', 'Podiatrist', 'Foot and ankle care professionals'),
('CH', 'Chiropractor', 'Chiropractic professionals');

-- Create lookup table for provinces
CREATE TABLE IF NOT EXISTS sa_provinces (
    code VARCHAR(5) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    full_name VARCHAR(200),
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert provinces
INSERT OR IGNORE INTO sa_provinces (code, name, full_name) VALUES
('GP', 'Gauteng', 'Gauteng Province'),
('WC', 'Western Cape', 'Western Cape Province'),
('KZN', 'KwaZulu-Natal', 'KwaZulu-Natal Province'),
('EC', 'Eastern Cape', 'Eastern Cape Province'),
('FS', 'Free State', 'Free State Province'),
('LP', 'Limpopo', 'Limpopo Province'),
('MP', 'Mpumalanga', 'Mpumalanga Province'),
('NW', 'North West', 'North West Province'),
('NC', 'Northern Cape', 'Northern Cape Province');

-- Create specializations lookup table
CREATE TABLE IF NOT EXISTS sa_medical_specializations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20),
    name VARCHAR(200) NOT NULL,
    category VARCHAR(50),
    registration_category VARCHAR(10),
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (registration_category) REFERENCES sa_hpcsa_registration_categories(code)
);

-- Insert common medical specializations
INSERT OR IGNORE INTO sa_medical_specializations (code, name, category, registration_category) VALUES
-- Medical Practitioner Specializations
('ANAES', 'Anaesthesiology', 'Medical', 'MP'),
('CARDIO', 'Cardiology', 'Medical', 'MP'),
('DERM', 'Dermatology', 'Medical', 'MP'),
('EMERG', 'Emergency Medicine', 'Medical', 'MP'),
('ENDO', 'Endocrinology', 'Medical', 'MP'),
('GASTRO', 'Gastroenterology', 'Medical', 'MP'),
('GENSURG', 'General Surgery', 'Surgical', 'MP'),
('GYNE', 'Gynaecology', 'Medical', 'MP'),
('HAEM', 'Haematology', 'Medical', 'MP'),
('INTERN', 'Internal Medicine', 'Medical', 'MP'),
('NEURO', 'Neurology', 'Medical', 'MP'),
('NEUROSURG', 'Neurosurgery', 'Surgical', 'MP'),
('OBSTET', 'Obstetrics', 'Medical', 'MP'),
('ONCO', 'Oncology', 'Medical', 'MP'),
('OPHTH', 'Ophthalmology', 'Medical', 'MP'),
('ORTHO', 'Orthopaedic Surgery', 'Surgical', 'MP'),
('PAED', 'Paediatrics', 'Medical', 'MP'),
('PATH', 'Pathology', 'Medical', 'MP'),
('PSYCH', 'Psychiatry', 'Medical', 'MP'),
('RADIO', 'Radiology', 'Medical', 'MP'),
('UROL', 'Urology', 'Surgical', 'MP'),

-- Dental Specializations
('ORTHO_DENT', 'Orthodontics', 'Dental', 'DP'),
('ORAL_SURG', 'Oral Surgery', 'Dental', 'DP'),
('PERIO', 'Periodontics', 'Dental', 'DP'),
('ENDO_DENT', 'Endodontics', 'Dental', 'DP'),
('PROS', 'Prosthodontics', 'Dental', 'DP'),

-- Allied Health Specializations
('CARDIO_PT', 'Cardiopulmonary Physiotherapy', 'Allied Health', 'PT'),
('NEURO_PT', 'Neurological Physiotherapy', 'Allied Health', 'PT'),
('ORTHO_PT', 'Orthopaedic Physiotherapy', 'Allied Health', 'PT'),
('PAED_PT', 'Paediatric Physiotherapy', 'Allied Health', 'PT'),
('SPORTS_PT', 'Sports Physiotherapy', 'Allied Health', 'PT');

-- Create validation functions table for HPCSA number validation
CREATE TABLE IF NOT EXISTS sa_hpcsa_validation_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    registration_category VARCHAR(10) NOT NULL,
    number_format VARCHAR(50) NOT NULL,
    min_length INTEGER NOT NULL,
    max_length INTEGER NOT NULL,
    validation_regex VARCHAR(200),
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (registration_category) REFERENCES sa_hpcsa_registration_categories(code)
);

-- Insert validation rules for different registration categories
INSERT OR IGNORE INTO sa_hpcsa_validation_rules 
(registration_category, number_format, min_length, max_length, validation_regex, description) VALUES
('MP', 'MP + 6-8 digits', 8, 10, '^MP[0-9]{6,8}$', 'Medical Practitioner: MP followed by 6-8 digits'),
('DP', 'DP + 6-8 digits', 8, 10, '^DP[0-9]{6,8}$', 'Dental Practitioner: DP followed by 6-8 digits'),
('DT', 'DT + 6-8 digits', 8, 10, '^DT[0-9]{6,8}$', 'Dental Therapist: DT followed by 6-8 digits'),
('PS', 'PS + 6-8 digits', 8, 10, '^PS[0-9]{6,8}$', 'Medical Specialist: PS followed by 6-8 digits'),
('RP', 'RP + 6-8 digits', 8, 10, '^RP[0-9]{6,8}$', 'Radiographer: RP followed by 6-8 digits'),
('RT', 'RT + 6-8 digits', 8, 10, '^RT[0-9]{6,8}$', 'Radiation Therapist: RT followed by 6-8 digits'),
('OT', 'OT + 6-8 digits', 8, 10, '^OT[0-9]{6,8}$', 'Occupational Therapist: OT followed by 6-8 digits'),
('PT', 'PT + 6-8 digits', 8, 10, '^PT[0-9]{6,8}$', 'Physiotherapist: PT followed by 6-8 digits'),
('SP', 'SP + 6-8 digits', 8, 10, '^SP[0-9]{6,8}$', 'Speech-Language Pathologist: SP followed by 6-8 digits'),
('AU', 'AU + 6-8 digits', 8, 10, '^AU[0-9]{6,8}$', 'Audiologist: AU followed by 6-8 digits'),
('OP', 'OP + 6-8 digits', 8, 10, '^OP[0-9]{6,8}$', 'Optometrist: OP followed by 6-8 digits'),
('CP', 'CP + 6-8 digits', 8, 10, '^CP[0-9]{6,8}$', 'Clinical Psychologist: CP followed by 6-8 digits'),
('PO', 'PO + 6-8 digits', 8, 10, '^PO[0-9]{6,8}$', 'Podiatrist: PO followed by 6-8 digits'),
('CH', 'CH + 6-8 digits', 8, 10, '^CH[0-9]{6,8}$', 'Chiropractor: CH followed by 6-8 digits');

-- Create view for active healthcare professionals with full details
CREATE VIEW IF NOT EXISTS vw_active_healthcare_professionals AS
SELECT 
    hp.*,
    rc.name as registration_category_name,
    rc.description as registration_category_description,
    p.name as province_name,
    p.full_name as province_full_name,
    ms.name as specialization_name,
    ms.category as specialization_category
FROM sa_healthcare_professionals hp
LEFT JOIN sa_hpcsa_registration_categories rc ON hp.registration_category = rc.code
LEFT JOIN sa_provinces p ON hp.province_code = p.code
LEFT JOIN sa_medical_specializations ms ON hp.specialization = ms.code
WHERE hp.is_active = 1 AND hp.is_deleted = 0;

-- Create view for validation statistics
CREATE VIEW IF NOT EXISTS vw_hpcsa_validation_stats AS
SELECT 
    registration_category,
    COUNT(*) as total_professionals,
    SUM(CASE WHEN hpcsa_validation_status = 'VALIDATED' THEN 1 ELSE 0 END) as validated_count,
    SUM(CASE WHEN hpcsa_validation_status = 'PENDING' THEN 1 ELSE 0 END) as pending_count,
    SUM(CASE WHEN hpcsa_validation_status = 'FAILED' THEN 1 ELSE 0 END) as failed_count,
    SUM(CASE WHEN registration_status = 'ACTIVE' THEN 1 ELSE 0 END) as active_count,
    ROUND(
        (SUM(CASE WHEN hpcsa_validation_status = 'VALIDATED' THEN 1 ELSE 0 END) * 100.0) / COUNT(*), 
        2
    ) as validation_percentage
FROM sa_healthcare_professionals
WHERE is_active = 1 AND is_deleted = 0
GROUP BY registration_category;

-- Insert sample data for testing
INSERT OR IGNORE INTO sa_healthcare_professionals 
(hpcsa_number, first_name, last_name, email, registration_category, province_code, specialization, hpcsa_validation_status, created_by) 
VALUES
('MP123456', 'Dr. John', 'Smith', 'john.smith@example.com', 'MP', 'GP', 'CARDIO', 'VALIDATED', 'SYSTEM'),
('DP789012', 'Dr. Sarah', 'Johnson', 'sarah.johnson@example.com', 'DP', 'WC', 'ORTHO_DENT', 'VALIDATED', 'SYSTEM'),
('PT345678', 'Jane', 'Williams', 'jane.williams@example.com', 'PT', 'KZN', 'SPORTS_PT', 'PENDING', 'SYSTEM'),
('PS901234', 'Prof. Michael', 'Brown', 'michael.brown@example.com', 'PS', 'GP', 'NEUROSURG', 'VALIDATED', 'SYSTEM'),
('RP567890', 'Lisa', 'Davis', 'lisa.davis@example.com', 'RP', 'EC', NULL, 'VALIDATED', 'SYSTEM');

-- Create stored procedures (functions) for common operations
-- Note: SQLite doesn't support stored procedures, but we can create these as application-level functions

-- Comments for application-level functions to implement:
-- 1. validate_hpcsa_number(hpcsa_number, registration_category) -> boolean
-- 2. get_professionals_by_province(province_code) -> result set
-- 3. get_professionals_by_specialization(specialization) -> result set
-- 4. update_validation_status(hpcsa_number, status, details) -> boolean
-- 5. search_professionals(search_term) -> result set
-- 6. get_validation_statistics() -> result set

-- Create audit log table for healthcare professionals
CREATE TABLE IF NOT EXISTS sa_healthcare_professionals_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    professional_id INTEGER NOT NULL,
    hpcsa_number VARCHAR(20) NOT NULL,
    action VARCHAR(50) NOT NULL, -- INSERT, UPDATE, DELETE, VALIDATE
    old_values TEXT, -- JSON of old values
    new_values TEXT, -- JSON of new values
    changed_by VARCHAR(100),
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT,
    notes TEXT,
    
    FOREIGN KEY (professional_id) REFERENCES sa_healthcare_professionals(id)
);

-- Create index for audit log
CREATE INDEX IF NOT EXISTS idx_hpcsa_audit_professional ON sa_healthcare_professionals_audit(professional_id);
CREATE INDEX IF NOT EXISTS idx_hpcsa_audit_action ON sa_healthcare_professionals_audit(action);
CREATE INDEX IF NOT EXISTS idx_hpcsa_audit_date ON sa_healthcare_professionals_audit(changed_at);
CREATE INDEX IF NOT EXISTS idx_hpcsa_audit_user ON sa_healthcare_professionals_audit(changed_by);

-- Create trigger for audit logging
CREATE TRIGGER IF NOT EXISTS trg_hpcsa_professionals_audit_insert
    AFTER INSERT ON sa_healthcare_professionals
    FOR EACH ROW
BEGIN
    INSERT INTO sa_healthcare_professionals_audit 
    (professional_id, hpcsa_number, action, new_values, changed_by)
    VALUES 
    (NEW.id, NEW.hpcsa_number, 'INSERT', 
     json_object(
         'hpcsa_number', NEW.hpcsa_number,
         'first_name', NEW.first_name,
         'last_name', NEW.last_name,
         'registration_category', NEW.registration_category,
         'province_code', NEW.province_code
     ), 
     NEW.created_by);
END;

CREATE TRIGGER IF NOT EXISTS trg_hpcsa_professionals_audit_update
    AFTER UPDATE ON sa_healthcare_professionals
    FOR EACH ROW
BEGIN
    INSERT INTO sa_healthcare_professionals_audit 
    (professional_id, hpcsa_number, action, old_values, new_values, changed_by)
    VALUES 
    (NEW.id, NEW.hpcsa_number, 'UPDATE',
     json_object(
         'hpcsa_number', OLD.hpcsa_number,
         'first_name', OLD.first_name,
         'last_name', OLD.last_name,
         'registration_category', OLD.registration_category,
         'province_code', OLD.province_code,
         'hpcsa_validation_status', OLD.hpcsa_validation_status
     ),
     json_object(
         'hpcsa_number', NEW.hpcsa_number,
         'first_name', NEW.first_name,
         'last_name', NEW.last_name,
         'registration_category', NEW.registration_category,
         'province_code', NEW.province_code,
         'hpcsa_validation_status', NEW.hpcsa_validation_status
     ),
     NEW.updated_by);
END;