#!/usr/bin/env python3
"""
Quick test of NAS indexer
"""
import os
import sys
import time
import threading

# Add current directory to path
sys.path.insert(0, os.getcwd())

def test_indexer():
    print("🔍 Testing NAS Patient Indexer...")
    
    try:
        from nas_patient_indexer import NASPatientIndexer
        print("✅ Indexer imported successfully")
        
        # Create indexer instance
        try:
            from backend.metadata_db import get_metadata_db_path
            db_path = get_metadata_db_path()
        except Exception:
            try:
                from backend.metadata_db import get_metadata_db_path
                db_path = get_metadata_db_path()
            except Exception:
                db_path = 'backend\\nas_patient_index.db'
        indexer = NASPatientIndexer('Z:\\', db_path)
        print(f"✅ Indexer created for path: {indexer.nas_path}")
        print(f"✅ Database path: {indexer.db_path}")
        
        # Check if Z: drive exists and has files
        import os
        z_drive = "Z:\\"
        if os.path.exists(z_drive):
            print(f"✅ Z: drive accessible")
            
            # Count some DICOM files
            dicom_count = 0
            for root, dirs, files in os.walk(z_drive):
                for file in files:
                    if file.lower().endswith('.dcm'):
                        dicom_count += 1
                        if dicom_count >= 10:  # Stop after finding 10
                            break
                if dicom_count >= 10:
                    break
            
            print(f"✅ Found {dicom_count} DICOM files (sample)")
            
            if dicom_count > 0:
                print("🚀 Starting limited indexing run...")
                
                # Start indexing in background
                def run_indexing():
                    try:
                        indexer.run_full_index(max_workers=1)
                        print("✅ Indexing completed")
                    except Exception as e:
                        print(f"❌ Indexing error: {e}")
                
                thread = threading.Thread(target=run_indexing)
                thread.daemon = True
                thread.start()
                
                # Monitor for 30 seconds
                for i in range(6):
                    time.sleep(5)
                    try:
                        from backend.metadata_db import get_metadata_db_path
                        db_path = get_metadata_db_path()
                    except Exception:
                        db_path = 'backend\\nas_patient_index.db'
                    if os.path.exists(db_path):
                        size = os.path.getsize(db_path)
                        print(f"⏱️  After {(i+1)*5}s: Database size = {size} bytes")
                        if size > 0:
                            print("✅ Database is growing! Indexing is working.")
                            break
                    else:
                        print(f"⏱️  After {(i+1)*5}s: Database not created yet")
                
            else:
                print("❌ No DICOM files found on Z: drive")
        else:
            print("❌ Z: drive not accessible")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_indexer()