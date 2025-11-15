"""
Tests for Token Issuer Service

Test coverage:
- Token generation with nonce
- Token signing and verification
- Nonce replay prevention
- Token expiration
- Revocation
- Statistics tracking
"""

import pytest
import time
import json
import base64
from datetime import datetime, timedelta

try:
    from mcp_medical_server.services.token_issuer import TokenIssuer, NonceStore, TokenStatus
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from services.token_issuer import TokenIssuer, NonceStore, TokenStatus


class TestNonceStore:
    """Tests for NonceStore"""
    
    def test_store_and_retrieve_nonce(self):
        """Test storing and retrieving a nonce"""
        store = NonceStore()
        nonce = "test-nonce-123"
        
        store.store_nonce(
            nonce=nonce,
            req_id="REQ-20251110-120000-abc123",
            expires_ts="2025-11-10T12:05:00Z"
        )
        
        record = store.get_nonce(nonce)
        assert record is not None
        assert record['req_id'] == "REQ-20251110-120000-abc123"
        assert record['used'] is False
    
    def test_mark_nonce_used(self):
        """Test marking nonce as used"""
        store = NonceStore()
        nonce = "test-nonce-123"
        
        store.store_nonce(
            nonce=nonce,
            req_id="REQ-20251110-120000-abc123",
            expires_ts="2025-11-10T12:05:00Z"
        )
        
        # Mark as used
        result = store.mark_nonce_used(nonce)
        assert result is True
        
        record = store.get_nonce(nonce)
        assert record['used'] is True
        assert record['used_ts'] is not None
    
    def test_mark_nonexistent_nonce_used_fails(self):
        """Test marking non-existent nonce as used fails"""
        store = NonceStore()
        result = store.mark_nonce_used("nonexistent")
        assert result is False
    
    def test_revoke_nonce(self):
        """Test revoking a nonce"""
        store = NonceStore()
        nonce = "test-nonce-123"
        
        store.store_nonce(
            nonce=nonce,
            req_id="REQ-20251110-120000-abc123",
            expires_ts="2025-11-10T12:05:00Z"
        )
        
        # Revoke
        result = store.revoke_nonce(nonce)
        assert result is True
        
        record = store.get_nonce(nonce)
        assert record['revoked'] is True
    
    def test_cleanup_expired_nonces(self):
        """Test cleaning up expired nonces"""
        store = NonceStore()
        
        # Add expired nonce
        store.store_nonce(
            nonce="expired-nonce",
            req_id="REQ-20251110-120000-abc123",
            expires_ts="2025-11-01T12:00:00Z"  # Past date
        )
        
        # Add non-expired nonce
        store.store_nonce(
            nonce="valid-nonce",
            req_id="REQ-20251110-120000-abc123",
            expires_ts="2099-11-10T12:00:00Z"  # Future date
        )
        
        # Cleanup
        removed = store.cleanup_expired()
        assert removed == 1
        
        # Verify expired is gone, valid remains
        assert store.get_nonce("expired-nonce") is None
        assert store.get_nonce("valid-nonce") is not None
    
    def test_stats(self):
        """Test statistics tracking"""
        store = NonceStore()
        
        # Add nonces in different states
        store.store_nonce("nonce1", "REQ-1", "2099-11-10T12:00:00Z")
        store.store_nonce("nonce2", "REQ-2", "2099-11-10T12:00:00Z")
        store.store_nonce("nonce3", "REQ-3", "2099-11-10T12:00:00Z")
        
        # Mark one as used
        store.mark_nonce_used("nonce1")
        
        # Revoke one
        store.revoke_nonce("nonce2")
        
        stats = store.get_stats()
        assert stats['total_nonces'] == 3
        assert stats['used_nonces'] == 1
        assert stats['revoked_nonces'] == 1
        assert stats['pending_nonces'] == 1


class TestTokenIssuer:
    """Tests for TokenIssuer"""
    
    def test_issue_token(self):
        """Test issuing a token"""
        issuer = TokenIssuer(server_key="test-secret-key-12345")
        
        result = issuer.issue_token(
            req_id="REQ-20251110-120000-abc123",
            vault="vault1",
            path="/credentials/db/password",
            ttl_seconds=300
        )
        
        assert 'token' in result
        assert 'nonce' in result
        assert 'exp_ts' in result
        assert 'exp_unix' in result
        assert result['req_id'] == "REQ-20251110-120000-abc123"
    
    def test_token_format(self):
        """Test token has correct format (payload.signature)"""
        issuer = TokenIssuer(server_key="test-secret-key-12345")
        
        result = issuer.issue_token(
            req_id="REQ-20251110-120000-abc123",
            vault="vault1",
            path="/credentials/db/password",
            ttl_seconds=300
        )
        
        token = result['token']
        parts = token.split('.')
        assert len(parts) == 2
        
        # Verify payload can be decoded
        payload_b64, signature_b64 = parts
        payload = base64.b64decode(payload_b64).decode('utf-8')
        claims = json.loads(payload)
        
        assert claims['iss'] == "mcp-server"
        assert claims['aud'] == "mcp-agent"
        assert claims['req_id'] == "REQ-20251110-120000-abc123"
        assert claims['vault'] == "vault1"
        assert claims['path'] == "/credentials/db/password"
    
    def test_validate_valid_token(self):
        """Test validating a valid token"""
        issuer = TokenIssuer(server_key="test-secret-key-12345")
        
        # Issue token
        result = issuer.issue_token(
            req_id="REQ-20251110-120000-abc123",
            vault="vault1",
            path="/credentials/db/password",
            ttl_seconds=300
        )
        
        # Validate token
        claims, status = issuer.validate_token(result['token'], check_nonce=False)
        
        assert status == TokenStatus.VALID
        assert claims is not None
        assert claims['req_id'] == "REQ-20251110-120000-abc123"
        assert claims['vault'] == "vault1"
    
    def test_validate_expired_token(self):
        """Test validating an expired token"""
        issuer = TokenIssuer(server_key="test-secret-key-12345")
        
        # Issue token with very short TTL
        result = issuer.issue_token(
            req_id="REQ-20251110-120000-abc123",
            vault="vault1",
            path="/credentials/db/password",
            ttl_seconds=0  # Expired immediately
        )
        
        # Wait a tiny bit to ensure expiration
        time.sleep(0.1)
        
        # Validate token
        claims, status = issuer.validate_token(result['token'], check_nonce=False)
        
        assert status == TokenStatus.EXPIRED
        assert claims is None
    
    def test_validate_tampered_token_fails(self):
        """Test validating a tampered token fails"""
        issuer = TokenIssuer(server_key="test-secret-key-12345")
        
        # Issue token
        result = issuer.issue_token(
            req_id="REQ-20251110-120000-abc123",
            vault="vault1",
            path="/credentials/db/password",
            ttl_seconds=300
        )
        
        # Tamper with token
        token = result['token']
        parts = token.split('.')
        payload_b64, signature_b64 = parts
        
        # Modify payload
        payload = base64.b64decode(payload_b64).decode('utf-8')
        tampered_payload = payload.replace("vault1", "vault-hacked")
        tampered_payload_b64 = base64.b64encode(tampered_payload.encode()).decode()
        
        tampered_token = f"{tampered_payload_b64}.{signature_b64}"
        
        # Validate tampered token
        claims, status = issuer.validate_token(tampered_token, check_nonce=False)
        
        assert status == TokenStatus.INVALID_SIGNATURE
        assert claims is None
    
    def test_nonce_replay_prevention(self):
        """Test that nonce cannot be reused"""
        issuer = TokenIssuer(server_key="test-secret-key-12345")
        
        # Issue token
        result = issuer.issue_token(
            req_id="REQ-20251110-120000-abc123",
            vault="vault1",
            path="/credentials/db/password",
            ttl_seconds=300
        )
        
        token = result['token']
        nonce = result['nonce']
        
        # First validation should succeed
        claims, status = issuer.validate_token(token, check_nonce=True)
        assert status == TokenStatus.VALID
        
        # Mark nonce as used
        issuer.mark_nonce_used(nonce)
        
        # Second validation should fail (nonce already used)
        claims, status = issuer.validate_token(token, check_nonce=True)
        assert status == TokenStatus.NONCE_ALREADY_USED
        assert claims is None
    
    def test_revoke_token(self):
        """Test revoking a token"""
        issuer = TokenIssuer(server_key="test-secret-key-12345")
        
        # Issue token
        result = issuer.issue_token(
            req_id="REQ-20251110-120000-abc123",
            vault="vault1",
            path="/credentials/db/password",
            ttl_seconds=300
        )
        
        nonce = result['nonce']
        
        # Revoke token
        result = issuer.revoke_token(nonce)
        assert result is True
        
        # Verify nonce is marked revoked
        store_record = issuer.nonce_store.get_nonce(nonce)
        assert store_record['revoked'] is True
    
    def test_different_server_keys_produce_different_signatures(self):
        """Test that different server keys produce different signatures"""
        issuer1 = TokenIssuer(server_key="key1")
        issuer2 = TokenIssuer(server_key="key2")
        
        result1 = issuer1.issue_token(
            req_id="REQ-20251110-120000-abc123",
            vault="vault1",
            path="/credentials/db/password",
            ttl_seconds=300
        )
        
        result2 = issuer2.issue_token(
            req_id="REQ-20251110-120000-abc123",
            vault="vault1",
            path="/credentials/db/password",
            ttl_seconds=300
        )
        
        # Tokens should be different
        assert result1['token'] != result2['token']
        
        # issuer1 can validate token1 but not token2
        claims, status = issuer1.validate_token(result1['token'], check_nonce=False)
        assert status == TokenStatus.VALID
        
        claims, status = issuer1.validate_token(result2['token'], check_nonce=False)
        assert status == TokenStatus.INVALID_SIGNATURE
    
    def test_invalid_token_format(self):
        """Test validating invalid token format"""
        issuer = TokenIssuer(server_key="test-secret-key-12345")
        
        # Test various invalid formats
        invalid_tokens = [
            "not-a-token",
            "payload-only",
            "too.many.parts.here",
            ""
        ]
        
        for invalid_token in invalid_tokens:
            claims, status = issuer.validate_token(invalid_token, check_nonce=False)
            assert status == TokenStatus.INVALID_SIGNATURE
            assert claims is None
    
    def test_cleanup_expired_nonces(self):
        """Test cleanup of expired nonces"""
        issuer = TokenIssuer(server_key="test-secret-key-12345")
        
        # Issue two tokens
        result1 = issuer.issue_token(
            req_id="REQ-1",
            vault="vault1",
            path="/path1",
            ttl_seconds=300
        )
        
        result2 = issuer.issue_token(
            req_id="REQ-2",
            vault="vault1",
            path="/path2",
            ttl_seconds=1
        )
        
        # Let second token expire
        time.sleep(1.1)
        
        # Cleanup
        removed = issuer.cleanup_expired_nonces()
        assert removed == 1
        
        # Verify first nonce still exists
        assert issuer.nonce_store.get_nonce(result1['nonce']) is not None
        assert issuer.nonce_store.get_nonce(result2['nonce']) is None


class TestTokenIssuerIntegration:
    """Integration tests for token issuer workflow"""
    
    def test_complete_token_lifecycle(self):
        """Test complete token lifecycle: issue -> validate -> use -> prevent replay"""
        issuer = TokenIssuer(server_key="test-secret-key-12345")
        
        # 1. Issue token
        result = issuer.issue_token(
            req_id="REQ-20251110-120000-abc123",
            vault="vault1",
            path="/credentials/db/password",
            ttl_seconds=300
        )
        
        token = result['token']
        nonce = result['nonce']
        
        # 2. Validate token (first time)
        claims, status = issuer.validate_token(token, check_nonce=True)
        assert status == TokenStatus.VALID
        assert claims['nonce'] == nonce
        
        # 3. Mark nonce as used
        issuer.mark_nonce_used(nonce)
        
        # 4. Try to use token again (should fail)
        claims, status = issuer.validate_token(token, check_nonce=True)
        assert status == TokenStatus.NONCE_ALREADY_USED
        assert claims is None
    
    def test_multiple_tokens_independence(self):
        """Test that multiple tokens are independent"""
        issuer = TokenIssuer(server_key="test-secret-key-12345")
        
        # Issue multiple tokens
        result1 = issuer.issue_token("REQ-1", "vault1", "/path1", 300)
        result2 = issuer.issue_token("REQ-2", "vault1", "/path2", 300)
        result3 = issuer.issue_token("REQ-3", "vault1", "/path3", 300)
        
        # Mark one nonce as used
        issuer.mark_nonce_used(result1['nonce'])
        
        # Other tokens should still be valid
        claims1, status1 = issuer.validate_token(result1['token'], check_nonce=True)
        assert status1 == TokenStatus.NONCE_ALREADY_USED
        
        claims2, status2 = issuer.validate_token(result2['token'], check_nonce=True)
        assert status2 == TokenStatus.VALID
        
        claims3, status3 = issuer.validate_token(result3['token'], check_nonce=True)
        assert status3 == TokenStatus.VALID
    
    def test_approval_signature_preservation(self):
        """Test that approval signature is stored in nonce record"""
        issuer = TokenIssuer(server_key="test-secret-key-12345")
        
        result = issuer.issue_token(
            req_id="REQ-20251110-120000-abc123",
            vault="vault1",
            path="/credentials/db/password",
            ttl_seconds=300,
            approval_signature="base64-approval-sig-here"
        )
        
        # Check nonce record
        nonce_record = issuer.nonce_store.get_nonce(result['nonce'])
        assert nonce_record['approval_signature'] == "base64-approval-sig-here"
    
    def test_token_claims_consistency(self):
        """Test that token claims are consistent between issue and validate"""
        issuer = TokenIssuer(server_key="test-secret-key-12345")
        
        issued_result = issuer.issue_token(
            req_id="REQ-20251110-143022-def456",
            vault="vault-prod",
            path="/secrets/prod/db",
            ttl_seconds=600
        )
        
        validated_claims, status = issuer.validate_token(
            issued_result['token'],
            check_nonce=False
        )
        
        assert validated_claims['req_id'] == "REQ-20251110-143022-def456"
        assert validated_claims['vault'] == "vault-prod"
        assert validated_claims['path'] == "/secrets/prod/db"
        assert validated_claims['exp'] == issued_result['exp_unix']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
