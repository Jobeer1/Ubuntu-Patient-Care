"""
Token Issuer Service

CRITICAL: Issues single-use tokens for credential retrieval.
Prevents replay attacks via nonce management.

This is Task 1.4 from the coordination plan.
"""

import secrets
import time
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, padding
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)


class TokenIssuer:
    """
    Issues and validates single-use retrieval tokens
    
    Features:
    - Ed25519 or RSA signatures
    - Single-use enforcement (nonce store)
    - TTL enforcement
    - Scope validation
    
    Token format:
    {
        "iss": "mcp-server",
        "aud": "mcp-agent",
        "req_id": "REQ-20251110-120000-abc123",
        "vault": "subnet-1",
        "path": "pacs/admin",
        "exp": 1699363200,
        "nonce": "random_32_byte_string",
        "created_ts": "2025-11-10T12:00:00Z"
    }
    """
    
    def __init__(self, private_key_path: Optional[str] = None):
        """
        Initialize token issuer
        
        Args:
            private_key_path: Path to server private key (Ed25519 or RSA)
        """
        self.private_key = None
        self.public_key = None
        self.nonce_store = NonceStore()
        
        if private_key_path:
            self._load_keys(private_key_path)
        else:
            # Generate ephemeral key for testing
            self._generate_ephemeral_key()
        
        logger.info("TokenIssuer initialized")
    
    def _generate_ephemeral_key(self):
        """Generate ephemeral Ed25519 key for testing"""
        self.private_key = ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        logger.warning("Using ephemeral key - NOT FOR PRODUCTION!")
    
    def _load_keys(self, private_key_path: str):
        """Load private key from file"""
        try:
            with open(private_key_path, 'rb') as f:
                key_data = f.read()
            
            # Try Ed25519 first
            try:
                self.private_key = serialization.load_pem_private_key(
                    key_data,
                    password=None,
                    backend=default_backend()
                )
                self.public_key = self.private_key.public_key()
                logger.info("Loaded Ed25519 private key")
            except:
                # Try RSA
                self.private_key = serialization.load_pem_private_key(
                    key_data,
                    password=None,
                    backend=default_backend()
                )
                self.public_key = self.private_key.public_key()
                logger.info("Loaded RSA private key")
                
        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
            raise
    
    def issue_token(
        self,
        req_id: str,
        vault: str,
        path: str,
        ttl_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        Issue single-use retrieval token
        
        Args:
            req_id: Credential request ID (e.g., "REQ-20251110-120000-abc123")
            vault: Vault ID where secret is stored
            path: Path to secret in vault
            ttl_seconds: Time-to-live in seconds (default: 300 = 5 minutes)
        
        Returns:
            {
                "token": "base64_encoded_signed_token",
                "nonce": "nonce_value",
                "expires_at": "2025-11-10T12:05:00Z"
            }
        
        Raises:
            ValueError: If parameters invalid
        """
        try:
            # Generate random nonce
            nonce = secrets.token_urlsafe(32)
            
            # Calculate expiration
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            exp_timestamp = int(expires_at.timestamp())
            
            # Create token claims
            token_claims = {
                "iss": "mcp-server",
                "aud": "mcp-agent",
                "req_id": req_id,
                "vault": vault,
                "path": path,
                "exp": exp_timestamp,
                "nonce": nonce,
                "created_ts": datetime.utcnow().isoformat() + "Z"
            }
            
            # Sign token
            token_json = json.dumps(token_claims, sort_keys=True)
            signature = self._sign(token_json.encode())
            
            # Combine token + signature
            token_with_sig = {
                "claims": token_claims,
                "signature": base64.b64encode(signature).decode()
            }
            
            # Encode as base64
            token_str = base64.b64encode(
                json.dumps(token_with_sig).encode()
            ).decode()
            
            # Store nonce
            self.nonce_store.add(nonce, req_id, expires_at)
            
            logger.info(f"Issued token for req_id={req_id}, vault={vault}")
            
            return {
                "token": token_str,
                "nonce": nonce,
                "expires_at": expires_at.isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Token issuance failed: {e}")
            raise
    
    def validate_token(self, token_str: str) -> bool:
        """
        Validate token: signature, TTL, nonce
        
        Args:
            token_str: Base64-encoded token
        
        Returns:
            True if valid
        
        Raises:
            ValueError: If token invalid
        """
        try:
            # Decode token
            token_json = base64.b64decode(token_str).decode()
            token_data = json.loads(token_json)
            
            claims = token_data["claims"]
            signature = base64.b64decode(token_data["signature"])
            
            # 1. Verify signature
            claims_json = json.dumps(claims, sort_keys=True)
            if not self._verify(claims_json.encode(), signature):
                logger.error("Token signature verification failed")
                return False
            
            # 2. Check TTL
            if time.time() > claims["exp"]:
                logger.error("Token expired")
                return False
            
            # 3. Check nonce (prevent replay)
            nonce = claims["nonce"]
            if self.nonce_store.is_used(nonce):
                logger.error(f"Token replay detected: {nonce}")
                return False
            
            # Mark nonce as used
            self.nonce_store.mark_used(nonce)
            
            logger.info(f"Token validated: req_id={claims['req_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return False
    
    def decode_token(self, token_str: str) -> Dict[str, Any]:
        """
        Decode token without validation (for inspection)
        
        Args:
            token_str: Base64-encoded token
        
        Returns:
            Token claims
        """
        try:
            token_json = base64.b64decode(token_str).decode()
            token_data = json.loads(token_json)
            return token_data["claims"]
        except Exception as e:
            logger.error(f"Token decode failed: {e}")
            raise ValueError("Invalid token format")
    
    def revoke_token(self, nonce: str):
        """
        Revoke token by marking nonce as used
        
        Args:
            nonce: Token nonce
        """
        self.nonce_store.mark_used(nonce)
        logger.info(f"Token revoked: {nonce}")
    
    def _sign(self, data: bytes) -> bytes:
        """Sign data with private key"""
        if isinstance(self.private_key, ed25519.Ed25519PrivateKey):
            return self.private_key.sign(data)
        elif isinstance(self.private_key, rsa.RSAPrivateKey):
            return self.private_key.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
        else:
            raise ValueError("Unsupported key type")
    
    def _verify(self, data: bytes, signature: bytes) -> bool:
        """Verify signature with public key"""
        try:
            if isinstance(self.public_key, ed25519.Ed25519PublicKey):
                self.public_key.verify(signature, data)
                return True
            elif isinstance(self.public_key, rsa.RSAPublicKey):
                self.public_key.verify(
                    signature,
                    data,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                return True
            else:
                return False
        except Exception:
            return False


class NonceStore:
    """
    In-memory nonce store (prevent token replay)
    
    In production, use database or Redis.
    """
    
    def __init__(self):
        """Initialize nonce store"""
        self.nonces = {}  # {nonce: {"req_id": ..., "expires_at": ..., "used": bool}}
        logger.info("NonceStore initialized (in-memory)")
    
    def add(self, nonce: str, req_id: str, expires_at: datetime):
        """Add nonce to store"""
        self.nonces[nonce] = {
            "req_id": req_id,
            "expires_at": expires_at,
            "used": False
        }
        logger.debug(f"Nonce added: {nonce[:8]}...")
    
    def is_used(self, nonce: str) -> bool:
        """Check if nonce has been used"""
        if nonce not in self.nonces:
            # Nonce not found - could be expired or invalid
            return True  # Treat as used (reject)
        
        nonce_data = self.nonces[nonce]
        
        # Check if expired
        if datetime.utcnow() > nonce_data["expires_at"]:
            return True  # Expired = used
        
        return nonce_data["used"]
    
    def mark_used(self, nonce: str):
        """Mark nonce as used"""
        if nonce in self.nonces:
            self.nonces[nonce]["used"] = True
            logger.debug(f"Nonce marked used: {nonce[:8]}...")
    
    def cleanup_expired(self):
        """Remove expired nonces (call periodically)"""
        now = datetime.utcnow()
        expired = [
            nonce for nonce, data in self.nonces.items()
            if now > data["expires_at"]
        ]
        
        for nonce in expired:
            del self.nonces[nonce]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired nonces")
