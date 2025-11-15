import sqlite3

db_path = r'c:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\4-PACS-Module\Orthanc\orthanc-source\NASIntegration\backend\orthanc-index\pacs_metadata.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("=== TABLES ===")
    for t in tables:
        print(f"  - {t[0]}")
    
    # Check patient_studies records
    if any('patient_studies' in t[0] for t in tables):
        cursor.execute("SELECT COUNT(*) FROM patient_studies")
        count = cursor.fetchone()[0]
        print(f"\n=== PATIENT_STUDIES TABLE ===")
        print(f"  Total records: {count}")
        
        if count > 0:
            cursor.execute("SELECT DISTINCT patient_id, patient_name FROM patient_studies LIMIT 5")
            samples = cursor.fetchall()
            print(f"  Sample records:")
            for row in samples:
                print(f"    - {row[0]}: {row[1]}")
    
    # Check patients records
    if any('patients' in t[0] and 'studies' not in t[0] for t in tables):
        cursor.execute("SELECT COUNT(*) FROM patients")
        count = cursor.fetchone()[0]
        print(f"\n=== PATIENTS TABLE ===")
        print(f"  Total records: {count}")
    
    conn.close()
    
except Exception as e:
    print(f"ERROR: {e}")
