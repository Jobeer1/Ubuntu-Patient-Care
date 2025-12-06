#!/usr/bin/env python3
"""
Compare patients table vs patient_studies table
"""
import sqlite3

def compare_tables():
    conn = sqlite3.connect('orthanc-index/pacs_metadata.db')
    cursor = conn.cursor()

    print('=== PATIENTS TABLE ===')
    cursor.execute('SELECT COUNT(*) FROM patients')
    print(f'Total records: {cursor.fetchone()[0]}')

    cursor.execute("SELECT * FROM patients WHERE patient_name LIKE '%SLAVTCHEV%'")
    rows = cursor.fetchall()
    print(f'SLAVTCHEV records: {len(rows)}')
    for row in rows:
        print(f'  {row}')

    print('\n=== PATIENT_STUDIES TABLE ===')
    cursor.execute('SELECT COUNT(*) FROM patient_studies')
    print(f'Total records: {cursor.fetchone()[0]}')

    cursor.execute("SELECT study_date, dicom_file_count FROM patient_studies WHERE patient_name LIKE '%SLAVTCHEV%' ORDER BY study_date")
    rows = cursor.fetchall()
    print(f'SLAVTCHEV records: {len(rows)}')
    for row in rows:
        print(f'  Date: {row[0]}, Files: {row[1]}')

    conn.close()

if __name__ == "__main__":
    compare_tables()