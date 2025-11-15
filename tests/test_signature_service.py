"""
Tests for Signature Service and Owner Approval CLI

Test coverage:
- Key generation and persistence
- Message signing and verification
- Passphrase protection
- Approval signature creation and verification
- CLI integration
"""

import pytest
import json
import os
import tempfile
import shutil
from pathlib import Path

try:
    from mcp_medical_server.services.signature_service import SignatureService, ApprovalSignatureFactory
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from services.signature_service import SignatureService, ApprovalSignatureFactory


class TestSignatureService:
    """Tests for SignatureService cryptographic operations"""
    
    def test_generate_key_pair(self):
        """Test Ed25519 key pair generation"""
        private_key, public_key = SignatureService.generate_key_pair()
        
        assert private_key is not None
        assert public_key is not None
        assert private_key.private_bytes is not None
        assert public_key.public_bytes is not None
    
    def test_sign_and_verify_message(self):
        """Test message signing and verification"""
        service = SignatureService()
        private_key, public_key = service.generate_key_pair()
        
        message = "This is a test message"
        signature = service.sign_message(private_key, message)
        
        assert signature is not None
        assert isinstance(signature, str)
        
        # Verify signature
        is_valid = service.verify_signature(public_key, message, signature)
        assert is_valid is True
    
    def test_verify_invalid_signature(self):
        """Test signature verification fails with invalid signature"""
        service = SignatureService()
        private_key, public_key = service.generate_key_pair()
        
        message = "This is a test message"
        signature = service.sign_message(private_key, message)
        
        # Tamper with message
        tampered_message = "This is a tampered message"
        is_valid = service.verify_signature(public_key, tampered_message, signature)
        assert is_valid is False
    
    def test_verify_wrong_key(self):
        """Test signature verification fails with wrong key"""
        service = SignatureService()
        
        # Create two key pairs
        private_key1, public_key1 = service.generate_key_pair()
        private_key2, public_key2 = service.generate_key_pair()
        
        message = "This is a test message"
        signature = service.sign_message(private_key1, message)
        
        # Verify with wrong key
        is_valid = service.verify_signature(public_key2, message, signature)
        assert is_valid is False
    
    def test_save_and_load_private_key(self):
        """Test saving and loading encrypted private key"""
        service = SignatureService()
        private_key, public_key = service.generate_key_pair()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = os.path.join(tmpdir, "test.key")
            passphrase = "super_secret_passphrase"
            
            # Save key
            service.save_private_key(private_key, key_path, passphrase)
            assert os.path.exists(key_path)
            
            # Load key
            loaded_key = service.load_private_key(key_path, passphrase)
            
            # Verify loaded key works
            message = "Test message"
            signature = service.sign_message(loaded_key, message)
            is_valid = service.verify_signature(public_key, message, signature)
            assert is_valid is True
    
    def test_load_private_key_wrong_passphrase(self):
        """Test loading private key with wrong passphrase fails"""
        service = SignatureService()
        private_key, _ = service.generate_key_pair()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = os.path.join(tmpdir, "test.key")
            correct_passphrase = "correct_passphrase"
            wrong_passphrase = "wrong_passphrase"
            
            # Save key
            service.save_private_key(private_key, key_path, correct_passphrase)
            
            # Try to load with wrong passphrase
            with pytest.raises(ValueError):
                service.load_private_key(key_path, wrong_passphrase)
    
    def test_save_and_load_public_key(self):
        """Test saving and loading public key"""
        service = SignatureService()
        _, public_key = service.generate_key_pair()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = os.path.join(tmpdir, "test.pub")
            
            # Save key
            service.save_public_key(public_key, key_path)
            assert os.path.exists(key_path)
            
            # Load key
            loaded_key = service.load_public_key(key_path)
            assert loaded_key is not None
    
    def test_message_as_bytes(self):
        """Test signing and verifying with message as bytes"""
        service = SignatureService()
        private_key, public_key = service.generate_key_pair()
        
        message = b"This is a test message as bytes"
        signature = service.sign_message(private_key, message)
        
        is_valid = service.verify_signature(public_key, message, signature)
        assert is_valid is True
    
    def test_file_permissions_on_private_key(self):
        """Test private key file has restricted permissions"""
        service = SignatureService()
        private_key, _ = service.generate_key_pair()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = os.path.join(tmpdir, "test.key")
            service.save_private_key(private_key, key_path, "passphrase")
            
            # Check file permissions (0o600 = -rw-------)
            stat_info = os.stat(key_path)
            mode = stat_info.st_mode & 0o777
            assert mode == 0o600


class TestApprovalSignatureFactory:
    """Tests for ApprovalSignatureFactory business logic"""
    
    def test_sign_approval(self):
        """Test signing a credential request approval"""
        factory = ApprovalSignatureFactory()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create owner keys
            private_key, public_key = factory.signature_service.generate_key_pair()
            key_path = os.path.join(tmpdir, "owner1.key")
            passphrase = "owner_passphrase"
            
            factory.signature_service.save_private_key(private_key, key_path, passphrase)
            
            # Sign approval
            approval = factory.sign_approval(
                req_id="REQ-20251110-120000-abc123",
                approver_id="owner1@hospital.com",
                private_key_path=key_path,
                passphrase=passphrase,
                ttl_seconds=300
            )
            
            assert approval['req_id'] == "REQ-20251110-120000-abc123"
            assert approval['approver'] == "owner1@hospital.com"
            assert approval['ttl_seconds'] == 300
            assert 'approved_ts' in approval
            assert 'signature' in approval
    
    def test_verify_approval(self):
        """Test verifying a signed approval"""
        factory = ApprovalSignatureFactory()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create owner keys
            private_key, public_key = factory.signature_service.generate_key_pair()
            private_key_path = os.path.join(tmpdir, "owner1.key")
            public_key_path = os.path.join(tmpdir, "owner1.pub")
            passphrase = "owner_passphrase"
            
            factory.signature_service.save_private_key(private_key, private_key_path, passphrase)
            factory.signature_service.save_public_key(public_key, public_key_path)
            
            # Sign approval
            approval = factory.sign_approval(
                req_id="REQ-20251110-120000-abc123",
                approver_id="owner1@hospital.com",
                private_key_path=private_key_path,
                passphrase=passphrase,
                ttl_seconds=300
            )
            
            # Verify approval
            is_valid = factory.verify_approval(approval, public_key_path)
            assert is_valid is True
    
    def test_tampered_approval_fails_verification(self):
        """Test that tampered approval fails verification"""
        factory = ApprovalSignatureFactory()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create owner keys
            private_key, public_key = factory.signature_service.generate_key_pair()
            private_key_path = os.path.join(tmpdir, "owner1.key")
            public_key_path = os.path.join(tmpdir, "owner1.pub")
            passphrase = "owner_passphrase"
            
            factory.signature_service.save_private_key(private_key, private_key_path, passphrase)
            factory.signature_service.save_public_key(public_key, public_key_path)
            
            # Sign approval
            approval = factory.sign_approval(
                req_id="REQ-20251110-120000-abc123",
                approver_id="owner1@hospital.com",
                private_key_path=private_key_path,
                passphrase=passphrase,
                ttl_seconds=300
            )
            
            # Tamper with approval
            approval['req_id'] = "REQ-20251110-120000-tampered"
            
            # Verify should fail
            is_valid = factory.verify_approval(approval, public_key_path)
            assert is_valid is False
    
    def test_wrong_passphrase_fails(self):
        """Test that wrong passphrase causes error"""
        factory = ApprovalSignatureFactory()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            private_key, _ = factory.signature_service.generate_key_pair()
            key_path = os.path.join(tmpdir, "owner1.key")
            
            factory.signature_service.save_private_key(private_key, key_path, "correct")
            
            with pytest.raises(ValueError):
                factory.sign_approval(
                    req_id="REQ-20251110-120000-abc123",
                    approver_id="owner1@hospital.com",
                    private_key_path=key_path,
                    passphrase="wrong_passphrase",
                    ttl_seconds=300
                )
    
    def test_missing_key_file_fails(self):
        """Test that missing key file causes error"""
        factory = ApprovalSignatureFactory()
        
        with pytest.raises(ValueError):
            factory.sign_approval(
                req_id="REQ-20251110-120000-abc123",
                approver_id="owner1@hospital.com",
                private_key_path="/nonexistent/path/to/key",
                passphrase="passphrase",
                ttl_seconds=300
            )
    
    def test_custom_ttl(self):
        """Test custom TTL is preserved"""
        factory = ApprovalSignatureFactory()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            private_key, _ = factory.signature_service.generate_key_pair()
            key_path = os.path.join(tmpdir, "owner1.key")
            passphrase = "passphrase"
            
            factory.signature_service.save_private_key(private_key, key_path, passphrase)
            
            approval = factory.sign_approval(
                req_id="REQ-20251110-120000-abc123",
                approver_id="owner1@hospital.com",
                private_key_path=key_path,
                passphrase=passphrase,
                ttl_seconds=600  # Custom TTL
            )
            
            assert approval['ttl_seconds'] == 600
    
    def test_approval_contains_all_required_fields(self):
        """Test approval dict contains all required fields"""
        factory = ApprovalSignatureFactory()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            private_key, _ = factory.signature_service.generate_key_pair()
            key_path = os.path.join(tmpdir, "owner1.key")
            
            factory.signature_service.save_private_key(private_key, key_path, "pass")
            
            approval = factory.sign_approval(
                req_id="REQ-20251110-120000-abc123",
                approver_id="owner1@hospital.com",
                private_key_path=key_path,
                passphrase="pass",
                ttl_seconds=300
            )
            
            required_fields = ['req_id', 'approver', 'approved_ts', 'signature', 'ttl_seconds']
            for field in required_fields:
                assert field in approval
                assert approval[field] is not None


class TestApprovalIntegration:
    """Integration tests for complete approval workflow"""
    
    def test_complete_approval_workflow(self):
        """Test complete: create request -> sign approval -> verify signature"""
        factory = ApprovalSignatureFactory()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create owner keys
            private_key, public_key = factory.signature_service.generate_key_pair()
            private_key_path = os.path.join(tmpdir, "owner1.key")
            public_key_path = os.path.join(tmpdir, "owner1.pub")
            
            factory.signature_service.save_private_key(private_key, private_key_path, "pass123")
            factory.signature_service.save_public_key(public_key, public_key_path)
            
            # Sign approval
            approval = factory.sign_approval(
                req_id="REQ-20251110-143022-def456",
                approver_id="dr.smith@hospital.com",
                private_key_path=private_key_path,
                passphrase="pass123",
                ttl_seconds=600
            )
            
            # Verify approval
            is_valid = factory.verify_approval(approval, public_key_path)
            
            # Assertions
            assert is_valid is True
            assert approval['req_id'] == "REQ-20251110-143022-def456"
            assert approval['approver'] == "dr.smith@hospital.com"
            assert approval['ttl_seconds'] == 600
    
    def test_multiple_approvals_have_different_timestamps(self):
        """Test that multiple approvals have different timestamps"""
        import time
        factory = ApprovalSignatureFactory()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            private_key, _ = factory.signature_service.generate_key_pair()
            key_path = os.path.join(tmpdir, "owner1.key")
            
            factory.signature_service.save_private_key(private_key, key_path, "pass")
            
            approval1 = factory.sign_approval(
                req_id="REQ-20251110-120000-aaa111",
                approver_id="owner1@hospital.com",
                private_key_path=key_path,
                passphrase="pass"
            )
            
            time.sleep(0.1)  # Small delay to ensure different timestamps
            
            approval2 = factory.sign_approval(
                req_id="REQ-20251110-120000-bbb222",
                approver_id="owner1@hospital.com",
                private_key_path=key_path,
                passphrase="pass"
            )
            
            assert approval1['approved_ts'] != approval2['approved_ts']
    
    def test_different_owners_have_different_keys(self):
        """Test that different owners have different signatures"""
        factory = ApprovalSignatureFactory()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two owner key pairs
            priv1, pub1 = factory.signature_service.generate_key_pair()
            priv2, pub2 = factory.signature_service.generate_key_pair()
            
            key_path1 = os.path.join(tmpdir, "owner1.key")
            key_path2 = os.path.join(tmpdir, "owner2.key")
            
            factory.signature_service.save_private_key(priv1, key_path1, "pass")
            factory.signature_service.save_private_key(priv2, key_path2, "pass")
            
            # Same request, different owners
            approval1 = factory.sign_approval(
                req_id="REQ-20251110-120000-abc123",
                approver_id="owner1@hospital.com",
                private_key_path=key_path1,
                passphrase="pass"
            )
            
            approval2 = factory.sign_approval(
                req_id="REQ-20251110-120000-abc123",
                approver_id="owner2@hospital.com",
                private_key_path=key_path2,
                passphrase="pass"
            )
            
            # Signatures should be different
            assert approval1['signature'] != approval2['signature']
            assert approval1['approver'] != approval2['approver']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
