import sqlite3

db_path = r'c:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\4-PACS-Module\Orthanc\orthanc-source\NASIntegration\backend\orthanc-index\pacs_metadata.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check date formats for recent dates
    cursor.execute("""
        SELECT patient_id, patient_name, study_date, modality, dicom_file_count 
        FROM patient_studies 
        WHERE study_date LIKE '%2025%' 
        ORDER BY study_date DESC 
        LIMIT 10
    """)
    
    print("=== RECENT STUDIES (2025) ===")
    rows = cursor.fetchall()
    for row in rows:
        print(f"  Date: {row[2]!r} | Patient: {row[1]} | Files: {row[4]}")
    
    # Check today specifically (both formats)
    print("\n=== TODAY'S DATE SEARCHES ===")
    
    # Format 1: With dashes
    cursor.execute("SELECT COUNT(*) FROM patient_studies WHERE study_date LIKE '%2025-10-31%'")
    count1 = cursor.fetchone()[0]
    print(f"  '2025-10-31' format: {count1} records")
    
    # Format 2: Without dashes
    cursor.execute("SELECT COUNT(*) FROM patient_studies WHERE study_date LIKE '%20251031%'")
    count2 = cursor.fetchone()[0]
    print(f"  '20251031' format: {count2} records")
    
    # Check SLAVTCHEV records
    print("\n=== SLAVTCHEV RECORDS ===")
    cursor.execute("""
        SELECT patient_id, patient_name, study_date, modality, dicom_file_count, folder_path
        FROM patient_studies 
        WHERE patient_name LIKE '%SLAVTCHEV%'
        ORDER BY study_date DESC
    """)
    
    rows = cursor.fetchall()
    print(f"  Total SLAVTCHEV records: {len(rows)}")
    for i, row in enumerate(rows, 1):
        print(f"  {i}. Date: {row[2]!r} | Name: {row[1]} | Files: {row[4]} | Modality: {row[3]}")
    
    conn.close()
    
except Exception as e:
    print(f"ERROR: {e}")
