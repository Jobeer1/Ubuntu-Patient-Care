"""
Full Integration Tests for Emergency Credential Retrieval System

End-to-end tests orchestrating the complete workflow:
- Request creation → Owner approval → Token issuance → Secret retrieval
- Error scenarios and edge cases
- Merkle audit trail verification
- Replay attack prevention
"""

import pytest
import time

try:
    from audit.report_finalizer import ReportFinalizer
    from mcp_medical_server.api.credentials import CredentialRequestManager
    from mcp_medical_server.services.signature_service import SignatureService, ApprovalSignatureFactory
    from mcp_medical_server.services.token_issuer import TokenIssuer, TokenStatus
    from mcp_medical_server.services.vault_adapter import LocalVault, VaultAdapter, RetrievalStatus
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from audit.report_finalizer import ReportFinalizer
    from mcp_medical_server.api.credentials import CredentialRequestManager
    from mcp_medical_server.services.signature_service import SignatureService, ApprovalSignatureFactory
    from mcp_medical_server.services.token_issuer import TokenIssuer, TokenStatus
    from mcp_medical_server.services.vault_adapter import LocalVault, VaultAdapter, RetrievalStatus


class TestCompleteEmergencyWorkflow:
    """Integration tests for complete emergency credential workflow"""
    
    @pytest.fixture
    def setup_components(self):
        """Setup all components for integration testing"""
        finalizer = ReportFinalizer()
        request_manager = CredentialRequestManager(finalizer)
        signature_factory = ApprovalSignatureFactory()
        token_issuer = TokenIssuer(server_key="test-secret-integration")
        vault = LocalVault(vault_id="vault-test")
        vault_adapter = VaultAdapter(vault, token_issuer)
        
        # Setup owner keys
        signature_service = SignatureService()
        private_key, public_key = signature_service.generate_key_pair()
        
        # Store demo secret
        vault.store_secret(
            "/credentials/patient-123/mri",
            "mri_token_abc123",
            owner_id="dr.owner@hospital.com"
        )
        
        return {
            'finalizer': finalizer,
            'request_manager': request_manager,
            'signature_factory': signature_factory,
            'token_issuer': token_issuer,
            'vault': vault,
            'vault_adapter': vault_adapter,
            'signature_service': signature_service,
            'private_key': private_key,
            'public_key': public_key
        }
    
    def test_complete_workflow_from_request_to_retrieval(self, setup_components):
        """Test complete workflow: request -> approve -> token -> retrieve"""
        c = setup_components
        
        # Step 1: Create request
        request = c['request_manager'].create_request(
            req_id="REQ-20251110-120000-int001",
            requester_id="dr.smith@hospital.com",
            reason="Emergency MRI interpretation",
            target_vault="vault-test",
            target_path="/credentials/patient-123/mri",
            patient_context={"patient_id": "P-123"}
        )
        
        assert request is not None
        assert request['status'] == "PENDING"
        assert request['merkle_proof']['ledger_tx_id'] is not None
        
        # Step 2: Sign approval
        req_id = request['req_id']
        from datetime import datetime
        approved_ts = datetime.utcnow().isoformat() + "Z"
        message = f"{req_id} | {approved_ts}"
        signature = c['signature_service'].sign_message(c['private_key'], message)
        
        approval = {
            "req_id": req_id,
            "approver": "dr.owner@hospital.com",
            "approved_ts": approved_ts,
            "signature": signature,
            "ttl_seconds": 300
        }
        
        # Verify approval signature
        is_valid = c['signature_service'].verify_signature(c['public_key'], message, signature)
        assert is_valid is True
        
        # Step 3: Update request status
        request = c['request_manager'].update_request_status(
            req_id=req_id,
            new_status="APPROVED"
        )
        assert request['status'] == "APPROVED"
        
        # Step 4: Issue token
        token_result = c['token_issuer'].issue_token(
            req_id=req_id,
            vault="vault-test",
            path="/credentials/patient-123/mri",
            ttl_seconds=300,
            approval_signature=signature
        )
        
        assert token_result['token'] is not None
        assert token_result['nonce'] is not None
        
        # Step 5: Retrieve secret
        secret, status = c['vault_adapter'].retrieve_secret(
            token=token_result['token'],
            req_id=req_id,
            actor_id="mcp-agent-001",
            finalizer=c['finalizer']
        )
        
        assert status == RetrievalStatus.SUCCESS
        assert secret == "mri_token_abc123"
        
        # Step 6: Update request to RETRIEVED
        request = c['request_manager'].update_request_status(
            req_id=req_id,
            new_status="RETRIEVED"
        )
        assert request['status'] == "RETRIEVED"
    
    def test_merkle_audit_trail_complete_workflow(self, setup_components):
        """Test that all workflow steps are Merkle-stamped"""
        c = setup_components
        initial_entries = len(c['finalizer'].ledger.entries)
        
        # Create request (stamps CREDENTIAL_REQUEST event)
        request = c['request_manager'].create_request(
            req_id="REQ-int002",
            requester_id="dr.test@hospital.com",
            reason="Test workflow",
            target_vault="vault-test",
            target_path="/credentials/patient-123/mri",
        )
        
        assert len(c['finalizer'].ledger.entries) > initial_entries
        
        # Update status (stamps CREDENTIAL_APPROVED event)
        c['request_manager'].update_request_status(
            req_id="REQ-int002",
            new_status="APPROVED"
        )
        
        # Issue token and retrieve (stamps CREDENTIAL_RETRIEVED event)
        token_result = c['token_issuer'].issue_token(
            req_id="REQ-int002",
            vault="vault-test",
            path="/credentials/patient-123/mri",
            ttl_seconds=300
        )
        
        c['vault_adapter'].retrieve_secret(
            token=token_result['token'],
            req_id="REQ-int002",
            actor_id="agent",
            finalizer=c['finalizer']
        )
        
        # Verify multiple events in ledger
        ledger_entries = c['finalizer'].ledger.entries
        assert len(ledger_entries) >= initial_entries + 3
    
    def test_replay_prevention_across_workflow(self, setup_components):
        """Test replay prevention at each stage"""
        c = setup_components
        
        # Create and issue token
        request = c['request_manager'].create_request(
            req_id="REQ-replay-test",
            requester_id="dr.test@hospital.com",
            reason="Replay test",
            target_vault="vault-test",
            target_path="/credentials/patient-123/mri",
        )
        
        token_result = c['token_issuer'].issue_token(
            req_id="REQ-replay-test",
            vault="vault-test",
            path="/credentials/patient-123/mri",
            ttl_seconds=300
        )
        
        # First retrieval succeeds
        secret1, status1 = c['vault_adapter'].retrieve_secret(
            token=token_result['token'],
            req_id="REQ-replay-test",
            actor_id="agent1",
        )
        assert status1 == RetrievalStatus.SUCCESS
        
        # Second retrieval with same token fails
        secret2, status2 = c['vault_adapter'].retrieve_secret(
            token=token_result['token'],
            req_id="REQ-replay-test",
            actor_id="agent1",
        )
        assert status2 == RetrievalStatus.NONCE_ALREADY_USED
    
    def test_workflow_with_multiple_requests(self, setup_components):
        """Test handling multiple concurrent requests"""
        c = setup_components
        
        requests_data = [
            ("REQ-multi-001", "dr.alice@hospital.com", "/credentials/patient-123/mri"),
            ("REQ-multi-002", "dr.bob@hospital.com", "/credentials/patient-123/mri"),
            ("REQ-multi-003", "dr.charlie@hospital.com", "/credentials/patient-123/mri"),
        ]
        
        # Create requests
        requests = []
        for req_id, requester, path in requests_data:
            request = c['request_manager'].create_request(
                req_id=req_id,
                requester_id=requester,
                reason="Multi-request test",
                target_vault="vault-test",
                target_path=path,
            )
            requests.append(request)
        
        # Issue tokens for each
        tokens = []
        for request in requests:
            token_result = c['token_issuer'].issue_token(
                req_id=request['req_id'],
                vault="vault-test",
                path=request['target_path'],
                ttl_seconds=300
            )
            tokens.append(token_result['token'])
        
        # Retrieve secrets for each
        for i, (request, token) in enumerate(zip(requests, tokens)):
            secret, status = c['vault_adapter'].retrieve_secret(
                token=token,
                req_id=request['req_id'],
                actor_id=f"agent-{i}",
            )
            assert status == RetrievalStatus.SUCCESS
            assert secret == "mri_token_abc123"


class TestErrorHandling:
    """Tests for error scenarios and edge cases"""
    
    @pytest.fixture
    def setup_components(self):
        """Setup components"""
        finalizer = ReportFinalizer()
        request_manager = CredentialRequestManager(finalizer)
        token_issuer = TokenIssuer(server_key="test-error")
        vault = LocalVault(vault_id="vault-error")
        vault_adapter = VaultAdapter(vault, token_issuer)
        
        vault.store_secret("/path", "secret", "owner")
        
        return {
            'finalizer': finalizer,
            'request_manager': request_manager,
            'token_issuer': token_issuer,
            'vault': vault,
            'vault_adapter': vault_adapter
        }
    
    def test_request_without_patient_context(self, setup_components):
        """Test request creation with minimal data"""
        c = setup_components
        
        request = c['request_manager'].create_request(
            req_id="REQ-minimal",
            requester_id="dr.test@hospital.com",
            reason="Test",
            target_vault="vault-error",
            target_path="/path",
        )
        
        assert request is not None
        assert request['patient_context'] is None
    
    def test_expired_request_handling(self, setup_components):
        """Test handling of expired requests"""
        c = setup_components
        
        # Create request with very short SLA
        request = c['request_manager'].create_request(
            req_id="REQ-expire-test",
            requester_id="dr.test@hospital.com",
            reason="Expiry test",
            target_vault="vault-error",
            target_path="/path",
            sla_seconds=0
        )
        
        time.sleep(0.1)
        
        # Check if expired
        retrieved = c['request_manager'].get_request("REQ-expire-test")
        assert retrieved['status'] == "EXPIRED"
    
    def test_invalid_vault_path(self, setup_components):
        """Test retrieval with invalid vault path"""
        c = setup_components
        
        token_result = c['token_issuer'].issue_token(
            req_id="REQ-invalid-path",
            vault="vault-error",
            path="/nonexistent/path",
            ttl_seconds=300
        )
        
        secret, status = c['vault_adapter'].retrieve_secret(
            token=token_result['token'],
            req_id="REQ-invalid-path",
            actor_id="agent",
        )
        
        assert status == RetrievalStatus.SECRET_NOT_FOUND
    
    def test_scope_mismatch_vault(self, setup_components):
        """Test retrieval with wrong vault"""
        c = setup_components
        
        token_result = c['token_issuer'].issue_token(
            req_id="REQ-scope",
            vault="vault-wrong",
            path="/path",
            ttl_seconds=300
        )
        
        secret, status = c['vault_adapter'].retrieve_secret(
            token=token_result['token'],
            req_id="REQ-scope",
            actor_id="agent",
        )
        
        assert status == RetrievalStatus.SCOPE_MISMATCH
    
    def test_expired_token_retrieval(self, setup_components):
        """Test retrieval with expired token"""
        c = setup_components
        
        token_result = c['token_issuer'].issue_token(
            req_id="REQ-token-expire",
            vault="vault-error",
            path="/path",
            ttl_seconds=0
        )
        
        time.sleep(0.1)
        
        secret, status = c['vault_adapter'].retrieve_secret(
            token=token_result['token'],
            req_id="REQ-token-expire",
            actor_id="agent",
        )
        
        assert status == RetrievalStatus.EXPIRED_TOKEN


class TestSecurityProperties:
    """Tests verifying security properties"""
    
    def test_different_keys_produce_different_tokens(self):
        """Test that different server keys produce different tokens"""
        issuer1 = TokenIssuer(server_key="key1")
        issuer2 = TokenIssuer(server_key="key2")
        
        token1 = issuer1.issue_token("REQ-1", "vault", "/path", 300)['token']
        token2 = issuer2.issue_token("REQ-1", "vault", "/path", 300)['token']
        
        assert token1 != token2
        
        # issuer1 can't validate token2
        claims, status = issuer1.validate_token(token2, check_nonce=False)
        assert status.value != "valid"
    
    def test_tampered_token_rejected(self):
        """Test that tampered tokens are rejected"""
        issuer = TokenIssuer(server_key="test")
        
        token_result = issuer.issue_token("REQ-1", "vault", "/path", 300)
        token = token_result['token']
        
        # Tamper with token
        parts = token.split('.')
        payload, sig = parts
        tampered = f"{payload}..TAMPERED"
        
        claims, status = issuer.validate_token(tampered, check_nonce=False)
        assert status.value != "valid"
    
    def test_signature_verification_prevents_forgery(self):
        """Test that forged signatures are detected"""
        from mcp_medical_server.services.signature_service import SignatureService
        
        service = SignatureService()
        priv, pub = service.generate_key_pair()
        
        message = "important message"
        signature = service.sign_message(priv, message)
        
        # Verify legitimate signature
        assert service.verify_signature(pub, message, signature) is True
        
        # Tampered message fails verification
        assert service.verify_signature(pub, "tampered message", signature) is False
        
        # Tampered signature fails verification
        tampered_sig = signature[:-4] + "XXXX"
        assert service.verify_signature(pub, message, tampered_sig) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
