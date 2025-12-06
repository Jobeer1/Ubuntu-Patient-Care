import sqlite3
import os
import shutil
import tempfile
from pathlib import Path

workspace = Path(r"C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc")
# collect candidate db files
candidates = sorted({str(p) for p in workspace.rglob('*.db')})
# include orthanc-index index file if present
orthanc_index = workspace / 'orthanc-source' / 'NASIntegration' / 'backend' / 'orthanc-index' / 'index'
if orthanc_index.exists():
    candidates.append(str(orthanc_index))

fragments = ['GUMEDE', 'SUBBAN', 'MBATHA', '639428', '639416', '639417']

print('Scanning', len(candidates), 'database files')

for db in candidates:
    print('\nDB:', db)
    try:
        conn = None
        try:
            conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=5)
        except sqlite3.OperationalError as e:
            # if locked and is orthanc index, try copying files
            err = str(e).lower()
            if 'locked' in err or 'readonly' in err:
                # try to copy index, wal, shm
                dbpath = Path(db)
                parent = dbpath.parent
                name = dbpath.name
                if name == 'index' and (parent / 'index-wal').exists():
                    with tempfile.TemporaryDirectory() as td:
                        for fname in ['index', 'index-wal', 'index-shm']:
                            src = parent / fname
                            if src.exists():
                                shutil.copy2(src, Path(td) / fname)
                        copydb = Path(td) / 'index'
                        conn = sqlite3.connect(f'file:{copydb}?mode=ro', uri=True, timeout=5)
                else:
                    raise
        cur = conn.cursor()
        cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cur.fetchall()]
        found_any = False
        for t in tables:
            try:
                cols = [c[1] for c in conn.execute(f"PRAGMA table_info('{t}')").fetchall()]
            except Exception:
                continue
            if not cols:
                continue
            where_parts = [f"{col} LIKE ? COLLATE NOCASE" for col in cols]
            query = f"SELECT * FROM {t} WHERE " + " OR ".join(where_parts) + " LIMIT 5"
            for frag in fragments:
                params = [f'%{frag}%'] * len(cols)
                try:
                    rows = conn.execute(query, params).fetchall()
                except Exception:
                    rows = []
                if rows:
                    print(f" Table: {t}  matched fragment: {frag}  rows:")
                    for r in rows:
                        # print only first 5 cols to keep output small
                        print('   ', r[:5])
                    found_any = True
                    break
            if found_any:
                break
        if not found_any:
            print('  No matches for fragments in this DB')
        conn.close()
    except Exception as e:
        print('  ERROR inspecting DB:', e)

print('\nDone')
