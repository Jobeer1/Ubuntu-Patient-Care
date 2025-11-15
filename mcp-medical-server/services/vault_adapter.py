"""
Vault Adapter

CRITICAL: Retrieves secrets from vault after token validation.
This is Task 1.5 from the coordination plan.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from services.token_issuer import TokenIssuer
from services.local_vault import LocalVault
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class VaultAdapter:
    """
    Vault adapter for secure secret retrieval
    
    Features:
    - Token validation before retrieval
    - Single-use token enforcement
    - Merkle-stamped audit trail
    - Scope validation
    - Error handling
    
    Flow:
    1. Validate token (signature, TTL, nonce)
    2. Check token scope matches request
    3. Retrieve secret from vault
    4. Merkle-stamp retrieval
    5. Invalidate token (mark nonce used)
    6. Return secret + proof
    """
    
    def __init__(
        self,
        vault: Optional[LocalVault] = None,
        token_issuer: Optional[TokenIssuer] = None
    ):
        """
        Initialize vault adapter
        
        Args:
            vault: LocalVault instance (or None for default)
            token_issuer: TokenIssuer instance (or None for default)
        """
        self.vault = vault or LocalVault()
        self.token_issuer = token_issuer or TokenIssuer()
        self.audit = AuditService()
        
        logger.info("VaultAdapter initialized")
    
    def retrieve_secret(
        self,
        token: str,
        vault_id: str
    ) -> Dict[str, Any]:
        """
        Retrieve secret after validating token
        
        Args:
            token: Single-use retrieval token
            vault_id: Vault ID (must match token scope)
        
        Returns:
            {
                "secret": "decrypted_secret_value",
                "merkle_proof": {...},
                "retrieved_at": "2025-11-10T12:00:00Z"
            }
        
        Raises:
            InvalidTokenError: If token invalid
            UnauthorizedError: If scope mismatch
            SecretNotFoundError: If secret doesn't exist
        """
        try:
            # 1. Validate token
            if not self.token_issuer.validate_token(token):
                raise InvalidTokenError("Token validation failed")
            
            # 2. Decode token to get claims
            token_data = self.token_issuer.decode_token(token)
            
            # 3. Check token scope matches request
            if token_data['vault'] != vault_id:
                logger.error(
                    f"Scope mismatch: token vault={token_data['vault']}, "
                    f"requested vault={vault_id}"
                )
                raise UnauthorizedError("Token scope does not match request")
            
            # 4. Retrieve secret from vault
            path = token_data['path']
            secret = self.vault.get_secret(vault_id, path)
            
            if secret is None:
                raise SecretNotFoundError(f"Secret not found: {vault_id}/{path}")
            
            # 5. Merkle-stamp retrieval
            merkle_proof = self.audit.record_event(
                event_type="CREDENTIAL_RETRIEVED",
                data={
                    "req_id": token_data['req_id'],
                    "vault_id": vault_id,
                    "path": path,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            )
            
            # 6. Invalidate token (already marked used by validate_token)
            # But explicitly revoke to be safe
            self.token_issuer.revoke_token(token_data['nonce'])
            
            logger.info(
                f"Secret retrieved: vault={vault_id}, path={path}, "
                f"req_id={token_data['req_id']}"
            )
            
            return {
                "secret": secret,
                "merkle_proof": merkle_proof,
                "retrieved_at": datetime.utcnow().isoformat() + "Z"
            }
            
        except (InvalidTokenError, UnauthorizedError, SecretNotFoundError):
            raise
        except Exception as e:
            logger.error(f"Secret retrieval failed: {e}")
            raise RetrievalError(f"Failed to retrieve secret: {e}")
    
    def store_secret(
        self,
        vault_id: str,
        path: str,
        secret: str,
        owner_id: str,
        cache_allowed: bool = False,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Store secret in vault
        
        Args:
            vault_id: Vault ID
            path: Path in vault
            secret: Secret value (will be encrypted)
            owner_id: Owner who can access this secret
            cache_allowed: Whether caching is allowed
            ttl_seconds: Optional TTL for secret
        
        Returns:
            True if successful
        """
        try:
            success = self.vault.store_secret(
                vault_id=vault_id,
                path=path,
                secret=secret,
                owner_id=owner_id,
                cache_allowed=cache_allowed,
                ttl_seconds=ttl_seconds
            )
            
            if success:
                # Merkle-stamp storage
                self.audit.record_event(
                    event_type="SECRET_STORED",
                    data={
                        "vault_id": vault_id,
                        "path": path,
                        "owner_id": owner_id,
                        "cache_allowed": cache_allowed,
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                )
                
                logger.info(f"Secret stored: vault={vault_id}, path={path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Secret storage failed: {e}")
            return False
    
    def list_secrets(self, vault_id: str) -> list:
        """
        List secrets in vault
        
        Args:
            vault_id: Vault ID
        
        Returns:
            List of secret paths
        """
        try:
            return self.vault.list_secrets(vault_id)
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []
    
    def delete_secret(self, vault_id: str, path: str) -> bool:
        """
        Delete secret from vault
        
        Args:
            vault_id: Vault ID
            path: Path in vault
        
        Returns:
            True if successful
        """
        try:
            success = self.vault.delete_secret(vault_id, path)
            
            if success:
                # Merkle-stamp deletion
                self.audit.record_event(
                    event_type="SECRET_DELETED",
                    data={
                        "vault_id": vault_id,
                        "path": path,
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                )
                
                logger.info(f"Secret deleted: vault={vault_id}, path={path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Secret deletion failed: {e}")
            return False


# Custom exceptions
class InvalidTokenError(Exception):
    """Token validation failed"""
    pass


class UnauthorizedError(Exception):
    """Token scope does not match request"""
    pass


class SecretNotFoundError(Exception):
    """Secret not found in vault"""
    pass


class RetrievalError(Exception):
    """General retrieval error"""
    pass
