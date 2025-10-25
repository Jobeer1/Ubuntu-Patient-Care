"""
Service initialization file
"""

from .database_operations import (
    get_database_connection,
    initialize_database,
    search_patients_in_database,
    add_patient_to_database,
    get_indexing_status,
    create_medical_share,
    get_medical_share,
    update_share_access
)

from .patient_search import (
    search_patient_comprehensive,
    search_orthanc_patients,
    search_folders_directly,
    find_patient_by_id_or_name
)

# Also expose the patient_search module as 'nas_patient_search' for backwards compatibility
from . import patient_search as nas_patient_search

from .dicom_integration import (
    upload_patient_to_orthanc,
    find_existing_study_in_orthanc,
    get_study_info_from_orthanc,
    get_patient_name_from_study,
    check_orthanc_connection
)

from .medical_sharing import (
    generate_secure_share_link,
    verify_share_access
)

from .file_operations import (
    get_patient_files,
    create_download_archive,
    convert_dicom_to_jpeg,
    convert_dicom_to_png,
    serve_file_securely
)

__all__ = [
    # Database operations
    'get_database_connection',
    'initialize_database',
    'search_patients_in_database',
    'add_patient_to_database',
    'get_indexing_status',
    'create_medical_share',
    'get_medical_share',
    'update_share_access',
    
    # Patient search
    'search_patient_comprehensive',
    'search_orthanc_patients', 
    'search_folders_directly',
    'find_patient_by_id_or_name',
    # Module alias for legacy imports
    'nas_patient_search',
    
    # DICOM integration
    'upload_patient_to_orthanc',
    'find_existing_study_in_orthanc',
    'get_study_info_from_orthanc',
    'get_patient_name_from_study',
    'check_orthanc_connection',
    
    # Medical sharing
    'generate_secure_share_link',
    'verify_share_access',
    
    # File operations
    'get_patient_files',
    'create_download_archive',
    'convert_dicom_to_jpeg',
    'convert_dicom_to_png',
    'serve_file_securely'
]