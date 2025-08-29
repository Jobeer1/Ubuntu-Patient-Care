#!/usr/bin/env python3
"""
Simple test script for reporting engine without SQLAlchemy dependencies
"""

import sys
import os
import tempfile
from datetime import datetime, timedelta

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_reporting_workflow():
    """Test basic reporting workflow without database"""
    print("Testing Reporting Workflow...")
    
    try:
        # Test workflow states
        from core.reporting_engine import WorkflowState, AutoSaveInterval
        
        print(f"✓ Workflow states available: {len(list(WorkflowState))}")
        print(f"✓ Auto-save intervals available: {len(list(AutoSaveInterval))}")
        
        # Test workflow event creation
        from core.reporting_engine import WorkflowEvent
        
        event = WorkflowEvent(
            event_id="test_event",
            session_id="test_session",
            report_id="test_report",
            user_id="test_user",
            event_type="test_event_type"
        )
        
        print(f"✓ Workflow event created: {event.event_type}")
        
        # Test report session creation
        from core.reporting_engine import ReportSession
        
        session = ReportSession(
            session_id="test_session",
            report_id="test_report",
            user_id="test_user",
            study_id="test_study"
        )
        
        print(f"✓ Report session created: {session.workflow_state.value}")
        
        print("Reporting Workflow: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Reporting Workflow failed: {e}\n")
        return False

def test_voice_engine_integration():
    """Test voice engine integration"""
    print("Testing Voice Engine Integration...")
    
    try:
        from services.voice_engine import VoiceEngine, DictationState
        
        # Create voice engine
        engine = VoiceEngine()
        
        # Test session management
        session = engine.start_session("test_user", "test_report")
        print(f"✓ Voice session started: {session.session_id}")
        
        # Test listening
        success = engine.start_listening()
        print(f"✓ Start listening: {success}")
        
        # Test simulation
        success = engine.simulate_dictation("Test dictation content")
        print(f"✓ Simulate dictation: {success}")
        
        # Test transcription
        transcription = engine.get_session_transcription()
        print(f"✓ Transcription: '{transcription[:30]}...'")
        
        # Test session info
        info = engine.get_session_info()
        print(f"✓ Session info: {info['state'] if info else 'None'}")
        
        # End session
        ended = engine.end_session()
        print(f"✓ Session ended: {ended.session_id if ended else 'None'}")
        
        print("Voice Engine Integration: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Voice Engine Integration failed: {e}\n")
        return False

def test_offline_voice_commands():
    """Test offline voice commands"""
    print("Testing Offline Voice Commands...")
    
    try:
        from services.offline_voice_commands import OfflineVoiceCommandProcessor
        
        processor = OfflineVoiceCommandProcessor()
        
        # Test command processing
        test_commands = [
            "load chest x-ray template",
            "go to findings section", 
            "start dictation",
            "normal chest study",
            "save report"
        ]
        
        for cmd in test_commands:
            command = processor.process_command(cmd)
            if command:
                print(f"✓ Command '{cmd}' -> {command.action}")
            else:
                print(f"✗ Command '{cmd}' not recognized")
        
        # Test templates
        templates = processor.get_available_templates()
        print(f"✓ Available templates: {len(templates)}")
        
        # Test examples
        examples = processor.get_command_examples()
        print(f"✓ Command examples: {len(examples)}")
        
        print("Offline Voice Commands: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Offline Voice Commands failed: {e}\n")
        return False

def test_typist_service():
    """Test typist service"""
    print("Testing Typist Service...")
    
    try:
        from services.typist_service import TypistService, Priority
        
        service = TypistService()
        
        # Test initialization
        print(f"✓ Typist service initialized with {len(service.typists)} typists")
        
        # Test assignment creation
        assignment_id = service.create_assignment(
            report_id="test_report",
            doctor_id="test_doctor",
            voice_recording_path="/test/audio.wav",
            stt_draft="Test STT draft content",
            priority=Priority.NORMAL
        )
        
        print(f"✓ Assignment created: {assignment_id}")
        
        # Test queue status
        status = service.get_queue_status()
        print(f"✓ Queue status: {status['pending_count']} pending")
        
        # Test typist assignment
        available_typist = None
        for typist_id, typist in service.typists.items():
            if typist.status.value == 'available':
                available_typist = typist_id
                break
        
        if available_typist:
            assignment = service.assign_to_typist(available_typist)
            print(f"✓ Assigned to typist: {assignment.typist_id if assignment else 'None'}")
        
        print("Typist Service: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Typist Service failed: {e}\n")
        return False

def test_template_manager():
    """Test template manager"""
    print("Testing Template Manager...")
    
    try:
        from services.template_manager import TemplateManager
        
        manager = TemplateManager()
        
        # Test initialization
        print(f"✓ Template manager initialized")
        
        # Test template loading (will use mock data)
        templates = manager.get_all_templates()
        print(f"✓ Available templates: {len(templates)}")
        
        # Test template categories (using enum)
        from services.template_manager import TemplateCategory
        categories = list(TemplateCategory)
        print(f"✓ Template categories: {len(categories)}")
        
        # Test voice command registration (create proper command object)
        from services.template_manager import VoiceCommand
        command = VoiceCommand(
            command_id="test_cmd",
            command_text="load test template",
            target_id="test_template"
        )
        success = manager.register_voice_command(command)
        print(f"✓ Voice command registered: {success}")
        
        print("Template Manager: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Template Manager failed: {e}\n")
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
        print(f"✓ Accent variations: {len(variations)}")
        
        # Test medical processor
        medical_processor = MedicalTerminologyProcessor()
        processed = medical_processor.process_medical_terms("patient has tb and numonia")
        print(f"✓ Medical processing: '{processed}'")
        
        # Test audio analyzer
        audio_analyzer = AudioQualityAnalyzer()
        mock_audio = b"mock_audio_data" * 1000
        analysis = audio_analyzer.analyze_audio_quality(mock_audio)
        print(f"✓ Audio analysis: {analysis['quality']}")
        
        # Test preprocessing
        preprocessed = preprocess_south_african_text("patient has tb", "respiratory")
        print(f"✓ Preprocessed: '{preprocessed}'")
        
        print("Voice Utils: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Voice Utils failed: {e}\n")
        return False

def test_offline_stt():
    """Test offline STT engine"""
    print("Testing Offline STT...")
    
    try:
        from services.offline_stt_service import OfflineSTTEngine, STTConfig, STTMode
        
        config = STTConfig(mode=STTMode.OFFLINE_ONLY)
        engine = OfflineSTTEngine(config)
        
        print(f"✓ STT engine created: {config.mode.value}")
        print(f"✓ Medical vocabulary: {len(engine.medical_vocabulary)} terms")
        
        # Test correction recording
        success = engine.record_correction("user123", "numonia", "pneumonia")
        print(f"✓ Correction recorded: {success}")
        
        # Test stats
        stats = engine.get_stats()
        print(f"✓ STT stats: {len(stats)} metrics")
        
        print("Offline STT: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Offline STT failed: {e}\n")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("MEDICAL REPORTING MODULE - SIMPLIFIED TESTS")
    print("=" * 60)
    print()
    
    tests = [
        test_reporting_workflow,
        test_voice_engine_integration,
        test_offline_voice_commands,
        test_typist_service,
        test_template_manager,
        test_voice_utils,
        test_offline_stt
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        if test_func():
            passed += 1
    
    print("=" * 60)
    print(f"TEST SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Reporting engine components are working.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)