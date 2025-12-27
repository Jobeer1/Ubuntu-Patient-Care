#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Add backend to path
backend_path = r'4-PACS-Module\Orthanc\orthanc-source\NASIntegration'
sys.path.insert(0, str(Path(backend_path).resolve()))

# Patch search_patients_in_database to log output
from backend.services import database_operations

original_search = database_operations.search_patients_in_database

def logged_search(params):
    result = original_search(params)
    print(f"\n>>> search_patients_in_database returned {len(result)} records")
    for i, r in enumerate(result):
        print(f"  Record {i+1}: study_date={r.get('study_date')}, files={r.get('dicom_file_count')}, folder ending={r.get('folder_path', '')[-20:] if r.get('folder_path') else 'N/A'}")
    return result

database_operations.search_patients_in_database = logged_search

# Patch patient search too
from backend.services import patient_search
patient_search.search_patients_in_database = logged_search

# Now call comprehensive search
result = patient_search.search_patient_comprehensive({'patient_name': 'SLAVTCHEV'})
print("\n" + "=" * 80)
print(f"Final result: {len(result.get('patients', []))} patient records")
print(f"Total found: {result.get('total_found')}")
print(f"Message: {result.get('message')}")
