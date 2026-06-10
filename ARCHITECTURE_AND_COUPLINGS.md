# Architecture and Couplings Guide

This document explains how the SDOH Chat application is wired, where the backend and frontend meet, and how to extend the system without breaking the existing flow.

The goal is to make the codebase easy to navigate for new contributors. The repo is a Flask application with a browser-based dashboard, plus five main agent experiences:

- Forge: integrity and insight coaching
- Quest: gamified challenge and story flow
- SDOH: continuity, recovery support, local export tooling, document indexing, and WhatsApp integration
- PACS Mentor: radiology infrastructure recovery and tactical continuity walkthroughs
- PACS Continuity: general PACS support sidebar item

## 1. System Overview

The app is a single-page chat dashboard backed by Flask.

At a high level:

1. The browser loads the dashboard HTML and JavaScript modules.
2. The dashboard asks the API for the current user, groups, contacts, and notification state.
3. Clicking a sidebar entry opens a chat thread and loads its history.
4. Sending a message posts to the matching backend route.
5. The route calls the appropriate agent class.
6. The agent returns structured output plus optional helper fields such as timeline items, exports, analytics, and tool-call metadata.
7. The route persists the agent response as a message and returns JSON to the browser.
8. The frontend renders the response and any panel updates.

The code is intentionally split so that:

- Flask owns authentication, persistence, and API shape.
- Agent classes own prompt logic and structured response generation.
- Frontend modules own UI state, rendering, and client-side downloads.

## 2. Backend Architecture

### 2.1 App bootstrap

The app starts in [flask_app.py](flask_app.py).

Key responsibilities:

- Create the Flask app.
- Configure SQLite (database URI `sqlite:///sdoh_chat_v7.db`), CORS, and the secret key.
- Register blueprints under `/api/sdoh/...` and `/api/sdoh/pacs/...` and `/api/sdoh/siim/...`.
- Initialize the database and default groups via `ensure_db_initialized()`.
- Serve the frontend HTML files from `/sdoh/...` routes.
- Explicitly serve static files from `/css/...`, `/js/...`, and `/voices/...`.

This file is the main entrypoint for local development and for understanding how the application is assembled.

### 2.2 Blueprint layout

The backend is organized into blueprints under `backend/routes/`.

Blueprint registration (all under `/api/sdoh`):

- `backend/routes/auth.py` → `/api/sdoh/auth`: login, register, alias, PIN, profile
- `backend/routes/chat.py` → `/api/sdoh`: shared dashboard, message persistence, notifications, deletions
- `backend/routes/agents.py` → `/api/sdoh`: Forge and Quest agent chat endpoints, story publishing, class selection
- `backend/routes/sdoh_routes.py` → `/api/sdoh`: **SDOH agent chat, greeting, document indexing, history packs, and OpenClaw/OpenAI-compatible endpoints**
- `backend/routes/moderation.py` → `/api/sdoh`: content moderation flows
- `backend/routes/voice.py` → `/api/sdoh`: voice upload and transcription paths
- `backend/routes/social.py` → `/api/sdoh`: community and social flows
- `backend/routes/pacs_mentor.py` → `/api/sdoh/pacs`: PACS Continuity Mentor infrastructure recovery endpoints
- `backend/routes/siim_routes.py` → `/api/sdoh/siim`: SIIM Hackathon integration
- `backend/routes/sdoh_auth.py`, `backend/routes/sdoh_contacts.py`, `backend/routes/sdoh_groups.py`, `backend/routes/sdoh_messages.py`: SDOH-specific route modules

**Important architectural note:** The SDOH routes were extracted from `agents.py` into `sdoh_routes.py` to reduce monolithic file size. `sdoh_routes.py` imports `agents_bp`, `sdoh_agent`, `_sdoh_owner_token`, and `_extract_sdoh_turn_from_payload` from `agents.py`, and `agents.py` imports `sdoh_routes` at its bottom — a standard Flask split-file blueprint pattern.

### 2.3 Data model coupling

The main model classes live in [backend/models.py](backend/models.py).

The core entity models are:

- `User`: stores alias, score (integrity_score), PIN hash, quest progress, insights, custom_api_key, user_role, credentials, forge/quest history, inventory, and agent state
- `Message`: stores chat transcript rows with soft-delete support (deleted_at)
- `Group`: stores public/private chat rooms with moderation fields
- `GroupVote`: tracks votes (e.g., for name reverts)
- `GroupMember`: maps users to groups
- `Contact`: stores contact relationships
- `Quest`: stores quest metadata for the Quest agent
- `QuestStory`: stores published stories in the Hall of Heroes
- `NPC`: stores NPC entities per user for the Quest agent
- `QuestSnapshot`: stores turn-based stage snapshots for Quest progress rollback
- `PaymentAllocation`: stores payment allocation drafts from SDOH agent
- `PacsAuditLog`: stores PACS mentor audit trail entries

For the SDOH agent, the important coupling is that `User.quest_progress` is reused as a JSON blob for phase 6 analytics and recovery state. That keeps the implementation lightweight and avoids adding a new table for the current stage.

### 2.4 Agent orchestration

The agent instantiations are split across two files:

**In [backend/routes/agents.py](backend/routes/agents.py):**
- `forge_agent = IntegrityForge(config_path)`
- `quest_agent = FantasyQuestMaster(config_path)`
- `sdoh_agent = SDOHContinuityAgent(config_path)`

**In [backend/routes/pacs_mentor.py](backend/routes/pacs_mentor.py):**
- `pacs_mentor = PACSContinuityMentor()` (instantiated per-request or module-level in pacs_mentor.py)

This means the route layer is the main coupling point between the Flask app and the agent logic.

#### Chat route pattern

Each agent route follows the same basic pattern:

1. Authenticate the user.
2. Load recent message history for the matching chat thread.
3. Read the request content.
4. Call the agent class.
5. Unpack the returned dict.
6. Update the user record and related state (insights, score, payment allocations, etc.).
7. Persist the agent response as a `Message`.
8. Return a JSON payload for the frontend.

### 2.5 SDOH agent internals

The SDOH logic lives in [agent_sdoh.py](agent_sdoh.py), with supporting mixin classes:

- `backend/sdoh_document_mixin.py`: document extraction and parsing
- `backend/sdoh_index_parser_mixin.py`: patient document index parsing
- `backend/sdoh_index_vocab.py`: vocabulary and terminology for indexing
- `backend/sdoh_openclaw_skills.py`: OpenClaw skill definitions
- `backend/sdoh_patient_index.py`: main patient document indexer
- `backend/sdoh_service_mixin.py`: service discovery and integration
- `backend/sdoh_timeline_mixin.py`: timeline construction

Its core responsibilities are:

- classify the user intent into document, continuity, communication, or general support
- detect urgent symptoms and escalate safely
- extract follow-up text from pasted clinical notes
- infer severity and continuity priority
- build timeline items
- generate clinician-facing summaries
- build local export bundles for `.ics` and `PATIENT_PASSPORT.md`
- maintain lightweight analytics signals for phase 6 (stored in `User.quest_progress`)
- operate in admin mode vs. patient device-only mode based on authentication context
- generate payment allocation drafts
- trigger patient-side document indexing and history pack generation
- handle WhatsApp sender number extraction and role-based access
- support OpenClaw/OpenAI-compatible chat completion and responses endpoints

The SDOH agent returns structured dictionaries rather than plain text alone. That structure is what the route and frontend depend on.

### 2.6 PACS Mentor Agent Internals

The PACS Mentor logic lives in [backend/agent_pacs.py](backend/agent_pacs.py).

Its core responsibilities are:

- **Optical Authorization**: Mandatory verification of the physical "Emergency Operational Continuity Directive" using Tesseract OCR.
- **Incident State Machine**: Tracking recovery through stages: DETECTED → TRIAGED → HYPOTHESIS_FORMED → VERIFIED → MITIGATED → RESOLVED → ESCALATED.
- **Passive Discovery**: Using Scapy for ARP sniffing to identify vendor hardware (GE, Cisco, VMware) on the local network.
- **Recovery Logging**: Append-only logging of triage steps to `INFRASTRUCTURE_RECOVERY_LOG.md`.
- **PACS Export Artifacts**: Generation of export bundles via `backend/pacs_exports.py`.
- **Continuity Registry**: State tracking through `backend/pacs_registry.py`.

Helper files:

- `backend/pacs_exports.py`: generates PACS export artifacts
- `backend/pacs_registry.py`: PACS continuity state registry

### 2.7 OpenClaw / OpenAI-compatible endpoints

The SDOH agent exposes OpenAI-compatible endpoints under `/api/sdoh/oc/` for integration with the OpenClaw WhatsApp gateway:

- `GET /api/sdoh/oc/v1/models`: model discovery (`sdoh-continuity-v1`)
- `POST /api/sdoh/oc/v1/chat/completions`: OpenAI Chat Completions-compatible
- `POST /api/sdoh/oc/v1/responses`: OpenAI Responses-compatible

These endpoints are authenticated via `SDOH_OWNER_TOKEN` (environment variable or `[PACS_SECURITY]` section of `config.ini`). They extract WhatsApp sender numbers from session keys and route messages through the same `sdoh_agent.chat()` pipeline, using role-based access for admin vs. patient flows.

### 2.8 Document indexing API

The SDOH agent exposes patient-side document indexing endpoints:

- `POST /api/sdoh/sdoh/index-documents`: scan a folder or all default directories
- `GET /api/sdoh/sdoh/my-documents`: retrieve full document index (metadata only, no file content) with optional filters for modality, body_part, doc_type, and text search
- `POST /api/sdoh/sdoh/history-pack`: build a patient-approved history pack for sharing with a practice (returned as markdown, never uploaded)

## 3. Frontend Architecture

### 3.1 Frontend file layout

The frontend lives under [frontend/](frontend/).

Primary HTML files:

- [frontend/dashboard.html](frontend/dashboard.html): main dashboard shell with chat, SDOH continuity panel, Quest Board, Forge/Quest panels, Hall of Heroes, Insights modal, Settings modal, and class selection modal
- [frontend/index.html](frontend/index.html): sign-in and sign-up page
- [frontend/pacs_mentor.html](frontend/pacs_mentor.html): dedicated PACS mentor interface

JavaScript modules under [frontend/js/modules/](frontend/js/modules/):

- [main.js](frontend/js/modules/main.js): dashboard loading, sidebar rendering, notification polling
- [ui.js](frontend/js/modules/ui.js): chat open/close behavior, settings, modals, panel toggles, PACS mentor interface
- [chat.js](frontend/js/modules/chat.js): message sending, loading, greetings, SDOH export rendering, Quest data rendering, Hall of Heroes rendering
- [api.js](frontend/js/modules/api.js): authenticated fetch wrapper
- [utils.js](frontend/js/modules/utils.js): shared browser utilities (escapeHtml, etc.)
- [config.js](frontend/js/modules/config.js): frontend configuration constants
- [contacts.js](frontend/js/modules/contacts.js): contact list loading and rendering
- [forge.js](frontend/js/modules/forge.js): Forge-specific panel updates and rendering
- [tts.js](frontend/js/modules/tts.js): text-to-speech engine (ElevenLabs + browser native)
- [voice_input.js](frontend/js/modules/voice_input.js): voice recording and transcription

### 3.2 Frontend boot sequence

The browser flow starts after login and dashboard load.

Sequence:

1. `main.js` calls `/dashboard` through `fetchWithAuth`.
2. The dashboard payload populates `window.currentUser`, `window.allGroups`, and `window.aliasColors`.
3. `renderGroups()` builds the sidebar entries.
4. `loadContacts()` and notification polling start.
5. When a user opens a thread, `ui.js` changes the visible panel and `chat.js` loads the thread history.

### 3.3 Global state coupling

The frontend uses a small set of global browser variables as its coordination layer.

Important globals:

- `window.currentUser`: active user profile and score data
- `window.allGroups`: group list for sidebar rendering
- `window.aliasColors`: per-letter alias color state
- `window.unreadCounts`: unread badge state by chat ID
- `window.currentGroup`: active chat target
- `window.API_BASE`: API root for authenticated requests
- `window.token`: current JWT token

This is a deliberate coupling choice. The modules are separate files, but the dashboard runtime is still a shared browser context.

## 4. Backend to Frontend Couplings

This section is the most important part of the document.

### 4.1 Dashboard payload coupling

The frontend expects the dashboard API to return:

- `user`
- `groups`
- likely any additional profile or score fields used by panels

The dashboard loader in `main.js` stores that payload in globals and immediately renders the group list.

If the backend changes the dashboard response shape, the sidebar and panels can break quickly.

### 4.2 Message history coupling

The chat loader in `chat.js` expects message objects to contain:

- `msg_id`
- `sender_id`
- `sender_alias`
- `content`
- `created_at`

Some message rendering is specialized:

- Quest messages can contain `[QUEST_DATA]` payloads that are parsed as JSON for quest card rendering.
- SDOH messages can include export bundle information returned from `/sdoh/chat`.

### 4.3 Agent response coupling

The browser does not just read `response` text. It also uses structured fields returned by the agent routes.

Forge currently uses:

- `response`
- `score`
- `insights`
- `verified`

Quest currently uses:

- `response`
- `score`
- `insights`
- `inventory`
- `active_quest_id`
- `quest_posted`
- `quest_name`
- `choices`
- `story_published`

SDOH currently uses (all fields from the `/api/sdoh/sdoh/chat` response):

- `response`
- `phase`
- `score`
- `confidence`
- `verified`
- `verification_required`
- `timeline_items`
- `draft_message`
- `barrier_type`
- `barrier_classification`
- `source_paragraph`
- `extracted_task`
- `anatomy`
- `modality`
- `timeline`
- `severity`
- `continuity_priority`
- `clinician_summary`
- `missed_window_reclamation`
- `patient_validation_required`
- `patient_validation_verified`
- `outbound_ready`
- `route`
- `tool_calls`
- `requested_source_path`
- `indexing_progress`
- `metadata_summary`
- `whatsapp_scope`
- `whatsapp_access`
- `assistant_number`
- `detected_exports`
- `detected_assistant_sources`
- `admin_mode`
- `patient_device_only`
- `whatsapp_number`
- `payment_allocation_draft`
- `payment_allocation_id`
- `export_bundle`
- `export_ready`
- `calendar_events`
- `calendar_filename`
- `ics_content`
- `passport_filename`
- `passport_markdown`
- `schema_notes`
- `analytics`
- `demo_case`

PACS Mentor currently uses:

- `response`
- `status` (Incident State)
- `progress` (Percentage)
- `current_step` (Tactical guidance)
- `details` (OCR validation info)

If you add a new SDOH field in the backend, you should add it to the route response in `backend/routes/sdoh_routes.py` and then decide whether the frontend actually needs to render it.

### 4.4 SDOH panel coupling

The SDOH panel in `dashboard.html` is populated by the render helpers in `chat.js`.

Those helpers expect these DOM IDs:

- `sdoh-summary`
- `sdoh-timeline-list`
- `sdoh-analytics`
- `sdoh-status-text`
- `sdoh-bar`
- `sdoh-export-flag`
- `sdoh-guardrail`
- `sdoh-download-ics`
- `sdoh-download-passport`
- `sdoh-copy-summary`

The backend export bundle is stored in `localStorage` and then rendered into this panel via `updateSdohPanel()`.

### 4.5 Sidebar coupling

The sidebar list in `main.js` is built from `window.allGroups` plus a hard-coded private chat section.

The current private chat entries are (5 items):

- FORGE → `forge_{user_id}`
- QUEST → `quest_{user_id}`
- SDOH NAVIGATOR → `sdoh_{user_id}`
- PACS CONTINUITY → `pacs_{user_id}`
- HALL OF HEROES (opens a modal, no chat ID)

The group IDs for private agents are hard-coded by convention:

- `forge_{user_id}`
- `quest_{user_id}`
- `sdoh_{user_id}`
- `pacs_{user_id}`

This convention matters because the message loader and notification logic rely on it.

## 5. Agent-Specific Request Flows

### 5.1 SDOH Request Flow

#### User flow

When the user opens SDOH Navigator and sends a message:

1. `sendMessage()` in `chat.js` detects the active group ID matches `sdoh_{user_id}`.
2. It dispatches to `sendToSdoh(text)`.
3. `sendToSdoh()` posts to `/api/sdoh/sdoh/chat`.
4. The backend route in `sdoh_routes.py` calls `sdoh_agent.chat()`.
5. The agent decides whether the message is urgent, a document extract, a continuity request, a communication request, a general prompt, or an admin tool invocation.
6. The backend returns structured metadata plus an export bundle, analytics, and optionally payment allocation drafts.
7. The frontend renders the reply bubble and calls `updateSdohPanel()` to refresh the SDOH continuity panel.
8. If export content is ready, the user can download `.ics` and `PATIENT_PASSPORT.md` locally.

### 5.2 Document flow

If the text looks like a pasted clinical note or radiology report:

- `agent_sdoh.py` tries `_build_extraction_result()` via the document mixin.
- That creates a source paragraph, extracted task, confidence level, anatomy, modality, and timeline data.
- The route returns the structured extraction fields.
- The frontend shows the draft message and export state if approved.

### 5.3 Rescue flow

If the message looks like a missed high-risk follow-up:

- the agent raises severity to `critical` or `high`
- the continuity priority engine computes the priority tier
- missed-window reclamation can mark the timeline items as blocked
- analytics counters increment to reflect the rescue event

### 5.4 Export flow

Approved items are converted into local artifacts:

- `calendar_events` for timeline records
- `ics_content` for download
- `passport_markdown` for `PATIENT_PASSPORT.md`
- `schema_notes` for interoperability guidance

These artifacts are produced by the backend and then cached in the browser for local download.

### 5.5 WhatsApp / OpenClaw flow

External messages arrive through the WhatsApp Cloud API → OpenClaw gateway:

1. OpenClaw forwards the message to `/api/sdoh/oc/v1/chat/completions` or `/api/sdoh/oc/v1/responses`
2. The endpoint authenticates via `X-SDOH-Owner-Token` or `Authorization: Bearer` header
3. Sender number is extracted from `X-Openclaw-Session-Key` or message body
4. Role is determined: admin numbers get admin mode, owner numbers get full verification, unknown numbers get patient mode
5. The same `sdoh_agent.chat()` pipeline processes the message
6. Response text and metadata are returned in OpenAI-compatible format

### 5.6 Document indexing flow

Patients can index their local medical documents:

1. `POST /api/sdoh/sdoh/index-documents` triggers `indexer.scan_folder()` or `indexer.scan_all_default_dirs()`
2. The indexer parses DICOM metadata, PDFs, images, and text files
3. Results are stored in the in-memory patient index (`sdoh_patient_index.py`)
4. `GET /api/sdoh/sdoh/my-documents` returns the indexed metadata (filenames only, no paths or content)
5. `POST /api/sdoh/sdoh/history-pack` builds a markdown summary for sharing with healthcare providers (patient-controlled)

## 6. Frontend File Couplings

### 6.1 [frontend/js/modules/main.js](frontend/js/modules/main.js)

This file owns dashboard startup and sidebar rendering.

Depends on:

- `fetchWithAuth` from `api.js`
- `renderGroups` from the same file
- `loadContacts` from the contacts module
- `openForgeChat`, `openQuestChat`, `openSdohChat`, `openPacsChat`, and `openHallOfHeroes` from `ui.js`

If you change chat IDs or group display names, this is one of the first files that needs updating.

### 6.2 [frontend/js/modules/ui.js](frontend/js/modules/ui.js)

This file owns view switching and panel visibility.

Depends on:

- DOM IDs in `dashboard.html`
- `loadMessages()` from `chat.js`
- `updateForgePanel()` and `updateQuestPanel()` from panel-specific modules

For SDOH and PACS it now owns:

- `openSdohChat()` and `openPacsChat()`
- hiding and showing the continuity and recovery panels

### 6.3 [frontend/js/modules/chat.js](frontend/js/modules/chat.js)

This file owns message fetching, rendering, greetings, SDOH export controls, Quest data rendering, and Hall of Heroes rendering.

Depends on:

- `fetchWithAuth()` for API calls
- `escapeHtml()` from `utils.js`
- `startTTS()` from the TTS module
- panel DOM nodes from `dashboard.html`

The most important couplings here are the response JSON shapes from the backend routes.

### 6.4 [frontend/dashboard.html](frontend/dashboard.html)

This file is the live DOM contract.

If you rename an element ID here, you must update the corresponding JavaScript selector.

The SDOH continuity panel and PACS recovery panel are especially coupled to the IDs listed earlier.

### 6.5 [frontend/js/modules/forge.js](frontend/js/modules/forge.js)

Owns Forge-specific panel rendering and score/insight updates.

### 6.6 [frontend/js/modules/tts.js](frontend/js/modules/tts.js)

Owns the text-to-speech engine, supporting both ElevenLabs API and browser-native speech synthesis.

### 6.7 [frontend/js/modules/contacts.js](frontend/js/modules/contacts.js)

Owns contact list loading and rendering for the contacts panel.

## 7. What Changes Usually Touch What

### 7.1 Adding a new SDOH or PACS field

Typical edit path:

1. Add the field to the agent result in `agent_sdoh.py` or `agent_pacs.py`.
2. Pass it through the route in `backend/routes/sdoh_routes.py` (for SDOH) or `backend/routes/pacs_mentor.py` (for PACS).
3. Render it in `frontend/js/modules/chat.js` if the UI needs it.
4. Add or update the relevant DOM node in `frontend/dashboard.html`.

### 7.2 Adding a new sidebar item

Typical edit path:

1. Add the entry in `frontend/js/modules/main.js` (the `renderGroups()` function).
2. Add the open function in `frontend/js/modules/ui.js`.
3. Make sure `sendMessage()` in `chat.js` knows how to route messages for that group.

### 7.3 Adding a new agent endpoint

Typical edit path:

1. Create or update the agent class.
2. Add a blueprint in `backend/routes/` (either a new file or extend an existing one).
3. Register the blueprint in `flask_app.py`.
4. Update the frontend sender (`sendMessage`) and loader paths.

### 7.4 Adding a new OpenClaw-compatible endpoint

Typical edit path:

1. Add a route to `backend/routes/sdoh_routes.py` under the `agents_bp` blueprint.
2. Use `_sdoh_owner_token()` for authentication.
3. Call `_extract_sdoh_turn_from_payload(data)` to parse the OpenClaw/OpenAI payload.
4. Route through `sdoh_agent.chat()`.
5. Return OpenAI-compatible JSON.

## 8. Contributor Workflow

Use this sequence when you make changes:

1. Find the exact backend or frontend surface you are changing.
2. Trace the request or event flow end to end.
3. Edit the smallest file set that preserves the coupling contract.
4. Run a syntax or runtime validation for the touched slice.
5. Update this guide if the shape of the system changed.

Recommended validation order:

1. Python syntax or route test for backend changes.
2. Frontend module syntax check for JS changes.
3. Route-level live test for SDOH behavior.
4. Browser-level verification for panel rendering and downloads.

## 9. Common Pitfalls

- Changing a backend response field without updating the frontend renderer.
- Renaming a hard-coded group ID and forgetting the notification or message dispatch branch.
- Adding a new DOM node without a matching selector in `chat.js` or `ui.js`.
- Treating `quest_progress` as quest-only state now that SDOH analytics also live there.
- Returning plain text from an agent when the route and UI expect structured fields.
- Modifying the SDOH route response shape in `sdoh_routes.py` without updating the corresponding default values in the `else` fallback branch (lines 182–220).
- Forgetting that `agents.py` and `sdoh_routes.py` are circularly imported — new symbols needed in `sdoh_routes.py` must be defined before the bottom-of-file import.

## 10. Current Status Snapshot

As of the latest implementation pass:

- Forge and Quest remain intact with their own routes in `agents.py`.
- SDOH has its own chat route, greeting, extraction path, document indexing API, local exports, analytics, and payment allocation drafts — all extracted to `backend/routes/sdoh_routes.py`.
- SDOH exposes three OpenClaw/OpenAI-compatible endpoints under `/api/sdoh/oc/` for WhatsApp gateway integration.
- SDOH supports patient-side document indexing with scan, search, and history pack generation.
- The dashboard contains an SDOH continuity panel with live analytics, export downloads, and summary copy functionality.
- Approved SDOH items can be exported locally as `.ics` and `PATIENT_PASSPORT.md`.
- PACS Mentor has its own blueprint under `/api/sdoh/pacs/` with full incident state machine, optical authorization, and audit logging.
- Five sidebar items: Forge, Quest, SDOH Navigator, PACS Continuity, and Hall of Heroes.
- Frontend JS modules include specialized files for config, contacts, forge panel, TTS, and voice input.
- WhatsApp sender number extraction and role-based access control are integrated across SDOH and PACS agents.

If you extend the system, keep the backend route, agent response shape, and frontend render code aligned.