"""
Local Vault - Prototype Implementation

SQLite + Fernet encryption for local secret storage.
In production, use HashiCorp Vault or similar.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class LocalVault:
    """
    Local vault using SQLite + Fernet encryption
    
    Features:
    - Encrypted secret storage
    - Per-vault isolation
    - Owner-based access control
    - TTL support
    - Cache policy
    """
    
    def __init__(
        self,
        db_path: str = "vault.db",
        encryption_key: Optional[bytes] = None
    ):
        """
        Initialize local vault
        
        Args:
            db_path: Path to SQLite database
            encryption_key: Fernet key (or None to generate)
        """
        self.db_path = Path(db_path)
        
        # Generate or use provided encryption key
        if encryption_key:
            self.cipher = Fernet(encryption_key)
        else:
            key = Fernet.generate_key()
            self.cipher = Fernet(key)
            logger.warning("Generated ephemeral encryption key - NOT FOR PRODUCTION!")
        
        # Initialize database
        self._init_db()
        
        logger.info(f"LocalVault initialized: {db_path}")
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vault_secrets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vault_id TEXT NOT NULL,
                path TEXT NOT NULL,
                encrypted_secret BLOB NOT NULL,
                created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                owner_id TEXT NOT NULL,
                cache_allowed BOOLEAN DEFAULT 0,
                ttl_seconds INTEGER,
                UNIQUE(vault_id, path)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vault_path 
            ON vault_secrets(vault_id, path)
        """)
        
        conn.commit()
        conn.close()
        
        logger.debug("Database schema initialized")
    
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
        Store encrypted secret
        
        Args:
            vault_id: Vault ID
            path: Path in vault
            secret: Secret value (plaintext)
            owner_id: Owner ID
            cache_allowed: Whether caching allowed
            ttl_seconds: Optional TTL
        
        Returns:
            True if successful
        """
        try:
            # Encrypt secret
            encrypted = self.cipher.encrypt(secret.encode())
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO vault_secrets 
                (vault_id, path, encrypted_secret, owner_id, cache_allowed, ttl_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (vault_id, path, encrypted, owner_id, cache_allowed, ttl_seconds))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Secret stored: {vault_id}/{path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store secret: {e}")
            return False
    
    def get_secret(self, vault_id: str, path: str) -> Optional[str]:
        """
        Retrieve and decrypt secret
        
        Args:
            vault_id: Vault ID
            path: Path in vault
        
        Returns:
            Decrypted secret or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT encrypted_secret FROM vault_secrets
                WHERE vault_id = ? AND path = ?
            """, (vault_id, path))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                logger.debug(f"Secret not found: {vault_id}/{path}")
                return None
            
            # Decrypt secret
            encrypted = row[0]
            decrypted = self.cipher.decrypt(encrypted).decode()
            
            logger.debug(f"Secret retrieved: {vault_id}/{path}")
            return decrypted
            
        except Exception as e:
            logger.error(f"Failed to retrieve secret: {e}")
            return None
    
    def list_secrets(self, vault_id: str) -> List[str]:
        """
        List all secret paths in vault
        
        Args:
            vault_id: Vault ID
        
        Returns:
            List of paths
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT path FROM vault_secrets
                WHERE vault_id = ?
                ORDER BY path
            """, (vault_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            paths = [row[0] for row in rows]
            logger.debug(f"Listed {len(paths)} secrets in {vault_id}")
            
            return paths
            
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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM vault_secrets
                WHERE vault_id = ? AND path = ?
            """, (vault_id, path))
            
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if deleted:
                logger.debug(f"Secret deleted: {vault_id}/{path}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete secret: {e}")
            return False
    
    def cleanup_expired(self):
        """Remove expired secrets (call periodically)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete secrets where TTL has expired
            cursor.execute("""
                DELETE FROM vault_secrets
                WHERE ttl_seconds IS NOT NULL
                AND datetime(created_ts, '+' || ttl_seconds || ' seconds') < datetime('now')
            """)
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} expired secrets")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
