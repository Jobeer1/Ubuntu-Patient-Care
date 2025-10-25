#!/usr/bin/env python3
import sqlite3
from pathlib import Path
import sys

DB = Path(__file__).parent / 'orthanc-index' / 'pacs_metadata.db'
print('Checking DB:', DB)
if not DB.exists():
    print('DB not found:', DB)
    sys.exit(1)

try:
    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()

    # Get list of tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print('Tables:', tables)

    # Check common tables and print counts
    common = ['patient_studies','patients','studies','instances']
    for t in common:
        if t in tables:
            try:
                cur.execute(f'SELECT COUNT(*) FROM {t}')
                cnt = cur.fetchone()[0]
            except Exception as e:
                cnt = f'error: {e}'
        else:
            cnt = 'not present'
        print(f'{t}: {cnt}')

    # Print sample rows from patient_studies
    if 'patient_studies' in tables:
        print('\nSample patient_studies rows:')
        try:
            cur.execute('SELECT patient_id, patient_name, folder_path FROM patient_studies LIMIT 5')
            for r in cur.fetchall():
                print(' ', r)
        except Exception as e:
            print('Could not fetch sample rows:', e)

    # Print total unique patients from patient_studies
    if 'patient_studies' in tables:
        try:
            cur.execute('SELECT COUNT(DISTINCT patient_id) FROM patient_studies')
            print('Distinct patient_id count:', cur.fetchone()[0])
        except Exception as e:
            print('Distinct count error:', e)

    conn.close()
except Exception as e:
    print('ERROR opening DB:', e)
    sys.exit(1)
