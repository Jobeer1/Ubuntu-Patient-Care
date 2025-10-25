#!/usr/bin/env python3
"""
Test the fixed patient search functionality
"""

import requests
import json

print("🧪 Testing Fixed Patient Search")
print("=" * 40)

# Test 1: Full name search
print("1. Testing full name search: 'VAN STRAATEN HERMANUS A HA MR'")
response = requests.post('http://localhost:5000/api/nas/search/patient', 
                        json={'patient_name': 'VAN STRAATEN HERMANUS A HA MR', 'patient_id': '', 'study_date': ''}, 
                        timeout=10)
print(f"   Status: {response.status_code}")
data = response.json()
print(f"   Found: {data['total_found']} patient(s)")
for patient in data['patients']:
    print(f"   - {patient['patient_name']} (ID: {patient['patient_id']})")

# Test 2: Partial name search
print("\n2. Testing partial name search: 'STRAATEN'")
response = requests.post('http://localhost:5000/api/nas/search/patient', 
                        json={'patient_name': 'STRAATEN', 'patient_id': '', 'study_date': ''}, 
                        timeout=10)
data = response.json()
print(f"   Status: {response.status_code}")
print(f"   Found: {data['total_found']} patient(s)")
for patient in data['patients']:
    print(f"   - {patient['patient_name']}")

# Test 3: Recent patient search
print("\n3. Testing recent patient search: 'MBATHA'")
response = requests.post('http://localhost:5000/api/nas/search/patient', 
                        json={'patient_name': 'MBATHA', 'patient_id': '', 'study_date': ''}, 
                        timeout=10)
data = response.json()
print(f"   Status: {response.status_code}")
print(f"   Found: {data['total_found']} patient(s)")
for patient in data['patients']:
    print(f"   - {patient['patient_name']} - {patient['study_date']}")

print("\n✅ Search test complete!")