from flask import Blueprint, request, jsonify
import uuid
import json
from ..extensions import db
from ..models import User, Group, Report, ModeratorLog
from ..auth_utils import require_auth

moderation_bp = Blueprint('moderation', __name__)

@moderation_bp.route('/report', methods=['POST'])
@require_auth
def create_report(current_user):
    """Report a user for moderation review"""
    data = request.get_json()
    reportee_id = data.get('reportee_id')
    reason = data.get('reason')
    context = data.get('context')  # Optional: group_id, message_id, etc.
    
    if not reportee_id or not reason:
        return jsonify({'error': 'reportee_id and reason required'}), 400
    
    # Create report
    report = Report(
        id=str(uuid.uuid4()),
        reporter_id=current_user.user_id,
        reportee_id=reportee_id,
        report_reason=reason,
        report_context=context
    )
    db.session.add(report)
    db.session.commit()
    
    return jsonify({
        'status': 'reported',
        'report_id': report.id,
        'message': 'Thank you for reporting. Moderators will review this.'
    }), 201

@moderation_bp.route('/reports', methods=['GET'])
@require_auth
def get_reports(current_user):
    """Get reports (admin/moderator only)"""
    # Check if user is moderator or admin
    if current_user.user_role not in ['admin', 'moderator']:
        return jsonify({'error': 'Moderator access required'}), 403
    
    reports = Report.query.filter_by(status='pending').all()
    return jsonify({
        'reports': [{
            'id': r.id,
            'reporter': r.reporter_id,
            'reportee': r.reportee_id,
            'reason': r.report_reason,
            'context': r.report_context,
            'created_at': r.created_at.isoformat(),
            'status': r.status
        } for r in reports]
    }), 200

@moderation_bp.route('/report/<report_id>/investigate', methods=['PUT'])
@require_auth
def investigate_report(current_user, report_id):
    """Investigate a report (moderator action)"""
    if current_user.user_role not in ['admin', 'moderator']:
        return jsonify({'error': 'Moderator access required'}), 403
    
    report = Report.query.get(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    data = request.get_json()
    notes = data.get('notes')
    resolution = data.get('resolution')  # warning, mute, ban, dismiss
    
    # Update report
    report.status = 'investigating'
    report.assigned_moderator = current_user.user_id
    report.investigation_notes = notes
    
    if resolution:
        report.status = 'resolved'
        report.resolution = resolution
        
        # Log moderator action
        log = ModeratorLog(
            id=str(uuid.uuid4()),
            moderator_id=current_user.user_id,
            action_type='investigate',
            target_user=report.reportee_id,
            details=json.dumps({'reason': report.report_reason, 'resolution': resolution})
        )
        db.session.add(log)
        
        # Apply resolution
        if resolution == 'ban':
            user = User.query.get(report.reportee_id)
            if user:
                user.is_banned = True
    
    db.session.commit()
    return jsonify({'status': 'investigated', 'resolution': resolution}), 200

@moderation_bp.route('/moderator/appoint', methods=['POST'])
@require_auth
def appoint_moderator(current_user):
    """Appoint a moderator (admin only, or room creator for their room)"""
    data = request.get_json()
    user_to_appoint = data.get('user_id')
    group_id = data.get('group_id')  # Optional: if specific to a group
    
    if not user_to_appoint:
        return jsonify({'error': 'user_id required'}), 400
    
    # Check authorization
    if group_id:
        group = Group.query.get(group_id)
        if not group or group.created_by != current_user.user_id:
            if current_user.user_role != 'admin':
                return jsonify({'error': 'Only group creator or admin can appoint'}), 403
        
        # Add to group moderators
        mods = json.loads(group.moderator_ids or '[]')
        if user_to_appoint not in mods:
            mods.append(user_to_appoint)
            group.moderator_ids = json.dumps(mods)
    
    else:
        # System-wide moderator (admin only)
        if current_user.user_role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        user = User.query.get(user_to_appoint)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.user_role = 'moderator'
    
    # Log the action
    log = ModeratorLog(
        id=str(uuid.uuid4()),
        moderator_id=current_user.user_id,
        action_type='appoint',
        target_user=user_to_appoint,
        group_id=group_id,
        details=json.dumps({'appointed_to': group_id or 'system-wide'})
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'status': 'appointed', 'moderator': user_to_appoint}), 201

@moderation_bp.route('/group/<group_id>/set-ai-moderator', methods=['POST'])
@require_auth
def set_ai_moderator(current_user, group_id):
    """Room creator can set optional AI moderator (with custom LLM key)"""
    group = Group.query.get(group_id)
    if not group or group.created_by != current_user.user_id:
        return jsonify({'error': 'Only group creator can set AI moderator'}), 403
    
    data = request.get_json()
    ai_key = data.get('ai_key')  # Custom LLM API key
    enable = data.get('enable', True)
    
    if ai_key:
        group.ai_moderator_key = ai_key
    
    group.ai_moderator_enabled = enable
    group.moderation_type = 'hybrid' if enable else 'human'
    db.session.commit()
    
    return jsonify({
        'status': 'ai_moderator_configured',
        'enabled': enable,
        'message': 'AI moderator will not count toward 20-user room limit'
    }), 200
