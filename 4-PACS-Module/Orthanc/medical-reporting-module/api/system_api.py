"""System API for health checks and service status monitoring"""

from flask import Blueprint, jsonify, request
import psutil
import os
import time
from datetime import datetime

system_bp = Blueprint('system', __name__)

@system_bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    try:
        return jsonify({
            'success': True,
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'Medical Reporting Module'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@system_bp.route('/status', methods=['GET'])
def system_status():
    """Detailed system status information"""
    try:
        # Get system information
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return jsonify({
            'success': True,
            'data': {
                'system': {
                    'cpu_usage': cpu_percent,
                    'memory': {
                        'total': memory.total,
                        'available': memory.available,
                        'percent': memory.percent
                    },
                    'disk': {
                        'total': disk.total,
                        'free': disk.free,
                        'percent': (disk.used / disk.total) * 100
                    }
                },
                'services': {
                    'voice_api': True,
                    'database': True,
                    'whisper': True
                },
                'uptime': time.time() - psutil.boot_time()
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@system_bp.route('/info', methods=['GET'])
def system_info():
    """System information endpoint"""
    try:
        return jsonify({
            'success': True,
            'data': {
                'version': '1.0.0',
                'environment': os.environ.get('FLASK_ENV', 'development'),
                'python_version': os.sys.version,
                'platform': os.name,
                'features': [
                    'speech_to_text',
                    'medical_terminology',
                    'voice_shortcuts',
                    'training_mode'
                ]
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500