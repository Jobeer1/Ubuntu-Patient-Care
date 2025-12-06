import os
import sqlite3
import shutil
import time
from pathlib import Path
import csv

base = Path(__file__).resolve().parent
orthanc_index = base / 'orthanc-index'
src_index = orthanc_index / 'index'
src_wal = orthanc_index / 'index-wal'
src_shm = orthanc_index / 'index-shm'

if not src_index.exists():
    print('Source index file not found:', src_index)
    raise SystemExit(1)

ts = time.strftime('%Y%m%d_%H%M%S')
out_dir = orthanc_index / f'readable_export_{ts}'
out_dir.mkdir(parents=True, exist_ok=True)

# 1) Copy binary files as a fail-safe (does not require sqlite)
print('Copying raw files to', out_dir)
shutil.copy2(src_index, out_dir / 'index')
if src_wal.exists():
    shutil.copy2(src_wal, out_dir / 'index-wal')
if src_shm.exists():
    shutil.copy2(src_shm, out_dir / 'index-shm')

# 2) Create a single-file readable DB using sqlite3 backup
readable_db = orthanc_index / f'index_readable_{ts}.db'
print('Attempting SQLite backup to', readable_db)
try:
    src_uri = f'file:{src_index.as_posix()}?mode=ro'
    src_conn = sqlite3.connect(src_uri, uri=True)
    dest_conn = sqlite3.connect(str(readable_db))
    src_conn.backup(dest_conn)
    dest_conn.commit()
    dest_conn.close()
    src_conn.close()
    print('SQLite backup completed:', readable_db)
except Exception as e:
    print('SQLite backup failed:', e)
    print('You can still open the copied files in', out_dir)
    raise SystemExit(1)

# 3) Vacuum the readable DB to ensure single-file layout
try:
    conn = sqlite3.connect(str(readable_db))
    conn.execute('VACUUM;')
    conn.commit()
    conn.close()
    print('VACUUM completed on', readable_db)
except Exception as e:
    print('VACUUM failed:', e)

# 4) Export each table to CSV and dump schema
try:
    conn = sqlite3.connect(str(readable_db))
    cur = conn.cursor()
    cur.execute("SELECT name, type, sql FROM sqlite_master WHERE type IN ('table','view') ORDER BY name")
    objs = cur.fetchall()
    schema_file = out_dir / 'schema.sql'
    with open(schema_file, 'w', encoding='utf-8') as sf:
        for name, typ, sql in objs:
            if sql:
                sf.write(sql + ';;\n')
    print('Schema written to', schema_file)

    tables = [row[0] for row in objs if row[1] == 'table']
    for t in tables:
        print('Exporting table', t)
        cur.execute(f"PRAGMA table_info('{t}')")
        cols = [r[1] for r in cur.fetchall()]
        csv_path = out_dir / f"{t}.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as cf:
            writer = csv.writer(cf)
            writer.writerow(cols)
            cur.execute(f"SELECT * FROM '{t}'")
            for row in cur:
                writer.writerow(row)
    conn.close()
    print('Exported tables to CSV in', out_dir)
except Exception as e:
    print('Failed to export tables:', e)
    raise

print('\nDONE.\nReadable DB:', readable_db)
print('Copied raw files (safe backup):', out_dir)
print('You can open the readable DB with a SQLite browser or use the CSVs for inspection.')
