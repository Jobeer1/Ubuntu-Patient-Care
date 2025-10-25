#!/usr/bin/env python3
"""
Demo API for Medical Reporting Module
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

demo_bp = Blueprint('demo', __name__)

@demo_bp.route('/voice/start', methods=['POST'])
def demo_voice_start():
    """Demo voice session start"""
    try:
        return jsonify({
            'success': True,
            'session_id': f'demo_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}',
            'message': 'Voice session started',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Demo voice start error: {e}")
        return jsonify({'error': str(e)}), 500

@demo_bp.route('/voice/transcribe', methods=['POST'])
def demo_voice_transcribe():
    """Demo voice transcription"""
    try:
        return jsonify({
            'success': True,
            'transcription': 'Demo transcription result',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Demo transcribe error: {e}")
        return jsonify({'error': str(e)}), 500