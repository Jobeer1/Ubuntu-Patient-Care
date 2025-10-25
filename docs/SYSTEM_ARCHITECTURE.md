# 🏥 Ubuntu Patient Care - System Architecture & Integration Documentation

**Complete RIS/PACS/EMR Medical System for South Africa**

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Component Structure](#component-structure)
4. [HL7 FHIR Integration](#hl7-fhir-integration)
5. [DICOM Workflow](#dicom-workflow)
6. [Database Architecture](#database-architecture)
7. [Integration Points](#integration-points)
8. [Data Flow](#data-flow)
9. [Security & Compliance](#security--compliance)
10. [Deployment Architecture](#deployment-architecture)

---

## 🎯 System Overview

Ubuntu Patient Care is a comprehensive healthcare information system integrating:

- **RIS (Radiology Information System)** - Complete radiology workflow management
- **PACS (Picture Archiving and Communication System)** - Medical image storage and viewing
- **EMR (Electronic Medical Records)** - Patient management via OpenEMR
- **Medical Billing** - South African medical aid integration
- **Medical Dictation** - AI-powered voice-to-text reporting

### Technology Stack

**Backend:**
- PHP 8.x (SA-RIS Backend)
- Node.js/Express (API Server)
- Python 3.x (Medical Reporting Module)
- Orthanc PACS (C++ DICOM Server)

**Frontend:**
- React 18 with TypeScript
- Material-UI (MUI)
- Ant Design
- Socket.io for real-time updates

**Databases:**
- PostgreSQL 15 (OpenEMR)
- MySQL 8.0 (SA-RIS)
- SQLite (Medical Reporting, Orthanc Index)

**Standards Compliance:**
- HL7 FHIR v4.0+
- DICOM 2023
- ICD-10 (South African)
- NRPL (National Reference Price List)
- POPI Act (Protection of Personal Information)

---


## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   SA-RIS     │  │   Medical    │  │   OpenEMR    │  │     NAS      │   │
│  │  Dashboard   │  │  Reporting   │  │   Patient    │  │ Integration  │   │
│  │  (React)     │  │   Module     │  │  Management  │  │   Backend    │   │
│  │  Port: 3000  │  │  Port: 5443  │  │  Port: 8080  │  │  Port: 5000  │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                  │                  │            │
└─────────┼─────────────────┼──────────────────┼──────────────────┼────────────┘
          │                 │                  │                  │
          │                 │                  │                  │
┌─────────┼─────────────────┼──────────────────┼──────────────────┼────────────┐
│         │        APPLICATION / API LAYER     │                  │            │
├─────────┼─────────────────┼──────────────────┼──────────────────┼────────────┤
│         │                 │                  │                  │            │
│  ┌──────▼──────────┐  ┌──▼──────────────┐  ┌▼─────────────┐  ┌▼──────────┐ │
│  │   SA-RIS API    │  │  Reporting API  │  │  OpenEMR     │  │NAS Backend│ │
│  │   (Node.js)     │  │  (Python/Flask) │  │  Server      │  │  (Flask)  │ │
│  │  Port: 3001     │  │  Port: 5443     │  │  (Node.js)   │  │Port: 5000 │ │
│  │                 │  │                 │  │  Port: 3001  │  │           │ │
│  │ ┌─────────────┐ │  │ ┌─────────────┐ │  │              │  │┌─────────┐│ │
│  │ │ FHIR Service│ │  │ │ STT Engine  │ │  │              │  ││NAS Auto │││ │
│  │ │ Orthanc     │ │  │ │ Whisper AI  │ │  │              │  ││Import   │││ │
│  │ │ Connector   │ │  │ │ Report Gen  │ │  │              │  ││PACS API │││ │
│  │ │ Workflow    │ │  │ │ NAS Storage │ │  │              │  ││Device   │││ │
│  │ │ Engine      │ │  │ └─────────────┘ │  │              │  ││Discovery│││ │
│  │ │ Billing     │ │  │                 │  │              │  ││SA Voice │││ │
│  │ └─────────────┘ │  └─────────────────┘  └──────────────┘  │└─────────┘│ │
│  └─────────────────┘                                          └───────────┘ │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Orthanc REST API (Port: 8042)                                       │   │
│  │  • DICOM Services (C-STORE, C-FIND, C-MOVE)                          │   │
│  │  • DICOMweb (WADO-RS, QIDO-RS, STOW-RS)                              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
          │                 │                  │                  │
          │                 │                  │                  │
┌─────────┼─────────────────┼──────────────────┼──────────────────┼────────────┐
│         │         INTEGRATION LAYER          │                  │            │
├─────────┼─────────────────┼──────────────────┼──────────────────┼────────────┤
│         │                 │                  │                  │            │
│  ┌──────▼──────────┐  ┌──▼──────────────┐  ┌▼─────────────┐  ┌▼──────────┐ │
│  │ FHIR Radiology  │  │  DICOM 2023     │  │ Healthbridge │  │  Orthanc  │ │
│  │    Service      │  │  Compliance     │  │  Connector   │  │ Connector │ │
│  │                 │  │                 │  │  (HL7 FHIR)  │  │           │ │
│  │ • Patient Sync  │  │ • Validation    │  │              │  │ • C-FIND  │ │
│  │ • ImagingStudy  │  │ • Security      │  │ • Claims     │  │ • C-MOVE  │ │
│  │ • FHIR Server   │  │ • AI Workflow   │  │ • Status     │  │ • C-STORE │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘  └───────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
          │                 │                  │                  │
          │                 │                  │                  │
┌─────────┼─────────────────┼──────────────────┼──────────────────┼────────────┐
│         │            DATA LAYER              │                  │            │
├─────────┼─────────────────┼──────────────────┼──────────────────┼────────────┤
│         │                 │                  │                  │            │
│  ┌──────▼──────────┐  ┌──▼──────────────┐  ┌▼─────────────┐  ┌▼──────────┐ │
│  │   MySQL 8.0     │  │   SQLite        │  │ PostgreSQL   │  │  Orthanc  │ │
│  │   SA-RIS DB     │  │   Reporting DB  │  │  OpenEMR DB  │  │  Index DB │ │
│  │                 │  │                 │  │              │  │           │ │
│  │ • Workflows     │  │ • Reports       │  │ • Patients   │  │ • Studies │ │
│  │ • Billing       │  │ • Transcripts   │  │ • Claims     │  │ • Series  │ │
│  │ • DICOM Studies │  │ • Audit Logs    │  │ • Users      │  │ • Inst.   │ │
│  │ • FHIR Mappings │  │ • Templates     │  │ • Med Aids   │  │           │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘  └───────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
          │                 │                  │                  │
          │                 │                  │                  │
┌─────────┼─────────────────┼──────────────────┼──────────────────┼────────────┐
│         │           STORAGE LAYER            │                  │            │
├─────────┼─────────────────┼──────────────────┼──────────────────┼────────────┤
│         │                 │                  │                  │            │
│  ┌──────▼──────────────────▼──────────────────▼──────────────────▼────────┐ │
│  │                      NAS / File Storage                                 │ │
│  │                                                                          │ │
│  │  • DICOM Images (Orthanc Storage)                                       │ │
│  │  • Medical Reports (PDF/DOCX)                                           │ │
│  │  • Audio Recordings (Voice Dictation)                                   │ │
│  │  • Patient Documents                                                     │ │
│  │  • Backup Archives                                                       │ │
│  │                                                                          │ │
│  │  Storage Tiers: Online → Nearline → Offline Archive                    │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
          │
          │
┌─────────▼─────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL INTEGRATIONS                                       │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Healthbridge │  │ SA FHIR      │  │ Medical Aid  │  │  Cloudflare  │     │
│  │ Clearing     │  │ Server       │  │ Schemes      │  │  Tunnel      │     │
│  │ House        │  │ (National)   │  │ (Discovery,  │  │  (Remote     │     │
│  │              │  │              │  │  Momentum,   │  │   Access)    │     │
│  │ • Claims     │  │ • Patient    │  │  Bonitas,    │  │              │     │
│  │ • Payments   │  │ • Studies    │  │  GEMS, etc)  │  │ • HTTPS      │     │
│  │ • Status     │  │ • Resources  │  │              │  │ • Secure     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
└───────────────────────────────────────────────────────────────────────────────┘
```

---


## 📁 Component Structure

### 1. SA-RIS Backend (`sa-ris-backend/`)

**Purpose:** Core radiology information system with HL7 FHIR and DICOM integration

**Key Files:**
```
sa-ris-backend/
├── server.js                      # Node.js Express API server
├── FHIRRadiologyService.php       # HL7 FHIR v4.0+ integration
├── OrthancConnector.php           # DICOM PACS integration
├── DICOM2023Compliance.php        # DICOM 2023 standards validation
├── RISWorkflowEngine.php          # Radiology workflow automation
├── SABillingEngine.php            # South African medical billing
├── database_schema.sql            # Complete MySQL schema
├── docker-compose.yml             # Container orchestration
└── config/
    └── database.php               # Database configuration
```

**Responsibilities:**
- HL7 FHIR resource management (Patient, ImagingStudy)
- DICOM study routing and quality assessment
- Radiology workflow state machine
- Medical aid billing and claims
- Real-time notifications via Socket.io

**API Endpoints:**
- `GET /api/dicom/studies` - List DICOM studies
- `POST /api/fhir/imaging-study` - Create FHIR ImagingStudy
- `POST /api/workflow/advance` - Advance workflow state
- `POST /api/billing/quote` - Generate billing quote
- `GET /api/dashboard` - Real-time dashboard data

---

### 2. SA-RIS Frontend (`sa-ris-frontend/`)

**Purpose:** React-based radiology dashboard with South African UI/UX

**Key Files:**
```
sa-ris-frontend/
├── src/
│   ├── SARadiologyDashboard.js    # Main dashboard component
│   ├── components/
│   │   └── AccessibilityContext.js # WCAG 2.1 AA compliance
│   └── styles/
│       └── sa-eye-candy.css       # SA flag colors & animations
├── package.json
└── .env                           # Environment configuration
```

**Features:**
- Multi-language support (English, Afrikaans, Zulu)
- Real-time workflow status updates
- DICOM image viewer integration
- Medical aid verification
- Billing quote generation
- Accessibility compliant (WCAG 2.1 AA)

---

### 3. Orthanc PACS (`Orthanc/`)

**Purpose:** Enterprise DICOM server for medical image storage

**Key Components:**
```
Orthanc/
├── orthanc-server/                # Core DICOM server
├── orthanc-dicomweb/              # DICOMweb plugin
├── orthanc-ohif/                  # OHIF viewer integration
├── orthanc-python/                # Python scripting
├── orthanc-source/
│   └── NASIntegration/            # NAS storage integration
├── medical-reporting-module/      # Voice dictation module
└── tools/
    ├── find_dicom_databases.py    # Database discovery
    └── search_patients_exact.py   # Patient search
```

**DICOM Services:**
- **C-STORE:** Receive images from modalities
- **C-FIND:** Query patient/study information
- **C-MOVE:** Retrieve images to workstations
- **WADO-RS:** Web access to DICOM objects
- **QIDO-RS:** Query based on DICOM objects

**Storage Architecture:**
- **Online Storage:** Recent studies (< 90 days)
- **Nearline Storage:** Older studies (90-365 days)
- **Offline Archive:** Historical studies (> 1 year)

---

### 4. NAS Integration Backend (`Orthanc/orthanc-source/NASIntegration/backend/`)

**Purpose:** Enterprise NAS integration with automated DICOM import and multi-hospital support

**Key Files:**
```
NASIntegration/backend/
├── app.py                         # Main Flask application
├── core/
│   ├── app_factory.py             # Application factory
│   ├── blueprint_registry.py      # Blueprint management
│   └── system_initializer.py      # System initialization
├── services/
│   ├── nas_orthanc_importer.py    # NAS→Orthanc auto-import
│   ├── dicom_integration.py       # DICOM processing
│   ├── patient_search.py          # Patient search service
│   └── medical_sharing.py         # Secure sharing
├── routes/
│   ├── nas_core.py                # NAS core routes
│   ├── device_discovery_routes.py # Device discovery
│   ├── indexing.py                # DICOM indexing
│   └── auth_routes.py             # Authentication
├── api/
│   └── enterprise_nas_api.py      # Enterprise NAS API
├── enterprise_pacs_api.py         # Multi-NAS PACS API
├── pacs_api.py                    # High-performance PACS API
├── reporting_module.py            # Reporting integration
├── south_african_voice_dictation.py # SA voice dictation
├── sa_medical_aid_api.py          # Medical aid integration
├── telemedicine_integration.py    # Telemedicine support
└── orthanc-index/
    └── pacs_metadata.db           # PACS metadata database
```

**Features:**
- **NAS→Orthanc Auto-Import:** Automatic DICOM import from NAS to Orthanc
- **Multi-NAS Support:** Enterprise multi-NAS PACS indexing
- **Device Discovery:** Automatic network device discovery
- **Patient Search:** High-performance patient search across NAS
- **Secure Sharing:** Encrypted medical image sharing
- **Telemedicine:** Video consultation integration
- **SA Voice Dictation:** South African English voice recognition (Vosk)
- **Medical Aid Integration:** Direct medical aid API integration
- **2FA Authentication:** Two-factor authentication support
- **Real-time Collaboration:** Multi-user collaboration features

**API Endpoints:**
- `GET /api/health` - Health check
- `POST /api/auth/login` - Authentication
- `GET /api/nas/devices` - List NAS devices
- `POST /api/nas/import` - Trigger NAS import
- `GET /api/pacs/patients` - Search patients
- `GET /api/pacs/studies` - List studies
- `POST /api/enterprise-pacs/index` - Index NAS
- `GET /api/reporting/reports` - List reports
- `POST /api/reporting/transcribe` - Voice transcription

**Background Services:**
- **NAS Auto-Import:** Runs every 5 minutes (300 seconds)
- **Device Discovery:** Continuous network scanning
- **DICOM Indexing:** Automatic metadata extraction
- **Background Processing:** Async task processing

---

### 5. Medical Reporting Module (`Orthanc/medical-reporting-module/`)

**Purpose:** AI-powered voice-to-text medical dictation

**Key Files:**
```
medical-reporting-module/
├── core/
│   └── app_factory.py             # Flask application factory
├── api/
│   ├── stt_routes.py              # Speech-to-text endpoints
│   └── report_routes.py           # Report management
├── services/
│   ├── whisper_service.py         # OpenAI Whisper integration
│   └── nas_service.py             # NAS storage service
├── models/
│   └── report_model.py            # Report data models
├── templates/
│   └── report_templates/          # Medical report templates
└── requirements.txt               # Python dependencies
```

**Features:**
- Real-time voice-to-text transcription
- Medical terminology recognition
- Report template system
- ICD-10 code suggestions
- HTTPS/TLS encryption
- Offline-capable

**API Endpoints:**
- `POST /api/stt/transcribe` - Transcribe audio to text
- `POST /api/reports/create` - Create new report
- `GET /api/reports/:id` - Retrieve report
- `PUT /api/reports/:id` - Update report
- `POST /api/reports/:id/finalize` - Finalize report

---

### 6. OpenEMR Integration (`openemr/`)

**Purpose:** Electronic medical records and patient management

**Key Components:**
```
openemr/
├── server/                        # Node.js backend
│   ├── database/
│   │   └── prisma/                # Prisma ORM
│   └── routes/
│       ├── patients.js            # Patient management
│       └── claims.js              # Claims processing
├── client/                        # React frontend
├── healthbridge_integration/
│   └── HealthbridgeConnector.php  # HL7 FHIR clearing house
├── fhir_integration/              # FHIR resources
├── sa_ris_integration/            # RIS integration
└── docker-compose.yml             # PostgreSQL + Redis
```

**Integrations:**
- **Healthbridge:** Claims submission and tracking
- **Medical Aid Schemes:** Real-time verification
- **FHIR Server:** Patient resource synchronization
- **SA-RIS:** Radiology order management

---

### 7. Offline DICOM Viewer (`offline-dicom-viewer/`)

**Purpose:** Browser-based DICOM viewer for offline use

**Key Files:**
```
offline-dicom-viewer/
├── index.html                     # Main viewer interface
├── src/
│   ├── dicom-parser.js            # DICOM file parsing
│   ├── image-renderer.js          # Image rendering
│   └── tools/
│       ├── windowing.js           # Window/Level adjustment
│       ├── zoom.js                # Zoom/Pan tools
│       └── measurements.js        # Measurement tools
├── styles/
│   └── viewer.css                 # Viewer styling
└── webpack.config.js              # Build configuration
```

**Features:**
- Drag-and-drop DICOM file loading
- Multi-series viewing
- Window/Level adjustment
- Zoom, pan, rotate
- Measurements (length, angle, ROI)
- Cine playback for multi-frame images
- Export to PNG/JPEG

---


## 🔗 HL7 FHIR Integration

### FHIR Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FHIR Integration Flow                         │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   SA-RIS     │         │    FHIR      │         │  National    │
│   Backend    │◄───────►│  Radiology   │◄───────►│  FHIR Server │
│              │         │   Service    │         │              │
└──────────────┘         └──────────────┘         └──────────────┘
       │                        │                         │
       │                        │                         │
       ▼                        ▼                         ▼
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Orthanc    │         │    FHIR      │         │  Healthbridge│
│   PACS       │         │   Mappings   │         │  Clearing    │
│   (DICOM)    │         │   Database   │         │  House       │
└──────────────┘         └──────────────┘         └──────────────┘
```

### FHIR Resources Implemented

#### 1. Patient Resource
```json
{
  "resourceType": "Patient",
  "identifier": [
    {
      "system": "http://sa.gov.za/id",
      "value": "8001015009087"
    }
  ],
  "name": [
    {
      "family": "Surname",
      "given": ["FirstName"],
      "text": "FirstName Surname"
    }
  ],
  "gender": "male",
  "birthDate": "1980-01-01",
  "address": [
    {
      "country": "ZA",
      "state": "Gauteng",
      "city": "Johannesburg"
    }
  ]
}
```

**Mapping:** `sa_ris_db.fhir_mappings` table links local patient_id to FHIR Patient ID

**Status:** ✅ **IMPLEMENTED**

---

#### 2. ImagingStudy Resource
```json
{
  "resourceType": "ImagingStudy",
  "id": "imaging-study-12345",
  "status": "available",
  "subject": {
    "reference": "Patient/patient-fhir-id"
  },
  "started": "2025-01-15T10:30:00Z",
  "numberOfSeries": 3,
  "numberOfInstances": 150,
  "description": "CT Head without contrast",
  "series": [
    {
      "uid": "1.2.840.113619.2.55.3.2831164605.123.1234567890.1",
      "number": 1,
      "modality": {
        "system": "http://dicom.nema.org/resources/ontology/DCM",
        "code": "CT"
      },
      "description": "Axial Brain",
      "numberOfInstances": 50,
      "bodySite": {
        "system": "http://snomed.info/sct",
        "code": "69536005",
        "display": "Head"
      }
    }
  ],
  "identifier": [
    {
      "system": "urn:dicom:uid",
      "value": "1.2.840.113619.2.55.3.2831164605.123"
    }
  ]
}
```

**Creation Flow:**
1. DICOM study received by Orthanc
2. `OrthancConnector.php` detects new study
3. `FHIRRadiologyService.php` creates ImagingStudy resource
4. Posted to national FHIR server: `https://fhir.sacoronavirus.co.za/r4/ImagingStudy`
5. FHIR ID stored in `fhir_mappings` table

**Status:** ✅ **IMPLEMENTED**

---

#### 3. DiagnosticReport Resource (Planned)

```json
{
  "resourceType": "DiagnosticReport",
  "id": "diagnostic-report-12345",
  "status": "final",
  "category": [
    {
      "coding": [
        {
          "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
          "code": "RAD",
          "display": "Radiology"
        }
      ]
    }
  ],
  "code": {
    "coding": [
      {
        "system": "http://loinc.org",
        "code": "24627-2",
        "display": "CT Head"
      }
    ]
  },
  "subject": {
    "reference": "Patient/patient-fhir-id"
  },
  "effectiveDateTime": "2025-01-15T10:30:00Z",
  "issued": "2025-01-15T14:30:00Z",
  "performer": [
    {
      "reference": "Practitioner/radiologist-id",
      "display": "Dr. Smith, Radiologist"
    }
  ],
  "resultsInterpreter": [
    {
      "reference": "Practitioner/radiologist-id"
    }
  ],
  "imagingStudy": [
    {
      "reference": "ImagingStudy/imaging-study-12345"
    }
  ],
  "conclusion": "No acute intracranial abnormality detected. Normal brain parenchyma.",
  "conclusionCode": [
    {
      "coding": [
        {
          "system": "http://snomed.info/sct",
          "code": "281900007",
          "display": "No abnormality detected"
        }
      ]
    }
  ],
  "presentedForm": [
    {
      "contentType": "application/pdf",
      "url": "https://nas-storage/reports/patient-12345/report.pdf",
      "title": "Radiology Report - CT Head"
    }
  ]
}
```

**Implementation Plan:**
- Automatically create DiagnosticReport when radiology report is finalized
- Link to ImagingStudy and Patient resources
- Include report PDF as presentedForm attachment
- Map ICD-10 codes to SNOMED CT conclusionCode
- Store FHIR ID in `fhir_mappings` table

**Status:** 📋 **PLANNED** - Will be implemented in Phase 2

---

#### 4. Observation Resource (Planned)

```json
{
  "resourceType": "Observation",
  "id": "observation-12345",
  "status": "final",
  "category": [
    {
      "coding": [
        {
          "system": "http://terminology.hl7.org/CodeSystem/observation-category",
          "code": "imaging",
          "display": "Imaging"
        }
      ]
    }
  ],
  "code": {
    "coding": [
      {
        "system": "http://loinc.org",
        "code": "59776-5",
        "display": "Procedure findings Narrative"
      }
    ]
  },
  "subject": {
    "reference": "Patient/patient-fhir-id"
  },
  "effectiveDateTime": "2025-01-15T10:30:00Z",
  "performer": [
    {
      "reference": "Practitioner/radiologist-id"
    }
  ],
  "valueString": "No acute intracranial abnormality detected",
  "interpretation": [
    {
      "coding": [
        {
          "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
          "code": "N",
          "display": "Normal"
        }
      ]
    }
  ],
  "bodySite": {
    "coding": [
      {
        "system": "http://snomed.info/sct",
        "code": "69536005",
        "display": "Head"
      }
    ]
  },
  "method": {
    "coding": [
      {
        "system": "http://snomed.info/sct",
        "code": "77477000",
        "display": "Computerized axial tomography"
      }
    ]
  },
  "derivedFrom": [
    {
      "reference": "ImagingStudy/imaging-study-12345"
    }
  ]
}
```

**Implementation Plan:**
- Create Observation resources for key findings
- Support AI-generated observations with confidence scores
- Link to ImagingStudy and DiagnosticReport
- Enable structured data extraction for analytics
- Support critical findings flagging

**Status:** 📋 **PLANNED** - Will be implemented in Phase 2

---

#### 5. ServiceRequest Resource (Planned)

```json
{
  "resourceType": "ServiceRequest",
  "id": "service-request-12345",
  "status": "completed",
  "intent": "order",
  "category": [
    {
      "coding": [
        {
          "system": "http://snomed.info/sct",
          "code": "363679005",
          "display": "Imaging"
        }
      ]
    }
  ],
  "code": {
    "coding": [
      {
        "system": "http://loinc.org",
        "code": "24627-2",
        "display": "CT Head without contrast"
      }
    ]
  },
  "subject": {
    "reference": "Patient/patient-fhir-id"
  },
  "authoredOn": "2025-01-14T09:00:00Z",
  "requester": {
    "reference": "Practitioner/referring-doctor-id",
    "display": "Dr. Jones, GP"
  },
  "reasonCode": [
    {
      "coding": [
        {
          "system": "http://hl7.org/fhir/sid/icd-10",
          "code": "R51",
          "display": "Headache"
        }
      ]
    }
  ],
  "supportingInfo": [
    {
      "reference": "ImagingStudy/imaging-study-12345"
    }
  ]
}
```

**Implementation Plan:**
- Create ServiceRequest when radiology order is placed
- Link to workflow booking
- Track order status through workflow states
- Enable order tracking and notifications

**Status:** 📋 **PLANNED** - Will be implemented in Phase 2

---

### FHIR Service Implementation

**File:** `sa-ris-backend/FHIRRadiologyService.php`

**Key Methods:**

```php
class FHIRRadiologyService {
    // Create FHIR ImagingStudy from DICOM study
    public function createImagingStudy($studyId, $patientId)
    
    // Ensure patient exists in FHIR server
    public function ensurePatientInFHIR($patientData)
    
    // Get FHIR resource by local ID
    public function getFHIRResource($localId, $resourceType)
    
    // Store FHIR resource mapping
    private function storeFHIRMapping($localId, $fhirId, $resourceType)
}
```

**FHIR Server Configuration:**
```php
$config = [
    'fhir_base_url' => 'https://fhir.sacoronavirus.co.za/r4',
    'fhir_timeout' => 30,
    'fhir_verify_ssl' => true
];
```

---

### Healthbridge HL7 FHIR Integration

**File:** `openemr/healthbridge_integration/HealthbridgeConnector.php`

**Purpose:** Electronic claims submission to South African medical aid schemes

**Key Features:**
- OAuth2 authentication
- Claim submission (single & batch)
- Real-time status tracking
- Payment reconciliation
- Automated remittance processing

**Claim Submission Flow:**
```
1. Generate claim from radiology study
   ↓
2. Format claim in Healthbridge format
   ↓
3. Validate claim data (ICD-10, NRPL codes)
   ↓
4. Submit to Healthbridge API
   ↓
5. Receive acknowledgment & reference number
   ↓
6. Track claim status
   ↓
7. Process payment notification
   ↓
8. Reconcile payment
```

**API Methods:**
```php
class HealthbridgeConnector {
    // Authenticate with Healthbridge
    public function authenticate()
    
    // Submit single claim
    public function submitClaim($claimData)
    
    // Submit batch of claims
    public function submitBatchClaims($claimsData)
    
    // Check claim status
    public function checkClaimStatus($healthbridgeReference)
    
    // Get payment remittance
    public function getRemittanceAdvice($paymentReference)
    
    // Automated reconciliation
    public function processReconciliation($startDate, $endDate)
}
```

---

### FHIR Data Synchronization

**Synchronization Points:**

1. **Patient Registration:**
   - Local patient created in SA-RIS
   - Patient resource created/updated in FHIR server
   - FHIR ID stored in `fhir_mappings` table

2. **Study Completion:**
   - DICOM study received in Orthanc
   - ImagingStudy resource created in FHIR server
   - Study linked to Patient resource

3. **Report Finalization:**
   - Radiology report completed
   - DiagnosticReport resource created (future)
   - Linked to ImagingStudy and Patient

4. **Claim Submission:**
   - Claim generated from study
   - Claim resource created in Healthbridge
   - Status synchronized back to SA-RIS

---


## 📡 DICOM Workflow

### DICOM Network Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DICOM Network Topology                        │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   CT Scanner │         │  MRI Scanner │         │  X-Ray       │
│   AE: CT001  │         │  AE: MRI001  │         │  AE: XR001   │
│   Port: 104  │         │  Port: 104   │         │  Port: 104   │
└──────┬───────┘         └──────┬───────┘         └──────┬───────┘
       │                        │                        │
       │ C-STORE                │ C-STORE                │ C-STORE
       │                        │                        │
       ▼                        ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Orthanc PACS Server                           │
│                    AE: ORTHANC                                   │
│                    Port: 4242 (DICOM)                            │
│                    Port: 8042 (REST API)                         │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  DICOM Services:                                            │ │
│  │  • C-STORE SCP (Receive images)                            │ │
│  │  • C-FIND SCP (Query studies)                              │ │
│  │  • C-MOVE SCP (Retrieve images)                            │ │
│  │  • WADO-RS (Web access)                                    │ │
│  │  • QIDO-RS (Query)                                          │ │
│  │  • STOW-RS (Store)                                          │ │
│  └────────────────────────────────────────────────────────────┘ │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                            │ REST API / DICOMweb
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
       ▼                    ▼                    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  SA-RIS      │     │  Radiology   │     │  DICOM       │
│  Backend     │     │  Workstation │     │  Viewer      │
│              │     │  AE: WS001   │     │  (Browser)   │
└──────────────┘     └──────────────┘     └──────────────┘
```

### DICOM Study Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                    DICOM Study Workflow                          │
└─────────────────────────────────────────────────────────────────┘

1. STUDY ACQUISITION
   ┌──────────────────────────────────────────────────────────┐
   │ Modality → C-STORE → Orthanc                             │
   │ • Patient demographics                                    │
   │ • Study metadata (StudyInstanceUID, Modality, etc.)      │
   │ • Series and instances                                    │
   └──────────────────────────────────────────────────────────┘
                            ↓
2. AUTOMATIC PROCESSING
   ┌──────────────────────────────────────────────────────────┐
   │ Orthanc Python Plugin                                     │
   │ • OnStoredInstance callback                               │
   │ • Extract DICOM tags                                      │
   │ • Store in Orthanc index database                         │
   │ • Trigger SA-RIS notification                             │
   └──────────────────────────────────────────────────────────┘
                            ↓
3. QUALITY ASSESSMENT
   ┌──────────────────────────────────────────────────────────┐
   │ OrthancConnector.assessImageQuality()                     │
   │ • Analyze series quality                                  │
   │ • Check for artifacts                                     │
   │ • Validate protocol compliance                            │
   │ • Flag for repeat if quality < 70%                        │
   └──────────────────────────────────────────────────────────┘
                            ↓
4. WORKFLOW INTEGRATION
   ┌──────────────────────────────────────────────────────────┐
   │ RISWorkflowEngine.processDICOMImages()                    │
   │ • Match study to workflow instance                        │
   │ • Validate patient demographics                           │
   │ • Update workflow state to COMPLETED                      │
   │ • Assign to radiologist                                   │
   └──────────────────────────────────────────────────────────┘
                            ↓
5. FHIR SYNCHRONIZATION
   ┌──────────────────────────────────────────────────────────┐
   │ FHIRRadiologyService.createImagingStudy()                 │
   │ • Create FHIR ImagingStudy resource                       │
   │ • Link to Patient resource                                │
   │ • Post to national FHIR server                            │
   │ • Store FHIR mapping                                      │
   └──────────────────────────────────────────────────────────┘
                            ↓
6. REPORTING
   ┌──────────────────────────────────────────────────────────┐
   │ Medical Reporting Module                                  │
   │ • Radiologist opens study                                 │
   │ • Voice dictation (Whisper AI)                            │
   │ • AI-assisted report generation                           │
   │ • Report finalization                                     │
   └──────────────────────────────────────────────────────────┘
                            ↓
7. BILLING & CLAIMS
   ┌──────────────────────────────────────────────────────────┐
   │ SABillingEngine + HealthbridgeConnector                   │
   │ • Generate billing quote                                  │
   │ • Create claim with NRPL codes                            │
   │ • Submit to medical aid via Healthbridge                  │
   │ • Track payment status                                    │
   └──────────────────────────────────────────────────────────┘
                            ↓
8. ARCHIVAL
   ┌──────────────────────────────────────────────────────────┐
   │ Storage Tiering                                           │
   │ • Online: Recent studies (< 90 days)                      │
   │ • Nearline: Older studies (90-365 days)                   │
   │ • Offline: Archive (> 1 year)                             │
   │ • NAS integration for long-term storage                   │
   └──────────────────────────────────────────────────────────┘
```

### DICOM 2023 Compliance

**File:** `sa-ris-backend/DICOM2023Compliance.php`

**Compliance Checks:**

1. **Metadata Compliance**
   - Required DICOM tags validation
   - DICOM 2023 specific tags
   - Deidentification metadata

2. **Security Compliance**
   - Encryption (AES-256-GCM)
   - Audit trail logging
   - Access control validation
   - Data integrity checks

3. **Worklist Compliance**
   - Scheduled procedure step elements
   - Modality worklist integration
   - Performed procedure step tracking

4. **AI/ML Workflow Compliance**
   - AI algorithm metadata
   - Confidence scores
   - Model version tracking
   - Prediction timestamps

**Validation Example:**
```php
$compliance = $dicomCompliance->validateStudyCompliance($studyId);

// Result:
[
    'study_id' => '12345',
    'compliant' => true,
    'issues' => [],
    'checked_at' => '2025-01-15 10:30:00',
    'dicom_version' => '2023'
]
```

---

### NAS Integration Auto-Import Service

**File:** `Orthanc/orthanc-source/NASIntegration/backend/services/nas_orthanc_importer.py`

**Purpose:** Automatically import DICOM files from NAS storage into Orthanc PACS

**Workflow:**
```
┌─────────────────────────────────────────────────────────────────┐
│              NAS→Orthanc Auto-Import Workflow                    │
└─────────────────────────────────────────────────────────────────┘

1. Background Service Starts (Every 5 minutes)
   ↓
2. Check Orthanc Connectivity
   ├─ Success → Continue
   └─ Failure → Log error, sleep 300 seconds, retry
   ↓
3. Scan NAS Directories for DICOM Files
   ├─ /nas/dicom/
   ├─ /nas/backup/
   └─ Configured NAS paths
   ↓
4. For Each DICOM File Found:
   ├─ Parse DICOM metadata
   ├─ Check if already in Orthanc (StudyInstanceUID)
   ├─ If new → Upload to Orthanc via REST API
   └─ Store metadata in pacs_metadata.db
   ↓
5. Update Import Statistics
   ├─ Files processed
   ├─ Files imported
   ├─ Errors encountered
   └─ Last import timestamp
   ↓
6. Sleep 300 seconds (5 minutes)
   ↓
7. Repeat from step 2
```

**Key Features:**
- **Automatic Discovery:** Scans configured NAS paths
- **Duplicate Detection:** Checks StudyInstanceUID before import
- **Metadata Extraction:** Extracts patient, study, series metadata
- **Error Handling:** Logs errors, continues processing
- **Performance:** Batch processing for efficiency
- **Monitoring:** Real-time import statistics

**Configuration:**
```python
# Environment variables
USE_ORTHANC_INTERNAL_INDEX = false  # Use external metadata DB
ORTHANC_URL = http://localhost:8042
NAS_PATHS = ['/nas/dicom', '/nas/backup']
IMPORT_INTERVAL = 300  # seconds
```

**Database:**
- `pacs_metadata.db` - Stores DICOM metadata for fast searching
- Indexed by PatientID, StudyInstanceUID, StudyDate
- Enables high-performance patient search without Orthanc queries

---

### Orthanc Connector Features

**File:** `sa-ris-backend/OrthancConnector.php`

**Advanced Features:**

1. **Intelligent Patient Matching**
   ```php
   $studies = $orthancConnector->findPatientStudies([
       'patient_id' => '8001015009087',
       'patient_name' => 'SURNAME^FIRSTNAME',
       'date_of_birth' => '1980-01-01'
   ]);
   ```
   - Exact ID matching
   - Name + DOB matching
   - Fuzzy search with confidence scoring
   - Duplicate detection

2. **Study Routing**
   ```php
   $result = $orthancConnector->routeStudyToWorkstation(
       $studyId, 
       'CT', 
       'urgent'
   );
   ```
   - Workstation capability matching
   - Load balancing
   - Urgency-based prioritization
   - Queue management

3. **Image Quality Assessment**
   ```php
   $quality = $orthancConnector->assessImageQuality($studyId);
   ```
   - Automated quality scoring
   - Artifact detection
   - Protocol compliance checking
   - Repeat flagging

4. **Anonymization**
   ```php
   $result = $orthancConnector->anonymizeStudy(
       $studyId, 
       'research'
   );
   ```
   - Minimal, standard, research levels
   - DICOM tag removal/replacement
   - Date shifting
   - Audit logging

5. **Storage Management**
   ```php
   $result = $orthancConnector->manageStorageTiering();
   ```
   - Automatic tiering (online/nearline/offline)
   - Age-based archival
   - Temporary file cleanup
   - Storage optimization

---

### DICOM Tags Mapping

**Key DICOM Tags Used:**

| DICOM Tag | Tag Name | Usage |
|-----------|----------|-------|
| (0010,0020) | PatientID | Patient identification |
| (0010,0010) | PatientName | Patient name |
| (0010,0030) | PatientBirthDate | Date of birth |
| (0010,0040) | PatientSex | Gender |
| (0020,000D) | StudyInstanceUID | Unique study identifier |
| (0020,000E) | SeriesInstanceUID | Unique series identifier |
| (0008,0018) | SOPInstanceUID | Unique instance identifier |
| (0008,0060) | Modality | Imaging modality (CT, MRI, etc.) |
| (0008,0020) | StudyDate | Date of study |
| (0008,0030) | StudyTime | Time of study |
| (0008,0050) | AccessionNumber | Accession number |
| (0008,1030) | StudyDescription | Study description |
| (0008,0090) | ReferringPhysicianName | Referring physician |
| (0018,0015) | BodyPartExamined | Body part |
| (0018,0010) | ContrastBolusAgent | Contrast agent |

**Storage in Database:**
- `dicom_studies` table: Study-level metadata
- `dicom_series` table: Series-level metadata
- Orthanc index database: Complete DICOM tags

---


## 🗄️ Database Architecture

### Database Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Database Architecture                         │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  MySQL 8.0 - SA-RIS Database (sa_ris_db)                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Core Workflow:                                                   │
│  • ris_workflow_instances          (Workflow tracking)           │
│  • ris_workflow_state_log          (State transitions)           │
│                                                                   │
│  Billing & Claims:                                                │
│  • sa_medical_aid_schemes          (Medical aid config)          │
│  • sa_nrpl_codes                   (Billing codes)               │
│  • sa_medical_aid_rates            (Scheme rates)                │
│  • sa_billing_quotes               (Quotes)                      │
│  • sa_claims_submitted             (Claims)                      │
│                                                                   │
│  DICOM Management:                                                │
│  • dicom_studies                   (Study metadata)              │
│  • dicom_series                    (Series metadata)             │
│  • image_quality_assessments       (Quality scores)              │
│                                                                   │
│  Reporting:                                                       │
│  • radiology_reports               (Reports)                     │
│  • ai_analysis_results             (AI findings)                 │
│                                                                   │
│  Users & Equipment:                                               │
│  • radiologists                    (Radiologist profiles)        │
│  • equipment                       (Equipment tracking)          │
│                                                                   │
│  FHIR Integration:                                                │
│  • fhir_mappings                   (Local ID ↔ FHIR ID)          │
│                                                                   │
│  Compliance:                                                      │
│  • patient_consents                (POPI Act consents)           │
│  • popi_audit_trail                (Audit logging)               │
│                                                                   │
│  Analytics:                                                       │
│  • daily_performance_metrics       (Performance tracking)        │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  PostgreSQL 15 - OpenEMR Database (sa_openemr_ris)               │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  • Users                           (System users)                │
│  • Patients                        (Patient demographics)        │
│  • Medical Aid Schemes             (Scheme configuration)        │
│  • Study Orders                    (Radiology orders)            │
│  • Claims                          (Medical aid claims)          │
│  • NRPL Codes                      (Billing codes)               │
│  • ICD-10 Codes                    (Diagnosis codes)             │
│  • Audit Logs                      (System audit trail)          │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  SQLite - Medical Reporting Database (medical_reporting.db)      │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  • reports                         (Medical reports)             │
│  • transcriptions                  (Voice transcripts)           │
│  • report_templates                (Report templates)            │
│  • audit_logs                      (Access logs)                 │
│  • nas_files                       (NAS file tracking)           │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  SQLite - Orthanc Index Database (orthanc.db)                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  • Resources                       (DICOM hierarchy)             │
│  • MainDicomTags                   (Indexed DICOM tags)          │
│  • DicomIdentifiers                (Patient/Study IDs)           │
│  • Metadata                        (Additional metadata)         │
│  • AttachedFiles                   (File storage info)           │
│  • Changes                         (Change tracking)             │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Key Database Tables

#### 1. ris_workflow_instances

**Purpose:** Track radiology workflow from booking to delivery

```sql
CREATE TABLE ris_workflow_instances (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    booking_id BIGINT NOT NULL,
    patient_id BIGINT NOT NULL,
    examination_type VARCHAR(50) NOT NULL,
    urgency ENUM('routine', 'urgent', 'stat') DEFAULT 'routine',
    current_state VARCHAR(50) NOT NULL DEFAULT 'BOOKED',
    previous_state VARCHAR(50),
    estimated_completion DATETIME,
    actual_completion DATETIME,
    assigned_radiologist_id BIGINT,
    assigned_technologist_id BIGINT,
    study_instance_uid VARCHAR(255),
    progress_percentage TINYINT DEFAULT 0,
    patient_satisfaction_score TINYINT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**Workflow States:**
- BOOKED → REGISTERED → IN_PROGRESS → COMPLETED → PRELIMINARY_READ → FINAL_REPORT → DELIVERED → ARCHIVED

---

#### 2. dicom_studies

**Purpose:** Store DICOM study metadata and link to workflows

```sql
CREATE TABLE dicom_studies (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    workflow_id BIGINT,
    study_instance_uid VARCHAR(255) UNIQUE NOT NULL,
    patient_id VARCHAR(100),
    patient_name VARCHAR(255),
    patient_birth_date DATE,
    study_date DATE,
    study_time TIME,
    accession_number VARCHAR(100),
    modality VARCHAR(10),
    study_description TEXT,
    referring_physician VARCHAR(255),
    images_count INT DEFAULT 0,
    series_count INT DEFAULT 0,
    study_size_mb DECIMAL(10,2),
    storage_location VARCHAR(255),
    storage_tier ENUM('online', 'nearline', 'offline') DEFAULT 'online',
    quality_score TINYINT,
    quality_issues TEXT,
    processing_status ENUM('received', 'processing', 'complete', 'error'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES ris_workflow_instances(id)
);
```

---

#### 3. sa_nrpl_codes

**Purpose:** National Reference Price List codes for billing

```sql
CREATE TABLE sa_nrpl_codes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nrpl_code VARCHAR(10) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50),
    modality VARCHAR(20),
    body_part VARCHAR(100),
    contrast_type ENUM('none', 'oral', 'iv', 'both'),
    base_price DECIMAL(10,2) NOT NULL,
    effective_date DATE NOT NULL,
    expiry_date DATE,
    active BOOLEAN DEFAULT TRUE
);
```

**Sample Data:**
| nrpl_code | description | modality | base_price |
|-----------|-------------|----------|------------|
| 3011 | CT Head without contrast | CT | 1850.00 |
| 3012 | CT Head with contrast | CT | 2450.00 |
| 3021 | MRI Brain without contrast | MRI | 4500.00 |
| 3001 | Chest X-Ray PA | XRAY | 320.00 |

---

#### 4. fhir_mappings

**Purpose:** Map local IDs to FHIR resource IDs

```sql
CREATE TABLE fhir_mappings (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    local_id VARCHAR(100) NOT NULL,
    fhir_id VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_mapping (local_id, resource_type)
);
```

**Example Mappings:**
| local_id | fhir_id | resource_type |
|----------|---------|---------------|
| 12345 | patient-abc123 | Patient |
| study-67890 | imaging-study-xyz789 | ImagingStudy |

---

#### 5. radiology_reports

**Purpose:** Store radiology reports with AI assistance tracking

```sql
CREATE TABLE radiology_reports (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    workflow_id BIGINT NOT NULL,
    study_id BIGINT NOT NULL,
    report_type ENUM('preliminary', 'final', 'amended', 'addendum'),
    template_id INT,
    clinical_indication TEXT,
    technique TEXT,
    findings TEXT NOT NULL,
    impression TEXT NOT NULL,
    recommendations TEXT,
    critical_findings TEXT,
    follow_up_required BOOLEAN DEFAULT FALSE,
    follow_up_timeframe VARCHAR(50),
    ai_assisted BOOLEAN DEFAULT FALSE,
    ai_confidence_score DECIMAL(3,2),
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_by VARCHAR(100),
    approved_at TIMESTAMP,
    delivered_at TIMESTAMP,
    status ENUM('draft', 'pending_approval', 'approved', 'delivered'),
    FOREIGN KEY (workflow_id) REFERENCES ris_workflow_instances(id),
    FOREIGN KEY (study_id) REFERENCES dicom_studies(id)
);
```

---

### Database Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                    Entity Relationship Diagram                   │
└─────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │    Patients      │
                    │  (OpenEMR DB)    │
                    └────────┬─────────┘
                             │
                             │ 1:N
                             │
                    ┌────────▼─────────┐
                    │  ris_workflow_   │
                    │   instances      │
                    └────────┬─────────┘
                             │
                ┌────────────┼────────────┐
                │            │            │
                │ 1:1        │ 1:1        │ 1:N
                │            │            │
        ┌───────▼──────┐ ┌──▼──────┐ ┌──▼──────────┐
        │ dicom_studies│ │ billing │ │  workflow   │
        │              │ │ quotes  │ │  state_log  │
        └───────┬──────┘ └──┬──────┘ └─────────────┘
                │            │
                │ 1:N        │ 1:1
                │            │
        ┌───────▼──────┐ ┌──▼──────────┐
        │ dicom_series │ │   claims    │
        │              │ │  submitted  │
        └───────┬──────┘ └─────────────┘
                │
                │ 1:N
                │
        ┌───────▼──────────┐
        │   radiology_     │
        │    reports       │
        └──────────────────┘
```

---

### Database Indexes & Performance

**Critical Indexes:**

```sql
-- Workflow queries
CREATE INDEX idx_workflow_patient_date 
ON ris_workflow_instances (patient_id, created_at);

CREATE INDEX idx_workflow_state_urgency_exam 
ON ris_workflow_instances (current_state, urgency, examination_type);

-- DICOM queries
CREATE INDEX idx_studies_patient_date 
ON dicom_studies (patient_id, study_date);

CREATE INDEX idx_study_instance_uid 
ON dicom_studies (study_instance_uid);

-- Billing queries
CREATE INDEX idx_claims_scheme_status_date 
ON sa_claims_submitted (medical_aid_scheme_id, status, submission_date);

-- FHIR mappings
CREATE INDEX idx_fhir_local_id 
ON fhir_mappings (local_id, resource_type);
```

**Performance Optimizations:**
- Composite indexes for common query patterns
- Partitioning for large tables (by date)
- Read replicas for reporting queries
- Connection pooling
- Query caching

---


## 🔄 Integration Points & Data Flow

### Complete Patient Journey Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              Complete Patient Journey - Data Flow                │
└─────────────────────────────────────────────────────────────────┘

STEP 1: PATIENT REGISTRATION
┌──────────────────────────────────────────────────────────────────┐
│ OpenEMR Frontend → OpenEMR API → PostgreSQL                      │
│                                                                   │
│ Data Created:                                                     │
│ • Patient demographics                                            │
│ • Medical aid details                                             │
│ • Contact information                                             │
│                                                                   │
│ Triggers:                                                         │
│ • FHIR Patient resource creation                                  │
│ • Medical aid verification (real-time)                            │
└──────────────────────────────────────────────────────────────────┘
                            ↓
STEP 2: RADIOLOGY BOOKING
┌──────────────────────────────────────────────────────────────────┐
│ SA-RIS Dashboard → SA-RIS API → MySQL                            │
│                                                                   │
│ Data Created:                                                     │
│ • Workflow instance (state: BOOKED)                               │
│ • Examination details                                             │
│ • Urgency level                                                   │
│ • Clinical indication                                             │
│                                                                   │
│ Triggers:                                                         │
│ • Billing quote generation                                        │
│ • Patient SMS notification                                        │
│ • Equipment scheduling                                            │
└──────────────────────────────────────────────────────────────────┘
                            ↓
STEP 3: IMAGE ACQUISITION
┌──────────────────────────────────────────────────────────────────┐
│ Modality → DICOM C-STORE → Orthanc PACS                          │
│                                                                   │
│ Data Created:                                                     │
│ • DICOM study (StudyInstanceUID)                                  │
│ • Series and instances                                            │
│ • DICOM tags (patient, study metadata)                            │
│                                                                   │
│ Storage:                                                          │
│ • Orthanc index database (SQLite)                                 │
│ • NAS storage (DICOM files)                                       │
│                                                                   │
│ Triggers:                                                         │
│ • OnStoredInstance Python callback                                │
│ • Quality assessment                                              │
│ • Workflow state update (COMPLETED)                               │
└──────────────────────────────────────────────────────────────────┘
                            ↓
STEP 4: DICOM PROCESSING
┌──────────────────────────────────────────────────────────────────┐
│ Orthanc → OrthancConnector → SA-RIS API → MySQL                  │
│                                                                   │
│ Processing:                                                       │
│ • Extract DICOM metadata                                          │
│ • Patient matching (fuzzy logic)                                  │
│ • Quality assessment                                              │
│ • Store in dicom_studies table                                    │
│                                                                   │
│ Data Flow:                                                        │
│ Orthanc REST API → OrthancConnector.php → MySQL                  │
│                                                                   │
│ Triggers:                                                         │
│ • FHIR ImagingStudy creation                                      │
│ • Radiologist assignment                                          │
│ • Notification to radiologist                                     │
└──────────────────────────────────────────────────────────────────┘
                            ↓
STEP 5: FHIR SYNCHRONIZATION
┌──────────────────────────────────────────────────────────────────┐
│ SA-RIS API → FHIRRadiologyService → National FHIR Server          │
│                                                                   │
│ FHIR Resources Created:                                           │
│ • Patient (if not exists)                                         │
│ • ImagingStudy                                                    │
│                                                                   │
│ Data Flow:                                                        │
│ MySQL → FHIRRadiologyService.php → HTTPS POST →                  │
│ https://fhir.sacoronavirus.co.za/r4/ImagingStudy                 │
│                                                                   │
│ Mapping Storage:                                                  │
│ • fhir_mappings table (local_id ↔ fhir_id)                       │
└──────────────────────────────────────────────────────────────────┘
                            ↓
STEP 6: MEDICAL REPORTING
┌──────────────────────────────────────────────────────────────────┐
│ Medical Reporting Module → Flask API → SQLite                    │
│                                                                   │
│ Reporting Flow:                                                   │
│ 1. Radiologist opens study in viewer                              │
│ 2. Voice dictation (microphone → WebRTC → Flask)                 │
│ 3. Whisper AI transcription (audio → text)                        │
│ 4. AI-assisted report generation                                  │
│ 5. Report finalization                                            │
│                                                                   │
│ Data Created:                                                     │
│ • Transcription (SQLite: medical_reporting.db)                    │
│ • Report draft                                                    │
│ • Final report (MySQL: radiology_reports)                         │
│                                                                   │
│ Storage:                                                          │
│ • Audio files → NAS                                               │
│ • Report PDF → NAS                                                │
│                                                                   │
│ Triggers:                                                         │
│ • Workflow state update (FINAL_REPORT)                            │
│ • Critical findings alert (if applicable)                         │
│ • Report delivery notification                                    │
└──────────────────────────────────────────────────────────────────┘
                            ↓
STEP 7: BILLING & CLAIMS
┌──────────────────────────────────────────────────────────────────┐
│ SA-RIS API → SABillingEngine → HealthbridgeConnector → Medical Aid│
│                                                                   │
│ Billing Flow:                                                     │
│ 1. Generate billing quote (NRPL codes)                            │
│ 2. Medical aid rate calculation                                   │
│ 3. Patient portion calculation                                    │
│ 4. Claim generation                                               │
│ 5. Healthbridge submission (HL7 FHIR)                             │
│                                                                   │
│ Data Created:                                                     │
│ • sa_billing_quotes                                               │
│ • sa_claims_submitted                                             │
│                                                                   │
│ External Integration:                                             │
│ HealthbridgeConnector.php → HTTPS POST →                          │
│ Healthbridge API → Medical Aid Scheme                             │
│                                                                   │
│ Triggers:                                                         │
│ • Claim status tracking                                           │
│ • Payment reconciliation                                          │
│ • Workflow state update (DELIVERED)                               │
└──────────────────────────────────────────────────────────────────┘
                            ↓
STEP 8: ARCHIVAL & ANALYTICS
┌──────────────────────────────────────────────────────────────────┐
│ Storage Tiering + Performance Metrics                             │
│                                                                   │
│ Archival:                                                         │
│ • Online storage (< 90 days)                                      │
│ • Nearline storage (90-365 days)                                  │
│ • Offline archive (> 1 year)                                      │
│                                                                   │
│ Analytics:                                                        │
│ • Daily performance metrics                                       │
│ • Workflow efficiency analysis                                    │
│ • Financial reporting                                             │
│ • Quality metrics                                                 │
│                                                                   │
│ Data Storage:                                                     │
│ • daily_performance_metrics table                                 │
│ • Analytics views                                                 │
└──────────────────────────────────────────────────────────────────┘
```

---

### Integration Point Details

#### 1. Orthanc ↔ SA-RIS Integration

**Connection Method:** REST API + Python Callbacks

**Data Flow:**
```
Orthanc Python Plugin (OnStoredInstance)
    ↓
Extract DICOM metadata
    ↓
HTTP POST to SA-RIS API
    ↓
OrthancConnector.php processes study
    ↓
Store in MySQL (dicom_studies table)
    ↓
Trigger workflow update
```

**API Endpoints:**
- `GET /api/dicom/studies` - List studies
- `GET /api/dicom/studies/:id` - Get study details
- `POST /api/dicom/process` - Process new study
- `GET /api/dicom/quality/:id` - Quality assessment

---

#### 2. SA-RIS ↔ FHIR Server Integration

**Connection Method:** HTTPS REST API (HL7 FHIR v4.0+)

**Data Flow:**
```
SA-RIS detects completed study
    ↓
FHIRRadiologyService.php
    ↓
Create FHIR ImagingStudy resource
    ↓
POST to https://fhir.sacoronavirus.co.za/r4/ImagingStudy
    ↓
Store FHIR ID in fhir_mappings table
```

**FHIR Operations:**
- `POST /Patient` - Create patient
- `GET /Patient?identifier=...` - Search patient
- `POST /ImagingStudy` - Create imaging study
- `GET /ImagingStudy/:id` - Retrieve study

---

#### 3. OpenEMR ↔ Healthbridge Integration

**Connection Method:** HTTPS REST API (OAuth2)

**Data Flow:**
```
Radiology study completed
    ↓
Generate billing quote (SABillingEngine.php)
    ↓
Create claim with NRPL codes
    ↓
HealthbridgeConnector.php
    ↓
OAuth2 authentication
    ↓
POST claim to Healthbridge API
    ↓
Receive acknowledgment
    ↓
Track claim status
    ↓
Process payment notification
```

**Healthbridge API Endpoints:**
- `POST /auth/token` - Authentication
- `POST /claims/submit` - Submit claim
- `POST /claims/batch-submit` - Batch submission
- `GET /claims/status/:ref` - Check status
- `GET /payments/remittance/:ref` - Get remittance

---

#### 4. Medical Reporting ↔ NAS Integration

**Connection Method:** File System / SMB

**Data Flow:**
```
Voice dictation audio
    ↓
Whisper AI transcription
    ↓
Report generation
    ↓
Save to NAS:
  - Audio: /nas/audio/{patient_id}/{study_id}/
  - Reports: /nas/reports/{patient_id}/{study_id}/
  - DICOM: /nas/dicom/{study_uid}/
    ↓
Track in nas_files table
```

**NAS Directory Structure:**
```
/nas/
├── dicom/
│   └── {StudyInstanceUID}/
│       ├── series-1/
│       │   ├── instance-1.dcm
│       │   └── instance-2.dcm
│       └── series-2/
├── reports/
│   └── {patient_id}/
│       └── {study_id}/
│           ├── report.pdf
│           └── report.docx
└── audio/
    └── {patient_id}/
        └── {study_id}/
            └── dictation.webm
```

---

### Real-Time Communication

**Technology:** Socket.io (WebSocket)

**Events:**
```javascript
// Client subscribes to workflow updates
socket.on('workflow:updated', (data) => {
    // Update dashboard in real-time
});

// Server emits workflow changes
io.emit('workflow:updated', {
    workflow_id: 12345,
    current_state: 'COMPLETED',
    progress: 75
});

// Critical findings alert
io.emit('critical:finding', {
    study_id: 67890,
    finding: 'Acute intracranial hemorrhage',
    urgency: 'stat'
});
```

**Real-Time Features:**
- Workflow state changes
- New study arrivals
- Critical findings alerts
- Radiologist assignments
- Claim status updates
- Equipment status changes

---


## 🔒 Security & Compliance

### POPI Act Compliance (Protection of Personal Information)

**Implementation:**

1. **Consent Management**
   ```sql
   CREATE TABLE patient_consents (
       patient_id BIGINT NOT NULL,
       consent_type ENUM('data_processing', 'data_sharing', 'research', 'teaching'),
       consent_given BOOLEAN NOT NULL,
       consent_date TIMESTAMP,
       withdrawal_date TIMESTAMP NULL,
       consent_document_path VARCHAR(255)
   );
   ```

2. **Audit Trail**
   ```sql
   CREATE TABLE popi_audit_trail (
       patient_id BIGINT,
       user_id INT NOT NULL,
       action_type ENUM('access', 'modify', 'delete', 'export', 'share'),
       table_name VARCHAR(100),
       record_id BIGINT,
       old_values JSON,
       new_values JSON,
       ip_address VARCHAR(45),
       action_timestamp TIMESTAMP
   );
   ```

3. **Data Encryption**
   - **At Rest:** AES-256 encryption for sensitive data
   - **In Transit:** TLS 1.3 for all API communications
   - **Database:** Encrypted columns for PII

4. **Access Control**
   - Role-based access control (RBAC)
   - Minimum necessary access principle
   - Session timeout (30 minutes)
   - Multi-factor authentication (MFA) support

---

### DICOM Security

**DICOM 2023 Security Profiles:**

1. **Secure Transport Connection Profile**
   - TLS 1.3 for DICOM communications
   - Certificate-based authentication
   - Encrypted DICOM transfers

2. **Audit Trail Profile**
   - All DICOM operations logged
   - User identification
   - Access timestamps
   - Action tracking (C-STORE, C-FIND, C-MOVE)

3. **De-identification Profile**
   - Automated anonymization
   - Configurable anonymization levels
   - Audit trail for anonymization

**Implementation:**
```php
// DICOM 2023 security validation
$securityCompliance = $this->checkSecurityCompliance($study);

// Checks:
// - Encryption metadata
// - Audit trail enabled
// - Access control validation
// - Data integrity verification
```

---

### HL7 FHIR Security

**OAuth 2.0 Authentication:**
```php
// Healthbridge authentication
$response = $this->apiClient->post('/auth/token', [
    'json' => [
        'client_id' => $config['client_id'],
        'client_secret' => $config['client_secret'],
        'grant_type' => 'client_credentials',
        'scope' => 'claims:submit claims:status'
    ]
]);
```

**FHIR Security:**
- OAuth 2.0 bearer tokens
- Token expiration and refresh
- Scope-based access control
- HTTPS only communications

---

### Network Security

**Firewall Rules:**
```
Allowed Inbound:
- Port 443 (HTTPS) - Web access
- Port 8042 (Orthanc REST API) - Internal only
- Port 4242 (DICOM) - Modality network only
- Port 3001 (SA-RIS API) - Internal only
- Port 5443 (Medical Reporting) - HTTPS only

Blocked:
- All other ports
- Direct database access from external networks
```

**Network Segmentation:**
```
┌─────────────────────────────────────────────────────────────┐
│                    Network Architecture                      │
└─────────────────────────────────────────────────────────────┘

Internet
    │
    │ HTTPS (443)
    │
┌───▼──────────────────────────────────────────────────────────┐
│  DMZ - Cloudflare Tunnel                                     │
│  • Public access                                             │
│  • DDoS protection                                           │
│  • SSL termination                                           │
└───┬──────────────────────────────────────────────────────────┘
    │
    │ Firewall
    │
┌───▼──────────────────────────────────────────────────────────┐
│  Application Network (VLAN 10)                               │
│  • SA-RIS Frontend (3000)                                    │
│  • SA-RIS API (3001)                                         │
│  • Medical Reporting (5443)                                  │
│  • OpenEMR (8080)                                            │
└───┬──────────────────────────────────────────────────────────┘
    │
    │ Firewall
    │
┌───▼──────────────────────────────────────────────────────────┐
│  PACS Network (VLAN 20)                                      │
│  • Orthanc PACS (8042, 4242)                                 │
│  • DICOM Viewer (5000)                                       │
│  • Modalities (CT, MRI, X-Ray)                               │
└───┬──────────────────────────────────────────────────────────┘
    │
    │ Firewall
    │
┌───▼──────────────────────────────────────────────────────────┐
│  Data Network (VLAN 30)                                      │
│  • MySQL (3306)                                              │
│  • PostgreSQL (5432)                                         │
│  • Redis (6379)                                              │
│  • NAS Storage                                               │
└──────────────────────────────────────────────────────────────┘
```

---

### Backup & Disaster Recovery

**Backup Strategy:**

1. **Database Backups**
   - Full backup: Daily at 2:00 AM
   - Incremental backup: Every 6 hours
   - Retention: 30 days online, 1 year archive
   - Encryption: AES-256

2. **DICOM Image Backups**
   - Continuous replication to secondary NAS
   - Weekly backup to offline storage
   - Retention: 7 years (legal requirement)

3. **Configuration Backups**
   - Daily backup of all configuration files
   - Version control (Git)
   - Retention: Indefinite

**Disaster Recovery:**
- RTO (Recovery Time Objective): 4 hours
- RPO (Recovery Point Objective): 6 hours
- Hot standby database server
- Automated failover for critical services

---

### Compliance Standards

**Standards Implemented:**

1. **HL7 FHIR v4.0+**
   - Patient resource
   - ImagingStudy resource
   - DiagnosticReport resource (planned)
   - Observation resource (planned)

2. **DICOM 2023**
   - Core DICOM services (C-STORE, C-FIND, C-MOVE)
   - DICOMweb (WADO-RS, QIDO-RS, STOW-RS)
   - Security profiles
   - AI/ML workflow support

3. **ICD-10 (South African)**
   - Complete ICD-10 code database
   - Validation on report creation
   - Integration with billing

4. **NRPL (National Reference Price List)**
   - Current tariff codes
   - Medical aid scheme rates
   - Automated billing calculations

5. **POPI Act**
   - Consent management
   - Audit trail
   - Data encryption
   - Access control

6. **WCAG 2.1 AA**
   - Keyboard navigation
   - Screen reader support
   - High contrast mode
   - Multi-language support

---


## 🚀 Deployment Architecture

### Docker Deployment

**Container Architecture:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Container Stack                        │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  Frontend Containers                                             │
├──────────────────────────────────────────────────────────────────┤
│  • sa-ris-frontend:latest        (React, Port 3000)              │
│  • medical-reporting-ui:latest   (Flask, Port 5443)              │
│  • dicom-viewer:latest           (Static, Port 5000)             │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  Application Containers                                          │
├──────────────────────────────────────────────────────────────────┤
│  • sa-ris-backend:latest         (Node.js, Port 3001)            │
│  • openemr-server:latest         (Node.js, Port 3001)            │
│  • medical-reporting-api:latest  (Python/Flask, Port 5000)       │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  PACS Container                                                  │
├──────────────────────────────────────────────────────────────────┤
│  • orthanc:latest                (C++, Ports 8042, 4242)         │
│    - orthanc-dicomweb plugin                                     │
│    - orthanc-python plugin                                       │
│    - orthanc-ohif plugin                                         │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  Database Containers                                             │
├──────────────────────────────────────────────────────────────────┤
│  • mysql:8.0                     (Port 3306)                     │
│  • postgres:15-alpine            (Port 5432)                     │
│  • redis:7-alpine                (Port 6379)                     │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  Reverse Proxy                                                   │
├──────────────────────────────────────────────────────────────────┤
│  • nginx:alpine                  (Ports 80, 443)                 │
│    - SSL termination                                             │
│    - Load balancing                                              │
│    - Static file serving                                         │
└──────────────────────────────────────────────────────────────────┘
```

---

### Docker Compose Configuration

**File:** `docker-compose.yml` (Production)

```yaml
version: '3.8'

services:
  # SA-RIS Backend
  sa-ris-backend:
    build: ./sa-ris-backend
    container_name: sa-ris-backend
    ports:
      - "3001:3001"
    environment:
      - NODE_ENV=production
      - MYSQL_HOST=mysql
      - MYSQL_DATABASE=sa_ris_db
      - ORTHANC_URL=http://orthanc:8042
      - FHIR_BASE_URL=https://fhir.sacoronavirus.co.za/r4
    depends_on:
      - mysql
      - redis
      - orthanc
    networks:
      - app-network
    restart: unless-stopped

  # Orthanc PACS
  orthanc:
    image: jodogne/orthanc:latest
    container_name: orthanc-pacs
    ports:
      - "8042:8042"  # REST API
      - "4242:4242"  # DICOM
    volumes:
      - orthanc-db:/var/lib/orthanc/db
      - orthanc-storage:/var/lib/orthanc/storage
      - ./Orthanc/orthanc.json:/etc/orthanc/orthanc.json
    environment:
      - ORTHANC_USERNAME=orthanc
      - ORTHANC_PASSWORD=${ORTHANC_PASSWORD}
    networks:
      - app-network
      - pacs-network
    restart: unless-stopped

  # MySQL Database
  mysql:
    image: mysql:8.0
    container_name: sa-ris-mysql
    ports:
      - "3306:3306"
    environment:
      - MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - MYSQL_DATABASE=sa_ris_db
      - MYSQL_USER=sa_ris_user
      - MYSQL_PASSWORD=${MYSQL_PASSWORD}
    volumes:
      - mysql-data:/var/lib/mysql
      - ./sa-ris-backend/database_schema.sql:/docker-entrypoint-initdb.d/schema.sql
    networks:
      - data-network
    restart: unless-stopped

  # PostgreSQL (OpenEMR)
  postgres:
    image: postgres:15-alpine
    container_name: openemr-postgres
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=sa_openemr_ris
      - POSTGRES_USER=openemr_user
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - data-network
    restart: unless-stopped

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: sa-ris-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - app-network
    restart: unless-stopped

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: sa-ris-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - ./sa-ris-frontend/build:/usr/share/nginx/html
    depends_on:
      - sa-ris-backend
      - orthanc
    networks:
      - app-network
    restart: unless-stopped

volumes:
  mysql-data:
  postgres-data:
  redis-data:
  orthanc-db:
  orthanc-storage:

networks:
  app-network:
    driver: bridge
  pacs-network:
    driver: bridge
  data-network:
    driver: bridge
```

---

### Startup Scripts

**Windows:** `start_system.bat`
```batch
@echo off
echo Starting Ubuntu Patient Care System...

REM Start Docker containers
cd sa-ris-backend
docker-compose up -d

REM Wait for services to be ready
timeout /t 10

REM Check service health
powershell -NoProfile -Command "./check_orthanc.ps1"
powershell -NoProfile -Command "./check_openemr.ps1"

echo System started successfully!
echo.
echo Access points:
echo - SA-RIS Dashboard: http://localhost:3000
echo - Medical Reporting: https://localhost:5443
echo - Orthanc PACS: http://localhost:8042
echo - OpenEMR: http://localhost:8080
echo.
pause
```

**Linux:** `start_system.sh`
```bash
#!/bin/bash

echo "Starting Ubuntu Patient Care System..."

# Start Docker containers
cd sa-ris-backend
docker-compose up -d

# Wait for services
sleep 10

# Check service health
./check_orthanc.sh
./check_openemr.sh

echo "System started successfully!"
echo ""
echo "Access points:"
echo "- SA-RIS Dashboard: http://localhost:3000"
echo "- Medical Reporting: https://localhost:5443"
echo "- Orthanc PACS: http://localhost:8042"
echo "- OpenEMR: http://localhost:8080"
```

---

### Production Deployment Checklist

**Pre-Deployment:**
- [ ] Update all environment variables
- [ ] Generate SSL certificates
- [ ] Configure firewall rules
- [ ] Set up backup schedules
- [ ] Configure monitoring
- [ ] Test disaster recovery procedures

**Deployment Steps:**
1. Clone repository
2. Configure environment files (.env)
3. Generate SSL certificates
4. Build Docker images
5. Initialize databases
6. Start containers
7. Verify all services
8. Configure reverse proxy
9. Set up monitoring
10. Test all integrations

**Post-Deployment:**
- [ ] Verify DICOM connectivity
- [ ] Test FHIR integration
- [ ] Validate Healthbridge connection
- [ ] Check backup automation
- [ ] Monitor system performance
- [ ] Review security logs

---

### Monitoring & Logging

**Logging Strategy:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Logging Architecture                          │
└─────────────────────────────────────────────────────────────────┘

Application Logs
    ↓
┌──────────────────────────────────────────────────────────────────┐
│  Log Aggregation                                                 │
│  • Winston (Node.js)                                             │
│  • Python logging                                                │
│  • Orthanc logs                                                  │
└──────────────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────────────┐
│  Log Storage                                                     │
│  • /var/log/sa-ris/                                              │
│  • /var/log/orthanc/                                             │
│  • /var/log/fhir/                                                │
│  • /var/log/healthbridge/                                        │
└──────────────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────────────┐
│  Log Analysis                                                    │
│  • Error tracking                                                │
│  • Performance monitoring                                        │
│  • Security auditing                                             │
│  • Compliance reporting                                          │
└──────────────────────────────────────────────────────────────────┘
```

**Log Levels:**
- ERROR: System errors requiring immediate attention
- WARN: Warning conditions
- INFO: Informational messages
- DEBUG: Detailed debugging information

**Monitoring Metrics:**
- System uptime
- API response times
- Database query performance
- DICOM transfer rates
- Storage utilization
- Active workflows
- User sessions
- Error rates

---

### Scaling Considerations

**Horizontal Scaling:**

```
Load Balancer (Nginx)
    │
    ├─── SA-RIS Backend Instance 1
    ├─── SA-RIS Backend Instance 2
    └─── SA-RIS Backend Instance 3
```

**Database Scaling:**
- Read replicas for reporting queries
- Connection pooling
- Query optimization
- Partitioning large tables

**Storage Scaling:**
- Tiered storage (online/nearline/offline)
- Distributed file system
- Cloud storage integration (optional)
- Automated archival

**PACS Scaling:**
- Multiple Orthanc instances
- Load balancing for DICOM services
- Distributed storage
- Caching layer

---

## 📊 System Metrics & Performance

### Expected Performance

**Throughput:**
- DICOM studies: 100-500 per day
- Reports generated: 50-200 per day
- Claims submitted: 50-150 per day
- Concurrent users: 10-50

**Response Times:**
- API endpoints: < 200ms (95th percentile)
- DICOM image retrieval: < 2 seconds
- Report generation: < 30 seconds
- FHIR synchronization: < 1 second

**Storage Requirements:**
- DICOM images: 50-200 GB per month
- Database: 5-10 GB per year
- Backups: 3x primary storage
- Total: 1-2 TB for first year

---

## 🎯 Future Enhancements

**Planned Features:**

1. **AI/ML Integration**
   - Automated image analysis
   - Abnormality detection
   - Report quality scoring
   - Predictive analytics

2. **Mobile Applications**
   - iOS/Android apps
   - Push notifications
   - Mobile image viewing
   - Voice dictation on mobile

3. **Advanced Analytics**
   - Business intelligence dashboard
   - Predictive modeling
   - Resource optimization
   - Financial forecasting

4. **Telemedicine Integration**
   - Video consultations
   - Remote reporting
   - Second opinion workflow
   - Patient portal

5. **Multi-Site Support**
   - Centralized PACS
   - Distributed workflows
   - Cross-site reporting
   - Consolidated billing

---

## 📚 References & Documentation

**Standards:**
- HL7 FHIR: https://www.hl7.org/fhir/
- DICOM: https://www.dicomstandard.org/
- ICD-10: https://www.who.int/classifications/icd/
- POPI Act: https://popia.co.za/

**Technologies:**
- Orthanc: https://www.orthanc-server.com/
- OpenEMR: https://www.open-emr.org/
- React: https://react.dev/
- Node.js: https://nodejs.org/

**Project Documentation:**
- Main README: `README.md`
- Integration Guide: `README_INTEGRATION.md`
- Running Guide: `RUNNING.md`
- OpenEMR README: `openemr/README.md`
- SA-RIS Backend: `sa-ris-backend/README.md`

---

## 📞 Support & Contact

**For Technical Support:**
- GitHub Issues: https://github.com/Jobeer1/Ubuntu-Patient-Care/issues
- Email: support@ubuntu-patient-care.com

**For Contributions:**
- Fork the repository
- Create feature branch
- Submit pull request
- Follow coding standards

---

---

## ✅ Implementation Status Summary

### Fully Implemented Components

**Core Infrastructure:**
- ✅ SA-RIS Backend (Node.js/PHP) - Workflow, billing, DICOM integration
- ✅ SA-RIS Frontend (React) - Dashboard, multi-language, accessibility
- ✅ Orthanc PACS - DICOM server with full C-STORE/C-FIND/C-MOVE
- ✅ NAS Integration Backend (Flask) - Auto-import, device discovery, PACS API
- ✅ Medical Reporting Module (Flask) - Voice dictation, report generation
- ✅ OpenEMR Integration - Patient management, claims processing
- ✅ Offline DICOM Viewer - Browser-based image viewing

**HL7 FHIR Integration:**
- ✅ Patient Resource - Create, read, search
- ✅ ImagingStudy Resource - Automatic creation from DICOM
- ✅ FHIR Mappings - Local ID ↔ FHIR ID tracking
- ✅ National FHIR Server Integration - https://fhir.sacoronavirus.co.za/r4
- ✅ Healthbridge Connector - Claims submission via HL7 FHIR

**DICOM Workflow:**
- ✅ DICOM 2023 Compliance - Validation and security profiles
- ✅ Orthanc Connector - Advanced patient matching, quality assessment
- ✅ NAS→Orthanc Auto-Import - Background service (5-minute intervals)
- ✅ Multi-NAS Support - Enterprise PACS indexing
- ✅ Storage Tiering - Online/nearline/offline archival

**South African Features:**
- ✅ Medical Aid Integration - Discovery, Momentum, Bonitas, GEMS, Bestmed
- ✅ NRPL Billing Codes - Complete tariff database
- ✅ ICD-10 Codes - South African code set
- ✅ POPI Act Compliance - Consent management, audit trail
- ✅ Multi-language Support - English, Afrikaans, Zulu
- ✅ SA Voice Dictation - Vosk model for South African English

**Advanced Features:**
- ✅ Real-time Updates - Socket.io for live notifications
- ✅ Device Discovery - Automatic network device detection
- ✅ 2FA Authentication - Two-factor authentication support
- ✅ Telemedicine Integration - Video consultation support
- ✅ Secure Sharing - Encrypted medical image sharing
- ✅ AI-Assisted Reporting - Whisper AI transcription

---

### Planned Components (Phase 2)

**HL7 FHIR Resources:**
- 📋 DiagnosticReport Resource - Radiology report as FHIR resource
- 📋 Observation Resource - Structured findings and measurements
- 📋 ServiceRequest Resource - Radiology order tracking
- 📋 Practitioner Resource - Radiologist and referring doctor profiles
- 📋 Organization Resource - Hospital and clinic information

**AI/ML Enhancements:**
- 📋 Automated Image Analysis - AI-powered abnormality detection
- 📋 Critical Findings Detection - Automatic flagging of urgent findings
- 📋 Report Quality Scoring - AI assessment of report completeness
- 📋 Predictive Analytics - Workflow optimization predictions

**Mobile Applications:**
- 📋 iOS/Android Apps - Native mobile applications
- 📋 Push Notifications - Real-time alerts on mobile
- 📋 Mobile Image Viewing - Optimized DICOM viewer for mobile
- 📋 Mobile Voice Dictation - On-the-go reporting

**Advanced Analytics:**
- 📋 Business Intelligence Dashboard - Executive reporting
- 📋 Predictive Modeling - Resource allocation optimization
- 📋 Financial Forecasting - Revenue and cost predictions
- 📋 Quality Metrics - Comprehensive quality tracking

**Multi-Site Support:**
- 📋 Centralized PACS - Multi-hospital PACS federation
- 📋 Distributed Workflows - Cross-site workflow management
- 📋 Cross-Site Reporting - Remote radiologist access
- 📋 Consolidated Billing - Multi-site financial management

---

## 🔢 System Statistics

**Current Deployment:**
- **Components:** 7 major systems
- **Databases:** 4 (MySQL, PostgreSQL, 2x SQLite)
- **API Endpoints:** 100+ REST endpoints
- **FHIR Resources:** 2 implemented, 5 planned
- **DICOM Services:** 6 (C-STORE, C-FIND, C-MOVE, WADO-RS, QIDO-RS, STOW-RS)
- **Languages Supported:** 3 (English, Afrikaans, Zulu)
- **Medical Aid Schemes:** 5+ integrated
- **Background Services:** 3 (NAS import, device discovery, background processing)

**Code Statistics:**
- **Backend:** ~50,000 lines (PHP, Node.js, Python)
- **Frontend:** ~20,000 lines (React, TypeScript)
- **Database Schema:** 40+ tables
- **API Routes:** 100+ endpoints
- **Docker Containers:** 7 services

---

**Document Version:** 1.1  
**Last Updated:** January 2025  
**Maintained By:** Ubuntu Patient Sorg Team

---

*Built with ❤️ for South African Healthcare*

