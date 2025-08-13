#!/usr/bin/env python3
"""
Minimal test server to check device endpoints
"""

from flask import Flask, jsonify
from flask_cors import CORS
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Import device manager
try:
    from device_management_fallback import device_manager
    logger.info("✅ Using fallback device manager")
except ImportError:
    logger.error("❌ Could not import device manager")
    device_manager = None

# Import device API endpoints
try:
    from device_api_endpoints import device_api_bp
    app.register_blueprint(device_api_bp)
    logger.info("✅ Device API endpoints registered")
except ImportError as e:
    logger.error(f"❌ Could not import device API endpoints: {e}")

@app.route('/test')
def test():
    return jsonify({
        'message': 'Test server is working',
        'device_manager_available': device_manager is not None
    })

@app.route('/api/devices/test')
def test_devices():
    """Test device endpoint"""
    if device_manager:
        devices = device_manager.get_all_devices()
        return jsonify({
            'success': True,
            'message': 'Device manager is working',
            'device_count': len(devices)
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Device manager not available'
        }), 500

if __name__ == '__main__':
    print("🧪 Starting test server...")
    print("Available routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.methods} {rule.rule}")
    
    app.run(debug=True, port=5001)