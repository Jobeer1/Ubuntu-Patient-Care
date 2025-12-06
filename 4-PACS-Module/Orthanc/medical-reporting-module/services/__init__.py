"""
NAS Integration Services
Modular service layer for medical imaging and patient data management
"""

# Database Operations
from .nas_database_operations import (
    get_database_connection,
    search_patients_in_database,
    get_medical_shares,
    create_medical_share,
    update_share_access,
    get_indexing_status
)

# Patient Search
from .nas_patient_search import (
    search_patient_comprehensive
)

# Medical Sharing  
from .nas_medical_sharing import (
    generate_secure_share_link,
    verify_share_access,
    get_share_statistics,
    cleanup_expired_shares,
    validate_share_permissions
)

# DICOM Integration
from .nas_dicom_integration import (
    check_orthanc_connection,
    upload_dicom_to_orthanc,
    upload_patient_folder_to_orthanc,
    get_patient_name_from_study,
    get_orthanc_studies,
    download_study_from_orthanc
)

# File Operations
from .nas_file_operations import (
    get_patient_files,
    serve_file_securely,
    convert_dicom_to_png,
    create_download_archive,
    cleanup_temp_files
)

# Service status check
def get_service_status():
    """Get status of all NAS integration services"""
    try:
        status = {
            'database': False,
            'orthanc': False,
            'file_system': False,
            'services_loaded': True
        }
        
        # Check database connection
        try:
            conn = get_database_connection()
            if conn:
                conn.close()
                status['database'] = True
        except Exception:
            pass
        
        # Check Orthanc connection
        try:
            status['orthanc'] = check_orthanc_connection()
        except Exception:
            pass
        
        # Check file system access
        try:
            import os
            nas_path = r"\\TRUENAS\Medical_Images"
            status['file_system'] = os.path.exists(nas_path)
        except Exception:
            pass
        
        return status
        
    except Exception as e:
        return {
            'database': False,
            'orthanc': False,
            'file_system': False,
            'services_loaded': False,
            'error': str(e)
        }

__all__ = [
    # Database operations
    'get_database_connection',
    'search_patients_in_database', 
    'get_medical_shares',
    'create_medical_share',
    'update_share_access',
    'get_indexing_status',
    
    # Patient search
    'search_patient_comprehensive',
    
    # Medical sharing
    'generate_secure_share_link',
    'verify_share_access', 
    'get_share_statistics',
    'cleanup_expired_shares',
    'validate_share_permissions',
    
    # DICOM integration
    'check_orthanc_connection',
    'upload_dicom_to_orthanc',
    'upload_patient_folder_to_orthanc',
    'get_patient_name_from_study',
    'get_orthanc_studies',
    'download_study_from_orthanc',
    
    # File operations
    'get_patient_files',
    'serve_file_securely',
    'convert_dicom_to_png',
    'create_download_archive',
    'cleanup_temp_files',
    
    # Service management
    'get_service_status'
]