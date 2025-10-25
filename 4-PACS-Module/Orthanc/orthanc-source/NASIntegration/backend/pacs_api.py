#!/usr/bin/env python3
"""
Fast PACS Search API
===================

High-performance patient search API for doctors.
Provides instant access to 9300+ patients on 11TB NAS drive.

Critical PACS Functions:
- Sub-second patient search by name/ID
- Instant study retrieval
- Direct image file access paths
- No storage duplication
"""

from flask import Blueprint, request, jsonify, send_file
from datetime import datetime
import logging
import sqlite3
import os
from .metadata_db import get_metadata_db_path
from pathlib import Path
import json

# Import the PACS indexer
try:
    from .pacs_indexer import PACSIndexer
except ImportError:
    from pacs_indexer import PACSIndexer

logger = logging.getLogger(__name__)

# Create blueprint for PACS API
pacs_bp = Blueprint('pacs', __name__, url_prefix='/api/pacs')

# Global indexer instance
indexer = None

def get_indexer():
    """Get or create the PACS indexer instance"""
    global indexer
    if indexer is None:
        # Determine canonical DB path. Prefer environment override, then
        # prefer the Orthanc index (if present) so we don't duplicate indexing.
        base_dir = os.path.dirname(__file__)
        env_db = os.environ.get('PACS_DB_PATH')
        candidates = []
        if env_db:
            candidates.append(env_db)
        # Add the canonical metadata DB (orthanc-index or fallback)
        candidates.append(get_metadata_db_path())

        # Pick the first existing candidate, otherwise default to canonical
        chosen = None
        for c in candidates:
            try:
                if c and os.path.exists(c):
                    chosen = c
                    break
            except Exception:
                continue

        if not chosen:
            chosen = get_metadata_db_path()

        logger.info(f"📚 Using PACS DB: {chosen}")
        indexer = PACSIndexer("Z:", chosen)
    return indexer

@pacs_bp.route('/search/patients', methods=['POST'])
def search_patients():
    """
    Fast patient search for doctors
    
    POST /api/pacs/search/patients
    {
        "query": "FELIX MAXWELL",  // Patient name or ID
        "modality": "CT",          // Optional: CT, MR, XR, etc.
        "study_date": "2025-09-22" // Optional: YYYY-MM-DD
    }
    
    Returns:
    {
        "success": true,
        "patients": [
            {
                "patient_id": "639380",
                "name": "FELIX MAXWELL",
                "birth_date": "19610203",
                "sex": "M",
                "medical_aid": "DIRECT TO PATIENT",
                "referring_doctor": "DR G CHARLTON",
                "folder_path": "Z:\\639380-20250922-...",
                "study_count": 1
            }
        ],
        "total_found": 1,
        "search_time_ms": 15
    }
    """
    start_time = datetime.now()
    
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        modality = data.get('modality', '').strip()
        study_date = data.get('study_date', '').strip()
        
        logger.info(f"🔍 PACS Search: query='{query}', modality='{modality}', date='{study_date}'")
        
        # Get indexer and search
        pacs = get_indexer()
        patients = pacs.search_patients(query, modality, study_date)
        
        search_time = (datetime.now() - start_time).total_seconds() * 1000
        
        logger.info(f"✅ Found {len(patients)} patients in {search_time:.1f}ms")
        
        return jsonify({
            'success': True,
            'patients': patients,
            'total_found': len(patients),
            'search_time_ms': round(search_time, 1),
            'search_criteria': {
                'query': query,
                'modality': modality,
                'study_date': study_date
            }
        })
        
    except Exception as e:
        logger.error(f"❌ PACS search failed: {e}")
        return jsonify({
            'success': False,
            'error': f'Search failed: {str(e)}',
            'patients': []
        }), 500

@pacs_bp.route('/patient/<patient_id>/studies', methods=['GET'])
def get_patient_studies(patient_id):
    """
    Get all studies for a specific patient
    
    GET /api/pacs/patient/639380/studies
    
    Returns:
    {
        "success": true,
        "patient_id": "639380",
        "studies": [
            {
                "study_instance_uid": "1.2.3.4.5...",
                "study_date": "20250922",
                "study_time": "125345",
                "study_description": "CT CHEST WITH CONTRAST",
                "modality": "CT",
                "accession_number": "A202509220001",
                "folder_path": "Z:\\639380-20250922-...",
                "series_count": 3,
                "instance_count": 150
            }
        ]
    }
    """
    try:
        logger.info(f"📊 Getting studies for patient: {patient_id}")
        
        pacs = get_indexer()
        studies = pacs.get_patient_studies(patient_id)
        
        logger.info(f"✅ Found {len(studies)} studies for patient {patient_id}")
        
        return jsonify({
            'success': True,
            'patient_id': patient_id,
            'studies': studies,
            'total_studies': len(studies)
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get studies for patient {patient_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get studies: {str(e)}'
        }), 500

@pacs_bp.route('/study/<study_uid>/images', methods=['GET'])
def get_study_images(study_uid):
    """
    Get all image file paths for a specific study
    
    GET /api/pacs/study/1.2.3.4.5.../images
    
    Returns:
    {
        "success": true,
        "study_uid": "1.2.3.4.5...",
        "images": [
            {
                "file_path": "Z:\\639380-20250922-\\CT001.dcm",
                "instance_number": 1,
                "sop_instance_uid": "1.2.3.4.5.6...",
                "series_description": "CHEST ARTERIAL",
                "series_number": 1,
                "modality": "CT"
            }
        ],
        "total_images": 150
    }
    """
    try:
        logger.info(f"🖼️ Getting images for study: {study_uid}")
        
        pacs = get_indexer()
        images = pacs.get_study_images(study_uid)
        
        logger.info(f"✅ Found {len(images)} images for study {study_uid}")
        
        return jsonify({
            'success': True,
            'study_uid': study_uid,
            'images': images,
            'total_images': len(images)
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get images for study {study_uid}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get images: {str(e)}'
        }), 500

@pacs_bp.route('/image/view', methods=['GET'])
def view_image():
    """
    Serve DICOM image directly from NAS
    
    GET /api/pacs/image/view?path=Z:\\639380-20250922-\\CT001.dcm
    
    Returns: DICOM file stream for viewer
    """
    try:
        file_path = request.args.get('path')
        if not file_path:
            return jsonify({'error': 'File path required'}), 400
        
        file_path = Path(file_path)
        
        # Security check - ensure path is within NAS drive
        if not str(file_path).startswith('Z:'):
            return jsonify({'error': 'Invalid file path'}), 403
        
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        logger.info(f"📷 Serving DICOM image: {file_path}")
        
        return send_file(
            str(file_path),
            mimetype='application/dicom',
            as_attachment=False,
            download_name=file_path.name
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to serve image: {e}")
        return jsonify({'error': f'Failed to serve image: {str(e)}'}), 500

@pacs_bp.route('/indexing/start', methods=['POST'])
def start_indexing():
    """
    Start full NAS indexing process
    
    POST /api/pacs/indexing/start
    
    Returns:
    {
        "success": true,
        "message": "Indexing started",
        "estimated_time": "45 minutes for 9300 patients"
    }
    """
    try:
        logger.info("🚀 Starting PACS indexing...")
        
        pacs = get_indexer()
        
        if pacs.is_indexing:
            return jsonify({
                'success': False,
                'error': 'Indexing already in progress'
            }), 409
        
        # Start indexing in background thread
        import threading
        
        def indexing_task():
            try:
                pacs.scan_nas_directory()
                logger.info("✅ PACS indexing completed successfully")
            except Exception as e:
                logger.error(f"❌ PACS indexing failed: {e}")
        
        thread = threading.Thread(target=indexing_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'PACS indexing started',
            'estimated_time': '45 minutes for 9300 patients',
            'note': 'Check /api/pacs/indexing/status for progress'
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to start indexing: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to start indexing: {str(e)}'
        }), 500

@pacs_bp.route('/indexing/status', methods=['GET'])
def get_indexing_status():
    """
    Get current indexing status
    
    GET /api/pacs/indexing/status
    
    Returns:
    {
        "success": true,
        "is_indexing": false,
        "stats": {
            "patients": 9347,
            "studies": 12156,
            "series": 45623,
            "instances": 2847392,
            "start_time": "2025-09-23T10:00:00",
            "end_time": "2025-09-23T10:45:00"
        },
        "db_exists": true
    }
    """
    try:
        pacs = get_indexer()
        status = pacs.get_indexing_status()
        
        return jsonify({
            'success': True,
            **status
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get indexing status: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get status: {str(e)}'
        }), 500

@pacs_bp.route('/stats', methods=['GET'])
def get_pacs_stats():
    """
    Get overall PACS statistics
    
    GET /api/pacs/stats
    
    Returns:
    {
        "success": true,
        "total_patients": 9347,
        "total_studies": 12156,
        "total_series": 45623,
        "total_instances": 2847392,
        "database_size_mb": 156.7,
        "last_indexed": "2025-09-23T10:45:00"
    }
    """
    try:
        pacs = get_indexer()
        
        if not os.path.exists(pacs.db_path):
            return jsonify({
                'success': False,
                'error': 'PACS index not found. Run indexing first.',
                'total_patients': 0,
                'total_studies': 0,
                'total_series': 0,
                'total_instances': 0
            })
        
        # Get database statistics
        conn = sqlite3.connect(pacs.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM patients')
        total_patients = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM studies')
        total_studies = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM series')
        total_series = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM instances')
        total_instances = cursor.fetchone()[0]
        
        cursor.execute('SELECT MAX(indexed_date) FROM patients')
        last_indexed = cursor.fetchone()[0]
        
        conn.close()
        
        # Get database file size
        db_size_mb = os.path.getsize(pacs.db_path) / (1024 * 1024)
        
        return jsonify({
            'success': True,
            'total_patients': total_patients,
            'total_studies': total_studies,
            'total_series': total_series,
            'total_instances': total_instances,
            'database_size_mb': round(db_size_mb, 1),
            'last_indexed': last_indexed
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get PACS stats: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get stats: {str(e)}'
        }), 500

# Health check endpoint
@pacs_bp.route('/health', methods=['GET'])
def health_check():
    """PACS API health check"""
    try:
        pacs = get_indexer()
        db_exists = os.path.exists(pacs.db_path)
        
        return jsonify({
            'success': True,
            'service': 'PACS API',
            'status': 'healthy',
            'database_ready': db_exists,
            'nas_accessible': os.path.exists('Z:'),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'service': 'PACS API',
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500