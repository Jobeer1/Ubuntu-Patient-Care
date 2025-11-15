#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Add backend to path
backend_path = r'4-PACS-Module\Orthanc\orthanc-source\NASIntegration'
sys.path.insert(0, str(Path(backend_path).resolve()))

from backend.services.patient_search import search_patient_comprehensive

# Test search
result = search_patient_comprehensive({'patient_name': 'SLAVTCHEV'})
print("=" * 80)
print("SEARCH RESULT FOR SLAVTCHEV:")
print("=" * 80)
print(json.dumps(result, indent=2))
print("=" * 80)
print(f"Total found: {result.get('total_found')}")
print(f"Number of patient records in results: {len(result.get('patients', []))}")
if result.get('patients'):
    for i, p in enumerate(result['patients']):
        print(f"\nPatient {i+1}:")
        print(f"  Name: {p.get('patient_name')}")
        print(f"  ID: {p.get('patient_id')}")
        print(f"  Study Date: {p.get('study_date')}")
        print(f"  File Count: {p.get('file_count')}")
        print(f"  Folder Path: {p.get('folder_path')}")
        print(f"  Studies in record: {len(p.get('studies', []))}")
