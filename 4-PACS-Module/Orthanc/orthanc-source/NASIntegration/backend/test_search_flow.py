import sys
import os
backend = r'c:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\4-PACS-Module\Orthanc\orthanc-source\NASIntegration\backend'
sys.path.insert(0, backend)

from services.database_operations import search_patients_in_database
from services.patient_search import _normalize_patient_record

# Simulate the search
search_params = {
    'patient_id': '',
    'patient_name': 'SLAVTCHEV KARLO K KK MR',
    'study_date': '',
    'limit': 100
}

print("=" * 70)
print("TESTING SEARCH FLOW")
print("=" * 70)

# Step 1: Get raw DB results
raw_results = search_patients_in_database(search_params)
print(f"\n✅ Step 1: Raw DB results - {len(raw_results)} records")
for i, r in enumerate(raw_results, 1):
    print(f"  {i}. {r.get('patient_id')} | {r.get('patient_name')} | {r.get('study_date')}")

# Step 2: Normalize each record
normalized = [_normalize_patient_record(p, 'nas_index') for p in raw_results]
print(f"\n✅ Step 2: After normalization - {len(normalized)} records")
for i, n in enumerate(normalized, 1):
    print(f"  {i}. {n.get('patient_id')} | {n.get('patient_name')} | {n.get('study_date')}")

# Step 3: Check for deduplication
patient_ids = set([n.get('patient_id') for n in normalized])
print(f"\n✅ Step 3: Unique patient IDs - {len(patient_ids)}")
for pid in patient_ids:
    studies = [n for n in normalized if n.get('patient_id') == pid]
    print(f"  Patient ID: {pid} -> {len(studies)} study/studies")
