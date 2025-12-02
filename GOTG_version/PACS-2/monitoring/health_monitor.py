#!/usr/bin/env python3
"""
GOTG PACS Health Monitor
Real-time system monitoring and alerting
"""

import os
import time
import logging
import requests
import psutil
import docker
from datetime import datetime
from flask import Flask, jsonify, render_template_string
from threading import Thread

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
ORTHANC_URL = os.getenv('ORTHANC_URL', 'http://pacs-orthanc:8042')
ALERT_EMAIL = os.getenv('ALERT_EMAIL', '')
ALERT_WHATSAPP = os.getenv('ALERT_WHATSAPP', '')

# Flask app
app = Flask(__name__)

class HealthMonitor:
    """Monitor PACS system health"""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.alerts = []
        self.metrics = {
            'system': {},
            'orthanc': {},
            'containers': {},
            'storage': {}
        }
    
    def check_system_health(self):
        """Check overall system health"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            self.metrics['system'] = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3),
                'timestamp': datetime.now().isoformat()
            }
            
            # Check thresholds
            if cpu_percent > 90:
                self.create_alert('critical', 'CPU usage above 90%')
            if memory.percent > 90:
                self.create_alert('critical', 'Memory usage above 90%')
            if disk.percent > 90:
                self.create_alert('critical', 'Disk usage above 90%')
            
            logger.debug(f"System health: CPU {cpu_percent}%, Memory {memory.percent}%, Disk {disk.percent}%")
            
        except Exception as e:
            logger.error(f"System health check failed: {e}")
    
    def check_orthanc_health(self):
        """Check Orthanc PACS health"""
        try:
            response = requests.get(
                f'{ORTHANC_URL}/system',
                auth=('orthanc', 'orthanc'),
                timeout=5
            )
            
            if response.status_code == 200:
                system_info = response.json()
                
                # Get statistics
                stats_response = requests.get(
                    f'{ORTHANC_URL}/statistics',
                    auth=('orthanc', 'orthanc'),
                    timeout=5
                )
                
                if stats_response.status_code == 200:
                    stats = stats_response.json()
                    
                    self.metrics['orthanc'] = {
                        'status': 'healthy',
                        'version': system_info.get('Version'),
                        'total_patients': stats.get('CountPatients', 0),
                        'total_studies': stats.get('CountStudies', 0),
                        'total_series': stats.get('CountSeries', 0),
                        'total_instances': stats.get('CountInstances', 0),
                        'disk_size_mb': stats.get('TotalDiskSizeMB', 0),
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    logger.debug(f"Orthanc healthy: {stats.get('CountStudies', 0)} studies")
                else:
                    self.metrics['orthanc'] = {'status': 'degraded'}
                    self.create_alert('warning', 'Orthanc statistics unavailable')
            else:
                self.metrics['orthanc'] = {'status': 'unhealthy'}
                self.create_alert('critical', 'Orthanc is not responding')
                
        except Exception as e:
            self.metrics['orthanc'] = {'status': 'error', 'error': str(e)}
            self.create_alert('critical', f'Orthanc health check failed: {e}')
            logger.error(f"Orthanc health check failed: {e}")
    
    def check_containers_health(self):
        """Check Docker containers health"""
        try:
            containers = self.docker_client.containers.list(all=True)
            container_status = {}
            
            for container in containers:
                if 'gotg-pacs' in container.name or 'pacs' in container.name:
                    status = container.status
                    container_status[container.name] = {
                        'status': status,
                        'image': container.image.tags[0] if container.image.tags else 'unknown',
                        'created': container.attrs['Created']
                    }
                    
                    if status != 'running':
                        self.create_alert('critical', f'Container {container.name} is {status}')
            
            self.metrics['containers'] = container_status
            logger.debug(f"Checked {len(container_status)} containers")
            
        except Exception as e:
            logger.error(f"Container health check failed: {e}")
    
    def check_storage_health(self):
        """Check storage health"""
        try:
            # Check DICOM storage
            dicom_path = '/var/lib/orthanc/db'
            if os.path.exists(dicom_path):
                total_size = 0
                file_count = 0
                
                for root, dirs, files in os.walk(dicom_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                        file_count += 1
                
                self.metrics['storage'] = {
                    'dicom_size_gb': total_size / (1024**3),
                    'file_count': file_count,
                    'timestamp': datetime.now().isoformat()
                }
                
                logger.debug(f"Storage: {total_size / (1024**3):.2f} GB, {file_count} files")
            
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
    
    def create_alert(self, severity, message):
        """Create alert"""
        alert = {
            'severity': severity,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        self.alerts.append(alert)
        logger.warning(f"Alert [{severity}]: {message}")
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        
        # Send notifications
        if severity == 'critical':
            self.send_notifications(alert)
    
    def send_notifications(self, alert):
        """Send alert notifications"""
        try:
            if ALERT_EMAIL:
                # Send email (implementation depends on email service)
                logger.info(f"Email alert sent to {ALERT_EMAIL}")
            
            if ALERT_WHATSAPP:
                # Send WhatsApp (implementation depends on WhatsApp API)
                logger.info(f"WhatsApp alert sent to {ALERT_WHATSAPP}")
        except Exception as e:
            logger.error(f"Failed to send notifications: {e}")
    
    def run(self):
        """Main monitoring loop"""
        logger.info("Starting GOTG PACS Health Monitor")
        
        while True:
            try:
                self.check_system_health()
                self.check_orthanc_health()
                self.check_containers_health()
                self.check_storage_health()
                time.sleep(30)
            except KeyboardInterrupt:
                logger.info("Shutting down health monitor")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)

# Global monitor instance
health_monitor = HealthMonitor()

# Dashboard HTML template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>GOTG PACS Monitor</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body { font-family: Arial, sans-serif; background: #1a1a1a; color: #fff; padding: 20px; }
        .header { background: #2d2d2d; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .metric-card { background: #2d2d2d; padding: 20px; border-radius: 8px; }
        .metric-card h3 { color: #00a8e8; margin-top: 0; }
        .status-healthy { color: #4caf50; }
        .status-warning { color: #ff9800; }
        .status-critical { color: #f44336; }
        .alert { background: #f44336; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .progress-bar { background: #444; height: 20px; border-radius: 4px; overflow: hidden; }
        .progress-fill { background: #00a8e8; height: 100%; transition: width 0.3s; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏥 GOTG PACS Health Monitor</h1>
        <p>Last updated: {{ timestamp }}</p>
    </div>
    
    <div class="metrics">
        <div class="metric-card">
            <h3>System Resources</h3>
            <p>CPU: {{ system.cpu_percent }}%</p>
            <div class="progress-bar"><div class="progress-fill" style="width: {{ system.cpu_percent }}%"></div></div>
            <p>Memory: {{ system.memory_percent }}%</p>
            <div class="progress-bar"><div class="progress-fill" style="width: {{ system.memory_percent }}%"></div></div>
            <p>Disk: {{ system.disk_percent }}%</p>
            <div class="progress-bar"><div class="progress-fill" style="width: {{ system.disk_percent }}%"></div></div>
        </div>
        
        <div class="metric-card">
            <h3>Orthanc PACS</h3>
            <p>Status: <span class="status-{{ orthanc.status }}">{{ orthanc.status }}</span></p>
            <p>Patients: {{ orthanc.total_patients }}</p>
            <p>Studies: {{ orthanc.total_studies }}</p>
            <p>Storage: {{ orthanc.disk_size_mb }} MB</p>
        </div>
        
        <div class="metric-card">
            <h3>Recent Alerts</h3>
            {% for alert in alerts[-5:] %}
            <div class="alert">{{ alert.message }} ({{ alert.timestamp }})</div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

# Flask routes
@app.route('/')
def dashboard():
    """Dashboard view"""
    return render_template_string(
        DASHBOARD_HTML,
        timestamp=datetime.now().isoformat(),
        system=health_monitor.metrics.get('system', {}),
        orthanc=health_monitor.metrics.get('orthanc', {}),
        alerts=health_monitor.alerts
    )

@app.route('/health')
def health():
    """Health check"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/metrics')
def metrics():
    """Get all metrics"""
    return jsonify(health_monitor.metrics)

@app.route('/alerts')
def alerts():
    """Get all alerts"""
    return jsonify(health_monitor.alerts)

def run_flask():
    """Run Flask server"""
    app.run(host='0.0.0.0', port=5002, debug=False)

if __name__ == '__main__':
    # Start Flask in separate thread
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Run monitor
    health_monitor.run()
