import os
import configparser
import concurrent.futures
import ipaddress
import json
import logging
import os
import re
import socket
import subprocess
import shutil
from datetime import datetime

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

import requests

try:
    import scapy.all as scapy
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

from PIL import Image

from backend.pacs_exports import generate_pacs_export_artifact
from backend.pacs_registry import PACSContinuityRegistry


def _normalize_sa_whatsapp_number(value):
    if value is None:
        return ""
    digits = re.sub(r"\D", "", str(value))
    if not digits:
        return ""
    if digits.startswith("27") and len(digits) >= 11:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) >= 10:
        return f"+27{digits[1:]}"
    return f"+{digits}"


def _extract_whatsapp_sender_number(session_key):
    text = str(session_key or "")
    matches = re.findall(r"\+?\d{10,15}", text)
    if not matches:
        return ""
    return _normalize_sa_whatsapp_number(matches[-1])


PACS_MENTOR_OWNER_NUMBERS = {
    _normalize_sa_whatsapp_number("+27663764491"),
}

PACS_MENTOR_ADMIN_NUMBERS = {
    _normalize_sa_whatsapp_number("+27768193339"),
}

class PACSContinuityMentor:
    """
    Expert AI Agent for Radiology Infrastructure Recovery.
    Implements mandatory Optical Authorization through the Emergency Override Gate.
    """
    
    def __init__(self, workspace_path=None):
        self.workspace_path = workspace_path or os.getcwd()
        self.log_file = os.path.join(self.workspace_path, "INFRASTRUCTURE_RECOVERY_LOG.md")
        self.state_file = os.path.join(self.workspace_path, "pacs_mentor_state.json")
        self.persona_name = "PACS Continuity Mentor"
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(self.workspace_path, "config.ini"))
        self.gemini_api_key = self.config.get("GEMINI", "api_key", fallback=os.environ.get("GEMINI_API_KEY"))
        self.gemini_model = self.config.get("GEMINI", "model", fallback=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite"))
        
        # Incident State Machine
        self.valid_states = ["DETECTED", "TRIAGED", "HYPOTHESIS_FORMED", "VERIFIED", "MITIGATED", "RESOLVED", "ESCALATED"]
        self.current_state = "DETECTED"
        self.emergency_override = False
        self.action_log = []
        self.network_map = {}
        self.registry = PACSContinuityRegistry(workspace_path=self.workspace_path)
        self.general_skill_topics = [
            "DICOM routing and AE title checks",
            "Modality onboarding and worklist triage",
            "Archive, storage, and backup validation",
            "FHIR, DICOMweb, and NAS continuity registry indexing",
            "RIS, PACS, and medical billing source inventory",
            "Deterministic EMPI patient reconciliation",
            "Cross-modality study timeline stitching",
            "HL7 / MPPS interface troubleshooting",
            "Network discovery and vendor fingerprinting",
            "Incident logging and escalation handoff",
            "Network layouts and workflow documentation",
            "Subscription and renewal reminders for Microsoft, Veeam, and similar services",
            "Patient account statements, invoices, and visit-charge explanations",
            "Appointment and referral confirmation workflows",
            "DICOM image metadata previews and report interpretation",
            "OpenClaw skills for xurl, summarize, openai-whisper, and wacli",
        ]
        self.pacs_role_prompt = (
            "You are the PACS Continuity Mentor. You help clinicians, PACS admins, and patients inspect mounted NAS sources, "
            "explain Firebird and other clinical database shares, search the local continuity registry, and guide safe read-only recovery across RIS, PACS, and medical billing sources. "
            "Treat WhatsApp sender +27768193339 and the local admin user 0768193339 as the admin/operator identity; everyone else is a patient. "
            "For patients, help with invoices, account statements, reports, DICOM images, appointment confirmation, and referral questions using only local indexed records or uploaded files. "
            "You do not recommend destructive changes, hidden deletions, or unsafe access bypasses. "
            "If the user wants to explore deeper into network topology, VM inventory, server status, or other sensitive LAN details, first ask for explicit admin proof using the admin/operator identity or a known device login. "
            "Do not expose sensitive discovery results to an unverified user. "
            "When the user asks about SIIM hackathon workflows, API keys, FHIR, DICOMweb, metadata extraction, or matching DICOM files to FHIR worklists, "
            "answer with practical PACS-admin steps and example fields instead of asking them to name a skill. "
            "When the user asks what tools or capabilities you have, answer with the concrete read-only capabilities you already have instead of asking for clarification. "
            "Be concise, accurate, and context-aware."
        )
        self.pacs_admin_role_prompt = (
            "You are the PACS Continuity Mentor operating in ADMIN MODE for the authenticated operator at +27768193339 or the local admin user 0768193339. You have full access to all read-only diagnostics, patient-support workflows, and troubleshooting capabilities. "
            "You can perform the following tasks WITHOUT requiring further authorization: "
            "1) Subnet scanning and ICMP ping sweeps on any CIDR block the user specifies (e.g., 155.235.81/28). "
            "2) Individual host/IP status checks. "
            "3) Configured VM and LAN inventory status reporting. "
            "4) Database health and continuity registry checks. "
            "5) DICOM metadata preview and analysis. "
            "6) Patient timeline and study reconciliation. "
            "7) Patient account, invoice, statement, report, appointment, and referral support on indexed records or uploaded documents. "
            "8) Read-only PACS export generation and safe handoff notes. "
            "You perform all checks as read-only operations that do not modify any source systems. "
            "Be direct and practical in your responses. When the user asks for network diagnostics, VM status, patient support, or infrastructure details, provide the information immediately. "
            "You do not need to ask for proof or authorization again. Respond with concrete results and, if checks are not fully conclusive, suggest next diagnostic steps. "
            "Do not recommend bypasses, password resets, or destructive changes."
        )
        self.last_model_provider = None
        self.last_model_name = None
        self.last_response_mode = None
        self.last_intent = None
        self.last_index_progress = None
        self.last_index_step = None
        self.last_index_result = None
        self.last_export_artifacts = []
        self.last_export_request = None
        self.admin_proof_verified = False
        self.admin_proof_basis = None
        self.is_admin_session = False
        def verify_auth(self, image_path):
            """
            Verify the physical directive via local OCR extraction.
            """
            if not PYTESSERACT_AVAILABLE:
                return {
                    "status": "fail",
                    "message": "OCR_ERROR: pytesseract not installed. OCR verification unavailable."
                }
            
            try:
                # Perform OCR using pytesseract
                # If Tesseract is installed but not on PATH, try common Windows install paths.
                if not shutil.which('tesseract'):
                    candidate = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                    if os.path.exists(candidate):
                        pytesseract.pytesseract.tesseract_cmd = candidate

                extracted_text = pytesseract.image_to_string(Image.open(image_path))
            except Exception as e:
                return {
                    "status": "fail",
                    "message": f"OCR_ERROR: Failed to process image. {str(e)}"
                }

            required_tokens = ["AUTHORIZE", "EMERGENCY", "RADIOLOGY", "DIAGNOSTIC"]
            required_tokens.append("NGWELEZANI")

            extracted_upper = extracted_text.upper()
            system_date = datetime.now().strftime("%Y-%m-%d")
            tokens_found = all(token in extracted_upper for token in required_tokens)
            date_match = system_date in extracted_text

            if tokens_found and date_match:
                self.emergency_override = True
                self.current_state = "VERIFIED"
                self.log_action("Authorization", "Physical Directive Uploaded", "Verified via Local OCR", "Unlock Phase 1 Discovery")
                return {
                    "status": "success",
                    "message": "EMERGENCY_OVERRIDE_ACTIVE: Optical verification complete. Scopes enabled: Read-Only Discovery, Supervised Recovery. You may now run Network Discovery.",
                    "details": f"Verified tokens: {', '.join(required_tokens)} on {system_date}"
                }

            missing = [t for t in required_tokens if t not in extracted_upper]
            if not date_match:
                missing.append(f"DATE_{system_date}")
            return {
                "status": "fail",
                "message": "AUTH_DENIED: Physical directive missing required security tokens or correct timestamp.",
                "details": f"Missing: {', '.join(missing)}"
            }

        def get_recovery_progress(self):
            """Return numeric progress based on state."""
            state_map = {
                "DETECTED": 10,
                "TRIAGED": 30,
                "HYPOTHESIS_FORMED": 50,
                "VERIFIED": 70,
                "MITIGATED": 90,
                "RESOLVED": 100
            }
            return state_map.get(self.current_state, 0)

        def verify_auth(self, image_path):
            """
            Verify the physical directive via local OCR extraction.
            """
            if not PYTESSERACT_AVAILABLE:
                return {
                    "status": "fail",
                    "message": "OCR_ERROR: pytesseract not installed. OCR verification unavailable."
                }
            
            try:
                if not shutil.which('tesseract'):
                    candidate = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                    if os.path.exists(candidate):
                        pytesseract.pytesseract.tesseract_cmd = candidate

                extracted_text = pytesseract.image_to_string(Image.open(image_path))
            except Exception as e:
                return {"status": "fail", "message": f"OCR_ERROR: Failed to process image. {str(e)}"}

            required_tokens = ["AUTHORIZE", "EMERGENCY", "RADIOLOGY", "DIAGNOSTIC", "NGWELEZANI"]
            extracted_upper = extracted_text.upper()
            system_date = datetime.now().strftime("%Y-%m-%d")
            tokens_found = all(token in extracted_upper for token in required_tokens)
            date_match = system_date in extracted_text

            if tokens_found and date_match:
                self.emergency_override = True
                self.current_state = "VERIFIED"
                self.log_action("Authorization", "Physical Directive Uploaded", "Verified via Local OCR", "Unlock Phase 1 Discovery")
                return {
                    "status": "success",
                    "message": "EMERGENCY_OVERRIDE_ACTIVE: Optical verification complete. Scopes enabled: Read-Only Discovery, Supervised Recovery. You may now run Network Discovery.",
                    "details": f"Verified tokens: {', '.join(required_tokens)} on {system_date}"
                }

            missing = [t for t in required_tokens if t not in extracted_upper]
            if not date_match:
                missing.append(f"DATE_{system_date}")
            return {
                "status": "fail",
                "message": "AUTH_DENIED: Physical directive missing required security tokens or correct timestamp.",
                "details": f"Missing: {', '.join(missing)}"
            }

        def get_recovery_progress(self):
            """Return numeric progress based on state."""
            state_map = {
                "DETECTED": 10,
                "TRIAGED": 30,
                "HYPOTHESIS_FORMED": 50,
                "VERIFIED": 70,
                "MITIGATED": 90,
                "RESOLVED": 100
            }
            return state_map.get(self.current_state, 0)

        def _history_to_text(self, history):
            lines = []
            for message in (history or [])[-8:]:
                role = (message.get("role") or "user").upper()
                content = (message.get("content") or "").strip()
                if content:
                    lines.append(f"{role}: {content}")
            return "\n".join(lines)

        def _extract_json_block(self, text):
            clean_text = (text or "").strip()
            if clean_text.startswith("```"):
                if "```json" in clean_text:
                    clean_text = clean_text.split("```json", 1)[1].rsplit("```", 1)[0].strip()
                else:
                    clean_text = clean_text.split("```", 1)[1].rsplit("```", 1)[0].strip()
            return clean_text

        def _gemini_parse_pacs_request(self, user_input, history=None):
            if not self.gemini_api_key:
                return None

            prompt = (
                f"{self.pacs_role_prompt} Return JSON only. "
                "Classify the user's current PACS request using the recent conversation context. "
                "Do not invent paths, database names, credentials, or data that you cannot infer from the conversation. "
                "Use one of these intent values: targeted_path_index, mounted_share_summary, database_explain, registry_search, timeline, general_help. "
                "If the user gives a Windows path like X:\\RIS, set target_path to that exact path. "
                "If the user mentions Firebird, set database_type to Firebird. "
                "If the user asks for mounted NAS devices or what is on them, use mounted_share_summary. "
                "If the request is ambiguous, set needs_clarification to true and provide one short clarification_question. "
                "If the request is a normal PACS guidance question, include a concise response in the response field. "
                "Return keys: intent, target_path, database_type, source_type, needs_clarification, clarification_question, summary, normalized_request, response."
            )

            history_text = self._history_to_text(history)
            user_block = f"RECENT HISTORY:\n{history_text or 'none'}\n\nCURRENT USER REQUEST:\n{user_input}"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": user_block}]}],
                "systemInstruction": {"parts": [{"text": prompt}]},
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 256, "responseMimeType": "application/json"},
            }

            try:
                response = requests.post(url, json=payload, timeout=20)
                if response.status_code != 200:
                    return None

                data = response.json()
                text_content = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(self._extract_json_block(text_content))
                if isinstance(parsed, dict):
                    return parsed
            except Exception as exc:
                print(f" [PACS Gemini Parse Error] {exc}")

            return None

        def _route_registry_request(self, user_input, history=None):
            explicit_paths = self._extract_windows_paths(user_input)
            if explicit_paths:
                self.last_model_provider = "direct"
                self.last_model_name = None
                self.last_response_mode = "registry_targeted_path"
                return self._build_targeted_registry_response(user_input, explicit_paths[0])

            parsed = self._gemini_parse_pacs_request(user_input, history=history)
            intent = (parsed or {}).get("intent")
            target_path = (parsed or {}).get("target_path")
            database_type = (parsed or {}).get("database_type")

            self.last_intent = intent
            if parsed:
                self.last_model_provider = "gemini"
                self.last_model_name = self.gemini_model
                self.last_response_mode = "tool_route"

            if parsed and parsed.get("needs_clarification") and parsed.get("clarification_question"):
                return parsed["clarification_question"]

            if intent == "targeted_path_index" and target_path:
                return self._build_targeted_registry_response(user_input, target_path)

            if intent == "database_explain" and database_type:
                registry_hits = self.registry.search_registry(database_type, limit=10)
                if registry_hits.get("asset_hits") or registry_hits.get("study_hits") or registry_hits.get("patient_hits"):
                    asset_hits = registry_hits.get("asset_hits", [])
                    family = asset_hits[0].get("asset_family") if asset_hits else database_type
                    locations = []
                    for asset in asset_hits[:3]:
                        location = asset.get("source_location") or asset.get("asset_path")
                        if location and location not in locations:
                            locations.append(location)
                    location_text = "; ".join(locations) if locations else "the indexed registry"
                    return (
                        f"I found {family} content in {location_text}. Firebird is a lightweight relational database engine that older RIS and PACS systems often use for local clinical metadata. "
                        f"In this workspace it is treated as a searchable mounted-share source, not as a live write target. "
                        f"Search terms like {database_type}, .fdb, or table names from the registry will bring back matching assets."
                    )

                return (
                    f"I do not see an indexed {database_type} share yet. If you point me at the mounted folder, I can classify it, index the files, and tell you which clinical tables or assets it contains."
                )

            if intent == "timeline":
                return self.registry.describe_registry()

            if intent == "registry_search":
                query = (parsed or {}).get("normalized_request") or user_input
                result = self.registry.search_registry(query, limit=10)
                return (
                    f"Search results for '{query}': {len(result.get('asset_hits', []))} asset hit(s), {len(result.get('study_hits', []))} study hit(s), and {len(result.get('patient_hits', []))} patient hit(s). "
                    "If you want, I can narrow that to a single mounted folder or database type."
                )

            if intent == "mounted_share_summary":
                return self.registry.describe_registry()

            if parsed and parsed.get("response"):
                return parsed["response"]

            text = (user_input or "").lower()
            if any(term in text for term in ["index", "sync", "refresh", "scan", "inventory", "discover"]):
                result = self.registry.sync_registry()
                snapshot = result.get("snapshot", {})
                lines = [
                    f"Registry sync complete. I discovered {result.get('sources_discovered', 0)} source(s), linked {snapshot.get('patient_count', 0)} patient record(s), and indexed {snapshot.get('study_count', 0)} study record(s).",
                    "Source coverage: FHIR for patient and encounter metadata, DICOMweb for study metadata, and NAS for raw DICOM files.",
                    "Matching policy: deterministic EMPI resolution using national ID first, then issuer patient ID, then exact name and birth date, then phonetic fallback.",
                    "Safety policy: I do not destructively merge source systems. I stitch records into one local continuity jacket and timeline.",
                ]
                if snapshot.get("sources"):
                    source_lines = []
                    for source in snapshot["sources"]:
                        source_lines.append(f"{source.get('source_type')} at {source.get('source_location')} -> {source.get('data_class')} ({source.get('last_status') or 'unknown'})")
                    lines.append("Configured sources: " + "; ".join(source_lines))
                if snapshot.get("modality_counts"):
                    modality_lines = []
                    for modality_row in snapshot["modality_counts"]:
                        modality_lines.append(f"{modality_row.get('modality') or 'UNKNOWN'}={modality_row.get('count', 0)}")
                    lines.append("Modality mix: " + ", ".join(modality_lines))
                return " ".join(lines)

            if any(term in text for term in ["timeline", "merge", "jacket", "reconcile", "empi", "patient history", "study history"]):
                return (
                    "I keep one local EMPI jacket per patient and stitch studies across FHIR, DICOMweb, and NAS by deterministic identity rules. "
                    "That means a new x-ray today can sit beside an ultrasound from five years ago in one chronological timeline without destructive source-system merges. "
                    "If you want, I can index the configured sources and then show the patient timeline for the linked EMPI."
                )

            return self.registry.describe_registry()

        def _build_registry_response(self, user_input, history=None):
            return self._route_registry_request(user_input, history=history)

        def generate_response(self, user_input, history=None):
            """State-aware response generator following Autonomic Mentorship rules."""
            self.last_model_provider = None
            self.last_model_name = None
            self.last_response_mode = None
            self.last_intent = None

            if self._is_emergency_request(user_input):
                if not self.emergency_override:
                    self.last_model_provider = "rules"
                    self.last_response_mode = "locked"
                    return (
                        "General PACS mentorship is available now, but password recovery and emergency procedures stay locked until you use the Break-Glass Emergency button and verify the directive."
                    )
                self.last_model_provider = "rules"
                self.last_response_mode = "emergency_guidance"
                return (
                    "Emergency override is active. Tell me the affected system, the symptom, and the checks already performed, and I will guide the recovery step by step."
                )

            if self._is_export_request(user_input):
                response = self._build_export_response(user_input)
                if response:
                    return response

            if self._is_registry_request(user_input):
                response = self._route_registry_request(user_input, history=history)
                if response:
                    return response

            parsed = self._gemini_parse_pacs_request(user_input, history=history)
            if parsed:
                self.last_intent = parsed.get("intent")
                self.last_model_provider = "gemini"
                self.last_model_name = self.gemini_model
                self.last_response_mode = "direct_response"

                if parsed.get("needs_clarification") and parsed.get("clarification_question"):
                    return parsed["clarification_question"]

                if parsed.get("response"):
                    return parsed["response"]

            local_response = self._call_local_gemma(user_input, history=history)
            if local_response:
                return local_response

            self.last_model_provider = "rules"
            self.last_response_mode = "deterministic_fallback"
            return self._build_general_guidance(user_input)

        def sync_continuity_registry(self, source_overrides=None):
            return self.registry.sync_registry(source_overrides=source_overrides)

        def get_continuity_timeline(self, empi_id):
            return self.registry.format_timeline(empi_id)

        def get_continuity_overview(self):
            return self.registry.describe_registry()

    def generate_response(self, user_input, history=None):
        """State-aware response generator following Autonomic Mentorship rules."""
        self.last_model_provider = None
        self.last_model_name = None
        self.last_response_mode = None
        self.last_intent = None
        self.last_index_progress = None
        self.last_index_step = None
        self.last_index_result = None
        self.last_export_artifacts = []
        self.last_export_request = None

        if self._is_emergency_request(user_input):
            if not self.emergency_override:
                self.last_model_provider = "rules"
                self.last_response_mode = "locked"
                return (
                    "General PACS mentorship is available now, but password recovery and emergency procedures stay locked until you use the Break-Glass Emergency button and verify the directive."
                )

            self.last_model_provider = "rules"
            self.last_response_mode = "emergency_guidance"
            return (
                "Emergency override is active. Tell me the affected system, the symptom, and the checks already performed, and I will guide the recovery step by step."
            )

        if self._is_database_health_request(user_input):
            return self._build_database_health_response(user_input)

        if self._is_export_request(user_input):
            response = self._build_export_response(user_input)
            if response:
                return response

        if self._is_runtime_identity_request(user_input):
            return self._build_runtime_identity_response()

        if self._is_patient_support_request(user_input):
            response = self._build_patient_support_response(user_input)
            if response:
                self.last_model_provider = 'rules'
                self.last_model_name = None
                self.last_response_mode = 'patient_support'
                return response

        if self._is_admin_proof_offer(user_input):
            return self._build_admin_proof_accepted_response(user_input)

        if self._is_subnet_scan_request(user_input):
            return self._build_subnet_scan_response(user_input)

        if self._is_deeper_discovery_request(user_input):
            return self._build_admin_proof_request()

        if self._is_registry_request(user_input):
            registry_response = self._route_registry_request(user_input, history=history)
            if registry_response:
                return registry_response

        pacs_admin_response = self._build_pacs_admin_response(user_input)
        if pacs_admin_response:
            self.last_model_provider = 'rules'
            self.last_model_name = None
            self.last_response_mode = 'pacs_admin_guidance'
            return pacs_admin_response

        parsed = self._gemini_parse_pacs_request(user_input, history=history)
        if parsed:
            self.last_intent = parsed.get("intent")
            self.last_model_provider = "gemini"
            self.last_model_name = self.gemini_model
            self.last_response_mode = "direct_response"

            if parsed.get("needs_clarification") and parsed.get("clarification_question"):
                return parsed["clarification_question"]

            if parsed.get("response"):
                return parsed["response"]

        gemma_response = self._call_local_gemma(user_input, history=history)
        if gemma_response:
            return gemma_response

        self.last_model_provider = "rules"
        self.last_response_mode = "deterministic_fallback"
        return self._build_general_guidance(user_input)

    def sync_continuity_registry(self, source_overrides=None):
        result = self.registry.sync_registry(source_overrides=source_overrides)
        self.last_index_result = result
        self.last_index_progress = result.get("progress_percent")
        self.last_index_step = result.get("current_step")
        return result

    def get_continuity_timeline(self, empi_id):
        return self.registry.format_timeline(empi_id)

    def get_continuity_overview(self):
        return self.registry.describe_registry()

    def get_greeting(self, user_name=None):
        name = user_name or "operator"
        return (
            f"Hello {name}. I can help with patient invoices, account statements, radiology reports, DICOM metadata, appointment and referral questions, "
            "plus mounted PACS/NAS sources, Firebird and other database shares, and safe read-only registry search steps."
        )

    def _extract_windows_paths(self, text):
        paths = []
        for match in re.finditer(r'([A-Za-z]:\\[^\s"\']+)', text or ''):
            candidate = match.group(1).rstrip('.,;:)])')
            if candidate not in paths:
                paths.append(candidate)
        return paths

    def _build_targeted_registry_response(self, user_input, target_path):
        result = self.sync_continuity_registry(source_overrides=[{
            "source_type": "NAS",
            "source_label": f"Targeted NAS path {target_path}",
            "source_location": target_path,
            "data_class": "targeted NAS archive",
            "auto_discovered": False,
        }])
        self.last_index_result = result
        self.last_index_progress = result.get("progress_percent")
        self.last_index_step = result.get("current_step")
        snapshot = result.get('snapshot', {})
        source_rows = snapshot.get('sources', [])
        source_text = 'no source records yet'
        if source_rows:
            source_text = '; '.join(
                f"{row.get('source_type')} at {row.get('source_location')} -> {row.get('data_class')} ({row.get('last_status') or 'unknown'})"
                for row in source_rows
            )
        return (
            f"Targeted index complete for {target_path}. I indexed the requested folder as a targeted NAS share. "
            f"Progress reached {result.get('progress_percent', 0)}% at {result.get('current_step') or target_path}. "
            f"Local registry totals now show {snapshot.get('patient_count', 0)} linked patient record(s), {snapshot.get('study_count', 0)} linked study record(s), and {snapshot.get('asset_count', 0)} searchable asset record(s). "
            f"Source detail: {source_text}"
        )

    def _is_emergency_request(self, user_input):
        text = (user_input or '').lower()
        return any(term in text for term in ['emergency', 'break-glass', 'password recovery', 'override', 'incident'])

    def _is_registry_request(self, user_input):
        text = (user_input or '').lower()
        return any(term in text for term in ['index', 'scan', 'mount', 'firebird', 'database', 'registry', 'nas', 'folder', 'timeline'])

    def _build_general_guidance(self, user_input):
        return (
            "I can help with PACS admin work across routing, worklists, archive health, interfaces, backups, and escalation planning. "
            f"My current focus areas are: {', '.join(self.general_skill_topics)}. Ask for the area you want to troubleshoot and I will narrow it down."
        )

    def _is_lan_inventory_request(self, user_input):
        text = (user_input or '').lower()
        has_inventory_phrase = any(term in text for term in [
            'map all vms',
            'all vms',
            'network equipment',
            'network devices',
            'lan',
            'topology',
            'map the network',
            'what is down on our lan',
            'what is down',
            'ping every single one',
        ])
        has_status_phrase = any(term in text for term in ['offline', 'down', 'ping', 'status', 'health'])
        return has_inventory_phrase and has_status_phrase

    def _is_deeper_discovery_request(self, user_input):
        text = (user_input or '').lower()
        has_depth_phrase = any(term in text for term in [
            'explore deeper',
            'deeper and further',
            'further',
            'full topology',
            'full network topology',
            'know our full network',
            'know everything',
            'everything of that lan',
            'discover and know',
            'map all',
            'medical billing',
            'workflow topology',
            'modality topology',
            'ris and pacs',
            'ris, pacs',
        ])
        has_discovery_phrase = any(term in text for term in ['discover', 'inventory', 'map', 'topology', 'offline', 'online'])
        return has_depth_phrase and has_discovery_phrase

    def _build_admin_proof_request(self):
        if self.admin_proof_verified or self.is_admin_session:
            return (
                'I already have site authorization on file for this session. Give me the hostnames, IPs, or inventory source you want checked, and I will keep the work read-only and site-scoped.'
            )
        return (
            'To go deeper, I need proof that you are authorized for the site. '\
            'Provide one of these: a known NAS, network device, VM, or server hostname/IP plus the normal login details for that system; '\
            'or an appointment letter, payslip, or hospital-management order that identifies you as PACS/admin staff. '\
            'If you cannot provide proof, I will stay in safe read-only mode and only give general PACS guidance.'
        )

    def _is_admin_proof_offer(self, user_input):
        text = (user_input or '').lower()
        has_proof_terms = any(term in text for term in [
            'proof',
            'verify my claims',
            'login details',
            'username',
            'password',
            'credential',
            'appointment letter',
            'payslip',
            'hospital-management order',
        ])
        has_target = bool(re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b|\b[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b', text))
        return has_proof_terms and has_target

    def _build_admin_proof_accepted_response(self, user_input):
        text = (user_input or '').strip()
        target_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b|\b[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b', text)
        target = target_match.group(0) if target_match else 'the named device'
        self.admin_proof_verified = True
        self.admin_proof_basis = target
        self.last_model_provider = 'rules'
        self.last_model_name = None
        self.last_response_mode = 'admin_proof'
        return (
            f'I can treat that as site-authorization evidence for {target}. I will not repeat the secret details back. '
            'I can now continue with safe read-only checks against configured targets or the named host, but I still cannot infer a full LAN inventory from one device alone. '
            'If you want me to keep going, give me the next hostnames or IPs, or let me summarize a passive discovery snapshot if one is already allowed.'
        )

    # ------------------------------------------------------------------ #
    #  Subnet sweep                                                        #
    # ------------------------------------------------------------------ #

    def _parse_cidr_from_input(self, user_input):
        """Return an ipaddress.IPv4Network if the message contains CIDR notation."""
        text = (user_input or '')
        # Match patterns like 155.235.81/28, 155.235.81.0/28, 10.0.0.0/24
        patterns = [
            r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/(\d{1,2})\b',   # a.b.c.d/n
            r'\b(\d{1,3}\.\d{1,3}\.\d{1,3})/(\d{1,2})\b',              # a.b.c/n  (missing octet)
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                raw_ip = m.group(1)
                prefix = int(m.group(2))
                # Pad a.b.c/n to a.b.c.0/n
                if raw_ip.count('.') == 2:
                    raw_ip = raw_ip + '.0'
                try:
                    return ipaddress.IPv4Network(f'{raw_ip}/{prefix}', strict=False)
                except ValueError:
                    pass
        return None

    def _is_subnet_scan_request(self, user_input):
        text = (user_input or '').lower()
        has_scan_phrase = any(term in text for term in [
            'find all vms',
            'scan the subnet',
            'hosts on the',
            'hosts on subnet',
            'all hosts on',
            'devices on the',
            'devices on subnet',
            'scan subnet',
            'ping sweep',
            'who is on',
            'what is on',
            'find all hosts',
            'find all devices',
            'find all machines',
        ])
        has_cidr = self._parse_cidr_from_input(user_input) is not None
        return has_scan_phrase or has_cidr

    def _ping_one(self, ip_str):
        """Ping a single IP. Returns (ip_str, online: bool, hostname: str|None)."""
        if os.name == 'nt':
            cmd = ['ping', '-n', '1', '-w', '800', ip_str]
        else:
            cmd = ['ping', '-c', '1', '-W', '1', ip_str]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=3)
            online = result.returncode == 0
        except Exception:
            online = False
        hostname = None
        if online:
            try:
                hostname = socket.gethostbyaddr(ip_str)[0]
            except Exception:
                pass
        return (ip_str, online, hostname)

    def _scan_subnet(self, network):
        """Ping all hosts in network concurrently. Returns list of (ip, online, hostname)."""
        hosts = list(network.hosts())
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, len(hosts) or 1)) as pool:
            results = list(pool.map(lambda h: self._ping_one(str(h)), hosts))
        return results

    def _build_subnet_scan_response(self, user_input):
        network = self._parse_cidr_from_input(user_input)
        if not network:
            self.last_model_provider = 'rules'
            self.last_model_name = None
            self.last_response_mode = 'subnet_scan'
            return (
                'I could not parse a subnet from your message. '
                'Give me a CIDR block like 10.0.0.0/24 or 155.235.81.0/28 and I will sweep it.'
            )

        host_count = network.num_addresses - 2  # exclude network and broadcast
        if host_count <= 0:
            host_count = 1

        # Safety cap: refuse to sweep more than a /20 (4094 hosts) in one call
        if host_count > 4094:
            self.last_model_provider = 'rules'
            self.last_model_name = None
            self.last_response_mode = 'subnet_scan'
            return (
                f'The subnet {network} contains {host_count} potential hosts. '
                'I will not sweep more than a /20 in a single chat request. '
                'Break the range into /24 blocks and I will scan each one.'
            )

        results = self._scan_subnet(network)
        online = [(ip, hn) for (ip, online, hn) in results if online]
        offline_count = len(results) - len(online)

        self.last_model_provider = 'rules'
        self.last_model_name = None
        self.last_response_mode = 'subnet_scan'

        # For admin-verified or admin-session users, always show full detail
        if self.admin_proof_verified or self.is_admin_session:
            if not online:
                return (
                    f'Swept {network} ({host_count} usable addresses). '
                    'No hosts responded to ICMP. '
                    'Possible causes: ICMP is blocked at the firewall, all hosts are offline, or this segment is not reachable from here.'
                )

            # Build detail lines – show IP + hostname if resolved
            lines = [
                f'Swept {network} — found {len(online)} online host(s) out of {host_count} usable address(es):',
            ]
            for ip, hn in online:
                if hn:
                    lines.append(f'  - {ip}  ({hn})')
                else:
                    lines.append(f'  - {ip}')
            if offline_count:
                lines.append(f'{offline_count} address(es) did not respond.')
            return '\n'.join(lines)

        # Non-admin path: redacted results
        return (
            f'Swept {network} ({host_count} usable addresses). '
            f'Found {len(online)} online host(s) and {offline_count} that did not respond. '
            'I will not list the hostnames or IPs until you pass admin proof. '
            'Provide a device login, payslip, or hospital-management order and I will share the full detail.'
        )

    # ------------------------------------------------------------------ #
    #  Runtime identity                                                    #
    # ------------------------------------------------------------------ #

    def _is_runtime_identity_request(self, user_input):
        text = (user_input or '').lower()
        return any(term in text for term in [
            'do you know the ip address',
            'your ip address',
            'machine your running on',
            'machine you are running on',
            'what is your ip',
            'host ip',
            'your host ip',
        ])

    def _build_runtime_identity_response(self):
        self.last_model_provider = 'rules'
        self.last_model_name = None
        self.last_response_mode = 'runtime_identity'
        return (
            'I do not have direct access to my host machine IP address or network configuration from this chat. '
            'What I can do is inspect the local continuity registry, summarize configured LAN targets, and report read-only online/offline status for devices you authorize me to check.'
        )

    def _is_vm_health_request(self, user_input):
        text = (user_input or '').lower()
        has_vm_phrase = any(term in text for term in [
            'check all vms',
            'all vms',
            'any of our vms',
            'which vm',
            'virtual machine',
            'vms',
            'hypervisor',
        ])
        has_offline_phrase = any(term in text for term in ['offline', 'down', 'ping', 'health', 'status'])
        return has_vm_phrase and has_offline_phrase

    def _configured_vm_targets(self):
        targets = []

        def extend_from_value(value):
            if not value:
                return
            for item in re.split(r"[;,\n]+", str(value)):
                candidate = item.strip()
                if candidate and candidate not in targets:
                    targets.append(candidate)

        if self.config.has_section('PACS_VM'):
            extend_from_value(self.config.get('PACS_VM', 'hosts', fallback=''))
            extend_from_value(self.config.get('PACS_VM', 'hostnames', fallback=''))
        if self.config.has_section('VM'):
            extend_from_value(self.config.get('VM', 'hosts', fallback=''))
            extend_from_value(self.config.get('VM', 'hostnames', fallback=''))

        extend_from_value(os.environ.get('PACS_VM_HOSTS'))
        extend_from_value(os.environ.get('VM_HOSTS'))

        return targets

    def _configured_lan_inventory(self):
        inventory = []

        def add_entries(section_name, option_names, default_kind):
            if not self.config.has_section(section_name):
                return
            for option_name in option_names:
                raw_value = self.config.get(section_name, option_name, fallback='')
                if not raw_value:
                    continue
                for item in re.split(r"[;,\n]+", str(raw_value)):
                    candidate = item.strip()
                    if not candidate:
                        continue
                    label = None
                    target = candidate
                    for separator in ('=', ':', '|'):
                        if separator in candidate:
                            left, right = candidate.split(separator, 1)
                            if right.strip():
                                label = left.strip()
                                target = right.strip()
                                break
                    entry = {
                        'label': label or target,
                        'target': target,
                        'kind': default_kind,
                        'section': section_name,
                    }
                    if entry not in inventory:
                        inventory.append(entry)

        add_entries('PACS_VM', ['hosts', 'hostnames'], 'vm')
        add_entries('VM', ['hosts', 'hostnames'], 'vm')
        add_entries('PACS_NETWORK', ['hosts', 'hostnames', 'devices', 'equipment'], 'network')
        add_entries('NETWORK', ['hosts', 'hostnames', 'devices', 'equipment'], 'network')

        for env_name, default_kind in (
            ('PACS_VM_HOSTS', 'vm'),
            ('VM_HOSTS', 'vm'),
            ('PACS_NETWORK_HOSTS', 'network'),
            ('NETWORK_HOSTS', 'network'),
        ):
            raw_value = os.environ.get(env_name)
            if not raw_value:
                continue
            for item in re.split(r"[;,\n]+", str(raw_value)):
                candidate = item.strip()
                if not candidate:
                    continue
                entry = {
                    'label': candidate,
                    'target': candidate,
                    'kind': default_kind,
                    'section': env_name,
                }
                if entry not in inventory:
                    inventory.append(entry)

        return inventory

    def _probe_vm_target(self, target):
        ping_command = ['ping']
        if os.name == 'nt':
            ping_command.extend(['-n', '1', '-w', '1000'])
        else:
            ping_command.extend(['-c', '1', '-W', '1'])
        ping_command.append(target)

        try:
            completed = subprocess.run(ping_command, capture_output=True, text=True, timeout=5)
            stdout = (completed.stdout or '') + '\n' + (completed.stderr or '')
            online = completed.returncode == 0
            reason = None
            if not online:
                if 'timed out' in stdout.lower() or 'request timed out' in stdout.lower():
                    reason = 'request timed out'
                elif 'unreachable' in stdout.lower():
                    reason = 'host unreachable'
                else:
                    reason = 'no ping response'
            return {
                'target': target,
                'status': 'online' if online else 'offline',
                'reason': reason,
            }
        except Exception as exc:
            return {
                'target': target,
                'status': 'unknown',
                'reason': str(exc),
            }

    def _build_vm_health_response(self, user_input):
        requested_targets = []
        for match in re.finditer(r'\b(?:\d{1,3}\.){3}\d{1,3}\b|\b[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b', user_input or ''):
            candidate = match.group(0)
            if candidate and candidate.lower() not in {'vm', 'vms', 'lan'} and candidate not in requested_targets:
                requested_targets.append(candidate)

        targets = requested_targets or self._configured_vm_targets()

        if not targets:
            self.last_model_provider = 'rules'
            self.last_model_name = None
            self.last_response_mode = 'vm_health'
            return (
                'I do not have a VM inventory configured yet, so I cannot truthfully ping every VM on your LAN from this chat. '
                'If you give me the hostnames or IPs, or set PACS_VM_HOSTS / VM_HOSTS in config.ini, I can check them read-only and report which ones are online or offline.'
            )

        results = [self._probe_vm_target(target) for target in targets]
        offline = [item for item in results if item['status'] != 'online']

        lines = [f"I checked {len(results)} VM target(s) with read-only ping probes."]
        for item in results:
            if item['status'] == 'online':
                lines.append(f"- {item['target']}: ONLINE")
            else:
                reason = item.get('reason') or 'no ping response'
                lines.append(f"- {item['target']}: {item['status'].upper()} ({reason})")

        if offline:
            lines.append('Likely causes: the VM is powered off, the guest network is disconnected, ICMP is blocked, or the host is unreachable from this segment.')
        else:
            lines.append('I did not find any offline VMs in the targets I could inspect.')

        self.last_model_provider = 'rules'
        self.last_model_name = None
        self.last_response_mode = 'vm_health'
        return ' '.join(lines)

    def _build_lan_inventory_response(self, user_input):
        inventory = self._configured_lan_inventory()
        discovered_nodes = self.network_map or {}

        if not inventory and not discovered_nodes:
            self.last_model_provider = 'rules'
            self.last_model_name = None
            self.last_response_mode = 'lan_inventory'
            return (
                'I do not have a LAN inventory configured yet, and I do not have a passive network snapshot to report. '
                'Add hostnames or IPs to PACS_VM_HOSTS / VM_HOSTS / PACS_NETWORK_HOSTS in config.ini, or run the passive discovery route after break-glass authorization. '
                'Then I can report what is online or offline without guessing.'
            )

        lines = []
        offline_found = False

        if inventory:
            ping_results = []
            for entry in inventory:
                probe = self._probe_vm_target(entry['target'])
                probe['label'] = entry['label']
                probe['kind'] = entry['kind']
                ping_results.append(probe)

            lines.append(f"I checked {len(ping_results)} configured LAN target(s) with read-only ping probes.")
            for result in ping_results:
                label = result.get('label') or result['target']
                kind = (result.get('kind') or 'device').upper()
                if result['status'] == 'online':
                    lines.append(f"- {label} [{kind}] -> {result['target']}: ONLINE")
                else:
                    offline_found = True
                    reason = result.get('reason') or 'no ping response'
                    lines.append(f"- {label} [{kind}] -> {result['target']}: {result['status'].upper()} ({reason})")

        if discovered_nodes:
            lines.append(f"Passive discovery snapshot contains {len(discovered_nodes)} node(s):")
            for ip, info in discovered_nodes.items():
                vendor = info.get('vendor') or 'Unknown Vendor'
                mac = info.get('mac') or 'unknown MAC'
                lines.append(f"- {ip}: {vendor} ({mac})")

        if offline_found:
            lines.append('Likely causes for offline entries: the device is powered off, the guest network is disconnected, ICMP is blocked, or the host is unreachable from this segment.')
        elif inventory:
            lines.append('I did not find any offline entries in the configured targets I could inspect.')

        self.last_model_provider = 'rules'
        self.last_model_name = None
        self.last_response_mode = 'lan_inventory'
        return ' '.join(lines)

    def _is_database_health_request(self, user_input):
        text = (user_input or '').lower()
        has_health_phrase = any(term in text for term in [
            'what database is down',
            'which database is down',
            'check all databases',
            'all databases',
            'offline',
            'down now',
            'what is offline',
            'whats offline',
            'what’s offline',
        ])
        has_database_reference = any(term in text for term in ['database', 'databases', 'firebird', 'sql server', 'ris', 'pacs'])
        return has_health_phrase and has_database_reference

    def _build_database_health_response(self, user_input):
        result = self.registry.sync_registry()
        snapshot = result.get('snapshot', {})
        reports = result.get('reports', []) or []
        sources = snapshot.get('sources', []) or []

        if not sources:
            self.last_model_provider = 'rules'
            self.last_model_name = None
            self.last_response_mode = 'database_health'
            return (
                'I do not have any configured database sources to inspect yet. Add the database mount, Firebird folder, or PACS/FHIR/DICOMweb source path to the registry, then I can check it and explain what is offline.'
            )

        lines = [
            f"I checked {len(sources)} database or database-like source(s) in the local registry.",
            f"Indexed records: {snapshot.get('patient_count', 0)} patient(s), {snapshot.get('study_count', 0)} study(ies), {snapshot.get('asset_count', 0)} asset(s).",
        ]

        offline_found = False
        for report in reports:
            status = (report.get('status') or 'unknown').upper()
            source_type = report.get('source_type') or 'UNKNOWN'
            current_step = report.get('current_step') or 'unknown source'
            notes = report.get('notes') or []
            reason = '; '.join(str(note) for note in notes if note) or None

            if status in {'PARTIAL', 'SKIPPED'}:
                offline_found = True
                if not reason:
                    reason = 'last sync reported partial results' if status == 'PARTIAL' else 'source was unavailable during the last check'
                lines.append(f"- {source_type} | {current_step} | {status} | {reason}")
            else:
                lines.append(f"- {source_type} | {current_step} | {status} | reachable on last sync")

        if offline_found:
            lines.append('Why it is offline: the registry reports the last observed access state. In practice, partial or skipped usually means the mount path was unavailable, the service lacked credentials, or the source did not answer during the read-only sync.')
        else:
            lines.append('I did not see any offline sources in the last registry sync.')

        self.last_model_provider = 'rules'
        self.last_model_name = None
        self.last_response_mode = 'database_health'
        return ' '.join(lines)

    def _build_capability_response(self):
        return (
            "For PACS staff and patients, I can already help with these read-only tools and workflows: "
            "1) inspect mounted NAS and database shares, including Firebird-style RIS folders and medical billing databases; "
            "2) index FHIR, DICOMweb, and NAS sources into a local continuity registry; "
            "3) preview DICOM metadata and build a redacted view without modifying the source file; "
            "4) search patients, studies, assets, and patient-support records with redaction; "
            "5) generate DOCX or PDF exports with workflow, database, and network diagrams from the local registry snapshot; "
            "6) show progress and failure state for indexing runs; "
            "7) ping configured VMs or hosts read-only and report online/offline status; "
            "8) summarize a configured LAN inventory or passive discovery snapshot for VMs and network equipment; "
            "9) explain FHIR, DICOMweb, SIIM hackathon, worklist, invoice, statement, appointment, referral, and report mappings with concrete fields; "
            "10) use the dedicated OpenClaw pacs-continuity skill for PACS continuity, routing, worklists, archive health, and break-glass recovery handoff; "
            "11) use OpenClaw skills like xurl, summarize, openai-whisper, and wacli for API checks, document summaries, transcription, and staff follow-up. "
            "If you give me a path, URL, or search term, I can act on it directly without needing you to name an OpenClaw skill."
        )

    def _is_patient_support_request(self, user_input):
        text = (user_input or '').lower()
        return any(term in text for term in [
            'invoice',
            'statement',
            'account',
            'billing',
            'bill',
            'report',
            'dicom',
            'image',
            'study',
            'appointment',
            'referral',
            'referrals',
            'confirm appointment',
            'confirm referral',
        ])

    def _build_patient_support_response(self, user_input):
        text = (user_input or '').lower()
        paths = self._extract_windows_paths(user_input)

        if any(term in text for term in ['dicom', 'image', 'study']) and paths:
            preview = self.registry.preview_dicom_metadata(paths[0], redact=True)
            if isinstance(preview, dict):
                status = preview.get('status') or 'unknown'
                notes = ', '.join(preview.get('notes', []) or [])
                return (
                    f"I checked the DICOM file at {paths[0]}. Status: {status}. "
                    f"Notes: {notes or 'none'}. "
                    "I can preview the metadata, but I will not alter the source image."
                )

        if any(term in text for term in ['invoice', 'statement', 'account', 'billing', 'bill']):
            return (
                "I can help you review an invoice or account statement in patient-safe mode. "
                "Send the account number, invoice number, or a PDF/screenshot of the statement and I can help explain what is shown, or search the indexed local records if the billing source is available. "
                "I will not invent charges, balances, or payment status."
            )

        if any(term in text for term in ['report', 'results']):
            return (
                "I can help explain a radiology report or summarize indexed study information. "
                "Send the study date, patient reference, or DICOM file path and I can preview the available metadata or help you understand the report wording. "
                "I will not guess at findings that are not present in the local record."
            )

        if any(term in text for term in ['appointment', 'book', 'booking', 'confirm']) or 'referral' in text:
            return (
                "I can help confirm an appointment or referral if you give me the clinic, date, or reference number. "
                "If the appointment or referral is indexed locally, I can help search it and summarize what is recorded. "
                "If not, I can draft the exact follow-up message you should send to the booking desk."
            )

        return (
            "I can help with invoices, account statements, reports, DICOM image metadata, appointment confirmation, and referrals. "
            "Give me the patient reference, invoice number, study date, or file path and I will stay in patient-safe read-only mode."
        )

    def _is_export_request(self, user_input):
        text = (user_input or '').lower()
        return any(term in text for term in ['export', 'download', 'docx', 'word document', 'pdf', 'workflow diagram', 'database diagram', 'network diagram'])

    def _resolve_export_formats(self, user_input):
        text = (user_input or '').lower()
        if 'both' in text or ('docx' in text and 'pdf' in text):
            return ['docx', 'pdf']
        if 'pdf' in text and 'docx' not in text and 'word' not in text:
            return ['pdf']
        return ['docx']

    def _build_export_response(self, user_input):
        formats = self._resolve_export_formats(user_input)
        export_dir = os.path.join(self.workspace_path, 'instance', 'pacs_exports')
        os.makedirs(export_dir, exist_ok=True)
        artifacts = []
        links = []

        for export_format in formats:
            artifact = generate_pacs_export_artifact(
                self.registry,
                mentor=self,
                output_format=export_format,
                include_diagrams=True,
                output_dir=export_dir,
            )
            artifacts.append(artifact)
            links.append(
                f'<a href="/pacs/export?format={export_format}&redact=true&include_diagrams=true" target="_blank" rel="noopener noreferrer">Download {export_format.upper()}</a>'
            )

        self.last_export_artifacts = artifacts
        self.last_export_request = user_input
        self.last_model_provider = 'rules'
        self.last_model_name = None
        self.last_response_mode = 'export'

        label = ' and '.join(export_format.upper() for export_format in formats)
        return (
            f"I generated a read-only {label} export from the local registry snapshot with workflow, database, and network diagrams. "
            f"Source systems were not modified. {' | '.join(links)}"
        )

    def _build_pacs_admin_response(self, user_input):
        text = (user_input or '').lower()

        if any(term in text for term in ['what tools', 'what can you do', 'what do you have', 'helpful to a pacs admin', 'tool to be helpful', 'right tools']):
            return self._build_capability_response()

        if self._is_deeper_discovery_request(user_input):
            return self._build_admin_proof_request()

        if self._is_lan_inventory_request(user_input):
            return self._build_lan_inventory_response(user_input)

        if self._is_vm_health_request(user_input):
            return self._build_vm_health_response(user_input)

        if self._is_database_health_request(user_input):
            return self._build_database_health_response(user_input)

        if self._is_export_request(user_input):
            return self._build_export_response(user_input)

        if any(term in text for term in ['scrub', 'de-ident', 'deidentify', 'anonym', 'redact', 'phi', 'privacy']):
            return (
                "For a read-only scrubbing workflow, I can preview DICOM metadata, mask patient identifiers, and build a redacted registry view without editing the source study database or DICOM file. "
                "Use pydicom with stop_before_pixels=True to inspect headers, then run a preview-only redaction pass that masks PatientName, PatientID, birth date, accession number, and physician identifiers. "
                "For indexed study databases, keep the original database untouched and serve only a masked result set from the local continuity registry."
            )

        if any(term in text for term in ['openclaw', 'skill', 'skills']):
            return (
                "Yes. This workspace has a dedicated OpenClaw pacs-continuity skill for PACS continuity, routing, worklists, archive health, and break-glass recovery handoff. "
                "For DICOM and FHIR work, I still rely on the registry preview/redaction helpers plus normal HTTP and Python tooling to inspect metadata and join records. "
                "For LAN topology, I can only report configured targets or a passive discovery snapshot; I cannot invent a full network map from free text."
            )

        if any(term in text for term in ['siim', 'hackathon', 'api key', 'api keys', 'fhir', 'dicomweb', 'metadata', 'metadata extraction', 'worklist', 'match', 'matching']):
            return (
                "For a PACS admin workflow, use the APIs this way: FHIR usually gives you patient, encounter, service request, and worklist-style clinical context; DICOMweb usually gives you study, series, instance, and retrieval metadata. "
                "Start by pulling the FHIR side for Patient.id, identifier, name, birthDate, and the order or worklist identifiers. Then pull DICOMweb StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID, AccessionNumber, PatientID, StudyDate, and Modality. "
                "Match in this order: accession number and StudyInstanceUID first, then PatientID, then name plus birth date. If you need a hackathon demo, build a small pipeline that queries both APIs, normalizes the identifiers, and prints a joined table of patient, order, study, and series fields. "
                "For privacy-safe demos, use the registry's read-only DICOM preview and redacted search helpers so you can show metadata extraction and PHI scrubbing without mutating the source system. "
                "The nearest useful OpenClaw workflow here is to use an HTTP probing skill such as xurl for the API responses, then a Python step for pydicom or FHIR parsing."
            )

        return None

    def _call_local_gemma(self, user_input, history=None):
        """Fallback to local Gemma 2B via Ollama when Gemini is unavailable."""
        history_text = self._history_to_text(history)
        prompt = (
            f"{self.pacs_role_prompt}\n\n"
            f"Recent conversation:\n{history_text or 'none'}\n\n"
            f"User request:\n{user_input}\n\n"
            "Answer as the PACS Continuity Mentor."
        )

        payload = {
            "model": "gemma:2b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.4,
                "num_predict": 220,
            },
        }

        for host in ("http://localhost:11434/api/generate", "http://127.0.0.1:11434/api/generate"):
            try:
                response = requests.post(host, json=payload, timeout=120)
                if response.status_code != 200:
                    continue
                data = response.json()
                text = (data.get("response") or "").strip()
                if text:
                    self.last_model_provider = "gemma"
                    self.last_model_name = "gemma:2b"
                    self.last_response_mode = "fallback"
                    return text
            except Exception as exc:
                print(f"[PACS Gemma Fallback Error] {exc}")

        return None

    def _call_local_gemma(self, user_input, history=None):
        """Fallback to local Gemma 2B via Ollama when Gemini is unavailable."""
        history_text = self._history_to_text(history)
        prompt = (
            f"{self.pacs_role_prompt}\n\n"
            f"Recent conversation:\n{history_text or 'none'}\n\n"
            f"User request:\n{user_input}\n\n"
            "Answer as the PACS Continuity Mentor."
        )

        payload = {
            "model": "gemma:2b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.4,
                "num_predict": 220,
            },
        }

        for host in ("http://localhost:11434/api/generate", "http://127.0.0.1:11434/api/generate"):
            try:
                response = requests.post(host, json=payload, timeout=120)
                if response.status_code != 200:
                    continue
                data = response.json()
                text = (data.get("response") or "").strip()
                if text:
                    self.last_model_provider = "gemma"
                    self.last_model_name = "gemma:2b"
                    self.last_response_mode = "fallback"
                    return text
            except Exception as exc:
                print(f"[PACS Gemma Fallback Error] {exc}")

        return None

    def verify_auth(self, image_path):
        """
        Verify the physical directive via local OCR extraction.
        """
        if not PYTESSERACT_AVAILABLE:
            return {
                "I can help patients and PACS staff across routing, worklists, archive health, interfaces, backups, invoices, statements, reports, DICOM image previews, appointments, referrals, and escalation planning. "
                "message": "OCR_ERROR: pytesseract not installed. OCR verification unavailable."
            }
        
        try:
            if not shutil.which('tesseract'):
                candidate = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                if os.path.exists(candidate):
                    pytesseract.pytesseract.tesseract_cmd = candidate

            extracted_text = pytesseract.image_to_string(Image.open(image_path))
        except Exception as e:
            return {"status": "fail", "message": f"OCR_ERROR: Failed to process image. {str(e)}"}

        required_tokens = ["AUTHORIZE", "EMERGENCY", "RADIOLOGY", "DIAGNOSTIC", "NGWELEZANI"]
        extracted_upper = extracted_text.upper()
        system_date = datetime.now().strftime("%Y-%m-%d")
        tokens_found = all(token in extracted_upper for token in required_tokens)
        date_match = system_date in extracted_text

        if tokens_found and date_match:
            self.emergency_override = True
            self.current_state = "VERIFIED"
            self.log_action("Authorization", "Physical Directive Uploaded", "Verified via Local OCR", "Unlock Phase 1 Discovery")
            return {
                "status": "success",
                "message": "EMERGENCY_OVERRIDE_ACTIVE: Optical verification complete. Scopes enabled: Read-Only Discovery, Supervised Recovery. You may now run Network Discovery.",
                "details": f"Verified tokens: {', '.join(required_tokens)} on {system_date}"
            }

        missing = [t for t in required_tokens if t not in extracted_upper]
        if not date_match:
            missing.append(f"DATE_{system_date}")
        return {
            "status": "fail",
            "message": "AUTH_DENIED: Physical directive missing required security tokens or correct timestamp.",
            "details": f"Missing: {', '.join(missing)}"
        }

    def get_recovery_progress(self):
        """Return numeric progress based on state."""
        state_map = {
            "DETECTED": 10,
            "TRIAGED": 30,
            "HYPOTHESIS_FORMED": 50,
            "VERIFIED": 70,
            "MITIGATED": 90,
            "RESOLVED": 100,
        }
        return state_map.get(self.current_state, 0)

    def _history_to_text(self, history):
        lines = []
        for message in (history or [])[-8:]:
            role = (message.get('role') or 'user').upper()
            content = (message.get('content') or '').strip()
            if content:
                lines.append(f"{role}: {content}")
        return '\n'.join(lines)

    def _extract_json_block(self, text):
        clean_text = (text or '').strip()
        if clean_text.startswith('```'):
            if '```json' in clean_text:
                clean_text = clean_text.split('```json', 1)[1].rsplit('```', 1)[0].strip()
            else:
                clean_text = clean_text.split('```', 1)[1].rsplit('```', 1)[0].strip()
        return clean_text

    def _gemini_parse_pacs_request(self, user_input, history=None):
        if not self.gemini_api_key:
            return None

        # Use admin prompt if in admin session
        role_prompt = self.pacs_admin_role_prompt if self.is_admin_session else self.pacs_role_prompt

        prompt = (
            f"{role_prompt} Return JSON only. "
            "Classify the user's current PACS request using the recent conversation context. "
            "Do not invent paths, database names, credentials, or data that you cannot infer from the conversation. "
            "If the user asks what tools, capabilities, or workflows you have, classify that as general_help and include a direct capability response rather than a clarification question. "
            "Use one of these intent values: targeted_path_index, mounted_share_summary, database_explain, registry_search, timeline, general_help, subnet_scan, vm_health. "
            "If the user asks about SIIM hackathon workflows, FHIR, DICOMweb, API keys, metadata extraction, or matching studies to patients, prefer general_help and provide a concrete response. "
            "If the user asks to find VMs on a subnet, scan a subnet, ping hosts, or check infrastructure status, use subnet_scan or vm_health intent. "
            "If the user gives a Windows path like X:\\RIS, set target_path to that exact path. "
            "If the user mentions Firebird, set database_type to Firebird. "
            "If the user asks for mounted NAS devices or what is on them, use mounted_share_summary. "
            "If the request is truly ambiguous, set needs_clarification to true and provide one short clarification_question. "
            "If the request is a normal PACS guidance question, include a concise response in the response field. "
            "Return keys: intent, target_path, database_type, source_type, needs_clarification, clarification_question, summary, normalized_request, response."
        )

        history_text = self._history_to_text(history)
        user_block = f"RECENT HISTORY:\n{history_text or 'none'}\n\nCURRENT USER REQUEST:\n{user_input}"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
        payload = {
            'contents': [{'role': 'user', 'parts': [{'text': user_block}]}],
            'systemInstruction': {'parts': [{'text': prompt}]},
            'generationConfig': {'temperature': 0.1, 'maxOutputTokens': 256, 'responseMimeType': 'application/json'},
        }

        try:
            response = requests.post(url, json=payload, timeout=20)
            if response.status_code != 200:
                return None

            data = response.json()
            text_content = data['candidates'][0]['content']['parts'][0]['text']
            parsed = json.loads(self._extract_json_block(text_content))
            if isinstance(parsed, dict):
                return parsed
        except Exception as exc:
            print(f" [PACS Gemini Parse Error] {exc}")

        return None

    def _route_registry_request(self, user_input, history=None):
        explicit_paths = self._extract_windows_paths(user_input)
        if explicit_paths:
            self.last_model_provider = "direct"
            self.last_model_name = None
            self.last_response_mode = "registry_targeted_path"
            return self._build_targeted_registry_response(user_input, explicit_paths[0])

        parsed = self._gemini_parse_pacs_request(user_input, history=history)
        intent = (parsed or {}).get('intent')
        target_path = (parsed or {}).get('target_path')
        database_type = (parsed or {}).get('database_type')

        self.last_intent = intent
        if parsed:
            self.last_model_provider = "gemini"
            self.last_model_name = self.gemini_model
            self.last_response_mode = "tool_route"

        if parsed and parsed.get('needs_clarification') and parsed.get('clarification_question'):
            return parsed['clarification_question']

        if intent == 'targeted_path_index' and target_path:
            return self._build_targeted_registry_response(user_input, target_path)

        if intent == 'database_explain' and database_type:
            registry_hits = self.registry.search_registry(database_type, limit=10)
            if registry_hits.get('asset_hits') or registry_hits.get('study_hits') or registry_hits.get('patient_hits'):
                asset_hits = registry_hits.get('asset_hits', [])
                family = asset_hits[0].get('asset_family') if asset_hits else database_type
                locations = []
                for asset in asset_hits[:3]:
                    location = asset.get('source_location') or asset.get('asset_path')
                    if location and location not in locations:
                        locations.append(location)
                location_text = '; '.join(locations) if locations else 'the indexed registry'
                return (
                    f"I found {family} content in {location_text}. Firebird is a lightweight relational database engine that older RIS and PACS systems often use for local clinical metadata. "
                    f"In this workspace it is treated as a searchable mounted-share source, not as a live write target. "
                    f"Search terms like {database_type}, .fdb, or table names from the registry will bring back matching assets."
                )

            return f"I do not see an indexed {database_type} share yet. If you point me at the mounted folder, I can classify it, index the files, and tell you which clinical tables or assets it contains."

        if intent == 'timeline':
            return self.registry.describe_registry()

        if intent == 'registry_search':
            query = (parsed or {}).get('normalized_request') or user_input
            result = self.registry.search_registry(query, limit=10)
            return (
                f"Search results for '{query}': {len(result.get('asset_hits', []))} asset hit(s), {len(result.get('study_hits', []))} study hit(s), and {len(result.get('patient_hits', []))} patient hit(s). "
                'If you want, I can narrow that to a single mounted folder or database type.'
            )

        if intent == 'mounted_share_summary':
            return self.registry.describe_registry()

        if parsed and parsed.get('response'):
            return parsed['response']

        text = (user_input or '').lower()
        if any(term in text for term in ['index', 'sync', 'refresh', 'scan', 'inventory', 'discover']):
            result = self.sync_continuity_registry()
            snapshot = result.get('snapshot', {})
            lines = [
                f"Registry sync complete. I discovered {result.get('sources_discovered', 0)} source(s), linked {snapshot.get('patient_count', 0)} patient record(s), and indexed {snapshot.get('study_count', 0)} study record(s).",
                'Source coverage: FHIR for patient and encounter metadata, DICOMweb for study metadata, and NAS for raw DICOM files.',
                'Matching policy: deterministic EMPI resolution using national ID first, then issuer patient ID, then exact name and birth date, then phonetic fallback.',
                'Safety policy: I do not destructively merge source systems. I stitch records into one local continuity jacket and timeline.',
            ]
            if result.get('progress_percent') is not None:
                lines.append(f"Progress: {result.get('progress_percent')}% ({result.get('current_step') or 'complete'}).")
            if snapshot.get('sources'):
                source_lines = []
                for source in snapshot['sources']:
                    source_lines.append(f"{source.get('source_type')} at {source.get('source_location')} -> {source.get('data_class')} ({source.get('last_status') or 'unknown'})")
                lines.append('Configured sources: ' + '; '.join(source_lines))
            if snapshot.get('modality_counts'):
                modality_lines = []
                for modality_row in snapshot['modality_counts']:
                    modality_lines.append(f"{modality_row.get('modality') or 'UNKNOWN'}={modality_row.get('count', 0)}")
                lines.append('Modality mix: ' + ', '.join(modality_lines))
            return ' '.join(lines)

        if any(term in text for term in ['timeline', 'merge', 'jacket', 'reconcile', 'empi', 'patient history', 'study history']):
            return (
                'I keep one local EMPI jacket per patient and stitch studies across FHIR, DICOMweb, and NAS by deterministic identity rules. '
                'That means a new x-ray today can sit beside an ultrasound from five years ago in one chronological timeline without destructive source-system merges. '
                'If you want, I can index the configured sources and then show the patient timeline for the linked EMPI.'
            )

        return self.registry.describe_registry()

    def _build_registry_response(self, user_input, history=None):
        return self._route_registry_request(user_input, history=history)

    def passive_discovery(self, interface="eth0", timeout=30):
        """
        Runs Phase 1 Locked Mode discovery.
        Identify hardware vendors via MAC OUI and probe clinical sockets.
        """
        if not self.emergency_override:
            return {"status": "fail", "message": "Emergency Override not active. Use the Break-Glass Emergency button to verify the directive before running discovery."}

        self.log_action("Network Discovery", f"Sniffing on {interface}", "Phase 1 - Locked Mode", "Scanning Broadcast Domain")
        
        # 1. MAC-to-Vendor Fingerprinting
        discovered_nodes = self._sniff_mac_oui(interface, timeout)
        
        # 2. Clinical Socket Probing
        topology = self._probe_clinical_sockets(discovered_nodes)
        self.network_map = topology
        
        self.current_state = "HYPOTHESIS_FORMED"
        return {"status": "success", "topology": topology}

    def _sniff_mac_oui(self, interface, timeout):
        """Passively capture ARP broadcasts to find active network interfaces."""
        if not SCAPY_AVAILABLE:
            return {}
        
        packets = scapy.sniff(filter="arp", iface=interface, timeout=timeout)
        nodes = {}
        for pkt in packets:
            if pkt.haslayer(scapy.ARP) and pkt.op == 1:
                ip = pkt.psrc
                mac = pkt.hwsrc
                oui = mac.replace(":", "").upper()[:6]
                
                # Internal IEEE OUI Dictionary (Simplified for Prototype)
                vendor_map = {
                    "000C29": "VMware Hypervisor (Potential PACS VM Host)",
                    "005056": "VMware Hypervisor (Potential PACS VM Host)",
                    "001A1E": "GE Healthcare Modality (CT/X-Ray Console)",
                    "00120F": "Siemens Modality",
                    "00000C": "Cisco Infrastructure"
                }
                vendor = vendor_map.get(oui, "Unknown Vendor")
                nodes[ip] = {"mac": mac, "vendor": vendor}
        return nodes

    def _probe_clinical_sockets(self, nodes):
        """Map active clinical routing engines and database stores."""
        clinical_ports = {
            104: "DICOM Listener",
            4242: "Orthanc/DICOM Router",
            11112: "DICOM Service",
            3050: "Firebird SQL (Clinical Metadata)",
            1433: "MSSQL (Database Store)",
            5432: "PostgreSQL (Database Store)"
        }
        
        topology = []
        for ip, info in nodes.items():
            active_services = []
            # In a real tool, we use soft-socket probes here
            # For the prototype logic, we append discovered info
            topology.append({
                "ip": ip,
                "vendor": info["vendor"],
                "mac": info["mac"],
                "potential_role": "Investigating..."
            })
        return topology

    def get_recovery_walkthrough(self, target_type="LINUX_VM"):
        """Returns step-by-step non-destructive physical override instructions."""
        if not self.emergency_override:
            return "Unauthorized. Recovery walkthroughs are locked until the Break-Glass Emergency directive is verified."

        if target_type == "LINUX_VM":
            self.current_state = "MITIGATED"
            return [
                "1. Connect to the console and capture the exact boot or service error message.",
                "2. Confirm power, storage, and network links are present before changing anything.",
                "3. Check the normal service logs or vendor recovery console using approved credentials.",
                "4. Restore the last known-good backup or snapshot only if change control approves it.",
                "5. Re-test DICOM, RIS, and database connectivity after the approved recovery step.",
                "VERIFICATION: Document the original failure, the approved recovery action, and the post-check result."
            ]
        elif target_type == "SWITCH_SERIAL":
            return [
                "1. Connect the laptop to the switch console port using the approved console cable.",
                "2. Capture the current boot and VLAN state before any change is made.",
                "3. Use the vendor-approved management CLI with the normal administrative login.",
                "4. Back up the running configuration, then apply only change-controlled edits.",
                "VERIFICATION: Re-check VLAN reachability, uplink status, and PACS path connectivity after the approved change."
            ]
        return "Unknown target type."

    def generate_incident_report(self):
        """Generates a JSON payload suitable for ServiceNow or IT Audit."""
        report = {
            "incident_id": f"PACS-RECOVERY-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "start_time": datetime.now().isoformat(),
            "status": self.current_state,
            "actions_performed": self.action_log,
            "discovery_snapshot": self.network_map,
            "validation_method": "OCR_DIRECTIVE_IMAGE",
            "compliance_note": "Non-destructive hardware intercept executed under clinical emergency protocols."
        }
        return report

