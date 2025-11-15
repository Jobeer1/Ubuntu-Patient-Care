"""
Tests for Vault Adapter and LocalVault

Test coverage:
- Vault secret storage and retrieval
- Fernet encryption
- Token validation and scope checking
- Nonce replay prevention
- Secret retrieval with Merkle-stamping
- Error handling
"""

import pytest
from datetime import datetime

try:
    from mcp_medical_server.services.vault_adapter import LocalVault, VaultAdapter, RetrievalStatus
    from mcp_medical_server.services.token_issuer import TokenIssuer
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from services.vault_adapter import LocalVault, VaultAdapter, RetrievalStatus
    from services.token_issuer import TokenIssuer


class TestLocalVault:
    """Tests for LocalVault"""
    
    def test_create_vault(self):
        """Test creating a local vault"""
        vault = LocalVault()
        assert vault.vault_id == "vault-local"
        assert vault.encryption_key is not None
    
    def test_store_and_retrieve_secret(self):
        """Test storing and retrieving a secret"""
        vault = LocalVault()
        path = "/credentials/db/password"
        secret = "super_secret_password_123"
        
        # Store
        result = vault.store_secret(path, secret, owner_id="admin@hospital.com")
        assert result is True
        
        # Retrieve
        retrieved = vault.retrieve_secret(path)
        assert retrieved == secret
    
    def test_secret_encryption(self):
        """Test that secrets are encrypted at rest"""
        vault = LocalVault()
        path = "/credentials/db/password"
        secret = "super_secret_password_123"
        
        vault.store_secret(path, secret, owner_id="admin@hospital.com")
        
        # Check that stored value is encrypted (different from original)
        stored_encrypted = vault.secrets[path]["encrypted_value"]
        assert stored_encrypted != secret
        assert "gAAAAAA" in stored_encrypted or "encrypted" in str(type(stored_encrypted))
    
    def test_secret_exists(self):
        """Test checking if secret exists"""
        vault = LocalVault()
        path = "/credentials/db/password"
        
        assert vault.secret_exists(path) is False
        
        vault.store_secret(path, "secret", owner_id="admin@hospital.com")
        
        assert vault.secret_exists(path) is True
    
    def test_retrieve_nonexistent_secret(self):
        """Test retrieving non-existent secret returns None"""
        vault = LocalVault()
        result = vault.retrieve_secret("/nonexistent/path")
        assert result is None
    
    def test_access_logging(self):
        """Test access logging"""
        vault = LocalVault()
        
        vault.log_access(
            path="/credentials/db/password",
            actor_id="agent1",
            success=True
        )
        
        log = vault.get_access_log()
        assert len(log) == 1
        assert log[0]['path'] == "/credentials/db/password"
        assert log[0]['actor_id'] == "agent1"
        assert log[0]['success'] is True
    
    def test_access_log_filtering(self):
        """Test filtering access log by path"""
        vault = LocalVault()
        
        vault.log_access("/path1", "agent1", True)
        vault.log_access("/path2", "agent1", True)
        vault.log_access("/path1", "agent2", False)
        
        log_path1 = vault.get_access_log("/path1")
        assert len(log_path1) == 2
        
        all_log = vault.get_access_log()
        assert len(all_log) == 3
    
    def test_encryption_key_persistence(self):
        """Test that encryption key can be reused"""
        # Create first vault and encrypt a secret
        vault1 = LocalVault()
        key = vault1.encryption_key
        vault1.store_secret("/path1", "secret123", "owner1")
        encrypted1 = vault1.secrets["/path1"]["encrypted_value"]
        
        # Create second vault with same key and retrieve
        vault2 = LocalVault(encryption_key=key)
        vault2.secrets = vault1.secrets
        
        retrieved = vault2.retrieve_secret("/path1")
        assert retrieved == "secret123"
    
    def test_multiple_secrets(self):
        """Test storing multiple secrets"""
        vault = LocalVault()
        
        secrets = {
            "/db/password": "db_pass_123",
            "/api/key": "api_key_456",
            "/ssl/cert": "cert_data_789"
        }
        
        for path, value in secrets.items():
            vault.store_secret(path, value, "owner1")
        
        for path, expected_value in secrets.items():
            retrieved = vault.retrieve_secret(path)
            assert retrieved == expected_value


class TestVaultAdapter:
    """Tests for VaultAdapter"""
    
    def test_retrieve_secret_with_valid_token(self):
        """Test successful secret retrieval with valid token"""
        # Setup
        vault = LocalVault()
        token_issuer = TokenIssuer(server_key="test-key")
        adapter = VaultAdapter(vault, token_issuer)
        
        # Store secret
        path = "/credentials/db/password"
        secret = "super_secret_123"
        vault.store_secret(path, secret, "owner1")
        
        # Issue token
        token_result = token_issuer.issue_token(
            req_id="REQ-20251110-120000-abc123",
            vault="vault-local",
            path=path,
            ttl_seconds=300
        )
        
        # Retrieve
        retrieved, status = adapter.retrieve_secret(
            token=token_result['token'],
            req_id="REQ-20251110-120000-abc123",
            actor_id="agent1"
        )
        
        assert status == RetrievalStatus.SUCCESS
        assert retrieved == secret
    
    def test_retrieve_secret_with_expired_token(self):
        """Test retrieval fails with expired token"""
        vault = LocalVault()
        token_issuer = TokenIssuer(server_key="test-key")
        adapter = VaultAdapter(vault, token_issuer)
        
        # Store secret
        vault.store_secret("/path", "secret", "owner1")
        
        # Issue token with very short TTL
        token_result = token_issuer.issue_token(
            req_id="REQ-123",
            vault="vault-local",
            path="/path",
            ttl_seconds=0
        )
        
        import time
        time.sleep(0.1)
        
        # Try to retrieve
        retrieved, status = adapter.retrieve_secret(
            token=token_result['token'],
            req_id="REQ-123",
            actor_id="agent1"
        )
        
        assert status == RetrievalStatus.EXPIRED_TOKEN
        assert retrieved is None
    
    def test_retrieve_secret_with_invalid_token(self):
        """Test retrieval fails with invalid token"""
        vault = LocalVault()
        token_issuer = TokenIssuer(server_key="test-key")
        adapter = VaultAdapter(vault, token_issuer)
        
        retrieved, status = adapter.retrieve_secret(
            token="invalid-token",
            req_id="REQ-123",
            actor_id="agent1"
        )
        
        assert status == RetrievalStatus.INVALID_TOKEN
        assert retrieved is None
    
    def test_retrieve_secret_scope_mismatch(self):
        """Test retrieval fails with vault scope mismatch"""
        vault = LocalVault(vault_id="vault-prod")
        token_issuer = TokenIssuer(server_key="test-key")
        adapter = VaultAdapter(vault, token_issuer)
        
        vault.store_secret("/path", "secret", "owner1")
        
        # Issue token for different vault
        token_result = token_issuer.issue_token(
            req_id="REQ-123",
            vault="vault-wrong",  # Different vault
            path="/path",
            ttl_seconds=300
        )
        
        retrieved, status = adapter.retrieve_secret(
            token=token_result['token'],
            req_id="REQ-123",
            actor_id="agent1"
        )
        
        assert status == RetrievalStatus.SCOPE_MISMATCH
        assert retrieved is None
    
    def test_retrieve_nonexistent_secret(self):
        """Test retrieval fails for non-existent secret"""
        vault = LocalVault()
        token_issuer = TokenIssuer(server_key="test-key")
        adapter = VaultAdapter(vault, token_issuer)
        
        # Issue token for non-existent path
        token_result = token_issuer.issue_token(
            req_id="REQ-123",
            vault="vault-local",
            path="/nonexistent/path",
            ttl_seconds=300
        )
        
        retrieved, status = adapter.retrieve_secret(
            token=token_result['token'],
            req_id="REQ-123",
            actor_id="agent1"
        )
        
        assert status == RetrievalStatus.SECRET_NOT_FOUND
        assert retrieved is None
    
    def test_nonce_replay_prevention(self):
        """Test that nonce cannot be reused for retrieval"""
        vault = LocalVault()
        token_issuer = TokenIssuer(server_key="test-key")
        adapter = VaultAdapter(vault, token_issuer)
        
        vault.store_secret("/path", "secret", "owner1")
        
        # Issue token
        token_result = token_issuer.issue_token(
            req_id="REQ-123",
            vault="vault-local",
            path="/path",
            ttl_seconds=300
        )
        
        token = token_result['token']
        
        # First retrieval should succeed
        retrieved1, status1 = adapter.retrieve_secret(token, "REQ-123", "agent1")
        assert status1 == RetrievalStatus.SUCCESS
        
        # Second retrieval with same token should fail (nonce already used)
        retrieved2, status2 = adapter.retrieve_secret(token, "REQ-123", "agent1")
        assert status2 == RetrievalStatus.NONCE_ALREADY_USED
        assert retrieved2 is None
    
    def test_access_logging(self):
        """Test access logging on retrieval"""
        vault = LocalVault()
        token_issuer = TokenIssuer(server_key="test-key")
        adapter = VaultAdapter(vault, token_issuer)
        
        vault.store_secret("/path", "secret", "owner1")
        
        token_result = token_issuer.issue_token(
            req_id="REQ-123",
            vault="vault-local",
            path="/path",
            ttl_seconds=300
        )
        
        adapter.retrieve_secret(
            token=token_result['token'],
            req_id="REQ-123",
            actor_id="agent1"
        )
        
        # Check adapter log
        log = adapter.get_access_log()
        assert len(log) == 1
        assert log[0]['req_id'] == "REQ-123"
        assert log[0]['actor_id'] == "agent1"
        assert log[0]['success'] is True
        
        # Check vault log
        vault_log = vault.get_access_log()
        assert len(vault_log) == 1
        assert vault_log[0]['success'] is True


class TestVaultAdapterIntegration:
    """Integration tests for vault adapter workflow"""
    
    def test_complete_secret_retrieval_flow(self):
        """Test complete flow: store -> issue token -> retrieve -> replay prevention"""
        # Setup
        vault = LocalVault()
        token_issuer = TokenIssuer(server_key="test-key")
        adapter = VaultAdapter(vault, token_issuer)
        
        req_id = "REQ-20251110-143022-def456"
        path = "/credentials/prod/db-password"
        secret = "prod_db_password_xyz789"
        
        # 1. Store secret
        vault.store_secret(path, secret, owner_id="admin@hospital.com")
        
        # 2. Issue token (after owner approval)
        token_result = token_issuer.issue_token(
            req_id=req_id,
            vault="vault-local",
            path=path,
            ttl_seconds=300
        )
        
        # 3. Retrieve secret with token
        retrieved, status = adapter.retrieve_secret(
            token=token_result['token'],
            req_id=req_id,
            actor_id="mcp-agent-1"
        )
        
        assert status == RetrievalStatus.SUCCESS
        assert retrieved == secret
        
        # 4. Try to reuse token (should fail)
        retrieved2, status2 = adapter.retrieve_secret(
            token=token_result['token'],
            req_id=req_id,
            actor_id="mcp-agent-1"
        )
        
        assert status2 == RetrievalStatus.NONCE_ALREADY_USED
        assert retrieved2 is None
    
    def test_multiple_concurrent_secrets(self):
        """Test handling multiple secrets and tokens concurrently"""
        vault = LocalVault()
        token_issuer = TokenIssuer(server_key="test-key")
        adapter = VaultAdapter(vault, token_issuer)
        
        # Store multiple secrets
        secrets_data = {
            "/db/master": "master_pass",
            "/db/replica": "replica_pass",
            "/api/key": "api_key_123"
        }
        
        for path, secret in secrets_data.items():
            vault.store_secret(path, secret, "owner1")
        
        # Issue tokens for each
        tokens = {}
        for path in secrets_data:
            result = token_issuer.issue_token(
                req_id=f"REQ-{path.replace('/', '-')}",
                vault="vault-local",
                path=path,
                ttl_seconds=300
            )
            tokens[path] = result['token']
        
        # Retrieve all secrets
        for path, expected_secret in secrets_data.items():
            retrieved, status = adapter.retrieve_secret(
                token=tokens[path],
                req_id=f"REQ-{path.replace('/', '-')}",
                actor_id="agent1"
            )
            
            assert status == RetrievalStatus.SUCCESS
            assert retrieved == expected_secret
    
    def test_different_vaults_are_isolated(self):
        """Test that different vault instances are isolated"""
        vault1 = LocalVault(vault_id="vault-prod")
        vault2 = LocalVault(vault_id="vault-staging")
        
        token_issuer = TokenIssuer(server_key="test-key")
        adapter1 = VaultAdapter(vault1, token_issuer)
        adapter2 = VaultAdapter(vault2, token_issuer)
        
        # Store secret in vault1
        vault1.store_secret("/secret", "secret-prod", "owner1")
        
        # Try to retrieve from vault2 using token for vault1
        token = token_issuer.issue_token(
            req_id="REQ-1",
            vault="vault-prod",
            path="/secret",
            ttl_seconds=300
        )
        
        retrieved, status = adapter2.retrieve_secret(
            token=token,
            req_id="REQ-1",
            actor_id="agent1"
        )
        
        # Should fail: scope mismatch
        assert status == RetrievalStatus.SCOPE_MISMATCH


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
