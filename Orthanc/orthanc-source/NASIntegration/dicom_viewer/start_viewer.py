#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - DICOM Viewer Startup

Starts the advanced DICOM viewer integrated with the SA medical imaging system.
"""

import os
import sys
import subprocess
import platform
import time

def check_node_installed():
    """Check if Node.js is installed"""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Node.js {version} is installed")
            return True
        else:
            return False
    except FileNotFoundError:
        return False

def install_dependencies():
    """Install npm dependencies"""
    print("📦 Installing DICOM viewer dependencies...")
    try:
        result = subprocess.run(['npm', 'install'], check=True, capture_output=True, text=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e.stderr}")
        return False

def start_viewer():
    """Start the DICOM viewer development server"""
    print("🚀 Starting SA DICOM Viewer...")
    print("🌐 The viewer will be available at: http://localhost:3001")
    print("🔗 It will connect to the main SA system at: http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop the viewer")
    print("=" * 60)
    
    try:
        # Set environment variables
        env = os.environ.copy()
        env['PORT'] = '3001'
        env['REACT_APP_API_URL'] = 'http://localhost:5000'
        env['REACT_APP_SA_SYSTEM'] = 'true'
        
        # Start the React development server
        subprocess.run(['npm', 'start'], env=env)
        
    except KeyboardInterrupt:
        print("\n👋 SA DICOM Viewer stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting viewer: {e}")

def main():
    print("🇿🇦 SOUTH AFRICAN ADVANCED DICOM VIEWER")
    print("🏥 World-Class Medical Imaging for SA Healthcare")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists('package.json'):
        print("❌ Error: package.json not found")
        print("Please run this script from the dicom_viewer directory")
        sys.exit(1)
    
    # Check Node.js installation
    if not check_node_installed():
        print("❌ Node.js is not installed")
        print("Please install Node.js from: https://nodejs.org/")
        print("Recommended version: Node.js 16 or higher")
        sys.exit(1)
    
    # Install dependencies if node_modules doesn't exist
    if not os.path.exists('node_modules'):
        if not install_dependencies():
            sys.exit(1)
    
    # Start the viewer
    start_viewer()

if __name__ == '__main__':
    main()