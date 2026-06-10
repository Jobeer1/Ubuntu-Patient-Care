# SDOH Agent Plan

## 1. Purpose
Create a third conversational agent focused on Social Determinants of Health support for patients recovering after diagnoses. The agent should behave like a patient-owned portal in the patient's pocket, help users stay organized, reduce missed care, keep medical data on the patient's own devices, let patients index their own DICOM images, reports, and scripts locally, validate the right patient before any handoff, and act as a secure local bridge between patient sovereignty and regulated practice-side exchange.

## 2. Core Use Cases
- Appointment reminders and preparation checklists.
- Patient-owned document triage for local DICOM images, reports, and scripts before a scan or visit.
- Patient-side document indexing and retrieval so the agent can surface the most relevant history by study date, body part, modality, or clinician note before a doctor visit.
- Patient-owned sovereign vault storage so reports, prescriptions, summaries, and study metadata live on patient hardware or trusted local storage.
- Practice-facing inbound validation so clinician payloads are matched to the correct patient before anything enters the local index.
- Transport coordination messages for family, friends, or caregivers.
- Trusted Circle Coordination: assign caregiver roles, manage ride coordination, support medication pickup, track appointment companions, and route fallback contacts.
- Follow-up task tracking after a diagnosis or procedure.
- Patient validation before any release of reports, personal DICOM images, account statements, or billing documents.
- Patient-safe report review, personal image handoff drafting, and account/statement explanation.
- Local interoperability handoff for patient-approved summaries, timelines, and passport exports into practice-side systems.
- Supportive recovery communication that encourages reaching out to trusted people without framing the agent as therapy.
- Simple recovery guidance that stays within support and navigation, not diagnosis or treatment decisions.
- Multimodal Document Digestion: Ingest raw, unstructured clinical data drops such as medicine scripts, blood lab panels, and radiology free-text reports via local file system nodes, then transform them into plain-language recovery guidance.
- Local Document Pack Builder: when the user mentions a scan, follow-up, or clinic visit, identify the most relevant local records to bring or share and explain why they matter without moving them off the patient device.
- Local Patient Index: build a searchable device-local index of patient-owned files so the agent can quickly find prior studies, reports, scripts, and summaries without uploading them to a cloud service.
- Local Switchboard Routing: Automatically funnel approved updates directly to specific family communication channels without risking multi-tenant data cross-contamination.
- Health Literacy Translation: Simplify radiology language, lab abnormalities, and next-step timelines while preserving source traceability and avoiding diagnosis.

## 3. Persona Requirements
- Warm, practical, and patient-first.
- Clear and low-friction language.
- Encouraging without sounding clinical or robotic.
- Focused on next steps the patient can actually take today.
- Able to draft short messages the user can send to family, caregivers, or clinic staff.

## 4. Safety and Scope Boundaries
- Do not replace a clinician.
- Do not diagnose, prescribe, or give treatment instructions.
- If the user describes urgent symptoms, encourage immediate clinical help or emergency services.
- Keep the agent helpful for organization, communication, and recovery support.
- Avoid shame-based language or anything that increases stress.
- Never release a report, image, statement, or account summary to an unvalidated patient context.
- Outbound drafts stay draft-only until the patient explicitly confirms the correct identity and destination.

## 5. Proposed Features

### 5.1 Patient Recovery Support
- Create reminder plans for medication, visits, labs, and follow-ups.
- Help users break post-diagnosis tasks into small steps.
- Offer checklists for what to bring to an appointment.
- Summarize questions the patient may want to ask their care team.

### 5.2 Family and Caregiver Communication
- Draft transport requests.
- Draft emotionally supportive messages when the patient needs help asking for support.
- Draft short updates to family after appointments, only if the patient wants them.
- Offer message templates that can be copied and edited.

### 5.3 Recovery Coordination
- Track upcoming appointments and reminders.
- Help the user plan travel time and preparation time.
- Encourage the user to identify one trusted person who can help when needed.
- Translate discharge and imaging follow-up instructions into plain-language next steps.

### 5.4 Role Separation by Function
- Care Navigator: reminders, preparation checklists, and day-of-care planning.
- Family Coordinator: communication drafts, ride planning, and trusted-circle coordination.
- Document Interpreter: plain-language summaries of reports, labs, and discharge instructions.
- Recovery Tracker: milestone monitoring, follow-up status, and barrier logging.

### 5.5 OpenClaw Native Automation Hooks
- Automated .ics Generation: The agent outputs structured date arrays that generate a local calendar file for the patient to download or sync natively to a mobile device.
- Headless Communication Handshake: Integrate with OpenClaw-native messaging capabilities, including WhatsApp/Signal allow-list controllers, to safely stage outbox drafts.
- OpenClaw WhatsApp anchor: support the operator number `+27663764491` as the initial WhatsApp integration target for SDOH continuity handoff and draft staging.
- OpenClaw SDOH WhatsApp config: maintain an example bridge file that binds the WhatsApp channel to the SDOH continuity agent and keeps owner-only elevated tools limited to the operator number.
- Portable Patient Passport: Produce a one-click markdown export named PATIENT_PASSPORT.md summarizing active drug timelines, appointment schedules, and SDOH barriers so a visiting surgeon or care coordinator can understand the patient in under 30 seconds.
- Local Connectivity Onboarding: when the admin operator logs in as `0768193339`, the first greeting should ask which local apps, VMs, databases, DICOM stores, or billing sources need to be connected and what read-only access or patient-matching keys are available.
- OpenClaw SDOH Continuity Skill: maintain an allowlisted `sdoh-continuity` skill package that teaches the agent how to request source details, preview DICOM metadata, and index local databases without guessing or writing to the source systems.

## 6. Product Design Goals
- Keep the interaction simple enough for patients who are tired, stressed, or not technically confident.
- Make the first response useful immediately.
- Prefer short structured outputs over long essays.
- Zero-Friction Audio Accessibility: Leverage OpenClaw mobile nodes to support raw local audio streaming, using Whisper-STT to parse incoming voice notes and local neural TTS to read insights aloud, bypassing technical literacy or manual typing blocks entirely for exhausted users.
- Reduce post-diagnosis cognitive load by breaking complex instructions into short, actionable steps.

## 6.1 Clinical Trust Safeguards
- Always cite the originating report section or discharge note when generating a reminder or summary.
- Preserve source traceability for every extracted instruction.
- Distinguish clinician instructions from AI-generated organization support.
- Never alter clinical findings or reinterpret them as diagnoses.
- Require explicit patient approval before any outbound communication is sent.

## 7. Technical Integration Plan

### 7.1 Backend
- Add a new agent class for the SDOH persona.
- Add a deterministic patient-owned document triage branch so short prompts like "I need a CT scan" return a local document pack checklist instead of forcing pasted-report extraction.
- Add a patient-side indexing and retrieval layer for local files so the agent can search device-held documents by modality, date, body part, and note content.
- Keep the SDOH chat route at `/api/sdoh/chat` and the greeting route at `/api/sdoh/greeting` so the frontend can reach them without a path mismatch.
- Make Gemma 2B the primary Ollama model and Gemini the fallback for continuity guidance.
- Reuse the existing message persistence, history, and insight patterns where useful.
- Add patient-validation state and outbound-release gating before any report, image, account, or statement handoff.
- Add practice-facing export hooks that stay local-first so a clinic or hospital can consume the patient-approved summary through local applications without requiring the patient to retype history.

### 7.2 Frontend
- Add a new private chat entry in the dashboard sidebar.
- Add a greeting/loading path for the SDOH agent.
- Reuse the existing chat UI, TTS, and auth flow.
- Make the UI labels clearly distinguish this agent from Forge and Quest.
- Present the SDOH experience as a private guarded portal centered on continuity and recovery, not as a general-purpose chat or therapy interface.
- For the admin operator, the greeting should explicitly ask what needs to be connected first: VM, app, database, DICOM source, billing source, or patient registry.

### 7.3 Data, Memory, and Sovereign Architecture
- Air-Gapped Operation: bind the data lifecycle entirely to the host's local area network environment.
- Sovereign Vault Storage: persist reports, prescriptions, summaries, and handoff artifacts in a patient-owned local vault such as ~/.openclaw/vault/ rather than in transient chat state.
- Local DICOM and Text Indexing: extract metadata from DICOM headers and key terms from local free-text reports so study date, modality, anatomy, and timeline are searchable without cloud upload.
- Local Parser Nodes: use lightweight local wrappers for pydicom, OCR, and regex parsing so raw images and scripts can be indexed by local tooling before the agent reasons over them.
- Verification Gate: require explicit patient matching or operator handoff validation before any inbound clinical document is appended to the patient's local history.
- Zero-Cloud Cross-Contamination: ensure practice-to-patient transfer terminates on patient device storage or trusted local infrastructure, not a shared multi-tenant database.
- Primary local inference: use Ollama running Gemma 2B for SDOH first, then fall back to Gemini only when local inference is unavailable.
- Patient-Owned Search: create indexes and metadata caches on patient devices so documents can be found quickly without uploading the source files.
- Isolated Session Snapshotting: persist chat states strictly using OpenClaw's local markdown log mechanics in ~/.openclaw/workspace so patient data remains under the direct, physical ownership of the family.
- Local-First Sovereignty: position the system as a patient-owned continuity layer that keeps clinical coordination inside the family's trusted infrastructure.
- Patient-Identity Safety: never let a summary, image, or statement leave the chat unless the patient context has been validated for that specific handoff.

### 7.4 Prompt-Routed Sub-Agent Model
- Allow the SDOH persona to route internally between care navigator, family coordinator, document interpreter, and recovery tracker behaviors.
- Add a patient-validation branch so the agent can distinguish review, draft, and outbound-release requests.
- Add a vault-intake branch so the agent can ingest locally stored reports, DICOM studies, and scripts through verified local file reads instead of chat-only prompts.
- Add a handoff-packaging branch so the agent can produce a patient passport, targeted history summary, or practice-facing interoperability export from local data only.
- Add an operator-onboarding branch for local app and database discovery so `0768193339` is prompted for the exact VM, source, and indexing details before any integration is attempted.
- Add a patient-device document retrieval branch so the agent can answer "what should I bring to the doctor?" by querying the local index rather than asking the patient to manually hunt through folders.
- Keep this as prompt routing unless a later implementation phase requires dedicated service boundaries.
- Use the routed mode to keep the system enterprise-like without adding unnecessary UI complexity.

## 8. Suggested Prompt Structure
- Identity: patient-owned care continuity orchestration agent.
- Mission: help patients stay on track after diagnoses and reduce post-discharge cognitive overload.
- Output style: short, practical, action-oriented.
- Common tools: reminders, draft messages, checklists, follow-up questions, document summaries.
- Escalation: urgent symptom safety notice when needed.

## 9. Implementation Phases
1. Define the exact persona and output format.
2. Add the backend SDOH agent class.
3. Add the new route and greeting endpoint.
4. Add the frontend chat entry and UI labels.
5. Test reminder drafting, family message drafting, and safety escalation.
6. Refine prompts based on real usage.
7. Wire the WhatsApp/OpenClaw handoff once the local agent path is stable and patient-identity checks are passing.

## 10. Open Questions
- None remaining for the current planning pass. The design choices below are now treated as fixed requirements for implementation.
- Reminders persist locally in REMINDERS.md and can be monitored by the local heartbeat workflow.
- Outbound messages are draft-only until the patient explicitly approves them.
- The agent appears as a private guarded portal while optionally writing silent continuity updates into quest_progress_update.
- Only active lifecycle context is retained across sessions; resolved barriers are pruned to prevent bloat.
- Missed-Window Reclamation: if the local heartbeat detects that a high-risk timeline event was missed while a host device or LAN node was offline, the system bypasses the standard queue and raises an immediate high-priority, voice-first UI notification when the patient next wakes the screen.

## 11. Clinical Outcome Targets
Expected Operational Impact:
- Reduce missed imaging follow-ups.
- Reduce no-show rates for oncology and radiology appointments.
- Improve medication adherence after discharge.
- Improve care-plan comprehension.
- Reduce caregiver coordination friction.
- Reduce post-discharge confusion.
- Improve continuity for rural or offline patients.

Continuity metrics:
- Reminder acknowledgment rate.
- Follow-up completion rate.
- Transport coordination success rate.
- Caregiver engagement frequency.
- Missed follow-up rescue count.

## 12. Imaging Follow-Up Rescue Flow
1. Radiology report detects a suspicious lesion or required follow-up.
2. The agent identifies that a follow-up imaging study or clinic action is needed.
3. The patient misses scheduling, forgets a date, or faces a transport barrier.
4. The agent detects the blocker through reminders, local document digestion, or support input.
5. The agent generates a simplified explanation, a reminder flow, a caregiver coordination draft, and local support suggestions.
6. The agent logs the continuity action as a measurable care-support outcome.

### 12.1 Continuity Priority Engine
- Prioritize high-risk missed follow-ups first.
- Escalate unresolved critical imaging pathways.
- Reduce reminder overload for low-risk events.
- Use severity tiers such as critical, high, moderate, and low to reduce alert fatigue and make follow-up logic clinically realistic.

### 12.2 Continuity Timeline
- Render care states as completed, upcoming, blocked, missed, awaiting transport, and awaiting lab.
- Give patients and care coordinators a recovery map instead of a flat task list.
- Show the timeline as a continuity view that makes care fragmentation visible at a glance.

### 12.3 Barrier Classification
- Transport: no ride or unreliable transit.
- Financial: medication cost or appointment cost.
- Cognitive: confusion, overwhelm, or memory failure.
- Social: no caregiver or weak support network.
- Infrastructure: offline, rural, or device-limited access.
- Scheduling: conflicting appointments or poor appointment access.
- Use these categories as structured SDOH observability fields.

### 12.4 Clinician-Facing Continuity Summary
- Generate a care continuity snapshot for clinicians or care coordinators.
- Example: patient missed two imaging scheduling attempts due to transport instability and caregiver unavailability.
- Keep the summary concise, factual, and useful for handoff or follow-up planning.

### 12.5 Explainable Extraction Pipeline
- Source paragraph: preserve the original text span from the report or discharge note.
- Extracted task: show the specific follow-up or action that was identified.
- Confidence level: indicate whether the extraction is high, medium, or low confidence.
- Anatomical and timeline stability: confidence must automatically downgrade when the model cannot confidently link the task to a specific anatomy, modality, or date window.
- Human verification: require confirmation when the output affects outbound communication, shared planning, or generation of an .ics reminder.
- Safety gate: do not allow caregiver drafts or calendar generation until the confidence state is high, or medium/low with explicit human verification.

### 12.6 Interoperability Layer
- Support local file exports that can map to DICOM SR, HL7 FHIR, SMART-on-FHIR, and DICOMweb concepts even if the initial implementation is mocked.
- Keep interoperability language explicit so the system reads as standards-aware and SIIM-aligned.
- Use local markdown, calendar, and structured export formats as the first implementation step.
- Add local index metadata that practice applications can consume so the patient can share a curated history packet into local EMR or PACS workflows without cloud transfer.
- Add code comments and schema notes that map Markdown fields directly to clinical interoperability concepts: barrier classification fields map to FHIR Condition and Observation resources using standard SDOH coding patterns, and PATIENT_PASSPORT.md task states map to FHIR CarePlan and ServiceRequest resources.
- Treat the local markdown layer as an implementation detail that can later be serialized into enterprise EMR-facing resources without changing the core patient workflow.
- Enforce patient-side export packaging so only validated local records are included in practice-facing bundles.

### 12.7 Measurable Analytics
- Track reminder acknowledgment rate.
- Track follow-up completion rate.
- Track transport coordination success.
- Track caregiver engagement frequency.
- Track missed follow-up rescue count.
- Use the analytics to make the system research-ready, deployment-ready, and evaluatable.

### 12.8 Demo Scenario
1. Patient receives a suspicious lung CT result.
2. A follow-up PET scan is required.
3. The patient misses scheduling because of transport instability.
4. The SDOH agent detects the continuity risk.
5. The agent generates a simplified summary, a ride coordination draft, an appointment timeline, and a caregiver notification draft.
6. The follow-up is completed successfully after the continuity workflow closes the loop.

## 13. Actionable Work Breakdown

### 13.1 Phase 1 - Backend Agent Skeleton
- [ ] Create a new SDOH agent class file with a recovery-focused prompt.
- [ ] Add patient-owned document guidance for short scan and visit prompts so the agent recommends the right local files before the doctor visit.
- [ ] Add a patient-side document indexer for local DICOM images, reports, scripts, and summaries.
- [ ] Load the local health graph or vault index on startup instead of relying only on recent chat history.
- [ ] Keep the route mapping aligned with the frontend at `/api/sdoh/chat` and `/api/sdoh/greeting`.
- [ ] Add a greeting endpoint for the SDOH persona.
- [ ] Reuse the existing auth, history, and message persistence flow.
- [ ] Make Gemma 2B the primary local model and Gemini the fallback.

Exit criteria:
- The backend can return a basic SDOH response for a test message.
- The backend can also turn a scan prep prompt into a local-only document checklist without pretending to move data off the patient device.
- The backend can also identify and rank patient-held records using local metadata.

### 13.2 Phase 2 - Clinical Extraction and Safety Gates
- [ ] Implement the explainable extraction pipeline.
- [ ] Require source paragraph, extracted task, and confidence level.
- [ ] Automatically downgrade confidence when anatomy, modality, or timeline linkage is weak.
- [ ] Block .ics generation and caregiver draft generation until human verification is satisfied when confidence is not high.
- [ ] Add patient validation before outbound release of reports, statements, or personal DICOM images.
- [ ] Add an inbox holding area for incoming practice payloads so unverified records do not pollute the patient index.
- [ ] Enforce explicit identity-matching checks before a received report or study is appended to the local vault.

Exit criteria:
- Low-confidence follow-ups cannot create outbound tasks without explicit review.

### 13.3 Phase 3 - Continuity Intelligence
- [ ] Implement severity-based continuity priority tiers.
- [ ] Add missed-window reclamation for offline high-risk events.
- [ ] Add barrier classification fields for transport, financial, cognitive, social, infrastructure, and scheduling barriers.
- [ ] Generate clinician-facing continuity snapshots.
- [ ] Route review-only requests differently from outbound handoff requests.
- [ ] Generate a doctor-ready summary from the local vault without sending the full history anywhere else.

Exit criteria:
- The agent can prioritize high-risk follow-ups and summarize barriers clearly.

### 13.4 Phase 4 - Local Export and Interoperability
- [x] Generate local `.ics` reminders from approved timeline items.
- [x] Generate `PATIENT_PASSPORT.md` from active recovery items.
- [x] Add schema notes that map markdown fields to FHIR and DICOM SR concepts.
- [x] Keep exports local-first and draft-only until approved.
- [ ] Prevent exports from being produced for the wrong patient or without explicit identity confirmation.
- [ ] Add a patient-approved history packet export that can be opened by practice-side local apps for more efficient diagnosis and recovery planning.
- [ ] Add `clinical_interop.json` as a local patient-to-practice exchange bundle for verified handoff.

Exit criteria:
- The system can export reminders and a patient passport without using cloud services.

### 13.5 Phase 5 - Frontend Portal
- [x] Add a private guarded SDOH chat entry in the dashboard.
- [x] Add a timeline or recovery view for upcoming, blocked, missed, and completed items.
- [x] Add UI states for reminder drafts, caregiver drafts, and verification gates.
- [x] Make the agent visually distinct from Forge and Quest.
- [ ] Surface patient-validation state and draft-only warning labels in the SDOH portal.
- [ ] Add an indexed-documents view that shows which local reports, DICOM studies, and scripts the patient can surface for a visit.
- [ ] Add vault-first search and retrieval affordances so the patient can query local records by body part, modality, date, or report terms.

Exit criteria:
- A user can open the SDOH portal, review a continuity item, and approve a draft.

### 13.6 Phase 6 - Analytics and Demo Readiness
- [x] Track reminder acknowledgment rate.
- [x] Track follow-up completion rate.
- [x] Track transport coordination success.
- [x] Track missed follow-up rescue count.
- [x] Add the lung CT to PET rescue demo flow.
- [ ] Add WhatsApp/OpenClaw staging for the SDOH workflow using `+27663764491` as the initial operator number.
- [x] Add admin onboarding and skill scaffolding for local app, VM, database, and DICOM discovery.

Exit criteria:
- The demo can show a measurable continuity improvement from alert to completion.

### 13.7 Phase 7 - Sovereign Vault Storage
- [ ] Create a folder-structured patient vault under `~/.openclaw/vault/` for identity, index, records, and exports.
- [ ] Store validation keys, local indexes, studies, reports, and scripts separately so patient files stay organized and auditable.
- [ ] Make the vault available to the agent through local file reads at greeting time.

Exit criteria:
- The agent can start from local vault state instead of chat history alone.

### 13.8 Phase 8 - Local Metadata Parsers
- [ ] Add a lightweight parser wrapper for DICOM metadata extraction with pydicom.
- [ ] Add local OCR and regex parsing for reports, scripts, and lab text.
- [ ] Persist extracted metadata such as modality, study date, body part, and key terms into the local index.

Exit criteria:
- The patient can drop a study or report into the vault and get an indexed local summary.

### 13.9 Phase 9 - Verification Gatekeeper
- [ ] Hold incoming practice payloads in an unindexed inbox until validation succeeds.
- [ ] Cross-check incoming patient metadata against local validation keys before ingestion.
- [ ] Block foreign records from blending into the local graph when identity matching fails.

Exit criteria:
- Wrong-patient records cannot be silently appended to the vault.

### 13.10 Phase 10 - Intent-Driven Retrieval
- [ ] Replace generic scan-prep replies with local index queries over the vault.
- [ ] Return targeted document packs for prompts like "I need a CT scan" or "what should I bring to the doctor?".
- [ ] Use the local graph to surface the relevant history, then synthesize a doctor-ready summary.

Exit criteria:
- The agent can answer a visit-prep prompt by querying local records rather than guessing from chat.

## 14. Progress Tracking

### 14.1 Recommended Task Order
1. Backend SDOH agent skeleton.
2. Extraction pipeline and confidence gates.
3. Continuity priority engine and barrier taxonomy.
4. Local export generation.
5. Frontend guarded portal and timeline view.
6. Analytics counters and demo scenario.

### 14.2 Status Model
- Not started: task is defined but untouched.
- In progress: task is actively being implemented.
- Blocked: task depends on a missing prerequisite.
- Ready for review: task is complete and needs validation.
- Done: task is validated and accepted.

### 14.3 Suggested Progress Log
- Task:
- Owner:
- Status:
- Dependency:
- Validation:
- Notes:

- Task: Patient-owned document triage
- Owner: SDOH agent
- Status: In progress
- Dependency: local patient-side documents or a pasted report for context
- Validation: short CT scan prompt returns a local document pack checklist
- Notes: keep the advice patient-facing, local-first, and draft-only until the patient approves sharing

### 14.4 Coding Agent Operating Rule
- Work one task at a time.
- Prefer the smallest complete change that satisfies the current exit criteria.
- Validate after each edit before moving to the next task.
- If a task needs broader redesign, stop and update the plan before coding further.