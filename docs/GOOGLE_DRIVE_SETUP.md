# Google Drive Integration Setup Guide

## ✅ What's Already Configured

### Google OAuth Client
- **Client ID**: `807845595525-arfmb2rtcif5b1bmpg86aji9dlv4pmau.apps.googleusercontent.com`
- **Creation Date**: October 18, 2025
- **Status**: ✅ Registered in Google Cloud Console
- **Configuration**: Added to `.env` file

### Backend Integration
- ✅ Google Drive routes implemented
- ✅ OAuth 2.0 flow ready
- ✅ File upload functionality
- ✅ MCP token handling
- ✅ Setup page created

## 🔧 What You Need to Do

### Step 1: Get Client Secret from Google Cloud Console

1. **Go to Google Cloud Console**:
   - Visit: https://console.cloud.google.com/apis/credentials
   - Sign in with your Google account

2. **Find Your OAuth Client**:
   - Look for: `807845595525-arfmb2rtcif5b1bmpg86aji9dlv4pmau`
   - Click on it to view details

3. **Copy the Client Secret**:
   - You'll see "Client secret" field
   - Click the copy icon or select and copy the value
   - It looks like: `GOCSPX-xxxxxxxxxxxxxxxxxxxxx`

### Step 2: Configure Redirect URI

While in the OAuth client details:

1. **Check Authorized redirect URIs**:
   - Should include: `http://localhost:5000/api/nas/gdrive/callback`
   - If not present, click "ADD URI" and add it
   - Click "SAVE"

2. **Verify OAuth consent screen**:
   - Go to "OAuth consent screen" in the left menu
   - Make sure your email is added as a test user
   - Status should be "Testing" or "Published"

### Step 3: Update .env File

1. Open: `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/.env`
2. Find this line:
   ```
   GDRIVE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET_HERE
   ```
3. Replace `YOUR_GOOGLE_CLIENT_SECRET_HERE` with the secret you copied
4. Save the file

Your `.env` should look like:
```env
GDRIVE_CLIENT_ID=807845595525-arfmb2rtcif5b1bmpg86aji9dlv4pmau.apps.googleusercontent.com
GDRIVE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxxx
GDRIVE_REDIRECT_URI=http://localhost:5000/api/nas/gdrive/callback
```

### Step 4: Restart Flask Backend

```bash
# Stop the current backend (Ctrl+C)
cd 4-PACS-Module\Orthanc\orthanc-source\NASIntegration\backend
py app.py
```

Look for:
```
✅ Google Drive integration registered
```

### Step 5: Connect Google Drive

1. **Open the setup page**:
   - Go to http://localhost:5000/api/nas/gdrive/setup
   - Or from Patients page, click the Google Drive setup button

2. **You should see**:
   - "Authenticated via MCP" (if you logged in via MCP)
   - Or "Not connected" (if fresh start)
   - A "Connect Google Drive" button

3. **Click "Connect Google Drive"**:
   - You'll be redirected to Google login
   - Sign in with your Google account
   - Grant permissions when asked:
     - ✓ See and download all your Google Drive files
     - ✓ See your primary Google Account email address
   - You'll be redirected back to the patients page

4. **Verify connection**:
   - Go back to http://localhost:5000/api/nas/gdrive/setup
   - You should see: "Connected as [your-email@gmail.com]"

## 🧪 Testing

### Test 1: Verify Configuration
```bash
py test_onedrive_endpoints.py
```

This will also test Google Drive endpoints.

### Test 2: Check Setup Page
Open: http://localhost:5000/api/nas/gdrive/setup

Should show:
- Configuration status
- Connect button
- Manual token option (for testing)

### Test 3: Upload a File
1. Go to Patients page
2. Select a patient
3. Click "Share to Google Drive"
4. Check your Google Drive for the uploaded file

## 📋 Google Cloud Console Checklist

### ✅ OAuth 2.0 Client Configuration
- [ ] Client ID: `807845595525-arfmb2rtcif5b1bmpg86aji9dlv4pmau`
- [ ] Client Secret: Copied and added to `.env`
- [ ] Authorized redirect URI: `http://localhost:5000/api/nas/gdrive/callback`
- [ ] Application type: Web application

### ✅ OAuth Consent Screen
- [ ] User type: External (or Internal if G Suite)
- [ ] App name: Set
- [ ] User support email: Set
- [ ] Developer contact email: Set
- [ ] Test users: Your email added
- [ ] Scopes: `drive.file` and `userinfo.email`

### ✅ APIs Enabled
- [ ] Google Drive API: Enabled
- [ ] Google+ API (optional): Enabled

## 🎯 What You Can Do After Setup

Once connected:
- ✅ Export patient data as ZIP files
- ✅ Upload to Google Drive automatically
- ✅ Share patient records securely
- ✅ Backup DICOM studies to cloud storage
- ✅ Access files from anywhere
- ✅ Organize files in folders

## 🔍 Troubleshooting

### "Not configured" Error
- Make sure you added the client secret to `.env`
- Restart the Flask backend

### "Redirect URI mismatch" Error
- Go to Google Cloud Console → Credentials
- Edit your OAuth client
- Add: `http://localhost:5000/api/nas/gdrive/callback`
- Make sure there's no trailing slash

### "Access blocked: This app's request is invalid" Error
- Go to OAuth consent screen
- Add your email as a test user
- Make sure the app is in "Testing" mode

### "Invalid client secret" Error
- The secret might be wrong
- Go back to Google Cloud Console
- Copy the secret again
- Update `.env` file
- Restart backend

### "Insufficient permissions" Error
- Make sure these scopes are enabled:
  - `https://www.googleapis.com/auth/drive.file`
  - `https://www.googleapis.com/auth/userinfo.email`

## 📊 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/nas/gdrive/config` | GET | Check configuration |
| `/api/nas/gdrive/status` | GET | Get connection status |
| `/api/nas/gdrive/login` | GET | Start OAuth flow |
| `/api/nas/gdrive/callback` | GET | OAuth callback |
| `/api/nas/gdrive/disconnect` | POST | Disconnect |
| `/api/nas/gdrive/manual_token` | POST | Save manual token |
| `/api/nas/gdrive/upload` | POST | Upload file |
| `/api/nas/gdrive/setup` | GET | Setup page |

## 🔐 Security Notes

- ❌ Never commit `.env` file to Git
- ✅ `.env.example` is safe to commit
- 🔄 Refresh tokens allow automatic token renewal
- 🔒 All communication uses HTTPS with Google
- 📁 Only files uploaded by your app are accessible (drive.file scope)

## 📞 Need Help?

1. Check Flask backend logs for errors
2. Check browser console (F12) for JavaScript errors
3. Verify Google Cloud Console settings
4. Make sure redirect URI matches exactly
5. Ensure you're added as a test user

## ⏭️ Next Steps

1. **Right Now**: Get client secret from Google Cloud Console
2. **Then**: Update `.env` file
3. **Next**: Restart Flask backend
4. **Finally**: Connect Google Drive via setup page

---

**Status**: ⏳ Waiting for client secret

**Action Required**: Get client secret from Google Cloud Console

**Estimated Time**: 2 minutes to configure, 30 seconds to connect
