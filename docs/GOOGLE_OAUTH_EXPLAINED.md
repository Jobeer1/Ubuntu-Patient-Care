# Google OAuth Configuration - Complete Explanation

## 📊 Two Different Google OAuth Clients

Your system uses **two separate Google OAuth clients** for different purposes:

```
┌─────────────────────────────────────────────────────────────┐
│                    GOOGLE OAUTH SETUP                        │
└─────────────────────────────────────────────────────────────┘

1. MCP Server (Port 8080) - User Authentication
   └─> For logging in with Google account
   └─> Used by MCP SSO Gateway

2. Flask Backend (Port 5000) - Google Drive Integration
   └─> For uploading files to Google Drive
   └─> Used by PACS system
```

## 🔐 Configuration Details

### 1. MCP Server - Google Login (Port 8080)

**Purpose**: User authentication via Google SSO

**Configuration File**: `4-PACS-Module/Orthanc/mcp-server/.env`

```env
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8080/auth/google/callback
```

**What it does**:
- Allows users to log in with their Google account
- Authenticates users for the MCP SSO Gateway
- Generates JWT tokens for session management
- Redirects to: `http://localhost:8080/auth/google/callback`

**Scopes**:
- `openid` - Basic authentication
- `email` - User's email address
- `profile` - User's profile information

---

### 2. Flask Backend - Google Drive (Port 5000)

**Purpose**: File uploads to Google Drive

**Configuration File**: `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/.env`

```env
GDRIVE_CLIENT_ID=807845595525-sl5078kmp1kd22v9aohudukkhsqi3rrn.apps.googleusercontent.com
GDRIVE_CLIENT_SECRET=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
GDRIVE_REDIRECT_URI=http://localhost:5000/api/nas/gdrive/callback
```

**What it does**:
- Allows uploading patient files to Google Drive
- Manages Google Drive file operations
- Stores files in user's Google Drive
- Redirects to: `http://localhost:5000/api/nas/gdrive/callback`

**Scopes**:
- `https://www.googleapis.com/auth/drive.file` - Upload files
- `https://www.googleapis.com/auth/userinfo.email` - User email

## 🔄 How They Work Together

```
┌─────────────────────────────────────────────────────────────┐
│                    COMPLETE WORKFLOW                         │
└─────────────────────────────────────────────────────────────┘

Step 1: User Authentication (MCP Server)
┌──────────┐         ┌──────────┐         ┌──────────┐
│   User   │────────>│   MCP    │────────>│  Google  │
│          │  Login  │  Server  │  OAuth  │   Auth   │
└──────────┘         │ :8080    │         └──────────┘
                     └──────────┘              │
                          │                    │
                          │<───────────────────┘
                          │   JWT Token
                          │
                          v
                    User is logged in ✅


Step 2: Google Drive Connection (Flask Backend)
┌──────────┐         ┌──────────┐         ┌──────────┐
│   User   │────────>│  Flask   │────────>│  Google  │
│          │ Connect │ Backend  │  OAuth  │   Auth   │
└──────────┘  Drive  │ :5000    │         └──────────┘
                     └──────────┘              │
                          │                    │
                          │<───────────────────┘
                          │   Access Token
                          │
                          v
                    Google Drive connected ✅


Step 3: File Upload
┌──────────┐         ┌──────────┐         ┌──────────┐
│   User   │────────>│  Flask   │────────>│  Google  │
│          │  Share  │ Backend  │  Upload │  Drive   │
└──────────┘ Patient │ :5000    │   ZIP   └──────────┘
                     └──────────┘              │
                          │                    │
                          │<───────────────────┘
                          │   Success
                          │
                          v
                    File in Google Drive ✅
```

## 📋 Google Cloud Console Setup

You need to configure **both OAuth clients** in Google Cloud Console:

### Client 1: MCP Server Authentication

**Client ID**: `807845595525-arfmb2rtcif5b1bmpg86aji9dlv4pmau`

**Settings**:
- Application type: Web application
- Authorized redirect URIs:
  - `http://localhost:8080/auth/google/callback`
- Scopes:
  - openid
  - email
  - profile

### Client 2: Google Drive Integration

**Client ID**: `807845595525-sl5078kmp1kd22v9aohudukkhsqi3rrn`

**Settings**:
- Application type: Web application
- Authorized redirect URIs:
  - `http://localhost:5000/api/nas/gdrive/callback`
- Scopes:
  - https://www.googleapis.com/auth/drive.file
  - https://www.googleapis.com/auth/userinfo.email

## 🚀 Starting Both Services

### Start MCP Server (Port 8080)
```bash
cd 4-PACS-Module\Orthanc\mcp-server
py run.py
```

**Access**:
- MCP Server: http://localhost:8080
- Google Login: http://localhost:8080/auth/google

### Start Flask Backend (Port 5000)
```bash
cd 4-PACS-Module\Orthanc\orthanc-source\NASIntegration\backend
py app.py
```

**Access**:
- Flask Backend: http://localhost:5000
- Google Drive Setup: http://localhost:5000/api/nas/gdrive/setup

## 🧪 Testing

### Test MCP Server Google Login
1. Go to http://localhost:8080
2. Click "Login with Google"
3. Sign in with your Google account
4. You should be redirected back with a JWT token

### Test Google Drive Integration
1. Go to http://localhost:5000/api/nas/gdrive/setup
2. Click "Connect Google Drive"
3. Sign in with your Google account
4. Grant permissions
5. You should see "Connected as [your-email]"

## 📊 Configuration Summary

| Service | Port | Client ID | Purpose | Redirect URI |
|---------|------|-----------|---------|--------------|
| MCP Server | 8080 | `...pmau` | User login | `/auth/google/callback` |
| Flask Backend | 5000 | `...3rrn` | File uploads | `/api/nas/gdrive/callback` |

## 🔐 Security Notes

- Each OAuth client has its own client secret
- Secrets are stored in separate `.env` files
- Never commit `.env` files to Git
- Each client has different scopes/permissions
- Tokens are stored separately

## ✅ Current Status

**MCP Server Google OAuth**:
- ✅ Client ID configured
- ✅ Client Secret configured
- ✅ Redirect URI set
- ⏳ Ready to use (restart MCP server)

**Flask Backend Google Drive**:
- ✅ Client ID configured
- ✅ Client Secret configured
- ✅ Redirect URI set
- ⏳ Ready to use (restart Flask backend)

## 🎯 Next Steps

1. **Restart MCP Server** (if running):
   ```bash
   cd 4-PACS-Module\Orthanc\mcp-server
   py run.py
   ```

2. **Restart Flask Backend** (if running):
   ```bash
   cd 4-PACS-Module\Orthanc\orthanc-source\NASIntegration\backend
   py app.py
   ```

3. **Test MCP Google Login**:
   - Go to http://localhost:8080
   - Click "Login with Google"

4. **Test Google Drive Integration**:
   - Go to http://localhost:5000/api/nas/gdrive/setup
   - Click "Connect Google Drive"

## 📞 Troubleshooting

### "Redirect URI mismatch" Error

**For MCP Server**:
- Check redirect URI is: `http://localhost:8080/auth/google/callback`
- No trailing slash!

**For Flask Backend**:
- Check redirect URI is: `http://localhost:5000/api/nas/gdrive/callback`
- No trailing slash!

### "Access blocked" Error

- Go to Google Cloud Console
- OAuth consent screen
- Add your email as a test user
- Make sure app is in "Testing" mode

### Wrong Client ID/Secret

- Make sure you're using the correct client for each service
- MCP Server: `...pmau`
- Flask Backend: `...3rrn`

---

**Summary**: You have two separate Google OAuth clients working together to provide both user authentication (MCP) and file storage (Google Drive) functionality!
