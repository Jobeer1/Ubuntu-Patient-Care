import os

new_content = r'''"""
SDOH Chat - Standalone Flask Application
Low-bandwidth, privacy-first chat for healthcare teams
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
import configparser
import local_tts
from backend.extensions import db
from backend.utils import init_default_groups

# Add local ffmpeg to PATH
ffmpeg_path = os.path.join(os.getcwd(), "bin", "ffmpeg", "bin")
if os.path.exists(ffmpeg_path):
    os.environ["PATH"] += os.pathsep + ffmpeg_path

# Initialize Flask app
app = Flask(__name__)

# HTTPS/SSL Configuration
CERT_FILE = os.path.join(os.path.dirname(__file__), 'cert.pem')
KEY_FILE = os.path.join(os.path.dirname(__file__), 'key.pem')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sdoh_chat_v7.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'sdoh-chat-secret-key-change-in-production'
app.config['JSON_SORT_KEYS'] = False

# Enable CORS
CORS(app, origins=["*"])

# Initialize database
db.init_app(app)

# Register Blueprints
from backend.routes.auth import auth_bp
from backend.routes.chat import chat_bp
from backend.routes.agents import agents_bp
from backend.routes.moderation import moderation_bp
from backend.routes.voice import voice_bp
from backend.routes.social import social_bp

app.register_blueprint(auth_bp, url_prefix='/api/sdoh/auth')
app.register_blueprint(chat_bp, url_prefix='/api/sdoh')
app.register_blueprint(agents_bp, url_prefix='/api/sdoh')
app.register_blueprint(moderation_bp, url_prefix='/api/sdoh')
app.register_blueprint(voice_bp, url_prefix='/api')
app.register_blueprint(social_bp, url_prefix='/api')

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
# HEALTH CHECK
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'healthy'}), 200

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
        ensure_db_initialized()
    
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
'''

with open('flask_app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("flask_app.py updated successfully.")
