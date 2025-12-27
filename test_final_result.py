#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Add backend to path
backend_path = r'4-PACS-Module\Orthanc\orthanc-source\NASIntegration'
sys.path.insert(0, str(Path(backend_path).resolve()))

from backend.services.patient_search import search_patient_comprehensive

result = search_patient_comprehensive({'patient_name': 'SLAVTCHEV'})
print(json.dumps(result, indent=2))
