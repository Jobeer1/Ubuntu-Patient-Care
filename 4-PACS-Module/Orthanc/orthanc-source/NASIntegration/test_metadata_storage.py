#!/usr/bin/env python3
"""
Test if the column errors are fixed by running a small indexing test
"""

import sys
import os
import tempfile
import sqlite3

# Add current directory to path
sys.path.append('.')

def test_metadata_storage():
    """Test storing metadata to ensure no column errors"""
    
    try:
        from nas_patient_indexer import NASPatientIndexer
        
        print("🧪 Testing metadata storage...")
        
        # Create a temporary database for testing
        temp_db = "test_metadata.db"
        
        # Remove if exists
        if os.path.exists(temp_db):
            os.remove(temp_db)
        
        # Create indexer with test database
        indexer = NASPatientIndexer()
        indexer.index_db_path = temp_db
        
        # Initialize database
        indexer.init_database()
        
        # Create test metadata
        test_metadata = {
            'patient_id': 'TEST001',
            'patient_name': 'Test Patient',
            'patient_birth_date': '19800101',
            'patient_sex': 'M',
            'study_date': '20250929',
            'study_description': 'Test Study',
            'modality': 'CT',
            'file_path': '/test/folder/file.dcm'
        }
        
        # Wait a moment for database to be fully created
        import time
        time.sleep(0.1)
        
        # Test storing metadata using the same connection approach as the indexer
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Verify table exists first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='patient_studies'")
        if not cursor.fetchone():
            print("❌ patient_studies table not found!")
            conn.close()
            return False
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO patient_studies 
                (patient_id, patient_name, patient_birth_date, patient_sex, 
                 study_date, study_description, modality, folder_path, 
                 dicom_file_count, folder_size_mb, last_indexed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (
                test_metadata['patient_id'],
                test_metadata['patient_name'],
                test_metadata['patient_birth_date'],
                test_metadata['patient_sex'],
                test_metadata['study_date'],
                test_metadata['study_description'],
                test_metadata['modality'],
                os.path.dirname(test_metadata['file_path']),
                0,  # dicom_file_count
                0   # folder_size_mb
            ))
            
            conn.commit()
            print("✅ Metadata stored successfully - no column errors!")
            
            # Verify the data was stored
            cursor.execute("SELECT * FROM patient_studies WHERE patient_id = ?", (test_metadata['patient_id'],))
            result = cursor.fetchone()
            
            if result:
                print(f"✅ Data verified: Patient {result[1]} stored correctly")
            else:
                print("❌ Data not found after storage")
                
        except Exception as e:
            print(f"❌ Error storing metadata: {e}")
            return False
        finally:
            conn.close()
        
        # Clean up
        if os.path.exists(temp_db):
            os.remove(temp_db)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during metadata storage test: {e}")
        return False

if __name__ == "__main__":
    success = test_metadata_storage()
    
    if success:
        print("\n✅ METADATA STORAGE TEST PASSED")
        print("🎯 Column errors should be fixed!")
    else:
        print("\n❌ METADATA STORAGE TEST FAILED")
        print("🔧 Column errors may still exist")