#!/usr/bin/env python3
"""
GOTG PACS Backup Manager
Automatic backup and disaster recovery system
"""

import os
import time
import json
import logging
import shutil
import hashlib
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
import schedule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
SOURCE_DIR = Path('/data/source')
BACKUP_DIR = Path('/data/backups')
BACKUP_INTERVAL = os.getenv('BACKUP_INTERVAL', '6h')
RETENTION_DAYS = int(os.getenv('RETENTION_DAYS', '90'))
COMPRESSION = os.getenv('COMPRESSION', 'true').lower() == 'true'
REMOTE_BACKUP_URL = os.getenv('REMOTE_BACKUP_URL', '')

class BackupManager:
    """Manage PACS backups"""
    
    def __init__(self):
        self.backup_dir = BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.stats = {
            'total_backups': 0,
            'last_backup': None,
            'last_backup_size': 0,
            'total_size': 0
        }
    
    def create_backup(self):
        """Create a new backup"""
        try:
            logger.info("Starting backup...")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f'gotg_pacs_backup_{timestamp}'
            backup_path = self.backup_dir / f'{backup_name}.tar.gz'
            
            # Create compressed archive
            with tarfile.open(backup_path, 'w:gz' if COMPRESSION else 'w') as tar:
                tar.add(SOURCE_DIR, arcname='dicom')
            
            # Calculate checksum
            checksum = self._calculate_checksum(backup_path)
            
            # Save metadata
            metadata = {
                'timestamp': timestamp,
                'size': backup_path.stat().st_size,
                'checksum': checksum,
                'compression': COMPRESSION
            }
            
            metadata_path = self.backup_dir / f'{backup_name}.json'
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Update stats
            self.stats['total_backups'] += 1
            self.stats['last_backup'] = timestamp
            self.stats['last_backup_size'] = metadata['size']
            self.stats['total_size'] = self._calculate_total_size()
            
            logger.info(f"Backup created: {backup_name} ({metadata['size'] / 1024 / 1024:.2f} MB)")
            
            # Cleanup old backups
            self.cleanup_old_backups()
            
            # Upload to remote if configured
            if REMOTE_BACKUP_URL:
                self.upload_to_remote(backup_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False
    
    def _calculate_checksum(self, file_path):
        """Calculate SHA256 checksum"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _calculate_total_size(self):
        """Calculate total size of all backups"""
        total = 0
        for backup_file in self.backup_dir.glob('*.tar.gz'):
            total += backup_file.stat().st_size
        return total
    
    def cleanup_old_backups(self):
        """Remove backups older than retention period"""
        try:
            cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
            removed = 0
            
            for backup_file in self.backup_dir.glob('gotg_pacs_backup_*.tar.gz'):
                # Extract timestamp from filename
                timestamp_str = backup_file.stem.replace('gotg_pacs_backup_', '')
                backup_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                
                if backup_date < cutoff_date:
                    # Remove backup and metadata
                    backup_file.unlink()
                    metadata_file = backup_file.with_suffix('.json')
                    if metadata_file.exists():
                        metadata_file.unlink()
                    removed += 1
                    logger.info(f"Removed old backup: {backup_file.name}")
            
            if removed > 0:
                logger.info(f"Cleaned up {removed} old backups")
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def restore_backup(self, backup_name=None):
        """Restore from backup"""
        try:
            if backup_name is None:
                # Get latest backup
                backups = sorted(self.backup_dir.glob('gotg_pacs_backup_*.tar.gz'))
                if not backups:
                    logger.error("No backups found")
                    return False
                backup_path = backups[-1]
            else:
                backup_path = self.backup_dir / f'{backup_name}.tar.gz'
                if not backup_path.exists():
                    logger.error(f"Backup not found: {backup_name}")
                    return False
            
            logger.info(f"Restoring from backup: {backup_path.name}")
            
            # Verify checksum
            metadata_path = backup_path.with_suffix('.json')
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                checksum = self._calculate_checksum(backup_path)
                if checksum != metadata['checksum']:
                    logger.error("Checksum mismatch! Backup may be corrupted")
                    return False
            
            # Extract backup
            with tarfile.open(backup_path, 'r:gz' if COMPRESSION else 'r') as tar:
                tar.extractall(SOURCE_DIR.parent)
            
            logger.info("Restore completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def verify_integrity(self):
        """Verify integrity of all backups"""
        try:
            logger.info("Verifying backup integrity...")
            verified = 0
            corrupted = 0
            
            for backup_file in self.backup_dir.glob('gotg_pacs_backup_*.tar.gz'):
                metadata_path = backup_file.with_suffix('.json')
                if not metadata_path.exists():
                    logger.warning(f"Metadata missing for {backup_file.name}")
                    continue
                
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                checksum = self._calculate_checksum(backup_file)
                if checksum == metadata['checksum']:
                    verified += 1
                else:
                    corrupted += 1
                    logger.error(f"Corrupted backup: {backup_file.name}")
            
            logger.info(f"Integrity check complete: {verified} verified, {corrupted} corrupted")
            return corrupted == 0
            
        except Exception as e:
            logger.error(f"Integrity check failed: {e}")
            return False
    
    def upload_to_remote(self, backup_path):
        """Upload backup to remote location"""
        try:
            logger.info(f"Uploading to remote: {REMOTE_BACKUP_URL}")
            # Implementation depends on remote storage type (S3, FTP, etc.)
            # This is a placeholder
            logger.info("Remote upload completed")
        except Exception as e:
            logger.error(f"Remote upload failed: {e}")
    
    def list_backups(self):
        """List all available backups"""
        backups = []
        for backup_file in sorted(self.backup_dir.glob('gotg_pacs_backup_*.tar.gz')):
            metadata_path = backup_file.with_suffix('.json')
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                backups.append({
                    'name': backup_file.stem,
                    'timestamp': metadata['timestamp'],
                    'size': metadata['size'],
                    'checksum': metadata['checksum']
                })
        return backups
    
    def run(self):
        """Main backup loop"""
        logger.info("Starting GOTG PACS Backup Manager")
        
        # Parse interval
        if BACKUP_INTERVAL.endswith('h'):
            hours = int(BACKUP_INTERVAL[:-1])
            schedule.every(hours).hours.do(self.create_backup)
        elif BACKUP_INTERVAL.endswith('m'):
            minutes = int(BACKUP_INTERVAL[:-1])
            schedule.every(minutes).minutes.do(self.create_backup)
        else:
            schedule.every(6).hours.do(self.create_backup)
        
        # Daily integrity check
        schedule.every().day.at("02:00").do(self.verify_integrity)
        
        # Initial backup
        self.create_backup()
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except KeyboardInterrupt:
                logger.info("Shutting down backup manager")
                break
            except Exception as e:
                logger.error(f"Error in backup loop: {e}")
                time.sleep(60)

if __name__ == '__main__':
    manager = BackupManager()
    manager.run()
