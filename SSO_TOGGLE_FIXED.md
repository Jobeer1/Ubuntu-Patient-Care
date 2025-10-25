# SSO Toggle - Fixed and Moved to Admin Page

## What Was Fixed

I've moved the SSO toggle button to the **correct location** - the admin page at http://localhost:8080/admin

## Changes Made

### 1. Added SSO Toggle to Admin Page
- **Location**: http://localhost:8080/admin
- **File**: `4-PACS-Module/Orthanc/mcp-server/static/admin-dashboard.html`
- **Position**: Right after the "System Modules" panel, before the tabs

### 2. Removed SSO Toggle from Regular Dashboard
- Cleaned up the regular dashboard (http://localhost:8080/dashboard)
- SSO toggle is now ONLY on the admin page

### 3. Backend Already Configured
- API endpoints already added to `auth.py`:
  - `GET /auth/sso/status` - Check SSO status
  - `POST /auth/sso/toggle` - Toggle SSO (admin only)

## How to Use

### Step 1: Restart MCP Server
```powershell
# Stop current server (Ctrl+C)
cd C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\4-PACS-Module\Orthanc\mcp-server
py run.py
```

### Step 2: Login as Admin
- Go to http://localhost:8080
- Click "Sign in with Microsoft" (or Google)
- Complete SSO login

### Step 3: Access Admin Page
After logging in, you'll be redirected to: **http://localhost:8080/admin**

### Step 4: Find the SSO Toggle
Look for the panel right below "System Modules":

```
┌─────────────────────────────────────────────────────────────┐
│ 🔐 SSO Authentication Control                               │
│ Enable or disable Single Sign-On for all users              │
│                                                              │
│ SSO Status: [🟢 Enabled]              [🔒 Disable SSO]     │
└─────────────────────────────────────────────────────────────┘
```

### Step 5: Toggle SSO
Click the button to enable or disable SSO for all users.

## What You'll See

### Admin Page Layout (http://localhost:8080/admin)

```
┌─────────────────────────────────────────────────────────────┐
│ 🏥🇿🇦 South African Medical Imaging - Admin                 │
│ User & Role Management for Ubuntu Patient Care System       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ System Modules                                               │
│ [Dictation] [PACS] [RIS] [Billing]                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 🔐 SSO Authentication Control                    ← HERE!    │
│ Enable or disable Single Sign-On for all users              │
│                                                              │
│ SSO Status: [🟢 Enabled]              [🔒 Disable SSO]     │
└─────────────────────────────────────────────────────────────┘

[👥 Users] [🔒 Patient Access] [👨‍⚕️ Doctor Assignment] ...
```

## Testing

### Quick Test
1. Restart MCP server
2. Login via Microsoft SSO
3. You should land on http://localhost:8080/admin
4. Look for the gold-bordered "SSO Authentication Control" panel
5. Click the toggle button
6. You should see a success message
7. The button text should change

### Full Test
1. **Enable SSO** (if disabled)
2. **Logout**
3. **Check login page** - SSO buttons should be visible
4. **Login as admin again**
5. **Disable SSO**
6. **Logout**
7. **Check login page** - SSO buttons should be hidden
8. **Try to access** `/auth/google` or `/auth/microsoft` directly
9. **Should redirect** with error message

## Troubleshooting

### "I don't see the SSO toggle on the admin page"

**Check:**
1. Are you on http://localhost:8080/admin (not /dashboard)?
2. Did you restart the MCP server after the changes?
3. Are you logged in as an admin?

**Solution:**
```powershell
# Restart server
cd C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\4-PACS-Module\Orthanc\mcp-server
# Press Ctrl+C to stop
py run.py
```

### "The toggle button doesn't work"

**Check browser console (F12):**
- Look for JavaScript errors
- Check network tab for failed API calls

**Check server logs:**
- Look for authentication errors
- Verify JWT token is valid

### "I'm redirected to dashboard instead of admin page"

**This is correct behavior for non-admin users!**

Only users with role "Admin" are redirected to /admin.
Other users go to /dashboard.

**To verify your role:**
- Open browser console (F12)
- Type: `document.cookie`
- Look for the access_token
- Decode it at jwt.io to see your role

## Files Modified

1. `4-PACS-Module/Orthanc/mcp-server/app/routes/auth.py`
   - Added SSO toggle endpoints
   - Added SSO status check to login routes

2. `4-PACS-Module/Orthanc/mcp-server/static/admin-dashboard.html`
   - Added SSO control panel UI
   - Added JavaScript functions for toggle

3. `4-PACS-Module/Orthanc/mcp-server/static/dashboard.html`
   - Removed SSO toggle (cleaned up)

## Configuration File

SSO status is stored in: `sso_config.json` (in MCP server root)

Example:
```json
{
  "enabled": true
}
```

## API Endpoints

### Check SSO Status
```bash
curl http://localhost:8080/auth/sso/status
```

Response:
```json
{
  "enabled": true,
  "microsoft_configured": true,
  "google_configured": true
}
```

### Toggle SSO (Admin Only)
```bash
curl -X POST http://localhost:8080/auth/sso/toggle \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"enabled": false}'
```

Response:
```json
{
  "success": true,
  "enabled": false,
  "message": "SSO disabled successfully"
}
```

## Summary

✅ SSO toggle is now on the **admin page** (http://localhost:8080/admin)
✅ Removed from regular dashboard
✅ Only visible to admin users
✅ Fully functional with backend API
✅ Persists across server restarts
✅ Shows real-time status updates

**Just restart the server and login as admin to see it!**
