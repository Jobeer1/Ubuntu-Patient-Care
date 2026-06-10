# PACS Mentor Agent Current Behavior

## What PACS Mentor Does Now
The PACS Continuity Mentor is a radiology infrastructure recovery guide for approved local operators. It focuses on read-only recovery support, operational continuity, and institutional knowledge capture.

## Current Inputs
- User message content.
- A local authorization image for the emergency directive flow.
- Local OCR output from the uploaded directive.
- Passive network discovery results.
- Logged recovery actions and current incident state.
- Recent PACS chat history for Gemini-backed intent parsing.

## Current Response Style
- Calm, expert, and step-by-step.
- Short instructions with explicit verification checks.
- Frames problems in terms of clinical imaging continuity.
- Refuses guidance until authorization is verified.

## Current Authorization Flow
1. The agent starts locked.
2. It requires an Emergency Operational Continuity Directive image.
3. It uses local OCR to verify required tokens and the current date.
4. If verification passes, it enables the emergency override state.
5. If verification fails, it returns an authorization denial.

## Current Operational Behavior
- Creates and appends to a local recovery log at `INFRASTRUCTURE_RECOVERY_LOG.md`.
- Writes PACS request/response audits to an append-only log for management review, separate from user chat history.
- Tracks an incident state machine from detected to resolved or escalated.
- Supports passive discovery of local network topology through ARP/MAC vendor fingerprints.
- Maps likely clinical infrastructure roles such as DICOM listeners and database stores.
- Returns short recovery walkthroughs for approved scenarios.
- Maintains a read-only continuity registry for configured FHIR, DICOMweb, and mounted NAS sources.
- Auto-discovers mounted Windows NAS/network drives when no explicit mount list is provided.
- Records the source type, source location, storage tier, and searchable asset family for each indexed study or file-based database so the mentor knows what kind of data is on each share.
- Can target a specific mounted folder path such as `X:\RIS` for direct indexing instead of always running a broad registry sync.
- Can export a read-only PACS report as DOCX or PDF with workflow, database, and network diagrams generated from the local registry snapshot.
- The export path is advisory only, is triggered by a natural-language chat request to the agent, and does not edit source DICOM files, NAS shares, or source databases.
- Recognizes Firebird-style database shares on mounted folders and returns a folder-specific indexing summary.
- Uses Gemini to interpret ambiguous and follow-up PACS questions in context, including Firebird follow-ups after targeted indexing.
- Falls back to local Gemma 2B when Gemini is unavailable, while keeping PACS request logging intact.
- Gives PACS admin staff concrete workflow guidance for SIIM-style FHIR/DICOMweb questions instead of asking for skill names.
- Reconciles patient identity with deterministic EMPI rules before linking studies.
- Stitches x-ray, ultrasound, and other modality histories into a single local timeline without destructive source-system merges.
- Supports fast retrieval and search through local SQLite indexes on EMPI, study date, modality, source metadata, and NAS asset metadata.
- Supports LAN inventory summaries for configured VMs and network equipment, plus passive discovery snapshots when the break-glass flow has enabled them.
- The mentor now names RIS, PACS, and medical billing sources in its core capability set and asks for admin proof before deeper sensitive discovery.
- Site proof is remembered for the current session so the mentor stops re-asking the same authorization prompt after proof is offered.
- For deeper LAN exploration, the mentor now asks for explicit PACS-admin proof before exposing sensitive topology details; audit logging redacts obvious credential-like fields.

## Current Recovery Coverage
The current code supports:
- Passive network discovery.
- Clinical socket mapping.
- Read-only recovery walkthroughs for locked systems.
- Incident report generation for audit or handoff.
- Registry sync, registry summary, and patient timeline lookup endpoints.
- Registry search endpoint for patients, studies, and storage assets.
- Targeted path indexing for explicitly requested mounted folders.
- Normal-mode registry queries that summarize source inventory and patient timelines without requiring break-glass access.

## Current Safety Boundaries
- It is read-only advisory by default.
- It is not meant to be a penetration-testing tool.
- It should not be used to bypass access controls on unapproved systems.
- It keeps recovery notes local to the workspace.
- It can only report LAN-wide status for configured targets or an already-collected passive discovery snapshot; it must not invent hosts from free-text prompts.
- It should ask for proof of PACS-admin authorization before exploring deeper into topology, credentialed device discovery, or sensitive LAN detail.

## Output Shape
Current methods return plain strings or JSON-like records such as:
- greeting text
- authorization success/failure payloads
- passive discovery topology
- recovery walkthrough steps
- incident reports

## Practical Limitations
- It depends on a valid local OCR verification path before advanced help is allowed.
- It assumes the operator is working in an approved recovery context.
- It is most useful for a technician who already has a known incident and needs safe next steps.
