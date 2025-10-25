#!/usr/bin/env python3
import sqlite3

try:
    from backend.metadata_db import get_metadata_db_path
    conn = sqlite3.connect(get_metadata_db_path())
except Exception:
    conn = sqlite3.connect('nas_patient_index.db')
cursor = conn.cursor()

# Check what tables exist
tables = cursor.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall()
print("Tables in database:", [t[0] for t in tables])

# Check patient_studies if it exists
try:
    count = cursor.execute('SELECT COUNT(*) FROM patient_studies').fetchone()[0]
    unique = cursor.execute('SELECT COUNT(DISTINCT patient_id) FROM patient_studies').fetchone()[0]
    print(f"Total patient_studies records: {count}")
    print(f"Unique patients: {unique}")
    
    if count > unique:
        avg_studies = count / unique
        print(f"✅ Normal radiology workflow: {count - unique} additional studies")
        print(f"📊 Average {avg_studies:.1f} studies per patient (follow-ups, different procedures)")
except:
    print("patient_studies table does not exist")

conn.close()