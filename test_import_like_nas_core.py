#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Add backend to path like nas_core would
backend_path = r'4-PACS-Module\Orthanc\orthanc-source\NASIntegration'
sys.path.insert(0, str(Path(backend_path).resolve()))

# Import like nas_core does
try:
    from backend.services import nas_patient_search as _ns
    search_service_func = _ns.search_patient_comprehensive
    print(f"Found via backend.services.nas_patient_search: {search_service_func}")
except Exception as e:
    print(f"Failed: {e}")
    search_service_func = None

if search_service_func:
    print(f"\nImported function: {search_service_func}")
    print(f"File: {search_service_func.__code__.co_filename}")
    print(f"Line: {search_service_func.__code__.co_firstlineno}")
    
    # Call it
    result = search_service_func({'patient_name': 'SLAVTCHEV'})
    print(f"\nResult total_found: {result.get('total_found')}")
    print(f"Result patients count: {len(result.get('patients', []))}")
