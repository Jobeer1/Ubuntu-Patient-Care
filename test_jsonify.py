#!/usr/bin/env python3
import json
import sys
import requests
from pathlib import Path

# Start by trying the actual search function first
backend_path = r'4-PACS-Module\Orthanc\orthanc-source\NASIntegration'
sys.path.insert(0, str(Path(backend_path).resolve()))

from backend.services.patient_search import search_patient_comprehensive

raw_result = search_patient_comprehensive({'patient_name': 'SLAVTCHEV'})
print("=" * 80)
print("RAW FUNCTION RESULT (from patient_search_comprehensive):")
print(f"  total_found: {raw_result.get('total_found')}")
print(f"  patients count: {len(raw_result.get('patients', []))}")
print(f"  message: {raw_result.get('message')}")
print("=" * 80)

# Now try jsonify
from flask import Flask, jsonify

app = Flask(__name__)

with app.app_context():
    jsonified = jsonify(raw_result)
    print("\nJSONIFIED RESULT:")
    print(f"  Type: {type(jsonified)}")
    print(f"  Data: {jsonified.get_json()}")
