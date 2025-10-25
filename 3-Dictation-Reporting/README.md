# Dictation & Medical Reporting Module

## Overview
This module handles medical report generation, voice dictation, report templates, and radiologist reporting workflows for the radiology department.

## Current Location
⚠️ **Note**: The reporting components are currently integrated within other modules:
- **Backend API**: `../1-RIS-Module/sa-ris-backend/reporting-api/`
- **Frontend UI**: `../1-RIS-Module/sa-ris-frontend/src/components/ReportingSystem.js`
- **Database**: `../Orthanc/reporting.db`

## Folder Structure

```
Reporting Components:
├── ../1-RIS-Module/sa-ris-backend/
│   ├── reporting-api/           # Reporting API module
│   │   ├── src/                 # Source code
│   │   └── package.json         # Dependencies
│   ├── routes/reports.js        # Report endpoints
│   ├── reporting_schema.sql     # Database schema
│   └── migrate_reporting_schema.php
│
├── ../1-RIS-Module/sa-ris-frontend/
│   └── src/components/
│       └── ReportingSystem.js   # Report UI component
│
└── ../Orthanc/
    ├── reporting.db             # Reports database
    └── medical-reporting-module/ # Advanced reporting features
```

## Key Features

### Report Generation
- Template-based reporting
- Structured report formats
- Free-text dictation
- Standardized terminology (RadLex)

### Voice Dictation
- Speech-to-text integration
- Real-time transcription
- Voice commands
- Dictation playback

### Report Templates
- Modality-specific templates
- Customizable fields
- Macros and shortcuts
- Common findings library

### Workflow Management
- Report assignment
- Status tracking (Draft, Pending, Approved)
- Peer review workflow
- Amendment tracking

### Report Distribution
- PDF generation
- Email delivery
- FHIR integration
- HL7 messaging

## Technology Stack

### Backend
- **Runtime**: Node.js
- **Database**: SQLite (reporting.db)
- **PDF Generation**: PDFKit
- **Templates**: Handlebars

### Frontend
- **Framework**: React
- **Editor**: Rich text editor
- **Speech**: Web Speech API
- **UI**: Ant Design

## Report Types

### Diagnostic Reports
- X-Ray reports
- CT scan reports
- MRI reports
- Ultrasound reports
- Mammography reports

### Specialized Reports
- Interventional radiology
- Nuclear medicine
- PET/CT reports
- Cardiac imaging

## Report Structure

### Standard Sections
1. **Patient Information**
   - Demographics
   - Medical aid details
   - Referring physician

2. **Clinical Indication**
   - Reason for examination
   - Clinical history
   - Previous imaging

3. **Technique**
   - Modality used
   - Contrast administration
   - Imaging parameters

4. **Findings**
   - Detailed observations
   - Measurements
   - Comparisons

5. **Impression**
   - Summary
   - Diagnosis
   - Recommendations

6. **Radiologist Details**
   - Name and signature
   - Credentials
   - Date and time

## Database Schema

### reports table
```sql
CREATE TABLE reports (
  report_id TEXT PRIMARY KEY,
  study_id TEXT NOT NULL,
  patient_id TEXT NOT NULL,
  radiologist_id TEXT,
  template_id TEXT,
  status TEXT DEFAULT 'draft',
  clinical_indication TEXT,
  technique TEXT,
  findings TEXT,
  impression TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME,
  approved_at DATETIME,
  FOREIGN KEY (study_id) REFERENCES studies(study_id)
);
```

### templates table
```sql
CREATE TABLE templates (
  template_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  modality TEXT,
  body_part TEXT,
  content TEXT,
  macros TEXT,
  created_by TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### report_amendments table
```sql
CREATE TABLE report_amendments (
  amendment_id TEXT PRIMARY KEY,
  report_id TEXT NOT NULL,
  amended_by TEXT,
  reason TEXT,
  changes TEXT,
  amended_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (report_id) REFERENCES reports(report_id)
);
```

## API Endpoints

### Reports
- `GET /api/reports` - List all reports
- `POST /api/reports` - Create new report
- `GET /api/reports/:id` - Get report details
- `PUT /api/reports/:id` - Update report
- `DELETE /api/reports/:id` - Delete report
- `POST /api/reports/:id/approve` - Approve report
- `POST /api/reports/:id/amend` - Amend report
- `GET /api/reports/:id/pdf` - Generate PDF

### Templates
- `GET /api/templates` - List templates
- `POST /api/templates` - Create template
- `GET /api/templates/:id` - Get template
- `PUT /api/templates/:id` - Update template
- `DELETE /api/templates/:id` - Delete template

### Dictation
- `POST /api/dictation/transcribe` - Transcribe audio
- `GET /api/dictation/macros` - Get macro list
- `POST /api/dictation/macro` - Create macro

## Report Workflow

### 1. Draft Creation
```javascript
// Create new report from template
POST /api/reports
{
  study_id: "study123",
  template_id: "ct_chest",
  clinical_indication: "Chest pain"
}
```

### 2. Dictation/Editing
```javascript
// Update report content
PUT /api/reports/report123
{
  findings: "...",
  impression: "..."
}
```

### 3. Review
```javascript
// Submit for review
PUT /api/reports/report123
{
  status: "pending_review"
}
```

### 4. Approval
```javascript
// Approve report
POST /api/reports/report123/approve
{
  radiologist_id: "rad001"
}
```

### 5. Distribution
```javascript
// Generate and send PDF
GET /api/reports/report123/pdf
POST /api/reports/report123/send
{
  recipients: ["doctor@example.com"]
}
```

## Voice Dictation Integration

### Web Speech API
```javascript
const recognition = new webkitSpeechRecognition();
recognition.continuous = true;
recognition.interimResults = true;

recognition.onresult = (event) => {
  const transcript = event.results[0][0].transcript;
  updateReportField(transcript);
};

recognition.start();
```

### Voice Commands
- "New paragraph" - Start new paragraph
- "Period" - Add period
- "Comma" - Add comma
- "Next section" - Move to next section
- "Insert macro [name]" - Insert predefined text

## Report Templates

### Example: CT Chest Template
```
CLINICAL INDICATION:
{{clinical_indication}}

TECHNIQUE:
CT chest performed with/without intravenous contrast.

FINDINGS:
Lungs: {{lungs_findings}}
Mediastinum: {{mediastinum_findings}}
Pleura: {{pleura_findings}}
Chest Wall: {{chest_wall_findings}}

IMPRESSION:
{{impression}}
```

### Macros
- `@normal_chest` - Normal chest findings
- `@pneumonia` - Pneumonia template
- `@pe_negative` - Negative PE findings
- `@nodule` - Pulmonary nodule description

## Integration Points

### RIS Integration
- Study information retrieval
- Patient demographics
- Referring physician details
- Previous reports

### PACS Integration
- Image viewing while reporting
- Key image references
- Measurement tools
- Image annotations

### Billing Integration
- Procedure codes
- Report completion triggers billing
- Authorization verification

## Quality Assurance

### Peer Review
- Random report selection
- Structured feedback
- Quality metrics
- Continuous improvement

### Report Metrics
- Turnaround time
- Amendment rate
- Critical findings communication
- Referring physician satisfaction

## Compliance

### Standards
- **HL7**: Health Level 7 messaging
- **FHIR**: Fast Healthcare Interoperability Resources
- **DICOM SR**: Structured Reporting
- **RadLex**: Radiology lexicon

### Regulations
- **POPIA**: Data protection
- **HPCSA**: Professional standards
- **Medical scheme requirements**

## Getting Started

### Backend Setup
```bash
cd ../1-RIS-Module/sa-ris-backend/reporting-api
npm install
npm start
```

### Database Setup
```bash
cd ../1-RIS-Module/sa-ris-backend
sqlite3 ../Orthanc/reporting.db < reporting_schema.sql
```

### Frontend Access
Navigate to the RIS frontend and access the Reporting tab:
```
http://localhost:3000/reporting
```

## Troubleshooting

### Report Not Saving
- Check database connection
- Verify write permissions
- Check disk space
- Review error logs

### Dictation Not Working
- Check browser compatibility
- Verify microphone permissions
- Test audio input
- Check Speech API support

### PDF Generation Fails
- Verify PDFKit installation
- Check template syntax
- Review font availability
- Check file system permissions

## Advanced Features

### AI-Assisted Reporting
- Automated findings detection
- Suggested impressions
- Critical findings alerts
- Natural language processing

### Analytics
- Report volume tracking
- Turnaround time analysis
- Radiologist productivity
- Quality metrics dashboard

### Mobile Access
- Responsive design
- Mobile dictation
- Push notifications
- Offline capability

## Related Modules
- **RIS Module**: `../1-RIS-Module/` - Study and patient management
- **PACS Module**: `../4-PACS-Module/` - Image viewing
- **Medical Billing**: `../2-Medical-Billing/` - Billing integration

## Future Enhancements
- Advanced AI integration
- Multi-language support
- Enhanced voice commands
- Collaborative reporting
- Real-time collaboration

## Support
For reporting issues, refer to the RIS backend documentation or contact the development team.
