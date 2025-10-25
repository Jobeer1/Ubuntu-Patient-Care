#!/usr/bin/env python3
"""
Start Full PACS Indexing
========================

This will index all 9300+ patients from the 11TB NAS drive.
Creates a fast searchable database for instant patient lookup.

CRITICAL for doctor workflow - enables sub-second patient search.
"""

import os
import sys
import logging
import time
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from pacs_indexer import PACSIndexer
    from metadata_db import get_metadata_db_path
except ImportError:
    print("❌ Error: pacs_indexer.py or metadata_db.py not found")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Start full PACS indexing"""
    logger.info("🏥 Ubuntu Patient Care - PACS Full Indexing")
    logger.info("=" * 60)
    logger.info("📊 Target: 9,300+ patients on 11TB NAS drive")
    logger.info("🎯 Goal: Sub-second patient search for doctors")
    logger.info("=" * 60)
    
    # Confirm before starting
    print("\n⚠️  WARNING: This will scan the entire 11TB NAS drive")
    print("📈 Estimated time: 45-60 minutes")
    print("💾 Database size: ~200MB when complete")
    print("🔥 This will enable INSTANT patient search for doctors")
    
    choice = input("\nStart full PACS indexing? (y/N): ").lower().strip()
    if choice != 'y':
        print("❌ Indexing cancelled")
        return
    
    # Initialize PACS indexer
    nas_path = "Z:"
    # Use canonical metadata DB (orthanc-index when present)
    db_path = get_metadata_db_path()
    
    logger.info(f"🔍 NAS Path: {nas_path}")
    logger.info(f"💾 Database: {db_path}")
    
    # Check NAS access
    if not os.path.exists(nas_path):
        logger.error(f"❌ NAS not accessible at {nas_path}")
        return
    
    # Create indexer
    indexer = PACSIndexer(nas_path, db_path)
    
    # Progress tracking
    start_time = datetime.now()
    
    def progress_callback(processed_files):
        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed > 0:
            speed = processed_files / elapsed
            logger.info(f"📈 Progress: {processed_files:,} files | {speed:.1f} files/sec")
    
    try:
        # Start indexing
        logger.info("🚀 Starting full PACS indexing...")
        indexer.scan_nas_directory(progress_callback)
        
        # Final statistics
        stats = indexer.stats
        duration = (stats['end_time'] - stats['start_time']).total_seconds()
        
        logger.info("\n🎉 PACS INDEXING COMPLETE!")
        logger.info("=" * 50)
        logger.info(f"👥 Patients indexed: {stats['patients']:,}")
        logger.info(f"📊 Studies indexed: {stats['studies']:,}")
        logger.info(f"🔬 Series indexed: {stats['series']:,}")
        logger.info(f"🖼️ Images indexed: {stats['instances']:,}")
        logger.info(f"⏱️ Total time: {duration/60:.1f} minutes")
        logger.info(f"🚀 Processing speed: {stats['instances']/duration:.1f} files/second")
        logger.info(f"❌ Errors: {stats['errors']}")
        
        # Database size
        if os.path.exists(db_path):
            db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
            logger.info(f"💾 Database size: {db_size_mb:.1f} MB")
        
        logger.info("\n✅ DOCTORS CAN NOW SEARCH PATIENTS INSTANTLY!")
        logger.info("🔍 Use: POST /api/pacs/search/patients")
        logger.info("📱 Access through Ubuntu Patient Care web interface")
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ Indexing interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Indexing failed: {e}")
        import traceback
        traceback.print_exc()

def test_search():
    """Test the patient search after indexing"""
    logger.info("\n🔍 Testing patient search...")
    
    db_path = os.path.join(os.path.dirname(__file__), "pacs_index.db")
    if not os.path.exists(db_path):
        logger.error("❌ Database not found. Run indexing first.")
        return
    
    indexer = PACSIndexer("Z:", db_path)
    
    # Test searches
    test_queries = ["FELIX", "MAXWELL", "639380"]
    
    for query in test_queries:
        logger.info(f"🔍 Searching for: '{query}'")
        patients = indexer.search_patients(query)
        
        for patient in patients[:3]:  # Show first 3 results
            logger.info(f"   ✅ {patient['name']} (ID: {patient['patient_id']})")
        
        if not patients:
            logger.info("   ❌ No patients found")
        else:
            logger.info(f"   📊 Total found: {len(patients)}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_search()
    else:
        main()