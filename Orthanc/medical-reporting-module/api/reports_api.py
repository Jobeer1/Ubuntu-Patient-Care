#!/usr/bin/env python3
"""
Reports API for Medical Reporting Module
Handle saving and retrieving medical reports
"""

import os
import logging
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

logger = logging.getLogger(__name__)

# Create blueprint
reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/save', methods=['POST'])
def save_report():
    """Save a medical report"""
    try:
        data = request.get_json()
        
        if not data or 'content' not in data:
            return jsonify({'error': 'Report content required'}), 400
        
        # Generate report ID
        report_id = str(uuid.uuid4())
        
        # Create report data
        report_data = {
            'id': report_id,
            'content': data['content'],
            'timestamp': data.get('timestamp', datetime.utcnow().isoformat()),
            'session_id': data.get('session_id'),
            'word_count': data.get('word_count', 0),
            'char_count': data.get('char_count', 0),
            'created_at': datetime.utcnow().isoformat(),
            'type': 'voice_dictation',
            'status': 'draft'
        }
        
        # Try to save to database
        try:
            # Get database service if available
            service_manager = getattr(current_app, 'service_manager', None)
            if service_manager:
                db_service = service_manager.get_service('database_service')
                if db_service:
                    # Save to database
                    db_service.save_report(report_data)
                    logger.info(f"Report {report_id} saved to database")
                else:
                    # Save to file as backup
                    _save_report_to_file(report_data)
                    logger.info(f"Report {report_id} saved to file")
            else:
                # Save to file as backup
                _save_report_to_file(report_data)
                logger.info(f"Report {report_id} saved to file")
                
        except Exception as db_error:
            logger.error(f"Database save failed: {db_error}")
            # Fallback to file save
            _save_report_to_file(report_data)
            logger.info(f"Report {report_id} saved to file (fallback)")
        
        return jsonify({
            'success': True,
            'report_id': report_id,
            'message': 'Report saved successfully',
            'timestamp': report_data['created_at']
        }), 201
        
    except Exception as e:
        logger.error(f"Report save error: {e}")
        return jsonify({'error': 'Failed to save report'}), 500

@reports_bp.route('/list', methods=['GET'])
def list_reports():
    """List saved reports"""
    try:
        # Try to get from database first
        reports = []
        
        try:
            service_manager = getattr(current_app, 'service_manager', None)
            if service_manager:
                db_service = service_manager.get_service('database_service')
                if db_service:
                    reports = db_service.get_reports()
        except Exception as db_error:
            logger.error(f"Database list failed: {db_error}")
        
        # If no database reports, try to get from files
        if not reports:
            reports = _get_reports_from_files()
        
        return jsonify({
            'success': True,
            'reports': reports,
            'total': len(reports)
        })
        
    except Exception as e:
        logger.error(f"Report list error: {e}")
        return jsonify({'error': 'Failed to list reports'}), 500

@reports_bp.route('/<report_id>', methods=['GET'])
def get_report(report_id):
    """Get a specific report"""
    try:
        # Try database first
        report = None
        
        try:
            service_manager = getattr(current_app, 'service_manager', None)
            if service_manager:
                db_service = service_manager.get_service('database_service')
                if db_service:
                    report = db_service.get_report(report_id)
        except Exception as db_error:
            logger.error(f"Database get failed: {db_error}")
        
        # If not in database, try files
        if not report:
            report = _get_report_from_file(report_id)
        
        if report:
            return jsonify({
                'success': True,
                'report': report
            })
        else:
            return jsonify({'error': 'Report not found'}), 404
            
    except Exception as e:
        logger.error(f"Report get error: {e}")
        return jsonify({'error': 'Failed to get report'}), 500

@reports_bp.route('/<report_id>', methods=['DELETE'])
def delete_report(report_id):
    """Delete a report"""
    try:
        deleted = False
        
        # Try database first
        try:
            service_manager = getattr(current_app, 'service_manager', None)
            if service_manager:
                db_service = service_manager.get_service('database_service')
                if db_service:
                    deleted = db_service.delete_report(report_id)
        except Exception as db_error:
            logger.error(f"Database delete failed: {db_error}")
        
        # If not in database, try files
        if not deleted:
            deleted = _delete_report_file(report_id)
        
        if deleted:
            return jsonify({
                'success': True,
                'message': 'Report deleted successfully'
            })
        else:
            return jsonify({'error': 'Report not found'}), 404
            
    except Exception as e:
        logger.error(f"Report delete error: {e}")
        return jsonify({'error': 'Failed to delete report'}), 500

def _save_report_to_file(report_data):
    """Save report to file as backup"""
    try:
        # Create reports directory if it doesn't exist
        reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        # Save as JSON file
        import json
        filename = f"report_{report_data['id']}.json"
        filepath = os.path.join(reports_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        # Also save as text file for easy reading
        text_filename = f"report_{report_data['id']}.txt"
        text_filepath = os.path.join(reports_dir, text_filename)
        
        with open(text_filepath, 'w', encoding='utf-8') as f:
            f.write(f"SA Medical Report\n")
            f.write(f"Report ID: {report_data['id']}\n")
            f.write(f"Created: {report_data['created_at']}\n")
            f.write(f"Word Count: {report_data['word_count']}\n")
            f.write(f"{'='*50}\n\n")
            f.write(report_data['content'])
        
        logger.info(f"Report saved to files: {filepath}")
        
    except Exception as e:
        logger.error(f"File save error: {e}")
        raise

def _get_reports_from_files():
    """Get reports from file system"""
    try:
        reports = []
        reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
        
        if os.path.exists(reports_dir):
            import json
            for filename in os.listdir(reports_dir):
                if filename.endswith('.json') and filename.startswith('report_'):
                    filepath = os.path.join(reports_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            report = json.load(f)
                            # Only include summary info for list
                            reports.append({
                                'id': report['id'],
                                'timestamp': report['timestamp'],
                                'created_at': report['created_at'],
                                'word_count': report['word_count'],
                                'char_count': report['char_count'],
                                'type': report.get('type', 'unknown'),
                                'status': report.get('status', 'unknown')
                            })
                    except Exception as file_error:
                        logger.error(f"Error reading report file {filename}: {file_error}")
        
        # Sort by creation date, newest first
        reports.sort(key=lambda x: x['created_at'], reverse=True)
        return reports
        
    except Exception as e:
        logger.error(f"File list error: {e}")
        return []

def _get_report_from_file(report_id):
    """Get specific report from file"""
    try:
        reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
        filename = f"report_{report_id}.json"
        filepath = os.path.join(reports_dir, filename)
        
        if os.path.exists(filepath):
            import json
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None
        
    except Exception as e:
        logger.error(f"File get error: {e}")
        return None

def _delete_report_file(report_id):
    """Delete report files"""
    try:
        reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
        
        # Delete JSON file
        json_filename = f"report_{report_id}.json"
        json_filepath = os.path.join(reports_dir, json_filename)
        
        # Delete text file
        text_filename = f"report_{report_id}.txt"
        text_filepath = os.path.join(reports_dir, text_filename)
        
        deleted = False
        
        if os.path.exists(json_filepath):
            os.remove(json_filepath)
            deleted = True
        
        if os.path.exists(text_filepath):
            os.remove(text_filepath)
            deleted = True
        
        return deleted
        
    except Exception as e:
        logger.error(f"File delete error: {e}")
        return False