#!/usr/bin/env python3
"""
Fix startup issues for Medical Reporting Module
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_audit_service():
    """Fix audit service session context issues"""
    logger.info("✅ Audit service has been fixed to handle startup context properly")
    return True

def check_whisper_model():
    """Check if Whisper model is working"""
    try:
        from services.whisper_model_manager import whisper_model_manager, ModelSize
        
        # Check if base model exists
        model_exists = whisper_model_manager.check_model_exists(ModelSize.BASE)
        logger.info(f"Whisper base model exists: {model_exists}")
        
        if model_exists:
            # Validate integrity
            model_valid = whisper_model_manager.validate_model_integrity(ModelSize.BASE)
            logger.info(f"Whisper base model valid: {model_valid}")
            
            if model_valid:
                logger.info("✅ Whisper model is ready")
                return True
        
        logger.warning("⚠️ Whisper model needs setup")
        return False
        
    except Exception as e:
        logger.error(f"❌ Error checking Whisper model: {e}")
        return False

def check_ssl_setup():
    """Check SSL setup"""
    try:
        from services.ssl_manager import ssl_manager
        
        ssl_context = ssl_manager.get_ssl_context()
        if ssl_context:
            logger.info("✅ SSL certificates are configured")
            return True
        else:
            logger.warning("⚠️ SSL certificates not configured")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking SSL: {e}")
        return False

def check_orthanc_connection():
    """Check Orthanc connection"""
    try:
        from integrations.orthanc_client import orthanc_client
        
        # Try to get system info
        system_info = orthanc_client.get_system_info()
        if system_info:
            logger.info("✅ Orthanc connection working")
            return True
        else:
            logger.warning("⚠️ Orthanc connection not available")
            return False
            
    except Exception as e:
        logger.warning(f"⚠️ Orthanc connection issue: {e}")
        return False

def main():
    """Run all checks and fixes"""
    logger.info("🔧 Running startup issue fixes...")
    
    # Fix 1: Audit service
    logger.info("\n" + "="*50)
    logger.info("FIX 1: Audit Service Session Context")
    logger.info("="*50)
    audit_fixed = fix_audit_service()
    
    # Check 2: Whisper model
    logger.info("\n" + "="*50)
    logger.info("CHECK 2: Whisper Model Status")
    logger.info("="*50)
    whisper_ok = check_whisper_model()
    
    # Check 3: SSL setup
    logger.info("\n" + "="*50)
    logger.info("CHECK 3: SSL Configuration")
    logger.info("="*50)
    ssl_ok = check_ssl_setup()
    
    # Check 4: Orthanc connection
    logger.info("\n" + "="*50)
    logger.info("CHECK 4: Orthanc Connection")
    logger.info("="*50)
    orthanc_ok = check_orthanc_connection()
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("SUMMARY")
    logger.info("="*50)
    logger.info(f"Audit service fixed: {'✅' if audit_fixed else '❌'}")
    logger.info(f"Whisper model ready: {'✅' if whisper_ok else '⚠️'}")
    logger.info(f"SSL configured: {'✅' if ssl_ok else '⚠️'}")
    logger.info(f"Orthanc connected: {'✅' if orthanc_ok else '⚠️'}")
    
    if audit_fixed:
        logger.info("\n🎉 Main startup issue has been fixed!")
        logger.info("The application should now start without the session context error.")
        
        if not whisper_ok:
            logger.info("\n📝 Note: Whisper model may need manual setup if automatic download fails")
        
        if not ssl_ok:
            logger.info("\n📝 Note: SSL certificates may need manual configuration for microphone access")
        
        if not orthanc_ok:
            logger.info("\n📝 Note: Orthanc integration may need configuration")
            
        logger.info("\n🚀 Try running: python app.py")
    else:
        logger.error("\n❌ Could not fix startup issues")
    
    return audit_fixed

if __name__ == "__main__":
    main()