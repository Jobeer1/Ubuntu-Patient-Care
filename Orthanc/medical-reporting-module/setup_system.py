#!/usr/bin/env python3
"""
Medical Reporting Module Setup Script
Initializes Whisper models, SSL certificates, and system configuration
"""

import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_whisper_models():
    """Setup Whisper models with automatic download"""
    try:
        logger.info("Setting up Whisper models...")
        
        from services.whisper_model_manager import whisper_model_manager, ModelSize
        
        # Get system specifications
        system_specs = whisper_model_manager.get_system_specs()
        logger.info(f"System specs: RAM={system_specs.total_ram_gb:.1f}GB, "
                   f"Available={system_specs.available_ram_gb:.1f}GB, "
                   f"CPU cores={system_specs.cpu_cores}")
        
        # Get optimal model size
        optimal_size = whisper_model_manager.get_optimal_model_size(system_specs)
        logger.info(f"Recommended model size: {optimal_size.value}")
        
        # Setup Whisper environment
        success, actual_size = whisper_model_manager.setup_whisper_environment(optimal_size)
        
        if success:
            logger.info(f"✅ Whisper model setup completed successfully with {actual_size.value} model")
            return True
        else:
            logger.error("❌ Failed to setup Whisper models")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error setting up Whisper models: {e}")
        return False

def setup_ssl_certificates():
    """Setup SSL certificates for HTTPS"""
    try:
        logger.info("Setting up SSL certificates...")
        
        from services.ssl_manager import ssl_manager
        
        # Check current SSL status
        ssl_status = ssl_manager.check_ssl_setup()
        
        if ssl_status.get("certificates_valid"):
            logger.info("✅ Valid SSL certificates already exist")
            return True
        
        # Setup development SSL
        success = ssl_manager.setup_development_ssl()
        
        if success:
            logger.info("✅ SSL certificates generated successfully")
            logger.info("🔒 HTTPS will be available for microphone access")
            return True
        else:
            logger.error("❌ Failed to generate SSL certificates")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error setting up SSL certificates: {e}")
        return False

def check_dependencies():
    """Check required dependencies"""
    try:
        logger.info("Checking dependencies...")
        
        required_packages = [
            'whisper',
            'torch',
            'flask',
            'flask-socketio',
            'requests',
            'psutil'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                logger.info(f"✅ {package} - installed")
            except ImportError:
                logger.warning(f"❌ {package} - missing")
                missing_packages.append(package)
        
        if missing_packages:
            logger.error(f"Missing packages: {missing_packages}")
            logger.info("Install missing packages with:")
            logger.info(f"pip install {' '.join(missing_packages)}")
            return False
        
        logger.info("✅ All dependencies are installed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking dependencies: {e}")
        return False

def check_system_requirements():
    """Check system requirements"""
    try:
        logger.info("Checking system requirements...")
        
        from services.whisper_model_manager import whisper_model_manager
        
        system_specs = whisper_model_manager.get_system_specs()
        
        # Check minimum requirements
        min_ram_gb = 2.0
        min_disk_gb = 5.0
        
        if system_specs.total_ram_gb < min_ram_gb:
            logger.warning(f"⚠️  Low RAM: {system_specs.total_ram_gb:.1f}GB (minimum {min_ram_gb}GB recommended)")
        else:
            logger.info(f"✅ RAM: {system_specs.total_ram_gb:.1f}GB")
        
        if system_specs.available_disk_gb < min_disk_gb:
            logger.warning(f"⚠️  Low disk space: {system_specs.available_disk_gb:.1f}GB (minimum {min_disk_gb}GB required)")
            return False
        else:
            logger.info(f"✅ Disk space: {system_specs.available_disk_gb:.1f}GB")
        
        logger.info(f"✅ CPU cores: {system_specs.cpu_cores}")
        
        if system_specs.has_gpu:
            logger.info("✅ GPU detected - faster processing available")
        else:
            logger.info("ℹ️  No GPU detected - using CPU (slower but functional)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking system requirements: {e}")
        return False

def test_voice_processing():
    """Test voice processing functionality"""
    try:
        logger.info("Testing voice processing...")
        
        from services.offline_stt_service import offline_stt_service
        from services.sa_localization_manager import sa_localization_manager
        
        # Test SA localization
        test_text = "patient has tb and numonia in right upper lobe"
        enhanced_text = sa_localization_manager.enhance_transcription_for_sa(test_text)
        
        logger.info(f"✅ SA Enhancement test: '{test_text}' -> '{enhanced_text}'")
        
        # Test Whisper initialization
        if offline_stt_service.initialize():
            logger.info("✅ Whisper STT engine initialized successfully")
        else:
            logger.error("❌ Failed to initialize Whisper STT engine")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing voice processing: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    try:
        logger.info("Creating directories...")
        
        directories = [
            "models/whisper",
            "ssl_certificates", 
            "offline_data",
            "logs",
            "temp"
        ]
        
        for directory in directories:
            dir_path = Path(directory)
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Created directory: {directory}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating directories: {e}")
        return False

def main():
    """Main setup function"""
    logger.info("=" * 60)
    logger.info("MEDICAL REPORTING MODULE SETUP")
    logger.info("=" * 60)
    
    success_count = 0
    total_steps = 6
    
    # Step 1: Check dependencies
    if check_dependencies():
        success_count += 1
    
    # Step 2: Check system requirements
    if check_system_requirements():
        success_count += 1
    
    # Step 3: Create directories
    if create_directories():
        success_count += 1
    
    # Step 4: Setup Whisper models
    if setup_whisper_models():
        success_count += 1
    
    # Step 5: Setup SSL certificates
    if setup_ssl_certificates():
        success_count += 1
    
    # Step 6: Test voice processing
    if test_voice_processing():
        success_count += 1
    
    # Summary
    logger.info("=" * 60)
    logger.info(f"SETUP COMPLETE: {success_count}/{total_steps} steps successful")
    logger.info("=" * 60)
    
    if success_count == total_steps:
        logger.info("🎉 All setup steps completed successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Start the application: python app.py")
        logger.info("2. Access via HTTPS: https://localhost:5001")
        logger.info("3. Test voice features in the browser")
        logger.info("")
        logger.info("Note: Browser may show security warning for self-signed certificates.")
        logger.info("Click 'Advanced' and 'Proceed to localhost' to continue.")
        return True
    else:
        logger.error(f"❌ Setup incomplete. {total_steps - success_count} steps failed.")
        logger.info("Please review the errors above and try again.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)