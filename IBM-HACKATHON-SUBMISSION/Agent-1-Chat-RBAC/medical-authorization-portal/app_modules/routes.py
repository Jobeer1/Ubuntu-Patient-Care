"""
Routes Module - Flask Endpoints
==============================
All Flask application routes organized by category
Authentication, dashboard, API endpoints, error handlers
"""

from flask import render_template, request, jsonify, session, redirect, url_for, send_from_directory
from functools import wraps
from app_modules.config import ThemeConfig
from app_modules.database import db
from app_modules.auth import AuthenticationManager, get_oauth_provider, generate_oauth_state
from app_modules.copilot import Copilot
from app_modules.utils import (
    success_response, error_response, login_required, 
    log_info, log_error, generate_unique_id, get_current_datetime
)

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

def register_auth_routes(app):
    """Register authentication routes"""
    
    @app.route('/', methods=['GET'])
    def index():
        """Home page"""
        if AuthenticationManager.is_authenticated():
            return redirect(url_for('dashboard'))
        return render_template('login.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Local login"""
        if request.method == 'POST':
            data = request.get_json() if request.is_json else request.form
            email = data.get('email', '').strip()
            password = data.get('password', '')
            
            if not email or not password:
                return error_response('Email and password required', 400)
            
            user = AuthenticationManager.local_login(email, password)
            
            if user:
                AuthenticationManager.set_session(user)
                return success_response(
                    {'redirect': url_for('dashboard')},
                    'Login successful'
                )
            else:
                return error_response('Invalid email or password', 401)
        
        return render_template('login.html')
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration"""
        if request.method == 'POST':
            data = request.get_json() if request.is_json else request.form
            email = data.get('email', '').strip()
            password = data.get('password', '')
            name = data.get('name', '').strip()
            
            if not all([email, password, name]):
                return error_response('Email, password, and name required', 400)
            
            user, message = AuthenticationManager.register_local_user(email, password, name)
            
            if user:
                return success_response({'redirect': url_for('login')}, message)
            else:
                return error_response(message, 400)
        
        return render_template('register.html')
    
    @app.route('/logout', methods=['POST'])
    def logout():
        """Logout user"""
        AuthenticationManager.clear_session()
        return success_response(
            {'redirect': url_for('login')},
            'Logged out successfully'
        )
    
    @app.route('/auth/google/login', methods=['GET'])
    def google_login():
        """Initiate Google OAuth"""
        state = generate_oauth_state()
        session['oauth_state'] = state
        
        provider = get_oauth_provider('google')
        auth_url = provider.get_authorization_url(state)
        
        return redirect(auth_url)
    
    @app.route('/auth/google/callback', methods=['GET'])
    def google_callback():
        """Google OAuth callback"""
        code = request.args.get('code')
        state = request.args.get('state')
        
        if not code or state != session.get('oauth_state'):
            log_error("Invalid Google OAuth callback")
            return redirect(url_for('login'))
        
        provider = get_oauth_provider('google')
        
        # Exchange code for token
        token_data = provider.exchange_code_for_token(code)
        if not token_data:
            return redirect(url_for('login'))
        
        # Get user info
        access_token = token_data.get('access_token')
        user_info = provider.get_user_info(access_token)
        
        if not user_info:
            return redirect(url_for('login'))
        
        # Create or update user
        user = AuthenticationManager.create_or_update_oauth_user('google', user_info)
        
        if user:
            AuthenticationManager.set_session(user)
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('login'))
    
    @app.route('/auth/microsoft/login', methods=['GET'])
    def microsoft_login():
        """Initiate Microsoft OAuth"""
        state = generate_oauth_state()
        session['oauth_state'] = state
        
        provider = get_oauth_provider('microsoft')
        auth_url = provider.get_authorization_url(state)
        
        return redirect(auth_url)
    
    @app.route('/auth/microsoft/callback', methods=['GET'])
    def microsoft_callback():
        """Microsoft OAuth callback"""
        code = request.args.get('code')
        state = request.args.get('state')
        
        if not code or state != session.get('oauth_state'):
            log_error("Invalid Microsoft OAuth callback")
            return redirect(url_for('login'))
        
        provider = get_oauth_provider('microsoft')
        
        # Exchange code for token
        token_data = provider.exchange_code_for_token(code)
        if not token_data:
            return redirect(url_for('login'))
        
        # Get user info
        access_token = token_data.get('access_token')
        user_info = provider.get_user_info(access_token)
        
        if not user_info:
            return redirect(url_for('login'))
        
        # Create or update user
        user = AuthenticationManager.create_or_update_oauth_user('microsoft', user_info)
        
        if user:
            AuthenticationManager.set_session(user)
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('login'))


# ============================================================================
# DASHBOARD ROUTES
# ============================================================================

def register_dashboard_routes(app):
    """Register dashboard routes"""
    
    @app.route('/dashboard', methods=['GET'])
    @login_required
    def dashboard():
        """Main dashboard - routes based on user role"""
        user = AuthenticationManager.get_current_user()
        
        if not user:
            return redirect(url_for('login'))
        
        # Route based on role
        if user['role'] == 'admin':
            return render_template('admin_dashboard.html', user=user)
        elif user['role'] == 'doctor':
            return render_template('doctor_dashboard.html', user=user)
        elif user['role'] == 'patient':
            return render_template('patient_dashboard_ai.html', user=user)
        else:
            return render_template('patient_dashboard_ai.html', user=user)
    
    @app.route('/patient-dashboard', methods=['GET'])
    @login_required
    def patient_dashboard_ai():
        """AI-powered patient dashboard"""
        user = AuthenticationManager.get_current_user()
        
        if not user or user['role'] != 'patient':
            return redirect(url_for('dashboard'))
        
        return render_template('patient_dashboard_ai.html', user=user)
    
    @app.route('/authorizations', methods=['GET'])
    @login_required
    def authorizations():
        """Authorizations page"""
        user = AuthenticationManager.get_current_user()
        return render_template('authorizations.html', user=user)
    
    @app.route('/patients', methods=['GET'])
    @login_required
    def patients():
        """Patient search page"""
        user = AuthenticationManager.get_current_user()
        return render_template('patients.html', user=user)
    
    @app.route('/chat', methods=['GET'])
    @login_required
    def chat():
        """Chat interface"""
        user = AuthenticationManager.get_current_user()
        return render_template('chat.html', user=user)


# ============================================================================
# API ROUTES: PATIENT DATA
# ============================================================================

def register_patient_api_routes(app):
    """Register patient API routes"""
    
    @app.route('/api/patient-data', methods=['GET'])
    @login_required
    def get_patient_data():
        """Get patient data for dashboard"""
        try:
            user = AuthenticationManager.get_current_user()
            
            if not user:
                return error_response('User not found', 404)
            
            # Get appointments
            appointments = db.appointments.get_user_appointments(user['id'])
            
            # Get authorizations
            authorizations = db.authorizations.get_user_authorizations(user['id'])
            
            # Get chat history
            chat_history = db.chat.get_chat_history(user['id'], limit=10)
            
            return success_response({
                'patient': {
                    'id': user['id'],
                    'name': user.get('name', user['email']),
                    'email': user['email'],
                    'role': user['role']
                },
                'appointments': appointments or [],
                'authorizations': authorizations or [],
                'recent_chats': chat_history or []
            })
        except Exception as e:
            log_error("Error getting patient data", e)
            return error_response(str(e), 500)
    
    @app.route('/api/book-appointment', methods=['POST'])
    @login_required
    def book_appointment():
        """Book appointment"""
        try:
            data = request.get_json()
            user_id = AuthenticationManager.get_current_user()['id']
            
            appointment = {
                'id': generate_unique_id(),
                'user_id': user_id,
                'specialty': data.get('specialty'),
                'doctor': data.get('doctor'),
                'date': data.get('date'),
                'time': data.get('time'),
                'reason': data.get('reason'),
                'status': 'scheduled'
            }
            
            db.appointments.create_appointment(appointment)
            
            return success_response(
                appointment,
                f"Appointment scheduled for {appointment['date']} at {appointment['time']}"
            )
        except Exception as e:
            log_error("Error booking appointment", e)
            return error_response(str(e), 500)
    
    @app.route('/api/update-profile', methods=['POST'])
    @login_required
    def update_profile():
        """Update user profile"""
        try:
            data = request.get_json()
            user_id = AuthenticationManager.get_current_user()['id']
            
            update_data = {
                'name': data.get('name'),
                'phone': data.get('phone'),
                'date_of_birth': data.get('dob'),
                'address': data.get('address')
            }
            
            db.users.update_user(user_id, update_data)
            
            return success_response({}, 'Profile updated successfully')
        except Exception as e:
            log_error("Error updating profile", e)
            return error_response(str(e), 500)


# ============================================================================
# API ROUTES: COPILOT AI
# ============================================================================

def register_copilot_api_routes(app):
    """Register Copilot AI API routes"""
    
    @app.route('/api/copilot-chat', methods=['POST'])
    @login_required
    def copilot_chat():
        """Chat with Copilot AI assistant"""
        try:
            data = request.get_json()
            message = data.get('message', '').strip()
            user_id = AuthenticationManager.get_current_user()['id']
            
            if not message:
                return error_response('Empty message', 400)
            
            # Get Copilot response
            response = Copilot.chat(user_id, message)
            
            return success_response(response)
        except Exception as e:
            log_error("Error in copilot chat", e)
            return error_response(str(e), 500)
    
    @app.route('/api/chat-history', methods=['GET'])
    @login_required
    def get_chat_history():
        """Get user chat history"""
        try:
            user_id = AuthenticationManager.get_current_user()['id']
            limit = request.args.get('limit', 50, type=int)
            
            history = db.chat.get_chat_history(user_id, limit=limit)
            
            return success_response({'history': history or []})
        except Exception as e:
            log_error("Error getting chat history", e)
            return error_response(str(e), 500)
    
    @app.route('/api/copilot-context', methods=['GET'])
    @login_required
    def copilot_context():
        """Get Copilot context for user"""
        try:
            user_id = AuthenticationManager.get_current_user()['id']
            context = Copilot.get_context(user_id)
            
            return success_response(context)
        except Exception as e:
            log_error("Error getting copilot context", e)
            return error_response(str(e), 500)
    
    @app.route('/api/copilot-suggestion', methods=['GET'])
    @login_required
    def copilot_suggestion():
        """Get next action suggestion from Copilot"""
        try:
            user_id = AuthenticationManager.get_current_user()['id']
            suggestion = Copilot.suggest_next_action(user_id)
            
            return success_response(suggestion)
        except Exception as e:
            log_error("Error getting copilot suggestion", e)
            return error_response(str(e), 500)


# ============================================================================
# API ROUTES: AUTHORIZATIONS & BENEFITS
# ============================================================================

def register_authorization_api_routes(app):
    """Register authorization and benefits API routes"""
    
    @app.route('/api/check-benefits', methods=['GET'])
    @login_required
    def check_benefits():
        """Get insurance benefits"""
        try:
            return success_response({
                'plan_name': 'Premium Health Plus',
                'copay': {'primary': 25, 'specialist': 50, 'emergency': 250},
                'deductible': {'individual': 1500, 'family': 3000, 'met': 750},
                'coverage': {'preventive': 100, 'inpatient': 80, 'outpatient': 70}
            })
        except Exception as e:
            log_error("Error checking benefits", e)
            return error_response(str(e), 500)
    
    @app.route('/api/pre-authorizations', methods=['GET'])
    @login_required
    def get_pre_authorizations():
        """Get user pre-authorizations"""
        try:
            user_id = AuthenticationManager.get_current_user()['id']
            authorizations = db.authorizations.get_user_authorizations(user_id)
            
            return success_response({'authorizations': authorizations or []})
        except Exception as e:
            log_error("Error getting pre-authorizations", e)
            return error_response(str(e), 500)
    
    @app.route('/api/create-preauth', methods=['POST'])
    @login_required
    def create_preauth():
        """Create pre-authorization request"""
        try:
            data = request.get_json()
            user_id = AuthenticationManager.get_current_user()['id']
            
            auth = {
                'id': generate_unique_id(),
                'user_id': user_id,
                'procedure': data.get('procedure'),
                'doctor': data.get('doctor'),
                'date_needed': data.get('date_needed'),
                'status': 'pending',
                'created_at': get_current_datetime()
            }
            
            db.authorizations.create_authorization(auth)
            
            return success_response(auth, 'Pre-authorization created')
        except Exception as e:
            log_error("Error creating pre-authorization", e)
            return error_response(str(e), 500)


# ============================================================================
# API ROUTES: MCP SERVER MANAGEMENT
# ============================================================================

def register_mcp_api_routes(app):
    """Register MCP server management API routes"""
    
    @app.route('/api/mcp-server-status', methods=['GET'])
    def mcp_server_status():
        """Check if MCP server is running"""
        import socket
        
        # Check if MCP server is running on port 3001
        mcp_port = 3001
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', mcp_port))
            sock.close()
            
            if result == 0:
                return success_response({'running': True, 'port': mcp_port})
            else:
                return success_response({'running': False, 'port': mcp_port})
        except Exception as e:
            log_error("Error checking MCP server status", e)
            return success_response({'running': False, 'error': str(e)})
    
    @app.route('/api/mcp-server-start', methods=['POST'])
    def mcp_server_start():
        """Start MCP server if not running"""
        import subprocess
        import os
        import socket
        import threading
        
        mcp_port = 3001
        
        try:
            # First check if already running
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', mcp_port))
            sock.close()
            
            if result == 0:
                return success_response({'status': 'already_running', 'port': mcp_port})
            
            # Try to start MCP server in background
            mcp_server_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mcp_server.py')
            
            if os.path.exists(mcp_server_path):
                # Start in background thread to avoid blocking
                def start_server():
                    try:
                        subprocess.Popen(['python', mcp_server_path], cwd=os.path.dirname(mcp_server_path))
                    except Exception as e:
                        log_error("Failed to start MCP server", e)
                
                thread = threading.Thread(target=start_server, daemon=True)
                thread.start()
                
                return success_response({'status': 'starting', 'port': mcp_port}, 'MCP server is starting...')
            else:
                # MCP server script not found - this is not an error, just inform user
                log_info(f"MCP server script not found at {mcp_server_path}")
                return success_response({
                    'status': 'not_available',
                    'port': mcp_port,
                    'message': 'MCP server is not installed in this deployment'
                })
        except Exception as e:
            log_error("Error starting MCP server", e)
            return error_response(str(e), 500)


# ============================================================================
# STATIC & ERROR ROUTES
# ============================================================================

def register_static_and_error_routes(app):
    """Register static file and error handling routes"""
    
    @app.route('/favicon.ico')
    def favicon():
        """Serve favicon"""
        try:
            return send_from_directory(
                app.static_folder,
                'favicon.svg',
                mimetype='image/svg+xml'
            )
        except:
            return '', 204
    
    @app.errorhandler(404)
    def not_found(error):
        """404 error handler"""
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def server_error(error):
        """500 error handler"""
        log_error(f"500 error: {error}")
        return render_template('500.html'), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        """403 error handler"""
        return error_response('Access forbidden', 403)
    
    @app.errorhandler(401)
    def unauthorized(error):
        """401 error handler"""
        return error_response('Unauthorized', 401)


# ============================================================================
# ROUTE REGISTRATION MAIN
# ============================================================================

def register_all_routes(app):
    """Register all routes with Flask app"""
    
    log_info("Registering authentication routes...")
    register_auth_routes(app)
    
    log_info("Registering dashboard routes...")
    register_dashboard_routes(app)
    
    log_info("Registering patient API routes...")
    register_patient_api_routes(app)
    
    log_info("Registering Copilot AI routes...")
    register_copilot_api_routes(app)
    
    log_info("Registering authorization API routes...")
    register_authorization_api_routes(app)
    
    log_info("Registering MCP server routes...")
    register_mcp_api_routes(app)
    
    log_info("Registering static and error routes...")
    register_static_and_error_routes(app)
    
    log_info("All routes registered successfully")
