#!/usr/bin/env python3
"""
Demo API for Medical Reporting Module
Simple voice demo endpoints for testing
"""

import os
import logging
import tempfile
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime

logger = logging.getLogger(__name__)

# Create blueprint
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

@demo_bp.route('/voice/simulate', methods=['POST'])
def demo_voice_simulate():
    """Demo voice simulation with SA enhancement"""
    try:
        data = request.get_json()
        text = data.get('text', 'No text provided')
        
        # Simulate SA medical terminology enhancement
        enhanced_text = _enhance_sa_medical_text(text)
        
        return jsonify({
            'success': True,
            'original_text': text,
            'enhanced_text': enhanced_text,
            'sa_terms_found': _count_sa_medical_terms(text),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Demo voice simulate error: {e}")
        return jsonify({'error': str(e)}), 500

@demo_bp.route('/voice/transcribe', methods=['POST'])
def demo_voice_transcribe():
    """Real voice transcription using Whisper"""
    try:
        # Check if audio file is provided
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400
        
        # Save audio file temporarily
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            audio_file.save(temp_file.name)
            temp_audio_path = temp_file.name
        
        try:
            # Get STT service
            service_manager = getattr(current_app, 'service_manager', None)
            if not service_manager:
                return jsonify({'error': 'Service manager not available'}), 500
            
            stt_service = service_manager.get_service('stt_service')
            if not stt_service:
                return jsonify({'error': 'STT service not available'}), 500
            
            # Transcribe audio
            transcription = stt_service.transcribe_audio_file(temp_audio_path)
            
            if transcription:
                # Enhance with SA medical terminology
                enhanced_text = _enhance_sa_medical_text(transcription)
                
                return jsonify({
                    'success': True,
                    'transcription': transcription,
                    'enhanced_text': enhanced_text,
                    'sa_terms_found': _count_sa_medical_terms(transcription),
                    'timestamp': datetime.utcnow().isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'No transcription generated'
                }), 400
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_audio_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Demo voice transcribe error: {e}")
        return jsonify({'error': str(e)}), 500

def _enhance_sa_medical_text(text):
    """Enhance text with South African medical terminology"""
    
    # SA medical term replacements
    sa_replacements = {
        'tb': 'tuberculosis',
        'mva': 'motor vehicle accident',
        'gsw': 'gunshot wound',
        'pcp': 'Pneumocystis pneumonia',
        'hiv': 'HIV',
        'aids': 'AIDS',
        'chest xray': 'chest X-ray',
        'x ray': 'X-ray',
        'ct scan': 'CT scan',
        'mri scan': 'MRI scan'
    }
    
    enhanced = text.lower()
    
    for term, replacement in sa_replacements.items():
        enhanced = enhanced.replace(term, replacement)
    
    # Capitalize first letter of sentences
    sentences = enhanced.split('. ')
    capitalized = [s.capitalize() for s in sentences if s.strip()]
    
    return '. '.join(capitalized)

def _count_sa_medical_terms(text):
    """Count South African medical terms in text"""
    
    sa_terms = [
        'tuberculosis', 'tb', 'pneumonia', 'silicosis', 'asbestosis',
        'hiv', 'aids', 'kaposi', 'pcp', 'pneumocystis',
        'mva', 'motor vehicle', 'gsw', 'gunshot', 'trauma',
        'chest', 'lung', 'heart', 'fracture', 'injury'
    ]
    
    text_lower = text.lower()
    count = 0
    
    for term in sa_terms:
        if term in text_lower:
            count += 1
    
    return count