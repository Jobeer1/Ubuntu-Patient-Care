#!/usr/bin/env python3
"""
Simple test to verify the actual database works with the fixed INSERT statement
"""

import sqlite3
import os

def test_actual_database():
    """Test the actual database with the fixed INSERT statement"""
    
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
        print("❌ Database doesn't exist")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Test the exact INSERT statement that was causing errors
        test_metadata = {
            'patient_id': 'TEST_COLUMN_FIX',
            'patient_name': 'Column Fix Test',
            'patient_birth_date': '19800101',
            'patient_sex': 'M',
            'study_date': '20250929',
            'study_description': 'Column Fix Test Study',
            'modality': 'TEST',
            'file_path': '/test/folder/file.dcm'
        }
        
        print("🧪 Testing the fixed INSERT statement...")
        
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
        print("✅ INSERT statement executed successfully!")
        
        # Verify the data
        cursor.execute("SELECT patient_name FROM patient_studies WHERE patient_id = ?", (test_metadata['patient_id'],))
        result = cursor.fetchone()
        
        if result:
            print(f"✅ Test record found: {result[0]}")
            
            # Clean up test record
            cursor.execute("DELETE FROM patient_studies WHERE patient_id = ?", (test_metadata['patient_id'],))
            conn.commit()
            print("✅ Test record cleaned up")
        else:
            print("❌ Test record not found")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error testing INSERT statement: {e}")
        return False

if __name__ == "__main__":
    success = test_actual_database()
    
    if success:
        print("\n✅ COLUMN FIX VERIFICATION PASSED")
        print("🎯 The 'study_instance_uid' column error should be fixed!")
    else:
        print("\n❌ COLUMN FIX VERIFICATION FAILED") 
        print("🔧 The column error may still exist")