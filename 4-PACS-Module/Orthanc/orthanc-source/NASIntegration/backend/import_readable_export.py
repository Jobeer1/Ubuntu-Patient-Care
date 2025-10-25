#!/usr/bin/env python3
"""
Import patient/study folder metadata from a readable Orthanc export DB or CSVs
into the safe `pacs_metadata.db`, and optionally scan a limited number of
folders to populate per-file `instances` rows (SOP -> file_path).

Usage:
  python import_readable_export.py        # import patient_studies only
  python import_readable_export.py --scan  # import and scan first N folders (default N=20)
  python import_readable_export.py --scan --limit 100  # scan first 100 folders

This script is conservative by default to avoid long scans on large NAS volumes.
"""

import sqlite3
import os
import argparse
from pathlib import Path
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from metadata_db import get_metadata_db_path
except Exception:
    from backend.metadata_db import get_metadata_db_path


DEFAULT_READABLE_DIR = os.path.join(os.path.dirname(__file__), 'orthanc-index', 'readable_export_20251003_085303')
DEFAULT_READABLE_DB = os.path.join(os.path.dirname(__file__), 'orthanc-index', 'index_readable_20251003_085303.db')


def import_patient_studies(source_db: str, target_db: str) -> int:
    """Copy patient_studies rows from source_db into target_db (patients/studies tables).
    Returns number of imported folders."""
    logger.info(f"Opening source DB: {source_db}")
    if not os.path.exists(source_db):
        # Try CSV fallback
        csv_path = os.path.join(os.path.dirname(source_db), 'readable_export_20251003_085303', 'patient_studies.csv')
        if os.path.exists(csv_path):
            logger.info(f"Found CSV: {csv_path} - will import CSV rows")
            return import_from_csv(csv_path, target_db)
        else:
            raise FileNotFoundError(f"Source readable DB not found: {source_db}")

    src = sqlite3.connect(f'file:{source_db}?mode=ro', uri=True)
    s_cur = src.cursor()
    s_cur.execute("SELECT patient_id, patient_name, patient_birth_date, patient_sex, study_date, study_description, modality, folder_path, dicom_file_count, folder_size_mb FROM patient_studies")
    rows = s_cur.fetchall()
    logger.info(f"Found {len(rows)} patient_studies rows in source DB")

    tgt = sqlite3.connect(target_db)
    t_cur = tgt.cursor()
    imported = 0
    for r in rows:
        patient_id, patient_name, birth_date, sex, study_date, study_description, modality, folder_path, dicom_file_count, folder_size_mb = r
        try:
            t_cur.execute('INSERT OR IGNORE INTO patients(patient_id, patient_name, patient_birth_date, patient_sex, folder_path) VALUES(?,?,?,?,?)',
                          (patient_id or f'AUTO_{hash(folder_path)%100000}', patient_name or '', birth_date or '', sex or '', folder_path or ''))
            # Insert study row using study_instance_uid synthesized from folder path if missing
            study_uid = f"STUDY_{hash((patient_id or '') + (folder_path or ''))%100000}"
            t_cur.execute('INSERT OR IGNORE INTO studies(study_instance_uid, patient_id, study_date, study_description, modality, folder_path) VALUES(?,?,?,?,?,?)',
                          (study_uid, patient_id or '', study_date or '', study_description or '', modality or '', folder_path or ''))
            imported += 1
        except Exception as e:
            logger.debug(f"Failed to import row {r}: {e}")
    tgt.commit()
    src.close()
    tgt.close()
    logger.info(f"Imported {imported} patient_studies into {target_db}")
    return imported


def import_from_csv(csv_path: str, target_db: str) -> int:
    import csv
    tgt = sqlite3.connect(target_db)
    t_cur = tgt.cursor()
    imported = 0
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            patient_id = row.get('patient_id') or f"AUTO_{hash(row.get('folder_path',''))%100000}"
            try:
                t_cur.execute('INSERT OR IGNORE INTO patients(patient_id, patient_name, patient_birth_date, patient_sex, folder_path) VALUES(?,?,?,?,?)',
                              (patient_id, row.get('patient_name',''), row.get('patient_birth_date',''), row.get('patient_sex',''), row.get('folder_path','')))
                study_uid = f"STUDY_{hash((patient_id or '') + (row.get('folder_path','') or ''))%100000}"
                t_cur.execute('INSERT OR IGNORE INTO studies(study_instance_uid, patient_id, study_date, study_description, modality, folder_path) VALUES(?,?,?,?,?,?)',
                              (study_uid, patient_id, row.get('study_date',''), row.get('study_description',''), row.get('modality',''), row.get('folder_path','')))
                imported += 1
            except Exception:
                continue
    tgt.commit()
    tgt.close()
    logger.info(f"Imported {imported} rows from CSV into {target_db}")
    return imported


def scan_folders_and_populate_instances(target_db: str, folders: list, limit_per_folder: int = 1000):
    """Scan each folder (list of folder paths) and add instance rows for DICOM files.
    Conservative: stops after limit_per_folder files per folder and handles errors.
    """
    try:
        import pydicom
    except Exception:
        logger.error('pydicom required for scanning DICOM headers. Install with: pip install pydicom')
        return 0

    conn = sqlite3.connect(target_db)
    cur = conn.cursor()
    total_added = 0
    for folder in folders:
        if not folder:
            continue
        logger.info(f"Scanning folder (limited): {folder}")
        if not os.path.exists(folder):
            logger.warning(f"Folder does not exist (skipping): {folder}")
            continue
        added = 0
        for root, dirs, files in os.walk(folder):
            for fname in files:
                if added >= limit_per_folder:
                    break
                if not (fname.lower().endswith(('.dcm', '.dicom', '.ima', '.img')) or '.' not in fname):
                    continue
                fp = os.path.join(root, fname)
                try:
                    ds = pydicom.dcmread(fp, stop_before_pixels=True)
                    sop = str(getattr(ds, 'SOPInstanceUID', f'SOP_{hash(fp)%100000}'))
                    series_uid = str(getattr(ds, 'SeriesInstanceUID', f'SER_{hash(fp)%100000}'))
                    inst_num = int(getattr(ds, 'InstanceNumber', 0) or 0)
                except Exception:
                    sop = f'SOP_{hash(fp)%100000}'
                    series_uid = f'SER_{hash(fp)%100000}'
                    inst_num = 0
                try:
                    cur.execute('INSERT OR IGNORE INTO series(series_instance_uid, study_instance_uid, folder_path) VALUES(?,?,?)', (series_uid, f'STUDY_{hash(folder)%100000}', folder))
                    cur.execute('INSERT OR REPLACE INTO instances(sop_instance_uid, series_instance_uid, instance_number, file_path, file_size) VALUES(?,?,?,?,?)', (sop, series_uid, inst_num, fp, os.path.getsize(fp)))
                    added += 1
                    total_added += 1
                except Exception as e:
                    logger.debug(f"Failed to insert instance for {fp}: {e}")
            if added >= limit_per_folder:
                break
        conn.commit()
        logger.info(f"Added {added} instances for folder {folder}")
        # small sleep to avoid hammering NAS
        time.sleep(0.1)
    conn.close()
    logger.info(f"Total instances added: {total_added}")
    return total_added


def main():
    parser = argparse.ArgumentParser(description='Import readable export into pacs_metadata.db')
    parser.add_argument('--source-db', default=DEFAULT_READABLE_DB, help='Readable export DB path')
    parser.add_argument('--scan', action='store_true', help='Also scan folders (limited) to populate instances')
    parser.add_argument('--limit', type=int, default=20, help='Number of folders to scan (default 20)')
    parser.add_argument('--files-per-folder', type=int, default=200, help='Max files to scan per folder')
    args = parser.parse_args()

    target_db = get_metadata_db_path()
    logger.info(f"Target PACS DB: {target_db}")

    imported = import_patient_studies(args.source_db, target_db)
    if args.scan:
        # Gather distinct folder_paths from patients/studies in target DB
        conn = sqlite3.connect(target_db)
        cur = conn.cursor()
        cur.execute('SELECT DISTINCT folder_path FROM patients WHERE folder_path IS NOT NULL')
        rows = [r[0] for r in cur.fetchall() if r[0]]
        # Also include study-level folder_path
        cur.execute('SELECT DISTINCT folder_path FROM studies WHERE folder_path IS NOT NULL')
        rows += [r[0] for r in cur.fetchall() if r[0]]
        # Deduplicate while preserving order
        seen = set()
        folders = []
        for f in rows:
            if f not in seen:
                seen.add(f)
                folders.append(f)
        conn.close()
        if not folders:
            logger.warning('No folder paths found to scan')
            return
        to_scan = folders[:args.limit]
        logger.info(f"Scanning first {len(to_scan)} folders (limit {args.files_per_folder} files/folder)")
        scan_folders_and_populate_instances(target_db, to_scan, limit_per_folder=args.files_per_folder)


if __name__ == '__main__':
    main()
