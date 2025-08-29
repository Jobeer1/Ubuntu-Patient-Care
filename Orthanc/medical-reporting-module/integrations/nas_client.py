"""
NAS storage integration client
"""

import os
import shutil
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import hashlib
from config.integration_config import IntegrationConfig

logger = logging.getLogger(__name__)

class NASClient:
    """Client for NAS storage integration"""
    
    def __init__(self):
        self.config = IntegrationConfig.NAS_CONFIG
        self.mount_point = Path(self.config['mount_point'])
        self.backup_enabled = self.config['backup_enabled']
        self.backup_path = Path(self.config['backup_path'])
        self.connection_timeout = self.config['connection_timeout']
        self.read_timeout = self.config['read_timeout']
        self.write_timeout = self.config['write_timeout']
        
        # Create backup directory if it doesn't exist
        if self.backup_enabled:
            self.backup_path.mkdir(parents=True, exist_ok=True)
    
    def check_connectivity(self) -> bool:
        """Check if NAS is accessible"""
        try:
            if not self.mount_point.exists():
                logger.error(f"NAS mount point does not exist: {self.mount_point}")
                return False
            
            if not self.mount_point.is_dir():
                logger.error(f"NAS mount point is not a directory: {self.mount_point}")
                return False
            
            # Try to create a test file
            test_file = self.mount_point / '.connectivity_test'
            try:
                test_file.write_text(f"Test at {datetime.utcnow().isoformat()}")
                test_file.unlink()  # Delete test file
                logger.info("NAS connectivity check successful")
                return True
            except Exception as e:
                logger.error(f"NAS write test failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"NAS connectivity check failed: {e}")
            return False
    
    def store_report(self, report_id: str, report_data: Dict[str, Any]) -> bool:
        """Store report data to NAS"""
        try:
            if not self.backup_enabled:
                logger.info("NAS backup is disabled")
                return True
            
            # Create report directory structure
            report_dir = self.backup_path / 'reports' / report_id[:2] / report_id
            report_dir.mkdir(parents=True, exist_ok=True)
            
            # Store report metadata
            metadata_file = report_dir / 'metadata.json'
            import json
            with open(metadata_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            logger.info(f"Report {report_id} stored to NAS")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store report to NAS: {e}")
            return False
    
    def store_voice_recording(self, session_id: str, audio_file_path: str) -> Optional[str]:
        """Store voice recording to NAS"""
        try:
            if not self.backup_enabled:
                return audio_file_path  # Return original path if backup disabled
            
            source_path = Path(audio_file_path)
            if not source_path.exists():
                logger.error(f"Source audio file does not exist: {audio_file_path}")
                return None
            
            # Create voice recordings directory structure
            voice_dir = self.backup_path / 'voice_recordings' / session_id[:2] / session_id
            voice_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy audio file to NAS
            nas_audio_path = voice_dir / source_path.name
            shutil.copy2(source_path, nas_audio_path)
            
            # Create checksum for integrity verification
            checksum = self._calculate_checksum(nas_audio_path)
            checksum_file = voice_dir / f"{source_path.stem}.checksum"
            checksum_file.write_text(checksum)
            
            logger.info(f"Voice recording {session_id} stored to NAS")
            return str(nas_audio_path)
            
        except Exception as e:
            logger.error(f"Failed to store voice recording to NAS: {e}")
            return None
    
    def store_dicom_cache(self, study_id: str, cache_data: bytes) -> bool:
        """Store DICOM cache data to NAS"""
        try:
            if not self.backup_enabled:
                return True
            
            # Create DICOM cache directory
            cache_dir = self.backup_path / 'dicom_cache' / study_id[:2] / study_id
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Store cache data
            cache_file = cache_dir / 'cache.dat'
            cache_file.write_bytes(cache_data)
            
            # Store metadata
            metadata = {
                'study_id': study_id,
                'cached_at': datetime.utcnow().isoformat(),
                'size_bytes': len(cache_data),
                'checksum': self._calculate_checksum_bytes(cache_data)
            }
            
            metadata_file = cache_dir / 'metadata.json'
            import json
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"DICOM cache for study {study_id} stored to NAS")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store DICOM cache to NAS: {e}")
            return False
    
    def retrieve_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve report data from NAS"""
        try:
            report_dir = self.backup_path / 'reports' / report_id[:2] / report_id
            metadata_file = report_dir / 'metadata.json'
            
            if not metadata_file.exists():
                logger.warning(f"Report {report_id} not found in NAS")
                return None
            
            import json
            with open(metadata_file, 'r') as f:
                report_data = json.load(f)
            
            logger.info(f"Report {report_id} retrieved from NAS")
            return report_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve report from NAS: {e}")
            return None
    
    def retrieve_voice_recording(self, session_id: str) -> Optional[str]:
        """Retrieve voice recording path from NAS"""
        try:
            voice_dir = self.backup_path / 'voice_recordings' / session_id[:2] / session_id
            
            if not voice_dir.exists():
                logger.warning(f"Voice recording {session_id} not found in NAS")
                return None
            
            # Find audio file (could be various formats)
            audio_files = list(voice_dir.glob('*.wav')) + list(voice_dir.glob('*.mp3')) + list(voice_dir.glob('*.ogg'))
            
            if not audio_files:
                logger.warning(f"No audio files found for session {session_id}")
                return None
            
            audio_path = audio_files[0]  # Take first found audio file
            
            # Verify integrity if checksum exists
            checksum_file = voice_dir / f"{audio_path.stem}.checksum"
            if checksum_file.exists():
                expected_checksum = checksum_file.read_text().strip()
                actual_checksum = self._calculate_checksum(audio_path)
                
                if expected_checksum != actual_checksum:
                    logger.error(f"Checksum mismatch for voice recording {session_id}")
                    return None
            
            logger.info(f"Voice recording {session_id} retrieved from NAS")
            return str(audio_path)
            
        except Exception as e:
            logger.error(f"Failed to retrieve voice recording from NAS: {e}")
            return None
    
    def list_reports(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List reports stored in NAS"""
        try:
            reports = []
            reports_dir = self.backup_path / 'reports'
            
            if not reports_dir.exists():
                return reports
            
            # Walk through directory structure
            for subdir in reports_dir.iterdir():
                if subdir.is_dir():
                    for report_dir in subdir.iterdir():
                        if report_dir.is_dir():
                            metadata_file = report_dir / 'metadata.json'
                            if metadata_file.exists():
                                try:
                                    import json
                                    with open(metadata_file, 'r') as f:
                                        report_data = json.load(f)
                                    
                                    reports.append({
                                        'report_id': report_dir.name,
                                        'stored_at': metadata_file.stat().st_mtime,
                                        'patient_id': report_data.get('patient_id'),
                                        'study_id': report_data.get('study_id')
                                    })
                                    
                                    if len(reports) >= limit:
                                        break
                                        
                                except Exception as e:
                                    logger.warning(f"Failed to read report metadata: {e}")
                                    continue
            
            # Sort by stored time (newest first)
            reports.sort(key=lambda x: x['stored_at'], reverse=True)
            return reports
            
        except Exception as e:
            logger.error(f"Failed to list reports from NAS: {e}")
            return []
    
    def cleanup_old_files(self, days_old: int = 30) -> int:
        """Clean up old files from NAS"""
        try:
            if not self.backup_enabled:
                return 0
            
            cutoff_time = datetime.utcnow().timestamp() - (days_old * 24 * 3600)
            deleted_count = 0
            
            for root, dirs, files in os.walk(self.backup_path):
                for file in files:
                    file_path = Path(root) / file
                    if file_path.stat().st_mtime < cutoff_time:
                        try:
                            file_path.unlink()
                            deleted_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to delete old file {file_path}: {e}")
            
            logger.info(f"Cleaned up {deleted_count} old files from NAS")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old files: {e}")
            return 0
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get NAS storage statistics"""
        try:
            if not self.mount_point.exists():
                return {'error': 'NAS not accessible'}
            
            # Get disk usage
            statvfs = os.statvfs(self.mount_point)
            total_bytes = statvfs.f_frsize * statvfs.f_blocks
            free_bytes = statvfs.f_frsize * statvfs.f_available
            used_bytes = total_bytes - free_bytes
            
            # Count files in backup directory
            file_counts = {'reports': 0, 'voice_recordings': 0, 'dicom_cache': 0}
            
            if self.backup_path.exists():
                for category in file_counts.keys():
                    category_dir = self.backup_path / category
                    if category_dir.exists():
                        file_counts[category] = sum(1 for _ in category_dir.rglob('*') if _.is_file())
            
            return {
                'total_bytes': total_bytes,
                'used_bytes': used_bytes,
                'free_bytes': free_bytes,
                'usage_percent': (used_bytes / total_bytes) * 100 if total_bytes > 0 else 0,
                'file_counts': file_counts,
                'backup_enabled': self.backup_enabled,
                'mount_point': str(self.mount_point),
                'backup_path': str(self.backup_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {'error': str(e)}
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _calculate_checksum_bytes(self, data: bytes) -> str:
        """Calculate SHA256 checksum of bytes"""
        return hashlib.sha256(data).hexdigest()

# Global NAS client instance
nas_client = NASClient()