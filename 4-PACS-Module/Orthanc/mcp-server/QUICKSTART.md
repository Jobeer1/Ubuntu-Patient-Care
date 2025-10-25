# MCP Server - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependencies (1 minute)
```bash
cd mcp-server
pip install -r requirements.txt
```

### Step 2: Generate Secret Keys (30 seconds)
```bash
python scripts/generate_secrets.py
```
Copy the generated keys.

### Step 3: Configure Environment (2 minutes)
```bash
cp .env.example .env
```

Edit `.env` file:
1. Paste the secret keys from Step 2
2. Add your Google OAuth credentials (optional for now)
3. Add your Microsoft OAuth credentials (optional for now)

**For testing without OAuth:**
You can skip OAuth configuration and use the API directly.

### Step 4: Setup Database (30 seconds)
```bash
python scripts/setup_database.py
```

This creates:
- Database tables
- Default roles (Admin, Radiologist, Technician, Typist)
- Test users

### Step 5: Start Server (30 seconds)
```bash
python run.py
```

Server starts at: **http://localhost:8080**

### Step 6: Test the Server (30 seconds)

Open your browser:
- **Admin Dashboard:** http://localhost:8080/admin ⭐ NEW!
- **API Documentation:** http://localhost:8080/docs
- **Test Login:** http://localhost:8080/test
- **Health Check:** http://localhost:8080/health
- **Server Info:** http://localhost:8080

---

## 🧪 Testing Without OAuth

### Test JWT Token Generation

1. Open http://localhost:8080/docs
2. Go to `/users` endpoint
3. Click "Try it out"
4. Create a test user
5. Use the user ID to test token validation

### Test with cURL

```bash
# Check server status
curl http://localhost:8080/health

# List users
curl http://localhost:8080/users

# Create a user
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","name":"Test User","role":"Radiologist"}'
```

---

## 🔐 Setting Up OAuth (Optional)

### Google OAuth Setup

1. Go to https://console.cloud.google.com/
2. Create a new project
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add redirect URI: `http://localhost:8080/auth/google/callback`
6. **Configure OAuth Consent Screen:**
   - Add test users (required for development)
   - ⚠️ Only test users can login until app is published
7. Copy Client ID and Secret to `.env`
   - Example Client ID: `807845595525-arfmb2rtcif5b1bmpg86aji9dlv4pmau.apps.googleusercontent.com`
   - Find your Client ID in the "Clients" tab under Google Auth Platform

### Microsoft OAuth Setup

**Your app is already registered!**

**Application Details:**
- Display name: Ubuntu Patient Care MCP SSO
- Client ID: `60271c16-3fcb-4ba7-972b-9f075200a567`
- Tenant ID: `fba55b68-1de1-4d10-a7cc-efa55942f829`
- Redirect URI: `http://localhost:8080/auth/microsoft/callback` ✓

**Steps:**
1. Go to https://portal.azure.com/ → App registrations
2. Find "Ubuntu Patient Care MCP SSO"
3. Go to "Certificates & secrets" → Create new client secret
4. Copy the secret VALUE immediately
5. Add to `.env`:
   ```
   MICROSOFT_CLIENT_ID=60271c16-3fcb-4ba7-972b-9f075200a567
   MICROSOFT_CLIENT_SECRET=your-secret-value
   MICROSOFT_TENANT_ID=fba55b68-1de1-4d10-a7cc-efa55942f829
   ```

### Test OAuth Login

1. Restart the server: `python run.py`
2. Visit: http://localhost:8080/auth/google
3. Login with your Google account
4. You'll be redirected with a JWT token

---

## 📊 View Logs

```bash
tail -f logs/mcp-server.log
```

---

## 🔧 Troubleshooting

### "Module not found" error
```bash
pip install -r requirements.txt
```

### "Database locked" error
Stop the server and delete `mcp_server.db`, then run setup again:
```bash
rm mcp_server.db
python scripts/setup_database.py
```

### OAuth not working
1. Check `.env` has correct credentials
2. Verify redirect URIs match exactly
3. Check logs: `tail -f logs/mcp-server.log`

---

## 🎯 Next Steps

1. **Integrate with RIS:** Modify RIS frontend to use MCP authentication
2. **Setup PACS Proxy:** Configure Nginx to validate JWT tokens
3. **Add More Users:** Use the `/users` API endpoint
4. **View Audit Logs:** Check `/audit/logs` endpoint

---

## 📚 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/google` | GET | Login with Google |
| `/auth/microsoft` | GET | Login with Microsoft |
| `/auth/logout` | GET | Logout |
| `/auth/status` | GET | Check auth status |
| `/token/validate` | POST | Validate JWT token |
| `/token/refresh` | POST | Refresh token |
| `/users` | GET | List users |
| `/users` | POST | Create user |
| `/users/{id}` | GET | Get user |
| `/audit/logs` | GET | View audit logs |

Full API documentation: http://localhost:8080/docs

---

## 💡 Tips

- Use the interactive API docs at `/docs` for testing
- Check audit logs to see all authentication events
- JWT tokens expire in 1 hour by default
- All passwords are handled by Google/Microsoft (no local passwords)

---

## 🆘 Need Help?

Check the logs:
```bash
cat logs/mcp-server.log
```

View recent audit events:
```bash
curl http://localhost:8080/audit/logs
```
