-- SA Healthcare Professionals Table Schema
-- Supports HPCSA registration validation and professional data management
-- Compatible with MySQL, PostgreSQL, SQL Server, Oracle, SQLite

-- Healthcare Professionals Table
CREATE TABLE IF NOT EXISTS sa_healthcare_professionals (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    hpcsa_number VARCHAR(20) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    id_number VARCHAR(13),
    email VARCHAR(255),
    phone VARCHAR(20),
    
    -- HPCSA Registration Details
    registration_category VARCHAR(50) NOT NULL, -- Medical Practitioner, Dentist, etc.
    specialization VARCHAR(100),
    registration_date DATE,
    registration_status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, SUSPENDED, EXPIRED
    
    -- Practice Information
    practice_name VARCHAR(200),
    practice_number VARCHAR(50),
    province_code VARCHAR(3) NOT NULL, -- GP, WC, KZN, etc.
    city VARCHAR(100),
    postal_code VARCHAR(10),
    
    -- System Fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Validation Fields
    hpcsa_verified BOOLEAN DEFAULT FALSE,
    hpcsa_verified_date TIMESTAMP NULL,
    last_verification_attempt TIMESTAMP NULL,
    verification_attempts INTEGER DEFAULT 0,
    
    -- Indexes for performance
    INDEX idx_hpcsa_number (hpcsa_number),
    INDEX idx_province_specialization (province_code, specialization),
    INDEX idx_registration_status (registration_status),
    INDEX idx_email (email),
    INDEX idx_active_professionals (is_active, registration_status)
);

-- HPCSA Registration Categories Reference Table
CREATE TABLE IF NOT EXISTS sa_hpcsa_categories (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    category_code VARCHAR(10) NOT NULL UNIQUE,
    category_name VARCHAR(100) NOT NULL,
    description TEXT,
    prefix VARCHAR(5) NOT NULL, -- MP, DP, etc.
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX idx_category_code (category_code),
    INDEX idx_prefix (prefix)
);

-- Insert standard HPCSA categories
INSERT INTO sa_hpcsa_categories (category_code, category_name, description, prefix) VALUES
('MP', 'Medical Practitioner', 'Registered medical doctors', 'MP'),
('DP', 'Dental Practitioner', 'Registered dentists', 'DP'),
('PS', 'Psychology', 'Registered psychologists', 'PS'),
('DT', 'Dental Therapy', 'Registered dental therapists', 'DT'),
('OH', 'Oral Hygiene', 'Registered oral hygienists', 'OH'),
('EM', 'Emergency Medical Care', 'Emergency medical care practitioners', 'EM'),
('OT', 'Occupational Therapy', 'Registered occupational therapists', 'OT'),
('PT', 'Physiotherapy', 'Registered physiotherapists', 'PT'),
('PO', 'Podiatry', 'Registered podiatrists', 'PO'),
('OP', 'Optometry', 'Registered optometrists', 'OP'),
('SP', 'Speech-Language Pathology', 'Speech-language pathologists', 'SP'),
('AU', 'Audiology', 'Registered audiologists', 'AU')
ON DUPLICATE KEY UPDATE category_name = VALUES(category_name);

-- SA Provinces Reference Table
CREATE TABLE IF NOT EXISTS sa_provinces (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    province_code VARCHAR(3) NOT NULL UNIQUE,
    province_name VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX idx_province_code (province_code)
);

-- Insert SA provinces
INSERT INTO sa_provinces (province_code, province_name) VALUES
('GP', 'Gauteng'),
('WC', 'Western Cape'),
('KZN', 'KwaZulu-Natal'),
('EC', 'Eastern Cape'),
('FS', 'Free State'),
('LP', 'Limpopo'),
('MP', 'Mpumalanga'),
('NC', 'Northern Cape'),
('NW', 'North West')
ON DUPLICATE KEY UPDATE province_name = VALUES(province_name);

-- Professional Specializations Table
CREATE TABLE IF NOT EXISTS sa_medical_specializations (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    specialization_code VARCHAR(20) NOT NULL UNIQUE,
    specialization_name VARCHAR(100) NOT NULL,
    category_code VARCHAR(10) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX idx_specialization_code (specialization_code),
    INDEX idx_category (category_code),
    FOREIGN KEY (category_code) REFERENCES sa_hpcsa_categories(category_code)
);

-- Insert common medical specializations
INSERT INTO sa_medical_specializations (specialization_code, specialization_name, category_code, description) VALUES
('GP', 'General Practice', 'MP', 'General medical practice'),
('CARDIO', 'Cardiology', 'MP', 'Heart and cardiovascular system'),
('ORTHO', 'Orthopedics', 'MP', 'Musculoskeletal system'),
('NEURO', 'Neurology', 'MP', 'Nervous system disorders'),
('PEDIA', 'Pediatrics', 'MP', 'Medical care of children'),
('GYNE', 'Gynecology', 'MP', 'Female reproductive system'),
('RADIO', 'Radiology', 'MP', 'Medical imaging and diagnosis'),
('ANES', 'Anesthesiology', 'MP', 'Anesthesia and pain management'),
('SURG', 'Surgery', 'MP', 'Surgical procedures'),
('PSYCH', 'Psychiatry', 'MP', 'Mental health disorders'),
('DERM', 'Dermatology', 'MP', 'Skin conditions'),
('OPHTH', 'Ophthalmology', 'MP', 'Eye and vision care')
ON DUPLICATE KEY UPDATE specialization_name = VALUES(specialization_name);

-- Professional Practice Permissions Table
CREATE TABLE IF NOT EXISTS sa_practice_permissions (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    professional_id INTEGER NOT NULL,
    permission_type VARCHAR(50) NOT NULL, -- DICOM_ACCESS, PATIENT_EDIT, REPORT_GENERATE, etc.
    granted_by INTEGER,
    granted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_date TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX idx_professional_permissions (professional_id, permission_type),
    INDEX idx_active_permissions (is_active, expires_date),
    FOREIGN KEY (professional_id) REFERENCES sa_healthcare_professionals(id) ON DELETE CASCADE
);

-- HPCSA Verification Log Table
CREATE TABLE IF NOT EXISTS sa_hpcsa_verification_log (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    professional_id INTEGER NOT NULL,
    hpcsa_number VARCHAR(20) NOT NULL,
    verification_type VARCHAR(30) NOT NULL, -- INITIAL, RENEWAL, MANUAL
    verification_status VARCHAR(20) NOT NULL, -- SUCCESS, FAILED, PENDING
    verification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verification_details TEXT,
    verified_by INTEGER,
    
    -- External verification data
    external_reference VARCHAR(100),
    external_response TEXT,
    
    INDEX idx_professional_verification (professional_id, verification_date),
    INDEX idx_hpcsa_verification (hpcsa_number, verification_status),
    INDEX idx_verification_date (verification_date),
    FOREIGN KEY (professional_id) REFERENCES sa_healthcare_professionals(id) ON DELETE CASCADE
);

-- Create views for common queries
CREATE VIEW sa_active_professionals AS
SELECT 
    hp.*,
    hc.category_name,
    hc.prefix as category_prefix,
    sp.province_name,
    ms.specialization_name
FROM sa_healthcare_professionals hp
LEFT JOIN sa_hpcsa_categories hc ON hp.registration_category = hc.category_code
LEFT JOIN sa_provinces sp ON hp.province_code = sp.province_code
LEFT JOIN sa_medical_specializations ms ON hp.specialization = ms.specialization_code
WHERE hp.is_active = TRUE AND hp.registration_status = 'ACTIVE';

-- View for verification status
CREATE VIEW sa_professional_verification_status AS
SELECT 
    hp.id,
    hp.hpcsa_number,
    hp.first_name,
    hp.last_name,
    hp.hpcsa_verified,
    hp.hpcsa_verified_date,
    hp.verification_attempts,
    hvl.verification_status as last_verification_status,
    hvl.verification_date as last_verification_date
FROM sa_healthcare_professionals hp
LEFT JOIN sa_hpcsa_verification_log hvl ON hp.id = hvl.professional_id
    AND hvl.id = (
        SELECT MAX(id) FROM sa_hpcsa_verification_log 
        WHERE professional_id = hp.id
    );