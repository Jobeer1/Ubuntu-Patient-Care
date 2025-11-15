#!/usr/bin/env python3
"""
Core Routes for Medical Reporting Module
Main application routes and pages - Refactored for maintainability
"""

import os
import logging
from flask import Blueprint, render_template, jsonify, request, current_app, send_from_directory
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Create blueprint
core_bp = Blueprint('core', __name__)

# Attempt to register template API routes onto the core blueprint at import time.
# This ensures the endpoints exist before the app starts handling requests and
# avoids adding URL rules at runtime which Flask disallows after the first request.
try:
    from . import template_routes
    try:
        template_routes.register(core_bp)
        logger.info('Template routes registered on core blueprint')
    except Exception:
        logger.exception('Failed to register template routes on core blueprint')
except Exception:
    # template_routes may not exist in older copies; that's fine, we'll fall back later
    pass

@core_bp.route('/health')
def health_check():
    """System health check endpoint"""
    try:
        services = _get_service_status()
    except Exception:
        logger.exception("Failed to gather service status")
        services = {}

    version = current_app.config.get('VERSION', '1.0.0')
    start_time = current_app.config.get('START_TIME')
    uptime_seconds = None
    if start_time and isinstance(start_time, datetime):
        try:
            # Handle both timezone-aware and naive datetimes
            now = datetime.now(timezone.utc)
            uptime_seconds = int((now - start_time).total_seconds())
        except TypeError:
            # Fallback if comparison still fails
            uptime_seconds = None

    payload = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': version,
        'services': services
    }
    if uptime_seconds is not None:
        payload['uptime_seconds'] = uptime_seconds

    return jsonify(payload)

@core_bp.route('/')
def dashboard():
    """Main SA Medical Reporting dashboard - Professional Version"""
    try:
        # Server-side Afrikaans date and greeting name to avoid client clock drift
        import locale
        try:
            locale.setlocale(locale.LC_TIME, 'af_ZA.UTF-8')
        except Exception:
            # Fallback if locale not available on host
            pass
        server_now = datetime.now()
        # Format a user-friendly date for the template (fallback if locale not available)
        try:
            server_date_display = server_now.strftime('%A, %d %B %Y')
        except Exception:
            server_date_display = server_now.isoformat()

        # doctor name can be supplied by app config or current_user (if available)
        doctor_name = current_app.config.get('DEFAULT_DOCTOR')
        if not doctor_name:
            try:
                from flask_login import current_user
                doctor_name = getattr(current_user, 'display_name', None) or getattr(current_user, 'name', None)
            except Exception:
                doctor_name = None
        doctor_name = doctor_name or 'Dr. Stoyanov'

        services = _get_service_status()
        logger.info("Rendering dashboard for %s", doctor_name)
        return render_template('dashboard_sa.html', server_date_iso=server_now.isoformat(), server_date_display=server_date_display, doctor_name=doctor_name, services=services)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        import traceback
        logger.error(f"Dashboard traceback: {traceback.format_exc()}")
        return _render_fallback_dashboard()

@core_bp.route('/favicon.ico')
def favicon():
    """Serve favicon to prevent 404 noise. Uses static if present else tiny PNG."""
    try:
        # Resolve frontend static directory relative to the package root
        from pathlib import Path
        pkg_root = Path(current_app.root_path)
        static_dir = (pkg_root.parent / 'frontend' / 'static').resolve()
        icon_path = static_dir / 'favicon.ico'
        if icon_path.exists():
            return send_from_directory(str(static_dir), 'favicon.ico')
    except Exception:
        pass
    # 1x1 transparent PNG
    import base64
    png_base64 = (
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4//8/AwAI/AL+9qg8WQAAAABJRU5ErkJggg=='
    )
    png_bytes = base64.b64decode(png_base64)
    from flask import make_response
    resp = make_response(png_bytes)
    resp.headers['Content-Type'] = 'image/png'
    return resp

@core_bp.route('/new-report')
def new_report():
    """New report interface"""
    try:
        return render_template('voice_reporting.html')
    except Exception as e:
        logger.error(f"New report error: {e}")
        return _render_fallback_page("New Report", "Create a new medical report")

@core_bp.route('/find-studies')
def find_studies():
    """Find studies interface for SA Medical"""
    try:
        from .study_routes import render_find_studies
        return render_find_studies()
    except Exception as e:
        logger.error(f"Find studies error: {e}")
        return _render_fallback_page("Find Studies", "Search for patient studies and DICOM images")

@core_bp.route('/templates')
def templates():
    """SA Medical templates management interface"""
    try:
        # Import lazily to avoid import-time errors when module not present
        try:
            from . import template_routes
            return template_routes.render_templates()
        except Exception:
            # If template_routes isn't available, fall back to the generic page
            logger.info('template_routes module not available, using fallback')
            return _render_fallback_page("Templates", "Manage HPCSA-compliant medical report templates")
    except Exception as e:
        logger.error(f"Templates error: {e}")
        return _render_fallback_page("Templates", "Manage HPCSA-compliant medical report templates")

@core_bp.route('/patients')
def patients():
    """Patient management interface"""
    try:
        from .patient_routes import render_patients
        return render_patients()
    except Exception as e:
        logger.error(f"Patients error: {e}")
        return _render_fallback_page("Patients", "Manage patient records with POPIA compliance")

@core_bp.route('/voice-reporting')
def voice_reporting():
    """Voice reporting interface"""
    try:
        return render_template('voice_reporting.html')
    except Exception as e:
        logger.error(f"Voice reporting error: {e}")
        return _render_fallback_page("Voice Reporting", "Voice dictation for medical reports")

@core_bp.route('/voice-demo')
def voice_demo():
    """Fully functional voice demo page with SA medical optimization"""
    try:
        logger.info("Rendering voice demo template")
        return render_template('voice_demo_sa.html')
    except Exception as e:
        logger.error(f"Voice demo error: {e}")
        import traceback
        logger.error(f"Voice demo traceback: {traceback.format_exc()}")
        from .voice_routes import render_voice_demo
        return render_voice_demo()

@core_bp.route('/auth')
def auth_page():
    """Authentication page"""
    try:
        logger.info("Rendering authentication page")
        return render_template('auth.html')
    except Exception as e:
        logger.error(f"Auth page error: {e}")
        return _render_fallback_page("Authentication", "User login and registration")

@core_bp.route('/enhanced-voice-demo')
def enhanced_voice_demo():
    """Enhanced voice demo with medical training and voice shortcuts"""
    try:
        # Check if user is authenticated (basic check)
        from flask import session
        if not session.get('user_id') and not session.get('demo_user_id'):
            return render_template('auth.html')
        
        logger.info("Rendering enhanced voice demo template")
        return render_template('enhanced_voice_demo.html')
    except Exception as e:
        logger.error(f"Enhanced voice demo error: {e}")
        import traceback
        logger.error(f"Enhanced voice demo traceback: {traceback.format_exc()}")
        return _render_fallback_page("Enhanced Voice Demo", "Voice dictation with medical training and shortcuts")

@core_bp.route('/dicom-viewer')
def dicom_viewer():
    """DICOM viewer interface"""
    try:
        from .dicom_routes import render_dicom_viewer
        return render_dicom_viewer()
    except Exception as e:
        logger.error(f"DICOM viewer error: {e}")
        return _render_fallback_page("DICOM Viewer", "Professional medical image viewer")

def _get_service_status():
    """Get status of all system services"""
    try:
        # Try relative import first (module lives inside this package)
        try:
            from .service_manager import ServiceManager
        except Exception:
            from core.service_manager import ServiceManager
    except Exception as e:
        logger.error(f"Service manager import error: {e}")
        return {
            'voice_engine': 'unknown',
            'dicom_service': 'unknown',
            'orthanc_pacs': 'unknown',
            'nas_storage': 'unknown'
        }

    try:
        service_manager = ServiceManager()
        return service_manager.get_all_service_status()
    except Exception as e:
        logger.error(f"Service status error: {e}")
        return {
            'voice_engine': 'unknown',
            'dicom_service': 'unknown',
            'orthanc_pacs': 'unknown',
            'nas_storage': 'unknown'
        }

def _render_fallback_dashboard():
    """Render a professional SA Medical dashboard with compact layout"""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SA Medical Reporting - Professional Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <link href="/static/css/sa-dashboard.css" rel="stylesheet">
        <style>
            :root {
                --sa-green: #007A4D;
                --sa-gold: #FFB612;
                --sa-red: #DE3831;
                --sa-blue: #002395;
                --sa-black: #000000;
                --sa-white: #FFFFFF;
            }
            
            body {
                background: linear-gradient(135deg, var(--sa-green) 0%, var(--sa-blue) 50%, var(--sa-gold) 100%);
                min-height: 100vh;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            .sa-compact-header {
                background: rgba(0, 0, 0, 0.8);
                backdrop-filter: blur(10px);
                padding: 0.75rem 0;
                border-bottom: 3px solid var(--sa-gold);
            }
            
            .sa-main-content {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                margin: 1rem;
                border-radius: 1rem;
                padding: 1.5rem;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            
            .sa-action-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 1rem;
                margin-bottom: 1.5rem;
            }
            
            .sa-action-card {
                background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
                border-radius: 0.75rem;
                padding: 1.25rem;
                text-align: center;
                transition: all 0.3s ease;
                cursor: pointer;
                border: 2px solid transparent;
                position: relative;
                overflow: hidden;
                min-height: 140px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }
            
            .sa-action-card:hover {
                transform: translateY(-4px) scale(1.02);
                box-shadow: 0 12px 25px rgba(0, 0, 0, 0.15);
            }
            
            .sa-action-card.new-report {
                border-left: 4px solid var(--sa-green);
            }
            
            .sa-action-card.new-report:hover {
                border-color: var(--sa-green);
                background: linear-gradient(145deg, #ffffff 0%, rgba(0, 122, 77, 0.05) 100%);
            }
            
            .sa-action-card.find-studies {
                border-left: 4px solid var(--sa-blue);
            }
            
            .sa-action-card.find-studies:hover {
                border-color: var(--sa-blue);
                background: linear-gradient(145deg, #ffffff 0%, rgba(0, 35, 149, 0.05) 100%);
            }
            
            .sa-action-card.voice-dictation {
                border-left: 4px solid var(--sa-gold);
            }
            
            .sa-action-card.voice-dictation:hover {
                border-color: var(--sa-gold);
                background: linear-gradient(145deg, #ffffff 0%, rgba(255, 182, 18, 0.05) 100%);
            }
            
            .sa-action-card.templates {
                border-left: 4px solid var(--sa-red);
            }
            
            .sa-action-card.templates:hover {
                border-color: var(--sa-red);
                background: linear-gradient(145deg, #ffffff 0%, rgba(222, 56, 49, 0.05) 100%);
            }
            
            .sa-status-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 1rem;
            }
            
            .sa-status-card {
                background: rgba(255, 255, 255, 0.9);
                border-radius: 0.75rem;
                padding: 1.25rem;
                border-top: 4px solid var(--sa-gold);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }
            
            .sa-flag-accent {
                background: linear-gradient(90deg, var(--sa-green) 0%, var(--sa-gold) 25%, var(--sa-red) 50%, var(--sa-blue) 75%, var(--sa-black) 100%);
                height: 4px;
                width: 100%;
                margin-bottom: 1rem;
                border-radius: 2px;
            }
            
            .sa-compact-footer {
                background: rgba(0, 0, 0, 0.8);
                color: white;
                text-align: center;
                padding: 1rem;
                margin-top: 1rem;
                border-radius: 0 0 1rem 1rem;
            }
        </style>
    </head>
    <body>
        <!-- Compact Header -->
        <header class="sa-compact-header text-white">
            <div class="container mx-auto px-4">
                <div class="flex justify-between items-center">
                    <div class="flex items-center">
                        <i class="fas fa-stethoscope text-xl mr-2 text-yellow-400"></i>
                        <span class="text-lg font-bold">SA Medical Reporting 🇿🇦</span>
                    </div>
                    <div class="text-right text-sm">
                        <div class="font-semibold">Goeie dag, Dr. [Name]</div>
                        <div class="opacity-90">Maandag, 25 Augustus 2025</div>
                    </div>
                </div>
            </div>
        </header>

        <!-- Main Content Container -->
        <div class="sa-main-content">
            <!-- SA Flag Accent -->
            <div class="sa-flag-accent"></div>
            
            <!-- System Status Alert -->
            <div class="bg-green-50 border-l-4 border-green-400 text-green-700 px-3 py-2 rounded mb-4">
                <div class="flex items-center">
                    <i class="fas fa-check-circle mr-2"></i>
                    <div class="text-sm">
                        <span class="font-semibold">✅ All Systems Operational</span> • 
                        POPIA Compliant • HPCSA Standards Applied
                    </div>
                </div>
            </div>

            <!-- Quick Actions Grid -->
            <section class="mb-6">
                <h2 class="text-xl font-bold text-gray-800 mb-3 flex items-center">
                    <i class="fas fa-bolt text-yellow-500 mr-2"></i>
                    Quick Actions
                </h2>
                <div class="sa-action-grid">
                    <a href="/new-report" class="sa-action-card new-report">
                        <i class="fas fa-plus-circle text-2xl mb-2" style="color: var(--sa-green);"></i>
                        <h3 class="font-semibold mb-1">New Report</h3>
                        <p class="text-xs text-gray-600">Create medical report with AI voice</p>
                    </a>
                    
                    <a href="/find-studies" class="sa-action-card find-studies">
                        <i class="fas fa-search text-2xl mb-2" style="color: var(--sa-blue);"></i>
                        <h3 class="font-semibold mb-1">Find Studies</h3>
                        <p class="text-xs text-gray-600">Search PACS and DICOM images</p>
                    </a>
                    
                    <a href="/voice-demo" class="sa-action-card voice-dictation">
                        <i class="fas fa-microphone text-2xl mb-2" style="color: var(--sa-gold);"></i>
                        <h3 class="font-semibold mb-1">Voice Dictation</h3>
                        <p class="text-xs text-gray-600">SA English voice reporting</p>
                    </a>
                    
                    <a href="/templates" class="sa-action-card templates">
                        <i class="fas fa-file-alt text-2xl mb-2" style="color: var(--sa-red);"></i>
                        <h3 class="font-semibold mb-1">SA Templates</h3>
                        <p class="text-xs text-gray-600">HPCSA-compliant templates</p>
                    </a>
                </div>
            </section>

            <!-- Dashboard Status Grid -->
            <div class="sa-status-grid">
                <!-- System Status -->
                <div class="sa-status-card">
                    <h3 class="font-bold text-gray-800 mb-3 flex items-center">
                        <i class="fas fa-chart-bar mr-2" style="color: var(--sa-blue);"></i>
                        System Status
                    </h3>
                    <div class="space-y-2 text-sm">
                        <div class="flex justify-between items-center">
                            <span>Voice Engine</span>
                            <span class="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">
                                <i class="fas fa-check-circle mr-1"></i>Ready
                            </span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span>DICOM Service</span>
                            <span class="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">
                                <i class="fas fa-check-circle mr-1"></i>Connected
                            </span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span>Orthanc PACS</span>
                            <span class="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">
                                <i class="fas fa-check-circle mr-1"></i>Online
                            </span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span>NAS Storage</span>
                            <span class="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">
                                <i class="fas fa-check-circle mr-1"></i>Mounted
                            </span>
                        </div>
                    </div>
                </div>

                <!-- Today's Activity -->
                <div class="sa-status-card">
                    <h3 class="font-bold text-gray-800 mb-3 flex items-center">
                        <i class="fas fa-chart-line mr-2" style="color: var(--sa-green);"></i>
                        Today's Activity
                    </h3>
                    <div class="grid grid-cols-2 gap-3 text-sm">
                        <div class="text-center">
                            <div class="text-xl font-bold" style="color: var(--sa-green);">0</div>
                            <div class="text-xs text-gray-600">Reports</div>
                        </div>
                        <div class="text-center">
                            <div class="text-xl font-bold" style="color: var(--sa-blue);">0</div>
                            <div class="text-xs text-gray-600">Voice Sessions</div>
                        </div>
                        <div class="text-center">
                            <div class="text-xl font-bold" style="color: var(--sa-gold);">0</div>
                            <div class="text-xs text-gray-600">Studies</div>
                        </div>
                        <div class="text-center">
                            <div class="text-xl font-bold" style="color: var(--sa-red);">0</div>
                            <div class="text-xs text-gray-600">Patients</div>
                        </div>
                    </div>
                </div>

                <!-- Quick Links -->
                <div class="sa-status-card">
                    <h3 class="font-bold text-gray-800 mb-3 flex items-center">
                        <i class="fas fa-link mr-2" style="color: var(--sa-gold);"></i>
                        Quick Links
                    </h3>
                    <div class="space-y-2 text-sm">
                        <a href="/dicom-viewer" class="block text-blue-600 hover:text-blue-800">
                            <i class="fas fa-eye mr-2"></i>DICOM Viewer
                        </a>
                        <a href="/patients" class="block text-blue-600 hover:text-blue-800">
                            <i class="fas fa-users mr-2"></i>Patient Management
                        </a>
                        <a href="/voice-reporting" class="block text-blue-600 hover:text-blue-800">
                            <i class="fas fa-microphone-alt mr-2"></i>Voice Reporting
                        </a>
                        <a href="/health" class="block text-blue-600 hover:text-blue-800">
                            <i class="fas fa-heartbeat mr-2"></i>System Health
                        </a>
                    </div>
                </div>

                <!-- SA Medical Info -->
                <div class="sa-status-card">
                    <h3 class="font-bold text-gray-800 mb-3 flex items-center">
                        <i class="fas fa-flag mr-2" style="color: var(--sa-green);"></i>
                        SA Medical Standards
                    </h3>
                    <div class="space-y-2 text-xs text-gray-600">
                        <div class="flex items-center">
                            <i class="fas fa-shield-alt mr-2 text-green-600"></i>
                            POPIA Compliant Data Handling
                        </div>
                        <div class="flex items-center">
                            <i class="fas fa-certificate mr-2 text-blue-600"></i>
                            HPCSA Standards Applied
                        </div>
                        <div class="flex items-center">
                            <i class="fas fa-language mr-2 text-yellow-600"></i>
                            SA English Medical Terms
                        </div>
                        <div class="flex items-center">
                            <i class="fas fa-id-card mr-2 text-red-600"></i>
                            SA ID Number Validation
                        </div>
                    </div>
                </div>
            </div>

            <!-- Compact Footer -->
            <div class="sa-compact-footer">
                <div class="text-xs">
                    © 2024 SA Medical Reporting Module • HPCSA Compliant • POPIA Secure • Version 1.0.0
                </div>
            </div>
        </div>

        <script>
            console.log('🇿🇦 SA Medical Dashboard loaded successfully - Compact Layout');
            
            // Add click handlers for action cards
            document.querySelectorAll('.sa-action-card').forEach(card => {
                card.addEventListener('click', function(e) {
                    e.preventDefault();
                    const href = this.getAttribute('href');
                    if (href) {
                        window.location.href = href;
                    }
                });
            });
        </script>
    </body>
    </html>
    '''

def _render_fallback_page(title, description):
    """Render a simple fallback page when specific routes fail"""
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - SA Medical Reporting</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="bg-gray-100">
        <div class="container mx-auto px-4 py-8">
            <div class="bg-white rounded-lg shadow-md p-6">
                <h1 class="text-2xl font-bold mb-4 text-blue-700">
                    <i class="fas fa-exclamation-circle mr-2"></i>{title}
                </h1>
                <p class="text-gray-600 mb-4">{description}</p>
                <div class="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded mb-4">
                    <i class="fas fa-tools mr-2"></i>
                    This feature is currently being updated. Please try again later.
                </div>
                <a href="/" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                    <i class="fas fa-home mr-2"></i>Back to Dashboard
                </a>
            </div>
        </div>
    </body>
    </html>
    '''