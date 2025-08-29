"""
Reporting API for Medical Reporting Module
Handles report CRUD operations and workflow management
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
import logging
import uuid
from typing import Dict, List, Any, Optional
from api.auth_api import require_auth, require_role
from core.reporting_engine import reporting_engine, WorkflowState, ReportSession
from models.report import ReportType, ReportStatus

logger = logging.getLogger(__name__)

reporting_bp = Blueprint('reporting', __name__)

# Mock report database
MOCK_REPORTS = {}

# Report status options
REPORT_STATUSES = [
    'draft',
    'in_progress', 
    'voice_review',
    'typist_review',
    'doctor_review',
    'completed',
    'signed'
]

def create_mock_report(report_id: str, user_id: str, **kwargs) -> Dict[str, Any]:
    """Create a mock report structure"""
    return {
        'id': report_id,
        'user_id': user_id,
        'patient_id': kwargs.get('patient_id', f'PAT{len(MOCK_REPORTS) + 1:04d}'),
        'study_id': kwargs.get('study_id', f'STU{len(MOCK_REPORTS) + 1:04d}'),
        'accession_number': kwargs.get('accession_number', f'ACC{len(MOCK_REPORTS) + 1:06d}'),
        'study_date': kwargs.get('study_date', datetime.utcnow().date().isoformat()),
        'modality': kwargs.get('modality', 'CR'),
        'body_part': kwargs.get('body_part', 'CHEST'),
        'procedure_description': kwargs.get('procedure_description', 'Chest X-Ray'),
        'template_id': kwargs.get('template_id'),
        'template_name': kwargs.get('template_name'),
        'status': kwargs.get('status', 'draft'),
        'priority': kwargs.get('priority', 'routine'),
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'report_content': kwargs.get('report_content', {}),
        'voice_session_id': kwargs.get('voice_session_id'),
        'transcription': kwargs.get('transcription', ''),
        'typist_notes': kwargs.get('typist_notes', ''),
        'doctor_notes': kwargs.get('doctor_notes', ''),
        'signed_at': kwargs.get('signed_at'),
        'signed_by': kwargs.get('signed_by'),
        'workflow_history': kwargs.get('workflow_history', [])
    }

# Initialize with some mock reports
def initialize_mock_reports():
    """Initialize mock reports for demo"""
    reports = [
        {
            'patient_id': 'PAT0001',
            'study_id': 'STU0001',
            'accession_number': 'ACC000001',
            'modality': 'CR',
            'body_part': 'CHEST',
            'procedure_description': 'Chest X-Ray PA and Lateral',
            'status': 'completed',
            'report_content': {
                'clinical_info': 'Cough and fever',
                'technique': 'PA and lateral chest radiographs',
                'findings': 'The lungs are clear bilaterally. No focal consolidation, pleural effusion, or pneumothorax. The cardiac silhouette is normal.',
                'impression': 'Normal chest radiograph.'
            }
        },
        {
            'patient_id': 'PAT0002',
            'study_id': 'STU0002',
            'accession_number': 'ACC000002',
            'modality': 'CT',
            'body_part': 'CHEST',
            'procedure_description': 'CT Chest with Contrast',
            'status': 'in_progress',
            'report_content': {
                'clinical_info': 'Shortness of breath',
                'technique': 'Axial CT images of the chest with IV contrast',
                'findings': 'Preliminary findings show...',
                'impression': 'Study in progress.'
            }
        }
    ]
    
    for i, report_data in enumerate(reports):
        report_id = str(uuid.uuid4())
        user_id = '1'  # Default to doctor1
        MOCK_REPORTS[report_id] = create_mock_report(report_id, user_id, **report_data)

# Initialize mock data
initialize_mock_reports()

@reporting_bp.route('/', methods=['GET'])
@require_auth
def list_reports():
    """List reports with filtering and pagination"""
    try:
        user_id = session['user_id']
        user_role = session['role']
        
        # Get query parameters
        status = request.args.get('status')
        modality = request.args.get('modality')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        patient_id = request.args.get('patient_id')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Filter reports
        filtered_reports = []
        for report in MOCK_REPORTS.values():
            # Role-based filtering
            if user_role == 'typist':
                # Typists see reports in typist_review status
                if report['status'] != 'typist_review':
                    continue
            elif user_role == 'radiologist':
                # Radiologists see their own reports or unassigned reports
                if report['user_id'] != user_id and report['status'] not in ['draft', 'in_progress']:
                    continue
            
            # Apply filters
            if status and report['status'] != status:
                continue
            if modality and report['modality'] != modality:
                continue
            if patient_id and report['patient_id'] != patient_id:
                continue
            if date_from:
                try:
                    report_date = datetime.fromisoformat(report['study_date'])
                    filter_date = datetime.fromisoformat(date_from)
                    if report_date < filter_date:
                        continue
                except:
                    pass
            if date_to:
                try:
                    report_date = datetime.fromisoformat(report['study_date'])
                    filter_date = datetime.fromisoformat(date_to)
                    if report_date > filter_date:
                        continue
                except:
                    pass
            
            filtered_reports.append(report)
        
        # Sort by updated_at descending
        filtered_reports.sort(key=lambda x: x['updated_at'], reverse=True)
        
        # Pagination
        total = len(filtered_reports)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_reports = filtered_reports[start:end]
        
        return jsonify({
            'reports': paginated_reports,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(f"Report listing error: {e}")
        return jsonify({'error': 'Failed to retrieve reports'}), 500

@reporting_bp.route('/', methods=['POST'])
@require_auth
def create_report():
    """Create a new report"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Report data required'}), 400
        
        # Required fields
        study_id = data.get('study_id')
        if not study_id:
            return jsonify({'error': 'Study ID required'}), 400
        
        # Optional fields
        template_id = data.get('template_id')
        report_type = ReportType(data.get('report_type', 'diagnostic'))
        
        # Create report using reporting engine
        session_obj = reporting_engine.create_report(
            user_id=user_id,
            study_id=study_id,
            template_id=template_id,
            report_type=report_type
        )
        
        # Get session info
        session_info = reporting_engine.get_session_info(session_obj.session_id)
        
        logger.info(f"Created report {session_obj.report_id} for user {user_id}")
        
        return jsonify({
            'report_id': session_obj.report_id,
            'session_id': session_obj.session_id,
            'session_info': session_info
        }), 201
        
    except Exception as e:
        logger.error(f"Report creation error: {e}")
        return jsonify({'error': 'Failed to create report'}), 500

@reporting_bp.route('/<report_id>', methods=['GET'])
@require_auth
def get_report(report_id):
    """Get a specific report"""
    try:
        user_id = session['user_id']
        user_role = session['role']
        
        report = MOCK_REPORTS.get(report_id)
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        # Check permissions
        if user_role == 'radiologist' and report['user_id'] != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({'report': report})
        
    except Exception as e:
        logger.error(f"Report retrieval error: {e}")
        return jsonify({'error': 'Failed to retrieve report'}), 500

@reporting_bp.route('/<report_id>', methods=['PUT'])
@require_auth
def update_report(report_id):
    """Update a report"""
    try:
        user_id = session['user_id']
        user_role = session['role']
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Update data required'}), 400
        
        report = MOCK_REPORTS.get(report_id)
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        # Check permissions
        if user_role == 'radiologist' and report['user_id'] != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Update allowed fields
        allowed_fields = [
            'template_id', 'template_name', 'status', 'priority',
            'report_content', 'transcription', 'typist_notes', 
            'doctor_notes'
        ]
        
        old_status = report['status']
        
        for field in allowed_fields:
            if field in data:
                report[field] = data[field]
        
        report['updated_at'] = datetime.utcnow().isoformat()
        
        # Add workflow history if status changed
        if 'status' in data and data['status'] != old_status:
            report['workflow_history'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'status_changed',
                'user_id': user_id,
                'old_status': old_status,
                'new_status': data['status']
            })
        
        logger.info(f"Updated report {report_id} by user {user_id}")
        
        return jsonify({'report': report})
        
    except Exception as e:
        logger.error(f"Report update error: {e}")
        return jsonify({'error': 'Failed to update report'}), 500

@reporting_bp.route('/<report_id>', methods=['DELETE'])
@require_auth
def delete_report(report_id):
    """Delete a report"""
    try:
        user_id = session['user_id']
        user_role = session['role']
        
        report = MOCK_REPORTS.get(report_id)
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        # Check permissions - only report owner or admin can delete
        if user_role != 'admin' and report['user_id'] != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Don't allow deletion of signed reports
        if report['status'] == 'signed':
            return jsonify({'error': 'Cannot delete signed reports'}), 400
        
        del MOCK_REPORTS[report_id]
        
        logger.info(f"Deleted report {report_id} by user {user_id}")
        
        return jsonify({'success': True, 'message': 'Report deleted successfully'})
        
    except Exception as e:
        logger.error(f"Report deletion error: {e}")
        return jsonify({'error': 'Failed to delete report'}), 500

@reporting_bp.route('/<report_id>/sign', methods=['POST'])
@require_role('radiologist')
def sign_report(report_id):
    """Sign a report"""
    try:
        user_id = session['user_id']
        
        report = MOCK_REPORTS.get(report_id)
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        # Check if user owns the report
        if report['user_id'] != user_id:
            return jsonify({'error': 'Can only sign your own reports'}), 403
        
        # Check if report is ready for signing
        if report['status'] not in ['completed', 'doctor_review']:
            return jsonify({'error': 'Report not ready for signing'}), 400
        
        # Sign the report
        report['status'] = 'signed'
        report['signed_at'] = datetime.utcnow().isoformat()
        report['signed_by'] = user_id
        report['updated_at'] = datetime.utcnow().isoformat()
        
        # Add workflow history
        report['workflow_history'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'signed',
            'user_id': user_id,
            'status': 'signed'
        })
        
        logger.info(f"Report {report_id} signed by user {user_id}")
        
        return jsonify({'report': report})
        
    except Exception as e:
        logger.error(f"Report signing error: {e}")
        return jsonify({'error': 'Failed to sign report'}), 500

@reporting_bp.route('/statistics', methods=['GET'])
@require_auth
def get_statistics():
    """Get reporting statistics"""
    try:
        user_id = session['user_id']
        user_role = session['role']
        
        # Calculate statistics
        total_reports = len(MOCK_REPORTS)
        user_reports = [r for r in MOCK_REPORTS.values() if r['user_id'] == user_id]
        
        stats = {
            'total_reports': total_reports if user_role == 'admin' else len(user_reports),
            'by_status': {},
            'by_modality': {},
            'recent_activity': []
        }
        
        # Filter reports based on role
        reports_to_analyze = MOCK_REPORTS.values() if user_role == 'admin' else user_reports
        
        # Count by status
        for report in reports_to_analyze:
            status = report['status']
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
            modality = report['modality']
            stats['by_modality'][modality] = stats['by_modality'].get(modality, 0) + 1
        
        # Recent activity (last 10 reports)
        recent_reports = sorted(reports_to_analyze, key=lambda x: x['updated_at'], reverse=True)[:10]
        stats['recent_activity'] = [
            {
                'report_id': r['id'],
                'patient_id': r['patient_id'],
                'procedure_description': r['procedure_description'],
                'status': r['status'],
                'updated_at': r['updated_at']
            }
            for r in recent_reports
        ]
        
        return jsonify({'statistics': stats})
        
    except Exception as e:
        logger.error(f"Statistics error: {e}")
        return jsonify({'error': 'Failed to retrieve statistics'}), 500

# New endpoints for enhanced reporting workflow

@reporting_bp.route('/session/<session_id>', methods=['GET'])
@require_auth
def get_session_info(session_id):
    """Get reporting session information"""
    try:
        user_id = session['user_id']
        
        session_info = reporting_engine.get_session_info(session_id)
        if not session_info:
            return jsonify({'error': 'Session not found'}), 404
        
        # Check permissions
        if session_info['user_id'] != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({'session': session_info})
        
    except Exception as e:
        logger.error(f"Session info error: {e}")
        return jsonify({'error': 'Failed to retrieve session info'}), 500

@reporting_bp.route('/session/<session_id>/images', methods=['GET'])
@require_auth
def load_study_images(session_id):
    """Load DICOM images for study"""
    try:
        user_id = session['user_id']
        
        # Verify session ownership
        session_info = reporting_engine.get_session_info(session_id)
        if not session_info or session_info['user_id'] != user_id:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Load images
        images = reporting_engine.load_study_images(session_id)
        
        return jsonify({
            'images': images,
            'count': len(images),
            'study_id': session_info['study_id']
        })
        
    except Exception as e:
        logger.error(f"Load images error: {e}")
        return jsonify({'error': 'Failed to load study images'}), 500

@reporting_bp.route('/session/<session_id>/dictation/start', methods=['POST'])
@require_auth
def start_dictation(session_id):
    """Start voice dictation for report"""
    try:
        user_id = session['user_id']
        
        # Verify session ownership
        session_info = reporting_engine.get_session_info(session_id)
        if not session_info or session_info['user_id'] != user_id:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Start dictation
        success = reporting_engine.start_dictation(session_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Dictation started',
                'session_id': session_id
            })
        else:
            return jsonify({'error': 'Failed to start dictation'}), 500
        
    except Exception as e:
        logger.error(f"Start dictation error: {e}")
        return jsonify({'error': 'Failed to start dictation'}), 500

@reporting_bp.route('/session/<session_id>/dictation/stop', methods=['POST'])
@require_auth
def stop_dictation(session_id):
    """Stop voice dictation"""
    try:
        user_id = session['user_id']
        
        # Verify session ownership
        session_info = reporting_engine.get_session_info(session_id)
        if not session_info or session_info['user_id'] != user_id:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Stop dictation
        success = reporting_engine.stop_dictation(session_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Dictation stopped',
                'session_id': session_id
            })
        else:
            return jsonify({'error': 'Failed to stop dictation'}), 500
        
    except Exception as e:
        logger.error(f"Stop dictation error: {e}")
        return jsonify({'error': 'Failed to stop dictation'}), 500

@reporting_bp.route('/session/<session_id>/draft', methods=['POST'])
@require_auth
def save_draft(session_id):
    """Save report draft"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Draft content required'}), 400
        
        # Verify session ownership
        session_info = reporting_engine.get_session_info(session_id)
        if not session_info or session_info['user_id'] != user_id:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Save draft
        success = reporting_engine.save_report_draft(session_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Draft saved',
                'session_id': session_id,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({'error': 'Failed to save draft'}), 500
        
    except Exception as e:
        logger.error(f"Save draft error: {e}")
        return jsonify({'error': 'Failed to save draft'}), 500

@reporting_bp.route('/session/<session_id>/submit-typing', methods=['POST'])
@require_auth
def submit_for_typing(session_id):
    """Submit report for typist review"""
    try:
        user_id = session['user_id']
        
        # Verify session ownership
        session_info = reporting_engine.get_session_info(session_id)
        if not session_info or session_info['user_id'] != user_id:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Submit for typing
        success = reporting_engine.submit_for_typing(session_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Report submitted for typing',
                'session_id': session_id,
                'new_status': 'typist_review'
            })
        else:
            return jsonify({'error': 'Failed to submit for typing'}), 500
        
    except Exception as e:
        logger.error(f"Submit for typing error: {e}")
        return jsonify({'error': 'Failed to submit for typing'}), 500

@reporting_bp.route('/session/<session_id>/finalize', methods=['POST'])
@require_auth
def finalize_report(session_id):
    """Finalize report"""
    try:
        user_id = session['user_id']
        
        # Verify session ownership
        session_info = reporting_engine.get_session_info(session_id)
        if not session_info or session_info['user_id'] != user_id:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Finalize report
        success = reporting_engine.finalize_report(session_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Report finalized',
                'session_id': session_id,
                'new_status': 'finalized'
            })
        else:
            return jsonify({'error': 'Failed to finalize report'}), 500
        
    except Exception as e:
        logger.error(f"Finalize report error: {e}")
        return jsonify({'error': 'Failed to finalize report'}), 500

@reporting_bp.route('/session/<session_id>/submit', methods=['POST'])
@require_auth
def submit_report(session_id):
    """Submit report to RIS"""
    try:
        user_id = session['user_id']
        
        # Verify session ownership
        session_info = reporting_engine.get_session_info(session_id)
        if not session_info or session_info['user_id'] != user_id:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Submit report
        success = reporting_engine.submit_report(session_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Report submitted to RIS',
                'session_id': session_id,
                'new_status': 'submitted'
            })
        else:
            return jsonify({'error': 'Failed to submit report'}), 500
        
    except Exception as e:
        logger.error(f"Submit report error: {e}")
        return jsonify({'error': 'Failed to submit report'}), 500

@reporting_bp.route('/session/<session_id>/end', methods=['POST'])
@require_auth
def end_session(session_id):
    """End reporting session"""
    try:
        user_id = session['user_id']
        
        # Verify session ownership
        session_info = reporting_engine.get_session_info(session_id)
        if not session_info or session_info['user_id'] != user_id:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # End session
        success = reporting_engine.end_session(session_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Session ended',
                'session_id': session_id
            })
        else:
            return jsonify({'error': 'Failed to end session'}), 500
        
    except Exception as e:
        logger.error(f"End session error: {e}")
        return jsonify({'error': 'Failed to end session'}), 500

@reporting_bp.route('/sessions/active', methods=['GET'])
@require_auth
def get_active_sessions():
    """Get all active sessions for user"""
    try:
        user_id = session['user_id']
        
        # Get all active sessions
        all_sessions = reporting_engine.get_active_sessions()
        
        # Filter by user
        user_sessions = [s for s in all_sessions if s['user_id'] == user_id]
        
        return jsonify({
            'sessions': user_sessions,
            'count': len(user_sessions)
        })
        
    except Exception as e:
        logger.error(f"Active sessions error: {e}")
        return jsonify({'error': 'Failed to retrieve active sessions'}), 500

@reporting_bp.route('/workflow/events', methods=['GET'])
@require_auth
def get_workflow_events():
    """Get workflow events"""
    try:
        user_id = session['user_id']
        
        # Get query parameters
        session_id = request.args.get('session_id')
        report_id = request.args.get('report_id')
        limit = int(request.args.get('limit', 50))
        
        # Get workflow events
        events = reporting_engine.get_workflow_events(
            session_id=session_id,
            report_id=report_id,
            limit=limit
        )
        
        # Filter events for user's reports only (unless admin)
        user_role = session.get('role', 'radiologist')
        if user_role != 'admin':
            events = [e for e in events if e['user_id'] == user_id]
        
        return jsonify({
            'events': events,
            'count': len(events)
        })
        
    except Exception as e:
        logger.error(f"Workflow events error: {e}")
        return jsonify({'error': 'Failed to retrieve workflow events'}), 500

@reporting_bp.route('/engine/stats', methods=['GET'])
@require_auth
def get_engine_stats():
    """Get reporting engine statistics"""
    try:
        stats = reporting_engine.get_engine_stats()
        
        return jsonify({'stats': stats})
        
    except Exception as e:
        logger.error(f"Engine stats error: {e}")
        return jsonify({'error': 'Failed to retrieve engine statistics'}), 500