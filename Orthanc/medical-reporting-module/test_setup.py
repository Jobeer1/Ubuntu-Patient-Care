#!/usr/bin/env python3
"""
Test script to verify Medical Reporting Module setup
"""

import sys
import os
import subprocess
from pathlib import Path

def test_directory_structure():
    """Test that all required directories exist"""
    print("Testing directory structure...")
    
    required_dirs = [
        'config',
        'core',
        'integrations', 
        'api',
        'models',
        'services',
        'utils',
        'frontend/templates',
    ]
    
    missing_dirs = []
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            missing_dirs.append(dir_name)
    
    if missing_dirs:
        print(f"❌ Missing directories: {missing_dirs}")
        return False
    else:
        print("✅ All required directories exist")
        return True

def test_required_files():
    """Test that all required files exist"""
    print("Testing required files...")
    
    required_files = [
        'app.py',
        'requirements.txt',
        'README.md',
        '.env.example',
        'config/settings.py',
        'config/offline_config.py',
        'config/integration_config.py',
        'frontend/templates/dashboard.html',
    ]
    
    missing_files = []
    for file_name in required_files:
        if not os.path.exists(file_name):
            missing_files.append(file_name)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files exist")
        return True

def test_python_imports():
    """Test that Python can import the configuration modules"""
    print("Testing Python imports...")
    
    try:
        sys.path.insert(0, os.getcwd())
        
        # Test configuration imports
        from config.settings import DevelopmentConfig, ProductionConfig
        from config.offline_config import OfflineConfig
        from config.integration_config import IntegrationConfig
        
        print("✅ Configuration modules import successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_flask_app():
    """Test that Flask app can be created"""
    print("Testing Flask app creation...")
    
    try:
        # Import and create app
        from app import app
        
        with app.app_context():
            # Test health endpoint
            with app.test_client() as client:
                response = client.get('/health')
                if response.status_code == 200:
                    print("✅ Flask app created and health endpoint working")
                    return True
                else:
                    print(f"❌ Health endpoint returned status {response.status_code}")
                    return False
                    
    except Exception as e:
        print(f"❌ Flask app creation failed: {e}")
        return False

def test_requirements():
    """Test that requirements.txt is valid"""
    print("Testing requirements.txt...")
    
    try:
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
            
        # Check for key dependencies
        key_deps = ['Flask', 'SQLAlchemy', 'requests', 'pydicom']
        missing_deps = []
        
        for dep in key_deps:
            if dep not in requirements:
                missing_deps.append(dep)
        
        if missing_deps:
            print(f"❌ Missing key dependencies: {missing_deps}")
            return False
        else:
            print("✅ Requirements.txt contains key dependencies")
            return True
            
    except Exception as e:
        print(f"❌ Error reading requirements.txt: {e}")
        return False

def main():
    """Run all tests"""
    print("🏥 Medical Reporting Module Setup Test")
    print("=" * 50)
    
    tests = [
        test_directory_structure,
        test_required_files,
        test_python_imports,
        test_flask_app,
        test_requirements,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Setup is complete.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and configure your settings")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Run the application: python app.py")
        return True
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)