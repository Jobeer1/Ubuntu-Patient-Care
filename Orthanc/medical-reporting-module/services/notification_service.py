"""
Notification Service for Medical Reporting Module
Handles notifications for report status updates and typist assignments
"""

import logging
import smtplib
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Types of notifications"""
    ASSIGNMENT_CREATED = "assignment_created"
    ASSIGNMENT_ASSIGNED = "assignment_assigned"
    ASSIGNMENT_STARTED = "assignment_started"
    ASSIGNMENT_COMPLETED = "assignment_completed"
    ASSIGNMENT_OVERDUE = "assignment_overdue"
    REPORT_READY = "report_ready"
    SYSTEM_ALERT = "system_alert"

@dataclass
class NotificationTemplate:
    """Notification template"""
    template_id: str
    notification_type: NotificationType
    subject_template: str
    body_template: str
    recipients: List[str]
    priority: int = 1  # 1=low, 5=high

class NotificationService:
    """Service for sending notifications"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.templates = {}
        self.notification_history = []
        
        # Email configuration
        self.smtp_server = self.config.get('smtp_server', 'localhost')
        self.smtp_port = self.config.get('smtp_port', 587)
        self.smtp_username = self.config.get('smtp_username', '')
        self.smtp_password = self.config.get('smtp_password', '')
        self.from_email = self.config.get('from_email', 'noreply@hospital.com')
        
        # Initialize default templates
        self._initialize_templates()
        
        logger.info("Notification service initialized")
    
    def _initialize_templates(self):
        """Initialize default notification templates"""
        templates = [
            NotificationTemplate(
                template_id="assignment_created",
                notification_type=NotificationType.ASSIGNMENT_CREATED,
                subject_template="New Report Assignment Available - Priority: {priority}",
                body_template="""
A new report assignment is available for processing:

Assignment ID: {assignment_id}
Report ID: {report_id}
Doctor: {doctor_name}
Priority: {priority}
Estimated Time: {estimated_time} minutes
Due: {due_time}

Audio Duration: {audio_duration} seconds
Draft Preview: {stt_preview}...

Please log in to the system to accept this assignment.
                """.strip(),
                recipients=["typists@hospital.com"],
                priority=2
            ),
            NotificationTemplate(
                template_id="assignment_completed",
                notification_type=NotificationType.ASSIGNMENT_COMPLETED,
                subject_template="Report Completed - {report_id}",
                body_template="""
Report assignment has been completed:

Assignment ID: {assignment_id}
Report ID: {report_id}
Typist: {typist_name}
Completion Time: {completion_time} minutes
Corrections Made: {corrections_made}

The report is now ready for doctor review.
                """.strip(),
                recipients=["doctors@hospital.com"],
                priority=3
            ),
            NotificationTemplate(
                template_id="assignment_overdue",
                notification_type=NotificationType.ASSIGNMENT_OVERDUE,
                subject_template="OVERDUE: Report Assignment - {assignment_id}",
                body_template="""
URGENT: The following report assignment is overdue:

Assignment ID: {assignment_id}
Report ID: {report_id}
Assigned to: {typist_name}
Due Time: {due_time}
Overdue by: {overdue_minutes} minutes

Please prioritize this assignment immediately.
                """.strip(),
                recipients=["supervisors@hospital.com", "typists@hospital.com"],
                priority=5
            ),
            NotificationTemplate(
                template_id="report_ready",
                notification_type=NotificationType.REPORT_READY,
                subject_template="Report Ready for Review - {report_id}",
                body_template="""
Your dictated report is ready for review:

Report ID: {report_id}
Patient: {patient_name}
Study Date: {study_date}
Processed by: {typist_name}
Processing Time: {processing_time} minutes

Please log in to review and finalize the report.
                """.strip(),
                recipients=[],  # Will be populated with doctor email
                priority=3
            )
        ]
        
        for template in templates:
            self.templates[template.template_id] = template
        
        logger.info(f"Initialized {len(templates)} notification templates")
    
    def send_notification(self, notification_type: NotificationType, 
                         data: Dict[str, Any], 
                         recipients: List[str] = None) -> bool:
        """Send notification based on type and data"""
        try:
            template_id = notification_type.value
            template = self.templates.get(template_id)
            
            if not template:
                logger.error(f"No template found for notification type: {notification_type}")
                return False
            
            # Use provided recipients or template defaults
            target_recipients = recipients or template.recipients
            
            if not target_recipients:
                logger.warning(f"No recipients specified for notification: {notification_type}")
                return False
            
            # Format subject and body
            subject = template.subject_template.format(**data)
            body = template.body_template.format(**data)
            
            # Send email notification
            success = self._send_email(target_recipients, subject, body)
            
            # Log notification
            self._log_notification(notification_type, data, target_recipients, success)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    def _send_email(self, recipients: List[str], subject: str, body: str) -> bool:
        """Send email notification"""
        try:
            # In development mode, just log the email
            if self.config.get('development_mode', True):
                logger.info(f"EMAIL NOTIFICATION (DEV MODE):")
                logger.info(f"To: {', '.join(recipients)}")
                logger.info(f"Subject: {subject}")
                logger.info(f"Body: {body}")
                return True
            
            # Create message
            msg = MimeMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            msg.attach(MimeText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_username and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _log_notification(self, notification_type: NotificationType, 
                         data: Dict[str, Any], recipients: List[str], 
                         success: bool):
        """Log notification attempt"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "notification_type": notification_type.value,
            "recipients": recipients,
            "data": data,
            "success": success
        }
        
        self.notification_history.append(log_entry)
        
        # Keep only last 1000 notifications
        if len(self.notification_history) > 1000:
            self.notification_history = self.notification_history[-1000:]
    
    def notify_assignment_created(self, assignment_data: Dict[str, Any]) -> bool:
        """Send notification for new assignment"""
        return self.send_notification(
            NotificationType.ASSIGNMENT_CREATED,
            assignment_data
        )
    
    def notify_assignment_completed(self, assignment_data: Dict[str, Any], 
                                  doctor_email: str = None) -> bool:
        """Send notification for completed assignment"""
        recipients = [doctor_email] if doctor_email else None
        return self.send_notification(
            NotificationType.ASSIGNMENT_COMPLETED,
            assignment_data,
            recipients
        )
    
    def notify_assignment_overdue(self, assignment_data: Dict[str, Any]) -> bool:
        """Send notification for overdue assignment"""
        return self.send_notification(
            NotificationType.ASSIGNMENT_OVERDUE,
            assignment_data
        )
    
    def notify_report_ready(self, report_data: Dict[str, Any], 
                           doctor_email: str) -> bool:
        """Send notification that report is ready for review"""
        return self.send_notification(
            NotificationType.REPORT_READY,
            report_data,
            [doctor_email]
        )
    
    def get_notification_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent notification history"""
        return self.notification_history[-limit:]
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        try:
            if not self.notification_history:
                return {"total_notifications": 0}
            
            # Count by type
            type_counts = {}
            success_count = 0
            
            for entry in self.notification_history:
                notification_type = entry["notification_type"]
                type_counts[notification_type] = type_counts.get(notification_type, 0) + 1
                
                if entry["success"]:
                    success_count += 1
            
            return {
                "total_notifications": len(self.notification_history),
                "successful_notifications": success_count,
                "success_rate": success_count / len(self.notification_history),
                "notifications_by_type": type_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to get notification stats: {e}")
            return {}

# Global notification service instance
notification_service = NotificationService({
    'development_mode': True,  # Set to False in production
    'smtp_server': 'localhost',
    'smtp_port': 587,
    'from_email': 'medical-reports@hospital.com'
})