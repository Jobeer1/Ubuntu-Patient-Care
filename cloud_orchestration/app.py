"""
Ubuntu Patient Care - Demo Flask Application with SSO & Gemini AI
Run this to launch the interactive demo dashboard.

Usage:
    python app.py
    
Then open: http://localhost:8080
"""

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from authlib.integrations.flask_client import OAuth
import os
import sys
import configparser
import google.generativeai as genai
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load configuration
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
config.read(config_path)

app = Flask(__name__, 
            template_folder='demo/templates',
            static_folder='demo/static')

# Configuration from config.ini
app.config['SECRET_KEY'] = config.get('OAuth', 'secret_key', fallback='ubuntu-patient-care-demo-2025')
app.config['DEBUG'] = config.getboolean('App', 'debug', fallback=True)

# Configure Gemini AI
gemini_key = config.get('Google', 'gemini_key', fallback=None)
if gemini_key:
    genai.configure(api_key=gemini_key)
    gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
else:
    gemini_model = None

# OAuth Setup
oauth = OAuth(app)

# Google OAuth
google = oauth.register(
    name='google',
    client_id=config.get('OAuth', 'google_client_id', fallback=''),
    client_secret=config.get('OAuth', 'google_client_secret', fallback=''),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Microsoft OAuth
microsoft = oauth.register(
    name='microsoft',
    client_id=config.get('OAuth', 'microsoft_client_id', fallback=''),
    client_secret=config.get('OAuth', 'microsoft_client_secret', fallback=''),
    server_metadata_url='https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)


@app.route('/')
def index():
    """
    Redirect to medical schemes dashboard or login.
    """
    user = session.get('user')
    if user:
        return redirect(url_for('medical_schemes'))
    return redirect(url_for('login'))


@app.route('/medical-schemes')
def medical_schemes():
    """
    Medical scheme automation dashboard.
    """
    user = session.get('user')
    if not user:
        # Allow demo access without login
        user = {'name': 'Demo User', 'email': 'demo@ubuntu-patient-care.co.za'}
    return render_template('medical_schemes.html', user=user)


@app.route('/login')
def login():
    """
    Login page with SSO options.
    """
    return render_template('login.html')


@app.route('/login/google')
def login_google():
    """
    Initiate Google OAuth login.
    """
    redirect_uri = url_for('auth_google', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/auth/google/callback')
def auth_google():
    """
    Google OAuth callback.
    """
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        session['user'] = {
            'name': user_info.get('name'),
            'email': user_info.get('email'),
            'picture': user_info.get('picture'),
            'provider': 'google'
        }
        return redirect(url_for('medical_schemes'))
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/login/microsoft')
def login_microsoft():
    """
    Initiate Microsoft OAuth login.
    """
    redirect_uri = url_for('auth_microsoft', _external=True)
    return microsoft.authorize_redirect(redirect_uri)


@app.route('/auth/microsoft/callback')
def auth_microsoft():
    """
    Microsoft OAuth callback.
    """
    try:
        token = microsoft.authorize_access_token()
        user_info = token.get('userinfo')
        session['user'] = {
            'name': user_info.get('name'),
            'email': user_info.get('email'),
            'picture': user_info.get('picture'),
            'provider': 'microsoft'
        }
        return redirect(url_for('medical_schemes'))
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/logout')
def logout():
    """
    Logout and clear session.
    """
    session.pop('user', None)
    return redirect(url_for('login'))


@app.route('/api/health')
def health():
    """
    Health check endpoint.
    """
    return jsonify({
        'status': 'healthy',
        'service': 'Ubuntu Patient Care Demo',
        'version': '1.0.0'
    })


@app.route('/api/simulate-upload', methods=['POST'])
def simulate_upload():
    """
    API endpoint to simulate clinic data upload.
    In production, this would trigger the actual drive_monitor.py
    """
    data = request.get_json() or {}
    
    return jsonify({
        'success': True,
        'message': 'Data upload simulated',
        'records': data.get('records', 50),
        'timestamp': '2025-11-17T10:30:00Z'
    })


@app.route('/api/start-training', methods=['POST'])
def start_training():
    """
    API endpoint to start training job.
    In production, this would trigger vertex_pipeline_definition.py
    """
    data = request.get_json() or {}
    
    return jsonify({
        'success': True,
        'job_id': f'vertex-ai-job-{os.urandom(4).hex()}',
        'message': 'Training job submitted',
        'accelerator': 'NVIDIA_TESLA_T4',
        'machine_type': 'n1-highmem-8'
    })


@app.route('/api/generate-audit', methods=['POST'])
def generate_audit():
    """
    API endpoint to generate audit artifact.
    In production, this would trigger opus_audit_artifact.py
    """
    data = request.get_json() or {}
    
    return jsonify({
        'success': True,
        'artifact_id': f'audit-{os.urandom(4).hex()}',
        'workflow_id': 'STT-OPTIMIZER-PIPELINE-V1',
        'validation_score': 0.963,
        'review_action': 'AUTO_APPROVED',
        'popia_compliant': True
    })


@app.route('/api/gemini-analyze', methods=['POST'])
def gemini_analyze():
    """
    Use Gemini 2.0 Flash to analyze training data quality.
    """
    if not gemini_model:
        return jsonify({
            'success': False,
            'error': 'Gemini API not configured'
        }), 400
    
    data = request.get_json() or {}
    text = data.get('text', '')
    
    try:
        prompt = f"""Analyze this medical transcription for quality and accuracy:

Text: {text}

Provide:
1. Quality score (0-100)
2. Key medical terms identified
3. Potential errors or concerns
4. Recommendations for improvement

Format as JSON."""
        
        response = gemini_model.generate_content(prompt)
        
        return jsonify({
            'success': True,
            'analysis': response.text,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/gemini-chat', methods=['POST'])
def gemini_chat():
    """
    Chat with Gemini connected to MCP server tools
    """
    data = request.get_json() or {}
    question = data.get('question', '')
    patient_context = data.get('context', {})
    
    try:
        from gemini_mcp_client import GeminiMCPClient
        client = GeminiMCPClient()
        
        response = client.get_medical_scheme_advice(question, patient_context)
        
        return jsonify({
            'success': True,
            'response': response,
            'timestamp': datetime.now().isoformat(),
            'mcp_connected': True
        })
    except Exception as e:
        # Fallback to regular Gemini if MCP not available
        if gemini_model:
            try:
                response = gemini_model.generate_content(f"""You are a medical scheme advisor for South African patients.

Question: {question}

Provide helpful advice about South African medical schemes (Discovery, Bonitas, Momentum, etc.)""")
                
                return jsonify({
                    'success': True,
                    'response': response.text,
                    'timestamp': datetime.now().isoformat(),
                    'mcp_connected': False
                })
            except:
                pass
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/gemini-suggest', methods=['POST'])
def gemini_suggest():
    """
    Use Gemini to suggest training improvements.
    """
    if not gemini_model:
        return jsonify({
            'success': False,
            'error': 'Gemini API not configured'
        }), 400
    
    data = request.get_json() or {}
    accuracy = data.get('accuracy', 0.88)
    
    try:
        prompt = f"""As an AI training expert, suggest improvements for a medical transcription model with {accuracy*100}% accuracy.

Current challenges:
- South African medical terminology
- Rural clinic environment
- Limited training data

Provide 3-5 specific, actionable recommendations."""
        
        response = gemini_model.generate_content(prompt)
        
        return jsonify({
            'success': True,
            'suggestions': response.text,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Medical Scheme Automation Routes
@app.route('/api/medical-scheme/check-benefits', methods=['POST'])
def check_benefits():
    """
    Check patient benefits using Gemini + Selenium automation
    """
    data = request.get_json() or {}
    
    try:
        from medical_scheme_automation import MedicalSchemePortalAutomation
        automation = MedicalSchemePortalAutomation()
        
        result = automation.check_patient_benefits(
            scheme=data.get('scheme', 'discovery'),
            patient_id=data.get('patient_id', ''),
            member_number=data.get('member_number', '')
        )
        
        automation.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/medical-scheme/request-authorization', methods=['POST'])
def request_authorization():
    """
    Request procedure authorization using Gemini + Selenium
    """
    data = request.get_json() or {}
    
    try:
        from medical_scheme_automation import MedicalSchemePortalAutomation
        automation = MedicalSchemePortalAutomation()
        
        result = automation.request_authorization(
            scheme=data.get('scheme', 'discovery'),
            patient_data=data.get('patient_data', {}),
            procedure=data.get('procedure', {})
        )
        
        automation.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/medical-scheme/submit-claim', methods=['POST'])
def submit_claim():
    """
    Submit medical claim using Gemini + Selenium
    """
    data = request.get_json() or {}
    
    try:
        from medical_scheme_automation import MedicalSchemePortalAutomation
        automation = MedicalSchemePortalAutomation()
        
        result = automation.submit_claim(
            scheme=data.get('scheme', 'discovery'),
            claim_data=data.get('claim_data', {})
        )
        
        automation.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/medical-scheme/register-practice', methods=['POST'])
def register_practice():
    """
    Auto-register practice with multiple medical schemes
    """
    data = request.get_json() or {}
    
    try:
        from medical_scheme_automation import MedicalSchemePortalAutomation
        automation = MedicalSchemePortalAutomation()
        
        result = automation.register_practice(
            practice_data=data.get('practice_data', {}),
            schemes=data.get('schemes', ['discovery', 'bonitas', 'momentum'])
        )
        
        automation.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    """
    404 error handler.
    """
    return jsonify({
        'error': 'Not found',
        'message': 'The requested resource was not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """
    500 error handler.
    """
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500


def main():
    """
    Main entry point for the Flask application.
    """
    host = config.get('App', 'host', fallback='0.0.0.0')
    port = config.getint('App', 'port', fallback=8080)
    
    print("\n" + "="*70)
    print("  🏥 UBUNTU PATIENT CARE - AI GENESIS HACKATHON DEMO")
    print("="*70)
    print("  Starting Flask server with SSO & Gemini AI...")
    print("  ")
    print(f"  📍 Local URL:  http://localhost:{port}")
    print(f"  📍 Network URL: http://127.0.0.1:{port}")
    print("  ")
    print("  🔐 SSO Enabled: Google & Microsoft")
    print("  🤖 Gemini 2.0 Flash: " + ("Enabled" if gemini_model else "Disabled"))
    print("  ")
    print("  Press Ctrl+C to stop the server")
    print("="*70 + "\n")
    
    # Run the Flask app
    app.run(
        host=host,
        port=port,
        debug=True,
        use_reloader=True
    )


if __name__ == '__main__':
    main()
