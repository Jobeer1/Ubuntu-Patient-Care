#!/usr/bin/env python3
"""
Reporting API for Medical Reporting Module
Handles report generation, storage, and retrieval
"""

from flask import Blueprint, request, jsonify, current_app
from models.database import db, Report
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

reporting_bp = Blueprint('reporting', __name__)


@reporting_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'reporting_api',
        'timestamp': datetime.utcnow().isoformat()
    })


@reporting_bp.route('/', methods=['GET'])
def list_reports():
    """List all reports for the current user"""
    try:
        user_id = request.args.get('user_id', 'demo_user')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        reports = Report.query.filter_by(user_id=user_id).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'reports': [{
                'id': report.id,
                'title': report.title,
                'content': report.content,
                'created_at': report.created_at.isoformat(),
                'updated_at': report.updated_at.isoformat()
            } for report in reports.items],
            'total': reports.total,
            'pages': reports.pages,
            'current_page': page
        })
        
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        return jsonify({'error': 'Failed to list reports'}), 500


@reporting_bp.route('/', methods=['POST'])
def create_report():
    """Create a new report"""
    try:
        data = request.get_json()
        
        if not data or 'content' not in data:
            return jsonify({'error': 'Report content is required'}), 400
        
        report = Report(
            title=data.get('title', 'Untitled Report'),
            content=data['content'],
            user_id=data.get('user_id', 'demo_user'),
            report_type=data.get('type', 'general')
        )
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'id': report.id,
            'title': report.title,
            'message': 'Report created successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating report: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create report'}), 500


@reporting_bp.route('/<int:report_id>', methods=['GET'])
def get_report(report_id):
    """Get a specific report"""
    try:
        report = Report.query.get_or_404(report_id)
        
        return jsonify({
            'id': report.id,
            'title': report.title,
            'content': report.content,
            'type': report.report_type,
            'created_at': report.created_at.isoformat(),
            'updated_at': report.updated_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting report {report_id}: {e}")
        return jsonify({'error': 'Report not found'}), 404


@reporting_bp.route('/<int:report_id>', methods=['PUT'])
def update_report(report_id):
    """Update a specific report"""
    try:
        report = Report.query.get_or_404(report_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        if 'title' in data:
            report.title = data['title']
        if 'content' in data:
            report.content = data['content']
        if 'type' in data:
            report.report_type = data['type']
        
        report.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'id': report.id,
            'message': 'Report updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating report {report_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update report'}), 500


@reporting_bp.route('/<int:report_id>', methods=['DELETE'])
def delete_report(report_id):
    """Delete a specific report"""
    try:
        report = Report.query.get_or_404(report_id)
        
        db.session.delete(report)
        db.session.commit()
        
        return jsonify({'message': 'Report deleted successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting report {report_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete report'}), 500


@reporting_bp.route('/templates', methods=['GET'])
def list_templates():
    """List available report templates"""
    templates = [
        {
            'id': 'consultation',
            'name': 'Consultation Note',
            'description': 'Standard consultation template',
            'content': '''CONSULTATION NOTE

Date: {date}
Patient: {patient_name}
ID Number: {patient_id}

CHIEF COMPLAINT:
{chief_complaint}

HISTORY OF PRESENT ILLNESS:
{history}

PHYSICAL EXAMINATION:
{examination}

ASSESSMENT:
{assessment}

PLAN:
{plan}

Dr. {doctor_name}
{qualification}'''
        },
        {
            'id': 'discharge',
            'name': 'Discharge Summary',
            'description': 'Hospital discharge summary',
            'content': '''DISCHARGE SUMMARY

Patient: {patient_name}
Admission Date: {admission_date}
Discharge Date: {discharge_date}

DIAGNOSIS:
{diagnosis}

TREATMENT RECEIVED:
{treatment}

DISCHARGE MEDICATIONS:
{medications}

FOLLOW-UP INSTRUCTIONS:
{followup}

Dr. {doctor_name}'''
        }
    ]
    
    return jsonify({'templates': templates})


@reporting_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404


@reporting_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500