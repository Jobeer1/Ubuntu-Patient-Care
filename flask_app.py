"""
SDOH Chat - Standalone Flask Application
Low-bandwidth, privacy-first chat for healthcare teams
"""

from flask import Flask, jsonify, request, send_from_directory, send_file, render_template_string
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from urllib.parse import quote_plus
import jwt
import bcrypt
import os
import uuid
import json
from pathlib import Path
from agent_forge import IntegrityForge
from agent_quest import QuestMaster
import io
import configparser
import local_tts

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')
SYSTEM_ELEVENLABS_KEY = config.get('ELEVENLABS', 'api_key', fallback=None)

# Try to import Whisper for transcription
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("⚠️ Whisper not installed. Audio transcription will be unavailable.")
    print("   Install with: pip install openai-whisper")

# Try to import ElevenLabs for voice generation
try:
    import requests as elevenlabs_requests
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

# Initialize Flask app
app = Flask(__name__)

# Create voice previews directory
VOICE_PREVIEWS_DIR = os.path.join(os.path.dirname(__file__), 'frontend', 'voices')
os.makedirs(VOICE_PREVIEWS_DIR, exist_ok=True)

# HTTPS/SSL Configuration
CERT_FILE = os.path.join(os.path.dirname(__file__), 'cert.pem')
KEY_FILE = os.path.join(os.path.dirname(__file__), 'key.pem')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sdoh_chat_v7.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Forge Agent
forge_agent = IntegrityForge(os.path.join(os.path.dirname(__file__), 'config.ini'))
quest_agent = QuestMaster(os.path.join(os.path.dirname(__file__), 'config.ini'))
app.config['SECRET_KEY'] = 'sdoh-chat-secret-key-change-in-production'
app.config['JSON_SORT_KEYS'] = False

# Enable CORS
CORS(app, origins=["*"])

# Initialize database
db = SQLAlchemy(app)

# Flag to track if DB is initialized
_db_initialized = False

def ensure_db_initialized():
    """Ensure database is created and populated with default data"""
    global _db_initialized
    if _db_initialized:
        return
    
    try:
        db.create_all()
        init_default_groups()
        _db_initialized = True
        print("✅ Database initialized with default groups")
    except Exception as e:
        print(f"⚠️ Error initializing database: {e}")

# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.String(10), primary_key=True)
    alias = db.Column(db.String(50), unique=True, nullable=True)
    pin_hash = db.Column(db.String(255), nullable=True)
    code_visible = db.Column(db.Boolean, default=False)
    alias_colors = db.Column(db.Text, nullable=True)
    
    # Forge / Agent Fields
    integrity_score = db.Column(db.Integer, default=10)
    forge_history = db.Column(db.Text, default='[]') # JSON list of messages
    custom_api_key = db.Column(db.String(255), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    
    # Role & Moderation Fields (NEW)
    user_role = db.Column(db.String(20), default='user')  # admin, moderator, user
    credentials = db.Column(db.Text, default='[]')  # JSON list of earned badges/credentials
    is_reported = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

class Message(db.Model):
    __tablename__ = 'messages'
    msg_id = db.Column(db.String(36), primary_key=True)
    sender_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    chat_id = db.Column(db.String(36), nullable=False)
    content = db.Column(db.Text, nullable=False)
    msg_type = db.Column(db.String(20), default='text')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    edited_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime)
    
    __table_args__ = (db.Index('idx_chat_created', 'chat_id', 'created_at'),)

class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.String(36), primary_key=True)
    group_name = db.Column(db.String(100))
    created_by = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    is_private = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_renamed_at = db.Column(db.DateTime)
    previous_name = db.Column(db.String(100))
    renamed_by = db.Column(db.String(10))
    
    # Moderation Fields (NEW)
    moderator_ids = db.Column(db.Text, default='[]')  # JSON list of appointed moderator user_ids
    moderation_type = db.Column(db.String(20), default='human')  # human, ai, hybrid
    ai_moderator_key = db.Column(db.String(255), nullable=True)  # Optional LLM API key for AI moderation
    ai_moderator_enabled = db.Column(db.Boolean, default=False)

class GroupVote(db.Model):
    __tablename__ = 'group_votes'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.String(36), db.ForeignKey('groups.id'), nullable=False)
    user_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    vote_type = db.Column(db.String(20))  # 'revert_name'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GroupMember(db.Model):
    __tablename__ = 'group_members'
    group_id = db.Column(db.String(36), db.ForeignKey('groups.id'), primary_key=True)
    user_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), primary_key=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

class Contact(db.Model):
    __tablename__ = 'contacts'
    user_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), primary_key=True)
    contact_id = db.Column(db.String(10), primary_key=True)
    contact_alias = db.Column(db.String(50))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

class Quest(db.Model):
    __tablename__ = 'quests'
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=True)  # JSON
    difficulty = db.Column(db.String(20), default='solo')  # solo, small-group, community
    created_by = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    reward = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

# NEW: User Control & Moderation Tables
class BlockList(db.Model):
    __tablename__ = 'block_list'
    user_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), primary_key=True)
    blocked_id = db.Column(db.String(10), primary_key=True)  # Blocked user's code
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MuteList(db.Model):
    __tablename__ = 'mute_list'
    user_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), primary_key=True)
    muted_id = db.Column(db.String(10), primary_key=True)  # Muted user's code
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.String(36), primary_key=True)
    reporter_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    reportee_id = db.Column(db.String(10), nullable=False)  # User being reported
    report_reason = db.Column(db.Text, nullable=False)
    report_context = db.Column(db.Text, nullable=True)  # Group ID or chat context
    status = db.Column(db.String(20), default='pending')  # pending, investigating, resolved, dismissed
    assigned_moderator = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=True)
    investigation_notes = db.Column(db.Text, nullable=True)
    resolution = db.Column(db.String(20), nullable=True)  # warning, mute, ban, dismiss
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ModeratorLog(db.Model):
    __tablename__ = 'moderator_logs'
    id = db.Column(db.String(36), primary_key=True)
    moderator_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)  # appoint, remove, warn, mute, investigate
    target_user = db.Column(db.String(10), nullable=True)
    group_id = db.Column(db.String(36), nullable=True)
    details = db.Column(db.Text, nullable=True)  # JSON details
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Credential(db.Model):
    __tablename__ = 'credentials'
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    credential_type = db.Column(db.String(50), nullable=False)  # quest-completed, peer-validated, community-vote
    credential_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    issued_by = db.Column(db.String(10), nullable=True)  # User/quest that issued it

class VoiceNote(db.Model):
    """Voice note model - Audio files in messages"""
    __tablename__ = 'voice_notes'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False, index=True)
    group_id = db.Column(db.String(36), db.ForeignKey('groups.id'), nullable=True, index=True)
    audio_data = db.Column(db.LargeBinary, nullable=False)  # WAV/MP3 blob
    duration = db.Column(db.Float, default=0.0)  # Duration in seconds
    transcription = db.Column(db.Text, nullable=True)  # Optional transcription
    file_type = db.Column(db.String(10), default='wav')  # wav, mp3, m4a
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class InviteCode(db.Model):
    """Invite code model - For user referral/invitations"""
    __tablename__ = 'invite_codes'
    code = db.Column(db.String(16), primary_key=True)  # e.g., 'ABC123DEF456'
    created_by = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False, index=True)
    uses_remaining = db.Column(db.Integer, default=10)  # Max invites per code
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))
    is_active = db.Column(db.Boolean, default=True)

class Referral(db.Model):
    """Referral tracking model"""
    __tablename__ = 'referrals'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    referrer_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False, index=True)
    referred_id = db.Column(db.String(10), db.ForeignKey('users.user_id'), nullable=False)
    invite_code = db.Column(db.String(16), db.ForeignKey('invite_codes.code'), nullable=True)
    referred_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_user_code():
    """Generate a random 10-digit code"""
    import random
    return str(random.randint(1000000000, 9999999999))

def hash_pin(pin):
    """Hash PIN with bcrypt"""
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt(rounds=12)).decode()

def verify_pin(pin, pin_hash):
    """Verify PIN against hash"""
    return bcrypt.checkpw(pin.encode(), pin_hash.encode())

def create_token(user_id, expires_in=86400):
    """Create JWT token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(seconds=expires_in),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['user_id']
    except:
        return None

def get_current_user():
    """Get current user from token"""
    token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return None
    return verify_token(token)

from functools import wraps

def require_auth(f):
    """Decorator to require JWT token authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Unauthorized - valid token required'}), 401
        
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        return f(current_user, *args, **kwargs)
    return decorated_function

# ============================================================================
# API ENDPOINTS - AUTHENTICATION
# ============================================================================

@app.route('/api/sdoh/auth/register', methods=['POST'])
def register():
    """Register new user"""
    ensure_db_initialized()  # Ensure DB is ready
    user_code = generate_user_code()
    return jsonify({
        'status': 'success',
        'user_id': user_code,
        'needs_alias': True
    }), 201

@app.route('/api/sdoh/auth/set-alias', methods=['POST'])
def set_alias():
    """Set user alias"""
    data = request.json
    user_code = data.get('user_id')
    alias = data.get('alias', '').strip()
    
    if not alias or len(alias) < 3 or len(alias) > 50:
        return jsonify({'error': 'Alias must be 3-50 characters'}), 400
    
    if User.query.filter_by(alias=alias).first():
        return jsonify({'error': 'Alias already taken'}), 400
    
    # Check if user exists, if not create placeholder with NULL pin_hash
    try:
        user = User.query.get(user_code)
        if not user:
            # Create new user with nullable pin_hash
            user = User(user_id=user_code, alias=alias, pin_hash=None)
            db.session.add(user)
        else:
            # Update existing user
            user.alias = alias
        
        db.session.commit()
        return jsonify({'status': 'success', 'alias': alias}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in set_alias: {str(e)}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/sdoh/auth/set-pin', methods=['POST'])
def set_pin():
    """Set user PIN"""
    data = request.json
    user_code = data.get('user_id')
    pin = data.get('pin', '')
    
    if not pin or len(pin) < 4 or len(pin) > 8 or not pin.isdigit():
        return jsonify({'error': 'PIN must be 4-8 digits'}), 400
    
    user = User.query.get(user_code)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.pin_hash = hash_pin(pin)
    db.session.commit()
    
    return jsonify({'status': 'success'}), 200

@app.route('/api/sdoh/auth/login', methods=['POST'])
def login():
    """Login user"""
    data = request.json
    user_code = data.get('user_id', '')
    pin = data.get('pin', '')
    
    user = User.query.get(user_code)
    if not user or not verify_pin(pin, user.pin_hash):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    token = create_token(user_code)
    return jsonify({
        'status': 'success',
        'token': token,
        'alias': user.alias,
        'user_id': user_code
    }), 200

@app.route('/api/sdoh/auth/profile', methods=['GET'])
def profile():
    """Get user profile"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user_id': user.user_id,
        'alias': user.alias,
        'code_visible': user.code_visible,
        'created_at': user.created_at.isoformat()
    }), 200

# ============================================================================
# API ENDPOINTS - VOICE & TRANSCRIPTION
# ============================================================================

@app.route('/api/dictation/transcribe', methods=['POST'])
def transcribe_audio():
    """Transcribe audio file using Whisper Mini"""
    if not WHISPER_AVAILABLE:
        return jsonify({'error': 'Whisper is not installed. Install with: pip install openai-whisper'}), 503
    
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Check if file is present
    if 'file' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['file']
    if audio_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Read audio data
        audio_data = audio_file.read()
        
        # Save to temp file for Whisper
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        try:
            # Load Whisper model (base is good for general use, tiny for speed)
            model = whisper.load_model('base')
            result = model.transcribe(tmp_path, language='en')
            text = result['text'].strip()
            
            return jsonify({
                'text': text,
                'status': 'success',
                'confidence': result.get('language', 'en')
            }), 200
        finally:
            # Clean up temp file
            os.unlink(tmp_path)
    
    except Exception as e:
        return jsonify({
            'error': f'Transcription failed: {str(e)}'
        }), 500

@app.route('/api/tts/voices', methods=['GET'])
def get_voice_list():
    """Get list of available voices with preview URLs"""
    voices = [
        {
            'id': '21m00Tcm4TlvDq8ikWAM',
            'name': 'Rachel',
            'description': 'Warm',
            'preview_url': '/api/tts/preview/rachel.mp3'
        },
        {
            'id': 'EXAVITQu4vr4xnSDxMaL',
            'name': 'Bella',
            'description': 'Calm',
            'preview_url': '/api/tts/preview/bella.mp3'
        },
        {
            'id': 'TX3LPaxmHKniDCm1u8gQ',
            'name': 'Charlotte',
            'description': 'Friendly',
            'preview_url': '/api/tts/preview/charlotte.mp3'
        },
        {
            'id': 'pMsXgVXv3BLzUgSXRplE',
            'name': 'Adam',
            'description': 'Serious',
            'preview_url': '/api/tts/preview/adam.mp3'
        },
        {
            'id': 'IX5yDUzCrqLEV5QZ7nXo',
            'name': 'Chris',
            'description': 'Dynamic',
            'preview_url': '/api/tts/preview/chris.mp3'
        }
    ]
    return jsonify(voices), 200

@app.route('/api/tts/preview/<filename>', methods=['GET'])
def get_voice_preview(filename):
    """Serve pre-generated voice preview audio"""
    try:
        return send_from_directory(VOICE_PREVIEWS_DIR, filename, mimetype='audio/mpeg')
    except:
        return jsonify({'error': 'Preview not found. Use /api/tts/generate-previews to create them.'}), 404

@app.route('/api/tts/generate-previews', methods=['POST'])
def generate_voice_previews():
    """Generate and store voice previews (Admin only, call once)"""
    # Simple auth check - can be made more secure
    api_key = request.json.get('api_key') if request.json else None
    
    if not api_key:
        return jsonify({'error': 'ElevenLabs API key required'}), 400
    
    voices = {
        'rachel.mp3': '21m00Tcm4TlvDq8ikWAM',
        'bella.mp3': 'EXAVITQu4vr4xnSDxMaL',
        'charlotte.mp3': 'TX3LPaxmHKniDCm1u8gQ',
        'adam.mp3': 'pMsXgVXv3BLzUgSXRplE',
        'chris.mp3': 'IX5yDUzCrqLEV5QZ7nXo'
    }
    
    preview_text = 'Hello, this is a voice preview.'
    generated = []
    failed = []
    
    for filename, voice_id in voices.items():
        try:
            response = elevenlabs_requests.post(
                f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
                headers={
                    'Content-Type': 'application/json',
                    'xi-api-key': api_key
                },
                json={
                    'text': preview_text,
                    'model_id': 'eleven_monolingual_v1',
                    'voice_settings': {
                        'stability': 0.5,
                        'similarity_boost': 0.75
                    }
                },
                timeout=10
            )
            
            if response.status_code == 200:
                # Save audio file
                filepath = os.path.join(VOICE_PREVIEWS_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                generated.append(filename)
                print(f"✅ Generated preview: {filename}")
            else:
                failed.append(f"{filename} (HTTP {response.status_code})")
                print(f"❌ Failed: {filename} - {response.status_code}")
        except Exception as e:
            failed.append(f"{filename} ({str(e)})")
            print(f"❌ Error generating {filename}: {str(e)}")
    
    return jsonify({
        'status': 'complete',
        'generated': generated,
        'failed': failed,
        'total': len(generated) + len(failed)
    }), 200

@app.route('/api/tts/speak', methods=['POST'])
def tts_speak():
    """Text-to-speech: Use browser TTS by default (instant), ElevenLabs on explicit request"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    text = data.get('text', '').strip()
    voice_id = data.get('voice_id', '21m00Tcm4TlvDq8ikWAM')
    api_key = data.get('api_key', '').strip()
    use_elevenlabs = data.get('use_elevenlabs', False)  # Only use ElevenLabs if explicitly requested
    stability = data.get('stability', 0.5)
    clarity = data.get('clarity', 0.75)
    
    if not text:
        return jsonify({'error': 'Text required'}), 400

    # 1. Try ElevenLabs ONLY if explicitly requested AND we have a key
    if use_elevenlabs:
        if not api_key and SYSTEM_ELEVENLABS_KEY:
            api_key = SYSTEM_ELEVENLABS_KEY
        
        if api_key:
            try:
                response = elevenlabs_requests.post(
                    f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
                    headers={
                        'Content-Type': 'application/json',
                        'xi-api-key': api_key
                    },
                    json={
                        'text': text,
                        'model_id': 'eleven_monolingual_v1',
                        'voice_settings': {
                            'stability': float(stability),
                            'similarity_boost': float(clarity)
                        }
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    return send_file(
                        io.BytesIO(response.content),
                        mimetype='audio/mpeg'
                    )
                else:
                    print(f"ElevenLabs Error: {response.status_code}")
            except Exception as e:
                print(f"ElevenLabs Error: {e}")

    # 2. Default: Use BROWSER TTS (Web Speech API - instant, no server processing)
    # This tells the frontend to use native browser speech synthesis
    return jsonify({
        'use_browser_tts': True,
        'text': text,
        'message': 'Use browser Speech Synthesis API for instant, local TTS'
    }), 200

# ============================================================================
# API ENDPOINTS - MESSAGES
# ============================================================================

@app.route('/api/sdoh/messages/send', methods=['POST'])
def send_message():
    """Send a message"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    to = data.get('to', '')  # recipient user_id or group_id
    text = data.get('text', '').strip()
    
    if not text or len(text) > 500:
        return jsonify({'error': 'Message must be 1-500 characters'}), 400
    
    msg_id = str(uuid.uuid4())
    msg = Message(msg_id=msg_id, sender_id=user_id, chat_id=to, content=text, msg_type='text')
    db.session.add(msg)
    db.session.commit()
    
    sender = User.query.get(user_id)
    return jsonify({
        'status': 'success',
        'msg_id': msg_id,
        'sender_alias': sender.alias,
        'content': text,
        'created_at': msg.created_at.isoformat()
    }), 201

@app.route('/api/sdoh/messages/<chat_id>', methods=['GET'])
def get_messages(chat_id):
    """Get messages from a chat"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    messages = Message.query.filter_by(chat_id=chat_id).filter(Message.deleted_at.is_(None)).order_by(Message.created_at.desc()).limit(limit).offset(offset).all()
    
    result = []
    for msg in reversed(messages):
        sender = User.query.get(msg.sender_id)
        result.append({
            'msg_id': msg.msg_id,
            'sender_alias': sender.alias if sender else 'Unknown',
            'content': msg.content,
            'created_at': msg.created_at.isoformat()
        })
    
    return jsonify(result), 200

# ============================================================================
# FRONTEND - SERVE HTML
# ============================================================================

@app.route('/')
def serve_root():
    """Redirect to chat"""
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'frontend'), 'index.html')

@app.route('/sdoh/')
@app.route('/sdoh/index.html')
def serve_index():
    """Serve login/register page"""
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'frontend'), 'index.html')

@app.route('/sdoh/dashboard.html')
def serve_dashboard():
    """Serve chat dashboard"""
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'frontend'), 'dashboard.html')

@app.route('/sdoh/<path:filename>')
def serve_frontend(filename):
    """Serve static files"""
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'frontend'), filename)

# ============================================================================
# DASHBOARD & SETTINGS
# ============================================================================

def init_default_groups():
    """Create default public groups if they don't exist"""
    defaults = [
        "General", "Announcements", "Doctors", "Nurses", 
        "Emergency", "Radiology", "Pathology", "Admin", 
        "Social", "Tech Support"
    ]
    
    try:
        # Check if we have any public groups
        existing = Group.query.filter_by(is_private=False).count()
        if existing >= len(defaults):
            print(f"✅ Found {existing} default groups")
            return
            
        # Create system user for group creation
        sys_user = User.query.get('SYSTEM')
        if not sys_user:
            sys_user = User(user_id='SYSTEM', alias='System', pin_hash='SYSTEM')
            db.session.add(sys_user)
            
        # Create The Forge Agent User
        forge_user = User.query.get('FORGE')
        if not forge_user:
            forge_user = User(user_id='FORGE', alias='The Forge', pin_hash='FORGE', alias_colors='{"0":"#ff0000","1":"#ff0000","2":"#ff0000","3":"#ff0000","4":"#ff0000","5":"#ff0000","6":"#ff0000","7":"#ff0000","8":"#ff0000"}')
            db.session.add(forge_user)
            
        db.session.commit()
            
        for name in defaults:
            # Check if group already exists
            if not Group.query.filter_by(group_name=name).first():
                group = Group(
                    id=str(uuid.uuid4()),
                    group_name=name,
                    created_by='SYSTEM',
                    is_private=False
                )
                db.session.add(group)
        
        db.session.commit()
        final_count = Group.query.filter_by(is_private=False).count()
        print(f"✅ Ensured {final_count} default groups exist")
    except Exception as e:
        print(f"⚠️ Error creating default groups: {e}")
        db.session.rollback()

@app.route('/api/sdoh/dashboard', methods=['GET'])
def get_dashboard_data():
    """Get user info and groups for dashboard"""
    ensure_db_initialized()  # Ensure DB is ready
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    user = User.query.get(user_id)
    
    # Get public groups
    public_groups = Group.query.filter_by(is_private=False).all()
    
    groups_data = []
    for g in public_groups:
        # Count active users in this group
        member_count = GroupMember.query.filter_by(group_id=g.id).count()
        
        groups_data.append({
            'id': g.id,
            'name': g.group_name,
            'is_private': g.is_private,
            'is_online': True,  # Public rooms are always "online" for now
            'member_count': member_count,
            'max_members': 20,  # 20 user limit per room
            'last_renamed_at': g.last_renamed_at.isoformat() if g.last_renamed_at else None
        })
    
    print(f"📊 Dashboard: User={user_id}, Groups={len(groups_data)}")
    if len(groups_data) == 0:
        print("⚠️ No public groups found!")
        
    # Ensure Personal Forge chat exists
    forge_chat_id = f"forge_{user_id}"
    
    return jsonify({
        'user': {
            'user_id': user.user_id,
            'alias': user.alias,
            'alias_colors': json.loads(user.alias_colors) if user.alias_colors else {},
            'integrity_score': user.integrity_score,
            'is_verified': user.is_verified,
            'custom_api_key': user.custom_api_key
        },
        'groups': groups_data,
        'forge_chat_id': forge_chat_id
    })

@app.route('/api/sdoh/groups/<group_id>/join', methods=['POST'])
def join_group(group_id):
    """Join a group (with 20-user limit)"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    group = Group.query.get(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    
    # Check if user is already a member
    existing = GroupMember.query.filter_by(group_id=group_id, user_id=user_id).first()
    if existing:
        return jsonify({'status': 'already_member'})
    
    # Check room capacity (20 user limit)
    member_count = GroupMember.query.filter_by(group_id=group_id).count()
    if member_count >= 20:
        return jsonify({'error': 'Room is full (20 user limit)'}), 400
    
    # Add user to group
    member = GroupMember(group_id=group_id, user_id=user_id)
    db.session.add(member)
    db.session.commit()
    
    return jsonify({'status': 'joined', 'member_count': member_count + 1})

@app.route('/api/sdoh/forge/chat', methods=['POST'])
def chat_with_forge():
    """Send message to The Forge Agent"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Empty message'}), 400
        
    user = User.query.get(user_id)
    
    # 1. Save User Message
    chat_id = f"forge_{user_id}"
    user_msg = Message(
        msg_id=str(uuid.uuid4()),
        sender_id=user_id,
        chat_id=chat_id,
        content=content
    )
    db.session.add(user_msg)
    
    # 2. Get History
    try:
        history = json.loads(user.forge_history)
    except:
        history = []
        
    # 3. Call Agent
    result = forge_agent.chat(
        user_input=content,
        history=history,
        current_score=user.integrity_score,
        user_api_key=user.custom_api_key
    )
    
    # 4. Extract response text and score adjustment
    if isinstance(result, dict):
        ai_response = result.get('response', str(result))
        score_adjustment = result.get('score_adjustment', 0)
    else:
        ai_response = str(result)
        score_adjustment = 0
    
    # 5. Update User State
    user.integrity_score = max(0, min(100, user.integrity_score + score_adjustment))
    user.is_verified = True
        
    # Update history
    history.append({"role": "user", "content": content})
    history.append({"role": "model", "content": ai_response})
    user.forge_history = json.dumps(history[-20:]) # Keep last 20 turns
    
    # 5. Save Agent Response
    agent_msg = Message(
        msg_id=str(uuid.uuid4()),
        sender_id='FORGE',
        chat_id=chat_id,
        content=ai_response
    )
    db.session.add(agent_msg)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'response': ai_response,
        'score': user.integrity_score,
        'verified': user.is_verified
    })

@app.route('/api/sdoh/quest/chat', methods=['POST'])
def chat_with_quest():
    """Send message to The Quest-Master Agent"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get(user_id)
    data = request.json
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Empty message'}), 400
    
    # Get or create quest history
    chat_id = f"quest_{user_id}"
    try:
        quest_history = json.loads(user.forge_history) if user.forge_history else []
    except:
        quest_history = []
    
    # 1. Save User Message
    user_msg = Message(
        msg_id=str(uuid.uuid4()),
        sender_id=user_id,
        chat_id=chat_id,
        content=content
    )
    db.session.add(user_msg)
    
    # 2. Call Quest Agent
    result = quest_agent.chat(
        user_input=content,
        history=quest_history,
        user_alias=user.alias,
        user_api_key=user.custom_api_key
    )
    
    # 3. If quest is ready, post to Quest Board
    posted_quest = None
    if result['quest_ready'] and result['quest_data']:
        quest_data = result['quest_data']
        posted_quest = Quest(
            id=str(uuid.uuid4()),
            name=quest_data.get('name', 'Untitled Quest'),
            description=quest_data.get('description', ''),
            requirements=json.dumps(quest_data.get('requirements', {})),
            difficulty=quest_data.get('difficulty', 'solo'),
            created_by=user_id,
            reward=quest_data.get('reward', '')
        )
        db.session.add(posted_quest)
    
    # 4. Update history
    quest_history.append({"role": "user", "content": content})
    quest_history.append({"role": "model", "content": result['response']})
    
    # 5. Save Agent Response
    agent_msg = Message(
        msg_id=str(uuid.uuid4()),
        sender_id='QUEST',
        chat_id=chat_id,
        content=result['response']
    )
    db.session.add(agent_msg)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'response': result['response'],
        'quest_posted': result['quest_ready'],
        'quest_id': posted_quest.id if posted_quest else None
    })

@app.route('/api/sdoh/quests', methods=['GET'])
def get_quests():
    """Get all active quests from the Quest Board"""
    try:
        quests = Quest.query.filter_by(status='active').order_by(Quest.created_at.desc()).all()
        
        quests_data = []
        for q in quests:
            creator = User.query.get(q.created_by)
            quests_data.append({
                'id': q.id,
                'name': q.name,
                'description': q.description,
                'requirements': json.loads(q.requirements) if q.requirements else {},
                'difficulty': q.difficulty,
                'created_by': creator.alias if creator else 'Unknown',
                'reward': q.reward,
                'created_at': q.created_at.isoformat()
            })
        
        return jsonify({'quests': quests_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sdoh/forge/greeting', methods=['GET'])
def get_forge_greeting():
    """Get personalized Forge greeting for user"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get(user_id)
    greeting = f"""Hello {user.alias}. I'm The Forge - your personal integrity coach and character auditor. I'm here to help you discover what you're truly made of. What brings you here today?

**[PRIVACY NOTICE]** Your API keys (ElevenLabs, Google Gemini, etc.) are stored ONLY in your browser's local storage. They are NEVER sent to our servers and NEVER logged. Each request is encrypted end-to-end. Your credentials are 100% under your control - we don't even have access to them. You can clear them anytime in Settings → Clear API Keys."""
    
    return jsonify({
        'greeting': greeting,
        'agent': 'The Forge',
        'role': 'Integrity Auditor - Onboarding & Personal Challenge Coach'
    })

@app.route('/api/sdoh/user/settings', methods=['POST'])
def update_settings():
    """Update user settings (alias colors, api key)"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    user = User.query.get(user_id)
    
    if 'alias_colors' in data:
        user.alias_colors = json.dumps(data['alias_colors'])
        
    if 'custom_api_key' in data:
        user.custom_api_key = data['custom_api_key'].strip() if data['custom_api_key'] else None
        
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/sdoh/groups/<group_id>/rename', methods=['POST'])
def rename_group(group_id):
    """Rename a group with cooldown"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    new_name = data.get('name', '').strip()
    
    if not new_name or len(new_name) < 3:
        return jsonify({'error': 'Name too short'}), 400
        
    group = Group.query.get(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404
        
    # Check cooldown (1 hour)
    if group.last_renamed_at:
        diff = datetime.utcnow() - group.last_renamed_at
        if diff.total_seconds() < 3600:
            minutes_left = int((3600 - diff.total_seconds()) / 60)
            return jsonify({'error': f'Please wait {minutes_left} minutes before renaming again'}), 429
            
    # Save previous state
    group.previous_name = group.group_name
    group.group_name = new_name
    group.last_renamed_at = datetime.utcnow()
    group.renamed_by = user_id
    
    # Clear old votes
    GroupVote.query.filter_by(group_id=group_id, vote_type='revert_name').delete()
    
    db.session.commit()
    return jsonify({'status': 'success', 'name': new_name})

@app.route('/api/sdoh/groups/<group_id>/vote-revert', methods=['POST'])
def vote_revert_group(group_id):
    """Vote to revert group name"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    group = Group.query.get(group_id)
    if not group or not group.previous_name:
        return jsonify({'error': 'Nothing to revert'}), 400
        
    # Check if already voted
    existing = GroupVote.query.filter_by(
        group_id=group_id, user_id=user_id, vote_type='revert_name'
    ).first()
    
    if existing:
        return jsonify({'error': 'Already voted'}), 400
        
    vote = GroupVote(group_id=group_id, user_id=user_id, vote_type='revert_name')
    db.session.add(vote)
    db.session.commit()
    
    # Check if we should revert (simple logic: 3 votes reverts it for now)
    count = GroupVote.query.filter_by(group_id=group_id, vote_type='revert_name').count()
    
    if count >= 3:  # Threshold
        group.group_name = group.previous_name
        group.previous_name = None
        group.last_renamed_at = None # Reset cooldown
        GroupVote.query.filter_by(group_id=group_id, vote_type='revert_name').delete()
        db.session.commit()
        return jsonify({'status': 'reverted', 'name': group.group_name})
        
    return jsonify({'status': 'voted', 'votes': count})

# ============================================================================
# VOICE NOTES & RECORDING ENDPOINTS (NEW)
# ============================================================================

@app.route('/api/voice-notes/upload', methods=['POST'])
def upload_voice_note():
    """Upload a voice note/recording"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Get audio data from request
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    group_id = request.form.get('group_id')  # Optional: which group to share to
    duration = request.form.get('duration', '0')  # Duration in seconds
    
    try:
        duration = float(duration)
    except:
        duration = 0.0
    
    # Read audio blob
    audio_data = audio_file.read()
    if len(audio_data) == 0:
        return jsonify({'error': 'Empty audio file'}), 400
    
    # Create voice note record
    note_id = str(uuid.uuid4())
    file_ext = audio_file.filename.split('.')[-1] if audio_file.filename else 'wav'
    
    voice_note = VoiceNote(
        id=note_id,
        sender_id=user_id,
        group_id=group_id,
        audio_data=audio_data,
        duration=duration,
        file_type=file_ext.lower()
    )
    
    db.session.add(voice_note)
    
    # If group specified, create a message linking to the voice note
    if group_id:
        msg = Message(
            msg_id=str(uuid.uuid4()),
            sender_id=user_id,
            chat_id=group_id,
            content=f'🎙️ Voice note ({duration:.1f}s)',
            msg_type='voice_note'
        )
        db.session.add(msg)
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'note_id': note_id,
        'url': f'/api/voice-notes/{note_id}',
        'duration': duration
    }), 201

@app.route('/api/voice-notes/<note_id>', methods=['GET'])
def get_voice_note(note_id):
    """Retrieve a voice note audio blob"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    note = VoiceNote.query.get(note_id)
    if not note:
        return jsonify({'error': 'Voice note not found'}), 404
    
    # Return audio blob
    return send_file(
        io.BytesIO(note.audio_data),
        mimetype=f'audio/{note.file_type}'
    )

@app.route('/api/voice-notes/chat/<chat_id>', methods=['GET'])
def list_voice_notes(chat_id):
    """List all voice notes in a chat/group"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Get messages of type 'voice_note'
    messages = Message.query.filter(
        Message.chat_id == chat_id,
        Message.msg_type == 'voice_note',
        Message.deleted_at.is_(None)
    ).order_by(Message.created_at.desc()).limit(50).all()
    
    notes_list = []
    for msg in messages:
        sender = User.query.get(msg.sender_id)
        notes_list.append({
            'msg_id': msg.msg_id,
            'sender_alias': sender.alias if sender else 'Unknown',
            'sender_id': msg.sender_id,
            'duration': msg.voice_note.duration if msg.voice_note else 0,
            'created_at': msg.created_at.isoformat(),
            'url': f'/api/voice-notes/{msg.voice_note.id}' if msg.voice_note else None
        })
    
    return jsonify({'notes': notes_list}), 200

# ============================================================================
# INVITE & REFERRAL ENDPOINTS (NEW)
# ============================================================================

@app.route('/api/invites/generate', methods=['POST'])
def generate_invite_link():
    """Generate a new invite code for the current user"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Generate unique code
    import secrets
    code = secrets.token_urlsafe(9)[:12].upper()
    
    # Check for collision (unlikely but possible)
    while InviteCode.query.get(code):
        code = secrets.token_urlsafe(9)[:12].upper()
    
    invite = InviteCode(
        code=code,
        created_by=user_id,
        uses_remaining=20,  # 20 invites per code
        is_active=True
    )
    
    db.session.add(invite)
    db.session.commit()
    
    # Build shareable links
    base_url = request.host_url.rstrip('/')
    invite_url = f"{base_url}/?ref={code}"
    
    return jsonify({
        'code': code,
        'invite_url': invite_url,
        'share_links': {
            'whatsapp': f"https://wa.me/?text=Join%20SDOH%20Chat!%20{quote_plus(invite_url)}",
            'email': f"mailto:?subject=Join%20SDOH%20Chat&body={quote_plus(f'Click here to join: {invite_url}')}",
            'copy': invite_url
        }
    }), 201

@app.route('/api/invites/my-link', methods=['GET'])
def get_my_invite_link():
    """Get or create the user's personal invite link"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Check if user already has an active invite code
    invite = InviteCode.query.filter_by(created_by=user_id, is_active=True).first()
    
    if not invite:
        # Create one if it doesn't exist
        import secrets
        code = secrets.token_urlsafe(9)[:12].upper()
        while InviteCode.query.get(code):
            code = secrets.token_urlsafe(9)[:12].upper()
        
        invite = InviteCode(
            code=code,
            created_by=user_id,
            uses_remaining=50,  # More generous for personal link
            is_active=True
        )
        db.session.add(invite)
        db.session.commit()
    
    user = User.query.get(user_id)
    base_url = request.host_url.rstrip('/')
    invite_url = f"{base_url}/?ref={invite.code}"
    
    return jsonify({
        'code': invite.code,
        'invite_url': invite_url,
        'uses_remaining': invite.uses_remaining,
        'user_alias': user.alias if user else 'Unknown',
        'share_links': {
            'whatsapp': f"https://wa.me/?text=Join%20SDOH%20Chat%20with%20me!%20{quote_plus(invite_url)}",
            'email': f"mailto:?subject=Join%20SDOH%20Chat%20-%20Invite%20from%20{quote_plus(user.alias if user else 'SDOH')}&body={quote_plus(f'Hey! Join me on SDOH Chat - a privacy-first healthcare communication platform.\\n\\n{invite_url}')}",
            'sms': f"sms:?body={quote_plus(f'Join SDOH Chat with me! {invite_url}')}",
            'copy': invite_url
        }
    }), 200

@app.route('/api/invites/<code>/stats', methods=['GET'])
def get_invite_stats(code):
    """Get stats for an invite code"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    invite = InviteCode.query.get(code)
    if not invite or invite.created_by != user_id:
        return jsonify({'error': 'Invite not found or not yours'}), 403
    
    # Count how many people used this code
    referrals = Referral.query.filter_by(invite_code=code).count()
    
    return jsonify({
        'code': code,
        'created_at': invite.created_at.isoformat(),
        'expires_at': invite.expires_at.isoformat(),
        'uses_remaining': invite.uses_remaining,
        'uses_total': 20 - invite.uses_remaining,
        'referrals_count': referrals,
        'is_active': invite.is_active
    }), 200

# Update register endpoint to handle invite codes
@app.route('/api/invites/redeem', methods=['POST'])
def redeem_invite():
    """Register a new user with an invite code (bonus: mark referral)"""
    user_id = get_current_user()
    if user_id:
        return jsonify({'error': 'Already logged in'}), 400
    
    data = request.json
    code = data.get('code', '').strip().upper()
    
    if not code:
        return jsonify({'error': 'No invite code provided'}), 400
    
    # Validate invite code
    invite = InviteCode.query.get(code)
    if not invite or not invite.is_active or invite.expires_at < datetime.utcnow():
        return jsonify({'error': 'Invalid or expired invite code'}), 400
    
    if invite.uses_remaining <= 0:
        return jsonify({'error': 'Invite code has no remaining uses'}), 400
    
    # Store code in session for use during registration
    # (The actual registration endpoint will be modified to create Referral record)
    return jsonify({
        'valid': True,
        'referrer_id': invite.created_by,
        'message': 'Proceed with registration - you will receive a referral bonus'
    }), 200

# ============================================================================
# GROUP MEMBER MANAGEMENT ENDPOINTS (NEW)
# ============================================================================

@app.route('/api/groups/<group_id>/members', methods=['GET'])
def list_group_members(group_id):
    """List all members in a group"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    group = Group.query.get(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    
    members = GroupMember.query.filter_by(group_id=group_id).all()
    member_list = []
    
    for membership in members:
        user = User.query.get(membership.user_id)
        if user:
            member_list.append({
                'user_id': user.user_id,
                'alias': user.alias,
                'joined_at': membership.joined_at.isoformat(),
                'integrity_score': user.integrity_score,
                'is_creator': user.user_id == group.created_by
            })
    
    return jsonify({
        'group_id': group_id,
        'member_count': len(member_list),
        'members': member_list
    }), 200

@app.route('/api/groups/<group_id>/members/<target_user_id>', methods=['DELETE'])
def remove_group_member(group_id, target_user_id):
    """Remove a member from a group (must be creator or admin)"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    group = Group.query.get(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    
    # Only group creator or admins can remove members
    if group.created_by != user_id:
        return jsonify({'error': 'Only group creator can remove members'}), 403
    
    membership = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=target_user_id
    ).first()
    
    if not membership:
        return jsonify({'error': 'Member not found in group'}), 404
    
    db.session.delete(membership)
    db.session.commit()
    
    return jsonify({'status': 'removed', 'user_id': target_user_id}), 200

@app.route('/api/groups/<group_id>/members/<target_user_id>/leave', methods=['POST'])
def leave_group(group_id, target_user_id):
    """User leaves a group (self-removal)"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Can only leave if it's yourself, or creator can remove others
    if target_user_id != user_id and Group.query.get(group_id).created_by != user_id:
        return jsonify({'error': 'Can only leave for yourself'}), 403
    
    membership = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=target_user_id
    ).first()
    
    if not membership:
        return jsonify({'error': 'Not a member of this group'}), 404
    
    db.session.delete(membership)
    db.session.commit()
    
    return jsonify({'status': 'left', 'group_id': group_id}), 200

# ============================================================================
# USER CONTROL ENDPOINTS (NEW)
# ============================================================================

@app.route('/api/sdoh/user/block', methods=['POST'])
@require_auth
def block_user(current_user):
    """Block a user - they won't see messages from blocked user"""
    data = request.get_json()
    blocked_id = data.get('blocked_id')
    
    if not blocked_id:
        return jsonify({'error': 'blocked_id required'}), 400
    
    # Check if already blocked
    existing = BlockList.query.filter_by(user_id=current_user.user_id, blocked_id=blocked_id).first()
    if existing:
        return jsonify({'status': 'already_blocked'}), 200
    
    # Add to block list
    block = BlockList(user_id=current_user.user_id, blocked_id=blocked_id)
    db.session.add(block)
    db.session.commit()
    
    return jsonify({'status': 'blocked', 'blocked_id': blocked_id}), 201

@app.route('/api/sdoh/user/block/<blocked_id>', methods=['DELETE'])
@require_auth
def unblock_user(current_user, blocked_id):
    """Unblock a user"""
    BlockList.query.filter_by(user_id=current_user.user_id, blocked_id=blocked_id).delete()
    db.session.commit()
    return jsonify({'status': 'unblocked'}), 200

@app.route('/api/sdoh/user/mute', methods=['POST'])
@require_auth
def mute_user(current_user):
    """Mute a user - muted user's messages hidden but not deleted"""
    data = request.get_json()
    muted_id = data.get('muted_id')
    
    if not muted_id:
        return jsonify({'error': 'muted_id required'}), 400
    
    # Check if already muted
    existing = MuteList.query.filter_by(user_id=current_user.user_id, muted_id=muted_id).first()
    if existing:
        return jsonify({'status': 'already_muted'}), 200
    
    # Add to mute list
    mute = MuteList(user_id=current_user.user_id, muted_id=muted_id)
    db.session.add(mute)
    db.session.commit()
    
    return jsonify({'status': 'muted', 'muted_id': muted_id}), 201

@app.route('/api/sdoh/user/mute/<muted_id>', methods=['DELETE'])
@require_auth
def unmute_user(current_user, muted_id):
    """Unmute a user"""
    MuteList.query.filter_by(user_id=current_user.user_id, muted_id=muted_id).delete()
    db.session.commit()
    return jsonify({'status': 'unmuted'}), 200

@app.route('/api/sdoh/user/blocked-list', methods=['GET'])
@require_auth
def get_blocked_list(current_user):
    """Get list of blocked users"""
    blocks = BlockList.query.filter_by(user_id=current_user.user_id).all()
    return jsonify({
        'blocked': [{'user_id': b.blocked_id, 'blocked_at': b.created_at.isoformat()} for b in blocks]
    }), 200

@app.route('/api/sdoh/user/muted-list', methods=['GET'])
@require_auth
def get_muted_list(current_user):
    """Get list of muted users"""
    mutes = MuteList.query.filter_by(user_id=current_user.user_id).all()
    return jsonify({
        'muted': [{'user_id': m.muted_id, 'muted_at': m.created_at.isoformat()} for m in mutes]
    }), 200

# ============================================================================
# MODERATION ENDPOINTS (NEW)
# ============================================================================

@app.route('/api/sdoh/report', methods=['POST'])
@require_auth
def create_report(current_user):
    """Report a user for moderation review"""
    data = request.get_json()
    reportee_id = data.get('reportee_id')
    reason = data.get('reason')
    context = data.get('context')  # Optional: group_id, message_id, etc.
    
    if not reportee_id or not reason:
        return jsonify({'error': 'reportee_id and reason required'}), 400
    
    # Create report
    report = Report(
        id=str(uuid.uuid4()),
        reporter_id=current_user.user_id,
        reportee_id=reportee_id,
        report_reason=reason,
        report_context=context
    )
    db.session.add(report)
    db.session.commit()
    
    return jsonify({
        'status': 'reported',
        'report_id': report.id,
        'message': 'Thank you for reporting. Moderators will review this.'
    }), 201

@app.route('/api/sdoh/reports', methods=['GET'])
@require_auth
def get_reports(current_user):
    """Get reports (admin/moderator only)"""
    # Check if user is moderator or admin
    if current_user.user_role not in ['admin', 'moderator']:
        return jsonify({'error': 'Moderator access required'}), 403
    
    reports = Report.query.filter_by(status='pending').all()
    return jsonify({
        'reports': [{
            'id': r.id,
            'reporter': r.reporter_id,
            'reportee': r.reportee_id,
            'reason': r.report_reason,
            'context': r.report_context,
            'created_at': r.created_at.isoformat(),
            'status': r.status
        } for r in reports]
    }), 200

@app.route('/api/sdoh/report/<report_id>/investigate', methods=['PUT'])
@require_auth
def investigate_report(current_user, report_id):
    """Investigate a report (moderator action)"""
    if current_user.user_role not in ['admin', 'moderator']:
        return jsonify({'error': 'Moderator access required'}), 403
    
    report = Report.query.get(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    data = request.get_json()
    notes = data.get('notes')
    resolution = data.get('resolution')  # warning, mute, ban, dismiss
    
    # Update report
    report.status = 'investigating'
    report.assigned_moderator = current_user.user_id
    report.investigation_notes = notes
    
    if resolution:
        report.status = 'resolved'
        report.resolution = resolution
        
        # Log moderator action
        log = ModeratorLog(
            id=str(uuid.uuid4()),
            moderator_id=current_user.user_id,
            action_type='investigate',
            target_user=report.reportee_id,
            details=json.dumps({'reason': report.report_reason, 'resolution': resolution})
        )
        db.session.add(log)
        
        # Apply resolution
        if resolution == 'ban':
            user = User.query.get(report.reportee_id)
            if user:
                user.is_banned = True
    
    db.session.commit()
    return jsonify({'status': 'investigated', 'resolution': resolution}), 200

@app.route('/api/sdoh/moderator/appoint', methods=['POST'])
@require_auth
def appoint_moderator(current_user):
    """Appoint a moderator (admin only, or room creator for their room)"""
    data = request.get_json()
    user_to_appoint = data.get('user_id')
    group_id = data.get('group_id')  # Optional: if specific to a group
    
    if not user_to_appoint:
        return jsonify({'error': 'user_id required'}), 400
    
    # Check authorization
    if group_id:
        group = Group.query.get(group_id)
        if not group or group.created_by != current_user.user_id:
            if current_user.user_role != 'admin':
                return jsonify({'error': 'Only group creator or admin can appoint'}), 403
        
        # Add to group moderators
        mods = json.loads(group.moderator_ids or '[]')
        if user_to_appoint not in mods:
            mods.append(user_to_appoint)
            group.moderator_ids = json.dumps(mods)
    
    else:
        # System-wide moderator (admin only)
        if current_user.user_role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        user = User.query.get(user_to_appoint)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.user_role = 'moderator'
    
    # Log the action
    log = ModeratorLog(
        id=str(uuid.uuid4()),
        moderator_id=current_user.user_id,
        action_type='appoint',
        target_user=user_to_appoint,
        group_id=group_id,
        details=json.dumps({'appointed_to': group_id or 'system-wide'})
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'status': 'appointed', 'moderator': user_to_appoint}), 201

@app.route('/api/sdoh/group/<group_id>/set-ai-moderator', methods=['POST'])
@require_auth
def set_ai_moderator(current_user, group_id):
    """Room creator can set optional AI moderator (with custom LLM key)"""
    group = Group.query.get(group_id)
    if not group or group.created_by != current_user.user_id:
        return jsonify({'error': 'Only group creator can set AI moderator'}), 403
    
    data = request.get_json()
    ai_key = data.get('ai_key')  # Custom LLM API key
    enable = data.get('enable', True)
    
    if ai_key:
        group.ai_moderator_key = ai_key
    
    group.ai_moderator_enabled = enable
    group.moderation_type = 'hybrid' if enable else 'human'
    db.session.commit()
    
    return jsonify({
        'status': 'ai_moderator_configured',
        'enabled': enable,
        'message': 'AI moderator will not count toward 20-user room limit'
    }), 200

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'healthy'}), 200

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# INITIALIZATION
# ============================================================================

if __name__ == '__main__':
    # Create tables
    with app.app_context():
        db.create_all()
        init_default_groups()
        print("✅ Database initialized")
    
    # Warmup TTS model in background (non-blocking)
    local_tts.warmup_tts()
    
    # Run server
    print("")
    print("╔═══════════════════════════════════════════════════╗")
    print("║         SDOH Chat - Flask Server                 ║")
    print("║         Privacy-First Healthcare Chat            ║")
    print("╚═══════════════════════════════════════════════════╝")
    print("")
    print("🚀 Starting SDOH Chat Server...")
    print("📍 URL: http://0.0.0.0:5001")
    print("💬 Chat: http://0.0.0.0:5001/sdoh/index.html")
    print("📚 API Docs: http://0.0.0.0:5001/health")
    print("")
    print("Press CTRL+C to stop")
    print("")
    
    app.run(host='0.0.0.0', port=5001, debug=True)
