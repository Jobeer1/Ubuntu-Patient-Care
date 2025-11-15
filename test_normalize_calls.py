#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Add backend to path
backend_path = r'4-PACS-Module\Orthanc\orthanc-source\NASIntegration'
sys.path.insert(0, str(Path(backend_path).resolve()))

# Patch the normalize function to add logging
from backend.services import patient_search

original_normalize = patient_search._normalize_patient_record

call_count = 0
def logged_normalize(rec, source):
    global call_count
    call_count += 1
    print(f"\n_normalize_patient_record CALL #{call_count}:")
    print(f"  Input study_date: {rec.get('study_date')}")
    print(f"  Input file_count: {rec.get('dicom_file_count')}")
    print(f"  Input folder_path: {rec.get('folder_path')[:50] if rec.get('folder_path') else 'N/A'}")
    result = original_normalize(rec, source)
    print(f"  Output study_date: {result.get('study_date')}")
    print(f"  Output file_count: {result.get('file_count')}")
    print(f"  Output studies count: {len(result.get('studies', []))}")
    return result

patient_search._normalize_patient_record = logged_normalize

# Now run the search
from backend.services.patient_search import search_patient_comprehensive

result = search_patient_comprehensive({'patient_name': 'SLAVTCHEV'})
print("\n" + "=" * 80)
print(f"FINAL RESULT:")
print(f"  Total found: {result.get('total_found')}")
print(f"  Number of patient records: {len(result.get('patients', []))}")
print(f"  Message: {result.get('message')}")
print("=" * 80)
if result.get('patients'):
    p = result['patients'][0]
    print(f"\nFirst (only) patient record:")
    print(f"  Study Date: {p.get('study_date')}")
    print(f"  File Count: {p.get('file_count')}")
    print(f"  Folder Path: {p.get('folder_path')[:60] if p.get('folder_path') else 'N/A'}")
    print(f"  Studies array length: {len(p.get('studies', []))}")
    for i, s in enumerate(p.get('studies', [])):
        print(f"    Study {i+1}: date={s.get('study_date')}, files={s.get('file_count')}")
