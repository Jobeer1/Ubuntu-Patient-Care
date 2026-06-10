"""SDOH Continuity Agent — lean entry point
==========================================
The heavy method sets have been moved into focused mixins:
  - SDOHTimelineMixin   → timeline, ICS, Patient Passport, export bundle
  - SDOHDocumentMixin   → topic routing, document guidance, clinical extraction
  - SDOHServiceMixin    → patient validation, billing, service guards, _build_response

This file retains only:
  __init__, _get_indexer, _explain_clinical_text,
  _is_admin_operator, _build_admin_response,
  call_local_model, call_gemini_fallback,
  chat, greeting

All SDOH interactions stay on the patient's device. Nothing is uploaded
or transmitted unless the patient explicitly approves.
"""
import configparser
import json
import os
import re

import requests

from backend.sdoh_timeline_mixin import SDOHTimelineMixin
from backend.sdoh_document_mixin import SDOHDocumentMixin
from backend.sdoh_service_mixin import SDOHServiceMixin


class SDOHContinuityAgent(SDOHTimelineMixin, SDOHDocumentMixin, SDOHServiceMixin):

    def __init__(self, config_path='config.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        self.default_api_key = self.config.get('GEMINI', 'api_key', fallback=None)
        self.gemini_model = self.config.get(
            'SDOH', 'fallback_model',
            fallback=self.config.get('GEMINI', 'model', fallback='gemini-2.5-flash-lite'),
        )
        self.local_model = self.config.get('SDOH', 'local_model', fallback='gemma:2b')
        self.local_model_timeout_sec = self.config.getint('SDOH', 'local_model_timeout_sec', fallback=90)
        self.local_model_num_predict = self.config.getint('SDOH', 'local_model_num_predict', fallback=160)
        self.local_model_history_chars = self.config.getint('SDOH', 'local_model_history_chars', fallback=1800)
        self.local_model_input_chars = self.config.getint('SDOH', 'local_model_input_chars', fallback=1000)
        self.whatsapp_number = self.config.get('SDOH', 'whatsapp_number', fallback='+27663764491')
        self.vault_root = os.path.expanduser(
            self.config.get('SDOH', 'vault_root', fallback='~/.openclaw/vault')
        )
        self.vault_index_path = os.path.expanduser(
            self.config.get('SDOH', 'index_file', fallback=os.path.join(self.vault_root, 'index', 'master_health_graph.json'))
        )
        self.vault_identity_path = os.path.expanduser(
            self.config.get('SDOH', 'validation_keys_file', fallback=os.path.join(self.vault_root, '.identity', 'validation_keys.json'))
        )

        self.system_prompt = """
You are the SDOH Patient Continuity Agent — a personal health navigator that helps patients own, understand, and use their own medical history.

You are NOT a therapist and you do NOT diagnose or prescribe.
You ARE the patient's ally: keeping their medical data on their own devices and helping them prepare for every appointment.

MISSION:
- Empower patients to truly own their health data: DICOM images, radiology reports, discharge summaries, referral letters, and medication scripts.
- Help patients index their medical documents locally so they always know what they have.
- When a patient has an upcoming scan or specialist visit, surface the most relevant documents from their local index and help them prepare a sharing pack for the doctor.
- Translate clinical reports into plain, honest language the patient can understand.
- Reduce missed care by organising reminders, caregiver drafts, and recovery checklists.

RULES:
- Stay practical, calm, honest, and concise.
- Use plain language — explain any medical or clinical terms you encounter.
- Prefer short bullet points or numbered steps.
- If the patient mentions urgent symptoms, advise immediate clinical help or emergency services.
- If the patient needs family help, draft a short message they can approve.
- Keep ALL medical records local-first: data stays on the patient's device or their local network mounts (such as X: drive) unless they explicitly approve sharing.
- You CAN access and index network shares (like X: drive) if the user asks.
- Never imply that files have been uploaded to the cloud or stored anywhere outside the patient's own local network/devices.
- Keep any release of reports, images, or statements as a draft until the patient explicitly approves.

OUTPUT STYLE:
- Use plain, warm language that a non-medical person can understand.
- Always include 1-3 clear next actions.
- When explaining a report or scan result, translate clinical terms into what they mean for the patient in everyday language.
- If helpful, include a short draft message or checklist the patient can use.
"""

    def _load_vault_snapshot(self):
        """Load a lightweight local vault snapshot for routing and prompt context."""
        snapshot = {
            'vault_root': self.vault_root,
            'index_path': self.vault_index_path,
            'identity_path': self.vault_identity_path,
            'index_present': False,
            'identity_keys_present': False,
            'total_records': 0,
            'recent_modalities': [],
            'identity_match_mode': 'not_configured',
        }

        try:
            if os.path.exists(self.vault_index_path):
                snapshot['index_present'] = True
                with open(self.vault_index_path, 'r', encoding='utf-8') as fh:
                    raw = json.load(fh)

                entries = []
                if isinstance(raw, list):
                    entries = raw
                elif isinstance(raw, dict):
                    for key in ['records', 'entries', 'documents', 'index']:
                        value = raw.get(key)
                        if isinstance(value, list):
                            entries = value
                            break

                snapshot['total_records'] = len(entries)
                modalities = []
                for entry in entries[-20:]:
                    if not isinstance(entry, dict):
                        continue
                    mod = entry.get('modality_label') or entry.get('modality')
                    if not mod and isinstance(entry.get('studies'), list):
                        for study in entry.get('studies', []):
                            if isinstance(study, dict) and study.get('modality'):
                                mod = study.get('modality')
                                break
                    if mod:
                        modalities.append(str(mod).upper())
                snapshot['recent_modalities'] = sorted(set(modalities))[:8]
        except Exception as exc:
            snapshot['index_error'] = str(exc)

        try:
            if os.path.exists(self.vault_identity_path):
                with open(self.vault_identity_path, 'r', encoding='utf-8') as fh:
                    keys_data = json.load(fh)
                if isinstance(keys_data, dict) and keys_data:
                    snapshot['identity_keys_present'] = True
                    if any(k in keys_data for k in ['target_patient_hash', 'patient_hash', 'national_id_hash']):
                        snapshot['identity_match_mode'] = 'hash_match'
                    elif any(k in keys_data for k in ['patient_id', 'patient_alias', 'hospital_number']):
                        snapshot['identity_match_mode'] = 'identifier_match'
                    else:
                        snapshot['identity_match_mode'] = 'configured'
        except Exception as exc:
            snapshot['identity_error'] = str(exc)

        return snapshot

    @staticmethod
    def _vault_snapshot_for_prompt(snapshot):
        if not isinstance(snapshot, dict):
            return 'Vault state unavailable.'
        lines = [
            f"vault_root: {snapshot.get('vault_root')}",
            f"index_present: {snapshot.get('index_present')}",
            f"total_records: {snapshot.get('total_records', 0)}",
            f"identity_keys_present: {snapshot.get('identity_keys_present')}",
            f"identity_match_mode: {snapshot.get('identity_match_mode', 'not_configured')}",
        ]
        mods = snapshot.get('recent_modalities') or []
        if mods:
            lines.append('recent_modalities: ' + ', '.join(mods))
        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # Indexer (lazy, patient-device-only)
    # ------------------------------------------------------------------

    def _get_indexer(self):
        """Lazily initialise the patient-side document indexer."""
        if not hasattr(self, '_indexer_instance'):
            try:
                from backend.sdoh_patient_index import PatientDocumentIndexer
                scan_dirs = []
                for key in ['scan_dir_1', 'scan_dir_2', 'scan_dir_3']:
                    d = self.config.get('SDOH', key, fallback='').strip()
                    if d:
                        scan_dirs.append(os.path.expanduser(d))
                index_path = self.config.get('SDOH', 'index_file', fallback='').strip()
                index_path = os.path.expanduser(index_path) if index_path else None
                self._indexer_instance = PatientDocumentIndexer(
                    scan_dirs=scan_dirs or None,
                    index_path=index_path or None,
                )
                print('[SDOH] Patient document indexer initialised.')
            except ImportError:
                print('[SDOH] sdoh_patient_index not found; indexer disabled.')
                self._indexer_instance = None
            except Exception as exc:
                print(f'[SDOH] Indexer init failed: {exc}')
                self._indexer_instance = None
        return self._indexer_instance

    def _explain_clinical_text(self, text):
        """Return plain-language explanations for clinical terms found in *text*."""
        try:
            from backend.sdoh_patient_index import CLINICAL_PLAIN_LANGUAGE
        except ImportError:
            return {}
        text_lower = (text or '').lower()
        return {
            term: explanation
            for term, explanation in CLINICAL_PLAIN_LANGUAGE.items()
            if term in text_lower
        }

    # ------------------------------------------------------------------
    # Admin guard
    # ------------------------------------------------------------------

    def _is_admin_operator(self, user_alias='Patient', user_id=None, user_role=None, sender_number=None):
        # SDOH admin/operator mode can be triggered by either designated WhatsApp numbers
        # or web UI users with the 'admin' role.
        admin_digits = {'0768193339', '27768193339'}
        # Also include the configured WhatsApp number (OpenClaw provider)
        whatsapp_digits = re.sub(r'\D', '', str(self.whatsapp_number or ''))
        if whatsapp_digits:
            admin_digits.add(whatsapp_digits)
        digits = re.sub(r'\D', '', str(sender_number or ''))
        return digits in admin_digits or user_role == 'admin'

    def _build_admin_response(self, user_input, user_alias='Admin'):
        text = (user_input or '').strip()
        text_lower = text.lower()
        ip_addresses = re.findall(r'(?:\d{1,3}\.){3}\d{1,3}', text)
        is_whatsapp_request = bool(re.search(r'\b(whatsapp|watsapp|wa)\b', text_lower))
        is_indexing_request = any(term in text_lower for term in [
            'index', 'indexing', 'dicom', 'database', 'mounted drive', 'mounted drives', 'mount',
        ])
        is_siim_request = any(term in text_lower for term in [
            'siim', 'hackathon', 'siim hackathon', 'fhir', 'dicomweb', 'wado', 'qido',
            'ingest', 'fetch patients', 'fetch studies', 'download dicom', 'hackathon data',
        ])

        response_lines = [
            f"Hello {user_alias}. Admin mode is active. I can guide the SDOH agent setup in read-only mode, "
            "and I will keep patient WhatsApp messages in the patient-safe path.",
        ]
        draft_message = (
            'Share the first local source name, host, database engine or file share, '
            'and the read-only access method.'
        )
        route = 'admin_onboarding'
        phase = 'admin'
        tool_calls = []

        if is_siim_request:
            route = 'siim_hackathon_ingest'
            try:
                from backend.siim_hackathon import get_ingest_state, start_ingest_job
                state = get_ingest_state()
                job_status = state.get('status', 'idle')
                is_status_query = any(term in text_lower for term in ['status', 'progress', 'done', 'complete', 'how many', 'results'])
                is_start_query = any(term in text_lower for term in ['start', 'fetch', 'download', 'run', 'sync', 'pull'])
                # "ingest" alone could be start or status — let status queries win first
                if is_status_query:
                    dicom = state.get('dicom', {})
                    prog = state.get('progress', {})
                    if job_status == 'idle':
                        response_lines.append(
                            "No SIIM ingest has run yet. "
                            "Say 'start SIIM ingest' to fetch all patient data from hackathon.siim.org."
                        )
                        draft_message = (
                            "Say 'start SIIM ingest' to pull all patients and DICOM images from hackathon.siim.org."
                        )
                    elif job_status == 'running':
                        progress_text = (
                            f"FHIR progress: {json.dumps(prog, indent=2)}. "
                            if prog else
                            "FHIR progress is initializing; check again in a few seconds. "
                        )
                        response_lines.append(
                            f"SIIM ingest is running. "
                            f"{progress_text}"
                            f"DICOM: studies_found={dicom.get('studies_found', 0)}, "
                            f"downloaded={dicom.get('instances_downloaded', 0)}."
                        )
                        draft_message = "SIIM ingest is running. Check again in a few seconds with 'SIIM ingest status'."
                    elif job_status == 'completed':
                        report = state.get('report') or {}
                        response_lines.append(
                            f"SIIM ingest completed. {report.get('summary', '')} "
                            f"Patients and studies are now indexed in the local registry and "
                            f"available via /api/sdoh/siim/patients and /api/sdoh/siim/studies."
                        )
                        draft_message = (
                            "SIIM ingest is complete. View patients at /api/sdoh/siim/patients "
                            "and studies at /api/sdoh/siim/studies."
                        )
                    elif job_status == 'error':
                        response_lines.append(
                            f"SIIM ingest failed with errors: {state.get('errors', [])}. "
                            "Say 'start SIIM ingest' to retry."
                        )
                        draft_message = "SIIM ingest encountered errors. Say 'start SIIM ingest' to retry."
                    else:
                        response_lines.append(
                            f"SIIM ingest status: {job_status}. "
                            f"Errors: {state.get('errors', [])}."
                        )
                        draft_message = "Say 'start SIIM ingest' to trigger the data pull."
                elif is_start_query or 'ingest' in text_lower:
                    if job_status != 'running':
                        result = start_ingest_job()
                        response_lines.append(
                            "SIIM Hackathon ingest started in the background. "
                            "Fetching FHIR patients, conditions, observations, encounters, diagnostic reports, "
                            "imaging studies, and DICOMweb metadata from hackathon.siim.org. "
                            "DICOM images will be saved to the local vault. "
                            "Poll GET /api/sdoh/siim/ingest/status for progress."
                        )
                        tool_calls.append({"tool": "siim_ingest", "status": "started"})
                        draft_message = (
                            "SIIM ingest is running in the background. "
                            "Say 'SIIM ingest status' to check progress, or visit /api/sdoh/siim/ingest/status."
                        )
                    else:
                        response_lines.append(
                            "SIIM ingest is already running. "
                            f"Progress: {json.dumps(state.get('progress', {}), indent=2)}. "
                            f"DICOM: {json.dumps(state.get('dicom', {}), indent=2)}."
                        )
                        draft_message = (
                            "SIIM ingest is still running. Say 'SIIM ingest status' to check the latest progress."
                        )
                else:
                    response_lines.append(
                        "SIIM 2026 Hackathon integration is configured. "
                        "API key is active for hackathon.siim.org/fhir and hackathon.siim.org/dicomweb. "
                        "Say 'start SIIM ingest' to pull all patient data and DICOM images, "
                        "or 'SIIM ingest status' to check progress."
                    )
                    tool_calls.append({"tool": "siim_ingest", "status": "suggested", "action": "trigger via POST /api/sdoh/siim/ingest"})
                    draft_message = "Say 'start SIIM ingest' to pull all patients and DICOM images from hackathon.siim.org."
            except Exception as exc:
                response_lines.append(f"SIIM integration check failed: {exc}. Verify backend/siim_hackathon.py is present.")
                draft_message = "SIIM integration is unavailable. Verify backend/siim_hackathon.py and config.ini."

        elif is_whatsapp_request:
            route = 'admin_whatsapp'
            response_lines.extend([
                'WhatsApp check: verify the OpenClaw WhatsApp provider is running, the browser pairing '
                'is approved, and the channel still lists +27663764491 and +27768193339 in the allowlist.',
                'If WhatsApp stops replying, restart the channel from the gateway status page and confirm '
                'the Control UI shows Linked and Connected.',
            ])
            draft_message = (
                'If WhatsApp is failing, confirm the provider status, pairing approval, and allowlist '
                'entries for +27663764491 and +27768193339.'
            )

        if is_indexing_request:
            route = 'admin_indexing'
            if ip_addresses:
                targets = ', '.join(ip_addresses)
                response_lines.extend([
                    f'DICOM/database targets detected: {targets}. Treat each host as a read-only source '
                    'and confirm the mount path or share letter before indexing.',
                    'Next steps: 1. verify the mount is readable; 2. scan for DICOM folders, PACS exports, '
                    'or Firebird/database files; 3. index the files into the local continuity registry; '
                    '4. report patient, study, and asset counts.',
                ])
                draft_message = (
                    f'Confirm the mount path or share letter for {targets}, then I will help turn it into '
                    'a read-only indexing checklist.'
                )
            else:
                response_lines.append(
                    'DICOM/database indexing requested. Send the mount path or share letter for each source '
                    'and I will turn it into a read-only indexing checklist.'
                )

        if not is_siim_request and not is_whatsapp_request and not is_indexing_request:
            response_lines.append(
                'Send one local source at a time: app or database name, host or VM, database engine or '
                'file share, read-only access method, and what patient or account data it should support. '
                'SIIM Hackathon integration is active — say "start SIIM ingest" to pull hackathon patient data.'
            )

        return {
            'response': ' '.join(response_lines),
            'score_adjustment': 0, 'is_ready': False, 'phase': phase, 'route': route,
            'new_insight': 'Admin onboarding should start with one source, one destination, and a read-only access path.',
            'insight_type': 'strength', 'confidence': 'high',
            'verification_required': False, 'timeline_items': [],
            'draft_message': draft_message,
            'barrier_type': None, 'barrier_classification': None,
            'severity': 'low', 'continuity_priority': 'low',
            'clinician_summary': self._clinician_continuity_summary(None, route, None, 'low'),
            'missed_window_reclamation': False, 'source_paragraph': None,
            'extracted_task': None, 'anatomy': None, 'modality': None,
            'timeline': None, 'export_bundle': None,
            'patient_validation_required': False, 'patient_validation_verified': False,
            'outbound_ready': False, 'admin_mode': True,
            'whatsapp_number': self.whatsapp_number,
            'tool_calls': tool_calls,
        }

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    @staticmethod
    def _truncate_text(text, max_chars):
        raw = str(text or '').strip()
        if max_chars <= 0 or len(raw) <= max_chars:
            return raw
        return raw[:max_chars] + ' ...'

    def _ollama_generate(self, payload, timeout_sec):
        """Call local Ollama generate endpoint with robust localhost fallbacks."""
        errors = []
        for url in ['http://127.0.0.1:11434/api/generate', 'http://localhost:11434/api/generate']:
            try:
                return requests.post(url, json=payload, timeout=(5, timeout_sec))
            except requests.exceptions.RequestException as exc:
                errors.append(exc)
        if errors:
            raise errors[-1]
        raise requests.exceptions.RequestException('Ollama endpoint unavailable')

    def call_local_model(self, user_input, history=None, current_score=0, user_alias='Patient', session_verified=False, sender_number=None):
        history_text = self._truncate_text(
            self._recent_history_text(history),
            self.local_model_history_chars,
        )
        compact_user_input = self._truncate_text(user_input, self.local_model_input_chars)
        vault_snapshot = self._load_vault_snapshot()
        
        # Load actual vault context text
        indexer = self._get_indexer()
        vault_context = "No direct context available."
        if indexer:
            search_query = f"{user_alias} {sender_number or ''} {compact_user_input}".strip()
            results = indexer.search(text_query=search_query, limit=5)
            if results:
                chunks = []
                for i, r in enumerate(results):
                    snippet = r.get("summary") or r.get("text_preview") or ""
                    chunks.append(f"[{i+1}] type={r.get('file_type', 'unknown')} date={r.get('study_date_display', 'unknown')}: {snippet[:400]}")
                vault_context = "\n".join(chunks)

        prompt = (
            f"{self.system_prompt}\n\n"
            f"Patient alias: {user_alias}\n"
            f"Patient number: {sender_number or 'Unknown'}\n"
            f"Continuity score: {current_score}/100\n"
            f"Validation status: {'verified' if session_verified else 'unverified'}\n\n"
            f"Retrieved Indexed Patient Context:\n{vault_context}\n\n"
            f"Recent history:\n{history_text}\n\n"
            f"Patient request:\n{compact_user_input}\n\n"
            "Respond with practical care continuity guidance only. Use the retrieved context above if helpful.\n"
        )
        payload = {
            'model': self.local_model,
            'prompt': prompt,
            'stream': False,
            'keep_alive': '30m',
            'options': {'temperature': 0.35, 'num_predict': self.local_model_num_predict},
        }
        try:
            print('[SDOH] Trying local Gemma model...')
            try:
                response = self._ollama_generate(payload, timeout_sec=self.local_model_timeout_sec)
            except requests.exceptions.ReadTimeout:
                # Retry with a compact prompt to avoid hanging long continuity threads.
                print('[SDOH] Local model timed out; retrying with compact prompt...')
                compact_prompt = (
                    f"Patient alias: {user_alias}\n"
                    f"Validation status: {'verified' if session_verified else 'unverified'}\n"
                    f"Retrieved Indexed Patient Context:\n{vault_context}\n\n"
                    f"Request: {compact_user_input}\n"
                    'Return a concise continuity-focused response in 3 bullet points. Use context if helpful.'
                )
                compact_payload = {
                    'model': self.local_model,
                    'prompt': compact_prompt,
                    'stream': False,
                    'keep_alive': '30m',
                    'options': {
                        'temperature': 0.3,
                        'num_predict': max(64, min(120, self.local_model_num_predict)),
                    },
                }
                response = self._ollama_generate(
                    compact_payload,
                    timeout_sec=max(45, int(self.local_model_timeout_sec * 0.7)),
                )

            if response.status_code == 200:
                text = (response.json().get('response') or '').strip()
                if text:
                    severity = self._severity_from_text(user_input)
                    barrier_type = self._classify_barrier(user_input)
                    return {
                        'response': text,
                        'score_adjustment': 0, 'is_ready': False, 'phase': 'local',
                        'new_insight': 'Local inference can keep sensitive continuity guidance on-device.',
                        'insight_type': 'strength', 'confidence': 'medium',
                        'verification_required': False, 'timeline_items': [],
                        'draft_message': None, 'barrier_type': barrier_type,
                        'barrier_classification': barrier_type, 'source_paragraph': None,
                        'extracted_task': None, 'anatomy': None, 'modality': None,
                        'timeline': None, 'severity': severity,
                        'continuity_priority': self._priority_from_severity(severity),
                        'clinician_summary': self._clinician_continuity_summary(None, 'local model response', barrier_type, severity),
                        'missed_window_reclamation': False,
                        'patient_validation_required': False,
                        'patient_validation_verified': bool(session_verified),
                        'outbound_ready': False,
                    }
            else:
                print(f'[SDOH] Local model HTTP {response.status_code}: {response.text[:240]}')
        except Exception as exc:
            print(f'[SDOH] Local model unavailable: {exc}')
        return None

    def call_gemini_fallback(self, user_input, history=None, current_score=0, user_alias='Patient', session_verified=False):
        api_key = self.default_api_key
        if not api_key:
            return None

        history_text = self._recent_history_text(history)
        vault_snapshot = self._load_vault_snapshot()
        prompt = (
            "You are the SDOH Continuity Agent.\n"
            "Do not claim to have sent anything.\n"
            "Do not release reports, DICOM images, accounts, or statements unless the user explicitly "
            "confirms the correct patient and destination.\n"
            "Keep the response practical and concise.\n\n"
            f"Patient alias: {user_alias}\n"
            f"Validation status: {'verified' if session_verified else 'unverified'}\n"
            f"Continuity score: {current_score}/100\n\n"
            f"Local vault snapshot:\n{self._vault_snapshot_for_prompt(vault_snapshot)}\n\n"
            f"Recent history:\n{history_text}\n\n"
            f"User request:\n{user_input}\n"
        )
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.gemini_model}:generateContent?key={api_key}"
        )
        payload = {
            'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
            'systemInstruction': {
                'parts': [{
                    'text': (
                        'You are a patient-safe SDOH continuity assistant. '
                        'Never invent patient identity and never claim to have sent sensitive records.'
                    ),
                }],
            },
            'generationConfig': {'temperature': 0.35, 'maxOutputTokens': 240},
        }
        try:
            response = requests.post(url, json=payload, timeout=90)
            if response.status_code != 200:
                print(f'[SDOH] Gemini fallback error: {response.status_code} - {response.text}')
                return None
            data = response.json()
            text = (
                data.get('candidates', [{}])[0]
                .get('content', {})
                .get('parts', [{}])[0]
                .get('text', '')
            )
            text = (text or '').strip()
            if not text:
                return None
            severity = self._severity_from_text(user_input)
            barrier_type = self._classify_barrier(user_input)
            return {
                'response': text,
                'score_adjustment': 0, 'is_ready': False, 'phase': 'gemini-fallback',
                'new_insight': 'Fallback inference keeps continuity guidance available when local hardware is offline.',
                'insight_type': 'strength', 'confidence': 'medium',
                'verification_required': False, 'timeline_items': [],
                'draft_message': None, 'barrier_type': barrier_type,
                'barrier_classification': barrier_type, 'source_paragraph': None,
                'extracted_task': None, 'anatomy': None, 'modality': None,
                'timeline': None, 'severity': severity,
                'continuity_priority': self._priority_from_severity(severity),
                'clinician_summary': self._clinician_continuity_summary(None, 'gemini fallback response', barrier_type, severity),
                'missed_window_reclamation': False,
                'patient_validation_required': False,
                'patient_validation_verified': bool(session_verified),
                'outbound_ready': False,
            }
        except Exception as exc:
            print(f'[SDOH] Gemini fallback unavailable: {exc}')
            return None

    def _extract_candidate_path_from_history(self, history):
        if not history:
            return None
        for msg in reversed(history):
            if not isinstance(msg, dict):
                continue
            content = msg.get('content', '')
            if not isinstance(content, str):
                continue
            path = self._extract_candidate_path(content)
            if path:
                return path
        return None

    def chat(self, user_input, history=None, current_score=0, user_alias='Patient',
             session_verified=False, user_id=None, user_role=None, sender_number=None):
        topic = self._topic(user_input)

        if topic == 'general':
            user_input_lower = (user_input or '').strip().lower()
            if any(term in user_input_lower for term in ['run now', 'yes', 'do it', 'execute now', 'scan now', 'index now', 'do it now', 'execute', 'start now', 'run']):
                if history:
                    # If the user confirms a previous suggestion, reuse the last detected source path.
                    path_from_history = self._extract_candidate_path_from_history(history)
                    if path_from_history and not self._extract_candidate_path(user_input):
                        user_input = f"{user_input} {path_from_history}"
                for msg in reversed(history[:-1]):
                    if msg.get('role') in ('assistant', 'model'):
                        content = msg.get('content', '').lower()
                        if 'metadata scope:' in content or 'i can run a metadata scan now' in content or 'metadata scan' in content:
                            topic = 'metadata_preview'
                            match = re.search(r'metadata scope:\s*([^\s\n]+)', msg.get('content', ''), re.IGNORECASE)
                            if match:
                                user_input = user_input + ' drive ' + match.group(1)
                        elif 'whatsapp chat' in content or 'export' in content:
                            topic = 'whatsapp_chat_indexing'
                        elif 'index' in content or 'pull' in content:
                            topic = 'index_records'
                        break


        if self._is_admin_operator(user_alias=user_alias, user_id=user_id,
                                   user_role=user_role, sender_number=sender_number):
            # Let admin trigger normal continuity routing if they specifically aren't trying to onboard a VM/PACS
            if topic in {'show_documents', 'index_records', 'history_pack', 'metadata_preview', 'whatsapp_chat_indexing'}:
                pass # Fall through to explicit routes below
            elif not any(t in (user_input or '').lower() for t in ['database', 'vm', 'mount', 'siim', 'ingest']):
                pass # Don't trap admin if they want to ask normal SDOH questions
            else:
                return self._build_admin_response(user_input, user_alias=user_alias or 'Admin')

        # Patient-owned health record routes (highest priority after admin)
        if topic == 'show_documents':
            return self._finalize_structured_response(
                self._build_show_documents_response(user_input, user_alias=user_alias),
                user_input=user_input, user_alias=user_alias, session_verified=session_verified,
            )
        if topic == 'index_records':
            return self._finalize_structured_response(
                self._build_index_guidance(user_input, user_alias=user_alias),
                user_input=user_input, user_alias=user_alias, session_verified=session_verified,
            )
        if topic == 'history_pack':
            return self._finalize_structured_response(
                self._build_history_pack_response(user_input, user_alias=user_alias),
                user_input=user_input, user_alias=user_alias, session_verified=session_verified,
            )
        if topic == 'metadata_preview':
            return self._finalize_structured_response(
                self._build_metadata_preview_response(user_input, user_alias=user_alias),
                user_input=user_input, user_alias=user_alias, session_verified=session_verified,
            )
        if topic == 'whatsapp_chat_indexing':
            return self._finalize_structured_response(
                self._build_whatsapp_chat_indexing_response(user_input, user_alias=user_alias),
                user_input=user_input, user_alias=user_alias, session_verified=session_verified,
            )
        if topic == 'siim_patients':
            return self._finalize_structured_response(
                self._build_siim_patients_response(user_input, user_alias=user_alias),
                user_input=user_input, user_alias=user_alias, session_verified=session_verified,
            )
        if topic == 'siim_ingest':
            return self._finalize_structured_response(
                self._build_siim_ingest_response(user_input, user_alias=user_alias),
                user_input=user_input, user_alias=user_alias, session_verified=session_verified,
            )
        if topic == 'siim_patient_detail':
            return self._finalize_structured_response(
                self._build_patient_document_guidance(user_input, user_alias=user_alias),
                user_input=user_input, user_alias=user_alias, session_verified=session_verified,
            )

        if topic in {'orientation', 'document'}:
            if topic == 'document' and not self._looks_like_pasted_document(user_input):
                guided = self._build_patient_document_guidance(user_input, user_alias=user_alias)
                return self._finalize_structured_response(
                    guided, user_input=user_input, user_alias=user_alias, session_verified=session_verified,
                )
            extraction = self._build_extraction_result(user_input, user_alias=user_alias)
            if topic == 'document' and extraction:
                return self._finalize_structured_response(
                    extraction, user_input=user_input, user_alias=user_alias, session_verified=session_verified,
                )

        routed = self._build_response(user_input, user_alias=user_alias, session_verified=session_verified)

        # Deterministic routing wins for non-general phases
        if routed.get('phase') != 'general':
            return self._finalize_structured_response(
                routed, user_input=user_input, user_alias=user_alias, session_verified=session_verified,
            )

        # Ensure Gemma (local privacy) is the primary model as requested.
        local = self.call_local_model(user_input, history, current_score, user_alias, session_verified=session_verified, sender_number=sender_number)
        if local:
            local.setdefault('route', routed.get('route', 'recovery_tracker'))
            return self._finalize_structured_response(
                local, user_input=user_input, user_alias=user_alias, session_verified=session_verified,
            )

        # Gemini fallback has been intentionally disabled per user request ("run by Gemma not gemini").
        print("[SDOH] Gemma failed and Gemini fallback is disabled.")
        return self._finalize_structured_response(
            {"reply": "I'm currently experiencing a connection issue with my local privacy systems. Please try again in an hour.", "route": routed.get('route', 'recovery_tracker')},
            user_input=user_input, user_alias=user_alias, session_verified=session_verified,
        )

        return self._finalize_structured_response(
            routed, user_input=user_input, user_alias=user_alias, session_verified=session_verified,
        )

    def greeting(self, user_alias='Patient', user_id=None, user_role=None):
        is_admin = self._is_admin_operator(user_alias=user_alias, user_id=user_id, user_role=user_role)
        vault_snapshot = self._load_vault_snapshot()

        if is_admin:
            return (
                f"Hello {user_alias}. I can help connect local apps, VMs, databases, DICOM sources, "
                "and billing or report indexes in read-only mode. "
                "Tell me what you want connected first, which VM or host it lives on, what database engine "
                "or file share it uses, what read-only access you can provide, and which patient identifier "
                "should be used so invoices and reports land on the right account. "
                f"For OpenClaw WhatsApp staging, the operator target is {self.whatsapp_number}. "
                f"Vault index path: {vault_snapshot.get('index_path')}. "
                "If you want, start with one source and I will turn it into a safe connection checklist."
            )

        indexer = self._get_indexer()
        index_stats = indexer.get_stats() if indexer else {}
        total_indexed = index_stats.get('total', 0)

        if total_indexed > 0:
            by_mod = index_stats.get('by_modality', {})
            record_summary = f"Your personal health record has {total_indexed} document(s) indexed."
            if by_mod:
                record_summary += ' Imaging studies: ' + ', '.join(f"{k} ({v})" for k, v in by_mod.items()) + '.'
            record_hint = (
                f" {record_summary} "
                "Type 'what documents do I have' to see your full index, or tell me about your next visit "
                "and I will find the most relevant documents for you to bring."
            )
        else:
            record_hint = (
                " You can build a personal health record right here — copy your DICOM files, reports, "
                "referrals, and medication scripts into a folder called 'medical_records' on your Desktop, "
                "then type 'index my records' and I will scan them for you. "
                "Everything stays on your own device."
            )

        vault_hint = (
            f" Vault: {vault_snapshot.get('total_records', 0)} indexed record(s), "
            f"identity keys {'configured' if vault_snapshot.get('identity_keys_present') else 'not configured'}"
            "."
        )

        return (
            f"Hello {user_alias}. I am your personal health navigator.\n\n"
            "I help you truly own your medical history — your DICOM images, reports, referrals, "
            "and medication scripts belong to you, and I keep them on your device.\n\n"
            "What I can do for you:\n"
            "  1. Index your local medical documents so you always know what you have.\n"
            "  2. When you have an upcoming scan or specialist visit, find the most relevant records to bring.\n"
            "  3. Translate clinical reports into plain language you can understand.\n"
            "  4. Build a doctor-ready history pack — you control exactly what gets shared.\n"
            "  5. Set up reminders, help with transport, and draft messages to family or carers.\n\n"
            + record_hint
            + vault_hint
        )