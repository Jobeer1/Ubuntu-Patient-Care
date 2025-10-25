# PACS Module (Picture Archiving and Communication System)

## Overview
This module contains the PACS infrastructure for storing, managing, and viewing medical images (DICOM files) for the radiology department.

## Current Location
⚠️ **Note**: PACS components are distributed across multiple locations:
- **Orthanc PACS**: `./Orthanc/` (root level - in use)
- **Offline Viewer**: `./offline-dicom-viewer/` (moved to this module)
- **Duplicate Orthanc**: `./4-PACS-Module/Orthanc/` (backup copy)

## Folder Structure

```
PACS Components:
├── ../Orthanc/                    # Main Orthanc PACS Server (IN USE)
│   ├── orthanc-server/            # Core PACS server
│   ├── orthanc-dicomweb/          # DICOMweb plugin
│   ├── orthanc-ohif/              # OHIF viewer integration
│   ├── orthanc-webviewer/         # Web-based viewer
│   ├── orthanc-python/            # Python plugins
│   ├── medical-reporting-module/  # Reporting integration
│   └── orthanc_management.db      # Management database
│
└── 4-PACS-Module/
    ├── offline-dicom-viewer/      # Standalone DICOM viewer
    │   ├── src/                   # Viewer source code
    │   ├── styles/                # CSS styles
    │   ├── index.html             # Main HTML
    │   └── webpack.config.js      # Build configuration
    │
    └── Orthanc/                   # Backup/duplicate copy
```

## Key Features

### DICOM Storage
- Store and retrieve DICOM images
- Multi-modality support (CT, MRI, X-Ray, US, etc.)
- Compression and optimization
- Long-term archival

### Image Viewing
- Web-based DICOM viewer (OHIF)
- Offline viewer for local files
- Multi-planar reconstruction (MPR)
- 3D rendering capabilities

### DICOM Services
- DICOM C-STORE (receive images)
- DICOM C-FIND (query studies)
- DICOM C-MOVE (retrieve images)
- DICOM C-ECHO (connectivity test)
- Modality Worklist (MWL)

### DICOMweb Support
- WADO-RS (retrieve)
- QIDO-RS (query)
- STOW-RS (store)
- RESTful API access

### Integration
- HL7 messaging
- FHIR resources
- RIS integration
- Reporting system integration

## Technology Stack

### Orthanc PACS
- **Core**: C++ (high performance)
- **Database**: SQLite/PostgreSQL
- **Plugins**: C++, Python, Lua
- **API**: REST + DICOM

### Offline Viewer
- **Framework**: Cornerstone.js
- **Build**: Webpack
- **UI**: HTML5/CSS3/JavaScript
- **DICOM Parser**: dicomParser

## Getting Started

### Orthanc Server Setup
```bash
cd ../Orthanc/orthanc-server
# Follow Orthanc installation guide
./start_orthanc.sh
```

Orthanc runs on:
- **Web UI**: http://localhost:8042
- **DICOM Port**: 4242
- **Credentials**: orthanc/orthanc

### Offline Viewer Setup
```bash
cd 4-PACS-Module/offline-dicom-viewer
npm install
npm run build
# Open index.html in browser
```

## Orthanc Configuration

### orthanc.json
```json
{
  "Name": "SA-RIS-PACS",
  "HttpPort": 8042,
  "DicomPort": 4242,
  "RemoteAccessAllowed": true,
  "AuthenticationEnabled": true,
  "RegisteredUsers": {
    "orthanc": "orthanc"
  },
  "DicomModalities": {
    "sample": ["SAMPLE", "localhost", 2000]
  },
  "OrthancPeers": {},
  "Plugins": [
    "./plugins/libOrthancDicomWeb.so",
    "./plugins/libOrthancWebViewer.so"
  ]
}
```

## DICOM Modalities

### Supported Modalities
- **CT** - Computed Tomography
- **MR** - Magnetic Resonance
- **CR** - Computed Radiography
- **DX** - Digital Radiography
- **US** - Ultrasound
- **MG** - Mammography
- **PT** - Positron Emission Tomography
- **NM** - Nuclear Medicine

## API Endpoints

### Orthanc REST API

#### Patients
- `GET /patients` - List all patients
- `GET /patients/{id}` - Get patient details
- `DELETE /patients/{id}` - Delete patient

#### Studies
- `GET /studies` - List all studies
- `GET /studies/{id}` - Get study details
- `GET /studies/{id}/archive` - Download as ZIP
- `POST /studies` - Upload DICOM

#### Series
- `GET /series/{id}` - Get series details
- `GET /series/{id}/instances` - List instances

#### Instances
- `GET /instances/{id}/file` - Download DICOM file
- `GET /instances/{id}/preview` - Get preview image
- `POST /instances` - Upload instance

### DICOMweb Endpoints
- `GET /dicom-web/studies` - QIDO-RS query
- `GET /dicom-web/studies/{id}/series` - Query series
- `POST /dicom-web/studies` - STOW-RS store
- `GET /dicom-web/studies/{id}/metadata` - Get metadata

## Offline DICOM Viewer

### Features
- Load local DICOM files
- No server required
- Window/Level adjustment
- Zoom and pan
- Measurements
- Annotations

### Usage
```javascript
// Load DICOM file
const file = document.getElementById('fileInput').files[0];
const arrayBuffer = await file.arrayBuffer();
const dataSet = dicomParser.parseDicom(new Uint8Array(arrayBuffer));

// Display image
cornerstone.loadImage(imageId).then(image => {
  cornerstone.displayImage(element, image);
});
```

## Integration with RIS

### Study Creation Flow
1. RIS creates appointment
2. Modality worklist generated
3. Images acquired at modality
4. DICOM sent to Orthanc
5. Study appears in RIS worklist

### OrthancConnector.js
```javascript
// In RIS backend
const orthanc = require('./OrthancConnector');

// Get study from Orthanc
const study = await orthanc.getStudy(studyInstanceUID);

// Send to modality
await orthanc.sendToModality(studyId, 'MODALITY_AET');
```

## Database Schema

### Orthanc Database
- `Resources` - All DICOM resources
- `MainDicomTags` - Indexed DICOM tags
- `Metadata` - Additional metadata
- `AttachedFiles` - File storage
- `Changes` - Change tracking

## Performance Optimization

### Storage
- Compression enabled
- Automatic cleanup
- Archive to external storage
- Tiered storage (hot/cold)

### Caching
- Image cache
- Metadata cache
- Query result cache

### Network
- Concurrent transfers
- Bandwidth throttling
- Compression
- Delta encoding

## Security

### Authentication
- HTTP Basic Auth
- Token-based auth
- LDAP integration
- Role-based access

### Encryption
- HTTPS/TLS
- DICOM TLS
- Database encryption
- At-rest encryption

### Audit
- Access logging
- Change tracking
- DICOM audit trail
- Compliance reporting

## Backup & Recovery

### Backup Strategy
```bash
# Backup Orthanc database
sqlite3 orthanc.db ".backup orthanc_backup.db"

# Backup DICOM files
tar -czf dicom_backup.tar.gz /var/lib/orthanc/
```

### Disaster Recovery
- Regular automated backups
- Off-site storage
- Point-in-time recovery
- Replication to secondary site

## Monitoring

### Health Checks
- Server uptime
- Disk space
- Database size
- Network connectivity

### Metrics
- Studies per day
- Storage growth
- Query performance
- Transfer speeds

## Troubleshooting

### Orthanc Won't Start
- Check port availability (8042, 4242)
- Verify configuration file
- Check database permissions
- Review error logs

### DICOM Transfer Fails
- Verify AE Title configuration
- Check network connectivity
- Test with DICOM echo
- Review firewall rules

### Viewer Issues
- Check browser compatibility
- Verify CORS settings
- Test with sample DICOM
- Check console errors

## Advanced Features

### AI Integration
- Automated measurements
- Abnormality detection
- Image quality assessment
- Hanging protocols

### 3D Rendering
- Volume rendering
- Surface rendering
- Maximum intensity projection (MIP)
- Multi-planar reconstruction (MPR)

### Worklist Management
- Modality worklist provider
- Scheduled procedure steps
- Performed procedure steps
- MPPS integration

## Related Modules
- **RIS Module**: `../1-RIS-Module/` - Study management
- **Reporting**: `../3-Dictation-Reporting/` - Report generation
- **Billing**: `../2-Medical-Billing/` - Procedure billing

## Standards Compliance
- **DICOM 3.0**: Full compliance
- **DICOMweb**: WADO-RS, QIDO-RS, STOW-RS
- **HL7**: Messaging integration
- **FHIR**: ImagingStudy resources
- **IHE**: Radiology profiles

## Support
For PACS-related issues, refer to Orthanc documentation at https://www.orthanc-server.com/
