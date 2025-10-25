#!/usr/bin/env python3
"""
Secure Audio File Handler for Medical STT System
Handles encrypted storage, secure deletion, and POPIA compliance
"""

import os
import tempfile
import secrets
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger(__name__)

class SecureAudioHandler:
    """Secure audio file management with encryption and automatic cleanup"""
    
    def __init__(self, storage_dir="temp/secure_audio"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Audio retention policy (POPIA compliance)
        self.retention_hours = 24  # Keep audio files for max 24 hours
        self.cleanup_interval = timedelta(hours=1)  # Run cleanup every hour
        
        # Encryption key derivation
        self.master_key = self._get_or_create_master_key()
    
    def _get_or_create_master_key(self):
        """Get or create master encryption key"""
        key_file = self.storage_dir / ".master_key"
        
        if key_file.exists():
            try:
                with open(key_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to read master key: {e}")
        
        # Create new master key
        master_key = secrets.token_bytes(32)
        try:
            with open(key_file, 'wb') as f:
                f.write(master_key)
            
            # Secure file permissions (owner read/write only)
            os.chmod(key_file, 0o600)
            logger.info("Created new master encryption key")
            
        except Exception as e:
            logger.error(f"Failed to create master key: {e}")
            # Use in-memory key as fallback
        
        return master_key
    
    def _derive_file_key(self, user_id, file_id):
        """Derive file-specific encryption key"""
        salt = f"{user_id}:{file_id}".encode('utf-8')
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return Fernet(key)
    
    def store_audio_securely(self, audio_data, user_id, purpose="training"):
        """Store audio data with encryption and metadata"""
        try:
            # Generate unique file ID
            file_id = f"{purpose}_{secrets.token_hex(16)}"
            timestamp = datetime.utcnow()
            
            # Create file-specific encryption key
            cipher = self._derive_file_key(user_id, file_id)
            
            # Encrypt audio data
            if isinstance(audio_data, str):
                # If it's a file path, read the file
                with open(audio_data, 'rb') as f:
                    raw_data = f.read()
            else:
                # If it's bytes, use directly
                raw_data = audio_data
            
            encrypted_data = cipher.encrypt(raw_data)
            
            # Create secure file path
            user_dir = self.storage_dir / user_id
            user_dir.mkdir(exist_ok=True)
            
            encrypted_file = user_dir / f"{file_id}.enc"
            metadata_file = user_dir / f"{file_id}.meta"
            
            # Store encrypted audio
            with open(encrypted_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Store metadata
            metadata = {
                'file_id': file_id,
                'user_id': user_id,
                'purpose': purpose,
                'created_at': timestamp.isoformat(),
                'expires_at': (timestamp + timedelta(hours=self.retention_hours)).isoformat(),
                'file_size': len(raw_data),
                'encrypted_size': len(encrypted_data)
            }
            
            import json
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f)
            
            # Secure file permissions
            os.chmod(encrypted_file, 0o600)
            os.chmod(metadata_file, 0o600)
            
            logger.info(f"Stored encrypted audio: {file_id} for user {user_id}")
            
            return {
                'file_id': file_id,
                'encrypted_path': str(encrypted_file),
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to store audio securely: {e}")
            return None
    
    def retrieve_audio_securely(self, file_id, user_id):
        """Retrieve and decrypt audio data"""
        try:
            user_dir = self.storage_dir / user_id
            encrypted_file = user_dir / f"{file_id}.enc"
            metadata_file = user_dir / f"{file_id}.meta"
            
            if not encrypted_file.exists() or not metadata_file.exists():
                logger.warning(f"Audio file not found: {file_id}")
                return None
            
            # Load metadata
            import json
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Check expiration
            expires_at = datetime.fromisoformat(metadata['expires_at'])
            if datetime.utcnow() > expires_at:
                logger.info(f"Audio file expired, cleaning up: {file_id}")
                self._secure_delete_file(encrypted_file)
                self._secure_delete_file(metadata_file)
                return None
            
            # Decrypt audio data
            cipher = self._derive_file_key(user_id, file_id)
            
            with open(encrypted_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = cipher.decrypt(encrypted_data)
            
            logger.info(f"Retrieved encrypted audio: {file_id}")
            return {
                'data': decrypted_data,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve audio: {e}")
            return None
    
    def create_temp_audio_file(self, audio_data, user_id, suffix='.wav'):
        """Create temporary decrypted audio file for processing"""
        try:
            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=f"audio_{user_id}_")
            
            with os.fdopen(temp_fd, 'wb') as f:
                if isinstance(audio_data, str):
                    # If it's a file path, copy the file
                    with open(audio_data, 'rb') as src:
                        f.write(src.read())
                else:
                    # If it's bytes, write directly
                    f.write(audio_data)
            
            # Secure file permissions
            os.chmod(temp_path, 0o600)
            
            return temp_path
            
        except Exception as e:
            logger.error(f"Failed to create temp audio file: {e}")
            return None
    
    def _secure_delete_file(self, file_path):
        """Securely delete file by overwriting with random data"""
        try:
            if not os.path.exists(file_path):
                return
            
            file_size = os.path.getsize(file_path)
            
            # Overwrite with random data multiple times
            with open(file_path, 'r+b') as f:
                for _ in range(3):  # 3 passes of random data
                    f.seek(0)
                    f.write(secrets.token_bytes(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            # Finally delete the file
            os.unlink(file_path)
            logger.debug(f"Securely deleted file: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to securely delete file {file_path}: {e}")
    
    def cleanup_expired_files(self):
        """Clean up expired audio files (POPIA compliance)"""
        try:
            cleanup_count = 0
            current_time = datetime.utcnow()
            
            for user_dir in self.storage_dir.iterdir():
                if not user_dir.is_dir():
                    continue
                
                for metadata_file in user_dir.glob("*.meta"):
                    try:
                        import json
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        
                        expires_at = datetime.fromisoformat(metadata['expires_at'])
                        if current_time > expires_at:
                            # File has expired, delete it
                            file_id = metadata['file_id']
                            encrypted_file = user_dir / f"{file_id}.enc"
                            
                            self._secure_delete_file(encrypted_file)
                            self._secure_delete_file(metadata_file)
                            
                            cleanup_count += 1
                            logger.info(f"Cleaned up expired audio: {file_id}")
                    
                    except Exception as e:
                        logger.error(f"Error processing metadata file {metadata_file}: {e}")
            
            logger.info(f"Audio cleanup completed: {cleanup_count} files removed")
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Audio cleanup failed: {e}")
            return 0
    
    def get_user_audio_stats(self, user_id):
        """Get audio storage statistics for user"""
        try:
            user_dir = self.storage_dir / user_id
            if not user_dir.exists():
                return {
                    'total_files': 0,
                    'total_size': 0,
                    'expired_files': 0
                }
            
            total_files = 0
            total_size = 0
            expired_files = 0
            current_time = datetime.utcnow()
            
            for metadata_file in user_dir.glob("*.meta"):
                try:
                    import json
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    total_files += 1
                    total_size += metadata.get('file_size', 0)
                    
                    expires_at = datetime.fromisoformat(metadata['expires_at'])
                    if current_time > expires_at:
                        expired_files += 1
                
                except Exception as e:
                    logger.error(f"Error reading metadata {metadata_file}: {e}")
            
            return {
                'total_files': total_files,
                'total_size': total_size,
                'expired_files': expired_files
            }
            
        except Exception as e:
            logger.error(f"Failed to get audio stats: {e}")
            return {'total_files': 0, 'total_size': 0, 'expired_files': 0}
    
    def delete_user_audio_data(self, user_id):
        """Delete all audio data for a user (POPIA right to erasure)"""
        try:
            user_dir = self.storage_dir / user_id
            if not user_dir.exists():
                return True
            
            deleted_count = 0
            
            # Delete all encrypted files and metadata
            for file_path in user_dir.iterdir():
                self._secure_delete_file(file_path)
                deleted_count += 1
            
            # Remove user directory
            user_dir.rmdir()
            
            logger.info(f"Deleted all audio data for user {user_id}: {deleted_count} files")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete user audio data: {e}")
            return False

# Global instance
secure_audio_handler = SecureAudioHandler()

def store_training_audio(audio_data, user_id):
    """Convenience function to store training audio"""
    return secure_audio_handler.store_audio_securely(audio_data, user_id, "training")

def store_shortcut_audio(audio_data, user_id):
    """Convenience function to store shortcut audio"""
    return secure_audio_handler.store_audio_securely(audio_data, user_id, "shortcut")

def retrieve_audio(file_id, user_id):
    """Convenience function to retrieve audio"""
    return secure_audio_handler.retrieve_audio_securely(file_id, user_id)

def cleanup_expired_audio():
    """Convenience function for cleanup"""
    return secure_audio_handler.cleanup_expired_files()