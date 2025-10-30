import sqlite3
from datetime import datetime

print("=" * 80)
print("TESTING FIX: Verifying patient list now shows 2025-10-20 patients")
print("=" * 80)

conn = sqlite3.connect('orthanc-index/pacs_metadata.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Simulate the FIXED query from database_operations.py
print("\n✅ Running FIXED query (ORDER BY last_study_date DESC, last_indexed DESC):\n")

c.execute('''
    SELECT 
        patient_id,
        MAX(patient_name) AS patient_name,
        MIN(substr(TRIM(REPLACE(study_date,'-','')),1,4)||'-'||substr(TRIM(REPLACE(study_date,'-','')),5,2)||'-'||substr(TRIM(REPLACE(study_date,'-','')),7,2)) AS first_study_date,
        MAX(substr(TRIM(REPLACE(study_date,'-','')),1,4)||'-'||substr(TRIM(REPLACE(study_date,'-','')),5,2)||'-'||substr(TRIM(REPLACE(study_date,'-','')),7,2)) AS last_study_date,
        MAX(last_indexed) AS last_indexed
    FROM patient_studies
    GROUP BY patient_id
    ORDER BY last_study_date DESC, last_indexed DESC
    LIMIT 100
''')

top100 = c.fetchall()

print(f"Top 20 patients (by clinical date):\n")
oct20_found = []
for idx, p in enumerate(top100[:20], start=1):
    patient_id = p['patient_id']
    patient_name = p['patient_name']
    last_study = p['last_study_date']
    indexed = p['last_indexed']
    
    # Highlight 2025-10-20 patients
    is_oct20 = last_study and '2025-10-20' in last_study
    marker = " 👉 OCT 20 PATIENT!" if is_oct20 else ""
    
    print(f"  {idx:2}. {patient_id:25} | {patient_name:30} | {last_study} {marker}")
    
    if is_oct20:
        oct20_found.append(patient_id)

print("\n" + "=" * 80)
if oct20_found:
    print(f"✅ SUCCESS! Found {len(oct20_found)} patients from 2025-10-20 in top 100:")
    for pid in oct20_found:
        print(f"   - {pid}")
    print("\n🎉 The fix works! Patients are now ordered by clinical date.")
else:
    print("⚠️  No 2025-10-20 patients in top 20. Checking full top 100...")
    
    # Check full 100
    for idx, p in enumerate(top100, start=1):
        last_study = p['last_study_date']
        if last_study and '2025-10-20' in last_study:
            oct20_found.append((idx, p['patient_id'], p['patient_name']))
    
    if oct20_found:
        print(f"\n✅ Found {len(oct20_found)} patients from 2025-10-20 in positions:")
        for pos, pid, name in oct20_found:
            print(f"   Position {pos}: {pid} - {name}")
    else:
        print("\n❌ Still not finding 2025-10-20 patients. Need to investigate further.")

conn.close()

print("\n" + "=" * 80)
print("NEXT STEP: Restart the PACS backend to apply the fix")
print("=" * 80)
