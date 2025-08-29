#!/usr/bin/env python3
"""
System Status Check for Medical Reporting Module
Comprehensive check of all system components
"""

import os
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'flask',
        'sqlalchemy',
        'requests',
        'psutil',
        'cryptography',
        'whisper',
        'torch',
        'numpy'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✅ {package} is installed")
        except ImportError:
            logger.error(f"❌ {package} is missing")
            missing_packages.append(package)
    
    return len(missing_packages) == 0, missing_packages

def check_file_structure():
    """Check if all required files and directories exist"""
    required_paths = [
        'services/whisper_model_manager.py',
        'services/offline_stt_service.py',
        'services/ssl_manager.py',
        'services/audit_service.py',
        'models/whisper/',
        'ssl_certificates/',
        'config/',
        'frontend/static/',
        'frontend/templates/'
    ]
    
    missing_paths = []
    
    for path in required_paths:
        if Path(path).exists():
            logger.info(f"✅ {path} exists")
        else:
            logger.error(f"❌ {path} is missing")
            missing_paths.append(path)
    
    return len(missing_paths) == 0, missing_paths

def check_whisper_setup():
    """Check Whisper model setup"""
    try:
        from services.whisper_model_manager import whisper_model_manager, ModelSize
        
        # Get system specs
        system_specs = whisper_model_manager.get_system_specs()
        logger.info(f"System RAM: {system_specs.total_ram_gb:.1f}GB")
        logger.info(f"Available RAM: {system_specs.available_ram_gb:.1f}GB")
        logger.info(f"CPU cores: {system_specs.cpu_cores}")
        logger.info(f"GPU available: {system_specs.has_gpu}")
        
        # Check optimal model size
        optimal_size = whisper_model_manager.get_optimal_model_size(system_specs)
        logger.info(f"Optimal model size: {optimal_size.value}")
        
        # Check if model exists
        model_exists = whisper_model_manager.check_model_exists(optimal_size)
        logger.info(f"Model exists: {model_exists}")
        
        if model_exists:
            model_valid = whisper_model_manager.validate_model_integrity(optimal_size)
            logger.info(f"Model valid: {model_valid}")
            return model_valid
        else:
            logger.warning("Model needs to be downloaded")
            return False
            
    except Exception as e:
        logger.error(f"Error checking Whisper setup: {e}")
        return False

def check_ssl_setup():
    """Check SSL certificate setup"""
    try:
        from services.ssl_manager import ssl_manager
        
        # Check if certificates exist
        cert_info = ssl_manager.get_certificate_info()
        if cert_info:
            logger.info(f"SSL certificate found")
            logger.info(f"Valid until: {cert_info.get('not_after', 'unknown')}")
            
            # Check if context can be created
            ssl_context = ssl_manager.get_ssl_context()
            if ssl_context:
                logger.info("✅ SSL context can be created")
                return True
            else:
                logger.warning("⚠️ SSL context creation failed")
                return False
        else:
            logger.warning("⚠️ No SSL certificates found")
            return False
            
    except Exception as e:
        logger.error(f"Error checking SSL setup: {e}")
        return False

def check_database_setup():
    """Check database setup"""
    try:
        from models.database import init_db, db
        
        # Try to initialize database
        init_db()
        logger.info("✅ Database initialization successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database setup error: {e}")
        return False

def check_services():
    """Check if all services can be imported and initialized"""
    services_to_check = [
        ('services.whisper_model_manager', 'whisper_model_manager'),
        ('services.offline_stt_service', 'offline_stt_service'),
        ('services.ssl_manager', 'ssl_manager'),
        ('services.audit_service', 'audit_service'),
        ('services.sa_localization_manager', 'sa_localization_manager'),
    ]
    
    all_services_ok = True
    
    for module_name, service_name in services_to_check:
        try:
            module = __import__(module_name, fromlist=[service_name])
            service = getattr(module, service_name)
            logger.info(f"✅ {service_name} imported successfully")
        except Exception as e:
            logger.error(f"❌ {service_name} import failed: {e}")
            all_services_ok = False
    
    return all_services_ok

def main():
    """Run comprehensive system check"""
    logger.info("🔍 Starting comprehensive system status check...")
    
    checks = []
    
    # Check 1: Dependencies
    logger.info("\n" + "="*60)
    logger.info("CHECK 1: Python Dependencies")
    logger.info("="*60)
    deps_ok, missing_deps = check_dependencies()
    checks.append(("Dependencies", deps_ok))
    if not deps_ok:
        logger.error(f"Missing packages: {', '.join(missing_deps)}")
    
    # Check 2: File structure
    logger.info("\n" + "="*60)
    logger.info("CHECK 2: File Structure")
    logger.info("="*60)
    files_ok, missing_files = check_file_structure()
    checks.append(("File Structure", files_ok))
    if not files_ok:
        logger.error(f"Missing paths: {', '.join(missing_files)}")
    
    # Check 3: Services
    logger.info("\n" + "="*60)
    logger.info("CHECK 3: Service Imports")
    logger.info("="*60)
    services_ok = check_services()
    checks.append(("Services", services_ok))
    
    # Check 4: Database
    logger.info("\n" + "="*60)
    logger.info("CHECK 4: Database Setup")
    logger.info("="*60)
    db_ok = check_database_setup()
    checks.append(("Database", db_ok))
    
    # Check 5: Whisper
    logger.info("\n" + "="*60)
    logger.info("CHECK 5: Whisper Model Setup")
    logger.info("="*60)
    whisper_ok = check_whisper_setup()
    checks.append(("Whisper Model", whisper_ok))
    
    # Check 6: SSL
    logger.info("\n" + "="*60)
    logger.info("CHECK 6: SSL Certificate Setup")
    logger.info("="*60)
    ssl_ok = check_ssl_setup()
    checks.append(("SSL Certificates", ssl_ok))
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("SYSTEM STATUS SUMMARY")
    logger.info("="*60)
    
    all_critical_ok = True
    for check_name, status in checks:
        status_icon = "✅" if status else "❌"
        logger.info(f"{status_icon} {check_name}: {'OK' if status else 'FAILED'}")
        
        # Critical checks
        if check_name in ["Dependencies", "File Structure", "Services", "Database"] and not status:
            all_critical_ok = False
    
    logger.info("\n" + "="*60)
    if all_critical_ok:
        logger.info("🎉 SYSTEM READY!")
        logger.info("All critical components are working.")
        
        # Check optional components
        optional_issues = []
        if not whisper_ok:
            optional_issues.append("Whisper model needs setup")
        if not ssl_ok:
            optional_issues.append("SSL certificates need configuration")
        
        if optional_issues:
            logger.info("\n📝 Optional improvements needed:")
            for issue in optional_issues:
                logger.info(f"  - {issue}")
        
        logger.info("\n🚀 You can start the application with: python app.py")
        
    else:
        logger.error("❌ SYSTEM NOT READY!")
        logger.error("Critical components are missing or broken.")
        logger.error("Please fix the issues above before starting the application.")
    
    return all_critical_ok

if __name__ == "__main__":
    main()