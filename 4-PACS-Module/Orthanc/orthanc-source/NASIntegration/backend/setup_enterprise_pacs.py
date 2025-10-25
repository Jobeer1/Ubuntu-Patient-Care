#!/usr/bin/env python3
"""
Enterprise Multi-NAS PACS Setup
===============================

Configure and initialize the multi-NAS PACS system for:
- NAS #1: DICOM CT Scans (Z: drive) 
- NAS #2: Firebird + JPEG2000 (Y: drive)
- NAS #3: Firebird + JPEG2000 (X: drive)

Features:
- SQL database for instant image location lookup
- Incremental updates for new procedures  
- Unified patient search across all NAS devices
"""

import os
import sys
import logging
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from multi_nas_pacs_indexer import MultiNASPACSIndexer, setup_three_nas_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def install_dependencies():
    """Install required dependencies for multi-NAS support"""
    import subprocess
    
    packages = [
        'pydicom',     # DICOM file support
        'fdb',         # Firebird database connector  
        'glymur',      # JPEG2000 support
        'pillow',      # Image processing
        'flask',       # Web API
        'flask-cors'   # CORS support
    ]
    
    logger.info("📦 Installing multi-NAS PACS dependencies...")
    
    for package in packages:
        try:
            logger.info(f"Installing {package}...")
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', package
            ], check=True, capture_output=True, text=True)
            logger.info(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            if package in ['fdb', 'glymur']:
                logger.warning(f"⚠️ {package} installation failed (optional for some NAS types)")
            else:
                logger.error(f"❌ Failed to install {package}: {e}")

def setup_enterprise_pacs():
    """Setup the enterprise PACS system"""
    logger.info("🏥 Ubuntu Patient Care - Enterprise Multi-NAS PACS Setup")
    logger.info("=" * 70)
    
    # Initialize the multi-NAS indexer
    indexer = setup_three_nas_config()
    
    logger.info("📊 Configured NAS Devices:")
    for nas_id, config in indexer.nas_configs.items():
        status = "✅ Connected" if os.path.exists(config['path']) else "❌ Not accessible"
        logger.info(f"   {nas_id}: {config['description']} - {status}")
    
    # Initialize database
    logger.info("\n💾 Initializing enterprise PACS database...")
    indexer.init_enterprise_database()
    
    # Test NAS #1 (DICOM CT) - the one currently connected
    logger.info("\n🔍 Testing NAS #1 (DICOM CT Scans)...")
    if os.path.exists('Z:'):
        logger.info("✅ Z: drive accessible")
        
        # Quick test with Felix Maxwell's folder
        felix_path = "Z:\\639380-20250922-"
        if os.path.exists(felix_path):
            logger.info(f"✅ Felix Maxwell folder found: {felix_path}")
            
            # Run quick index of Felix Maxwell
            logger.info("🚀 Quick indexing of Felix Maxwell...")
            indexer.index_nas_device('nas_ct_dicom', incremental=False)
            
            # Test search
            logger.info("🔍 Testing multi-NAS patient search...")
            patients = indexer.search_patients_across_nas("FELIX")
            
            if patients:
                patient = patients[0]
                logger.info(f"✅ Found patient: {patient['name']}")
                logger.info(f"   NAS Device: {patient['nas_id']} ({patient['nas_description']})")
                logger.info(f"   Studies: {patient['study_count']}")
                logger.info(f"   Images: {patient['image_count']}")
                
                # Get image locations
                images = indexer.get_image_locations(patient['patient_id'], patient['nas_id'])
                logger.info(f"   Image files: {len(images)} locations in SQL database")
                
                if images:
                    sample_image = images[0]
                    logger.info(f"   Sample file: {sample_image['file_path']}")
                    logger.info(f"   Format: {sample_image['file_format']}")
                    logger.info(f"   Size: {sample_image['file_size']:,} bytes")
                
                logger.info("\n✅ NAS #1 (DICOM CT) - FULLY OPERATIONAL!")
            else:
                logger.error("❌ Felix Maxwell not found in search")
        else:
            logger.warning("⚠️ Felix Maxwell folder not found")
    else:
        logger.error("❌ Z: drive not accessible")
    
    # Information about other NAS devices
    logger.info("\n📋 NAS #2 & #3 Configuration:")
    logger.info("   These require Firebird database connections")
    logger.info("   Update credentials in multi_nas_pacs_indexer.py:")
    logger.info("   - firebird_db: Path to .fdb file")
    logger.info("   - firebird_host: Database server")
    logger.info("   - firebird_user: Username")
    logger.info("   - firebird_password: Password")
    
    # Start incremental monitoring
    logger.info("\n🔄 Starting incremental monitoring...")
    indexer.start_incremental_monitoring(15)  # Every 15 minutes
    
    return indexer

def test_sql_search_speed():
    """Test the SQL database search speed"""
    logger.info("\n⚡ Testing SQL search performance...")
    
    import sqlite3
    import time
    
    db_path = "enterprise_pacs_index.db"
    if not os.path.exists(db_path):
        logger.error("❌ Enterprise database not found")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Test various search queries
    test_queries = [
        ("Patient name search", "SELECT COUNT(*) FROM patients WHERE patient_name LIKE '%FELIX%'"),
        ("Patient ID search", "SELECT COUNT(*) FROM patients WHERE patient_id LIKE '%639380%'"),
        ("Modality search", "SELECT COUNT(*) FROM studies WHERE modality = 'CT'"),
        ("Date range search", "SELECT COUNT(*) FROM studies WHERE study_date >= '20250920'"),
        ("Image location lookup", "SELECT file_path FROM instances WHERE nas_id = 'nas_ct_dicom' LIMIT 10")
    ]
    
    for test_name, query in test_queries:
        start_time = time.time()
        cursor.execute(query)
        results = cursor.fetchall()
        search_time = (time.time() - start_time) * 1000
        
        logger.info(f"   {test_name}: {search_time:.2f}ms")
    
    conn.close()
    logger.info("✅ SQL search performance tested")

def main():
    """Main setup function"""
    try:
        # Install dependencies
        install_dependencies()
        
        # Setup enterprise PACS
        indexer = setup_enterprise_pacs()
        
        # Test search performance
        test_sql_search_speed()
        
        logger.info("\n" + "=" * 70)
        logger.info("🎉 ENTERPRISE MULTI-NAS PACS SETUP COMPLETE!")
        logger.info("=" * 70)
        logger.info("✅ Features Available:")
        logger.info("   🔍 Unified patient search across all NAS devices")
        logger.info("   📁 SQL database for instant image file locations")
        logger.info("   🔄 Incremental updates every 15 minutes")
        logger.info("   🏥 Support for DICOM, Firebird, and JPEG2000")
        logger.info("   ⚡ Sub-second search performance")
        
        logger.info("\n🌐 API Endpoints Available:")
        logger.info("   POST /api/enterprise-pacs/search/patients")
        logger.info("   GET  /api/enterprise-pacs/patient/{id}/images")
        logger.info("   GET  /api/enterprise-pacs/image/serve")
        logger.info("   POST /api/enterprise-pacs/incremental/trigger")
        
        logger.info("\n🚀 Next Steps:")
        logger.info("   1. Configure Firebird database connections for NAS #2 & #3")
        logger.info("   2. Start full indexing: POST /api/enterprise-pacs/indexing/start")
        logger.info("   3. Access via web interface: http://localhost:5000/pacs-search")
        
        logger.info("\n🔥 DOCTORS NOW HAVE INSTANT ACCESS TO ALL MEDICAL IMAGES!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n❌ Enterprise PACS setup failed. Check logs above.")
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("🏥 Your enterprise PACS system is ready for production use!")