"""
Shim to expose medical-reporting-module's dicom_download_service as a local package
This allows imports like `from services.dicom_download_service import download_patient_studies`
regardless of how the application is started.
"""
import os
import sys

# Try to import the local bundled service first
try:
    from services import dicom_download_service as _module  # type: ignore
    download_patient_studies = getattr(_module, 'download_patient_studies')
except Exception:
    # Try to locate the medical-reporting-module folder relative to this file
    this_dir = os.path.abspath(os.path.dirname(__file__))
    medical_module_path = None
    search_dir = this_dir
    for _ in range(6):
        candidate = os.path.join(search_dir, 'medical-reporting-module')
        if os.path.isdir(candidate):
            medical_module_path = candidate
            break
        parent = os.path.dirname(search_dir)
        if parent == search_dir:
            break
        search_dir = parent

    if not medical_module_path:
        # Also try a sibling path used in the repo
        candidate = os.path.abspath(os.path.join(this_dir, '..', '..', 'medical-reporting-module'))
        if os.path.isdir(candidate):
            medical_module_path = candidate

    if medical_module_path:
        if medical_module_path not in sys.path:
            sys.path.insert(0, medical_module_path)
        try:
            from services import dicom_download_service as _module
            download_patient_studies = getattr(_module, 'download_patient_studies')
        except Exception:
            # Final fallback: try loading by file path
            import importlib.util
            service_file = os.path.join(medical_module_path, 'services', 'dicom_download_service.py')
            if os.path.exists(service_file):
                spec = importlib.util.spec_from_file_location('dicom_download_service', service_file)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                download_patient_studies = getattr(mod, 'download_patient_studies')
            else:
                # Provide a stub that returns an error so imports succeed but calls fail gracefully
                def download_patient_studies(patient_id, study_uid=None, format_type='raw'):
                    return {'success': False, 'error': 'dicom_download_service not available'}
    else:
        # Provide a stub implementation
        def download_patient_studies(patient_id, study_uid=None, format_type='raw'):
            return {'success': False, 'error': 'dicom_download_service not found'}
