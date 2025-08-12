#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - Web Interface Blueprint

All HTML interfaces organized in a single blueprint for clean separation.
"""

from flask import Blueprint, render_template_string
import logging

logger = logging.getLogger(__name__)

# Create blueprint for web interfaces
web_bp = Blueprint('web_interfaces', __name__)

@web_bp.route('/')
def main_interface():
    """Serve the main login/dashboard application"""
    from .templates.main_interface import MAIN_INTERFACE_TEMPLATE
    return render_template_string(MAIN_INTERFACE_TEMPLATE)

@web_bp.route('/user-management')
def user_management_interface():
    """Serve user management interface"""
    from .templates.user_management import USER_MANAGEMENT_TEMPLATE
    return render_template_string(USER_MANAGEMENT_TEMPLATE)

@web_bp.route('/nas-config')
def nas_config_interface():
    """Serve NAS configuration interface"""
    from .templates.nas_config import NAS_CONFIG_TEMPLATE
    return render_template_string(NAS_CONFIG_TEMPLATE)

@web_bp.route('/device-management')
def device_management_interface():
    """Serve device management interface"""
    from .templates.device_management import DEVICE_MANAGEMENT_TEMPLATE
    return render_template_string(DEVICE_MANAGEMENT_TEMPLATE)

@web_bp.route('/reporting-dashboard')
def reporting_dashboard_interface():
    """Serve reporting dashboard interface"""
    from .templates.reporting_dashboard import REPORTING_DASHBOARD_TEMPLATE
    return render_template_string(REPORTING_DASHBOARD_TEMPLATE)

@web_bp.route('/system-status')
def system_status_interface():
    """Serve system status interface"""
    from .templates.system_status import SYSTEM_STATUS_TEMPLATE
    return render_template_string(SYSTEM_STATUS_TEMPLATE)