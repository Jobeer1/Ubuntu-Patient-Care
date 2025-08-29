-- SA Comprehensive Audit Logging Schema
-- HPCSA and POPIA compliant audit logging system

-- Drop existing audit tables if they exist (for development)
-- DROP TABLE IF EXISTS sa_audit_log;
-- DROP TABLE IF EXISTS sa_audit_categories;
-- DROP TABLE IF EXISTS sa_audit_retention_policies;

-- Create audit categories lookup table
CREATE TABLE IF NOT EXISTS sa_audit_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_code VARCHAR(20) NOT NULL UNIQUE,
    category_name VARCHAR(100) NOT NULL,
    description TEXT,
    retention_days INTEGER DEFAULT 2555, -- 7 years default
    is_sensitive BOOLEAN DEFAULT 0,
    requires_encryption BOOLEAN DEFAULT 0,
    compliance_framework VARCHAR(50), -- HPCSA, POPIA, BOTH
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert audit categories
INSERT OR IGNORE INTO sa_audit_categories 
(category_code, category_name, description, retention_days, is_sensitive, requires_encryption, compliance_framework) VALUES
-- Authentication and Access
('AUTH_LOGIN', 'User Login', 'User authentication attempts', 2555, 0, 0, 'BOTH'),
('AUTH_LOGOUT', 'User Logout', 'User logout events', 2555, 0, 0, 'BOTH'),
('AUTH_FAILED', 'Failed Authentication', 'Failed login attempts', 2555, 1, 0, 'BOTH'),
('AUTH_2FA', 'Two-Factor Authentication', '2FA verification events', 2555, 1, 0, 'BOTH'),
('AUTH_SESSION', 'Session Management', 'Session creation, validation, destruction', 1825, 0, 0, 'BOTH'),

-- Data Access and Modification
('DATA_VIEW', 'Data Viewing', 'Patient data viewing events', 2555, 1, 1, 'BOTH'),
('DATA_CREATE', 'Data Creation', 'New patient/study data creation', 2555, 1, 1, 'BOTH'),
('DATA_UPDATE', 'Data Modification', 'Patient/study data modifications', 2555, 1, 1, 'BOTH'),
('DATA_DELETE', 'Data Deletion', 'Data deletion events', 2555, 1, 1, 'BOTH'),
('DATA_EXPORT', 'Data Export', 'Data export/download events', 2555, 1, 1, 'BOTH'),
('DATA_PRINT', 'Data Printing', 'Report/image printing events', 2555, 1, 0, 'BOTH'),

-- DICOM Operations
('DICOM_STORE', 'DICOM Storage', 'DICOM image storage events', 2555, 1, 1, 'HPCSA'),
('DICOM_RETRIEVE', 'DICOM Retrieval', 'DICOM image retrieval events', 2555, 1, 1, 'HPCSA'),
('DICOM_QUERY', 'DICOM Query', 'DICOM database queries', 1825, 1, 0, 'HPCSA'),
('DICOM_MOVE', 'DICOM Move', 'DICOM image transfer events', 2555, 1, 1, 'HPCSA'),
('DICOM_DELETE', 'DICOM Deletion', 'DICOM image deletion events', 2555, 1, 1, 'HPCSA'),

-- Healthcare Professional Operations
('HPCSA_VALIDATE', 'HPCSA Validation', 'Healthcare professional validation', 2555, 0, 0, 'HPCSA'),
('HPCSA_CREATE', 'Professional Creation', 'New healthcare professional registration', 2555, 1, 0, 'HPCSA'),
('HPCSA_UPDATE', 'Professional Update', 'Healthcare professional data updates', 2555, 1, 0, 'HPCSA'),
('HPCSA_STATUS', 'Status Change', 'Professional status changes', 2555, 1, 0, 'HPCSA'),

-- Medical Aid Operations
('MEDAID_VALIDATE', 'Medical Aid Validation', 'Medical aid member validation', 2555, 1, 1, 'POPIA'),
('MEDAID_QUERY', 'Medical Aid Query', 'Medical aid information queries', 1825, 1, 1, 'POPIA'),
('MEDAID_UPDATE', 'Medical Aid Update', 'Medical aid information updates', 2555, 1, 1, 'POPIA'),

-- System Operations
('SYSTEM_CONFIG', 'System Configuration', 'System configuration changes', 2555, 0, 0, 'BOTH'),
('SYSTEM_BACKUP', 'System Backup', 'Backup operations', 1095, 0, 0, 'BOTH'),
('SYSTEM_RESTORE', 'System Restore', 'Restore operations', 2555, 1, 0, 'BOTH'),
('SYSTEM_MAINTENANCE', 'System Maintenance', 'Maintenance operations', 1095, 0, 0, 'BOTH'),

-- Compliance and Privacy
('POPIA_CONSENT', 'POPIA Consent', 'Data processing consent events', 2555, 1, 1, 'POPIA'),
('POPIA_ACCESS', 'Data Subject Access', 'Data subject access requests', 2555, 1, 1, 'POPIA'),
('POPIA_CORRECTION', 'Data Correction', 'Data correction requests', 2555, 1, 1, 'POPIA'),
('POPIA_DELETION', 'Data Deletion Request', 'Data deletion requests', 2555, 1, 1, 'POPIA'),
('PRIVACY_BREACH', 'Privacy Breach', 'Potential privacy breach incidents', 2555, 1, 1, 'POPIA'),

-- Security Events
('SECURITY_ALERT', 'Security Alert', 'Security-related alerts', 2555, 1, 0, 'BOTH'),
('SECURITY_BREACH', 'Security Breach', 'Security breach incidents', 2555, 1, 1, 'BOTH'),
('SECURITY_SCAN', 'Security Scan', 'Security scanning events', 365, 0, 0, 'BOTH'),

-- Administrative
('ADMIN_USER', 'User Administration', 'User account administration', 2555, 1, 0, 'BOTH'),
('ADMIN_ROLE', 'Role Administration', 'Role and permission changes', 2555, 1, 0, 'BOTH'),
('ADMIN_POLICY', 'Policy Administration', 'Policy and procedure changes', 2555, 0, 0, 'BOTH');

-- Create comprehensive audit log table
CREATE TABLE IF NOT EXISTS sa_audit_log (
    -- Primary identification
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_uuid VARCHAR(36) NOT NULL UNIQUE, -- UUID for cross-system correlation
    
    -- Event classification
    category_code VARCHAR(20) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_subtype VARCHAR(50),
    severity_level VARCHAR(10) DEFAULT 'INFO', -- DEBUG, INFO, WARN, ERROR, CRITICAL
    
    -- Timestamp information
    event_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_date DATE GENERATED ALWAYS AS (DATE(event_timestamp)) STORED,
    event_hour INTEGER GENERATED ALWAYS AS (CAST(strftime('%H', event_timestamp) AS INTEGER)) STORED,
    
    -- User and session information
    user_id VARCHAR(100),
    username VARCHAR(100),
    user_role VARCHAR(50),
    session_id VARCHAR(100),
    hpcsa_number VARCHAR(20),
    
    -- Network and system information
    ip_address VARCHAR(45), -- IPv6 compatible
    user_agent TEXT,
    request_method VARCHAR(10),
    request_url TEXT,
    response_status INTEGER,
    
    -- Resource information
    resource_type VARCHAR(50), -- PATIENT, STUDY, SERIES, INSTANCE, USER, etc.
    resource_id VARCHAR(100),
    resource_name VARCHAR(200),
    parent_resource_type VARCHAR(50),
    parent_resource_id VARCHAR(100),
    
    -- Event details
    action VARCHAR(100) NOT NULL,
    description TEXT,
    event_data TEXT, -- JSON data for complex events
    
    -- Before/after data for changes
    old_values TEXT, -- JSON of old values
    new_values TEXT, -- JSON of new values
    changed_fields TEXT, -- JSON array of changed field names
    
    -- Patient information (for healthcare events)
    patient_id VARCHAR(100),
    patient_identifier VARCHAR(100), -- SA ID, Passport, etc.
    patient_name_hash VARCHAR(64), -- Hashed for privacy
    
    -- Study/DICOM information
    study_instance_uid VARCHAR(100),
    series_instance_uid VARCHAR(100),
    sop_instance_uid VARCHAR(100),
    modality VARCHAR(10),
    study_date DATE,
    
    -- Compliance and privacy
    contains_phi BOOLEAN DEFAULT 0, -- Contains Personal Health Information
    contains_pii BOOLEAN DEFAULT 0, -- Contains Personally Identifiable Information
    consent_status VARCHAR(20), -- GIVEN, WITHDRAWN, PENDING, NOT_REQUIRED
    legal_basis VARCHAR(50), -- POPIA legal basis for processing
    
    -- Data classification
    data_classification VARCHAR(20) DEFAULT 'INTERNAL', -- PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
    sensitivity_level INTEGER DEFAULT 1, -- 1-5 scale
    
    -- Geographic and organizational
    facility_code VARCHAR(20),
    department_code VARCHAR(20),
    location VARCHAR(100),
    
    -- Technical details
    application_name VARCHAR(50) DEFAULT 'ORTHANC_SA',
    application_version VARCHAR(20),
    system_hostname VARCHAR(100),
    process_id INTEGER,
    thread_id INTEGER,
    
    -- Performance metrics
    execution_time_ms INTEGER,
    data_size_bytes INTEGER,
    
    -- Error information
    error_code VARCHAR(50),
    error_message TEXT,
    stack_trace TEXT,
    
    -- Correlation and tracing
    correlation_id VARCHAR(100), -- For tracing related events
    parent_audit_id INTEGER, -- For hierarchical events
    transaction_id VARCHAR(100),
    
    -- Retention and archival
    retention_date DATE, -- When this record can be deleted
    archived BOOLEAN DEFAULT 0,
    archived_at DATETIME,
    
    -- Verification and integrity
    checksum VARCHAR(64), -- For data integrity verification
    digital_signature TEXT, -- For non-repudiation
    
    -- System fields
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'SYSTEM',
    
    -- Constraints and foreign keys
    FOREIGN KEY (category_code) REFERENCES sa_audit_categories(category_code),
    FOREIGN KEY (parent_audit_id) REFERENCES sa_audit_log(id),
    
    -- Check constraints
    CONSTRAINT chk_severity_level CHECK (
        severity_level IN ('DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL')
    ),
    CONSTRAINT chk_consent_status CHECK (
        consent_status IN ('GIVEN', 'WITHDRAWN', 'PENDING', 'NOT_REQUIRED', 'UNKNOWN')
    ),
    CONSTRAINT chk_data_classification CHECK (
        data_classification IN ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED')
    ),
    CONSTRAINT chk_sensitivity_level CHECK (
        sensitivity_level BETWEEN 1 AND 5
    )
);

-- Create comprehensive indexes for efficient querying
-- Primary access patterns
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON sa_audit_log(event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_date ON sa_audit_log(event_date DESC);
CREATE INDEX IF NOT EXISTS idx_audit_category ON sa_audit_log(category_code);
CREATE INDEX IF NOT EXISTS idx_audit_user ON sa_audit_log(username);
CREATE INDEX IF NOT EXISTS idx_audit_user_id ON sa_audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_session ON sa_audit_log(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_ip ON sa_audit_log(ip_address);
CREATE INDEX IF NOT EXISTS idx_audit_action ON sa_audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON sa_audit_log(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_patient ON sa_audit_log(patient_id);
CREATE INDEX IF NOT EXISTS idx_audit_hpcsa ON sa_audit_log(hpcsa_number);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_audit_user_date ON sa_audit_log(username, event_date DESC);
CREATE INDEX IF NOT EXISTS idx_audit_category_date ON sa_audit_log(category_code, event_date DESC);
CREATE INDEX IF NOT EXISTS idx_audit_patient_date ON sa_audit_log(patient_id, event_date DESC) WHERE patient_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_resource_action ON sa_audit_log(resource_type, action, event_date DESC);
CREATE INDEX IF NOT EXISTS idx_audit_severity_date ON sa_audit_log(severity_level, event_date DESC) WHERE severity_level IN ('ERROR', 'CRITICAL');

-- DICOM-specific indexes
CREATE INDEX IF NOT EXISTS idx_audit_study ON sa_audit_log(study_instance_uid) WHERE study_instance_uid IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_series ON sa_audit_log(series_instance_uid) WHERE series_instance_uid IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_modality ON sa_audit_log(modality) WHERE modality IS NOT NULL;

-- Compliance and privacy indexes
CREATE INDEX IF NOT EXISTS idx_audit_phi ON sa_audit_log(contains_phi, event_date DESC) WHERE contains_phi = 1;
CREATE INDEX IF NOT EXISTS idx_audit_pii ON sa_audit_log(contains_pii, event_date DESC) WHERE contains_pii = 1;
CREATE INDEX IF NOT EXISTS idx_audit_consent ON sa_audit_log(consent_status, event_date DESC);
CREATE INDEX IF NOT EXISTS idx_audit_classification ON sa_audit_log(data_classification, sensitivity_level);

-- Retention and archival indexes
CREATE INDEX IF NOT EXISTS idx_audit_retention ON sa_audit_log(retention_date) WHERE retention_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_archived ON sa_audit_log(archived, archived_at);

-- Correlation and tracing indexes
CREATE INDEX IF NOT EXISTS idx_audit_correlation ON sa_audit_log(correlation_id) WHERE correlation_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_transaction ON sa_audit_log(transaction_id) WHERE transaction_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_parent ON sa_audit_log(parent_audit_id) WHERE parent_audit_id IS NOT NULL;

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_audit_execution_time ON sa_audit_log(execution_time_ms DESC) WHERE execution_time_ms > 1000;
CREATE INDEX IF NOT EXISTS idx_audit_data_size ON sa_audit_log(data_size_bytes DESC) WHERE data_size_bytes > 1048576; -- > 1MB

-- Create audit retention policies table
CREATE TABLE IF NOT EXISTS sa_audit_retention_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_name VARCHAR(100) NOT NULL UNIQUE,
    category_code VARCHAR(20),
    retention_days INTEGER NOT NULL,
    archive_after_days INTEGER,
    auto_delete BOOLEAN DEFAULT 0,
    encryption_required BOOLEAN DEFAULT 0,
    backup_required BOOLEAN DEFAULT 1,
    compliance_framework VARCHAR(50),
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (category_code) REFERENCES sa_audit_categories(category_code)
);

-- Insert default retention policies
INSERT OR IGNORE INTO sa_audit_retention_policies 
(policy_name, category_code, retention_days, archive_after_days, auto_delete, encryption_required, compliance_framework, description) VALUES
('HPCSA_STANDARD', NULL, 2555, 1825, 0, 0, 'HPCSA', 'Standard HPCSA retention: 7 years, archive after 5 years'),
('POPIA_SENSITIVE', NULL, 2555, 365, 0, 1, 'POPIA', 'POPIA sensitive data: 7 years with encryption, archive after 1 year'),
('SECURITY_EVENTS', 'SECURITY_ALERT', 1095, 365, 0, 0, 'BOTH', 'Security events: 3 years, archive after 1 year'),
('SYSTEM_LOGS', 'SYSTEM_MAINTENANCE', 365, 90, 1, 0, 'BOTH', 'System logs: 1 year, archive after 90 days, auto-delete'),
('AUTHENTICATION', 'AUTH_LOGIN', 1825, 365, 0, 0, 'BOTH', 'Authentication logs: 5 years, archive after 1 year');

-- Create triggers for automatic audit log management

-- Trigger to set retention date based on category
CREATE TRIGGER IF NOT EXISTS trg_audit_set_retention
    AFTER INSERT ON sa_audit_log
    FOR EACH ROW
    WHEN NEW.retention_date IS NULL
BEGIN
    UPDATE sa_audit_log 
    SET retention_date = DATE(NEW.event_timestamp, '+' || 
        (SELECT COALESCE(retention_days, 2555) FROM sa_audit_categories WHERE category_code = NEW.category_code) || ' days')
    WHERE id = NEW.id;
END;

-- Trigger to generate UUID if not provided
CREATE TRIGGER IF NOT EXISTS trg_audit_generate_uuid
    AFTER INSERT ON sa_audit_log
    FOR EACH ROW
    WHEN NEW.audit_uuid IS NULL
BEGIN
    UPDATE sa_audit_log 
    SET audit_uuid = (
        lower(hex(randomblob(4))) || '-' || 
        lower(hex(randomblob(2))) || '-' || 
        '4' || substr(lower(hex(randomblob(2))), 2) || '-' || 
        substr('89ab', abs(random()) % 4 + 1, 1) || 
        substr(lower(hex(randomblob(2))), 2) || '-' || 
        lower(hex(randomblob(6)))
    )
    WHERE id = NEW.id;
END;

-- Trigger to calculate checksum for integrity
CREATE TRIGGER IF NOT EXISTS trg_audit_calculate_checksum
    AFTER INSERT ON sa_audit_log
    FOR EACH ROW
    WHEN NEW.checksum IS NULL
BEGIN
    UPDATE sa_audit_log 
    SET checksum = hex(
        hash(
            COALESCE(NEW.category_code, '') || 
            COALESCE(NEW.event_type, '') || 
            COALESCE(NEW.username, '') || 
            COALESCE(NEW.action, '') || 
            COALESCE(NEW.resource_id, '') || 
            NEW.event_timestamp
        )
    )
    WHERE id = NEW.id;
END;

-- Create views for common audit queries

-- View for recent audit events
CREATE VIEW IF NOT EXISTS vw_recent_audit_events AS
SELECT 
    al.*,
    ac.category_name,
    ac.compliance_framework,
    ac.is_sensitive
FROM sa_audit_log al
LEFT JOIN sa_audit_categories ac ON al.category_code = ac.category_code
WHERE al.event_timestamp >= datetime('now', '-7 days')
ORDER BY al.event_timestamp DESC;

-- View for security events
CREATE VIEW IF NOT EXISTS vw_security_audit_events AS
SELECT 
    al.*,
    ac.category_name
FROM sa_audit_log al
LEFT JOIN sa_audit_categories ac ON al.category_code = ac.category_code
WHERE al.category_code LIKE 'SECURITY_%' 
   OR al.category_code LIKE 'AUTH_%'
   OR al.severity_level IN ('ERROR', 'CRITICAL')
ORDER BY al.event_timestamp DESC;

-- View for patient data access
CREATE VIEW IF NOT EXISTS vw_patient_data_access AS
SELECT 
    al.*,
    ac.category_name
FROM sa_audit_log al
LEFT JOIN sa_audit_categories ac ON al.category_code = ac.category_code
WHERE al.patient_id IS NOT NULL
   OR al.contains_phi = 1
   OR al.contains_pii = 1
ORDER BY al.event_timestamp DESC;

-- View for HPCSA compliance events
CREATE VIEW IF NOT EXISTS vw_hpcsa_compliance_events AS
SELECT 
    al.*,
    ac.category_name
FROM sa_audit_log al
LEFT JOIN sa_audit_categories ac ON al.category_code = ac.category_code
WHERE ac.compliance_framework IN ('HPCSA', 'BOTH')
   OR al.hpcsa_number IS NOT NULL
ORDER BY al.event_timestamp DESC;

-- View for POPIA compliance events
CREATE VIEW IF NOT EXISTS vw_popia_compliance_events AS
SELECT 
    al.*,
    ac.category_name
FROM sa_audit_log al
LEFT JOIN sa_audit_categories ac ON al.category_code = ac.category_code
WHERE ac.compliance_framework IN ('POPIA', 'BOTH')
   OR al.contains_pii = 1
   OR al.consent_status IS NOT NULL
ORDER BY al.event_timestamp DESC;

-- View for audit statistics
CREATE VIEW IF NOT EXISTS vw_audit_statistics AS
SELECT 
    DATE(event_timestamp) as audit_date,
    category_code,
    COUNT(*) as event_count,
    COUNT(DISTINCT username) as unique_users,
    COUNT(DISTINCT ip_address) as unique_ips,
    SUM(CASE WHEN severity_level = 'ERROR' THEN 1 ELSE 0 END) as error_count,
    SUM(CASE WHEN severity_level = 'CRITICAL' THEN 1 ELSE 0 END) as critical_count,
    SUM(CASE WHEN contains_phi = 1 THEN 1 ELSE 0 END) as phi_events,
    SUM(CASE WHEN contains_pii = 1 THEN 1 ELSE 0 END) as pii_events,
    AVG(execution_time_ms) as avg_execution_time,
    SUM(data_size_bytes) as total_data_size
FROM sa_audit_log
WHERE event_timestamp >= datetime('now', '-30 days')
GROUP BY DATE(event_timestamp), category_code
ORDER BY audit_date DESC, event_count DESC;

-- Create sample audit entries for testing
INSERT OR IGNORE INTO sa_audit_log 
(category_code, event_type, action, username, user_role, ip_address, description, severity_level, created_by) VALUES
('AUTH_LOGIN', 'USER_LOGIN', 'LOGIN_SUCCESS', 'admin', 'ADMINISTRATOR', '127.0.0.1', 'Administrator login successful', 'INFO', 'SYSTEM'),
('DATA_VIEW', 'PATIENT_VIEW', 'VIEW_PATIENT_RECORD', 'dr.smith', 'DOCTOR', '192.168.1.100', 'Viewed patient medical record', 'INFO', 'SYSTEM'),
('DICOM_STORE', 'IMAGE_STORE', 'STORE_DICOM_IMAGE', 'tech.jones', 'TECHNICIAN', '192.168.1.101', 'Stored new DICOM image', 'INFO', 'SYSTEM'),
('HPCSA_VALIDATE', 'PROFESSIONAL_VALIDATION', 'VALIDATE_HPCSA_NUMBER', 'admin', 'ADMINISTRATOR', '127.0.0.1', 'Validated healthcare professional HPCSA number', 'INFO', 'SYSTEM'),
('SECURITY_ALERT', 'FAILED_LOGIN', 'LOGIN_FAILED', 'unknown', 'UNKNOWN', '203.0.113.1', 'Multiple failed login attempts detected', 'WARN', 'SYSTEM');

-- Create cleanup procedures (to be implemented as application functions)
-- Note: SQLite doesn't support stored procedures, implement these in application code:
-- 1. cleanup_expired_audit_logs() - Remove logs past retention date
-- 2. archive_old_audit_logs() - Move old logs to archive tables
-- 3. generate_audit_report(start_date, end_date, category) - Generate compliance reports
-- 4. validate_audit_integrity() - Verify checksums and detect tampering
-- 5. export_audit_logs(criteria) - Export logs for external analysis