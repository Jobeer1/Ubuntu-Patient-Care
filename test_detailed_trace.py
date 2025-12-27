#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Add backend to path
backend_path = r'4-PACS-Module\Orthanc\orthanc-source\NASIntegration'
sys.path.insert(0, str(Path(backend_path).resolve()))

# Patch EVERYTHING to log
from backend.services import patient_search

# Patch search_patient_comprehensive itself
original_search_comp = patient_search.search_patient_comprehensive

def logged_search_comp(search_params):
    print(f"\n>>> Entering search_patient_comprehensive with params: {search_params}")
    
    # Call original
    from backend.services.database_operations import search_patients_in_database
    
    nas_patients = search_patients_in_database(search_params)
    print(f">>> After DB search: nas_patients has {len(nas_patients)} records")
    for i, p in enumerate(nas_patients):
        print(f"    Record {i+1}: study_date={p.get('study_date')}, files={p.get('dicom_file_count')}")
    
    if nas_patients:
        # normalize records so UI fields are predictable
        normalized = [patient_search._normalize_patient_record(p, 'nas_index') for p in nas_patients]
        print(f">>> After normalization: normalized has {len(normalized)} records")
        for i, p in enumerate(normalized):
            print(f"    Record {i+1}: study_date={p.get('study_date')}, file_count={p.get('file_count')}, studies_in_record={len(p.get('studies', []))}")
        
        results = {
            'patients': normalized,
            'total_found': len(normalized),
            'source': 'nas_index',
            'search_criteria': search_params,
            'success': True,
            'message': f'Found {len(normalized)} patient(s) in NAS index'
        }
        print(f">>> Returning results with patients count: {len(results['patients'])}, total_found: {results['total_found']}")
        return results

patient_search.search_patient_comprehensive = logged_search_comp

# Now call it
result = logged_search_comp({'patient_name': 'SLAVTCHEV'})
print("\n" + "=" * 80)
print(f"Final: {len(result.get('patients', []))} patient records, total_found={result.get('total_found')}")
