"""
MCP-Integrated Advanced Indexing and Search API
Provides robust, efficient DICOM indexing and intelligent search with full monitoring
"""

import logging
import json
import os
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from flask import Blueprint, request, jsonify
import sqlite3

from services.intelligent_indexing_service import IntelligentDICOMIndexer
from services.intelligent_search_service import IntelligentSearchService

logger = logging.getLogger(__name__)

# Create blueprint
advanced_indexing_api = Blueprint('advanced_indexing', __name__, url_prefix='/api/advanced')


class AdvancedIndexingManager:
    """Manages intelligent indexing and search with MCP integration"""
    
    def __init__(self, db_path: str, nas_path: str):
        self.db_path = db_path
        self.nas_path = nas_path
        self.indexer = IntelligentDICOMIndexer(db_path, nas_path)
        self.search_service = IntelligentSearchService(db_path)
        self.indexing_jobs = {}
    
    def get_indexing_status(self) -> Dict:
        """Get current indexing status and statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get latest indexing job
            cursor.execute('''
                SELECT job_id, status, start_time, end_time, indexed_files, error_count, progress_percent
                FROM indexing_jobs
                ORDER BY start_time DESC
                LIMIT 1
            ''')
            
            latest_job = cursor.fetchone()
            
            # Get database statistics
            cursor.execute('SELECT COUNT(*) FROM patient_master')
            total_patients = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM studies')
            total_studies = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM file_hashes')
            total_files = cursor.fetchone()[0]
            
            cursor.execute('SELECT SUM(file_size) FROM file_hashes')
            total_size = cursor.fetchone()[0] or 0
            
            conn.close()
            
            status = {
                'database_ready': True,
                'total_patients': total_patients,
                'total_studies': total_studies,
                'total_files': total_files,
                'total_size_gb': round(total_size / (1024**3), 2),
                'latest_job': None
            }
            
            if latest_job:
                status['latest_job'] = {
                    'job_id': latest_job[0],
                    'status': latest_job[1],
                    'start_time': latest_job[2],
                    'end_time': latest_job[3],
                    'files_indexed': latest_job[4],
                    'errors': latest_job[5],
                    'progress': latest_job[6]
                }
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Error getting indexing status: {e}")
            return {'database_ready': False, 'error': str(e)}
    
    def start_intelligent_indexing(self, folder_path: Optional[str] = None, num_workers: int = 4) -> Dict:
        """Start intelligent indexing of NAS folder"""
        folder_path = folder_path or self.nas_path
        
        logger.info(f"🚀 Starting intelligent indexing: {folder_path}")
        
        try:
            result = self.indexer.index_directory(folder_path, recursive=True, num_workers=num_workers)
            
            if result['success']:
                logger.info(f"✅ Indexing completed: {result['stats']}")
                return {
                    'success': True,
                    'message': 'Intelligent indexing completed',
                    'job_id': result['job_id'],
                    'stats': result['stats']
                }
            else:
                logger.error(f"❌ Indexing failed: {result.get('error')}")
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                }
        
        except Exception as e:
            logger.error(f"❌ Error starting indexing: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Initialize manager (will be done in app initialization)
indexing_manager = None


@advanced_indexing_api.route('/indexing/status', methods=['GET'])
def get_indexing_status():
    """Get indexing status and statistics"""
    try:
        status = indexing_manager.get_indexing_status()
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


@advanced_indexing_api.route('/indexing/start', methods=['POST'])
def start_indexing():
    """Start intelligent indexing"""
    try:
        data = request.get_json() or {}
        folder_path = data.get('folder_path')
        num_workers = data.get('num_workers', 4)
        
        result = indexing_manager.start_intelligent_indexing(folder_path, num_workers)
        
        return jsonify(result), 200 if result.get('success') else 400
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


@advanced_indexing_api.route('/search/intelligent', methods=['POST'])
def intelligent_search():
    """Perform intelligent patient search"""
    try:
        query = request.get_json() or {}
        limit = request.args.get('limit', 50, type=int)
        
        if not query:
            return jsonify({'error': 'No search criteria provided'}), 400
        
        result = indexing_manager.search_service.search_patients(query, limit=limit)
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


@advanced_indexing_api.route('/search/by-id/<patient_id>', methods=['GET'])
def search_by_id(patient_id):
    """Quick search by patient ID"""
    try:
        result = indexing_manager.search_service.search_patients(
            {'patient_id': patient_id},
            limit=50
        )
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


@advanced_indexing_api.route('/search/by-name/<patient_name>', methods=['GET'])
def search_by_name(patient_name):
    """Search by patient name with fuzzy matching"""
    try:
        result = indexing_manager.search_service.search_patients(
            {'patient_name': patient_name},
            limit=50
        )
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


@advanced_indexing_api.route('/search/all-studies/<patient_id>', methods=['GET'])
def get_all_patient_studies(patient_id):
    """Get ALL studies for a specific patient (including historical)"""
    try:
        conn = sqlite3.connect(indexing_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.study_uid, s.study_date, s.modality, s.study_description,
                   s.folder_path, COUNT(fh.file_path) as file_count,
                   s.is_complete
            FROM studies s
            LEFT JOIN file_hashes fh ON s.id = fh.study_id
            WHERE s.patient_id = ?
            GROUP BY s.study_uid
            ORDER BY s.study_date DESC
        ''', (patient_id,))
        
        studies = []
        for row in cursor.fetchall():
            studies.append({
                'study_uid': row[0],
                'study_date': row[1],
                'modality': row[2],
                'study_description': row[3],
                'folder_path': row[4],
                'file_count': row[5],
                'is_complete': bool(row[6])
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'patient_id': patient_id,
            'total_studies': len(studies),
            'studies': studies,
            'timestamp': datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


@advanced_indexing_api.route('/database/health-check', methods=['GET'])
def database_health_check():
    """Check database integrity and return diagnostics"""
    try:
        conn = sqlite3.connect(indexing_manager.db_path)
        cursor = conn.cursor()
        
        checks = {}
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        checks['tables_exist'] = all(t in tables for t in [
            'patient_master', 'studies', 'series', 'file_hashes', 'search_index'
        ])
        
        # Check indices
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indices = [row[0] for row in cursor.fetchall()]
        checks['indices_exist'] = len(indices) > 5
        
        # Data integrity checks
        cursor.execute('SELECT COUNT(*) FROM patient_master')
        checks['patient_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM studies')
        checks['study_count'] = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*)
            FROM studies s
            WHERE NOT EXISTS (SELECT 1 FROM patient_master pm WHERE pm.patient_id = s.patient_id)
        ''')
        checks['orphaned_studies'] = cursor.fetchone()[0]
        
        conn.close()
        
        status = 'healthy' if checks['tables_exist'] and checks['indices_exist'] and checks['orphaned_studies'] == 0 else 'warning'
        
        return jsonify({
            'status': status,
            'checks': checks,
            'timestamp': datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500


def initialize_advanced_indexing(app, db_path: str, nas_path: str):
    """Initialize the advanced indexing system in the Flask app"""
    global indexing_manager
    
    try:
        indexing_manager = AdvancedIndexingManager(db_path, nas_path)
        app.register_blueprint(advanced_indexing_api)
        logger.info("✅ Advanced indexing system initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize advanced indexing: {e}")
        return False
