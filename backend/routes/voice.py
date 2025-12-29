from flask import Blueprint, request, jsonify, current_app
import os
import configparser
import tempfile
from ..auth_utils import require_auth

voice_bp = Blueprint('voice', __name__)

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')
SYSTEM_ELEVENLABS_KEY = config.get('ELEVENLABS', 'api_key', fallback=None)

# Try to import Whisper
try:
    import whisper
    WHISPER_AVAILABLE = True
except (ImportError, OSError):
    WHISPER_AVAILABLE = False

# Try to import ElevenLabs
try:
    import requests as elevenlabs_requests
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

@voice_bp.route('/dictation/transcribe', methods=['POST', 'OPTIONS'])
def transcribe_audio():
    """Transcribe audio file using Whisper Mini"""
    
    # Handle OPTIONS for CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    # Manual Auth Check to debug 401
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        print("❌ [Voice] Missing Authorization Header")
        return jsonify({'error': 'Missing Authorization Header'}), 401
    
    # Verify Token
    from ..auth_utils import verify_token
    from ..models import User
    
    token = auth_header.replace('Bearer ', '')
    user_id = verify_token(token)
    
    if not user_id:
        print(f"❌ [Voice] Invalid Token: {token[:10]}...")
        return jsonify({'error': 'Invalid Token'}), 401
        
    current_user = User.query.get(user_id)
    if not current_user:
        print(f"❌ [Voice] User Not Found: {user_id}")
        return jsonify({'error': 'User Not Found'}), 401

    print(f"✅ [Voice] Authenticated User: {current_user.alias}")

    if not WHISPER_AVAILABLE:
        return jsonify({'error': 'Whisper is not installed. Install with: pip install openai-whisper'}), 503
    
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
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        try:
            # Load Whisper model (tiny is much faster for CPU)
            # Was 'base', switching to 'tiny' for speed
            model = whisper.load_model('tiny')
            result = model.transcribe(tmp_path, language='en')
            text = result['text'].strip()
            
            return jsonify({
                'text': text,
                'status': 'success',
            })
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    except Exception as e:
        print(f"Transcription error: {e}")
        return jsonify({'error': str(e)}), 500

@voice_bp.route('/tts/speak', methods=['POST'])
@require_auth
def tts_speak(current_user):
    """Generate speech from text using ElevenLabs"""
    data = request.get_json()
    text = data.get('text')
    voice_id = data.get('voice_id', '21m00Tcm4TlvDq8ikWAM')
    api_key = data.get('api_key') or SYSTEM_ELEVENLABS_KEY
    
    if not text:
        return jsonify({'error': 'Text required'}), 400
        
    # Try ElevenLabs if key provided
    if api_key and ELEVENLABS_AVAILABLE:
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": api_key
            }
            payload = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": data.get('stability', 0.5),
                    "similarity_boost": data.get('clarity', 0.75)
                }
            }
            response = elevenlabs_requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                return response.content, 200, {'Content-Type': 'audio/mpeg'}
            else:
                print(f"ElevenLabs Error: {response.text}")
                return jsonify({'error': 'ElevenLabs API error'}), response.status_code
        except Exception as e:
            print(f"ElevenLabs Exception: {e}")
            return jsonify({'error': str(e)}), 500
            
    return jsonify({'error': 'TTS not configured'}), 400

# Voice Previews
VOICE_PREVIEWS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'voices'))
if not os.path.exists(VOICE_PREVIEWS_DIR):
    os.makedirs(VOICE_PREVIEWS_DIR, exist_ok=True)

from flask import send_from_directory

@voice_bp.route('/tts/voices', methods=['GET'])
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

@voice_bp.route('/tts/preview/<filename>', methods=['GET'])
def get_voice_preview(filename):
    """Serve pre-generated voice preview audio"""
    try:
        return send_from_directory(VOICE_PREVIEWS_DIR, filename, mimetype='audio/mpeg')
    except:
        return jsonify({'error': 'Preview not found. Use /api/tts/generate-previews to create them.'}), 404

@voice_bp.route('/tts/generate-previews', methods=['POST'])
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

