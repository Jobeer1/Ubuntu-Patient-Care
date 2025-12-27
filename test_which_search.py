#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Add backend to path
backend_path = r'4-PACS-Module\Orthanc\orthanc-source\NASIntegration'
sys.path.insert(0, str(Path(backend_path).resolve()))

from backend.services.patient_search import search_patient_comprehensive

# Add debug to see which function is being called
import inspect
print("=" * 80)
print(f"search_patient_comprehensive function location:")
print(f"Module: {inspect.getfile(search_patient_comprehensive)}")
print(f"Line: {inspect.getsourcelines(search_patient_comprehensive)[1]}")
print("=" * 80)

# Test search
result = search_patient_comprehensive({'patient_name': 'SLAVTCHEV'})
print(f"Total found: {result.get('total_found')}")
print(f"Message: {result.get('message')}")
