#!/usr/bin/env python3
import json
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Add backend to path
backend_path = r'4-PACS-Module\Orthanc\orthanc-source\NASIntegration'
sys.path.insert(0, str(Path(backend_path).resolve()))

from backend.services.database_operations import search_patients_in_database

# Test search
result = search_patients_in_database({'patient_name': 'SLAVTCHEV'})
print("=" * 80)
print(f"Database returned {len(result)} records:")
print("=" * 80)
for i, r in enumerate(result):
    print(f"\nRecord {i+1}:")
    print(f"  Study Date: {r.get('study_date')}")
    print(f"  File Count: {r.get('dicom_file_count')}")
    print(f"  Folder Path: {r.get('folder_path')}")
