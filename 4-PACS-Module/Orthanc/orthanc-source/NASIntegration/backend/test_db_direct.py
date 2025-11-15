"""
Direct database connection test
"""
import sqlite3
from pathlib import Path

# Try both possible database paths
db_paths = [
    Path('orthanc-index') / 'pacs_metadata.db',
    Path('nas_patients.db'),
]

for db_path in db_paths:
    if db_path.exists():
        print(f"✅ Found database: {db_path}")
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]
        print(f"   Tables: {tables}")
        
        if 'patient_studies' in tables:
            cursor.execute("SELECT COUNT(*) FROM patient_studies")
            count = cursor.fetchone()[0]
            print(f"   Patient records: {count}")
        
        conn.close()
        break
else:
    print("❌ No database found!")
