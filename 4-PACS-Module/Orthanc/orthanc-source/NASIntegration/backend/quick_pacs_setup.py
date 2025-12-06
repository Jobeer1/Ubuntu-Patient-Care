#!/usr/bin/env python3
"""
Quick PACS Setup for Felix Maxwell
=================================

This will quickly index just Felix Maxwell's folder to test the system.
Perfect for immediate testing without waiting for full 11TB indexing.
"""

import os
import sys
import logging
from datetime import datetime

# Add current directory to path for imports  
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pacs_indexer import PACSIndexer
try:
    from metadata_db import get_metadata_db_path
except Exception:
    def get_metadata_db_path():
        return os.path.join(os.path.dirname(__file__), 'pacs_index.db')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def quick_felix_setup():
    """Quick setup with just Felix Maxwell's data"""
    logger.info("🏥 Ubuntu Patient Care - Quick PACS Setup")
    logger.info("🎯 Target: Felix Maxwell (Patient 639380)")
    logger.info("=" * 50)
    
    # Felix Maxwell's folder
    felix_path = "Z:\\639380-20250922-"
    db_path = get_metadata_db_path()
    
    if not os.path.exists(felix_path):
        logger.error(f"❌ Felix Maxwell folder not found: {felix_path}")
        return False
    
    logger.info(f"📁 Indexing folder: {felix_path}")
    logger.info(f"💾 Database: {db_path}")
    
    # Create indexer with Felix's folder only
    indexer = PACSIndexer(felix_path, db_path)
    
    try:
        # Quick scan
        start_time = datetime.now()
        logger.info("🚀 Starting quick Felix Maxwell indexing...")
        
        indexer.scan_nas_directory()
        
        duration = (datetime.now() - start_time).total_seconds()
        stats = indexer.stats
        
        logger.info("\n🎉 QUICK PACS SETUP COMPLETE!")
        logger.info("=" * 40)
        logger.info(f"👥 Patients: {stats['patients']}")
        logger.info(f"📊 Studies: {stats['studies']}")
        logger.info(f"🖼️ Images: {stats['instances']}")
        logger.info(f"⏱️ Time: {duration:.1f} seconds")
        
        # Test search
        logger.info("\n🔍 Testing patient search...")
        patients = indexer.search_patients("FELIX")
        
        if patients:
            patient = patients[0]
            logger.info(f"✅ Found: {patient['name']}")
            logger.info(f"   ID: {patient['patient_id']}")
            logger.info(f"   DOB: {patient['birth_date']}")
            logger.info(f"   Studies: {patient['study_count']}")
            
            # Get studies
            studies = indexer.get_patient_studies(patient['patient_id'])
            for study in studies:
                logger.info(f"   📊 Study: {study['study_description']}")
                logger.info(f"      Date: {study['study_date']}")
                logger.info(f"      Images: {study['instance_count']}")
            
            logger.info("\n✅ PACS SYSTEM READY FOR TESTING!")
            logger.info("🌐 Access: http://localhost:5000/pacs-search")
            logger.info("🔍 Search for: FELIX, MAXWELL, or 639380")
            
            return True
        else:
            logger.error("❌ Felix Maxwell not found in search")
            return False
            
    except Exception as e:
        logger.error(f"❌ Quick setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = quick_felix_setup()
    
    if success:
        print("\n" + "="*60)
        print("🎉 QUICK PACS SETUP SUCCESSFUL!")
        print("🌐 Open: http://localhost:5000/pacs-search")
        print("🔍 Search for Felix Maxwell to test")
        print("="*60)
    else:
        print("\n❌ Quick setup failed. Check logs above.")
        sys.exit(1)