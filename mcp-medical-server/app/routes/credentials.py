"""
Credential Request API Routes

CRITICAL: Emergency credential retrieval endpoints.
This is the core of the Worker Productivity Plan.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import CredentialRequest, CredentialApproval
from app.services.audit_service import AuditService
from app.middleware.access_control import require_auth

router = APIRouter()
audit = AuditService()


# Request Models
class CredentialRequestCreate(BaseModel):
    """Emergency credential request"""
    requester_id: str = Field(..., description="Email/ID of requester")
    reason: str = Field(..., description="Justification for access")
    target_vault: str = Field(..., description="Vault ID (e.g., 'subnet-1')")
    target_path: str = Field(..., description="Path to secret")
    patient_context: Optional[Dict[str, Any]] = Field(None, description="Patient/study context")
    emergency: bool = Field(False, description="Emergency flag for SLA")


class CredentialRequestResponse(BaseModel):
    """Response after creating request"""
    req_id: str
    status: str
    created_ts: str
    expires_ts: str
    merkle_proof: Dict[str, Any]


class ApprovalCreate(BaseModel):
    """Owner approval"""
    req_id: str
    approver_id: str
    signature: str
    ttl_seconds: int = 300


# Endpoints
@router.post("/requests", response_model=CredentialRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_credential_request(
    request: CredentialRequestCreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_auth)
):
    """
    Create emergency credential request
    
    Flow:
    1. Validate requester
    2. Create request record
    3. Merkle-stamp request
    4. Notify owner (if emergency)
    5. Return request ID + proof
    """
    try:
        import secrets
        from datetime import datetime, timedelta
        
        # Generate request ID
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        random_suffix = secrets.token_hex(6)
        req_id = f"REQ-{timestamp}-{random_suffix}"
        
        # Calculate expiration (5 minutes for emergency, 1 hour for normal)
        ttl_minutes = 5 if request.emergency else 60
        expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        
        # Create request record
        db_request = CredentialRequest(
            req_id=req_id,
            requester_id=request.requester_id,
            status="PENDING",
            reason=request.reason,
            target_vault=request.target_vault,
            target_path=request.target_path,
            patient_context=request.patient_context,
            emergency=request.emergency,
            created_ts=datetime.utcnow(),
            expires_ts=expires_at
        )
        
        db.add(db_request)
        db.commit()
        db.refresh(db_request)
        
        # Merkle-stamp the request
        merkle_proof = audit.record_event(
            event_type="CREDENTIAL_REQUEST",
            data={
                "req_id": req_id,
                "requester_id": request.requester_id,
                "target_vault": request.target_vault,
                "target_path": request.target_path,
                "emergency": request.emergency,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Update request with merkle proof
        db_request.merkle_proof_id = merkle_proof.get("hash", "")
        db.commit()
        
        # TODO: Notify owner if emergency
        if request.emergency:
            # Send notification (SMS/push/email)
            pass
        
        return CredentialRequestResponse(
            req_id=req_id,
            status="PENDING",
            created_ts=db_request.created_ts.isoformat() + "Z",
            expires_ts=expires_at.isoformat() + "Z",
            merkle_proof=merkle_proof
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create request: {str(e)}"
        )


@router.get("/requests/{req_id}")
async def get_credential_request(
    req_id: str,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_auth)
):
    """Get request status"""
    request = db.query(CredentialRequest).filter(
        CredentialRequest.req_id == req_id
    ).first()
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    return {
        "req_id": request.req_id,
        "status": request.status,
        "requester_id": request.requester_id,
        "reason": request.reason,
        "target_vault": request.target_vault,
        "target_path": request.target_path,
        "emergency": request.emergency,
        "created_ts": request.created_ts.isoformat() + "Z",
        "expires_ts": request.expires_ts.isoformat() + "Z" if request.expires_ts else None
    }


@router.post("/requests/{req_id}/approve")
async def approve_credential_request(
    req_id: str,
    approval: ApprovalCreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_auth)
):
    """
    Approve credential request (owner only)
    
    Flow:
    1. Validate request exists
    2. Verify owner signature
    3. Issue single-use token
    4. Merkle-stamp approval
    5. Return token
    """
    try:
        from services.signature_service import SignatureService
        from services.token_issuer import TokenIssuer
        
        # Get request
        request = db.query(CredentialRequest).filter(
            CredentialRequest.req_id == req_id
        ).first()
        
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found"
            )
        
        if request.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Request already {request.status}"
            )
        
        # Verify signature
        sig_service = SignatureService()
        is_valid = sig_service.verify_approval(
            req_id=req_id,
            approver_id=approval.approver_id,
            signature=approval.signature
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )
        
        # Issue token
        token_issuer = TokenIssuer()
        token_data = token_issuer.issue_token(
            req_id=req_id,
            vault=request.target_vault,
            path=request.target_path,
            ttl_seconds=approval.ttl_seconds
        )
        
        # Create approval record
        db_approval = CredentialApproval(
            req_id=req_id,
            approver_id=approval.approver_id,
            signature=approval.signature,
            approved_ts=datetime.utcnow(),
            ttl_seconds=approval.ttl_seconds
        )
        
        db.add(db_approval)
        
        # Update request status
        request.status = "APPROVED"
        db.commit()
        
        # Merkle-stamp approval
        merkle_proof = audit.record_event(
            event_type="CREDENTIAL_APPROVED",
            data={
                "req_id": req_id,
                "approver_id": approval.approver_id,
                "ttl_seconds": approval.ttl_seconds,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        db_approval.merkle_proof_id = merkle_proof.get("hash", "")
        db.commit()
        
        return {
            "req_id": req_id,
            "status": "APPROVED",
            "token": token_data["token"],
            "nonce": token_data["nonce"],
            "expires_at": token_data["expires_at"],
            "merkle_proof": merkle_proof
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Approval failed: {str(e)}"
        )


@router.get("/requests")
async def list_credential_requests(
    status_filter: Optional[str] = None,
    emergency_only: bool = False,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_auth)
):
    """List credential requests (filtered)"""
    query = db.query(CredentialRequest)
    
    if status_filter:
        query = query.filter(CredentialRequest.status == status_filter)
    
    if emergency_only:
        query = query.filter(CredentialRequest.emergency == True)
    
    requests = query.order_by(CredentialRequest.created_ts.desc()).limit(100).all()
    
    return {
        "requests": [
            {
                "req_id": req.req_id,
                "status": req.status,
                "requester_id": req.requester_id,
                "emergency": req.emergency,
                "created_ts": req.created_ts.isoformat() + "Z",
                "target_vault": req.target_vault
            }
            for req in requests
        ],
        "count": len(requests)
    }
