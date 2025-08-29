"""
Tests for voice processing engine components
"""

import unittest
import tempfile
import os
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Import the components we're testing
from services.voice_engine import VoiceEngine, VoiceSession, VoiceCommand, VoiceCommandType, DictationState
from services.stt_service import (
    STTService, STTConfig, STTProvider, VoiceCommandProcessor, 
    STTLearningEngine, AudioQuality, STTResult
)
from services.typist_service import (
    TypistService, Typist, TypistAssignment, TypistFeedback,
    TypistStatus, ReportStatus, Priority
)
from utils.voice_utils import (
    SouthAfricanAccentProcessor, MedicalTerminologyProcessor,
    AudioQualityAnalyzer, preprocess_south_african_text
)

class TestVoiceEngine(unittest.TestCase):
    """Test cases for VoiceEngine"""
    
    def setUp(self):
        self.voice_engine = VoiceEngine()
    
    def test_voice_engine_initialization(self):
        """Test voice engine initializes correctly"""
        self.assertIsNotNone(self.voice_engine)
        self.assertIsNone(self.voice_engine.current_session)
        self.assertTrue(len(self.voice_engine.voice_commands) > 0)
        self.assertTrue(len(self.voice_engine.medical_vocabulary) > 0)
    
    def test_start_session(self):
        """Test starting a voice session"""
        session = self.voice_engine.start_session("user123", "report456")
        
        self.assertIsNotNone(session)
        self.assertEqual(session.user_id, "user123")
        self.assertEqual(session.report_id, "report456")
        self.assertEqual(session.state, DictationState.IDLE)
        self.assertEqual(self.voice_engine.current_session, session)
    
    def test_start_listening(self):
        """Test starting to listen for voice input"""
        # Start session first
        session = self.voice_engine.start_session("user123")
        
        # Start listening
        result = self.voice_engine.start_listening()
        
        self.assertTrue(result)
        self.assertEqual(session.state, DictationState.LISTENING)
    
    def test_stop_listening(self):
        """Test stopping voice input"""
        # Start session and listening
        session = self.voice_engine.start_session("user123")
        self.voice_engine.start_listening()
        
        # Stop listening
        result = self.voice_engine.stop_listening()
        
        self.assertTrue(result)
        self.assertEqual(session.state, DictationState.IDLE)
    
    def test_simulate_dictation(self):
        """Test simulating dictation input"""
        # Start session
        session = self.voice_engine.start_session("user123")
        
        # Simulate dictation
        test_text = "The lungs are clear bilaterally"
        result = self.voice_engine.simulate_dictation(test_text)
        
        self.assertTrue(result)
        self.assertEqual(len(session.transcription_segments), 1)
        self.assertIn("clear bilaterally", session.transcription_segments[0]['processed_text'])
    
    def test_voice_command_detection(self):
        """Test voice command detection"""
        # Start session
        session = self.voice_engine.start_session("user123")
        
        # Test command detection
        command_executed = []
        
        def command_callback(command):
            command_executed.append(command)
        
        self.voice_engine.add_command_callback(command_callback)
        
        # Simulate command
        self.voice_engine.simulate_dictation("load chest x-ray template")
        
        # Should have executed command, not added to transcription
        self.assertEqual(len(session.transcription_segments), 0)
        self.assertEqual(len(session.commands_executed), 1)
    
    def test_medical_terminology_processing(self):
        """Test medical terminology processing"""
        # Start session
        session = self.voice_engine.start_session("user123")
        
        # Test medical term correction
        self.voice_engine.simulate_dictation("patient has tb and pneumonia")
        
        transcription = self.voice_engine.get_session_transcription()
        self.assertIn("tuberculosis", transcription.lower())
        self.assertIn("pneumonia", transcription.lower())
    
    def test_end_session(self):
        """Test ending a voice session"""
        # Start session
        session = self.voice_engine.start_session("user123")
        session_id = session.session_id
        
        # End session
        ended_session = self.voice_engine.end_session()
        
        self.assertIsNotNone(ended_session)
        self.assertEqual(ended_session.session_id, session_id)
        self.assertIsNone(self.voice_engine.current_session)
        self.assertIsNotNone(ended_session.end_time)

class TestSTTService(unittest.TestCase):
    """Test cases for STTService"""
    
    def setUp(self):
        self.config = STTConfig(provider=STTProvider.MOCK)
        self.stt_service = STTService(self.config)
    
    def test_stt_service_initialization(self):
        """Test STT service initializes correctly"""
        self.assertIsNotNone(self.stt_service)
        self.assertEqual(self.stt_service.config.provider, STTProvider.MOCK)
        self.assertIsNotNone(self.stt_service.command_processor)
        self.assertIsNotNone(self.stt_service.learning_engine)
    
    def test_mock_stt_processing(self):
        """Test mock STT processing"""
        # Create mock audio data
        audio_data = b"mock_audio_data" * 100
        
        # Process audio
        result = self.stt_service.process_audio(audio_data, "user123")
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, STTResult)
        self.assertTrue(len(result.text) > 0)
        self.assertGreater(result.confidence, 0.0)
        self.assertIsInstance(result.audio_quality, AudioQuality)
    
    def test_medical_vocabulary_application(self):
        """Test medical vocabulary corrections"""
        # Test with medical terms
        test_text = "patient has tb and numonia"
        corrected = self.stt_service._apply_medical_vocabulary(test_text)
        
        self.assertIn("tuberculosis", corrected.lower())
        self.assertIn("pneumonia", corrected.lower())
    
    def test_audio_quality_assessment(self):
        """Test audio quality assessment"""
        # Test different audio sizes
        poor_audio = b"x" * 500
        good_audio = b"x" * 8000
        
        poor_quality = self.stt_service._assess_audio_quality(poor_audio)
        good_quality = self.stt_service._assess_audio_quality(good_audio)
        
        # Good audio should have better quality
        quality_order = [AudioQuality.POOR, AudioQuality.FAIR, AudioQuality.GOOD, AudioQuality.EXCELLENT]
        self.assertLessEqual(quality_order.index(poor_quality), quality_order.index(good_quality))

class TestVoiceCommandProcessor(unittest.TestCase):
    """Test cases for VoiceCommandProcessor"""
    
    def setUp(self):
        self.processor = VoiceCommandProcessor()
    
    def test_template_command_detection(self):
        """Test template loading command detection"""
        test_cases = [
            "load chest x-ray template",
            "use ct chest template",
            "open tuberculosis template"
        ]
        
        for test_text in test_cases:
            command = self.processor.process_command(test_text)
            self.assertIsNotNone(command)
            self.assertEqual(command["action"], "load_template")
    
    def test_navigation_command_detection(self):
        """Test navigation command detection"""
        test_cases = [
            "go to findings",
            "move to impression section",
            "jump to conclusion"
        ]
        
        for test_text in test_cases:
            command = self.processor.process_command(test_text)
            self.assertIsNotNone(command)
            self.assertEqual(command["action"], "navigate_section")
    
    def test_dictation_control_commands(self):
        """Test dictation control commands"""
        test_cases = [
            ("start dictation", "start"),
            ("stop dictation", "stop"),
            ("pause dictation", "pause")
        ]
        
        for test_text, expected_param in test_cases:
            command = self.processor.process_command(test_text)
            self.assertIsNotNone(command)
            self.assertEqual(command["action"], "dictation_control")
            self.assertEqual(command["parameter"], expected_param)
    
    def test_template_mapping(self):
        """Test template name mapping"""
        command = self.processor.process_command("load chest x-ray template")
        
        self.assertIsNotNone(command)
        self.assertIn("template_id", command)
        self.assertEqual(command["template_id"], "chest_xray_template")

class TestSTTLearningEngine(unittest.TestCase):
    """Test cases for STTLearningEngine"""
    
    def setUp(self):
        self.learning_engine = STTLearningEngine()
    
    def test_record_correction(self):
        """Test recording corrections"""
        result = self.learning_engine.record_correction(
            "user123",
            "numonia in the lung",
            "pneumonia in the lung",
            "chest x-ray report"
        )
        
        self.assertTrue(result)
        self.assertEqual(len(self.learning_engine.correction_history), 1)
        self.assertIn("user123", self.learning_engine.user_corrections)
    
    def test_medical_term_learning(self):
        """Test medical term correction learning"""
        # Record medical term correction
        self.learning_engine.record_correction(
            "user123",
            "numonia",
            "pneumonia"
        )
        
        # Check if learned
        self.assertIn("numonia", self.learning_engine.medical_term_corrections)
        self.assertEqual(self.learning_engine.medical_term_corrections["numonia"], "pneumonia")
    
    def test_apply_learned_corrections(self):
        """Test applying learned corrections"""
        # Record correction
        self.learning_engine.record_correction(
            "user123",
            "tuberkulosis",
            "tuberculosis"
        )
        
        # Apply to new text
        test_text = "patient has tuberkulosis"
        corrected = self.learning_engine.apply_learned_corrections(test_text, "user123")
        
        self.assertIn("tuberculosis", corrected)
    
    def test_learning_stats(self):
        """Test learning statistics"""
        # Record some corrections
        self.learning_engine.record_correction("user123", "original1", "corrected1")
        self.learning_engine.record_correction("user123", "original2", "corrected2")
        
        stats = self.learning_engine.get_learning_stats("user123")
        
        self.assertEqual(stats["total_corrections"], 2)
        self.assertEqual(stats["user_corrections"], 2)

class TestTypistService(unittest.TestCase):
    """Test cases for TypistService"""
    
    def setUp(self):
        self.typist_service = TypistService()
    
    def test_typist_service_initialization(self):
        """Test typist service initializes with demo data"""
        self.assertGreater(len(self.typist_service.typists), 0)
        
        # Check demo typists
        for typist in self.typist_service.typists.values():
            self.assertIsInstance(typist, Typist)
            self.assertTrue(len(typist.name) > 0)
    
    def test_create_assignment(self):
        """Test creating typist assignment"""
        assignment_id = self.typist_service.create_assignment(
            report_id="report123",
            doctor_id="doctor456",
            voice_recording_path="/path/to/audio.wav",
            stt_draft="The lungs are clear bilaterally",
            priority=Priority.HIGH,
            audio_duration=120.0
        )
        
        self.assertIsNotNone(assignment_id)
        
        # Check assignment in queue
        assignment = self.typist_service.queue.assignments.get(assignment_id)
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.report_id, "report123")
        self.assertEqual(assignment.priority, Priority.HIGH)
    
    def test_assign_to_typist(self):
        """Test assigning work to typist"""
        # Create assignment first
        assignment_id = self.typist_service.create_assignment(
            report_id="report123",
            doctor_id="doctor456",
            voice_recording_path="/path/to/audio.wav",
            stt_draft="Test report content"
        )
        
        # Find available typist
        available_typist = None
        for typist_id, typist in self.typist_service.typists.items():
            if typist.status == TypistStatus.AVAILABLE:
                available_typist = typist_id
                break
        
        self.assertIsNotNone(available_typist)
        
        # Assign to typist
        assignment = self.typist_service.assign_to_typist(available_typist)
        
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.typist_id, available_typist)
        self.assertEqual(assignment.status, ReportStatus.ASSIGNED)
    
    def test_complete_assignment(self):
        """Test completing assignment"""
        # Create and assign
        assignment_id = self.typist_service.create_assignment(
            report_id="report123",
            doctor_id="doctor456",
            voice_recording_path="/path/to/audio.wav",
            stt_draft="Test report content"
        )
        
        # Find available typist and assign
        for typist_id, typist in self.typist_service.typists.items():
            if typist.status == TypistStatus.AVAILABLE:
                assignment = self.typist_service.assign_to_typist(typist_id)
                break
        
        # Start work
        self.typist_service.start_work(assignment_id)
        
        # Complete assignment
        result = self.typist_service.complete_assignment(
            assignment_id,
            "Corrected report content",
            15.0,  # completion time
            3      # corrections made
        )
        
        self.assertTrue(result)
        
        # Check assignment status
        assignment = self.typist_service.queue.assignments[assignment_id]
        self.assertEqual(assignment.status, ReportStatus.COMPLETED)
        self.assertEqual(assignment.actual_completion_time, 15.0)
    
    def test_submit_feedback(self):
        """Test submitting feedback"""
        # Create assignment
        assignment_id = self.typist_service.create_assignment(
            report_id="report123",
            doctor_id="doctor456",
            voice_recording_path="/path/to/audio.wav",
            stt_draft="Original STT text"
        )
        
        # Submit feedback
        feedback_id = self.typist_service.submit_feedback(
            assignment_id=assignment_id,
            typist_id="typist_001",
            corrected_text="Corrected text",
            error_categories=["medical_terminology", "pronunciation"],
            audio_quality_rating=4,
            difficulty_rating=3,
            suggestions="Improve medical vocabulary"
        )
        
        self.assertIsNotNone(feedback_id)
        self.assertEqual(len(self.typist_service.feedback_history), 1)
        
        feedback = self.typist_service.feedback_history[0]
        self.assertEqual(feedback.assignment_id, assignment_id)
        self.assertEqual(feedback.audio_quality_rating, 4)
    
    def test_queue_statistics(self):
        """Test queue statistics"""
        # Create some assignments
        for i in range(3):
            self.typist_service.create_assignment(
                report_id=f"report{i}",
                doctor_id="doctor456",
                voice_recording_path="/path/to/audio.wav",
                stt_draft=f"Test report {i}"
            )
        
        stats = self.typist_service.get_queue_status()
        
        self.assertIn("total_typists", stats)
        self.assertIn("pending_count", stats)
        self.assertGreater(stats["total_typists"], 0)

class TestSouthAfricanAccentProcessor(unittest.TestCase):
    """Test cases for South African accent processing"""
    
    def setUp(self):
        self.processor = SouthAfricanAccentProcessor()
    
    def test_accent_processor_initialization(self):
        """Test accent processor initializes correctly"""
        self.assertIsNotNone(self.processor.accent_patterns)
        self.assertIsNotNone(self.processor.pronunciation_mappings)
        self.assertGreater(len(self.processor.pronunciation_mappings), 0)
    
    def test_pronunciation_mappings(self):
        """Test pronunciation mappings"""
        # Test some South African pronunciations
        mappings = self.processor.pronunciation_mappings
        
        self.assertIn("about", mappings)
        self.assertIn("tuberculosis", mappings)
        self.assertIn("pneumonia", mappings)
    
    def test_accent_variations(self):
        """Test generating accent variations"""
        test_text = "The patient has tuberculosis"
        variations = self.processor.process_accent_variations(test_text)
        
        self.assertIsInstance(variations, list)
        self.assertGreater(len(variations), 0)
        self.assertIn(test_text, variations)  # Original should be included

class TestMedicalTerminologyProcessor(unittest.TestCase):
    """Test cases for medical terminology processing"""
    
    def setUp(self):
        self.processor = MedicalTerminologyProcessor()
    
    def test_medical_processor_initialization(self):
        """Test medical processor initializes correctly"""
        self.assertIsNotNone(self.processor.medical_dictionary)
        self.assertIsNotNone(self.processor.abbreviation_expansions)
        self.assertGreater(len(self.processor.medical_dictionary), 0)
    
    def test_abbreviation_expansion(self):
        """Test medical abbreviation expansion"""
        test_text = "patient has tb and hiv"
        processed = self.processor.process_medical_terms(test_text)
        
        self.assertIn("tuberculosis", processed.lower())
        self.assertIn("human immunodeficiency virus", processed.lower())
    
    def test_medical_term_correction(self):
        """Test medical term correction"""
        test_text = "patient has numonia and silicosis"
        processed = self.processor.process_medical_terms(test_text)
        
        self.assertIn("pneumonia", processed.lower())
        self.assertIn("silicosis", processed.lower())
    
    def test_term_suggestions(self):
        """Test medical term suggestions"""
        suggestions = self.processor.get_term_suggestions("pneum")
        
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        
        # Should include pneumonia-related terms
        suggestion_text = " ".join(suggestions).lower()
        self.assertIn("pneumonia", suggestion_text)
    
    def test_context_aware_processing(self):
        """Test context-aware medical term processing"""
        respiratory_context = "chest x-ray respiratory examination"
        
        suggestions = self.processor.get_term_suggestions("tb", respiratory_context)
        
        # Should prioritize respiratory-related terms
        self.assertIsInstance(suggestions, list)

class TestAudioQualityAnalyzer(unittest.TestCase):
    """Test cases for audio quality analysis"""
    
    def setUp(self):
        self.analyzer = AudioQualityAnalyzer()
    
    def test_analyzer_initialization(self):
        """Test analyzer initializes correctly"""
        self.assertIsNotNone(self.analyzer.quality_thresholds)
        self.assertIn("excellent", self.analyzer.quality_thresholds)
        self.assertIn("poor", self.analyzer.quality_thresholds)
    
    def test_audio_quality_analysis(self):
        """Test audio quality analysis"""
        # Create mock audio data of different sizes
        small_audio = b"x" * 500
        large_audio = b"x" * 10000
        
        small_result = self.analyzer.analyze_audio_quality(small_audio)
        large_result = self.analyzer.analyze_audio_quality(large_audio)
        
        self.assertIn("quality", small_result)
        self.assertIn("metrics", small_result)
        self.assertIn("quality", large_result)
        self.assertIn("metrics", large_result)
        
        # Larger audio should generally have better quality
        quality_levels = ["poor", "fair", "good", "excellent"]
        small_quality_idx = quality_levels.index(small_result["quality"])
        large_quality_idx = quality_levels.index(large_result["quality"])
        
        self.assertLessEqual(small_quality_idx, large_quality_idx)
    
    def test_quality_recommendations(self):
        """Test quality recommendations"""
        poor_audio = b"x" * 100
        result = self.analyzer.analyze_audio_quality(poor_audio)
        
        self.assertIn("recommendations", result)
        self.assertIsInstance(result["recommendations"], list)
        
        if result["quality"] in ["poor", "fair"]:
            self.assertGreater(len(result["recommendations"]), 0)

class TestUtilityFunctions(unittest.TestCase):
    """Test cases for utility functions"""
    
    def test_preprocess_south_african_text(self):
        """Test South African text preprocessing"""
        test_text = "patient has tb and numonia"
        processed = preprocess_south_african_text(test_text, "respiratory")
        
        self.assertIsInstance(processed, str)
        self.assertIn("tuberculosis", processed.lower())
        self.assertIn("pneumonia", processed.lower())
    
    def test_analyze_voice_audio(self):
        """Test voice audio analysis utility"""
        from utils.voice_utils import analyze_voice_audio
        
        audio_data = b"mock_audio" * 1000
        result = analyze_voice_audio(audio_data)
        
        self.assertIn("quality", result)
        self.assertIn("metrics", result)
    
    def test_get_medical_suggestions(self):
        """Test medical suggestions utility"""
        from utils.voice_utils import get_medical_suggestions
        
        suggestions = get_medical_suggestions("pneum", "respiratory")
        
        self.assertIsInstance(suggestions, list)

if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestVoiceEngine,
        TestSTTService,
        TestVoiceCommandProcessor,
        TestSTTLearningEngine,
        TestTypistService,
        TestSouthAfricanAccentProcessor,
        TestMedicalTerminologyProcessor,
        TestAudioQualityAnalyzer,
        TestUtilityFunctions
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\nTest Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")