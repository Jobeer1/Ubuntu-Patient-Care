# Microsoft SSO Redirect URI Mismatch - Fix Guide

## 🚨 Problem

You're getting this error:

```
AADSTS50011: The redirect URI 'http://localhost:8080/auth/microsoft/callback' 
specified in the request does not match the redirect URIs configured for the 
application '60271c16-3fcb-4ba7-972b-9f075200a567'.
```

## ✅ Solution

The redirect URI `http://localhost:8080/auth/microsoft/callback` is **NOT** registered in your Azure app registration. You need to add it.

---

## 🔧 Step-by-Step Fix

### Step 1: Go to Azure Portal

1. Open: **https://portal.azure.com/**
2. Sign in with your Microsoft account

### Step 2: Navigate to Your App Registration

**Option A - Direct Link (Fastest):**
- Click: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Authentication/appId/60271c16-3fcb-4ba7-972b-9f075200a567

**Option B - Manual Navigation:**
1. Click **"Azure Active Directory"** (left sidebar)
2. Click **"App registrations"**
3. Search for: **"Ubuntu Patient Care MCP SSO"**
4. Click on it to open

### Step 3: Add Redirect URI to Web Platform

1. In the app details, click **"Authentication"** (left sidebar)

2. Look for **"Platform configurations"** section

3. Under **"Web"** section, you should see **"Redirect URIs"**

4. Click **"Add URI"** button

5. Enter the redirect URI:
   ```
   http://localhost:8080/auth/microsoft/callback
   ```

6. Click **"Save"** button at the top

### Step 4: Verify Configuration

1. After saving, you should see under **Web** section:
   - **Redirect URIs:**
     - `http://localhost:8080/auth/microsoft/callback`

2. Confirm the count shows: **1 web**

### Step 5: Restart Your MCP Server

```bash
# PowerShell (Windows)
cd mcp-server
python run.py
```

Or if using a terminal in VS Code:
```bash
python run.py
```

### Step 6: Test the Fix

1. Open your browser: **http://localhost:8080/test**
2. Click **"Sign in with Microsoft"**
3. You should now login successfully!

---

## 📋 Troubleshooting Checklist

### ✓ Redirect URI Added
- [ ] Went to Azure Portal
- [ ] Opened "Ubuntu Patient Care MCP SSO" app
- [ ] Added redirect URI: `http://localhost:8080/auth/microsoft/callback`
- [ ] Clicked Save

### ✓ Configuration File
- [ ] `.env` file exists in `mcp-server/` folder
- [ ] Contains `MICROSOFT_CLIENT_ID=60271c16-3fcb-4ba7-972b-9f075200a567`
- [ ] Contains valid `MICROSOFT_CLIENT_SECRET` (if you need to update it, see below)
- [ ] Contains `MICROSOFT_REDIRECT_URI=http://localhost:8080/auth/microsoft/callback`

### ✓ Server Running
- [ ] MCP Server is running on port 8080
- [ ] No error messages in console
- [ ] Can access: http://localhost:8080/health

---

## 🔍 Verify Your Configuration

### Check Azure Portal Configuration

1. Go to: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Authentication/appId/60271c16-3fcb-4ba7-972b-9f075200a567

2. Under **Web** section, verify:
   ```
   Redirect URIs:
   - http://localhost:8080/auth/microsoft/callback
   ```

### Check .env File

Open `mcp-server/.env` and verify:

```env
MICROSOFT_CLIENT_ID=60271c16-3fcb-4ba7-972b-9f075200a567
MICROSOFT_CLIENT_SECRET=your-secret-value
MICROSOFT_TENANT_ID=fba55b68-1de1-4d10-a7cc-efa55942f829
MICROSOFT_REDIRECT_URI=http://localhost:8080/auth/microsoft/callback
```

### Check Server Logs

```bash
# PowerShell
Get-Content .\logs\mcp-server.log -Tail 20
```

Look for: `Starting MCP Server...` and `Server running on http://0.0.0.0:8080`

---

## ⚠️ Common Issues

### Issue 1: Still Getting Redirect URI Mismatch After Adding

**Cause:** Server is still running old configuration

**Solution:**
1. Stop the MCP server (Ctrl+C)
2. Wait 5 seconds
3. Restart: `python run.py`
4. Clear browser cache (Ctrl+Shift+Delete)
5. Try login again

### Issue 2: Can't Find "Authentication" Tab

**Cause:** You're in the wrong section

**Solution:**
1. Make sure you're viewing the app registration (not just the managed app)
2. Go to: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Authentication/appId/60271c16-3fcb-4ba7-972b-9f075200a567
3. You should see **"Authentication"** in the left sidebar

### Issue 3: Client Secret is Missing/Expired

**Cause:** Need a valid client secret

**Solution:**
1. Go to: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Credentials/appId/60271c16-3fcb-4ba7-972b-9f075200a567
2. Under **"Client secrets"**, click **"New client secret"**
3. Fill in:
   - Description: `MCP Server Secret`
   - Expires: `24 months`
4. Click **"Add"**
5. **⚠️ COPY the VALUE immediately** (shown only once!)
6. Update `.env` file:
   ```env
   MICROSOFT_CLIENT_SECRET=your-new-secret-value
   ```
7. Restart MCP server

---

## 🎯 Expected Result

After completing these steps, when you click "Sign in with Microsoft":

1. ✅ You'll be redirected to Microsoft login page
2. ✅ You can sign in with any Microsoft account
3. ✅ You'll be redirected back to: `http://localhost:8080/auth/microsoft/callback`
4. ✅ You'll see your dashboard

---

## 📞 Still Having Issues?

### Check these files:

1. **MCP Server is running:**
   ```bash
   # Terminal command
   netstat -ano | findstr :8080
   ```
   Should show something is listening on port 8080

2. **View error logs:**
   ```bash
   Get-Content mcp-server\logs\mcp-server.log -Tail 50
   ```

3. **Test server health:**
   - Open browser: http://localhost:8080/health
   - Should return: `{"status":"healthy"}`

4. **Test auth endpoint:**
   - Open browser: http://localhost:8080/auth/status
   - Should return: `{"authenticated":false}` (if not logged in)

---

## 📊 Reference: Complete Configuration

### Your Azure App Details
- **Display Name:** Ubuntu Patient Care MCP SSO
- **Client ID:** `60271c16-3fcb-4ba7-972b-9f075200a567`
- **Tenant ID:** `fba55b68-1de1-4d10-a7cc-efa55942f829`
- **Object ID:** `5da23eaa-b5dc-4331-8602-c37e33989bf8`

### Required Redirect URIs
For local development:
```
http://localhost:8080/auth/microsoft/callback
```

For production (add these later):
```
https://your-production-domain.com/auth/microsoft/callback
```

### Required Scopes
```
openid email profile offline_access Files.ReadWrite
```

---

## 🚀 Next Steps After Fix

1. ✅ Test login with Microsoft account
2. ✅ Verify user is created in database
3. ✅ Check RBAC roles are assigned correctly
4. ✅ Test accessing protected endpoints with JWT token
5. ✅ Verify audit logs record the login

---

## 📝 Notes

- This fix only adds the redirect URI to Azure
- Your `.env` file must have valid `MICROSOFT_CLIENT_SECRET`
- If you don't have the secret, create a new one in Azure Portal → Certificates & secrets
- After any Azure changes, restart the MCP server to reload environment

---

**Version:** 1.0  
**Date:** October 19, 2025  
**Status:** Ready to follow
