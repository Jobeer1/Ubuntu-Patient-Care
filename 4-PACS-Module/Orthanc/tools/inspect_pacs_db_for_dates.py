import sqlite3
import os
from datetime import datetime, timedelta
from backend.metadata_db import get_metadata_db_path


def inspect_db():
    db = get_metadata_db_path()
    print('DB path:', db)
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    now = datetime.now()
    today = now.strftime('%Y%m%d')
    yesterday = (now - timedelta(days=1)).strftime('%Y%m%d')
    week_start = (now - timedelta(days=now.weekday())).strftime('%Y%m%d')

    print('today', today, 'yesterday', yesterday, 'week_start', week_start)

    for d in [today, yesterday]:
        try:
            cur.execute('SELECT COUNT(DISTINCT patient_id) FROM patient_studies WHERE study_date = ?', (d,))
            print(d, 'patient_studies exact count:', cur.fetchone()[0])
        except Exception as e:
            print('Error querying patient_studies exact:', e)
            try:
                dd = f"{d[0:4]}-{d[4:6]}-{d[6:8]}"
                cur.execute('SELECT COUNT(*) FROM patients WHERE first_study_date = ? OR last_study_date = ?', (dd, dd))
                print(dd, 'patients view count:', cur.fetchone()[0])
            except Exception as e2:
                print('Error querying patients view:', e2)

    try:
        cur.execute("SELECT DISTINCT study_date FROM patient_studies ORDER BY study_date DESC LIMIT 40")
        rows = cur.fetchall()
        print('\nSample study_date values from patient_studies (len, repr):')
        for r in rows:
            s = r[0]
            print(len(str(s)), repr(s))
    except Exception as e:
        print('Error fetching sample study_date values:', e)

    try:
        cur.execute("SELECT DISTINCT first_study_date, last_study_date FROM patients ORDER BY first_study_date DESC LIMIT 40")
        rows = cur.fetchall()
        print('\nSample patients view first/last study dates (len, repr):')
        for r in rows:
            print(len(str(r[0])) if r[0] else 0, repr(r[0]), '|', len(str(r[1])) if r[1] else 0, repr(r[1]))
    except Exception as e:
        print('Error fetching patients view dates:', e)

    conn.close()

if __name__ == '__main__':
    import sys
    pid = None
    if len(sys.argv) > 1:
        pid = sys.argv[1]
    if pid:
        # Print patient_studies rows for the given patient id
        db = get_metadata_db_path()
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            cur.execute('SELECT * FROM patient_studies WHERE patient_id = ? LIMIT 50', (pid,))
            rows = cur.fetchall()
            if not rows:
                print(f'No patient_studies rows found for patient_id={pid}')
            else:
                for r in rows:
                    print('---')
                    for k in r.keys():
                        print(f"{k}: {r[k]}")
                    # Show whether folder path exists on disk
                    fp = r['folder_path'] if 'folder_path' in r.keys() else ''
                    if fp:
                        exists = os.path.exists(fp)
                        print('folder_exists:', exists, 'path:', fp)
                        if exists:
                            # show a few sample files
                            sample = []
                            for root, dirs, files in os.walk(fp):
                                for f in files[:10]:
                                    sample.append(os.path.join(root, f))
                                break
                            print('sample_files:', sample)
        except Exception as e:
            print('Error querying patient_studies for patient:', e)
        finally:
            conn.close()
    else:
        inspect_db()
