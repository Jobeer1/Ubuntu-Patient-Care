"""SDOH Patient Service, Validation, Billing, and Routing
==========================================================
Mixin providing patient validation, billing extraction, service guards,
and the main deterministic routing logic for SDOHContinuityAgent.

Safety principle: no report, image, statement, or invoice leaves the system
unless the correct patient identity has been confirmed and the destination
explicitly approved.
"""
from __future__ import annotations

import re


class SDOHServiceMixin:

    # ------------------------------------------------------------------
    # Patient-service request profile
    # ------------------------------------------------------------------

    def _patient_request_profile(self, user_input):
        text_lower = (user_input or '').lower()
        profiles = [
            ('dicom', ['dicom', 'x-ray', 'xray', 'image', 'images', 'study', 'scan', 'radiology'], [
                'patient name or alias', 'date of birth or hospital number',
                'study date or accession number', 'destination approval',
            ]),
            ('report', ['report', 'reports', 'results', 'radiology report', 'lab report'], [
                'patient name or alias', 'date of birth or hospital number',
                'report date or report number', 'destination approval',
            ]),
            ('invoice', ['invoice', 'invoices'], [
                'patient name or alias', 'account number', 'invoice number',
                'amount if you want payment matching',
            ]),
            ('statement', ['statement', 'statements', 'billing statement', 'account statement'], [
                'patient name or alias', 'account number', 'statement date or period',
                'destination approval',
            ]),
            ('payment', ['payment', 'payments', 'pay invoice', 'settle account', 'allocate payment', 'receipt'], [
                'patient name or alias', 'account number', 'invoice number',
                'payment amount', 'payment reference if available',
            ]),
        ]
        for request_type, terms, required_fields in profiles:
            if any(term in text_lower for term in terms):
                return {
                    'request_type': request_type,
                    'required_fields': required_fields,
                    'match_order': 'national ID -> issuer patient ID / account number -> exact name + DOB -> phonetic fallback',
                }
        return {
            'request_type': 'general',
            'required_fields': [
                'patient name or alias', 'what you want sent or explained',
                'destination approval if anything will leave the system',
            ],
            'match_order': 'national ID -> issuer patient ID / account number -> exact name + DOB -> phonetic fallback',
        }

# ------------------------------------------------------------------
    # Billing field extraction
    # ------------------------------------------------------------------

    def _extract_billing_fields(self, user_input):
        text = user_input or ''

        def _find(patterns):
            import re  # 🧠 Force local scope to use the standard regex library module
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if value:
                        return value
            return None

        account_number = _find([
            r'(?:account|acct)\s*(?:number|no\.?|#)?\s*[:\-]?\s*([A-Za-z0-9\-]{4,})',
            r'\baccount\s+([A-Za-z0-9\-]{4,})\b',
        ])
        invoice_number = _find([
            r'(?:invoice|inv)\s*(?:number|no\.?|#)?\s*[:\-]?\s*([A-Za-z0-9\-]{4,})',
            r'\binvoice\s+([A-Za-z0-9\-]{4,})\b',
        ])
        payment_reference = _find([
            r'(?:reference|ref|payment\s+reference)\s*(?:number|no\.?|#)?\s*[:\-]?\s*([A-Za-z0-9\-]{4,})',
            r'\bref(?:erence)?\s+([A-Za-z0-9\-]{4,})\b',
        ])
        amount = _find([
            r'(?:amount|pay|payment|settle)\s*(?:of|for|:)?\s*(?:r|zar|\$)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)',
            r'(?:r|zar|\$)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)',
        ])

        if not payment_reference:
            if account_number and invoice_number:
                payment_reference = f'{account_number}/{invoice_number}'
            else:
                payment_reference = account_number or invoice_number

        return {
            'account_number': account_number,
            'invoice_number': invoice_number,
            'payment_reference': payment_reference,
            'amount': amount,
            'currency': 'ZAR',
        }

    def _contains_any(self, text, terms):
        """Check if any of the terms are present in the text (case-insensitive)."""
        if not text:
            return False
        text_lower = text.lower()
        return any(term.lower() in text_lower for term in terms)

    # ------------------------------------------------------------------
    # Patient validation gate
    # ------------------------------------------------------------------

    def _patient_validation_status(self, user_input, user_alias='Patient', session_verified=False):
        request_profile = self._patient_request_profile(user_input)
        validation_request = self._contains_any(user_input, [
            'patient validation', 'validate patient', 'verify patient',
            'confirm patient', 'confirm identity', 'wrong patient',
        ])
        sensitive_request = self._contains_any(user_input, [
            'report', 'reports', 'dicom', 'image', 'images', 'statement', 'statements',
            'account', 'accounts', 'invoice', 'invoices', 'payment', 'payments',
            'receipt', 'settle account',
        ])
        outbound_request = self._contains_any(user_input, [
            'send', 'share', 'forward', 'release', 'deliver', 'whatsapp', 'email', 'text',
        ])

        if validation_request:
            return {
                'required': True, 'verified': False,
                'reason': f"Confirm the patient alias or code before I release any {request_profile['request_type']}.",
                'mode': 'validation',
                'request_type': request_profile['request_type'],
                'required_fields': request_profile['required_fields'],
                'match_order': request_profile['match_order'],
            }

        if sensitive_request and outbound_request:
            text_lower = (user_input or '').lower()
            alias_present = bool(user_alias and user_alias.strip() and user_alias.strip().lower() in text_lower)
            explicit_self = any(t in text_lower for t in ['my ', 'mine', 'for me', 'this is me', 'i confirm', 'confirm this is me'])
            verified = bool(session_verified and (alias_present or explicit_self))
            return {
                'required': True, 'verified': verified,
                'reason': None if verified else (
                    f"I need to confirm the right patient before any outbound {request_profile['request_type']} handoff. "
                    "Please include the patient alias or code, the needed identifiers, and approve the destination."
                ),
                'mode': 'handoff',
                'request_type': request_profile['request_type'],
                'required_fields': request_profile['required_fields'],
                'match_order': request_profile['match_order'],
            }

        return {
            'required': False, 'verified': bool(session_verified), 'reason': None,
            'mode': 'review',
            'request_type': request_profile['request_type'],
            'required_fields': request_profile['required_fields'],
            'match_order': request_profile['match_order'],
        }

    def _finalize_structured_response(self, response, user_input=None, user_alias='Patient', session_verified=False):
        if not isinstance(response, dict):
            return response
        validation = self._patient_validation_status(user_input, user_alias=user_alias, session_verified=session_verified)
        response.setdefault('patient_validation_required', validation['required'])
        response.setdefault('patient_validation_verified', validation['verified'])
        response.setdefault('validation_mode', validation['mode'])
        response.setdefault('outbound_ready', False)
        response.setdefault('whatsapp_number', self.whatsapp_number)
        if hasattr(self, '_load_vault_snapshot'):
            response.setdefault('vault_state', self._load_vault_snapshot())
        if validation['required'] and not validation['verified']:
            response['verification_required'] = True
        return response

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Real patient data lookup (PACS registry)
    # ------------------------------------------------------------------

    def _build_patient_id_lookup_response(self, user_input, user_alias='Patient'):
        """Query the local PACS registry for the patient identified in user_input."""
        try:
            from backend.patient_data_tools import get_tools, _extract_sa_national_id
        except ImportError:
            return None  # Fall through to generic routing if tools not available

        tools = get_tools()
        national_id = _extract_sa_national_id(user_input or '')
        patient = tools.lookup_patient(user_input)
        text_lower = (user_input or '').lower()

        wants_images = any(t in text_lower for t in [
            'dicom', 'x-ray', 'xray', 'ct', 'mri', 'scan', 'image', 'images', 'study', 'studies',
        ])
        wants_statement = any(t in text_lower for t in [
            'statement', 'account', 'invoice', 'billing', 'bill', 'payment',
        ])
        wants_appointment = any(t in text_lower for t in [
            'appointment', 'appointments', 'booking', 'schedule',
        ])

        if patient is None:
            # Honest not-found response
            search_id = national_id or user_input[:40]
            response_text = (
                f"I searched our local PACS registry for ID **{search_id}** but found no matching records.\n\n"
                "This could mean:\n"
                "• The patient has not been registered in our local registry yet.\n"
                "• The ID was entered incorrectly — please double-check all 13 digits.\n"
                "• Records may be stored under a different identifier.\n\n"
                "Please contact the practice to verify the account, or ask the administrator to register the patient in the system."
            )
            return {
                'response': response_text,
                'score_adjustment': 0, 'is_ready': False, 'phase': 'records',
                'route': 'patient_id_lookup_not_found',
                'new_insight': 'Patient not found in local registry — direct contact with practice required.',
                'insight_type': 'barrier', 'confidence': 'high',
                'verification_required': False, 'timeline_items': [],
                'draft_message': None, 'barrier_type': 'identity_not_found',
                'barrier_classification': 'identity_not_found',
                'severity': 'low', 'continuity_priority': 'low',
                'clinician_summary': self._clinician_continuity_summary(None, 'patient not found', 'identity_not_found', 'low'),
                'missed_window_reclamation': False, 'source_paragraph': None,
                'extracted_task': None, 'anatomy': None, 'modality': None,
                'timeline': None, 'export_bundle': None,
                'patient_validation_required': False, 'patient_validation_verified': False,
                'outbound_ready': False,
                'patient_found': False,
                'search_id': search_id,
            }

        # Patient found
        patient_summary = tools.format_patient_summary(patient)
        empi_id = patient.get('empi_id', '')
        response_lines = [f"I found your record: **{patient_summary}**\n"]

        if wants_images or (not wants_statement and not wants_appointment):
            studies = tools.get_studies_for_patient(empi_id)
            studies_text = tools.format_studies_list(studies)
            response_lines.append("**Imaging studies on file:**")
            response_lines.append(studies_text)

            if studies:
                accessible = [s for s in studies if tools.check_drive_accessible(s.get('source_location', ''))]
                if accessible:
                    response_lines.append(
                        "\n✓ At least one study is on an accessible drive. "
                        "Type \"send me study 1\" to prepare it for delivery."
                    )
                else:
                    response_lines.append(
                        "\n⚠ The imaging archive drives (Y:\\, Z:\\) are currently offline or not mapped. "
                        "Please ensure the NAS drives are connected, then try again."
                    )
            response_lines.append("")

        if wants_statement:
            stmt = tools.get_account_statement(patient)
            response_lines.append("**Account statement:**")
            response_lines.append(stmt['message'])
            response_lines.append("")

        if wants_appointment:
            appt = tools.get_appointments(patient)
            response_lines.append("**Appointments:**")
            response_lines.append(appt['message'])
            response_lines.append("")

        return {
            'response': '\n'.join(response_lines).strip(),
            'score_adjustment': 0, 'is_ready': False, 'phase': 'records',
            'route': 'patient_id_lookup',
            'new_insight': f'Patient registry lookup completed for {patient_summary}.',
            'insight_type': 'strength', 'confidence': 'high',
            'verification_required': False, 'timeline_items': [],
            'draft_message': None, 'barrier_type': None, 'barrier_classification': None,
            'severity': 'low', 'continuity_priority': 'low',
            'clinician_summary': self._clinician_continuity_summary(None, 'patient registry lookup', None, 'low'),
            'missed_window_reclamation': False, 'source_paragraph': None,
            'extracted_task': None, 'anatomy': None, 'modality': None,
            'timeline': None, 'export_bundle': None,
            'patient_validation_required': False, 'patient_validation_verified': True,
            'outbound_ready': False,
            'patient_found': True,
            'patient_empi_id': empi_id,
        }

    # Main deterministic routing
    # ------------------------------------------------------------------

    def _build_response(self, user_input, user_alias='Patient', session_verified=False):
        """Route to the right sub-handler based on detected topic."""
        if self._is_urgent(user_input):
            return {
                'response': (
                    "This sounds urgent. Please contact your care team or emergency services right now. "
                    "If you want, I can help you draft a message after you are safe."
                ),
                'score_adjustment': 0, 'is_ready': False, 'phase': 'safety', 'route': 'safety',
                'new_insight': 'Urgent symptoms require immediate clinical escalation, not passive monitoring.',
                'insight_type': 'strength', 'confidence': 'high',
                'verification_required': True, 'timeline_items': [], 'draft_message': None,
                'barrier_type': None, 'barrier_classification': None,
                'severity': 'critical', 'continuity_priority': 'critical',
                'clinician_summary': self._clinician_continuity_summary(None, None, None, 'critical'),
                'missed_window_reclamation': False, 'source_paragraph': None,
                'extracted_task': None, 'anatomy': None, 'modality': None,
                'timeline': None, 'export_bundle': None,
            }

        validation = self._patient_validation_status(user_input, user_alias=user_alias, session_verified=session_verified)

        if self._topic(user_input) == 'patient_id_lookup':
            result = self._build_patient_id_lookup_response(user_input, user_alias=user_alias)
            if result is not None:
                return result
            # Fall through if tools unavailable

        if self._topic(user_input) == 'validation':
            return {
                'response': (
                    'I can validate the patient context before any release, but I need the patient alias or code '
                    'and the exact item you want checked. I will only stage a draft until the identity is confirmed.'
                ),
                'score_adjustment': 0, 'is_ready': False, 'phase': 'validation',
                'route': 'patient_validation',
                'new_insight': 'The safest handoff starts with the right identity match.',
                'insight_type': 'strength', 'confidence': 'high',
                'verification_required': True, 'timeline_items': [], 'draft_message': None,
                'barrier_type': None, 'barrier_classification': None,
                'severity': 'low', 'continuity_priority': 'low',
                'clinician_summary': self._clinician_continuity_summary(None, 'patient validation', None, 'low'),
                'missed_window_reclamation': False, 'source_paragraph': None,
                'extracted_task': None, 'anatomy': None, 'modality': None,
                'timeline': None, 'export_bundle': None,
                'patient_validation_required': True, 'patient_validation_verified': False,
                'outbound_ready': False,
            }

        if self._topic(user_input) == 'practice_onboarding':
            return {
                'response': (
                    'Yes. I can support practice-side onboarding in a patient-safe, local-first way. '
                    'I will keep ingestion read-only first, validate patient matching keys, and only then allow records into the local vault or authorized network shares (like X: drive) (including network databases like the X: drive).\n\n'
                    'Start with one source:\n'
                    '1. Source type: app, VM, database, PACS export, or file share.\n'
                    '2. Host and engine: IP/hostname plus DB type or share path.\n'
                    '3. Read-only method: credentials, mounted path, or export drop-folder.\n'
                    '4. Matching keys: patient hash/ID fields used to prevent wrong-patient ingestion.\n'
                    '5. Data scope: DICOM, report text, scripts, statements, or invoices.\n\n'
                    'Once you provide those details, I will turn it into a strict validation and indexing checklist.'
                ),
                'score_adjustment': 0, 'is_ready': False, 'phase': 'onboarding',
                'route': 'practice_onboarding',
                'new_insight': 'Practice integrations should begin read-only with explicit patient-match keys before local indexing.',
                'insight_type': 'strength', 'confidence': 'high',
                'verification_required': True, 'timeline_items': [],
                'draft_message': 'Share one source now: type, host/path, read-only method, and patient matching fields.',
                'barrier_type': None, 'barrier_classification': None,
                'severity': 'low', 'continuity_priority': 'low',
                'clinician_summary': self._clinician_continuity_summary(None, 'practice onboarding request', None, 'low'),
                'missed_window_reclamation': False,
                'source_paragraph': None, 'extracted_task': 'prepare onboarding checklist for local app/database source',
                'anatomy': None, 'modality': None, 'timeline': None,
                'export_bundle': None,
                'patient_validation_required': True,
                'patient_validation_verified': bool(session_verified),
                'outbound_ready': False,
                'tool_calls': [
                    {
                        'name': 'sdoh.index_documents',
                        'status': 'suggested',
                        'args': {'folder': '<practice-share-or-drive>'},
                    },
                    {
                        'name': 'sdoh.my_documents',
                        'status': 'suggested',
                        'args': {'modality': '<optional>', 'body_part': '<optional>', 'q': '<optional>'},
                    },
                ],
            }

        if self._topic(user_input) == 'practice_indexing':
            text = user_input or ''
            drive_match = re.search(r'\b([A-Za-z])\s*drive\b', text, re.IGNORECASE)
            path_match = re.search(r'\b([A-Za-z]:\\[^\n\r]*)', text)
            drive_path = None
            if path_match:
                drive_path = path_match.group(1).strip()
            elif drive_match:
                drive_path = f"{drive_match.group(1).upper()}:\\"

            path_text = drive_path or 'the requested mapped drive'
            return {
                'response': (
                    f"Yes. I can stage a read-only index pass on {path_text}, but I will not auto-share records across patients. "
                    "I first isolate incoming files, extract metadata, and enforce patient-match keys before anything is mapped for handoff.\n\n"
                    "Safe indexing workflow:\n"
                    "1. Confirm the exact drive path and read-only access method.\n"
                    "2. Run a metadata-only scan (PatientID, StudyDate, Modality, BodyPart).\n"
                    "3. Validate matching keys against your local identity rules.\n"
                    "4. Produce a review list of candidate records per patient.\n"
                    "5. Only after approval, prepare targeted patient bundles.\n\n"
                    "Send the drive path, matching fields, and preferred output location, then I will generate the strict indexing checklist."
                ),
                'score_adjustment': 0, 'is_ready': False, 'phase': 'onboarding',
                'route': 'practice_indexing',
                'new_insight': 'Drive-wide DICOM indexing must remain read-only and identity-validated before any patient handoff mapping.',
                'insight_type': 'strength', 'confidence': 'high',
                'verification_required': True, 'timeline_items': [],
                'draft_message': 'Provide drive path, read-only method, patient matching keys, and export destination for a safe indexing runbook.',
                'barrier_type': None, 'barrier_classification': None,
                'severity': 'high', 'continuity_priority': 'high',
                'clinician_summary': self._clinician_continuity_summary(None, 'practice drive indexing request', None, 'high'),
                'missed_window_reclamation': False,
                'source_paragraph': None, 'extracted_task': 'prepare safe drive-level indexing and patient matching checklist',
                'anatomy': None, 'modality': 'dicom', 'timeline': None,
                'export_bundle': None,
                'patient_validation_required': True,
                'patient_validation_verified': bool(session_verified),
                'outbound_ready': False,
                'requested_source_path': drive_path,
                'tool_calls': [
                    {
                        'name': 'sdoh.index_documents',
                        'status': 'suggested',
                        'args': {'folder': drive_path or '<mapped-drive>'},
                    },
                    {
                        'name': 'sdoh.my_documents',
                        'status': 'suggested',
                        'args': {'modality': 'CT', 'body_part': '<optional>', 'q': 'follow-up'},
                    },
                ],
            }

        if self._topic(user_input) == 'metadata_preview' and hasattr(self, '_build_metadata_preview_response'):
            return self._build_metadata_preview_response(user_input, user_alias=user_alias)

        if self._topic(user_input) == 'whatsapp_chat_indexing' and hasattr(self, '_build_whatsapp_chat_indexing_response'):
            return self._build_whatsapp_chat_indexing_response(user_input, user_alias=user_alias)

        if self._topic(user_input) == 'vault_ingest':
            vault_state = self._load_vault_snapshot() if hasattr(self, '_load_vault_snapshot') else {}
            identity_ready = bool(vault_state.get('identity_keys_present'))
            index_ready = bool(vault_state.get('index_present'))
            verification_ready = bool(session_verified and identity_ready)
            blocked_reason = (
                'I found no local validation keys yet.'
                if not identity_ready else
                'The session is not verified yet for inbound clinical ingestion.'
            )
            guidance = [
                'I can stage incoming practice payloads in the local vault or authorized network shares (like X: drive) (including network databases like the X: drive) inbox and block ingestion until identity checks pass.',
                'Required fields: sender_verification_token, target_patient_hash, payload_type, and clinical_data.',
                'Safety rule: if the patient hash does not match local validation keys exactly, ingestion is blocked and the record stays isolated.',
            ]
            if not index_ready:
                guidance.append('I also need a local index file before approved records can be appended to the patient graph.')
            if not verification_ready:
                guidance.append(blocked_reason)

            return {
                'response': ' '.join(guidance),
                'score_adjustment': 0, 'is_ready': False, 'phase': 'ingest',
                'route': 'validation_gatekeeper',
                'new_insight': 'Inbound clinical documents must pass local identity matching before they join the patient timeline.',
                'insight_type': 'strength', 'confidence': 'high',
                'verification_required': not verification_ready,
                'timeline_items': [],
                'draft_message': 'Share sender token, patient hash, payload type, and destination vault folder for a dry-run verification check.',
                'barrier_type': None, 'barrier_classification': None,
                'severity': 'high' if not verification_ready else 'low',
                'continuity_priority': 'high' if not verification_ready else 'low',
                'clinician_summary': self._clinician_continuity_summary(None, 'inbound payload verification', None, 'high' if not verification_ready else 'low'),
                'missed_window_reclamation': False,
                'source_paragraph': None, 'extracted_task': 'verify inbound payload before local ingest',
                'anatomy': None, 'modality': None, 'timeline': None,
                'export_bundle': None,
                'patient_validation_required': True,
                'patient_validation_verified': verification_ready,
                'outbound_ready': False,
                'ingest_ready': verification_ready,
                'ingest_blocked_reason': None if verification_ready else blocked_reason,
                'required_fields': ['sender_verification_token', 'target_patient_hash', 'payload_type', 'clinical_data'],
            }

        if self._topic(user_input) == 'patient_service':
            request_profile = self._patient_request_profile(user_input)
            if validation['required'] and not validation['verified']:
                return {
                    'response': (
                        f"{validation['reason']} I will use the local deterministic patient registry so the wrong "
                        "report, invoice, or DICOM image does not go to the wrong person. "
                        f"I need: {', '.join(request_profile['required_fields'])}. Match order: {request_profile['match_order']}."
                    ),
                    'score_adjustment': 0, 'is_ready': False, 'phase': 'records',
                    'route': 'patient_service_guard',
                    'new_insight': 'Patient identity must be matched before a report, image, or statement leaves the system.',
                    'insight_type': 'strength', 'confidence': 'high',
                    'verification_required': True, 'timeline_items': [],
                    'draft_message': f"Please confirm the patient alias or code and the needed identifiers for this {request_profile['request_type']} before I stage the handoff.",
                    'barrier_type': None, 'barrier_classification': None,
                    'severity': 'low', 'continuity_priority': 'low',
                    'clinician_summary': self._clinician_continuity_summary(None, 'patient handoff blocked', None, 'low'),
                    'missed_window_reclamation': False, 'source_paragraph': None,
                    'extracted_task': None, 'anatomy': None, 'modality': None,
                    'timeline': None, 'export_bundle': None,
                    'patient_validation_required': True, 'patient_validation_verified': False,
                    'outbound_ready': False, 'request_type': request_profile['request_type'],
                    'required_fields': request_profile['required_fields'],
                    'match_order': request_profile['match_order'],
                    'whatsapp_number': self.whatsapp_number,
                }
            return {
                'response': (
                    f"The patient identity looks consistent for review. I can prepare a draft for the "
                    f"{request_profile['request_type']} and keep it draft-only until you approve the final destination."
                ),
                'score_adjustment': 0, 'is_ready': False, 'phase': 'records',
                'route': 'patient_service',
                'new_insight': 'Draft-only delivery prevents the wrong patient from receiving sensitive records.',
                'insight_type': 'strength', 'confidence': 'high',
                'verification_required': False, 'timeline_items': [],
                'draft_message': f"Please confirm the exact patient and approve the final release destination for this {request_profile['request_type']}.",
                'barrier_type': None, 'barrier_classification': None,
                'severity': 'low', 'continuity_priority': 'low',
                'clinician_summary': self._clinician_continuity_summary(None, 'patient handoff draft', None, 'low'),
                'missed_window_reclamation': False, 'source_paragraph': None,
                'extracted_task': None, 'anatomy': None, 'modality': None,
                'timeline': None, 'export_bundle': None,
                'patient_validation_required': True, 'patient_validation_verified': True,
                'outbound_ready': False, 'request_type': request_profile['request_type'],
                'required_fields': request_profile['required_fields'],
                'match_order': request_profile['match_order'],
                'whatsapp_number': self.whatsapp_number,
            }

        if self._topic(user_input) == 'payment':
            billing_fields = self._extract_billing_fields(user_input)
            request_profile = self._patient_request_profile(user_input)
            has_account = bool(billing_fields['account_number'])
            has_amount = bool(billing_fields['amount'])
            outbound_ready = bool(validation['verified'] and has_account and has_amount)

            if validation['required'] and not validation['verified']:
                return {
                    'response': validation['reason'],
                    'score_adjustment': 0, 'is_ready': False, 'phase': 'billing',
                    'route': 'payment_guard',
                    'new_insight': 'Payment allocation must be tied to the correct patient before any posting.',
                    'insight_type': 'strength', 'confidence': 'high',
                    'verification_required': True, 'timeline_items': [],
                    'draft_message': 'Please confirm the patient and account before I stage a payment allocation draft.',
                    'barrier_type': None, 'barrier_classification': None,
                    'severity': 'low', 'continuity_priority': 'low',
                    'clinician_summary': self._clinician_continuity_summary(None, 'payment allocation blocked', None, 'low'),
                    'missed_window_reclamation': False, 'source_paragraph': None,
                    'extracted_task': None, 'anatomy': None, 'modality': None,
                    'timeline': None, 'export_bundle': None,
                    'patient_validation_required': True, 'patient_validation_verified': False,
                    'outbound_ready': False, 'request_type': request_profile['request_type'],
                    'required_fields': request_profile['required_fields'],
                    'match_order': request_profile['match_order'],
                    'whatsapp_number': self.whatsapp_number,
                    'payment_allocation_draft': {
                        'status': 'blocked', 'patient_alias': user_alias,
                        **billing_fields,
                        'verification_required': True, 'verification_verified': False,
                    },
                }

            return {
                'response': (
                    'I can stage a local payment allocation draft. Send the patient alias, account number, '
                    'invoice number, and amount so I can match it to the correct account before posting.'
                    if not outbound_ready else
                    'The payment details look complete. I have prepared a local allocation draft for the correct '
                    'account and it is ready for review before posting.'
                ),
                'score_adjustment': 0, 'is_ready': False, 'phase': 'billing',
                'route': 'payment_allocation',
                'new_insight': 'Payment workflows should stay local, traceable, and tied to verified account references.',
                'insight_type': 'strength', 'confidence': 'high',
                'verification_required': not outbound_ready, 'timeline_items': [],
                'draft_message': (
                    'Please confirm the patient and account before posting the allocation.'
                    if not outbound_ready else
                    'Please review the payment allocation and confirm the target account.'
                ),
                'barrier_type': None, 'barrier_classification': None,
                'severity': 'low', 'continuity_priority': 'low',
                'clinician_summary': self._clinician_continuity_summary(None, 'payment allocation', None, 'low'),
                'missed_window_reclamation': False, 'source_paragraph': None,
                'extracted_task': None, 'anatomy': None, 'modality': None,
                'timeline': None, 'export_bundle': None,
                'patient_validation_required': True,
                'patient_validation_verified': bool(validation['verified']),
                'outbound_ready': outbound_ready,
                'request_type': request_profile['request_type'],
                'required_fields': request_profile['required_fields'],
                'match_order': request_profile['match_order'],
                'whatsapp_number': self.whatsapp_number,
                'payment_allocation_draft': {
                    'status': 'ready_for_allocation' if outbound_ready else 'draft',
                    'patient_alias': user_alias, **billing_fields,
                    'verification_required': not outbound_ready,
                    'verification_verified': bool(validation['verified']),
                },
            }

        topic = self._topic(user_input)
        barrier_type = self._classify_barrier(user_input)

        if topic == 'continuity':
            severity = self._severity_from_text(user_input)
            response = [
                'Here is the next-step plan:',
                '1. Confirm the appointment or follow-up date.',
                '2. Check whether transport, caregiver help, or prep is needed.',
                '3. If you want, I can draft a short message to family or a reminder list.',
            ]
            if barrier_type:
                response.append(f'Barrier detected: {barrier_type}.')
            draft_message = 'Could you help me with transport for my follow-up appointment? I want to make sure I get there on time.'
            timeline_items = [
                self._build_timeline_item('Confirm follow-up date', 'upcoming', severity, barrier_type),
                self._build_timeline_item('Check transport and caregiver support', 'upcoming', severity, barrier_type),
            ]
            reclamation = self._apply_missed_window_reclamation(user_input, timeline_items, severity)
            if reclamation['triggered']:
                response.append(reclamation['message'])
                timeline_items = reclamation['timeline_items']
            return {
                'response': '\n'.join(response),
                'score_adjustment': 0, 'is_ready': False, 'phase': 'continuity',
                'route': 'care_navigator',
                'new_insight': 'The main failure mode is usually coordination, not motivation.',
                'insight_type': 'strength',
                'confidence': 'medium' if barrier_type else 'high',
                'verification_required': False, 'timeline_items': timeline_items,
                'draft_message': draft_message, 'barrier_type': barrier_type,
                'barrier_classification': barrier_type, 'severity': severity,
                'continuity_priority': self._priority_from_severity(severity),
                'clinician_summary': self._clinician_continuity_summary(None, 'follow-up continuity', barrier_type, severity),
                'missed_window_reclamation': reclamation['triggered'],
                'source_paragraph': None, 'extracted_task': None,
                'anatomy': None, 'modality': None, 'timeline': None,
                'export_bundle': self._build_export_bundle(
                    user_alias=user_alias, source_paragraph=None,
                    extracted_task='follow-up continuity', timeline_items=timeline_items,
                    barrier_type=barrier_type, severity=severity,
                    continuity_priority=self._priority_from_severity(severity),
                    timeline=None, verification_required=False,
                    clinician_summary=self._clinician_continuity_summary(None, 'follow-up continuity', barrier_type, severity),
                ),
            }

        if topic == 'communication':
            draft_message = 'I need help with my recovery plan. Can you please help with transport, reminders, or checking in with me after my appointment?'
            return {
                'response': (
                    "I can help draft that message.\n"
                    f"Draft: {draft_message}\n\n"
                    "If you want, I can make it shorter, warmer, or more direct."
                ),
                'score_adjustment': 0, 'is_ready': False, 'phase': 'communication',
                'route': 'family_coordinator',
                'new_insight': 'Clear support requests reduce friction for both patients and caregivers.',
                'insight_type': 'strength', 'confidence': 'high',
                'verification_required': False, 'timeline_items': [],
                'draft_message': draft_message, 'barrier_type': barrier_type,
                'barrier_classification': barrier_type, 'severity': 'low',
                'continuity_priority': 'low',
                'clinician_summary': self._clinician_continuity_summary(None, 'support request', barrier_type, 'low'),
                'missed_window_reclamation': False, 'source_paragraph': None,
                'extracted_task': None, 'anatomy': None, 'modality': None,
                'timeline': None, 'export_bundle': None,
            }

        if topic == 'orientation':
            return {
                'response': (
                    'SDOH means Social Determinants of Health. It covers the practical things that can affect '
                    'recovery and follow-up, like transport, money, caregiver support, scheduling, and access '
                    'to devices or signal.\n\n'
                    'I can help you with:\n'
                    '1. reminder plans for appointments, labs, and medication\n'
                    '2. short messages to family, caregivers, or clinic staff\n'
                    '3. plain-language summaries of reports or discharge instructions\n'
                    '4. tracking blocked, missed, or completed follow-up items\n\n'
                    'If you want, tell me one thing you are trying to keep on track and I will turn it into next steps.'
                ),
                'score_adjustment': 0, 'is_ready': False, 'phase': 'orientation',
                'route': 'recovery_tracker',
                'new_insight': 'Orientation questions should answer the purpose of SDOH before asking for details.',
                'insight_type': 'strength', 'confidence': 'high',
                'verification_required': False, 'timeline_items': [], 'draft_message': None,
                'barrier_type': barrier_type, 'barrier_classification': barrier_type,
                'source_paragraph': None, 'extracted_task': None,
                'anatomy': None, 'modality': None, 'timeline': None,
                'severity': 'low', 'continuity_priority': 'low',
                'clinician_summary': self._clinician_continuity_summary(None, 'orientation', barrier_type, 'low'),
                'missed_window_reclamation': False, 'export_bundle': None,
            }

        if topic == 'document':
            extraction = self._build_extraction_result(user_input)
            if extraction:
                extraction['route'] = 'document_interpreter'
                return extraction
            return {
                'response': (
                    "I can help translate the document into care continuity steps. "
                    "If you paste the report text, I will pull out the follow-up action, the timeline, "
                    "and any support needs."
                ),
                'score_adjustment': 0, 'is_ready': False, 'phase': 'document',
                'route': 'document_interpreter',
                'new_insight': 'Clinical documents are most useful when they become concrete next steps.',
                'insight_type': 'strength', 'confidence': 'medium',
                'verification_required': True, 'timeline_items': [], 'draft_message': None,
                'barrier_type': barrier_type, 'barrier_classification': barrier_type,
                'source_paragraph': None, 'extracted_task': None,
                'anatomy': None, 'modality': None, 'timeline': None,
                'severity': 'low', 'continuity_priority': 'low',
                'clinician_summary': self._clinician_continuity_summary(None, 'document review', barrier_type, 'low'),
                'missed_window_reclamation': False, 'export_bundle': None,
            }

        return {
            'response': (
                "Tell me the next follow-up you are trying to protect, or the barrier making it hard. "
                "I can help with reminders, family messages, or a plain-language recovery summary."
            ),
            'score_adjustment': 0, 'is_ready': False, 'phase': 'general',
            'route': 'recovery_tracker',
            'new_insight': 'The best support starts with one concrete next step.',
            'insight_type': 'strength', 'confidence': 'high',
            'verification_required': False, 'timeline_items': [], 'draft_message': None,
            'barrier_type': barrier_type, 'barrier_classification': barrier_type,
            'source_paragraph': None, 'extracted_task': None,
            'anatomy': None, 'modality': None, 'timeline': None,
            'severity': 'low', 'continuity_priority': 'low',
            'clinician_summary': self._clinician_continuity_summary(None, 'general continuity', barrier_type, 'low'),
            'missed_window_reclamation': False, 'export_bundle': None,
        }
