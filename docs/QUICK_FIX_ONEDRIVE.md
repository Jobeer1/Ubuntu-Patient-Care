# Quick Fix: OneDrive "Connected as unknown" Error

## The Problem
After logging in with Microsoft, you saw "Connected as unknown (expires: n/a)"

## The Fix (3 Steps)

### Step 1: Restart the Flask Backend
```bash
# In the terminal running the Flask backend, press Ctrl+C to stop it
# Then restart it:
cd 4-PACS-Module\Orthanc\orthanc-source\NASIntegration\backend
py app.py
```

Look for this line in the startup output:
```
✅ OneDrive integration registered
```

### Step 2: Test the Endpoints (Optional)
```bash
py test_onedrive_endpoints.py
```

You should see all endpoints responding with ✅

### Step 3: Check the OneDrive Setup Page
1. Go to http://localhost:5000/patients
2. Click the OneDrive setup button
3. You should now see:
   - "Authenticated via MCP as fjstrausss@hotmail.com"
   - A message about connecting OneDrive

## What Changed?

I created the missing OneDrive integration:
- ✅ OAuth routes for Microsoft OneDrive
- ✅ MCP token recognition
- ✅ File upload functionality
- ✅ Status and configuration endpoints

## To Complete OneDrive Setup

You have two options:

### Option 1: Full OAuth Setup (Recommended)
See detailed instructions in: `ONEDRIVE_SETUP_GUIDE.md`
- Register an Azure AD app
- Configure environment variables
- Connect OneDrive with full OAuth

### Option 2: Quick Test with Manual Token
1. Go to https://developer.microsoft.com/en-us/graph/graph-explorer
2. Sign in and get an access token
3. Paste it in the "Manual token" section on the setup page
4. Click "Save token"

## Need Help?

Check these files:
- `ONEDRIVE_SETUP_GUIDE.md` - Detailed setup instructions
- `ONEDRIVE_FIX_SUMMARY.md` - Technical details of the fix
- `test_onedrive_endpoints.py` - Test script

## Current Status

✅ MCP authentication working (you're logged in as fjstrausss@hotmail.com)
✅ Flask backend has OneDrive routes
⏳ OneDrive OAuth needs to be configured (optional)
⏳ Backend needs to be restarted to load new routes

**Next Action**: Restart the Flask backend!
