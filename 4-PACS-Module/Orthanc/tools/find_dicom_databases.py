import sqlite3
import shutil
import tempfile
from pathlib import Path

workspace = Path(r"C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc")

def inspect_db(dbpath: Path):
    info = {
        'path': str(dbpath),
        'tables': [],
        'dicom_tables': [],
        'sample_matches': []
    }
    try:
        try:
            conn = sqlite3.connect(f'file:{dbpath}?mode=ro', uri=True, timeout=5)
        except sqlite3.OperationalError as e:
            # handle locked orthanc index by copying index/wal/shm
            if 'locked' in str(e).lower() and dbpath.name == 'index':
                parent = dbpath.parent
                if (parent / 'index-wal').exists():
                    with tempfile.TemporaryDirectory() as td:
                        for fname in ['index', 'index-wal', 'index-shm']:
                            src = parent / fname
                            if src.exists():
                                shutil.copy2(src, Path(td) / fname)
                        conn = sqlite3.connect(f'file:{Path(td)/"index"}?mode=ro', uri=True)
                else:
                    raise
            else:
                raise
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        info['tables'] = tables
        # possible dicom-identifying table names
        dicom_table_names = set(['dicom_files','dicom','dicomobjects','attachedfiles','attached_files','attached_files','attachedfile','attachedFile','files','studies','series','instances','MainDicomTags','Resources','Metadata','DicomIdentifiers'])
        for t in tables:
            if t.lower() in set(n.lower() for n in dicom_table_names):
                info['dicom_tables'].append(t)
        # look for file path or .dcm occurrences in text columns of tables
        for t in tables:
            try:
                cols = conn.execute(f"PRAGMA table_info('{t}')").fetchall()
                colnames = [c[1] for c in cols]
            except Exception:
                continue
            if not colnames:
                continue
            # build a query scanning text columns for typical markers
            markers = ['\\Image Archiving\\', '.dcm', '1.2.840']
            where_clauses = []
            text_cols = []
            for c in cols:
                ctype = (c[2] or '').lower()
                if 'char' in ctype or 'text' in ctype or 'clob' in ctype or ctype == '':
                    text_cols.append(c[1])
            if not text_cols:
                # fallback: use all columns
                text_cols = [c[1] for c in cols]
            for m in markers:
                where_clauses = [f"{col} LIKE ? COLLATE NOCASE" for col in text_cols]
                query = f"SELECT * FROM {t} WHERE (" + " OR ".join(where_clauses) + ") LIMIT 3"
                params = [f'%{m}%'] * len(text_cols)
                try:
                    rows = conn.execute(query, params).fetchall()
                except Exception:
                    rows = []
                if rows:
                    info['sample_matches'].append({'table': t, 'marker': m, 'rows': [tuple(str(x)[:200] for x in r) for r in rows]})
        conn.close()
    except Exception as e:
        info['error'] = str(e)
    return info


def main():
    db_files = sorted([p for p in workspace.rglob('*.db')])
    # include orthanc-index 'index' file if present
    idx = workspace / 'orthanc-source' / 'NASIntegration' / 'backend' / 'orthanc-index' / 'index'
    if idx.exists():
        db_files.append(idx)
    print(f'Found {len(db_files)} database files to inspect\n')
    results = []
    for db in db_files:
        print('Inspecting:', db)
        info = inspect_db(db)
        # determine if it 'contains dicom images'
        contains = False
        reasons = []
        if info.get('dicom_tables'):
            contains = True
            reasons.append('dicom-related table names: ' + ','.join(info['dicom_tables']))
        if info.get('sample_matches'):
            contains = True
            reasons.append('sample file-path matches: ' + ','.join([f"{m['table']}:{m['marker']}" for m in info['sample_matches']]))
        if info.get('error'):
            reasons.append('error: ' + info['error'])
        info['contains_dicom'] = contains
        info['reasons'] = reasons
        results.append(info)
        # print a compact summary for user
        print('  contains_dicom:', contains)
        if reasons:
            for r in reasons:
                print('   -', r)
        else:
            print('   - no dicom markers found')
        print()
    # write results to a small report file
    import json
    out = workspace / 'tools' / 'dicom_db_report.json'
    out.write_text(json.dumps(results, indent=2))
    print('Wrote report to', out)

if __name__ == '__main__':
    main()
