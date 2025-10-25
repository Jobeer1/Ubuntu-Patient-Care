#!/usr/bin/env python3
"""
Enterprise Multi-NAS PACS API
=============================

Enhanced PACS API for multiple NAS devices with:
- Unified patient search across all NAS devices
- Fast image location lookup (SQL database)
- Incremental updates for new procedures
- Support for DICOM, Firebird, and JPEG2000 formats
"""

from flask import Blueprint, request, jsonify, send_file
from datetime import datetime, timedelta
import logging
import sqlite3
import os
from pathlib import Path
import json
import threading

# Import the multi-NAS indexer
try:
    from .multi_nas_pacs_indexer import MultiNASPACSIndexer, setup_three_nas_config
except ImportError:
    from multi_nas_pacs_indexer import MultiNASPACSIndexer, setup_three_nas_config

logger = logging.getLogger(__name__)

# Create blueprint for Enterprise PACS API
enterprise_pacs_bp = Blueprint('enterprise_pacs', __name__, url_prefix='/api/enterprise-pacs')

# Global indexer instance
indexer = None

def get_enterprise_indexer():
    """Get or create the enterprise PACS indexer instance"""
    global indexer
    if indexer is None:
        indexer = setup_three_nas_config()
        indexer.init_enterprise_database()
        
        # Start incremental monitoring (every 15 minutes)
        indexer.start_incremental_monitoring(15)
        logger.info("✅ Enterprise PACS indexer initialized with 3 NAS devices")
    return indexer

@enterprise_pacs_bp.route('/search/patients', methods=['POST'])
def search_patients_multi_nas():
    """
    Search patients across all NAS devices
    
    POST /api/enterprise-pacs/search/patients
    {
        "query": "FELIX MAXWELL",
        "modality": "CT",
        "study_date": "2025-09-22",
        "nas_filter": "nas_ct_dicom"  // Optional: search specific NAS
    }
    
    Returns patients from all NAS devices with image locations
    """
    start_time = datetime.now()
    
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        modality = data.get('modality', '').strip()
        study_date = data.get('study_date', '').strip()
        nas_filter = data.get('nas_filter', '').strip()
        
        logger.info(f"🔍 Enterprise PACS Search: query='{query}', modality='{modality}', nas='{nas_filter}'")
        
        # Get indexer and search across all NAS devices
        pacs = get_enterprise_indexer()
        patients = pacs.search_patients_across_nas(query, modality, study_date, nas_filter)
        
        search_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Enhance results with NAS information
        enhanced_patients = []
        for patient in patients:
            enhanced_patient = patient.copy()
            enhanced_patient['image_locations_available'] = True
            enhanced_patient['formats_available'] = patient.get('formats', '').split(',') if patient.get('formats') else []
            enhanced_patient['modalities_available'] = patient.get('modalities', '').split(',') if patient.get('modalities') else []
            enhanced_patients.append(enhanced_patient)
        
        logger.info(f"✅ Found {len(patients)} patients across NAS devices in {search_time:.1f}ms")
        
        return jsonify({
            'success': True,
            'patients': enhanced_patients,
            'total_found': len(patients),
            'search_time_ms': round(search_time, 1),
            'nas_devices_searched': list(pacs.nas_configs.keys()),
            'search_criteria': {
                'query': query,
                'modality': modality,
                'study_date': study_date,
                'nas_filter': nas_filter
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Enterprise PACS search failed: {e}")
        return jsonify({
            'success': False,
            'error': f'Multi-NAS search failed: {str(e)}',
            'patients': []
        }), 500

@enterprise_pacs_bp.route('/patient/<patient_id>/images', methods=['GET'])
def get_patient_image_locations(patient_id):
    """
    Get all image file locations for a patient across all NAS devices
    
    GET /api/enterprise-pacs/patient/639380/images?nas_id=nas_ct_dicom
    
    Returns:
    {
        "success": true,
        "patient_id": "639380",
        "images": [
            {
                "file_path": "Z:\\639380-20250922-\\CT001.dcm",
                "file_format": "DCM",
                "compression_type": "DICOM",
                "nas_id": "nas_ct_dicom",
                "nas_description": "CT DICOM NAS",
                "study_description": "CT PARANASAL SINUSES",
                "modality": "CT",
                "image_width": 512,
                "image_height": 512,
                "file_size": 264192
            }
        ],
        "total_images": 691,
        "nas_devices": ["nas_ct_dicom", "nas_firebird_1"],
        "formats": ["DCM", "JP2"]
    }
    """
    try:
        nas_id = request.args.get('nas_id')  # Optional filter
        
        logger.info(f"🖼️ Getting image locations for patient: {patient_id}")
        
        pacs = get_enterprise_indexer()
        images = pacs.get_image_locations(patient_id, nas_id)
        
        # Group by NAS device and format
        nas_devices = list(set(img['nas_id'] for img in images))
        formats = list(set(img['file_format'] for img in images))
        
        logger.info(f"✅ Found {len(images)} image locations for patient {patient_id}")
        
        return jsonify({
            'success': True,
            'patient_id': patient_id,
            'images': images,
            'total_images': len(images),
            'nas_devices': nas_devices,
            'formats': formats,
            'filtered_by_nas': nas_id
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get image locations for patient {patient_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get image locations: {str(e)}'
        }), 500

@enterprise_pacs_bp.route('/image/serve', methods=['GET'])
def serve_image_from_nas():
    """
    Serve image directly from any NAS device
    
    GET /api/enterprise-pacs/image/serve?path=Z:\\file.dcm&format=DCM
    GET /api/enterprise-pacs/image/serve?path=Y:\\file.jp2&format=JP2
    
    Handles multiple formats:
    - DICOM files (.dcm) 
    - JPEG2000 files (.jp2)
    - Compressed formats from Firebird databases
    """
    try:
        file_path = request.args.get('path')
        file_format = request.args.get('format', 'DCM')
        
        if not file_path:
            return jsonify({'error': 'File path required'}), 400
        
        file_path = Path(file_path)
        
        # Security check - ensure path is within known NAS drives
        allowed_drives = ['Z:', 'Y:', 'X:']  # Your three NAS devices
        if not any(str(file_path).startswith(drive) for drive in allowed_drives):
            return jsonify({'error': 'Invalid file path - not in allowed NAS drives'}), 403
        
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        logger.info(f"📷 Serving {file_format} image: {file_path}")
        
        # Determine MIME type based on format
        if file_format.upper() in ['DCM', 'DICOM']:
            mimetype = 'application/dicom'
        elif file_format.upper() in ['JP2', 'JPEG2000']:
            mimetype = 'image/jp2'
        elif file_format.upper() in ['JPG', 'JPEG']:
            mimetype = 'image/jpeg'
        else:
            mimetype = 'application/octet-stream'
        
        return send_file(
            str(file_path),
            mimetype=mimetype,
            as_attachment=False,
            download_name=file_path.name
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to serve image: {e}")
        return jsonify({'error': f'Failed to serve image: {str(e)}'}), 500

@enterprise_pacs_bp.route('/indexing/start', methods=['POST'])
def start_multi_nas_indexing():
    """
    Start indexing for specific NAS device or all devices
    
    POST /api/enterprise-pacs/indexing/start
    {
        "nas_id": "nas_ct_dicom",  // Optional: specific NAS
        "incremental": true        // Optional: incremental vs full
    }
    """
    try:
        data = request.get_json() or {}
        nas_id = data.get('nas_id')
        incremental = data.get('incremental', False)
        
        pacs = get_enterprise_indexer()
        
        if nas_id:
            # Index specific NAS
            if nas_id not in pacs.nas_configs:
                return jsonify({
                    'success': False,
                    'error': f'Unknown NAS device: {nas_id}',
                    'available_nas': list(pacs.nas_configs.keys())
                }), 400
            
            # Start indexing in background
            thread = threading.Thread(
                target=pacs.index_nas_device,
                args=(nas_id, incremental),
                daemon=True
            )
            thread.start()
            
            message = f"{'Incremental' if incremental else 'Full'} indexing started for {nas_id}"
            
        else:
            # Index all NAS devices
            def index_all():
                for nas_id in pacs.nas_configs.keys():
                    pacs.index_nas_device(nas_id, incremental)
            
            thread = threading.Thread(target=index_all, daemon=True)
            thread.start()
            
            message = f"{'Incremental' if incremental else 'Full'} indexing started for all NAS devices"
        
        return jsonify({
            'success': True,
            'message': message,
            'nas_devices': list(pacs.nas_configs.keys()),
            'incremental': incremental
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to start indexing: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to start indexing: {str(e)}'
        }), 500

@enterprise_pacs_bp.route('/indexing/status', methods=['GET'])
def get_multi_nas_indexing_status():
    """
    Get indexing status for all NAS devices
    
    GET /api/enterprise-pacs/indexing/status
    """
    try:
        pacs = get_enterprise_indexer()
        
        # Get status from update log
        conn = sqlite3.connect(pacs.db_path)
        cursor = conn.cursor()
        
        # Get latest update for each NAS
        cursor.execute('''
            SELECT 
                ul.nas_id,
                nd.description,
                ul.update_type,
                ul.start_time,
                ul.end_time,
                ul.files_processed,
                ul.status,
                nd.total_patients,
                nd.total_studies,
                nd.total_instances
            FROM update_log ul
            JOIN nas_devices nd ON ul.nas_id = nd.nas_id
            WHERE ul.id IN (
                SELECT MAX(id) FROM update_log GROUP BY nas_id
            )
            ORDER BY ul.start_time DESC
        ''')
        
        nas_status = []
        for row in cursor.fetchall():
            nas_status.append({
                'nas_id': row[0],
                'description': row[1],
                'last_update_type': row[2],
                'last_start_time': row[3],
                'last_end_time': row[4],
                'files_processed': row[5],
                'status': row[6],
                'total_patients': row[7],
                'total_studies': row[8],
                'total_instances': row[9],
                'is_indexing': row[6] == 'running'
            })
        
        # Overall statistics
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT patient_id) as total_patients,
                COUNT(DISTINCT study_instance_uid) as total_studies,
                COUNT(DISTINCT series_instance_uid) as total_series,
                COUNT(*) as total_instances
            FROM instances
        ''')
        overall_stats = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'nas_devices': nas_status,
            'overall_stats': {
                'total_patients': overall_stats[0],
                'total_studies': overall_stats[1],
                'total_series': overall_stats[2],
                'total_instances': overall_stats[3]
            },
            'last_incremental_update': pacs.stats.get('last_incremental_update'),
            'incremental_monitoring_active': True
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get indexing status: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get status: {str(e)}'
        }), 500

@enterprise_pacs_bp.route('/nas-devices', methods=['GET'])
def list_nas_devices():
    """
    List all configured NAS devices
    
    GET /api/enterprise-pacs/nas-devices
    """
    try:
        pacs = get_enterprise_indexer()
        
        devices = []
        for nas_id, config in pacs.nas_configs.items():
            device_info = {
                'nas_id': nas_id,
                'type': config['type'],
                'description': config['description'],
                'path': config['path'],
                'accessible': os.path.exists(config['path'])
            }
            
            # Add format-specific info
            if config['type'] == 'firebird_jpeg2000':
                device_info['database'] = config.get('firebird_db')
                device_info['host'] = config.get('firebird_host')
            
            devices.append(device_info)
        
        return jsonify({
            'success': True,
            'nas_devices': devices,
            'total_devices': len(devices)
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to list NAS devices: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to list devices: {str(e)}'
        }), 500

@enterprise_pacs_bp.route('/incremental/trigger', methods=['POST'])
def trigger_incremental_update():
    """
    Manually trigger incremental update for new procedures
    
    POST /api/enterprise-pacs/incremental/trigger
    {
        "nas_id": "nas_ct_dicom"  // Optional: specific NAS
    }
    """
    try:
        data = request.get_json() or {}
        nas_id = data.get('nas_id')
        
        pacs = get_enterprise_indexer()
        
        def run_incremental():
            if nas_id:
                pacs.index_nas_device(nas_id, incremental=True)
            else:
                for device_id in pacs.nas_configs.keys():
                    pacs.index_nas_device(device_id, incremental=True)
        
        # Run in background
        thread = threading.Thread(target=run_incremental, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Incremental update triggered',
            'nas_id': nas_id or 'all',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to trigger incremental update: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to trigger update: {str(e)}'
        }), 500

# Health check for enterprise PACS
@enterprise_pacs_bp.route('/health', methods=['GET'])
def enterprise_pacs_health():
    """Enterprise PACS health check"""
    try:
        pacs = get_enterprise_indexer()
        
        # Check database
        db_exists = os.path.exists(pacs.db_path)
        
        # Check NAS accessibility
        nas_status = {}
        for nas_id, config in pacs.nas_configs.items():
            nas_status[nas_id] = {
                'accessible': os.path.exists(config['path']),
                'type': config['type']
            }
        
        all_nas_accessible = all(status['accessible'] for status in nas_status.values())
        
        return jsonify({
            'success': True,
            'service': 'Enterprise PACS API',
            'status': 'healthy' if db_exists and all_nas_accessible else 'degraded',
            'database_ready': db_exists,
            'nas_devices': nas_status,
            'incremental_monitoring': 'active',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'service': 'Enterprise PACS API',
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500