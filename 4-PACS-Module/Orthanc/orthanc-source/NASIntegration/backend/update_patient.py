#!/usr/bin/env python3
"""
Update existing patient record with today's CT scan
"""
import sqlite3
from datetime import datetime

def update_patient_record():
    conn = sqlite3.connect('orthanc-index/pacs_metadata.db')
    cursor = conn.cursor()

    # Update the existing record with today's study information
    cursor.execute('''
        UPDATE patient_studies 
        SET study_date = '20251030',
            study_description = 'CT SCAN - TODAY', 
            dicom_file_count = 3099,
            folder_size_mb = 2797.08,
            last_indexed = ?
        WHERE patient_id = '67208-20080612-081818-498-8326'
    ''', (datetime.now().isoformat(),))

    conn.commit()
    print('✅ Updated patient record with today\'s CT scan')

    # Verify update
    cursor.execute('SELECT study_date, dicom_file_count, folder_size_mb FROM patient_studies WHERE patient_name LIKE \'%SLAVTCHEV%\'')
    record = cursor.fetchone()
    print(f'📋 Updated record: Date={record[0]}, Files={record[1]}, Size={record[2]:.2f}MB')

    conn.close()

if __name__ == "__main__":
    update_patient_record()