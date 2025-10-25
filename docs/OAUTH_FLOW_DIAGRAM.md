# 🔐 OAuth Authentication Flow

## 📊 Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LOGIN PAGE (localhost:5000/login)                │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  🏥🇿🇦 South African Medical Imaging System                   │ │
│  │                                                               │ │
│  │  ┌─────────────────────────────────────────────────────┐    │ │
│  │  │  Username: [____________]                           │    │ │
│  │  │  Password: [____________]                           │    │ │
│  │  │  Role:     [▼ Select Role]                          │    │ │
│  │  │  [🚀 Secure Login]                                  │    │ │
│  │  └─────────────────────────────────────────────────────┘    │ │
│  │                                                               │ │
│  │  ─────────────── OR CONTINUE WITH ───────────────            │ │
│  │                                                               │ │
│  │  [🔵 Sign in with Microsoft]  ← NEW!                        │ │
│  │  [🔴 Sign in with Google]     ← NEW!                        │ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ User clicks OAuth button
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKEND ROUTES (Flask)                           │
│                                                                     │
│  /api/auth/microsoft  ──────────────────────────────────────────┐  │
│  /api/auth/google     ──────────────────────────────────────────┤  │
│                                                                  │  │
│  • Reads OAuth config from .env                                 │  │
│  • Builds authorization URL                                     │  │
│  • Redirects to OAuth provider                                  │  │
└──────────────────────────────────────────────────────────────────┼──┘
                                                                   │
                                                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│              OAUTH PROVIDER (Microsoft/Google)                      │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  🔐 Sign in to your account                                  │ │
│  │                                                               │ │
│  │  Email:    [user@example.com]                                │ │
│  │  Password: [************]                                    │ │
│  │                                                               │ │
│  │  [Sign In]                                                   │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  User authenticates with their Microsoft/Google account            │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ OAuth provider redirects back
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              CALLBACK ROUTE (Flask Backend)                         │
│                                                                     │
│  /auth/microsoft/callback  ─────────────────────────────────────┐  │
│  /auth/google/callback     ─────────────────────────────────────┤  │
│                                                                  │  │
│  1. Receives authorization code                                 │  │
│  2. Exchanges code for access token                             │  │
│  3. Fetches user info from provider API                         │  │
│  4. Creates Flask session:                                      │  │
│     • session['user_id']                                        │  │
│     • session['username']                                       │  │
│     • session['email']                                          │  │
│     • session['oauth_provider']                                 │  │
│     • session['authenticated'] = True                           │  │
│  5. Redirects to dashboard                                      │  │
└──────────────────────────────────────────────────────────────────┼──┘
                                                                   │
                                                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DASHBOARD (localhost:5000/)                      │
│                                                                     │
│  ✅ User is now authenticated and can access:                      │
│     • Patient records                                               │
│     • DICOM images                                                  │
│     • Medical reports                                               │
│     • System features based on role                                 │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔄 Authentication Methods Comparison

| Method | Setup Required | User Experience | Security | Best For |
|--------|---------------|-----------------|----------|----------|
| **Local Auth** | None | Username + Password + Role | Basic | Development, Testing |
| **Microsoft OAuth** | Azure App Registration | Single Sign-On | Enterprise SSO | Organizations using Microsoft 365 |
| **Google OAuth** | Google Cloud Project | Single Sign-On | OAuth 2.0 | Public access, Gmail users |

## 🔐 Security Features

### Session Management
```python
session['user_id'] = user_info.get('id')
session['username'] = username
session['email'] = email
session['oauth_provider'] = 'microsoft' or 'google'
session['authenticated'] = True
session['is_admin'] = False  # Default for OAuth users
session['role'] = 'user'
```

### OAuth Scopes Requested

**Microsoft:**
- `openid` - Basic authentication
- `profile` - User's profile information
- `email` - User's email address
- `User.Read` - Read user's profile from Microsoft Graph

**Google:**
- `openid` - Basic authentication
- `profile` - User's profile information
- `email` - User's email address

## 🛡️ Error Handling

The system handles various error scenarios:

1. **OAuth Not Configured**: Shows error message on login page
2. **Authorization Failed**: Redirects to login with error message
3. **Token Exchange Failed**: Logs error and shows user-friendly message
4. **Network Errors**: Catches exceptions and provides feedback

## 🔧 Configuration Files

```
backend/
├── .env                    ← Your OAuth credentials (not in git)
├── .env.example           ← Template for OAuth setup
├── routes/
│   └── auth_routes.py     ← OAuth implementation
└── templates/
    └── login.html         ← Login page with OAuth buttons
```

## 📝 Environment Variables

```env
# Microsoft OAuth
MICROSOFT_CLIENT_ID=abc123...
MICROSOFT_CLIENT_SECRET=xyz789...
MICROSOFT_TENANT_ID=common
MICROSOFT_REDIRECT_URI=http://localhost:5000/auth/microsoft/callback

# Google OAuth
GOOGLE_CLIENT_ID=123456...
GOOGLE_CLIENT_SECRET=secret789...
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback
```

## 🎯 User Roles After OAuth Login

By default, OAuth users get:
- `role`: `user`
- `is_admin`: `False`
- `user_type`: `user`

To customize roles based on email domain or specific users, modify the callback functions in `auth_routes.py`:

```python
# Example: Grant admin to specific domain
if email.endswith('@hospital.co.za'):
    session['is_admin'] = True
    session['role'] = 'admin'
```

## 🚀 Next Steps

1. ✅ OAuth buttons added to login page
2. ✅ Backend routes implemented
3. ✅ Session management configured
4. ⏳ Configure OAuth credentials (see OAUTH_SETUP_GUIDE.md)
5. ⏳ Test authentication flow
6. ⏳ Customize user roles based on your needs
