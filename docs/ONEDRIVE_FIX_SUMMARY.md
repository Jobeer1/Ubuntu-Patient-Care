# OneDrive Integration Fix - Summary

## Problem
After logging in with your Microsoft account via the MCP server, the OneDrive setup page showed:
- "Connected as unknown (expires: n/a)"
- The Flask backend didn't have OneDrive integration routes
- The MCP authentication token wasn't being recognized

## Solution Implemented

### 1. Created OneDrive Integration Routes
**File**: `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/routes/onedrive_routes.py`

Features:
- OAuth 2.0 flow for Microsoft OneDrive
- Token storage and validation
- MCP token recognition and handling
- File upload to OneDrive
- Manual token fallback for testing
- Status and configuration endpoints

### 2. Created Google Drive Stub
**File**: `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/routes/gdrive_routes.py`

Placeholder for future Google Drive integration.

### 3. Registered Blueprints
**File**: `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/app.py`

Added:
```python
# OneDrive Integration
from routes.onedrive_routes import onedrive_bp
app.register_blueprint(onedrive_bp)

# Google Drive Integration (stub)
from routes.gdrive_routes import gdrive_bp
app.register_blueprint(gdrive_bp)
```

### 4. Updated Dependencies
**File**: `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/requirements.txt`

Added: `PyJWT==2.8.0` (already installed on your system)

### 5. Enhanced OneDrive Setup Page
**File**: `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/templates/onedrive_setup.html`

Now shows proper status when authenticated via MCP.

### 6. Created Configuration Template
**File**: `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/.env.example`

Template for OneDrive OAuth credentials.

## What You Need to Do Next

### Immediate Fix (Restart Backend)
1. Stop the Flask backend (Ctrl+C in the terminal)
2. Restart it: `py app.py` in the backend directory
3. Refresh the OneDrive setup page

The page should now show:
- "Authenticated via MCP as fjstrausss@hotmail.com"
- A message explaining you need to connect OneDrive

### To Enable Full OneDrive Integration

Choose one option:

**Option A: Azure App Registration (Production)**
1. Follow the detailed steps in `ONEDRIVE_SETUP_GUIDE.md`
2. Register an Azure AD app
3. Configure environment variables
4. Restart backend
5. Click "Connect OneDrive"

**Option B: Manual Token (Quick Test)**
1. Get a token from Microsoft Graph Explorer
2. Paste it in the "Manual token" section
3. Click "Save token"
4. Token expires in 1 hour

## API Endpoints Added

- `GET /api/nas/onedrive/config` - Check if OneDrive is configured
- `GET /api/nas/onedrive/status` - Get connection status (handles MCP token)
- `GET /api/nas/onedrive/login` - Start OAuth flow
- `GET /api/nas/onedrive/callback` - OAuth callback handler
- `POST /api/nas/onedrive/disconnect` - Disconnect OneDrive
- `POST /api/nas/onedrive/manual_token` - Save manual token
- `POST /api/nas/onedrive/upload` - Upload file to OneDrive
- `GET /api/nas/onedrive/setup` - Setup page
- `GET /api/nas/gdrive/config` - Google Drive config (stub)
- `GET /api/nas/gdrive/status` - Google Drive status (stub)

## Testing

After restarting the backend:
1. Go to http://localhost:5000/patients
2. Click OneDrive setup
3. You should see your email from MCP authentication
4. Follow the setup guide to complete OneDrive connection

## Files Created/Modified

**Created:**
- `routes/onedrive_routes.py` (258 lines)
- `routes/gdrive_routes.py` (24 lines)
- `.env.example` (configuration template)
- `ONEDRIVE_SETUP_GUIDE.md` (detailed setup instructions)
- `RESTART_BACKEND_WITH_ONEDRIVE.bat` (helper script)
- `ONEDRIVE_FIX_SUMMARY.md` (this file)

**Modified:**
- `app.py` (added blueprint registrations)
- `requirements.txt` (added PyJWT)
- `templates/onedrive_setup.html` (better MCP handling)

## Status
✅ Backend routes created
✅ MCP token handling implemented
✅ Dependencies installed
⏳ Waiting for backend restart
⏳ Waiting for Azure AD configuration (optional)
