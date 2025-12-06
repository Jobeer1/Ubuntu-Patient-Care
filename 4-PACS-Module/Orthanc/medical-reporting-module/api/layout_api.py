#!/usr/bin/env python3
"""
Layout API for Medical Reporting Module
Handles UI layout configurations and preferences
"""

from flask import Blueprint, request, jsonify
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

layout_bp = Blueprint('layout', __name__)


@layout_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'layout_api',
        'timestamp': datetime.utcnow().isoformat()
    })


@layout_bp.route('/preferences', methods=['GET'])
def get_layout_preferences():
    """Get user layout preferences"""
    try:
        user_id = request.args.get('user_id', 'demo_user')
        
        # Default layout preferences
        preferences = {
            'theme': 'light',
            'sidebar_collapsed': False,
            'panel_positions': {
                'transcription': {'x': 0, 'y': 0, 'width': 60, 'height': 70},
                'controls': {'x': 60, 'y': 0, 'width': 40, 'height': 30},
                'status': {'x': 60, 'y': 30, 'width': 40, 'height': 40}
            },
            'font_size': 'medium',
            'auto_save': True,
            'show_visualizer': True
        }
        
        return jsonify({
            'user_id': user_id,
            'preferences': preferences
        })
        
    except Exception as e:
        logger.error(f"Error getting layout preferences: {e}")
        return jsonify({'error': 'Failed to get preferences'}), 500


@layout_bp.route('/preferences', methods=['POST'])
def save_layout_preferences():
    """Save user layout preferences"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'demo_user')
        preferences = data.get('preferences', {})
        
        # In a real implementation, save to database
        # For now, just return success
        
        return jsonify({
            'message': 'Layout preferences saved successfully',
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Error saving layout preferences: {e}")
        return jsonify({'error': 'Failed to save preferences'}), 500


@layout_bp.route('/themes', methods=['GET'])
def list_themes():
    """List available themes"""
    themes = [
        {
            'id': 'light',
            'name': 'Light Theme',
            'description': 'Clean light interface',
            'primary_color': '#007bff',
            'background_color': '#ffffff'
        },
        {
            'id': 'dark',
            'name': 'Dark Theme',
            'description': 'Easy on the eyes dark mode',
            'primary_color': '#0d6efd',
            'background_color': '#212529'
        },
        {
            'id': 'medical',
            'name': 'Medical Theme',
            'description': 'Professional medical interface',
            'primary_color': '#28a745',
            'background_color': '#f8f9fa'
        }
    ]
    
    return jsonify({'themes': themes})


@layout_bp.route('/components', methods=['GET'])
def list_components():
    """List available UI components"""
    components = [
        {
            'id': 'transcription_panel',
            'name': 'Transcription Panel',
            'type': 'panel',
            'resizable': True,
            'movable': True
        },
        {
            'id': 'control_panel',
            'name': 'Control Panel',
            'type': 'panel',
            'resizable': True,
            'movable': True
        },
        {
            'id': 'status_panel',
            'name': 'Status Panel',
            'type': 'panel',
            'resizable': True,
            'movable': True
        },
        {
            'id': 'audio_visualizer',
            'name': 'Audio Visualizer',
            'type': 'widget',
            'resizable': False,
            'movable': False
        }
    ]
    
    return jsonify({'components': components})


@layout_bp.route('/reset', methods=['POST'])
def reset_layout():
    """Reset layout to default"""
    try:
        user_id = request.json.get('user_id', 'demo_user') if request.json else 'demo_user'
        
        # Reset to default layout
        return jsonify({
            'message': 'Layout reset to default',
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Error resetting layout: {e}")
        return jsonify({'error': 'Failed to reset layout'}), 500


@layout_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Layout resource not found'}), 404


@layout_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Layout service error'}), 500