"""
Security Monitor for Agent 3 Credential Vault

Real-time monitoring for breach attempts, anomalies, and security incidents
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import statistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Security threat levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class IncidentType(Enum):
    """Types of security incidents"""
    BRUTE_FORCE = "brute_force"
    UNUSUAL_ACCESS = "unusual_access"
    CREDENTIAL_ABUSE = "credential_abuse"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    POLICY_VIOLATION = "policy_violation"
    DATA_EXPOSURE = "data_exposure"
    ROTATION_OVERDUE = "rotation_overdue"
    EXPIRATION_OVERDUE = "expiration_overdue"
    INSIDER_THREAT = "insider_threat"
    SYSTEM_COMPROMISE = "system_compromise"


@dataclass
class SecurityIncident:
    """Security incident report"""
    incident_id: str
    incident_type: IncidentType
    threat_level: ThreatLevel
    detected_at: datetime
    credential_id: str
    description: str
    affected_resource: str
    indicators: List[str]
    recommended_action: str
    status: str = "open"  # open, investigating, resolved
    investigation_notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return {
            "incident_id": self.incident_id,
            "incident_type": self.incident_type.value,
            "threat_level": self.threat_level.name,
            "detected_at": self.detected_at.isoformat(),
            "credential_id": self.credential_id,
            "description": self.description,
            "affected_resource": self.affected_resource,
            "indicators": self.indicators,
            "recommended_action": self.recommended_action,
            "status": self.status
        }


@dataclass
class AccessMetrics:
    """Metrics for credential access"""
    credential_id: str
    total_accesses: int = 0
    successful_accesses: int = 0
    failed_accesses: int = 0
    unique_actors: int = 0
    access_times: List[datetime] = None
    
    def __post_init__(self):
        if self.access_times is None:
            self.access_times = []
    
    def calculate_success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_accesses == 0:
            return 0.0
        return (self.successful_accesses / self.total_accesses) * 100
    
    def get_access_frequency(self, hours: int = 24) -> int:
        """Get access frequency in last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return sum(1 for t in self.access_times if t > cutoff)


class AnomalyDetector:
    """
    Detects anomalous credential usage patterns
    
    Uses statistical analysis to identify unusual activity
    """
    
    def __init__(self, credential_id: str):
        """Initialize detector"""
        self.credential_id = credential_id
        self.baseline_metrics = {}
        self.current_metrics = AccessMetrics(credential_id)
        self.anomalies: List[Dict[str, Any]] = []
        self.access_history: List[Dict[str, Any]] = []
    
    def set_baseline(self, metrics: Dict[str, Any]):
        """Set baseline metrics for comparison"""
        self.baseline_metrics = metrics
        logger.info(f"Baseline set for {self.credential_id}: {metrics}")
    
    def record_access(self, accessed_by: str, success: bool, 
                     timestamp: datetime = None):
        """Record credential access"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.current_metrics.total_accesses += 1
        if success:
            self.current_metrics.successful_accesses += 1
        else:
            self.current_metrics.failed_accesses += 1
        
        self.current_metrics.access_times.append(timestamp)
        
        self.access_history.append({
            "accessed_by": accessed_by,
            "success": success,
            "timestamp": timestamp,
            "hour": timestamp.hour
        })
    
    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalous patterns"""
        anomalies = []
        
        if not self.baseline_metrics:
            return anomalies
        
        # Check success rate
        current_rate = self.current_metrics.calculate_success_rate()
        baseline_rate = self.baseline_metrics.get("success_rate", 95)
        
        if current_rate < baseline_rate - 20:  # 20% drop
            anomalies.append({
                "type": "degraded_success_rate",
                "severity": "high",
                "baseline": baseline_rate,
                "current": current_rate,
                "message": f"Success rate dropped from {baseline_rate}% to {current_rate}%"
            })
        
        # Check access frequency
        baseline_freq = self.baseline_metrics.get("access_frequency_24h", 10)
        current_freq = self.current_metrics.get_access_frequency(hours=24)
        
        if current_freq > baseline_freq * 3:  # 3x increase
            anomalies.append({
                "type": "unusual_access_frequency",
                "severity": "medium",
                "baseline": baseline_freq,
                "current": current_freq,
                "message": f"Access frequency unusually high: {current_freq} accesses in 24h"
            })
        
        # Check for new unique actors
        unique_actors = set(a["accessed_by"] for a in self.access_history)
        baseline_actors = self.baseline_metrics.get("unique_actors", set())
        new_actors = unique_actors - baseline_actors
        
        if new_actors:
            anomalies.append({
                "type": "new_actors_detected",
                "severity": "medium",
                "new_actors": list(new_actors),
                "message": f"New users accessing credential: {new_actors}"
            })
        
        self.anomalies.extend(anomalies)
        return anomalies
    
    def get_anomaly_score(self) -> float:
        """
        Calculate anomaly score (0-100)
        
        Higher score = more anomalous
        """
        score = 0.0
        
        # Factor: Success rate
        current_rate = self.current_metrics.calculate_success_rate()
        baseline_rate = self.baseline_metrics.get("success_rate", 95)
        if current_rate < baseline_rate:
            score += (baseline_rate - current_rate) * 0.5
        
        # Factor: Access frequency
        baseline_freq = self.baseline_metrics.get("access_frequency_24h", 10)
        current_freq = self.current_metrics.get_access_frequency(hours=24)
        if current_freq > baseline_freq:
            ratio = current_freq / baseline_freq
            score += min(30, (ratio - 1) * 10)
        
        # Factor: Failed attempts
        if self.current_metrics.failed_accesses >= 5:
            score += min(30, self.current_metrics.failed_accesses * 5)
        
        return min(100, score)


class BruteForceDectector:
    """
    Detects brute force and credential abuse attacks
    """
    
    def __init__(self, credential_id: str, 
                 failure_threshold: int = 5,
                 window_minutes: int = 5):
        """
        Initialize detector
        
        Args:
            credential_id: Credential to monitor
            failure_threshold: Trigger alert after N failures
            window_minutes: Time window to analyze
        """
        self.credential_id = credential_id
        self.failure_threshold = failure_threshold
        self.window_minutes = window_minutes
        self.failed_attempts: List[Dict[str, Any]] = []
        self.blocked_ips: List[str] = []
        self.blocked_users: List[str] = []
    
    def record_failed_attempt(self, user: str = None, client_ip: str = None,
                            timestamp: datetime = None):
        """Record failed access attempt"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.failed_attempts.append({
            "user": user,
            "client_ip": client_ip,
            "timestamp": timestamp
        })
    
    def detect_brute_force(self) -> Optional[Dict[str, Any]]:
        """
        Detect ongoing brute force attack
        
        Returns: Attack details or None if no attack detected
        """
        if not self.failed_attempts:
            return None
        
        now = datetime.now()
        window_start = now - timedelta(minutes=self.window_minutes)
        
        # Get failures in window
        recent_failures = [
            f for f in self.failed_attempts
            if f["timestamp"] > window_start
        ]
        
        if len(recent_failures) < self.failure_threshold:
            return None
        
        # Analyze failure pattern
        ips = [f["client_ip"] for f in recent_failures if f["client_ip"]]
        users = [f["user"] for f in recent_failures if f["user"]]
        
        # Count by IP
        ip_counts = {}
        for ip in ips:
            ip_counts[ip] = ip_counts.get(ip, 0) + 1
        
        # Count by user
        user_counts = {}
        for user in users:
            user_counts[user] = user_counts.get(user, 0) + 1
        
        attack_info = {
            "attack_type": "brute_force",
            "credential_id": self.credential_id,
            "failures_in_window": len(recent_failures),
            "window_minutes": self.window_minutes,
            "by_ip": ip_counts,
            "by_user": user_counts,
            "recommendation": "Block IPs and consider credential rotation",
            "timestamp": now.isoformat()
        }
        
        # Block offending IPs
        for ip, count in ip_counts.items():
            if count >= self.failure_threshold // 2 and ip not in self.blocked_ips:
                self.blocked_ips.append(ip)
                logger.warning(f"Blocked IP {ip} for {self.credential_id}")
        
        return attack_info
    
    def is_blocked(self, client_ip: str) -> bool:
        """Check if IP is blocked"""
        return client_ip in self.blocked_ips
    
    def get_blocked_entities(self) -> Dict[str, List]:
        """Get list of blocked IPs and users"""
        return {
            "blocked_ips": self.blocked_ips,
            "blocked_users": self.blocked_users
        }


class SecurityMonitor:
    """
    Central security monitoring system
    
    Coordinates all security detection and incident reporting
    """
    
    def __init__(self):
        """Initialize monitor"""
        self.incidents: List[SecurityIncident] = []
        self.anomaly_detectors: Dict[str, AnomalyDetector] = {}
        self.brute_force_detectors: Dict[str, BruteForceDectector] = {}
        self.security_policies: Dict[str, Any] = self._setup_policies()
    
    def _setup_policies(self) -> Dict[str, Any]:
        """Setup default security policies"""
        return {
            "max_failed_attempts": 5,
            "brute_force_window_minutes": 5,
            "rotation_interval_days": 90,
            "max_expiration_days": 365,
            "require_mfa_for_sensitive": True,
            "unusual_access_hours": (22, 6),  # 10 PM to 6 AM
            "max_concurrent_sessions": 3,
            "session_timeout_minutes": 30
        }
    
    def register_credential(self, credential_id: str):
        """Register credential for monitoring"""
        if credential_id not in self.anomaly_detectors:
            self.anomaly_detectors[credential_id] = AnomalyDetector(credential_id)
            self.brute_force_detectors[credential_id] = BruteForceDectector(credential_id)
            logger.info(f"Registered {credential_id} for monitoring")
    
    def record_access(self, credential_id: str, user: str,
                     success: bool, client_ip: str = None):
        """Record credential access"""
        if credential_id not in self.anomaly_detectors:
            self.register_credential(credential_id)
        
        timestamp = datetime.now()
        
        self.anomaly_detectors[credential_id].record_access(user, success, timestamp)
        
        if not success:
            self.brute_force_detectors[credential_id].record_failed_attempt(
                user=user,
                client_ip=client_ip,
                timestamp=timestamp
            )
            
            # Check for brute force
            attack = self.brute_force_detectors[credential_id].detect_brute_force()
            if attack:
                self._create_incident(
                    IncidentType.BRUTE_FORCE,
                    credential_id,
                    f"Brute force attack detected: {attack['failures_in_window']} failures",
                    affected_resource=client_ip or "unknown",
                    indicators=list(attack["by_ip"].keys()),
                    threat_level=ThreatLevel.CRITICAL
                )
    
    def check_credential_policy(self, credential_id: str,
                               created_at: datetime,
                               last_rotated: datetime,
                               expires_at: datetime) -> List[Dict[str, Any]]:
        """Check credential against policies"""
        violations = []
        now = datetime.now()
        
        # Check rotation
        rotation_age = (now - last_rotated).days
        if rotation_age > self.security_policies["rotation_interval_days"]:
            violations.append({
                "policy": "rotation_interval",
                "violation": f"Credential not rotated for {rotation_age} days",
                "severity": ThreatLevel.HIGH,
                "action": "Rotate credential"
            })
            
            self._create_incident(
                IncidentType.ROTATION_OVERDUE,
                credential_id,
                f"Credential rotation overdue by {rotation_age - self.security_policies['rotation_interval_days']} days",
                affected_resource=credential_id,
                threat_level=ThreatLevel.HIGH
            )
        
        # Check expiration
        days_to_expiry = (expires_at - now).days
        if days_to_expiry < 0:
            violations.append({
                "policy": "expiration",
                "violation": "Credential has expired",
                "severity": ThreatLevel.CRITICAL,
                "action": "Immediately revoke and replace credential"
            })
            
            self._create_incident(
                IncidentType.EXPIRATION_OVERDUE,
                credential_id,
                "Credential has expired and must be replaced",
                affected_resource=credential_id,
                threat_level=ThreatLevel.CRITICAL
            )
        elif days_to_expiry < 30:
            violations.append({
                "policy": "expiration_warning",
                "violation": f"Credential expires in {days_to_expiry} days",
                "severity": ThreatLevel.MEDIUM,
                "action": "Plan credential renewal"
            })
        
        return violations
    
    def get_security_score(self, credential_id: str) -> float:
        """
        Calculate security score for credential (0-100)
        
        Higher score = more secure
        """
        if credential_id not in self.anomaly_detectors:
            return 100.0
        
        anomaly_score = self.anomaly_detectors[credential_id].get_anomaly_score()
        
        # Invert: lower anomaly = higher security
        security_score = 100 - anomaly_score
        
        return max(0, min(100, security_score))
    
    def _create_incident(self, incident_type: IncidentType,
                        credential_id: str, description: str,
                        affected_resource: str,
                        threat_level: ThreatLevel = ThreatLevel.MEDIUM,
                        indicators: List[str] = None):
        """Create security incident"""
        import secrets
        
        # Determine recommended action
        action_map = {
            IncidentType.BRUTE_FORCE: "Block attacking IPs immediately and rotate credential",
            IncidentType.UNUSUAL_ACCESS: "Review access logs and investigate abnormal activity",
            IncidentType.ROTATION_OVERDUE: "Rotate credential to new values",
            IncidentType.EXPIRATION_OVERDUE: "Revoke expired credential and create replacement",
            IncidentType.SYSTEM_COMPROMISE: "Isolate affected systems and begin incident response"
        }
        
        incident = SecurityIncident(
            incident_id=secrets.token_hex(16),
            incident_type=incident_type,
            threat_level=threat_level,
            detected_at=datetime.now(),
            credential_id=credential_id,
            description=description,
            affected_resource=affected_resource,
            indicators=indicators or [],
            recommended_action=action_map.get(incident_type, "Investigate and take appropriate action")
        )
        
        self.incidents.append(incident)
        
        log_level = {
            ThreatLevel.LOW: logging.INFO,
            ThreatLevel.MEDIUM: logging.WARNING,
            ThreatLevel.HIGH: logging.WARNING,
            ThreatLevel.CRITICAL: logging.CRITICAL
        }
        
        logger.log(
            log_level.get(threat_level, logging.INFO),
            f"[{incident_type.value.upper()}] {description}"
        )
    
    def get_incidents(self, status: str = None,
                     threat_level: ThreatLevel = None) -> List[Dict[str, Any]]:
        """Get security incidents"""
        incidents = self.incidents
        
        if status:
            incidents = [i for i in incidents if i.status == status]
        
        if threat_level:
            incidents = [i for i in incidents if i.threat_level == threat_level]
        
        return [i.to_dict() for i in incidents]
    
    def get_security_report(self) -> Dict[str, Any]:
        """Generate security report"""
        return {
            "report_time": datetime.now().isoformat(),
            "total_incidents": len(self.incidents),
            "by_type": {t.value: len([i for i in self.incidents if i.incident_type == t])
                       for t in IncidentType},
            "by_threat_level": {
                "low": len([i for i in self.incidents if i.threat_level == ThreatLevel.LOW]),
                "medium": len([i for i in self.incidents if i.threat_level == ThreatLevel.MEDIUM]),
                "high": len([i for i in self.incidents if i.threat_level == ThreatLevel.HIGH]),
                "critical": len([i for i in self.incidents if i.threat_level == ThreatLevel.CRITICAL])
            },
            "open_incidents": len([i for i in self.incidents if i.status == "open"]),
            "credentials_monitored": len(self.anomaly_detectors),
            "anomaly_detection_enabled": len(self.anomaly_detectors) > 0,
            "brute_force_protection_enabled": len(self.brute_force_detectors) > 0
        }


if __name__ == "__main__":
    print("=" * 80)
    print("SECURITY MONITOR FOR CREDENTIAL VAULT")
    print("=" * 80)
    
    # Initialize
    monitor = SecurityMonitor()
    
    print("\n[*] Registering credentials...")
    cred_id = "cred_ehr_db"
    monitor.register_credential(cred_id)
    
    # Simulate some access
    print("\n[*] Simulating credential access...")
    
    # Normal access
    monitor.record_access(cred_id, "Dr_Smith", success=True)
    monitor.record_access(cred_id, "Dr_Smith", success=True)
    
    # Failed attempts (simulate brute force)
    print("    [!] Simulating brute force attack...")
    for i in range(6):
        monitor.record_access(cred_id, f"attacker_{i}", success=False, 
                            client_ip="203.0.113.100")
    
    # Check security score
    print("\n[+] Security Analysis:")
    score = monitor.get_security_score(cred_id)
    print(f"    Security Score: {score:.1f}/100")
    
    # Get incidents
    print("\n[!] Incidents Detected:")
    incidents = monitor.get_incidents()
    for incident in incidents:
        print(f"    - {incident['incident_type']}: {incident['description']}")
    
    # Security report
    print("\n[+] Security Report:")
    report = monitor.get_security_report()
    print(f"    Total Incidents: {report['total_incidents']}")
    print(f"    Critical: {report['by_threat_level']['critical']}")
    print(f"    Open: {report['open_incidents']}")
