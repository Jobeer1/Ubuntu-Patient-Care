import sqlite3
import shutil
import tempfile
from pathlib import Path

workspace = Path(r"C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc")
fragments = [
    'GUMEDE QINISILE Q MISS',
    '604553-20181021-220241-8719-9823',
    'SUBBAN DHANALUTCHMEE D MRS',
    '615809-20201221-074203-8134-2184',
    'MBATHA ENZOKUHLE E MAST',
    '639428-20250926-074531-7863-7116',
    'ZULU THOBILE M TM MRS',
    '109778-20210305-095641-3796-8881'
]

candidates = sorted({str(p) for p in workspace.rglob('*.db')})
# include orthanc-index
orthanc_index = workspace / 'orthanc-source' / 'NASIntegration' / 'backend' / 'orthanc-index' / 'index'
if orthanc_index.exists():
    candidates.append(str(orthanc_index))

print('Searching', len(candidates), 'DB files for', len(fragments), 'fragments')

for db in candidates:
    print('\nDB:', db)
    dbpath = Path(db)
    try:
        try:
            conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=5)
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower() and dbpath.name == 'index':
                with tempfile.TemporaryDirectory() as td:
                    for fname in ['index', 'index-wal', 'index-shm']:
                        src = dbpath.parent / fname
                        if src.exists():
                            shutil.copy2(src, Path(td) / fname)
                    conn = sqlite3.connect(f'file:{Path(td)/"index"}?mode=ro', uri=True)
            else:
                raise
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        found = False
        for t in tables:
            try:
                cols = [c[1] for c in conn.execute(f"PRAGMA table_info('{t}')").fetchall()]
            except Exception:
                continue
            if not cols: continue
            where = ' OR '.join([f"{col} LIKE ? COLLATE NOCASE" for col in cols])
            for frag in fragments:
                params = [f'%{frag}%'] * len(cols)
                try:
                    rows = conn.execute(f"SELECT * FROM {t} WHERE {where} LIMIT 5", params).fetchall()
                except Exception:
                    rows = []
                if rows:
                    print(f" Table: {t}  fragment: {frag}  rows:")
                    for r in rows:
                        print('   ', r[:10])
                    found = True
        if not found:
            print('  No matches')
        conn.close()
    except Exception as e:
        print('  ERROR:', e)

print('\nDone')
