#!/usr/bin/env python3
"""
Read DICOM header metadata (no pixel data) from a list of files and output JSON lines.

Usage:
  python metadata_extractor.py --list nas_dicom_files.txt --limit 20 --out metadata.jsonl

The script uses pydicom.dcmread(..., stop_before_pixels=True) so it does not load image pixels
or copy full datasets to disk. Safe for dry-run metadata inspection.
"""
import argparse
import json
from pathlib import Path

try:
    import pydicom
    from pydicom import datadict
except ImportError:
    print('Missing pydicom. Install with: pip install pydicom')
    raise

COMMON_TAGS = [
    'PatientName', 'PatientID', 'PatientBirthDate', 'PatientSex', 'PatientAge',
    'StudyDate', 'StudyTime', 'StudyInstanceUID', 'StudyID', 'StudyDescription',
    'Modality', 'SeriesInstanceUID', 'SeriesNumber', 'SeriesDescription',
    'InstanceNumber', 'NumberOfFrames', 'Rows', 'Columns', 'PixelSpacing',
]


def safe_get(ds, name):
    return str(getattr(ds, name)) if hasattr(ds, name) else None


def extract_metadata(path: Path):
    try:
        ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=False)
    except Exception as e:
        return {'_error': str(e), 'path': str(path)}

    tags = {k: safe_get(ds, k) for k in COMMON_TAGS}

    # Also include Patient MainDicomTags mapping if available
    main = {}
    for k, v in getattr(ds, 'dir', lambda: [])():
        pass

    # pydicom stores many attributes directly; include MainDicomTags if present
    if 'MainDicomTags' in ds.dir() if hasattr(ds, 'dir') else False:
        try:
            mdt = getattr(ds, 'MainDicomTags')
            for tk in COMMON_TAGS:
                if tk in mdt:
                    tags[tk] = str(mdt.get(tk))
        except Exception:
            pass

    return {'path': str(path), 'tags': tags}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--list', required=True, help='Text file listing full paths to DICOM files (one per line)')
    p.add_argument('--limit', type=int, default=0, help='Limit number of files inspected (0 = all)')
    p.add_argument('--out', default='metadata.jsonl', help='Output JSON-lines file')

    args = p.parse_args()

    paths = [l.strip() for l in open(args.list, 'r', encoding='utf-8') if l.strip()]
    if args.limit:
        paths = paths[:args.limit]

    outp = Path(args.out)
    with outp.open('w', encoding='utf-8') as f:
        for pth in paths:
            p = Path(pth)
            if not p.exists():
                rec = {'path': str(p), '_error': 'file not found'}
            else:
                rec = extract_metadata(p)
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            print('WROTE:', rec.get('path'))

    print('Done. Wrote', outp)

if __name__ == '__main__':
    main()
