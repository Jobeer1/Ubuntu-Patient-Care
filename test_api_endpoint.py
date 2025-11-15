#!/usr/bin/env python3
"""
Test the actual API endpoint to verify the fix is working end-to-end
"""
import os
import sys
import requests
import json
from pathlib import Path
from time import sleep

# Start the backend server in the background
backend_path = r'4-PACS-Module\Orthanc\orthanc-source\NASIntegration'
backend_script = os.path.join(backend_path, 'app.py')

print("=" * 80)
print("Starting backend server...")
print("=" * 80)

# Add path
sys.path.insert(0, str(Path(backend_path).resolve()))

# Import and run Flask app
try:
    from app import app
    print("✅ Flask app imported successfully")
except Exception as e:
    print(f"❌ Failed to import app: {e}")
    sys.exit(1)

# Create test client
client = app.test_client()

# Test the search endpoint
print("\n" + "=" * 80)
print("Testing /api/nas/search/patient endpoint...")
print("=" * 80)

response = client.post('/api/nas/search/patient', 
                       json={'patient_name': 'SLAVTCHEV'},
                       content_type='application/json')

print(f"\nStatus Code: {response.status_code}")

if response.status_code == 200:
    data = response.get_json()
    print(f"Total found: {data.get('total_found')}")
    print(f"Message: {data.get('message')}")
    print(f"Number of patient records: {len(data.get('patients', []))}")
    
    print("\nPatient records:")
    for i, p in enumerate(data.get('patients', [])):
        print(f"\n  Record {i+1}:")
        print(f"    Study Date: {p.get('study_date')}")
        print(f"    File Count: {p.get('file_count')}")
        print(f"    Folder Path: {p.get('folder_path')[:60] if p.get('folder_path') else 'N/A'}...")
        
        if data.get('total_found') == 2:
            print("\n✅ SUCCESS! API is returning 2 separate records!")
        else:
            print(f"\n❌ ISSUE: Expected 2 records but got {data.get('total_found')}")
else:
    print(f"❌ API Error: {response.status_code}")
    print(response.get_data())
