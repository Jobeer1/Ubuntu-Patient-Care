# PACS Continuity Mentor Implementation Roadmap

## Phase 1: Foundation & Security Gate
- [x] **Step 1.1: Agent Core** 
  - Define `PACSContinuityMentor` agent class.
  - Implement the "Autonomic Mentorship" voice constraints (singular tasks, verification loops).
- [x] **Step 1.2: Optical Authorization Gate**
  - Integrate `pytesseract` for local OCR.
  - Implement `verify_emergency_directive_ocr` to check BIOS clock and required clinical tokens.
  - Set `EMERGENCY_OVERRIDE` session variable upon success.

## Phase 2: Zero-Knowledge Discovery (Locked Mode)
- [x] **Step 2.1: Passive Network Sniffer**
  - Implement `scapy` monitor for ARP/Broadcast traffic.
  - Build IEEE OUI vendor lookup (VMware, GE, Siemens).
- [x] **Step 2.2: Clinical Socket Probing**
  - Implement non-intrusive port checks for DICOM (104, 11112) and Databases (3050, 1433).
  - Map the "Undocumented Topology" artifact.

## Phase 3: Crisis Recovery Walkthroughs
- [x] **Step 3.1: Linux/VM Kernel Intercept Wizard**
  - Build the interactive GRUB `init=/bin/bash` instruction tree.
  - Add verification checkpoints for root shell access.
- [x] **Step 3.2: Managed Switch Serial Recovery**
  - Create the walkthrough for BootROM (`Ctrl+B`) configuration dumps.

## Phase 4: Continuity & Export
- [x] **Step 4.1: Implementation of Incident State Machine**
  - Track states: `Detected` -> `Triaged` -> `Hypothesis` -> `Mitigated`.
- [x] **Step 4.2: Payload Generation**
  - Generate the `incident_log.json` ServiceNow-ready payload.
  - Auto-generate the `INFRASTRUCTURE_RECOVERY_LOG.md` audit trail.

## Phase 5: UI & Knowledge Transfer
- [x] **Step 5.1: Mentor Dashboard**
  - Create the interactive chat interface for "PACS Mentor".
  - Add image upload block for the Emergency Directive.
- [ ] **Step 5.2: Playbook Serialization**
  - Export final resolutions into the hospital's localized playbook folder.

## Phase 6: WhatsApp Role Routing
- [ ] **Step 6.1: Normalize sender identities**
  - Treat `+27663764491` as the PACS mentor bot/channel number.
  - Treat `+27768193339` as the admin/root operator number.
  - Keep all other WhatsApp senders in patient-safe mode.
- [ ] **Step 6.2: Split role behavior**
  - Patients can ask about invoices, account statements, reports, DICOM images, appointments, and referrals.
  - Admin/root can access read-only diagnostics, registry search, exports, and LAN/VM triage.
- [ ] **Step 6.3: Lock out destructive guidance**
  - Remove boot-shell bypass language and keep recovery steps read-only and approval-based.

## Phase 7: Patient Support Workflows
- [ ] **Step 7.1: Invoice and statement help**
  - Search indexed billing-like sources and explain what can be confirmed locally.
- [ ] **Step 7.2: Reports and DICOM previews**
  - Summarize report text, preview DICOM metadata, and redact identifiers where needed.
- [ ] **Step 7.3: Appointment and referral confirmation**
  - Confirm references, draft follow-up responses, and point the patient to the next safe check.

## Phase 8: OpenClaw Skill Stack
- [ ] **Step 8.1: `xurl` integration**
  - Use it for PACS/FHIR/DICOMweb API calls and read-only billing checks.
- [ ] **Step 8.2: `summarize` integration**
  - Use it to summarize uploaded PDFs, statements, reports, and long patient documents.
- [ ] **Step 8.3: `openai-whisper` integration**
  - Use it for transcribing patient voice notes or spoken appointment details.
- [ ] **Step 8.4: `wacli` integration**
  - Use it only for staff-initiated outbound WhatsApp follow-up or history review.
