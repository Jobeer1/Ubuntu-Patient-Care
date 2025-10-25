# 🚀 Quick Reference - MCP OAuth Integration

## ✅ Current Status

**MCP Server**: ✅ Running on port 8080
**PACS Backend**: ✅ Running on port 5000
**OAuth**: ✅ Microsoft & Google configured

---

## 🔗 URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Login Page** | http://localhost:5000/login | Main login page |
| **MCP Server** | http://localhost:8080 | SSO Gateway |
| **MCP API Docs** | http://localhost:8080/docs | API documentation |
| **PACS Health** | http://localhost:5000/api/health | Health check |

---

## 🔐 Authentication Methods

### 1. Microsoft OAuth ✅
- **Button**: "Sign in with Microsoft"
- **Endpoint**: http://localhost:8080/auth/microsoft
- **Status**: Configured and active
- **Expires**: 4/16/2026

### 2. Google OAuth ✅
- **Button**: "Sign in with Google"
- **Endpoint**: http://localhost:8080/auth/google
- **Status**: Configured and active

### 3. Local Login ✅
- **Form**: Email + Password
- **Endpoint**: http://localhost:8080/auth/login
- **Status**: Available

---

## 🎯 How to Use

### Quick Test (30 seconds)

1. Open: http://localhost:5000/login
2. Click: "Sign in with Microsoft"
3. Login with your Microsoft account
4. Done! You're authenticated

### Test with Google

1. Open: http://localhost:5000/login
2. Click: "Sign in with Google"
3. Login with your Google account
4. Done! You're authenticated

---

## 🔧 Servers

### Start MCP Server
```bash
cd 4-PACS-Module/Orthanc/mcp-server
python run.py
```

### Start PACS Backend
```bash
cd 4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend
python app.py
```

### Check Status
```bash
# MCP Server
curl http://localhost:8080/docs

# PACS Backend
curl http://localhost:5000/api/health
```

---

## 📊 OAuth Configuration

### Microsoft
```
Client ID: 60271c16-3fcb-4ba7-972b-9f075200a567
Tenant ID: fba55b68-1de1-4d10-a7cc-efa55942f829
Redirect: http://localhost:8080/auth/microsoft/callback
```

### Google
```
Client ID: 807845595525-arfmb2rtcif5b1bmpg86aji9dlv4pmau.apps.googleusercontent.com
Redirect: http://localhost:8080/auth/google/callback
```

---

## 🐛 Troubleshooting

### "Microsoft OAuth not configured"
**Fix**: MCP server is running! Just refresh the page.

### CORS Error
**Fix**: Already configured in MCP server.

### Redirect URI Mismatch
**Fix**: Already correctly configured.

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| **MCP_INTEGRATION_COMPLETE.md** | Complete summary |
| **MCP_LOGIN_INTEGRATION_GUIDE.md** | Detailed guide |
| **test_mcp_integration.html** | Interactive test |
| **QUICK_REFERENCE.md** | This file |

---

## ✅ Verification

- [x] MCP Server running
- [x] PACS Backend running
- [x] Login page accessible
- [x] Microsoft OAuth working
- [x] Google OAuth working
- [x] OAuth credentials valid
- [x] Redirect URIs correct

---

## 🎉 Summary

**Everything is ready!** Just visit http://localhost:5000/login and click an OAuth button to sign in.

**No additional configuration needed** - all OAuth credentials are already set up and working!

---

**Last Updated**: October 21, 2025
**Status**: ✅ Operational
