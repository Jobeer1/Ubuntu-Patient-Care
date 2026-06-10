# SDOH Agent — Complete Implementation Guide

## Overview

The SDOH Continuity Agent is a patient-facing continuity guide that helps patients own, understand, and use their medical history. It operates in a local-first, privacy-by-default architecture where all patient data stays on the patient's device unless explicitly approved for sharing.

---

## Architecture Summary

### Core Agent Location
- **Primary file**: `agent_sdoh.py` (lean entry point)
- **Mixin files**:
  - `backend/sdoh_timeline_mixin.py` - Timeline construction, ICS export, Patient Passport generation
  - `backend/sdoh_document_mixin.py` - Topic routing, document guidance, clinical extraction
  - `backend/sdoh_service_mixin.py` - Patient validation, billing, service guards, `_build_response`
  - `backend/sdoh_index_parser_mixin.py` - Patient document index parsing
  - `backend/sdoh_index_vocab.py` - Vocabulary and terminology for indexing
- **Indexer class**: `PatientDocumentIndexer` in `backend/sdoh_patient_index.py`

### Class Inheritance
```python
SDOHContinuityAgent(SDOHTimelineMixin, SDOHDocumentMixin, SDOHServiceMixin)
```

### Agent Response Fields (additional fields from ARCHITECTURE_AND_COUPLINGS.md)
- `demo_case` - Tracks demo case interactions (e.g., lung_ct_to_pet_rescue)
- `payment_allocation_draft` - Payment allocation draft object
- `payment_allocation_id` - UUID of created payment allocation
- `calendar_filename` - Filename for calendar export
- `passport_filename` - Filename for passport export

---

## Configuration (config.ini)

```ini
[SDOH]
local_model = gemma:2b                    # Primary local model (Ollama)
fallback_model = gemini-2.5-flash-lite   # Cloud fallback (currently disabled)
local_model_timeout_sec = 90              # Ollama timeout
local_model_num_predict = 160             # Max tokens for local model
local_model_history_chars = 1800          # History character limit
local_model_input_chars = 1000            # Input character limit
whatsapp_number = +27663764491           # OpenClaw WhatsApp provider number
vault_root = ~/.openclaw/vault            # Vault root directory
index_file = ~/.openclaw/vault/index/master_health_graph.json  # Index file path

[SIIM_HACKATHON]
fhir_base_url = https://hackathon.siim.org/fhir
dicomweb_base_url = https://hackathon.siim.org/dicomweb
api_key_header = apikey
api_key = 7cfbc85a-719b-4334-851f-227cbdb11448
fhir_resources = Patient,Condition,Observation,Encounter,DiagnosticReport,ImagingStudy,MedicationRequest,Procedure,AllergyIntolerance
dicom_max_instances = 200
ssl_verify = false                        # Hackathon SSL cert may be self-signed
dicom_vault_path =                         # Defaults to ~/.openclaw/vault/siim_hackathon/
```

---

## Core Capabilities

### 1. Patient Document Indexing
- **Indexer class**: `PatientDocumentIndexer` in `backend/sdoh_patient_index.py`
- **Default scan directories** (configurable via config.ini):
  - Configured via `scan_dir_1`, `scan_dir_2`, `scan_dir_3` in `[SDOH]` section
  - If not configured, defaults to `~/sdoh_medical_records`

#### Supported File Types
| Extension | Type | Processing |
|-----------|------|------------|
| `.dcm` | DICOM | pydicom header parsing, magic-byte fallback |
| `.jp2`, `.j2k` | JPEG2000 | Header parsing, DICOM companion lookup |
| `.pdf` | PDF | pdfminer.six or pypdf text extraction |
| `.txt`, `.md` | Text | Plain text parsing |
| `.jpg`, `.jpeg`, `.png` | Images | Metadata extraction |

#### Document Detection
- **DICOM files**: Detected via magic bytes at offset 128 (`DICM` signature)
- **JP2 files**: Parsed via `openclaw` or raw header analysis
- **Body part detection**: 8 anatomical regions with keyword matching
- **Modality detection**: 15 modality codes (CT, MR, CR, DX, US, PT, etc.)

---

### 2. Intent Classification (`_topic` method)

| Topic | Keywords Detected | Route Handler |
|-------|-------------------|---------------|
| `index_records` | index, scan, dicom, folder, drive | `_build_index_guidance()` |
| `show_documents` | document, report, show me, what do i have | `_build_show_documents_response()` |
| `history_pack` | history pack, share, prepare | `_build_history_pack_response()` |
| `metadata_preview` | metadata scope, scan drive, preview index | `_build_metadata_preview_response()` |
| `whatsapp_chat_indexing` | whatsapp chat, export | `_build_whatsapp_chat_indexing_response()` |
| `siim_patients` | siim patients, list patients | `_build_siim_patients_response()` |
| `siim_ingest` | siim ingest, start ingest, fetch patients | `_build_siim_ingest_response()` |
| `siim_patient_detail` | patient detail, which studies | `_build_patient_document_guidance()` |
| `general` | (default) | `_build_response()` |

---

### 3. Deterministic Routing (`_build_response` in sdoh_service_mixin.py)

| Route | Trigger | Response Handler |
|-------|---------|----------------|
| `safety` | Urgent symptoms (chest pain, stroke, etc.) | Escalate to emergency services |
| `patient_validation` | Explicit validation request | Request patient identity confirmation |
| `practice_onboarding` | Requests about database/VM integration | Safe integration checklist |
| `practice_indexing` | Requests about drive-level indexing | Identity-validated checklist |
| `vault_ingest` | Inbound clinical documents | Validation gatekeeper |
| `patient_service` | Reports/images/statements + outbound | Patient handoff guard |
| `payment` | Payment/invoice-related | Payment allocation draft |
| `care_navigator` | Continuity/reminders | Timeline + draft message |
| `family_coordinator` | Communication/support requests | Draft message generation |
| `orientation` | SDOH questions | Plain explanation |
| `document_interpreter` | Pasted clinical text | Extraction + timeline |
| `recovery_tracker` | (default) | General continuity support |

---

## API Endpoints (backend/routes/sdoh_routes.py)

All endpoints under `/api/sdoh/...`:

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/sdoh/chat` | POST | Required | Send message to SDOH agent |
| `/sdoh/greeting` | GET | Required | Get personalized greeting |
| `/sdoh/index-documents` | POST | Required | Trigger document indexing |
| `/sdoh/my-documents` | GET | Required | Retrieve indexed documents |
| `/sdoh/history-pack` | POST | Required | Build patient history pack |
| `/oc/v1/models` | GET | Not required | OpenAI-compatible model list |
| `/oc/v1/chat/completions` | POST | Owner token required | OpenAI Chat Completions |
| `/oc/v1/responses` | POST | Owner token required | OpenAI Responses API |
| `/index_folder` | POST | Not required | Direct folder indexing (proxy guest mode) |

### OpenClaw Authentication
- **Header**: `X-SDOH-Owner-Token` or `Authorization: Bearer <token>`
- **Token source**: `PACS_SECURITY.owner_token` in config.ini
- **Admin numbers**: `+27768193339`, `0768193339` (auto-admin mode)
- **Owner number**: `+27663764491` (full access)

---

## SIIM Hackathon Integration

### Endpoints
- `POST /api/sdoh/siim/ingest` - Start background ingest (admin only)
- `GET /api/sdoh/siim/ingest/status` - Poll ingest progress
- `GET /api/sdoh/siim/sources` - List SIIM-registered sources
- `GET /api/sdoh/siim/patients` - List SIIM patients
- `GET /api/sdoh/siim/studies` - List SIIM imaging studies

### Ingest State File
- **Location**: `~/.openclaw/vault/siim_hackathon/ingest_state.json`
- **Schema**:
```json
{
  "status": "idle|running|completed|error",
  "started_at": "ISO8601",
  "finished_at": "ISO8601|null",
  "progress": {
    "Patient": {"fetched": 10, "indexed": 10},
    "Condition": {"fetched": 8, "indexed": 8},
    "Observation": {"fetched": 10, "indexed": 10},
    "DiagnosticReport": {"fetched": 63, "indexed": 63},
    "ImagingStudy": {"fetched": 64, "indexed": 64}
  },
  "dicom": {
    "studies_found": 0,
    "instances_downloaded": 0,
    "bytes_written": 0,
    "vault_files_scanned": 0,
    "vault_studies_indexed": 0
  },
  "errors": []
}
```

### FHIR Resources Fetched
1. Patient - EMPI matching + registry entry
2. Condition - Clinical condition records
3. Observation - Lab results / vitals
4. Encounter - Visit records
5. DiagnosticReport - Radiology reports
6. ImagingStudy - Study metadata
7. MedicationRequest - Medication orders
8. Procedure - Procedure records
9. AllergyIntolerance - Allergy records

### DICOMweb Operations
1. **QIDO-RS**: Query studies, series, instances metadata
2. **WADO-RS**: Download actual DICOM files
3. **Local vault path**: `~/.openclaw/vault/siim_hackathon/`
4. **Max instances**: 200 per run (configurable)

### Resources
- Orientation Webinar: https://my.siim.org/event-information?id=a0lUO00000C6qEjYAJ
- Brainstorming Session: https://us02web.zoom.us/meeting/register/JSo_I9U5TpSqUIadhIBLNA#/registration
- API Keys: https://siim.org/learning-events/events/hackathon/siim-hackathon-api-platform-participant-agreement/
- Docs: https://imaginginformatics.github.io/hackathon-docs/

---

## OpenClaw Skills (`backend/sdoh_openclaw_skills.py`)

| Method | Purpose |
|--------|---------|
| `extract_dicom_metadata()` | Comprehensive DICOM tag extraction |
| `extract_jp2_metadata()` | JP2 image analysis |
| `classify_medical_document()` | NLP-based document classification |
| `extract_medical_entities()` | NER for medications/diagnoses/procedures |
| `verify_patient_anonymization()` | PII detection for redaction |

---

## Local Proxy (`sdoh_oc_proxy.py`)

### Purpose
Standalone Flask proxy (port 5001) that adapts OpenAI Responses calls to SDOH endpoints. Used when:
- Main Flask backend (port 5002) is unavailable
- Session context needs isolation
- Local-first operation preferred

### Endpoints
- `GET /api/sdoh/oc/v1/models` - Returns `sdoh-continuity-v1`
- `POST /api/sdoh/oc/v1/chat/completions` - Chat completions
- `POST /api/sdoh/oc/v1/responses` - SSE streaming responses

### Authentication
Same owner token system as main backend.

---

## Response Fields (JSON Schema)

### Core Fields (always present)
| Field | Type | Description |
|-------|------|-------------|
| `response` | string | Main agent reply text |
| `phase` | string | General, local, recovery_tracker, etc. |
| `score` | int | Integrity score adjustment |
| `confidence` | string | high, medium, low |
| `verification_required` | bool | Whether verification needed |
| `route` | string | Routing key for frontend |

### Document Processing Fields
| Field | Type | Description |
|-------|------|-------------|
| `source_paragraph` | string | Extracted source text |
| `extracted_task` | string | Action item from document |
| `anatomy` | string | Detected body part |
| `modality` | string | Detected modality |
| `timeline` | string | Timeline text |
| `timeline_items` | array | Calendar event objects |
| `barrier_classification` | string | transport, financial, etc. |

### Validation Fields
| Field | Type | Description |
|-------|------|-------------|
| `patient_validation_required` | bool | Identity confirmation needed |
| `patient_validation_verified` | bool | Identity confirmed |
| `outbound_ready` | bool | Safe to share |

### Export Bundle Fields
| Field | Type | Description |
|-------|------|-------------|
| `export_bundle.export_ready` | bool | Export generated |
| `export_bundle.calendar_events` | array | .ics event objects |
| `export_bundle.ics_content` | string | ICS file content |
| `export_bundle.passport_markdown` | string | PATIENT_PASSPORT.md |
| `export_bundle.schema_notes` | string | Interoperability notes |

### Administrative Fields
| Field | Type | Description |
|-------|------|-------------|
| `admin_mode` | bool | Admin/operator session |
| `tool_calls` | array | Suggested executions |
| `requested_source_path` | string | Folder for indexing |
| `indexing_progress` | object | Scan progress |
| `metadata_summary` | object | Vault query results |
| `demo_case` | string | Demo case identifier |
| `payment_allocation_draft` | object | Payment allocation object |
| `payment_allocation_id` | string | Payment allocation UUID |
| `calendar_filename` | string | .ics filename |
| `passport_filename` | string | .passport filename |

---

## Frontend Integration (chat.js)

### SDOH Panel DOM IDs
```javascript
sdoh-summary              // Care snapshot
sdoh-timeline-list        // Recovery timeline items
sdoh-analytics            // Interaction analytics
sdoh-status-text        // Export status
sdoh-bar                // Progress bar
sdoh-export-flag        // Export flag text
sdoh-guardrail          // Safety guardrail text
sdoh-download-ics       // Download .ics button
sdoh-download-passport    // Download passport button
sdoh-copy-summary        // Copy summary button
```

### Key Functions
| Function | Purpose |
|----------|---------|
| `sendToSdoh(text)` | POST to `/sdoh/chat`, render response |
| `loadSdohGreeting()` | GET `/sdoh/greeting` |
| `saveSdohExportBundle(bundle)` | Persist to localStorage |
| `loadSdohExportBundle()` | Retrieve from localStorage |
| `renderSdohPanel(bundle)` | Update panel UI |
| `downloadSdohICS()` | Download calendar file |
| `downloadSdohPassport()` | Download markdown file |

---

## PACS Continuity Registry (`backend/pacs_registry.py`)

### Database Path
- **Default**: `./instance/pacs_continuity_registry.db`

### Tables
| Table | Purpose |
|-------|---------|
| `registry_sources` | Configured source tracking |
| `empi_patients` | Patient identity registry |
| `source_identity_links` | Source->EMPI linking |
| `imaging_studies` | DICOM study metadata |
| `storage_assets` | Archive file inventory |

### EMPI Match Order
1. `national_id` - exact match
2. `issuer_patient_id` - source-specific match
3. Exact name + birth date
4. Phonetic name + birth date
5. New EMPI creation

---

## Clinical Plain Language (`backend/sdoh_patient_index.py`)

| Term | Meaning |
|------|---------|
| lesion | Area looking different from normal tissue |
| nodule | Small lump needing follow-up |
| mass | Growth needing investigation |
| opacity | Lighter area on scan (fluid/infection) |
| effusion | Fluid where it shouldn't be |
| calcification | Calcium deposits (normal or monitored) |
| pneumonia | Lung infection |
| atelectasis | Partially collapsed lung |
| cardiomegaly | Larger-than-normal heart |
| malignant | Cancerous (urgent follow-up) |

---

## Troubleshooting Quick Reference

### Common Issues

| Problem | Check | Fix |
|---------|-------|-----|
| No documents found | `index_file` config | Set `index_file` in SDOH section |
| Gemini fallback failing | `api_key` config | Verify GEMINI.api_key |
| WhatsApp not responding | OpenClaw session key | Check `X-Openclaw-Session-Key` header |
| SIIM ingest stuck | `ingest_state.json` | Check status, restart if stale >1hr |
| Ollama timeout | CPU-only system | Decrease `local_model_num_predict` |
| Context overflow (livenessState=blocked) | Session file size | Run `reset_sdoh_session.py` to clear |
| Session already compacted | Session trajectory | Delete session files in `.openclaw/agents/sdoh/sessions/` |
| Large vault index (1.4GB+) | `master_health_graph.json` | Use `quick_sample_files()` for large archives |

### Validation Checklist
- [ ] Vault path exists (`~/.openclaw/vault/`)
- [ ] Validation keys configured (`.identity/validation_keys.json`)
- [ ] Index file accessible
- [ ] Owner token matches across config + environment

### Debug Commands
```bash
# Check vault index
python -c "import json; print(json.load(open('~/.openclaw/vault/index/master_health_graph.json')))"

# Check SIIM status
curl -s http://localhost:5002/api/sdoh/siim/ingest/status -H "Authorization: Bearer $TOKEN"

# Test localhost agent
python sdoh_oc_proxy.py
curl http://localhost:5001/api/sdoh/oc/v1/chat/completions -d '{"messages":[{"role":"user","content":"hello"}]}' -H "X-SDOH-Owner-Token: $TOKEN"
```

---

## Agent State Machine

```
User Input -> _topic() -> _build_response() -> chat() -> _finalize_structured_response()
                     |
                     |- index_records -> _build_index_guidance()
                     |- show_documents -> _build_show_documents_response()
                     |- history_pack -> _build_history_pack_response()
                     |- metadata_preview -> _build_metadata_preview_response()
                     |- whatsapp_chat_indexing -> _build_whatsapp_chat_indexing_response()
                     |- siim_patients -> _build_siim_patients_response()
                     |- siim_ingest -> _build_siim_ingest_response()
                     |- siim_patient_detail -> _build_patient_document_guidance()
                     |- vault_ingest -> admin validation gate
                     |- patient_service -> validation gate
                     |- payment -> payment_allocation_draft
                     |- general -> care_navigator / family_coordinator
```

---

## Export Generation Flow

1. **Trigger**: User confirms or confidence gate passes
2. **Timeline**: `_build_timeline_item()` creates items
3. **Calendar**: `_calendar_events_from_timeline()` builds events
4. **ICS**: `_build_ics_content()` formats .ics string
5. **Passport**: `_build_patient_passport()` formats markdown
6. **Bundle**: `_build_export_bundle()` combines all
7. **Download**: Frontend buttons trigger file downloads

---

## Security Model

- **Local-first**: All indexing/processing on device
- **Explicit approval**: No outbound without verification
- **Redaction**: Patient names/IDs masked in registry queries
- **Admin gating**: Sensitive operations require admin proof
- **Token auth**: WhatsApp bridge secured by owner token