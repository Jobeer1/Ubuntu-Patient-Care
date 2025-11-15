#!/usr/bin/env python3
"""
Check patient data in the NAS index database
"""
import sqlite3
import os
from datetime import datetime

def check_patient_data():
    db_path = 'orthanc-index/pacs_metadata.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check indexing status
        print("=== INDEXING STATUS ===")
        try:
            cursor.execute('SELECT * FROM indexing_status ORDER BY timestamp DESC LIMIT 5')
            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    print(f"Indexing: {row}")
            else:
                print("No indexing status found")
        except Exception as e:
            print(f"No indexing_status table: {e}")
        
        # Check for SLAVTCHEV KARLO patient
        print("\n=== PATIENT SEARCH: SLAVTCHEV KARLO ===")
        try:
            # Try different table names
            tables_to_check = ['patient_studies', 'patients', 'studies']
            
            for table in tables_to_check:
                try:
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                    if cursor.fetchone():
                        print(f"\nChecking table: {table}")
                        cursor.execute(f"SELECT * FROM {table} WHERE patient_name LIKE '%SLAVTCHEV%' OR patient_name LIKE '%KARLO%'")
                        rows = cursor.fetchall()
                        if rows:
                            for row in rows:
                                print(f"Found: {row}")
                        else:
                            print("No matching records found")
                except Exception as e:
                    print(f"Error checking {table}: {e}")
        except Exception as e:
            print(f"Error searching patient: {e}")
        
        # Check all tables in database
        print("\n=== DATABASE STRUCTURE ===")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Available tables: {[t[0] for t in tables]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

def check_nas_folder():
    """Check the NAS folder directly for recent files"""
    nas_path = r"\\155.235.81.155\Image Archiving"
    patient_folder = "67208-20080612-0"
    
    print(f"\n=== CHECKING NAS FOLDER DIRECTLY ===")
    print(f"Looking in: {nas_path}")
    
    try:
        if os.path.exists(nas_path):
            # Look for patient folders
            for item in os.listdir(nas_path):
                if "67208" in item or "SLAVTCHEV" in item.upper() or "KARLO" in item.upper():
                    full_path = os.path.join(nas_path, item)
                    if os.path.isdir(full_path):
                        print(f"Found patient folder: {item}")
                        try:
                            # Check for recent files (today)
                            today = datetime.now().date()
                            for root, dirs, files in os.walk(full_path):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    try:
                                        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).date()
                                        if mod_time == today:
                                            print(f"  📅 TODAY'S FILE: {file_path}")
                                            print(f"    Modified: {datetime.fromtimestamp(os.path.getmtime(file_path))}")
                                    except:
                                        pass
                        except Exception as e:
                            print(f"Error scanning folder {item}: {e}")
        else:
            print(f"❌ NAS path not accessible: {nas_path}")
    except Exception as e:
        print(f"❌ Error accessing NAS: {e}")

if __name__ == "__main__":
    check_patient_data()
    check_nas_folder()