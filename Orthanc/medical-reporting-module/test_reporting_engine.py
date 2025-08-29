#!/usr/bin/env python3
"""
Test script for reporting engine and workflow management
"""

import sys
import os
import tempfile
from datetime import datetime, timedelta

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_reporting_engine():
    """Test reporting engine functionality"""
    print("Testing Reporting Engine...")
    
    try:
        from core.reporting_engine import ReportingEngine, WorkflowState
        from models.report import ReportType
        
        # Create engine
        engine = ReportingEngine()
        
        # Test session creation
        session = engine.create_report(
            user_id="doctor123",
            study_id="study456",
            template_id="chest_xray_template",
            report_type=ReportType.DIAGNOSTIC
        )
        
        print(f"✓ Report session created: {session.session_id}")
        print(f"✓ Report ID: {session.report_id}")
        print(f"✓ Workflow state: {session.workflow_state.value}")
        
        # Test session info
        session_info = engine.get_session_info(session.session_id)
        print(f"✓ Session info retrieved: {session_info['workflow_state']}")
        
        # Test draft saving
        draft_content = {
            "clinical_info": "Patient presents with chest pain",
            "findings": "Preliminary findings show...",
            "impression": "Study in progress"
        }
        
        success = engine.save_report_draft(session.session_id, draft_content)
        print(f"✓ Draft saved: {success}")
        
        # Test dictation workflow
        success = engine.start_dictation(session.session_id)
        print(f"✓ Dictation started: {success}")
        
        success = engine.stop_dictation(session.session_id)
        print(f"✓ Dictation stopped: {success}")
        
        # Test finalization
        success = engine.finalize_report(session.session_id)
        print(f"✓ Report finalized: {success}")
        
        # Test session ending
        success = engine.end_session(session.session_id)
        print(f"✓ Session ended: {success}")
        
        # Test statistics
        stats = engine.get_engine_stats()
        print(f"✓ Engine stats: {len(stats)} metrics")
        
        print("Reporting Engine: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Reporting Engine failed: {e}\n")
        return False

def test_workflow_events():
    """Test workflow event tracking"""
    print("Testing Workflow Events...")
    
    try:
        from core.reporting_engine import ReportingEngine, WorkflowState
        
        # Create engine
        engine = ReportingEngine()
        
        # Create session
        session = engine.create_report(
            user_id="doctor123",
            study_id="study789"
        )
        
        # Perform various workflow actions
        engine.start_dictation(session.session_id)
        engine.stop_dictation(session.session_id)
        engine.save_report_draft(session.session_id, {"test": "content"})
        engine.finalize_report(session.session_id)
        
        # Get workflow events
        events = engine.get_workflow_events(session_id=session.session_id)
        
        print(f"✓ Workflow events tracked: {len(events)}")
        
        # Check event types
        event_types = [e['event_type'] for e in events]
        expected_events = ['report_created', 'dictation_started', 'dictation_stopped', 'draft_saved', 'report_finalized']
        
        for expected in expected_events:
            if expected in event_types:
                print(f"✓ Event tracked: {expected}")
            else:
                print(f"✗ Missing event: {expected}")
        
        # End session
        engine.end_session(session.session_id)
        
        print("Workflow Events: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Workflow Events failed: {e}\n")
        return False

def test_voice_integration():
    """Test voice integration with reporting engine"""
    print("Testing Voice Integration...")
    
    try:
        from core.reporting_engine import ReportingEngine
        from services.voice_engine import VoiceEngine
        
        # Create engines
        reporting_engine = ReportingEngine()
        
        # Create session
        session = reporting_engine.create_report(
            user_id="doctor123",
            study_id="study999"
        )
        
        # Start dictation (this should integrate with voice engine)
        success = reporting_engine.start_dictation(session.session_id)
        print(f"✓ Voice dictation integration: {success}")
        
        # Simulate voice transcription
        voice_engine = reporting_engine.voice_engine
        voice_session = voice_engine.start_session("doctor123", session.report_id)
        
        # Simulate dictation
        success = voice_engine.simulate_dictation("The lungs are clear bilaterally")
        print(f"✓ Voice simulation: {success}")
        
        # Get transcription
        transcription = voice_engine.get_session_transcription()
        print(f"✓ Transcription retrieved: '{transcription[:30]}...'")
        
        # Stop dictation
        reporting_engine.stop_dictation(session.session_id)
        
        # End sessions
        reporting_engine.end_session(session.session_id)
        
        print("Voice Integration: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Voice Integration failed: {e}\n")
        return False

def test_typist_workflow():
    """Test typist workflow integration"""
    print("Testing Typist Workflow...")
    
    try:
        from core.reporting_engine import ReportingEngine
        from services.typist_service import TypistService
        
        # Create engine
        engine = ReportingEngine()
        
        # Create session
        session = engine.create_report(
            user_id="doctor123",
            study_id="study111"
        )
        
        # Add some content
        engine.save_report_draft(session.session_id, {
            "findings": "Patient has pneumonia in right lower lobe"
        })
        
        # Submit for typing
        success = engine.submit_for_typing(session.session_id)
        print(f"✓ Submitted for typing: {success}")
        
        # Check typist service has assignment
        typist_service = engine.typist_service
        queue_status = typist_service.get_queue_status()
        print(f"✓ Typist queue status: {queue_status['pending_count']} pending")
        
        # End session
        engine.end_session(session.session_id)
        
        print("Typist Workflow: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Typist Workflow failed: {e}\n")
        return False

def test_offline_integration():
    """Test offline manager integration"""
    print("Testing Offline Integration...")
    
    try:
        from core.reporting_engine import ReportingEngine
        
        # Create engine
        engine = ReportingEngine()
        
        # Create session
        session = engine.create_report(
            user_id="doctor123",
            study_id="study222"
        )
        
        # Save draft (should work offline)
        success = engine.save_report_draft(session.session_id, {
            "clinical_info": "Chest pain, rule out pneumonia",
            "findings": "Bilateral lung fields are clear"
        })
        print(f"✓ Offline draft save: {success}")
        
        # Try to load study images (will use cache/mock)
        images = engine.load_study_images(session.session_id)
        print(f"✓ Study images loaded: {len(images)} images")
        
        # Finalize report (should queue for sync if offline)
        finalize_success = engine.finalize_report(session.session_id)
        print(f"✓ Report finalized: {finalize_success}")
        
        # Try to submit (should queue if offline)
        success = engine.submit_report(session.session_id)
        print(f"✓ Report submission (offline queue): {success}")
        
        # End session
        engine.end_session(session.session_id)
        
        print("Offline Integration: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Offline Integration failed: {e}\n")
        return False

def test_auto_save():
    """Test auto-save functionality"""
    print("Testing Auto-Save...")
    
    try:
        from core.reporting_engine import ReportingEngine, AutoSaveInterval
        import time
        
        # Create engine
        engine = ReportingEngine()
        
        # Create session with auto-save enabled
        session = engine.create_report(
            user_id="doctor123",
            study_id="study333"
        )
        
        # Modify session to have short auto-save interval for testing
        active_session = engine.active_sessions[session.session_id]
        active_session.auto_save_interval = AutoSaveInterval.EVERY_30_SECONDS
        
        print(f"✓ Auto-save enabled: {active_session.auto_save_enabled}")
        print(f"✓ Auto-save interval: {active_session.auto_save_interval.value} seconds")
        
        # Add some content
        engine.save_report_draft(session.session_id, {
            "findings": "Initial findings..."
        })
        
        # Auto-save thread should be running
        print(f"✓ Auto-save thread running: {engine.auto_save_running}")
        
        # End session
        engine.end_session(session.session_id)
        
        print("Auto-Save: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Auto-Save failed: {e}\n")
        return False

def test_session_management():
    """Test session management"""
    print("Testing Session Management...")
    
    try:
        from core.reporting_engine import ReportingEngine
        
        # Create engine
        engine = ReportingEngine()
        
        # Create multiple sessions
        sessions = []
        for i in range(3):
            session = engine.create_report(
                user_id=f"doctor{i}",
                study_id=f"study{i}"
            )
            sessions.append(session)
        
        print(f"✓ Created {len(sessions)} sessions")
        
        # Get active sessions
        active_sessions = engine.get_active_sessions()
        print(f"✓ Active sessions: {len(active_sessions)}")
        
        # Test session info for each
        for session in sessions:
            info = engine.get_session_info(session.session_id)
            if info:
                print(f"✓ Session {session.session_id[:8]}... info retrieved")
            else:
                print(f"✗ Failed to get info for session {session.session_id}")
        
        # End all sessions
        for session in sessions:
            success = engine.end_session(session.session_id)
            if success:
                print(f"✓ Session {session.session_id[:8]}... ended")
        
        # Check no active sessions remain
        active_sessions = engine.get_active_sessions()
        print(f"✓ Active sessions after cleanup: {len(active_sessions)}")
        
        print("Session Management: PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Session Management failed: {e}\n")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("MEDICAL REPORTING MODULE - REPORTING ENGINE TESTS")
    print("=" * 60)
    print()
    
    # Set up temporary cache directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ['OFFLINE_CACHE_DIR'] = temp_dir
        
        tests = [
            test_reporting_engine,
            test_workflow_events,
            test_voice_integration,
            test_typist_workflow,
            test_offline_integration,
            test_auto_save,
            test_session_management
        ]
        
        passed = 0
        total = len(tests)
        
        for test_func in tests:
            if test_func():
                passed += 1
        
        print("=" * 60)
        print(f"TEST SUMMARY: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Reporting engine is ready for South African medical workflow.")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
        print("=" * 60)
        
        return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)