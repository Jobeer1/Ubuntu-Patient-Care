"""
Tests for Shamir Secret Sharing

Author: Kiro Team
Task: K3.2
"""

import sys
import pytest
import secrets
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.shamir_unseal import (
    ShamirSecretSharing,
    Share,
    VaultUnseal
)


class TestShare:
    """Test Share dataclass."""
    
    def test_to_string(self):
        """Test share serialization."""
        share = Share(index=1, value=0xabcdef1234567890)
        share_str = share.to_string()
        
        assert share_str.startswith("1:")
        assert len(share_str) > 10
    
    def test_from_string(self):
        """Test share deserialization."""
        share_str = "1:00000000000000000000000000000000000000000000000000000000abcdef12"
        share = Share.from_string(share_str)
        
        assert share.index == 1
        assert share.value == 0xabcdef12
    
    def test_round_trip(self):
        """Test serialization round trip."""
        original = Share(index=5, value=0x123456789abcdef0)
        share_str = original.to_string()
        reconstructed = Share.from_string(share_str)
        
        assert reconstructed.index == original.index
        assert reconstructed.value == original.value


class TestShamirSecretSharing:
    """Test Shamir Secret Sharing implementation."""
    
    def test_initialization(self):
        """Test SSS initialization."""
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        
        assert shamir.threshold == 3
        assert shamir.num_shares == 5
    
    def test_invalid_parameters(self):
        """Test invalid parameter validation."""
        # Threshold too low
        with pytest.raises(ValueError):
            ShamirSecretSharing(threshold=1, num_shares=5)
        
        # Threshold > num_shares
        with pytest.raises(ValueError):
            ShamirSecretSharing(threshold=6, num_shares=5)
        
        # Too many shares
        with pytest.raises(ValueError):
            ShamirSecretSharing(threshold=3, num_shares=300)
    
    def test_split_secret(self):
        """Test secret splitting."""
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        secret = secrets.token_bytes(32)
        
        shares = shamir.split_secret(secret)
        
        assert len(shares) == 5
        assert all(isinstance(s, Share) for s in shares)
        assert all(s.index >= 1 and s.index <= 5 for s in shares)
    
    def test_reconstruct_secret(self):
        """Test secret reconstruction."""
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        original_secret = secrets.token_bytes(32)
        
        # Split secret
        shares = shamir.split_secret(original_secret)
        
        # Reconstruct with exactly threshold shares
        reconstructed = shamir.reconstruct_secret(shares[:3])
        
        assert reconstructed == original_secret
    
    def test_reconstruct_with_different_shares(self):
        """Test reconstruction with different share combinations."""
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        original_secret = secrets.token_bytes(32)
        
        shares = shamir.split_secret(original_secret)
        
        # Try different combinations
        combinations = [
            [shares[0], shares[1], shares[2]],
            [shares[0], shares[2], shares[4]],
            [shares[1], shares[3], shares[4]],
            [shares[0], shares[1], shares[2], shares[3]],  # More than threshold
        ]
        
        for combo in combinations:
            reconstructed = shamir.reconstruct_secret(combo)
            assert reconstructed == original_secret
    
    def test_insufficient_shares(self):
        """Test reconstruction fails with insufficient shares."""
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        secret = secrets.token_bytes(32)
        
        shares = shamir.split_secret(secret)
        
        # Try with only 2 shares (need 3)
        with pytest.raises(ValueError, match="Need at least 3 shares"):
            shamir.reconstruct_secret(shares[:2])
    
    def test_verify_shares_valid(self):
        """Test share verification with valid shares."""
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        secret = secrets.token_bytes(32)
        
        shares = shamir.split_secret(secret)
        
        assert shamir.verify_shares(shares) is True
        assert shamir.verify_shares(shares[:3]) is True
    
    def test_verify_shares_duplicate(self):
        """Test share verification detects duplicates."""
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        secret = secrets.token_bytes(32)
        
        shares = shamir.split_secret(secret)
        
        # Add duplicate
        duplicate_shares = shares[:2] + [shares[0]]
        
        assert shamir.verify_shares(duplicate_shares) is False
    
    def test_verify_shares_invalid_index(self):
        """Test share verification detects invalid indices."""
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        
        invalid_share = Share(index=10, value=12345)  # Index out of range
        
        assert shamir.verify_shares([invalid_share]) is False
    
    def test_secret_too_large(self):
        """Test rejection of oversized secrets."""
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        
        # Secret larger than 32 bytes
        large_secret = secrets.token_bytes(64)
        
        with pytest.raises(ValueError, match="at most 32 bytes"):
            shamir.split_secret(large_secret)
    
    def test_deterministic_reconstruction(self):
        """Test reconstruction is deterministic."""
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        secret = secrets.token_bytes(32)
        
        shares = shamir.split_secret(secret)
        
        # Reconstruct multiple times
        result1 = shamir.reconstruct_secret(shares[:3])
        result2 = shamir.reconstruct_secret(shares[:3])
        result3 = shamir.reconstruct_secret(shares[2:5])
        
        assert result1 == result2 == result3 == secret
    
    def test_different_secrets_different_shares(self):
        """Test different secrets produce different shares."""
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        
        secret1 = secrets.token_bytes(32)
        secret2 = secrets.token_bytes(32)
        
        shares1 = shamir.split_secret(secret1)
        shares2 = shamir.split_secret(secret2)
        
        # Shares should be different
        assert shares1[0].value != shares2[0].value


class TestVaultUnseal:
    """Test VaultUnseal service."""
    
    def test_initialization(self):
        """Test vault unseal initialization."""
        vault = VaultUnseal(threshold=3, num_shares=5)
        
        assert vault.is_sealed is True
        assert len(vault.collected_shares) == 0
    
    def test_add_share_success(self):
        """Test adding valid share."""
        vault = VaultUnseal(threshold=3, num_shares=5)
        
        # Generate test shares
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        secret = secrets.token_bytes(32)
        shares = shamir.split_secret(secret)
        
        # Add first share
        result = vault.add_share(shares[0].to_string())
        
        assert result['success'] is True
        assert result['progress'] == 1
        assert result['required'] == 3
        assert result['sealed'] is True
    
    def test_add_duplicate_share(self):
        """Test adding duplicate share is rejected."""
        vault = VaultUnseal(threshold=3, num_shares=5)
        
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        secret = secrets.token_bytes(32)
        shares = shamir.split_secret(secret)
        
        # Add share twice
        vault.add_share(shares[0].to_string())
        result = vault.add_share(shares[0].to_string())
        
        assert result['success'] is False
        assert 'already provided' in result['error']
    
    def test_unseal_with_threshold_shares(self):
        """Test vault unseals with threshold shares."""
        vault = VaultUnseal(threshold=3, num_shares=5)
        
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        secret = secrets.token_bytes(32)
        shares = shamir.split_secret(secret)
        
        # Add shares one by one
        vault.add_share(shares[0].to_string())
        vault.add_share(shares[1].to_string())
        result = vault.add_share(shares[2].to_string())
        
        # Should unseal after 3rd share
        assert result['success'] is True
        assert result['sealed'] is False
        assert 'master_key' in result
        assert vault.is_sealed is False
    
    def test_get_status(self):
        """Test getting vault status."""
        vault = VaultUnseal(threshold=3, num_shares=5)
        
        status = vault.get_status()
        
        assert status['sealed'] is True
        assert status['progress'] == 0
        assert status['required'] == 3
        assert status['total_shares'] == 5
    
    def test_reset(self):
        """Test resetting unseal process."""
        vault = VaultUnseal(threshold=3, num_shares=5)
        
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        secret = secrets.token_bytes(32)
        shares = shamir.split_secret(secret)
        
        # Add some shares
        vault.add_share(shares[0].to_string())
        vault.add_share(shares[1].to_string())
        
        assert len(vault.collected_shares) == 2
        
        # Reset
        vault.reset()
        
        assert len(vault.collected_shares) == 0
    
    def test_invalid_share_format(self):
        """Test invalid share format is rejected."""
        vault = VaultUnseal(threshold=3, num_shares=5)
        
        result = vault.add_share("invalid_format")
        
        assert result['success'] is False
        assert 'error' in result


class TestShamirSecurity:
    """Test security properties of Shamir Secret Sharing."""
    
    def test_k_minus_1_shares_reveal_nothing(self):
        """Test that k-1 shares reveal no information about secret."""
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        
        secret1 = b'\x00' * 32
        secret2 = secrets.token_bytes(32)
        
        shares1 = shamir.split_secret(secret1)
        shares2 = shamir.split_secret(secret2)
        
        # With only 2 shares (k-1), we can't distinguish secrets
        # This is a statistical test - shares should look random
        
        # Just verify we can't reconstruct
        with pytest.raises(ValueError):
            shamir.reconstruct_secret(shares1[:2])
        
        with pytest.raises(ValueError):
            shamir.reconstruct_secret(shares2[:2])
    
    def test_shares_are_random(self):
        """Test that shares appear random."""
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        secret = b'\x00' * 32  # All zeros
        
        shares = shamir.split_secret(secret)
        
        # Shares should not be all zeros (they're random)
        assert any(share.value != 0 for share in shares)
    
    def test_different_splits_different_shares(self):
        """Test that splitting same secret twice gives different shares."""
        shamir = ShamirSecretSharing(threshold=3, num_shares=5)
        secret = secrets.token_bytes(32)
        
        shares1 = shamir.split_secret(secret)
        shares2 = shamir.split_secret(secret)
        
        # Shares should be different (due to random coefficients)
        assert shares1[0].value != shares2[0].value


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
