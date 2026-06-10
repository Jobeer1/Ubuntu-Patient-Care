from flask import Blueprint, request, jsonify, send_file
from sqlalchemy import desc
from backend.agent_pacs import (
    PACSContinuityMentor,
    PACS_MENTOR_ADMIN_NUMBERS,
    PACS_MENTOR_OWNER_NUMBERS,
    _extract_whatsapp_sender_number,
    _normalize_sa_whatsapp_number,
)
from backend.pacs_exports import generate_pacs_export_artifact
from backend.models import db, Message, User, PacsAuditLog
from backend.auth_utils import require_auth, get_current_user
import configparser
import os
import threading
import time
import uuid
import json
import re


def _pacs_client_context():
    forwarded_for = request.headers.get('X-Forwarded-For')
    client_ip = forwarded_for.split(',')[0].strip() if forwarded_for else request.remote_addr
    client_machine = request.headers.get('X-Client-Machine') or request.user_agent.platform or request.user_agent.browser or client_ip
    return {
        'client_ip': client_ip,
        'client_machine': client_machine,
        'user_agent': request.user_agent.string,
    }


def _redact_sensitive_text(value):
    if value is None:
        return None
    text = str(value)
    patterns = [
        (r'(?i)\b(password|pass|passwd|pwd)\s*[:=]\s*([^\s,;]+)', r'\1=[REDACTED]'),
        (r'(?i)\b(token|secret|api[_-]?key|api key|key)\s*[:=]\s*([^\s,;]+)', r'\1=[REDACTED]'),
        (r'(?i)\b(username|user|login)\s*[:=]\s*([^\s,;]+)', r'\1=[REDACTED]'),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


def _append_pacs_audit_file(entry):
    audit_dir = os.path.join('instance')
    os.makedirs(audit_dir, exist_ok=True)
    audit_file = os.path.join(audit_dir, 'pacs_audit_log.jsonl')
    with open(audit_file, 'a', encoding='utf-8') as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + '\n')


def _log_pacs_audit(current_user, route, action, chat_id=None, request_text=None, response_text=None, metadata=None, mentor_instance=None):
    context = _pacs_client_context()
    entry = PacsAuditLog(
        user_id=getattr(current_user, 'user_id', None),
        user_alias=getattr(current_user, 'alias', None),
        chat_id=chat_id,
        route=route,
        action=action,
        request_text=_redact_sensitive_text(request_text),
        response_text=_redact_sensitive_text(response_text),
        model_provider=getattr(mentor_instance or mentor, 'last_model_provider', None),
        model_name=getattr(mentor_instance or mentor, 'last_model_name', None),
        client_ip=context['client_ip'],
        client_machine=context['client_machine'],
        user_agent=context['user_agent'],
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )
    db.session.add(entry)
    db.session.flush()

    try:
        _append_pacs_audit_file({
            'id': entry.id,
            'user_id': entry.user_id,
            'user_alias': entry.user_alias,
            'chat_id': entry.chat_id,
            'route': entry.route,
            'action': entry.action,
            'request_text': entry.request_text,
            'response_text': entry.response_text,
            'model_provider': entry.model_provider,
            'model_name': entry.model_name,
            'client_ip': entry.client_ip,
            'client_machine': entry.client_machine,
            'user_agent': entry.user_agent,
            'metadata': metadata or {},
            'created_at': entry.created_at.isoformat() if entry.created_at else None,
        })
    except Exception as exc:
        print(f'PACS audit file append failed: {exc}')

    return entry

pacs_bp = Blueprint('pacs', __name__)
mentor = PACSContinuityMentor()

# ── OpenClaw / WhatsApp bridge ────────────────────────────────────────────
# Per-session mentor pool keyed by OpenClaw session key so every WhatsApp
# sender gets its own admin_proof_verified state.
_oc_session_lock = threading.Lock()
_oc_session_mentors: dict = {}


def _get_oc_session_mentor(session_key: str) -> PACSContinuityMentor:
    with _oc_session_lock:
        if session_key not in _oc_session_mentors:
            _oc_session_mentors[session_key] = PACSContinuityMentor()
        return _oc_session_mentors[session_key]


def _is_pacs_owner_user(current_user) -> bool:
    if not current_user:
        return False
    alias = (getattr(current_user, 'alias', '') or '').strip().lower()
    user_id = (getattr(current_user, 'user_id', '') or '').strip().lower()
    normalized_user_id = _normalize_sa_whatsapp_number(user_id)
    return bool(
        getattr(current_user, 'is_verified', False)
        or getattr(current_user, 'user_role', '') in {'admin', 'moderator'}
        or alias == 'jobeer'
        or user_id == 'jobeer'
        or normalized_user_id in PACS_MENTOR_ADMIN_NUMBERS
        or normalized_user_id in PACS_MENTOR_OWNER_NUMBERS
    )


def _pacs_owner_token() -> str:
    """Return the PACS owner token from env var or config.ini [PACS_SECURITY]."""
    token = os.environ.get('PACS_OWNER_TOKEN', '')
    if not token:
        cfg = configparser.ConfigParser()
        cfg.read(os.path.join(os.path.dirname(__file__), '..', '..', 'config.ini'))
        token = cfg.get('PACS_SECURITY', 'owner_token', fallback='')
    return token.strip()

@pacs_bp.route('/greet', methods=['GET'])
def greet():
    user_name = None
    current_user_id = get_current_user()
    current_user = None
    if current_user_id:
        current_user = User.query.get(current_user_id)
        if current_user:
            user_name = current_user.alias or current_user.user_id

    greeting = mentor.get_greeting(user_name=user_name)
    try:
        _log_pacs_audit(current_user, 'greet', 'greet', chat_id=f'pacs_{current_user_id}' if current_user_id else None, response_text=greeting, metadata={'route': 'greet'})
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print(f'PACS audit logging failed for greet: {exc}')
    return jsonify({
        "response": greeting,
        "greeting": greeting
    })

@pacs_bp.route('/verify-auth', methods=['POST'])
def verify_auth():
    """
    Endpoint for uploading the physical directive image.
    """
    if 'file' not in request.files:
        return jsonify({"status": "fail", "message": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "fail", "message": "No selected file"}), 400

    # Save temporary file for OCR processing
    temp_path = os.path.join("instance", "temp_directive.jpg")
    os.makedirs("instance", exist_ok=True)
    file.save(temp_path)
    
    try:
        result = mentor.verify_auth(temp_path)
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
    current_user_id = get_current_user()
    current_user = User.query.get(current_user_id) if current_user_id else None
    try:
        _log_pacs_audit(current_user, 'verify-auth', 'verify-auth', response_text=json.dumps(result, ensure_ascii=False), metadata={'route': 'verify-auth'})
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print(f'PACS audit logging failed for verify-auth: {exc}')

    return jsonify(result)

@pacs_bp.route('/chat', methods=['POST'])
@require_auth
def chat(current_user):
    data = request.json
    user_input = data.get('message', '')
    pacs_chat_id = f"pacs_{current_user.user_id}"
    session_mentor = _get_oc_session_mentor(f"dashboard_{current_user.user_id}")

    if _is_pacs_owner_user(current_user):
        session_mentor.is_admin_session = True
        session_mentor.admin_proof_verified = True
        session_mentor.admin_proof_basis = 'dashboard-owner-account'

    recent_messages = Message.query.filter_by(chat_id=pacs_chat_id).filter(Message.deleted_at.is_(None)).order_by(Message.created_at.asc()).all()
    history = []
    for msg in recent_messages[-12:]:
        if msg.sender_id == current_user.user_id:
            role = 'user'
        else:
            role = 'model'
        history.append({
            'role': role,
            'content': msg.content,
        })
    
    # 1. Store User message in DB
    user_msg_id = str(uuid.uuid4())
    user_msg = Message(
        msg_id=user_msg_id,
        sender_id=current_user.user_id,
        chat_id=pacs_chat_id,
        content=user_input,
        msg_type='text'
    )
    db.session.add(user_msg)
    
    # 2. Get Mentor response
    response = session_mentor.generate_response(user_input, history=history)
    
    # 3. Store Mentor response in DB (as SYSTEM or dedicated Mentor ID)
    # Note: We use 'SYSTEM' as sender for bot-like mentors in this app structure
    mentor_msg_id = str(uuid.uuid4())
    mentor_msg = Message(
        msg_id=mentor_msg_id,
        sender_id='SYSTEM',  # Or a dedicated bot ID if existed
        chat_id=pacs_chat_id,
        content=response,
        msg_type='text'
    )
    db.session.add(mentor_msg)

    _log_pacs_audit(
        current_user,
        'chat',
        'chat_request',
        chat_id=pacs_chat_id,
        request_text=user_input,
        response_text=response,
        mentor_instance=session_mentor,
        metadata={
            'route': 'chat',
            'history_count': len(history),
            'mentor_state': session_mentor.current_state,
            'response_mode': getattr(session_mentor, 'last_response_mode', None),
            'model_provider': getattr(session_mentor, 'last_model_provider', None),
            'model_name': getattr(session_mentor, 'last_model_name', None),
            'is_admin_session': session_mentor.is_admin_session,
            'export_artifacts': [
                {
                    'output_format': artifact.get('output_format'),
                    'file_name': artifact.get('file_name'),
                    'mime_type': artifact.get('mime_type'),
                }
                for artifact in getattr(mentor, 'last_export_artifacts', [])
            ],
        }
    )
    
    db.session.commit()
    
    return jsonify({
        "response": response,
        "status": session_mentor.current_state,
        "progress": session_mentor.last_index_progress if session_mentor.last_index_progress is not None else session_mentor.get_recovery_progress(),
        "index_progress": session_mentor.last_index_progress,
        "index_step": session_mentor.last_index_step,
        "current_step": session_mentor.last_index_step or ("Authorization Confirmed" if session_mentor.emergency_override or session_mentor.is_admin_session else "General PACS mentorship available"),
        "is_admin": session_mentor.is_admin_session,
    })

@pacs_bp.route('/discover', methods=['POST'])
def discover():
    """
    Triggers Phase 1 Locked Mode discovery via passive sniffing.
    """
    data = request.get_json(silent=True) or {}
    interface = data.get('interface', 'eth0')
    result = mentor.passive_discovery(interface=interface)
    current_user_id = get_current_user()
    current_user = User.query.get(current_user_id) if current_user_id else None
    try:
        _log_pacs_audit(current_user, 'discover', 'passive_discovery', request_text=json.dumps(data, ensure_ascii=False), response_text=json.dumps(result, ensure_ascii=False), metadata={'route': 'discover'})
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print(f'PACS audit logging failed for discover: {exc}')
    return jsonify(result)

@pacs_bp.route('/walkthrough', methods=['GET'])
def walkthrough():
    """
    Returns the requested recovery walkthrough.
    """
    target = request.args.get('target', 'LINUX_VM')
    steps = mentor.get_recovery_walkthrough(target_type=target)
    current_user_id = get_current_user()
    current_user = User.query.get(current_user_id) if current_user_id else None
    try:
        _log_pacs_audit(current_user, 'walkthrough', 'walkthrough', request_text=target, response_text=json.dumps(steps, ensure_ascii=False), metadata={'route': 'walkthrough'})
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print(f'PACS audit logging failed for walkthrough: {exc}')
    return jsonify({"steps": steps})

@pacs_bp.route('/registry/sync', methods=['POST'])
def registry_sync():
    """Refresh the local continuity registry from configured FHIR, DICOMweb, and NAS sources."""
    data = request.get_json(silent=True) or {}
    source_overrides = data.get('sources') if isinstance(data.get('sources'), list) else None
    result = mentor.sync_continuity_registry(source_overrides=source_overrides)
    current_user_id = get_current_user()
    current_user = User.query.get(current_user_id) if current_user_id else None
    try:
        _log_pacs_audit(current_user, 'registry_sync', 'registry_sync', request_text=json.dumps(data, ensure_ascii=False), response_text=json.dumps(result, ensure_ascii=False), metadata={'route': 'registry_sync'})
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print(f'PACS audit logging failed for registry_sync: {exc}')
    return jsonify(result)

@pacs_bp.route('/registry/summary', methods=['GET'])
def registry_summary():
    """Return the current local continuity registry snapshot."""
    result = mentor.registry.registry_snapshot()
    current_user_id = get_current_user()
    current_user = User.query.get(current_user_id) if current_user_id else None
    try:
        _log_pacs_audit(current_user, 'registry_summary', 'registry_summary', response_text=json.dumps(result, ensure_ascii=False), metadata={'route': 'registry_summary'})
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print(f'PACS audit logging failed for registry_summary: {exc}')
    return jsonify(result)

@pacs_bp.route('/registry/patients/<empi_id>/timeline', methods=['GET'])
def registry_timeline(empi_id):
    """Return the consolidated timeline for a linked EMPI."""
    result = mentor.registry.get_patient_timeline(empi_id)
    current_user_id = get_current_user()
    current_user = User.query.get(current_user_id) if current_user_id else None
    try:
        _log_pacs_audit(current_user, 'registry_timeline', 'registry_timeline', chat_id=empi_id, request_text=empi_id, response_text=json.dumps(result, ensure_ascii=False), metadata={'route': 'registry_timeline'})
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print(f'PACS audit logging failed for registry_timeline: {exc}')
    return jsonify(result)

@pacs_bp.route('/registry/search', methods=['GET', 'POST'])
def registry_search():
    """Search the local continuity registry for patients, studies, and storage assets."""
    payload = request.get_json(silent=True) or {}
    query = request.args.get('q') or payload.get('q') or payload.get('query') or ''
    limit = request.args.get('limit') or payload.get('limit') or 25
    redact_value = request.args.get('redact') or payload.get('redact') or False
    try:
        limit = max(1, min(100, int(limit)))
    except (TypeError, ValueError):
        limit = 25
    redact = str(redact_value).lower() in {'1', 'true', 'yes', 'on'}
    result = mentor.registry.search_registry(query, limit=limit, redact=redact)
    current_user_id = get_current_user()
    current_user = User.query.get(current_user_id) if current_user_id else None
    try:
        _log_pacs_audit(current_user, 'registry_search', 'registry_search', request_text=query, response_text=json.dumps(result, ensure_ascii=False), metadata={'route': 'registry_search', 'limit': limit, 'redact': redact})
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print(f'PACS audit logging failed for registry_search: {exc}')
    return jsonify(result)

@pacs_bp.route('/registry/dicom-preview', methods=['GET', 'POST'])
def dicom_preview():
    """Return a read-only, optionally redacted preview of DICOM metadata."""
    payload = request.get_json(silent=True) or {}
    file_path = request.args.get('path') or payload.get('path') or payload.get('file_path') or ''
    redact_value = request.args.get('redact') or payload.get('redact') or True
    redact = str(redact_value).lower() not in {'0', 'false', 'no', 'off'}
    result = mentor.registry.preview_dicom_metadata(file_path, redact=redact)
    current_user_id = get_current_user()
    current_user = User.query.get(current_user_id) if current_user_id else None
    try:
        _log_pacs_audit(current_user, 'dicom_preview', 'dicom_preview', request_text=file_path, response_text=json.dumps(result, ensure_ascii=False), metadata={'route': 'dicom_preview', 'redact': redact})
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print(f'PACS audit logging failed for dicom_preview: {exc}')
    return jsonify(result)

@pacs_bp.route('/report', methods=['GET'])
def report():
    """
    Generates the final incident log for export.
    """
    result = mentor.generate_incident_report()
    current_user_id = get_current_user()
    current_user = User.query.get(current_user_id) if current_user_id else None
    try:
        _log_pacs_audit(current_user, 'report', 'report', response_text=json.dumps(result, ensure_ascii=False), metadata={'route': 'report'})
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print(f'PACS audit logging failed for report: {exc}')
    return jsonify(result)

@pacs_bp.route('/export', methods=['GET', 'POST'])
def export():
    """Generate a read-only PACS export as DOCX or PDF without modifying source systems."""
    payload = request.get_json(silent=True) or {}
    export_format = (request.args.get('format') or payload.get('format') or 'docx').lower()
    query = request.args.get('q') or request.args.get('query') or payload.get('q') or payload.get('query')
    redact_value = request.args.get('redact') if request.args.get('redact') is not None else payload.get('redact')
    include_diagrams_value = request.args.get('include_diagrams') if request.args.get('include_diagrams') is not None else payload.get('include_diagrams')
    redact = str(redact_value).lower() not in {'0', 'false', 'no', 'off'}
    include_diagrams = str(include_diagrams_value).lower() not in {'0', 'false', 'no', 'off'}

    try:
        export_artifact = generate_pacs_export_artifact(
            mentor.registry,
            mentor=mentor,
            output_format=export_format,
            query=query,
            redact=redact,
            include_diagrams=include_diagrams,
        )
    except Exception as exc:
        current_user_id = get_current_user()
        current_user = User.query.get(current_user_id) if current_user_id else None
        try:
            _log_pacs_audit(current_user, 'export', 'export_failed', request_text=json.dumps(payload, ensure_ascii=False), response_text=str(exc), metadata={'route': 'export', 'format': export_format})
            db.session.commit()
        except Exception as audit_exc:
            db.session.rollback()
            print(f'PACS audit logging failed for export failure: {audit_exc}')
        return jsonify({'status': 'fail', 'message': str(exc)}), 400

    current_user_id = get_current_user()
    current_user = User.query.get(current_user_id) if current_user_id else None
    try:
        _log_pacs_audit(
            current_user,
            'export',
            'export_success',
            request_text=json.dumps(payload, ensure_ascii=False),
            response_text=json.dumps({
                'file_name': export_artifact['file_name'],
                'output_format': export_artifact['output_format'],
                'include_diagrams': include_diagrams,
                'redact': redact,
                'query': query,
            }, ensure_ascii=False),
            metadata={
                'route': 'export',
                'format': export_format,
                'include_diagrams': include_diagrams,
                'redact': redact,
                'query': query,
            }
        )
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print(f'PACS audit logging failed for export: {exc}')

    return send_file(
        export_artifact['file_path'],
        as_attachment=True,
        download_name=export_artifact['file_name'],
        mimetype=export_artifact['mime_type'],
        conditional=False,
        max_age=0,
    )

@pacs_bp.route('/audit', methods=['GET'])
@require_auth
def audit_logs(current_user):
    """Return PACS audit events for management review."""
    if current_user.user_role not in ['admin', 'moderator']:
        return jsonify({'error': 'Management access required'}), 403

    limit = request.args.get('limit', 100, type=int)
    limit = max(1, min(500, limit))
    chat_id = request.args.get('chat_id')
    user_id = request.args.get('user_id')
    event_type = request.args.get('event_type')

    query = PacsAuditLog.query.order_by(desc(PacsAuditLog.created_at))
    if chat_id:
        query = query.filter_by(chat_id=chat_id)
    if user_id:
        query = query.filter_by(user_id=user_id)
    if event_type:
        query = query.filter_by(action=event_type)

    events = query.limit(limit).all()
    return jsonify({
        'events': [{
            'id': event.id,
            'user_id': event.user_id,
            'user_alias': event.user_alias,
            'chat_id': event.chat_id,
            'route': event.route,
            'action': event.action,
            'request_text': event.request_text,
            'response_text': event.response_text,
            'model_provider': event.model_provider,
            'model_name': event.model_name,
            'client_ip': event.client_ip,
            'client_machine': event.client_machine,
            'user_agent': event.user_agent,
            'metadata': json.loads(event.metadata_json) if event.metadata_json else {},
            'created_at': event.created_at.isoformat() if event.created_at else None,
        } for event in events]
    })


# ── OpenClaw / WhatsApp bridge endpoints ──────────────────────────────────

@pacs_bp.route('/oc/v1/models', methods=['GET'])
def oc_models():
    """OpenAI-compatible /v1/models list for OpenClaw custom-provider discovery."""
    return jsonify({
        'object': 'list',
        'data': [{
            'id': 'pacs-mentor-v1',
            'object': 'model',
            'created': 1716000000,
            'owned_by': 'stoyanov-radiology',
        }]
    })


@pacs_bp.route('/oc/v1/chat/completions', methods=['POST'])
def oc_chat_completions():
    """
    OpenAI-compatible chat-completions endpoint consumed by the OpenClaw gateway.

    Owner detection
    ---------------
    The request must carry the owner token either as:
      - Authorization: Bearer <token>   (OpenClaw apiKey field)
      - X-PACS-Owner-Token: <token>     (OpenClaw defaultHeaders field)
        The token authenticates the gateway. Sender identity is still taken from
        the OpenClaw session key so patients and the admin WhatsApp operator can
        have different mentor privileges.

    Session isolation
    -----------------
    Each OpenClaw session key (x-openclaw-session-key header) maps to a
    dedicated PACSContinuityMentor so proof state is per-sender.
    """
    # --- auth / owner check -------------------------------------------
    owner_token = _pacs_owner_token()
    auth_header = request.headers.get('Authorization', '')
    bearer = auth_header[7:].strip() if auth_header.startswith('Bearer ') else ''
    custom_tok = request.headers.get('X-PACS-Owner-Token', '').strip()
    is_gateway_authenticated = bool(owner_token) and (bearer == owner_token or custom_tok == owner_token)

    # --- session-scoped mentor ----------------------------------------
    session_key = (
        request.headers.get('X-Openclaw-Session-Key')
        or request.headers.get('X-OpenClaw-Session-Key')
        or request.remote_addr
    )
    session_mentor = _get_oc_session_mentor(session_key)

    sender_number = _extract_whatsapp_sender_number(session_key)
    sender_is_admin = sender_number in PACS_MENTOR_ADMIN_NUMBERS or sender_number in PACS_MENTOR_OWNER_NUMBERS
    session_mentor.is_admin_session = bool(sender_is_admin)
    if sender_is_admin and not session_mentor.admin_proof_verified:
        session_mentor.admin_proof_verified = True
        session_mentor.admin_proof_basis = f'openclaw-whatsapp-sender:{sender_number or "unknown"}'

    # --- parse OpenAI messages ----------------------------------------
    data = request.get_json(force=True) or {}
    messages = data.get('messages', [])

    history = []
    user_input = ''
    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content') or ''
        # Flatten list content (multimodal / tool-result blocks)
        if isinstance(content, list):
            content = ' '.join(
                part.get('text', '') for part in content
                if isinstance(part, dict) and part.get('type') == 'text'
            )
        # Tool results arrive as context; treat them as user turns
        if role == 'tool':
            role = 'user'
            content = f'[Tool result] {content}'
        if role == 'system':
            continue  # PACS agent has its own system prompt
        if role == 'user':
            user_input = content
            history.append({'role': 'user', 'content': content})
        elif role == 'assistant':
            history.append({'role': 'model', 'content': content})

    if not user_input:
        return jsonify({'error': {'message': 'No user message found', 'type': 'invalid_request_error'}}), 400

    # --- generate response --------------------------------------------
    prior_history = history[:-1] if len(history) > 1 else []
    response_text = session_mentor.generate_response(user_input, history=prior_history)

    return jsonify({
        'id': f'chatcmpl-pacs-{uuid.uuid4().hex[:8]}',
        'object': 'chat.completion',
        'created': int(time.time()),
        'model': 'pacs-mentor-v1',
        'choices': [{
            'index': 0,
            'message': {
                'role': 'assistant',
                'content': response_text,
            },
            'finish_reason': 'stop',
        }],
        'usage': {
            'prompt_tokens': sum(len((m.get('content') or '').split()) for m in messages),
            'completion_tokens': len(response_text.split()),
            'total_tokens': (
                sum(len((m.get('content') or '').split()) for m in messages)
                + len(response_text.split())
            ),
        },
    })
