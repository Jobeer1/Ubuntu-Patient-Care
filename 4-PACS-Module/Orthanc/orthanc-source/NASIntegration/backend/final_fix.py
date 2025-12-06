#!/usr/bin/env python3
"""
Final fix for patient indexing with correct database schema
"""
import sqlite3
import os
import pydicom
from datetime import datetime, date

def final_fix():
    """Fix patient indexing with correct database schema"""
    db_path = 'orthanc-index/pacs_metadata.db'
    nas_path = r"\\155.235.81.155\Image Archiving\67208-20080612-0"
    
    print(f"🔧 Final fix for SLAVTCHEV KARLO patient...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Count today's files
        today = date.today()
        todays_files = []
        
        for root, dirs, files in os.walk(nas_path):
            for file in files:
                if file.lower().endswith('.dcm'):
                    file_path = os.path.join(root, file)
                    try:
                        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).date()
                        if mod_time == today:
                            todays_files.append(file_path)
                    except:
                        pass
        
        print(f"📅 Found {len(todays_files)} files from today")
        
        if len(todays_files) > 0:
            # Process sample file to get study info
            sample_file = todays_files[0]
            dcm = pydicom.dcmread(sample_file, force=True)
            
            study_date = getattr(dcm, 'StudyDate', '').strip()
            study_time = getattr(dcm, 'StudyTime', '').strip()
            patient_name = str(getattr(dcm, 'PatientName', '')).strip()
            patient_id = getattr(dcm, 'PatientID', '').strip()
            patient_sex = getattr(dcm, 'PatientSex', '').strip()
            patient_birth_date = getattr(dcm, 'PatientBirthDate', '').strip()
            modality = getattr(dcm, 'Modality', '').strip()
            study_description = getattr(dcm, 'StudyDescription', '').strip()
            
            # Calculate folder size
            total_size = sum(os.path.getsize(f) for f in todays_files) / (1024 * 1024)  # MB
            
            print(f"📊 Today's Study Info:")
            print(f"  Patient: {patient_name}")
            print(f"  Patient ID: {patient_id}")
            print(f"  Study Date: {study_date}")
            print(f"  Modality: {modality}")
            print(f"  Description: {study_description}")
            print(f"  File Count: {len(todays_files)}")
            print(f"  Total Size: {total_size:.2f} MB")
            
            # Insert new record with correct column names
            cursor.execute('''
                INSERT INTO patient_studies 
                (patient_id, patient_name, patient_birth_date, patient_sex, 
                 study_date, study_description, modality, folder_path, 
                 dicom_file_count, folder_size_mb, last_indexed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient_id,
                patient_name,
                patient_birth_date,
                patient_sex,
                study_date,
                study_description,
                modality,
                nas_path,
                len(todays_files),
                total_size,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            print(f"✅ Successfully added today's CT study to database!")
            
            # Verify the update
            cursor.execute('''
                SELECT study_date, modality, study_description, dicom_file_count, folder_size_mb 
                FROM patient_studies 
                WHERE patient_name LIKE '%SLAVTCHEV%' 
                ORDER BY study_date DESC
            ''')
            
            records = cursor.fetchall()
            print(f"📋 All SLAVTCHEV studies:")
            for i, record in enumerate(records, 1):
                print(f"  {i}. Date: {record[0]}, {record[1]}, {record[2]}, Files: {record[3]}, Size: {record[4]:.2f} MB")
        
        conn.close()
        print(f"💾 Database update completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    final_fix()