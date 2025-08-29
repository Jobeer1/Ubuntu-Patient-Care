"""
Web page routes blueprint for the South African Medical Imaging System
Refactored to use external templates and static files for better maintainability
"""

from flask import Blueprint, render_template, render_template_string, session, redirect, url_for

web_bp = Blueprint('web', __name__)

@web_bp.route('/login')
def login_page():
    """Login page for all users (admin, doctors, users)"""
    return render_template('login.html')

@web_bp.route('/')
def dashboard():
    """Main dashboard page - requires authentication"""
    if 'authenticated' not in session:
        return redirect(url_for('web.login_page'))
    
    return render_template('dashboard.html')

@web_bp.route('/nas-integration')
def nas_integration():
    """Enhanced NAS integration management page for medical image handling"""
    if 'authenticated' not in session:
        return redirect(url_for('web.login_page'))
    
    # Admin-only access for network discovery
    if session.get('user_type') != 'admin':
        return redirect(url_for('web.dashboard'))
    
    return render_template('nas_integration.html')

@web_bp.route('/share/<share_id>')
def patient_download_page(share_id):
    """Patient download page for shared medical images"""
    return render_template('patient_share.html', share_id=share_id)

@web_bp.route('/nas-test-api')
def nas_test_api():
    """NAS API testing interface"""
    if 'authenticated' not in session:
        return redirect(url_for('web.login_page'))
    
    if session.get('user_type') != 'admin':
        return redirect(url_for('web.dashboard'))
    
    return render_template('nas_test_api.html')


@web_bp.route('/patients')
def patients_page():
    """Compatibility route: older links may point to /patients — serve patient viewer."""
    if 'authenticated' not in session:
        return redirect(url_for('web.login_page'))
    # Try to render the Jinja template file if available, otherwise use the
    # embedded template string from the web_interfaces package for compatibility.
    try:
        return render_template('patient_viewer.html')
    except Exception:
        try:
            # Import the embedded template string
            from web_interfaces.templates.patient_viewer import PATIENT_VIEWER_TEMPLATE
            return render_template_string(PATIENT_VIEWER_TEMPLATE)
        except Exception:
            # As a last resort return a minimal placeholder page
            return render_template_string('<h1>Patient Viewer</h1><p>Template missing.</p>')


@web_bp.route('/dicom-viewer')
def dicom_viewer_page():
    """Compatibility route for older DICOM viewer links.

    Tries, in order:
    1. Render `dicom_viewer.html` Jinja template if present
    2. Use embedded `DICOM_VIEWER_TEMPLATE` from `web_interfaces.templates.dicom_viewer`
    3. Serve the static `offline-dicom-viewer/index.html` file from the repo
    """
    if 'authenticated' not in session:
        return redirect(url_for('web.login_page'))

    # 1) Try Jinja template file
    try:
        return render_template('dicom_viewer.html')
    except Exception:
        pass

    # 2) Try embedded template string
    try:
        from web_interfaces.templates.dicom_viewer import DICOM_VIEWER_TEMPLATE
        return render_template_string(DICOM_VIEWER_TEMPLATE)
    except Exception:
        pass

    # 3) Try to serve the offline-dicom-viewer static index if present
    try:
        import os
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        static_index = os.path.join(base, 'offline-dicom-viewer', 'index.html')
        if os.path.exists(static_index):
            with open(static_index, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception:
        pass

    # Final fallback
    return render_template_string('<h1>DICOM Viewer</h1><p>Viewer not available.</p>'), 404


@web_bp.route('/reporting')
def reporting_page():
    """Compatibility route for reporting dashboard links.

    Tries: Jinja `reporting.html` -> embedded `REPORTING_DASHBOARD_TEMPLATE` -> redirect to `/reporting-dashboard`.
    """
    if 'authenticated' not in session:
        return redirect(url_for('web.login_page'))

    # 1) Try Jinja template file
    try:
        return render_template('reporting.html')
    except Exception:
        pass

    # 2) Try embedded template
    try:
        from web_interfaces.templates.reporting_dashboard import REPORTING_DASHBOARD_TEMPLATE
        return render_template_string(REPORTING_DASHBOARD_TEMPLATE)
    except Exception:
        pass

    # 3) Redirect to the interface blueprint's route
    return redirect(url_for('web_interfaces.reporting_dashboard_interface'))


@web_bp.route('/device-discovery')
def device_discovery_page():
    """Compatibility route for device discovery / management links.

    Serves the device discovery/management UI. Fallbacks:
    1. `device_discovery.html` Jinja template
    2. Embedded `DEVICE_MANAGEMENT_TEMPLATE` from web_interfaces
    3. Redirect to `/device-management`
    """
    if 'authenticated' not in session:
        return redirect(url_for('web.login_page'))

    # 1) Try Jinja template
    try:
        return render_template('device_discovery.html')
    except Exception:
        pass

    # 2) Try embedded device management template
    try:
        from web_interfaces.templates.device_management import DEVICE_MANAGEMENT_TEMPLATE
        return render_template_string(DEVICE_MANAGEMENT_TEMPLATE)
    except Exception:
        pass

    # 3) Redirect to the interface blueprint's device management route
    return redirect(url_for('web_interfaces.device_management_interface'))


@web_bp.route('/device-management')
def device_management_page():
    """Serve the Device Management UI (compatibility).

    Tries:
    1. `device_management.html` Jinja template
    2. Embedded `DEVICE_MANAGEMENT_TEMPLATE` from `web_interfaces.templates.device_management`
    3. Redirect to the interface blueprint's `device_management_interface`
    """
    if 'authenticated' not in session:
        return redirect(url_for('web.login_page'))

    # 1) Try Jinja template file
    try:
        return render_template('device_management.html')
    except Exception:
        pass

    # 2) Try embedded template string
    try:
        from web_interfaces.templates.device_management import DEVICE_MANAGEMENT_TEMPLATE
        return render_template_string(DEVICE_MANAGEMENT_TEMPLATE)
    except Exception:
        pass

    # 3) Redirect to the blueprint route
    return redirect(url_for('web_interfaces.device_management_interface'))


@web_bp.route('/orthanc-manager')
def orthanc_manager_page():
    """Serve Orthanc management UI (compatibility route)."""
    if 'authenticated' not in session:
        return redirect(url_for('web.login_page'))

    # Try Jinja template first
    try:
        return render_template('orthanc_manager.html')
    except Exception:
        pass

    # Try embedded template from web_interfaces
    try:
        from web_interfaces.templates.orthanc_server_management import ORTHANC_SERVER_MANAGEMENT_TEMPLATE
        return render_template_string(ORTHANC_SERVER_MANAGEMENT_TEMPLATE)
    except Exception:
        pass

    # Redirect to interface blueprint
    return redirect(url_for('web_interfaces.orthanc_server_management_interface'))


@web_bp.route('/Orthanc manager')
def orthanc_manager_compat():
    """Compatibility path for legacy link with space/uppercase."""
    return redirect(url_for('web.orthanc_manager_page'))


@web_bp.route('/admin')
@web_bp.route('/admin/<path:subpath>')
def admin_page(subpath=None):
    """Serve the Admin UI (compatibility). Tries:
    1. Jinja `admin.html`
    2. Embedded admin/user-management template
    3. Frontend SPA `frontend/build/index.html` if present
    """
    if 'authenticated' not in session:
        return redirect(url_for('web.login_page'))

    # 1) Try Jinja template file
    try:
        return render_template('admin.html')
    except Exception:
        pass

    # 2) Try embedded templates from web_interfaces
    try:
        from web_interfaces.templates.user_management import USER_MANAGEMENT_TEMPLATE
        return render_template_string(USER_MANAGEMENT_TEMPLATE)
    except Exception:
        pass

    # 3) Try to serve frontend SPA index if present (built React/TS app)
    try:
        import os
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        spa_index = os.path.join(base, 'frontend', 'build', 'index.html')
        if os.path.exists(spa_index):
            with open(spa_index, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception:
        pass

    # Final fallback
    return render_template_string('<h1>Admin Panel</h1><p>Admin interface not available.</p>'), 404
