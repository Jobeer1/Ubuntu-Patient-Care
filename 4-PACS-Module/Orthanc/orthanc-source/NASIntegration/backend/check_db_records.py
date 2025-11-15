#!/usr/bin/env python3
"""
Check database records directly
"""
import sqlite3

def check_database():
    conn = sqlite3.connect('orthanc-index/pacs_metadata.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT study_date, dicom_file_count, folder_size_mb, study_description, folder_path 
        FROM patient_studies 
        WHERE patient_name LIKE '%SLAVTCHEV%' 
        ORDER BY study_date
    ''')
    
    records = cursor.fetchall()
    print(f'Records in database: {len(records)}')
    for i, record in enumerate(records, 1):
        print(f'{i}. Date: {record[0]}, Files: {record[1]}, Size: {record[2]:.2f}MB')
        print(f'   Desc: {record[3]}')
        print(f'   Path: {record[4]}')
        print()
    
    conn.close()

if __name__ == "__main__":
    check_database()