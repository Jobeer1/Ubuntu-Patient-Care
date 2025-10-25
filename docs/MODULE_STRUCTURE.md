# Modular System Architecture

## Overview
The SA Radiology Information System has been organized into 4 distinct modules for better code organization, maintainability, and understanding.

## Module Structure

```
Ubuntu-Patient-Care/
├── 1-RIS-Module/              # Radiology Information System
├── 2-Medical-Billing/         # Medical Billing & Authorization
├── 3-Dictation-Reporting/     # Medical Reporting & Dictation
└── 4-PACS-Module/             # Picture Archiving & Communication
```

## Module Descriptions

### 1. RIS Module (Radiology Information System)
**Location**: `1-RIS-Module/`

**Purpose**: Core radiology workflow management and EHR/EMR

**Components**:
- OpenEMR (EHR/EMR system)
- Patient management
- Appointment scheduling
- Worklist management
- Study tracking
- Medical authorization integration
- FHIR integration
- Clinical documentation

**Technology**: Node.js + React + PHP (OpenEMR)

**Documentation**: See `1-RIS-Module/README.md`

---

### 2. Medical Billing Module
**Location**: `2-Medical-Billing/` (references `../mcp-medical-server/` and OpenEMR)

**Purpose**: Medical billing and scheme authorization

**Components**:
- OpenEMR billing module
- Medical aid validation
- Pre-authorization requests
- Cost estimation
- Billing calculations
- Claims management
- Insurance verification
- ICD-10 coding

**Technology**: Python (FastMCP) + Node.js bridge + PHP (OpenEMR)

**Documentation**: See `2-Medical-Billing/README.md`

**Note**: The MCP server is currently at root level (`../mcp-medical-server/`) because it's actively running. OpenEMR is in `1-RIS-Module/openemr/`.

---

### 3. Dictation & Reporting Module
**Location**: `3-Dictation-Reporting/` (references components in RIS and Orthanc)

**Purpose**: Medical report generation and dictation

**Components**:
- Report templates
- Voice dictation
- Report workflow
- PDF generation
- Report distribution

**Technology**: Node.js + React + Web Speech API

**Documentation**: See `3-Dictation-Reporting/README.md`

**Note**: Reporting components are integrated within the RIS module and Orthanc.

---

### 4. PACS Module (Picture Archiving & Communication System)
**Location**: `4-PACS-Module/` (references `../Orthanc/`)

**Purpose**: Medical image storage and viewing

**Components**:
- DICOM storage (Orthanc)
- Image viewing (OHIF, offline viewer)
- DICOM services (C-STORE, C-FIND, C-MOVE)
- DICOMweb API
- Modality worklist

**Technology**: C++ (Orthanc) + JavaScript (viewers)

**Documentation**: See `4-PACS-Module/README.md`

**Note**: Main Orthanc server is at root level (`../Orthanc/`) because it's actively running.

---

## Module Interactions

```
┌─────────────────┐
│   RIS Module    │ ◄──── User Interface (React)
│  (Frontend/UI)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   RIS Module    │ ◄──── Core Business Logic
│    (Backend)    │
│                 │
│  ┌───────────┐  │
│  │  OpenEMR  │  │ ◄──── EHR/EMR System
│  │  (PHP)    │  │       - Patient Records
│  └───────────┘  │       - Clinical Docs
│                 │       - Billing
└─┬───┬───┬───┬───┘
  │   │   │   │
  │   │   │   └──────► ┌──────────────────┐
  │   │   │            │  PACS Module     │
  │   │   │            │  (Orthanc)       │
  │   │   │            │  - Image Storage │
  │   │   │            │  - DICOM         │
  │   │   │            └──────────────────┘
  │   │   │
  │   │   └────────────► ┌──────────────────┐
  │   │                  │ Reporting Module │
  │   │                  │ - Templates      │
  │   │                  │ - Dictation      │
  │   │                  │ - PDF Gen        │
  │   │                  └──────────────────┘
  │   │
  │   └────────────────► ┌──────────────────┐
  │                      │ Billing Module   │
  │                      │ - OpenEMR        │
  │                      │ - MCP Server     │
  │                      │ - Auth Requests  │
  │                      │ - Cost Calc      │
  │                      └──────────────────┘
  │
  └──────────────────────► Database (SQLite)
```

## Data Flow

### 1. Patient Registration
```
User → RIS Frontend → RIS Backend → Database
                    ↓
              Medical Billing (validate member)
```

### 2. Study Booking
```
User → RIS Frontend → RIS Backend → PACS (create worklist)
                    ↓
              Medical Billing (pre-auth check)
```

### 3. Image Acquisition
```
Modality → PACS (DICOM C-STORE) → RIS Backend (notification)
                                 ↓
                           Update worklist
```

### 4. Reporting
```
Radiologist → RIS Frontend → Reporting Module → Generate PDF
                           ↓
                     PACS (view images)
```

### 5. Billing
```
Study Complete → RIS Backend → Billing Module → Generate invoice
                             ↓
                       Submit to medical scheme
```

## File Locations

### Active Components (Cannot Move - In Use)
- **Orthanc PACS**: `./Orthanc/` (port 8042, 4242)
- **MCP Server**: `./mcp-medical-server/` (Python process)
- **Databases**: Various `.db` files at root

### Organized Components
- **RIS Backend**: `./1-RIS-Module/sa-ris-backend/`
- **RIS Frontend**: `./1-RIS-Module/sa-ris-frontend/`
- **Offline Viewer**: `./4-PACS-Module/offline-dicom-viewer/`

### Documentation
- **Module READMEs**: Each module has detailed README.md
- **System Docs**: Root level documentation files

## Getting Started

### 1. Start OpenEMR (EHR/EMR)
```bash
cd 1-RIS-Module/openemr
docker-compose up -d
# Access: http://localhost:8080
```

### 2. Start PACS (Orthanc)
```bash
cd Orthanc/orthanc-server
./start_orthanc.sh
# Access: http://localhost:8042
```

### 3. Start Medical Billing (MCP Server)
```bash
cd mcp-medical-server
python server.py
# Runs in background
```

### 4. Start RIS Backend
```bash
cd 1-RIS-Module/sa-ris-backend
npm install
npm start
# Access: http://localhost:5000
```

### 5. Start RIS Frontend
```bash
cd 1-RIS-Module/sa-ris-frontend
npm install
npm start
# Access: http://localhost:3000
```

## Quick Start Scripts

### Windows
```powershell
# Start all services
.\START_SYSTEM_CORRECTLY.ps1

# Or start individually
.\start_backend.ps1
.\start_frontend.ps1
```

### Linux/Mac
```bash
# Start all services
./start_services.sh
```

## Environment Configuration

### OpenEMR
```
OPENEMR_URL=http://localhost:8080
MYSQL_ROOT_PASSWORD=root
MYSQL_DATABASE=openemr
```

### RIS Backend (.env)
```
PORT=5000
ORTHANC_URL=http://localhost:8042
MCP_SERVER_URL=http://localhost:8000
OPENEMR_URL=http://localhost:8080
```

### RIS Frontend (.env)
```
REACT_APP_API_URL=http://localhost:5000
REACT_APP_ORTHANC_URL=http://localhost:8042
REACT_APP_OPENEMR_URL=http://localhost:8080
```

### MCP Server
Configured in `.kiro/settings/mcp.json`

## Module Dependencies

```
RIS Module
├── Depends on: PACS, Billing, Reporting
├── Provides: Core workflow, UI, EHR/EMR
├── Components: OpenEMR, sa-ris-backend, sa-ris-frontend
└── Database: medical_schemes.db, openemr (MySQL)

Medical Billing
├── Depends on: RIS (OpenEMR)
├── Provides: Authorization, validation, claims
├── Components: MCP Server, OpenEMR billing
└── Database: medical_schemes.db, openemr (MySQL)

Reporting
├── Depends on: RIS, PACS
├── Provides: Report generation
└── Database: reporting.db

PACS
├── Depends on: None (standalone)
├── Provides: Image storage, viewing
└── Database: orthanc.db, orthanc_management.db
```

## Development Guidelines

### Adding Features
1. Identify which module the feature belongs to
2. Update the appropriate module's code
3. Update module README if needed
4. Test integration with other modules

### Module Communication
- Use REST APIs for inter-module communication
- Document API endpoints in module READMEs
- Use environment variables for URLs
- Implement proper error handling

### Database Management
- Each module manages its own database
- Use foreign keys for cross-module references
- Document schema in module READMEs
- Implement migrations for schema changes

## Troubleshooting

### Module Won't Start
1. Check if required ports are available
2. Verify dependencies are installed
3. Check environment variables
4. Review module-specific README

### Integration Issues
1. Verify all modules are running
2. Check network connectivity
3. Review API endpoint URLs
4. Check CORS configuration

### Database Errors
1. Verify database files exist
2. Check file permissions
3. Review schema migrations
4. Check disk space

## Future Improvements

### Phase 1: Complete Separation
- Move Orthanc to 4-PACS-Module (when not in use)
- Move mcp-medical-server to 2-Medical-Billing
- Extract reporting components to 3-Dictation-Reporting

### Phase 2: Microservices
- Containerize each module (Docker)
- Implement service discovery
- Add API gateway
- Implement message queue

### Phase 3: Scalability
- Load balancing
- Database replication
- Caching layer
- CDN for static assets

## Support & Documentation

### Module-Specific Help
- See individual module README files
- Check module-specific documentation
- Review API documentation

### System-Wide Help
- See main README.md
- Check SYSTEM_ARCHITECTURE.md
- Review VISUAL_GUIDE.md

### Getting Help
- Check troubleshooting sections
- Review error logs
- Consult module documentation
- Contact development team

## Version History
- **v1.0** - Initial modular organization
- **Current** - 4 modules with comprehensive documentation

---

**Note**: This modular structure improves code organization while maintaining full system functionality. Each module can be developed, tested, and deployed independently while working together as a cohesive system.
