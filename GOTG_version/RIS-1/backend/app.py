"""
GOTG-RIS Backend: Lightweight Flask API for offline-first RIS
Optimized for low-end devices, instant local persistence, smart sync
"""

import os
import json
import sqlite3
import hashlib
import gzip
import io
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Any, Tuple

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'gotg-ris-dev-key-change-in-production')
app.config['DATABASE'] = os.getenv('DB_PATH', './ris.db')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', './uploads')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max upload

CORS(app, resources={r"/api/*": {"origins": "*"}})

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# =============================================
# Database Helper Functions
# =============================================

def get_db():
    """Get database connection with row factory"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging for concurrent access
    conn.execute("PRAGMA synchronous = NORMAL")  # Good balance between speed and safety
    return conn

def init_db():
    """Initialize database from schema"""
    if not os.path.exists(app.config['DATABASE']):
        conn = get_db()
        with open('./database/schema.sql', 'r') as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
        print("✅ Database initialized")

# =============================================
# Authentication & Authorization
# =============================================

def token_required(f):
    """Decorator to check JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Missing token'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user_id = data['user_id']
            request.clinic_id = data['clinic_id']
            request.role = data['role']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

# =============================================
# Data Compression & Serialization
# =============================================

class DataCompressor:
    """Compress and decompress data efficiently"""
    
    @staticmethod
    def compress_json(data: Dict) -> Tuple[bytes, Dict]:
        """Compress JSON data and return compressed bytes + metadata"""
        json_str = json.dumps(data, separators=(',', ':'))
        original_size = len(json_str.encode('utf-8'))
        
        # Compress
        compressed = gzip.compress(json_str.encode('utf-8'), compresslevel=6)
        compressed_size = len(compressed)
        
        # Calculate compression ratio
        ratio = 1 - (compressed_size / original_size) if original_size > 0 else 0
        
        metadata = {
            'original_size': original_size,
            'compressed_size': compressed_size,
            'compression_ratio': round(ratio, 2),
            'algorithm': 'gzip',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return compressed, metadata
    
    @staticmethod
    def decompress_json(compressed_data: bytes) -> Dict:
        """Decompress JSON data"""
        try:
            json_str = gzip.decompress(compressed_data).decode('utf-8')
            return json.loads(json_str)
        except Exception as e:
            raise ValueError(f"Decompression failed: {str(e)}")
    
    @staticmethod
    def calculate_checksum(data: bytes) -> str:
        """Calculate SHA256 checksum of data"""
        return hashlib.sha256(data).hexdigest()

# =============================================
# Sync Engine
# =============================================

class OfflineSyncEngine:
    """Manages offline-first data synchronization"""
    
    @staticmethod
    def get_sync_queue(conn, status='pending', limit=100):
        """Get pending sync operations"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sync_queue 
            WHERE sync_status = ? 
            ORDER BY priority DESC, created_at ASC 
            LIMIT ?
        """, (status, limit))
        return cursor.fetchall()
    
    @staticmethod
    def add_to_sync_queue(conn, entity_type: str, operation: str, 
                         entity_id: int = None, entity_uid: str = None,
                         payload: Dict = None, priority: int = 0):
        """Add operation to sync queue"""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sync_queue (entity_type, entity_id, entity_uid, operation, 
                                   payload, priority, sync_status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """, (entity_type, entity_id, entity_uid, json.dumps(payload or {}), priority))
        conn.commit()
        return cursor.lastrowid
    
    @staticmethod
    def mark_synced(conn, sync_queue_id: int, success: bool = True, 
                   error_message: str = None):
        """Mark item as synced or failed"""
        cursor = conn.cursor()
        status = 'synced' if success else 'failed'
        cursor.execute("""
            UPDATE sync_queue 
            SET sync_status = ?, last_sync_attempt = ?, sync_attempts = sync_attempts + 1,
                error_message = ?
            WHERE id = ?
        """, (status, datetime.utcnow().isoformat(), error_message, sync_queue_id))
        conn.commit()
    
    @staticmethod
    def check_conflict(conn, entity_type: str, entity_id: int, 
                      local_version: str, remote_version: str) -> Dict:
        """Check for sync conflicts"""
        if local_version == remote_version:
            return {'conflict': False}
        
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conflicts (entity_type, entity_id, local_version, 
                                 remote_version, resolution_strategy)
            VALUES (?, ?, ?, ?, 'pending')
        """, (entity_type, entity_id, local_version, remote_version))
        conn.commit()
        
        return {
            'conflict': True,
            'resolution_needed': True,
            'local_version': local_version,
            'remote_version': remote_version
        }
    
    @staticmethod
    def resolve_conflict(conn, conflict_id: int, resolution_strategy: str,
                        resolved_value: str = None):
        """Resolve a conflict"""
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE conflicts 
            SET resolution_strategy = ?, resolved_value = ?, resolved_at = ?
            WHERE id = ?
        """, (resolution_strategy, resolved_value, datetime.utcnow().isoformat(), conflict_id))
        conn.commit()

# =============================================
# Authentication Endpoints
# =============================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not user['is_active']:
        return jsonify({'error': 'User account is inactive'}), 403
    
    # Generate JWT token
    token = jwt.encode({
        'user_id': user['id'],
        'clinic_id': user['clinic_id'],
        'role': user['role'],
        'exp': datetime.utcnow() + timedelta(days=7)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'role': user['role']
        }
    }), 200

@app.route('/api/auth/change-password', methods=['POST'])
@token_required
def change_password():
    """Change user password"""
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({'error': 'Both passwords required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (request.user_id,))
    user = cursor.fetchone()
    
    if not check_password_hash(user['password_hash'], old_password):
        conn.close()
        return jsonify({'error': 'Current password incorrect'}), 401
    
    new_hash = generate_password_hash(new_password)
    cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?',
                  (new_hash, request.user_id))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Password changed successfully'}), 200

# =============================================
# Patient Endpoints (Offline-First)
# =============================================

@app.route('/api/patients', methods=['GET'])
@token_required
def get_patients():
    """Get all patients for clinic"""
    conn = get_db()
    cursor = conn.cursor()
    
    search = request.args.get('search', '')
    if search:
        cursor.execute("""
            SELECT * FROM patients 
            WHERE clinic_id = ? AND (first_name LIKE ? OR last_name LIKE ? OR patient_id LIKE ?)
            LIMIT 1000
        """, (request.clinic_id, f'%{search}%', f'%{search}%', f'%{search}%'))
    else:
        cursor.execute("""
            SELECT * FROM patients 
            WHERE clinic_id = ? AND status = 'active'
            LIMIT 1000
        """, (request.clinic_id,))
    
    patients = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(patients), 200

@app.route('/api/patients', methods=['POST'])
@token_required
def create_patient():
    """Create new patient (instant local save, queued for sync)"""
    data = request.get_json()
    
    # Validate required fields
    if not data.get('first_name') or not data.get('last_name'):
        return jsonify({'error': 'First and last name required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Generate patient ID
    patient_id = f"GOTG_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Save to local database immediately (INSTANT LOCAL PERSISTENCE)
    cursor.execute("""
        INSERT INTO patients 
        (patient_id, first_name, last_name, date_of_birth, gender, phone, email, 
         id_number, clinic_id, status, sync_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 'pending')
    """, (patient_id, data['first_name'], data['last_name'], data.get('date_of_birth'),
          data.get('gender'), data.get('phone'), data.get('email'),
          data.get('id_number'), request.clinic_id))
    
    patient_row_id = cursor.lastrowid
    
    # Queue for sync
    OfflineSyncEngine.add_to_sync_queue(
        conn, 'patient', 'create', patient_row_id, patient_id, data, priority=1
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'id': patient_row_id,
        'patient_id': patient_id,
        'message': 'Patient saved locally (will sync when online)',
        'status': 'saved_locally'
    }), 201

@app.route('/api/patients/<int:patient_id>', methods=['GET'])
@token_required
def get_patient(patient_id):
    """Get patient details with all studies"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get patient
    cursor.execute('SELECT * FROM patients WHERE id = ? AND clinic_id = ?',
                  (patient_id, request.clinic_id))
    patient = cursor.fetchone()
    
    if not patient:
        conn.close()
        return jsonify({'error': 'Patient not found'}), 404
    
    # Get patient's studies
    cursor.execute("""
        SELECT * FROM studies 
        WHERE patient_id = ?
        ORDER BY study_date DESC
    """, (patient_id,))
    studies = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'patient': dict(patient),
        'studies': studies,
        'study_count': len(studies)
    }), 200

@app.route('/api/patients/<int:patient_id>', methods=['PUT'])
@token_required
def update_patient(patient_id):
    """Update patient (instant local, queued for sync)"""
    data = request.get_json()
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check patient exists and belongs to clinic
    cursor.execute('SELECT * FROM patients WHERE id = ? AND clinic_id = ?',
                  (patient_id, request.clinic_id))
    patient = cursor.fetchone()
    
    if not patient:
        conn.close()
        return jsonify({'error': 'Patient not found'}), 404
    
    # Update locally
    update_fields = []
    update_values = []
    for key in ['first_name', 'last_name', 'phone', 'email']:
        if key in data:
            update_fields.append(f'{key} = ?')
            update_values.append(data[key])
    
    if update_fields:
        update_fields.append('updated_at = ?')
        update_values.append(datetime.utcnow().isoformat())
        update_values.append(patient_id)
        
        cursor.execute(f"""
            UPDATE patients 
            SET {', '.join(update_fields)}
            WHERE id = ?
        """, update_values)
        
        # Queue for sync
        OfflineSyncEngine.add_to_sync_queue(
            conn, 'patient', 'update', patient_id, patient['patient_id'], data, priority=1
        )
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Patient updated'}), 200

# =============================================
# Study Endpoints (DICOM Studies)
# =============================================

@app.route('/api/studies', methods=['GET'])
@token_required
def get_studies():
    """Get studies with optional filters"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Build query with filters
    query = 'SELECT * FROM studies WHERE clinic_id = ?'
    params = [request.clinic_id]
    
    if request.args.get('patient_id'):
        query += ' AND patient_id = ?'
        params.append(request.args.get('patient_id'))
    
    if request.args.get('modality'):
        query += ' AND modality = ?'
        params.append(request.args.get('modality'))
    
    if request.args.get('status'):
        query += ' AND status = ?'
        params.append(request.args.get('status'))
    
    query += ' ORDER BY study_date DESC LIMIT 500'
    cursor.execute(query, params)
    
    studies = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({
        'studies': studies,
        'count': len(studies)
    }), 200

@app.route('/api/studies', methods=['POST'])
@token_required
def create_study():
    """Create new study (instant local save, queued for sync)"""
    data = request.get_json()
    
    if not data.get('patient_id') or not data.get('modality'):
        return jsonify({'error': 'Patient ID and modality required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Verify patient exists
    cursor.execute('SELECT id FROM patients WHERE id = ? AND clinic_id = ?',
                  (data['patient_id'], request.clinic_id))
    patient = cursor.fetchone()
    
    if not patient:
        conn.close()
        return jsonify({'error': 'Patient not found'}), 404
    
    # Generate UIDs
    study_uid = f"1.2.{int(datetime.now().timestamp())}.{request.clinic_id}"
    accession = f"ACC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Save study
    cursor.execute("""
        INSERT INTO studies 
        (study_uid, patient_id, accession_number, modality, description,
         referring_physician, study_date, status, clinic_id, sync_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, 'pending')
    """, (study_uid, data['patient_id'], accession, data['modality'],
          data.get('description'), data.get('referring_physician'),
          datetime.now().isoformat(), request.clinic_id))
    
    study_id = cursor.lastrowid
    
    # Queue for sync
    OfflineSyncEngine.add_to_sync_queue(
        conn, 'study', 'create', study_id, study_uid, data, priority=2
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'id': study_id,
        'study_uid': study_uid,
        'accession_number': accession,
        'message': 'Study created locally'
    }), 201

@app.route('/api/studies/<int:study_id>/series', methods=['GET'])
@token_required
def get_study_series(study_id):
    """Get all series in a study"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.*, COUNT(di.id) as instance_count
        FROM series s
        LEFT JOIN dicom_instances di ON di.series_id = s.id
        WHERE s.study_id = ?
        GROUP BY s.id
    """, (study_id,))
    
    series = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'series': series}), 200

# =============================================
# Report Endpoints
# =============================================

@app.route('/api/reports', methods=['POST'])
@token_required
def create_report():
    """Create radiology report (instant local save, queued for sync)"""
    data = request.get_json()
    
    if not data.get('study_id'):
        return jsonify({'error': 'Study ID required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Generate report UID
    report_uid = f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Save report
    cursor.execute("""
        INSERT INTO reports 
        (report_uid, study_id, radiologist_name, findings, impression, 
         recommendations, report_status, sync_status)
        VALUES (?, ?, ?, ?, ?, ?, 'draft', 'pending')
    """, (report_uid, data['study_id'], data.get('radiologist_name'),
          data.get('findings'), data.get('impression'),
          data.get('recommendations')))
    
    report_id = cursor.lastrowid
    
    # Queue for sync
    OfflineSyncEngine.add_to_sync_queue(
        conn, 'report', 'create', report_id, report_uid, data, priority=1
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'id': report_id,
        'report_uid': report_uid,
        'message': 'Report saved locally'
    }), 201

@app.route('/api/reports/<int:report_id>', methods=['PUT'])
@token_required
def update_report(report_id):
    """Update report"""
    data = request.get_json()
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Update fields
    cursor.execute("""
        UPDATE reports 
        SET findings = ?, impression = ?, recommendations = ?,
            report_status = ?, updated_at = ?
        WHERE id = ?
    """, (data.get('findings'), data.get('impression'),
          data.get('recommendations'), data.get('report_status', 'draft'),
          datetime.utcnow().isoformat(), report_id))
    
    # Queue for sync
    cursor.execute('SELECT report_uid FROM reports WHERE id = ?', (report_id,))
    report = cursor.fetchone()
    if report:
        OfflineSyncEngine.add_to_sync_queue(
            conn, 'report', 'update', report_id, report['report_uid'], data, priority=1
        )
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Report updated'}), 200

# =============================================
# Sync Endpoints
# =============================================

@app.route('/api/sync/status', methods=['GET'])
@token_required
def get_sync_status():
    """Get current sync status for clinic"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get sync queue stats
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN sync_status = 'pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN sync_status = 'synced' THEN 1 ELSE 0 END) as synced,
            SUM(CASE WHEN sync_status = 'failed' THEN 1 ELSE 0 END) as failed
        FROM sync_queue
    """)
    
    stats = dict(cursor.fetchone())
    
    # Get pending items by type
    cursor.execute("""
        SELECT entity_type, COUNT(*) as count
        FROM sync_queue
        WHERE sync_status = 'pending'
        GROUP BY entity_type
    """)
    
    pending_by_type = {row['entity_type']: row['count'] for row in cursor.fetchall()}
    
    # Get clinic's last sync time
    cursor.execute("""
        SELECT MAX(sync_timestamp) as last_sync
        FROM sync_log
        WHERE entity_type IN (SELECT entity_type FROM sync_queue LIMIT 1)
    """)
    
    last_sync_row = cursor.fetchone()
    last_sync = last_sync_row['last_sync'] if last_sync_row else None
    
    conn.close()
    
    return jsonify({
        'queue_stats': stats,
        'pending_by_type': pending_by_type,
        'last_sync': last_sync,
        'clinic_id': request.clinic_id,
        'is_online': check_connectivity()
    }), 200

@app.route('/api/sync/queue', methods=['GET'])
@token_required
def get_sync_queue():
    """Get pending sync items"""
    conn = get_db()
    limit = request.args.get('limit', 100, type=int)
    
    pending_items = OfflineSyncEngine.get_sync_queue(conn, limit=limit)
    items = [dict(row) for row in pending_items]
    
    conn.close()
    
    return jsonify({'pending_items': items, 'count': len(items)}), 200

@app.route('/api/sync/check-conflict', methods=['POST'])
@token_required
def check_conflict():
    """Check for sync conflicts"""
    data = request.get_json()
    
    conn = get_db()
    result = OfflineSyncEngine.check_conflict(
        conn, data['entity_type'], data['entity_id'],
        data['local_version'], data['remote_version']
    )
    conn.close()
    
    return jsonify(result), 200

# =============================================
# System Endpoints
# =============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM patients LIMIT 1')
        cursor.fetchone()
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
@token_required
def get_statistics():
    """Get system statistics"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as count FROM patients WHERE clinic_id = ?',
                  (request.clinic_id,))
    patient_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM studies WHERE clinic_id = ?',
                  (request.clinic_id,))
    study_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM reports WHERE study_id IN (SELECT id FROM studies WHERE clinic_id = ?)',
                  (request.clinic_id,))
    report_count = cursor.fetchone()['count']
    
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN sync_status = 'pending' THEN 1 ELSE 0 END) as pending_sync
        FROM sync_queue
    """)
    pending_sync = cursor.fetchone()['pending_sync'] or 0
    
    conn.close()
    
    return jsonify({
        'patients': patient_count,
        'studies': study_count,
        'reports': report_count,
        'pending_sync': pending_sync,
        'offline_capable': True
    }), 200

def check_connectivity() -> bool:
    """Check if system has internet connectivity"""
    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except (socket.timeout, socket.error):
        return False

# =============================================
# Error Handlers
# =============================================

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# =============================================
# Startup
# =============================================

if __name__ == '__main__':
    init_db()
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'False') == 'True'
    )
