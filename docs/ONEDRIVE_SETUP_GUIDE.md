# OneDrive Integration Setup Guide

## Problem Fixed
The OneDrive integration was showing "Connected as unknown" because the backend routes were missing. I've now added:
- OneDrive OAuth routes (`/api/nas/onedrive/*`)
- Google Drive stub routes (`/api/nas/gdrive/*`)
- MCP token handling for seamless integration

## Current Status
✅ You're authenticated via the MCP server with your Microsoft account (fjstrausss@hotmail.com)
✅ The Flask backend now recognizes your MCP authentication
⚠️ You still need to connect OneDrive to enable file uploads

## How to Connect OneDrive

### Option 1: Using Azure App Registration (Recommended for Production)

1. **Register an Azure AD Application**
   - Go to https://portal.azure.com
   - Navigate to "Azure Active Directory" → "App registrations" → "New registration"
   - Name: "Ubuntu Patient Care OneDrive"
   - Supported account types: "Accounts in any organizational directory and personal Microsoft accounts"
   - Redirect URI: `http://localhost:5000/api/nas/onedrive/callback`
   - Click "Register"

2. **Configure API Permissions**
   - In your app, go to "API permissions"
   - Click "Add a permission" → "Microsoft Graph" → "Delegated permissions"
   - Add these permissions:
     - `Files.ReadWrite.All`
     - `offline_access`
   - Click "Grant admin consent" (if you're an admin)

3. **Create a Client Secret**
   - Go to "Certificates & secrets"
   - Click "New client secret"
   - Description: "OneDrive Integration"
   - Expires: Choose your preference (12 months recommended)
   - Click "Add"
   - **IMPORTANT**: Copy the secret value immediately (you won't see it again!)

4. **Configure Environment Variables**
   - Create a `.env` file in `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/`
   - Add these lines:
     ```
     ONEDRIVE_CLIENT_ID=your_application_client_id
     ONEDRIVE_CLIENT_SECRET=your_client_secret_value
     ONEDRIVE_REDIRECT_URI=http://localhost:5000/api/nas/onedrive/callback
     ```

5. **Restart the Flask Backend**
   - Stop the current backend (Ctrl+C)
   - Start it again: `py app.py`

6. **Connect OneDrive**
   - Go to http://localhost:5000/patients
   - Click the OneDrive setup button
   - Click "Connect OneDrive"
   - Sign in with your Microsoft account
   - Grant permissions
   - You'll be redirected back to the patients page

### Option 2: Manual Token (Quick Test/Development)

If you don't want to set up Azure AD right now, you can use a manual access token:

1. **Get an Access Token**
   - Go to https://developer.microsoft.com/en-us/graph/graph-explorer
   - Sign in with your Microsoft account
   - Click "Modify permissions" and consent to `Files.ReadWrite.All`
   - Copy the access token from the "Access token" tab

2. **Save the Token**
   - Go to http://localhost:5000/patients
   - Click the OneDrive setup button
   - Scroll down to "Manual token" section
   - Paste your access token
   - Click "Save token"

**Note**: Manual tokens expire after 1 hour and don't auto-refresh.

## Testing the Integration

Once connected, you can:
1. Go to the Patients page
2. Select a patient
3. Click "Share to OneDrive"
4. The patient's data will be exported as a ZIP and uploaded to your OneDrive

## Troubleshooting

### "Not configured" Error
- Make sure you've set the environment variables in `.env`
- Restart the Flask backend after adding the `.env` file

### "Failed to connect OneDrive" Error
- Check that your redirect URI matches exactly: `http://localhost:5000/api/nas/onedrive/callback`
- Verify your client secret is correct (they expire!)
- Check the Flask backend logs for detailed error messages

### "Connected as unknown"
- This was the original issue - now fixed!
- The backend now properly handles MCP authentication
- Refresh the page to see your email address

## Next Steps

After connecting OneDrive, you can:
- Export patient data to OneDrive
- Share patient records securely
- Backup DICOM studies to cloud storage

## Files Modified

- ✅ Created `routes/onedrive_routes.py` - OneDrive OAuth and upload logic
- ✅ Created `routes/gdrive_routes.py` - Google Drive stub
- ✅ Updated `app.py` - Registered new blueprints
- ✅ Updated `requirements.txt` - Added PyJWT
- ✅ Updated `templates/onedrive_setup.html` - Better MCP token handling
- ✅ Created `.env.example` - Configuration template
