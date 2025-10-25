# 🚀 OAuth Quick Start - 5 Minute Setup

## ✅ What's Already Done

The login page at `http://localhost:5000/login` now has:
- ✅ Microsoft OAuth button
- ✅ Google OAuth button  
- ✅ Backend OAuth routes configured
- ✅ Session management for OAuth users
- ✅ Automatic redirect to dashboard after login

## 🔧 Quick Setup (Choose One or Both)

### Option 1: Microsoft OAuth (Recommended for Organizations)

1. **Get Credentials** (5 minutes):
   - Go to [Azure Portal](https://portal.azure.com)
   - Azure Active Directory → App registrations → New registration
   - Redirect URI: `http://localhost:5000/auth/microsoft/callback`
   - Copy Client ID and create Client Secret

2. **Configure Backend**:
   ```bash
   cd 4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend
   copy .env.example .env
   ```
   
   Edit `.env`:
   ```env
   MICROSOFT_CLIENT_ID=your-client-id
   MICROSOFT_CLIENT_SECRET=your-client-secret
   MICROSOFT_TENANT_ID=common
   ```

3. **Restart Backend**:
   ```bash
   python app.py
   ```

4. **Test**: Click "Sign in with Microsoft" at `http://localhost:5000/login`

### Option 2: Google OAuth (Recommended for Public Access)

1. **Get Credentials** (5 minutes):
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create project → APIs & Services → Credentials
   - Create OAuth client ID (Web application)
   - Redirect URI: `http://localhost:5000/auth/google/callback`
   - Copy Client ID and Client Secret

2. **Configure Backend**:
   ```bash
   cd 4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend
   copy .env.example .env
   ```
   
   Edit `.env`:
   ```env
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

3. **Restart Backend**:
   ```bash
   python app.py
   ```

4. **Test**: Click "Sign in with Google" at `http://localhost:5000/login`

## 🎯 Without OAuth Configuration

If you don't configure OAuth, the system still works perfectly with:
- Username/password authentication
- Three user roles: admin, doctor, user
- Default credentials: admin/admin, doctor/doctor, user/user

The OAuth buttons will show an error message if clicked without configuration.

## 📝 Files Modified

1. `backend/routes/auth_routes.py` - Added OAuth routes
2. `backend/templates/login.html` - Updated with OAuth buttons
3. `backend/.env.example` - OAuth configuration template
4. `OAUTH_SETUP_GUIDE.md` - Detailed setup instructions

## 🔍 Testing

1. **Local Auth**: Works immediately, no setup needed
2. **Microsoft OAuth**: Requires Azure app registration
3. **Google OAuth**: Requires Google Cloud project

## 📚 Need More Help?

See `OAUTH_SETUP_GUIDE.md` for detailed step-by-step instructions with screenshots and troubleshooting.
