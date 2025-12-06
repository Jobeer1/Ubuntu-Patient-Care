#!/usr/bin/env python3
"""
Clean up the database to remove the empty dicom_files table completely
"""

import sqlite3
import os

def clean_database():
    """Remove the dicom_files table and any other bloated tables"""
    try:
        from backend.metadata_db import get_metadata_db_path
        db_path = get_metadata_db_path()
    except Exception:
        db_path = "nas_patient_index.db"
    
    if not os.path.exists(db_path):
        print("❌ Database doesn't exist")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🧹 Cleaning up database...")
        
        # Get current tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        print("📋 Current tables:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   - {table}: {count} records")
        
        # Drop unnecessary tables
        tables_to_drop = ['dicom_files', 'patients', 'studies', 'series']
        
        for table in tables_to_drop:
            if table in tables:
                print(f"🗑️  Dropping table: {table}")
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
        
        # Clean up sqlite_sequence for dropped tables
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('patients', 'studies', 'series', 'dicom_files')")
        
        conn.commit()
        
        # Check final state
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        remaining_tables = [row[0] for row in cursor.fetchall()]
        
        print("\n✅ Final database tables:")
        for table in remaining_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   - {table}: {count} records")
        
        # Check database size
        conn.close()
        db_size = os.path.getsize(db_path)
        db_size_kb = db_size / 1024
        print(f"\n📊 Database size: {db_size_kb:.2f} KB")
        
        # Run VACUUM to compact database
        conn = sqlite3.connect(db_path)
        conn.execute("VACUUM")
        conn.close()
        
        db_size_after = os.path.getsize(db_path)
        db_size_after_kb = db_size_after / 1024
        print(f"📊 Database size after VACUUM: {db_size_after_kb:.2f} KB")
        
        return True
        
    except Exception as e:
        print(f"❌ Error cleaning database: {e}")
        return False

if __name__ == "__main__":
    print("🧹 Database Cleanup Script")
    print("=" * 40)
    
    success = clean_database()
    
    if success:
        print("\n✅ Database cleanup completed successfully!")
        print("🎯 Remaining tables should only contain lightweight metadata")
    else:
        print("\n❌ Database cleanup failed!")