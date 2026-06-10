"""
SDOH Chat - Standalone Flask Application
Low-bandwidth, privacy-first chat for healthcare teams
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
import configparser
try:
    import local_tts
except ImportError:
    # Provide fallback if local_tts is not available
    class local_tts:
        @staticmethod
        def warmup_tts():
            pass
from backend.extensions import db
from backend.utils import init_default_groups

# Add local ffmpeg to PATH
ffmpeg_path = os.path.join(os.getcwd(), "bin", "ffmpeg", "bin")
if os.path.exists(ffmpeg_path):
    os.environ["PATH"] += os.pathsep + ffmpeg_path

# Get the frontend directory path
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), 'frontend')
print(f"DEBUG: Frontend directory set to: {FRONTEND_DIR}")
if not os.path.exists(FRONTEND_DIR):
    print("CRITICAL ERROR: Frontend directory does not exist!")

# Initialize Flask app (NO static folder to avoid conflicts)
app = Flask(__name__)

# Add cache busting for static files
@app.after_request
def add_header(response):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response

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
from backend.routes.pacs_mentor import pacs_bp
from backend.routes.siim_routes import siim_bp

app.register_blueprint(auth_bp, url_prefix='/api/sdoh/auth')
app.register_blueprint(chat_bp, url_prefix='/api/sdoh')
app.register_blueprint(agents_bp, url_prefix='/api/sdoh')
app.register_blueprint(moderation_bp, url_prefix='/api/sdoh')
app.register_blueprint(voice_bp, url_prefix='/api/sdoh')
app.register_blueprint(social_bp, url_prefix='/api/sdoh')
app.register_blueprint(pacs_bp, url_prefix='/api/sdoh/pacs')
app.register_blueprint(siim_bp, url_prefix='/api/sdoh/siim')

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
# FRONTEND - SERVE HTML & STATIC FILES
# ============================================================================

@app.route('/')
def serve_root():
    """Serve root/index"""
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/sdoh/')
@app.route('/sdoh/index.html')
def serve_index():
    """Serve login/register page"""
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/sdoh/dashboard.html')
def serve_dashboard():
    """Serve chat dashboard"""
    return send_from_directory(FRONTEND_DIR, 'dashboard.html')

# Explicit Static Routes - PREVENT CATCH-ALL CONFLICTS
@app.route('/css/<path:filename>')
def serve_css(filename):
    directory = os.path.join(FRONTEND_DIR, 'css')
    print(f"DEBUG: Serving CSS {filename} from {directory}")
    try:
        return send_from_directory(directory, filename)
    except Exception as e:
        print(f"ERROR serving CSS {filename}: {e}")
        return jsonify({'error': str(e)}), 404

@app.route('/js/<path:filename>')
def serve_js(filename):
    directory = os.path.join(FRONTEND_DIR, 'js')
    print(f"DEBUG: Serving JS {filename} from {directory}")
    try:
        return send_from_directory(directory, filename)
    except Exception as e:
        print(f"ERROR serving JS {filename}: {e}")
        return jsonify({'error': str(e)}), 404

@app.route('/voices/<path:filename>')
def serve_voices(filename):
    directory = os.path.join(FRONTEND_DIR, 'voices')
    print(f"DEBUG: Serving Voice {filename} from {directory}")
    try:
        return send_from_directory(directory, filename)
    except Exception as e:
        print(f"ERROR serving Voice {filename}: {e}")
        return jsonify({'error': str(e)}), 404

@app.route('/sdoh/<path:filename>')
def serve_frontend(filename):
    """Serve other frontend files"""
    return send_from_directory(FRONTEND_DIR, filename)

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
    
    import sys
    print(f"DEBUG: Running on Python: {sys.executable}")
    
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
    print("📍 URL: http://0.0.0.0:5002")
    print("💬 Chat: http://0.0.0.0:5002/sdoh/index.html")
    print("📚 API Docs: http://0.0.0.0:5002/health")
    print("")
    print("Press CTRL+C to stop")
    print("")
    
    app.run(host='0.0.0.0', port=5002, debug=True)
