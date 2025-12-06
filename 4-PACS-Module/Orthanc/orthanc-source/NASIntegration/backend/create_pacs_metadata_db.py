#!/usr/bin/env python3
"""
Create or initialize the PACS metadata database used for fast NAS retrieval.

This script creates a safe metadata DB at the path returned by
`backend.metadata_db.get_metadata_db_path()` and initializes the optimized
schema (patients, studies, series, instances). It can optionally scan a
single directory and insert file-path-only records (no pixel uploads).

Usage:
  python create_pacs_metadata_db.py            # create DB only
  python create_pacs_metadata_db.py "Z:\\sample_patient"  # init and scan one folder

The script avoids touching Orthanc internal index files.
"""

import sys
import os
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from metadata_db import get_metadata_db_path
except Exception:
    from backend.metadata_db import get_metadata_db_path


SCHEMA = [
    '''
    CREATE TABLE IF NOT EXISTS patients (
        patient_id TEXT PRIMARY KEY,
        patient_name TEXT NOT NULL,
        patient_birth_date TEXT,
        patient_sex TEXT,
        patient_age TEXT,
        medical_aid TEXT,
        referring_doctor TEXT,
        indexed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        folder_path TEXT NOT NULL
    )
    ''',
    '''
    CREATE TABLE IF NOT EXISTS studies (
        study_instance_uid TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        study_date TEXT,
        study_time TEXT,
        study_description TEXT,
        modality TEXT,
        accession_number TEXT,
        study_id TEXT,
        folder_path TEXT NOT NULL,
        FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
    )
    ''',
    '''
    CREATE TABLE IF NOT EXISTS series (
        series_instance_uid TEXT PRIMARY KEY,
        study_instance_uid TEXT NOT NULL,
        series_number INTEGER,
        series_description TEXT,
        modality TEXT,
        body_part TEXT,
        series_date TEXT,
        series_time TEXT,
        folder_path TEXT NOT NULL,
        instance_count INTEGER DEFAULT 0,
        FOREIGN KEY (study_instance_uid) REFERENCES studies (study_instance_uid)
    )
    ''',
    '''
    CREATE TABLE IF NOT EXISTS instances (
        sop_instance_uid TEXT PRIMARY KEY,
        series_instance_uid TEXT NOT NULL,
        instance_number INTEGER,
        file_path TEXT NOT NULL UNIQUE,
        file_size INTEGER,
        acquisition_date TEXT,
        acquisition_time TEXT,
        slice_location REAL,
        FOREIGN KEY (series_instance_uid) REFERENCES series (series_instance_uid)
    )
    ''',
    'CREATE INDEX IF NOT EXISTS idx_patient_name ON patients (patient_name)',
    'CREATE INDEX IF NOT EXISTS idx_patient_id ON patients (patient_id)',
    'CREATE INDEX IF NOT EXISTS idx_study_date ON studies (study_date)',
    'CREATE INDEX IF NOT EXISTS idx_modality ON studies (modality)'
]


def init_db(db_path: str):
    Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for stmt in SCHEMA:
        cur.execute(stmt)
    conn.commit()
    conn.close()
    logger.info(f"Initialized PACS metadata DB at: {db_path}")


def scan_folder_and_add_paths(db_path: str, folder: str):
    """Scan a single folder for DICOM files and add file_path entries only.

    This function does not read pixel data. It will insert minimal placeholder
    SOP/Series/Study values if the DICOM header is not read (safe fallback).
    """
    try:
        import pydicom
    except Exception:
        logger.error("pydicom is required to extract DICOM headers for the scan. Install with: pip install pydicom")
        return

    folder_path = Path(folder)
    if not folder_path.exists():
        logger.error(f"Folder not found: {folder}")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    files_added = 0
    for root, dirs, files in os.walk(folder_path):
        for fname in files:
            fpath = Path(root) / fname
            if not fpath.is_file():
                continue
            # Basic check for likely DICOM file
            if not (fname.lower().endswith('.dcm') or '.' not in fname or fname.lower().endswith(('.ima', '.img'))):
                continue

            try:
                ds = pydicom.dcmread(str(fpath), stop_before_pixels=True)
                patient_id = str(getattr(ds, 'PatientID', f'AUTO_{hash(str(fpath))%100000}'))
                patient_name = str(getattr(ds, 'PatientName', 'Unknown')).replace('^', ' ')
                study_uid = str(getattr(ds, 'StudyInstanceUID', f'STUDY_{hash(str(fpath))%100000}'))
                series_uid = str(getattr(ds, 'SeriesInstanceUID', f'SER_{hash(str(fpath))%100000}'))
                sop_uid = str(getattr(ds, 'SOPInstanceUID', f'SOP_{hash(str(fpath))%100000}'))
                instance_number = int(getattr(ds, 'InstanceNumber', 0) or 0)
            except Exception:
                # Fallbacks when DICOM headers can't be read
                patient_id = f'AUTO_{hash(str(fpath))%100000}'
                patient_name = 'Unknown'
                study_uid = f'STUDY_{hash(str(fpath))%100000}'
                series_uid = f'SER_{hash(str(fpath))%100000}'
                sop_uid = f'SOP_{hash(str(fpath))%100000}'
                instance_number = 0

            # Insert or ignore patient/study/series rows
            try:
                cur.execute('INSERT OR IGNORE INTO patients (patient_id, patient_name, folder_path) VALUES (?, ?, ?)',
                            (patient_id, patient_name, str(folder_path)))
                cur.execute('INSERT OR IGNORE INTO studies (study_instance_uid, patient_id, folder_path) VALUES (?, ?, ?)',
                            (study_uid, patient_id, str(folder_path)))
                cur.execute('INSERT OR IGNORE INTO series (series_instance_uid, study_instance_uid, folder_path) VALUES (?, ?, ?)',
                            (series_uid, study_uid, str(folder_path)))

                cur.execute('INSERT OR REPLACE INTO instances (sop_instance_uid, series_instance_uid, instance_number, file_path, file_size) VALUES (?, ?, ?, ?, ?)',
                            (sop_uid, series_uid, instance_number, str(fpath), fpath.stat().st_size))
                files_added += 1
            except Exception as e:
                logger.debug(f"Failed to insert {fpath}: {e}")

            if files_added % 100 == 0 and files_added > 0:
                conn.commit()

    conn.commit()
    conn.close()
    logger.info(f"Scan complete. Files added/updated: {files_added}")


def main():
    db_path = get_metadata_db_path()
    init_db(db_path)

    if len(sys.argv) > 1:
        folder = sys.argv[1]
        scan_folder_and_add_paths(db_path, folder)
    else:
        logger.info("No folder provided; database initialized and ready. Run with a folder path to add file paths.")


if __name__ == '__main__':
    main()
