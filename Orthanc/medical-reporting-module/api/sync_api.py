"""
Synchronization API for Medical Reporting Module
Handles offline/online synchronization and data conflict resolution
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
import logging
import uuid
from typing import Dict, List, Any, Optional
from api.auth_api import require_auth
from services.offline_manager import offline_manager

logger = logging.getLogger(__name__)

sync_bp = Blueprint('sync', __name__)

@sync_bp.route('/status', methods=['GET'])
@require_auth
def get_sync_status():
    """Get current synchronization status"""
    try:
        user_id = session['user_id']
        
        # Get sync status from offline manager
        status = offline_manager.get_sync_status()
        
        return jsonify({
            'sync_status': status,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Sync status error: {e}")
        return jsonify({'error': 'Failed to get sync status'}), 500

@sync_bp.route('/queue', methods=['GET'])
@require_auth
def get_sync_queue():
    """Get pending synchronization queue"""
    try:
        user_id = session['user_id']
        
        # Get sync queue from offline manager
        queue = offline_manager.get_sync_queue()
        
        # Filter by user if not admin
        user_role = session.get('role', 'radiologist')
        if user_role != 'admin':
            queue = [item for item in queue if item.get('user_id') == user_id]
        
        return jsonify({
            'queue': queue,
            'count': len(queue),
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Sync queue error: {e}")
        return jsonify({'error': 'Failed to get sync queue'}), 500

@sync_bp.route('/start', methods=['POST'])
@require_auth
def start_sync():
    """Start synchronization process"""
    try:
        user_id = session['user_id']
        data = request.get_json() or {}
        
        # Get sync options
        force_sync = data.get('force_sync', False)
        sync_type = data.get('sync_type', 'full')  # full, incremental, reports_only
        
        # Start synchronization
        success = offline_manager.start_sync(
            user_id=user_id,
            force_sync=force_sync,
            sync_type=sync_type
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Synchronization started',
                'sync_type': sync_type,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({'error': 'Failed to start synchronization'}), 500
        
    except Exception as e:
        logger.error(f"Start sync error: {e}")
        return jsonify({'error': 'Failed to start synchronization'}), 500

@sync_bp.route('/stop', methods=['POST'])
@require_auth
def stop_sync():
    """Stop synchronization process"""
    try:
        user_id = session['user_id']
        
        # Stop synchronization
        success = offline_manager.stop_sync()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Synchronization stopped',
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({'error': 'Failed to stop synchronization'}), 500
        
    except Exception as e:
        logger.error(f"Stop sync error: {e}")
        return jsonify({'error': 'Failed to stop synchronization'}), 500

@sync_bp.route('/conflicts', methods=['GET'])
@require_auth
def get_conflicts():
    """Get synchronization conflicts"""
    try:
        user_id = session['user_id']
        
        # Get conflicts from offline manager
        conflicts = offline_manager.get_conflicts()
        
        # Filter by user if not admin
        user_role = session.get('role', 'radiologist')
        if user_role != 'admin':
            conflicts = [conflict for conflict in conflicts if conflict.get('user_id') == user_id]
        
        return jsonify({
            'conflicts': conflicts,
            'count': len(conflicts),
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Conflicts retrieval error: {e}")
        return jsonify({'error': 'Failed to get conflicts'}), 500

@sync_bp.route('/conflicts/<conflict_id>/resolve', methods=['POST'])
@require_auth
def resolve_conflict(conflict_id):
    """Resolve a synchronization conflict"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        if not data or 'resolution' not in data:
            return jsonify({'error': 'Resolution strategy required'}), 400
        
        resolution = data['resolution']  # 'local', 'remote', 'merge', 'custom'
        custom_data = data.get('custom_data')
        
        # Resolve conflict
        success = offline_manager.resolve_conflict(
            conflict_id=conflict_id,
            resolution=resolution,
            user_id=user_id,
            custom_data=custom_data
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Conflict resolved',
                'conflict_id': conflict_id,
                'resolution': resolution
            })
        else:
            return jsonify({'error': 'Failed to resolve conflict'}), 500
        
    except Exception as e:
        logger.error(f"Conflict resolution error: {e}")
        return jsonify({'error': 'Failed to resolve conflict'}), 500

@sync_bp.route('/history', methods=['GET'])
@require_auth
def get_sync_history():
    """Get synchronization history"""
    try:
        user_id = session['user_id']
        
        # Get query parameters
        limit = int(request.args.get('limit', 50))
        days = int(request.args.get('days', 7))
        
        # Get sync history
        history = offline_manager.get_sync_history(
            user_id=user_id,
            limit=limit,
            days=days
        )
        
        return jsonify({
            'history': history,
            'count': len(history),
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Sync history error: {e}")
        return jsonify({'error': 'Failed to get sync history'}), 500

@sync_bp.route('/cache/status', methods=['GET'])
@require_auth
def get_cache_status():
    """Get cache status"""
    try:
        # Get cache status from offline manager
        cache_status = offline_manager.get_cache_status()
        
        return jsonify({
            'cache_status': cache_status,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Cache status error: {e}")
        return jsonify({'error': 'Failed to get cache status'}), 500

@sync_bp.route('/cache/clear', methods=['POST'])
@require_auth
def clear_cache():
    """Clear local cache"""
    try:
        user_id = session['user_id']
        data = request.get_json() or {}
        
        # Get clear options
        cache_type = data.get('cache_type', 'all')  # all, images, reports, templates
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({'error': 'Confirmation required to clear cache'}), 400
        
        # Clear cache
        success = offline_manager.clear_cache(
            cache_type=cache_type,
            user_id=user_id
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Cache cleared: {cache_type}',
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({'error': 'Failed to clear cache'}), 500
        
    except Exception as e:
        logger.error(f"Clear cache error: {e}")
        return jsonify({'error': 'Failed to clear cache'}), 500

@sync_bp.route('/offline-mode', methods=['POST'])
@require_auth
def toggle_offline_mode():
    """Toggle offline mode"""
    try:
        user_id = session['user_id']
        data = request.get_json() or {}
        
        offline_mode = data.get('offline_mode', True)
        
        # Set offline mode
        success = offline_manager.set_offline_mode(offline_mode)
        
        if success:
            return jsonify({
                'success': True,
                'offline_mode': offline_mode,
                'message': f'Offline mode {"enabled" if offline_mode else "disabled"}',
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({'error': 'Failed to toggle offline mode'}), 500
        
    except Exception as e:
        logger.error(f"Toggle offline mode error: {e}")
        return jsonify({'error': 'Failed to toggle offline mode'}), 500

@sync_bp.route('/connectivity', methods=['GET'])
@require_auth
def check_connectivity():
    """Check connectivity to external systems"""
    try:
        # Check connectivity to various systems
        connectivity = offline_manager.check_connectivity()
        
        return jsonify({
            'connectivity': connectivity,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Connectivity check error: {e}")
        return jsonify({'error': 'Failed to check connectivity'}), 500

@sync_bp.route('/settings', methods=['GET'])
@require_auth
def get_sync_settings():
    """Get synchronization settings"""
    try:
        user_id = session['user_id']
        
        # Get sync settings
        settings = offline_manager.get_sync_settings(user_id)
        
        return jsonify({
            'settings': settings,
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Sync settings error: {e}")
        return jsonify({'error': 'Failed to get sync settings'}), 500

@sync_bp.route('/settings', methods=['PUT'])
@require_auth
def update_sync_settings():
    """Update synchronization settings"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Settings data required'}), 400
        
        # Update sync settings
        success = offline_manager.update_sync_settings(user_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Sync settings updated',
                'settings': data
            })
        else:
            return jsonify({'error': 'Failed to update sync settings'}), 500
        
    except Exception as e:
        logger.error(f"Sync settings update error: {e}")
        return jsonify({'error': 'Failed to update sync settings'}), 500

@sync_bp.route('/stats', methods=['GET'])
@require_auth
def get_sync_stats():
    """Get synchronization statistics"""
    try:
        user_id = session['user_id']
        
        # Get sync statistics
        stats = offline_manager.get_sync_stats(user_id)
        
        return jsonify({
            'stats': stats,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Sync stats error: {e}")
        return jsonify({'error': 'Failed to get sync statistics'}), 500