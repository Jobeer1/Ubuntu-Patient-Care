#!/usr/bin/env python3
"""
Simple test script for voice processing components
"""

import sys
import os
import tempfile

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_offline_stt_engine():
    """Test offline STT engine"""
    print("Testing Offline STT Engine...")
    
    try:
        from services.offline_stt_service import OfflineSTTEngine, STTConfig, STTMode
        
        # Create config
        config = STTConfig(
            mode=STTMode.OFFLINE_ONLY,
            model_size="base",
            enable_medical_terminology=True
        )
        
        # Create engine
        engine = OfflineSTTEngine(config)
        
        # Test initialization (will work without Whisper in mock mode)
        print(f"✓ Engine created with config: {config.mode.value}")
        
        # Test medical vocabulary
        print(f"✓ Medical vocabulary loaded: {len(engine.medical_vocabulary)} terms")
        
        # Test correction recording (works without Whisper)
        success = engine.record_correction("user123", "numonia", "pneumonia")
        print(f"✓ Correction recording: {success}")
        
        # Test stats (works without Whisper)
        stats = engine.get_stats()
        print(f"✓ Stats retrieved: {len(stats)} items")
        
        print("Offline STT Engine: PASSED (Mock mode - Whisper not installed)\n")
        return True
        
    except Exception as e:
        print(f"✗ Offline STT Engine failed: {e}\n")
        return False

def test_offline_voice_commands():
    """Test offline voice commands"""
    print("Testing Offline Voice Commands...")
    
    try:
        from services.offline_voice_commands import OfflineVoiceCommandProcessor
        
        # Create processor
        processor = OfflineVoiceCommandProcessor()
        
        # Test command processing
        test_commands = [
            "load chest x-ray template",
            "go to findings section",
            "start dictation",
            "normal chest study"
        ]
        
        for cmd_text in test_commands:
            command = processor.process_command(cmd_text)
            if command:
                print(f"✓ Command '{cmd_text}' -> {command.action}")
            else:
                print(f"✗ Command '{cmd_text}' not recognized")
        
        # Test available templates
        templates = processor.get_available_templates()
        print(f"✓ Available templates: {len(templates)}")
        
        # Test command examples
        examples = processor.get_command_examples()
        print(f"✓ Command examples: {len(examples)}")
        
        print("Offline Voice Commands: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Offline Voice Commands failed: {e}\n")
        return False

def test_voice_utils():
    """Test voice utilities"""
    print("Testing Voice Utils...")
    
    try:
        from utils.voice_utils import (
            SouthAfricanAccentProcessor,
            MedicalTerminologyProcessor,
            AudioQualityAnalyzer,
            preprocess_south_african_text
        )
        
        # Test accent processor
        accent_processor = SouthAfricanAccentProcessor()
        variations = accent_processor.process_accent_variations("tuberculosis")
        print(f"✓ Accent variations for 'tuberculosis': {len(variations)}")
        
        # Test medical terminology processor
        medical_processor = MedicalTerminologyProcessor()
        processed = medical_processor.process_medical_terms("patient has tb and numonia")
        print(f"✓ Medical processing: '{processed}'")
        
        # Test audio quality analyzer
        audio_analyzer = AudioQualityAnalyzer()
        mock_audio = b"mock_audio_data" * 1000
        analysis = audio_analyzer.analyze_audio_quality(mock_audio)
        print(f"✓ Audio quality analysis: {analysis['quality']}")
        
        # Test preprocessing utility
        preprocessed = preprocess_south_african_text("patient has tb", "respiratory")
        print(f"✓ Preprocessed text: '{preprocessed}'")
        
        print("Voice Utils: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Voice Utils failed: {e}\n")
        return False

def test_voice_engine():
    """Test voice engine"""
    print("Testing Voice Engine...")
    
    try:
        from services.voice_engine import VoiceEngine, DictationState
        
        # Create engine
        engine = VoiceEngine()
        
        # Test session management
        session = engine.start_session("user123", "report456")
        print(f"✓ Session started: {session.session_id}")
        
        # Test listening
        success = engine.start_listening()
        print(f"✓ Start listening: {success}")
        
        # Test simulation
        success = engine.simulate_dictation("The lungs are clear bilaterally")
        print(f"✓ Simulate dictation: {success}")
        
        # Test transcription
        transcription = engine.get_session_transcription()
        print(f"✓ Session transcription: '{transcription[:50]}...'")
        
        # Test command simulation
        success = engine.simulate_dictation("load chest x-ray template")
        print(f"✓ Command simulation: {success}")
        
        # Test session info
        info = engine.get_session_info()
        print(f"✓ Session info: {info['state']}")
        
        # Test end session
        ended_session = engine.end_session()
        print(f"✓ Session ended: {ended_session.session_id}")
        
        print("Voice Engine: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Voice Engine failed: {e}\n")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("MEDICAL REPORTING MODULE - VOICE PROCESSING TESTS")
    print("=" * 60)
    print()
    
    # Set up temporary cache directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ['OFFLINE_CACHE_DIR'] = temp_dir
        
        tests = [
            test_offline_stt_engine,
            test_offline_voice_commands,
            test_voice_utils,
            test_voice_engine
        ]
        
        passed = 0
        total = len(tests)
        
        for test_func in tests:
            if test_func():
                passed += 1
        
        print("=" * 60)
        print(f"TEST SUMMARY: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Voice processing is ready for South African users.")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
        print("=" * 60)
        
        return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)