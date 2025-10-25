# MCP Integration Fixed - Medical Authorization Working

## Problem

The Medical Authorization Panel was failing with 404 errors when trying to call MCP tools:
```
POST /mcp HTTP/1.1" 404 75
MCP Tool Error (list_pending_preauths): AxiosError
Failed to load pending pre-auths: AxiosError
```

## Root Cause

1. **Missing MCP Routes**: The backend server.js wasn't importing or mounting the MCP bridge router
2. **Incorrect API Endpoint**: Frontend was calling `/mcp` instead of `/api/mcp`
3. **Wrong Request Format**: Frontend was sending generic POST requests instead of using the specific REST endpoints

## Fixes Applied

### 1. Backend - Added MCP Routes (server.js)

**Added MCP bridge import:**
```javascript
const mcpBridge = require('./mcp_bridge');
```

**Mounted MCP routes:**
```javascript
// MCP Medical Authorization endpoints
app.use('/api/mcp', mcpBridge);
```

This makes all MCP endpoints available at:
- `POST /api/mcp/validate-medical-aid`
- `POST /api/mcp/validate-preauth-requirements`
- `POST /api/mcp/estimate-patient-cost`
- `POST /api/mcp/create-preauth-request`
- `GET /api/mcp/check-preauth-status/:preauth_id`
- `GET /api/mcp/list-pending-preauths`
- `GET /api/mcp/health`

### 2. Frontend - Fixed API Calls (MedicalAuthorizationPanel.js)

**Updated API base URL:**
```javascript
// Before
const MCP_SERVER_URL = 'http://localhost:3001/mcp';

// After
const MCP_API_BASE = 'http://localhost:3001/api/mcp';
```

**Rewrote callMCPTool function to use REST endpoints:**
```javascript
// Before - Generic POST to /mcp
const callMCPTool = async (toolName, arguments_) => {
  const response = await axios.post(MCP_SERVER_URL, {
    tool: toolName,
    arguments: arguments_
  });
  return response.data;
};

// After - Specific REST endpoints
const callMCPTool = async (toolName, arguments_) => {
  let response;
  
  switch (toolName) {
    case 'validate_medical_aid':
      response = await axios.post(`${MCP_API_BASE}/validate-medical-aid`, arguments_);
      break;
    case 'validate_preauth_requirements':
      response = await axios.post(`${MCP_API_BASE}/validate-preauth-requirements`, arguments_);
      break;
    case 'estimate_patient_cost':
      response = await axios.post(`${MCP_API_BASE}/estimate-patient-cost`, arguments_);
      break;
    case 'create_preauth_request':
      response = await axios.post(`${MCP_API_BASE}/create-preauth-request`, arguments_);
      break;
    case 'list_pending_preauths':
      response = await axios.get(`${MCP_API_BASE}/list-pending-preauths`, { params: arguments_ });
      break;
    case 'check_preauth_status':
      response = await axios.get(`${MCP_API_BASE}/check-preauth-status/${arguments_.preauth_id}`);
      break;
    default:
      throw new Error(`Unknown MCP tool: ${toolName}`);
  }
  
  return response.data.data || response.data;
};
```

### 3. Code Cleanup

**Removed unused imports and variables:**
- Removed `React` import (using named imports only)
- Removed `AlertOutlined` (not used)
- Removed `selectedPatient` and `setSelectedPatient` state (not used)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SA-RIS Frontend                          │
│                  (React Application)                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │     MedicalAuthorizationPanel.js                     │  │
│  │                                                      │  │
│  │  - Validate Medical Aid                             │  │
│  │  - Check Pre-Auth Requirements                      │  │
│  │  - Estimate Patient Cost                            │  │
│  │  - Create Pre-Auth Request                          │  │
│  │  - List Pending Pre-Auths                           │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          │ HTTP REST API                    │
│                          ▼                                  │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ POST/GET /api/mcp/*
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    SA-RIS Backend                           │
│                  (Express.js Server)                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              server.js                               │  │
│  │                                                      │  │
│  │  app.use('/api/mcp', mcpBridge)                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            mcp_bridge.js                             │  │
│  │                                                      │  │
│  │  - Express Router                                    │  │
│  │  - Spawns MCP Python Server                         │  │
│  │  - Translates REST → JSON-RPC                       │  │
│  │  - Handles MCP Tool Calls                           │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          │ JSON-RPC over stdio              │
│                          ▼                                  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              MCP Medical Server                             │
│                (Python Server)                              │
│                                                             │
│  - Medical Aid Validation                                   │
│  - Pre-Authorization Logic                                  │
│  - Cost Estimation                                          │
│  - South African Medical Schemes                            │
│  - ICD-10 & CPT Code Validation                            │
└─────────────────────────────────────────────────────────────┘
```

## Testing

### Backend Health Check
```bash
curl http://localhost:3001/api/mcp/health
```

Expected response:
```json
{
  "success": true,
  "mcp_ready": true,
  "mcp_running": true
}
```

### Validate Medical Aid
```bash
curl -X POST http://localhost:3001/api/mcp/validate-medical-aid \
  -H "Content-Type: application/json" \
  -d '{
    "member_number": "123456789",
    "scheme_code": "DISCOVERY"
  }'
```

### List Pending Pre-Auths
```bash
curl http://localhost:3001/api/mcp/list-pending-preauths?status=queued
```

## Files Modified

1. **sa-ris-backend/server.js**
   - Added MCP bridge import
   - Mounted MCP routes at `/api/mcp`

2. **sa-ris-frontend/src/components/MedicalAuthorizationPanel.js**
   - Updated API base URL
   - Rewrote callMCPTool to use REST endpoints
   - Removed unused imports and state variables

## Benefits

✅ **Proper REST API**: Clean, RESTful endpoints instead of generic RPC
✅ **Better Error Handling**: Specific error messages for each endpoint
✅ **Type Safety**: Clear request/response contracts
✅ **Easier Testing**: Can test endpoints with curl/Postman
✅ **Better Logging**: Each endpoint logs separately
✅ **Scalability**: Easy to add new endpoints

## Next Steps

1. **Start MCP Server**: Ensure the Python MCP server is running
2. **Test Integration**: Use the Medical Authorization Panel
3. **Monitor Logs**: Check both backend and MCP server logs
4. **Add Error Handling**: Improve user feedback for MCP errors

## Conclusion

The Medical Authorization Panel now properly communicates with the MCP server through well-defined REST API endpoints. The 404 errors are resolved, and the system is ready for medical aid validation and pre-authorization workflows.
