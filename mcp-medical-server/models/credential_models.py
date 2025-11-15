"""
Database models for credential requests

CRITICAL: These models store emergency access requests and approvals.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class CredentialRequest(Base):
    """Emergency credential access request"""
    __tablename__ = "credential_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    req_id = Column(String(64), unique=True, nullable=False, index=True)
    requester_id = Column(String(128), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="PENDING", index=True)
    reason = Column(Text, nullable=False)
    target_vault = Column(String(128), nullable=False)
    target_path = Column(String(512), nullable=False)
    patient_context = Column(JSON, nullable=True)
    emergency = Column(Boolean, default=False, index=True)
    created_ts = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_ts = Column(DateTime, nullable=True)
    merkle_proof_id = Column(String(128), nullable=True)


class CredentialApproval(Base):
    """Owner approval for credential request"""
    __tablename__ = "credential_approvals"
    
    id = Column(Integer, primary_key=True, index=True)
    req_id = Column(String(64), ForeignKey("credential_requests.req_id"), unique=True, nullable=False)
    approver_id = Column(String(128), nullable=False)
    signature = Column(Text, nullable=False)
    approved_ts = Column(DateTime, default=datetime.utcnow, nullable=False)
    ttl_seconds = Column(Integer, nullable=False)
    merkle_proof_id = Column(String(128), nullable=True)


class TokenNonce(Base):
    """Single-use token nonces (prevent replay)"""
    __tablename__ = "token_nonces"
    
    id = Column(Integer, primary_key=True, index=True)
    nonce = Column(String(256), unique=True, nullable=False, index=True)
    req_id = Column(String(64), ForeignKey("credential_requests.req_id"), nullable=False)
    created_ts = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_ts = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, index=True)


class VaultSecret(Base):
    """Encrypted secrets in local vault"""
    __tablename__ = "vault_secrets"
    
    id = Column(Integer, primary_key=True, index=True)
    vault_id = Column(String(128), nullable=False, index=True)
    path = Column(String(512), nullable=False)
    encrypted_secret = Column(Text, nullable=False)
    created_ts = Column(DateTime, default=datetime.utcnow, nullable=False)
    owner_id = Column(String(128), nullable=False)
    cache_allowed = Column(Boolean, default=False)
    ttl_seconds = Column(Integer, nullable=True)
    
    __table_args__ = (
        # Unique constraint on vault_id + path
        {'sqlite_autoincrement': True},
    )
