-- Initialize MCP Credentials Database
-- Version: 1.0.0
-- Description: Schema for emergency credential retrieval system

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Credentials table (stores encrypted secrets)
CREATE TABLE IF NOT EXISTS credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    secret_type VARCHAR(50) NOT NULL, -- 'password', 'api_key', 'private_key', 'token', 'certificate'
    encrypted_value BYTEA NOT NULL,
    key_version INT DEFAULT 1,
    metadata JSONB DEFAULT '{}',
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT valid_secret_type CHECK (secret_type IN ('password', 'api_key', 'private_key', 'token', 'certificate', 'connection_string'))
);

-- Emergency requests table
CREATE TABLE IF NOT EXISTS emergency_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    requester_id VARCHAR(255) NOT NULL,
    requester_name VARCHAR(255),
    resource_name VARCHAR(255) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    reason TEXT NOT NULL,
    urgency_level VARCHAR(20) DEFAULT 'normal', -- 'low', 'normal', 'high', 'critical'
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'approved', 'denied', 'expired', 'completed'
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    approved_by VARCHAR(255),
    approved_at TIMESTAMP,
    denial_reason TEXT,
    completion_time INTERVAL,
    metadata JSONB DEFAULT '{}',
    CONSTRAINT valid_status CHECK (status IN ('pending', 'approved', 'denied', 'expired', 'completed')),
    CONSTRAINT valid_urgency CHECK (urgency_level IN ('low', 'normal', 'high', 'critical'))
);

-- Approval workflows table
CREATE TABLE IF NOT EXISTS approval_workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID NOT NULL REFERENCES emergency_requests(id) ON DELETE CASCADE,
    approver_role VARCHAR(50) NOT NULL,
    approver_id VARCHAR(255),
    approver_name VARCHAR(255),
    decision VARCHAR(20), -- 'approved', 'denied', NULL (pending)
    decision_time TIMESTAMP,
    decision_reason TEXT,
    offline_signature VARCHAR(500),
    signature_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Token table (ephemeral tokens for credential retrieval)
CREATE TABLE IF NOT EXISTS tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID NOT NULL REFERENCES emergency_requests(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    token_type VARCHAR(50) DEFAULT 'ephemeral', -- 'ephemeral', 'session', 'api'
    nonce VARCHAR(255) NOT NULL UNIQUE,
    is_used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP,
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    metadata JSONB DEFAULT '{}'
);

-- Audit log (Merkle-stamped events)
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    actor VARCHAR(255),
    resource_id UUID,
    resource_type VARCHAR(50),
    action VARCHAR(50),
    result VARCHAR(20), -- 'success', 'failure', 'partial'
    details JSONB,
    error_message TEXT,
    merkle_leaf VARCHAR(255),
    previous_hash VARCHAR(255),
    current_hash VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_server_confirmed TIMESTAMP
);

-- Ephemeral accounts table
CREATE TABLE IF NOT EXISTS ephemeral_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID NOT NULL REFERENCES emergency_requests(id) ON DELETE CASCADE,
    account_name VARCHAR(255) NOT NULL,
    account_type VARCHAR(50), -- 'ssh', 'api', 'database'
    target_system VARCHAR(255),
    target_ip VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    revoked_at TIMESTAMP,
    revocation_reason TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Nonce table (replay prevention)
CREATE TABLE IF NOT EXISTS nonces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nonce_value VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    used_count INT DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);

-- Vault unseal shares table (for Shamir secret sharing)
CREATE TABLE IF NOT EXISTS vault_unseal_shares (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    share_index INT NOT NULL,
    share_hash VARCHAR(255) NOT NULL,
    holder_id VARCHAR(255),
    holder_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    UNIQUE(share_index)
);

-- Owner authorization table
CREATE TABLE IF NOT EXISTS owner_authorizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id VARCHAR(255) NOT NULL,
    owner_name VARCHAR(255),
    authorization_scope JSONB NOT NULL, -- device list, network ranges, time windows
    authorized_actions TEXT[], -- 'imaging', 'ephemeral_account', 'credential_extraction'
    valid_from TIMESTAMP NOT NULL,
    valid_until TIMESTAMP NOT NULL,
    offline_signature VARCHAR(500),
    signature_verified BOOLEAN DEFAULT FALSE,
    verification_key VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Indexes for performance
CREATE INDEX idx_credentials_active ON credentials(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_credentials_expires ON credentials(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_emergency_requests_status ON emergency_requests(status);
CREATE INDEX idx_emergency_requests_requester ON emergency_requests(requester_id);
CREATE INDEX idx_emergency_requests_expires ON emergency_requests(expires_at);
CREATE INDEX idx_tokens_request_id ON tokens(request_id);
CREATE INDEX idx_tokens_expires ON tokens(expires_at);
CREATE INDEX idx_tokens_is_used ON tokens(is_used);
CREATE INDEX idx_audit_log_event_type ON audit_log(event_type);
CREATE INDEX idx_audit_log_actor ON audit_log(actor);
CREATE INDEX idx_audit_log_created ON audit_log(created_at);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_id, resource_type);
CREATE INDEX idx_ephemeral_accounts_active ON ephemeral_accounts(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_ephemeral_accounts_expires ON ephemeral_accounts(expires_at);
CREATE INDEX idx_nonces_expires ON nonces(expires_at);
CREATE INDEX idx_owner_authorizations_owner ON owner_authorizations(owner_id);
CREATE INDEX idx_owner_authorizations_valid ON owner_authorizations(valid_from, valid_until);

-- Views for common queries
CREATE VIEW active_credentials AS
SELECT * FROM credentials
WHERE is_active = TRUE AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP);

CREATE VIEW pending_requests AS
SELECT * FROM emergency_requests
WHERE status = 'pending' AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP);

CREATE VIEW active_ephemeral_accounts AS
SELECT * FROM ephemeral_accounts
WHERE is_active = TRUE AND expires_at > CURRENT_TIMESTAMP;

-- Stored procedure for credential cleanup (expired)
CREATE OR REPLACE FUNCTION cleanup_expired_credentials()
RETURNS TABLE(deleted_count INT) AS $$
DECLARE
    count INT;
BEGIN
    DELETE FROM credentials
    WHERE expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP;
    GET DIAGNOSTICS count = ROW_COUNT;
    RETURN QUERY SELECT count;
END;
$$ LANGUAGE plpgsql;

-- Stored procedure for request cleanup
CREATE OR REPLACE FUNCTION cleanup_expired_requests()
RETURNS TABLE(deleted_count INT) AS $$
DECLARE
    count INT;
BEGIN
    DELETE FROM emergency_requests
    WHERE status = 'pending' AND (expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP);
    GET DIAGNOSTICS count = ROW_COUNT;
    RETURN QUERY SELECT count;
END;
$$ LANGUAGE plpgsql;

-- Stored procedure for Merkle tree validation
CREATE OR REPLACE FUNCTION validate_merkle_chain(start_id UUID)
RETURNS TABLE(is_valid BOOLEAN, last_hash VARCHAR) AS $$
BEGIN
    WITH RECURSIVE chain AS (
        SELECT id, current_hash, previous_hash, 1 as depth
        FROM audit_log
        WHERE id = start_id
        UNION ALL
        SELECT a.id, a.current_hash, a.previous_hash, c.depth + 1
        FROM audit_log a
        INNER JOIN chain c ON a.current_hash = c.previous_hash
        WHERE c.depth < 100
    )
    SELECT TRUE, MAX(current_hash)::VARCHAR FROM chain;
END;
$$ LANGUAGE plpgsql;

-- Permissions: Grant read-only access to application user
GRANT CONNECT ON DATABASE mcp_credentials TO mcp_user;
GRANT USAGE ON SCHEMA public TO mcp_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO mcp_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mcp_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO mcp_user;

-- Insert sample data for testing (if needed)
-- This should be disabled in production
INSERT INTO credentials (name, secret_type, encrypted_value, metadata)
VALUES (
    'Sample Test Credential',
    'password',
    pgp_sym_encrypt('test_password_12345', 'sample_key'),
    jsonb_build_object('source', 'test', 'environment', 'development')
) ON CONFLICT DO NOTHING;

COMMIT;
