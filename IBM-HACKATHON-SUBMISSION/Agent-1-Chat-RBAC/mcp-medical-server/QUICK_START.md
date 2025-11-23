# SSO/RBAC Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### Step 1: Install Dependencies
```bash
cd mcp-medical-server
pip install -r requirements.txt
```

### Step 2: Configure OAuth
Create `.env`:
```bash
GOOGLE_CLIENT_ID=your-id
GOOGLE_CLIENT_SECRET=your-secret
MICROSOFT_CLIENT_ID=your-id
MICROSOFT_CLIENT_SECRET=your-secret
JWT_SECRET_KEY=your-super-secret-key-32-chars
```

### Step 3: Start FastAPI Server
```bash
uvicorn server:fast_app --port 8080 --reload
```

### Step 4: Start MCP Server (separate terminal)
```bash
python server.py
```

## 🔑 Key Concepts

### OAuth 2.0 Credentials
Get from:
- **Google**: https://console.cloud.google.com/
- **Microsoft**: https://portal.azure.com/

### JWT Token
- **Generated on**: Login or OAuth callback
- **Stored in**: HTTP-only cookie
- **Expires in**: 24 hours (configurable)
- **Contains**: user_id, email, role, permissions

### Roles
- **Admin**: Full access
- **Radiologist**: Medical professionals
- **Referring Doctor**: Medical professionals
- **Technician**: Support staff
- **Patient**: Individual users

## 📝 Common Tasks

### Login via Google
```bash
# User clicks
GET http://localhost:8080/auth/google

# Redirects to Google consent, then back to callback
# JWT cookie automatically set
```

### Login via Microsoft
```bash
# User clicks
GET http://localhost:8080/auth/microsoft

# Same flow as Google
```

### Local Login
```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Returns: {"access_token": "...", "user": {...}}
```

### Get Current User
```bash
curl -X GET http://localhost:8080/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"

# Returns: {"id": 1, "email": "...", "role": "Doctor"}
```

### Check User Permissions
```bash
curl -X GET http://localhost:8080/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check for permission in response
# "can_view_patients", "can_create_reports", etc.
```

### Logout
```bash
curl -X POST http://localhost:8080/auth/logout \
  -H "Authorization: Bearer YOUR_TOKEN"

# Clears JWT cookie
```

## 🧪 Test Accounts

After setup, create test accounts:

```bash
# Create admin account
curl -X POST http://localhost:8080/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "AdminPass123!",
    "full_name": "Admin User",
    "role": "Admin"
  }'

# Create doctor account
curl -X POST http://localhost:8080/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "doctor@example.com",
    "password": "DoctorPass123!",
    "full_name": "Dr. Smith",
    "role": "Referring Doctor"
  }'

# Create patient account
curl -X POST http://localhost:8080/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "patient@example.com",
    "password": "PatientPass123!",
    "full_name": "John Patient",
    "role": "Patient"
  }'
```

## 🔒 Security Checklist

Before production:
- [ ] Set `DEBUG=false`
- [ ] Set `JWT_COOKIE_SECURE=true` (HTTPS only)
- [ ] Use strong `JWT_SECRET_KEY` (32+ chars, random)
- [ ] Configure OAuth with production URLs
- [ ] Use PostgreSQL (not SQLite)
- [ ] Enable CORS only for your domain
- [ ] Test OAuth callback URLs
- [ ] Set up monitoring/alerts
- [ ] Regular backups of auth database
- [ ] Review audit logs regularly

## 🐛 Troubleshooting

### OAuth Token Error
```bash
# Check credentials
echo $GOOGLE_CLIENT_ID
echo $GOOGLE_CLIENT_SECRET

# Test with curl
curl http://localhost:8080/auth/sso/config
```

### Permission Denied
```bash
# Check user role
curl http://localhost:8080/auth/me -H "Authorization: Bearer TOKEN"

# Check audit log
curl http://localhost:8080/auth/audit-logs -H "Authorization: Bearer ADMIN_TOKEN"
```

### Token Expired
```bash
# Login again to get new token
curl -X POST http://localhost:8080/auth/login ...

# Or refresh token
curl http://localhost:8080/auth/token -H "Authorization: Bearer TOKEN"
```

## 📚 Documentation

- **Full Guide**: `SSO_RBAC_INTEGRATION_GUIDE.md`
- **Migration Details**: `MIGRATION_COMPLETE.md`
- **API Docs**: `http://localhost:8080/docs` (auto-generated)

## 💡 Pro Tips

1. **Use JWT Token in Headers**
   ```bash
   Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
   ```

2. **Token is Auto-Set in Cookie**
   - After OAuth login, JWT is stored in HTTP-only cookie
   - Browser auto-includes it in requests
   - No manual header needed for web apps

3. **MCP Tools Protected by RBAC**
   ```python
   # In your connector code:
   permissions = get_user_permissions(user_token)
   if permissions.get("can_view_patients"):
       # Call MCP tool
   ```

4. **Cross-Server Tokens**
   - Same JWT works across PACS and Medical servers
   - Both use same JWT_SECRET_KEY
   - Same role model everywhere

5. **Audit Everything**
   - All access is logged automatically
   - View with: `GET /auth/audit-logs`
   - Includes: user, action, resource, timestamp, status

## 🎯 Next Steps

1. **Test OAuth Login**
   - Click "Login with Google/Microsoft"
   - Verify JWT cookie set
   - Verify user created in database

2. **Test RBAC Enforcement**
   - Create user with different roles
   - Verify access denied for restricted endpoints
   - Check audit logs for denials

3. **Test MCP Integration**
   - Make authenticated MCP tool call
   - Verify RBAC enforced
   - Check audit log for tool call

4. **Build Connector**
   - Use JWT for cross-server calls
   - Verify token in authorization header
   - Share JWT_SECRET_KEY between servers

## 📞 Need Help?

1. **Check Logs**: `tail -f medical_schemes.db` (or database logs)
2. **Read Docs**: `SSO_RBAC_INTEGRATION_GUIDE.md`
3. **Review Code**: `app/routes/auth.py` (all endpoints)
4. **Test API**: `http://localhost:8080/docs` (Swagger UI)

---

**Quick Reference**: Most common tasks shown above. See full guide for advanced features.
