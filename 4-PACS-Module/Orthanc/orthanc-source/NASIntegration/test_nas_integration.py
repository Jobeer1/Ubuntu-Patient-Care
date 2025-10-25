#!/usr/bin/env python3
"""
Test the enhanced NAS integration for Ubuntu Patient Care
Verify that the new indexing and search system works properly
"""

import os
import sys
import logging
import requests
import json
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_nas_integration():
    """Test the NAS integration system"""
    logger.info("🏥 Testing Ubuntu Patient Care NAS Integration")
    logger.info("=" * 60)
    
    base_url = "http://localhost:5000"
    
    # Test 1: Check if NAS is accessible
    logger.info("1️⃣ Testing NAS accessibility...")
    nas_path = Path("Z:\\")
    if nas_path.exists():
        logger.info(f"✅ NAS accessible at {nas_path}")
        
        # Count some folders
        try:
            folders = list(nas_path.iterdir())
            logger.info(f"   📁 Found {len(folders)} items in NAS root")
            
            # Look for Felix Maxwell folder
            felix_folders = [f for f in folders if f.is_dir() and "639380-20250922" in f.name]
            if felix_folders:
                logger.info(f"   🎯 Found Felix Maxwell folder: {felix_folders[0].name}")
            else:
                logger.warning("   ⚠️ Felix Maxwell folder not found in root")
                
        except Exception as e:
            logger.error(f"   ❌ Error accessing NAS: {e}")
    else:
        logger.error("❌ NAS not accessible - Z: drive not found")
        return False
    
    # Test 2: Check indexing status
    logger.info("\n2️⃣ Testing indexing status...")
    try:
        response = requests.get(f"{base_url}/api/nas/index/status", timeout=10)
        if response.status_code == 200:
            status_data = response.json()
            logger.info("✅ Indexing status endpoint working")
            logger.info(f"   Status: {status_data.get('indexing', {}).get('status', 'unknown')}")
            logger.info(f"   Available: {status_data.get('available', False)}")
            
            if not status_data.get('available'):
                logger.info("   💡 Index not available - will need to run indexing")
        else:
            logger.error(f"❌ Status check failed: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Error checking status: {e}")
    
    # Test 3: Login and test search
    logger.info("\n3️⃣ Testing patient search...")
    session = requests.Session()
    
    # Login
    try:
        login_data = {
            "username": "admin",
            "password": "admin",
            "user_type": "admin"
        }
        
        login_response = session.post(f"{base_url}/api/auth/login", json=login_data, timeout=10)
        
        if login_response.status_code == 200:
            logger.info("✅ Login successful")
            
            # Test search
            search_data = {
                "patient_id": "FELIX",
                "patient_name": "FELIX MAXWELL",
                "study_date": "",
                "modality": ""
            }
            
            search_response = session.post(f"{base_url}/api/nas/search/patient", 
                                        json=search_data, timeout=30)
            
            if search_response.status_code == 200:
                search_results = search_response.json()
                logger.info("✅ Patient search working")
                logger.info(f"   Found {search_results.get('total_found', 0)} patients")
                logger.info(f"   Source: {search_results.get('source', 'unknown')}")
                
                # Show first patient
                patients = search_results.get('patients', [])
                if patients:
                    patient = patients[0]
                    logger.info(f"   First patient: {patient.get('name', 'Unknown')} (ID: {patient.get('patient_id', 'N/A')})")
                    logger.info(f"   Studies: {len(patient.get('studies', []))}")
                
                # Check if we got the right patient
                for patient in patients:
                    if "FELIX" in patient.get('name', '').upper() or "MAXWELL" in patient.get('name', '').upper():
                        logger.info(f"🎯 Found Felix Maxwell: {patient['name']} (ID: {patient['patient_id']})")
                        break
                else:
                    logger.warning("⚠️ Felix Maxwell not found in search results")
                
            else:
                logger.error(f"❌ Search failed: {search_response.status_code}")
                logger.error(f"   Response: {search_response.text}")
        else:
            logger.error(f"❌ Login failed: {login_response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Search test failed: {e}")
    
    # Test 4: Check if we should run indexing
    logger.info("\n4️⃣ Recommendations...")
    
    # Check if index exists
    try:
        from backend.metadata_db import get_metadata_db_path
        index_file = Path(get_metadata_db_path())
    except Exception:
        index_file = Path("nas_patient_index.db")
    if index_file.exists():
        logger.info(f"✅ Patient index database exists ({index_file.stat().st_size / 1024 / 1024:.1f} MB)")
        logger.info("   💡 You can search patients using the existing index")
    else:
        logger.warning("⚠️ Patient index database not found")
        logger.info("   💡 RECOMMENDATION: Run full indexing to scan your 11TB NAS")
        logger.info("   📋 This will create a searchable database of all 9300+ patients")
        logger.info("   🚀 Use the 'Start Indexing' button in the web interface")
    
    logger.info("\n" + "=" * 60)
    logger.info("🏥 Test completed!")
    
    return True

def start_manual_indexing():
    """Start indexing manually for testing"""
    logger.info("🚀 Starting manual NAS indexing...")
    
    try:
        # Add current directory to path
        sys.path.append(os.path.dirname(__file__))
        
        from nas_patient_indexer import NASPatientIndexer
        
        # Create indexer
        indexer = NASPatientIndexer(nas_path="Z:\\")
        
        # Run a small test (limit to first 5 folders)
        logger.info("Running test indexing (first 5 patient folders)...")
        
        # Get patient folders
        patient_folders = indexer.scan_patient_folders()
        
        if patient_folders:
            logger.info(f"Found {len(patient_folders)} patient folders")
            
            # Index first 5 for testing
            test_folders = patient_folders[:5]
            logger.info(f"Testing with first {len(test_folders)} folders...")
            
            indexer.init_database()
            
            for folder in test_folders:
                logger.info(f"Indexing {folder.name}...")
                result = indexer.index_patient_folder(folder)
                logger.info(f"   Found {result['dicom_files']} DICOM files, {len(result['patients'])} patients")
            
            logger.info("✅ Test indexing completed!")
            
            # Test search
            from nas_patient_search import NASPatientSearch
            searcher = NASPatientSearch()
            
            if searcher.available:
                results = searcher.search_patients(limit=10)
                logger.info(f"Search test: Found {results['total_found']} patients")
                
                for patient in results['patients'][:3]:
                    logger.info(f"   - {patient['name']} (ID: {patient['patient_id']})")
            
        else:
            logger.error("No patient folders found!")
            
    except Exception as e:
        logger.error(f"Manual indexing failed: {e}")
        raise

def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Ubuntu Patient Care NAS Integration")
    parser.add_argument("--index", action="store_true", help="Run manual indexing test")
    parser.add_argument("--test", action="store_true", help="Run integration tests")
    
    args = parser.parse_args()
    
    if args.index:
        start_manual_indexing()
    elif args.test:
        test_nas_integration()
    else:
        # Run both by default
        test_nas_integration()
        
        # Ask if user wants to run indexing
        response = input("\n🤔 Would you like to run a small indexing test? (y/n): ")
        if response.lower().startswith('y'):
            start_manual_indexing()

if __name__ == "__main__":
    main()