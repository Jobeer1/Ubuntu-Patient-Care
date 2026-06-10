"""SDOH Flask Routes
===================
All SDOH-related HTTP endpoints extracted from agents.py.

Import order: this module imports `agents_bp`, `sdoh_agent`,
`_sdoh_owner_token`, and `_extract_sdoh_turn_from_payload` from agents.py.
agents.py imports this module at its bottom (after all those names are
defined) — a standard Flask split-file blueprint pattern.

Patient data principle: routes never store or forward raw medical files;
they return metadata and markdown only.  The patient controls what leaves
their device.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime

from flask import jsonify, request

from ..extensions import db
from ..models import Message, PaymentAllocation
from ..auth_utils import require_auth
from backend.agent_pacs import (
    _extract_whatsapp_sender_number,
    _normalize_sa_whatsapp_number,
    PACS_MENTOR_ADMIN_NUMBERS,
    PACS_MENTOR_OWNER_NUMBERS,
)

# These are defined in agents.py before this module is imported.
from backend.routes.agents import (
    agents_bp,
    sdoh_agent,
    _sdoh_owner_token,
    _extract_sdoh_turn_from_payload,
)


# ---------------------------------------------------------------------------
# /sdoh/chat
# ---------------------------------------------------------------------------

@agents_bp.route('/sdoh/chat', methods=['POST'])
@require_auth
def chat_with_sdoh(current_user):
    """Send message to the SDOH Continuity Agent."""
    data = request.json
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Empty message'}), 400

    chat_id = f"sdoh_{current_user.user_id}"
    content_lower = content.lower()

    def load_quest_progress():
        try:
            return json.loads(current_user.quest_progress) if current_user.quest_progress else {}
        except Exception:
            return {}

    def save_quest_progress(progress):
        current_user.quest_progress = json.dumps(progress)

    def update_sdoh_analytics(progress, result_payload):
        analytics = progress.get('sdoh_analytics', {}) if isinstance(progress, dict) else {}
        analytics['total_interactions'] = int(analytics.get('total_interactions', 0)) + 1

        if any(term in content_lower for term in ['ack', 'acknowledged', 'confirmed', 'confirmed it', 'done', 'scheduled', 'booked']):
            analytics['reminder_acknowledgment_count'] = int(analytics.get('reminder_acknowledgment_count', 0)) + 1

        if any(term in content_lower for term in ['completed', 'attended', 'went', 'done with it', 'showed up', 'went to the appointment']):
            analytics['follow_up_completion_count'] = int(analytics.get('follow_up_completion_count', 0)) + 1

        if result_payload.get('barrier_type') == 'transport' or any(term in content_lower for term in ['transport', 'ride', 'car', 'bus', 'taxi']):
            analytics['transport_coordination_count'] = int(analytics.get('transport_coordination_count', 0)) + 1

        if result_payload.get('barrier_type') == 'social' or any(term in content_lower for term in ['caregiver', 'family', 'trusted person', 'someone to go with', 'support with me']):
            analytics['caregiver_engagement_count'] = int(analytics.get('caregiver_engagement_count', 0)) + 1

        if result_payload.get('missed_window_reclamation'):
            analytics['missed_follow_up_rescue_count'] = int(analytics.get('missed_follow_up_rescue_count', 0)) + 1

        demo_case = any(term in content_lower for term in ['lung ct', 'follow-up pet', 'follow up pet', 'pet scan', 'left lung mass', 'suspicious lung', 'missed scheduling'])
        if demo_case:
            analytics['demo_case_count'] = int(analytics.get('demo_case_count', 0)) + 1
            analytics['last_demo_case'] = 'lung_ct_to_pet_rescue'

        analytics['last_event'] = {
            'timestamp': datetime.utcnow().isoformat(),
            'phase': result_payload.get('phase'),
            'severity': result_payload.get('severity'),
            'export_ready': bool(result_payload.get('export_bundle', {}).get('export_ready')) if isinstance(result_payload.get('export_bundle'), dict) else False,
        }

        total = max(analytics['total_interactions'], 1)
        analytics['reminder_acknowledgment_rate'] = round(analytics.get('reminder_acknowledgment_count', 0) / total, 3)
        analytics['follow_up_completion_rate'] = round(analytics.get('follow_up_completion_count', 0) / total, 3)
        analytics['transport_coordination_success_rate'] = round(analytics.get('transport_coordination_count', 0) / total, 3)
        analytics['caregiver_engagement_frequency'] = round(analytics.get('caregiver_engagement_count', 0) / total, 3)
        analytics['missed_follow_up_rescue_count'] = int(analytics.get('missed_follow_up_rescue_count', 0))
        progress['sdoh_analytics'] = analytics
        return progress, analytics

    try:
        history_msgs = (
            Message.query
            .filter_by(chat_id=chat_id)
            .filter(Message.deleted_at.is_(None))
            .order_by(Message.created_at.desc())
            .limit(50)
            .all()
        )
        history = []
        for msg in reversed(history_msgs):
            role = 'user' if msg.sender_id == current_user.user_id else 'model'
            history.append({'role': role, 'content': msg.content})
    except Exception as exc:
        print(f"Error loading SDOH history: {exc}")
        history = []

    user_msg = Message(
        msg_id=str(uuid.uuid4()),
        sender_id=current_user.user_id,
        chat_id=chat_id,
        content=content,
    )
    db.session.add(user_msg)

    result = sdoh_agent.chat(
        user_input=content,
        history=history,
        current_score=current_user.integrity_score,
        user_alias=current_user.alias,
        session_verified=current_user.is_verified,
        user_id=current_user.user_id,
        user_role=current_user.user_role,
    )

    if isinstance(result, dict):
        ai_response = result.get('response', str(result))
        score_adjustment = result.get('score_adjustment', 0)
        new_insight = result.get('new_insight')
        insight_type = result.get('insight_type', 'strength')
        phase = result.get('phase')
        confidence = result.get('confidence', 'high')
        verification_required = result.get('verification_required', False)
        timeline_items = result.get('timeline_items', [])
        draft_message = result.get('draft_message')
        barrier_type = result.get('barrier_type')
        barrier_classification = result.get('barrier_classification', barrier_type)
        source_paragraph = result.get('source_paragraph')
        extracted_task = result.get('extracted_task')
        anatomy = result.get('anatomy')
        modality = result.get('modality')
        timeline = result.get('timeline')
        severity = result.get('severity')
        continuity_priority = result.get('continuity_priority')
        clinician_summary = result.get('clinician_summary')
        missed_window_reclamation = result.get('missed_window_reclamation', False)
        export_bundle = result.get('export_bundle')
        patient_validation_required = result.get('patient_validation_required', False)
        patient_validation_verified = result.get('patient_validation_verified', False)
        outbound_ready = result.get('outbound_ready', False)
        whatsapp_number = result.get('whatsapp_number')
        payment_allocation_draft = result.get('payment_allocation_draft')
        route = result.get('route')
        tool_calls = result.get('tool_calls', [])
        requested_source_path = result.get('requested_source_path')
        indexing_progress = result.get('indexing_progress')
        metadata_summary = result.get('metadata_summary')
        whatsapp_scope = result.get('whatsapp_scope')
        whatsapp_access = result.get('whatsapp_access')
        assistant_number = result.get('assistant_number')
        detected_exports = result.get('detected_exports', [])
        detected_assistant_sources = result.get('detected_assistant_sources', [])
        admin_mode = result.get('admin_mode', False)
        patient_device_only = result.get('patient_device_only', False)
    else:
        ai_response = str(result)
        score_adjustment = 0
        new_insight = None
        insight_type = None
        phase = None
        confidence = 'high'
        verification_required = False
        timeline_items = []
        draft_message = None
        barrier_type = None
        barrier_classification = None
        source_paragraph = None
        extracted_task = None
        anatomy = None
        modality = None
        timeline = None
        severity = None
        continuity_priority = None
        clinician_summary = None
        missed_window_reclamation = False
        export_bundle = None
        patient_validation_required = False
        patient_validation_verified = False
        outbound_ready = False
        whatsapp_number = None
        payment_allocation_draft = None
        route = None
        tool_calls = []
        requested_source_path = None
        indexing_progress = None
        metadata_summary = None
        whatsapp_scope = None
        whatsapp_access = None
        assistant_number = None
        detected_exports = []
        detected_assistant_sources = []
        admin_mode = False
        patient_device_only = False

    quest_progress = load_quest_progress()
    quest_progress, sdoh_analytics = update_sdoh_analytics(quest_progress, {
        'phase': result.get('phase') if isinstance(result, dict) else 'local',
        'severity': severity,
        'export_bundle': export_bundle,
        'barrier_type': barrier_type,
        'missed_window_reclamation': missed_window_reclamation,
    })
    save_quest_progress(quest_progress)

    current_user.integrity_score = max(0, current_user.integrity_score + score_adjustment)
    current_user.is_verified = bool(current_user.is_verified or patient_validation_verified)

    payment_allocation_id = None
    if isinstance(payment_allocation_draft, dict):
        payment_status = payment_allocation_draft.get('status')
        if payment_status in ['draft', 'ready_for_allocation']:
            payment_allocation = PaymentAllocation(
                id=str(uuid.uuid4()),
                user_id=current_user.user_id,
                patient_alias=payment_allocation_draft.get('patient_alias') or current_user.alias,
                account_number=payment_allocation_draft.get('account_number'),
                invoice_number=payment_allocation_draft.get('invoice_number'),
                payment_reference=payment_allocation_draft.get('payment_reference'),
                amount=payment_allocation_draft.get('amount'),
                currency=payment_allocation_draft.get('currency') or 'ZAR',
                status='allocated' if payment_status == 'ready_for_allocation' and outbound_ready else 'draft',
                source_channel='sdoh_chat',
                verification_required=bool(payment_allocation_draft.get('verification_required', True)),
                verification_verified=bool(payment_allocation_draft.get('verification_verified', False)),
                allocated_account=payment_allocation_draft.get('account_number') if payment_status == 'ready_for_allocation' and outbound_ready else None,
                allocation_notes=ai_response,
            )
            db.session.add(payment_allocation)
            payment_allocation_id = payment_allocation.id

    if new_insight:
        try:
            current_insights = json.loads(current_user.insights) if current_user.insights else []
        except Exception:
            current_insights = []
        insight_texts = [i.get('text') for i in current_insights if isinstance(i, dict)]
        if new_insight not in insight_texts:
            current_insights.append({
                'text': new_insight,
                'type': insight_type,
                'xp': score_adjustment,
                'trigger_msg': content[:100] + '...' if len(content) > 100 else content,
                'date': datetime.utcnow().isoformat(),
            })
            current_user.insights = json.dumps(current_insights)

    agent_msg = Message(
        msg_id=str(uuid.uuid4()),
        sender_id='SDOH',
        chat_id=chat_id,
        content=ai_response,
    )
    db.session.add(agent_msg)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'response': ai_response,
        'phase': phase,
        'score': current_user.integrity_score,
        'insights': json.loads(current_user.insights) if current_user.insights else [],
        'verified': current_user.is_verified,
        'confidence': confidence,
        'verification_required': verification_required,
        'timeline_items': timeline_items,
        'draft_message': draft_message,
        'barrier_type': barrier_type,
        'barrier_classification': barrier_classification,
        'source_paragraph': source_paragraph,
        'extracted_task': extracted_task,
        'anatomy': anatomy,
        'modality': modality,
        'timeline': timeline,
        'severity': severity,
        'continuity_priority': continuity_priority,
        'clinician_summary': clinician_summary,
        'missed_window_reclamation': missed_window_reclamation,
        'patient_validation_required': patient_validation_required,
        'patient_validation_verified': patient_validation_verified,
        'outbound_ready': outbound_ready,
        'route': route,
        'tool_calls': tool_calls,
        'requested_source_path': requested_source_path,
        'indexing_progress': indexing_progress,
        'metadata_summary': metadata_summary,
        'whatsapp_scope': whatsapp_scope,
        'whatsapp_access': whatsapp_access,
        'assistant_number': assistant_number,
        'detected_exports': detected_exports,
        'detected_assistant_sources': detected_assistant_sources,
        'admin_mode': admin_mode,
        'patient_device_only': patient_device_only,
        'whatsapp_number': whatsapp_number,
        'payment_allocation_draft': payment_allocation_draft,
        'payment_allocation_id': payment_allocation_id,
        'export_bundle': export_bundle,
        'export_ready': export_bundle.get('export_ready') if isinstance(export_bundle, dict) else False,
        'calendar_events': export_bundle.get('calendar_events') if isinstance(export_bundle, dict) else [],
        'calendar_filename': export_bundle.get('calendar_filename') if isinstance(export_bundle, dict) else None,
        'ics_content': export_bundle.get('ics_content') if isinstance(export_bundle, dict) else None,
        'passport_filename': export_bundle.get('passport_filename') if isinstance(export_bundle, dict) else None,
        'passport_markdown': export_bundle.get('passport_markdown') if isinstance(export_bundle, dict) else None,
        'schema_notes': export_bundle.get('schema_notes') if isinstance(export_bundle, dict) else None,
        'analytics': sdoh_analytics,
        'demo_case': sdoh_analytics.get('last_demo_case'),
    })


# ---------------------------------------------------------------------------
# /sdoh/greeting
# ---------------------------------------------------------------------------

@agents_bp.route('/sdoh/greeting', methods=['GET'])
@require_auth
def get_sdoh_greeting(current_user):
    """Get personalised SDOH continuity greeting for the user."""
    indexer = sdoh_agent._get_indexer()
    index_stats = indexer.get_stats() if indexer else {}
    return jsonify({
        'greeting': sdoh_agent.greeting(current_user.alias, current_user.user_id, current_user.user_role),
        'agent': 'SDOH Patient Navigator',
        'role': 'Patient-owned health record, document indexing, and care continuity',
        'whatsapp_number': sdoh_agent.whatsapp_number,
        'index_stats': index_stats,
    })


# ---------------------------------------------------------------------------
# /sdoh/index-documents
# ---------------------------------------------------------------------------

@agents_bp.route('/sdoh/index-documents', methods=['POST'])
@require_auth
def sdoh_index_documents(current_user):
    """
    Trigger a local document index scan.

    Body (JSON, optional):
      { "folder": "/path/to/folder" }   -- scan a specific folder
      {}                                 -- scan all default directories
    """
    indexer = sdoh_agent._get_indexer()
    if not indexer:
        return jsonify({'error': 'Patient document indexer is not available in this deployment.'}), 503

    data = request.get_json(silent=True) or {}
    folder = (data.get('folder') or '').strip()

    try:
        if folder:
            result = indexer.scan_folder(os.path.expanduser(folder))
        else:
            result = indexer.scan_all_default_dirs()
        return jsonify({'status': 'success', **result})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# /sdoh/my-documents
# ---------------------------------------------------------------------------

@agents_bp.route('/sdoh/my-documents', methods=['GET'])
@require_auth
def sdoh_my_documents(current_user):
    """
    Return the full patient-side document index (metadata only, no file content).
    Supports optional query params: modality, body_part, doc_type, q
    """
    indexer = sdoh_agent._get_indexer()
    if not indexer:
        return jsonify({'error': 'Patient document indexer is not available in this deployment.'}), 503

    modality = request.args.get('modality', '').strip() or None
    body_part = request.args.get('body_part', '').strip() or None
    doc_type = request.args.get('doc_type', '').strip() or None
    text_query = request.args.get('q', '').strip() or None

    try:
        if any([modality, body_part, doc_type, text_query]):
            documents = indexer.search(
                modality=modality,
                body_part=body_part,
                doc_type=doc_type,
                text_query=text_query,
                limit=50,
            )
        else:
            documents = indexer._index

        # Strip file paths for security — return filename only, not full path
        safe_docs = []
        for doc in documents:
            safe_doc = {k: v for k, v in doc.items() if k not in {'text_preview', 'raw_header_hints'}}
            if 'file_path' in safe_doc:
                safe_doc['filename'] = os.path.basename(safe_doc.pop('file_path'))
            safe_docs.append(safe_doc)

        stats = indexer.get_stats()
        return jsonify({'status': 'success', 'documents': safe_docs, 'total': len(safe_docs), 'stats': stats})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# /sdoh/history-pack
# ---------------------------------------------------------------------------

@agents_bp.route('/sdoh/history-pack', methods=['POST'])
@require_auth
def sdoh_history_pack(current_user):
    """
    Build a patient-approved history pack for sharing with a practice.

    Body (JSON):
      {
        "visit_description": "I need a CT scan of my chest",
        "approved_filenames": ["report_2026.pdf", "chest_ct.dcm"]   // optional
      }

    Returns the history pack as markdown text.  The pack is NEVER sent to any
    external service — it is returned to the patient's browser/app for them to
    download or forward themselves.
    """
    indexer = sdoh_agent._get_indexer()
    if not indexer:
        return jsonify({'error': 'Patient document indexer is not available in this deployment.'}), 503

    data = request.get_json(silent=True) or {}
    visit_description = (data.get('visit_description') or '').strip() or 'upcoming medical visit'
    approved_filenames = data.get('approved_filenames') or []

    approved_paths = None
    if approved_filenames:
        approved_set = set(approved_filenames)
        approved_paths = [
            entry['file_path']
            for entry in indexer._index
            if os.path.basename(entry.get('file_path', '')) in approved_set
        ]

    try:
        pack = indexer.build_history_pack(
            user_alias=current_user.alias,
            visit_description=visit_description,
            approved_file_paths=approved_paths if approved_paths else None,
        )
        return jsonify({
            'status': 'success',
            'document_count': pack['document_count'],
            'filename': pack['filename'],
            'history_pack_markdown': pack['history_pack_markdown'],
            'note': (
                'This history pack lives on your device only. '
                'Download it and hand it to your doctor — nothing has been uploaded or shared.'
            ),
        })
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# OpenClaw / OpenAI-compatible endpoints
# ---------------------------------------------------------------------------

@agents_bp.route('/oc/v1/models', methods=['GET'])
def sdoh_oc_models():
    """OpenAI-compatible model list for OpenClaw discovery."""
    return jsonify({
        'object': 'list',
        'data': [{
            'id': 'sdoh-continuity-v1',
            'object': 'model',
            'created': 1716000000,
            'owned_by': 'stoyanov-radiology',
        }],
    })


@agents_bp.route('/oc/v1/chat/completions', methods=['POST'])
def sdoh_oc_chat_completions():
    """OpenAI-compatible SDOH chat-completions endpoint for OpenClaw."""
    owner_token = _sdoh_owner_token()
    auth_header = request.headers.get('Authorization', '')
    bearer = auth_header[7:].strip() if auth_header.startswith('Bearer ') else ''
    custom_tok = request.headers.get('X-SDOH-Owner-Token', '').strip()
    is_gateway_authenticated = bool(owner_token) and (bearer == owner_token or custom_tok == owner_token)

    if not is_gateway_authenticated:
        return jsonify({'error': {'message': 'Unauthorized', 'type': 'authentication_error'}}), 401

    session_key = (
        request.headers.get('X-Openclaw-Session-Key')
        or request.headers.get('X-OpenClaw-Session-Key')
        or request.remote_addr
    )

    data = request.get_json(force=True) or {}
    user_input, history = _extract_sdoh_turn_from_payload(data)

    if not user_input:
        return jsonify({'error': {'message': 'No user message found', 'type': 'invalid_request_error'}}), 400

    sender_number = _extract_whatsapp_sender_number(session_key)
    if not sender_number:
        # OpenClaw prefixes WhatsApp messages with "[WhatsApp +XXXXXXXXXXX ...]";
        # fall back to extracting the sender number from the message body.
        sender_number = _extract_whatsapp_sender_number(user_input)
    sender_is_owner = sender_number in PACS_MENTOR_OWNER_NUMBERS or sender_number == _normalize_sa_whatsapp_number('+27663764491')
    sender_is_admin = sender_number in PACS_MENTOR_ADMIN_NUMBERS or sender_number == _normalize_sa_whatsapp_number('+27768193339')

    # Limit prior history to last 6 messages (3 exchanges) to prevent context overflow
    # in OpenClaw sessions. The agent already limits recent history internally.
    prior_history = history[-6:-1] if len(history) > 6 else history[:-1] if len(history) > 1 else []
    result = sdoh_agent.chat(
        user_input=user_input,
        history=prior_history,
        current_score=0,
        user_alias='Admin' if sender_is_admin else 'Patient',
        session_verified=sender_is_owner or sender_is_admin or is_gateway_authenticated,
        sender_number=sender_number,
        user_role='admin' if sender_is_admin else None,
    )

    response_text = result.get('response', str(result)) if isinstance(result, dict) else str(result)
    route = result.get('route') if isinstance(result, dict) else None
    tool_calls = result.get('tool_calls', []) if isinstance(result, dict) else []
    requested_source_path = result.get('requested_source_path') if isinstance(result, dict) else None
    indexing_progress = result.get('indexing_progress') if isinstance(result, dict) else None
    metadata_summary = result.get('metadata_summary') if isinstance(result, dict) else None
    messages = data.get('messages', [])
    return jsonify({
        'id': f'chatcmpl-sdoh-{uuid.uuid4().hex[:8]}',
        'object': 'chat.completion',
        'created': int(time.time()),
        'model': 'sdoh-continuity-v1',
        'choices': [{
            'index': 0,
            'message': {'role': 'assistant', 'content': response_text},
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
        'route': route,
        'tool_calls': tool_calls,
        'requested_source_path': requested_source_path,
        'indexing_progress': indexing_progress,
        'metadata_summary': metadata_summary,
        'sender_number': sender_number,
        'whatsapp_number': sdoh_agent.whatsapp_number,
        'admin_mode': result.get('admin_mode', False) if isinstance(result, dict) else False,
        'patient_validation_required': result.get('patient_validation_required', False) if isinstance(result, dict) else False,
        'patient_validation_verified': result.get('patient_validation_verified', False) if isinstance(result, dict) else False,
        'outbound_ready': result.get('outbound_ready', False) if isinstance(result, dict) else False,
        'payment_allocation_draft': result.get('payment_allocation_draft') if isinstance(result, dict) else None,
    })


@agents_bp.route('/oc/v1/responses', methods=['POST'])
def sdoh_oc_responses():
    """OpenAI Responses-compatible SDOH endpoint for OpenClaw."""
    owner_token = _sdoh_owner_token()
    auth_header = request.headers.get('Authorization', '')
    bearer = auth_header[7:].strip() if auth_header.startswith('Bearer ') else ''
    custom_tok = request.headers.get('X-SDOH-Owner-Token', '').strip()
    is_gateway_authenticated = bool(owner_token) and (bearer == owner_token or custom_tok == owner_token)

    if not is_gateway_authenticated:
        return jsonify({'error': {'message': 'Unauthorized', 'type': 'authentication_error'}}), 401

    session_key = (
        request.headers.get('X-Openclaw-Session-Key')
        or request.headers.get('X-OpenClaw-Session-Key')
        or request.remote_addr
    )

    data = request.get_json(force=True) or {}
    user_input, history = _extract_sdoh_turn_from_payload(data)

    if not user_input:
        return jsonify({'error': {'message': 'No user message found', 'type': 'invalid_request_error'}}), 400

    sender_number = _extract_whatsapp_sender_number(session_key)
    if not sender_number:
        # OpenClaw prefixes WhatsApp messages with "[WhatsApp +XXXXXXXXXXX ...]";
        # fall back to extracting the sender number from the message body.
        sender_number = _extract_whatsapp_sender_number(user_input)
    sender_is_owner = sender_number in PACS_MENTOR_OWNER_NUMBERS or sender_number == _normalize_sa_whatsapp_number('+27663764491')
    sender_is_admin = sender_number in PACS_MENTOR_ADMIN_NUMBERS or sender_number == _normalize_sa_whatsapp_number('+27768193339')

    # Limit prior history to last 6 messages (3 exchanges) to prevent context overflow
    # in OpenClaw sessions. The agent already limits recent history internally.
    prior_history = history[-6:-1] if len(history) > 6 else history[:-1] if len(history) > 1 else []
    result = sdoh_agent.chat(
        user_input=user_input,
        history=prior_history,
        current_score=0,
        user_alias='Admin' if sender_is_admin else 'Patient',
        session_verified=sender_is_owner or sender_is_admin or is_gateway_authenticated,
        sender_number=sender_number,
        user_role='admin' if sender_is_admin else None,
    )

    response_text = result.get('response', str(result)) if isinstance(result, dict) else str(result)
    # Use truncated history count for accurate token reporting
    truncated_messages = history[-6:] if len(history) > 6 else history
    prompt_tokens = sum(len((m.get('content') or '').split()) for m in truncated_messages)
    if not prompt_tokens and isinstance(data.get('input'), str):
        prompt_tokens = len(data.get('input', '').split())
    completion_tokens = len(response_text.split())
    route = result.get('route') if isinstance(result, dict) else None
    tool_calls = result.get('tool_calls', []) if isinstance(result, dict) else []
    requested_source_path = result.get('requested_source_path') if isinstance(result, dict) else None
    indexing_progress = result.get('indexing_progress') if isinstance(result, dict) else None
    metadata_summary = result.get('metadata_summary') if isinstance(result, dict) else None

    return jsonify({
        'id': f'resp-sdoh-{uuid.uuid4().hex[:8]}',
        'object': 'response',
        'created_at': int(time.time()),
        'status': 'completed',
        'model': 'sdoh-continuity-v1',
        'output': [{
            'id': f'msg-{uuid.uuid4().hex[:8]}',
            'type': 'message',
            'role': 'assistant',
            'content': [{'type': 'output_text', 'text': response_text}],
        }],
        'usage': {
            'input_tokens': prompt_tokens,
            'output_tokens': completion_tokens,
            'total_tokens': prompt_tokens + completion_tokens,
        },
        'route': route,
        'tool_calls': tool_calls,
        'requested_source_path': requested_source_path,
        'indexing_progress': indexing_progress,
        'metadata_summary': metadata_summary,
    })


# ---------------------------------------------------------------------------
# /index_folder (direct folder path endpoint for proxy)
# Note: Blueprint is registered with /api/sdoh prefix in flask_app.py, so route is just /index_folder
# ---------------------------------------------------------------------------

@agents_bp.route('/index_folder', methods=['POST'])
def sdoh_index_folder():
    """
    Index a specific folder path provided directly (used by sdoh_oc_proxy).
    
    Body (JSON):
      { "folder_path": "X:\\\\UV images\\\\2018" }
    
    Returns immediate progress summary - the proxy doesn't have auth context so
    this endpoint operates in guest mode (no persisted user data).
    """
    indexer = None
    try:
        from backend.sdoh_patient_index import PatientDocumentIndexer
        indexer = PatientDocumentIndexer()
    except Exception as exc:
        return jsonify({'error': f'Indexer unavailable: {exc}'}), 503

    data = request.get_json(silent=True) or {}
    folder_path = (data.get('folder_path') or '').strip()
    
    if not folder_path:
        return jsonify({'error': 'No folder_path provided'}), 400

    # Progress tracking for large folder indexing
    progress_updates = []
    def _progress_callback(scanned, new_entries, current_path):
        progress_updates.append({
            'scanned': scanned,
            'new_entries': new_entries,
            'current_path': current_path,
            'timestamp': datetime.utcnow().isoformat(),
        })

    try:
        import os
        expanded_path = os.path.expanduser(folder_path)
        result = indexer.scan_folder(expanded_path, progress_callback=_progress_callback)
        
        # Include progress history in response
        result['progress_updates'] = progress_updates
        result['status'] = 'completed'
        
        # Format user-friendly summary
        summary_lines = [
            f'✅ Indexing completed for: {folder_path}',
            f'   Files scanned: {result.get("scanned", 0)}',
            f'   New files added: {result.get("new", 0)}',
            f'   Total indexed: {result.get("total_indexed", 0)}',
            f'   Time elapsed: {result.get("elapsed_sec", 0):.1f}s',
        ]
        
        if result.get('error'):
            summary_lines.append(f'   Warning: {result.get("error")}')
        
        return jsonify({
            'status': 'success',
            'summary': '\n'.join(summary_lines),
            'progress_updates': progress_updates,
            **result,
        })
    except Exception as exc:
        import traceback
        return jsonify({
            'status': 'error',
            'error': str(exc),
            'traceback': traceback.format_exc()[-1000:],
            'progress_updates': progress_updates,
        }), 500
