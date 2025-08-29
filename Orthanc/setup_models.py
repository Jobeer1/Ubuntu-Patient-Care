#!/usr/bin/env python3
"""
Model Setup Script for Ubuntu Patient Care - Orthanc Integration
Downloads required model weights for voice transcription functionality
"""

import os
import sys
import requests
import subprocess
from pathlib import Path

def download_file(url, local_path):
    """Download a file with progress indication"""
    print(f"Downloading {local_path.name}...")
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0
    
    os.makedirs(local_path.parent, exist_ok=True)
    
    with open(local_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"\rProgress: {percent:.1f}%", end='', flush=True)
    
    print(f"\n✓ Downloaded {local_path.name}")

def setup_whisper_models():
    """Setup Whisper models for voice transcription"""
    base_path = Path(__file__).parent
    models_dir = base_path / "medical-reporting-module" / "models" / "whisper"
    cache_dir = models_dir / "cache"
    
    # Create directories
    models_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(exist_ok=True)
    
    # For hackathon demo, we'll use a smaller model that can be downloaded quickly
    # Alternative: Use OpenAI's API or download pre-trained models
    
    print("Setting up voice transcription models...")
    
    try:
        # Install whisper if not available
        subprocess.run([sys.executable, "-m", "pip", "install", "openai-whisper"], check=True, capture_output=True)
        
        # Download base model (this will cache it automatically)
        import whisper
        print("Loading Whisper base model (this may take a few minutes on first run)...")
        model = whisper.load_model("base", download_root=str(models_dir))
        print("✓ Whisper model ready!")
        
        return True
        
    except Exception as e:
        print(f"Error setting up models: {e}")
        print("\nFor hackathon demo, you can:")
        print("1. Use the web interface without voice features initially")
        print("2. Upload your own model weights to: medical-reporting-module/models/whisper/")
        return False

def setup_environment():
    """Setup the complete environment"""
    print("🚀 Ubuntu Patient Care - Setting up environment for hackathon demo")
    print("=" * 60)
    
    # Install Python dependencies
    print("Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✓ Python dependencies installed")
    except:
        print("⚠ Could not install from requirements.txt - installing essential packages...")
        essential_packages = [
            "flask", "flask-cors", "sqlalchemy", "requests", 
            "pillow", "numpy", "pydicom", "openai-whisper"
        ]
        for package in essential_packages:
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", package], 
                              check=True, capture_output=True)
            except:
                print(f"Could not install {package}")
    
    # Setup models
    if setup_whisper_models():
        print("\n🎉 Setup complete! Ready for hackathon demo.")
    else:
        print("\n⚠ Setup completed with warnings. Voice features may need manual setup.")
    
    print("\nTo start the application:")
    print("1. cd medical-reporting-module")
    print("2. python app.py")
    print("\nFor development with auto-reload:")
    print("python app.py --debug")

if __name__ == "__main__":
    setup_environment()
