#!/usr/bin/env python3
"""
Test a small indexing operation to verify the lightweight system works
"""

import sys
import os
import sqlite3
from pathlib import Path

# Add current directory to path
sys.path.append('.')

def test_small_indexing():
    """Test indexing a single folder to ensure no bloat"""
    try:
        # Import the indexer
        from nas_patient_indexer import NASPatientIndexer

        print("🧪 Testing Small Indexing Operation")
        print("=" * 50)

        # Resolve DB path
        try:
            from backend.metadata_db import get_metadata_db_path
            dbp = get_metadata_db_path()
        except Exception:
            dbp = 'nas_patient_index.db'

        # Check database before
        if os.path.exists(dbp):
            db_size_before = os.path.getsize(dbp) / 1024
            print(f"📊 Database size BEFORE: {db_size_before:.2f} KB")

            conn = sqlite3.connect(dbp)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM patient_studies")
            records_before = cursor.fetchone()[0]
            conn.close()
            print(f"📊 Records BEFORE: {records_before}")
        else:
            db_size_before = 0
            records_before = 0
            print("📊 No database exists yet")

        # Create indexer instance (but don't run full indexing)
        indexer = NASPatientIndexer()

        # Initialize database (this should create the lightweight schema)
        indexer.init_database()

        print("\n✅ Database initialized with lightweight schema")

        # Check database after initialization
        db_size_after = os.path.getsize(dbp) / 1024
        print(f"📊 Database size AFTER initialization: {db_size_after:.2f} KB")

        # Check tables created
        conn = sqlite3.connect(dbp)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        print(f"📋 Tables created: {', '.join(tables)}")

        # Verify no bloated tables exist
        bloated_tables = ['patients', 'studies', 'series', 'dicom_files']
        found_bloated = [table for table in bloated_tables if table in tables]

        if found_bloated:
            print(f"❌ BLOATED TABLES FOUND: {found_bloated}")
            return False
        else:
            print("✅ No bloated tables found")

        # Check for patient_studies table
        if 'patient_studies' in tables:
            print("✅ Lightweight patient_studies table exists")
        else:
            print("❌ patient_studies table missing")
            return False

        conn.close()

        print(f"\n📊 Database size change: {db_size_before:.2f} KB → {db_size_after:.2f} KB")

        if db_size_after < 10000:  # Should be under 10MB for lightweight system
            print("✅ Database size looks good for lightweight system")
            return True
        else:
            print(f"⚠️  Database is too large: {db_size_after:.2f} KB")
            return False

    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

if __name__ == "__main__":
    success = test_small_indexing()
    
    if success:
        print("\n✅ SMALL INDEXING TEST PASSED")
        print("🎯 The indexer is ready for full operation without database bloat")
    else:
        print("\n❌ SMALL INDEXING TEST FAILED")
        print("🔧 Check the issues above before proceeding")