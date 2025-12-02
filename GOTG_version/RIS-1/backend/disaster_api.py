"""
Emergency API Layer for Disaster RIS
Integrates all ML systems into Flask API
Handles offline operation, queuing, sync-when-online

Routes:
- Data Recovery APIs
- Biometric Identification
- Medical Extraction
- Data Fusion
- Family Reconstruction
- Medication Safety
- Critical Alerts
- Bandwidth Optimization
"""

import os
import json
import logging
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify
import sqlite3
import queue
import threading

# Import ML modules
from nas_recovery import DisasterRecoveryManager, DataSourceType
from fingerprint_engine import FingerprintTemplateGenerator, FingerprintMatcher, FingerprintDatabaseManager
from conditions_extraction import UnifiedMedicalExtractor
from data_fusion import SmartDataFusionEngine, MultiSourceProfileBuilder
from family_reconstruction import FamilyTreeReconstructor, FamilyReunificationCoordinator
from medication_safety import MedicationSafetyChecker, UrgencyScoringEngine
from bandwidth_optimization import CompressionEngine, StreamingTransfer, AdaptiveCompression

logger = logging.getLogger(__name__)

# Create blueprint
disaster_api = Blueprint('disaster', __name__, url_prefix='/api/disaster')

# Initialize ML engines
recovery_manager = DisasterRecoveryManager()
fingerprint_gen = FingerprintTemplateGenerator()
fingerprint_matcher = FingerprintMatcher()
fingerprint_db = FingerprintDatabaseManager()
medical_extractor = UnifiedMedicalExtractor()
fusion_engine = SmartDataFusionEngine()
profile_builder = MultiSourceProfileBuilder()
family_reconstructor = FamilyTreeReconstructor()
family_coordinator = FamilyReunificationCoordinator()
medication_checker = MedicationSafetyChecker()
urgency_scorer = UrgencyScoringEngine()
compression_engine = CompressionEngine()
streaming_transfer = StreamingTransfer()
adaptive_compression = AdaptiveCompression()

# Offline queuing
operation_queue = queue.Queue()
sync_status = {'pending_operations': 0, 'last_sync': None}

# =============================================
# Data Recovery Endpoints
# =============================================

@disaster_api.route('/recovery/initiate', methods=['POST'])
def initiate_data_recovery():
    """Initiate recovery from damaged data source"""
    
    try:
        data = request.get_json()
        source_path = data.get('source_path')
        source_type = data.get('source_type')
        
        if not source_path or not source_type:
            return jsonify({'error': 'Missing source_path or source_type'}), 400
        
        job_id = recovery_manager.initiate_recovery(source_path, source_type)
        
        # Queue for processing
        operation_queue.put({
            'type': 'recovery',
            'job_id': job_id,
            'source_path': source_path,
            'source_type': source_type,
            'created_at': datetime.utcnow().isoformat()
        })
        
        sync_status['pending_operations'] += 1
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'queued': True,
            'message': 'Recovery job queued. Will execute when online or immediately.'
        }), 200
    
    except Exception as e:
        logger.error(f"Recovery initiation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@disaster_api.route('/recovery/execute', methods=['POST'])
def execute_data_recovery():
    """Execute recovery immediately (if online) or return queued result"""
    
    try:
        data = request.get_json()
        source_path = data.get('source_path')
        source_type = data.get('source_type')
        
        success, recovered = recovery_manager.execute_recovery(source_path, source_type)
        
        if success:
            return jsonify({
                'success': True,
                'records_recovered': len(recovered),
                'records': [r.to_dict() for r in recovered],
                'quality_scores': [r.quality_score for r in recovered]
            }), 200
        else:
            return jsonify({'error': 'Recovery failed'}), 500
    
    except Exception as e:
        logger.error(f"Recovery execution error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =============================================
# Fingerprint Biometric Endpoints
# =============================================

@disaster_api.route('/biometric/enroll', methods=['POST'])
def enroll_fingerprint():
    """Enroll patient fingerprint for future matching"""
    
    try:
        patient_id = request.form.get('patient_id')
        finger_name = request.form.get('finger_name', 'left_thumb')
        
        if not patient_id:
            return jsonify({'error': 'Missing patient_id'}), 400
        
        # Get image from request
        if 'image' not in request.files:
            return jsonify({'error': 'Missing image file'}), 400
        
        image = request.files['image']
        image_data = image.read()
        
        # Generate template
        success, template_bytes, metrics = fingerprint_gen.generate_template(
            image_data, int(patient_id), finger_name
        )
        
        if success:
            # Store template
            stored_success, template_id = fingerprint_db.store_template(
                int(patient_id), finger_name, template_bytes,
                metrics.get('quality_score', 0.5)
            )
            
            if stored_success:
                return jsonify({
                    'success': True,
                    'template_id': template_id,
                    'finger': finger_name,
                    'quality_score': metrics.get('quality_score'),
                    'minutiae_count': metrics.get('minutiae_count'),
                    'message': 'Fingerprint enrolled successfully'
                }), 200
        
        return jsonify({'error': 'Failed to generate template', 'details': metrics}), 500
    
    except Exception as e:
        logger.error(f"Enrollment error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@disaster_api.route('/biometric/identify', methods=['POST'])
def identify_by_fingerprint():
    """Identify patient from fingerprint"""
    
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'Missing image file'}), 400
        
        image = request.files['image']
        image_data = image.read()
        
        # Generate template
        success, template_bytes, metrics = fingerprint_gen.generate_template(
            image_data, None, 'comparison'
        )
        
        if not success:
            return jsonify({'error': 'Failed to generate template'}), 400
        
        # Load templates for matching
        fingerprint_matcher.load_templates()
        
        # Match 1:N
        matches = fingerprint_matcher.match_1_to_n(template_bytes, limit=5)
        
        high_confidence_matches = [m for m in matches if m.matched]
        
        return jsonify({
            'success': True,
            'total_matches': len(matches),
            'high_confidence_matches': len(high_confidence_matches),
            'matches': [
                {
                    'patient_id': m.patient_id,
                    'confidence': m.confidence,
                    'matched': m.matched,
                    'distance': m.distance,
                    'minutiae_matched': m.num_minutiae_matched
                }
                for m in matches
            ],
            'extraction_metrics': metrics
        }), 200
    
    except Exception as e:
        logger.error(f"Identification error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =============================================
# Medical Information Extraction
# =============================================

@disaster_api.route('/medical/extract', methods=['POST'])
def extract_medical_info():
    """Extract medical conditions, medications, allergies from text"""
    
    try:
        data = request.get_json()
        text = data.get('text')
        
        if not text:
            return jsonify({'error': 'Missing text field'}), 400
        
        # Extract all medical information
        result = medical_extractor.extract_all(text)
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Extraction error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =============================================
# Data Fusion Endpoints
# =============================================

@disaster_api.route('/fusion/build-profile', methods=['POST'])
def build_patient_profile():
    """Build complete patient profile from multiple sources"""
    
    try:
        data = request.get_json()
        
        # Extract sources
        photo_data = data.get('photo_data')
        document_data = data.get('document_data')
        biometric_data = data.get('biometric_data')
        verbal_description = data.get('verbal_description')
        recovered_data = data.get('recovered_data')
        
        # Build profile
        fused = profile_builder.build_profile_from_sources(
            photo_data=photo_data,
            document_data=document_data,
            biometric_data=biometric_data,
            verbal_description=verbal_description,
            recovered_data=recovered_data
        )
        
        # Save to database
        success, fusion_id = fusion_engine.save_fused_record(fused)
        
        return jsonify({
            'success': success,
            'fusion_id': fusion_id,
            'profile': fused.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Profile building error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =============================================
# Family Reconstruction Endpoints
# =============================================

@disaster_api.route('/family/reconstruct', methods=['POST'])
def reconstruct_families():
    """Reconstruct family trees from patient list"""
    
    try:
        data = request.get_json()
        patients = data.get('patients', [])
        
        if not patients:
            return jsonify({'error': 'No patients provided'}), 400
        
        # Reconstruct families
        clusters = family_reconstructor.reconstruct_family_tree(patients)
        
        # Get reunification priorities
        reunifications = family_coordinator.prioritize_reunifications(clusters)
        
        return jsonify({
            'success': True,
            'family_clusters': len(clusters),
            'separated_families': sum(1 for c in clusters if c.separated_count > 1),
            'clusters': [
                {
                    'cluster_id': c.cluster_id,
                    'members': len(c.members),
                    'separated': c.separated_count,
                    'surname': c.primary_surname
                }
                for c in clusters
            ],
            'reunification_priorities': reunifications
        }), 200
    
    except Exception as e:
        logger.error(f"Family reconstruction error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =============================================
# Medication Safety Endpoints
# =============================================

@disaster_api.route('/safety/check-medications', methods=['POST'])
def check_medication_safety():
    """Check medications for interactions and allergies"""
    
    try:
        data = request.get_json()
        medications = data.get('medications', [])
        allergies = data.get('allergies', [])
        conditions = data.get('conditions', [])
        
        # Check safety
        alerts = medication_checker.check_patient_medications(
            medications, allergies, conditions
        )
        
        critical_alerts = [a for a in alerts if a.severity == 'critical']
        high_alerts = [a for a in alerts if a.severity == 'high']
        
        return jsonify({
            'success': True,
            'total_alerts': len(alerts),
            'critical_count': len(critical_alerts),
            'high_count': len(high_alerts),
            'alerts': [
                {
                    'type': a.alert_type,
                    'severity': a.severity,
                    'message': a.message,
                    'action': a.suggested_action
                }
                for a in alerts
            ]
        }), 200
    
    except Exception as e:
        logger.error(f"Safety check error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =============================================
# Urgency & Triage Endpoints
# =============================================

@disaster_api.route('/triage/urgency-score', methods=['POST'])
def calculate_urgency():
    """Calculate urgency score for patient triage"""
    
    try:
        patient_data = request.get_json()
        
        # Calculate urgency
        urgency = urgency_scorer.calculate_urgency(patient_data)
        
        return jsonify({
            'success': True,
            'urgency_level': urgency.urgency_level,  # 1-5
            'score': urgency.score,
            'critical_factors': urgency.critical_factors,
            'stable_factors': urgency.stable_factors,
            'reasoning': urgency.reasoning
        }), 200
    
    except Exception as e:
        logger.error(f"Urgency calculation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =============================================
# Bandwidth Optimization Endpoints
# =============================================

@disaster_api.route('/bandwidth/optimize', methods=['POST'])
def optimize_for_bandwidth():
    """Get optimization recommendations for available bandwidth"""
    
    try:
        data = request.get_json()
        patient_data = data.get('patient_data', {})
        bandwidth_kbps = data.get('bandwidth_kbps')
        
        if not bandwidth_kbps:
            return jsonify({'error': 'Missing bandwidth_kbps'}), 400
        
        # Get optimization strategy
        strategy = adaptive_compression.optimize_for_bandwidth(
            patient_data, bandwidth_kbps
        )
        
        return jsonify(strategy), 200
    
    except Exception as e:
        logger.error(f"Optimization error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@disaster_api.route('/bandwidth/compress', methods=['POST'])
def compress_patient_data():
    """Compress patient data for transmission"""
    
    try:
        data = request.get_json()
        patient_data = data.get('patient_data', {})
        target_kb = data.get('target_kb', 100)
        
        # Compress
        compressed, metrics = compression_engine.compress_for_bandwidth(
            patient_data, target_kb
        )
        
        # Encode for transmission
        import base64
        encoded = base64.b64encode(compressed).decode('utf-8')
        
        return jsonify({
            'success': True,
            'compressed_data': encoded,
            'metrics': {
                'original_size': metrics.original_size,
                'compressed_size': metrics.compressed_size,
                'compression_ratio': f"{metrics.compression_ratio:.1%}",
                'algorithm': metrics.algorithm,
                'checksum': metrics.checksum
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Compression error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@disaster_api.route('/bandwidth/stream', methods=['POST'])
def stream_patient_data():
    """Stream patient data in chunks for unreliable connections"""
    
    try:
        data = request.get_json()
        patient_data = data.get('patient_data', {})
        
        # Generate first chunk
        stream_gen = streaming_transfer.stream_patient_data(patient_data)
        first_chunk = next(stream_gen)
        
        import base64
        encoded = base64.b64encode(first_chunk.data).decode('utf-8')
        
        return jsonify({
            'success': True,
            'chunk': {
                'chunk_id': first_chunk.chunk_id,
                'total_chunks': first_chunk.total_chunks,
                'data': encoded,
                'checksum': first_chunk.checksum,
                'is_final': first_chunk.is_final
            },
            'message': 'Call /next-chunk to get subsequent chunks'
        }), 200
    
    except Exception as e:
        logger.error(f"Streaming error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =============================================
# Sync & Queue Management
# =============================================

@disaster_api.route('/sync/status', methods=['GET'])
def get_sync_status():
    """Get current sync status and pending operations"""
    
    return jsonify({
        'pending_operations': sync_status['pending_operations'],
        'last_sync': sync_status['last_sync'],
        'queue_size': operation_queue.qsize(),
        'is_online': True,  # This should be determined by connectivity
        'next_sync': 'immediate' if sync_status['pending_operations'] > 0 else 'not needed'
    }), 200

@disaster_api.route('/sync/execute', methods=['POST'])
def execute_sync():
    """Execute sync of all pending operations"""
    
    try:
        synced = 0
        failed = 0
        
        while not operation_queue.empty():
            try:
                operation = operation_queue.get_nowait()
                
                # Process operation
                # (In real implementation, would sync to server)
                synced += 1
                
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Sync operation failed: {str(e)}")
                failed += 1
        
        sync_status['pending_operations'] = 0
        sync_status['last_sync'] = datetime.utcnow().isoformat()
        
        return jsonify({
            'success': True,
            'synced_operations': synced,
            'failed_operations': failed,
            'last_sync': sync_status['last_sync']
        }), 200
    
    except Exception as e:
        logger.error(f"Sync execution error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =============================================
# Health & Status Endpoints
# =============================================

@disaster_api.route('/health', methods=['GET'])
def health_check():
    """System health check"""
    
    return jsonify({
        'status': 'healthy',
        'modules': {
            'recovery': 'ready',
            'biometric': 'ready',
            'medical_extraction': 'ready',
            'fusion': 'ready',
            'family_reconstruction': 'ready',
            'medication_safety': 'ready',
            'urgency_scoring': 'ready',
            'bandwidth_optimization': 'ready',
        },
        'queue_pending': sync_status['pending_operations'],
        'timestamp': datetime.utcnow().isoformat()
    }), 200

