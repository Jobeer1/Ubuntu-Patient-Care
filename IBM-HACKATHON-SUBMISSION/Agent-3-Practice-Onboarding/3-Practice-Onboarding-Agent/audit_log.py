"""
Audit Log System for Agent 3 Credential Vault

Complete tracking and logging of all credential access, rotation, and security events
"""

import json
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of audit events"""
    CREDENTIAL_CREATED = "credential_created"
    CREDENTIAL_RETRIEVED = "credential_retrieved"
    CREDENTIAL_ROTATED = "credential_rotated"
    CREDENTIAL_EXPIRED = "credential_expired"
    CREDENTIAL_REVOKED = "credential_revoked"
    ACCESS_DENIED = "access_denied"
    FAILED_ATTEMPT = "failed_attempt"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    VAULT_OPENED = "vault_opened"
    VAULT_LOCKED = "vault_locked"
    AUDIT_LOG_EXPORTED = "audit_log_exported"
    SYSTEM_EVENT = "system_event"
    POLICY_VIOLATION = "policy_violation"
    BREACH_DETECTED = "breach_detected"


class SeverityLevel(Enum):
    """Severity of audit event"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Single audit log entry"""
    event_id: str
    event_type: EventType
    severity: SeverityLevel
    timestamp: datetime
    actor: str  # User/service who performed action
    target_resource: str  # What was accessed (credential ID, etc)
    action: str  # What happened
    details: Dict[str, Any]  # Additional details
    result: bool  # Success/failure
    client_ip: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "target_resource": self.target_resource,
            "action": self.action,
            "details": self.details,
            "result": self.result,
            "client_ip": self.client_ip,
            "session_id": self.session_id
        }
    
    def calculate_signature(self, signing_key: bytes) -> str:
        """
        Calculate HMAC-SHA256 signature for audit event
        
        Ensures tampering is detectable
        """
        event_str = json.dumps(self.to_dict(), sort_keys=True)
        signature = hmac.new(signing_key, event_str.encode(), hashlib.sha256).hexdigest()
        return signature


class RotationSchedule:
    """Credential rotation schedule and tracking"""
    
    def __init__(self, credential_id: str, interval_days: int = 90,
                 last_rotation: Optional[datetime] = None):
        """Initialize rotation schedule"""
        self.credential_id = credential_id
        self.interval_days = interval_days
        self.last_rotation = last_rotation or datetime.now()
        self.next_rotation = self.last_rotation + timedelta(days=interval_days)
        self.rotation_history: List[Dict[str, Any]] = []
    
    def is_due_for_rotation(self) -> bool:
        """Check if credential is due for rotation"""
        return datetime.now() >= self.next_rotation
    
    def days_until_rotation(self) -> int:
        """Get days until next rotation"""
        delta = self.next_rotation - datetime.now()
        return max(0, delta.days)
    
    def mark_rotated(self, rotated_by: str, reason: str = "scheduled"):
        """Mark credential as rotated"""
        now = datetime.now()
        self.rotation_history.append({
            "rotated_at": now.isoformat(),
            "rotated_by": rotated_by,
            "reason": reason,
            "previous_rotation": self.last_rotation.isoformat()
        })
        self.last_rotation = now
        self.next_rotation = now + timedelta(days=self.interval_days)
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get rotation history"""
        return self.rotation_history


class ExpirationTracker:
    """Track credential expiration dates and alerts"""
    
    def __init__(self, credential_id: str, expires_at: datetime):
        """Initialize expiration tracker"""
        self.credential_id = credential_id
        self.expires_at = expires_at
        self.expiration_alerts: List[Dict[str, Any]] = []
        self.extension_history: List[Dict[str, Any]] = []
    
    def is_expired(self) -> bool:
        """Check if credential is expired"""
        return datetime.now() > self.expires_at
    
    def days_until_expiration(self) -> int:
        """Get days until expiration"""
        delta = self.expires_at - datetime.now()
        return delta.days
    
    def generate_alerts(self) -> List[Dict[str, Any]]:
        """Generate alerts at various thresholds"""
        days_left = self.days_until_expiration()
        alerts = []
        
        # 30 days warning
        if 25 <= days_left <= 35:
            alerts.append({
                "severity": "warning",
                "days_left": days_left,
                "message": f"Credential expires in {days_left} days"
            })
        
        # 7 days critical
        if 0 <= days_left <= 7:
            alerts.append({
                "severity": "critical",
                "days_left": days_left,
                "message": f"Credential expires in {days_left} days - immediate action required"
            })
        
        # Already expired
        if days_left < 0:
            alerts.append({
                "severity": "critical",
                "days_left": 0,
                "message": "Credential has expired"
            })
        
        self.expiration_alerts.extend(alerts)
        return alerts
    
    def extend_expiration(self, new_expiration: datetime, extended_by: str):
        """Extend credential expiration"""
        old_expiration = self.expires_at
        self.expires_at = new_expiration
        self.extension_history.append({
            "extended_at": datetime.now().isoformat(),
            "extended_by": extended_by,
            "old_expiration": old_expiration.isoformat(),
            "new_expiration": new_expiration.isoformat()
        })


class AccessPatternAnalyzer:
    """Analyze credential access patterns for anomalies"""
    
    def __init__(self, credential_id: str, normal_access_window: tuple = (8, 18)):
        """
        Initialize analyzer
        
        Args:
            credential_id: Credential to track
            normal_access_window: (start_hour, end_hour) for normal access
        """
        self.credential_id = credential_id
        self.normal_access_window = normal_access_window
        self.access_history: List[Dict[str, Any]] = []
        self.anomalies: List[Dict[str, Any]] = []
    
    def record_access(self, accessed_by: str, success: bool, 
                     timestamp: datetime = None):
        """Record credential access"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.access_history.append({
            "accessed_by": accessed_by,
            "success": success,
            "timestamp": timestamp.isoformat(),
            "hour": timestamp.hour
        })
    
    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalous access patterns"""
        anomalies = []
        
        if not self.access_history:
            return anomalies
        
        # Check for after-hours access
        after_hours = [
            a for a in self.access_history
            if not (self.normal_access_window[0] <= a['hour'] < self.normal_access_window[1])
        ]
        
        if after_hours:
            anomalies.append({
                "type": "after_hours_access",
                "severity": "warning",
                "count": len(after_hours),
                "instances": after_hours
            })
        
        # Check for repeated failures
        recent_failures = [
            a for a in self.access_history[-20:]
            if not a['success']
        ]
        
        if len(recent_failures) >= 3:
            anomalies.append({
                "type": "repeated_failed_attempts",
                "severity": "critical",
                "count": len(recent_failures),
                "message": "Multiple failed access attempts detected"
            })
        
        # Check for unusual access frequency
        last_24h = [
            a for a in self.access_history
            if datetime.fromisoformat(a['timestamp']) > datetime.now() - timedelta(hours=24)
        ]
        
        if len(last_24h) > 50:  # More than 50 accesses in 24h
            anomalies.append({
                "type": "unusual_frequency",
                "severity": "warning",
                "count": len(last_24h),
                "message": "Unusually high access frequency"
            })
        
        # Check for access by unusual actors
        unique_actors = set(a['accessed_by'] for a in self.access_history)
        if len(unique_actors) > 10:
            anomalies.append({
                "type": "many_different_actors",
                "severity": "warning",
                "count": len(unique_actors),
                "actors": list(unique_actors)
            })
        
        self.anomalies.extend(anomalies)
        return anomalies


class BreachDetector:
    """
    Detect potential credential breaches
    
    Identifies suspicious patterns that indicate compromise
    """
    
    def __init__(self, credential_id: str):
        """Initialize detector"""
        self.credential_id = credential_id
        self.failed_attempts = 0
        self.failed_attempt_times: List[datetime] = []
        self.breach_indicators: List[Dict[str, Any]] = []
        self.breach_detected = False
    
    def record_failed_attempt(self, timestamp: datetime = None):
        """Record failed access attempt"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.failed_attempt_times.append(timestamp)
        self.failed_attempts += 1
    
    def analyze_for_breach(self) -> bool:
        """Analyze access patterns for breach indicators"""
        indicators = []
        
        # Indicator 1: Rapid failed attempts (brute force)
        recent_30s = [
            t for t in self.failed_attempt_times
            if datetime.now() - t < timedelta(seconds=30)
        ]
        if len(recent_30s) >= 5:
            indicators.append({
                "type": "brute_force_detected",
                "severity": "critical",
                "failed_attempts_30s": len(recent_30s),
                "message": "Rapid failed access attempts detected - possible brute force"
            })
        
        # Indicator 2: Total failed attempts
        if self.failed_attempts >= 10:
            indicators.append({
                "type": "excessive_failed_attempts",
                "severity": "high",
                "total_failed": self.failed_attempts,
                "message": f"{self.failed_attempts} failed attempts recorded"
            })
        
        # Indicator 3: Repeated failures over time
        if len(self.failed_attempt_times) >= 5:
            oldest_failure = self.failed_attempt_times[0]
            if datetime.now() - oldest_failure < timedelta(hours=1):
                indicators.append({
                    "type": "persistent_attack",
                    "severity": "critical",
                    "message": "Multiple failed attempts within 1 hour - possible attack"
                })
        
        self.breach_indicators.extend(indicators)
        
        # Determine if breach is likely
        if any(ind["severity"] == "critical" for ind in indicators):
            self.breach_detected = True
        
        return self.breach_detected
    
    def get_breach_status(self) -> Dict[str, Any]:
        """Get breach detection status"""
        return {
            "credential_id": self.credential_id,
            "breach_detected": self.breach_detected,
            "indicators": self.breach_indicators,
            "failed_attempts": self.failed_attempts,
            "recommendation": "Immediately rotate credential and investigate" if self.breach_detected else "No action needed"
        }


class AuditLogManager:
    """
    Central audit log management
    
    Maintains complete audit trail with integrity checking
    """
    
    def __init__(self, signing_key: bytes = None):
        """Initialize audit log manager"""
        self.signing_key = signing_key or b"audit_log_signing_key"
        self.events: List[AuditEvent] = []
        self.rotation_schedules: Dict[str, RotationSchedule] = {}
        self.expiration_trackers: Dict[str, ExpirationTracker] = {}
        self.access_analyzers: Dict[str, AccessPatternAnalyzer] = {}
        self.breach_detectors: Dict[str, BreachDetector] = {}
    
    def log_event(self, event_type: EventType, target_resource: str,
                 action: str, actor: str = "system",
                 severity: SeverityLevel = SeverityLevel.INFO,
                 details: Dict[str, Any] = None,
                 result: bool = True,
                 client_ip: Optional[str] = None) -> str:
        """Log an audit event"""
        import secrets
        
        event = AuditEvent(
            event_id=secrets.token_hex(16),
            event_type=event_type,
            severity=severity,
            timestamp=datetime.now(),
            actor=actor,
            target_resource=target_resource,
            action=action,
            details=details or {},
            result=result,
            client_ip=client_ip
        )
        
        self.events.append(event)
        logger.log(
            logging.WARNING if severity == SeverityLevel.WARNING else
            logging.CRITICAL if severity == SeverityLevel.CRITICAL else
            logging.INFO,
            f"[{event_type.value}] {action} - {target_resource} by {actor}"
        )
        
        return event.event_id
    
    def setup_rotation_schedule(self, credential_id: str, interval_days: int = 90):
        """Setup rotation schedule for credential"""
        schedule = RotationSchedule(credential_id, interval_days)
        self.rotation_schedules[credential_id] = schedule
    
    def setup_expiration_tracking(self, credential_id: str, expires_at: datetime):
        """Setup expiration tracking"""
        tracker = ExpirationTracker(credential_id, expires_at)
        self.expiration_trackers[credential_id] = tracker
    
    def setup_access_analyzer(self, credential_id: str):
        """Setup access pattern analyzer"""
        analyzer = AccessPatternAnalyzer(credential_id)
        self.access_analyzers[credential_id] = analyzer
    
    def setup_breach_detector(self, credential_id: str):
        """Setup breach detector"""
        detector = BreachDetector(credential_id)
        self.breach_detectors[credential_id] = detector
    
    def get_compliance_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate compliance report"""
        cutoff = datetime.now() - timedelta(days=days)
        
        recent_events = [e for e in self.events if e.timestamp > cutoff]
        
        # Count by event type
        event_counts = {}
        for event in recent_events:
            key = event.event_type.value
            event_counts[key] = event_counts.get(key, 0) + 1
        
        # Count by severity
        severity_counts = {}
        for event in recent_events:
            key = event.severity.value
            severity_counts[key] = severity_counts.get(key, 0) + 1
        
        return {
            "report_period_days": days,
            "total_events": len(recent_events),
            "event_types": event_counts,
            "severity_distribution": severity_counts,
            "rotations_due": sum(1 for s in self.rotation_schedules.values() if s.is_due_for_rotation()),
            "expiring_soon": sum(1 for t in self.expiration_trackers.values() if 0 <= t.days_until_expiration() <= 30),
            "breaches_detected": sum(1 for d in self.breach_detectors.values() if d.breach_detected)
        }
    
    def export_logs(self, include_signatures: bool = True) -> str:
        """Export logs as JSON"""
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "event_count": len(self.events),
            "events": [e.to_dict() for e in self.events]
        }
        
        if include_signatures:
            for event_dict in export_data["events"]:
                # Add signature (reconstruct event for signing)
                event = AuditEvent(**{
                    k: v if k != "event_type" and k != "severity" else
                       EventType(v) if k == "event_type" else SeverityLevel(v)
                    for k, v in event_dict.items()
                    if k not in ["severity", "event_type"]
                })
                event_dict["signature"] = event.calculate_signature(self.signing_key)
        
        return json.dumps(export_data, indent=2)


if __name__ == "__main__":
    print("=" * 80)
    print("AUDIT LOG SYSTEM FOR CREDENTIAL VAULT")
    print("=" * 80)
    
    # Initialize
    manager = AuditLogManager()
    
    print("\n[*] Logging credential events...")
    
    # Log some events
    cred_id = "cred_12345"
    
    manager.log_event(
        EventType.CREDENTIAL_CREATED,
        cred_id,
        "New EHR database credential created",
        actor="admin_user",
        severity=SeverityLevel.INFO,
        details={"type": "mysql", "host": "192.168.1.20"}
    )
    
    manager.log_event(
        EventType.CREDENTIAL_RETRIEVED,
        cred_id,
        "Credential accessed",
        actor="Dr_Smith",
        severity=SeverityLevel.INFO,
        details={"reason": "Patient lookup"}
    )
    
    manager.log_event(
        EventType.FAILED_ATTEMPT,
        cred_id,
        "Failed access attempt",
        actor="unknown_user",
        severity=SeverityLevel.WARNING,
        result=False,
        client_ip="203.0.113.45"
    )
    
    # Setup tracking
    print("\n[*] Setting up credential tracking...")
    manager.setup_rotation_schedule(cred_id, interval_days=90)
    manager.setup_expiration_tracking(cred_id, datetime.now() + timedelta(days=45))
    manager.setup_access_analyzer(cred_id)
    manager.setup_breach_detector(cred_id)
    
    # Generate report
    print("\n[+] Compliance Report:")
    report = manager.get_compliance_report(days=30)
    for key, value in report.items():
        print(f"    {key}: {value}")
    
    # Export logs
    print("\n[*] Exporting logs...")
    logs_json = manager.export_logs()
    print(f"    Exported {len(manager.events)} events")
    print(f"    Log size: {len(logs_json)} bytes")
