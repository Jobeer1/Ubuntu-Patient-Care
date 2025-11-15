-- Emergency Credential Retrieval System - Database Initialization
-- Initializes PostgreSQL with all required tables and indexes

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schema
CREATE SCHEMA IF NOT EXISTS credentials;

-- Set default search path
SET search_path TO credentials, public;

-- ============================================================
-- Table: credential_requests
-- Stores all emergency credential requests
-- ============================================================
CREATE TABLE IF NOT EXISTS credential_requests (
    req_id VARCHAR(50) PRIMARY KEY,
    requester_id VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    reason TEXT NOT NULL,
    target_vault VARCHAR(255) NOT NULL,
    target_path VARCHAR(500) NOT NULL,
    patient_context JSONB,
    
    -- SLA Tracking
    created_ts TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_ts TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Merkle Proof
    merkle_proof_id VARCHAR(100),
    merkle_proof_hash VARCHAR(256),
    
    -- Metadata
    notes TEXT,
    
    CONSTRAINT requests_status_valid CHECK (
        status IN ('PENDING', 'APPROVED', 'RETRIEVED', 'EXPIRED', 'DENIED', 'CANCELLED')
    )
);

CREATE INDEX idx_credential_requests_requester ON credential_requests(requester_id);
CREATE INDEX idx_credential_requests_status ON credential_requests(status);
CREATE INDEX idx_credential_requests_created ON credential_requests(created_ts DESC);
CREATE INDEX idx_credential_requests_expires ON credential_requests(expires_ts);
CREATE INDEX idx_credential_requests_vault_path ON credential_requests(target_vault, target_path);

-- ============================================================
-- Table: token_nonces
-- Tracks single-use nonces for replay prevention
-- ============================================================
CREATE TABLE IF NOT EXISTS token_nonces (
    nonce_id VARCHAR(100) PRIMARY KEY,
    req_id VARCHAR(50) NOT NULL,
    nonce_value VARCHAR(256) NOT NULL UNIQUE,
    
    -- Status Tracking
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    
    -- Timestamps
    created_ts TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    used_ts TIMESTAMP WITH TIME ZONE,
    revoked_ts TIMESTAMP WITH TIME ZONE,
    expires_ts TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Metadata
    token_claims JSONB,
    
    CONSTRAINT nonce_status_valid CHECK (
        status IN ('PENDING', 'USED', 'REVOKED', 'EXPIRED')
    ),
    
    CONSTRAINT fk_nonce_request FOREIGN KEY (req_id) 
        REFERENCES credential_requests(req_id) ON DELETE CASCADE
);

CREATE INDEX idx_token_nonces_req_id ON token_nonces(req_id);
CREATE INDEX idx_token_nonces_status ON token_nonces(status);
CREATE INDEX idx_token_nonces_nonce_value ON token_nonces(nonce_value);
CREATE INDEX idx_token_nonces_expires ON token_nonces(expires_ts);

-- ============================================================
-- Table: vault_secrets
-- Stores encrypted secrets for different vaults
-- ============================================================
CREATE TABLE IF NOT EXISTS vault_secrets (
    secret_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    req_id VARCHAR(50) NOT NULL,
    vault_id VARCHAR(255) NOT NULL,
    vault_path VARCHAR(500) NOT NULL,
    
    -- Encrypted secret (using Fernet in application)
    encrypted_secret BYTEA NOT NULL,
    encryption_key_id VARCHAR(100),
    
    -- Metadata
    secret_type VARCHAR(50),
    scope JSONB,
    
    -- Timestamps
    created_ts TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_ts TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT fk_secret_request FOREIGN KEY (req_id) 
        REFERENCES credential_requests(req_id) ON DELETE CASCADE
);

CREATE INDEX idx_vault_secrets_req_id ON vault_secrets(req_id);
CREATE INDEX idx_vault_secrets_vault_path ON vault_secrets(vault_id, vault_path);
CREATE INDEX idx_vault_secrets_expires ON vault_secrets(expires_ts);

-- ============================================================
-- Table: credential_approvals
-- Tracks owner approvals with digital signatures
-- ============================================================
CREATE TABLE IF NOT EXISTS credential_approvals (
    approval_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    req_id VARCHAR(50) NOT NULL UNIQUE,
    
    approver_id VARCHAR(255) NOT NULL,
    approver_key_id VARCHAR(100),
    
    -- Digital Signature (Ed25519)
    signature_algorithm VARCHAR(50) NOT NULL DEFAULT 'Ed25519',
    signature BYTEA NOT NULL,
    signature_verified BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Timestamps
    created_ts TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approved_ts TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_ts TIMESTAMP WITH TIME ZONE NOT NULL,
    verified_ts TIMESTAMP WITH TIME ZONE,
    
    -- Audit
    notes TEXT,
    
    CONSTRAINT fk_approval_request FOREIGN KEY (req_id) 
        REFERENCES credential_requests(req_id) ON DELETE CASCADE
);

CREATE INDEX idx_credential_approvals_req_id ON credential_approvals(req_id);
CREATE INDEX idx_credential_approvals_approver ON credential_approvals(approver_id);
CREATE INDEX idx_credential_approvals_expires ON credential_approvals(expires_ts);

-- ============================================================
-- Table: credential_audit_events
-- Audit trail for all credential operations (Merkle ledger integration)
-- ============================================================
CREATE TABLE IF NOT EXISTS credential_audit_events (
    event_id BIGSERIAL PRIMARY KEY,
    req_id VARCHAR(50),
    event_type VARCHAR(50) NOT NULL,
    actor_id VARCHAR(255),
    
    -- Event Data
    event_data JSONB,
    
    -- Merkle Tree Integration
    content_hash VARCHAR(256) NOT NULL,
    merkle_tx_id VARCHAR(100),
    merkle_proof_hash VARCHAR(256),
    merkle_next_hash VARCHAR(256),
    
    -- Timestamps
    created_ts TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Status
    verified BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_audit_events_req_id ON credential_audit_events(req_id);
CREATE INDEX idx_audit_events_type ON credential_audit_events(event_type);
CREATE INDEX idx_audit_events_actor ON credential_audit_events(actor_id);
CREATE INDEX idx_audit_events_created ON credential_audit_events(created_ts DESC);
CREATE INDEX idx_audit_events_merkle_tx ON credential_audit_events(merkle_tx_id);

-- ============================================================
-- Table: retrieval_history
-- Tracks all secret retrieval attempts (for audit + analytics)
-- ============================================================
CREATE TABLE IF NOT EXISTS retrieval_history (
    retrieval_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    req_id VARCHAR(50) NOT NULL,
    nonce_id VARCHAR(100),
    
    requester_id VARCHAR(255),
    requester_ip_address INET,
    requester_user_agent TEXT,
    
    -- Retrieval Details
    vault_id VARCHAR(255) NOT NULL,
    vault_path VARCHAR(500) NOT NULL,
    retrieval_status VARCHAR(50) NOT NULL,
    
    -- Timestamps
    attempted_ts TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    success_ts TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    error_message TEXT,
    error_code VARCHAR(50),
    duration_ms INTEGER,
    
    CONSTRAINT fk_retrieval_request FOREIGN KEY (req_id) 
        REFERENCES credential_requests(req_id) ON DELETE CASCADE,
    
    CONSTRAINT fk_retrieval_nonce FOREIGN KEY (nonce_id) 
        REFERENCES token_nonces(nonce_id) ON DELETE SET NULL
);

CREATE INDEX idx_retrieval_history_req_id ON retrieval_history(req_id);
CREATE INDEX idx_retrieval_history_nonce_id ON retrieval_history(nonce_id);
CREATE INDEX idx_retrieval_history_attempted ON retrieval_history(attempted_ts DESC);
CREATE INDEX idx_retrieval_history_status ON retrieval_history(retrieval_status);

-- ============================================================
-- Views for common queries
-- ============================================================

-- View: pending_requests (for system monitoring)
CREATE VIEW pending_requests AS
SELECT 
    req_id,
    requester_id,
    target_vault,
    target_path,
    created_ts,
    expires_ts,
    EXTRACT(EPOCH FROM (expires_ts - CURRENT_TIMESTAMP)) as seconds_remaining
FROM credential_requests
WHERE status = 'PENDING'
    AND expires_ts > CURRENT_TIMESTAMP
ORDER BY expires_ts ASC;

-- View: expired_requests (for cleanup)
CREATE VIEW expired_requests AS
SELECT 
    req_id,
    requester_id,
    target_vault,
    expires_ts
FROM credential_requests
WHERE expires_ts <= CURRENT_TIMESTAMP
    AND status NOT IN ('EXPIRED', 'CANCELLED');

-- View: nonce_usage_summary (for analytics)
CREATE VIEW nonce_usage_summary AS
SELECT 
    status,
    COUNT(*) as count,
    COUNT(*) FILTER (WHERE age(CURRENT_TIMESTAMP, created_ts) < interval '1 hour') as last_hour
FROM token_nonces
GROUP BY status;

-- View: retrieval_success_rate (for monitoring)
CREATE VIEW retrieval_success_rate AS
SELECT 
    DATE(attempted_ts) as date,
    COUNT(*) as total_attempts,
    COUNT(*) FILTER (WHERE success_ts IS NOT NULL) as successful,
    ROUND(100.0 * COUNT(*) FILTER (WHERE success_ts IS NOT NULL) / COUNT(*), 2) as success_rate_pct
FROM retrieval_history
GROUP BY DATE(attempted_ts)
ORDER BY date DESC;

-- ============================================================
-- Stored Procedures / Functions
-- ============================================================

-- Function: mark_expired_requests
-- Periodically run to mark expired requests as expired
CREATE OR REPLACE FUNCTION mark_expired_requests()
RETURNS TABLE(updated_count INT) AS $$
DECLARE
    v_updated_count INT;
BEGIN
    UPDATE credential_requests
    SET status = 'EXPIRED'
    WHERE status = 'PENDING'
        AND expires_ts <= CURRENT_TIMESTAMP;
    
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    
    RETURN QUERY SELECT v_updated_count;
END;
$$ LANGUAGE plpgsql;

-- Function: cleanup_expired_nonces
-- Periodically run to mark expired nonces as expired
CREATE OR REPLACE FUNCTION cleanup_expired_nonces()
RETURNS TABLE(updated_count INT) AS $$
DECLARE
    v_updated_count INT;
BEGIN
    UPDATE token_nonces
    SET status = 'EXPIRED'
    WHERE status = 'PENDING'
        AND expires_ts <= CURRENT_TIMESTAMP;
    
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    
    RETURN QUERY SELECT v_updated_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Initialization Data (Optional)
-- ============================================================

-- Comment out or remove for production
-- INSERT INTO credential_requests (req_id, requester_id, reason, target_vault, target_path, expires_ts)
-- VALUES ('REQ-20251110-000001', 'test@example.com', 'Test request', 'test-vault', 'test/path', CURRENT_TIMESTAMP + interval '5 minutes');

-- ============================================================
-- Grants (for application user)
-- ============================================================

-- Grant permissions to app user (if created separately)
-- GRANT ALL PRIVILEGES ON SCHEMA credentials TO app_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA credentials TO app_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA credentials TO app_user;

COMMIT;
