#!/usr/bin/env python3
"""
Build a JSON index (no pixel data) of DICOM series from a list of file paths.
Output structure: list of series objects, each contains patient and study metadata plus file paths.

Usage:
  python build_index.py --list nas_dicom_files.txt --out index.json --limit 0

This script only reads DICOM headers (pydicom.dcmread(..., stop_before_pixels=True)).
"""
import argparse
import json
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

try:
    import pydicom
except ImportError:
    print('Missing pydicom. Install with: pip install pydicom')
    raise

FIELDS = [
    'PatientName', 'PatientID', 'PatientBirthDate', 'PatientSex', 'PatientAge',
    'StudyDate', 'StudyTime', 'StudyInstanceUID', 'StudyID', 'StudyDescription', 'Modality',
    'SeriesInstanceUID', 'SeriesNumber', 'SeriesDescription', 'SeriesTime'
]


def safe_get(ds, tag):
    return str(getattr(ds, tag)) if hasattr(ds, tag) else None


def index_files(paths, limit=0, workers=8):
    """
    Parallel header-only indexing of DICOM files.
    Writes incremental status to index_status.json.
    """
    # prepare status file
    status = {
        'enumerated_files': len(paths),
        'files_processed': 0,
        'series_count': 0,
        'errors': 0
    }
    status_lock = threading.Lock()
    status_path = Path('index_status.json')

    def write_status():
        with status_lock:
            with status_path.open('w', encoding='utf-8') as sf:
                json.dump(status, sf, ensure_ascii=False)

    # series grouping
    series_map = {}
    series_lock = threading.Lock()

    def process_file(path_str):
        try:
            ds = pydicom.dcmread(path_str, stop_before_pixels=True)
        except Exception as e:
            with status_lock:
                status['errors'] += 1
                status['files_processed'] += 1
            write_status()
            return None
        # determine series UID
        series_uid = safe_get(ds, 'SeriesInstanceUID') or (
            safe_get(ds, 'StudyInstanceUID') + ':' + str(safe_get(ds, 'SeriesNumber'))
            if safe_get(ds, 'StudyInstanceUID') else None)
        if not series_uid:
            series_uid = f'UNKNOWN_SERIES_{hash(path_str)}'
        # metadata
        entry = {k: safe_get(ds, k) for k in FIELDS}
        entry['path'] = path_str
        return series_uid, entry

    # submit tasks
    paths_to_process = paths[:limit] if limit else paths
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_file, str(p)): p for p in paths_to_process}
        for fut in as_completed(futures):
            res = fut.result()
            with status_lock:
                status['files_processed'] += 1
            if res is None:
                write_status()
                continue
            uid, meta = res
            with series_lock:
                if uid not in series_map:
                    series_map[uid] = {k: meta.get(k) for k in FIELDS}
                    series_map[uid]['SeriesKey'] = uid
                    series_map[uid]['files'] = []
                series_map[uid]['files'].append(meta['path'])
                series_map[uid]['file_count'] = len(series_map[uid]['files'])
                status['series_count'] = len(series_map)
            write_status()

    # collate results
    results = []
    for uid, entry in series_map.items():
        results.append(entry)
    # remove status file on completion
    status['running'] = False
    write_status()
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--list', required=True, help='Text file with one full path per line')
    p.add_argument('--out', default='index.json', help='Output JSON file')
    p.add_argument('--limit', type=int, default=0, help='Limit number of files to index (0=all)')

    args = p.parse_args()

    with open(args.list, 'r', encoding='utf-8') as f:
        paths = [l.strip() for l in f if l.strip()]

    if not paths:
        print('No paths found in list', args.list)
        return

    print('Indexing', len(paths), 'files (limit=', args.limit, ')')
    results = index_files(paths, limit=args.limit)

    # write compact JSON array
    outp = Path(args.out)
    with outp.open('w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print('Wrote', outp, 'with', len(results), 'series entries')

if __name__ == '__main__':
    main()
