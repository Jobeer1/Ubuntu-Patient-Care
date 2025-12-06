-- =============================================
-- GOTG-RIS: Lightweight SQLite Database Schema
-- Optimized for low-end devices, offline operation, instant sync
-- Minimal footprint: <50MB for 10,000 patients
-- =============================================

-- =============================================
-- Core Patients Table
-- =============================================
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT UNIQUE NOT NULL,  -- e.g., SA_ID_123456789
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    date_of_birth TEXT,  -- ISO 8601 format
    gender TEXT,  -- M, F, O
    phone TEXT,
    email TEXT,
    id_number TEXT UNIQUE,  -- South African ID
    clinic_id INTEGER,
    status TEXT DEFAULT 'active',  -- active, inactive, archived
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    sync_status TEXT DEFAULT 'pending'  -- pending, synced, failed
);
CREATE INDEX IF NOT EXISTS idx_patients_patient_id ON patients(patient_id);
CREATE INDEX IF NOT EXISTS idx_patients_id_number ON patients(id_number);
CREATE INDEX IF NOT EXISTS idx_patients_clinic_id ON patients(clinic_id);
CREATE INDEX IF NOT EXISTS idx_patients_sync_status ON patients(sync_status);

-- =============================================
-- Studies Table (Radiology Studies)
-- =============================================
CREATE TABLE IF NOT EXISTS studies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    study_uid TEXT UNIQUE NOT NULL,  -- DICOM Study UID
    patient_id INTEGER NOT NULL,
    accession_number TEXT UNIQUE,
    modality TEXT NOT NULL,  -- CR, DX, CT, MR, US, XC, etc.
    description TEXT,
    referring_physician TEXT,
    performing_physician TEXT,
    study_date TEXT NOT NULL,  -- ISO 8601 format
    study_time TEXT,
    body_part TEXT,
    procedure_code TEXT,
    priority TEXT DEFAULT 'routine',  -- routine, urgent, stat
    status TEXT DEFAULT 'pending',  -- pending, in_progress, completed, reported
    image_count INTEGER DEFAULT 0,
    total_size_bytes INTEGER DEFAULT 0,
    notes TEXT,
    clinic_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    sync_status TEXT DEFAULT 'pending',
    is_local_copy BOOLEAN DEFAULT 1,  -- 1 = stored locally, 0 = reference only
    FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_studies_study_uid ON studies(study_uid);
CREATE INDEX IF NOT EXISTS idx_studies_accession ON studies(accession_number);
CREATE INDEX IF NOT EXISTS idx_studies_patient_id ON studies(patient_id);
CREATE INDEX IF NOT EXISTS idx_studies_modality ON studies(modality);
CREATE INDEX IF NOT EXISTS idx_studies_status ON studies(status);
CREATE INDEX IF NOT EXISTS idx_studies_study_date ON studies(study_date);
CREATE INDEX IF NOT EXISTS idx_studies_sync_status ON studies(sync_status);

-- =============================================
-- Series Table (Image Groups within Study)
-- =============================================
CREATE TABLE IF NOT EXISTS series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_uid TEXT UNIQUE NOT NULL,  -- DICOM Series UID
    study_id INTEGER NOT NULL,
    series_number INTEGER,
    modality TEXT,
    series_description TEXT,
    instance_count INTEGER DEFAULT 0,
    series_date TEXT,
    series_time TEXT,
    body_part TEXT,
    image_laterality TEXT,  -- L, R, B (bilateral)
    total_size_bytes INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    sync_status TEXT DEFAULT 'pending',
    FOREIGN KEY(study_id) REFERENCES studies(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_series_series_uid ON series(series_uid);
CREATE INDEX IF NOT EXISTS idx_series_study_id ON series(study_id);
CREATE INDEX IF NOT EXISTS idx_series_modality ON series(modality);
CREATE INDEX IF NOT EXISTS idx_series_sync_status ON series(sync_status);

-- =============================================
-- DICOM Instances Table (Individual Images)
-- =============================================
CREATE TABLE IF NOT EXISTS dicom_instances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_uid TEXT UNIQUE NOT NULL,  -- DICOM Instance UID
    series_id INTEGER NOT NULL,
    instance_number INTEGER,
    sop_class TEXT,
    file_path TEXT,  -- Local path to DICOM file
    file_size INTEGER,
    compressed_size INTEGER,
    is_compressed BOOLEAN DEFAULT 0,
    compression_type TEXT,  -- gzip, deflate, etc.
    thumbnail_path TEXT,  -- Cached thumbnail for quick loading
    thumbnail_size INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    sync_status TEXT DEFAULT 'pending',
    is_synced BOOLEAN DEFAULT 0,
    FOREIGN KEY(series_id) REFERENCES series(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_instances_instance_uid ON dicom_instances(instance_uid);
CREATE INDEX IF NOT EXISTS idx_instances_series_id ON dicom_instances(series_id);
CREATE INDEX IF NOT EXISTS idx_instances_is_synced ON dicom_instances(is_synced);

-- =============================================
-- Reports Table
-- =============================================
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_uid TEXT UNIQUE NOT NULL,
    study_id INTEGER NOT NULL,
    radiologist_name TEXT,
    report_text TEXT,
    findings TEXT,
    impression TEXT,
    recommendations TEXT,
    report_date TEXT DEFAULT CURRENT_TIMESTAMP,
    report_status TEXT DEFAULT 'draft',  -- draft, finalized, verified
    verification_date TEXT,
    verified_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    sync_status TEXT DEFAULT 'pending',
    FOREIGN KEY(study_id) REFERENCES studies(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_reports_report_uid ON reports(report_uid);
CREATE INDEX IF NOT EXISTS idx_reports_study_id ON reports(study_id);
CREATE INDEX IF NOT EXISTS idx_reports_report_status ON reports(report_status);
CREATE INDEX IF NOT EXISTS idx_reports_sync_status ON reports(sync_status);

-- =============================================
-- Sync Queue Table (For offline-first sync)
-- =============================================
CREATE TABLE IF NOT EXISTS sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,  -- patient, study, report, etc.
    entity_id INTEGER,
    entity_uid TEXT,  -- UID for DICOM objects
    operation TEXT NOT NULL,  -- create, update, delete
    payload TEXT,  -- JSON data to sync
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    sync_attempts INTEGER DEFAULT 0,
    last_sync_attempt TEXT,
    sync_status TEXT DEFAULT 'pending',  -- pending, synced, failed
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    priority INTEGER DEFAULT 0  -- Higher = sync first
);
CREATE INDEX IF NOT EXISTS idx_sync_queue_status ON sync_queue(sync_status);
CREATE INDEX IF NOT EXISTS idx_sync_queue_entity_type ON sync_queue(entity_type);
CREATE INDEX IF NOT EXISTS idx_sync_queue_priority ON sync_queue(priority);
CREATE INDEX IF NOT EXISTS idx_sync_queue_created_at ON sync_queue(created_at);

-- =============================================
-- Sync Log Table (Audit trail for sync operations)
-- =============================================
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_batch_id TEXT,
    entity_type TEXT,
    entity_id INTEGER,
    operation TEXT,
    sync_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT,  -- success, failed, conflict
    data_size_bytes INTEGER,
    compressed_size_bytes INTEGER,
    compression_ratio REAL,
    sync_duration_ms INTEGER,
    error_details TEXT,
    conflict_resolution_strategy TEXT,  -- last_write_wins, field_merge, manual
    remote_version TEXT,
    local_version TEXT
);
CREATE INDEX IF NOT EXISTS idx_sync_log_timestamp ON sync_log(sync_timestamp);
CREATE INDEX IF NOT EXISTS idx_sync_log_sync_batch_id ON sync_log(sync_batch_id);
CREATE INDEX IF NOT EXISTS idx_sync_log_entity_type ON sync_log(entity_type);

-- =============================================
-- Conflict Resolution Table
-- =============================================
CREATE TABLE IF NOT EXISTS conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    entity_uid TEXT,
    local_version TEXT,
    remote_version TEXT,
    conflict_field TEXT,
    local_value TEXT,
    remote_value TEXT,
    resolution_strategy TEXT DEFAULT 'pending',  -- pending, resolved, manual
    resolved_value TEXT,
    resolved_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(resolution_strategy);
CREATE INDEX IF NOT EXISTS idx_conflicts_entity_type ON conflicts(entity_type);

-- =============================================
-- Clinics/Facilities Table
-- =============================================
CREATE TABLE IF NOT EXISTS clinics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinic_code TEXT UNIQUE NOT NULL,
    clinic_name TEXT NOT NULL,
    location TEXT,
    region TEXT,
    phone TEXT,
    address TEXT,
    gps_latitude REAL,
    gps_longitude REAL,
    connectivity_type TEXT,  -- offline, 2g, 3g, 4g, broadband
    last_sync TEXT,
    last_sync_status TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_clinics_clinic_code ON clinics(clinic_code);
CREATE INDEX IF NOT EXISTS idx_clinics_connectivity ON clinics(connectivity_type);

-- =============================================
-- Users/Staff Table
-- =============================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    full_name TEXT,
    role TEXT NOT NULL,  -- admin, radiologist, technician, receptionist
    clinic_id INTEGER,
    permissions TEXT,  -- JSON list of permissions
    is_active BOOLEAN DEFAULT 1,
    last_login TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(clinic_id) REFERENCES clinics(id)
);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_clinic_id ON users(clinic_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- =============================================
-- Local Cache Metadata
-- =============================================
CREATE TABLE IF NOT EXISTS cache_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,
    data_type TEXT,  -- study, series, report, image
    entity_uid TEXT,
    file_path TEXT,
    file_size INTEGER,
    compressed_size INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_accessed TEXT,
    ttl_seconds INTEGER DEFAULT 86400,  -- 24 hours
    is_archived BOOLEAN DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_cache_cache_key ON cache_metadata(cache_key);
CREATE INDEX IF NOT EXISTS idx_cache_entity_uid ON cache_metadata(entity_uid);
CREATE INDEX IF NOT EXISTS idx_cache_last_accessed ON cache_metadata(last_accessed);

-- =============================================
-- Analytics/Statistics (Local)
-- =============================================
CREATE TABLE IF NOT EXISTS daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stat_date TEXT NOT NULL,
    clinic_id INTEGER,
    studies_processed INTEGER DEFAULT 0,
    patients_registered INTEGER DEFAULT 0,
    reports_generated INTEGER DEFAULT 0,
    sync_successful INTEGER DEFAULT 0,
    sync_failed INTEGER DEFAULT 0,
    avg_sync_time_ms INTEGER,
    storage_used_bytes INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(clinic_id) REFERENCES clinics(id)
);
CREATE INDEX IF NOT EXISTS idx_stats_stat_date ON daily_stats(stat_date);
CREATE INDEX IF NOT EXISTS idx_stats_clinic_id ON daily_stats(clinic_id);

-- =============================================
-- Seed Data: Default Clinics and Users
-- =============================================

INSERT OR IGNORE INTO clinics (clinic_code, clinic_name, location, connectivity_type)
VALUES ('GOTG_PRIMARY', 'GOTG Primary Clinic', 'Primary Location', 'offline');

INSERT OR IGNORE INTO users (username, password_hash, full_name, role, clinic_id)
VALUES ('admin', 'demo_hash_change_on_first_login', 'System Admin', 'admin', 1);
