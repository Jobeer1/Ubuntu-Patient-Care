#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Add backend to path
backend_path = r'4-PACS-Module\Orthanc\orthanc-source\NASIntegration'
sys.path.insert(0, str(Path(backend_path).resolve()))

from backend.services.database_operations import search_patients_in_database

# Test search directly from database
result = search_patients_in_database({'patient_name': 'SLAVTCHEV'})
print("=" * 80)
print("DIRECT DATABASE SEARCH FOR SLAVTCHEV:")
print("=" * 80)
print(f"Number of records returned: {len(result)}")
print("=" * 80)
for i, r in enumerate(result):
    print(f"\nRecord {i+1}:")
    print(json.dumps(r, indent=2))
