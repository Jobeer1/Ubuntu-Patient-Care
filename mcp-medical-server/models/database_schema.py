"""
Database Schema for Emergency Credential Retrieval System

Defines SQLAlchemy models for:
- credential_requests: Emergency access requests
- token_nonces: Nonce store for token replay prevention
- vault_secrets: Encrypted secrets storage
- credential_approvals: Approval audit trail
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class CredentialRequest(Base):
    """
    Emergency credential access requests.
    
    Each request represents a clinician's request for emergency access
    to a credential/secret stored in a vault.
    """
    __tablename__ = "credential_requests"
    
    id = Column(Integer, primary_key=True)
    req_id = Column(String(32), unique=True, nullable=False, index=True)
    requester_id = Column(String(128), nullable=False)  # Email/username
    status = Column(String(32), nullable=False, default="PENDING")  # PENDING, APPROVED, RETRIEVED, EXPIRED, DENIED
    reason = Column(Text, nullable=False)  # Justification for request
    target_vault = Column(String(128), nullable=False)
    target_path = Column(String(512), nullable=False)
    patient_context = Column(JSON)  # {patient_id, study_id, ...}
    created_ts = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    expires_ts = Column(TIMESTAMP, nullable=False)  # SLA timeout
    merkle_proof_id = Column(String(64))  # Link to audit ledger
    
    # Relationships
    approvals = relationship("CredentialApproval", back_populates="request")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "req_id": self.req_id,
            "requester_id": self.requester_id,
            "status": self.status,
            "reason": self.reason,
            "target_vault": self.target_vault,
            "target_path": self.target_path,
            "patient_context": self.patient_context,
            "created_ts": self.created_ts.isoformat() if self.created_ts else None,
            "expires_ts": self.expires_ts.isoformat() if self.expires_ts else None,
            "merkle_proof_id": self.merkle_proof_id
        }


class TokenNonce(Base):
    """
    Nonce store for single-use token replay prevention.
    
    Each token is issued with a unique nonce. The nonce is marked
    as "used" after the token is validated once, preventing replay.
    """
    __tablename__ = "token_nonces"
    
    id = Column(Integer, primary_key=True)
    nonce = Column(String(256), unique=True, nullable=False, index=True)
    req_id = Column(String(32), ForeignKey("credential_requests.req_id"), nullable=False)
    created_ts = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    expires_ts = Column(TIMESTAMP, nullable=False)  # Token expiration time
    used = Column(Boolean, default=False)  # True after token validation
    used_ts = Column(TIMESTAMP)  # When token was used (for audit)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "nonce": self.nonce,
            "req_id": self.req_id,
            "created_ts": self.created_ts.isoformat() if self.created_ts else None,
            "expires_ts": self.expires_ts.isoformat() if self.expires_ts else None,
            "used": self.used,
            "used_ts": self.used_ts.isoformat() if self.used_ts else None
        }


class VaultSecret(Base):
    """
    Encrypted secrets storage.
    
    Stores credentials and secrets encrypted with Fernet (AES-128-CBC).
    Each secret is scoped to a vault and path.
    """
    __tablename__ = "vault_secrets"
    
    id = Column(Integer, primary_key=True)
    vault_id = Column(String(128), nullable=False)
    path = Column(String(512), nullable=False)
    encrypted_secret = Column(Text, nullable=False)  # Fernet-encrypted value
    created_ts = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    owner_id = Column(String(128), nullable=False)  # Owner who created this secret
    description = Column(String(512))  # Human-readable description
    cache_allowed = Column(Boolean, default=False)  # Owner allows caching
    last_accessed_ts = Column(TIMESTAMP)  # For audit
    
    __table_args__ = (
        # Unique constraint: (vault_id, path) - one secret per path per vault
        # In production: add UNIQUE constraint
    )
    
    def to_dict(self):
        """Convert to dictionary (without encrypted value)"""
        return {
            "id": self.id,
            "vault_id": self.vault_id,
            "path": self.path,
            "created_ts": self.created_ts.isoformat() if self.created_ts else None,
            "owner_id": self.owner_id,
            "description": self.description,
            "cache_allowed": self.cache_allowed,
            "last_accessed_ts": self.last_accessed_ts.isoformat() if self.last_accessed_ts else None
        }


class CredentialApproval(Base):
    """
    Approval audit trail for credential requests.
    
    Records each time a request is approved, including:
    - Who approved it
    - When
    - Digital signature (non-repudiation)
    - TTL granted
    """
    __tablename__ = "credential_approvals"
    
    id = Column(Integer, primary_key=True)
    req_id = Column(String(32), ForeignKey("credential_requests.req_id"), unique=True, nullable=False, index=True)
    approver_id = Column(String(128), nullable=False)  # Owner who approved
    signature = Column(Text)  # Ed25519/RSA digital signature (for offline approval)
    approved_ts = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    ttl_seconds = Column(Integer, default=300)  # How long token is valid (default 5 min)
    merkle_proof_id = Column(String(64))  # Link to audit ledger
    
    # Relationships
    request = relationship("CredentialRequest", back_populates="approvals")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "req_id": self.req_id,
            "approver_id": self.approver_id,
            "signature": self.signature,
            "approved_ts": self.approved_ts.isoformat() if self.approved_ts else None,
            "ttl_seconds": self.ttl_seconds,
            "merkle_proof_id": self.merkle_proof_id
        }


# Database initialization helper
def create_tables(engine):
    """
    Create all tables in the database.
    
    Usage:
        from sqlalchemy import create_engine
        engine = create_engine("sqlite:///credentials.db")
        create_tables(engine)
    """
    Base.metadata.create_all(engine)


def drop_tables(engine):
    """Drop all tables (for testing)"""
    Base.metadata.drop_all(engine)


# SQL DDL for reference (if using raw SQL instead of SQLAlchemy)
SQL_DDL = """
-- Credential requests
CREATE TABLE IF NOT EXISTS credential_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    req_id VARCHAR(32) UNIQUE NOT NULL,
    requester_id VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    reason TEXT,
    target_vault VARCHAR(128),
    target_path VARCHAR(512),
    patient_context JSON,
    created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_ts TIMESTAMP,
    merkle_proof_id VARCHAR(64)
);
CREATE INDEX idx_credential_requests_req_id ON credential_requests(req_id);
CREATE INDEX idx_credential_requests_status ON credential_requests(status);

-- Token nonces (replay prevention)
CREATE TABLE IF NOT EXISTS token_nonces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nonce VARCHAR(256) UNIQUE NOT NULL,
    req_id VARCHAR(32) NOT NULL,
    created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_ts TIMESTAMP,
    used BOOLEAN DEFAULT FALSE,
    used_ts TIMESTAMP,
    FOREIGN KEY (req_id) REFERENCES credential_requests(req_id)
);
CREATE INDEX idx_token_nonces_nonce ON token_nonces(nonce);
CREATE INDEX idx_token_nonces_req_id ON token_nonces(req_id);

-- Vault secrets
CREATE TABLE IF NOT EXISTS vault_secrets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vault_id VARCHAR(128) NOT NULL,
    path VARCHAR(512) NOT NULL,
    encrypted_secret TEXT,
    created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    owner_id VARCHAR(128) NOT NULL,
    description VARCHAR(512),
    cache_allowed BOOLEAN DEFAULT FALSE,
    last_accessed_ts TIMESTAMP,
    UNIQUE(vault_id, path)
);
CREATE INDEX idx_vault_secrets_vault ON vault_secrets(vault_id);
CREATE INDEX idx_vault_secrets_path ON vault_secrets(path);

-- Credential approvals
CREATE TABLE IF NOT EXISTS credential_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    req_id VARCHAR(32) UNIQUE NOT NULL,
    approver_id VARCHAR(128) NOT NULL,
    signature TEXT,
    approved_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ttl_seconds INTEGER DEFAULT 300,
    merkle_proof_id VARCHAR(64),
    FOREIGN KEY (req_id) REFERENCES credential_requests(req_id)
);
CREATE INDEX idx_credential_approvals_req_id ON credential_approvals(req_id);
"""
