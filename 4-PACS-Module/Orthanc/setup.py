#!/usr/bin/env python3
"""
Ubuntu Patient Care - Setup Script
Automated installation and configuration for the medical AI platform
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_banner():
    """Display Ubuntu Patient Care setup banner"""
    print("="*60)
    print("🏥 UBUNTU PATIENT CARE - MEDICAL AI PLATFORM 🏥")
    print("="*60)
    print("🎯 Code with Kiro Hackathon 2025 - Educational Apps")
    print("🚀 AI-Powered Medical Education & Documentation")
    print("="*60)
    print()

def check_python_version():
    """Ensure Python 3.8+ is being used"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python version: {sys.version.split()[0]}")

def check_system_dependencies():
    """Check for required system dependencies"""
    print("🔍 Checking system dependencies...")
    
    # Check for FFmpeg
    if shutil.which('ffmpeg') is None:
        print("⚠️  FFmpeg not found - required for audio processing")
        print("   Install: https://ffmpeg.org/download.html")
        print("   Windows: Download from https://ffmpeg.org/download.html")
        print("   macOS: brew install ffmpeg")
        print("   Ubuntu: sudo apt install ffmpeg")
    else:
        print("✅ FFmpeg found")
    
    # Check for Git
    if shutil.which('git') is None:
        print("⚠️  Git not found - recommended for development")
    else:
        print("✅ Git found")

def create_virtual_environment():
    """Create Python virtual environment"""
    print("🐍 Setting up Python virtual environment...")
    
    venv_path = Path("venv")
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return
    
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Virtual environment created")
    except subprocess.CalledProcessError:
        print("❌ Failed to create virtual environment")
        sys.exit(1)

def get_activation_command():
    """Get the appropriate activation command for the OS"""
    if sys.platform == "win32":
        return "venv\\Scripts\\activate"
    else:
        return "source venv/bin/activate"

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    # Determine pip path
    if sys.platform == "win32":
        pip_path = Path("venv/Scripts/pip")
    else:
        pip_path = Path("venv/bin/pip")
    
    if not pip_path.exists():
        print("❌ Virtual environment not properly created")
        sys.exit(1)
    
    # Install requirements
    requirements_file = Path("medical-reporting-module/requirements.txt")
    if not requirements_file.exists():
        print("❌ requirements.txt not found")
        print("   Make sure you're in the project root directory")
        sys.exit(1)
    
    try:
        subprocess.run([
            str(pip_path), "install", "-r", str(requirements_file)
        ], check=True)
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        print("💡 Try manually: pip install -r medical-reporting-module/requirements.txt")

def setup_ssl_certificates():
    """Set up SSL certificates for HTTPS"""
    print("🔒 Setting up SSL certificates...")
    
    cert_dir = Path("medical-reporting-module/certs")
    cert_file = cert_dir / "cert.pem"
    key_file = cert_dir / "key.pem"
    
    if cert_file.exists() and key_file.exists():
        print("✅ SSL certificates already exist")
        return
    
    cert_dir.mkdir(exist_ok=True)
    
    # Try to run the SSL setup script
    ssl_script = Path("medical-reporting-module/install_ssl_deps.py")
    if ssl_script.exists():
        try:
            os.chdir("medical-reporting-module")
            subprocess.run([sys.executable, "install_ssl_deps.py"], check=True)
            os.chdir("..")
            print("✅ SSL certificates generated")
        except subprocess.CalledProcessError:
            print("⚠️  SSL certificate generation failed")
            print("   The application will still work but HTTPS may not be available")
    else:
        print("⚠️  SSL setup script not found")

def create_database():
    """Initialize the application database"""
    print("🗄️  Setting up database...")
    
    try:
        os.chdir("medical-reporting-module")
        
        # Try to initialize the database
        init_script = """
from app import app
with app.app_context():
    try:
        from models import db
        db.create_all()
        print('✅ Database initialized successfully')
    except Exception as e:
        print(f'⚠️  Database initialization issue: {e}')
        print('   This may be normal for first-time setup')
"""
        
        with open("temp_db_init.py", "w") as f:
            f.write(init_script)
        
        # Determine python path
        if sys.platform == "win32":
            python_path = "../venv/Scripts/python"
        else:
            python_path = "../venv/bin/python"
        
        subprocess.run([python_path, "temp_db_init.py"], check=True)
        
        # Clean up temp file
        os.remove("temp_db_init.py")
        os.chdir("..")
        
    except subprocess.CalledProcessError:
        print("⚠️  Database setup encountered issues")
        print("   You may need to run database initialization manually")
        os.chdir("..")
    except Exception as e:
        print(f"⚠️  Database setup error: {e}")
        os.chdir("..")

def create_environment_file():
    """Create .env file with default configuration"""
    print("⚙️  Creating configuration file...")
    
    env_file = Path("medical-reporting-module/.env")
    if env_file.exists():
        print("✅ Configuration file already exists")
        return
    
    env_content = """# Ubuntu Patient Care Configuration
# Medical AI Platform Settings

# Application Settings
FLASK_ENV=development
SECRET_KEY=ubuntu-patient-care-secret-key-change-in-production
DEBUG=True

# Database
DATABASE_URL=sqlite:///medical_reporting.db

# Orthanc DICOM Server (optional)
ORTHANC_URL=http://localhost:8042
ORTHANC_USERNAME=orthanc
ORTHANC_PASSWORD=orthanc

# Audio Processing
TEMP_AUDIO_DIR=temp/audio
MAX_AUDIO_SIZE=50MB

# Security
ENCRYPTION_KEY=ubuntu-patient-care-encryption-key
SESSION_LIFETIME=24

# Medical Compliance
ENABLE_AUDIT_LOGGING=True
POPIA_COMPLIANCE=True
HIPAA_MODE=False
"""
    
    with open(env_file, "w") as f:
        f.write(env_content)
    
    print("✅ Configuration file created")
    print("⚠️  Remember to update SECRET_KEY and ENCRYPTION_KEY for production!")

def print_completion_instructions():
    """Print final instructions for running the application"""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE! 🎉")
    print("="*60)
    
    activation_cmd = get_activation_command()
    
    print(f"""
🚀 To start Ubuntu Patient Care:

1. Activate the virtual environment:
   {activation_cmd}

2. Navigate to the application directory:
   cd medical-reporting-module

3. Start the application:
   python app.py

4. Open your browser to:
   https://127.0.0.1:5443

📚 Key Features to Try:
   • Voice-to-Text Medical Reporting
   • DICOM Medical Image Viewer (2x2 grid layouts)
   • Medical Template Management
   • Educational Training Modules

🔗 Important URLs:
   • Main Dashboard: https://127.0.0.1:5443
   • Medical Reporting: https://127.0.0.1:5443/voice-demo
   • DICOM Viewer: https://127.0.0.1:5443/find-studies
   • Templates: https://127.0.0.1:5443/templates

🏆 Code with Kiro Hackathon 2025
   Category: Educational Apps
   
💡 For support or issues:
   Check the README.md and documentation in docs/
""")

def main():
    """Main setup process"""
    print_banner()
    
    # Verify we're in the right directory
    if not Path("medical-reporting-module").exists():
        print("❌ Error: medical-reporting-module directory not found")
        print("   Make sure you're running this script from the project root")
        sys.exit(1)
    
    print("🏗️  Starting Ubuntu Patient Care setup...\n")
    
    # Run setup steps
    check_python_version()
    check_system_dependencies()
    create_virtual_environment()
    install_dependencies()
    setup_ssl_certificates()
    create_environment_file()
    create_database()
    
    print_completion_instructions()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed with error: {e}")
        print("💡 Check the error message above and try manual installation")
        sys.exit(1)
