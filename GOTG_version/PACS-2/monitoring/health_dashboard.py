#!/usr/bin/env python3
"""
GOTG PACS - Health Dashboard & Monitoring
Real-time visibility and predictive alerts
PRODUCTION-READY - Lives depend on this
"""

import sqlite3
import logging
import json
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from flask import Blueprint, jsonify
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== HEALTH DASHBOARD =====

class HealthDashboard:
    """Comprehensive health monitoring and alerting"""
    
    def __init__(self, db_path="/var/lib/pacs/health.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize health database"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Health events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_events (
                id INTEGER PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                component TEXT NOT NULL,
                status TEXT NOT NULL,
                value FLOAT,
                message TEXT
            )
        """)
        
        # Alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                severity TEXT NOT NULL,
                component TEXT NOT NULL,
                message TEXT NOT NULL,
                resolved BOOLEAN DEFAULT FALSE
            )
        """)
        
        # Performance baselines
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS baselines (
                id INTEGER PRIMARY KEY,
                component TEXT NOT NULL UNIQUE,
                normal_range_min FLOAT,
                normal_range_max FLOAT,
                warning_threshold FLOAT,
                critical_threshold FLOAT
            )
        """)
        
        conn.commit()
        conn.close()
        
        self._init_baselines()
    
    def _init_baselines(self):
        """Initialize performance baselines"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        baselines = {
            'cpu': {
                'normal_min': 0,
                'normal_max': 60,
                'warning': 80,
                'critical': 95
            },
            'memory': {
                'normal_min': 0,
                'normal_max': 70,
                'warning': 85,
                'critical': 95
            },
            'disk': {
                'normal_min': 0,
                'normal_max': 80,
                'warning': 90,
                'critical': 95
            },
            'sync_queue': {
                'normal_min': 0,
                'normal_max': 100,
                'warning': 500,
                'critical': 1000
            },
            'sync_failure_rate': {
                'normal_min': 0,
                'normal_max': 0.01,  # 1%
                'warning': 0.05,     # 5%
                'critical': 0.10     # 10%
            }
        }
        
        for component, thresholds in baselines.items():
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO baselines 
                    (component, normal_range_min, normal_range_max, warning_threshold, critical_threshold)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    component,
                    thresholds['normal_min'],
                    thresholds['normal_max'],
                    thresholds['warning'],
                    thresholds['critical']
                ))
            except Exception as e:
                logger.error(f"Failed to set baseline for {component}: {e}")
        
        conn.commit()
        conn.close()
    
    def record_event(self, component: str, status: str, value: float, message: str):
        """Record health event"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO health_events (component, status, value, message)
                VALUES (?, ?, ?, ?)
            """, (component, status, value, message))
            
            # Create alert if necessary
            if status in ['warning', 'critical']:
                cursor.execute("""
                    INSERT INTO alerts (severity, component, message)
                    VALUES (?, ?, ?)
                """, (status, component, message))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to record event: {e}")
    
    def get_dashboard_data(self) -> dict:
        """Get comprehensive dashboard data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get latest events for each component
            components = ['cpu', 'memory', 'disk', 'sync_queue', 'sync_failure_rate', 
                         'network', 'storage', 'database']
            latest_events = {}
            
            for component in components:
                cursor.execute("""
                    SELECT timestamp, status, value, message
                    FROM health_events
                    WHERE component = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (component,))
                
                result = cursor.fetchone()
                if result:
                    latest_events[component] = {
                        'timestamp': result[0],
                        'status': result[1],
                        'value': result[2],
                        'message': result[3]
                    }
            
            # Calculate trends (last 24 hours)
            cutoff = datetime.now() - timedelta(hours=24)
            
            cursor.execute("""
                SELECT component, AVG(value), MIN(value), MAX(value), COUNT(*)
                FROM health_events
                WHERE timestamp > ?
                GROUP BY component
            """, (cutoff.isoformat(),))
            
            trends = {}
            for row in cursor.fetchall():
                component, avg_val, min_val, max_val, count = row
                if avg_val is not None:
                    trends[component] = {
                        'average': round(avg_val, 2),
                        'minimum': round(min_val, 2) if min_val else 0,
                        'maximum': round(max_val, 2) if max_val else 0,
                        'samples': count
                    }
            
            # Get active alerts
            cursor.execute("""
                SELECT severity, component, message, timestamp
                FROM alerts
                WHERE resolved = FALSE
                ORDER BY timestamp DESC
            """)
            
            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    'severity': row[0],
                    'component': row[1],
                    'message': row[2],
                    'timestamp': row[3]
                })
            
            conn.close()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'status': self._calculate_overall_status(latest_events),
                'components': latest_events,
                'trends': trends,
                'alerts': alerts,
                'system_resources': self._get_system_resources()
            }
        
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'status': 'unknown',
                'error': str(e)
            }
    
    def _calculate_overall_status(self, events: dict) -> str:
        """Calculate overall system status"""
        if any(e.get('status') == 'critical' for e in events.values()):
            return 'critical'
        if any(e.get('status') == 'warning' for e in events.values()):
            return 'warning'
        return 'healthy'
    
    def _get_system_resources(self) -> dict:
        """Get current system resource usage"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'cpu_count': psutil.cpu_count(),
                'memory_mb': psutil.virtual_memory().total / (1024 * 1024),
                'disk_gb': psutil.disk_usage('/').total / (1024 * 1024 * 1024)
            }
        except Exception as e:
            logger.error(f"Failed to get system resources: {e}")
            return {}
    
    def get_active_alerts(self) -> List[Dict]:
        """Get active alerts only"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT severity, component, message, timestamp
                FROM alerts
                WHERE resolved = FALSE
                ORDER BY timestamp DESC
            """)
            
            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    'severity': row[0],
                    'component': row[1],
                    'message': row[2],
                    'timestamp': row[3]
                })
            
            conn.close()
            return alerts
        
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []
    
    def resolve_alert(self, alert_id: int):
        """Mark alert as resolved"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE alerts
                SET resolved = TRUE
                WHERE id = ?
            """, (alert_id,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
    
    def get_performance_trend(self, component: str, hours: int = 24) -> dict:
        """Get performance trend for a component"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff = datetime.now() - timedelta(hours=hours)
            
            cursor.execute("""
                SELECT timestamp, value, status
                FROM health_events
                WHERE component = ? AND timestamp > ?
                ORDER BY timestamp ASC
            """, (component, cutoff.isoformat()))
            
            data_points = []
            for row in cursor.fetchall():
                data_points.append({
                    'timestamp': row[0],
                    'value': row[1],
                    'status': row[2]
                })
            
            conn.close()
            
            if not data_points:
                return {'component': component, 'data_points': []}
            
            return {
                'component': component,
                'period_hours': hours,
                'data_points': data_points,
                'min': min(p['value'] for p in data_points if p['value'] is not None),
                'max': max(p['value'] for p in data_points if p['value'] is not None),
                'avg': sum(p['value'] for p in data_points if p['value'] is not None) / len(data_points)
            }
        
        except Exception as e:
            logger.error(f"Failed to get performance trend: {e}")
            return {'error': str(e)}

# ===== FLASK BLUEPRINT =====

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
health_dashboard = HealthDashboard()

@dashboard_bp.route('/status')
def dashboard_status():
    """Get health dashboard data"""
    return jsonify(health_dashboard.get_dashboard_data())

@dashboard_bp.route('/alerts')
def get_alerts():
    """Get active alerts"""
    return jsonify(health_dashboard.get_active_alerts())

@dashboard_bp.route('/alert/<int:alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id):
    """Resolve an alert"""
    health_dashboard.resolve_alert(alert_id)
    return jsonify({'status': 'resolved'})

@dashboard_bp.route('/trend/<component>')
def get_trend(component):
    """Get performance trend for component"""
    hours = request.args.get('hours', 24, type=int)
    return jsonify(health_dashboard.get_performance_trend(component, hours))

@dashboard_bp.route('/health')
def health_check():
    """Health check endpoint"""
    data = health_dashboard.get_dashboard_data()
    status_code = 200 if data['status'] in ['healthy', 'warning'] else 500
    return jsonify(data), status_code

# ===== MAIN EXECUTION =====

if __name__ == '__main__':
    # Initialize dashboard
    dashboard = HealthDashboard()
    
    # Record some sample events
    dashboard.record_event('cpu', 'normal', 45.0, 'CPU usage normal')
    dashboard.record_event('memory', 'normal', 62.0, 'Memory usage normal')
    dashboard.record_event('disk', 'warning', 82.0, 'Disk usage approaching limit')
    
    # Display dashboard
    print(json.dumps(dashboard.get_dashboard_data(), indent=2))
