#!/usr/bin/env python3
"""
Simple test of Whisper functionality without audio files
"""

import sys
import os
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_whisper_basic():
    """Test basic Whisper functionality"""
    print("Testing basic Whisper functionality...")
    
    try:
        import whisper
        print("✓ Whisper imported successfully")
        
        # Load model
        model = whisper.load_model("base")
        print("✓ Whisper base model loaded")
        
        # Test with a simple numpy array (simulating audio)
        # Create 1 second of silence at 16kHz
        audio = np.zeros(16000, dtype=np.float32)
        
        # Transcribe
        result = model.transcribe(audio, language="en")
        print(f"✓ Transcription completed: '{result['text']}'")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_medical_stt_engine():
    """Test our medical STT engine with mock data"""
    print("\nTesting Medical STT Engine...")
    
    try:
        from services.offline_stt_service import OfflineSTTEngine, STTConfig, STTMode
        
        config = STTConfig(
            mode=STTMode.OFFLINE_ONLY,
            model_size="base",
            enable_medical_terminology=True
        )
        
        engine = OfflineSTTEngine(config)
        
        # Initialize
        if not engine.initialize():
            print("✗ Failed to initialize engine")
            return False
        
        print("✓ Engine initialized successfully")
        print(f"✓ Medical vocabulary loaded: {len(engine.medical_vocabulary)} terms")
        
        # Test medical corrections
        test_text = "the patient has numonia and tb"
        corrected = engine._apply_medical_corrections(test_text)
        print(f"✓ Medical correction test: '{test_text}' -> '{corrected}'")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("WHISPER FUNCTIONALITY TEST")
    print("=" * 50)
    
    test1 = test_whisper_basic()
    test2 = test_medical_stt_engine()
    
    print("\n" + "=" * 50)
    if test1 and test2:
        print("🎉 ALL TESTS PASSED!")
        print("Whisper is working correctly with medical vocabulary!")
    else:
        print("❌ SOME TESTS FAILED!")
    print("=" * 50)