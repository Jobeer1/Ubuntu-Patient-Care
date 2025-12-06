#!/usr/bin/env python3
"""
Check the current patient_studies table schema
"""

import sqlite3
import os

def check_table_schema():
    """Check the current patient_studies table schema"""
    try:
        from backend.metadata_db import get_metadata_db_path
        db_path = get_metadata_db_path()
    except Exception:
        db_path = "nas_patient_index.db"
    
    if not os.path.exists(db_path):
        print("❌ Database doesn't exist")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute("PRAGMA table_info(patient_studies)")
        columns = cursor.fetchall()
        
        print("📋 Current patient_studies table schema:")
        for col in columns:
            print(f"   {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'}")
        
        # Check if study_instance_uid column exists
        column_names = [col[1] for col in columns]
        if 'study_instance_uid' in column_names:
            print("✅ study_instance_uid column EXISTS")
        else:
            print("❌ study_instance_uid column MISSING")
            print(f"📝 Available columns: {', '.join(column_names)}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking schema: {e}")

if __name__ == "__main__":
    check_table_schema()