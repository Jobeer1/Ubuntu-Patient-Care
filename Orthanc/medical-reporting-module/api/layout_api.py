"""
Layout API for Medical Reporting Module
Handles customizable screen layouts and viewport management
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime
import logging
import uuid
from typing import Dict, List, Any, Optional
from api.auth_api import require_auth

logger = logging.getLogger(__name__)

layout_bp = Blueprint('layout', __name__)

# Mock layout database
MOCK_LAYOUTS = {}

def create_mock_layout(layout_id: str, user_id: str, **kwargs) -> Dict[str, Any]:
    """Create a mock layout structure"""
    return {
        'id': layout_id,
        'name': kwargs.get('name', 'Untitled Layout'),
        'description': kwargs.get('description', ''),
        'user_id': user_id,
        'is_default': kwargs.get('is_default', False),
        'is_public': kwargs.get('is_public', False),
        'layout_type': kwargs.get('layout_type', 'custom'),  # custom, preset, examination_specific
        'examination_type': kwargs.get('examination_type', ''),
        'viewport_config': kwargs.get('viewport_config', {
            'rows': 2,
            'columns': 2,
            'viewports': [
                {'id': 'vp1', 'row': 0, 'col': 0, 'width': 1, 'height': 1},
                {'id': 'vp2', 'row': 0, 'col': 1, 'width': 1, 'height': 1},
                {'id': 'vp3', 'row': 1, 'col': 0, 'width': 1, 'height': 1},
                {'id': 'vp4', 'row': 1, 'col': 1, 'width': 1, 'height': 1}
            ]
        }),
        'panel_config': kwargs.get('panel_config', {
            'report_panel': {'visible': True, 'width': 300, 'position': 'right'},
            'template_panel': {'visible': True, 'width': 250, 'position': 'left'},
            'tools_panel': {'visible': True, 'height': 60, 'position': 'top'},
            'status_panel': {'visible': True, 'height': 30, 'position': 'bottom'}
        }),
        'window_config': kwargs.get('window_config', {
            'multi_monitor': False,
            'primary_monitor': {'width': 1920, 'height': 1080},
            'secondary_monitor': None
        }),
        'preferences': kwargs.get('preferences', {
            'auto_sync_scroll': True,
            'auto_sync_zoom': True,
            'auto_window_level': True,
            'default_tool': 'pan',
            'mouse_bindings': {
                'left': 'window_level',
                'middle': 'pan',
                'right': 'zoom'
            }
        }),
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'usage_count': kwargs.get('usage_count', 0)
    }

# Initialize with some mock layouts
def initialize_mock_layouts():
    """Initialize mock layouts for demo"""
    layouts = [
        {
            'name': 'Standard 2x2',
            'description': 'Standard 2x2 viewport layout for general use',
            'is_public': True,
            'layout_type': 'preset',
            'viewport_config': {
                'rows': 2,
                'columns': 2,
                'viewports': [
                    {'id': 'vp1', 'row': 0, 'col': 0, 'width': 1, 'height': 1},
                    {'id': 'vp2', 'row': 0, 'col': 1, 'width': 1, 'height': 1},
                    {'id': 'vp3', 'row': 1, 'col': 0, 'width': 1, 'height': 1},
                    {'id': 'vp4', 'row': 1, 'col': 1, 'width': 1, 'height': 1}
                ]
            }
        },
        {
            'name': 'Single Large View',
            'description': 'Single viewport for detailed examination',
            'is_public': True,
            'layout_type': 'preset',
            'viewport_config': {
                'rows': 1,
                'columns': 1,
                'viewports': [
                    {'id': 'vp1', 'row': 0, 'col': 0, 'width': 1, 'height': 1}
                ]
            }
        },
        {
            'name': 'Chest X-Ray Layout',
            'description': 'Optimized layout for chest X-ray reporting',
            'is_public': True,
            'layout_type': 'examination_specific',
            'examination_type': 'chest_xray',
            'viewport_config': {
                'rows': 1,
                'columns': 2,
                'viewports': [
                    {'id': 'vp1', 'row': 0, 'col': 0, 'width': 1, 'height': 1},
                    {'id': 'vp2', 'row': 0, 'col': 1, 'width': 1, 'height': 1}
                ]
            },
            'panel_config': {
                'report_panel': {'visible': True, 'width': 350, 'position': 'right'},
                'template_panel': {'visible': True, 'width': 200, 'position': 'left'},
                'tools_panel': {'visible': True, 'height': 60, 'position': 'top'},
                'status_panel': {'visible': True, 'height': 30, 'position': 'bottom'}
            }
        }
    ]
    
    for i, layout_data in enumerate(layouts):
        layout_id = str(uuid.uuid4())
        user_id = '1'  # Default to doctor1
        MOCK_LAYOUTS[layout_id] = create_mock_layout(layout_id, user_id, **layout_data)

# Initialize mock data
initialize_mock_layouts()

@layout_bp.route('/', methods=['GET'])
@require_auth
def list_layouts():
    """List layouts with filtering"""
    try:
        user_id = session['user_id']
        
        # Get query parameters
        layout_type = request.args.get('layout_type')
        examination_type = request.args.get('examination_type')
        public_only = request.args.get('public_only', 'false').lower() == 'true'
        
        # Filter layouts
        filtered_layouts = []
        for layout in MOCK_LAYOUTS.values():
            # Show public layouts or user's own layouts
            if not (layout['is_public'] or layout['user_id'] == user_id):
                if public_only:
                    continue
            
            # Apply filters
            if layout_type and layout['layout_type'] != layout_type:
                continue
            if examination_type and layout['examination_type'] != examination_type:
                continue
            
            filtered_layouts.append(layout)
        
        # Sort by usage count and name
        filtered_layouts.sort(key=lambda x: (-x['usage_count'], x['name']))
        
        return jsonify({
            'layouts': filtered_layouts,
            'total': len(filtered_layouts)
        })
        
    except Exception as e:
        logger.error(f"Layout listing error: {e}")
        return jsonify({'error': 'Failed to retrieve layouts'}), 500

@layout_bp.route('/', methods=['POST'])
@require_auth
def create_layout():
    """Create a new layout"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({'error': 'Layout name required'}), 400
        
        # Generate layout ID
        layout_id = str(uuid.uuid4())
        
        # Create layout
        layout = create_mock_layout(
            layout_id=layout_id,
            user_id=user_id,
            **data
        )
        
        MOCK_LAYOUTS[layout_id] = layout
        
        logger.info(f"Created layout {layout_id} by user {user_id}")
        
        return jsonify({'layout': layout}), 201
        
    except Exception as e:
        logger.error(f"Layout creation error: {e}")
        return jsonify({'error': 'Failed to create layout'}), 500

@layout_bp.route('/<layout_id>', methods=['GET'])
@require_auth
def get_layout(layout_id):
    """Get a specific layout"""
    try:
        user_id = session['user_id']
        
        layout = MOCK_LAYOUTS.get(layout_id)
        if not layout:
            return jsonify({'error': 'Layout not found'}), 404
        
        # Check permissions
        if not layout['is_public'] and layout['user_id'] != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Increment usage count
        layout['usage_count'] += 1
        
        return jsonify({'layout': layout})
        
    except Exception as e:
        logger.error(f"Layout retrieval error: {e}")
        return jsonify({'error': 'Failed to retrieve layout'}), 500

@layout_bp.route('/<layout_id>', methods=['PUT'])
@require_auth
def update_layout(layout_id):
    """Update a layout"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Update data required'}), 400
        
        layout = MOCK_LAYOUTS.get(layout_id)
        if not layout:
            return jsonify({'error': 'Layout not found'}), 404
        
        # Check permissions - only creator can update
        if layout['user_id'] != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Update allowed fields
        allowed_fields = [
            'name', 'description', 'is_default', 'is_public', 'layout_type',
            'examination_type', 'viewport_config', 'panel_config', 
            'window_config', 'preferences'
        ]
        
        for field in allowed_fields:
            if field in data:
                layout[field] = data[field]
        
        layout['updated_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Updated layout {layout_id} by user {user_id}")
        
        return jsonify({'layout': layout})
        
    except Exception as e:
        logger.error(f"Layout update error: {e}")
        return jsonify({'error': 'Failed to update layout'}), 500

@layout_bp.route('/<layout_id>', methods=['DELETE'])
@require_auth
def delete_layout(layout_id):
    """Delete a layout"""
    try:
        user_id = session['user_id']
        user_role = session['role']
        
        layout = MOCK_LAYOUTS.get(layout_id)
        if not layout:
            return jsonify({'error': 'Layout not found'}), 404
        
        # Check permissions - only creator or admin can delete
        if layout['user_id'] != user_id and user_role != 'admin':
            return jsonify({'error': 'Access denied'}), 403
        
        # Don't allow deletion of default layouts
        if layout['is_default']:
            return jsonify({'error': 'Cannot delete default layouts'}), 400
        
        del MOCK_LAYOUTS[layout_id]
        
        logger.info(f"Deleted layout {layout_id} by user {user_id}")
        
        return jsonify({'success': True, 'message': 'Layout deleted successfully'})
        
    except Exception as e:
        logger.error(f"Layout deletion error: {e}")
        return jsonify({'error': 'Failed to delete layout'}), 500

@layout_bp.route('/<layout_id>/duplicate', methods=['POST'])
@require_auth
def duplicate_layout(layout_id):
    """Duplicate an existing layout"""
    try:
        user_id = session['user_id']
        
        layout = MOCK_LAYOUTS.get(layout_id)
        if not layout:
            return jsonify({'error': 'Layout not found'}), 404
        
        # Check permissions
        if not layout['is_public'] and layout['user_id'] != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Create duplicate
        new_layout_id = str(uuid.uuid4())
        new_layout = create_mock_layout(
            layout_id=new_layout_id,
            user_id=user_id,
            name=f"{layout['name']} (Copy)",
            description=layout['description'],
            is_default=False,  # Copies are not default
            is_public=False,   # Copies are private by default
            layout_type='custom',  # Copies become custom
            examination_type=layout['examination_type'],
            viewport_config=layout['viewport_config'].copy(),
            panel_config=layout['panel_config'].copy(),
            window_config=layout['window_config'].copy(),
            preferences=layout['preferences'].copy()
        )
        
        MOCK_LAYOUTS[new_layout_id] = new_layout
        
        logger.info(f"Duplicated layout {layout_id} to {new_layout_id} by user {user_id}")
        
        return jsonify({'layout': new_layout}), 201
        
    except Exception as e:
        logger.error(f"Layout duplication error: {e}")
        return jsonify({'error': 'Failed to duplicate layout'}), 500

@layout_bp.route('/<layout_id>/set-default', methods=['POST'])
@require_auth
def set_default_layout(layout_id):
    """Set a layout as default for the user"""
    try:
        user_id = session['user_id']
        
        layout = MOCK_LAYOUTS.get(layout_id)
        if not layout:
            return jsonify({'error': 'Layout not found'}), 404
        
        # Check permissions
        if not layout['is_public'] and layout['user_id'] != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Clear existing default for this user
        for existing_layout in MOCK_LAYOUTS.values():
            if existing_layout['user_id'] == user_id and existing_layout['is_default']:
                existing_layout['is_default'] = False
        
        # Set new default
        layout['is_default'] = True
        layout['updated_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Set layout {layout_id} as default for user {user_id}")
        
        return jsonify({'layout': layout})
        
    except Exception as e:
        logger.error(f"Set default layout error: {e}")
        return jsonify({'error': 'Failed to set default layout'}), 500

@layout_bp.route('/presets', methods=['GET'])
@require_auth
def get_preset_layouts():
    """Get available preset layouts"""
    try:
        preset_layouts = [layout for layout in MOCK_LAYOUTS.values() 
                         if layout['layout_type'] == 'preset' and layout['is_public']]
        
        return jsonify({
            'presets': preset_layouts,
            'total': len(preset_layouts)
        })
        
    except Exception as e:
        logger.error(f"Preset layouts error: {e}")
        return jsonify({'error': 'Failed to retrieve preset layouts'}), 500

@layout_bp.route('/examination-types', methods=['GET'])
@require_auth
def get_examination_types():
    """Get available examination-specific layouts"""
    try:
        user_id = session['user_id']
        
        examination_layouts = {}
        for layout in MOCK_LAYOUTS.values():
            if (layout['layout_type'] == 'examination_specific' and 
                layout['examination_type'] and
                (layout['is_public'] or layout['user_id'] == user_id)):
                
                exam_type = layout['examination_type']
                if exam_type not in examination_layouts:
                    examination_layouts[exam_type] = []
                examination_layouts[exam_type].append(layout)
        
        return jsonify({
            'examination_layouts': examination_layouts,
            'examination_types': list(examination_layouts.keys())
        })
        
    except Exception as e:
        logger.error(f"Examination layouts error: {e}")
        return jsonify({'error': 'Failed to retrieve examination layouts'}), 500

@layout_bp.route('/viewport-presets', methods=['GET'])
@require_auth
def get_viewport_presets():
    """Get common viewport configuration presets"""
    try:
        presets = {
            'single': {
                'name': 'Single Viewport',
                'rows': 1,
                'columns': 1,
                'viewports': [
                    {'id': 'vp1', 'row': 0, 'col': 0, 'width': 1, 'height': 1}
                ]
            },
            '1x2': {
                'name': '1x2 Layout',
                'rows': 1,
                'columns': 2,
                'viewports': [
                    {'id': 'vp1', 'row': 0, 'col': 0, 'width': 1, 'height': 1},
                    {'id': 'vp2', 'row': 0, 'col': 1, 'width': 1, 'height': 1}
                ]
            },
            '2x1': {
                'name': '2x1 Layout',
                'rows': 2,
                'columns': 1,
                'viewports': [
                    {'id': 'vp1', 'row': 0, 'col': 0, 'width': 1, 'height': 1},
                    {'id': 'vp2', 'row': 1, 'col': 0, 'width': 1, 'height': 1}
                ]
            },
            '2x2': {
                'name': '2x2 Layout',
                'rows': 2,
                'columns': 2,
                'viewports': [
                    {'id': 'vp1', 'row': 0, 'col': 0, 'width': 1, 'height': 1},
                    {'id': 'vp2', 'row': 0, 'col': 1, 'width': 1, 'height': 1},
                    {'id': 'vp3', 'row': 1, 'col': 0, 'width': 1, 'height': 1},
                    {'id': 'vp4', 'row': 1, 'col': 1, 'width': 1, 'height': 1}
                ]
            },
            '3x3': {
                'name': '3x3 Layout',
                'rows': 3,
                'columns': 3,
                'viewports': [
                    {'id': f'vp{i+1}', 'row': i//3, 'col': i%3, 'width': 1, 'height': 1}
                    for i in range(9)
                ]
            }
        }
        
        return jsonify({'viewport_presets': presets})
        
    except Exception as e:
        logger.error(f"Viewport presets error: {e}")
        return jsonify({'error': 'Failed to retrieve viewport presets'}), 500