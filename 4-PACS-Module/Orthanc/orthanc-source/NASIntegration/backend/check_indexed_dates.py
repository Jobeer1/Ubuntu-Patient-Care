import sqlite3
from datetime import datetime

conn = sqlite3.connect('orthanc-index/pacs_metadata.db')
c = conn.cursor()

print("=" * 80)
print("Checking when 2025-10-20 patients were indexed")
print("=" * 80)

# Get 2025-10-20 patients with their indexing time
c.execute('''
    SELECT patient_id, patient_name, study_date, last_indexed 
    FROM patient_studies 
    WHERE study_date LIKE '20251020%' OR study_date LIKE '2025-10-20%'
    ORDER BY last_indexed
''')

oct20_patients = c.fetchall()
print(f"\n✅ Found {len(oct20_patients)} patients from 2025-10-20:\n")
for p in oct20_patients:
    print(f"  {p[0]:20} | {p[1]:25} | {p[2]:12} | Indexed: {p[3]}")

# Check the LIMIT 100 query that database_operations.py uses
print("\n" + "=" * 80)
print("Checking what the LIMIT 100 query returns (simulating patient list)")
print("=" * 80)

# Simulate the VIEW patients query
c.execute('''
    SELECT 
        patient_id,
        MAX(patient_name) AS patient_name,
        MIN(study_date) AS first_study_date,
        MAX(study_date) AS last_study_date,
        MAX(last_indexed) AS last_indexed
    FROM patient_studies
    GROUP BY patient_id
    ORDER BY last_indexed DESC
    LIMIT 100
''')

top100 = c.fetchall()
print(f"\n✅ Top 100 patients by last_indexed:\n")

# Check if any 2025-10-20 patients are in top 100
oct20_ids = set(p[0] for p in oct20_patients)
found_in_top100 = []

for idx, p in enumerate(top100[:10]):  # Show first 10
    is_oct20 = p[0] in oct20_ids
    marker = "👉 OCT 20!" if is_oct20 else ""
    print(f"  {idx+1:3}. {p[0]:20} | {p[1]:25} | {p[2]:10} to {p[3]:10} | {p[4]} {marker}")
    if is_oct20:
        found_in_top100.append(p[0])

print("\n...")
for idx, p in enumerate(top100[90:], start=91):  # Show last 10
    is_oct20 = p[0] in oct20_ids
    marker = "👉 OCT 20!" if is_oct20 else ""
    print(f"  {idx:3}. {p[0]:20} | {p[1]:25} | {p[2]:10} to {p[3]:10} | {p[4]} {marker}")
    if is_oct20:
        found_in_top100.append(p[0])

print("\n" + "=" * 80)
if found_in_top100:
    print(f"✅ {len(found_in_top100)} patients from 2025-10-20 ARE in top 100")
    print(f"   IDs: {found_in_top100}")
else:
    print("❌ NO patients from 2025-10-20 are in the top 100 results!")
    print("\n🔍 ROOT CAUSE FOUND:")
    print("   The LIMIT 100 + ORDER BY last_indexed DESC query excludes 2025-10-20 patients")
    print("   because they were indexed earlier than the most recent 100 patients.")

# Show position of 2025-10-20 patients in full list
c.execute('''
    SELECT patient_id, MAX(last_indexed) as last_idx
    FROM patient_studies
    GROUP BY patient_id
    ORDER BY last_idx DESC
''')

all_patients = c.fetchall()
oct20_positions = []
for idx, p in enumerate(all_patients, start=1):
    if p[0] in oct20_ids:
        oct20_positions.append((idx, p[0], p[1]))

print("\n" + "=" * 80)
print("Position of 2025-10-20 patients in full patient list (by last_indexed):")
print("=" * 80)
for pos, pid, last_idx in oct20_positions:
    print(f"  Position {pos:4} / {len(all_patients)}: {pid:20} (indexed {last_idx})")

conn.close()

print("\n" + "=" * 80)
print("RECOMMENDATION:")
print("=" * 80)
print("""
The search query should ORDER BY study_date DESC or last_study_date DESC
instead of last_indexed DESC to show most recent patients by clinical date,
not by when they were indexed.

Fix: Change line 234 in database_operations.py from:
    ORDER BY last_indexed DESC
To:
    ORDER BY last_study_date DESC, last_indexed DESC
""")
