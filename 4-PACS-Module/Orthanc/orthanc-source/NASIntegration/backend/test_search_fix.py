"""
Quick test of the search service after fixing the database query
"""
import sys
sys.path.insert(0, '.')

from services.database_operations import search_patients_in_database

# Test 1: Search for SLAVTCHEV by name
print("=== TEST 1: Search SLAVTCHEV ===")
results = search_patients_in_database({'patient_name': 'SLAVTCHEV'})
print(f"Found {len(results)} result(s)")
for r in results:
    print(f"  - {r['patient_name']}: {r['study_date']} ({r['dicom_file_count']} files)")

# Test 2: Search for all patients (empty search)
print("\n=== TEST 2: All patients (limit 5) ===")
results = search_patients_in_database({})
print(f"Found {len(results)} result(s) (showing first 5)")
for r in results[:5]:
    print(f"  - {r['patient_name']}: {r['study_date']}")

# Test 3: Search by date
print("\n=== TEST 3: Search today's date (2025-10-31) ===")
results = search_patients_in_database({'study_date': '2025-10-31'})
print(f"Found {len(results)} result(s)")
for r in results[:5]:
    print(f"  - {r['patient_name']}: {r['study_date']}")
