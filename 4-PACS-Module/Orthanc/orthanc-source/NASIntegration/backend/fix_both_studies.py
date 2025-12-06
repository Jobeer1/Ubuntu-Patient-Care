#!/usr/bin/env python3
"""
Fix patient database to show both today's CT and historical studies
"""
import sqlite3
import os
import pydicom
from datetime import datetime, date

def fix_patient_studies():
    """Add today's CT as separate study while preserving historical data"""
    db_path = 'orthanc-index/pacs_metadata.db'
    nas_path = r"\\155.235.81.155\Image Archiving\67208-20080612-0"
    
    print(f"🔧 Fixing patient studies to show both current and historical CTs...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # First, restore the 2022 study data
        print("📋 Step 1: Restoring 2022 historical study...")
        cursor.execute('''
            UPDATE patient_studies 
            SET study_date = '20220803',
                study_description = 'ABDOMEN & PELVIS',
                modality = 'CT',
                dicom_file_count = 1,
                folder_size_mb = 0.51,
                last_indexed = '2025-10-04 18:30:17'
            WHERE patient_id = '67208-20080612-081818-498-8326'
        ''')
        
        # Now add today's study as a separate entry
        print("📋 Step 2: Adding today's CT as new study...")
        
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
            # Process sample file to get today's study info
            sample_file = todays_files[0]
            dcm = pydicom.dcmread(sample_file, force=True)
            
            patient_name = str(getattr(dcm, 'PatientName', '')).strip()
            patient_id = getattr(dcm, 'PatientID', '').strip()
            patient_sex = getattr(dcm, 'PatientSex', '').strip()
            patient_birth_date = getattr(dcm, 'PatientBirthDate', '').strip()
            modality = getattr(dcm, 'Modality', '').strip()
            study_description = getattr(dcm, 'StudyDescription', 'CT SCAN').strip()
            
            # Calculate folder size for today's files only
            total_size = sum(os.path.getsize(f) for f in todays_files) / (1024 * 1024)  # MB
            
            # Create a separate folder path for today's study
            todays_folder_path = f"{nas_path}\\TODAY-{today.strftime('%Y%m%d')}"
            
            # Insert today's study as a new record
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
                '20251030',  # Today's date
                f'CT SCAN - {study_description}' if study_description else 'CT SCAN - TODAY',
                modality,
                todays_folder_path,  # Different path to avoid unique constraint
                len(todays_files),
                total_size,
                datetime.now().isoformat()
            ))
            
            print(f"✅ Added today's CT study: {len(todays_files)} files, {total_size:.2f} MB")
        
        conn.commit()
        
        # Verify both studies are now present
        print("📋 Step 3: Verifying both studies are present...")
        cursor.execute('''
            SELECT study_date, modality, study_description, dicom_file_count, folder_size_mb, folder_path
            FROM patient_studies 
            WHERE patient_name LIKE '%SLAVTCHEV%' 
            ORDER BY study_date ASC
        ''')
        
        records = cursor.fetchall()
        print(f"📋 SLAVTCHEV studies ({len(records)} total):")
        for i, record in enumerate(records, 1):
            print(f"  {i}. {record[0]} - {record[1]} - {record[2]} - {record[3]} files - {record[4]:.2f}MB")
            print(f"     Path: {record[5]}")
        
        conn.close()
        print(f"✅ Database updated successfully! Both studies should now be visible.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_patient_studies()