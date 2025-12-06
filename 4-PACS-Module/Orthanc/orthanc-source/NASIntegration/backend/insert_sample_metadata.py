#!/usr/bin/env python3
"""
Insert a small, safe sample of patient/study/series/instance rows into the pacs_metadata.db
This creates only file-path records (no pixel data) to verify APIs and indexing work.
"""
import sqlite3
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from metadata_db import get_metadata_db_path
except Exception:
    from backend.metadata_db import get_metadata_db_path


def insert_sample():
    db_path = get_metadata_db_path()
    db_path = os.path.abspath(db_path)
    logger.info(f"Using DB: {db_path}")
    Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Sample data (safe): no real patient data. Replace later with real scan results.
    patient_id = 'SAMPLE_PAT_001'
    patient_name = 'Sample Patient'
    folder_path = 'Z:/SAMPLE_PAT_001'

    study_uid = '1.2.840.SAMPLE.STUDY.1'
    series_uid = '1.2.840.SAMPLE.SERIES.1'
    sop_uid = '1.2.840.SAMPLE.SOP.1'
    file_path = 'Z:/SAMPLE_PAT_001/IMG0001.dcm'

    try:
        cur.execute('INSERT OR IGNORE INTO patients(patient_id, patient_name, folder_path) VALUES(?,?,?)',
                    (patient_id, patient_name, folder_path))
        cur.execute('INSERT OR IGNORE INTO studies(study_instance_uid, patient_id, folder_path) VALUES(?,?,?)',
                    (study_uid, patient_id, folder_path))
        cur.execute('INSERT OR IGNORE INTO series(series_instance_uid, study_instance_uid, folder_path) VALUES(?,?,?)',
                    (series_uid, study_uid, folder_path))
        cur.execute('INSERT OR REPLACE INTO instances(sop_instance_uid, series_instance_uid, instance_number, file_path, file_size) VALUES(?,?,?,?,?)',
                    (sop_uid, series_uid, 1, file_path, 0))

        conn.commit()

        logger.info('Sample metadata inserted successfully')

        # Print inserted rows
        for row in cur.execute('SELECT patient_id, patient_name, folder_path FROM patients'):
            print('PATIENT:', row)
        for row in cur.execute('SELECT study_instance_uid, patient_id, folder_path FROM studies'):
            print('STUDY: ', row)
        for row in cur.execute('SELECT series_instance_uid, study_instance_uid, folder_path FROM series'):
            print('SERIES:', row)
        for row in cur.execute('SELECT sop_instance_uid, series_instance_uid, file_path FROM instances'):
            print('INSTANCE:', row)

    except Exception as e:
        logger.error(f'Failed to insert sample metadata: {e}')
    finally:
        conn.close()


if __name__ == '__main__':
    insert_sample()
