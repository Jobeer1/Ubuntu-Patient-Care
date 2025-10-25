#!/usr/bin/env python3
"""
Install SSL dependencies for HTTPS support
"""
import subprocess
import sys

def install_package(package):
    """Install a Python package using pip"""
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        print(f"✅ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def main():
    print("Installing SSL dependencies for HTTPS support...")
    
    # Install cryptography package for SSL certificate generation
    success = install_package('cryptography')
    
    if success:
        print("\n🎉 SSL dependencies installed successfully!")
        print("You can now run the app with HTTPS support:")
        print("python app.py")
        print("\nThe app will be available at: https://localhost:5443")
        print("Note: You'll see a security warning for the self-signed certificate - this is normal for development.")
    else:
        print("\n❌ Failed to install dependencies. Please install manually:")
        print("pip install cryptography")

if __name__ == '__main__':
    main()