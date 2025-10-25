#!/usr/bin/env python3
"""
Import DICOM files listed in a text file into Orthanc.
Usage:
  python import_from_list.py --list nas_dicom_files.txt --dry-run --limit 20

Reads `nas_import_config.json` for Orthanc URL and credentials if present.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print('Missing requests library. Install with: pip install requests')
    sys.exit(1)

DEFAULT_CONFIG = 'nas_import_config.json'


def load_orthanc_config(config_path: str):
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                cfg = json.load(f)
            orth = cfg.get('orthanc', {})
            return orth.get('url', 'http://localhost:8042'), orth.get('username'), orth.get('password')
        except Exception as e:
            print('Could not read config:', e)
    return 'http://localhost:8042', None, None


def post_dicom(orthanc_url, auth, file_path):
    url = orthanc_url.rstrip('/') + '/instances'
    with open(file_path, 'rb') as f:
        data = f.read()
    headers = {'Content-Type': 'application/dicom'}
    try:
        r = requests.post(url, data=data, headers=headers, auth=auth, timeout=60)
        return r.status_code, r.text
    except Exception as e:
        return None, str(e)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--list', required=True, help='Path to text file with one full path per line')
    p.add_argument('--config', default=DEFAULT_CONFIG, help='Path to nas_import_config.json to read orthanc creds')
    p.add_argument('--dry-run', action='store_true', help='Do not POST to Orthanc, only open files to verify access')
    p.add_argument('--limit', type=int, default=0, help='Limit number of files processed (0 = all)')
    p.add_argument('--skip-errors', action='store_true', help='Continue on file read errors')

    args = p.parse_args()

    orthanc_url, orth_user, orth_pass = load_orthanc_config(args.config)
    auth = None
    if orth_user and orth_pass:
        auth = (orth_user, orth_pass)

    if not os.path.exists(args.list):
        print('List file not found:', args.list)
        sys.exit(1)

    with open(args.list, 'r', encoding='utf-8') as f:
        paths = [l.strip() for l in f if l.strip()]

    if not paths:
        print('No files listed in', args.list)
        sys.exit(0)

    total = len(paths)
    print(f'Found {total} files in list; dry-run={args.dry_run}; limit={args.limit}')

    processed = 0
    for i, path in enumerate(paths):
        if args.limit and processed >= args.limit:
            break
        try:
            # Support relative paths: if path starts with \\ or drive letter, use as-is
            ppath = Path(path)
            if not ppath.exists():
                print(f'[{i+1}/{total}] MISSING: {path} (file not found)')
                if not args.skip_errors:
                    continue
                else:
                    processed += 1
                    continue

            size = ppath.stat().st_size
            print(f'[{i+1}/{total}] OPEN: {path} ({size} bytes)')

            if args.dry_run:
                # Just read a small prefix to ensure file is accessible
                with open(ppath, 'rb') as fh:
                    _ = fh.read(1024)
                print('   OK (read sample)')
            else:
                status, text = post_dicom(orthanc_url, auth, ppath)
                if status == 200:
                    print('   IMPORTED -> OK')
                else:
                    print(f'   IMPORT FAILED -> {status} {text}')

            processed += 1
            time.sleep(0.05)

        except Exception as e:
            print(f'   ERROR reading {path}:', e)
            if not args.skip_errors:
                continue

    print(f'Done. Processed {processed} files.')


if __name__ == '__main__':
    main()
