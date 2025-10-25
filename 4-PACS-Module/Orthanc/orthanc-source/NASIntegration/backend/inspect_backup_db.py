import sqlite3
import os
import sys
from pathlib import Path

p = Path(r"c:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc\orthanc-source\NASIntegration\backend\orthanc-index\backups\orthanc_index_backup_20251003_113100")
index = p / 'index'
if not index.exists():
    print('Index file not found:', index)
    sys.exit(2)

print('Inspecting:', index)
try:
    con = sqlite3.connect(str(index))
except Exception as e:
    print('Failed to open sqlite:', e)
    sys.exit(3)

cur = con.cursor()
# list tables
cur.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table','view') ORDER BY name")
items = cur.fetchall()
print('\nSchema objects:')
for name, typ in items:
    print('-', typ, name)

print('\nRow counts:')
for name, typ in items:
    try:
        cur.execute(f"SELECT count(*) FROM {name}")
        cnt = cur.fetchone()[0]
    except Exception as e:
        cnt = f'ERROR: {e}'
    print('-', name, cnt)

con.close()
