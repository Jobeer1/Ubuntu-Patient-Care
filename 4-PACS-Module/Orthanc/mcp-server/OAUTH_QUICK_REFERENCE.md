# Google OAuth - Quick Reference Card

## 🔐 Your OAuth Configuration

### Google OAuth

**Client ID:**
```
807845595525-arfmb2rtcif5b1bmpg86aji9dlv4pmau.apps.googleusercontent.com
```

**Where to find it:**
- Google Cloud Console → APIs & Services → Credentials
- Look under "OAuth 2.0 Client IDs"
- Click on "Clients" tab

### Microsoft OAuth

**Application (Client) ID:**
```
60271c16-3fcb-4ba7-972b-9f075200a567
```

**Directory (Tenant) ID:**
```
fba55b68-1de1-4d10-a7cc-efa55942f829
```

**Where to find it:**
- Azure Portal → App registrations → Ubuntu Patient Care MCP SSO
- Or: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Overview/appId/60271c16-3fcb-4ba7-972b-9f075200a567

---

## ⚠️ Critical: Test Users

**OAuth access is restricted to test users!**

### Add Test Users
1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. Scroll to "Test users" section
3. Click "Add Users"
4. Enter email addresses
5. Click "Save"

### Who Can Login?
- ✅ Only users added to test users list
- ❌ Other users will get "Error 403: access_denied"

---

## 📝 Configuration in .env

### Google OAuth
```env
GOOGLE_CLIENT_ID=807845595525-arfmb2rtcif5b1bmpg86aji9dlv4pmau.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret-here
GOOGLE_REDIRECT_URI=http://localhost:8080/auth/google/callback
```

### Microsoft OAuth
```env
MICROSOFT_CLIENT_ID=60271c16-3fcb-4ba7-972b-9f075200a567
MICROSOFT_CLIENT_SECRET=your-secret-here
MICROSOFT_TENANT_ID=fba55b68-1de1-4d10-a7cc-efa55942f829
MICROSOFT_REDIRECT_URI=http://localhost:8080/auth/microsoft/callback
```

---

## 🚀 Quick Setup Steps

1. **Add test users** (critical!)
   - https://console.cloud.google.com/apis/credentials/consent
   
2. **Copy credentials to .env**
   - Client ID (above)
   - Client Secret (from Google Console)
   
3. **Restart server**
   ```bash
   python run.py
   ```
   
4. **Test login**
   - http://localhost:8080/test
   - Use test user account

---

## 🔧 Common Issues

### Google: "Error 403: access_denied"
**Solution:** Add user to test users list in Google Console

### Google: "redirect_uri_mismatch"
**Solution:** Verify redirect URI: `http://localhost:8080/auth/google/callback`

### Microsoft: "Invalid client secret"
**Solution:** Create new client secret in Azure Portal → Certificates & secrets

### Microsoft: "redirect_uri_mismatch"
**Solution:** Verify redirect URI: `http://localhost:8080/auth/microsoft/callback`

### "Client ID not found"
**Solution:** Check `.env` file has correct Client IDs

---

## 📚 Full Documentation

- **Google OAuth:** `OAUTH_SETUP_GUIDE.md`
- **Microsoft OAuth:** `MICROSOFT_OAUTH_GUIDE.md`
- **Getting Started:** `GETTING_STARTED.md`

---

**Quick Links:**

### Google
- **Console:** https://console.cloud.google.com/
- **OAuth Consent:** https://console.cloud.google.com/apis/credentials/consent
- **Credentials:** https://console.cloud.google.com/apis/credentials

### Microsoft
- **Azure Portal:** https://portal.azure.com/
- **Your App:** https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Overview/appId/60271c16-3fcb-4ba7-972b-9f075200a567
- **App Registrations:** https://portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/~/RegisteredApps

### Testing
- **Test Login:** http://localhost:8080/test
- **Admin Dashboard:** http://localhost:8080/admin
- **API Docs:** http://localhost:8080/docs
