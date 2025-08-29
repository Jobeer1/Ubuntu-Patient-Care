-- South African Healthcare Integration Schema Extension
-- Extends Orthanc's SQLite database with SA-specific tables and fields

-- =====================================================
-- PHASE 1: Core SA Healthcare Tables
-- =====================================================

-- SA Users table (extends Orthanc's user management)
CREATE TABLE IF NOT EXISTS SAUsers (
    user_id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    salt VARCHAR(100) NOT NULL,
    full_name VARCHAR(200),
    email VARCHAR(100),
    role VARCHAR(50) DEFAULT 'viewer',
    province VARCHAR(50),
    preferred_language VARCHAR(10) DEFAULT 'en',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP NULL
);

-- SA Healthcare Professionals table (HPCSA integration)
CREATE TABLE IF NOT EXISTS SAHealthcareProfessionals (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50),
    hpcsa_number VARCHAR(20) UNIQUE NOT NULL,
    practice_number VARCHAR(20),
    practice_name VARCHAR(200),
    specialization VARCHAR(100),
    sub_specialization VARCHAR(100),
    province VARCHAR(50),
    city VARCHAR(100),
    phone VARCHAR(20),
    emergency_contact VARCHAR(20),
    is_verified BOOLEAN DEFAULT FALSE,
    verification_date TIMESTAMP,
    verification_method VARCHAR(50),
    license_expiry_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES SAUsers(user_id) ON DELETE CASCADE
);

-- SA Two-Factor Authentication table
CREATE TABLE IF NOT EXISTS SA2FA (
    user_id VARCHAR(50) PRIMARY KEY,
    secret_key VARCHAR(200) NOT NULL,
    backup_codes TEXT, -- JSON array of backup codes
    is_enabled BOOLEAN DEFAULT FALSE,
    enabled_at TIMESTAMP,
    failed_attempts INTEGER DEFAULT 0,
    last_failed_attempt TIMESTAMP,
    lockout_until TIMESTAMP,
    recovery_codes_used INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES SAUsers(user_id) ON DELETE CASCADE
);

-- =====================================================
-- PHASE 1: Extend Orthanc Core Tables
-- =====================================================

-- Extend Patients table with SA-specific fields
-- Note: These will be added to existing Orthanc Patients table
/*
ALTER TABLE Patients ADD COLUMN sa_id_number VARCHAR(13);
ALTER TABLE Patients ADD COLUMN medical_scheme VARCHAR(100);
ALTER TABLE Patients ADD COLUMN medical_scheme_number VARCHAR(50);
ALTER TABLE Patients ADD COLUMN scheme_option VARCHAR(100);
ALTER TABLE Patients ADD COLUMN preferred_language VARCHAR(10) DEFAULT 'en';
ALTER TABLE Patients ADD COLUMN traditional_name VARCHAR(255);
ALTER TABLE Patients ADD COLUMN popia_consent BOOLEAN DEFAULT FALSE;
ALTER TABLE Patients ADD COLUMN consent_date TIMESTAMP;
ALTER TABLE Patients ADD COLUMN consent_version VARCHAR(10);
ALTER TABLE Patients ADD COLUMN data_retention_period INTEGER DEFAULT 2555; -- 7 years in days
*/

-- SA Patient Extensions table (alternative approach to avoid altering core table)
CREATE TABLE IF NOT EXISTS SAPatientExtensions (
    patient_id VARCHAR(50) PRIMARY KEY,
    orthanc_patient_id VARCHAR(50) UNIQUE NOT NULL,
    sa_id_number VARCHAR(13),
    medical_scheme VARCHAR(100),
    medical_scheme_number VARCHAR(50),
    scheme_option VARCHAR(100),
    preferred_language VARCHAR(10) DEFAULT 'en',
    traditional_name VARCHAR(255),
    popia_consent BOOLEAN DEFAULT FALSE,
    consent_date TIMESTAMP,
    consent_version VARCHAR(10) DEFAULT '1.0',
    data_retention_period INTEGER DEFAULT 2555, -- 7 years in days
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- PHASE 2: SA Healthcare Features
-- =====================================================

-- SA Medical Reports table
CREATE TABLE IF NOT EXISTS SAReports (
    report_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50),
    study_id VARCHAR(50),
    series_id VARCHAR(50),
    template_id VARCHAR(50),
    template_name VARCHAR(200),
    content TEXT,
    structured_data TEXT, -- JSON structured report data
    language VARCHAR(10) DEFAULT 'en',
    status VARCHAR(50) DEFAULT 'draft', -- draft, completed, signed, archived
    created_by VARCHAR(50),
    reviewed_by VARCHAR(50),
    signed_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    signed_at TIMESTAMP,
    version INTEGER DEFAULT 1,
    FOREIGN KEY (created_by) REFERENCES SAUsers(user_id),
    FOREIGN KEY (reviewed_by) REFERENCES SAUsers(user_id),
    FOREIGN KEY (signed_by) REFERENCES SAUsers(user_id)
);

-- SA Secure Shares table (patient link sharing)
CREATE TABLE IF NOT EXISTS SASecureShares (
    share_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50),
    study_id VARCHAR(50),
    series_id VARCHAR(50),
    share_token VARCHAR(100) UNIQUE NOT NULL,
    share_type VARCHAR(50) DEFAULT 'view', -- view, download, annotate
    password_hash VARCHAR(255),
    created_by VARCHAR(50),
    recipient_email VARCHAR(100),
    recipient_name VARCHAR(200),
    expires_at TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    max_access_count INTEGER DEFAULT 0, -- 0 = unlimited
    last_accessed TIMESTAMP,
    last_access_ip VARCHAR(45),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES SAUsers(user_id)
);

-- SA Audit Log table (HPCSA and POPIA compliance)
CREATE TABLE IF NOT EXISTS SAAuditLog (
    audit_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50),
    hpcsa_number VARCHAR(20),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50), -- patient, study, series, instance, report
    resource_id VARCHAR(50),
    patient_id VARCHAR(50),
    details TEXT, -- JSON details of the action
    ip_address VARCHAR(45),
    user_agent TEXT,
    session_id VARCHAR(100),
    compliance_flags TEXT, -- JSON compliance metadata
    risk_level VARCHAR(20) DEFAULT 'low', -- low, medium, high, critical
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_patient_timestamp (patient_id, timestamp),
    INDEX idx_action_timestamp (action, timestamp)
);

-- =====================================================
-- PHASE 3: Advanced SA Features
-- =====================================================

-- SA Medical Templates table
CREATE TABLE IF NOT EXISTS SAMedicalTemplates (
    template_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100), -- TB_screening, trauma_assessment, etc.
    modality VARCHAR(20), -- CT, MRI, X-Ray, etc.
    body_part VARCHAR(100),
    language VARCHAR(10) DEFAULT 'en',
    template_data TEXT, -- JSON template structure
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    FOREIGN KEY (created_by) REFERENCES SAUsers(user_id)
);

-- SA Medical Terminology table (multi-language support)
CREATE TABLE IF NOT EXISTS SAMedicalTerminology (
    term_id VARCHAR(50) PRIMARY KEY,
    english_term VARCHAR(200) NOT NULL,
    afrikaans_term VARCHAR(200),
    zulu_term VARCHAR(200),
    xhosa_term VARCHAR(200),
    category VARCHAR(100), -- anatomy, pathology, procedure, etc.
    modality VARCHAR(20),
    body_system VARCHAR(100),
    synonyms TEXT, -- JSON array of synonyms
    abbreviations TEXT, -- JSON array of abbreviations
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- SA Referring Doctors table (doctor-patient relationships)
CREATE TABLE IF NOT EXISTS SAReferringDoctors (
    referral_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50),
    referring_doctor_id VARCHAR(50),
    study_id VARCHAR(50),
    referral_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    referral_reason TEXT,
    urgency_level VARCHAR(20) DEFAULT 'routine', -- urgent, routine, stat
    clinical_history TEXT,
    access_granted BOOLEAN DEFAULT TRUE,
    access_expires TIMESTAMP,
    notification_sent BOOLEAN DEFAULT FALSE,
    report_shared BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (referring_doctor_id) REFERENCES SAHealthcareProfessionals(id)
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- SA Users indexes
CREATE INDEX IF NOT EXISTS idx_sa_users_username ON SAUsers(username);
CREATE INDEX IF NOT EXISTS idx_sa_users_email ON SAUsers(email);
CREATE INDEX IF NOT EXISTS idx_sa_users_role ON SAUsers(role);
CREATE INDEX IF NOT EXISTS idx_sa_users_active ON SAUsers(is_active);

-- SA Healthcare Professionals indexes
CREATE INDEX IF NOT EXISTS idx_sa_hcp_hpcsa ON SAHealthcareProfessionals(hpcsa_number);
CREATE INDEX IF NOT EXISTS idx_sa_hcp_province ON SAHealthcareProfessionals(province);
CREATE INDEX IF NOT EXISTS idx_sa_hcp_specialization ON SAHealthcareProfessionals(specialization);
CREATE INDEX IF NOT EXISTS idx_sa_hcp_verified ON SAHealthcareProfessionals(is_verified);

-- SA Patient Extensions indexes
CREATE INDEX IF NOT EXISTS idx_sa_patient_sa_id ON SAPatientExtensions(sa_id_number);
CREATE INDEX IF NOT EXISTS idx_sa_patient_scheme ON SAPatientExtensions(medical_scheme);
CREATE INDEX IF NOT EXISTS idx_sa_patient_orthanc_id ON SAPatientExtensions(orthanc_patient_id);

-- SA Reports indexes
CREATE INDEX IF NOT EXISTS idx_sa_reports_patient ON SAReports(patient_id);
CREATE INDEX IF NOT EXISTS idx_sa_reports_study ON SAReports(study_id);
CREATE INDEX IF NOT EXISTS idx_sa_reports_created_by ON SAReports(created_by);
CREATE INDEX IF NOT EXISTS idx_sa_reports_status ON SAReports(status);
CREATE INDEX IF NOT EXISTS idx_sa_reports_created_at ON SAReports(created_at);

-- SA Secure Shares indexes
CREATE INDEX IF NOT EXISTS idx_sa_shares_token ON SASecureShares(share_token);
CREATE INDEX IF NOT EXISTS idx_sa_shares_patient ON SASecureShares(patient_id);
CREATE INDEX IF NOT EXISTS idx_sa_shares_created_by ON SASecureShares(created_by);
CREATE INDEX IF NOT EXISTS idx_sa_shares_expires ON SASecureShares(expires_at);
CREATE INDEX IF NOT EXISTS idx_sa_shares_active ON SASecureShares(is_active);

-- =====================================================
-- TRIGGERS FOR DATA INTEGRITY
-- =====================================================

-- Update timestamp trigger for SAHealthcareProfessionals
CREATE TRIGGER IF NOT EXISTS update_sa_hcp_timestamp 
    AFTER UPDATE ON SAHealthcareProfessionals
    FOR EACH ROW
    BEGIN
        UPDATE SAHealthcareProfessionals 
        SET updated_at = CURRENT_TIMESTAMP 
        WHERE id = NEW.id;
    END;

-- Update timestamp trigger for SAPatientExtensions
CREATE TRIGGER IF NOT EXISTS update_sa_patient_timestamp 
    AFTER UPDATE ON SAPatientExtensions
    FOR EACH ROW
    BEGIN
        UPDATE SAPatientExtensions 
        SET updated_at = CURRENT_TIMESTAMP 
        WHERE patient_id = NEW.patient_id;
    END;

-- Audit log trigger for sensitive operations
CREATE TRIGGER IF NOT EXISTS audit_sa_patient_access
    AFTER UPDATE ON SAPatientExtensions
    FOR EACH ROW
    WHEN NEW.popia_consent != OLD.popia_consent
    BEGIN
        INSERT INTO SAAuditLog (
            audit_id, action, resource_type, resource_id, patient_id,
            details, timestamp
        ) VALUES (
            'audit_' || hex(randomblob(16)),
            'POPIA_CONSENT_CHANGED',
            'patient',
            NEW.patient_id,
            NEW.patient_id,
            json_object('old_consent', OLD.popia_consent, 'new_consent', NEW.popia_consent),
            CURRENT_TIMESTAMP
        );
    END;

-- =====================================================
-- INITIAL DATA SETUP
-- =====================================================

-- Insert default SA provinces
INSERT OR IGNORE INTO SAMedicalTerminology (term_id, english_term, category) VALUES
('province_gp', 'Gauteng', 'geography'),
('province_wc', 'Western Cape', 'geography'),
('province_kzn', 'KwaZulu-Natal', 'geography'),
('province_ec', 'Eastern Cape', 'geography'),
('province_lp', 'Limpopo', 'geography'),
('province_mp', 'Mpumalanga', 'geography'),
('province_nw', 'North West', 'geography'),
('province_fs', 'Free State', 'geography'),
('province_nc', 'Northern Cape', 'geography');

-- Insert default medical schemes
INSERT OR IGNORE INTO SAMedicalTerminology (term_id, english_term, category) VALUES
('scheme_discovery', 'Discovery Health', 'medical_scheme'),
('scheme_momentum', 'Momentum Health', 'medical_scheme'),
('scheme_bonitas', 'Bonitas Medical Fund', 'medical_scheme'),
('scheme_medshield', 'Medshield Medical Scheme', 'medical_scheme'),
('scheme_gems', 'Government Employees Medical Scheme', 'medical_scheme'),
('scheme_polmed', 'Police Medical Scheme', 'medical_scheme');

-- Insert default specializations
INSERT OR IGNORE INTO SAMedicalTerminology (term_id, english_term, afrikaans_term, zulu_term, category) VALUES
('spec_radiology', 'Radiology', 'Radiologie', 'I-Radiology', 'specialization'),
('spec_cardiology', 'Cardiology', 'Kardiologie', 'I-Cardiology', 'specialization'),
('spec_neurology', 'Neurology', 'Neurologie', 'I-Neurology', 'specialization'),
('spec_orthopedics', 'Orthopedics', 'Ortopedies', 'I-Orthopedics', 'specialization'),
('spec_general', 'General Practice', 'Algemene Praktyk', 'Ukusebenza Jikelele', 'specialization');