"""
Tests for Typist Service
"""

import pytest
import uuid
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.typist_service import (
    TypistService, Typist, TypistAssignment, TypistFeedback,
    TypistStatus, ReportStatus, Priority
)

class TestTypistService:
    """Test cases for TypistService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = TypistService()
    
    def test_initialization(self):
        """Test service initialization"""
        assert len(self.service.typists) == 3  # Demo typists
        assert self.service.queue is not None
        assert isinstance(self.service.feedback_history, list)
    
    def test_create_assignment(self):
        """Test creating a new assignment"""
        assignment_id = self.service.create_assignment(
            report_id="report_001",
            doctor_id="doctor_001",
            voice_recording_path="/path/to/audio.wav",
            stt_draft="Patient presents with chest pain and shortness of breath.",
            priority=Priority.HIGH,
            audio_duration=120.0
        )
        
        assert assignment_id is not None
        assert assignment_id in self.service.queue.assignments
        
        assignment = self.service.queue.assignments[assignment_id]
        assert assignment.report_id == "report_001"
        assert assignment.priority == Priority.HIGH
        assert assignment.status == ReportStatus.PENDING
    
    def test_assign_to_typist(self):
        """Test assigning work to a typist"""
        # Create an assignment first
        assignment_id = self.service.create_assignment(
            report_id="report_002",
            doctor_id="doctor_002",
            voice_recording_path="/path/to/audio2.wav",
            stt_draft="Normal chest X-ray findings.",
            priority=Priority.NORMAL,
            audio_duration=60.0
        )
        
        # Assign to available typist
        typist_id = "typist_001"
        assignment = self.service.assign_to_typist(typist_id)
        
        assert assignment is not None
        assert assignment.typist_id == typist_id
        assert assignment.status == ReportStatus.ASSIGNED
        
        # Check typist workload updated
        typist = self.service.typists[typist_id]
        assert typist.current_workload == 1
    
    def test_complete_assignment(self):
        """Test completing an assignment"""
        # Create and assign
        assignment_id = self.service.create_assignment(
            report_id="report_003",
            doctor_id="doctor_003",
            voice_recording_path="/path/to/audio3.wav",
            stt_draft="Pneumonia in right lower lobe.",
            priority=Priority.URGENT,
            audio_duration=180.0
        )
        
        typist_id = "typist_002"
        assignment = self.service.assign_to_typist(typist_id)
        
        # Start work
        self.service.start_work(assignment.assignment_id)
        
        # Complete assignment
        success = self.service.complete_assignment(
            assignment.assignment_id,
            corrected_text="Pneumonia in the right lower lobe with consolidation.",
            completion_time=15.0,
            corrections_made=2
        )
        
        assert success
        assert assignment.status == ReportStatus.COMPLETED
        assert assignment.actual_completion_time == 15.0
        assert assignment.corrections_made == 2
        
        # Check typist workload decreased
        typist = self.service.typists[typist_id]
        assert typist.current_workload == 0
    
    def test_submit_feedback(self):
        """Test submitting feedback"""
        # Create and complete an assignment
        assignment_id = self.service.create_assignment(
            report_id="report_004",
            doctor_id="doctor_004",
            voice_recording_path="/path/to/audio4.wav",
            stt_draft="Cardiomegaly noted on chest X-ray.",
            priority=Priority.NORMAL,
            audio_duration=90.0
        )
        
        typist_id = "typist_003"
        assignment = self.service.assign_to_typist(typist_id)
        self.service.start_work(assignment.assignment_id)
        self.service.complete_assignment(
            assignment.assignment_id,
            "Cardiomegaly noted on chest X-ray examination.",
            12.0,
            1
        )
        
        # Submit feedback
        feedback_id = self.service.submit_feedback(
            assignment_id=assignment.assignment_id,
            typist_id=typist_id,
            corrected_text="Cardiomegaly noted on chest X-ray examination.",
            error_categories=["grammar", "medical_terminology"],
            audio_quality_rating=4,
            difficulty_rating=3,
            suggestions="Audio quality was good but some medical terms were unclear."
        )
        
        assert feedback_id is not None
        assert len(self.service.feedback_history) == 1
        
        feedback = self.service.feedback_history[0]
        assert feedback.assignment_id == assignment.assignment_id
        assert feedback.typist_id == typist_id
        assert len(feedback.error_categories) == 2
        assert feedback.audio_quality_rating == 4
    
    def test_typist_workload_management(self):
        """Test typist workload management"""
        typist_id = "typist_001"
        initial_workload = self.service.typists[typist_id].current_workload
        
        # Create multiple assignments
        for i in range(3):
            assignment_id = self.service.create_assignment(
                report_id=f"report_00{i+5}",
                doctor_id=f"doctor_00{i+5}",
                voice_recording_path=f"/path/to/audio{i+5}.wav",
                stt_draft=f"Test report {i+5}",
                priority=Priority.NORMAL,
                audio_duration=60.0
            )
        
        # Assign all to same typist
        assignments = []
        for _ in range(3):
            assignment = self.service.assign_to_typist(typist_id)
            if assignment:
                assignments.append(assignment)
        
        # Check workload
        typist = self.service.typists[typist_id]
        assert typist.current_workload == initial_workload + len(assignments)
        
        # Get workload info
        workload_info = self.service.get_typist_workload(typist_id)
        assert workload_info["current_workload"] == typist.current_workload
        assert workload_info["utilization"] == typist.current_workload / typist.max_workload
    
    def test_queue_statistics(self):
        """Test queue statistics"""
        # Create some assignments
        for i in range(5):
            self.service.create_assignment(
                report_id=f"report_stat_{i}",
                doctor_id=f"doctor_stat_{i}",
                voice_recording_path=f"/path/to/stat_{i}.wav",
                stt_draft=f"Statistics test report {i}",
                priority=Priority.NORMAL,
                audio_duration=60.0
            )
        
        # Assign some
        self.service.assign_to_typist("typist_001")
        self.service.assign_to_typist("typist_002")
        
        # Get queue status
        status = self.service.get_queue_status()
        
        assert "total_assignments" in status
        assert "pending_count" in status
        assert "total_typists" in status
        assert "available_typists" in status
        assert "capacity_utilization" in status
        assert status["total_typists"] == 3
    
    def test_feedback_summary(self):
        """Test feedback summary generation"""
        # Create assignment and feedback
        assignment_id = self.service.create_assignment(
            report_id="report_feedback",
            doctor_id="doctor_feedback",
            voice_recording_path="/path/to/feedback.wav",
            stt_draft="Feedback test report",
            priority=Priority.NORMAL,
            audio_duration=60.0
        )
        
        typist_id = "typist_001"
        assignment = self.service.assign_to_typist(typist_id)
        self.service.complete_assignment(assignment.assignment_id, "Corrected text", 10.0, 1)
        
        # Submit multiple feedback entries
        for i in range(3):
            self.service.submit_feedback(
                assignment_id=assignment.assignment_id,
                typist_id=typist_id,
                corrected_text=f"Corrected text {i}",
                error_categories=["grammar", "punctuation"],
                audio_quality_rating=4,
                difficulty_rating=2,
                suggestions=f"Suggestion {i}"
            )
        
        # Get feedback summary
        summary = self.service.get_feedback_summary(days=7)
        
        assert summary["feedback_count"] == 3
        assert "error_categories" in summary
        assert "average_audio_quality" in summary
        assert "average_difficulty" in summary
        assert summary["average_audio_quality"] == 4.0
        assert summary["average_difficulty"] == 2.0
    
    def test_priority_queue_ordering(self):
        """Test that assignments are processed by priority"""
        # Create assignments with different priorities
        priorities = [Priority.LOW, Priority.URGENT, Priority.NORMAL, Priority.HIGH, Priority.STAT]
        assignment_ids = []
        
        for i, priority in enumerate(priorities):
            assignment_id = self.service.create_assignment(
                report_id=f"priority_test_{i}",
                doctor_id=f"doctor_priority_{i}",
                voice_recording_path=f"/path/to/priority_{i}.wav",
                stt_draft=f"Priority test {priority.name}",
                priority=priority,
                audio_duration=60.0
            )
            assignment_ids.append(assignment_id)
        
        # Assign to typists and check order (STAT should come first)
        assigned_priorities = []
        for _ in range(len(priorities)):
            assignment = self.service.assign_to_typist("typist_001")
            if assignment:
                assigned_priorities.append(assignment.priority)
            
            # Reset typist workload for next assignment
            self.service.typists["typist_001"].current_workload = 0
            self.service.typists["typist_001"].status = TypistStatus.AVAILABLE
        
        # STAT (5) should be first, then URGENT (4), HIGH (3), NORMAL (2), LOW (1)
        expected_order = [Priority.STAT, Priority.URGENT, Priority.HIGH, Priority.NORMAL, Priority.LOW]
        assert assigned_priorities == expected_order
    
    def test_callback_system(self):
        """Test callback system for events"""
        assignment_events = []
        completion_events = []
        feedback_events = []
        
        def assignment_callback(event, assignment):
            assignment_events.append((event, assignment.assignment_id))
        
        def completion_callback(assignment, corrected_text):
            completion_events.append((assignment.assignment_id, corrected_text))
        
        def feedback_callback(feedback):
            feedback_events.append(feedback.feedback_id)
        
        # Register callbacks
        self.service.add_assignment_callback(assignment_callback)
        self.service.add_completion_callback(completion_callback)
        self.service.add_feedback_callback(feedback_callback)
        
        # Create and process assignment
        assignment_id = self.service.create_assignment(
            report_id="callback_test",
            doctor_id="doctor_callback",
            voice_recording_path="/path/to/callback.wav",
            stt_draft="Callback test report",
            priority=Priority.NORMAL,
            audio_duration=60.0
        )
        
        assignment = self.service.assign_to_typist("typist_001")
        self.service.start_work(assignment.assignment_id)
        self.service.complete_assignment(assignment.assignment_id, "Corrected callback text", 10.0, 1)
        
        feedback_id = self.service.submit_feedback(
            assignment_id=assignment.assignment_id,
            typist_id="typist_001",
            corrected_text="Corrected callback text",
            error_categories=["test"],
            audio_quality_rating=5,
            difficulty_rating=1
        )
        
        # Check callbacks were triggered
        assert len(assignment_events) >= 2  # created, assigned, started
        assert len(completion_events) == 1
        assert len(feedback_events) == 1
        
        assert completion_events[0][0] == assignment.assignment_id
        assert completion_events[0][1] == "Corrected callback text"
        assert feedback_events[0] == feedback_id

if __name__ == "__main__":
    pytest.main([__file__])