#!/usr/bin/env python3
"""
WHISPER DEPENDENCY DIAGNOSTIC
"""

def check_whisper_dependencies():
    """Check all Whisper dependencies"""
    print("🔍 Checking Whisper Dependencies...")
    
    # Check 1: Whisper import
    try:
        import whisper
        print("✅ Whisper module imported")
    except ImportError as e:
        print(f"❌ Whisper import failed: {e}")
        return False
    
    # Check 2: Torch (required by Whisper)
    try:
        import torch
        print(f"✅ PyTorch version: {torch.__version__}")
    except ImportError as e:
        print(f"❌ PyTorch not available: {e}")
        return False
    
    # Check 3: FFmpeg (critical for audio processing)
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ FFmpeg is available in PATH")
        else:
            print("❌ FFmpeg found but returned error")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg not found in PATH")
        print("💡 This is likely the root cause!")
        return False
    except subprocess.TimeoutExpired:
        print("❌ FFmpeg check timed out")
        return False
    except Exception as e:
        print(f"❌ FFmpeg check failed: {e}")
        return False
    
    # Check 4: Audio processing libs
    try:
        import librosa
        print("✅ Librosa available")
    except ImportError:
        print("⚠️  Librosa not available (optional)")
    
    try:
        import soundfile
        print("✅ SoundFile available")
    except ImportError:
        print("⚠️  SoundFile not available (optional)")
    
    return True

def suggest_fixes():
    """Suggest fixes for common issues"""
    print("\n🔧 SUGGESTED FIXES:")
    print("=" * 40)
    print("1. Install FFmpeg:")
    print("   - Download from: https://ffmpeg.org/download.html")
    print("   - Add to Windows PATH environment variable")
    print("   - OR use: conda install ffmpeg")
    print()
    print("2. Alternative: Install conda-forge version:")
    print("   conda install -c conda-forge ffmpeg")
    print()
    print("3. Quick test FFmpeg:")
    print("   ffmpeg -version")
    print()
    print("4. If using pip, try:")
    print("   pip install ffmpeg-python")

def main():
    """Run dependency diagnostic"""
    print("=" * 60)
    print("🔍 WHISPER DEPENDENCY DIAGNOSTIC")
    print("=" * 60)
    
    all_good = check_whisper_dependencies()
    
    if not all_good:
        suggest_fixes()
    else:
        print("\n✅ All dependencies look good!")
        print("The issue might be elsewhere...")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
