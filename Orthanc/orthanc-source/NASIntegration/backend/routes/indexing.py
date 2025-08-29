"""
Indexing blueprint: handles starting/stopping/indexing status for NAS indexing operations.
Extracted from nas_core.py to improve maintainability.
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

indexing_bp = Blueprint('nas_indexing', __name__)

# Simple in-memory indexing state for frontend polling (compat/demo)
indexing_state = {
    'state': 'idle',
    'progress': 0,
    'details': 'Idle',
    'started_at': None
}


@indexing_bp.route('/indexing/start', methods=['POST'])
def start_indexing():
    """Start indexing process"""
    try:
        data = request.get_json() or {}
        share_path = data.get('share_path') or data.get('sharePath') or data.get('path')
        username = data.get('username')
        # Note: password omitted from logs for security
        indexing_state['state'] = 'indexing'
        indexing_state['progress'] = 0
        indexing_state['details'] = f"Indexing started for {share_path or 'unknown share'}"
        indexing_state['started_at'] = datetime.utcnow()
        logger.info(f"Indexing started for share: {share_path}")
        return jsonify({
            'success': True,
            'message': 'Indexing started',
            'status': 'indexing'
        })
    except Exception as e:
        logger.error(f"Start indexing error: {e}")
        return jsonify({ 'success': False, 'error': str(e) }), 500


@indexing_bp.route('/indexing/stop', methods=['POST'])
def stop_indexing():
    """Stop indexing process"""
    try:
        indexing_state['state'] = 'idle'
        indexing_state['progress'] = 100
        indexing_state['details'] = 'Stopped by user'
        indexing_state['started_at'] = None
        return jsonify({
            'success': True,
            'message': 'Indexing stopped',
            'status': 'idle'
        })
    except Exception as e:
        logger.error(f"Stop indexing error: {e}")
        return jsonify({ 'success': False, 'error': str(e) }), 500


@indexing_bp.route('/start-indexing', methods=['POST'])
def start_indexing_compat():
    """Compatibility endpoint: /api/nas/start-indexing"""
    return start_indexing()


@indexing_bp.route('/indexing/status', methods=['GET'])
def indexing_status():
    """Return indexing status for frontend polling"""
    try:
        # Compute progress if indexing
        if indexing_state['state'] == 'indexing' and indexing_state['started_at']:
            elapsed = (datetime.utcnow() - indexing_state['started_at']).total_seconds()
            # simple simulated progress: 5% per second (demo); cap at 100
            prog = min(100, int(elapsed * 5))
            indexing_state['progress'] = prog
            if prog >= 100:
                indexing_state['state'] = 'completed'
                indexing_state['details'] = 'Indexing complete'
        return jsonify({
            'success': True,
            'status': {
                'state': indexing_state['state'],
                'progress': indexing_state['progress'],
                'details': indexing_state['details']
            }
        })
    except Exception as e:
        logger.error(f"Indexing status error: {e}")
        return jsonify({ 'success': False, 'error': str(e) }), 500
