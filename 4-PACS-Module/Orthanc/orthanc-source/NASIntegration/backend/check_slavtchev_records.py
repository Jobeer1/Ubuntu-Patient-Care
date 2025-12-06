import sqlite3

db_path = r'c:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\4-PACS-Module\Orthanc\orthanc-source\NASIntegration\backend\orthanc-index\pacs_metadata.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check all SLAVTCHEV records
cur.execute('''
    SELECT patient_id, patient_name, study_date, dicom_file_count, folder_path
    FROM patient_studies 
    WHERE patient_name LIKE ? OR patient_name LIKE ?
    ORDER BY study_date DESC
''', ['%SLAVTCHEV%', '%KARLO%'])

rows = cur.fetchall()
print(f'✅ Found {len(rows)} rows in patient_studies:')
for r in rows:
    print(f'  Patient ID: {r[0]}')
    print(f'  Name: {r[1]}')
    print(f'  Study Date: {r[2]}')
    print(f'  Files: {r[3]}')
    print(f'  Folder: {r[4]}')
    print()

conn.close()
