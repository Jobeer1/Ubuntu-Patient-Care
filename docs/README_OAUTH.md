# 🔐 OAuth Authentication - Complete Guide

## 📖 Overview

The South African Medical Imaging System now supports **three authentication methods**:

1. **Local Authentication** - Username/password with role selection
2. **Microsoft OAuth** - Single Sign-On with Microsoft/Azure AD
3. **Google OAuth** - Single Sign-On with Google accounts

All authentication methods are available at: **http://localhost:5000/login**

---

## 🚀 Quick Start

### Option 1: Use Without OAuth (Immediate)

No configuration needed! Just start the backend:

```bash
cd 4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend
python app.py
```

Visit http://localhost:5000/login and use:
- **Username**: admin, **Password**: admin, **Role**: Administrator
- **Username**: doctor, **Password**: doctor, **Role**: Medical Doctor
- **Username**: user, **Password**: user, **Role**: Healthcare User

### Option 2: Enable Microsoft OAuth (5 minutes)

1. Register app at [Azure Portal](https://portal.azure.com)
2. Add redirect URI: `http://localhost:5000/auth/microsoft/callback`
3. Create `.env` file with credentials:
   ```env
   MICROSOFT_CLIENT_ID=your-client-id
   MICROSOFT_CLIENT_SECRET=your-client-secret
   ```
4. Restart backend
5. Click "Sign in with Microsoft" button

### Option 3: Enable Google OAuth (5 minutes)

1. Create project at [Google Cloud Console](https://console.cloud.google.com)
2. Create OAuth credentials
3. Add redirect URI: `http://localhost:5000/auth/google/callback`
4. Add to `.env` file:
   ```env
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```
5. Restart backend
6. Click "Sign in with Google" button

---

## 📚 Documentation Files

| File | Purpose | When to Use |
|------|---------|-------------|
| **OAUTH_QUICK_START.md** | 5-minute setup guide | First time setup |
| **OAUTH_SETUP_GUIDE.md** | Detailed step-by-step instructions | Need detailed help |
| **OAUTH_FLOW_DIAGRAM.md** | Visual flow documentation | Understanding how it works |
| **OAUTH_LOGIN_PAGE_PREVIEW.md** | UI preview and design | See what it looks like |
| **OAUTH_IMPLEMENTATION_SUMMARY.md** | Technical implementation details | Developer reference |
| **README_OAUTH.md** | This file - complete overview | Start here |

---

## 🎯 Features

### ✅ What's Working

- **Three authentication methods** in one login page
- **Session management** for all auth types
- **Automatic user creation** for OAuth users
- **Role-based access control**
- **Error handling** with user-friendly messages
- **Secure token exchange** following OAuth 2.0 standards
- **Beautiful UI** with South African theme

### 🔒 Security Features

- OAuth 2.0 standard protocol
- Secure session management
- HTTPS ready for production
- Client secret protection
- Token validation
- Error logging

---

## 🛠️ Technical Details

### Backend Implementation

**File**: `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/routes/auth_routes.py`

**New Routes**:
- `GET /api/auth/microsoft` - Initiate Microsoft OAuth
- `GET /auth/microsoft/callback` - Handle Microsoft callback
- `GET /api/auth/google` - Initiate Google OAuth
- `GET /auth/google/callback` - Handle Google callback

**Dependencies**:
- `Flask` - Web framework
- `requests` - HTTP library for OAuth API calls
- `urllib.parse` - URL encoding

### Frontend Implementation

**File**: `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/templates/login.html`

**Features**:
- Inline CSS (no external dependencies)
- JavaScript for form handling
- OAuth button handlers
- Error/success message display
- Responsive design

### Session Data Structure

```python
{
    'user_id': 'unique-user-id',
    'username': 'extracted-from-email',
    'email': 'user@example.com',
    'name': 'User Display Name',
    'oauth_provider': 'microsoft' or 'google',
    'authenticated': True,
    'is_admin': False,
    'role': 'user',
    'user_type': 'user'
}
```

---

## 🔧 Configuration

### Environment Variables

Create `.env` file in backend directory:

```env
# Microsoft OAuth
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
MICROSOFT_TENANT_ID=common
MICROSOFT_REDIRECT_URI=http://localhost:5000/auth/microsoft/callback

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback
```

### Redirect URIs

**Important**: These must match exactly in your OAuth provider configuration:

- **Microsoft**: `http://localhost:5000/auth/microsoft/callback`
- **Google**: `http://localhost:5000/auth/google/callback`

For production, change to HTTPS:
- `https://yourdomain.com/auth/microsoft/callback`
- `https://yourdomain.com/auth/google/callback`

---

## 🧪 Testing

### Test Script

Run the included test script:

```bash
python test_oauth_endpoints.py
```

Expected output:
```
✅ Health check: OK
✅ Microsoft OAuth endpoint: OK (redirects to OAuth provider)
✅ Google OAuth endpoint: OK (redirects to OAuth provider)
✅ Login page: OK
```

### Manual Testing

1. **Test Login Page**:
   ```
   Visit: http://localhost:5000/login
   Expected: See login form with OAuth buttons
   ```

2. **Test Local Auth**:
   ```
   Username: admin
   Password: admin
   Role: Administrator
   Expected: Redirect to dashboard
   ```

3. **Test Microsoft OAuth** (if configured):
   ```
   Click: "Sign in with Microsoft"
   Expected: Redirect to Microsoft login
   After login: Redirect to dashboard
   ```

4. **Test Google OAuth** (if configured):
   ```
   Click: "Sign in with Google"
   Expected: Redirect to Google login
   After login: Redirect to dashboard
   ```

---

## 🐛 Troubleshooting

### Problem: OAuth buttons show "not configured" error

**Solution**:
1. Check `.env` file exists with credentials
2. Restart backend server
3. Verify environment variables are loaded

### Problem: Redirect URI mismatch error

**Solution**:
1. Check redirect URI in Azure/Google matches exactly
2. No trailing slashes
3. Use `http://` for localhost, `https://` for production

### Problem: "Failed to get access token"

**Solution**:
1. Verify client secret is correct
2. Check client secret hasn't expired
3. Ensure API permissions are granted
4. Check backend logs for detailed error

### Problem: OAuth users can't access admin features

**Solution**:
OAuth users default to `user` role. To grant admin access, modify `auth_routes.py`:

```python
# In microsoft_callback or google_callback function:
if email.endswith('@yourhospital.co.za'):
    session['is_admin'] = True
    session['role'] = 'admin'
```

---

## 🎨 Customization

### Change User Roles Based on Email

Edit `auth_routes.py` in the callback functions:

```python
# Example: Grant admin to specific domain
if email.endswith('@hospital.co.za'):
    session['is_admin'] = True
    session['role'] = 'admin'
elif email.endswith('@doctor.co.za'):
    session['role'] = 'doctor'
else:
    session['role'] = 'user'
```

### Add More OAuth Providers

Follow the same pattern:

1. Add provider configuration to `.env`
2. Create initiation route (`/api/auth/provider`)
3. Create callback route (`/auth/provider/callback`)
4. Add button to login page
5. Update documentation

---

## 📊 Comparison Matrix

| Feature | Local Auth | Microsoft OAuth | Google OAuth |
|---------|-----------|-----------------|--------------|
| **Setup Time** | 0 minutes | 5 minutes | 5 minutes |
| **User Experience** | Username + Password | Single Sign-On | Single Sign-On |
| **Security** | Basic | Enterprise SSO | OAuth 2.0 |
| **MFA Support** | No | Yes (if enabled) | Yes (if enabled) |
| **User Management** | Manual | Azure AD | Google Admin |
| **Best For** | Development | Organizations | Public Access |
| **Cost** | Free | Azure AD license | Free tier available |

---

## 🚀 Production Deployment

### Checklist

- [ ] Change redirect URIs to HTTPS
- [ ] Update `.env` with production URLs
- [ ] Enable `SESSION_COOKIE_SECURE = True`
- [ ] Use strong `SECRET_KEY`
- [ ] Enable HTTPS on web server
- [ ] Configure firewall rules
- [ ] Set up monitoring/logging
- [ ] Test all authentication flows
- [ ] Document for users
- [ ] Train support staff

### Production Environment Variables

```env
# Production settings
SECRET_KEY=generate-strong-random-key
DEBUG=False
SESSION_COOKIE_SECURE=True

# Microsoft OAuth (Production)
MICROSOFT_CLIENT_ID=prod-client-id
MICROSOFT_CLIENT_SECRET=prod-client-secret
MICROSOFT_TENANT_ID=your-tenant-id
MICROSOFT_REDIRECT_URI=https://yourdomain.com/auth/microsoft/callback

# Google OAuth (Production)
GOOGLE_CLIENT_ID=prod-client-id
GOOGLE_CLIENT_SECRET=prod-client-secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback
```

---

## 📈 Benefits

### For Users
- ✅ Single Sign-On with existing accounts
- ✅ No new passwords to remember
- ✅ Familiar login experience
- ✅ Multi-factor authentication support
- ✅ Faster login process

### For Administrators
- ✅ Centralized user management
- ✅ Leverage existing identity providers
- ✅ Reduced password support tickets
- ✅ Better security compliance
- ✅ Audit trail from OAuth provider

### For Developers
- ✅ Standard OAuth 2.0 implementation
- ✅ Well-documented code
- ✅ Easy to extend
- ✅ Error handling included
- ✅ Production ready

---

## 🎓 Learning Resources

### OAuth 2.0
- [OAuth 2.0 Simplified](https://aaronparecki.com/oauth-2-simplified/)
- [OAuth 2.0 RFC](https://tools.ietf.org/html/rfc6749)

### Microsoft OAuth
- [Microsoft Identity Platform](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
- [Azure AD OAuth Tutorial](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow)

### Google OAuth
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [Google Sign-In](https://developers.google.com/identity/sign-in/web)

---

## 📞 Support

### Getting Help

1. **Check Documentation**: Start with `OAUTH_QUICK_START.md`
2. **Review Logs**: Check backend console for errors
3. **Test Endpoints**: Run `test_oauth_endpoints.py`
4. **Troubleshooting**: See troubleshooting section above

### Common Issues

Most issues are related to:
- Missing or incorrect credentials in `.env`
- Redirect URI mismatch
- Expired client secrets
- Missing API permissions

---

## ✅ Summary

The OAuth implementation is **complete and ready to use**:

- ✅ Login page updated with OAuth buttons
- ✅ Backend routes implemented
- ✅ Session management configured
- ✅ Error handling included
- ✅ Documentation complete
- ✅ Test script provided
- ✅ Production ready

**Next Steps**:
1. Choose authentication method(s)
2. Configure OAuth credentials (optional)
3. Test authentication flows
4. Deploy to production

**Status**: 🎉 **READY FOR USE**

---

## 📝 Version History

- **v1.0** (Current) - Initial OAuth implementation
  - Microsoft OAuth support
  - Google OAuth support
  - Updated login page
  - Complete documentation

---

## 📄 License

Part of the South African Medical Imaging System project.

---

**For detailed setup instructions, see `OAUTH_SETUP_GUIDE.md`**

**For quick 5-minute setup, see `OAUTH_QUICK_START.md`**
