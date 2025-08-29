"""
Typist Service for Medical Reporting Module
Manages typist queue, assignments, and feedback collection for STT improvement
"""

import logging
import threading
import queue
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class TypistStatus(Enum):
    """Typist availability status"""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    ON_BREAK = "on_break"

class ReportStatus(Enum):
    """Report processing status"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    RETURNED = "returned"
    CANCELLED = "cancelled"

class Priority(Enum):
    """Report priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    STAT = 5

@dataclass
class Typist:
    """Typist information"""
    typist_id: str
    name: str
    email: str
    status: TypistStatus
    specialties: List[str]
    current_workload: int
    max_workload: int
    average_completion_time: float  # minutes
    quality_score: float  # 0.0 to 1.0
    last_active: datetime
    shift_start: Optional[str] = None  # HH:MM format
    shift_end: Optional[str] = None    # HH:MM format
    
    def __post_init__(self):
        if self.specialties is None:
            self.specialties = []

@dataclass
class TypistAssignment:
    """Typist assignment for a report"""
    assignment_id: str
    report_id: str
    typist_id: str
    doctor_id: str
    priority: Priority
    assigned_at: datetime
    due_at: datetime
    status: ReportStatus
    voice_recording_path: str
    stt_draft: str
    original_audio_duration: float  # seconds
    estimated_completion_time: float  # minutes
    actual_completion_time: Optional[float] = None
    corrections_made: int = 0
    feedback_provided: bool = False
    notes: str = ""

@dataclass
class TypistFeedback:
    """Feedback from typist for STT improvement"""
    feedback_id: str
    assignment_id: str
    typist_id: str
    original_stt: str
    corrected_text: str
    error_categories: List[str]
    audio_quality_rating: int  # 1-5 scale
    difficulty_rating: int     # 1-5 scale
    suggestions: str
    timestamp: datetime
    
    def __post_init__(self):
        if self.error_categories is None:
            self.error_categories = []

class TypistQueue:
    """Queue management for typist assignments"""
    
    def __init__(self):
        self.pending_queue = queue.PriorityQueue()
        self.assignments: Dict[str, TypistAssignment] = {}
        self.queue_lock = threading.Lock()
        
        logger.info("Typist queue initialized")
    
    def add_assignment(self, assignment: TypistAssignment) -> bool:
        """Add assignment to queue"""
        try:
            with self.queue_lock:
                # Priority queue uses tuple (priority, timestamp, assignment)
                priority_value = assignment.priority.value
                timestamp = assignment.assigned_at.timestamp()
                
                self.pending_queue.put((priority_value, timestamp, assignment))
                self.assignments[assignment.assignment_id] = assignment
                
                logger.info(f"Added assignment {assignment.assignment_id} to queue with priority {assignment.priority.name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add assignment to queue: {e}")
            return False
    
    def get_next_assignment(self, typist_specialties: List[str] = None) -> Optional[TypistAssignment]:
        """Get next assignment from queue"""
        try:
            with self.queue_lock:
                if self.pending_queue.empty():
                    return None
                
                # Get highest priority assignment
                priority_value, timestamp, assignment = self.pending_queue.get()
                
                # Check if typist has required specialty (if specified)
                if typist_specialties:
                    # For now, assume all typists can handle all reports
                    # In production, would match specialties
                    pass
                
                assignment.status = ReportStatus.ASSIGNED
                return assignment
                
        except Exception as e:
            logger.error(f"Failed to get next assignment: {e}")
            return None
    
    def update_assignment_status(self, assignment_id: str, status: ReportStatus) -> bool:
        """Update assignment status"""
        try:
            if assignment_id in self.assignments:
                self.assignments[assignment_id].status = status
                logger.info(f"Updated assignment {assignment_id} status to {status.name}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to update assignment status: {e}")
            return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            with self.queue_lock:
                status_counts = {}
                for assignment in self.assignments.values():
                    status = assignment.status.name
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                return {
                    "pending_count": self.pending_queue.qsize(),
                    "total_assignments": len(self.assignments),
                    "status_breakdown": status_counts
                }
                
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}

class TypistService:
    """Service for managing typist workflow and feedback collection"""
    
    def __init__(self):
        self.typists: Dict[str, Typist] = {}
        self.queue = TypistQueue()
        self.feedback_history: List[TypistFeedback] = []
        
        # Callbacks
        self.assignment_callbacks: List[Callable] = []
        self.completion_callbacks: List[Callable] = []
        self.feedback_callbacks: List[Callable] = []
        
        # Initialize demo typists
        self._initialize_demo_typists()
        
        logger.info("Typist service initialized")
    
    def _initialize_demo_typists(self):
        """Initialize demo typists for testing"""
        demo_typists = [
            Typist(
                typist_id="typist_001",
                name="Sarah Johnson",
                email="sarah.johnson@hospital.com",
                status=TypistStatus.AVAILABLE,
                specialties=["radiology", "general"],
                current_workload=0,
                max_workload=5,
                average_completion_time=15.0,
                quality_score=0.95,
                last_active=datetime.utcnow(),
                shift_start="08:00",
                shift_end="17:00"
            ),
            Typist(
                typist_id="typist_002",
                name="Michael Chen",
                email="michael.chen@hospital.com",
                status=TypistStatus.AVAILABLE,
                specialties=["cardiology", "radiology"],
                current_workload=2,
                max_workload=4,
                average_completion_time=12.0,
                quality_score=0.92,
                last_active=datetime.utcnow(),
                shift_start="12:00",
                shift_end="21:00"
            ),
            Typist(
                typist_id="typist_003",
                name="Linda Williams",
                email="linda.williams@hospital.com",
                status=TypistStatus.BUSY,
                specialties=["orthopedics", "general"],
                current_workload=3,
                max_workload=3,
                average_completion_time=18.0,
                quality_score=0.88,
                last_active=datetime.utcnow(),
                shift_start="06:00",
                shift_end="15:00"
            )
        ]
        
        for typist in demo_typists:
            self.typists[typist.typist_id] = typist
        
        logger.info(f"Initialized {len(demo_typists)} demo typists")
    
    def create_assignment(self, report_id: str, doctor_id: str, 
                         voice_recording_path: str, stt_draft: str,
                         priority: Priority = Priority.NORMAL,
                         audio_duration: float = 0.0) -> Optional[str]:
        """Create a new typist assignment"""
        try:
            assignment_id = str(uuid.uuid4())
            
            # Calculate estimated completion time based on audio duration and complexity
            estimated_time = self._estimate_completion_time(stt_draft, audio_duration)
            
            # Calculate due time based on priority
            due_at = self._calculate_due_time(priority, estimated_time)
            
            assignment = TypistAssignment(
                assignment_id=assignment_id,
                report_id=report_id,
                typist_id="",  # Will be assigned when picked up
                doctor_id=doctor_id,
                priority=priority,
                assigned_at=datetime.utcnow(),
                due_at=due_at,
                status=ReportStatus.PENDING,
                voice_recording_path=voice_recording_path,
                stt_draft=stt_draft,
                original_audio_duration=audio_duration,
                estimated_completion_time=estimated_time
            )
            
            # Add to queue
            if self.queue.add_assignment(assignment):
                # Notify callbacks
                self._notify_assignment_callbacks('created', assignment)
                
                logger.info(f"Created typist assignment: {assignment_id}")
                return assignment_id
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create typist assignment: {e}")
            return None
    
    def _estimate_completion_time(self, stt_draft: str, audio_duration: float) -> float:
        """Estimate completion time based on content complexity"""
        try:
            # Base time from audio duration (assume 1:3 ratio for typing)
            base_time = audio_duration / 60.0 * 3.0  # Convert to minutes
            
            # Adjust based on text complexity
            word_count = len(stt_draft.split())
            complexity_factor = 1.0
            
            # Check for complex medical terms
            complex_terms = [
                "pneumoconiosis", "tuberculosis", "consolidation",
                "atelectasis", "pneumothorax", "cardiomegaly"
            ]
            
            for term in complex_terms:
                if term.lower() in stt_draft.lower():
                    complexity_factor += 0.1
            
            # Minimum 5 minutes, maximum 60 minutes
            estimated_time = max(5.0, min(60.0, base_time * complexity_factor))
            
            return estimated_time
            
        except Exception as e:
            logger.error(f"Failed to estimate completion time: {e}")
            return 15.0  # Default 15 minutes
    
    def _calculate_due_time(self, priority: Priority, estimated_time: float) -> datetime:
        """Calculate due time based on priority"""
        try:
            now = datetime.utcnow()
            
            # Priority-based multipliers
            priority_multipliers = {
                Priority.STAT: 0.5,      # 50% of estimated time
                Priority.URGENT: 1.0,    # Estimated time
                Priority.HIGH: 2.0,      # 2x estimated time
                Priority.NORMAL: 4.0,    # 4x estimated time
                Priority.LOW: 8.0        # 8x estimated time
            }
            
            multiplier = priority_multipliers.get(priority, 4.0)
            due_minutes = estimated_time * multiplier
            
            return now + timedelta(minutes=due_minutes)
            
        except Exception as e:
            logger.error(f"Failed to calculate due time: {e}")
            return datetime.utcnow() + timedelta(hours=4)  # Default 4 hours
    
    def assign_to_typist(self, typist_id: str) -> Optional[TypistAssignment]:
        """Assign next available work to a typist"""
        try:
            if typist_id not in self.typists:
                logger.error(f"Typist not found: {typist_id}")
                return None
            
            typist = self.typists[typist_id]
            
            # Check if typist is available and has capacity
            if (typist.status != TypistStatus.AVAILABLE or 
                typist.current_workload >= typist.max_workload):
                logger.info(f"Typist {typist_id} not available for assignment")
                return None
            
            # Get next assignment from queue
            assignment = self.queue.get_next_assignment(typist.specialties)
            
            if assignment:
                assignment.typist_id = typist_id
                assignment.status = ReportStatus.ASSIGNED
                
                # Update typist workload
                typist.current_workload += 1
                typist.last_active = datetime.utcnow()
                
                # Update typist status if at capacity
                if typist.current_workload >= typist.max_workload:
                    typist.status = TypistStatus.BUSY
                
                # Notify callbacks
                self._notify_assignment_callbacks('assigned', assignment)
                
                logger.info(f"Assigned {assignment.assignment_id} to typist {typist_id}")
                return assignment
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to assign to typist: {e}")
            return None
    
    def start_work(self, assignment_id: str) -> bool:
        """Mark assignment as in progress"""
        try:
            assignment = self.queue.assignments.get(assignment_id)
            if not assignment:
                return False
            
            assignment.status = ReportStatus.IN_PROGRESS
            
            # Notify callbacks
            self._notify_assignment_callbacks('started', assignment)
            
            logger.info(f"Started work on assignment: {assignment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start work: {e}")
            return False
    
    def complete_assignment(self, assignment_id: str, corrected_text: str,
                          completion_time: float, corrections_made: int = 0) -> bool:
        """Complete a typist assignment"""
        try:
            assignment = self.queue.assignments.get(assignment_id)
            if not assignment:
                return False
            
            assignment.status = ReportStatus.COMPLETED
            assignment.actual_completion_time = completion_time
            assignment.corrections_made = corrections_made
            
            # Update typist workload and status
            if assignment.typist_id in self.typists:
                typist = self.typists[assignment.typist_id]
                typist.current_workload = max(0, typist.current_workload - 1)
                typist.last_active = datetime.utcnow()
                
                # Update average completion time
                typist.average_completion_time = (
                    (typist.average_completion_time + completion_time) / 2.0
                )
                
                # Update status if no longer at capacity
                if (typist.current_workload < typist.max_workload and 
                    typist.status == TypistStatus.BUSY):
                    typist.status = TypistStatus.AVAILABLE
            
            # Notify callbacks
            self._notify_completion_callbacks(assignment, corrected_text)
            
            logger.info(f"Completed assignment: {assignment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete assignment: {e}")
            return False
    
    def submit_feedback(self, assignment_id: str, typist_id: str,
                       corrected_text: str, error_categories: List[str],
                       audio_quality_rating: int, difficulty_rating: int,
                       suggestions: str = "") -> Optional[str]:
        """Submit feedback for STT improvement"""
        try:
            assignment = self.queue.assignments.get(assignment_id)
            if not assignment:
                return None
            
            feedback_id = str(uuid.uuid4())
            
            feedback = TypistFeedback(
                feedback_id=feedback_id,
                assignment_id=assignment_id,
                typist_id=typist_id,
                original_stt=assignment.stt_draft,
                corrected_text=corrected_text,
                error_categories=error_categories,
                audio_quality_rating=audio_quality_rating,
                difficulty_rating=difficulty_rating,
                suggestions=suggestions,
                timestamp=datetime.utcnow()
            )
            
            self.feedback_history.append(feedback)
            assignment.feedback_provided = True
            
            # Notify feedback callbacks
            self._notify_feedback_callbacks(feedback)
            
            logger.info(f"Submitted feedback: {feedback_id}")
            return feedback_id
            
        except Exception as e:
            logger.error(f"Failed to submit feedback: {e}")
            return None
    
    def get_typist_workload(self, typist_id: str) -> Dict[str, Any]:
        """Get typist workload information"""
        try:
            if typist_id not in self.typists:
                return {}
            
            typist = self.typists[typist_id]
            
            # Get assignments for this typist
            typist_assignments = [
                assignment for assignment in self.queue.assignments.values()
                if assignment.typist_id == typist_id and 
                assignment.status in [ReportStatus.ASSIGNED, ReportStatus.IN_PROGRESS]
            ]
            
            return {
                "typist_id": typist_id,
                "name": typist.name,
                "status": typist.status.name,
                "current_workload": typist.current_workload,
                "max_workload": typist.max_workload,
                "utilization": typist.current_workload / typist.max_workload,
                "average_completion_time": typist.average_completion_time,
                "quality_score": typist.quality_score,
                "active_assignments": len(typist_assignments),
                "last_active": typist.last_active.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get typist workload: {e}")
            return {}
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get overall queue status"""
        try:
            queue_stats = self.queue.get_queue_stats()
            
            # Add typist statistics
            available_typists = sum(
                1 for t in self.typists.values() 
                if t.status == TypistStatus.AVAILABLE
            )
            
            busy_typists = sum(
                1 for t in self.typists.values() 
                if t.status == TypistStatus.BUSY
            )
            
            total_capacity = sum(t.max_workload for t in self.typists.values())
            current_load = sum(t.current_workload for t in self.typists.values())
            
            queue_stats.update({
                "total_typists": len(self.typists),
                "available_typists": available_typists,
                "busy_typists": busy_typists,
                "total_capacity": total_capacity,
                "current_load": current_load,
                "capacity_utilization": current_load / total_capacity if total_capacity > 0 else 0,
                "feedback_count": len(self.feedback_history)
            })
            
            return queue_stats
            
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return {}
    
    def get_feedback_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get feedback summary for recent period"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            recent_feedback = [
                f for f in self.feedback_history 
                if f.timestamp >= cutoff_date
            ]
            
            if not recent_feedback:
                return {"period_days": days, "feedback_count": 0}
            
            # Analyze error categories
            error_counts = {}
            for feedback in recent_feedback:
                for category in feedback.error_categories:
                    error_counts[category] = error_counts.get(category, 0) + 1
            
            # Calculate averages
            avg_audio_quality = sum(f.audio_quality_rating for f in recent_feedback) / len(recent_feedback)
            avg_difficulty = sum(f.difficulty_rating for f in recent_feedback) / len(recent_feedback)
            
            return {
                "period_days": days,
                "feedback_count": len(recent_feedback),
                "error_categories": error_counts,
                "average_audio_quality": round(avg_audio_quality, 2),
                "average_difficulty": round(avg_difficulty, 2),
                "most_common_errors": sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            }
            
        except Exception as e:
            logger.error(f"Failed to get feedback summary: {e}")
            return {}
    
    def add_assignment_callback(self, callback: Callable):
        """Add callback for assignment events"""
        self.assignment_callbacks.append(callback)
    
    def add_completion_callback(self, callback: Callable):
        """Add callback for completion events"""
        self.completion_callbacks.append(callback)
    
    def add_feedback_callback(self, callback: Callable):
        """Add callback for feedback events"""
        self.feedback_callbacks.append(callback)
    
    def _notify_assignment_callbacks(self, event: str, assignment: TypistAssignment):
        """Notify assignment callbacks"""
        for callback in self.assignment_callbacks:
            try:
                callback(event, assignment)
            except Exception as e:
                logger.error(f"Error in assignment callback: {e}")
    
    def _notify_completion_callbacks(self, assignment: TypistAssignment, corrected_text: str):
        """Notify completion callbacks"""
        for callback in self.completion_callbacks:
            try:
                callback(assignment, corrected_text)
            except Exception as e:
                logger.error(f"Error in completion callback: {e}")
    
    def _notify_feedback_callbacks(self, feedback: TypistFeedback):
        """Notify feedback callbacks"""
        for callback in self.feedback_callbacks:
            try:
                callback(feedback)
            except Exception as e:
                logger.error(f"Error in feedback callback: {e}")

# Global typist service instance
typist_service = TypistService()