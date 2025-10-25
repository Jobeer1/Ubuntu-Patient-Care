import sqlite3
from pathlib import Path

paths = []
try:
    from backend.metadata_db import get_metadata_db_path
    paths.append(Path(get_metadata_db_path()))
except Exception:
    paths.append(Path(r"C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc\orthanc-source\NASIntegration\backend\nas_patient_index.db"))

paths.append(Path(r"C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc\orthanc-source\NASIntegration\backend\nas_patient_index_backup_20250926_165157.db"))

for p in paths:
    print('\nDB:', p)
    if not p.exists():
        print('  not found')
        continue
    try:
        conn = sqlite3.connect(f'file:{p}?mode=ro', uri=True)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(' Tables:', tables)
        if 'patient_studies' in tables:
            cnt = cur.execute('SELECT COUNT(*) FROM patient_studies').fetchone()[0]
            print(' patient_studies count:', cnt)
            print(' sample rows:')
            for r in cur.execute('SELECT * FROM patient_studies LIMIT 5'):
                print('  ', r)
        elif 'patients' in tables:
            cnt = cur.execute('SELECT COUNT(*) FROM patients').fetchone()[0]
            print(' patients count:', cnt)
            print(' sample rows:')
            for r in cur.execute('SELECT * FROM patients LIMIT 5'):
                print('  ', r)
        else:
            print(' no patient table found')
        conn.close()
    except Exception as e:
        print(' ERROR:', e)
