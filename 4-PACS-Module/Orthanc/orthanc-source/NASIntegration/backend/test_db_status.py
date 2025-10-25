#!/usr/bin/env python3
"""
Test the current database status
"""

import sqlite3
import os

# Check current database
try:
    from backend.metadata_db import get_metadata_db_path
    db_path = get_metadata_db_path()
except Exception:
    try:
        from backend.metadata_db import get_metadata_db_path
        db_path = get_metadata_db_path()
    except Exception:
        db_path = "nas_patient_index.db"
if os.path.exists(db_path):
    size_kb = os.path.getsize(db_path) / 1024
    print(f"📊 Current database size: {size_kb:.2f} KB")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check what tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"📋 Tables: {[t[0] for t in tables]}")
    
    # Check patient count
    try:
        cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_studies")
        patient_count = cursor.fetchone()[0]
        print(f"👥 Patient count: {patient_count}")
        
        # Sample patients
        cursor.execute("SELECT patient_id, patient_name FROM patient_studies LIMIT 5")
        samples = cursor.fetchall()
        print("📝 Sample patients:")
        for patient in samples:
            print(f"   - {patient[0]}: {patient[1]}")
            
    except Exception as e:
        print(f"❌ Error querying patients: {e}")
    
    conn.close()
else:
    print("❌ Database not found")