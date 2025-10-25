#!/usr/bin/env python3
"""
Real-time Collaboration API Endpoints
RESTful API for managing multi-user DICOM viewing sessions
"""

from flask import Blueprint, request, jsonify, current_app
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from functools import wraps
import json
from datetime import datetime
from realtime_collaboration import RealtimeCollaborationManager, CollaborationEventType

# Create Blueprint
collaboration_bp = Blueprint('collaboration', __name__, url_prefix='/api/collaboration')

# Initialize collaboration manager
collaboration_manager = RealtimeCollaborationManager()

def require_auth(f):
    """Decorator to require user authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Implementation would check user authentication
        # For now, we'll assume authentication is handled elsewhere
        return f(*args, **kwargs)
    return decorated_function

@collaboration_bp.route('/sessions', methods=['POST'])
@require_auth
def create_session():
    """Create a new collaboration session"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['study_id', 'created_by', 'title']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
                
        session_id = collaboration_manager.create_collaboration_session(
            study_id=data['study_id'],
            created_by=data['created_by'],
            title=data['title'],
            description=data.get('description'),
            max_participants=data.get('max_participants', 10)
        )
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Collaboration session created successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@collaboration_bp.route('/sessions/<session_id>/join', methods=['POST'])
@require_auth
def join_session(session_id):
    """Join a collaboration session"""
    try:
        data = request.get_json()
        
        required_fields = ['user_id', 'username', 'role']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
                
        success = collaboration_manager.join_session(
            session_id=session_id,
            user_id=data['user_id'],
            username=data['username'],
            role=data['role'],
            hospital_id=data.get('hospital_id')
        )
        
        if success:
            session_data = collaboration_manager.get_session_data(session_id)
            return jsonify({
                'success': True,
                'message': 'Joined session successfully',
                'session_data': session_data
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to join session (session full or not found)'
            }), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@collaboration_bp.route('/sessions/<session_id>/leave', methods=['POST'])
@require_auth
def leave_session(session_id):
    """Leave a collaboration session"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID required'}), 400
            
        collaboration_manager.leave_session(session_id, user_id)
        
        return jsonify({
            'success': True,
            'message': 'Left session successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@collaboration_bp.route('/sessions/<session_id>', methods=['GET'])
@require_auth
def get_session_data(session_id):
    """Get complete session data"""
    try:
        session_data = collaboration_manager.get_session_data(session_id)
        
        if session_data:
            return jsonify({
                'success': True,
                'session_data': session_data
            })
        else:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@collaboration_bp.route('/sessions/<session_id>/annotations', methods=['POST'])
@require_auth
def add_annotation(session_id):
    """Add an annotation to the session"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        annotation_data = data.get('annotation')
        
        if not user_id or not annotation_data:
            return jsonify({'success': False, 'error': 'User ID and annotation data required'}), 400
            
        annotation_id = collaboration_manager.add_annotation(
            session_id, user_id, annotation_data
        )
        
        return jsonify({
            'success': True,
            'annotation_id': annotation_id,
            'message': 'Annotation added successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@collaboration_bp.route('/sessions/<session_id>/measurements', methods=['POST'])
@require_auth
def add_measurement(session_id):
    """Add a measurement to the session"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        measurement_data = data.get('measurement')
        
        if not user_id or not measurement_data:
            return jsonify({'success': False, 'error': 'User ID and measurement data required'}), 400
            
        measurement_id = collaboration_manager.add_measurement(
            session_id, user_id, measurement_data
        )
        
        return jsonify({
            'success': True,
            'measurement_id': measurement_id,
            'message': 'Measurement added successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@collaboration_bp.route('/sessions/<session_id>/chat', methods=['POST'])
@require_auth
def send_chat_message(session_id):
    """Send a chat message in the session"""
    try:
        data = request.get_json()
        
        required_fields = ['user_id', 'username', 'message']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
                
        message_id = collaboration_manager.send_chat_message(
            session_id=session_id,
            user_id=data['user_id'],
            username=data['username'],
            message=data['message'],
            message_type=data.get('message_type', 'text'),
            reference_id=data.get('reference_id')
        )
        
        return jsonify({
            'success': True,
            'message_id': message_id,
            'message': 'Chat message sent successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@collaboration_bp.route('/sessions/<session_id>/viewport', methods=['POST'])
@require_auth
def update_viewport(session_id):
    """Update viewport (presenter mode)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        viewport_data = data.get('viewport')
        
        if not user_id or not viewport_data:
            return jsonify({'success': False, 'error': 'User ID and viewport data required'}), 400
            
        collaboration_manager.update_viewport(session_id, user_id, viewport_data)
        
        return jsonify({
            'success': True,
            'message': 'Viewport updated successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@collaboration_bp.route('/sessions', methods=['GET'])
@require_auth
def get_active_sessions():
    """Get list of active collaboration sessions"""
    try:
        import sqlite3
        conn = sqlite3.connect(collaboration_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT cs.*, COUNT(sp.user_id) as participant_count
            FROM collaboration_sessions cs
            LEFT JOIN session_participants sp ON cs.session_id = sp.session_id 
                AND sp.left_at IS NULL
            WHERE cs.is_active = 1
            GROUP BY cs.session_id
            ORDER BY cs.created_at DESC
        ''')
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                'session_id': row[0],
                'study_id': row[1],
                'created_by': row[2],
                'title': row[3],
                'description': row[4],
                'max_participants': row[5],
                'is_active': bool(row[6]),
                'created_at': row[7],
                'participant_count': row[9]
            })
            
        conn.close()
        
        return jsonify({
            'success': True,
            'sessions': sessions,
            'total': len(sessions)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@collaboration_bp.route('/sessions/<session_id>/participants', methods=['GET'])
@require_auth
def get_session_participants(session_id):
    """Get list of session participants"""
    try:
        import sqlite3
        conn = sqlite3.connect(collaboration_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, username, role, hospital_id, avatar_color, 
                   is_presenter, joined_at
            FROM session_participants
            WHERE session_id = ? AND left_at IS NULL
            ORDER BY joined_at
        ''', (session_id,))
        
        participants = []
        for row in cursor.fetchall():
            participants.append({
                'user_id': row[0],
                'username': row[1],
                'role': row[2],
                'hospital_id': row[3],
                'avatar_color': row[4],
                'is_presenter': bool(row[5]),
                'joined_at': row[6]
            })
            
        conn.close()
        
        return jsonify({
            'success': True,
            'participants': participants,
            'total': len(participants)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@collaboration_bp.route('/sessions/<session_id>/annotations', methods=['GET'])
@require_auth
def get_session_annotations(session_id):
    """Get all annotations for a session"""
    try:
        import sqlite3
        conn = sqlite3.connect(collaboration_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ca.*, sp.username, sp.avatar_color
            FROM collaboration_annotations ca
            JOIN session_participants sp ON ca.user_id = sp.user_id 
                AND ca.session_id = sp.session_id
            WHERE ca.session_id = ? AND ca.is_temporary = 0
            ORDER BY ca.created_at
        ''', (session_id,))
        
        annotations = []
        for row in cursor.fetchall():
            annotations.append({
                'annotation_id': row[0],
                'user_id': row[2],
                'username': row[12],
                'avatar_color': row[13],
                'study_id': row[3],
                'series_id': row[4],
                'instance_id': row[5],
                'type': row[6],
                'coordinates': json.loads(row[7]),
                'text': row[8],
                'style': json.loads(row[9]) if row[9] else {},
                'created_at': row[11],
                'updated_at': row[12]
            })
            
        conn.close()
        
        return jsonify({
            'success': True,
            'annotations': annotations,
            'total': len(annotations)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@collaboration_bp.route('/sessions/<session_id>/measurements', methods=['GET'])
@require_auth
def get_session_measurements(session_id):
    """Get all measurements for a session"""
    try:
        import sqlite3
        conn = sqlite3.connect(collaboration_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT cm.*, sp.username, sp.avatar_color
            FROM collaboration_measurements cm
            JOIN session_participants sp ON cm.user_id = sp.user_id 
                AND cm.session_id = sp.session_id
            WHERE cm.session_id = ?
            ORDER BY cm.created_at
        ''', (session_id,))
        
        measurements = []
        for row in cursor.fetchall():
            measurements.append({
                'measurement_id': row[0],
                'user_id': row[2],
                'username': row[10],
                'avatar_color': row[11],
                'study_id': row[3],
                'type': row[4],
                'coordinates': json.loads(row[5]),
                'value': row[6],
                'unit': row[7],
                'label': row[8],
                'created_at': row[9]
            })
            
        conn.close()
        
        return jsonify({
            'success': True,
            'measurements': measurements,
            'total': len(measurements)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@collaboration_bp.route('/sessions/<session_id>/chat', methods=['GET'])
@require_auth
def get_chat_history(session_id):
    """Get chat history for a session"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        import sqlite3
        conn = sqlite3.connect(collaboration_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT message_id, user_id, username, message, message_type,
                   reference_id, timestamp
            FROM collaboration_chat
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (session_id, limit))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'message_id': row[0],
                'user_id': row[1],
                'username': row[2],
                'message': row[3],
                'message_type': row[4],
                'reference_id': row[5],
                'timestamp': row[6]
            })
            
        conn.close()
        
        return jsonify({
            'success': True,
            'messages': list(reversed(messages)),
            'total': len(messages)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@collaboration_bp.route('/sessions/<session_id>/presenter', methods=['POST'])
@require_auth
def change_presenter(session_id):
    """Change the session presenter"""
    try:
        data = request.get_json()
        new_presenter_id = data.get('user_id')
        
        if not new_presenter_id:
            return jsonify({'success': False, 'error': 'User ID required'}), 400
            
        import sqlite3
        conn = sqlite3.connect(collaboration_manager.db_path)
        cursor = conn.cursor()
        
        # Remove presenter status from all users
        cursor.execute('''
            UPDATE session_participants 
            SET is_presenter = 0 
            WHERE session_id = ?
        ''', (session_id,))
        
        # Set new presenter
        cursor.execute('''
            UPDATE session_participants 
            SET is_presenter = 1 
            WHERE session_id = ? AND user_id = ?
        ''', (session_id, new_presenter_id))
        
        conn.commit()
        conn.close()
        
        # Update in-memory session
        if session_id in collaboration_manager.active_sessions:
            session = collaboration_manager.active_sessions[session_id]
            for participant in session.participants:
                participant.is_presenter = (participant.user_id == new_presenter_id)
        
        return jsonify({
            'success': True,
            'message': 'Presenter changed successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# WebSocket events for real-time communication
def init_socketio_events(socketio):
    """Initialize SocketIO events for real-time collaboration"""
    
    @socketio.on('join_collaboration_session')
    def on_join_session(data):
        session_id = data['session_id']
        user_id = data['user_id']
        
        join_room(session_id)
        
        # Send current session data to the user
        session_data = collaboration_manager.get_session_data(session_id)
        if session_data:
            emit('session_data', session_data)
            
    @socketio.on('leave_collaboration_session')
    def on_leave_session(data):
        session_id = data['session_id']
        user_id = data['user_id']
        
        leave_room(session_id)
        collaboration_manager.leave_session(session_id, user_id)
        
    @socketio.on('cursor_move')
    def on_cursor_move(data):
        session_id = data['session_id']
        user_id = data['user_id']
        cursor_data = data['cursor_data']
        
        # Broadcast cursor position to other users in the session
        emit('cursor_update', {
            'user_id': user_id,
            'cursor_data': cursor_data
        }, room=session_id, include_self=False)
        
    @socketio.on('viewport_change')
    def on_viewport_change(data):
        session_id = data['session_id']
        user_id = data['user_id']
        viewport_data = data['viewport_data']
        
        # Check if user is presenter
        if session_id in collaboration_manager.active_sessions:
            session = collaboration_manager.active_sessions[session_id]
            user = next((p for p in session.participants if p.user_id == user_id), None)
            
            if user and user.is_presenter:
                # Broadcast viewport change to all participants
                emit('viewport_update', {
                    'user_id': user_id,
                    'viewport_data': viewport_data
                }, room=session_id, include_self=False)
                
    @socketio.on('annotation_added')
    def on_annotation_added(data):
        session_id = data['session_id']
        
        # Broadcast annotation to all participants
        emit('annotation_update', data, room=session_id, include_self=False)
        
    @socketio.on('measurement_added')
    def on_measurement_added(data):
        session_id = data['session_id']
        
        # Broadcast measurement to all participants
        emit('measurement_update', data, room=session_id, include_self=False)
        
    @socketio.on('chat_message')
    def on_chat_message(data):
        session_id = data['session_id']
        
        # Broadcast chat message to all participants
        emit('chat_update', data, room=session_id, include_self=False)

# Error handlers
@collaboration_bp.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@collaboration_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == "__main__":
    # Test the endpoints
    from flask import Flask
    
    app = Flask(__name__)
    app.register_blueprint(collaboration_bp)
    
    print("Real-time Collaboration API endpoints registered:")
    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith('collaboration'):
            print(f"  {rule.methods} {rule.rule}")