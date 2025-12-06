#!/usr/bin/env python3
"""
Multi-Hospital Network API Endpoints
RESTful API for managing distributed PACS across South African healthcare facilities
"""

from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import json
from datetime import datetime
from multi_hospital_network import MultiHospitalNetworkManager, SA_HEALTHCARE_PROVINCES, SA_HOSPITAL_TYPES, SA_EMERGENCY_TYPES

# Create Blueprint
multi_hospital_bp = Blueprint('multi_hospital', __name__, url_prefix='/api/multi-hospital')

# Initialize network manager
network_manager = MultiHospitalNetworkManager()

def require_admin_auth(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Implementation would check admin authentication
        # For now, we'll assume authentication is handled elsewhere
        return f(*args, **kwargs)
    return decorated_function

def require_hospital_auth(f):
    """Decorator to require hospital authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Implementation would check hospital API key authentication
        return f(*args, **kwargs)
    return decorated_function

@multi_hospital_bp.route('/hospitals', methods=['GET'])
@require_admin_auth
def get_hospitals():
    """Get list of all hospitals in the network"""
    try:
        import sqlite3
        conn = sqlite3.connect(network_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, type, province, city, status, last_sync, created_at
            FROM hospitals
            ORDER BY name
        ''')
        
        hospitals = []
        for row in cursor.fetchall():
            hospitals.append({
                'id': row[0],
                'name': row[1],
                'type': row[2],
                'province': row[3],
                'city': row[4],
                'status': row[5],
                'last_sync': row[6],
                'created_at': row[7]
            })
            
        conn.close()
        
        return jsonify({
            'success': True,
            'hospitals': hospitals,
            'total': len(hospitals)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@multi_hospital_bp.route('/hospitals', methods=['POST'])
@require_admin_auth
def register_hospital():
    """Register a new hospital in the network"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'type', 'province', 'city', 'api_endpoint']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
                
        # Validate province
        if data['province'] not in SA_HEALTHCARE_PROVINCES:
            return jsonify({'success': False, 'error': 'Invalid province'}), 400
            
        # Validate hospital type
        if data['type'] not in SA_HOSPITAL_TYPES:
            return jsonify({'success': False, 'error': 'Invalid hospital type'}), 400
            
        hospital_id = network_manager.register_hospital(data)
        
        return jsonify({
            'success': True,
            'hospital_id': hospital_id,
            'message': 'Hospital registered successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@multi_hospital_bp.route('/hospitals/<hospital_id>', methods=['GET'])
@require_admin_auth
def get_hospital_details(hospital_id):
    """Get detailed information about a specific hospital"""
    try:
        import sqlite3
        conn = sqlite3.connect(network_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM hospitals WHERE id = ?', (hospital_id,))
        hospital = cursor.fetchone()
        
        if not hospital:
            return jsonify({'success': False, 'error': 'Hospital not found'}), 404
            
        # Get connection count
        cursor.execute('''
            SELECT COUNT(*) FROM hospital_connections 
            WHERE (hospital_a_id = ? OR hospital_b_id = ?) AND status = 'active'
        ''', (hospital_id, hospital_id))
        connection_count = cursor.fetchone()[0]
        
        # Get shared studies count
        cursor.execute('''
            SELECT COUNT(*) FROM shared_studies 
            WHERE (source_hospital_id = ? OR target_hospital_id = ?) AND status = 'active'
        ''', (hospital_id, hospital_id))
        shared_studies_count = cursor.fetchone()[0]
        
        conn.close()
        
        hospital_data = {
            'id': hospital[0],
            'name': hospital[1],
            'type': hospital[2],
            'province': hospital[3],
            'city': hospital[4],
            'address': hospital[5],
            'contact_person': hospital[6],
            'phone': hospital[7],
            'email': hospital[8],
            'api_endpoint': hospital[9],
            'status': hospital[11],
            'last_sync': hospital[12],
            'created_at': hospital[13],
            'updated_at': hospital[14],
            'connection_count': connection_count,
            'shared_studies_count': shared_studies_count
        }
        
        return jsonify({
            'success': True,
            'hospital': hospital_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@multi_hospital_bp.route('/connections', methods=['POST'])
@require_admin_auth
def create_hospital_connection():
    """Create a connection between two hospitals"""
    try:
        data = request.get_json()
        
        required_fields = ['hospital_a_id', 'hospital_b_id', 'connection_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
                
        valid_connection_types = ['full', 'referral_only', 'emergency_only']
        if data['connection_type'] not in valid_connection_types:
            return jsonify({'success': False, 'error': 'Invalid connection type'}), 400
            
        connection_id = network_manager.create_hospital_connection(
            data['hospital_a_id'],
            data['hospital_b_id'],
            data['connection_type'],
            data.get('permissions')
        )
        
        return jsonify({
            'success': True,
            'connection_id': connection_id,
            'message': 'Hospital connection created successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@multi_hospital_bp.route('/share-study', methods=['POST'])
@require_hospital_auth
def share_study():
    """Share a study with another hospital"""
    try:
        data = request.get_json()
        
        required_fields = ['study_id', 'source_hospital_id', 'target_hospital_id', 
                          'patient_id', 'sharing_reason', 'shared_by_user_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
                
        valid_sharing_reasons = ['referral', 'consultation', 'emergency', 'second_opinion']
        if data['sharing_reason'] not in valid_sharing_reasons:
            return jsonify({'success': False, 'error': 'Invalid sharing reason'}), 400
            
        share_id = network_manager.share_study_with_hospital(
            data['study_id'],
            data['source_hospital_id'],
            data['target_hospital_id'],
            data['patient_id'],
            data['sharing_reason'],
            data['shared_by_user_id'],
            data.get('expires_hours', 24)
        )
        
        return jsonify({
            'success': True,
            'share_id': share_id,
            'message': 'Study shared successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@multi_hospital_bp.route('/emergency-access', methods=['POST'])
@require_hospital_auth
def request_emergency_access():
    """Request emergency access to patient data"""
    try:
        data = request.get_json()
        
        required_fields = ['requesting_hospital_id', 'patient_id', 'accessing_user_id', 
                          'emergency_type', 'justification']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
                
        if data['emergency_type'] not in SA_EMERGENCY_TYPES:
            return jsonify({'success': False, 'error': 'Invalid emergency type'}), 400
            
        access_id = network_manager.request_emergency_access(
            data['requesting_hospital_id'],
            data['patient_id'],
            data['accessing_user_id'],
            data['emergency_type'],
            data['justification']
        )
        
        return jsonify({
            'success': True,
            'access_id': access_id,
            'message': 'Emergency access granted',
            'expires_in_minutes': 60
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@multi_hospital_bp.route('/sync/<hospital_id>', methods=['POST'])
@require_admin_auth
def sync_hospital(hospital_id):
    """Synchronize data with a specific hospital"""
    try:
        data = request.get_json() or {}
        sync_type = data.get('sync_type', 'incremental')
        
        if sync_type not in ['full', 'incremental']:
            return jsonify({'success': False, 'error': 'Invalid sync type'}), 400
            
        result = network_manager.sync_with_hospital(hospital_id, sync_type)
        
        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 500
            
        return jsonify({
            'success': True,
            'sync_result': result,
            'message': f'{sync_type.title()} sync completed successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@multi_hospital_bp.route('/network-status', methods=['GET'])
@require_admin_auth
def get_network_status():
    """Get overall network status and statistics"""
    try:
        status = network_manager.get_network_status()
        
        return jsonify({
            'success': True,
            'network_status': status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@multi_hospital_bp.route('/shared-studies', methods=['GET'])
@require_hospital_auth
def get_shared_studies():
    """Get list of shared studies for a hospital"""
    try:
        hospital_id = request.args.get('hospital_id')
        if not hospital_id:
            return jsonify({'success': False, 'error': 'Hospital ID required'}), 400
            
        import sqlite3
        conn = sqlite3.connect(network_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ss.*, h1.name as source_hospital_name, h2.name as target_hospital_name
            FROM shared_studies ss
            JOIN hospitals h1 ON ss.source_hospital_id = h1.id
            JOIN hospitals h2 ON ss.target_hospital_id = h2.id
            WHERE (ss.source_hospital_id = ? OR ss.target_hospital_id = ?)
            AND ss.status = 'active'
            AND ss.expires_at > datetime('now')
            ORDER BY ss.created_at DESC
        ''', (hospital_id, hospital_id))
        
        shared_studies = []
        for row in cursor.fetchall():
            shared_studies.append({
                'id': row[0],
                'study_id': row[1],
                'source_hospital_id': row[2],
                'target_hospital_id': row[3],
                'patient_id': row[4],
                'study_date': row[5],
                'modality': row[6],
                'description': row[7],
                'sharing_reason': row[8],
                'shared_by_user_id': row[9],
                'access_level': row[10],
                'expires_at': row[11],
                'created_at': row[13],
                'source_hospital_name': row[14],
                'target_hospital_name': row[15]
            })
            
        conn.close()
        
        return jsonify({
            'success': True,
            'shared_studies': shared_studies,
            'total': len(shared_studies)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@multi_hospital_bp.route('/emergency-access-logs', methods=['GET'])
@require_admin_auth
def get_emergency_access_logs():
    """Get emergency access logs for audit purposes"""
    try:
        import sqlite3
        conn = sqlite3.connect(network_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT eal.*, h.name as hospital_name
            FROM emergency_access_logs eal
            JOIN hospitals h ON eal.requesting_hospital_id = h.id
            ORDER BY eal.created_at DESC
            LIMIT 100
        ''')
        
        access_logs = []
        for row in cursor.fetchall():
            access_logs.append({
                'id': row[0],
                'requesting_hospital_id': row[1],
                'patient_id': row[2],
                'accessing_user_id': row[3],
                'emergency_type': row[4],
                'justification': row[5],
                'accessed_studies': json.loads(row[6]) if row[6] else [],
                'approved_by': row[7],
                'access_duration_minutes': row[8],
                'created_at': row[9],
                'expires_at': row[10],
                'hospital_name': row[11]
            })
            
        conn.close()
        
        return jsonify({
            'success': True,
            'emergency_access_logs': access_logs,
            'total': len(access_logs)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@multi_hospital_bp.route('/provinces', methods=['GET'])
def get_sa_provinces():
    """Get list of South African provinces"""
    return jsonify({
        'success': True,
        'provinces': SA_HEALTHCARE_PROVINCES
    })

@multi_hospital_bp.route('/hospital-types', methods=['GET'])
def get_hospital_types():
    """Get list of hospital types"""
    return jsonify({
        'success': True,
        'hospital_types': SA_HOSPITAL_TYPES
    })

@multi_hospital_bp.route('/emergency-types', methods=['GET'])
def get_emergency_types():
    """Get list of emergency types"""
    return jsonify({
        'success': True,
        'emergency_types': SA_EMERGENCY_TYPES
    })

# Error handlers
@multi_hospital_bp.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@multi_hospital_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == "__main__":
    # Test the endpoints
    from flask import Flask
    
    app = Flask(__name__)
    app.register_blueprint(multi_hospital_bp)
    
    print("Multi-Hospital Network API endpoints registered:")
    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith('multi_hospital'):
            print(f"  {rule.methods} {rule.rule}")