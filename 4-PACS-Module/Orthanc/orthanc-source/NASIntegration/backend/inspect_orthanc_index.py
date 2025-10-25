import os
import sqlite3
from pathlib import Path

folder = Path(r"C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc\orthanc-source\NASIntegration\backend\orthanc-index")
print('Inspecting folder:', folder)
for item in sorted(folder.iterdir()):
    print('\nFILE:', item.name)
    if item.is_file():
        try:
            with item.open('rb') as f:
                header = f.read(16)
            print('  Header bytes:', header)
            if header.startswith(b"SQLite format 3"):
                print('  -> SQLite database detected (main file)')
                # Open read-only to avoid any writes
                uri = f'file:{item.as_posix()}?mode=ro'
                try:
                    conn = sqlite3.connect(uri, uri=True)
                    cur = conn.cursor()
                    cur.execute("SELECT name, type, sql FROM sqlite_master WHERE type IN ('table','view') ORDER BY name")
                    objs = cur.fetchall()
                    if not objs:
                        print('   No tables or views found in sqlite_master')
                    else:
                        for name, typ, sql in objs:
                            print(f"   object: {typ} {name}")
                            if sql:
                                print('     SQL:', sql[:200])

                        # list user tables
                        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
                        tables = [r[0] for r in cur.fetchall()]
                        for t in tables:
                            try:
                                cur.execute(f"SELECT COUNT(*) FROM '{t}'")
                                cnt = cur.fetchone()[0]
                            except Exception as e:
                                cnt = f'ERROR: {e}'
                            print(f"     table {t}: {cnt} rows")
                            # show up to 3 sample rows
                            try:
                                cur.execute(f"SELECT * FROM '{t}' LIMIT 3")
                                rows = cur.fetchall()
                                for r in rows:
                                    print('       sample row:', r)
                            except Exception as e:
                                print('       could not select samples:', e)
                    conn.close()
                except Exception as e:
                    print('   Could not open sqlite db read-only:', e)
            else:
                print('  -> Not a SQLite database or main db file (could be WAL/SHM)')
        except Exception as e:
            print('  Error reading file:', e)
    else:
        print('  Not a regular file')

print('\nDone.')
