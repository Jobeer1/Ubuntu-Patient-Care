# OneDrive Integration - Ready to Use! 🎉

## ✅ What's Been Configured

### Azure AD Application
- **App Name**: UPC PACS onedrive setup
- **Client ID**: `42f0676f-4209-4be8-a72d-4102f5e260d8`
- **Tenant ID**: `fba55b68-1de1-4d10-a7cc-efa55942f829`
- **Status**: ✅ Registered and configured in `.env` file

### Flask Backend
- **OneDrive Routes**: ✅ Created and registered
- **Google Drive Stub**: ✅ Created
- **MCP Token Handling**: ✅ Implemented
- **Configuration File**: ✅ `.env` file created

### Your Current Status
- ✅ Logged in via MCP server as `fjstrausss@hotmail.com`
- ✅ Backend code ready
- ⏳ Need to create client secret in Azure Portal
- ⏳ Need to restart Flask backend

## 🚀 Quick Start (3 Steps)

### Step 1: Create Client Secret in Azure Portal

1. Go to https://portal.azure.com
2. Navigate to: **Azure Active Directory** → **App registrations** → **UPC PACS onedrive setup**
3. Click **Certificates & secrets** (left menu)
4. Click **New client secret**
5. Description: `OneDrive Integration`
6. Expires: **12 months**
7. Click **Add**
8. **COPY THE VALUE** immediately (looks like: `abc123~XyZ456...`)

### Step 2: Update .env File

1. Open: `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/.env`
2. Find this line:
   ```
   ONEDRIVE_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
   ```
3. Replace `YOUR_CLIENT_SECRET_HERE` with the secret you just copied
4. Save the file

### Step 3: Restart Flask Backend

```bash
# Stop the current backend (Ctrl+C in the terminal)
cd 4-PACS-Module\Orthanc\orthanc-source\NASIntegration\backend
py app.py
```

Look for: `✅ OneDrive integration registered`

## 🧪 Test It!

### Verify Configuration
```bash
py verify_onedrive_setup.py
```

### Test Endpoints
```bash
py test_onedrive_endpoints.py
```

### Connect OneDrive
1. Go to http://localhost:5000/api/nas/onedrive/setup
2. Click **Connect OneDrive**
3. Sign in with Microsoft
4. Grant permissions
5. Done! ✅

## 📋 Azure AD Checklist

Before connecting, make sure these are configured in Azure Portal:

### Authentication
- [ ] Redirect URI: `http://localhost:5000/api/nas/onedrive/callback`
- [ ] Access tokens: ✅ Enabled
- [ ] ID tokens: ✅ Enabled

### API Permissions
- [ ] `Files.ReadWrite.All` (Delegated) - ✅ Added
- [ ] `offline_access` (Delegated) - ✅ Added
- [ ] `User.Read` (Delegated) - ✅ Added
- [ ] Admin consent: ✅ Granted

### Certificates & Secrets
- [ ] Client secret created
- [ ] Secret value copied to `.env` file

## 🎯 What You Can Do After Setup

Once connected, you can:
- ✅ Export patient data as ZIP files
- ✅ Upload to OneDrive automatically
- ✅ Share patient records securely
- ✅ Backup DICOM studies to cloud storage

## 📚 Documentation

| File | Purpose |
|------|---------|
| `COMPLETE_ONEDRIVE_SETUP.md` | **START HERE** - Complete step-by-step guide |
| `verify_onedrive_setup.py` | Verify your configuration |
| `test_onedrive_endpoints.py` | Test API endpoints |
| `ONEDRIVE_SETUP_GUIDE.md` | Detailed Azure AD setup |
| `ONEDRIVE_FLOW_DIAGRAM.md` | Visual flow diagram |
| `QUICK_FIX_ONEDRIVE.md` | Quick reference |

## 🔧 Configuration Files

```
4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/
├── .env                          ← Your secrets (DO NOT COMMIT!)
├── .env.example                  ← Template (safe to commit)
├── routes/
│   ├── onedrive_routes.py       ← OneDrive OAuth & upload
│   └── gdrive_routes.py         ← Google Drive stub
└── templates/
    └── onedrive_setup.html      ← Setup page
```

## ⚡ Quick Commands

```bash
# Verify setup
py verify_onedrive_setup.py

# Test endpoints
py test_onedrive_endpoints.py

# Start backend
cd 4-PACS-Module\Orthanc\orthanc-source\NASIntegration\backend
py app.py

# Open setup page
start http://localhost:5000/api/nas/onedrive/setup
```

## 🐛 Troubleshooting

### "Not configured" Error
→ Create client secret and update `.env` file

### "Redirect URI mismatch" Error
→ Check Azure Portal → Authentication → Redirect URIs

### "Insufficient privileges" Error
→ Grant admin consent in Azure Portal → API permissions

### "Invalid client secret" Error
→ Create new secret, update `.env`, restart backend

## 🎉 Success Indicators

You'll know it's working when:
1. ✅ `verify_onedrive_setup.py` shows all green checkmarks
2. ✅ `test_onedrive_endpoints.py` shows all endpoints responding
3. ✅ Setup page shows "Authenticated via MCP as fjstrausss@hotmail.com"
4. ✅ After clicking "Connect OneDrive", you see "Connected as fjstrausss@hotmail.com"
5. ✅ You can upload files to OneDrive from the Patients page

## 🔐 Security Reminder

- ❌ Never commit `.env` file to Git
- ✅ `.env.example` is safe to commit
- 🔄 Client secrets expire - renew them periodically
- 🔒 Keep your Azure AD credentials secure

## 📞 Need Help?

1. Run `py verify_onedrive_setup.py` to check configuration
2. Check Flask backend logs for error messages
3. Check browser console (F12) for JavaScript errors
4. Review `COMPLETE_ONEDRIVE_SETUP.md` for detailed steps

---

**Current Status**: ⏳ Waiting for client secret to be created

**Next Action**: Create client secret in Azure Portal (Step 1 above)
