-- SA Comprehensive Audit Logging Schema
-- Supports HPCSA and POPIA compliance requirements
-- Compatible with MySQL, PostgreSQL, SQL Server, Oracle, SQLite

-- Main Audit Log Table
CREATE TABLE IF NOT EXISTS sa_audit_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- Event Identification
    event_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- LOGIN, LOGOUT, DICOM_ACCESS, PATIENT_VIEW, etc.
    event_category VARCHAR(30) NOT NULL, -- AUTHENTICATION, DICOM, PATIENT, SYSTEM, COMPLIANCE
    event_severity VARCHAR(20) DEFAULT 'INFO', -- INFO, WARNING, ERROR, CRITICAL
    
    -- Timestamp Information
    event_timestamp TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    event_date DATE GENERATED ALWAYS AS (DATE(event_timestamp)) STORED,
    event_hour TINYINT GENERATED ALWAYS AS (HOUR(event_timestamp)) STORED,
    
    -- User and Session Information
    user_id INTEGER,
    username VARCHAR(100),
    hpcsa_number VARCHAR(20),
    session_token VARCHAR(255),
    user_role VARCHAR(50),
    
    -- Source Information
    source_ip VARCHAR(45), -- IPv6 compatible
    source_port INTEGER,
    user_agent TEXT,
    client_application VARCHAR(100),
    client_version VARCHAR(50),
    
    -- Resource Information
    resource_type VARCHAR(50), -- PATIENT, STUDY, SERIES, INSTANCE, USER, etc.
    resource_id VARCHAR(100),
    resource_name VARCHAR(255),
    parent_resource_id VARCHAR(100),
    
    -- DICOM Specific Information
    patient_id VARCHAR(100),
    study_instance_uid VARCHAR(255),
    series_instance_uid VARCHAR(255),
    sop_instance_uid VARCHAR(255),
    modality VARCHAR(10),
    study_date DATE,
    
    -- Action Details
    action_performed VARCHAR(100), -- VIEW, EDIT, DELETE, DOWNLOAD, UPLOAD, etc.
    action_result VARCHAR(20) DEFAULT 'SUCCESS', -- SUCCESS, FAILED, PARTIAL
    action_details TEXT,
    
    -- POPIA Compliance Fields
    data_subject_consent BOOLEAN,
    data_processing_purpose VARCHAR(200),
    data_retention_category VARCHAR(50),
    data_minimization_applied BOOLEAN DEFAULT TRUE,
    
    -- HPCSA Compliance Fields
    professional_context VARCHAR(100), -- DIAGNOSIS, TREATMENT, CONSULTATION, etc.
    patient_relationship VARCHAR(50), -- PRIMARY_CARE, REFERRAL, CONSULTATION, etc.
    clinical_justification TEXT,
    
    -- Technical Information
    request_method VARCHAR(10), -- GET, POST, PUT, DELETE
    request_url TEXT,
    request_size INTEGER,
    response_code INTEGER,
    response_size INTEGER,
    processing_time_ms INTEGER,
    
    -- Error Information
    error_code VARCHAR(50),
    error_message TEXT,
    stack_trace TEXT,
    
    -- Compliance and Security
    compliance_flags JSON, -- Flexible compliance metadata
    security_level VARCHAR(20) DEFAULT 'STANDARD', -- STANDARD, HIGH, CRITICAL
    encryption_used BOOLEAN DEFAULT FALSE,
    data_classification VARCHAR(30), -- PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
    
    -- Retention and Archival
    retention_period_days INTEGER DEFAULT 2555, -- 7 years default for medical records
    archive_date DATE,
    is_archived BOOLEAN DEFAULT FALSE,
    
    -- Indexes for performance
    INDEX idx_event_timestamp (event_timestamp),
    INDEX idx_event_type_category (event_type, event_category),
    INDEX idx_user_events (user_id, event_timestamp),
    INDEX idx_hpcsa_events (hpcsa_number, event_timestamp),
    INDEX idx_patient_events (patient_id, event_timestamp),
    INDEX idx_study_events (study_instance_uid, event_timestamp),
    INDEX idx_resource_events (resource_type, resource_id, event_timestamp),
    INDEX idx_compliance_events (event_category, event_severity, event_timestamp),
    INDEX idx_session_events (session_token, event_timestamp),
    INDEX idx_source_ip (source_ip, event_timestamp),
    INDEX idx_event_date_hour (event_date, event_hour),
    INDEX idx_retention_archive (retention_period_days, archive_date, is_archived)
);

-- Audit Log Categories Reference Table
CREATE TABLE IF NOT EXISTS sa_audit_categories (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    category_code VARCHAR(30) NOT NULL UNIQUE,
    category_name VARCHAR(100) NOT NULL,
    description TEXT,
    retention_days INTEGER DEFAULT 2555,
    compliance_level VARCHAR(20) DEFAULT 'STANDARD',
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX idx_category_code (category_code)
);

-- Insert standard audit categories
INSERT INTO sa_audit_categories (category_code, category_name, description, retention_days, compliance_level) VALUES
('AUTHENTICATION', 'Authentication Events', 'Login, logout, session management', 2555, 'HIGH'),
('DICOM', 'DICOM Operations', 'DICOM data access, modification, transfer', 2555, 'CRITICAL'),
('PATIENT', 'Patient Data Access', 'Patient information viewing, editing', 2555, 'CRITICAL'),
('SYSTEM', 'System Operations', 'System configuration, maintenance', 1095, 'STANDARD'),
('COMPLIANCE', 'Compliance Events', 'HPCSA, POPIA compliance checks', 2555, 'CRITICAL'),
('SECURITY', 'Security Events', 'Security violations, suspicious activity', 2555, 'CRITICAL'),
('ADMIN', 'Administrative Actions', 'User management, system administration', 2555, 'HIGH'),
('BACKUP', 'Backup Operations', 'Data backup and recovery operations', 365, 'STANDARD'),
('INTEGRATION', 'System Integration', 'External system communications', 1095, 'STANDARD'),
('PERFORMANCE', 'Performance Monitoring', 'System performance and health checks', 90, 'STANDARD')
ON DUPLICATE KEY UPDATE category_name = VALUES(category_name);

-- Data Processing Purposes for POPIA Compliance
CREATE TABLE IF NOT EXISTS sa_data_processing_purposes (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    purpose_code VARCHAR(50) NOT NULL UNIQUE,
    purpose_name VARCHAR(200) NOT NULL,
    description TEXT,
    legal_basis VARCHAR(100),
    retention_period_days INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX idx_purpose_code (purpose_code)
);

-- Insert POPIA-compliant data processing purposes
INSERT INTO sa_data_processing_purposes (purpose_code, purpose_name, description, legal_basis, retention_period_days) VALUES
('MEDICAL_TREATMENT', 'Medical Treatment and Care', 'Processing for direct medical treatment of the patient', 'Vital interests of data subject', 2555),
('MEDICAL_DIAGNOSIS', 'Medical Diagnosis', 'Processing for diagnostic purposes', 'Vital interests of data subject', 2555),
('HEALTHCARE_ADMIN', 'Healthcare Administration', 'Administrative processing for healthcare delivery', 'Legitimate interests', 2555),
('MEDICAL_RESEARCH', 'Medical Research', 'Processing for medical research purposes', 'Consent', 3650),
('QUALITY_ASSURANCE', 'Quality Assurance', 'Processing for healthcare quality improvement', 'Legitimate interests', 1825),
('LEGAL_COMPLIANCE', 'Legal Compliance', 'Processing required by law', 'Legal obligation', 2555),
('BILLING_INSURANCE', 'Billing and Insurance', 'Processing for billing and insurance claims', 'Contract', 2190),
('SYSTEM_MAINTENANCE', 'System Maintenance', 'Technical system maintenance and support', 'Legitimate interests', 365),
('SECURITY_MONITORING', 'Security Monitoring', 'Monitoring for security and fraud prevention', 'Legitimate interests', 1095),
('AUDIT_COMPLIANCE', 'Audit and Compliance', 'Regulatory audit and compliance monitoring', 'Legal obligation', 2555)
ON DUPLICATE KEY UPDATE purpose_name = VALUES(purpose_name);

-- Audit Log Summary Table (for performance)
CREATE TABLE IF NOT EXISTS sa_audit_summary (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    summary_date DATE NOT NULL,
    summary_hour TINYINT NOT NULL,
    event_category VARCHAR(30) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    
    -- Counts
    total_events INTEGER DEFAULT 0,
    success_events INTEGER DEFAULT 0,
    failed_events INTEGER DEFAULT 0,
    warning_events INTEGER DEFAULT 0,
    error_events INTEGER DEFAULT 0,
    
    -- User Statistics
    unique_users INTEGER DEFAULT 0,
    unique_hpcsa_numbers INTEGER DEFAULT 0,
    unique_sessions INTEGER DEFAULT 0,
    unique_source_ips INTEGER DEFAULT 0,
    
    -- Resource Statistics
    unique_patients INTEGER DEFAULT 0,
    unique_studies INTEGER DEFAULT 0,
    dicom_instances_accessed INTEGER DEFAULT 0,
    
    -- Performance Statistics
    avg_processing_time_ms DECIMAL(10,2) DEFAULT 0,
    max_processing_time_ms INTEGER DEFAULT 0,
    total_data_transferred_mb DECIMAL(15,2) DEFAULT 0,
    
    -- Compliance Statistics
    popia_compliant_events INTEGER DEFAULT 0,
    hpcsa_compliant_events INTEGER DEFAULT 0,
    consent_verified_events INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_summary (summary_date, summary_hour, event_category, event_type),
    INDEX idx_summary_date (summary_date),
    INDEX idx_summary_category (event_category, summary_date),
    INDEX idx_summary_performance (summary_date, avg_processing_time_ms)
);

-- Audit Log Retention Policy Table
CREATE TABLE IF NOT EXISTS sa_audit_retention_policy (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    policy_name VARCHAR(100) NOT NULL UNIQUE,
    event_category VARCHAR(30) NOT NULL,
    retention_days INTEGER NOT NULL,
    archive_after_days INTEGER,
    delete_after_days INTEGER,
    compression_enabled BOOLEAN DEFAULT TRUE,
    encryption_required BOOLEAN DEFAULT FALSE,
    
    -- Policy conditions
    conditions JSON, -- Flexible conditions for policy application
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_policy_category (event_category),
    INDEX idx_policy_retention (retention_days)
);

-- Insert default retention policies
INSERT INTO sa_audit_retention_policy (policy_name, event_category, retention_days, archive_after_days, delete_after_days, encryption_required) VALUES
('HPCSA_Medical_Records', 'DICOM', 2555, 1825, 3650, TRUE), -- 7 years retention, 10 years deletion
('HPCSA_Patient_Data', 'PATIENT', 2555, 1825, 3650, TRUE),
('POPIA_Authentication', 'AUTHENTICATION', 2555, 1095, 2555, FALSE),
('Security_Critical', 'SECURITY', 2555, 365, 3650, TRUE),
('System_Operations', 'SYSTEM', 365, 180, 730, FALSE),
('Performance_Monitoring', 'PERFORMANCE', 90, 30, 180, FALSE),
('Compliance_Audit', 'COMPLIANCE', 2555, 1825, 3650, TRUE)
ON DUPLICATE KEY UPDATE retention_days = VALUES(retention_days);

-- Views for common audit queries
CREATE VIEW sa_recent_critical_events AS
SELECT 
    al.*,
    ac.category_name,
    dpp.purpose_name
FROM sa_audit_log al
LEFT JOIN sa_audit_categories ac ON al.event_category = ac.category_code
LEFT JOIN sa_data_processing_purposes dpp ON al.data_processing_purpose = dpp.purpose_code
WHERE al.event_timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
AND al.event_severity IN ('ERROR', 'CRITICAL')
ORDER BY al.event_timestamp DESC;

-- View for HPCSA compliance reporting
CREATE VIEW sa_hpcsa_compliance_report AS
SELECT 
    DATE(al.event_timestamp) as report_date,
    al.hpcsa_number,
    al.professional_context,
    COUNT(*) as total_accesses,
    COUNT(DISTINCT al.patient_id) as unique_patients,
    COUNT(DISTINCT al.study_instance_uid) as unique_studies,
    SUM(CASE WHEN al.action_result = 'SUCCESS' THEN 1 ELSE 0 END) as successful_accesses,
    SUM(CASE WHEN al.clinical_justification IS NOT NULL THEN 1 ELSE 0 END) as justified_accesses
FROM sa_audit_log al
WHERE al.event_category IN ('DICOM', 'PATIENT')
AND al.hpcsa_number IS NOT NULL
AND al.event_timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(al.event_timestamp), al.hpcsa_number, al.professional_context
ORDER BY report_date DESC, al.hpcsa_number;

-- View for POPIA compliance reporting
CREATE VIEW sa_popia_compliance_report AS
SELECT 
    DATE(al.event_timestamp) as report_date,
    al.data_processing_purpose,
    dpp.purpose_name,
    COUNT(*) as total_processing_events,
    SUM(CASE WHEN al.data_subject_consent = TRUE THEN 1 ELSE 0 END) as consent_verified_events,
    SUM(CASE WHEN al.data_minimization_applied = TRUE THEN 1 ELSE 0 END) as minimization_applied_events,
    COUNT(DISTINCT al.patient_id) as unique_data_subjects,
    AVG(al.processing_time_ms) as avg_processing_time
FROM sa_audit_log al
LEFT JOIN sa_data_processing_purposes dpp ON al.data_processing_purpose = dpp.purpose_code
WHERE al.event_timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)
AND al.data_processing_purpose IS NOT NULL
GROUP BY DATE(al.event_timestamp), al.data_processing_purpose, dpp.purpose_name
ORDER BY report_date DESC, total_processing_events DESC;

-- Stored procedures for audit log maintenance
DELIMITER //

CREATE PROCEDURE sa_cleanup_audit_logs()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_category VARCHAR(30);
    DECLARE v_retention_days INT;
    DECLARE v_delete_after_days INT;
    
    DECLARE retention_cursor CURSOR FOR 
        SELECT event_category, retention_days, delete_after_days 
        FROM sa_audit_retention_policy 
        WHERE is_active = TRUE;
    
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    OPEN retention_cursor;
    
    retention_loop: LOOP
        FETCH retention_cursor INTO v_category, v_retention_days, v_delete_after_days;
        IF done THEN
            LEAVE retention_loop;
        END IF;
        
        -- Archive old records
        UPDATE sa_audit_log 
        SET is_archived = TRUE, archive_date = CURDATE()
        WHERE event_category = v_category 
        AND event_timestamp < DATE_SUB(NOW(), INTERVAL v_retention_days DAY)
        AND is_archived = FALSE;
        
        -- Delete very old records if specified
        IF v_delete_after_days IS NOT NULL THEN
            DELETE FROM sa_audit_log 
            WHERE event_category = v_category 
            AND event_timestamp < DATE_SUB(NOW(), INTERVAL v_delete_after_days DAY);
        END IF;
        
    END LOOP;
    
    CLOSE retention_cursor;
END //

CREATE PROCEDURE sa_generate_audit_summary(IN summary_date DATE)
BEGIN
    INSERT INTO sa_audit_summary (
        summary_date, summary_hour, event_category, event_type,
        total_events, success_events, failed_events, warning_events, error_events,
        unique_users, unique_hpcsa_numbers, unique_sessions, unique_source_ips,
        unique_patients, unique_studies, dicom_instances_accessed,
        avg_processing_time_ms, max_processing_time_ms,
        popia_compliant_events, hpcsa_compliant_events, consent_verified_events
    )
    SELECT 
        DATE(event_timestamp) as summary_date,
        HOUR(event_timestamp) as summary_hour,
        event_category,
        event_type,
        COUNT(*) as total_events,
        SUM(CASE WHEN action_result = 'SUCCESS' THEN 1 ELSE 0 END) as success_events,
        SUM(CASE WHEN action_result = 'FAILED' THEN 1 ELSE 0 END) as failed_events,
        SUM(CASE WHEN event_severity = 'WARNING' THEN 1 ELSE 0 END) as warning_events,
        SUM(CASE WHEN event_severity IN ('ERROR', 'CRITICAL') THEN 1 ELSE 0 END) as error_events,
        COUNT(DISTINCT user_id) as unique_users,
        COUNT(DISTINCT hpcsa_number) as unique_hpcsa_numbers,
        COUNT(DISTINCT session_token) as unique_sessions,
        COUNT(DISTINCT source_ip) as unique_source_ips,
        COUNT(DISTINCT patient_id) as unique_patients,
        COUNT(DISTINCT study_instance_uid) as unique_studies,
        SUM(CASE WHEN resource_type = 'INSTANCE' THEN 1 ELSE 0 END) as dicom_instances_accessed,
        AVG(processing_time_ms) as avg_processing_time_ms,
        MAX(processing_time_ms) as max_processing_time_ms,
        SUM(CASE WHEN data_processing_purpose IS NOT NULL THEN 1 ELSE 0 END) as popia_compliant_events,
        SUM(CASE WHEN hpcsa_number IS NOT NULL AND clinical_justification IS NOT NULL THEN 1 ELSE 0 END) as hpcsa_compliant_events,
        SUM(CASE WHEN data_subject_consent = TRUE THEN 1 ELSE 0 END) as consent_verified_events
    FROM sa_audit_log
    WHERE DATE(event_timestamp) = summary_date
    GROUP BY DATE(event_timestamp), HOUR(event_timestamp), event_category, event_type
    ON DUPLICATE KEY UPDATE
        total_events = VALUES(total_events),
        success_events = VALUES(success_events),
        failed_events = VALUES(failed_events),
        warning_events = VALUES(warning_events),
        error_events = VALUES(error_events),
        unique_users = VALUES(unique_users),
        unique_hpcsa_numbers = VALUES(unique_hpcsa_numbers),
        unique_sessions = VALUES(unique_sessions),
        unique_source_ips = VALUES(unique_source_ips),
        unique_patients = VALUES(unique_patients),
        unique_studies = VALUES(unique_studies),
        dicom_instances_accessed = VALUES(dicom_instances_accessed),
        avg_processing_time_ms = VALUES(avg_processing_time_ms),
        max_processing_time_ms = VALUES(max_processing_time_ms),
        popia_compliant_events = VALUES(popia_compliant_events),
        hpcsa_compliant_events = VALUES(hpcsa_compliant_events),
        consent_verified_events = VALUES(consent_verified_events),
        updated_at = CURRENT_TIMESTAMP;
END //

DELIMITER ;

-- Triggers for automatic audit logging
DELIMITER //

CREATE TRIGGER sa_audit_log_insert_trigger
    AFTER INSERT ON sa_audit_log
    FOR EACH ROW
BEGIN
    -- Update summary statistics in real-time for critical events
    IF NEW.event_severity IN ('ERROR', 'CRITICAL') THEN
        INSERT INTO sa_audit_summary (
            summary_date, summary_hour, event_category, event_type,
            total_events, error_events
        ) VALUES (
            DATE(NEW.event_timestamp), HOUR(NEW.event_timestamp),
            NEW.event_category, NEW.event_type, 1, 1
        ) ON DUPLICATE KEY UPDATE
            total_events = total_events + 1,
            error_events = error_events + 1,
            updated_at = CURRENT_TIMESTAMP;
    END IF;
END //

DELIMITER ;