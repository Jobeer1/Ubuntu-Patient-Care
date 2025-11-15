"""
Credential Request ORM Model

Simple in-memory model for storing credential requests.
In production, this would use SQLAlchemy with a real database.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class CredentialRequestModel:
    """SQLAlchemy-like model for credential requests"""
    
    req_id: str
    requester_id: str
    status: str
    reason: str
    target_vault: str
    target_path: str
    patient_id: str
    study_id: str
    created_ts: str
    expires_ts: str
    merkle_proof_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return asdict(self)


# Simple in-memory database store (in production: use actual database)
class CredentialRequestStore:
    """In-memory store for credential requests"""
    
    def __init__(self):
        self.requests: Dict[str, CredentialRequestModel] = {}
    
    def create(self, model: CredentialRequestModel) -> CredentialRequestModel:
        """Store a new credential request"""
        self.requests[model.req_id] = model
        return model
    
    def get(self, req_id: str) -> Optional[CredentialRequestModel]:
        """Retrieve a credential request by ID"""
        return self.requests.get(req_id)
    
    def list_by_status(self, status: str) -> list:
        """List all requests with a given status"""
        return [
            model for model in self.requests.values()
            if model.status == status
        ]
    
    def update(self, req_id: str, **kwargs) -> Optional[CredentialRequestModel]:
        """Update a credential request"""
        if req_id not in self.requests:
            return None
        
        model = self.requests[req_id]
        for key, value in kwargs.items():
            if hasattr(model, key):
                setattr(model, key, value)
        
        return model


# Global store instance
_store = CredentialRequestStore()


def get_store() -> CredentialRequestStore:
    """Get the credential request store"""
    return _store
