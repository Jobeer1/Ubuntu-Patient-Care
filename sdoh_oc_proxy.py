#!/usr/bin/env python
"""Local proxy that adapts OpenAI Responses calls to the existing SDOH chat endpoint."""

from __future__ import annotations

import configparser
import json
import os
import re
import ssl
import time
import traceback
import urllib.error
import urllib.request
import uuid

from flask import Flask, Response, jsonify, request, stream_with_context


ROOT_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(ROOT_DIR, "config.ini")
BACKEND_BASE_URL = "https://127.0.0.1:5002/api/sdoh/oc"
PROXY_PORT = 5001


def load_owner_token() -> str:
    token = os.environ.get("SDOH_OWNER_TOKEN", "").strip()
    if token:
        return token
    parser = configparser.ConfigParser()
    parser.read(CONFIG_PATH)
    return parser.get("PACS_SECURITY", "owner_token", fallback="").strip()


OWNER_TOKEN = load_owner_token()
SSL_CONTEXT = ssl._create_unverified_context()
APP = Flask(__name__)
_LOCAL_SDOH_AGENT = None


def require_gateway_auth():
    auth_header = request.headers.get("Authorization", "")
    bearer = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
    custom_token = request.headers.get("X-SDOH-Owner-Token", "").strip()
    if OWNER_TOKEN and (bearer == OWNER_TOKEN or custom_token == OWNER_TOKEN):
        return None
    return jsonify({"error": {"message": "Unauthorized", "type": "authentication_error"}}), 401


def get_local_sdoh_agent():
    """Lazy local fallback agent used when backend bridge is unavailable/stale."""
    global _LOCAL_SDOH_AGENT
    if _LOCAL_SDOH_AGENT is None:
        from agent_sdoh import SDOHContinuityAgent
        _LOCAL_SDOH_AGENT = SDOHContinuityAgent(CONFIG_PATH)
    return _LOCAL_SDOH_AGENT


def unwrap_openclaw_metadata(text: str) -> str:
    """Extract the actionable user line from OpenClaw metadata envelopes."""
    raw = str(text or "").strip()
    if not raw:
        return raw

    cleaned = re.sub(
        r"Conversation info \(untrusted metadata\):\s*```json.*?```",
        "",
        raw,
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned = re.sub(
        r"Sender \(untrusted metadata\):\s*```json.*?```",
        "",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned = re.sub(
        r"The previous attempt did not produce a user-visible answer\..*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not lines:
        return raw

    for line in reversed(lines):
        if line in {"```", "```json"}:
            continue
        if line.lower().startswith("conversation info (untrusted metadata)"):
            continue
        if line.lower().startswith("sender (untrusted metadata)"):
            continue
        return line

    return lines[-1]


def ensure_deliverable_text(text: str, user_hint: str = "") -> str:
    """Prevent non-deliverable empty/NO_REPLY terminal turns."""
    normalized = str(text or "").strip()
    if normalized and normalized.upper() != "NO_REPLY":
        return normalized

    hint = unwrap_openclaw_metadata(user_hint)
    if hint:
        return (
            f"I am here and ready to help. You asked: {hint}\n\n"
            "Tell me what you want me to do now, for example: \"index Z: drive\" or \"index all WhatsApp chats\"."
        )
    return (
        "I am here and ready to help. Tell me what you want me to do now, "
        "for example: \"index Z: drive\" or \"index all WhatsApp chats\"."
    )


def extract_user_hint(messages: list[dict[str, str]]) -> str:
    for msg in reversed(messages or []):
        if str(msg.get("role") or "").lower() == "user":
            return str(msg.get("content") or "")
    return ""


def ensure_chat_payload_deliverable(chat_payload: dict[str, object], user_hint: str = "") -> dict[str, object]:
    if not isinstance(chat_payload, dict):
        return chat_payload
    choices = chat_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return chat_payload
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return chat_payload
    message = first_choice.get("message")
    if not isinstance(message, dict):
        message = {}
        first_choice["message"] = message

    fixed_text = ensure_deliverable_text(message.get("content", ""), user_hint=user_hint)
    message["role"] = "assistant"
    message["content"] = fixed_text

    usage = chat_payload.get("usage")
    if isinstance(usage, dict):
        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = len(fixed_text.split())
        usage["completion_tokens"] = completion_tokens
        usage["total_tokens"] = prompt_tokens + completion_tokens

    return chat_payload


def _extract_sender_number_from_metadata(messages: list[dict]) -> str:
    """Pull the WhatsApp sender number from OpenClaw's metadata envelope."""
    for msg in (messages or []):
        if str(msg.get("role") or "").lower() != "user":
            continue
        content = str(msg.get("content") or "")
        # OpenClaw embeds sender info in JSON block: "sender": "+27768193339"
        m = re.search(r'"sender"\s*:\s*"([+\d]+)"', content)
        if m:
            return m.group(1)
        # Also try plain "Sender (untrusted metadata): +27768193339"
        m = re.search(r'Sender \(untrusted metadata\):\s*([+\d]+)', content, re.IGNORECASE)
        if m:
            return m.group(1)
    return ""


_ADMIN_NUMBERS = {"27768193339", "0768193339"}


def _query_vault_index_for_folder(folder_path: str) -> dict:
    """Query the master_health_graph.json for files matching a folder path."""
    vault_index_path = os.path.expanduser("~/.openclaw/vault/index/master_health_graph.json")
    
    if not os.path.exists(vault_index_path):
        return {"count": 0, "error": "Vault index not found"}
    
    try:
        with open(vault_index_path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        
        entries = []
        if isinstance(data, list):
            entries = data
        elif isinstance(data, dict):
            for key in ['records', 'entries', 'documents', 'index']:
                value = data.get(key)
                if isinstance(value, list):
                    entries = value
                    break
        
        normalized_folder = folder_path.replace('\\\\', '\\').lower()
        matching = [e for e in entries if e.get('file_path', '').replace('\\\\', '\\').lower().startswith(normalized_folder)]
        
        modalities = {}
        for e in matching:
            mod = e.get('modality') or e.get('modality_label', 'unknown')
            modalities[mod] = modalities.get(mod, 0) + 1
        
        return {"count": len(matching), "modalities": modalities, "sample": matching[:5] if matching else []}
    except Exception as e:
        return {"count": 0, "error": str(e)}


_DRIVE_UNC_CACHE: dict = {}

def _resolve_drive_to_unc(path: str) -> str:
    """Resolve a Windows drive-letter path to its UNC equivalent using 'net use'.
    
    When the SDOH agent runs in an elevated (Admin) process, mapped network drives
    created in a normal user session are invisible. This function queries 'net use'
    to find the real UNC path and rewrites the path so the agent can access the share
    directly via the network stack regardless of elevation level.
    
    Returns the original path unchanged if no mapping is found or it already resolves.
    """
    if not path or len(path) < 2 or path[1] != ':':
        return path
    
    drive_letter = path[0].upper()
    
    # Return immediately if the path is accessible as-is
    try:
        if os.path.exists(path) or os.path.isdir(path):
            return path
    except Exception:
        pass
    
    # Check cache
    if drive_letter in _DRIVE_UNC_CACHE:
        unc_root = _DRIVE_UNC_CACHE[drive_letter]
        if unc_root:
            remainder = path[2:]  # e.g. '\\UV images\\2018'
            return unc_root.rstrip('\\') + remainder
        return path
    
    # Query net use to find the UNC mapping
    try:
        import subprocess
        result = subprocess.run(
            ['net', 'use', f'{drive_letter}:'],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout
        # Match 'Remote name   \\server\share name with spaces' to end of line
        m = re.search(r'Remote name\s+(\\[^\r\n]+)', output)
        if not m:
            m = re.search(r'(\\\S[^\r\n]*)', output)
        if m:
            unc_root = m.group(1).strip()
            _DRIVE_UNC_CACHE[drive_letter] = unc_root
            remainder = path[2:]
            resolved = unc_root.rstrip('\\') + remainder
            return resolved
        pass
    except Exception:
        pass
    _DRIVE_UNC_CACHE[drive_letter] = None  # negative cache
    return path


def local_chat_completions_payload(chat_payload: dict[str, object]) -> dict[str, object]:
    """Build an OpenAI-compatible chat completion directly from local SDOH agent."""
    # Extract sender BEFORE normalising — normalize_input_messages strips the
    # OpenClaw metadata envelope (which carries "sender") from user messages.
    raw_messages = chat_payload.get("messages") or []
    sender_number = _extract_sender_number_from_metadata(raw_messages)

    messages = normalize_input_messages(chat_payload)
    if not messages:
        messages = [{"role": "user", "content": "ping"}]

    # Detect an indexing command from the user
    user_text = raw_messages[-1].get("content", "") if raw_messages else ""
    # Check for various indexing command patterns
    is_indexing_request = any(phrase in user_text.lower() for phrase in [
        "start indexing this folder",
        "show me the indexing status on this folder",
        "index this folder",
        "scan this folder",
        "index folder",
        "scan folder",
    ])
    # Check for vault index query (CT scans 2017 vs 2018, etc.) — any 4-digit year
    is_vault_query = any(phrase in user_text.lower() for phrase in [
        "how many ct scans",
        "how many scans",
        "ct scans in",
        "ct scans were done",
        "scans in",
        "dicom in",
        "records in",
    ]) and bool(re.search(r'\b(19|20)\d{2}\b', user_text))
    if is_indexing_request:
        # Handle various path formats:
        # - Double parentheses: (("X:\UV images\2018")
        # - Single parentheses: ("X:\UV images\2018")
        # - Quoted path: "X:\UV images\2018"
        # - Bare path: X:\UV images\2018
        # - Path with spaces in parentheses: (("X:\UV images\2018")
        m = re.search(r'\(?\(?["\']?([A-Za-z]:\\[^"\')]+)["\']?\)?\)?', user_text)
        if not m:
            m = re.search(r'"([A-Za-z]:\\[^"]+)"', user_text)
        if not m:
            m = re.search(r'([A-Za-z]:\\S+)', user_text)
        folder = m.group(1).strip().rstrip("\"')" ) if m else ""
        if folder:
            # Resolve drive letter to UNC if the path isn't directly accessible
            # (happens when agent runs elevated but the drive was mapped in a normal session)
            original_folder = folder
            unc_folder = _resolve_drive_to_unc(folder)
            if unc_folder != folder:
                folder = unc_folder
            # Do indexing in the background to prevent OpenClaw from timing out
            try:
                vault_status = _query_vault_index_for_folder(original_folder)
                vault_count = vault_status.get('count', 0)
                vault_modalities = vault_status.get('modalities', {})
                
                import threading
                def _bg_scan():
                    try:
                        from backend.sdoh_patient_index import PatientDocumentIndexer
                        indexer = PatientDocumentIndexer()
                        indexer.scan_folder(folder)
                    except Exception as e:
                        print(f"Background indexing error: {e}")
                
                threading.Thread(target=_bg_scan, daemon=True).start()
                
                display_folder = f"{original_folder}" if unc_folder != original_folder else folder
                if unc_folder != original_folder:
                    display_folder += f" (via {unc_folder})"
                
                summary_lines = [
                    f"🚀 Indexing started in the background for: {display_folder}",
                    f"This folder is being scanned and metadata is being extracted. This process may take 10+ minutes for large DICOM folders.",
                ]
                if vault_count > 0:
                    mod_summary = ", ".join(f"{k} ({v})" for k, v in sorted(vault_modalities.items()))
                    summary_lines.append(f"   📊 Vault index: {vault_count} records already indexed here")
                    if mod_summary:
                        summary_lines.append(f"   Modalities: {mod_summary}")
                
                summary = '\n'.join(summary_lines)
            except Exception as exc:
                summary = f"⚠️ Failed to start indexing for {folder}: {exc}"
            
            response_text = f"{summary}\n\nType 'what documents do I have' later to view indexed files."
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    }
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }
    
    # Admin/patient routing from sender number (needed before SIIM routing below).
    sender_digits = re.sub(r"\D", "", sender_number)
    is_admin = sender_digits in _ADMIN_NUMBERS
    user_alias = "Admin" if is_admin else "Patient"

    # ------------------------------------------------------------------
    # SIIM ingest routing — intercept before generic agent call
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # SIIM ingest routing — intercept before generic agent call
    # ------------------------------------------------------------------
    user_text_lower = user_text.lower()
    
    # SIIM INGEST COMMANDS - only "start"/"begin" ingest, or check "status"
    # NOT queries asking to "show"/"list"/"get" SIIM patients
    is_siim_command_start = any(kw in user_text_lower for kw in ['start', 'begin', 'run']) and 'ingest' in user_text_lower and 'siim' in user_text_lower
    is_siim_command_status = any(kw in user_text_lower for kw in ['status', 'progress', 'how far']) and 'siim' in user_text_lower and 'ingest' in user_text_lower
    
    # If it's a SIIM query (show/list/get) even with hackathon keyword, don't route to ingest
    is_siim_query = any(kw in user_text_lower for kw in ['show', 'list', 'get', 'display', 'search for']) and 'siim' in user_text_lower
    
    # Only route to SIIM ingest if it's an ingest command and NOT a query
    is_siim_ingest_cmd = (is_siim_command_start or is_siim_command_status) and not is_siim_query
    
    if is_siim_ingest_cmd:
        try:
            from backend.siim_hackathon import get_ingest_state, start_ingest_job
            # Use a minimal shim so we can call the mixin method standalone
            from backend.sdoh_document_mixin import SDOHDocumentMixin
            class _Shim(SDOHDocumentMixin):
                def _get_indexer(self):
                    try:
                        from backend.sdoh_patient_index import PatientDocumentIndexer
                        return PatientDocumentIndexer()
                    except Exception:
                        return None
            shim = _Shim()
            siim_result = shim._build_siim_ingest_response(user_text, user_alias)
            response_text = siim_result.get('response', '')
            # Enrich status responses with live progress data
            live_state = get_ingest_state()
            live_status = live_state.get('status', 'idle')
            progress = live_state.get('progress', {})
            dicom = live_state.get('dicom', {})
            done_types = [rt for rt, v in progress.items() if v.get('fetched', 0) > 0]
            total_types = len(progress) or 9
            total_fhir = sum(v.get('indexed', 0) for v in progress.values() if isinstance(v, dict))
            if live_status == 'running':
                response_text = (
                    f"⏳ SIIM ingest is running...\n"
                    f"   FHIR resources done: {len(done_types)}/{total_types} types, {total_fhir} records indexed\n"
                    f"   Types completed: {', '.join(done_types) if done_types else 'starting...'}\n"
                    f"   DICOM: {dicom.get('instances_downloaded', 0)} instances downloaded\n"
                    f"Type 'SIIM ingest status' to check again."
                )
            elif live_status == 'completed':
                response_text = (
                    f"✅ SIIM ingest complete!\n"
                    f"   FHIR: {total_fhir} records across {len(progress)} resource types\n"
                    f"   DICOM: {dicom.get('instances_downloaded', 0)} instances downloaded "
                    f"({dicom.get('studies_found', 0)} studies found)\n"
                    f"Type 'show me my SIIM patients' to view the indexed records."
                )
            elif live_status == 'error':
                errors = live_state.get('errors', [])
                response_text = (
                    f"❌ SIIM ingest error: {errors[-1] if errors else 'unknown'}\n"
                    f"Type 'Start full SIIM ingest' to retry."
                )
            # else: keep the response from _build_siim_ingest_response (e.g. 'started' message)
            return {
                "choices": [{"message": {"role": "assistant", "content": response_text}}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "route": "siim_ingest",
            }
        except Exception as exc:
            response_text = f"SIIM ingest command received but handler failed: {exc}"
            return {
                "choices": [{"message": {"role": "assistant", "content": response_text}}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }

    # Check for show_documents commands (can also include SIIM if asking to LIST/SHOW SIIM patients)
    is_asking_to_show = any(t in user_text_lower for t in ['document', 'report', 'show me', 'what do i have', 'list', 'patient', 'search for'])
    
    # ALSO check for patient-specific queries (what is wrong, what has been done, tell me more, etc.)
    # These should query the database for patient details
    is_patient_specific_query = any(phrase in user_text_lower for phrase in [
        'what is wrong', 'what has been done', 'tell me more', 'what studies',
        'what procedures', 'what scans', 'any findings', 'any results',
        'what tests', 'any diagnosis', 'patient details', 'patient information'
    ]) or (
        # Or if asking about a known SIIM patient by name
        any(name in user_text_lower for name in ['siim neela', 'siim ravi', 'siim andy', 'siim sally']) and
        any(verb in user_text_lower for verb in ['what', 'tell', 'show', 'give me'])
    )
    
    # Only exclude from show_documents if it's a SIIM COMMAND (ingest/status) NOT a SIIM query (list/show patients)
    is_siim_command = any(t in user_text_lower for t in ['start', 'ingest', 'status']) and is_siim_ingest_cmd
    
    is_show_documents_cmd = (is_asking_to_show or is_patient_specific_query) and not is_siim_command
    
    print(f"[PROXY DEBUG] Query: {user_text_lower[:60]}")
    print(f"[PROXY DEBUG]   is_asking_to_show={is_asking_to_show}, is_patient_specific={is_patient_specific_query}, is_siim_command={is_siim_command}, is_show_documents_cmd={is_show_documents_cmd}")
    
    if is_show_documents_cmd:
        try:
            from backend.sdoh_document_mixin import SDOHDocumentMixin
            class _Shim(SDOHDocumentMixin):
                def _get_indexer(self):
                    try:
                        from backend.sdoh_patient_index import PatientDocumentIndexer
                        return PatientDocumentIndexer()
                    except Exception as e:
                        print(f"[PROXY] Indexer creation failed: {e}")
                        return None
            
            print(f"[PROXY] Creating shim and calling _build_show_documents_response...")
            shim = _Shim()
            doc_result = shim._build_show_documents_response(user_text, user_alias)
            response_text = doc_result.get('response', '')
            
            print(f"[PROXY] Got response: {response_text[:100] if response_text else 'EMPTY'}")
            print(f"[PROXY] Full result keys: {list(doc_result.keys()) if isinstance(doc_result, dict) else 'NOT A DICT'}")
            
            # Only return if we got a real response (not None/empty)
            if response_text:
                print(f"[PROXY] Returning show_documents response")
                return {
                    "choices": [{"message": {"role": "assistant", "content": response_text}}],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "route": "show_documents",
                }
            else:
                print(f"[PROXY] No response text, falling through to agent")
        except Exception as exc:
            print(f"[PROXY] show_documents error: {exc}")
            traceback.print_exc()
            pass  # Fall through if it fails

    if is_vault_query:
        # Query the vault index for statistics
        # Extract ALL years from the query (handles "2017 vs 2018" etc.)
        years = re.findall(r'\b((19|20)\d{2})\b', user_text)
        years = [y[0] for y in years]  # unwrap tuple groups
        if years:
            # Query for all years and build comparison
            year_stats = []
            for year in years:
                vault_status = _query_vault_index_for_folder(f"X:\\UV images\\{year}")
                vault_count = vault_status.get('count', 0)
                vault_modalities = vault_status.get('modalities', {})
                ct_count = vault_modalities.get('CT', 0)
                year_stats.append((year, vault_count, ct_count, vault_modalities))
            
            if year_stats:
                lines = ["📊 Vault index comparison:"]
                for year, total, ct, mods in year_stats:
                    mod_summary = ", ".join(f"{k} ({v})" for k, v in sorted(mods.items()))
                    lines.append(f"   {year}: {total} total records, {ct} CT scans")
                    if mod_summary:
                        lines.append(f"      Modalities: {mod_summary}")
                
                response_text = '\n'.join(lines) + "\n\nType 'show me the indexing status on this folder ((\"X:\\UV images\\2018\")' to see details."
            else:
                response_text = "No records found in vault index for the specified years."
            
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    }
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }
    
    # Admin/patient routing from sender number (already computed above).

    user_input = ""
    history = []
    # Limit history to last 6 messages (3 exchanges) to prevent context overflow
    # in OpenClaw sessions. The agent already limits recent history internally,
    # but we need to cap it here to prevent the session from becoming too large.
    recent_messages = messages[-6:] if len(messages) > 6 else messages
    for msg in recent_messages:
        role = str(msg.get("role") or "user").lower()
        content = str(msg.get("content") or "")
        if role == "user":
            user_input = content
            history.append({"role": "user", "content": content})
        elif role in {"assistant", "model"}:
            history.append({"role": "model", "content": content})

    if not user_input:
        user_input = "ping"

    # Quick response path for simple requests to avoid loading huge vault index
    # This handles basic greetings and simple queries without full agent initialization
    user_input_lower = user_input.lower().strip()
    is_simple_greeting = any(phrase in user_input_lower for phrase in [
        "hello", "hi", "hey", "ping", "test", "greetings",
        "what can you do", "help", "what do you do"
    ]) and len(user_input) < 50

    if is_simple_greeting:
        # Return a quick response without loading the full agent/vault
        response_text = (
            "I am here and ready to help. I'm your SDOH Patient Continuity Agent.\n\n"
            "I can help you:\n"
            "  1. Index your local medical documents (DICOM, PDF, reports)\n"
            "  2. Find relevant records for upcoming scans or visits\n"
            "  3. Translate clinical reports into plain language\n"
            "  4. Build a doctor-ready history pack for sharing\n"
            "  5. Set up reminders and draft messages to family or carers\n\n"
            "Tell me what you want to do, for example: \"index X:\\UV images\\2019\" or \"show me my documents\"."
        )
        return {
            "id": f"chatcmpl-sdoh-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "sdoh-continuity-v1",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": response_text},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "route": "quick_response",
            "admin_mode": is_admin,
        }

    agent = get_local_sdoh_agent()
    result = agent.chat(
        user_input=user_input,
        history=history[:-1] if history else [],
        current_score=0,
        user_alias=user_alias,
        session_verified=True,
        sender_number=sender_number or None,
        user_role="admin" if is_admin else None,
    )

    response_text = result.get("response", str(result)) if isinstance(result, dict) else str(result)
    response_text = ensure_deliverable_text(response_text, user_hint=user_input)
    prompt_tokens = sum(len((m.get("content") or "").split()) for m in messages)
    completion_tokens = len(response_text.split())

    payload = {
        "id": f"chatcmpl-sdoh-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "sdoh-continuity-v1",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": response_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }

    if isinstance(result, dict):
        for key in [
            "route", "tool_calls", "requested_source_path", "indexing_progress",
            "metadata_summary", "patient_validation_required",
            "patient_validation_verified", "outbound_ready", "admin_mode",
        ]:
            if key in result:
                payload[key] = result.get(key)

    return payload


def should_prefer_local_agent(chat_payload: dict[str, object]) -> bool:
    """Route ALL meaningful requests to local agent (has current code; Flask backend may be stale)."""
    return True


def normalize_input_messages(data: dict[str, object]) -> list[dict[str, str]]:
    messages = data.get("messages")
    if isinstance(messages, list) and messages:
        normalized = []
        for message in messages:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role", "user"))
            content = message.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("type") in {"input_text", "output_text", "text"}
                )
            # Strip OpenClaw metadata from user messages
            if role.lower() == "user":
                content = unwrap_openclaw_metadata(str(content))
            normalized.append({"role": role, "content": str(content)})
        return normalized or [{"role": "user", "content": "ping"}]

    input_value = data.get("input")
    if isinstance(input_value, str):
        return [{"role": "user", "content": unwrap_openclaw_metadata(input_value)}]
    if isinstance(input_value, list):
        normalized = []
        for item in input_value:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "user"))
            content = item.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("type") in {"input_text", "output_text", "text"}
                )
            if role.lower() == "user":
                content = unwrap_openclaw_metadata(str(content))
            normalized.append({"role": role, "content": str(content)})
        return normalized or [{"role": "user", "content": "ping"}]

    return [{"role": "user", "content": "ping"}]


def to_responses_resource(chat_payload: dict[str, object], model: str) -> dict[str, object]:
    choices = chat_payload.get("choices")
    response_text = ""
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            if isinstance(message, dict):
                response_text = str(message.get("content", ""))
    user_hint = str(chat_payload.get("_proxy_user_hint") or "") if isinstance(chat_payload, dict) else ""
    response_text = ensure_deliverable_text(response_text, user_hint=user_hint)

    usage = chat_payload.get("usage") if isinstance(chat_payload.get("usage"), dict) else {}
    input_tokens = int(usage.get("prompt_tokens", 0)) if isinstance(usage, dict) else 0
    output_tokens = int(usage.get("completion_tokens", 0)) if isinstance(usage, dict) else 0

    # Preserve deterministic SDOH routing metadata for tool-aware clients.
    route = chat_payload.get("route")
    tool_calls = chat_payload.get("tool_calls")
    requested_source_path = chat_payload.get("requested_source_path")
    indexing_progress = chat_payload.get("indexing_progress")
    metadata_summary = chat_payload.get("metadata_summary")

    response_payload = {
        "id": f"resp-sdoh-{uuid.uuid4().hex[:8]}",
        "object": "response",
        "created_at": int(time.time()),
        "status": "completed",
        "model": model,
        "output_text": response_text,
        "output": [
            {
                "id": f"msg-{uuid.uuid4().hex[:8]}",
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": response_text,
                        "annotations": [],
                    }
                ],
            }
        ],
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
    }

    if route is not None:
        response_payload["route"] = route
    if isinstance(tool_calls, list):
        response_payload["tool_calls"] = tool_calls
    if requested_source_path is not None:
        response_payload["requested_source_path"] = requested_source_path
    if isinstance(indexing_progress, dict):
        response_payload["indexing_progress"] = indexing_progress
    if isinstance(metadata_summary, dict):
        response_payload["metadata_summary"] = metadata_summary

    return response_payload


@APP.get("/api/sdoh/oc/v1/models")
@APP.get("/api/sdoh/oc/models")
def proxy_models():
    auth_error = require_gateway_auth()
    if auth_error:
        return auth_error
    return jsonify(
        {
            "object": "list",
            "data": [
                {
                    "id": "sdoh-continuity-v1",
                    "object": "model",
                    "created": 1716000000,
                    "owned_by": "stoyanov-radiology",
                }
            ],
        }
    )


@APP.post("/api/sdoh/oc/v1/chat/completions")
@APP.post("/api/sdoh/oc/chat/completions")
def proxy_chat_completions():
    auth_error = require_gateway_auth()
    if auth_error:
        return auth_error

    data = request.get_json(force=True) or {}
    user_hint = extract_user_hint(normalize_input_messages(data))
    # Route directly to local agent to avoid context overflow in OpenClaw sessions
    local_payload = local_chat_completions_payload(data)
    local_payload["_proxy_user_hint"] = user_hint
    local_payload["proxy_fallback"] = "local_agent_preferred"
    return jsonify(local_payload), 200


def _sse_event(event_type: str, data: dict) -> str:
    """Format a single SSE event line-pair."""
    return f"event: {event_type}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


def responses_resource_as_sse(response_payload: dict) -> str:
    """
    Convert a completed Responses-API JSON payload into the minimum SSE event
    sequence that OpenClaw's processResponsesStream expects.
    """
    rid = response_payload.get("id", f"resp-sdoh-{uuid.uuid4().hex[:8]}")
    model = response_payload.get("model", "sdoh-continuity-v1")
    output_items = response_payload.get("output") or []
    item = output_items[0] if output_items else {}
    item_id = item.get("id", f"msg-{uuid.uuid4().hex[:8]}")

    # Extract full text from the first content block
    content_blocks = item.get("content") or []
    text = ""
    if content_blocks:
        text = str(content_blocks[0].get("text", ""))
    if not text:
        text = str(response_payload.get("output_text", ""))

    usage = response_payload.get("usage") or {}
    created_at = response_payload.get("created_at") or int(time.time())

    initial_response = {
        "id": rid,
        "object": "response",
        "created_at": created_at,
        "status": "in_progress",
        "model": model,
        "output": [],
    }
    final_response = {
        "id": rid,
        "object": "response",
        "created_at": created_at,
        "status": "completed",
        "model": model,
        "output": [
            {
                "id": item_id,
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }
        ],
        "usage": usage,
        "output_text": text,
    }

    parts = []
    parts.append(_sse_event("response.created", {"type": "response.created", "response": initial_response}))
    parts.append(_sse_event("response.output_item.added", {
        "type": "response.output_item.added",
        "output_index": 0,
        "item": {"id": item_id, "type": "message", "role": "assistant", "status": "in_progress", "content": []},
    }))
    parts.append(_sse_event("response.output_text.delta", {
        "type": "response.output_text.delta",
        "item_id": item_id,
        "output_index": 0,
        "content_index": 0,
        "delta": text,
    }))
    parts.append(_sse_event("response.output_item.done", {
        "type": "response.output_item.done",
        "output_index": 0,
        "item": {
            "id": item_id,
            "type": "message",
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": text, "annotations": []}],
        },
    }))
    parts.append(_sse_event("response.completed", {"type": "response.completed", "response": final_response}))
    parts.append("data: [DONE]\n\n")
    return "".join(parts)


@APP.post("/api/sdoh/oc/v1/responses")
@APP.post("/api/sdoh/oc/responses")
def proxy_responses():
    auth_error = require_gateway_auth()
    if auth_error:
        return auth_error

    data = request.get_json(force=True) or {}
    model = str(data.get("model", "sdoh-continuity-v1"))
    wants_stream = bool(data.get("stream", False))

    chat_payload = {
        "model": model,
        "messages": normalize_input_messages(data),
        "stream": False,
    }
    user_hint = extract_user_hint(chat_payload.get("messages") or [])

    def _build_response_payload() -> dict:
        """Compute the completed Responses-API payload (non-streaming internally)."""
        local_chat = local_chat_completions_payload(chat_payload)
        local_chat["_proxy_user_hint"] = user_hint
        local_chat["proxy_fallback"] = "local_agent_preferred"
        return to_responses_resource(local_chat, model)

    if wants_stream:
        @stream_with_context
        def generate():
            try:
                response_payload = _build_response_payload()
            except Exception as exc:
                err_payload = {
                    "id": f"resp-sdoh-{uuid.uuid4().hex[:8]}",
                    "object": "response",
                    "status": "failed",
                    "model": model,
                    "output": [],
                    "output_text": f"Proxy error: {exc}",
                }
                response_payload = err_payload

            sse_body = responses_resource_as_sse(response_payload).encode("utf-8")
            yield sse_body

        return Response(
            generate(),
            status=200,
            mimetype="text/event-stream; charset=utf-8",
            direct_passthrough=True,
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # Non-streaming fallback (kept for direct tests / compatibility)
    try:
        response_payload = _build_response_payload()
        return jsonify(response_payload), 200
    except Exception as exc:
        return jsonify({
            "error": {
                "message": f"Proxy fallback failure: {exc}",
                "type": "server_error",
                "trace": traceback.format_exc()[-1200:],
            }
        }), 500


if __name__ == "__main__":
    APP.run(host="127.0.0.1", port=PROXY_PORT, debug=False, use_reloader=False)