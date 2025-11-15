"""
Test suite for FastAPI endpoints (Task 2.3)

Tests cover:
- Request creation and status tracking
- Approval workflow
- Token generation and validation
- Credential retrieval
- Audit logging
- Health checks
- Error handling
"""

import pytest
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# For testing, we'll use SQLite in-memory
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import after database setup
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.main import app, Base, get_db


# Create test database
Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def clear_database():
    """Clear database before each test"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def sample_request_payload():
    """Sample request creation payload"""
    return {
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


@pytest.fixture
def sample_approval_payload():
    """Sample approval payload"""
    return {
        "approver_id": "OWNER-001",
        "signature": "base64-encoded-signature-here",
        "ttl_seconds": 300
    }


# ============================================================================
# Test: Request Creation
# ============================================================================

class TestRequestCreation:
    """Tests for POST /api/v1/requests"""
    
    def test_create_request_success(self, clear_database, sample_request_payload):
        """Test successful request creation"""
        response = client.post(
            "/api/v1/requests",
            json=sample_request_payload
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "req_id" in data
        assert data["status"] == "PENDING"
        assert data["message"]
        
        # Verify request ID format
        assert data["req_id"].startswith("REQ-")
    
    def test_create_request_with_empty_reason(self, clear_database, sample_request_payload):
        """Test request creation with empty reason"""
        payload = sample_request_payload.copy()
        payload["reason"] = ""
        
        response = client.post(
            "/api/v1/requests",
            json=payload
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_request_non_emergency(self, clear_database, sample_request_payload):
        """Test non-emergency request creation"""
        payload = sample_request_payload.copy()
        payload["emergency"] = False
        
        response = client.post(
            "/api/v1/requests",
            json=payload
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "PENDING"
    
    def test_create_multiple_requests(self, clear_database, sample_request_payload):
        """Test creating multiple requests"""
        req_ids = []
        
        for i in range(3):
            payload = sample_request_payload.copy()
            payload["requester_id"] = f"DR-{i}"
            
            response = client.post(
                "/api/v1/requests",
                json=payload
            )
            
            assert response.status_code == 201
            req_ids.append(response.json()["req_id"])
        
        # Verify all requests have unique IDs
        assert len(set(req_ids)) == 3


# ============================================================================
# Test: Request Status Retrieval
# ============================================================================

class TestRequestStatus:
    """Tests for GET /api/v1/requests/{req_id}"""
    
    def test_get_request_status_success(self, clear_database, sample_request_payload):
        """Test successful request status retrieval"""
        # Create request
        response = client.post(
            "/api/v1/requests",
            json=sample_request_payload
        )
        req_id = response.json()["req_id"]
        
        # Get status
        response = client.get(f"/api/v1/requests/{req_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["req_id"] == req_id
        assert data["status"] == "PENDING"
        assert data["requester_id"] == sample_request_payload["requester_id"]
        assert data["reason"] == sample_request_payload["reason"]
    
    def test_get_request_not_found(self, clear_database):
        """Test retrieving non-existent request"""
        response = client.get("/api/v1/requests/REQ-NONEXISTENT")
        
        assert response.status_code == 404
        data = response.json()
        assert "REQUEST_NOT_FOUND" in str(data)
    
    def test_request_status_fields(self, clear_database, sample_request_payload):
        """Test all response fields are present"""
        response = client.post(
            "/api/v1/requests",
            json=sample_request_payload
        )
        req_id = response.json()["req_id"]
        
        response = client.get(f"/api/v1/requests/{req_id}")
        data = response.json()
        
        required_fields = [
            "req_id", "requester_id", "status", "reason",
            "target_vault", "target_path", "patient_context",
            "emergency", "created_ts", "expires_ts"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"


# ============================================================================
# Test: Request Approval
# ============================================================================

class TestRequestApproval:
    """Tests for POST /api/v1/requests/{req_id}/approve"""
    
    def test_approve_request_success(self, clear_database, sample_request_payload, sample_approval_payload):
        """Test successful request approval"""
        # Create request
        response = client.post(
            "/api/v1/requests",
            json=sample_request_payload
        )
        req_id = response.json()["req_id"]
        
        # Approve request
        response = client.post(
            f"/api/v1/requests/{req_id}/approve",
            json=sample_approval_payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["req_id"] == req_id
        assert data["status"] == "APPROVED"
        assert data["approver_id"] == sample_approval_payload["approver_id"]
        assert data["ttl_seconds"] == sample_approval_payload["ttl_seconds"]
    
    def test_approve_nonexistent_request(self, clear_database, sample_approval_payload):
        """Test approving non-existent request"""
        response = client.post(
            "/api/v1/requests/REQ-NONEXISTENT/approve",
            json=sample_approval_payload
        )
        
        assert response.status_code == 404
    
    def test_approve_with_invalid_ttl(self, clear_database, sample_request_payload, sample_approval_payload):
        """Test approval with invalid TTL"""
        # Create request
        response = client.post(
            "/api/v1/requests",
            json=sample_request_payload
        )
        req_id = response.json()["req_id"]
        
        # Try approval with too short TTL
        payload = sample_approval_payload.copy()
        payload["ttl_seconds"] = 30  # Less than 60 seconds
        
        response = client.post(
            f"/api/v1/requests/{req_id}/approve",
            json=payload
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_approve_request_twice(self, clear_database, sample_request_payload, sample_approval_payload):
        """Test approving request twice should fail"""
        # Create request
        response = client.post(
            "/api/v1/requests",
            json=sample_request_payload
        )
        req_id = response.json()["req_id"]
        
        # Approve first time
        response = client.post(
            f"/api/v1/requests/{req_id}/approve",
            json=sample_approval_payload
        )
        assert response.status_code == 200
        
        # Try to approve second time
        response = client.post(
            f"/api/v1/requests/{req_id}/approve",
            json=sample_approval_payload
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "INVALID_REQUEST_STATE" in str(data)


# ============================================================================
# Test: Token Generation
# ============================================================================

class TestTokenGeneration:
    """Tests for GET /api/v1/requests/{req_id}/token"""
    
    def test_issue_token_success(self, clear_database, sample_request_payload, sample_approval_payload):
        """Test successful token generation"""
        # Create and approve request
        response = client.post(
            "/api/v1/requests",
            json=sample_request_payload
        )
        req_id = response.json()["req_id"]
        
        client.post(
            f"/api/v1/requests/{req_id}/approve",
            json=sample_approval_payload
        )
        
        # Issue token
        response = client.get(f"/api/v1/requests/{req_id}/token")
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] > 0
    
    def test_issue_token_from_pending_request(self, clear_database, sample_request_payload):
        """Test token generation from pending request should fail"""
        # Create request (no approval)
        response = client.post(
            "/api/v1/requests",
            json=sample_request_payload
        )
        req_id = response.json()["req_id"]
        
        # Try to issue token
        response = client.get(f"/api/v1/requests/{req_id}/token")
        
        assert response.status_code == 400
        data = response.json()
        assert "REQUEST_NOT_APPROVED" in str(data)
    
    def test_token_format_validity(self, clear_database, sample_request_payload, sample_approval_payload):
        """Test token has valid format"""
        # Create and approve request
        response = client.post(
            "/api/v1/requests",
            json=sample_request_payload
        )
        req_id = response.json()["req_id"]
        
        client.post(
            f"/api/v1/requests/{req_id}/approve",
            json=sample_approval_payload
        )
        
        # Issue token
        response = client.get(f"/api/v1/requests/{req_id}/token")
        data = response.json()
        token = data["token"]
        
        # Token should be base64-encoded
        import base64
        try:
            decoded = base64.b64decode(token).decode()
            # Should contain req_id
            assert req_id in decoded
        except Exception:
            pytest.fail("Token is not valid base64")


# ============================================================================
# Test: Credential Retrieval
# ============================================================================

class TestCredentialRetrieval:
    """Tests for POST /api/v1/credentials/retrieve"""
    
    def test_retrieve_credential_success(self, clear_database, sample_request_payload, sample_approval_payload):
        """Test successful credential retrieval"""
        # Create, approve, and get token
        response = client.post(
            "/api/v1/requests",
            json=sample_request_payload
        )
        req_id = response.json()["req_id"]
        
        client.post(
            f"/api/v1/requests/{req_id}/approve",
            json=sample_approval_payload
        )
        
        response = client.get(f"/api/v1/requests/{req_id}/token")
        token = response.json()["token"]
        
        # Retrieve credential
        response = client.post(
            "/api/v1/credentials/retrieve",
            json={
                "token": token,
                "req_id": req_id
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "credential" in data
        assert data["vault_id"] == sample_request_payload["target_vault"]
        assert data["path"] == sample_request_payload["target_path"]
    
    def test_retrieve_credential_invalid_token_format(self, clear_database, sample_request_payload):
        """Test credential retrieval with invalid token format"""
        # Create request
        response = client.post(
            "/api/v1/requests",
            json=sample_request_payload
        )
        req_id = response.json()["req_id"]
        
        # Try to retrieve with invalid token
        response = client.post(
            "/api/v1/credentials/retrieve",
            json={
                "token": "invalid-token-format",
                "req_id": req_id
            }
        )
        
        assert response.status_code == 400
    
    def test_retrieve_credential_from_pending_request(self, clear_database, sample_request_payload):
        """Test credential retrieval from pending request should fail"""
        # Create request
        response = client.post(
            "/api/v1/requests",
            json=sample_request_payload
        )
        req_id = response.json()["req_id"]
        
        # Try to retrieve from pending
        response = client.post(
            "/api/v1/credentials/retrieve",
            json={
                "token": "dummy-token",
                "req_id": req_id
            }
        )
        
        assert response.status_code in [400, 404]


# ============================================================================
# Test: Audit Log
# ============================================================================

class TestAuditLog:
    """Tests for GET /api/v1/audit/log"""
    
    def test_audit_log_retrieval(self, clear_database, sample_request_payload):
        """Test audit log retrieval"""
        # Create request (generates audit event)
        client.post(
            "/api/v1/requests",
            json=sample_request_payload
        )
        
        # Get audit log
        response = client.get("/api/v1/audit/log")
        
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "count" in data
        assert data["count"] > 0
    
    def test_audit_log_pagination(self, clear_database, sample_request_payload):
        """Test audit log pagination"""
        # Create multiple requests
        for i in range(5):
            payload = sample_request_payload.copy()
            payload["requester_id"] = f"DR-{i}"
            client.post("/api/v1/requests", json=payload)
        
        # Get first page
        response = client.get("/api/v1/audit/log?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) <= 2
    
    def test_audit_log_filtering_by_event_type(self, clear_database, sample_request_payload):
        """Test audit log filtering by event type"""
        # Create request
        client.post("/api/v1/requests", json=sample_request_payload)
        
        # Get log filtered by event type
        response = client.get("/api/v1/audit/log?event_type=REQUEST_CREATED")
        
        assert response.status_code == 200
        data = response.json()
        
        for entry in data["entries"]:
            assert entry["event_type"] == "REQUEST_CREATED"


# ============================================================================
# Test: Health Checks
# ============================================================================

class TestHealthChecks:
    """Tests for health check endpoints"""
    
    def test_health_live(self, clear_database):
        """Test liveness probe"""
        response = client.get("/api/v1/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data
    
    def test_health_ready(self, clear_database):
        """Test readiness probe"""
        response = client.get("/api/v1/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "redis" in data


# ============================================================================
# Test: Root Endpoint
# ============================================================================

class TestRootEndpoint:
    """Tests for root endpoint"""
    
    def test_root_endpoint(self, clear_database):
        """Test root endpoint returns API info"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """End-to-end integration tests"""
    
    def test_complete_workflow(self, clear_database, sample_request_payload, sample_approval_payload):
        """Test complete request-approve-token-retrieve workflow"""
        # 1. Create request
        response = client.post(
            "/api/v1/requests",
            json=sample_request_payload
        )
        assert response.status_code == 201
        req_id = response.json()["req_id"]
        
        # 2. Check status is PENDING
        response = client.get(f"/api/v1/requests/{req_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "PENDING"
        
        # 3. Approve request
        response = client.post(
            f"/api/v1/requests/{req_id}/approve",
            json=sample_approval_payload
        )
        assert response.status_code == 200
        assert response.json()["status"] == "APPROVED"
        
        # 4. Issue token
        response = client.get(f"/api/v1/requests/{req_id}/token")
        assert response.status_code == 200
        token = response.json()["token"]
        
        # 5. Retrieve credential
        response = client.post(
            "/api/v1/credentials/retrieve",
            json={"token": token, "req_id": req_id}
        )
        assert response.status_code == 200
        
        # 6. Check audit log has events
        response = client.get("/api/v1/audit/log")
        assert response.status_code == 200
        assert response.json()["count"] >= 3  # At least CREATE, APPROVE, TOKEN, RETRIEVE
    
    def test_multiple_concurrent_requests(self, clear_database, sample_request_payload):
        """Test handling multiple concurrent requests"""
        req_ids = []
        
        # Create multiple requests
        for i in range(5):
            payload = sample_request_payload.copy()
            payload["requester_id"] = f"DR-{i}"
            
            response = client.post("/api/v1/requests", json=payload)
            assert response.status_code == 201
            req_ids.append(response.json()["req_id"])
        
        # Verify all requests exist
        for req_id in req_ids:
            response = client.get(f"/api/v1/requests/{req_id}")
            assert response.status_code == 200
    
    def test_error_recovery(self, clear_database, sample_request_payload, sample_approval_payload):
        """Test system recovery from errors"""
        # Create request
        response = client.post("/api/v1/requests", json=sample_request_payload)
        req_id = response.json()["req_id"]
        
        # Try to approve with bad signature (should not crash)
        bad_approval = sample_approval_payload.copy()
        bad_approval["signature"] = ""
        
        response = client.post(
            f"/api/v1/requests/{req_id}/approve",
            json=bad_approval
        )
        assert response.status_code == 200  # Should still succeed (signature validation in adapter)
        
        # System should still be operational
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
