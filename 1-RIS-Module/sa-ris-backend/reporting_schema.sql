-- ===============================================
-- SA Medical Reporting Module - Database Schema
-- Comprehensive schema for South African radiology reporting
-- ===============================================

-- Enable UUID extension for PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===============================================
-- Core Tables
-- ===============================================

-- Radiology Reports Table
CREATE TABLE radiology_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id VARCHAR(50) NOT NULL,
    study_instance_uid VARCHAR(255) NOT NULL,
    reporting_doctor_id VARCHAR(50) NOT NULL,
    
    -- Workflow state
    status VARCHAR(50) NOT NULL DEFAULT 'awaiting_dictation' 
        CHECK (status IN ('awaiting_dictation', 'dictation_in_progress', 'awaiting_transcription', 
                         'transcription_in_progress', 'awaiting_authorization', 'authorization_in_progress', 
                         'authorized', 'delivered', 'amended')),
    priority VARCHAR(20) NOT NULL DEFAULT 'routine' 
        CHECK (priority IN ('stat', 'urgent', 'routine')),
    
    -- Report content
    clinical_history TEXT,
    technique TEXT,
    findings TEXT,
    impression TEXT,
    recommendations TEXT,
    
    -- Dictation data
    original_audio_url VARCHAR(500),
    dictation_session_id UUID,
    dictation_timestamp TIMESTAMP WITH TIME ZONE,
    
    -- Transcription data
    transcription_completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Authorization data
    authorized_by VARCHAR(50),
    authorized_at TIMESTAMP WITH TIME ZONE,
    digital_signature TEXT,
    
    -- Billing data
    claim_number VARCHAR(100),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    version INTEGER DEFAULT 1,
    
    -- Indexes
    CONSTRAINT fk_patient_id FOREIGN KEY (patient_id) REFERENCES patients(pid) ON DELETE CASCADE,
    CONSTRAINT unique_study_report UNIQUE (study_instance_uid, reporting_doctor_id)
);

-- Audio Sessions Table
CREATE TABLE audio_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES radiology_reports(id) ON DELETE CASCADE,
    doctor_id VARCHAR(50) NOT NULL,
    
    -- Audio file information
    audio_file_url VARCHAR(500) NOT NULL,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    file_size_bytes BIGINT NOT NULL DEFAULT 0,
    format VARCHAR(10) NOT NULL DEFAULT 'wav' CHECK (format IN ('wav', 'mp3', 'ogg')),
    sample_rate INTEGER NOT NULL DEFAULT 44100,
    channels INTEGER NOT NULL DEFAULT 1,
    
    -- STT Results
    transcription_text TEXT,
    confidence_score DECIMAL(3,2) DEFAULT 0.0 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    medical_terms_detected JSONB DEFAULT '[]',
    
    -- Security
    encrypted BOOLEAN DEFAULT TRUE,
    encryption_key VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '1 year')
);

-- Transcription Reviews Table
CREATE TABLE transcription_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES radiology_reports(id) ON DELETE CASCADE,
    transcriptionist_id VARCHAR(50) NOT NULL,
    
    -- Review data
    reviewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    quality_score INTEGER DEFAULT 0 CHECK (quality_score >= 0 AND quality_score <= 100),
    notes TEXT,
    time_spent_minutes INTEGER DEFAULT 0,
    
    -- Status
    status VARCHAR(20) DEFAULT 'in_progress' CHECK (status IN ('assigned', 'in_progress', 'completed', 'rejected')),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Text Changes Table (for tracking transcriptionist edits)
CREATE TABLE text_changes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transcription_review_id UUID NOT NULL REFERENCES transcription_reviews(id) ON DELETE CASCADE,
    
    -- Change details
    position_start INTEGER NOT NULL,
    position_end INTEGER NOT NULL,
    original_text TEXT NOT NULL,
    corrected_text TEXT NOT NULL,
    change_type VARCHAR(20) NOT NULL CHECK (change_type IN ('medical_term', 'grammar', 'punctuation', 'structure')),
    confidence_improvement DECIMAL(3,2) DEFAULT 0.0,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Report Workflow States Table
CREATE TABLE report_workflow_states (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES radiology_reports(id) ON DELETE CASCADE,
    
    -- State information
    current_state VARCHAR(50) NOT NULL,
    previous_state VARCHAR(50),
    
    -- Assigned users
    assigned_doctor_id VARCHAR(50),
    assigned_transcriptionist_id VARCHAR(50),
    
    -- Timing metrics
    dictation_started_at TIMESTAMP WITH TIME ZONE,
    dictation_completed_at TIMESTAMP WITH TIME ZONE,
    transcription_started_at TIMESTAMP WITH TIME ZONE,
    transcription_completed_at TIMESTAMP WITH TIME ZONE,
    authorization_started_at TIMESTAMP WITH TIME ZONE,
    authorization_completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Performance metrics
    total_processing_time_minutes INTEGER,
    dictation_duration_minutes INTEGER,
    transcription_duration_minutes INTEGER,
    authorization_duration_minutes INTEGER,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- State Transitions Table (for audit trail)
CREATE TABLE state_transitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES radiology_reports(id) ON DELETE CASCADE,
    
    -- Transition details
    from_state VARCHAR(50) NOT NULL,
    to_state VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    reason TEXT,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Billing Codes Table
CREATE TABLE report_billing_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES radiology_reports(id) ON DELETE CASCADE,
    
    -- Billing information
    nrpl_code VARCHAR(20) NOT NULL,
    description TEXT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    medical_aid_scheme VARCHAR(50),
    authorization_code VARCHAR(100),
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'submitted', 'paid', 'rejected')),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Medical Terms Dictionary Table
CREATE TABLE medical_terms_dictionary (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    term VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(100) NOT NULL,
    language VARCHAR(10) DEFAULT 'en' CHECK (language IN ('en', 'af')),
    pronunciation VARCHAR(500),
    definition TEXT,
    synonyms JSONB DEFAULT '[]',
    
    -- Usage statistics
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User Preferences Table
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(50) NOT NULL UNIQUE,
    
    -- Dictation preferences
    preferred_language VARCHAR(10) DEFAULT 'en',
    audio_quality VARCHAR(20) DEFAULT 'high' CHECK (audio_quality IN ('low', 'medium', 'high')),
    auto_punctuation BOOLEAN DEFAULT TRUE,
    
    -- UI preferences
    layout_config JSONB DEFAULT '{}',
    theme VARCHAR(20) DEFAULT 'light' CHECK (theme IN ('light', 'dark', 'high_contrast')),
    
    -- Notification preferences
    email_notifications BOOLEAN DEFAULT TRUE,
    sms_notifications BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ===============================================
-- Indexes for Performance Optimization
-- ===============================================

-- Primary workflow indexes
CREATE INDEX idx_reports_status ON radiology_reports(status);
CREATE INDEX idx_reports_priority ON radiology_reports(priority);
CREATE INDEX idx_reports_patient_id ON radiology_reports(patient_id);
CREATE INDEX idx_reports_doctor_id ON radiology_reports(reporting_doctor_id);
CREATE INDEX idx_reports_created_at ON radiology_reports(created_at);
CREATE INDEX idx_reports_study_uid ON radiology_reports(study_instance_uid);

-- Audio session indexes
CREATE INDEX idx_audio_sessions_report_id ON audio_sessions(report_id);
CREATE INDEX idx_audio_sessions_doctor_id ON audio_sessions(doctor_id);
CREATE INDEX idx_audio_sessions_created_at ON audio_sessions(created_at);

-- Transcription review indexes
CREATE INDEX idx_transcription_reviews_report_id ON transcription_reviews(report_id);
CREATE INDEX idx_transcription_reviews_transcriptionist_id ON transcription_reviews(transcriptionist_id);
CREATE INDEX idx_transcription_reviews_status ON transcription_reviews(status);

-- Workflow state indexes
CREATE INDEX idx_workflow_states_report_id ON report_workflow_states(report_id);
CREATE INDEX idx_workflow_states_current_state ON report_workflow_states(current_state);
CREATE INDEX idx_workflow_states_assigned_doctor ON report_workflow_states(assigned_doctor_id);
CREATE INDEX idx_workflow_states_assigned_transcriptionist ON report_workflow_states(assigned_transcriptionist_id);

-- State transition indexes (for audit queries)
CREATE INDEX idx_state_transitions_report_id ON state_transitions(report_id);
CREATE INDEX idx_state_transitions_user_id ON state_transitions(user_id);
CREATE INDEX idx_state_transitions_created_at ON state_transitions(created_at);

-- Billing indexes
CREATE INDEX idx_billing_codes_report_id ON report_billing_codes(report_id);
CREATE INDEX idx_billing_codes_status ON report_billing_codes(status);
CREATE INDEX idx_billing_codes_medical_aid ON report_billing_codes(medical_aid_scheme);

-- Medical terms indexes
CREATE INDEX idx_medical_terms_term ON medical_terms_dictionary(term);
CREATE INDEX idx_medical_terms_category ON medical_terms_dictionary(category);
CREATE INDEX idx_medical_terms_language ON medical_terms_dictionary(language);
CREATE INDEX idx_medical_terms_usage_count ON medical_terms_dictionary(usage_count DESC);

-- ===============================================
-- Triggers for Automatic Updates
-- ===============================================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers
CREATE TRIGGER update_radiology_reports_updated_at BEFORE UPDATE ON radiology_reports FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_transcription_reviews_updated_at BEFORE UPDATE ON transcription_reviews FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_report_workflow_states_updated_at BEFORE UPDATE ON report_workflow_states FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON user_preferences FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Version increment trigger for reports
CREATE OR REPLACE FUNCTION increment_report_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER increment_radiology_reports_version BEFORE UPDATE ON radiology_reports FOR EACH ROW EXECUTE FUNCTION increment_report_version();

-- ===============================================
-- Views for Common Queries
-- ===============================================

-- Active Reports View
CREATE VIEW active_reports AS
SELECT 
    r.id,
    r.patient_id,
    r.study_instance_uid,
    r.reporting_doctor_id,
    r.status,
    r.priority,
    r.created_at,
    ws.assigned_transcriptionist_id,
    ws.dictation_started_at,
    ws.transcription_started_at,
    CASE 
        WHEN r.status = 'stat' THEN 1
        WHEN r.status = 'urgent' THEN 2
        ELSE 3
    END as priority_order
FROM radiology_reports r
LEFT JOIN report_workflow_states ws ON r.id = ws.report_id
WHERE r.status NOT IN ('delivered', 'archived')
ORDER BY priority_order, r.created_at;

-- Transcriptionist Queue View
CREATE VIEW transcriptionist_queue AS
SELECT 
    r.id as report_id,
    r.patient_id,
    r.study_instance_uid,
    r.priority,
    r.created_at,
    a.audio_file_url,
    a.duration_seconds,
    a.transcription_text,
    a.confidence_score,
    CASE 
        WHEN r.priority = 'stat' THEN 1
        WHEN r.priority = 'urgent' THEN 2
        ELSE 3
    END as priority_order
FROM radiology_reports r
JOIN audio_sessions a ON r.id = a.report_id
WHERE r.status = 'awaiting_transcription'
ORDER BY priority_order, r.created_at;

-- Doctor Authorization Queue View
CREATE VIEW doctor_authorization_queue AS
SELECT 
    r.id as report_id,
    r.patient_id,
    r.study_instance_uid,
    r.reporting_doctor_id,
    r.priority,
    r.created_at,
    tr.transcriptionist_id,
    tr.reviewed_at,
    tr.quality_score,
    COUNT(tc.id) as total_changes
FROM radiology_reports r
JOIN transcription_reviews tr ON r.id = tr.report_id
LEFT JOIN text_changes tc ON tr.id = tc.transcription_review_id
WHERE r.status = 'awaiting_authorization'
GROUP BY r.id, r.patient_id, r.study_instance_uid, r.reporting_doctor_id, 
         r.priority, r.created_at, tr.transcriptionist_id, tr.reviewed_at, tr.quality_score
ORDER BY r.priority, r.created_at;

-- ===============================================
-- Initial Data Population
-- ===============================================

-- Insert common medical terms for South African radiology
INSERT INTO medical_terms_dictionary (term, category, language, definition) VALUES
-- English terms
('pneumothorax', 'chest', 'en', 'Presence of air in the pleural cavity'),
('consolidation', 'chest', 'en', 'Lung tissue filled with liquid instead of air'),
('atelectasis', 'chest', 'en', 'Collapse or closure of a lung'),
('cardiomegaly', 'chest', 'en', 'Enlargement of the heart'),
('pleural effusion', 'chest', 'en', 'Excess fluid in the pleural cavity'),
('pneumonia', 'chest', 'en', 'Infection that inflames air sacs in lungs'),
('fracture', 'musculoskeletal', 'en', 'Break in bone continuity'),
('dislocation', 'musculoskeletal', 'en', 'Displacement of bone from joint'),
('hemorrhage', 'general', 'en', 'Bleeding or escape of blood from vessels'),
('ischemia', 'general', 'en', 'Inadequate blood supply to tissue'),

-- Afrikaans terms
('longontsteking', 'chest', 'af', 'Infeksie wat lugsakke in longe ontstek'),
('breuk', 'musculoskeletal', 'af', 'Breek in been kontinuiteit'),
('bloeding', 'general', 'af', 'Bloeding of ontsnapping van bloed uit vate'),
('hartvergroting', 'chest', 'af', 'Vergroting van die hart');

-- Insert default user preferences for common roles
INSERT INTO user_preferences (user_id, preferred_language, layout_config) VALUES
('radiologist_default', 'en', '{"panels": 2, "layout": "side_by_side"}'),
('transcriptionist_default', 'en', '{"audio_controls": "bottom", "text_size": "medium"}');

-- ===============================================
-- Functions for Common Operations
-- ===============================================

-- Function to get next report for transcriptionist
CREATE OR REPLACE FUNCTION get_next_transcription_report(transcriptionist_id VARCHAR(50))
RETURNS TABLE(
    report_id UUID,
    patient_id VARCHAR(50),
    study_instance_uid VARCHAR(255),
    priority VARCHAR(20),
    audio_file_url VARCHAR(500),
    transcription_text TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tq.report_id,
        tq.patient_id,
        tq.study_instance_uid,
        tq.priority,
        tq.audio_file_url,
        tq.transcription_text
    FROM transcriptionist_queue tq
    WHERE NOT EXISTS (
        SELECT 1 FROM transcription_reviews tr 
        WHERE tr.report_id = tq.report_id 
        AND tr.status IN ('assigned', 'in_progress')
    )
    ORDER BY tq.priority_order, tq.created_at
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate workflow metrics
CREATE OR REPLACE FUNCTION calculate_workflow_metrics(start_date DATE, end_date DATE)
RETURNS TABLE(
    total_reports INTEGER,
    avg_dictation_time_minutes NUMERIC,
    avg_transcription_time_minutes NUMERIC,
    avg_authorization_time_minutes NUMERIC,
    avg_total_time_minutes NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER as total_reports,
        AVG(ws.dictation_duration_minutes) as avg_dictation_time_minutes,
        AVG(ws.transcription_duration_minutes) as avg_transcription_time_minutes,
        AVG(ws.authorization_duration_minutes) as avg_authorization_time_minutes,
        AVG(ws.total_processing_time_minutes) as avg_total_time_minutes
    FROM report_workflow_states ws
    JOIN radiology_reports r ON ws.report_id = r.id
    WHERE r.created_at::DATE BETWEEN start_date AND end_date
    AND r.status = 'delivered';
END;
$$ LANGUAGE plpgsql;

-- ===============================================
-- Security and Audit
-- ===============================================

-- Enable Row Level Security on sensitive tables
ALTER TABLE radiology_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE audio_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcription_reviews ENABLE ROW LEVEL SECURITY;

-- Create audit log table
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    user_id VARCHAR(50) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_log_table_name ON audit_log(table_name);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

-- ===============================================
-- Comments for Documentation
-- ===============================================

COMMENT ON TABLE radiology_reports IS 'Main table storing radiology reports with workflow status';
COMMENT ON TABLE audio_sessions IS 'Stores audio recordings and STT results for dictated reports';
COMMENT ON TABLE transcription_reviews IS 'Tracks transcriptionist reviews and corrections';
COMMENT ON TABLE text_changes IS 'Detailed log of all text changes made during transcription';
COMMENT ON TABLE report_workflow_states IS 'Tracks workflow state and timing metrics';
COMMENT ON TABLE state_transitions IS 'Audit trail of all workflow state changes';
COMMENT ON TABLE report_billing_codes IS 'Billing codes and medical aid information for reports';
COMMENT ON TABLE medical_terms_dictionary IS 'Dictionary of medical terms for STT accuracy';
COMMENT ON TABLE user_preferences IS 'User-specific preferences and settings';
COMMENT ON TABLE audit_log IS 'Comprehensive audit trail for POPI Act compliance';

-- Schema version for migration tracking
CREATE TABLE schema_version (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    description TEXT
);

INSERT INTO schema_version (version, description) VALUES 
('1.0.0', 'Initial SA Medical Reporting Module schema');