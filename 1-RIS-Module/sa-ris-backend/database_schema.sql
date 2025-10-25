-- =============================================
-- South African RIS - Complete Database Schema
-- Optimized for high-performance radiology workflows
-- Includes SA-specific billing and compliance features
-- =============================================

-- Create database with optimal settings
CREATE DATABASE IF NOT EXISTS sa_ris_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE sa_ris_db;

-- =============================================
-- Core Workflow Tables
-- =============================================

-- Workflow instances tracking
CREATE TABLE ris_workflow_instances (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    booking_id BIGINT NOT NULL,
    patient_id BIGINT NOT NULL,
    examination_type VARCHAR(50) NOT NULL,
    urgency ENUM('routine', 'urgent', 'stat') DEFAULT 'routine',
    current_state VARCHAR(50) NOT NULL DEFAULT 'BOOKED',
    previous_state VARCHAR(50),
    estimated_completion DATETIME,
    actual_completion DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    assigned_radiologist_id BIGINT,
    assigned_technologist_id BIGINT,
    study_instance_uid VARCHAR(255),
    progress_percentage TINYINT DEFAULT 0,
    patient_satisfaction_score TINYINT,
    notes TEXT,
    
    INDEX idx_patient_id (patient_id),
    INDEX idx_current_state (current_state),
    INDEX idx_urgency (urgency),
    INDEX idx_examination_type (examination_type),
    INDEX idx_created_at (created_at),
    INDEX idx_estimated_completion (estimated_completion),
    INDEX idx_composite_search (current_state, urgency, examination_type)
) ENGINE=InnoDB;

-- Workflow state transitions log
CREATE TABLE ris_workflow_state_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    workflow_id BIGINT NOT NULL,
    from_state VARCHAR(50),
    to_state VARCHAR(50) NOT NULL,
    transition_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    triggered_by VARCHAR(100),
    trigger_type ENUM('manual', 'automatic', 'scheduled') DEFAULT 'manual',
    notes TEXT,
    
    FOREIGN KEY (workflow_id) REFERENCES ris_workflow_instances(id) ON DELETE CASCADE,
    INDEX idx_workflow_id (workflow_id),
    INDEX idx_transition_time (transition_time)
) ENGINE=InnoDB;

-- =============================================
-- SA-Specific Billing Tables
-- =============================================

-- Medical Aid Schemes configuration
CREATE TABLE sa_medical_aid_schemes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    scheme_code VARCHAR(10) UNIQUE NOT NULL,
    scheme_name VARCHAR(100) NOT NULL,
    billing_format ENUM('XML', 'EDI', 'PDF') NOT NULL,
    api_endpoint VARCHAR(255),
    authorization_required BOOLEAN DEFAULT FALSE,
    real_time_verification BOOLEAN DEFAULT FALSE,
    tariff_structure VARCHAR(50) DEFAULT 'NRPL_2024',
    claim_submission_method ENUM('electronic', 'manual') DEFAULT 'electronic',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_scheme_code (scheme_code),
    INDEX idx_active (active)
) ENGINE=InnoDB;

-- NRPL (National Reference Price List) codes
CREATE TABLE sa_nrpl_codes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nrpl_code VARCHAR(10) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50),
    modality VARCHAR(20),
    body_part VARCHAR(100),
    contrast_type ENUM('none', 'oral', 'iv', 'both'),
    base_price DECIMAL(10,2) NOT NULL,
    effective_date DATE NOT NULL,
    expiry_date DATE,
    active BOOLEAN DEFAULT TRUE,
    
    INDEX idx_nrpl_code (nrpl_code),
    INDEX idx_modality (modality),
    INDEX idx_category (category),
    INDEX idx_effective_date (effective_date),
    INDEX idx_active (active)
) ENGINE=InnoDB;

-- Medical aid scheme specific rates
CREATE TABLE sa_medical_aid_rates (
    id INT PRIMARY KEY AUTO_INCREMENT,
    scheme_id INT NOT NULL,
    nrpl_code_id INT NOT NULL,
    rate_percentage DECIMAL(5,2) NOT NULL,
    co_payment_percentage DECIMAL(5,2) DEFAULT 0,
    annual_limit DECIMAL(12,2),
    per_procedure_limit DECIMAL(10,2),
    pre_authorization_required BOOLEAN DEFAULT FALSE,
    effective_date DATE NOT NULL,
    expiry_date DATE,
    
    FOREIGN KEY (scheme_id) REFERENCES sa_medical_aid_schemes(id),
    FOREIGN KEY (nrpl_code_id) REFERENCES sa_nrpl_codes(id),
    UNIQUE KEY unique_scheme_nrpl_date (scheme_id, nrpl_code_id, effective_date),
    INDEX idx_scheme_id (scheme_id),
    INDEX idx_effective_date (effective_date)
) ENGINE=InnoDB;

-- Billing quotes and estimates
CREATE TABLE sa_billing_quotes (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    workflow_id BIGINT NOT NULL,
    patient_id BIGINT NOT NULL,
    medical_aid_scheme_id INT,
    member_number VARCHAR(50),
    quote_number VARCHAR(50) UNIQUE NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    medical_aid_portion DECIMAL(12,2) DEFAULT 0,
    patient_portion DECIMAL(12,2) NOT NULL,
    savings_account_used DECIMAL(10,2) DEFAULT 0,
    co_payment_amount DECIMAL(10,2) DEFAULT 0,
    authorization_code VARCHAR(100),
    quote_valid_until DATE,
    status ENUM('draft', 'sent', 'accepted', 'expired') DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (workflow_id) REFERENCES ris_workflow_instances(id),
    FOREIGN KEY (medical_aid_scheme_id) REFERENCES sa_medical_aid_schemes(id),
    INDEX idx_workflow_id (workflow_id),
    INDEX idx_patient_id (patient_id),
    INDEX idx_quote_number (quote_number),
    INDEX idx_status (status)
) ENGINE=InnoDB;

-- Claims submitted to medical aids
CREATE TABLE sa_claims_submitted (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    workflow_id BIGINT NOT NULL,
    quote_id BIGINT,
    claim_number VARCHAR(50) UNIQUE NOT NULL,
    medical_aid_scheme_id INT NOT NULL,
    member_number VARCHAR(50) NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    claim_document LONGTEXT,
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledgment_number VARCHAR(100),
    status ENUM('submitted', 'acknowledged', 'paid', 'rejected', 'queried') DEFAULT 'submitted',
    payment_date DATE,
    payment_amount DECIMAL(12,2),
    rejection_reason TEXT,
    last_status_check TIMESTAMP,
    
    FOREIGN KEY (workflow_id) REFERENCES ris_workflow_instances(id),
    FOREIGN KEY (quote_id) REFERENCES sa_billing_quotes(id),
    FOREIGN KEY (medical_aid_scheme_id) REFERENCES sa_medical_aid_schemes(id),
    INDEX idx_claim_number (claim_number),
    INDEX idx_submission_date (submission_date),
    INDEX idx_status (status),
    INDEX idx_payment_date (payment_date)
) ENGINE=InnoDB;

-- =============================================
-- DICOM and Image Management Tables
-- =============================================

-- DICOM studies tracking
CREATE TABLE dicom_studies (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    workflow_id BIGINT,
    study_instance_uid VARCHAR(255) UNIQUE NOT NULL,
    patient_id VARCHAR(100),
    patient_name VARCHAR(255),
    patient_birth_date DATE,
    study_date DATE,
    study_time TIME,
    accession_number VARCHAR(100),
    modality VARCHAR(10),
    study_description TEXT,
    referring_physician VARCHAR(255),
    images_count INT DEFAULT 0,
    series_count INT DEFAULT 0,
    study_size_mb DECIMAL(10,2),
    storage_location VARCHAR(255),
    storage_tier ENUM('online', 'nearline', 'offline') DEFAULT 'online',
    quality_score TINYINT,
    quality_issues TEXT,
    processing_status ENUM('received', 'processing', 'complete', 'error') DEFAULT 'received',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (workflow_id) REFERENCES ris_workflow_instances(id),
    INDEX idx_study_instance_uid (study_instance_uid),
    INDEX idx_patient_id (patient_id),
    INDEX idx_study_date (study_date),
    INDEX idx_modality (modality),
    INDEX idx_storage_tier (storage_tier),
    INDEX idx_processing_status (processing_status),
    INDEX idx_last_accessed (last_accessed)
) ENGINE=InnoDB;

-- DICOM series within studies
CREATE TABLE dicom_series (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    study_id BIGINT NOT NULL,
    series_instance_uid VARCHAR(255) UNIQUE NOT NULL,
    series_number INT,
    series_description TEXT,
    modality VARCHAR(10),
    body_part VARCHAR(100),
    series_date DATE,
    series_time TIME,
    images_count INT DEFAULT 0,
    slice_thickness DECIMAL(6,3),
    pixel_spacing VARCHAR(50),
    contrast_agent VARCHAR(100),
    acquisition_parameters JSON,
    quality_metrics JSON,
    
    FOREIGN KEY (study_id) REFERENCES dicom_studies(id) ON DELETE CASCADE,
    INDEX idx_series_instance_uid (series_instance_uid),
    INDEX idx_study_id (study_id),
    INDEX idx_modality (modality),
    INDEX idx_body_part (body_part)
) ENGINE=InnoDB;

-- Image quality assessment results
CREATE TABLE image_quality_assessments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    study_id BIGINT NOT NULL,
    series_id BIGINT,
    overall_quality_score TINYINT NOT NULL,
    noise_level DECIMAL(6,3),
    contrast_score TINYINT,
    sharpness_score TINYINT,
    artifact_detection JSON,
    motion_artifacts BOOLEAN DEFAULT FALSE,
    positioning_score TINYINT,
    protocol_compliance BOOLEAN DEFAULT TRUE,
    requires_repeat BOOLEAN DEFAULT FALSE,
    assessment_algorithm VARCHAR(50),
    assessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_by VARCHAR(100),
    
    FOREIGN KEY (study_id) REFERENCES dicom_studies(id) ON DELETE CASCADE,
    FOREIGN KEY (series_id) REFERENCES dicom_series(id) ON DELETE CASCADE,
    INDEX idx_study_id (study_id),
    INDEX idx_overall_quality_score (overall_quality_score),
    INDEX idx_requires_repeat (requires_repeat),
    INDEX idx_assessed_at (assessed_at)
) ENGINE=InnoDB;

-- =============================================
-- Reporting and AI Tables
-- =============================================

-- Radiology reports
CREATE TABLE radiology_reports (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    workflow_id BIGINT NOT NULL,
    study_id BIGINT NOT NULL,
    report_type ENUM('preliminary', 'final', 'amended', 'addendum') DEFAULT 'preliminary',
    template_id INT,
    clinical_indication TEXT,
    technique TEXT,
    findings TEXT NOT NULL,
    impression TEXT NOT NULL,
    recommendations TEXT,
    critical_findings TEXT,
    follow_up_required BOOLEAN DEFAULT FALSE,
    follow_up_timeframe VARCHAR(50),
    ai_assisted BOOLEAN DEFAULT FALSE,
    ai_confidence_score DECIMAL(3,2),
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_by VARCHAR(100),
    approved_at TIMESTAMP,
    delivered_at TIMESTAMP,
    status ENUM('draft', 'pending_approval', 'approved', 'delivered', 'amended') DEFAULT 'draft',
    
    FOREIGN KEY (workflow_id) REFERENCES ris_workflow_instances(id),
    FOREIGN KEY (study_id) REFERENCES dicom_studies(id),
    INDEX idx_workflow_id (workflow_id),
    INDEX idx_study_id (study_id),
    INDEX idx_report_type (report_type),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_critical_findings (critical_findings(255))
) ENGINE=InnoDB;

-- AI analysis results
CREATE TABLE ai_analysis_results (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    study_id BIGINT NOT NULL,
    series_id BIGINT,
    ai_model_name VARCHAR(100) NOT NULL,
    ai_model_version VARCHAR(20) NOT NULL,
    analysis_type ENUM('detection', 'classification', 'segmentation', 'measurement') NOT NULL,
    findings JSON NOT NULL,
    confidence_scores JSON,
    processing_time_seconds DECIMAL(6,2),
    critical_findings_detected BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_by VARCHAR(100),
    review_status ENUM('pending', 'confirmed', 'rejected', 'modified') DEFAULT 'pending',
    
    FOREIGN KEY (study_id) REFERENCES dicom_studies(id) ON DELETE CASCADE,
    FOREIGN KEY (series_id) REFERENCES dicom_series(id) ON DELETE CASCADE,
    INDEX idx_study_id (study_id),
    INDEX idx_ai_model (ai_model_name, ai_model_version),
    INDEX idx_analysis_type (analysis_type),
    INDEX idx_critical_findings_detected (critical_findings_detected),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB;

-- =============================================
-- User and Equipment Management
-- =============================================

-- Radiologists and their specialties
CREATE TABLE radiologists (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    practice_number VARCHAR(20),
    subspecialties JSON,
    current_workload INT DEFAULT 0,
    max_workload INT DEFAULT 10,
    shift_start TIME,
    shift_end TIME,
    availability_status ENUM('available', 'busy', 'offline') DEFAULT 'available',
    average_report_time_minutes INT,
    quality_score DECIMAL(3,2),
    active BOOLEAN DEFAULT TRUE,
    
    INDEX idx_user_id (user_id),
    INDEX idx_availability_status (availability_status),
    INDEX idx_current_workload (current_workload),
    INDEX idx_active (active)
) ENGINE=InnoDB;

-- Equipment and workstations
CREATE TABLE equipment (
    id INT PRIMARY KEY AUTO_INCREMENT,
    equipment_code VARCHAR(20) UNIQUE NOT NULL,
    equipment_name VARCHAR(100) NOT NULL,
    equipment_type ENUM('scanner', 'workstation', 'printer') NOT NULL,
    modality VARCHAR(20),
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    serial_number VARCHAR(100),
    location VARCHAR(100),
    status ENUM('operational', 'maintenance', 'offline', 'error') DEFAULT 'operational',
    utilization_percentage TINYINT DEFAULT 0,
    last_service_date DATE,
    next_service_due DATE,
    service_contract VARCHAR(100),
    capabilities JSON,
    performance_metrics JSON,
    
    INDEX idx_equipment_code (equipment_code),
    INDEX idx_equipment_type (equipment_type),
    INDEX idx_modality (modality),
    INDEX idx_status (status),
    INDEX idx_next_service_due (next_service_due)
) ENGINE=InnoDB;

-- =============================================
-- POPI Act Compliance Tables
-- =============================================

-- Consent management
CREATE TABLE patient_consents (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    patient_id BIGINT NOT NULL,
    workflow_id BIGINT,
    consent_type ENUM('data_processing', 'data_sharing', 'research', 'teaching') NOT NULL,
    consent_given BOOLEAN NOT NULL,
    consent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    consent_expiry DATE,
    withdrawal_date TIMESTAMP NULL,
    consent_document_path VARCHAR(255),
    witnessed_by VARCHAR(100),
    notes TEXT,
    
    FOREIGN KEY (workflow_id) REFERENCES ris_workflow_instances(id),
    INDEX idx_patient_id (patient_id),
    INDEX idx_consent_type (consent_type),
    INDEX idx_consent_given (consent_given),
    INDEX idx_consent_date (consent_date)
) ENGINE=InnoDB;

-- Audit trail for POPI compliance
CREATE TABLE popi_audit_trail (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    patient_id BIGINT,
    user_id INT NOT NULL,
    action_type ENUM('access', 'modify', 'delete', 'export', 'share') NOT NULL,
    table_name VARCHAR(100),
    record_id BIGINT,
    old_values JSON,
    new_values JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    justification TEXT,
    
    INDEX idx_patient_id (patient_id),
    INDEX idx_user_id (user_id),
    INDEX idx_action_type (action_type),
    INDEX idx_action_timestamp (action_timestamp),
    INDEX idx_table_record (table_name, record_id)
) ENGINE=InnoDB;

-- =============================================
-- Analytics and Performance Tables
-- =============================================

-- Daily performance metrics
CREATE TABLE daily_performance_metrics (
    id INT PRIMARY KEY AUTO_INCREMENT,
    metric_date DATE NOT NULL,
    total_examinations INT DEFAULT 0,
    total_reports INT DEFAULT 0,
    total_revenue DECIMAL(12,2) DEFAULT 0,
    average_turnaround_time_minutes INT,
    patient_satisfaction_avg DECIMAL(3,2),
    equipment_utilization_avg DECIMAL(3,2),
    critical_findings_count INT DEFAULT 0,
    repeat_examinations_count INT DEFAULT 0,
    claims_submitted INT DEFAULT 0,
    claims_paid INT DEFAULT 0,
    
    UNIQUE KEY unique_date (metric_date),
    INDEX idx_metric_date (metric_date)
) ENGINE=InnoDB;

-- =============================================
-- Views for Common Queries
-- =============================================

-- Current workflow status view
CREATE VIEW v_current_workflow_status AS
SELECT 
    w.id as workflow_id,
    w.patient_id,
    w.examination_type,
    w.urgency,
    w.current_state,
    w.progress_percentage,
    w.estimated_completion,
    w.created_at,
    ds.patient_name,
    ds.study_instance_uid,
    r.first_name as radiologist_first_name,
    r.last_name as radiologist_last_name,
    mas.scheme_name as medical_aid_scheme,
    bq.total_amount as estimated_cost
FROM ris_workflow_instances w
LEFT JOIN dicom_studies ds ON w.id = ds.workflow_id
LEFT JOIN radiologists r ON w.assigned_radiologist_id = r.id
LEFT JOIN sa_billing_quotes bq ON w.id = bq.workflow_id AND bq.status = 'accepted'
LEFT JOIN sa_medical_aid_schemes mas ON bq.medical_aid_scheme_id = mas.id
WHERE w.current_state NOT IN ('DELIVERED', 'ARCHIVED')
ORDER BY 
    CASE w.urgency 
        WHEN 'stat' THEN 1 
        WHEN 'urgent' THEN 2 
        WHEN 'routine' THEN 3 
    END,
    w.estimated_completion ASC;

-- Financial summary view
CREATE VIEW v_financial_summary AS
SELECT 
    DATE(cs.submission_date) as submission_date,
    mas.scheme_name,
    COUNT(*) as claims_count,
    SUM(cs.total_amount) as total_claimed,
    SUM(CASE WHEN cs.status = 'paid' THEN cs.payment_amount ELSE 0 END) as total_paid,
    AVG(DATEDIFF(cs.payment_date, cs.submission_date)) as avg_payment_days
FROM sa_claims_submitted cs
JOIN sa_medical_aid_schemes mas ON cs.medical_aid_scheme_id = mas.id
WHERE cs.submission_date >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY)
GROUP BY DATE(cs.submission_date), mas.scheme_name
ORDER BY submission_date DESC, mas.scheme_name;

-- =============================================
-- Indexes for Performance Optimization
-- =============================================

-- Composite indexes for common query patterns
CREATE INDEX idx_workflow_patient_date ON ris_workflow_instances (patient_id, created_at);
CREATE INDEX idx_workflow_state_urgency_exam ON ris_workflow_instances (current_state, urgency, examination_type);
CREATE INDEX idx_claims_scheme_status_date ON sa_claims_submitted (medical_aid_scheme_id, status, submission_date);
CREATE INDEX idx_studies_patient_date ON dicom_studies (patient_id, study_date);
CREATE INDEX idx_reports_created_status ON radiology_reports (created_at, status);

-- =============================================
-- Sample Data for Testing
-- =============================================

-- Insert sample medical aid schemes
INSERT INTO sa_medical_aid_schemes (scheme_code, scheme_name, billing_format, authorization_required, real_time_verification) VALUES
('DHMS', 'Discovery Health Medical Scheme', 'XML', TRUE, TRUE),
('MOM', 'Momentum Health', 'EDI', TRUE, TRUE),
('BON', 'Bonitas Medical Fund', 'XML', FALSE, TRUE),
('GEMS', 'Government Employees Medical Scheme', 'PDF', TRUE, FALSE),
('BESTMED', 'Bestmed Medical Scheme', 'XML', FALSE, TRUE);

-- Insert sample NRPL codes
INSERT INTO sa_nrpl_codes (nrpl_code, description, category, modality, base_price) VALUES
('3011', 'CT Head without contrast', 'Diagnostic Imaging', 'CT', 1850.00),
('3012', 'CT Head with contrast', 'Diagnostic Imaging', 'CT', 2450.00),
('3021', 'MRI Brain without contrast', 'Diagnostic Imaging', 'MRI', 4500.00),
('3022', 'MRI Brain with contrast', 'Diagnostic Imaging', 'MRI', 5200.00),
('3001', 'Chest X-Ray PA', 'Diagnostic Imaging', 'XRAY', 320.00),
('3041', 'Abdominal Ultrasound', 'Diagnostic Imaging', 'US', 850.00),
('3051', 'Bilateral Mammography', 'Diagnostic Imaging', 'MG', 1200.00);

-- =============================================
-- Stored Procedures for Common Operations
-- =============================================

DELIMITER //

-- Procedure to advance workflow state
CREATE PROCEDURE sp_advance_workflow(
    IN p_workflow_id BIGINT,
    IN p_new_state VARCHAR(50),
    IN p_triggered_by VARCHAR(100)
)
BEGIN
    DECLARE v_current_state VARCHAR(50);
    
    -- Get current state
    SELECT current_state INTO v_current_state 
    FROM ris_workflow_instances 
    WHERE id = p_workflow_id;
    
    -- Update workflow state
    UPDATE ris_workflow_instances 
    SET 
        previous_state = v_current_state,
        current_state = p_new_state,
        last_updated = CURRENT_TIMESTAMP
    WHERE id = p_workflow_id;
    
    -- Log state transition
    INSERT INTO ris_workflow_state_log (workflow_id, from_state, to_state, triggered_by)
    VALUES (p_workflow_id, v_current_state, p_new_state, p_triggered_by);
    
END //

-- Procedure to calculate workflow performance metrics
CREATE PROCEDURE sp_calculate_daily_metrics(IN p_date DATE)
BEGIN
    INSERT INTO daily_performance_metrics (
        metric_date,
        total_examinations,
        total_reports,
        total_revenue,
        average_turnaround_time_minutes
    )
    SELECT 
        p_date,
        COUNT(DISTINCT w.id),
        COUNT(DISTINCT rr.id),
        COALESCE(SUM(bq.total_amount), 0),
        AVG(TIMESTAMPDIFF(MINUTE, w.created_at, w.actual_completion))
    FROM ris_workflow_instances w
    LEFT JOIN radiology_reports rr ON w.id = rr.workflow_id AND DATE(rr.created_at) = p_date
    LEFT JOIN sa_billing_quotes bq ON w.id = bq.workflow_id
    WHERE DATE(w.created_at) = p_date
    ON DUPLICATE KEY UPDATE
        total_examinations = VALUES(total_examinations),
        total_reports = VALUES(total_reports),
        total_revenue = VALUES(total_revenue),
        average_turnaround_time_minutes = VALUES(average_turnaround_time_minutes);
END //

DELIMITER ;

-- =============================================
-- Triggers for Audit Trail and Automation
-- =============================================

-- Trigger to automatically log patient data access
DELIMITER //

CREATE TRIGGER tr_patient_data_access 
AFTER SELECT ON ris_workflow_instances
FOR EACH ROW
BEGIN
    INSERT INTO popi_audit_trail (patient_id, user_id, action_type, table_name, record_id, action_timestamp)
    VALUES (NEW.patient_id, @current_user_id, 'access', 'ris_workflow_instances', NEW.id, CURRENT_TIMESTAMP);
END //

-- Trigger to update workflow progress when report is created
CREATE TRIGGER tr_update_workflow_progress
AFTER INSERT ON radiology_reports
FOR EACH ROW
BEGIN
    UPDATE ris_workflow_instances 
    SET progress_percentage = 90
    WHERE id = NEW.workflow_id AND progress_percentage < 90;
END //

DELIMITER ;
