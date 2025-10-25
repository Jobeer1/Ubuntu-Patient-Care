#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - Clean Installation Script

Simplified installation with better dependency management.
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def main():
    print("🇿🇦 SOUTH AFRICAN MEDICAL IMAGING SYSTEM")
    print("🏥 Clean Installation Script")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version.split()[0]} is compatible")
    
    # Change to backend directory
    backend_dir = "backend"
    if os.path.exists(backend_dir):
        os.chdir(backend_dir)
        print(f"📁 Changed to {backend_dir} directory")
    
    # Install core dependencies
    print("\n📦 Installing Core Dependencies...")
    if not run_command("pip install -r requirements-core.txt", "Installing core packages"):
        print("⚠️ Some core packages failed to install. System may have limited functionality.")
    
    # Ask about optional dependencies
    print("\n🤔 Optional Features:")
    print("   • Voice Recognition (Vosk, SpeechRecognition)")
    print("   • AI Diagnosis (TensorFlow)")
    print("   • Face Recognition (face_recognition)")
    print("   • Advanced DICOM (pydicom, pynetdicom)")
    print("   • Advanced Image Processing (OpenCV, SciPy)")
    
    install_optional = input("\nInstall optional features? (y/N): ").lower().strip()
    
    if install_optional in ['y', 'yes']:
        print("\n📦 Installing Optional Dependencies...")
        if not run_command("pip install -r requirements-optional.txt", "Installing optional packages"):
            print("⚠️ Some optional packages failed. You can install them later.")
    else:
        print("⏭️ Skipping optional dependencies")
    
    # Create directories
    print("\n📁 Creating Directory Structure...")
    directories = [
        "data", "logs", "audio_recordings", 
        "dicom_cache", "models", "temp"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    print("✅ Directory structure created")
    
    # Test imports
    print("\n🧪 Testing System Components...")
    test_imports = [
        ("Flask", "flask"),
        ("User Database", "user_db"),
        ("Image Database", "image_db"),
        ("NAS Connector", "nas_connector"),
    ]
    
    working_components = 0
    for name, module in test_imports:
        try:
            __import__(module)
            print(f"✅ {name}: Available")
            working_components += 1
        except ImportError:
            print(f"⚠️ {name}: Not available")
    
    # Installation complete
    print("\n🎉 INSTALLATION COMPLETE!")
    print("=" * 50)
    print(f"✅ Core System: Ready ({working_components}/{len(test_imports)} components)")
    
    if install_optional == 'y':
        print("✅ Optional Features: Installed")
    else:
        print("⚠️ Optional Features: Not installed")
        print("   Run: pip install -r requirements-optional.txt (to install later)")
    
    print("\n🚀 Quick Start:")
    print("1. Run: python start_sa_system.py")
    print("2. Open: http://localhost:5000")
    print("3. Login: admin / admin123")
    
    print("\n📚 Documentation:")
    print("• System Status: http://localhost:5000/system-status")
    print("• Progress Tracker: SOUTH_AFRICAN_PROGRESS_TRACKER.md")
    
    print("\n🇿🇦 Ready to revolutionize South African healthcare!")

if __name__ == "__main__":
    main()