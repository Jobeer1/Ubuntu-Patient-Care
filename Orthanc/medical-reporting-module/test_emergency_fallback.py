#!/usr/bin/env python3
"""
TEST EMERGENCY STT FALLBACK
"""

def test_emergency_fallback():
    """Test the emergency STT fallback service"""
    print("🚨 Testing Emergency STT Fallback...")
    
    try:
        from services.emergency_stt_service import emergency_stt
        
        # Test if service is available
        if emergency_stt.is_available():
            print("✅ Emergency STT service is available")
        else:
            print("❌ Emergency STT service not available")
            return False
        
        # Test with dummy audio data
        dummy_audio = b'RIFF\x24\x08\x00\x00WAVE' + b'\x00' * 100
        
        print(f"🎤 Testing transcription with {len(dummy_audio)} bytes of audio data...")
        
        transcription = emergency_stt.transcribe_audio_data(dummy_audio)
        
        if transcription:
            print(f"✅ Emergency STT transcription successful!")
            print(f"Result: '{transcription}'")
            return True
        else:
            print("❌ Emergency STT returned empty result")
            return False
            
    except Exception as e:
        print(f"❌ Emergency STT test failed: {e}")
        return False

def main():
    """Run emergency STT test"""
    print("=" * 50)
    print("🚨 EMERGENCY STT FALLBACK TEST")
    print("=" * 50)
    
    success = test_emergency_fallback()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 EMERGENCY FALLBACK WORKING!")
        print("💡 STT will now work even if Whisper file access fails")
    else:
        print("❌ EMERGENCY FALLBACK FAILED")
    print("=" * 50)

if __name__ == "__main__":
    main()
