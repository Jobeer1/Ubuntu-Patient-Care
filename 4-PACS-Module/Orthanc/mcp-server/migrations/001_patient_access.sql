-- Migration 001: Patient Access Control Tables
-- Created: 2025-10-21
-- Purpose: Add patient-level access control for referring doctors and patients

-- ============================================================================
-- Table 1: patient_relationships
-- Links MCP users to their patient records (for self-access)
-- ============================================================================
CREATE TABLE IF NOT EXISTS patient_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,                      -- MCP user ID
    patient_identifier VARCHAR(255) NOT NULL,      -- Patient ID/MRN from PACS
    relationship_type VARCHAR(50) NOT NULL,        -- 'self', 'child', 'parent', 'guardian'
    access_level VARCHAR(50) DEFAULT 'view',       -- 'view', 'download', 'share'
    created_by INTEGER,                            -- Admin who created this
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,                     -- Optional expiration
    is_active BOOLEAN DEFAULT 1,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE(user_id, patient_identifier)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_patient_rel_user ON patient_relationships(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_patient_rel_patient ON patient_relationships(patient_identifier);
CREATE INDEX IF NOT EXISTS idx_patient_rel_expires ON patient_relationships(expires_at);

-- ============================================================================
-- Table 2: doctor_patient_assignments
-- Links referring doctors to their assigned patients
-- ============================================================================
CREATE TABLE IF NOT EXISTS doctor_patient_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_user_id INTEGER NOT NULL,               -- MCP user ID (Referring Doctor)
    patient_identifier VARCHAR(255) NOT NULL,      -- Patient ID/MRN from PACS
    assignment_type VARCHAR(50) DEFAULT 'referring', -- 'referring', 'consulting', 'primary'
    access_level VARCHAR(50) DEFAULT 'view',       -- 'view', 'download', 'share', 'report'
    assigned_by INTEGER,                           -- Admin who assigned
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT 1,
    notes TEXT,
    FOREIGN KEY (doctor_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE(doctor_user_id, patient_identifier)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_doctor_assign_doctor ON doctor_patient_assignments(doctor_user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_doctor_assign_patient ON doctor_patient_assignments(patient_identifier);
CREATE INDEX IF NOT EXISTS idx_doctor_assign_expires ON doctor_patient_assignments(expires_at);

-- ============================================================================
-- Table 3: family_access
-- Links parents/guardians to children's patient records
-- ============================================================================
CREATE TABLE IF NOT EXISTS family_access (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_user_id INTEGER NOT NULL,               -- Parent/Guardian MCP user ID
    child_patient_identifier VARCHAR(255) NOT NULL, -- Child's Patient ID
    relationship VARCHAR(50) NOT NULL,             -- 'parent', 'legal_guardian', 'caregiver'
    access_level VARCHAR(50) DEFAULT 'view',
    verified BOOLEAN DEFAULT 0,                    -- Admin verification required
    verified_by INTEGER,
    verified_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,                     -- e.g., when child turns 18
    is_active BOOLEAN DEFAULT 1,
    notes TEXT,
    FOREIGN KEY (parent_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (verified_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_family_access_parent ON family_access(parent_user_id, is_active, verified);
CREATE INDEX IF NOT EXISTS idx_family_access_child ON family_access(child_patient_identifier);
CREATE INDEX IF NOT EXISTS idx_family_access_expires ON family_access(expires_at);

-- ============================================================================
-- Table 4: pacs_connection_config
-- Configuration for PACS database connection
-- ============================================================================
CREATE TABLE IF NOT EXISTS pacs_connection_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT,
    description TEXT,
    updated_by INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Insert default configuration values
INSERT OR IGNORE INTO pacs_connection_config (config_key, config_value, description) VALUES
('pacs_db_path', '../4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/orthanc-index/pacs_metadata.db', 'Path to PACS metadata database'),
('pacs_api_url', 'http://localhost:5000', 'PACS backend API URL'),
('enable_patient_access', '1', 'Enable patient self-access to images'),
('enable_family_access', '1', 'Enable family member access'),
('require_admin_verification', '1', 'Require admin verification for family access'),
('access_log_retention_days', '365', 'Number of days to retain access logs');

-- ============================================================================
-- Table 5: access_audit_log
-- Audit trail for all access attempts
-- ============================================================================
CREATE TABLE IF NOT EXISTS access_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    patient_identifier VARCHAR(255) NOT NULL,
    access_type VARCHAR(50) NOT NULL,              -- 'view', 'download', 'share', 'denied'
    access_granted BOOLEAN NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Index for audit queries
CREATE INDEX IF NOT EXISTS idx_audit_user ON access_audit_log(user_id, accessed_at);
CREATE INDEX IF NOT EXISTS idx_audit_patient ON access_audit_log(patient_identifier, accessed_at);
CREATE INDEX IF NOT EXISTS idx_audit_date ON access_audit_log(accessed_at);

-- ============================================================================
-- Migration Complete
-- ============================================================================
-- Tables created:
-- 1. patient_relationships (user → patient mapping)
-- 2. doctor_patient_assignments (doctor → patient mapping)
-- 3. family_access (parent → child mapping)
-- 4. pacs_connection_config (PACS connection settings)
-- 5. access_audit_log (audit trail)
--
-- Total indexes: 12
-- Total foreign keys: 9
-- ============================================================================
