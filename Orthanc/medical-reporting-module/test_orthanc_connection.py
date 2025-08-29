#!/usr/bin/env python3
"""
Test Orthanc connection and setup
"""

import requests
import logging
from integrations.orthanc_client import orthanc_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_orthanc_connection():
    """Test connection to Orthanc server"""
    try:
        logger.info("Testing Orthanc connection...")
        
        # Test basic connectivity
        if orthanc_client.check_connectivity():
            logger.info("✅ Orthanc connection successful")
            
            # Get system info
            system_info = orthanc_client.get_system_info()
            if system_info:
                logger.info(f"✅ Orthanc version: {system_info.get('Version', 'unknown')}")
                logger.info(f"✅ Database version: {system_info.get('DatabaseVersion', 'unknown')}")
                logger.info(f"✅ Storage size: {system_info.get('StorageSize', 'unknown')} bytes")
            
            # Test study search
            logger.info("Testing study search...")
            studies = orthanc_client.search_studies({})
            logger.info(f"✅ Found {len(studies)} studies in Orthanc")
            
            if studies:
                # Test getting details of first study
                first_study = studies[0]
                study_id = first_study.get('ID')
                if study_id:
                    study_details = orthanc_client.get_study_details(study_id)
                    if study_details:
                        logger.info(f"✅ Successfully retrieved study details for {study_id}")
                        
                        # Test series retrieval
                        series = orthanc_client.get_study_series(study_id)
                        logger.info(f"✅ Found {len(series)} series in study")
            
            return True
            
        else:
            logger.error("❌ Failed to connect to Orthanc server")
            logger.info("Checking possible issues:")
            
            # Test basic HTTP connection
            try:
                response = requests.get(orthanc_client.base_url, timeout=5)
                logger.info(f"HTTP response status: {response.status_code}")
            except requests.exceptions.ConnectionError:
                logger.error("❌ Connection refused - Orthanc server may not be running")
                logger.info("💡 Make sure Orthanc is running on http://localhost:8042")
            except requests.exceptions.Timeout:
                logger.error("❌ Connection timeout - Orthanc server may be slow")
            except Exception as e:
                logger.error(f"❌ Connection error: {e}")
            
            return False
            
    except Exception as e:
        logger.error(f"❌ Error testing Orthanc connection: {e}")
        return False

def setup_orthanc_for_reporting():
    """Setup Orthanc integration for medical reporting"""
    try:
        logger.info("Setting up Orthanc integration...")
        
        # Test connection first
        if not test_orthanc_connection():
            logger.error("❌ Cannot setup Orthanc integration - connection failed")
            return False
        
        # Add any additional setup here (plugins, configuration, etc.)
        logger.info("✅ Orthanc integration setup completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error setting up Orthanc integration: {e}")
        return False

if __name__ == "__main__":
    success = test_orthanc_connection()
    if success:
        setup_orthanc_for_reporting()
    else:
        logger.info("\n" + "="*60)
        logger.info("ORTHANC CONNECTION TROUBLESHOOTING")
        logger.info("="*60)
        logger.info("1. Make sure Orthanc server is running:")
        logger.info("   - Check if Orthanc is installed and running")
        logger.info("   - Default URL: http://localhost:8042")
        logger.info("   - Default credentials: orthanc/orthanc")
        logger.info("")
        logger.info("2. Check Orthanc configuration:")
        logger.info("   - Ensure HTTP server is enabled")
        logger.info("   - Check authentication settings")
        logger.info("   - Verify network connectivity")
        logger.info("")
        logger.info("3. Environment variables (optional):")
        logger.info("   - ORTHANC_URL=http://your-orthanc-server:8042")
        logger.info("   - ORTHANC_USERNAME=your-username")
        logger.info("   - ORTHANC_PASSWORD=your-password")
        logger.info("="*60)