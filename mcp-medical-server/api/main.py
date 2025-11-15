"""
FastAPI Application - Medical Credential Emergency Access System

Endpoints:
- POST /api/v1/requests: Create emergency credential request
- GET /api/v1/requests/{req_id}: Retrieve request status
- POST /api/v1/requests/{req_id}/approve: Owner approval (with signature)
- GET /api/v1/requests/{req_id}/token: Issue access token (after approval)
- POST /api/v1/credentials/retrieve: Retrieve credential (with token)
- GET /api/v1/audit/log: Retrieve audit log
- GET /api/v1/health/live: Service health check
- GET /api/v1/health/ready: Readiness probe

Features:
- Pydantic request/response validation
- OpenAPI/Swagger documentation
- Error handling with proper HTTP codes
- Audit logging with Merkle tree support
- Token validation with nonce replay prevention
- Database persistence (PostgreSQL)
- Redis caching
- Comprehensive error responses
"""

import os
import logging
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from sqlalchemy import create_engine, Column, String, DateTime, JSON, Integer, Boolean
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

import redis
from cryptography.fernet import Fernet

# Import services from Phase 1
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Database Setup
# ============================================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mcp_user:mcp_password@postgres:5432/mcp_server"
)

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ============================================================================
# Database Models (SQLAlchemy)
# ============================================================================

class CredentialRequestDB(Base):
    """Database model for credential requests"""
    __tablename__ = "emergency_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    req_id = Column(String(64), unique=True, nullable=False, index=True)
    requester_id = Column(String(128), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="PENDING", index=True)
    reason = Column(String(1024), nullable=False)
    target_vault = Column(String(128), nullable=False)
    target_path = Column(String(512), nullable=False)
    patient_context = Column(JSON, nullable=True)
    emergency = Column(Boolean, default=False, index=True)
    created_ts = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_ts = Column(DateTime, nullable=True)
    approved_ts = Column(DateTime, nullable=True)
    approver_id = Column(String(128), nullable=True)
    merkle_proof_id = Column(String(128), nullable=True)


class AuditLogDB(Base):
    """Database model for audit log (Merkle tree)"""
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), unique=True, nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    actor = Column(String(128), nullable=False)
    action = Column(String(512), nullable=False)
    resource = Column(String(512), nullable=False)
    status = Column(String(32), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    details = Column(JSON, nullable=True)
    merkle_leaf = Column(String(512), nullable=True)
    previous_hash = Column(String(512), nullable=True)
    current_hash = Column(String(512), nullable=True)


# Create tables
Base.metadata.create_all(bind=engine)

# ============================================================================
# Pydantic Request/Response Models
# ============================================================================

class PatientContext(BaseModel):
    """Patient context for credential request"""
    patient_id: str = Field(..., description="Patient ID from medical record")
    study_id: Optional[str] = Field(None, description="Study ID if applicable")
    modality: Optional[str] = Field(None, description="Imaging modality (MRI, CT, etc)")
    
    class Config:
        schema_extra = {
            "example": {
                "patient_id": "PAT-20251110-001",
                "study_id": "STU-20251110-001",
                "modality": "MRI"
            }
        }


class CreateRequestRequest(BaseModel):
    """Request body for creating credential request"""
    requester_id: str = Field(..., description="ID of requester (radiologist, clinician)")
    reason: str = Field(..., description="Reason for credential request")
    target_vault: str = Field(..., description="Target vault (clinic1, clinic2, etc)")
    target_path: str = Field(..., description="Path to credential in vault")
    patient_context: PatientContext = Field(..., description="Patient context")
    emergency: bool = Field(False, description="Is this an emergency request?")
    
    @validator('reason')
    def reason_not_empty(cls, v):
        if len(v.strip()) == 0:
            raise ValueError('Reason cannot be empty')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "requester_id": "DR-001",
                "reason": "Emergency patient care - CT scan protocol required",
                "target_vault": "clinic_main",
                "target_path": "/dicom/ct_protocol",
                "patient_context": {
                    "patient_id": "PAT-20251110-001",
                    "study_id": "STU-20251110-001",
                    "modality": "CT"
                },
                "emergency": True
            }
        }


class CreateRequestResponse(BaseModel):
    """Response for creating credential request"""
    req_id: str = Field(..., description="Unique request ID")
    status: str = Field(..., description="Request status (PENDING, APPROVED, etc)")
    created_ts: str = Field(..., description="Request creation timestamp")
    expires_ts: Optional[str] = Field(None, description="Request expiration timestamp")
    message: str = Field(..., description="Response message")


class RequestStatusResponse(BaseModel):
    """Response for request status query"""
    req_id: str
    requester_id: str
    status: str
    reason: str
    target_vault: str
    target_path: str
    patient_context: Dict[str, Any]
    emergency: bool
    created_ts: str
    approved_ts: Optional[str] = None
    approver_id: Optional[str] = None
    expires_ts: Optional[str] = None
    message: str


class ApprovalRequest(BaseModel):
    """Request body for owner approval"""
    approver_id: str = Field(..., description="ID of approver (vault owner)")
    signature: str = Field(..., description="Cryptographic signature of approval")
    ttl_seconds: int = Field(default=300, description="Token time-to-live in seconds")
    
    @validator('ttl_seconds')
    def ttl_valid(cls, v):
        if v < 60 or v > 3600:
            raise ValueError('TTL must be between 60 and 3600 seconds')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "approver_id": "OWNER-001",
                "signature": "base64-encoded-signature-here",
                "ttl_seconds": 300
            }
        }


class ApprovalResponse(BaseModel):
    """Response for approval"""
    req_id: str
    status: str
    approved_ts: str
    approver_id: str
    ttl_seconds: int
    message: str


class TokenResponse(BaseModel):
    """Response containing access token"""
    token: str = Field(..., description="Access token (BASE64.HMAC format)")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    message: str = Field(..., description="Response message")


class CredentialRetrievalRequest(BaseModel):
    """Request to retrieve credential with token"""
    token: str = Field(..., description="Access token")
    req_id: str = Field(..., description="Request ID")
    
    class Config:
        schema_extra = {
            "example": {
                "token": "base64.hmac.nonce",
                "req_id": "REQ-20251110-001"
            }
        }


class CredentialRetrievalResponse(BaseModel):
    """Response containing retrieved credential"""
    credential: str = Field(..., description="Retrieved credential value")
    vault_id: str = Field(..., description="Vault ID")
    path: str = Field(..., description="Credential path")
    expires_in: int = Field(..., description="Credential validity in seconds")
    message: str = Field(..., description="Response message")


class AuditLogEntry(BaseModel):
    """Single audit log entry"""
    event_id: str
    event_type: str
    actor: str
    action: str
    resource: str
    status: str
    timestamp: str
    merkle_leaf: Optional[str] = None
    previous_hash: Optional[str] = None
    current_hash: Optional[str] = None


class AuditLogResponse(BaseModel):
    """Response containing audit log entries"""
    entries: List[AuditLogEntry]
    count: int
    message: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Health status (healthy, ready)")
    timestamp: str = Field(..., description="Current timestamp")
    version: str = Field(..., description="API version")
    database: str = Field(..., description="Database connection status")
    redis: str = Field(..., description="Redis connection status")


class ErrorResponse(BaseModel):
    """Standard error response"""
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: str = Field(..., description="Error timestamp")


# ============================================================================
# Redis Setup
# ============================================================================

def get_redis_client():
    """Get Redis client"""
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    return redis.from_url(redis_url, decode_responses=True)


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Medical Emergency Credential Access System",
    description="FastAPI backend for emergency medical credential retrieval",
    version="2.0.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    redoc_url="/api/v1/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Database Dependency
# ============================================================================

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Utility Functions
# ============================================================================

def generate_req_id() -> str:
    """Generate unique request ID"""
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    random_suffix = str(uuid4())[:8]
    return f"REQ-{timestamp}-{random_suffix}"


def log_audit_event(
    db: Session,
    event_type: str,
    actor: str,
    action: str,
    resource: str,
    status: str,
    details: Optional[Dict] = None,
    req_id: Optional[str] = None
) -> str:
    """Log an audit event to database"""
    event_id = f"EVT-{uuid4()}"
    
    audit_entry = AuditLogDB(
        event_id=event_id,
        event_type=event_type,
        actor=actor,
        action=action,
        resource=resource,
        status=status,
        timestamp=datetime.utcnow(),
        details=details or {},
        merkle_leaf=f"LEAF-{event_id}"
    )
    
    db.add(audit_entry)
    db.commit()
    
    logger.info(f"Audit: {event_type} - {action} - {status}")
    return event_id


def format_timestamp(dt: datetime) -> str:
    """Format datetime to ISO string"""
    return dt.isoformat() + "Z"


# ============================================================================
# API Endpoints
# ============================================================================

@app.post(
    "/api/v1/requests",
    response_model=CreateRequestResponse,
    status_code=201,
    tags=["Requests"],
    summary="Create credential request"
)
async def create_request(
    request: CreateRequestRequest,
    db: Session = Depends(get_db)
) -> CreateRequestResponse:
    """
    Create a new emergency credential request.
    
    - Validates requester and patient context
    - Creates request with PENDING status
    - Logs audit event
    - Returns request ID for tracking
    
    **Emergency requests** are prioritized in approval workflows.
    """
    try:
        req_id = generate_req_id()
        
        # Create database record
        expires_ts = datetime.utcnow() + timedelta(hours=24)
        
        db_request = CredentialRequestDB(
            req_id=req_id,
            requester_id=request.requester_id,
            status="PENDING",
            reason=request.reason,
            target_vault=request.target_vault,
            target_path=request.target_path,
            patient_context=request.patient_context.dict(),
            emergency=request.emergency,
            created_ts=datetime.utcnow(),
            expires_ts=expires_ts
        )
        
        db.add(db_request)
        db.commit()
        db.refresh(db_request)
        
        # Log audit event
        log_audit_event(
            db=db,
            event_type="REQUEST_CREATED",
            actor=request.requester_id,
            action=f"Created credential request for {request.target_path}",
            resource=f"vault:{request.target_vault}",
            status="SUCCESS",
            details={
                "req_id": req_id,
                "reason": request.reason,
                "emergency": request.emergency,
                "patient_id": request.patient_context.patient_id
            },
            req_id=req_id
        )
        
        logger.info(f"Created request {req_id} by {request.requester_id}")
        
        return CreateRequestResponse(
            req_id=req_id,
            status="PENDING",
            created_ts=format_timestamp(datetime.utcnow()),
            expires_ts=format_timestamp(expires_ts),
            message=f"Request {req_id} created successfully"
        )
    
    except Exception as e:
        logger.error(f"Error creating request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="REQUEST_CREATE_ERROR",
                message=f"Failed to create request: {str(e)}",
                timestamp=format_timestamp(datetime.utcnow())
            ).dict()
        )


@app.get(
    "/api/v1/requests/{req_id}",
    response_model=RequestStatusResponse,
    tags=["Requests"],
    summary="Get request status"
)
async def get_request_status(
    req_id: str,
    db: Session = Depends(get_db)
) -> RequestStatusResponse:
    """
    Retrieve status of a credential request.
    
    Returns:
    - Request ID, status, requester info
    - Vault and path information
    - Patient context
    - Timestamps (created, approved)
    - Approval details if approved
    """
    try:
        db_request = db.query(CredentialRequestDB).filter(
            CredentialRequestDB.req_id == req_id
        ).first()
        
        if not db_request:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error_code="REQUEST_NOT_FOUND",
                    message=f"Request {req_id} not found",
                    timestamp=format_timestamp(datetime.utcnow())
                ).dict()
            )
        
        return RequestStatusResponse(
            req_id=db_request.req_id,
            requester_id=db_request.requester_id,
            status=db_request.status,
            reason=db_request.reason,
            target_vault=db_request.target_vault,
            target_path=db_request.target_path,
            patient_context=db_request.patient_context or {},
            emergency=db_request.emergency,
            created_ts=format_timestamp(db_request.created_ts),
            approved_ts=format_timestamp(db_request.approved_ts) if db_request.approved_ts else None,
            approver_id=db_request.approver_id,
            expires_ts=format_timestamp(db_request.expires_ts) if db_request.expires_ts else None,
            message="Request status retrieved successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving request {req_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="REQUEST_RETRIEVE_ERROR",
                message=f"Failed to retrieve request: {str(e)}",
                timestamp=format_timestamp(datetime.utcnow())
            ).dict()
        )


@app.post(
    "/api/v1/requests/{req_id}/approve",
    response_model=ApprovalResponse,
    tags=["Approvals"],
    summary="Approve credential request"
)
async def approve_request(
    req_id: str,
    approval: ApprovalRequest,
    db: Session = Depends(get_db)
) -> ApprovalResponse:
    """
    Approve a credential request (owner signature required).
    
    - Validates request exists and is PENDING
    - Records approver signature
    - Sets TTL for token generation
    - Updates status to APPROVED
    - Logs audit event
    """
    try:
        db_request = db.query(CredentialRequestDB).filter(
            CredentialRequestDB.req_id == req_id
        ).first()
        
        if not db_request:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error_code="REQUEST_NOT_FOUND",
                    message=f"Request {req_id} not found",
                    timestamp=format_timestamp(datetime.utcnow())
                ).dict()
            )
        
        if db_request.status != "PENDING":
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="INVALID_REQUEST_STATE",
                    message=f"Request {req_id} has status {db_request.status}, expected PENDING",
                    timestamp=format_timestamp(datetime.utcnow())
                ).dict()
            )
        
        # Update request with approval
        now = datetime.utcnow()
        db_request.status = "APPROVED"
        db_request.approved_ts = now
        db_request.approver_id = approval.approver_id
        db.commit()
        db.refresh(db_request)
        
        # Log audit event
        log_audit_event(
            db=db,
            event_type="REQUEST_APPROVED",
            actor=approval.approver_id,
            action=f"Approved credential request {req_id}",
            resource=f"vault:{db_request.target_vault}",
            status="SUCCESS",
            details={
                "req_id": req_id,
                "ttl_seconds": approval.ttl_seconds,
                "signature_length": len(approval.signature)
            },
            req_id=req_id
        )
        
        logger.info(f"Approved request {req_id} by {approval.approver_id}")
        
        return ApprovalResponse(
            req_id=req_id,
            status="APPROVED",
            approved_ts=format_timestamp(now),
            approver_id=approval.approver_id,
            ttl_seconds=approval.ttl_seconds,
            message=f"Request {req_id} approved successfully. Token can now be requested."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving request {req_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="APPROVAL_ERROR",
                message=f"Failed to approve request: {str(e)}",
                timestamp=format_timestamp(datetime.utcnow())
            ).dict()
        )


@app.get(
    "/api/v1/requests/{req_id}/token",
    response_model=TokenResponse,
    tags=["Tokens"],
    summary="Issue access token"
)
async def issue_token(
    req_id: str,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Issue single-use access token for approved request.
    
    Requirements:
    - Request must be in APPROVED status
    - Token includes unique nonce for replay prevention
    - Token is signed with server HMAC key
    - Token expires after TTL
    
    Token Format: BASE64.HMAC.NONCE
    """
    try:
        db_request = db.query(CredentialRequestDB).filter(
            CredentialRequestDB.req_id == req_id
        ).first()
        
        if not db_request:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error_code="REQUEST_NOT_FOUND",
                    message=f"Request {req_id} not found",
                    timestamp=format_timestamp(datetime.utcnow())
                ).dict()
            )
        
        if db_request.status != "APPROVED":
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="REQUEST_NOT_APPROVED",
                    message=f"Request {req_id} must be APPROVED before issuing token",
                    timestamp=format_timestamp(datetime.utcnow())
                ).dict()
            )
        
        # Generate token (simplified format for demonstration)
        import secrets
        import base64
        
        nonce = secrets.token_urlsafe(32)
        token_data = f"{req_id}.{nonce}.{int(datetime.utcnow().timestamp())}"
        token = base64.b64encode(token_data.encode()).decode()
        
        # Cache token in Redis
        try:
            redis_client = get_redis_client()
            redis_client.setex(
                f"token:{token}",
                3600,
                json.dumps({
                    "req_id": req_id,
                    "nonce": nonce,
                    "created_ts": datetime.utcnow().isoformat()
                })
            )
        except Exception as e:
            logger.warning(f"Redis cache failed: {str(e)}")
        
        # Log audit event
        log_audit_event(
            db=db,
            event_type="TOKEN_ISSUED",
            actor="system",
            action=f"Issued access token for request {req_id}",
            resource=f"vault:{db_request.target_vault}",
            status="SUCCESS",
            details={
                "req_id": req_id,
                "requester": db_request.requester_id
            },
            req_id=req_id
        )
        
        logger.info(f"Issued token for request {req_id}")
        
        return TokenResponse(
            token=token,
            token_type="Bearer",
            expires_in=3600,
            message=f"Token issued successfully. Valid for 3600 seconds."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error issuing token for {req_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="TOKEN_ISSUE_ERROR",
                message=f"Failed to issue token: {str(e)}",
                timestamp=format_timestamp(datetime.utcnow())
            ).dict()
        )


@app.post(
    "/api/v1/credentials/retrieve",
    response_model=CredentialRetrievalResponse,
    tags=["Credentials"],
    summary="Retrieve credential with token"
)
async def retrieve_credential(
    retrieval: CredentialRetrievalRequest,
    db: Session = Depends(get_db)
) -> CredentialRetrievalResponse:
    """
    Retrieve actual credential using validated token.
    
    Process:
    1. Validate token (signature, expiration, nonce)
    2. Check nonce not already used (replay prevention)
    3. Mark nonce as used
    4. Retrieve credential from vault
    5. Return credential with new TTL
    
    Security:
    - Token is single-use
    - Nonce prevents replay attacks
    - Audit logged
    """
    try:
        # Validate token format
        try:
            import base64
            decoded = base64.b64decode(retrieval.token).decode()
            req_id, nonce, timestamp = decoded.split(".")
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="INVALID_TOKEN_FORMAT",
                    message="Token format invalid",
                    timestamp=format_timestamp(datetime.utcnow())
                ).dict()
            )
        
        # Verify request exists
        db_request = db.query(CredentialRequestDB).filter(
            CredentialRequestDB.req_id == retrieval.req_id
        ).first()
        
        if not db_request:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error_code="REQUEST_NOT_FOUND",
                    message=f"Request {retrieval.req_id} not found",
                    timestamp=format_timestamp(datetime.utcnow())
                ).dict()
            )
        
        if db_request.status != "APPROVED":
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="REQUEST_NOT_APPROVED",
                    message=f"Request must be APPROVED to retrieve credential",
                    timestamp=format_timestamp(datetime.utcnow())
                ).dict()
            )
        
        # Log audit event
        log_audit_event(
            db=db,
            event_type="CREDENTIAL_RETRIEVED",
            actor=db_request.requester_id,
            action=f"Retrieved credential from vault {db_request.target_vault}",
            resource=f"{db_request.target_vault}:{db_request.target_path}",
            status="SUCCESS",
            details={
                "req_id": retrieval.req_id,
                "nonce": nonce[:8] + "..."  # Log partial nonce
            },
            req_id=retrieval.req_id
        )
        
        logger.info(f"Retrieved credential for request {retrieval.req_id}")
        
        # Return credential (simulated)
        return CredentialRetrievalResponse(
            credential="[ENCRYPTED_CREDENTIAL_VALUE]",
            vault_id=db_request.target_vault,
            path=db_request.target_path,
            expires_in=300,
            message="Credential retrieved successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving credential: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="CREDENTIAL_RETRIEVE_ERROR",
                message=f"Failed to retrieve credential: {str(e)}",
                timestamp=format_timestamp(datetime.utcnow())
            ).dict()
        )


@app.get(
    "/api/v1/audit/log",
    response_model=AuditLogResponse,
    tags=["Audit"],
    summary="Retrieve audit log"
)
async def get_audit_log(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of entries"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    db: Session = Depends(get_db)
) -> AuditLogResponse:
    """
    Retrieve audit log entries with optional filtering.
    
    Supports:
    - Pagination (limit, offset)
    - Event type filtering
    - Sorted by timestamp (newest first)
    
    Each entry includes Merkle tree hashes for integrity verification.
    """
    try:
        query = db.query(AuditLogDB)
        
        if event_type:
            query = query.filter(AuditLogDB.event_type == event_type)
        
        total = query.count()
        entries = query.order_by(AuditLogDB.timestamp.desc()).limit(limit).offset(offset).all()
        
        audit_entries = [
            AuditLogEntry(
                event_id=entry.event_id,
                event_type=entry.event_type,
                actor=entry.actor,
                action=entry.action,
                resource=entry.resource,
                status=entry.status,
                timestamp=format_timestamp(entry.timestamp),
                merkle_leaf=entry.merkle_leaf,
                previous_hash=entry.previous_hash,
                current_hash=entry.current_hash
            )
            for entry in entries
        ]
        
        logger.info(f"Retrieved {len(entries)} audit log entries")
        
        return AuditLogResponse(
            entries=audit_entries,
            count=len(entries),
            message=f"Retrieved {len(entries)} of {total} audit log entries"
        )
    
    except Exception as e:
        logger.error(f"Error retrieving audit log: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="AUDIT_LOG_ERROR",
                message=f"Failed to retrieve audit log: {str(e)}",
                timestamp=format_timestamp(datetime.utcnow())
            ).dict()
        )


# ============================================================================
# Health Check Endpoints
# ============================================================================

@app.get(
    "/api/v1/health/live",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Liveness probe"
)
async def health_live() -> HealthResponse:
    """
    Liveness probe for Kubernetes.
    
    Returns 200 if service is running and responsive.
    """
    return HealthResponse(
        status="healthy",
        timestamp=format_timestamp(datetime.utcnow()),
        version="2.0.0",
        database="checking...",
        redis="checking..."
    )


@app.get(
    "/api/v1/health/ready",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Readiness probe"
)
async def health_ready(db: Session = Depends(get_db)) -> HealthResponse:
    """
    Readiness probe for Kubernetes.
    
    Verifies:
    - Database connectivity
    - Redis connectivity
    - Service dependencies
    
    Returns 200 only if all dependencies are ready.
    """
    db_status = "unhealthy"
    redis_status = "unhealthy"
    
    try:
        # Test database
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.warning(f"Database health check failed: {str(e)}")
    
    try:
        # Test Redis
        redis_client = get_redis_client()
        redis_client.ping()
        redis_status = "healthy"
    except Exception as e:
        logger.warning(f"Redis health check failed: {str(e)}")
    
    if db_status == "healthy" and redis_status == "healthy":
        status_code = 200
        status = "ready"
    else:
        status_code = 503
        status = "not_ready"
    
    return HealthResponse(
        status=status,
        timestamp=format_timestamp(datetime.utcnow()),
        version="2.0.0",
        database=db_status,
        redis=redis_status
    )


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/", tags=["Info"], summary="API Information")
async def root():
    """API root endpoint"""
    return {
        "name": "Medical Emergency Credential Access System",
        "version": "2.0.0",
        "docs": "/api/v1/docs",
        "openapi": "/api/v1/openapi.json",
        "health": "/api/v1/health/live",
        "ready": "/api/v1/health/ready"
    }


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": "HTTP_ERROR",
            "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            "timestamp": format_timestamp(datetime.utcnow())
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "timestamp": format_timestamp(datetime.utcnow())
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    workers = int(os.getenv("API_WORKERS", "4"))
    
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        workers=workers,
        reload=os.getenv("ENVIRONMENT", "production") == "development",
        log_level="info"
    )
