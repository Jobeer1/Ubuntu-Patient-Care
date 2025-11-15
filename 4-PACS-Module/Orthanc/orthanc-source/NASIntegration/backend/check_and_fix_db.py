#!/usr/bin/env python3
"""
Check database schema and fix patient indexing
"""
import sqlite3
import os
import pydicom
from datetime import datetime, date

def check_and_fix_database():
    """Check database schema and update with today's CT scan"""
    db_path = 'orthanc-index/pacs_metadata.db'
    nas_path = r"\\155.235.81.155\Image Archiving\67208-20080612-0"
    
    print(f"🔍 Checking database schema...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check existing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Available tables: {tables}")
        
        # Check patient_studies schema if it exists
        if 'patient_studies' in tables:
            cursor.execute("PRAGMA table_info(patient_studies)")
            columns = cursor.fetchall()
            print(f"📋 patient_studies columns:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            # Check current records
            cursor.execute("SELECT * FROM patient_studies WHERE patient_name LIKE '%SLAVTCHEV%'")
            records = cursor.fetchall()
            print(f"📋 Current SLAVTCHEV records: {len(records)}")
            for record in records:
                print(f"  {record}")
        
        # Count today's files
        today = date.today()
        todays_files = []
        
        print(f"\n🔍 Checking files from today ({today})...")
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
            # Process one sample file to get study info
            sample_file = todays_files[0]
            print(f"🧪 Processing sample file: {os.path.basename(sample_file)}")
            
            try:
                dcm = pydicom.dcmread(sample_file, force=True)
                
                study_date = getattr(dcm, 'StudyDate', '').strip()
                study_time = getattr(dcm, 'StudyTime', '').strip()
                patient_name = str(getattr(dcm, 'PatientName', '')).strip()
                patient_id = getattr(dcm, 'PatientID', '').strip()
                modality = getattr(dcm, 'Modality', '').strip()
                
                print(f"📊 Study Info:")
                print(f"  Patient: {patient_name}")
                print(f"  Patient ID: {patient_id}")
                print(f"  Study Date: {study_date}")
                print(f"  Study Time: {study_time}")
                print(f"  Modality: {modality}")
                
                # Try to update/insert based on actual schema
                if 'patient_studies' in tables:
                    try:
                        # Simple update using existing columns
                        cursor.execute('''
                            INSERT OR REPLACE INTO patient_studies 
                            (patient_id, patient_name, study_date, folder_path, file_count, last_updated)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            patient_id,
                            patient_name,
                            study_date,
                            nas_path,
                            len(todays_files),
                            datetime.now().isoformat()
                        ))
                        
                        conn.commit()
                        print(f"✅ Successfully updated database with today's study!")
                        
                        # Verify the update
                        cursor.execute("SELECT * FROM patient_studies WHERE patient_name LIKE '%SLAVTCHEV%' ORDER BY study_date DESC")
                        updated_records = cursor.fetchall()
                        print(f"📋 Updated records:")
                        for record in updated_records:
                            print(f"  {record}")
                            
                    except Exception as e:
                        print(f"❌ Error updating database: {e}")
                        # Try alternative approach
                        print("🔧 Attempting alternative database update...")
                        
            except Exception as e:
                print(f"❌ Error reading DICOM file: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    check_and_fix_database()