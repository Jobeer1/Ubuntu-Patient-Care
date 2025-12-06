-- GOTG Dictation-3 Database Schema
-- Integrates seamlessly with RIS-1 database
-- All tables include sync_status for offline-first operation

-- ============================================================================
-- DICTATIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS dictations (
    dictation_id TEXT PRIMARY KEY,
    study_id TEXT,
    user_id TEXT NOT NULL,
    clinic_id TEXT NOT NULL,
    
    -- Content
    transcription TEXT NOT NULL,
    transcription_language TEXT DEFAULT 'en',
    transcription_confidence REAL DEFAULT 0.0,
    audio_duration_seconds REAL,
    
    -- Status
    status TEXT DEFAULT 'completed',  -- completed, archived, deleted
    sync_status TEXT DEFAULT 'pending',  -- pending, synced, conflict, failed
    
    -- Metadata
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    uploaded_at TEXT,
    synced_at TEXT,
    
    -- Relations
    FOREIGN KEY (clinic_id) REFERENCES clinics(clinic_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (study_id) REFERENCES studies(study_id)
);

CREATE INDEX IF NOT EXISTS idx_dictations_user_id ON dictations(user_id);
CREATE INDEX IF NOT EXISTS idx_dictations_clinic_id ON dictations(clinic_id);
CREATE INDEX IF NOT EXISTS idx_dictations_study_id ON dictations(study_id);
CREATE INDEX IF NOT EXISTS idx_dictations_created_at ON dictations(created_at);
CREATE INDEX IF NOT EXISTS idx_dictations_sync_status ON dictations(sync_status);

-- ============================================================================
-- ASSESSMENTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS assessments (
    assessment_id TEXT PRIMARY KEY,
    dictation_id TEXT NOT NULL,
    study_id TEXT,
    user_id TEXT NOT NULL,
    clinic_id TEXT NOT NULL,
    
    -- Assessment data (JSON)
    assessment_data TEXT NOT NULL,  -- JSON: injuries, severity, observations, etc.
    
    -- Primary injury
    primary_injury_type TEXT,
    primary_injury_category TEXT,
    overall_severity TEXT,  -- critical, severe, moderate, minor, none
    severity_score REAL DEFAULT 0.0,
    
    -- Status
    status TEXT DEFAULT 'completed',  -- completed, archived, deleted
    sync_status TEXT DEFAULT 'pending',
    
    -- Metadata
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    synced_at TEXT,
    
    -- Relations
    FOREIGN KEY (dictation_id) REFERENCES dictations(dictation_id),
    FOREIGN KEY (clinic_id) REFERENCES clinics(clinic_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (study_id) REFERENCES studies(study_id)
);

CREATE INDEX IF NOT EXISTS idx_assessments_dictation_id ON assessments(dictation_id);
CREATE INDEX IF NOT EXISTS idx_assessments_study_id ON assessments(study_id);
CREATE INDEX IF NOT EXISTS idx_assessments_user_id ON assessments(user_id);
CREATE INDEX IF NOT EXISTS idx_assessments_severity ON assessments(overall_severity);
CREATE INDEX IF NOT EXISTS idx_assessments_sync_status ON assessments(sync_status);

-- ============================================================================
-- INJURY CLASSIFICATIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS injury_classifications (
    injury_id TEXT PRIMARY KEY,
    assessment_id TEXT NOT NULL,
    dictation_id TEXT NOT NULL,
    
    -- Classification
    injury_type TEXT NOT NULL,
    injury_category TEXT NOT NULL,
    icd10_code TEXT,
    
    -- Severity & Confidence
    severity_level TEXT,  -- critical, severe, moderate, minor
    confidence_score REAL,
    mention_count INTEGER DEFAULT 1,
    
    -- Metadata
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Relations
    FOREIGN KEY (assessment_id) REFERENCES assessments(assessment_id),
    FOREIGN KEY (dictation_id) REFERENCES dictations(dictation_id)
);

CREATE INDEX IF NOT EXISTS idx_injury_class_assessment_id ON injury_classifications(assessment_id);
CREATE INDEX IF NOT EXISTS idx_injury_class_icd10 ON injury_classifications(icd10_code);
CREATE INDEX IF NOT EXISTS idx_injury_class_severity ON injury_classifications(severity_level);

-- ============================================================================
-- TRANSCRIPTION HISTORY TABLE (for edits)
-- ============================================================================

CREATE TABLE IF NOT EXISTS transcription_history (
    history_id TEXT PRIMARY KEY,
    dictation_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    
    -- Content
    original_text TEXT NOT NULL,
    corrected_text TEXT NOT NULL,
    
    -- Change tracking
    change_description TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Relations
    FOREIGN KEY (dictation_id) REFERENCES dictations(dictation_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_transcription_history_dictation_id ON transcription_history(dictation_id);

-- ============================================================================
-- VITAL SIGNS EXTRACTION TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS vital_signs_extracted (
    vital_id TEXT PRIMARY KEY,
    dictation_id TEXT NOT NULL,
    assessment_id TEXT,
    
    -- Vitals
    heart_rate INTEGER,
    systolic_bp INTEGER,
    diastolic_bp INTEGER,
    respiratory_rate INTEGER,
    oxygen_saturation REAL,
    temperature REAL,
    
    -- Context
    mentioned_by_clinician TEXT DEFAULT 'yes',
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Relations
    FOREIGN KEY (dictation_id) REFERENCES dictations(dictation_id),
    FOREIGN KEY (assessment_id) REFERENCES assessments(assessment_id)
);

CREATE INDEX IF NOT EXISTS idx_vital_signs_dictation_id ON vital_signs_extracted(dictation_id);
CREATE INDEX IF NOT EXISTS idx_vital_signs_assessment_id ON vital_signs_extracted(assessment_id);

-- ============================================================================
-- CLINICAL OBSERVATIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS clinical_observations (
    observation_id TEXT PRIMARY KEY,
    dictation_id TEXT NOT NULL,
    assessment_id TEXT,
    
    -- Observation
    observation_type TEXT,  -- consciousness, appearance, behavior, etc.
    observation_value TEXT,
    
    -- Metadata
    recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Relations
    FOREIGN KEY (dictation_id) REFERENCES dictations(dictation_id),
    FOREIGN KEY (assessment_id) REFERENCES assessments(assessment_id)
);

CREATE INDEX IF NOT EXISTS idx_clinical_obs_dictation_id ON clinical_observations(dictation_id);

-- ============================================================================
-- SYNC QUEUE (shared with RIS-1)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sync_queue (
    sync_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,  -- dictation, assessment, injury_classification
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,  -- create, update, delete
    clinic_id TEXT NOT NULL,
    
    -- Sync tracking
    sync_status TEXT DEFAULT 'pending',  -- pending, synced, failed, conflict
    retry_count INTEGER DEFAULT 0,
    last_retry TEXT,
    error_message TEXT,
    
    -- Metadata
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    synced_at TEXT,
    
    FOREIGN KEY (clinic_id) REFERENCES clinics(clinic_id)
);

CREATE INDEX IF NOT EXISTS idx_sync_queue_entity ON sync_queue(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_sync_queue_status ON sync_queue(sync_status);
CREATE INDEX IF NOT EXISTS idx_sync_queue_clinic ON sync_queue(clinic_id);

-- ============================================================================
-- SYNC LOG (audit trail)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sync_log (
    log_id TEXT PRIMARY KEY,
    sync_id TEXT,
    entity_type TEXT,
    entity_id TEXT,
    action TEXT,
    clinic_id TEXT,
    
    -- Sync details
    local_version INTEGER,
    remote_version INTEGER,
    conflict_detected INTEGER DEFAULT 0,
    resolution_strategy TEXT,
    
    -- Metadata
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER,
    bytes_transferred INTEGER,
    status TEXT,  -- success, failure, conflict
    
    FOREIGN KEY (clinic_id) REFERENCES clinics(clinic_id)
);

CREATE INDEX IF NOT EXISTS idx_sync_log_timestamp ON sync_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_sync_log_entity ON sync_log(entity_type, entity_id);

-- ============================================================================
-- CACHE METADATA (for offline IndexedDB sync)
-- ============================================================================

CREATE TABLE IF NOT EXISTS cache_metadata (
    cache_id TEXT PRIMARY KEY,
    entity_type TEXT,  -- dictation, assessment, etc.
    entity_id TEXT,
    clinic_id TEXT,
    
    -- Cache info
    last_cached_at TEXT,
    cache_size_bytes INTEGER,
    is_compressed INTEGER DEFAULT 0,
    compression_ratio REAL,
    
    -- Metadata
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    accessed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_cache_metadata_entity ON cache_metadata(entity_type, entity_id);

-- ============================================================================
-- CLINICS TABLE (shared with RIS-1)
-- ============================================================================

CREATE TABLE IF NOT EXISTS clinics (
    clinic_id TEXT PRIMARY KEY,
    clinic_name TEXT NOT NULL,
    country TEXT,
    province TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    timezone TEXT DEFAULT 'UTC',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- USERS TABLE (shared with RIS-1)
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    clinic_id TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    full_name TEXT,
    role TEXT,  -- admin, radiologist, clinician, triage, receptionist
    password_hash TEXT,
    is_active INTEGER DEFAULT 1,
    
    -- Sync tracking
    sync_status TEXT DEFAULT 'synced',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (clinic_id) REFERENCES clinics(clinic_id)
);

CREATE INDEX IF NOT EXISTS idx_users_clinic_id ON users(clinic_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- ============================================================================
-- STUDIES TABLE (shared with RIS-1)
-- ============================================================================

CREATE TABLE IF NOT EXISTS studies (
    study_id TEXT PRIMARY KEY,
    clinic_id TEXT NOT NULL,
    patient_id TEXT,
    modality TEXT,  -- XR, CT, MRI, US, NM, PT, etc.
    study_date TEXT,
    
    -- Status
    status TEXT DEFAULT 'pending',
    sync_status TEXT DEFAULT 'pending',
    
    -- Metadata
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (clinic_id) REFERENCES clinics(clinic_id)
);

CREATE INDEX IF NOT EXISTS idx_studies_clinic_id ON studies(clinic_id);
CREATE INDEX IF NOT EXISTS idx_studies_patient_id ON studies(patient_id);

-- ============================================================================
-- REPORTS TABLE (shared with RIS-1)
-- ============================================================================

CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    study_id TEXT,
    clinic_id TEXT,
    user_id TEXT,
    
    -- Content
    report_text TEXT,
    status TEXT DEFAULT 'draft',
    
    -- Sync tracking
    sync_status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (study_id) REFERENCES studies(study_id),
    FOREIGN KEY (clinic_id) REFERENCES clinics(clinic_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_reports_study_id ON reports(study_id);
CREATE INDEX IF NOT EXISTS idx_reports_clinic_id ON reports(clinic_id);

-- ============================================================================
-- PERFORMANCE STATISTICS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS daily_stats (
    stat_id TEXT PRIMARY KEY,
    clinic_id TEXT NOT NULL,
    stat_date TEXT NOT NULL,
    
    -- Dictation stats
    total_dictations INTEGER DEFAULT 0,
    avg_transcription_confidence REAL DEFAULT 0.0,
    avg_processing_time_ms REAL DEFAULT 0.0,
    
    -- Injury assessment stats
    critical_injuries_count INTEGER DEFAULT 0,
    severe_injuries_count INTEGER DEFAULT 0,
    moderate_injuries_count INTEGER DEFAULT 0,
    
    -- Sync stats
    synced_items_count INTEGER DEFAULT 0,
    sync_failures INTEGER DEFAULT 0,
    avg_sync_time_ms REAL DEFAULT 0.0,
    
    -- Metadata
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (clinic_id) REFERENCES clinics(clinic_id)
);

CREATE INDEX IF NOT EXISTS idx_daily_stats_clinic_date ON daily_stats(clinic_id, stat_date);

-- ============================================================================
-- ENABLE PRAGMA SETTINGS FOR PERFORMANCE
-- ============================================================================

PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -64000;
PRAGMA query_only = FALSE;
