# 🔐 OAuth Setup Guide - Microsoft & Google Login

This guide will help you configure Microsoft and Google OAuth authentication for the South African Medical Imaging System.

## 🎯 Overview

The login page at `http://localhost:5000/login` now supports three authentication methods:
1. **Local Authentication** - Username/password with role selection
2. **Microsoft OAuth** - Sign in with Microsoft/Azure AD accounts
3. **Google OAuth** - Sign in with Google accounts

## 📋 Prerequisites

- Access to Azure Portal (for Microsoft OAuth)
- Access to Google Cloud Console (for Google OAuth)
- Backend server running on `http://localhost:5000`

---

## 🔵 Microsoft OAuth Setup

### Step 1: Register Application in Azure Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. Fill in the details:
   - **Name**: SA Medical Imaging System
   - **Supported account types**: Choose based on your needs
     - Single tenant (your organization only)
     - Multi-tenant (any Azure AD)
     - Multi-tenant + personal Microsoft accounts
   - **Redirect URI**: 
     - Platform: **Web**
     - URI: `http://localhost:5000/auth/microsoft/callback`
5. Click **Register**

### Step 2: Get Client ID

1. After registration, you'll see the **Application (client) ID**
2. Copy this value - this is your `MICROSOFT_CLIENT_ID`

### Step 3: Create Client Secret

1. In your app registration, go to **Certificates & secrets**
2. Click **New client secret**
3. Add a description (e.g., "SA Medical System Secret")
4. Choose expiration period
5. Click **Add**
6. **IMPORTANT**: Copy the secret **Value** immediately (you won't see it again)
7. This is your `MICROSOFT_CLIENT_SECRET`

### Step 4: Get Tenant ID

1. In your app registration, go to **Overview**
2. Copy the **Directory (tenant) ID**
3. This is your `MICROSOFT_TENANT_ID`
4. Or use `common` to allow any Microsoft account

### Step 5: Configure API Permissions

1. Go to **API permissions**
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Select **Delegated permissions**
5. Add these permissions:
   - `openid`
   - `profile`
   - `email`
   - `User.Read`
6. Click **Add permissions**
7. (Optional) Click **Grant admin consent** if you have admin rights

---

## 🔴 Google OAuth Setup

### Step 1: Create Project in Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Name it "SA Medical Imaging System"

### Step 2: Enable Google+ API

1. In the left menu, go to **APIs & Services** → **Library**
2. Search for "Google+ API"
3. Click on it and click **Enable**

### Step 3: Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. If prompted, configure the OAuth consent screen:
   - User Type: **Internal** (for organization) or **External** (for public)
   - Fill in app name, user support email, developer contact
   - Add scopes: `openid`, `profile`, `email`
   - Save and continue
4. Back to Create OAuth client ID:
   - Application type: **Web application**
   - Name: SA Medical Imaging System
   - **Authorized redirect URIs**: Add `http://localhost:5000/auth/google/callback`
5. Click **Create**

### Step 4: Get Client ID and Secret

1. After creation, you'll see a dialog with:
   - **Client ID** - this is your `GOOGLE_CLIENT_ID`
   - **Client secret** - this is your `GOOGLE_CLIENT_SECRET`
2. Copy both values

---

## ⚙️ Configure Backend

### Step 1: Create .env File

1. Navigate to the backend directory:
   ```bash
   cd 4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend
   ```

2. Copy the example file:
   ```bash
   copy .env.example .env
   ```

3. Edit `.env` and add your OAuth credentials:
   ```env
   # Microsoft OAuth
   MICROSOFT_CLIENT_ID=your-actual-client-id-here
   MICROSOFT_CLIENT_SECRET=your-actual-client-secret-here
   MICROSOFT_TENANT_ID=common
   MICROSOFT_REDIRECT_URI=http://localhost:5000/auth/microsoft/callback

   # Google OAuth
   GOOGLE_CLIENT_ID=your-actual-client-id-here
   GOOGLE_CLIENT_SECRET=your-actual-client-secret-here
   GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback
   ```

### Step 2: Install Required Dependencies

Make sure you have the `requests` library installed:
```bash
pip install requests
```

### Step 3: Restart Backend Server

Restart your Flask backend to load the new environment variables:
```bash
python app.py
```

---

## 🧪 Testing OAuth Login

### Test Microsoft Login

1. Open `http://localhost:5000/login`
2. Click **Sign in with Microsoft**
3. You'll be redirected to Microsoft login
4. Sign in with your Microsoft account
5. Grant permissions if prompted
6. You'll be redirected back to the dashboard

### Test Google Login

1. Open `http://localhost:5000/login`
2. Click **Sign in with Google**
3. You'll be redirected to Google login
4. Sign in with your Google account
5. Grant permissions if prompted
6. You'll be redirected back to the dashboard

---

## 🔍 Troubleshooting

### "OAuth not configured" Error

**Problem**: Clicking OAuth buttons shows "OAuth not configured"

**Solution**: 
- Make sure `.env` file exists with valid credentials
- Restart the backend server after adding credentials
- Check that environment variables are loaded

### Redirect URI Mismatch

**Problem**: Error about redirect URI not matching

**Solution**:
- Ensure redirect URI in Azure/Google matches exactly: `http://localhost:5000/auth/microsoft/callback` or `http://localhost:5000/auth/google/callback`
- No trailing slashes
- Use `http://` not `https://` for localhost

### "Failed to get access token"

**Problem**: Authentication fails after entering credentials

**Solution**:
- Verify client secret is correct (not expired)
- Check API permissions are granted
- For Microsoft: Ensure tenant ID is correct
- Check backend logs for detailed error messages

### Users Can't Access Admin Features

**Problem**: OAuth users don't have admin access

**Solution**:
- OAuth users default to `user` role for security
- To grant admin access, modify the OAuth callback in `auth_routes.py`:
  ```python
  # Add logic to check email domain or specific users
  if email.endswith('@yourhospital.co.za'):
      session['is_admin'] = True
      session['role'] = 'admin'
  ```

---

## 🔒 Security Best Practices

1. **Never commit `.env` file** - It's in `.gitignore` for a reason
2. **Use HTTPS in production** - Update redirect URIs to use `https://`
3. **Rotate secrets regularly** - Change client secrets periodically
4. **Limit OAuth scopes** - Only request necessary permissions
5. **Validate user domains** - Restrict to your organization's email domains
6. **Enable MFA** - Require multi-factor authentication for OAuth providers

---

## 📚 Additional Resources

### Microsoft OAuth
- [Azure AD OAuth Documentation](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
- [Microsoft Graph API](https://docs.microsoft.com/en-us/graph/)

### Google OAuth
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google API Console](https://console.cloud.google.com)

---

## ✅ Quick Test Checklist

- [ ] Azure app registered with correct redirect URI
- [ ] Microsoft Client ID and Secret added to `.env`
- [ ] Google Cloud project created
- [ ] Google OAuth credentials created with correct redirect URI
- [ ] Google Client ID and Secret added to `.env`
- [ ] Backend server restarted
- [ ] Can access login page at `http://localhost:5000/login`
- [ ] Microsoft login button works
- [ ] Google login button works
- [ ] Successfully redirected to dashboard after OAuth login
- [ ] Session persists across page refreshes

---

## 🎉 Success!

Once configured, users can:
- Sign in with their Microsoft work/school accounts
- Sign in with their Google accounts
- Use traditional username/password authentication
- All authentication methods lead to the same dashboard

The system automatically creates user sessions for OAuth users with appropriate permissions.
