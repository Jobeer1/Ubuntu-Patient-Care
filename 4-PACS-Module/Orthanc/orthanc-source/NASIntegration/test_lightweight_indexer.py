#!/usr/bin/env python3
"""
Test script to verify the lightweight indexer works without creating dicom_files table
"""

import sqlite3
import os
import sys

def test_database_schema():
    """Test that the database only has lightweight tables"""
    try:
        from backend.metadata_db import get_metadata_db_path
        db_path = get_metadata_db_path()
    except Exception:
        try:
            from backend.metadata_db import get_metadata_db_path
            db_path = get_metadata_db_path()
        except Exception:
            db_path = "nas_patient_index.db"
    
    if not os.path.exists(db_path):
        print("❌ Database doesn't exist yet")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        print("📋 Current database tables:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   - {table}: {count} records")
        
        # Check if dicom_files table exists (it shouldn't)
        if 'dicom_files' in tables:
            print("❌ ERROR: dicom_files table still exists!")
            cursor.execute("SELECT COUNT(*) FROM dicom_files")
            count = cursor.fetchone()[0]
            print(f"   dicom_files has {count} records - THIS SHOULD BE 0!")
            return False
        else:
            print("✅ SUCCESS: No dicom_files table found (as expected)")
        
        # Check database size
        db_size = os.path.getsize(db_path)
        db_size_mb = db_size / (1024 * 1024)
        print(f"📊 Database size: {db_size_mb:.2f} MB")
        
        if db_size_mb > 10:  # Alert if over 10MB
            print(f"⚠️  WARNING: Database is {db_size_mb:.2f} MB - this might be too large")
        else:
            print(f"✅ Database size looks good: {db_size_mb:.2f} MB")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False

def test_indexer_import():
    """Test that the indexer can be imported without errors"""
    try:
        sys.path.append('.')
        import nas_patient_indexer
        print("✅ Indexer module imported successfully")
        
        # Check if NASPatientIndexer class exists
        if hasattr(nas_patient_indexer, 'NASPatientIndexer'):
            print("✅ NASPatientIndexer class found")
            return True
        else:
            print("❌ NASPatientIndexer class not found")
            return False
            
    except Exception as e:
        print(f"❌ Error importing indexer: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Lightweight Indexer System")
    print("=" * 50)
    
    # Test 1: Import check
    print("\n1. Testing indexer import...")
    import_ok = test_indexer_import()
    
    # Test 2: Database schema check
    print("\n2. Testing database schema...")
    schema_ok = test_database_schema()
    
    print("\n" + "=" * 50)
    if import_ok and schema_ok:
        print("✅ ALL TESTS PASSED - Lightweight indexer is working correctly!")
    else:
        print("❌ SOME TESTS FAILED - Check the issues above")
        
    print("\n🎯 Expected behavior:")
    print("   - No dicom_files table")
    print("   - Database under 10MB")
    print("   - Only patient metadata stored")
    print("   - No individual DICOM file records")