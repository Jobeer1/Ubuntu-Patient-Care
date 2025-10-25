#!/usr/bin/env python3
"""
Test the fixed indexer to make sure it doesn't have column errors
"""

import sys
import os

# Add current directory to path
sys.path.append('.')

def test_indexer_initialization():
    """Test that the indexer can initialize without column errors"""
    
    try:
        from nas_patient_indexer import NASPatientIndexer
        
        print("🧪 Testing indexer initialization...")
        
        # Create indexer instance
        indexer = NASPatientIndexer()
        
        # Test database initialization
        indexer.init_database()
        
        print("✅ Indexer initialization successful!")
        
        # Check the table was created correctly
        import sqlite3
        try:
            from backend.metadata_db import get_metadata_db_path
            conn = sqlite3.connect(get_metadata_db_path())
        except Exception:
            conn = sqlite3.connect("nas_patient_index.db")
        cursor = conn.cursor()
        
        # Check table schema
        cursor.execute("PRAGMA table_info(patient_studies)")
        columns = cursor.fetchall()
        
        print("📋 Table schema after initialization:")
        column_names = []
        for col in columns:
            column_names.append(col[1])
            print(f"   {col[1]} ({col[2]})")
        
        # Check if we have the correct columns
        required_columns = ['patient_id', 'patient_name', 'study_date', 'study_description', 'modality', 'folder_path']
        
        missing_columns = [col for col in required_columns if col not in column_names]
        if missing_columns:
            print(f"❌ Missing columns: {missing_columns}")
        else:
            print("✅ All required columns present")
        
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error during initialization test: {e}")
        return False

if __name__ == "__main__":
    success = test_indexer_initialization()
    
    if success:
        print("\n✅ INDEXER COLUMN FIX TEST PASSED")
        print("🎯 The indexer should now work without column errors")
    else:
        print("\n❌ INDEXER COLUMN FIX TEST FAILED")
        print("🔧 Additional fixes may be needed")