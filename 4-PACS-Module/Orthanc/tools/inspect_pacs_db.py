import sqlite3, os
from pathlib import Path
candidates = [
    Path(r"c:/Users/Admin/Desktop/ELC/Ubuntu-Patient-Care/Orthanc/backend/orthanc-index/pacs_metadata.db"),
    Path(r"c:/Users/Admin/Desktop/ELC/Ubuntu-Patient-Care/Orthanc/orthanc-source/NASIntegration/backend/orthanc-index/pacs_metadata.db"),
    Path(r"c:/Users/Admin/Desktop/ELC/Ubuntu-Patient-Care/Orthanc/orthanc-source/backend/orthanc-index/pacs_metadata.db"),
]
found = None
for c in candidates:
    if c.exists():
        found = c
        break
if not found:
    print('Tried candidate DB paths:')
    for c in candidates:
        print(' -', c)
    print('Database file not found; aborting')
    raise SystemExit(1)
p = found
print('DB path:', p)
print('DB exists:', p.exists())

conn = sqlite3.connect(str(p))
cur = conn.cursor()
# list tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print('tables:', tables)

# describe tables of interest
for t in ('patients','patient_studies'):
    try:
        cur.execute(f"PRAGMA table_info({t})")
        print(f'schema {t}:', cur.fetchall())
    except Exception as e:
        print(f'failed to get schema for {t}:', e)

# try to find the patient
pid = '114567-20140331-081802-165-1795'
print('\nLooking up patient id:', pid)
try:
    cur.execute("SELECT patient_id, folder_path, first_study_date, last_study_date FROM patients WHERE patient_id = ?", (pid,))
    r = cur.fetchone()
    print('patient row:', r)
except Exception as e:
    print('query error', e)

# If not found in patients, try patient_studies
if not r:
    try:
        cur.execute("SELECT patient_id, study_uid, file_path FROM patient_studies WHERE patient_id = ? LIMIT 5", (pid,))
        rows = cur.fetchall()
        print('patient_studies rows (up to 5):', rows)
    except Exception as e:
        print('patient_studies query error', e)

conn.close()
print('\nDone')
