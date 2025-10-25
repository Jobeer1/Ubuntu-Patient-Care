# Medical Billing Module

## Overview
This module handles medical billing, medical aid scheme validation, pre-authorization requests, and integration with South African medical schemes.

## Current Location
⚠️ **Note**: The medical billing server is currently located at the root level due to active processes:
- **Location**: `../mcp-medical-server/`
- **Reason**: Server is running and cannot be moved while in use

## Folder Structure

```
Medical Billing Components:
├── ../mcp-medical-server/        # MCP Medical Authorization Server (Python)
│   ├── server.py                 # FastMCP server implementation
│   ├── medical_schemes.db        # Medical schemes database
│   ├── requirements.txt          # Python dependencies
│   └── README.md                 # Server documentation
│
├── OpenEMR Integration:
│   └── ../1-RIS-Module/openemr/  # OpenEMR EHR/EMR System
│       ├── fhir_integration/     # FHIR billing resources
│       ├── icd10_service/        # ICD-10 diagnosis codes
│       └── server/               # Billing module
│
└── RIS Integration:
    └── ../1-RIS-Module/sa-ris-backend/
        ├── mcp_bridge.js         # Bridge to MCP server
        ├── SABillingEngine.js    # Billing calculation engine
        └── routes/billing.js     # Billing API endpoints
```

## Key Features

### OpenEMR Billing Integration
- Complete billing and insurance management
- Claims submission and tracking
- Payment posting and reconciliation
- ICD-10 diagnosis coding
- CPT/NRPL procedure codes
- Patient statements and invoicing
- Insurance eligibility verification

### Medical Aid Validation
- Validate medical aid member numbers
- Check scheme codes (DISCOVERY, MOMENTUM, BONITAS, etc.)
- Verify patient eligibility
- Real-time validation
- Integration with OpenEMR insurance module

### Pre-Authorization
- Create pre-authorization requests
- Check procedure requirements
- Track authorization status
- Automated submission workflow

### Cost Estimation
- Calculate patient portions
- Estimate procedure costs
- Apply scheme rules
- Co-payment calculations

### Billing Integration
- Generate invoices
- Track payments
- Medical scheme claims
- ICD-10 and NRPL code support

## Technology Stack

### MCP Server (Python)
- **Framework**: FastMCP
- **Database**: SQLite
- **Protocol**: Model Context Protocol (MCP)
- **API**: RESTful + MCP tools

### RIS Integration (Node.js)
- **Bridge**: mcp_bridge.js
- **Engine**: SABillingEngine.js
- **Communication**: HTTP/JSON

## MCP Tools Available

### 1. validate_medical_aid
Validates medical aid member information (offline)
```javascript
{
  member_number: "string",
  scheme_code: "string",
  id_number: "string" (optional)
}
```

### 2. validate_preauth_requirements
Checks if procedure requires pre-authorization (offline)
```javascript
{
  scheme_code: "string",
  plan_code: "string",
  procedure_code: "string" (NRPL code)
}
```

### 3. estimate_patient_cost
Calculates patient portion for procedure (offline)
```javascript
{
  member_number: "string",
  scheme_code: "string",
  procedure_code: "string" (NRPL code)
}
```

### 4. create_preauth_request
Creates pre-authorization request with validation
```javascript
{
  patient_id: "string",
  member_number: "string",
  scheme_code: "string",
  procedure_code: "string",
  clinical_indication: "string",
  icd10_codes: ["string"],
  urgency: "routine|urgent|emergency"
}
```

### 5. check_preauth_status
Checks status of pre-authorization request
```javascript
{
  preauth_id: "string"
}
```

### 6. list_pending_preauths
Lists all pending pre-authorization requests
```javascript
{
  status: "queued|submitted|approved|rejected"
}
```

## Getting Started

### MCP Server Setup
```bash
cd ../mcp-medical-server
pip install -r requirements.txt
python server.py
```

### Configuration
The MCP server is configured in `.kiro/settings/mcp.json`:
```json
{
  "mcpServers": {
    "medical-auth": {
      "command": "python",
      "args": ["../mcp-medical-server/server.py"],
      "disabled": false
    }
  }
}
```

## Medical Schemes Supported

### Major Schemes
- **Discovery Health** (DISCOVERY)
- **Momentum Health** (MOMENTUM)
- **Bonitas** (BONITAS)
- **Medshield** (MEDSHIELD)
- **Bestmed** (BESTMED)
- **Fedhealth** (FEDHEALTH)
- **Gems** (GEMS)
- **Polmed** (POLMED)

### Plan Types
- Hospital Plans
- Comprehensive Plans
- Savings Plans
- Network Plans

## Database Schema

### medical_schemes table
- `scheme_code` - Unique scheme identifier
- `scheme_name` - Full scheme name
- `contact_info` - Contact details
- `authorization_required` - Boolean flag

### authorizations table
- `preauth_id` - Unique authorization ID
- `patient_id` - Patient reference
- `member_number` - Medical aid member number
- `scheme_code` - Medical scheme
- `procedure_code` - NRPL procedure code
- `status` - queued/submitted/approved/rejected
- `created_at` - Timestamp
- `updated_at` - Timestamp

### procedures table
- `procedure_code` - NRPL code
- `description` - Procedure description
- `base_cost` - Base cost in ZAR
- `requires_auth` - Authorization requirement

## API Endpoints (via RIS Backend)

### Billing
- `POST /api/billing/invoice` - Generate invoice
- `GET /api/billing/invoices` - List invoices
- `GET /api/billing/invoice/:id` - Get invoice details
- `PUT /api/billing/invoice/:id/pay` - Record payment

### Medical Authorization
- `POST /api/medical-auth/validate` - Validate member
- `POST /api/medical-auth/preauth` - Create pre-auth
- `GET /api/medical-auth/status/:id` - Check status
- `GET /api/medical-auth/pending` - List pending

## Integration with RIS

### From Frontend
```javascript
// In MedicalAuthorizationPanel.js
const validateMember = async (memberNumber, schemeCode) => {
  const response = await axios.post('/api/medical-auth/validate', {
    member_number: memberNumber,
    scheme_code: schemeCode
  });
  return response.data;
};
```

### From Backend
```javascript
// In mcp_bridge.js
const mcpClient = require('./mcp_bridge');
const result = await mcpClient.validateMedicalAid({
  member_number: '123456789',
  scheme_code: 'DISCOVERY'
});
```

## Billing Workflow

1. **Patient Registration**
   - Capture medical aid details
   - Validate member number
   - Check scheme status

2. **Study Booking**
   - Check if pre-auth required
   - Estimate patient cost
   - Create pre-auth if needed

3. **Pre-Authorization**
   - Submit clinical details
   - Attach ICD-10 codes
   - Track approval status

4. **Study Completion**
   - Generate invoice
   - Submit claim to scheme
   - Track payment

5. **Payment Processing**
   - Receive scheme payment
   - Collect patient portion
   - Reconcile accounts

## Testing

### Test MCP Server
```bash
cd ../mcp-medical-server
python test_server.py
```

### Test Integration
```bash
cd ../1-RIS-Module/sa-ris-backend
npm test -- billing
```

## Troubleshooting

### MCP Server Issues
- Check if Python 3.8+ is installed
- Verify FastMCP is installed
- Check database file permissions
- Review server logs

### Authorization Failures
- Verify member number format
- Check scheme code validity
- Ensure procedure code is correct
- Review clinical indication

### Database Errors
- Check SQLite file exists
- Verify write permissions
- Run database migrations
- Check disk space

## Compliance & Security

### Data Protection
- POPIA compliance (South African data protection)
- Encrypted member data
- Audit logging
- Access controls

### Medical Scheme Integration
- Follows SAMEDICAL standards
- NRPL procedure codes
- ICD-10 diagnosis codes
- Electronic claims submission

## Related Modules
- **RIS Module**: `../1-RIS-Module/` - Patient and study management
- **PACS Module**: `../4-PACS-Module/` - Image storage
- **Reporting**: `../3-Dictation-Reporting/` - Clinical reports

## Future Enhancements
- Real-time scheme integration APIs
- Automated claims submission
- Payment gateway integration
- Advanced analytics and reporting

## Support
For billing-related issues, refer to the MCP server documentation or contact system administrators.
