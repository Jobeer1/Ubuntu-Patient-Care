#!/usr/bin/env python3
"""
Check the database structure and content to debug search issues
"""

import sqlite3
import os

# Change to the correct directory
os.chdir(r"C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc\orthanc-source\NASIntegration")

print("🔍 Debugging NAS Patient Database")
print("=" * 50)

try:
    # Connect to database
    try:
        from backend.metadata_db import get_metadata_db_path
        db_path = get_metadata_db_path()
    except Exception:
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'nas_patient_index.db'))
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"📋 Tables in database: {tables}")
    
    if 'patient_studies' in tables:
        # Check record count
        cursor.execute("SELECT COUNT(*) FROM patient_studies")
        count = cursor.fetchone()[0]
        print(f"📊 Records in patient_studies: {count}")
        
        if count > 0:
            # Show sample records
            cursor.execute("SELECT patient_id, patient_name, study_date, folder_path FROM patient_studies LIMIT 5")
            records = cursor.fetchall()
            print(f"📄 Sample records:")
            for i, record in enumerate(records, 1):
                print(f"  {i}. ID: {record[0]}, Name: {record[1]}, Date: {record[2]}")
            
            # Check for VAN STRAATEN specifically
            cursor.execute("SELECT patient_id, patient_name, study_date FROM patient_studies WHERE patient_name LIKE '%VAN STRAATEN%' OR patient_name LIKE '%STRAATEN%'")
            straaten_records = cursor.fetchall()
            print(f"🔍 Records matching 'STRAATEN': {len(straaten_records)}")
            for record in straaten_records:
                print(f"  Found: {record[1]} (ID: {record[0]}, Date: {record[2]})")
                
            # Check for any recent records
            cursor.execute("SELECT patient_id, patient_name, study_date FROM patient_studies ORDER BY study_date DESC LIMIT 10")
            recent_records = cursor.fetchall()
            print(f"📅 Most recent records:")
            for record in recent_records:
                print(f"  {record[1]} - {record[2]}")
        else:
            print("⚠️ No records in patient_studies table!")
    else:
        print("❌ patient_studies table not found!")
        
        # Check if there are other patient tables
        for table in tables:
            if 'patient' in table.lower():
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"📊 Records in {table}: {count}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Database error: {e}")

# Also check the other database path
medical_module_db = r"C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc\medical-reporting-module\nas_patient_index.db"
if os.path.exists(medical_module_db):
    print(f"\n🔍 Found database in medical module: {medical_module_db}")
    try:
        conn = sqlite3.connect(medical_module_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM patient_studies")
        count = cursor.fetchone()[0]
        print(f"📊 Records in medical module database: {count}")
        conn.close()
    except Exception as e:
        print(f"❌ Medical module database error: {e}")

print("\n✅ Database check complete!")