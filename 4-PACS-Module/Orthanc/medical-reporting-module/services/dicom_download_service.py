"""
DICOM Download Service
Handles downloading DICOM files for patients and studies from the NAS system
"""

import os
import sqlite3
import zipfile
import tempfile
import logging
import shutil
from typing import Dict, List, Optional, Any
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DICOMDownloadService:
    """Service for downloading DICOM files from the NAS patient database"""
    
    def __init__(self):
        """Initialize the download service"""
        self.db_path = self._get_database_path()
        self.nas_storage_path = self._get_nas_storage_path()
        
    def _get_database_path(self) -> str:
        """Get the path to the NAS patient database"""
        # Default path - adjust based on your setup
        current_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            # Prefer canonical metadata DB helper when available
            try:
                from backend.metadata_db import get_metadata_db_path
                return get_metadata_db_path()
            except Exception:
                # fallback to environment override
                env_path = os.environ.get('PACS_DB_PATH')
                if env_path:
                    return os.path.abspath(os.path.expanduser(env_path))
                # otherwise fall through to legacy
        except Exception:
            pass
        # Legacy fallback location relative to this module
        return os.path.abspath(os.path.join(current_dir, '..', 'database', 'nas_patient_index.db'))
    
    def _get_nas_storage_path(self) -> str:
        """Get the base path where DICOM files are stored on NAS"""
        # Allow overriding via environment variable
        env_path = os.environ.get('NAS_STORAGE_PATH') or os.environ.get('NAS_DICOM_PATH')
        if env_path:
            env_path = os.path.abspath(os.path.expanduser(env_path))
            if os.path.exists(env_path):
                return env_path

        # Common Linux mount
        linux_candidate = '/mnt/nas/dicom_storage'
        if os.path.exists(linux_candidate):
            return linux_candidate

        # Common Windows UNC or drive letter fallbacks
        windows_candidates = [
            r"\\155.235.81.155\Image Archiving",
            "Z:\\",
            r"Z:\dicom_storage",
            r"\\TRUENAS\Medical_Images",
        ]
        for p in windows_candidates:
            if os.path.exists(p):
                return p

        # As a last resort, try a relative path (useful for tests)
        relative = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_dicom_storage'))
        if os.path.exists(relative):
            return relative

        # If none found, return empty string and let callers handle the missing path
        return ''

    def _verify_storage_path(self) -> bool:
        """Verify the NAS storage path exists and log a clear error if not."""
        if not self.nas_storage_path:
            logger.error("NAS storage path not configured or not found. Set NAS_STORAGE_PATH env var or mount NAS.")
            return False
        if not os.path.exists(self.nas_storage_path):
            logger.error(f"NAS storage path does not exist: {self.nas_storage_path}")
            return False
        return True
    
    def get_patient_studies(self, patient_id: str, study_uid: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get study information for a patient"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # The lightweight `patient_studies` schema stores one record per patient folder
                # and does NOT include study_instance_uid, num_series, num_instances, or file_path
                # We adapt by using the table's existing columns and exposing a synthetic study id.
                if study_uid:
                    cursor.execute("""
                        SELECT id AS study_id, study_date, study_description, modality,
                               dicom_file_count AS num_instances, patient_name, patient_id,
                               folder_path AS file_path, folder_size_mb AS study_size_mb
                        FROM patient_studies
                        WHERE patient_id = ? AND id = ?
                    """, (patient_id, study_uid))
                else:
                    cursor.execute("""
                        SELECT id AS study_id, study_date, study_description, modality,
                               dicom_file_count AS num_instances, patient_name, patient_id,
                               folder_path AS file_path, folder_size_mb AS study_size_mb
                        FROM patient_studies
                        WHERE patient_id = ?
                        ORDER BY study_date DESC
                    """, (patient_id,))
                
                studies = []
                for row in cursor.fetchall():
                    studies.append({
                        'study_id': row['study_id'],
                        'study_uid': str(row['study_id']),
                        'study_date': row['study_date'],
                        'study_time': row['study_date'] or '',
                        'description': row['study_description'],
                        'modality': row['modality'],
                        'num_series': 0,
                        'num_instances': row['num_instances'] or 0,
                        'patient_name': row['patient_name'],
                        'patient_id': row['patient_id'],
                        'file_path': row['file_path'],
                        'size_mb': row['study_size_mb'] or 0
                    })
                
                return studies
                
        except Exception as e:
            logger.error(f"Error getting patient studies: {e}")
            return []
    
    def find_dicom_files(self, study_info: Dict[str, Any]) -> List[str]:
        """Find DICOM files for a study"""
        dicom_files = []
        
        try:
            # Get the base path from the database (folder_path field)
            file_path = study_info.get('file_path', '')

            if not file_path:
                logger.warning(f"No file path found for study {study_info.get('study_uid') or study_info.get('study_id')}")
                return []

            # If folder_path is an absolute path (UNC or drive-letter), use it directly
            if os.path.isabs(file_path) or file_path.startswith('\\'):
                full_path = file_path
            else:
                # Otherwise join with configured NAS storage base path
                full_path = os.path.join(self.nas_storage_path, file_path.lstrip('/')) if self.nas_storage_path else file_path

            if os.path.exists(full_path):
                # Walk through directory to find DICOM files
                for root, dirs, files in os.walk(full_path):
                    for file in files:
                        file_ext = os.path.splitext(file)[1].lower()
                        # Common DICOM file extensions or pattern matches
                        if file_ext in ['.dcm', '.dicom', ''] or file.upper().startswith(('IM','CT','MR')):
                            full_file_path = os.path.join(root, file)
                            dicom_files.append(full_file_path)
            else:
                logger.warning(f"Study path does not exist: {full_path}")
        
        except Exception as e:
            logger.error(f"Error finding DICOM files: {e}")
        
        return dicom_files
    
    def create_download_zip(self, patient_id: str, studies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a ZIP file containing DICOM studies for download"""
        try:
            # Create temporary directory for ZIP file
            temp_dir = tempfile.mkdtemp()
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            patient_name = studies[0]['patient_name'].replace(' ', '_') if studies else 'Unknown'
            zip_filename = f"DICOM_{patient_name}_{patient_id}_{timestamp}.zip"
            zip_path = os.path.join(temp_dir, zip_filename)
            
            # Create ZIP file
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                total_files = 0
                
                for study in studies:
                    study_uid = study['study_uid']
                    study_desc = study['description'] or 'Unknown_Study'
                    study_date = study['study_date'] or 'Unknown_Date'
                    
                    # Create folder name for study
                    study_folder = f"{study_date}_{study_desc}_{study_uid[:8]}"
                    study_folder = "".join(c for c in study_folder if c.isalnum() or c in '._-')
                    
                    # Find DICOM files for this study
                    dicom_files = self.find_dicom_files(study)
                    
                    for dicom_file in dicom_files:
                        try:
                            # Get relative filename
                            filename = os.path.basename(dicom_file)
                            
                            # Add to ZIP with study folder structure
                            archive_name = f"{study_folder}/{filename}"
                            zipf.write(dicom_file, archive_name)
                            total_files += 1
                        except Exception as e:
                            logger.warning(f"Could not add file {dicom_file} to ZIP: {e}")
            
            # Get file size
            file_size = os.path.getsize(zip_path)
            
            return {
                'success': True,
                'file_path': zip_path,
                'filename': zip_filename,
                'size_bytes': file_size,
                'total_files': total_files,
                'mimetype': 'application/zip'
            }
            
        except Exception as e:
            logger.error(f"Error creating download ZIP: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global service instance
_download_service = DICOMDownloadService()


def download_patient_studies(patient_id: str, study_uid: Optional[str] = None, format_type: str = 'zip') -> Dict[str, Any]:
    """Main function to download patient studies"""
    try:
        logger.info(f"📥 Processing download request for patient {patient_id}")
        
        if not patient_id:
            return {
                'success': False,
                'error': 'Patient ID is required'
            }
        # Verify NAS storage path before proceeding
        if not _download_service._verify_storage_path():
            return {
                'success': False,
                'error': 'NAS storage path not configured or not accessible. Set NAS_STORAGE_PATH or mount NAS.'
            }
        # Get study information
        studies = _download_service.get_patient_studies(patient_id, study_uid)
        
        if not studies:
            return {
                'success': False,
                'error': f'No studies found for patient {patient_id}'
            }
        
        logger.info(f"Found {len(studies)} studies for patient {patient_id}")
        
        if format_type == 'zip':
            # Create ZIP file for download
            result = _download_service.create_download_zip(patient_id, studies)
            return result
        else:
            # For individual files, return the first study's first file
            # This is a simplified implementation
            first_study = studies[0]
            dicom_files = _download_service.find_dicom_files(first_study)
            
            if dicom_files:
                return {
                    'success': True,
                    'file_path': dicom_files[0],
                    'filename': os.path.basename(dicom_files[0]),
                    'mimetype': 'application/dicom'
                }
            else:
                return {
                    'success': False,
                    'error': 'No DICOM files found'
                }
    
    except Exception as e:
        logger.error(f"Download service error: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def get_download_stats(patient_id: str) -> Dict[str, Any]:
    """Get download statistics for a patient"""
    try:
        studies = _download_service.get_patient_studies(patient_id)
        
        total_size = sum(study.get('size_mb', 0) for study in studies)
        total_instances = sum(study.get('num_instances', 0) for study in studies)
        
        return {
            'success': True,
            'patient_id': patient_id,
            'total_studies': len(studies),
            'total_size_mb': total_size,
            'total_instances': total_instances,
            'studies': studies
        }
        
    except Exception as e:
        logger.error(f"Error getting download stats: {e}")
        return {
            'success': False,
            'error': str(e)
        }


if __name__ == "__main__":
    # Test the download service
    test_patient_id = "12345"
    result = download_patient_studies(test_patient_id)
    print(f"Download result: {result}")