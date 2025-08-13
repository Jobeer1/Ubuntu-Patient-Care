#!/usr/bin/env python3
"""
Telemedicine API Endpoints
RESTful API for managing remote consultations and diagnosis
"""

from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import json
from datetime import datetime, timedelta
from telemedicine_integration import TelemedicineManager, ConsultationType, ConsultationStatus, SA_MEDICAL_SPECIALTIES

# Create Blueprint
telemedicine_bp = Blueprint('telemedicine', __name__, url_prefix='/api/telemedicine')

# Initialize telemedicine manager
telemedicine_manager = TelemedicineManager()

def require_auth(f):
    """Decorator to require user authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Implementation would check user authentication
        # For now, we'll assume authentication is handled elsewhere
        return f(*args, **kwargs)
    return decorated_function

def require_doctor_auth(f):
    """Decorator to require doctor-level authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Implementation would check doctor authentication
        return f(*args, **kwargs)
    return decorated_function

@telemedicine_bp.route('/consultations', methods=['POST'])
@require_doctor_auth
def schedule_consultation():
    """Schedule a new telemedicine consultation"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = [
            'patient_id', 'study_id', 'consultation_type', 'scheduled_time',
            'requesting_doctor_id', 'consulting_specialist_id', 'hospital_id',
            'specialist_hospital_id', 'title', 'clinical_question'
        ]
        
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
                
        # Validate consultation type
        valid_types = [t.value for t in ConsultationType]
        if data['consultation_type'] not in valid_types:
            return jsonify({'success': False, 'error': 'Invalid consultation type'}), 400
            
        # Parse scheduled time
        try:
            data['scheduled_time'] = datetime.fromisoformat(data['scheduled_time'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid scheduled_time format'}), 400
            
        consultation_id = telemedicine_manager.schedule_consultation(data)
        
        return jsonify({
            'success': True,
            'consultation_id': consultation_id,
            'message': 'Consultation scheduled successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@telemedicine_bp.route('/consultations/<consultation_id>/start', methods=['POST'])
@require_doctor_auth
def start_consultation(consultation_id):
    """Start a telemedicine consultation"""
    try:
        data = request.get_json()
        meeting_room_id = data.get('meeting_room_id', f'room_{consultation_id}')
        
        success = telemedicine_manager.start_consultation(consultation_id, meeting_room_id)
        
        if success:
            return jsonify({
                'success': True,
                'meeting_room_id': meeting_room_id,
                'message': 'Consultation started successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to start consultation'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@telemedicine_bp.route('/consultations/<consultation_id>/end', methods=['POST'])
@require_doctor_auth
def end_consultation(consultation_id):
    """End a telemedicine consultation"""
    try:
        data = request.get_json()
        
        success = telemedicine_manager.end_consultation(
            consultation_id=consultation_id,
            consultation_notes=data.get('consultation_notes'),
            diagnosis=data.get('diagnosis'),
            recommendations=data.get('recommendations'),
            follow_up_required=data.get('follow_up_required', False),
            follow_up_date=datetime.fromisoformat(data['follow_up_date']) if data.get('follow_up_date') else None
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Consultation ended successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to end consultation'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@telemedicine_bp.route('/consultations/<consultation_id>/join', methods=['POST'])
@require_auth
def join_consultation(consultation_id):
    """Join a telemedicine consultation"""
    try:
        data = request.get_json()
        
        required_fields = ['user_id', 'username', 'role']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
                
        participant_id = telemedicine_manager.join_consultation(
            consultation_id=consultation_id,
            user_id=data['user_id'],
            username=data['username'],
            role=data['role'],
            hospital_id=data.get('hospital_id')
        )
        
        return jsonify({
            'success': True,
            'participant_id': participant_id,
            'message': 'Joined consultation successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@telemedicine_bp.route('/consultations/<consultation_id>/leave', methods=['POST'])
@require_auth
def leave_consultation(consultation_id):
    """Leave a telemedicine consultation"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID required'}), 400
            
        telemedicine_manager.leave_consultation(consultation_id, user_id)
        
        return jsonify({
            'success': True,
            'message': 'Left consultation successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@telemedicine_bp.route('/consultations/<consultation_id>', methods=['GET'])
@require_auth
def get_consultation_details(consultation_id):
    """Get detailed consultation information"""
    try:
        consultation_data = telemedicine_manager.get_consultation_details(consultation_id)
        
        if consultation_data:
            return jsonify({
                'success': True,
                'consultation_data': consultation_data
            })
        else:
            return jsonify({'success': False, 'error': 'Consultation not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@telemedicine_bp.route('/consultations/<consultation_id>/share-image', methods=['POST'])
@require_doctor_auth
def share_image_in_consultation(consultation_id):
    """Share an image during consultation"""
    try:
        data = request.get_json()
        
        required_fields = ['study_id', 'shared_by_user_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
                
        share_id = telemedicine_manager.share_image_in_consultation(
            consultation_id=consultation_id,
            study_id=data['study_id'],
            shared_by_user_id=data['shared_by_user_id'],
            series_id=data.get('series_id'),
            instance_id=data.get('instance_id'),
            annotation_data=data.get('annotation_data'),
            measurement_data=data.get('measurement_data')
        )
        
        return jsonify({
            'success': True,
            'share_id': share_id,
            'message': 'Image shared successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@telemedicine_bp.route('/consultations/<consultation_id>/messages', methods=['POST'])
@require_auth
def send_consultation_message(consultation_id):
    """Send a message during consultation"""
    try:
        data = request.get_json()
        
        required_fields = ['user_id', 'username', 'message']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
                
        message_id = telemedicine_manager.send_consultation_message(
            consultation_id=consultation_id,
            user_id=data['user_id'],
            username=data['username'],
            message=data['message'],
            message_type=data.get('message_type', 'text'),
            reference_data=data.get('reference_data')
        )
        
        return jsonify({
            'success': True,
            'message_id': message_id,
            'message': 'Message sent successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@telemedicine_bp.route('/specialists/available', methods=['GET'])
@require_doctor_auth
def find_available_specialists():
    """Find available specialists for consultation"""
    try:
        specialty = request.args.get('specialty')
        consultation_type = request.args.get('consultation_type')
        preferred_time = request.args.get('preferred_time')
        duration_minutes = request.args.get('duration_minutes', 30, type=int)
        
        if not all([specialty, consultation_type, preferred_time]):
            return jsonify({
                'success': False, 
                'error': 'specialty, consultation_type, and preferred_time are required'
            }), 400
            
        try:
            preferred_time = datetime.fromisoformat(preferred_time.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid preferred_time format'}), 400
            
        specialists = telemedicine_manager.find_available_specialists(
            specialty, consultation_type, preferred_time, duration_minutes
        )
        
        return jsonify({
            'success': True,
            'specialists': specialists,
            'total': len(specialists)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@telemedicine_bp.route('/consultations', methods=['GET'])
@require_auth
def get_consultations():
    """Get list of consultations"""
    try:
        user_id = request.args.get('user_id')
        status = request.args.get('status')
        consultation_type = request.args.get('consultation_type')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        limit = request.args.get('limit', 50, type=int)
        
        import sqlite3
        conn = sqlite3.connect(telemedicine_manager.db_path)
        cursor = conn.cursor()
        
        # Build query
        query = '''
            SELECT tc.*, 
                   rd.username as requesting_doctor_name,
                   cs.username as consulting_specialist_name,
                   h1.name as hospital_name,
                   h2.name as specialist_hospital_name
            FROM telemedicine_consultations tc
            LEFT JOIN users rd ON tc.requesting_doctor_id = rd.user_id
            LEFT JOIN users cs ON tc.consulting_specialist_id = cs.user_id
            LEFT JOIN hospitals h1 ON tc.hospital_id = h1.id
            LEFT JOIN hospitals h2 ON tc.specialist_hospital_id = h2.id
            WHERE 1=1
        '''
        
        params = []
        
        if user_id:
            query += ' AND (tc.requesting_doctor_id = ? OR tc.consulting_specialist_id = ?)'
            params.extend([user_id, user_id])
            
        if status:
            query += ' AND tc.status = ?'
            params.append(status)
            
        if consultation_type:
            query += ' AND tc.consultation_type = ?'
            params.append(consultation_type)
            
        if date_from:
            query += ' AND DATE(tc.scheduled_time) >= DATE(?)'
            params.append(date_from)
            
        if date_to:
            query += ' AND DATE(tc.scheduled_time) <= DATE(?)'
            params.append(date_to)
            
        query += ' ORDER BY tc.scheduled_time DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        
        consultations = []
        for row in cursor.fetchall():
            consultations.append({
                'consultation_id': row[0],
                'patient_id': row[1],
                'study_id': row[2],
                'consultation_type': row[3],
                'status': row[4],
                'scheduled_time': row[5],
                'duration_minutes': row[6],
                'requesting_doctor_id': row[7],
                'consulting_specialist_id': row[8],
                'hospital_id': row[9],
                'specialist_hospital_id': row[10],
                'title': row[11],
                'description': row[12],
                'clinical_question': row[13],
                'urgency_level': row[14],
                'created_at': row[15],
                'started_at': row[16],
                'ended_at': row[17],
                'requesting_doctor_name': row[24],
                'consulting_specialist_name': row[25],
                'hospital_name': row[26],
                'specialist_hospital_name': row[27]
            })
            
        conn.close()
        
        return jsonify({
            'success': True,
            'consultations': consultations,
            'total': len(consultations)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@telemedicine_bp.route('/emergency-queue', methods=['GET'])
@require_auth
def get_emergency_queue():
    """Get emergency consultation queue"""
    try:
        import sqlite3
        conn = sqlite3.connect(telemedicine_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT eq.*, tc.title, tc.patient_id, tc.urgency_level,
                   tc.requesting_doctor_id, tc.clinical_question,
                   rd.username as requesting_doctor_name
            FROM emergency_consultation_queue eq
            JOIN telemedicine_consultations tc ON eq.consultation_id = tc.consultation_id
            LEFT JOIN users rd ON tc.requesting_doctor_id = rd.user_id
            WHERE eq.assigned_at IS NULL
            ORDER BY eq.priority_score DESC, eq.created_at ASC
        ''')
        
        queue_items = []
        for row in cursor.fetchall():
            queue_items.append({
                'queue_id': row[0],
                'consultation_id': row[1],
                'priority_score': row[2],
                'triage_notes': row[3],
                'estimated_wait_minutes': row[4],
                'queue_position': row[5],
                'created_at': row[6],
                'title': row[8],
                'patient_id': row[9],
                'urgency_level': row[10],
                'requesting_doctor_id': row[11],
                'clinical_question': row[12],
                'requesting_doctor_name': row[13]
            })
            
        conn.close()
        
        return jsonify({
            'success': True,
            'queue_items': queue_items,
            'total': len(queue_items)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@telemedicine_bp.route('/consultations/<consultation_id>/feedback', methods=['POST'])
@require_auth
def submit_consultation_feedback(consultation_id):
    """Submit feedback for a consultation"""
    try:
        data = request.get_json()
        
        required_fields = ['reviewer_user_id', 'reviewer_role', 'rating']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
                
        # Validate ratings
        rating = data.get('rating')
        if not (1 <= rating <= 5):
            return jsonify({'success': False, 'error': 'Rating must be between 1 and 5'}), 400
            
        import sqlite3
        conn = sqlite3.connect(telemedicine_manager.db_path)
        cursor = conn.cursor()
        
        feedback_id = str(uuid.uuid4())
        
        cursor.execute('''
            INSERT INTO consultation_feedback (
                feedback_id, consultation_id, reviewer_user_id, reviewer_role,
                rating, technical_quality_rating, clinical_value_rating,
                feedback_text, would_recommend
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            feedback_id, consultation_id, data['reviewer_user_id'], data['reviewer_role'],
            data['rating'], data.get('technical_quality_rating'), data.get('clinical_value_rating'),
            data.get('feedback_text'), data.get('would_recommend')
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'feedback_id': feedback_id,
            'message': 'Feedback submitted successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@telemedicine_bp.route('/statistics', methods=['GET'])
@require_auth
def get_telemedicine_statistics():
    """Get telemedicine usage statistics"""
    try:
        import sqlite3
        conn = sqlite3.connect(telemedicine_manager.db_path)
        cursor = conn.cursor()
        
        # Total consultations
        cursor.execute('SELECT COUNT(*) FROM telemedicine_consultations')
        total_consultations = cursor.fetchone()[0]
        
        # Consultations by status
        cursor.execute('''
            SELECT status, COUNT(*) 
            FROM telemedicine_consultations 
            GROUP BY status
        ''')
        consultations_by_status = dict(cursor.fetchall())
        
        # Consultations by type
        cursor.execute('''
            SELECT consultation_type, COUNT(*) 
            FROM telemedicine_consultations 
            GROUP BY consultation_type
        ''')
        consultations_by_type = dict(cursor.fetchall())
        
        # Average consultation duration
        cursor.execute('''
            SELECT AVG(
                CASE 
                    WHEN started_at IS NOT NULL AND ended_at IS NOT NULL 
                    THEN (julianday(ended_at) - julianday(started_at)) * 24 * 60
                    ELSE duration_minutes
                END
            ) FROM telemedicine_consultations
            WHERE status = 'completed'
        ''')
        avg_duration = cursor.fetchone()[0] or 0
        
        # Recent activity (last 30 days)
        cursor.execute('''
            SELECT COUNT(*) FROM telemedicine_consultations
            WHERE created_at >= datetime('now', '-30 days')
        ''')
        recent_consultations = cursor.fetchone()[0]
        
        # Emergency queue size
        cursor.execute('''
            SELECT COUNT(*) FROM emergency_consultation_queue
            WHERE assigned_at IS NULL
        ''')
        emergency_queue_size = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_consultations': total_consultations,
                'consultations_by_status': consultations_by_status,
                'consultations_by_type': consultations_by_type,
                'average_duration_minutes': round(avg_duration, 1),
                'recent_consultations_30_days': recent_consultations,
                'emergency_queue_size': emergency_queue_size
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@telemedicine_bp.route('/specialties', methods=['GET'])
def get_medical_specialties():
    """Get list of medical specialties"""
    return jsonify({
        'success': True,
        'specialties': SA_MEDICAL_SPECIALTIES
    })

@telemedicine_bp.route('/consultation-types', methods=['GET'])
def get_consultation_types():
    """Get list of consultation types"""
    return jsonify({
        'success': True,
        'consultation_types': [t.value for t in ConsultationType]
    })

# Error handlers
@telemedicine_bp.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@telemedicine_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == "__main__":
    # Test the endpoints
    from flask import Flask
    
    app = Flask(__name__)
    app.register_blueprint(telemedicine_bp)
    
    print("Telemedicine API endpoints registered:")
    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith('telemedicine'):
            print(f"  {rule.methods} {rule.rule}")