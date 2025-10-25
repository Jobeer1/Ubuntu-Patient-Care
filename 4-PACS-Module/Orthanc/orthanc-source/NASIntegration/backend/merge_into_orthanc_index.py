#!/usr/bin/env python3
"""
Merge pacs_metadata (instances) into Orthanc internal index safely.

Strategy (conservative):
- Backup existing Orthanc index files (index, index-wal, index-shm)
- Open the Orthanc index (it's safe because Orthanc is stopped)
- Create a new table `ExternalFiles` to hold mappings sop_instance_uid -> file_path
- Copy rows from pacs_metadata.db.instances into ExternalFiles

This keeps Orthanc internal schema untouched and stores external mappings
inside the same DB files so tools that open the Orthanc DB can see them.

Run only when Orthanc service/process is stopped.
"""

import os
import shutil
import sqlite3
import time
from pathlib import Path
import logging
import socket
import sys
import argparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)
ORTHANC_INDEX_DIR = os.path.join(BASE_DIR, 'orthanc-index')
ORTHANC_INDEX_FILE = os.path.join(ORTHANC_INDEX_DIR, 'index')
PACX_META_DB = os.path.join(ORTHANC_INDEX_DIR, 'pacs_metadata.db')


def backup_index_files():
    ts = time.strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(ORTHANC_INDEX_DIR, 'backups', f'orthanc_index_backup_{ts}')
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
            logger.info(f'File not present, skipping backup: {src}')
    return backup_dir, copied


def ensure_safe_to_run(force: bool = False) -> None:
    """Abort unless safety conditions are met.

    Conditions to proceed:
    - If --force is provided, allow (with a warning).
    - Else, the environment variable USE_ORTHANC_INTERNAL_INDEX must be set to
      a truthy value ('1','true','yes').
    - And Orthanc must NOT be reachable on the configured host/port (default
      localhost:8042). We perform a simple TCP probe to detect a running
      Orthanc and refuse to modify the index if it's running.
    """
    if force:
        logger.warning('Force flag provided: skipping env/Orthanc-running checks. Proceed with extreme caution!')
        return

    env_val = os.environ.get('USE_ORTHANC_INTERNAL_INDEX', 'false').lower()
    if env_val not in ('1', 'true', 'yes'):
        logger.error('Refusing to merge: USE_ORTHANC_INTERNAL_INDEX is not enabled. Set the env var to "true" to allow merges into Orthanc internals.')
        raise SystemExit(1)

    # Probe Orthanc to ensure it's not running. Defaults to localhost:8042
    orthanc_host = os.environ.get('ORTHANC_HOST', '127.0.0.1')
    try:
        orthanc_port = int(os.environ.get('ORTHANC_PORT', '8042'))
    except Exception:
        orthanc_port = 8042

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        s.connect((orthanc_host, orthanc_port))
        s.close()
        logger.error(f'Orthanc appears to be reachable at {orthanc_host}:{orthanc_port}. Stop Orthanc before running this merge.')
        raise SystemExit(1)
    except (ConnectionRefusedError, socket.timeout, OSError):
        # Orthanc is likely not running — safe to continue
        logger.info(f'Orthanc not reachable at {orthanc_host}:{orthanc_port}; proceeding with merge.')



def merge_external_files():
    if not os.path.exists(ORTHANC_INDEX_FILE):
        raise FileNotFoundError(f'Orthanc index file not found: {ORTHANC_INDEX_FILE}')

    if not os.path.exists(PACX_META_DB):
        raise FileNotFoundError(f'PACS metadata DB not found: {PACX_META_DB}')

    # Connect to Orthanc index DB (writeable)
    conn = sqlite3.connect(ORTHANC_INDEX_FILE)
    cur = conn.cursor()

    # Create conservative table to store external file mappings
    cur.execute('''
    CREATE TABLE IF NOT EXISTS ExternalFiles (
        sop_instance_uid TEXT PRIMARY KEY,
        series_instance_uid TEXT,
        study_instance_uid TEXT,
        patient_id TEXT,
        file_path TEXT
    )
    ''')
    conn.commit()

    # Read from pacs_metadata.db
    src = sqlite3.connect(PACX_META_DB)
    s_cur = src.cursor()
    s_cur.execute('SELECT sop_instance_uid, series_instance_uid, file_path FROM instances')
    rows = s_cur.fetchall()
    logger.info(f'Found {len(rows)} instances in pacs_metadata.db to import')

    inserted = 0
    for sop, series_uid, file_path in rows:
        try:
            # We don't have study/patient mapping in instances table reliably here; leave nulls or try lookup
            # Try to lookup study and patient using series->studies/patients tables in pacs_metadata
            study_uid = None
            patient_id = None
            try:
                s_cur.execute('SELECT study_instance_uid FROM series WHERE series_instance_uid = ?', (series_uid,))
                r = s_cur.fetchone()
                if r:
                    study_uid = r[0]
                s_cur.execute('SELECT patient_id FROM studies WHERE study_instance_uid = ?', (study_uid,))
                r2 = s_cur.fetchone()
                if r2:
                    patient_id = r2[0]
            except Exception:
                study_uid = None
                patient_id = None

            cur.execute('INSERT OR REPLACE INTO ExternalFiles (sop_instance_uid, series_instance_uid, study_instance_uid, patient_id, file_path) VALUES (?,?,?,?,?)',
                        (sop, series_uid, study_uid, patient_id, file_path))
            inserted += 1
            if inserted % 500 == 0:
                conn.commit()
        except Exception as e:
            logger.debug(f'Failed to write ExternalFiles row for {sop}: {e}')

    conn.commit()
    src.close()

    # Report counts
    cur.execute('SELECT COUNT(*) FROM ExternalFiles')
    total = cur.fetchone()[0]
    conn.close()
    logger.info(f'Inserted/updated {inserted} rows into Orthanc ExternalFiles table (total now {total})')
    return inserted, total


def main():
    parser = argparse.ArgumentParser(description='Merge pacs_metadata.db into Orthanc internal index (ExternalFiles).')
    parser.add_argument('--force', action='store_true', help='Bypass safety checks (USE WITH EXTREME CAUTION)')
    args = parser.parse_args()

    ensure_safe_to_run(force=args.force)

    backup_dir, copied = backup_index_files()
    logger.info(f'Backup complete: {backup_dir}')
    inserted, total = merge_external_files()
    logger.info(f'Merge complete: inserted {inserted}. total ExternalFiles rows: {total}')


if __name__ == '__main__':
    main()
