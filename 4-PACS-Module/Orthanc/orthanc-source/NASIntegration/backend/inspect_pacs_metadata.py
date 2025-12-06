import sqlite3
import os
from pathlib import Path

db_path = r"c:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc\orthanc-source\NASIntegration\backend\orthanc-index\pacs_metadata.db"

if not os.path.exists(db_path):
    print(f"❌ Database not found: {db_path}")
    exit(1)

print(f"Inspecting: {db_path}\n")

con = sqlite3.connect(db_path)
cur = con.cursor()

# Get all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cur.fetchall()]

print("=" * 60)
print("TABLES AND ROW COUNTS")
print("=" * 60)
for table in tables:
    try:
        cur.execute(f"SELECT count(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table:30} {count:>10} rows")
    except Exception as e:
        print(f"  {table:30} ERROR: {e}")

# Get recent indexing status if available
print("\n" + "=" * 60)
print("INDEXING STATUS")
print("=" * 60)
try:
    cur.execute("SELECT * FROM indexing_status ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if row:
        cur.execute("PRAGMA table_info(indexing_status)")
        cols = [c[1] for c in cur.fetchall()]
        for col, val in zip(cols, row):
            print(f"  {col:25} {val}")
    else:
        print("  No indexing status records found")
except Exception as e:
    print(f"  Unable to read indexing_status: {e}")

# Sample patient_studies records
print("\n" + "=" * 60)
print("SAMPLE PATIENT_STUDIES (first 5)")
print("=" * 60)
try:
    cur.execute("SELECT patient_id, patient_name, study_date, folder_path FROM patient_studies LIMIT 5")
    rows = cur.fetchall()
    if rows:
        for row in rows:
            print(f"  Patient: {row[0]}")
            print(f"    Name: {row[1]}")
            print(f"    Study Date: {row[2]}")
            print(f"    Folder: {row[3]}")
            print()
    else:
        print("  No patient_studies records found")
except Exception as e:
    print(f"  Unable to read patient_studies: {e}")

con.close()
