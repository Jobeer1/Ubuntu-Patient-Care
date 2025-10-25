# Microsoft OAuth Setup Guide

## 🔐 Your Microsoft OAuth Configuration

Your application is **already registered** in Azure!

---

## 📋 Application Details

### Registration Information
- **Display Name:** Ubuntu Patient Care MCP SSO
- **Application (client) ID:** `60271c16-3fcb-4ba7-972b-9f075200a567`
- **Object ID:** `5da23eaa-b5dc-4331-8602-c37e33989bf8`
- **Directory (tenant) ID:** `fba55b68-1de1-4d10-a7cc-efa55942f829`

### Configuration
- **Supported account types:** All Microsoft account users
- **Redirect URIs:** 1 web, 0 spa, 0 public client
  - `http://localhost:8080/auth/microsoft/callback`
- **Client credentials:** Add a certificate or secret (see Step 2 below)
- **Application ID URI:** Not configured (optional)
- **Managed application:** Ubuntu Patient Care MCP SSO (in local directory)

### Quick Links
- **App Registration:** https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Overview/appId/60271c16-3fcb-4ba7-972b-9f075200a567
- **Authentication:** https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Authentication/appId/60271c16-3fcb-4ba7-972b-9f075200a567
- **Certificates & Secrets:** https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Credentials/appId/60271c16-3fcb-4ba7-972b-9f075200a567

---

## 🚀 Quick Setup

### Step 1: Access Your Application

1. Go to: https://portal.azure.com/
2. Navigate to: **Azure Active Directory** → **App registrations**
3. Find: **Ubuntu Patient Care MCP SSO**
4. Or use direct link: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Overview/appId/60271c16-3fcb-4ba7-972b-9f075200a567

---

### Step 2: Create Client Secret

**⚠️ CRITICAL: You need to create a client secret!**

1. In your app, go to **"Certificates & secrets"**
2. Click **"New client secret"**
3. Fill in:
   - **Description:** MCP Server Secret
   - **Expires:** 24 months (recommended)
4. Click **"Add"**
5. **⚠️ IMMEDIATELY copy the VALUE** (not the Secret ID)
   - This is shown only once!
   - If you miss it, you'll need to create a new secret

**Example secret value:**
```
abc123~xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

### Step 3: Configure .env File

1. Open `mcp-server/.env` file
2. Add your credentials:

```env
# Microsoft OAuth Configuration
MICROSOFT_CLIENT_ID=60271c16-3fcb-4ba7-972b-9f075200a567
MICROSOFT_CLIENT_SECRET=your-secret-value-here
MICROSOFT_TENANT_ID=fba55b68-1de1-4d10-a7cc-efa55942f829
MICROSOFT_REDIRECT_URI=http://localhost:8080/auth/microsoft/callback
```

3. Replace `your-secret-value-here` with the actual secret from Step 2
4. Save the file

---

### Step 4: Restart MCP Server

```bash
cd mcp-server
python run.py
```

---

### Step 5: Test Login

1. Open browser: http://localhost:8080/test
2. Click **"Sign in with Microsoft"**
3. Login with any Microsoft account:
   - Personal Microsoft account (outlook.com, hotmail.com, live.com)
   - Work or school account (if your organization allows)
4. Grant permissions when prompted
5. You should be redirected back logged in

**Success!** You're now using Microsoft SSO.

---

## 🔍 Finding Your Configuration

### Application (Client) ID
**Where:** Azure Portal → App registrations → Ubuntu Patient Care MCP SSO → Overview

**Your ID:**
```
60271c16-3fcb-4ba7-972b-9f075200a567
```

### Directory (Tenant) ID
**Where:** Azure Portal → App registrations → Ubuntu Patient Care MCP SSO → Overview

**Your ID:**
```
fba55b68-1de1-4d10-a7cc-efa55942f829
```

### Client Secret
**Where:** Azure Portal → App registrations → Ubuntu Patient Care MCP SSO → Certificates & secrets

**⚠️ Note:** Secrets are only shown once when created. If lost, create a new one.

---

## 🎯 Supported Account Types

Your app is configured for: **All Microsoft account users**

This means:
- ✅ Personal Microsoft accounts (outlook.com, hotmail.com, live.com)
- ✅ Work or school accounts (Azure AD)
- ✅ Any Microsoft account can login

**No test user restrictions!** Unlike Google OAuth, Microsoft allows any user to login immediately.

---

## 🔧 Verify Configuration

### Check Redirect URIs

1. Go to: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Authentication/appId/60271c16-3fcb-4ba7-972b-9f075200a567
2. Under **"Web"** section, verify:
   - Redirect URI: `http://localhost:8080/auth/microsoft/callback`
   - Should show: **1 web** redirect URI

### Check API Permissions

1. Go to: **API permissions** tab
2. Should have:
   - Microsoft Graph → Delegated permissions
   - `openid`, `email`, `profile`, `User.Read`

### Check Client Secrets

1. Go to: **Certificates & secrets** tab
2. Should have at least one active client secret
3. Check expiration date
4. Create new secret if expired

---

## ⚠️ Common Issues & Solutions

### Issue 1: "AADSTS700016: Application not found"

**Cause:** Wrong Client ID in `.env`

**Solution:**
1. Verify Client ID in `.env` matches: `60271c16-3fcb-4ba7-972b-9f075200a567`
2. No extra spaces or characters
3. Restart server

---

### Issue 2: "AADSTS7000215: Invalid client secret"

**Cause:** Wrong or expired client secret

**Solution:**
1. Go to Azure Portal → Certificates & secrets
2. Create new client secret
3. Copy the VALUE immediately
4. Update `.env` with new secret
5. Restart server

---

### Issue 3: "redirect_uri_mismatch"

**Cause:** Redirect URI not configured

**Solution:**
1. Go to Azure Portal → Authentication
2. Add redirect URI: `http://localhost:8080/auth/microsoft/callback`
3. Click "Save"
4. Try login again

---

### Issue 4: "Client secret not found in .env"

**Cause:** Environment variables not loaded

**Solution:**
1. Check `.env` file exists in `mcp-server/` directory
2. Verify contents:
   ```bash
   cat .env | grep MICROSOFT
   ```
3. Restart server:
   ```bash
   python run.py
   ```

---

### Issue 5: "AADSTS50020: User account from identity provider does not exist"

**Cause:** User's Microsoft account not recognized

**Solution:**
1. Verify user has a valid Microsoft account
2. Try with different Microsoft account
3. Check if organization policies block external apps

---

## 🔐 Security Best Practices

### Protect Your Client Secret

1. **Never commit to Git:**
   ```bash
   # .gitignore already includes .env
   ```

2. **Use environment variables:**
   ```bash
   export MICROSOFT_CLIENT_SECRET=your-secret
   ```

3. **Rotate secrets regularly:**
   - Create new secret every 6-12 months
   - Delete old secrets after rotation

### Monitor Secret Expiration

1. Go to: Certificates & secrets
2. Check expiration dates
3. Set calendar reminder 1 month before expiration
4. Create new secret before old one expires

### Restrict Redirect URIs

1. Only add necessary redirect URIs
2. Use HTTPS in production
3. Avoid wildcards
4. Remove unused URIs

---

## 📊 OAuth Flow Diagram

```
User clicks "Sign in with Microsoft"
         ↓
MCP Server redirects to Microsoft
         ↓
User logs in with Microsoft account
         ↓
Microsoft checks: Valid account?
         ↓
    Yes → Continue
    No  → Error
         ↓
User grants permissions
         ↓
Microsoft redirects to: http://localhost:8080/auth/microsoft/callback
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

## 🚀 Production Deployment

### Update Redirect URIs

1. Go to: Authentication tab
2. Add production URI:
   ```
   https://your-domain.com/auth/microsoft/callback
   ```
3. Click "Save"

### Update .env for Production

```env
MICROSOFT_REDIRECT_URI=https://your-domain.com/auth/microsoft/callback
```

### Enable HTTPS

1. Obtain SSL certificate (Let's Encrypt)
2. Configure web server (Nginx/Apache)
3. Update all URLs to HTTPS

---

## 📝 Configuration Checklist

- [ ] Application registered in Azure (✓ Already done)
- [ ] Client secret created
- [ ] Client ID added to `.env`
- [ ] Client secret added to `.env`
- [ ] Tenant ID added to `.env`
- [ ] Redirect URI configured
- [ ] MCP Server restarted
- [ ] Test login successful

---

## 🎓 Additional Resources

### Microsoft Documentation
- **Microsoft Identity Platform:** https://docs.microsoft.com/en-us/azure/active-directory/develop/
- **OAuth 2.0:** https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow
- **App Registration:** https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app

### MCP Server Documentation
- **Getting Started:** `GETTING_STARTED.md`
- **Quick Start:** `QUICKSTART.md`
- **Main README:** `README.md`

---

## 🆘 Need Help?

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
cat .env | grep MICROSOFT
```

### Azure Portal Links
- **Your App:** https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Overview/appId/60271c16-3fcb-4ba7-972b-9f075200a567
- **All Apps:** https://portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/~/RegisteredApps

---

## ✅ Quick Reference

### Your Configuration
```env
MICROSOFT_CLIENT_ID=60271c16-3fcb-4ba7-972b-9f075200a567
MICROSOFT_CLIENT_SECRET=your-secret-here
MICROSOFT_TENANT_ID=fba55b68-1de1-4d10-a7cc-efa55942f829
MICROSOFT_REDIRECT_URI=http://localhost:8080/auth/microsoft/callback
```

### Test Login
```
http://localhost:8080/test
```

### Azure Portal
```
https://portal.azure.com/
→ App registrations
→ Ubuntu Patient Care MCP SSO
```

---

**Version:** 1.0.0  
**Last Updated:** October 18, 2025  
**Status:** Complete ✅
