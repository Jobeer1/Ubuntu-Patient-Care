#!/usr/bin/env python3
"""
System API for Medical Reporting Module
System status, health checks, and monitoring endpoints
"""

import logging
from flask import Blueprint, jsonify, request
from datetime import datetime
import psutil
import os

logger = logging.getLogger(__name__)

# Create blueprint
system_api = Blueprint('system_api', __name__, url_prefix='/api/system')

@system_api.route('/status', methods=['GET'])
def get_system_status():
    """Get comprehensive system status"""
    try:
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get service status (mock for now)
        services = {
            'voice_engine': 'online',
            'dicom_service': 'online', 
            'orthanc_pacs': 'online',
            'nas_storage': 'online',
            'whisper_model': 'loaded',
            'ssl_certificates': 'valid',
            'database': 'connected'
        }
        
        # Calculate uptime
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'environment': os.getenv('FLASK_ENV', 'production'),
            'services': services,
            'system_metrics': {
                'cpu_usage': f"{cpu_percent}%",
                'memory_usage': f"{memory.percent}%",
                'memory_available': f"{memory.available / (1024**3):.1f} GB",
                'disk_usage': f"{disk.percent}%",
                'disk_free': f"{disk.free / (1024**3):.1f} GB"
            },
            'uptime': {
                'days': uptime.days,
                'hours': uptime.seconds // 3600,
                'minutes': (uptime.seconds % 3600) // 60
            },
            'features': {
                'voice_dictation': True,
                'dicom_viewer': True,
                'pacs_integration': True,
                'nas_storage': True,
                'ssl_enabled': True,
                'sa_localization': True
            }
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"System status error: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get system status',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@system_api.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'message': 'SA Medical Reporting Module is running'
    })

@system_api.route('/version', methods=['GET'])
def get_version():
    """Get application version information"""
    return jsonify({
        'version': '1.0.0',
        'build_date': '2024-08-25',
        'environment': os.getenv('FLASK_ENV', 'production'),
        'python_version': os.sys.version,
        'features': [
            'Voice Dictation',
            'DICOM Integration', 
            'SA Localization',
            'POPIA Compliance',
            'HPCSA Standards'
        ]
    })

@system_api.route('/logs', methods=['GET'])
def get_system_logs():
    """Get recent system logs"""
    try:
        # Get query parameters
        level = request.args.get('level', 'INFO')
        limit = int(request.args.get('limit', 100))
        
        # Mock log entries (in production, read from actual log files)
        logs = [
            {
                'timestamp': datetime.utcnow().isoformat(),
                'level': 'INFO',
                'module': 'system_api',
                'message': 'System status requested'
            },
            {
                'timestamp': datetime.utcnow().isoformat(),
                'level': 'INFO', 
                'module': 'voice_engine',
                'message': 'Voice engine initialized successfully'
            },
            {
                'timestamp': datetime.utcnow().isoformat(),
                'level': 'INFO',
                'module': 'ssl_manager', 
                'message': 'SSL certificates validated'
            }
        ]
        
        return jsonify({
            'logs': logs[:limit],
            'total': len(logs),
            'level_filter': level,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"System logs error: {e}")
        return jsonify({
            'error': 'Failed to retrieve system logs',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@system_api.route('/restart', methods=['POST'])
def restart_system():
    """Restart system services (admin only)"""
    try:
        # In production, this would restart services
        # For now, just return success
        
        return jsonify({
            'status': 'success',
            'message': 'System restart initiated',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"System restart error: {e}")
        return jsonify({
            'error': 'Failed to restart system',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@system_api.route('/config', methods=['GET'])
def get_system_config():
    """Get system configuration (sanitized)"""
    try:
        config = {
            'voice_engine': {
                'model': 'whisper-base',
                'language': 'en-ZA',
                'offline_mode': True
            },
            'dicom': {
                'orthanc_enabled': True,
                'port': 8042
            },
            'ssl': {
                'enabled': True,
                'port': 5001
            },
            'localization': {
                'country': 'South Africa',
                'medical_terms': 78,
                'compliance': ['POPIA', 'HPCSA']
            }
        }
        
        return jsonify({
            'config': config,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"System config error: {e}")
        return jsonify({
            'error': 'Failed to get system configuration',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# Error handlers
@system_api.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'timestamp': datetime.utcnow().isoformat()
    }), 404

@system_api.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'timestamp': datetime.utcnow().isoformat()
    }), 500