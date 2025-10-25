# OneDrive Integration - Visual Guide 🎨

## 🎯 Current Status

```
┌─────────────────────────────────────────────────────────────┐
│                    ✅ CONFIGURATION COMPLETE                 │
└─────────────────────────────────────────────────────────────┘

Azure AD App:  ✅ Registered
Client ID:     ✅ 42f0676f-4209-4be8-a72d-4102f5e260d8
Client Secret: ✅ Ok28Q~encB43... (expires 4/18/2026)
Tenant ID:     ✅ fba55b68-1de1-4d10-a7cc-efa55942f829
.env File:     ✅ Configured
Backend Code:  ✅ Ready
MCP Auth:      ✅ Logged in as fjstrausss@hotmail.com

┌─────────────────────────────────────────────────────────────┐
│                    ⏳ NEXT: RESTART BACKEND                  │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start (Visual)

```
Step 1: Restart Backend
┌──────────────────────────────────────────────────────────┐
│  Terminal                                                 │
│  ────────                                                 │
│  > cd 4-PACS-Module\Orthanc\orthanc-source\              │
│       NASIntegration\backend                             │
│  > py app.py                                             │
│                                                           │
│  Look for:                                               │
│  ✅ OneDrive integration registered                      │
│  ✅ Google Drive integration registered                  │
└──────────────────────────────────────────────────────────┘

Step 2: Open Setup Page
┌──────────────────────────────────────────────────────────┐
│  Browser: http://localhost:5000/api/nas/onedrive/setup   │
│  ────────────────────────────────────────────────────────│
│                                                           │
│  OneDrive / Microsoft account setup                      │
│  ═══════════════════════════════════════                 │
│                                                           │
│  ✅ Authenticated via MCP as fjstrausss@hotmail.com      │
│     Click Connect OneDrive to link your OneDrive account │
│                                                           │
│  [Connect OneDrive]  [Disconnect]                        │
│                                                           │
└──────────────────────────────────────────────────────────┘

Step 3: Click Connect OneDrive
┌──────────────────────────────────────────────────────────┐
│  Microsoft Login Page                                     │
│  ────────────────────                                     │
│                                                           │
│  Sign in to your Microsoft account                       │
│                                                           │
│  Email: fjstrausss@hotmail.com                           │
│  Password: ••••••••••                                    │
│                                                           │
│  [Sign in]                                               │
│                                                           │
└──────────────────────────────────────────────────────────┘

Step 4: Grant Permissions
┌──────────────────────────────────────────────────────────┐
│  Permissions requested                                    │
│  ────────────────────                                     │
│                                                           │
│  UPC PACS onedrive setup wants to:                       │
│                                                           │
│  ✓ Read and write files in all site collections         │
│  ✓ Maintain access to data you have given it access to  │
│  ✓ Sign you in and read your profile                    │
│                                                           │
│  [Accept]  [Cancel]                                      │
│                                                           │
└──────────────────────────────────────────────────────────┘

Step 5: Success!
┌──────────────────────────────────────────────────────────┐
│  Browser: http://localhost:5000/patients                 │
│  ────────────────────────────────────────────────────────│
│                                                           │
│  ✅ Redirected back to patients page                     │
│  ✅ OneDrive is now connected!                           │
│                                                           │
│  Go back to setup page to verify:                       │
│  "Connected as fjstrausss@hotmail.com"                   │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

## 🔄 Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         AUTHENTICATION FLOW                      │
└─────────────────────────────────────────────────────────────────┘

1. MCP Server Authentication (Already Done ✅)
   ┌──────────┐         ┌──────────┐         ┌──────────┐
   │   You    │────────>│   MCP    │────────>│Microsoft │
   │          │  Login  │  Server  │  OAuth  │   OAuth  │
   └──────────┘         └──────────┘         └──────────┘
                              │                     │
                              │<────────────────────┘
                              │   JWT Token
                              │
                              v
                        ┌──────────┐
                        │  Flask   │
                        │ Backend  │
                        └──────────┘
                              │
                              v
                    "Authenticated via MCP"


2. OneDrive Connection (Next Step ⏳)
   ┌──────────┐         ┌──────────┐         ┌──────────┐
   │   You    │────────>│  Flask   │────────>│Microsoft │
   │          │  Click  │ Backend  │  OAuth  │   OAuth  │
   └──────────┘ Connect └──────────┘         └──────────┘
                              │                     │
                              │<────────────────────┘
                              │   Access Token
                              │
                              v
                        ┌──────────┐
                        │ OneDrive │
                        │  Token   │
                        │  Saved   │
                        └──────────┘
                              │
                              v
                    "Connected to OneDrive"


3. File Upload (After Connection ✅)
   ┌──────────┐         ┌──────────┐         ┌──────────┐
   │   You    │────────>│  Flask   │────────>│ OneDrive │
   │          │  Share  │ Backend  │  Upload │   API    │
   └──────────┘ Patient └──────────┘  ZIP    └──────────┘
                              │                     │
                              │<────────────────────┘
                              │   Success
                              │
                              v
                    "File uploaded to OneDrive"
```

## 📊 Configuration Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      CONFIGURATION DETAILS                       │
└─────────────────────────────────────────────────────────────────┘

Azure AD Application
├── Name: UPC PACS onedrive setup
├── Client ID: 42f0676f-4209-4be8-a72d-4102f5e260d8
├── Tenant ID: fba55b68-1de1-4d10-a7cc-efa55942f829
├── Secret: Ok28Q~encB43.MxwEPSn4CkMU8KcAqj_GHFhkdmP
├── Expires: 4/18/2026
└── Redirect: http://localhost:5000/api/nas/onedrive/callback

Backend Configuration (.env)
├── ONEDRIVE_CLIENT_ID ✅
├── ONEDRIVE_CLIENT_SECRET ✅
├── ONEDRIVE_REDIRECT_URI ✅
└── ONEDRIVE_TENANT_ID ✅

API Permissions (Need to verify in Azure Portal)
├── Files.ReadWrite.All (Delegated)
├── offline_access (Delegated)
└── User.Read (Delegated)

Backend Routes
├── /api/nas/onedrive/config ✅
├── /api/nas/onedrive/status ✅
├── /api/nas/onedrive/login ✅
├── /api/nas/onedrive/callback ✅
├── /api/nas/onedrive/disconnect ✅
├── /api/nas/onedrive/manual_token ✅
├── /api/nas/onedrive/upload ✅
└── /api/nas/onedrive/setup ✅
```

## 🎯 What Happens When You Click "Connect OneDrive"

```
┌─────────────────────────────────────────────────────────────────┐
│                    STEP-BY-STEP BREAKDOWN                        │
└─────────────────────────────────────────────────────────────────┘

1. You click "Connect OneDrive"
   └─> Browser sends GET to /api/nas/onedrive/login

2. Flask Backend
   └─> Generates OAuth URL with your Client ID
   └─> Redirects you to Microsoft login page

3. Microsoft Login Page
   └─> You enter your credentials
   └─> You grant permissions
   └─> Microsoft generates authorization code

4. Microsoft Redirects Back
   └─> URL: /api/nas/onedrive/callback?code=ABC123...
   └─> Flask receives the authorization code

5. Flask Backend
   └─> Exchanges code for access token
   └─> Calls Microsoft Graph API to get user info
   └─> Saves token to instance/onedrive_token.json
   └─> Redirects you to /patients

6. Token Saved
   {
     "access_token": "EwB4A8l...",
     "refresh_token": "M.R3_BAY...",
     "account_email": "fjstrausss@hotmail.com",
     "expires_at": "2025-10-20T15:46:04"
   }

7. You're Connected! ✅
   └─> Can now upload files to OneDrive
```

## 🧪 Testing Checklist

```
┌─────────────────────────────────────────────────────────────────┐
│                         TEST CHECKLIST                           │
└─────────────────────────────────────────────────────────────────┘

Before Connecting:
[ ] Flask backend is running
[ ] See "✅ OneDrive integration registered" in logs
[ ] Setup page loads: http://localhost:5000/api/nas/onedrive/setup
[ ] Shows "Authenticated via MCP as fjstrausss@hotmail.com"
[ ] "Connect OneDrive" button is visible

During Connection:
[ ] Click "Connect OneDrive"
[ ] Redirected to Microsoft login
[ ] Can sign in successfully
[ ] Permissions page appears
[ ] Click "Accept"
[ ] Redirected back to patients page

After Connection:
[ ] Go back to setup page
[ ] Shows "Connected as fjstrausss@hotmail.com"
[ ] No errors in browser console (F12)
[ ] No errors in Flask backend logs

File Upload Test:
[ ] Go to patients page
[ ] Select a patient
[ ] Click "Share to OneDrive" (or export button)
[ ] File uploads successfully
[ ] Check OneDrive - file is there!
```

## 🎉 Success Screen

```
┌─────────────────────────────────────────────────────────────────┐
│                    ✅ ONEDRIVE CONNECTED!                        │
└─────────────────────────────────────────────────────────────────┘

Setup Page Shows:
┌──────────────────────────────────────────────────────────┐
│  OneDrive / Microsoft account setup                      │
│  ═══════════════════════════════════════                 │
│                                                           │
│  ✅ Connected as fjstrausss@hotmail.com                  │
│     (expires: 2025-10-20T15:46:04)                       │
│                                                           │
│  [Connect OneDrive]  [Disconnect]                        │
│                                                           │
└──────────────────────────────────────────────────────────┘

You Can Now:
✅ Export patient data as ZIP files
✅ Upload to OneDrive automatically
✅ Share patient records securely
✅ Backup DICOM studies to cloud
✅ Access files from anywhere
```

## 📞 Quick Help

```
Problem: "Not configured" error
Solution: Restart Flask backend

Problem: "Redirect URI mismatch"
Solution: Check Azure Portal → Authentication → Redirect URIs

Problem: "Insufficient privileges"
Solution: Azure Portal → API permissions → Grant admin consent

Problem: Can't see "Connect OneDrive" button
Solution: Check browser console (F12) for JavaScript errors

Problem: Connection fails silently
Solution: Check Flask backend logs for detailed error messages
```

---

**Ready to start?** Run: `START_ONEDRIVE_BACKEND.bat`

**Need help?** Check: `ONEDRIVE_COMPLETE.md`

**Want details?** Read: `COMPLETE_ONEDRIVE_SETUP.md`
