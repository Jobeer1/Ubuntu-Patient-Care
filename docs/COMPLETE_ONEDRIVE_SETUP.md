# Complete OneDrive Setup - Final Steps

## ✅ What's Already Done

Your Azure AD application is registered:
- **App Name**: UPC PACS onedrive setup
- **Client ID**: 42f0676f-4209-4be8-a72d-4102f5e260d8
- **Tenant ID**: fba55b68-1de1-4d10-a7cc-efa55942f829
- **Configuration**: Saved to `.env` file

## 🔧 What You Need to Do Now

### Step 1: Add Redirect URI (If Not Already Added)

1. Go to https://portal.azure.com
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click on **UPC PACS onedrive setup**
4. Go to **Authentication** in the left menu
5. Under **Platform configurations** → **Web**:
   - If you see the redirect URI already: ✅ Skip to Step 2
   - If not, click **Add URI** and add:
     ```
     http://localhost:5000/api/nas/onedrive/callback
     ```
6. Scroll down and make sure these are checked:
   - ✅ Access tokens (used for implicit flows)
   - ✅ ID tokens (used for implicit and hybrid flows)
7. Click **Save**

### Step 2: Configure API Permissions

1. Still in your app, go to **API permissions** in the left menu
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Select **Delegated permissions**
5. Search for and add these permissions:
   - ✅ `Files.ReadWrite.All` - Read and write files in all site collections
   - ✅ `offline_access` - Maintain access to data you have given it access to
   - ✅ `User.Read` - Sign in and read user profile
6. Click **Add permissions**
7. Click **Grant admin consent for [Your Organization]** (if you're an admin)
   - If you see a green checkmark, you're good!
   - If not, you may need an admin to approve

### Step 3: Create Client Secret

1. Go to **Certificates & secrets** in the left menu
2. Click **New client secret**
3. Description: `OneDrive Integration Secret`
4. Expires: Choose **12 months** (recommended) or **24 months**
5. Click **Add**
6. **CRITICAL**: Copy the **Value** immediately (you won't see it again!)
   - It looks like: `abc123~XyZ456.qwerty789`
   - NOT the "Secret ID"

### Step 4: Update the .env File

1. Open: `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/.env`
2. Replace `YOUR_CLIENT_SECRET_HERE` with the secret value you just copied
3. Save the file

Your `.env` should look like:
```env
ONEDRIVE_CLIENT_ID=42f0676f-4209-4be8-a72d-4102f5e260d8
ONEDRIVE_CLIENT_SECRET=abc123~XyZ456.qwerty789
ONEDRIVE_REDIRECT_URI=http://localhost:5000/api/nas/onedrive/callback
ONEDRIVE_TENANT_ID=fba55b68-1de1-4d10-a7cc-efa55942f829
```

### Step 5: Restart Flask Backend

```bash
# Stop the current backend (Ctrl+C)
cd 4-PACS-Module\Orthanc\orthanc-source\NASIntegration\backend
py app.py
```

Look for this in the startup output:
```
✅ OneDrive integration registered
```

### Step 6: Test the Connection

1. Go to http://localhost:5000/patients
2. Click the **OneDrive setup** button (or go directly to http://localhost:5000/api/nas/onedrive/setup)
3. You should see:
   - "Authenticated via MCP as fjstrausss@hotmail.com"
   - A message about connecting OneDrive
4. Click **Connect OneDrive**
5. You'll be redirected to Microsoft login
6. Sign in with your Microsoft account (fjstrausss@hotmail.com)
7. Grant permissions when asked
8. You'll be redirected back to the patients page
9. Go back to OneDrive setup - you should now see:
   - "Connected as fjstrausss@hotmail.com"

### Step 7: Test File Upload

1. Go to the **Patients** page
2. Select a patient
3. Click **Share to OneDrive** (or similar button)
4. The patient data will be exported and uploaded to your OneDrive
5. Check your OneDrive to verify the file is there!

## 🧪 Quick Test

Run this to verify endpoints are working:
```bash
py test_onedrive_endpoints.py
```

Expected output:
```
✅ Health Check
✅ OneDrive Config
   Response: {"configured": true, ...}
✅ OneDrive Status
   Response: {"connected": true, "account_email": "fjstrausss@hotmail.com", ...}
```

## 🔍 Troubleshooting

### "Not configured" Error
- Make sure you saved the `.env` file
- Make sure the client secret is correct (no extra spaces)
- Restart the Flask backend

### "Redirect URI mismatch" Error
- Go to Azure Portal → Authentication
- Make sure the redirect URI is exactly: `http://localhost:5000/api/nas/onedrive/callback`
- No trailing slash!

### "Insufficient privileges" Error
- Go to Azure Portal → API permissions
- Make sure you granted admin consent
- If you're not an admin, ask your IT admin to approve

### "Invalid client secret" Error
- The secret may have expired
- Create a new secret in Azure Portal
- Update the `.env` file
- Restart the backend

## 📋 Checklist

- [ ] Redirect URI added in Azure Portal
- [ ] API permissions configured (Files.ReadWrite.All, offline_access, User.Read)
- [ ] Admin consent granted
- [ ] Client secret created
- [ ] `.env` file updated with client secret
- [ ] Flask backend restarted
- [ ] OneDrive setup page shows "Authenticated via MCP"
- [ ] Clicked "Connect OneDrive"
- [ ] Successfully logged in with Microsoft
- [ ] OneDrive setup page shows "Connected as [your email]"
- [ ] Tested file upload to OneDrive

## 🎉 Success!

Once all steps are complete, you'll be able to:
- ✅ Export patient data as ZIP files
- ✅ Upload to OneDrive automatically
- ✅ Share patient records securely
- ✅ Backup DICOM studies to cloud storage

## 📞 Need Help?

If you get stuck:
1. Check the Flask backend logs for error messages
2. Check the browser console (F12) for JavaScript errors
3. Verify all Azure AD settings match this guide
4. Make sure the `.env` file has no typos

## 🔐 Security Notes

- Never commit the `.env` file to Git (it contains secrets!)
- The `.env.example` file is safe to commit (no secrets)
- Client secrets expire - you'll need to renew them periodically
- Keep your Azure AD app credentials secure
