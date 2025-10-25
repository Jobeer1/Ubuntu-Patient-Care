# Google OAuth Setup Guide

## Current Status
✅ **Google OAuth backend is configured and ready**
✅ **Google login button is functional**
⚠️ **Google credentials are NOT configured in `.env`**

## Why Google Login Button Doesn't Work
The button attempts to redirect to `/auth/google`, but the backend returns a 500 error because `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are not set in the `.env` file.

## How to Enable Google OAuth

### Step 1: Create a Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project named "Ubuntu Patient Care"
3. Enable the **Google+ API**

### Step 2: Create OAuth 2.0 Credentials
1. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
2. Choose **Web Application**
3. Add authorized redirect URIs:
   ```
   http://localhost:8080/auth/google/callback
   ```
4. Copy the **Client ID** and **Client Secret**

### Step 3: Update .env File
Edit `mcp-server/.env` and replace:

```properties
# OLD (placeholder)
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# NEW (your actual credentials)
GOOGLE_CLIENT_ID=YOUR_CLIENT_ID.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET
```

### Step 4: Restart the Server
```bash
cd mcp-server
py run.py
```

### Step 5: Test Google Login
1. Navigate to http://localhost:8080/
2. Click "Sign in with Google"
3. You should be redirected to Google login
4. After authentication, you'll be redirected to the dashboard

## Files Involved

- **Frontend**: `mcp-server/static/login.html` - Google sign-in button
- **Backend**: `mcp-server/app/routes/auth.py` - OAuth handling
- **Config**: `mcp-server/.env` - Credentials storage
- **Settings**: `mcp-server/config/settings.py` - Configuration loading

## Architecture

The Google OAuth flow:
```
User clicks "Sign in with Google" button
    ↓
Frontend redirects to /auth/google endpoint
    ↓
Backend initiates OAuth redirect to Google
    ↓
User authenticates with Google
    ↓
Google redirects to /auth/google/callback
    ↓
Backend exchanges code for tokens
    ↓
Backend creates/updates user in database
    ↓
Frontend redirected to /dashboard with JWT token
```

## Current Implementation Status

✅ Google OAuth endpoint implemented (`/auth/google`)
✅ Google callback handler implemented (`/auth/google/callback`)
✅ User creation/update on first login
✅ Google Drive token storage for future integration
✅ Frontend button functional and styled
✅ Error handling with user-friendly messages

**Status**: Ready for production once credentials are configured!
