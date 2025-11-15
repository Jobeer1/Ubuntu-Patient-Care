#!/usr/bin/env python3
import json
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

# Add backend to path
backend_path = r'4-PACS-Module\Orthanc\orthanc-source\NASIntegration'
sys.path.insert(0, str(Path(backend_path).resolve()))

from backend.services import nas_patient_search as _ns
search_service_func = _ns.search_patient_comprehensive

result = search_service_func({'patient_name': 'SLAVTCHEV'})
print("\n" + "=" * 80)
print(f"FINAL RESULT: {result.get('total_found')} patients, {len(result.get('patients', []))} records")
