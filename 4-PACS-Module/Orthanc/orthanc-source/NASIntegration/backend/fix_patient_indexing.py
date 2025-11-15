#!/usr/bin/env python3
"""
Fix patient indexing by manually processing today's CT files
"""
import sqlite3
import os
import pydicom
from datetime import datetime, date
import glob

def process_todays_files():
    """Process today's DICOM files for SLAVTCHEV KARLO"""
    nas_path = r"\\155.235.81.155\Image Archiving\67208-20080612-0"
    db_path = 'orthanc-index/pacs_metadata.db'
    
    print(f"🔍 Processing today's files in: {nas_path}")
    
    # Get today's date
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Count files from today
    todays_files = []
    total_files = 0
    
    try:
        for root, dirs, files in os.walk(nas_path):
            for file in files:
                if file.lower().endswith('.dcm'):
                    total_files += 1
                    file_path = os.path.join(root, file)
                    try:
                        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).date()
                        if mod_time == today:
                            todays_files.append(file_path)
                    except:
                        pass
    except Exception as e:
        print(f"❌ Error scanning directory: {e}")
        return
    
    print(f"📊 Total DICOM files in folder: {total_files}")
    print(f"📅 Files from today: {len(todays_files)}")
    
    if len(todays_files) > 0:
        print(f"🔍 Processing sample of today's files...")
        
        # Process a few sample files to extract study info
        study_info = {}
        processed = 0
        
        for file_path in todays_files[:10]:  # Sample first 10 files
            try:
                dcm = pydicom.dcmread(file_path, force=True)
                
                study_date = getattr(dcm, 'StudyDate', '').strip()
                study_time = getattr(dcm, 'StudyTime', '').strip()
                study_uid = getattr(dcm, 'StudyInstanceUID', '').strip()
                series_uid = getattr(dcm, 'SeriesInstanceUID', '').strip()
                patient_name = str(getattr(dcm, 'PatientName', '')).strip()
                patient_id = getattr(dcm, 'PatientID', '').strip()
                
                if study_uid not in study_info:
                    study_info[study_uid] = {
                        'study_date': study_date,
                        'study_time': study_time,
                        'patient_name': patient_name,
                        'patient_id': patient_id,
                        'series_count': 0,
                        'file_count': 0
                    }
                
                study_info[study_uid]['file_count'] += 1
                processed += 1
                
                print(f"✅ File {processed}: Study Date: {study_date}, Study UID: {study_uid[:20]}...")
                
            except Exception as e:
                print(f"⚠️  Error reading {file_path}: {e}")
        
        # Insert/update database records
        print(f"\n🔧 Updating database with new study information...")
        
        for study_uid, info in study_info.items():
            try:
                # Insert or update patient_studies table
                cursor.execute('''
                    INSERT OR REPLACE INTO patient_studies 
                    (patient_id, patient_name, study_date, study_uid, folder_path, file_count, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    info['patient_id'],
                    info['patient_name'], 
                    info['study_date'],
                    study_uid,
                    nas_path,
                    len(todays_files),  # Total files for today
                    datetime.now().isoformat()
                ))
                
                print(f"✅ Updated database for study: {info['study_date']} (UID: {study_uid[:20]}...)")
                
            except Exception as e:
                print(f"❌ Error updating database: {e}")
        
        conn.commit()
        print(f"💾 Database updated successfully!")
        
    else:
        print("⚠️  No files from today found")
    
    # Show current database contents for this patient
    print(f"\n🔍 Current database records for patient 67208:")
    cursor.execute('''
        SELECT patient_name, study_date, study_uid, file_count, last_updated 
        FROM patient_studies 
        WHERE patient_id LIKE '%67208%' OR patient_name LIKE '%SLAVTCHEV%'
        ORDER BY study_date DESC
    ''')
    
    rows = cursor.fetchall()
    for row in rows:
        print(f"  📋 {row[0]} | {row[1]} | Files: {row[3]} | Updated: {row[4]}")
    
    conn.close()

if __name__ == "__main__":
    process_todays_files()