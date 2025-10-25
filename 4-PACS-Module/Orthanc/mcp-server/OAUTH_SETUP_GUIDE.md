# Google OAuth Setup Guide

## 🔐 Complete Google OAuth Configuration

This guide walks you through setting up Google OAuth for the MCP Server.

---

## 📋 Prerequisites

- Google account (Gmail or Google Workspace)
- Access to Google Cloud Console
- MCP Server installed

---

## 🚀 Step-by-Step Setup

### Step 1: Access Google Cloud Console

1. Go to: https://console.cloud.google.com/
2. Sign in with your Google account

---

### Step 2: Create a New Project

1. Click the project dropdown (top left)
2. Click **"New Project"**
3. Enter project details:
   - **Project name:** Ubuntu Patient Care
   - **Organization:** (optional)
4. Click **"Create"**
5. Wait for project creation (takes a few seconds)
6. Select your new project from the dropdown

---

### Step 3: Enable Required APIs

1. Go to: https://console.cloud.google.com/apis/library
2. Search for **"Google+ API"** or **"Google Identity"**
3. Click on the API
4. Click **"Enable"**
5. Wait for activation

---

### Step 4: Configure OAuth Consent Screen

**This is critical for security and user access!**

1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. Choose user type:
   - **Internal** - If using Google Workspace (recommended)
   - **External** - For personal Gmail accounts
3. Click **"Create"**

4. Fill in **OAuth consent screen:**
   - **App name:** Ubuntu Patient Care
   - **User support email:** Your email
   - **App logo:** (optional)
   - **Application home page:** http://localhost:8080
   - **Authorized domains:** (leave empty for localhost)
   - **Developer contact:** Your email
5. Click **"Save and Continue"**

6. **Add Scopes:**
   - Click **"Add or Remove Scopes"**
   - Select:
     - `openid`
     - `email`
     - `profile`
   - Click **"Update"**
   - Click **"Save and Continue"**

7. **Add Test Users:** ⚠️ **CRITICAL STEP**
   - Click **"Add Users"**
   - Enter email addresses of users who should be able to login:
     ```
     doctor1@clinic.org
     doctor2@clinic.org
     admin@clinic.org
     ```
   - Click **"Add"**
   - Click **"Save and Continue"**

   **⚠️ Important Notes:**
   - Only test users can login during development
   - OAuth access is restricted to these test users
   - You must add each user's email before they can login
   - To add more users later, return to this screen

8. Review and click **"Back to Dashboard"**

---

### Step 5: Create OAuth Credentials

1. Go to: https://console.cloud.google.com/apis/credentials
2. Click **"Create Credentials"** → **"OAuth 2.0 Client ID"**

3. If prompted, configure consent screen (you already did this)

4. Fill in application details:
   - **Application type:** Web application
   - **Name:** Ubuntu Patient Care Web Client

5. **Add Authorized Redirect URIs:**
   - Click **"Add URI"**
   - Enter: `http://localhost:8080/auth/google/callback`
   - For production, also add: `https://your-domain.com/auth/google/callback`

6. Click **"Create"**

7. **Save Your Credentials:**
   - A popup appears with your credentials
   - **Client ID:** `807845595525-arfmb2rtcif5b1bmpg86aji9dlv4pmau.apps.googleusercontent.com`
   - **Client Secret:** `GOCSPX-xxxxxxxxxxxxxxxxxxxxx`
   - Click **"Download JSON"** (optional, for backup)
   - Click **"OK"**

---

### Step 6: Configure MCP Server

1. Open your `.env` file:
   ```bash
   cd mcp-server
   nano .env
   ```

2. Add your credentials:
   ```env
   GOOGLE_CLIENT_ID=807845595525-arfmb2rtcif5b1bmpg86aji9dlv4pmau.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-your-actual-secret-here
   GOOGLE_REDIRECT_URI=http://localhost:8080/auth/google/callback
   ```

3. Save the file (Ctrl+O, Enter, Ctrl+X in nano)

---

### Step 7: Restart MCP Server

```bash
# Stop the server (Ctrl+C if running)

# Start the server
python run.py
```

---

### Step 8: Test OAuth Login

1. Open browser: http://localhost:8080/test
2. Click **"Sign in with Google"**
3. You should see Google's login page
4. Login with a **test user** account (must be added in Step 4)
5. Grant permissions when prompted
6. You should be redirected back to the MCP Server

**Success!** You're now logged in with Google SSO.

---

## 🔍 Finding Your Client ID Later

Your Client ID can always be accessed:

1. Go to: https://console.cloud.google.com/apis/credentials
2. Look under **"OAuth 2.0 Client IDs"**
3. Click on your client name
4. Your Client ID is displayed at the top

**Example Client ID:**
```
807845595525-arfmb2rtcif5b1bmpg86aji9dlv4pmau.apps.googleusercontent.com
```

---

## ⚠️ Common Issues & Solutions

### Issue 1: "Access Blocked: This app's request is invalid"

**Cause:** Redirect URI mismatch

**Solution:**
1. Check your `.env` file: `GOOGLE_REDIRECT_URI=http://localhost:8080/auth/google/callback`
2. Go to Google Cloud Console → Credentials
3. Edit your OAuth client
4. Verify redirect URI exactly matches: `http://localhost:8080/auth/google/callback`
5. Save and try again

---

### Issue 2: "Error 403: access_denied"

**Cause:** User not added to test users list

**Solution:**
1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. Scroll to **"Test users"** section
3. Click **"Add Users"**
4. Add the user's email address
5. Click **"Save"**
6. Try logging in again

**⚠️ Remember:** Only test users can login during development!

---

### Issue 3: "Error 400: redirect_uri_mismatch"

**Cause:** Redirect URI not authorized

**Solution:**
1. Check the error message for the actual redirect URI being used
2. Go to Google Cloud Console → Credentials
3. Edit your OAuth client
4. Add the exact URI from the error message
5. Common URIs to add:
   - `http://localhost:8080/auth/google/callback`
   - `http://127.0.0.1:8080/auth/google/callback`
   - `https://your-domain.com/auth/google/callback`

---

### Issue 4: "Client ID not found in .env"

**Cause:** Environment variables not loaded

**Solution:**
1. Verify `.env` file exists in `mcp-server/` directory
2. Check file contents:
   ```bash
   cat .env | grep GOOGLE
   ```
3. Restart the server:
   ```bash
   python run.py
   ```

---

### Issue 5: "OAuth consent screen not configured"

**Cause:** Skipped Step 4

**Solution:**
1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. Complete the OAuth consent screen configuration
3. Add test users
4. Try again

---

## 📝 Test Users Management

### Adding Test Users

**During Development:**
1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. Scroll to **"Test users"**
3. Click **"Add Users"**
4. Enter email addresses (one per line):
   ```
   doctor1@clinic.org
   doctor2@clinic.org
   radiologist@clinic.org
   ```
5. Click **"Save"**

**⚠️ Important:**
- Maximum 100 test users
- Only test users can login
- Users must have Google accounts
- Email must match exactly

### Removing Test Users

1. Go to OAuth consent screen
2. Find user in test users list
3. Click **"Remove"**
4. Confirm removal

---

## 🚀 Publishing Your App (Production)

**For production use, publish your OAuth app:**

### Step 1: Complete App Verification

1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. Click **"Publish App"**
3. Complete verification process:
   - Privacy policy URL
   - Terms of service URL
   - App homepage
   - App logo

### Step 2: Submit for Verification

1. Google will review your app
2. Review takes 1-4 weeks
3. Once approved, any Google user can login

### Step 3: Update Production URLs

1. Add production redirect URI:
   ```
   https://your-domain.com/auth/google/callback
   ```
2. Update `.env` for production:
   ```env
   GOOGLE_REDIRECT_URI=https://your-domain.com/auth/google/callback
   ```

---

## 🔐 Security Best Practices

### Protect Your Client Secret

1. **Never commit to Git:**
   ```bash
   # .gitignore already includes .env
   ```

2. **Use environment variables:**
   ```bash
   export GOOGLE_CLIENT_SECRET=your-secret
   ```

3. **Rotate secrets regularly:**
   - Generate new secret every 6-12 months
   - Update in Google Console and `.env`

### Restrict Redirect URIs

1. Only add necessary redirect URIs
2. Use HTTPS in production
3. Avoid wildcards

### Monitor Usage

1. Go to: https://console.cloud.google.com/apis/dashboard
2. View OAuth usage statistics
3. Set up alerts for unusual activity

---

## 📊 OAuth Flow Diagram

```
User clicks "Sign in with Google"
         ↓
MCP Server redirects to Google
         ↓
User logs in with Google account
         ↓
Google checks: Is user in test users list?
         ↓
    Yes → Continue
    No  → Error 403: access_denied
         ↓
User grants permissions
         ↓
Google redirects to: http://localhost:8080/auth/google/callback
         ↓
MCP Server receives authorization code
         ↓
MCP Server exchanges code for user info
         ↓
MCP Server creates/updates user in database
         ↓
MCP Server generates JWT token
         ↓
User is logged in!
```

---

## 📚 Additional Resources

### Google Documentation
- **OAuth 2.0:** https://developers.google.com/identity/protocols/oauth2
- **OpenID Connect:** https://developers.google.com/identity/protocols/oauth2/openid-connect
- **Console Guide:** https://support.google.com/cloud/answer/6158849

### MCP Server Documentation
- **Getting Started:** `GETTING_STARTED.md`
- **Quick Start:** `QUICKSTART.md`
- **Testing Guide:** `TESTING.md`

---

## 🆘 Still Having Issues?

### Check Server Logs
```bash
tail -f mcp-server/logs/mcp-server.log
```

### Test API Directly
```bash
curl http://localhost:8080/auth/status
```

### Verify Configuration
```bash
cd mcp-server
cat .env | grep GOOGLE
```

### Get Help
- Check documentation in `mcp-server/` folder
- View API docs: http://localhost:8080/docs
- Review error messages in browser console (F12)

---

## ✅ Configuration Checklist

- [ ] Google Cloud project created
- [ ] APIs enabled (Google+ API)
- [ ] OAuth consent screen configured
- [ ] Test users added (⚠️ Critical!)
- [ ] OAuth credentials created
- [ ] Client ID copied to `.env`
- [ ] Client Secret copied to `.env`
- [ ] Redirect URI matches exactly
- [ ] MCP Server restarted
- [ ] Test login successful

---

**Your Configuration:**
```env
GOOGLE_CLIENT_ID=807845595525-arfmb2rtcif5b1bmpg86aji9dlv4pmau.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret-here
GOOGLE_REDIRECT_URI=http://localhost:8080/auth/google/callback
```

**Test Users:** (Add in OAuth consent screen)
- doctor1@clinic.org
- doctor2@clinic.org
- admin@clinic.org

**Test URL:** http://localhost:8080/test

---

**Version:** 1.0.0  
**Last Updated:** October 18, 2025  
**Status:** Complete ✅
