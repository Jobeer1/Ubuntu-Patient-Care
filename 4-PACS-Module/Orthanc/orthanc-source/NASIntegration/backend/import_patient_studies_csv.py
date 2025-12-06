#!/usr/bin/env python3
"""
Robust importer for patient_studies.csv -> pacs_metadata.db

This script reads the CSV file line-by-line (resilient to encoding/whitespace)
and inserts rows into patients and studies tables. It reports counts at the end.
"""
import csv
import os
import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CSV_PATH = os.path.join(os.path.dirname(__file__), 'orthanc-index', 'readable_export_20251003_085303', 'patient_studies.csv')

try:
    from metadata_db import get_metadata_db_path
except Exception:
    from backend.metadata_db import get_metadata_db_path


def normalize_path(p):
    if not p:
        return ''
    # Convert UNC backslashes to python-friendly form
    return p.replace('\\\\', r'\\').strip()


def main():
    csv_path = CSV_PATH
    if not os.path.exists(csv_path):
        logger.error(f'CSV not found: {csv_path}')
        return

    db_path = get_metadata_db_path()
    logger.info(f'Target DB: {db_path}')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    inserted = 0
    skipped = 0
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            logger.error('Empty CSV')
            return
        # Map header columns to indices
        idx = {name.strip(): i for i, name in enumerate(header)}
        # Required columns: patient_id, patient_name, folder_path
        for row in reader:
            try:
                patient_id = row[idx.get('patient_id', '')].strip() if idx.get('patient_id') is not None else ''
                patient_name = row[idx.get('patient_name', '')].strip() if idx.get('patient_name') is not None else ''
                folder_path = row[idx.get('folder_path', '')].strip() if idx.get('folder_path') is not None else ''
                study_date = row[idx.get('study_date', '')].strip() if idx.get('study_date') is not None else ''
                study_description = row[idx.get('study_description', '')].strip() if idx.get('study_description') is not None else ''
                modality = row[idx.get('modality', '')].strip() if idx.get('modality') is not None else ''

                if not patient_id and not folder_path:
                    skipped += 1
                    continue

                folder_path = normalize_path(folder_path)

                # Insert patient
                cur.execute('INSERT OR IGNORE INTO patients(patient_id, patient_name, folder_path) VALUES(?,?,?)',
                            (patient_id or f'AUTO_{hash(folder_path)%100000}', patient_name, folder_path))
                study_uid = f"STUDY_{hash((patient_id or '') + folder_path)%100000}"
                cur.execute('INSERT OR IGNORE INTO studies(study_instance_uid, patient_id, study_date, study_description, modality, folder_path) VALUES(?,?,?,?,?,?)',
                            (study_uid, patient_id or '', study_date, study_description, modality, folder_path))
                inserted += 1
                if inserted % 500 == 0:
                    conn.commit()
            except Exception as e:
                skipped += 1
                continue

    conn.commit()
    # report counts
    cur.execute('SELECT COUNT(DISTINCT patient_id) FROM patients')
    patients_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(DISTINCT study_instance_uid) FROM studies')
    studies_count = cur.fetchone()[0]
    conn.close()
    logger.info(f'Inserted rows: {inserted}, skipped: {skipped}')
    logger.info(f'Patients in DB: {patients_count}, Studies in DB: {studies_count}')


if __name__ == '__main__':
    main()
