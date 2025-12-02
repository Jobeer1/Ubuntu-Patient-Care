-- =============================================
-- Additional Tables for Enhanced RIS with ML Features
-- =============================================

-- =============================================
-- Facial Encodings Table
-- =============================================
CREATE TABLE IF NOT EXISTS facial_encodings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    encoding TEXT NOT NULL,  -- 128-dimensional vector as JSON
    encoding_hash TEXT,
    is_primary BOOLEAN DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_facial_encodings_patient_id ON facial_encodings(patient_id);
CREATE INDEX IF NOT EXISTS idx_facial_encodings_hash ON facial_encodings(encoding_hash);

-- =============================================
-- Fingerprints Table
-- =============================================
CREATE TABLE IF NOT EXISTS fingerprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    finger_position TEXT NOT NULL,  -- thumb_left, index_left, etc.
    minutiae TEXT NOT NULL,  -- Minutiae points as JSON
    template_size INTEGER,
    quality_score REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    UNIQUE(patient_id, finger_position)
);
CREATE INDEX IF NOT EXISTS idx_fingerprints_patient_id ON fingerprints(patient_id);
CREATE INDEX IF NOT EXISTS idx_fingerprints_finger_position ON fingerprints(finger_position);

-- =============================================
-- Emergency Contacts Table
-- =============================================
CREATE TABLE IF NOT EXISTS emergency_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    relationship TEXT,
    address TEXT,
    verified BOOLEAN DEFAULT 0,
    source TEXT,  -- manual, scraper, imported
    consent_given BOOLEAN DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_emergency_contacts_patient_id ON emergency_contacts(patient_id);
CREATE INDEX IF NOT EXISTS idx_emergency_contacts_phone ON emergency_contacts(phone);
CREATE INDEX IF NOT EXISTS idx_emergency_contacts_consent ON emergency_contacts(consent_given);

-- =============================================
-- Family Relationships Table
-- =============================================
CREATE TABLE IF NOT EXISTS family_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    family_member_id INTEGER NOT NULL,
    relationship TEXT NOT NULL,  -- parent, child, sibling, spouse
    verified BOOLEAN DEFAULT 0,
    confidence REAL,
    match_sources TEXT,  -- JSON array of sources
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY(family_member_id) REFERENCES patients(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_family_relationships_patient_id ON family_relationships(patient_id);
CREATE INDEX IF NOT EXISTS idx_family_relationships_family_member_id ON family_relationships(family_member_id);
CREATE INDEX IF NOT EXISTS idx_family_relationships_verified ON family_relationships(verified);

-- =============================================
-- Triage Records Table
-- =============================================
CREATE TABLE IF NOT EXISTS triage_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    triage_id TEXT UNIQUE NOT NULL,
    patient_id INTEGER NOT NULL,
    severity_level TEXT,  -- critical, urgent, moderate, minor, walking
    chief_complaint TEXT,
    vital_signs TEXT,  -- JSON: hr, bp, temp, rr, o2
    injuries TEXT,  -- JSON array
    treatment_given TEXT,
    assigned_to TEXT,  -- Healthcare worker ID
    location_lat REAL,
    location_lon REAL,
    sync_status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_triage_records_patient_id ON triage_records(patient_id);
CREATE INDEX IF NOT EXISTS idx_triage_records_severity_level ON triage_records(severity_level);
CREATE INDEX IF NOT EXISTS idx_triage_records_sync_status ON triage_records(sync_status);
CREATE INDEX IF NOT EXISTS idx_triage_records_created_at ON triage_records(created_at);

-- =============================================
-- Disaster Events Table
-- =============================================
CREATE TABLE IF NOT EXISTS disaster_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT,  -- earthquake, flood, conflict, pandemic, accident
    location TEXT,
    magnitude TEXT,
    status TEXT DEFAULT 'active',  -- active, contained, resolved
    affected_population INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_disaster_events_status ON disaster_events(status);
CREATE INDEX IF NOT EXISTS idx_disaster_events_event_type ON disaster_events(event_type);
CREATE INDEX IF NOT EXISTS idx_disaster_events_created_at ON disaster_events(created_at);

-- =============================================
-- Volunteer Tasks Table
-- =============================================
CREATE TABLE IF NOT EXISTS volunteer_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT UNIQUE NOT NULL,
    volunteer_id TEXT NOT NULL,
    task_type TEXT,  -- triage, supply_distribution, casualty_evacuation, data_entry
    patient_id INTEGER,
    location TEXT,
    status TEXT DEFAULT 'assigned',  -- assigned, in_progress, completed, failed
    priority INTEGER DEFAULT 5,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_volunteer_tasks_volunteer_id ON volunteer_tasks(volunteer_id);
CREATE INDEX IF NOT EXISTS idx_volunteer_tasks_status ON volunteer_tasks(status);
CREATE INDEX IF NOT EXISTS idx_volunteer_tasks_priority ON volunteer_tasks(priority);
CREATE INDEX IF NOT EXISTS idx_volunteer_tasks_created_at ON volunteer_tasks(created_at);

-- =============================================
-- Emergency Alerts Table
-- =============================================
CREATE TABLE IF NOT EXISTS emergency_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    message TEXT,
    severity TEXT,  -- critical, urgent, info
    recipient_type TEXT,  -- all, healthcare_workers, volunteers, patients
    delivered BOOLEAN DEFAULT 0,
    delivered_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_emergency_alerts_severity ON emergency_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_emergency_alerts_delivered ON emergency_alerts(delivered);
CREATE INDEX IF NOT EXISTS idx_emergency_alerts_created_at ON emergency_alerts(created_at);

-- =============================================
-- QR Code Patient IDs Table
-- =============================================
CREATE TABLE IF NOT EXISTS qr_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    qr_data TEXT,
    qr_hash TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_scanned TEXT,
    FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    UNIQUE(patient_id)
);
CREATE INDEX IF NOT EXISTS idx_qr_codes_patient_id ON qr_codes(patient_id);
CREATE INDEX IF NOT EXISTS idx_qr_codes_hash ON qr_codes(qr_hash);

-- =============================================
-- Biometric Match History Table
-- =============================================
CREATE TABLE IF NOT EXISTS biometric_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_patient_id INTEGER,
    matched_patient_id INTEGER NOT NULL,
    match_type TEXT,  -- facial, fingerprint, combined
    confidence REAL,
    algorithm_version TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(matched_patient_id) REFERENCES patients(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_biometric_matches_matched_patient_id ON biometric_matches(matched_patient_id);
CREATE INDEX IF NOT EXISTS idx_biometric_matches_confidence ON biometric_matches(confidence);
CREATE INDEX IF NOT EXISTS idx_biometric_matches_created_at ON biometric_matches(created_at);

-- =============================================
-- ML Model Metadata Table
-- =============================================
CREATE TABLE IF NOT EXISTS ml_model_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT UNIQUE NOT NULL,
    model_type TEXT,  -- facial_recognition, fingerprint_matching, identity_validation
    version TEXT,
    size_bytes INTEGER,
    accuracy_score REAL,
    last_updated TEXT,
    local_path TEXT,
    remote_url TEXT,
    is_available BOOLEAN DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ml_model_metadata_model_name ON ml_model_metadata(model_name);
CREATE INDEX IF NOT EXISTS idx_ml_model_metadata_model_type ON ml_model_metadata(model_type);
