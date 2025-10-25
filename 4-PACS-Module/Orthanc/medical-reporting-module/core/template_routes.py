#!/usr/bin/env python3
"""
Simple Template Management Routes

Stores templates as JSON files under the Flask instance path (instance/report_templates).
Provides lightweight API for listing, creating, updating and deleting templates and
renders a small management UI.
"""
import os
import json
import uuid
import logging
from datetime import datetime
from flask import current_app, request, jsonify, render_template

logger = logging.getLogger(__name__)


def _templates_dir():
    p = os.path.join(current_app.instance_path, 'report_templates')
    os.makedirs(p, exist_ok=True)
    return p


def _template_path(template_id):
    return os.path.join(_templates_dir(), f"{template_id}.json")


def _read_template_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        logger.exception('Failed to read template file: %s', path)
        return None


def render_templates():
    """Render the templates management page"""
    try:
        return render_template('templates_manager.html')
    except Exception:
        logger.exception('Failed to render templates_manager.html')
        # Fallback simple page
        return ('<h3>Templates</h3><p>Template manager not available.</p>')


def list_templates():
    try:
        files = []
        for fname in os.listdir(_templates_dir()):
            if not fname.endswith('.json'):
                continue
            t = _read_template_file(os.path.join(_templates_dir(), fname))
            if t:
                files.append(t)
        # sort by name
        files.sort(key=lambda x: x.get('name', '').lower())
        return jsonify({'success': True, 'templates': files})
    except Exception as e:
        logger.exception('Failed to list templates: %s', e)
        return jsonify({'success': False, 'error': 'Failed to list templates'})


def create_template():
    try:
        # Accept multipart file upload or JSON/form fields
        name = None
        description = None
        content = None

        if request.is_json:
            data = request.get_json()
            name = data.get('name')
            description = data.get('description')
            content = data.get('content')
        else:
            name = request.form.get('name')
            description = request.form.get('description')

        if 'file' in request.files:
            f = request.files['file']
            content = f.stream.read().decode('utf-8')
            if not name:
                name = f.filename

        if content is None:
            content = request.form.get('content') or ''

        if not name:
            return jsonify({'success': False, 'error': 'Template name required'}), 400

        template_id = str(uuid.uuid4())
        payload = {
            'id': template_id,
            'name': name,
            'description': description or '',
            'content': content,
            'created_at': datetime.utcnow().isoformat()
        }
        path = _template_path(template_id)
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

        return jsonify({'success': True, 'template': payload})
    except Exception as e:
        logger.exception('Failed to create template: %s', e)
        return jsonify({'success': False, 'error': 'Failed to create template'})


def update_template(template_id):
    try:
        path = _template_path(template_id)
        if not os.path.exists(path):
            return jsonify({'success': False, 'error': 'Template not found'}), 404

        tpl = _read_template_file(path) or {}
        data = None
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        if 'name' in data:
            tpl['name'] = data.get('name')
        if 'description' in data:
            tpl['description'] = data.get('description')
        if 'content' in data:
            tpl['content'] = data.get('content')

        tpl['updated_at'] = datetime.utcnow().isoformat()
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(tpl, fh, ensure_ascii=False, indent=2)

        return jsonify({'success': True, 'template': tpl})
    except Exception as e:
        logger.exception('Failed to update template: %s', e)
        return jsonify({'success': False, 'error': 'Failed to update template'})


def delete_template(template_id):
    try:
        path = _template_path(template_id)
        if os.path.exists(path):
            os.remove(path)
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Template not found'}), 404
    except Exception as e:
        logger.exception('Failed to delete template: %s', e)
        return jsonify({'success': False, 'error': 'Failed to delete template'})


def register(bp):
    """Register API endpoints onto a provided blueprint (to avoid circular imports)."""
    bp.add_url_rule('/api/templates', endpoint='list_templates', view_func=list_templates, methods=['GET'])
    bp.add_url_rule('/api/templates', endpoint='create_template', view_func=create_template, methods=['POST'])
    bp.add_url_rule('/api/templates/<template_id>', endpoint='update_template', view_func=update_template, methods=['PUT'])
    bp.add_url_rule('/api/templates/<template_id>', endpoint='delete_template', view_func=delete_template, methods=['DELETE'])


def register_on_app(app):
    """Register API endpoints directly on a Flask app instance. Safe to call at runtime.

    This checks for existing view functions to avoid double-registration.
    """
    try:
        # use unique view function names on the app
        if 'template_list' not in app.view_functions:
            app.add_url_rule('/api/templates', endpoint='template_list', view_func=list_templates, methods=['GET'])
        if 'template_create' not in app.view_functions:
            app.add_url_rule('/api/templates', endpoint='template_create', view_func=create_template, methods=['POST'])
        if 'template_update' not in app.view_functions:
            app.add_url_rule('/api/templates/<template_id>', endpoint='template_update', view_func=update_template, methods=['PUT'])
        if 'template_delete' not in app.view_functions:
            app.add_url_rule('/api/templates/<template_id>', endpoint='template_delete', view_func=delete_template, methods=['DELETE'])
    except Exception:
        logger.exception('Failed to register template routes on app')


# Try to auto-register onto the core blueprint if available (helps when imported
# during app setup). This avoids adding URL rules after the first request.
try:
    from .routes import core_bp
    try:
        register(core_bp)
    except Exception:
        # ignore errors if already registered
        pass
except Exception:
    # core_bp not available at import time in some contexts
    pass

