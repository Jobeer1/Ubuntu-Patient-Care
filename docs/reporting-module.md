# 📝 Radiology Reporting Module with Voice Dictation & Image Comparison

## Overview
A next-generation reporting module designed for South African radiologists and doctors. This module enables seamless, secure, and efficient report creation with integrated voice dictation (speech-to-text), multi-image comparison, and highly customizable image display layouts. Built to work offline and integrate with the Ubuntu Patient Care system, Orthanc PACS, and OpenEMR.

---

## Key Features

### 1. Voice Dictation (Speech-to-Text)
- **Lightweight, Offline STT Engine:** Integrates Vosk, Coqui STT, or Whisper.cpp for on-premise, privacy-preserving speech-to-text.
- **South African Accent Support:** Optimized for local English, Afrikaans, isiZulu, isiXhosa, and other major languages.
- **Medical Vocabulary:** Custom dictionary for radiology and South African medical terms.
- **Real-Time Dictation:** Dictate directly into the report editor, with live transcription and easy correction.
- **Audio File Storage:** Secure, encrypted storage of original audio for audit and review.

### 2. Image Comparison & Custom Display
- **Multi-Panel DICOM Viewer:** Compare 2–4 images/studies side-by-side.
- **Drag-and-Drop:** Easily assign studies/series to panels.
- **Synchronized Navigation:** Link/unlink panels for scrolling, zoom, and window/level.
- **Custom Layouts:** Choose from presets (1x1, 2x1, 2x2, custom grid) or define your own.
- **User Profiles:** Save preferred layouts and settings per doctor.
- **Overlay Controls:** Toggle annotations, measurements, and patient info.
- **High-Performance Rendering:** Optimized for low-bandwidth and load-shedding scenarios.

### 3. Reporting Workflow
- **Create/Edit/Sign Reports:** Draft, edit, finalize, and digitally sign reports.
- **Attach Key Images:** Embed or reference images in the report.
- **Patient & Study Linking:** Auto-link to OpenEMR and Orthanc records.
- **Export Options:** PDF, HL7, FHIR, and direct EHR integration.
- **Audit Trail:** Every edit, sign-off, and access is logged for POPI compliance.
- **Template Library:** Pre-built and custom templates for common studies (e.g., chest X-ray, CT brain, mammogram).

### 4. Seamless System Integration
- **Dashboard Launch:** Open from dashboard, worklist, or DICOM viewer.
- **Data Sync:** Works offline with local cache, syncs when online.
- **Billing Integration:** Link reports to claims and medical aid billing.
- **Notifications:** Real-time updates to dashboard and workflow.

### 5. South African Context & Compliance
- **POPI Act:** All data encrypted at rest and in transit; full audit logging.
- **Language Support:** Dictation and UI in all 11 official languages.
- **Medical Aid Ready:** Reports formatted for SA medical aid requirements.
- **Load Shedding Resilience:** Auto-save, local-first, and rapid recovery after power loss.
- **Cultural Sensitivity:** Support for traditional medicine notes and family involvement.

---

## Technical Architecture

### Frontend
- **Framework:** React (with Cornerstone.js for DICOM)
- **STT Integration:** WebSocket/REST to local STT microservice
- **Rich Text Editor:** For dictation, editing, and template use
- **Customizable UI:** Layout manager, panel controls, and user profiles

### Backend
- **STT Microservice:** Python/Node/C++ (Vosk/Coqui/Whisper.cpp)
- **API:** Endpoints for report CRUD, image fetch, layout management
- **Database:** Store reports, audio, and user settings (PostgreSQL/MySQL)
- **Security:** Encrypted storage, access control, audit logging

### Integration Points
- **Orthanc PACS:** DICOM image fetch and metadata
- **OpenEMR:** Patient and study data, report linking
- **Dashboard:** Launch, notifications, and workflow updates
- **Billing Engine:** Report status triggers claim generation

---


## User Workflow
1. **Launch Reporting:** From dashboard, worklist, or viewer
2. **Select Images:** Drag studies/series into comparison panels
3. **Customize Layout:** Choose or create preferred display
4. **Dictate Report:** Doctor uses voice dictation (STT) or keyboard to create initial report draft.
5. **Transcription Review:** The draft is sent to the transcription team (three staff) who review and correct the STT output for medical accuracy and terminology.
6. **Doctor Proofreading & Authorisation:** The corrected report is sent back to the doctor for final proofreading and digital authorisation/sign-off.
7. **Billing Team Processing:** Once authorised, the report is sent to the billing team to assign fees and submit claims to medical schemes.
8. **Sync & Notify:** Report syncs to backend, notifies team, and links to billing and claims.

---

## Installation & Configuration

### Prerequisites
- Docker & Docker Compose
- Ubuntu 20.04+ or compatible Linux
- Sufficient CPU for STT (recommend AVX2 support for Whisper.cpp)

### Setup Steps
1. **Deploy STT Microservice:**
   - Choose Vosk, Coqui, or Whisper.cpp
   - Run as Docker container or local service
2. **Update Docker Compose:**
   - Add reporting-frontend and reporting-backend services
   - Link to Orthanc, OpenEMR, and database
3. **Configure Environment:**
   - Set language, audio storage, and security options
4. **User Training:**
   - Provide guide for dictation, editing, and layout customization

---

## Security & Compliance
- All audio and report data encrypted (AES-256)
- Full audit trail for POPI Act
- Local/offline STT for privacy
- Role-based access control

---

## Future Enhancements
- AI-powered report suggestions
- Advanced measurement and annotation tools
- Mobile dictation app
- Integration with national health registries

---

## Support & Feedback
- For issues, contact: [support@ubuntu-patient-care.com](mailto:support@ubuntu-patient-care.com)
- Feature requests: [GitHub Issues](https://github.com/Jobeer1/Ubuntu-Patient-Care/issues)

---

**Built for South African radiologists, by South African developers.**
