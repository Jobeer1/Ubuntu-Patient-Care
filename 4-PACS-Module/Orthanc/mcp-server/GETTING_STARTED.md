# Getting Started with MCP Server

## 🎉 Welcome!

You've just built a complete Single Sign-On (SSO) gateway for your Ubuntu Patient Care System. This guide will help you get started in minutes.

---

## 📦 What You Have

A production-ready MCP Server with:
- ✅ Google & Microsoft SSO integration
- ✅ JWT token management
- ✅ User & role management
- ✅ Audit logging for compliance
- ✅ Context management for AI models
- ✅ Complete API documentation
- ✅ Test interface included

---

## 🚀 Quick Start (5 Minutes)

### Option 1: Automated Installation (Recommended)

**Windows:**
```cmd
cd mcp-server
install.bat
```

**Linux/Mac:**
```bash
cd mcp-server
chmod +x install.sh
./install.sh
```

This will:
1. Create virtual environment
2. Install dependencies
3. Generate secret keys
4. Setup database
5. Create default users

### Option 2: Manual Installation

```bash
cd mcp-server

# Install dependencies
pip install -r requirements.txt

# Generate secrets
python scripts/generate_secrets.py

# Create .env file
cp .env.example .env
# Edit .env and paste the generated secrets

# Setup database
python scripts/setup_database.py

# Start server
python run.py
```

---

## 🧪 Test It Works

### 1. Check Server Health
Open browser: http://localhost:8080/health

**Expected:** `{"status": "healthy"}`

### 2. View API Documentation
Open browser: http://localhost:8080/docs

**Expected:** Interactive Swagger UI

### 3. Test Login Interface
Open browser: http://localhost:8080/test

**Expected:** Beautiful login page with SSO buttons

### 4. List Users
```bash
curl http://localhost:8080/users
```

**Expected:** JSON array with 3 default users

---

## 🔐 Configure OAuth (Optional for Testing)

### For Google SSO

1. **Go to Google Cloud Console**
   - https://console.cloud.google.com/

2. **Create Project**
   - Name: "Ubuntu Patient Care"

3. **Enable APIs**
   - Google+ API or Google Identity

4. **Create OAuth Credentials**
   - Application type: Web application
   - Authorized redirect URI: `http://localhost:8080/auth/google/callback`

5. **Configure OAuth Consent Screen**
   - Add test users (emails that can login during development)
   - ⚠️ **Important:** OAuth access is restricted to test users listed on your OAuth consent screen
   - You must add each user's email to the test users list before they can login

6. **Copy Credentials to .env**
   ```
   GOOGLE_CLIENT_ID=807845595525-arfmb2rtcif5b1bmpg86aji9dlv4pmau.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```
   
   **Note:** The client ID can always be accessed from the "Clients" tab under Google Auth Platform

7. **Restart Server**
   ```bash
   python run.py
   ```

8. **Test Login**
   - Go to: http://localhost:8080/test
   - Click "Sign in with Google"
   - Login with a test user account (must be added to OAuth consent screen)

### For Microsoft SSO

1. **Go to Azure Portal**
   - https://portal.azure.com/

2. **Your Application is Already Registered!**
   - **Display name:** Ubuntu Patient Care MCP SSO
   - **Application (client) ID:** `60271c16-3fcb-4ba7-972b-9f075200a567`
   - **Directory (tenant) ID:** `fba55b68-1de1-4d10-a7cc-efa55942f829`
   - **Object ID:** `5da23eaa-b5dc-4331-8602-c37e33989bf8`
   - **Supported accounts:** All Microsoft account users

3. **Verify Redirect URI**
   - Go to: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Authentication/appId/60271c16-3fcb-4ba7-972b-9f075200a567
   - Check redirect URI: `http://localhost:8080/auth/microsoft/callback`
   - Should show: **1 web** redirect URI

4. **Create Client Secret** (if not already done)
   - Go to "Certificates & secrets"
   - Click "New client secret"
   - Description: "MCP Server Secret"
   - Expires: Choose duration (e.g., 24 months)
   - Click "Add"
   - **⚠️ IMPORTANT:** Copy the secret VALUE immediately (won't be shown again)

5. **Copy Credentials to .env**
   ```
   MICROSOFT_CLIENT_ID=60271c16-3fcb-4ba7-972b-9f075200a567
   MICROSOFT_CLIENT_SECRET=your-client-secret-value-here
   MICROSOFT_TENANT_ID=fba55b68-1de1-4d10-a7cc-efa55942f829
   ```

6. **Restart Server**
   ```bash
   python run.py
   ```

7. **Test Login**
   - Go to: http://localhost:8080/test
   - Click "Sign in with Microsoft"
   - Login with any Microsoft account (personal or work)

---

## 📚 Key Endpoints

### Authentication
- `GET /auth/google` - Login with Google
- `GET /auth/microsoft` - Login with Microsoft
- `GET /auth/status` - Check if logged in
- `GET /auth/logout` - Logout

### Token Management
- `POST /token/validate` - Validate JWT (for PACS/RIS)
- `POST /token/refresh` - Refresh expired token

### User Management
- `GET /users` - List all users
- `POST /users` - Create new user
- `GET /users/{id}` - Get user details
- `PUT /users/{id}` - Update user

### Audit Logs
- `GET /audit/logs` - View all logs (admin)
- `GET /audit/user/{id}` - User's activity

### System
- `GET /` - Server info
- `GET /health` - Health check
- `GET /docs` - API documentation
- `GET /test` - Test login page

---

## 🎯 Next Steps

### 1. Test Without OAuth (Immediate)

You can test the MCP server immediately without OAuth:

```bash
# Create a test user
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@clinic.org",
    "name": "Test Doctor",
    "role": "Radiologist"
  }'

# View all users
curl http://localhost:8080/users

# Check audit logs
curl http://localhost:8080/audit/logs
```

### 2. Configure OAuth (For SSO)

Follow the OAuth configuration steps above to enable one-click login.

### 3. Integrate with RIS

Modify your RIS frontend to:
1. Add SSO login buttons
2. Redirect to MCP for authentication
3. Store JWT token
4. Include token in API requests

Example RIS login page:
```html
<button onclick="window.location.href='http://localhost:8080/auth/google'">
  Sign in with Google
</button>
```

### 4. Integrate with PACS

Setup Nginx reverse proxy to:
1. Intercept PACS requests
2. Validate JWT with MCP
3. Forward valid requests to Orthanc

See: `SSO_IMPLEMENTATION_GUIDE.md` for details

### 5. Deploy to Production

1. Setup HTTPS/TLS
2. Use PostgreSQL instead of SQLite
3. Configure production URLs
4. Enable rate limiting
5. Setup monitoring

---

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| `README.md` | Main documentation |
| `QUICKSTART.md` | 5-minute setup guide |
| `GETTING_STARTED.md` | This file - first steps |
| `TESTING.md` | Complete testing guide |
| `ARCHITECTURE.md` | System architecture diagrams |
| `PROJECT_SUMMARY.md` | Complete feature list |
| `/docs` | Interactive API docs (when server running) |

---

## 🔧 Common Tasks

### View Logs
```bash
tail -f logs/mcp-server.log
```

### Check Database
```bash
sqlite3 mcp_server.db "SELECT * FROM users;"
```

### Create Admin User
```bash
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@clinic.org",
    "name": "System Admin",
    "role": "Admin"
  }'
```

### Reset Database
```bash
rm mcp_server.db
python scripts/setup_database.py
```

### Generate New Secrets
```bash
python scripts/generate_secrets.py
```

---

## 🆘 Troubleshooting

### Server won't start
```bash
# Check Python version (need 3.8+)
python --version

# Reinstall dependencies
pip install -r requirements.txt

# Check logs
cat logs/mcp-server.log
```

### OAuth not working
1. Check credentials in `.env`
2. Verify redirect URIs match exactly
3. Restart server after changing `.env`
4. Check browser console for errors

### Database errors
```bash
# Reset database
rm mcp_server.db
python scripts/setup_database.py
```

### Port already in use
Edit `.env` and change `MCP_PORT=8080` to another port

---

## 💡 Tips

1. **Use the test interface** at `/test` for quick testing
2. **Check API docs** at `/docs` for all endpoints
3. **View audit logs** to see all activity
4. **Start without OAuth** to test basic functionality
5. **Read TESTING.md** for comprehensive test procedures

---

## 🎓 Learning Path

### Day 1: Setup & Testing
1. ✅ Install MCP server
2. ✅ Test health endpoint
3. ✅ View API documentation
4. ✅ Create test users
5. ✅ View audit logs

### Day 2: OAuth Configuration
1. ✅ Register with Google
2. ✅ Configure Google OAuth
3. ✅ Test Google login
4. ✅ Register with Microsoft
5. ✅ Test Microsoft login

### Day 3: RIS Integration
1. ✅ Modify RIS login page
2. ✅ Add SSO buttons
3. ✅ Handle JWT tokens
4. ✅ Test end-to-end flow

### Day 4: PACS Integration
1. ✅ Setup Nginx proxy
2. ✅ Configure JWT validation
3. ✅ Test PACS access
4. ✅ Verify audit logging

### Day 5: Production Deployment
1. ✅ Setup HTTPS
2. ✅ Configure PostgreSQL
3. ✅ Deploy to server
4. ✅ Monitor and test

---

## 🎉 Success Checklist

- [ ] MCP server running
- [ ] Health check passes
- [ ] API docs accessible
- [ ] Can create users
- [ ] Can view audit logs
- [ ] Google OAuth configured (optional)
- [ ] Microsoft OAuth configured (optional)
- [ ] Test login works
- [ ] JWT tokens generated
- [ ] Token validation works

---

## 📞 Need Help?

1. **Check logs:** `tail -f logs/mcp-server.log`
2. **View audit logs:** `curl http://localhost:8080/audit/logs`
3. **Read documentation:** See files in `mcp-server/` folder
4. **Test endpoints:** Use `/docs` for interactive testing

---

## 🚀 You're Ready!

Your MCP Server is now set up and ready to provide secure Single Sign-On for your Ubuntu Patient Care System.

**Next:** Configure OAuth credentials and integrate with RIS/PACS

**Questions?** Check the documentation files or view logs for troubleshooting.

---

**Happy Coding! 🎉**
