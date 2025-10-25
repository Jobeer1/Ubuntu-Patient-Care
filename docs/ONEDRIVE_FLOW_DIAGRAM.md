# OneDrive Integration Flow

## Current Authentication Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    WHAT HAPPENED BEFORE                          │
└─────────────────────────────────────────────────────────────────┘

1. You → MCP Server (http://0.0.0.0:8080)
   └─> Clicked "Login with Microsoft"

2. MCP Server → Microsoft OAuth
   └─> You logged in with fjstrausss@hotmail.com

3. Microsoft → MCP Server
   └─> Returned authorization code

4. MCP Server → Microsoft
   └─> Exchanged code for JWT token

5. MCP Server → Flask Backend
   └─> Redirected to: http://localhost:5000/?mcp_token=eyJhbGc...
   
6. Flask Backend → Browser
   └─> Showed "Connected as unknown" ❌ (routes were missing!)


┌─────────────────────────────────────────────────────────────────┐
│                    WHAT HAPPENS NOW (FIXED)                      │
└─────────────────────────────────────────────────────────────────┘

1. You → MCP Server (http://0.0.0.0:8080)
   └─> Already logged in ✅

2. MCP Server → Flask Backend
   └─> Redirects with: ?mcp_token=eyJhbGc...

3. Flask Backend (NEW!)
   ├─> Decodes JWT token
   ├─> Extracts: email, name, expiration
   ├─> Saves to: instance/onedrive_token.json
   └─> Shows: "Authenticated via MCP as fjstrausss@hotmail.com" ✅

4. OneDrive Setup Page
   └─> Shows proper status with your email ✅


┌─────────────────────────────────────────────────────────────────┐
│              FULL ONEDRIVE INTEGRATION (OPTIONAL)                │
└─────────────────────────────────────────────────────────────────┘

To enable file uploads to OneDrive:

1. You → Azure Portal
   └─> Register app, get Client ID & Secret

2. You → Flask Backend
   └─> Configure .env with credentials

3. You → OneDrive Setup Page
   └─> Click "Connect OneDrive"

4. Flask Backend → Microsoft OAuth
   └─> Redirects to Microsoft login

5. Microsoft → Flask Backend
   └─> Returns authorization code

6. Flask Backend → Microsoft
   └─> Exchanges code for OneDrive access token

7. Flask Backend
   ├─> Saves OneDrive token
   └─> Shows: "Connected as fjstrausss@hotmail.com" ✅

8. You → Patients Page
   └─> Click "Share to OneDrive"

9. Flask Backend → OneDrive
   └─> Uploads patient ZIP file ✅


┌─────────────────────────────────────────────────────────────────┐
│                      TOKEN STORAGE                               │
└─────────────────────────────────────────────────────────────────┘

File: instance/onedrive_token.json

Current (MCP only):
{
  "mcp_token": "eyJhbGc...",
  "account_email": "fjstrausss@hotmail.com",
  "account_name": "Johann Strauss",
  "expires_at": "2025-10-20T14:46:04",
  "source": "mcp"
}

After OneDrive OAuth:
{
  "mcp_token": "eyJhbGc...",
  "access_token": "EwB4A8l...",      ← OneDrive token
  "refresh_token": "M.R3_BAY...",    ← For auto-refresh
  "account_email": "fjstrausss@hotmail.com",
  "account_name": "Johann Strauss",
  "expires_at": "2025-10-20T15:46:04",
  "source": "mcp"
}


┌─────────────────────────────────────────────────────────────────┐
│                    API ENDPOINTS ADDED                           │
└─────────────────────────────────────────────────────────────────┘

OneDrive:
  GET  /api/nas/onedrive/config      - Check configuration
  GET  /api/nas/onedrive/status      - Get connection status
  GET  /api/nas/onedrive/login       - Start OAuth flow
  GET  /api/nas/onedrive/callback    - OAuth callback
  POST /api/nas/onedrive/disconnect  - Disconnect
  POST /api/nas/onedrive/manual_token - Save manual token
  POST /api/nas/onedrive/upload      - Upload file
  GET  /api/nas/onedrive/setup       - Setup page

Google Drive (stub):
  GET  /api/nas/gdrive/config        - Check configuration
  GET  /api/nas/gdrive/status        - Get connection status


┌─────────────────────────────────────────────────────────────────┐
│                      QUICK ACTIONS                               │
└─────────────────────────────────────────────────────────────────┘

Right Now:
  1. Restart Flask backend (Ctrl+C, then py app.py)
  2. Refresh OneDrive setup page
  3. See your email displayed correctly ✅

Later (Optional):
  1. Follow ONEDRIVE_SETUP_GUIDE.md
  2. Configure Azure AD app
  3. Enable full OneDrive uploads
```

## Summary

**Before**: Flask backend had no OneDrive routes → "Connected as unknown"
**After**: Flask backend recognizes MCP token → Shows your email correctly
**Next**: Configure Azure AD for full OneDrive integration (optional)
