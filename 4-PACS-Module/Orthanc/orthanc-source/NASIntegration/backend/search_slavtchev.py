import sqlite3

db_path = r'c:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\4-PACS-Module\Orthanc\orthanc-source\NASIntegration\backend\orthanc-index\pacs_metadata.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Search for SLAVTCHEV
    cursor.execute("SELECT DISTINCT patient_id, patient_name, study_date, modality, dicom_file_count FROM patient_studies WHERE patient_name LIKE '%SLAVTCHEV%' ORDER BY study_date DESC")
    rows = cursor.fetchall()
    
    print(f"=== SLAVTCHEV SEARCH RESULTS ===")
    print(f"Found {len(rows)} record(s)")
    
    for row in rows:
        print(f"\n  Patient ID: {row[0]}")
        print(f"  Name: {row[1]}")
        print(f"  Study Date: {row[2]}")
        print(f"  Modality: {row[3]}")
        print(f"  DICOM Files: {row[4]}")
    
    conn.close()
    
except Exception as e:
    print(f"ERROR: {e}")
