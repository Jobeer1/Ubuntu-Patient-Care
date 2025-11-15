"""
FHIR Adapter Module - P1-FHIR-004

Converts local database records (OpenEMR, Orthanc) to/from FHIR R4 resources.

Usage:
    from fhir_adapter import to_fhir, from_fhir
    
    # Convert local patient to FHIR
    fhir_patient = to_fhir('Patient', local_patient_record)
    
    # Convert FHIR back to local format
    local_patient = from_fhir('Patient', fhir_json)
"""

from .core import to_fhir, from_fhir, register_adapter
from .adapters.patient import PatientAdapter
from .adapters.imaging_study import ImagingStudyAdapter

__version__ = "0.1.0"
__all__ = ["to_fhir", "from_fhir", "register_adapter"]

# Auto-register built-in adapters
PatientAdapter.register()
ImagingStudyAdapter.register()
