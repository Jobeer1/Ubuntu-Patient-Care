"""
Signature Service for Emergency Credential Approval

Provides Ed25519 digital signature operations for non-repudiable offline approval.

Functions:
- generate_key_pair() - Create new Ed25519 key pair
- load_private_key() - Load from PEM file (passphrase protected)
- save_private_key() - Save to PEM file with passphrase
- sign_message() - Create Ed25519 signature
- verify_signature() - Verify Ed25519 signature
"""

import os
import base64
from datetime import datetime
from typing import Tuple, Dict, Optional
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.backends import default_backend


class SignatureService:
    """
    Ed25519 signature operations for credential approvals.
    
    Usage:
        service = SignatureService()
        
        # Generate new key pair for owner
        private_key, public_key = service.generate_key_pair()
        service.save_private_key(private_key, "owner1.key", passphrase="secret")
        
        # Sign approval
        msg = "REQ-20251110-120000-abc123 | 2025-11-10T12:00:00Z"
        signature = service.sign_message(private_key, msg)
        
        # Verify signature
        is_valid = service.verify_signature(public_key, msg, signature)
    """
    
    @staticmethod
    def generate_key_pair() -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """
        Generate new Ed25519 key pair for owner.
        
        Returns:
            Tuple of (private_key, public_key)
        """
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        return private_key, public_key
    
    @staticmethod
    def save_private_key(private_key: ed25519.Ed25519PrivateKey, 
                         path: str, 
                         passphrase: str) -> None:
        """
        Save private key to PEM file with passphrase protection.
        
        Args:
            private_key: Ed25519 private key
            path: File path to save to
            passphrase: Password to encrypt the key
        """
        pem_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(
                passphrase.encode() if isinstance(passphrase, str) else passphrase
            )
        )
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(pem_bytes)
        
        # Restrict file permissions to owner only
        os.chmod(path, 0o600)
    
    @staticmethod
    def save_public_key(public_key: ed25519.Ed25519PublicKey, 
                        path: str) -> None:
        """
        Save public key to PEM file (unencrypted).
        
        Args:
            public_key: Ed25519 public key
            path: File path to save to
        """
        pem_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(pem_bytes)
    
    @staticmethod
    def load_private_key(path: str, 
                         passphrase: str) -> ed25519.Ed25519PrivateKey:
        """
        Load private key from PEM file.
        
        Args:
            path: File path to load from
            passphrase: Password to decrypt the key
            
        Returns:
            Ed25519 private key
            
        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If passphrase is incorrect
        """
        try:
            with open(path, 'rb') as f:
                pem_bytes = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Private key file not found: {path}")
        
        try:
            private_key = serialization.load_pem_private_key(
                pem_bytes,
                password=passphrase.encode() if isinstance(passphrase, str) else passphrase,
                backend=default_backend()
            )
            return private_key
        except ValueError as e:
            raise ValueError(f"Failed to load private key (wrong passphrase?): {str(e)}")
    
    @staticmethod
    def load_public_key(path: str) -> ed25519.Ed25519PublicKey:
        """
        Load public key from PEM file.
        
        Args:
            path: File path to load from
            
        Returns:
            Ed25519 public key
            
        Raises:
            FileNotFoundError: If file does not exist
        """
        try:
            with open(path, 'rb') as f:
                pem_bytes = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Public key file not found: {path}")
        
        public_key = serialization.load_pem_public_key(
            pem_bytes,
            backend=default_backend()
        )
        return public_key
    
    @staticmethod
    def sign_message(private_key: ed25519.Ed25519PrivateKey, 
                     message: str) -> str:
        """
        Create Ed25519 signature for message.
        
        Args:
            private_key: Ed25519 private key
            message: Message to sign
            
        Returns:
            Base64-encoded signature
        """
        message_bytes = message.encode('utf-8') if isinstance(message, str) else message
        signature_bytes = private_key.sign(message_bytes)
        return base64.b64encode(signature_bytes).decode('ascii')
    
    @staticmethod
    def verify_signature(public_key: ed25519.Ed25519PublicKey, 
                         message: str, 
                         signature_b64: str) -> bool:
        """
        Verify Ed25519 signature.
        
        Args:
            public_key: Ed25519 public key
            message: Original message
            signature_b64: Base64-encoded signature
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            message_bytes = message.encode('utf-8') if isinstance(message, str) else message
            signature_bytes = base64.b64decode(signature_b64)
            public_key.verify(signature_bytes, message_bytes)
            return True
        except Exception:
            return False


class ApprovalSignatureFactory:
    """
    Factory for creating and verifying approval signatures.
    
    Wraps the cryptographic operations with business logic for credential approvals.
    """
    
    def __init__(self, key_dir: str = "/etc/mcp-server/owner-keys"):
        """
        Initialize with key directory.
        
        Args:
            key_dir: Directory containing owner private keys
        """
        self.key_dir = key_dir
        self.signature_service = SignatureService()
    
    def sign_approval(self, 
                      req_id: str, 
                      approver_id: str, 
                      private_key_path: str,
                      passphrase: str,
                      ttl_seconds: int = 300) -> Dict[str, str]:
        """
        Create a signed approval for a credential request.
        
        Args:
            req_id: Credential request ID (e.g., "REQ-20251110-120000-abc123")
            approver_id: Owner ID (e.g., "owner1@hospital.com")
            private_key_path: Path to owner's private key
            passphrase: Passphrase to decrypt private key
            ttl_seconds: Token time-to-live in seconds
            
        Returns:
            Dict with signature and metadata:
            {
                "req_id": "REQ-20251110-120000-abc123",
                "approver": "owner1@hospital.com",
                "approved_ts": "2025-11-10T12:00:00Z",
                "signature": "base64-encoded-signature",
                "ttl_seconds": 300
            }
            
        Raises:
            FileNotFoundError: If private key file not found
            ValueError: If passphrase is incorrect
        """
        # Load private key
        try:
            private_key = self.signature_service.load_private_key(
                private_key_path, 
                passphrase
            )
        except (FileNotFoundError, ValueError) as e:
            raise ValueError(f"Failed to load private key: {str(e)}")
        
        # Create message to sign: req_id | approved_ts
        approved_ts = datetime.utcnow().isoformat() + "Z"
        message = f"{req_id} | {approved_ts}"
        
        # Sign the message
        signature = self.signature_service.sign_message(private_key, message)
        
        # Return approval dict
        return {
            "req_id": req_id,
            "approver": approver_id,
            "approved_ts": approved_ts,
            "signature": signature,
            "ttl_seconds": ttl_seconds
        }
    
    def verify_approval(self, 
                        approval: Dict[str, str], 
                        public_key_path: str) -> bool:
        """
        Verify a signed approval.
        
        Args:
            approval: Approval dict with signature
            public_key_path: Path to owner's public key
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            public_key = self.signature_service.load_public_key(public_key_path)
        except FileNotFoundError:
            return False
        
        # Reconstruct message
        message = f"{approval['req_id']} | {approval['approved_ts']}"
        
        # Verify signature
        return self.signature_service.verify_signature(
            public_key,
            message,
            approval['signature']
        )
