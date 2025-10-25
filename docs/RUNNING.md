Running SA-RIS locally (Windows PowerShell)

Prereqs:
- Docker Desktop running
- Node.js (14+) and npm
- Optional: OpenEMR running (via docker-compose or external)

1) Start core services (Orthanc + DB + backend PHP)

# From repository root (PowerShell)
.
# If you want the compose to run in background
powershell -NoProfile -ExecutionPolicy Bypass -Command "./start_services.ps1 -Detach"

# OR foreground (shows logs)
powershell -NoProfile -ExecutionPolicy Bypass -Command "./start_services.ps1"

2) Check Orthanc health

powershell -NoProfile -Command "./check_orthanc.ps1"

2.5) Check OpenEMR health

powershell -NoProfile -Command "./check_openemr.ps1"

3) Start Node backend (API / static server)
cd sa-ris-backend
npm install
npm start

4) Verify integration endpoints
# Health
Invoke-RestMethod http://localhost:3001/health

# List DICOM studies (requires Orthanc reachable)
Invoke-RestMethod http://localhost:3001/api/dicom/studies

# Get a study (replace STUDY_ID)
Invoke-RestMethod http://localhost:3001/api/dicom/studies/STUDY_ID

Notes:
- OpenEMR UI expected at http://localhost:8080 when started via docker-compose
- Docker compose file is at `sa-ris-backend/docker-compose.yml`
- If Orthanc runs on a remote host, set ORTHANC_URL environment variable before running start script.
