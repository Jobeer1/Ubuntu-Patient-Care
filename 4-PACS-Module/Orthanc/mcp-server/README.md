# MCP Server - Single Sign-On Gateway
## Ubuntu Patient Care System

A lightweight, user-friendly authentication gateway for PACS and RIS modules.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd mcp-server
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your Google/Microsoft credentials
```

### 3. Initialize Database
```bash
python scripts/setup_database.py
```

### 4. Start Server
```bash
python run.py
```

Server runs on: http://localhost:8080

## 🔑 Features

- ✅ One-click Google/Microsoft SSO
- ✅ JWT token generation and validation
- ✅ Role-based access control (RBAC)
- ✅ Audit logging for compliance
- ✅ Context management for AI models
- ✅ PACS/RIS integration ready

## ⚠️ Important: OAuth Test Users

**Google OAuth is restricted to test users during development!**

Before users can login:
1. Go to Google Cloud Console → OAuth consent screen
2. Add their email to the "Test users" list
3. See `OAUTH_SETUP_GUIDE.md` for detailed instructions

**Your Client ID:** `807845595525-arfmb2rtcif5b1bmpg86aji9dlv4pmau.apps.googleusercontent.com`  
**Find it:** Google Cloud Console → APIs & Services → Credentials → Clients tab

## 📋 Default Users

After setup, test with these accounts:

| Email | Role | Password (SSO) |
|-------|------|----------------|
| admin@clinic.org | Admin | Use Google/Microsoft |
| radiologist@clinic.org | Radiologist | Use Google/Microsoft |
| tech@clinic.org | Technician | Use Google/Microsoft |

## 🔧 Configuration

Edit `.env` file:
- Add Google Client ID/Secret
- Add Microsoft Client ID/Secret
- Set JWT secret key
- Configure RIS/PACS URLs

## 🎨 User Interfaces

### Admin Dashboard
- **URL:** http://localhost:8080/admin
- **Features:**
  - 👥 User management (add, edit, view)
  - 🎭 Role assignment (Admin, Radiologist, Technician, Typist, Referring Doctor)
  - 📊 User statistics
  - 📋 Audit log viewer
  - 🔍 Search and filter
  - ✨ Beautiful, user-friendly interface

### Test Login Page
- **URL:** http://localhost:8080/test
- **Features:**
  - Test Google/Microsoft SSO
  - Check authentication status
  - Logout functionality

## 📚 API Endpoints

### Authentication
- `GET /auth/google` - Login with Google
- `GET /auth/microsoft` - Login with Microsoft
- `GET /auth/logout` - Logout
- `GET /auth/status` - Check login status

### Token Management
- `POST /token/validate` - Validate JWT
- `POST /token/refresh` - Refresh token

### User Management
- `GET /users` - List users (admin)
- `POST /users` - Create user (admin)
- `GET /users/:id` - Get user details

### Audit
- `GET /audit/logs` - View audit logs (admin)

## 🔒 Security

- HTTPS required in production
- JWT tokens expire in 1 hour
- All access logged for compliance
- MFA enforced via Google/Microsoft

## 📞 Support

For issues, check logs in `logs/mcp-server.log`
