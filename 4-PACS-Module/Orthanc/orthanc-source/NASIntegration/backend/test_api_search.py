import requests
import json

BASE_URL = 'http://localhost:5000'

# Search for SLAVTCHEV
search_payload = {
    'patient_id': '',
    'patient_name': 'SLAVTCHEV KARLO K KK MR',
    'study_date': '',
    'limit': 100
}

print("=" * 70)
print("TESTING API SEARCH ENDPOINT")
print("=" * 70)

try:
    response = requests.post(f'{BASE_URL}/api/nas/search/patient', json=search_payload, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Response status: {response.status_code}")
        print(f"✅ Total found: {data.get('total_found')}")
        print(f"✅ Message: {data.get('message')}")
        print(f"✅ Number of patient records returned: {len(data.get('patients', []))}")
        
        print(f"\n📋 Patient records:")
        for i, patient in enumerate(data.get('patients', []), 1):
            print(f"  {i}. ID: {patient.get('patient_id')}")
            print(f"     Name: {patient.get('patient_name')}")
            print(f"     Study Date: {patient.get('study_date')}")
            print(f"     Files: {patient.get('file_count')}")
            print(f"     Folder: {patient.get('folder_path')}")
            print()
    else:
        print(f"❌ Response status: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")
