#!/usr/bin/env python3
"""
PACS System Test and Setup
=========================

Tests the new high-performance PACS system for Ubuntu Patient Care.
Installs dependencies and runs quick functionality tests.
"""

import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def install_dependencies():
    """Install required Python packages"""
    packages = [
        'pydicom',  # DICOM file reading
        'flask',    # Web framework 
        'flask-cors',  # CORS support
        'sqlite3'   # Database (usually built-in)
    ]
    
    logger.info("📦 Installing PACS dependencies...")
    
    for package in packages:
        try:
            if package == 'sqlite3':
                # sqlite3 is usually built-in to Python
                import sqlite3
                logger.info(f"✅ {package} already available")
                continue
                
            logger.info(f"Installing {package}...")
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', package
            ], capture_output=True)
            logger.info(f"✅ {package} installed successfully")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to install {package}: {e}")
        except ImportError:
            logger.warning(f"⚠️ {package} not found but may be available")

def test_nas_access():
    """Test access to the NAS drive"""
    logger.info("🔍 Testing NAS access...")
    
    nas_path = "Z:"
    if os.path.exists(nas_path):
        logger.info(f"✅ NAS accessible at {nas_path}")
        
        # Test Felix Maxwell folder
        felix_pattern = "Z:\\639380-20250922-*"
        try:
            import glob
            felix_folders = glob.glob(felix_pattern)
            if felix_folders:
                logger.info(f"✅ Found Felix Maxwell folder: {felix_folders[0]}")
                return True
            else:
                logger.warning(f"⚠️ Felix Maxwell folder not found with pattern: {felix_pattern}")
                return False
        except Exception as e:
            logger.error(f"❌ Error searching for Felix Maxwell folder: {e}")
            return False
    else:
        logger.error(f"❌ NAS not accessible at {nas_path}")
        return False

def test_dicom_reading():
    """Test DICOM file reading capability"""
    logger.info("📄 Testing DICOM reading...")
    
    try:
        import pydicom
        logger.info("✅ pydicom imported successfully")
        
        # Try to find a DICOM file to test with
        import glob
        dicom_files = glob.glob("Z:\\639380-20250922-*\\**\\*", recursive=True)
        
        for file_path in dicom_files[:5]:  # Test first 5 files
            if os.path.isfile(file_path):
                try:
                    ds = pydicom.dcmread(file_path, stop_before_pixels=True)
                    patient_name = str(getattr(ds, 'PatientName', 'Unknown'))
                    logger.info(f"✅ Successfully read DICOM: {patient_name}")
                    return True
                except Exception as e:
                    logger.debug(f"Skipping non-DICOM file {file_path}: {e}")
                    continue
        
        logger.warning("⚠️ No readable DICOM files found")
        return False
        
    except ImportError:
        logger.error("❌ pydicom not available")
        return False

def quick_index_test():
    """Run a quick indexing test on Felix Maxwell's folder"""
    logger.info("🚀 Running quick PACS index test...")
    
    try:
        # Import our PACS indexer
        from pacs_indexer import PACSIndexer
        
        # Create test indexer for just Felix Maxwell's folder
        import glob
        felix_folders = glob.glob("Z:\\639380-20250922-*")
        
        if not felix_folders:
            logger.error("❌ Felix Maxwell folder not found")
            return False
            
        felix_folder = felix_folders[0]
        logger.info(f"📁 Testing with folder: {felix_folder}")
        
        # Create small test database
        test_indexer = PACSIndexer(felix_folder, "test_pacs.db")
        test_indexer.init_database()
        
        # Scan just Felix's folder
        logger.info("🔍 Scanning Felix Maxwell's DICOM files...")
        
        import os
        dicom_count = 0
        for root, dirs, files in os.walk(felix_folder):
            for file in files:
                if file.lower().endswith(('.dcm', '.dicom', '.ima')) or '.' not in file:
                    file_path = os.path.join(root, file)
                    metadata = test_indexer.extract_dicom_metadata(file_path)
                    
                    if metadata:
                        patient_name = metadata['patient']['patient_name']
                        patient_id = metadata['patient']['patient_id']
                        study_date = metadata['study']['study_date']
                        
                        logger.info(f"✅ Found patient: {patient_name} (ID: {patient_id}, Date: {study_date})")
                        dicom_count += 1
                        
                        if dicom_count >= 3:  # Test first 3 files only
                            break
            
            if dicom_count >= 3:
                break
        
        if dicom_count > 0:
            logger.info(f"✅ Successfully processed {dicom_count} DICOM files")
            return True
        else:
            logger.error("❌ No DICOM files processed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Quick index test failed: {e}")
        return False

def main():
    """Main test function"""
    logger.info("🏥 Ubuntu Patient Care - PACS System Test")
    logger.info("=" * 60)
    
    # Test results
    results = {
        'dependencies': False,
        'nas_access': False,
        'dicom_reading': False,
        'index_test': False
    }
    
    # Run tests
    try:
        install_dependencies()
        results['dependencies'] = True
    except Exception as e:
        logger.error(f"Dependencies test failed: {e}")
    
    try:
        results['nas_access'] = test_nas_access()
    except Exception as e:
        logger.error(f"NAS access test failed: {e}")
    
    try:
        results['dicom_reading'] = test_dicom_reading()
    except Exception as e:
        logger.error(f"DICOM reading test failed: {e}")
    
    try:
        results['index_test'] = quick_index_test()
    except Exception as e:
        logger.error(f"Index test failed: {e}")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("🎯 PACS System Test Results:")
    logger.info(f"   Dependencies: {'✅ PASS' if results['dependencies'] else '❌ FAIL'}")
    logger.info(f"   NAS Access: {'✅ PASS' if results['nas_access'] else '❌ FAIL'}")
    logger.info(f"   DICOM Reading: {'✅ PASS' if results['dicom_reading'] else '❌ FAIL'}")
    logger.info(f"   Index Test: {'✅ PASS' if results['index_test'] else '❌ FAIL'}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n🎉 All tests passed! PACS system is ready.")
        logger.info("Next steps:")
        logger.info("1. Start full NAS indexing: python pacs_indexer.py")
        logger.info("2. Test patient search: POST /api/pacs/search/patients")
        logger.info("3. Access patient images directly from NAS paths")
    else:
        logger.error("\n❌ Some tests failed. Check the logs above.")
        
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)