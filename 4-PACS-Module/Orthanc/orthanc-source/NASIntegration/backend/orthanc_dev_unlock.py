#!/usr/bin/env python3
"""
Create a development-friendly Orthanc index by copying the safe
`pacs_metadata.db` into the `index` file so tools can open it without
an Orthanc process locking it.

This script is conservative:
- It refuses to run when Orthanc is reachable on ORTHANC_HOST:ORTHANC_PORT.
- It backs up any existing `index`, `index-wal`, `index-shm` files.
- It writes a marker file `index.DEV_UNLOCKED` containing a timestamp.

Run only when you intend to use this copy for development and when
Orthanc is not running. To restore the original index, copy files
back from the backups directory.
"""

import os
import time
import shutil
import sqlite3
import socket
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)
ORTHANC_INDEX_DIR = os.path.join(BASE_DIR, 'orthanc-index')
ORTHANC_INDEX_FILE = os.path.join(ORTHANC_INDEX_DIR, 'index')
PACS_META_DB = os.path.join(ORTHANC_INDEX_DIR, 'pacs_metadata.db')


def orthanc_reachable(host: str = '127.0.0.1', port: int = 8042) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def backup_index_files(ts=None):
    ts = ts or time.strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(ORTHANC_INDEX_DIR, 'backups', f'dev_unlock_backup_{ts}')
    Path(backup_dir).mkdir(parents=True, exist_ok=True)
    files = ['index', 'index-wal', 'index-shm']
    copied = []
    for f in files:
        src = os.path.join(ORTHANC_INDEX_DIR, f)
        if os.path.exists(src):
            dst = os.path.join(backup_dir, f)
            shutil.copy2(src, dst)
            copied.append(dst)
            logger.info(f'Backed up {src} -> {dst}')
        else:
            logger.info(f'Not present, skipping: {src}')
    return backup_dir, copied


def copy_pacs_into_index():
    if not os.path.exists(PACS_META_DB):
        raise FileNotFoundError(f'pacs_metadata.db not found: {PACS_META_DB}')

    # Prepare destination directory
    Path(ORTHANC_INDEX_DIR).mkdir(parents=True, exist_ok=True)

    # Create a writable copy by using sqlite backup API
    src = sqlite3.connect(f'file:{PACS_META_DB}?mode=ro', uri=True)
    try:
        # Ensure destination file path exists (will be overwritten)
        if os.path.exists(ORTHANC_INDEX_FILE):
            try:
                os.remove(ORTHANC_INDEX_FILE)
            except Exception:
                # If removal fails, we'll still try to overwrite by opening normally
                pass

        dest = sqlite3.connect(ORTHANC_INDEX_FILE)
        with dest:
            src.backup(dest)
        dest.close()
        logger.info(f'Copied pacs_metadata.db -> {ORTHANC_INDEX_FILE}')
    finally:
        src.close()


def write_marker(ts=None):
    ts = ts or time.strftime('%Y%m%d_%H%M%S')
    marker = os.path.join(ORTHANC_INDEX_DIR, f'index.DEV_UNLOCKED')
    with open(marker, 'w') as f:
        f.write(f'DEV_UNLOCKED={ts}\n')
    logger.info(f'Wrote marker file: {marker}')


def remove_wal_shm():
    for p in ('index-wal', 'index-shm'):
        fp = os.path.join(ORTHANC_INDEX_DIR, p)
        try:
            if os.path.exists(fp):
                os.remove(fp)
                logger.info(f'Removed {fp}')
        except Exception as e:
            logger.warning(f'Could not remove {fp}: {e}')


def main():
    orthanc_host = os.environ.get('ORTHANC_HOST', '127.0.0.1')
    orthanc_port = int(os.environ.get('ORTHANC_PORT', '8042'))

    if orthanc_reachable(orthanc_host, orthanc_port):
        logger.error(f'Orthanc appears reachable at {orthanc_host}:{orthanc_port}. Stop Orthanc before unlocking the index for development.')
        return 1

    ts = time.strftime('%Y%m%d_%H%M%S')
    backup_dir, copied = backup_index_files(ts)
    logger.info(f'Backup complete: {backup_dir}')

    copy_pacs_into_index()
    remove_wal_shm()
    write_marker(ts)

    logger.info('Development unlock complete: orthanc-index/index is now a readable copy of pacs_metadata.db')
    logger.info('To restore original index, copy files back from the backup folder created above.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
