# RIS Module (Radiology Information System)

## Overview
This module contains the core Radiology Information System (RIS) components that manage patient workflows, appointments, studies, and worklists for radiology departments.

## Folder Structure

```
1-RIS-Module/
├── openemr/                 # OpenEMR Integration (EHR/EMR System)
│   ├── sa_ris_integration/  # RIS integration module
│   ├── fhir_integration/    # FHIR API integration
│   ├── healthbridge_integration/ # HealthBridge connector
│   ├── icd10_service/       # ICD-10 diagnosis codes
│   ├── workflow_sync/       # Workflow synchronization
│   ├── server/              # OpenEMR backend
│   ├── client/              # OpenEMR frontend
│   └── docker-compose.yml   # Docker setup
│
├── sa-ris-backend/          # Backend API server (Node.js/Express)
│   ├── routes/              # API route handlers
│   │   ├── patients.js      # Patient management endpoints
│   │   ├── appointments.js  # Appointment scheduling
│   │   ├── billing.js       # Billing integration
│   │   └── reports.js       # Report management
│   ├── config/              # Configuration files
│   ├── reporting-api/       # Reporting API module
│   ├── server.js            # Main server entry point
│   ├── mcp_bridge.js        # Medical authorization bridge
│   ├── RISWorkflowEngine.js # Workflow automation
│   ├── FHIRRadiologyService.js # FHIR integration
│   ├── OrthancConnector.js  # PACS integration
│   ├── database_schema.sql  # Database schema
│   └── medical_schemes.db   # Medical schemes database
│
└── sa-ris-frontend/         # Frontend UI (React)
    ├── src/
    │   ├── components/      # React components
    │   │   ├── PatientManagement.js
    │   │   ├── AppointmentScheduling.js
    │   │   ├── WorklistManagement.js
    │   │   ├── StudyManagement.js
    │   │   ├── BillingSystem.js
    │   │   ├── ReportingSystem.js
    │   │   └── MedicalAuthorizationPanel.js
    │   ├── SARadiologyDashboard.js  # Main dashboard
    │   └── App.js           # Root component
    └── public/              # Static assets
```

## Key Features

### OpenEMR Integration (EHR/EMR)
- Complete Electronic Health Records system
- Patient demographics and medical history
- Clinical documentation
- Billing and insurance management
- FHIR API for interoperability
- HealthBridge integration for lab results
- ICD-10 diagnosis coding
- Workflow synchronization with RIS

### Patient Management
- Patient registration and demographics
- Medical history tracking
- Patient search and filtering
- Integration with medical aid schemes
- OpenEMR EHR integration

### Appointment Scheduling
- Calendar-based scheduling
- Resource allocation (rooms, equipment)
- Appointment reminders
- Conflict detection

### Worklist Management
- Modality worklists (MWL)
- Study status tracking
- Priority management
- Radiologist assignment

### Study Management
- Study creation and tracking
- DICOM integration via Orthanc
- Image viewing integration
- Study completion workflow

### Medical Authorization
- Pre-authorization requests
- Medical scheme validation
- Authorization status tracking
- Integration with medical billing

## Technology Stack

### Backend
- **Runtime**: Node.js
- **Framework**: Express.js
- **Database**: SQLite (medical_schemes.db)
- **Real-time**: Socket.io
- **Testing**: Jest
- **Security**: Helmet, CORS

### Frontend
- **Framework**: React 18
- **UI Library**: Ant Design
- **State Management**: React Query
- **Routing**: React Router
- **Charts**: Recharts
- **HTTP Client**: Axios

## Getting Started

### Prerequisites
- Node.js 16+ and npm
- SQLite3
- Docker and Docker Compose (for OpenEMR)
- PHP 7.4+ (for OpenEMR standalone)

### OpenEMR Setup (EHR/EMR System)
```bash
cd 1-RIS-Module/openemr
docker-compose up -d
```
OpenEMR runs on: http://localhost:8080

For detailed OpenEMR setup, see: `openemr/HOW_TO_RUN_LOCALLY.md`

### Backend Setup
```bash
cd 1-RIS-Module/sa-ris-backend
npm install
npm start
```
Backend runs on: http://localhost:5000

### Frontend Setup
```bash
cd 1-RIS-Module/sa-ris-frontend
npm install
npm start
```
Frontend runs on: http://localhost:3000

## Environment Variables

### Backend (.env)
```
PORT=5000
DB_PATH=./medical_schemes.db
ORTHANC_URL=http://localhost:8042
ORTHANC_USERNAME=orthanc
ORTHANC_PASSWORD=orthanc
```

### Frontend (.env)
```
REACT_APP_API_URL=http://localhost:5000
REACT_APP_ORTHANC_URL=http://localhost:8042
```

## API Endpoints

### Patients
- `GET /api/patients` - List all patients
- `POST /api/patients` - Create new patient
- `GET /api/patients/:id` - Get patient details
- `PUT /api/patients/:id` - Update patient
- `DELETE /api/patients/:id` - Delete patient

### Appointments
- `GET /api/appointments` - List appointments
- `POST /api/appointments` - Create appointment
- `PUT /api/appointments/:id` - Update appointment
- `DELETE /api/appointments/:id` - Cancel appointment

### Studies
- `GET /api/studies` - List studies
- `POST /api/studies` - Create study
- `GET /api/studies/:id` - Get study details
- `PUT /api/studies/:id/status` - Update study status

### Medical Authorization
- `POST /api/medical-auth/validate` - Validate medical aid member
- `POST /api/medical-auth/preauth` - Create pre-authorization request
- `GET /api/medical-auth/status/:id` - Check authorization status

## Integration Points

### PACS Integration (Orthanc)
- Located in: `../4-PACS-Module/Orthanc/`
- Connector: `OrthancConnector.js`
- DICOM storage and retrieval
- Modality worklist provider

### Medical Billing
- Located in: `../2-Medical-Billing/`
- Bridge: `mcp_bridge.js`
- Medical scheme validation
- Pre-authorization workflow

### Reporting/Dictation
- Located in: `../3-Dictation-Reporting/`
- API: `reporting-api/`
- Report templates
- Voice dictation integration

## Database Schema

The RIS uses SQLite with the following main tables:
- `patients` - Patient demographics
- `appointments` - Scheduled appointments
- `studies` - Radiology studies
- `worklists` - Modality worklists
- `medical_schemes` - Medical aid schemes
- `authorizations` - Pre-authorization records

## Testing

### Backend Tests
```bash
cd sa-ris-backend
npm test
```

### Frontend Tests
```bash
cd sa-ris-frontend
npm test
```

## Troubleshooting

### Backend won't start
- Check if port 5000 is available
- Verify database file exists
- Check Orthanc connectivity

### Frontend won't connect
- Verify backend is running
- Check CORS settings
- Verify API URL in .env

### Database errors
- Check file permissions on .db files
- Verify schema is up to date
- Run migrations if needed

## Related Modules
- **PACS Module**: `../4-PACS-Module/` - Image storage and viewing
- **Medical Billing**: `../2-Medical-Billing/` - Billing and authorization
- **Dictation/Reporting**: `../3-Dictation-Reporting/` - Report generation

## Support
For issues or questions, refer to the main project README or system documentation.
