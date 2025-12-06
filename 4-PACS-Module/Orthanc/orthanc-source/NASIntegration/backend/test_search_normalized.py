import sqlite3

conn = sqlite3.connect(r'c:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\4-PACS-Module\Orthanc\orthanc-source\NASIntegration\backend\orthanc-index\pacs_metadata.db')
cur = conn.cursor()

# Test normalized search
search_term = 'SLAVTCHEV KARLO K KK MR'
cur.execute('''
    SELECT patient_id, REPLACE(patient_name, '^', ' ') as patient_name, study_date 
    FROM patient_studies 
    WHERE REPLACE(patient_name, '^', ' ') LIKE ? 
    ORDER BY study_date DESC
''', [f'%{search_term}%'])

rows = cur.fetchall()
print(f'✅ Found {len(rows)} rows for "{search_term}":')
for r in rows:
    print(f'  {r[0]} | {r[1]} | {r[2]}')

conn.close()
