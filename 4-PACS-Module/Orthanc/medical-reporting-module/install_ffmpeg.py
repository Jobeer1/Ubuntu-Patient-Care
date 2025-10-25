#!/usr/bin/env python3
"""
FFmpeg Installation Script for Windows
Automatically downloads and installs FFmpeg for Whisper audio processing
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
from pathlib import Path

def check_ffmpeg():
    """Check if FFmpeg is available in PATH"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ FFmpeg is already installed and accessible")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass
    
    print("❌ FFmpeg not found in PATH")
    return False

def download_ffmpeg_windows():
    """Download and install FFmpeg for Windows"""
    print("📥 Downloading FFmpeg for Windows...")
    
    # FFmpeg download URL for Windows (static build)
    ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    
    # Create temp directory
    temp_dir = Path("temp_ffmpeg")
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # Download FFmpeg
        zip_path = temp_dir / "ffmpeg.zip"
        print(f"Downloading from {ffmpeg_url}...")
        urllib.request.urlretrieve(ffmpeg_url, zip_path)
        print("✅ Download complete")
        
        # Extract FFmpeg
        print("📦 Extracting FFmpeg...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Find the extracted directory
        extracted_dirs = [d for d in temp_dir.iterdir() if d.is_dir()]
        if not extracted_dirs:
            raise Exception("No directories found in extracted archive")
        
        ffmpeg_dir = extracted_dirs[0]
        ffmpeg_bin = ffmpeg_dir / "bin"
        
        if not ffmpeg_bin.exists():
            raise Exception("FFmpeg bin directory not found in extracted archive")
        
        # Create local ffmpeg directory
        local_ffmpeg = Path("ffmpeg")
        if local_ffmpeg.exists():
            shutil.rmtree(local_ffmpeg)
        
        # Copy FFmpeg to local directory
        shutil.copytree(ffmpeg_bin, local_ffmpeg)
        print(f"✅ FFmpeg installed to {local_ffmpeg.absolute()}")
        
        # Add to PATH for current session
        current_path = os.environ.get('PATH', '')
        ffmpeg_path = str(local_ffmpeg.absolute())
        
        if ffmpeg_path not in current_path:
            os.environ['PATH'] = ffmpeg_path + os.pathsep + current_path
            print("✅ FFmpeg added to PATH for current session")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to install FFmpeg: {e}")
        return False
    
    finally:
        # Clean up temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

def install_ffmpeg():
    """Main installation function"""
    print("🔧 FFmpeg Installation for Medical Reporting Module")
    print("=" * 50)
    
    # Check if already installed
    if check_ffmpeg():
        return True
    
    # Install for Windows
    if sys.platform.startswith('win'):
        return download_ffmpeg_windows()
    else:
        print("❌ Automatic installation only supported on Windows")
        print("Please install FFmpeg manually:")
        print("- Ubuntu/Debian: sudo apt install ffmpeg")
        print("- macOS: brew install ffmpeg")
        print("- Or download from: https://ffmpeg.org/download.html")
        return False

if __name__ == "__main__":
    success = install_ffmpeg()
    if success:
        print("\n✅ FFmpeg installation complete!")
        print("The Medical Reporting Module should now work properly.")
    else:
        print("\n❌ FFmpeg installation failed!")
        print("Please install FFmpeg manually for the STT system to work.")
    
    input("Press Enter to continue...")