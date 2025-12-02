#!/usr/bin/env python3
"""
GOTG Dictation-3: Multi-User LAN-Enabled Backend

Professional Flask server for voice dictation and injury assessment.
Features:
- Multi-user concurrent support on LAN network
- Session management with user isolation
- Real-time voice transcription (OpenAI Whisper)
- AI-powered injury detection
- Offline-first operation with sync queue
- <2 second transcription, <1 second injury rendering
"""

import os
import sys
import json
import uuid
import sqlite3
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from functools import wraps
from contextlib import contextmanager

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
import jwt

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

# Import injury detection ML
sys.path.insert(0, str(Path(__file__).parent / "ml_models"))
from injury_detector import InjuryDetector

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# FLASK APP CONFIGURATION
# ============================================================================

app = Flask(__name__)
CORS(app)  # Enable CORS for LAN access

# Session & Security
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_SECURE'] = False  # LAN development
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# File uploads
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', '/tmp/dictation_audio')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DB_PATH = os.environ.get('DICTATION_DB_PATH', '/data/dictation.db')
RIS1_DB_PATH = os.environ.get('RIS1_DB_PATH', '/data/ris1.db')

# Create data directory
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Database connection pool with thread safety
db_locks = {}
db_lock = threading.Lock()

# ============================================================================
# JWT CONFIGURATION
# ============================================================================

JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-gotg-dictation-secret-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRY_HOURS = 24

# ============================================================================
# WHISPER CONFIGURATION
# ============================================================================

WHISPER_MODEL_SIZE = os.environ.get('WHISPER_MODEL', 'tiny')  # tiny=39M
SUPPORTED_LANGUAGES = ['en', 'zu', 'xh', 'af', 'en-ZA']
WHISPER_MODEL = None

def load_whisper_model():
    """Lazy-load Whisper model to save memory"""
    global WHISPER_MODEL
    if WHISPER_AVAILABLE and WHISPER_MODEL is None:
        logger.info(f"Loading Whisper {WHISPER_MODEL_SIZE} model...")
        WHISPER_MODEL = whisper.load_model(WHISPER_MODEL_SIZE)
        logger.info("✓ Whisper model loaded")
    return WHISPER_MODEL

# ============================================================================
# DATABASE HELPERS - THREAD-SAFE
# ============================================================================

@contextmanager
def get_db_connection(db_path=DB_PATH):
    """Get thread-safe database connection with locking"""
    # Create lock for this database if needed
    with db_lock:
        if db_path not in db_locks:
            db_locks[db_path] = threading.Lock()
    
    db_file_lock = db_locks[db_path]
    
    # Acquire lock for this operation
    db_file_lock.acquire()
    
    try:
        conn = sqlite3.connect(db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for concurrent access
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA foreign_keys=ON')
        yield conn
        conn.commit()
        conn.close()
    finally:
        db_file_lock.release()

def init_db():
    """Initialize database schema"""
    try:
        with get_db_connection(DB_PATH) as conn:
            c = conn.cursor()
            
            # Create tables for Dictation-3
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    clinic_id TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'clinician',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS dictation_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    clinic_id TEXT NOT NULL,
                    study_id TEXT,
                    status TEXT DEFAULT 'active',
                    transcription TEXT,
                    audio_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS assessments (
                    assessment_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    clinic_id TEXT NOT NULL,
                    primary_injury TEXT,
                    severity REAL,
                    injuries_json TEXT,
                    vital_signs_json TEXT,
                    clinical_observations_json TEXT,
                    processing_time_ms INTEGER,
                    confidence REAL,
                    sync_status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES dictation_sessions(session_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS sync_queue (
                    sync_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    clinic_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    action TEXT,
                    payload TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced_at TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES dictation_sessions(session_id)
                )
            ''')
            
            # Create indexes for performance
            c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user ON dictation_sessions(user_id)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_clinic ON dictation_sessions(clinic_id)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_assessments_user ON assessments(user_id)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_assessments_clinic ON assessments(clinic_id)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_sync_status ON sync_queue(status)')
            
            logger.info("✓ Database initialized successfully")
    
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        raise

# ============================================================================
# AUTHENTICATION & JWT
# ============================================================================

def create_token(user_id: str, clinic_id: str, email: str, role: str = "clinician") -> str:
    """Create JWT token with user info"""
    payload = {
        'user_id': user_id,
        'clinic_id': clinic_id,
        'email': email,
        'role': role,
        'iat': datetime.utcnow().isoformat(),
        'exp': (datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)).isoformat()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> Optional[Dict]:
    """Verify JWT token"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token verification failed: {e}")
        return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Missing authorization header'}), 401
        
        try:
            token = auth_header.split(' ')[1]
            payload = verify_token(token)
            if not payload:
                return jsonify({'error': 'Invalid or expired token'}), 401
            request.user = payload
            request.user_id = payload.get('user_id')
            request.clinic_id = payload.get('clinic_id')
        except (IndexError, ValueError):
            return jsonify({'error': 'Invalid authorization header'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# API ENDPOINTS - AUTHENTICATION
# ============================================================================

@app.route('/api/dictation/auth/login', methods=['POST'])
def login():
    """Login endpoint for multi-user LAN access"""
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ['email', 'clinic_id']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        email = data['email']
        clinic_id = data['clinic_id']
        
        # For development: auto-create user if doesn't exist
        user_id = str(uuid.uuid4())
        
        with get_db_connection(DB_PATH) as conn:
            c = conn.cursor()
            
            # Check if user exists
            c.execute('SELECT user_id, role FROM users WHERE email = ? AND clinic_id = ?',
                     (email, clinic_id))
            user = c.fetchone()
            
            if not user:
                # Create new user
                role = data.get('role', 'clinician')
                c.execute('''
                    INSERT INTO users (user_id, clinic_id, email, password_hash, role)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, clinic_id, email, 'dev-hash', role))
                user_id = user_id
                role = role
            else:
                user_id = user['user_id']
                role = user['role']
        
        # Create token
        token = create_token(user_id, clinic_id, email, role)
        
        return jsonify({
            'token': token,
            'user_id': user_id,
            'email': email,
            'clinic_id': clinic_id,
            'role': role
        }), 200
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# API ENDPOINTS - DICTATION SESSIONS
# ============================================================================

@app.route('/api/dictation/session/start', methods=['POST'])
@require_auth
def start_session():
    """Start new dictation session with user isolation"""
    try:
        data = request.get_json() or {}
        
        session_id = str(uuid.uuid4())
        study_id = data.get('study_id')
        
        with get_db_connection(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO dictation_sessions
                (session_id, user_id, clinic_id, study_id, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, request.user_id, request.clinic_id, study_id, 'active'))
        
        logger.info(f"Session started: {session_id} for user {request.user_id}")
        
        return jsonify({
            'session_id': session_id,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Session start error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dictation/session/<session_id>/upload-audio', methods=['POST'])
@require_auth
def upload_audio(session_id):
    """Upload audio file for session"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        # Secure filename and save
        filename = secure_filename(f"{session_id}_audio.webm")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        audio_file.save(filepath)
        
        # Update session with audio path
        with get_db_connection(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                UPDATE dictation_sessions
                SET audio_path = ?, updated_at = ?
                WHERE session_id = ? AND user_id = ?
            ''', (filepath, datetime.utcnow(), session_id, request.user_id))
        
        logger.info(f"Audio uploaded for session {session_id}")
        
        return jsonify({
            'session_id': session_id,
            'audio_path': filepath,
            'size': os.path.getsize(filepath)
        }), 200
    
    except Exception as e:
        logger.error(f"Audio upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dictation/session/<session_id>/transcribe', methods=['POST'])
@require_auth
def transcribe_audio(session_id):
    """Transcribe audio using Whisper"""
    try:
        # Get session
        with get_db_connection(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                SELECT audio_path FROM dictation_sessions
                WHERE session_id = ? AND user_id = ?
            ''', (session_id, request.user_id))
            session_row = c.fetchone()
            
            if not session_row:
                return jsonify({'error': 'Session not found'}), 404
            
            audio_path = session_row['audio_path']
        
        if not audio_path or not os.path.exists(audio_path):
            return jsonify({'error': 'Audio file not found'}), 404
        
        # Load Whisper model
        model = load_whisper_model()
        if not model:
            return jsonify({'error': 'Whisper not available'}), 503
        
        # Transcribe
        start_time = time.time()
        language = request.get_json().get('language', 'en') if request.is_json else 'en'
        
        result = model.transcribe(audio_path, language=language)
        transcription = result['text']
        confidence = result.get('confidence', 0.95)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Update session
        with get_db_connection(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                UPDATE dictation_sessions
                SET transcription = ?, updated_at = ?
                WHERE session_id = ? AND user_id = ?
            ''', (transcription, datetime.utcnow(), session_id, request.user_id))
        
        logger.info(f"Transcription complete: {session_id} ({processing_time}ms)")
        
        return jsonify({
            'session_id': session_id,
            'transcription': transcription,
            'confidence': confidence,
            'processing_time_ms': processing_time,
            'language': language
        }), 200
    
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dictation/session/<session_id>/assess-injuries', methods=['POST'])
@require_auth
def assess_injuries(session_id):
    """Assess injuries from transcription"""
    try:
        data = request.get_json()
        transcription = data.get('transcription', '')
        
        if not transcription:
            return jsonify({'error': 'No transcription provided'}), 400
        
        # Run injury detection
        detector = InjuryDetector()
        start_time = time.time()
        
        assessment = detector.analyze_transcription(transcription)
        processing_time = int((time.time() - start_time) * 1000)
        
        assessment['processing_time_ms'] = processing_time
        
        # Save assessment
        assessment_id = str(uuid.uuid4())
        
        with get_db_connection(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO assessments
                (assessment_id, session_id, user_id, clinic_id,
                 primary_injury, severity, injuries_json,
                 vital_signs_json, clinical_observations_json,
                 processing_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                assessment_id,
                session_id,
                request.user_id,
                request.clinic_id,
                assessment.get('primary_injury', {}).get('injury_type'),
                assessment.get('primary_injury', {}).get('severity'),
                json.dumps(assessment.get('injuries', [])),
                json.dumps(assessment.get('vital_signs', {})),
                json.dumps(assessment.get('clinical_observations', {})),
                processing_time
            ))
        
        logger.info(f"Assessment complete: {assessment_id} ({processing_time}ms)")
        
        return jsonify(assessment), 200
    
    except Exception as e:
        logger.error(f"Assessment error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dictation/session/<session_id>/complete', methods=['POST'])
@require_auth
def complete_session(session_id):
    """Complete and save session"""
    try:
        data = request.get_json() or {}
        
        with get_db_connection(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                UPDATE dictation_sessions
                SET status = ?, updated_at = ?
                WHERE session_id = ? AND user_id = ?
            ''', ('completed', datetime.utcnow(), session_id, request.user_id))
            
            # Add to sync queue
            sync_id = str(uuid.uuid4())
            c.execute('''
                INSERT INTO sync_queue
                (sync_id, session_id, clinic_id, user_id, action, payload)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                sync_id,
                session_id,
                request.clinic_id,
                request.user_id,
                'save_dictation',
                json.dumps(data)
            ))
        
        logger.info(f"Session completed: {session_id}")
        
        return jsonify({
            'session_id': session_id,
            'status': 'completed'
        }), 200
    
    except Exception as e:
        logger.error(f"Session completion error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# API ENDPOINTS - QUERIES & LISTING
# ============================================================================

@app.route('/api/dictation/sessions', methods=['GET'])
@require_auth
def list_sessions():
    """List user's dictation sessions with clinic isolation"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        with get_db_connection(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                SELECT s.session_id, s.transcription, s.status,
                       a.primary_injury, a.severity, a.created_at
                FROM dictation_sessions s
                LEFT JOIN assessments a ON s.session_id = a.session_id
                WHERE s.user_id = ? AND s.clinic_id = ?
                ORDER BY s.created_at DESC
                LIMIT ?
            ''', (request.user_id, request.clinic_id, limit))
            
            sessions = []
            for row in c.fetchall():
                sessions.append({
                    'session_id': row['session_id'],
                    'transcription': row['transcription'] or '',
                    'status': row['status'],
                    'primary_injury': row['primary_injury'],
                    'primary_severity': row['severity'],
                    'created_at': row['created_at']
                })
        
        return jsonify({'sessions': sessions, 'count': len(sessions)}), 200
    
    except Exception as e:
        logger.error(f"List sessions error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dictation/pending-sync', methods=['GET'])
@require_auth
def get_pending_sync():
    """Get pending items for RIS-1 sync"""
    try:
        with get_db_connection(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                SELECT sync_id, action, payload, created_at
                FROM sync_queue
                WHERE user_id = ? AND clinic_id = ? AND status = ?
                ORDER BY created_at ASC
            ''', (request.user_id, request.clinic_id, 'pending'))
            
            pending = []
            for row in c.fetchall():
                pending.append({
                    'sync_id': row['sync_id'],
                    'action': row['action'],
                    'payload': json.loads(row['payload']),
                    'created_at': row['created_at']
                })
        
        return jsonify({'pending': pending, 'count': len(pending)}), 200
    
    except Exception as e:
        logger.error(f"Get pending sync error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dictation/mark-synced', methods=['POST'])
@require_auth
def mark_synced():
    """Mark sync items as synced"""
    try:
        data = request.get_json() or {}
        sync_ids = data.get('sync_ids', [])
        
        if not sync_ids:
            return jsonify({'error': 'No sync IDs provided'}), 400
        
        with get_db_connection(DB_PATH) as conn:
            c = conn.cursor()
            for sync_id in sync_ids:
                c.execute('''
                    UPDATE sync_queue
                    SET status = ?, synced_at = ?
                    WHERE sync_id = ? AND user_id = ?
                ''', ('synced', datetime.utcnow(), sync_id, request.user_id))
        
        logger.info(f"Marked {len(sync_ids)} items as synced")
        
        return jsonify({'synced_count': len(sync_ids)}), 200
    
    except Exception as e:
        logger.error(f"Mark synced error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.route('/api/dictation/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'whisper': 'available' if WHISPER_AVAILABLE else 'unavailable'
    }), 200

@app.route('/health', methods=['GET'])
def simple_health():
    """Simple health check"""
    return jsonify({'status': 'ok'}), 200

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# INITIALIZATION & STARTUP
# ============================================================================

@app.before_first_request
def startup():
    """Initialize app on first request"""
    logger.info("Starting GOTG Dictation-3 Multi-User Backend...")
    init_db()
    load_whisper_model()
    logger.info("✓ Application ready")

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Get configuration
    host = os.environ.get('FLASK_HOST', '0.0.0.0')  # Listen on all interfaces for LAN
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting server on {host}:{port}")
    
    # Run server with thread pool for concurrent users
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True,  # Enable threading for concurrent requests
        use_reloader=False  # Disable reloader in production
    )
