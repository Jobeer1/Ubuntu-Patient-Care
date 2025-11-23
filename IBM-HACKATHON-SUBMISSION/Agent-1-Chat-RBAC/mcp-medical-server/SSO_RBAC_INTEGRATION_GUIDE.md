# SSO/RBAC Integration Guide for Medical Schemes MCP Server

## Overview

The Medical Schemes MCP Server now includes a complete **OAuth 2.0 Single Sign-On (SSO)** and **Role-Based Access Control (RBAC)** system integrated alongside the existing MCP medical tools. This enables secure authentication, authorization, and access control for medical scheme authorizations.

## Architecture

### Two-Part System

**1. MCP Server (stdio-based)**
- Handles medical pre-authorization tools
- Offline-capable with SQLite database
- Validates members, benefits, costs
- Creates pre-auth requests
- Runs on stdin/stdout for inter-server communication

**2. FastAPI Authentication Layer (HTTP-based)**
- Handles OAuth 2.0 login flows (Google, Microsoft)
- Manages JWT tokens and sessions
- Enforces role-based access control
- Audits all access events
- Runs on HTTP port (default: 8080)

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Application                       │
│                    (Web/Mobile/Desktop)                          │
└──────────────────┬──────────────────┬──────────────────────────┘
                   │                  │
         ┌─────────┴──────────┐       │
         │                    │       │
    [OAuth Login]      [Medical Tools]
         │                    │
    HTTP/REST          MCP Protocol (stdio)
         │                    │
    ┌────▼──────────────┐    │
    │   FastAPI Auth    │    │
    │   - OAuth 2.0     │    │
    │   - JWT Tokens    │    │
    │   - RBAC/Perms    │    │
    │   - Audit Logs    │    │
    └────┬──────────────┘    │
         │                   │
    [DB Auth Tables]     ┌───▼───────────────┐
    [User Roles]         │   MCP Server      │
    [Permissions]        │   - Pre-Auth      │
    [Audit Logs]         │   - Benefits      │
                         │   - Validation    │
                         └───────────────────┘
                              │
                         [Medical DB]
                         [Members Table]
                         [Benefits Table]
                         [Utilization]
```

## OAuth 2.0 Flow

### Google OAuth Flow

```
1. User clicks "Login with Google"
   ↓
2. Redirect to: GET /auth/google
   ↓
3. Google OAuth consent screen
   ↓
4. User grants permissions
   ↓
5. Google redirects to: /auth/google/callback?code=...&state=...
   ↓
6. Backend exchanges code for tokens
   ↓
7. Create/update user in database
   ↓
8. Generate JWT token
   ↓
9. Set HTTP-only cookie with JWT
   ↓
10. Redirect to dashboard
```

### Microsoft OAuth Flow

```
Same as Google but:
- Endpoint: /auth/microsoft
- Callback: /auth/microsoft/callback
- Tenant: Common tenant (or custom tenant_id)
```

### Local Authentication Flow

```
1. User enters email & password
   ↓
2. POST /auth/login with credentials
   ↓
3. Hash password and compare with stored hash
   ↓
4. If valid, generate JWT token
   ↓
5. Set HTTP-only cookie
   ↓
6. Return user info + token
```

## RBAC System

### Role Hierarchy

```
Admin (Full Access)
  ├─ All modules
  ├─ User management
  ├─ Role management
  └─ Audit logs

Radiologist (Medical Professional)
  ├─ Medical imaging modules
  ├─ Report creation
  ├─ Patient data viewing
  └─ Study sharing

Referring Doctor (Medical Professional)
  ├─ Patient management
  ├─ Imaging ordering
  ├─ Report viewing
  └─ Cloud export

Technician (Medical Support)
  ├─ Image acquisition
  ├─ Patient data entry
  ├─ Image editing
  └─ Patient records

Patient (Individual)
  ├─ Own imaging
  ├─ Own reports
  └─ Cloud export
```

### Permission Model

Each role has fine-grained permissions:

```python
{
    "Patient": {
        "can_view_images": True,
        "can_view_reports": True,
        "can_export_to_cloud": True,
        "modules": ["my-images", "my-reports"]
    },
    "Admin": {
        "can_view_images": True,
        "can_upload_images": True,
        "can_edit_images": True,
        "can_delete_images": True,
        "can_view_reports": True,
        "can_create_reports": True,
        "can_edit_reports": True,
        "can_approve_reports": True,
        "can_view_patients": True,
        "can_create_patients": True,
        "can_edit_patients": True,
        "can_manage_users": True,
        "can_manage_roles": True,
        "can_view_audit_logs": True,
        "can_export_to_cloud": True,
        "can_share_studies": True,
        "modules": ["admin", "users", "audit", "medical-schemes", ...]
    },
    # ... other roles
}
```

## File Structure

```
mcp-medical-server/
├── server.py                          # Main entry point (MCP + FastAPI setup)
├── config/
│   ├── __init__.py
│   └── settings.py                    # Configuration (OAuth creds, JWT secret, etc.)
├── app/
│   ├── __init__.py
│   ├── database.py                    # SQLAlchemy setup, session management
│   ├── models.py                      # Database models (User, Role, Permission, etc.)
│   ├── routes/
│   │   ├── __init__.py
│   │   └── auth.py                    # OAuth endpoints, login/logout, admin controls
│   ├── services/
│   │   ├── __init__.py
│   │   ├── rbac_service.py            # Role-based access control logic
│   │   ├── jwt_service.py             # Token generation & validation
│   │   ├── user_service.py            # User CRUD, password hashing
│   │   ├── access_control.py          # Patient-level access checks
│   │   └── audit_service.py           # Event logging
│   └── middleware/
│       ├── __init__.py
│       └── access_control.py          # Request decorators, auth enforcement
├── medical_schemes.db                 # SQLite database (auto-created)
└── requirements.txt                   # Dependencies
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure OAuth Credentials

Create a `.env` file:

```bash
# OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-key-min-32-characters-long
JWT_EXPIRATION_HOURS=24

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
DEBUG=false

# Database (optional, uses SQLite by default)
DATABASE_URL=sqlite:///./medical_schemes.db
```

### 3. Obtain OAuth Credentials

#### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project
3. Enable "Google+ API"
4. Create OAuth 2.0 credential (Web Application)
5. Add authorized redirect URI: `http://localhost:8080/auth/google/callback`
6. Download credentials and add to `.env`

#### Microsoft OAuth

1. Go to [Azure Portal](https://portal.azure.com/)
2. Register new application
3. Create client secret
4. Add redirect URI: `http://localhost:8080/auth/microsoft/callback`
5. Grant permissions: `User.Read`, `offline_access`
6. Add credentials to `.env`

### 4. Run FastAPI Server

```bash
# For development with auto-reload
uvicorn server:fast_app --port 8080 --reload

# For production
uvicorn server:fast_app --port 8080 --host 0.0.0.0
```

### 5. Run MCP Server (Separate Terminal)

```bash
python server.py
```

The MCP server runs on stdin/stdout for inter-server communication.

## API Endpoints

### Authentication

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/google` | GET | Start Google OAuth flow |
| `/auth/google/callback` | GET | Google OAuth callback |
| `/auth/microsoft` | GET | Start Microsoft OAuth flow |
| `/auth/microsoft/callback` | GET | Microsoft OAuth callback |
| `/auth/login` | POST | Local email/password login |
| `/auth/signup` | POST | Register new local account |
| `/auth/logout` | POST | Logout (clear JWT cookie) |
| `/auth/me` | GET | Get current user info (requires auth) |
| `/auth/token` | GET | Refresh JWT token |
| `/auth/sso/config` | GET | Get SSO status (public) |
| `/auth/admin/toggle-sso` | POST | Enable/disable SSO (admin only) |

### RBAC & Access Control

```python
# Check user permissions
GET /auth/permissions

# Get accessible modules
GET /auth/modules

# Check patient access (MCP-integrated)
POST /auth/check-access
{
    "patient_id": "patient123",
    "token": "jwt-token"
}

# View audit logs (admin only)
GET /auth/audit-logs?user_id=123&limit=100
```

## Usage Examples

### 1. OAuth Login (Web/Client)

```html
<!-- Google Login -->
<a href="http://localhost:8080/auth/google">Login with Google</a>

<!-- Microsoft Login -->
<a href="http://localhost:8080/auth/microsoft">Login with Microsoft</a>
```

### 2. Local Login (API)

```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

Response:
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "role": "Doctor"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### 3. Accessing Protected Endpoints

```bash
# Using Bearer token
curl -X GET http://localhost:8080/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."

# Or use cookie (auto-set by OAuth login)
curl -X GET http://localhost:8080/auth/me \
  -H "Cookie: access_token=eyJhbGciOiJIUzI1NiIs..."
```

### 4. MCP Integration - Verify Access Before Tool Call

```python
# Before calling an MCP tool (e.g., validate_medical_aid):
# 1. Verify user is authenticated
# 2. Check if user has required role
# 3. Check if user can access patient data
# 4. Log the access attempt

user_token = "jwt-token-from-auth"
patient_id = "patient123"

# Verify token and access
response = requests.post(
    "http://localhost:8080/auth/check-access",
    json={
        "patient_id": patient_id,
        "token": user_token
    }
)

if response.status_code == 200:
    # User has access, proceed with MCP tool
    mcp_result = call_mcp_tool("validate_medical_aid", {
        "member_number": "1234567890",
        "scheme_code": "DISCOVERY"
    })
else:
    # Access denied, log and return error
    print("Access denied")
```

## RBAC Enforcement in MCP Tools

When calling MCP tools, enforce role-based access:

```python
from app.services.rbac_service import RBACService
from app.services.access_control import AccessControlService

def call_mcp_tool_with_rbac(user, tool_name, args):
    """Call MCP tool with RBAC enforcement"""
    
    # 1. Check if user can access this tool
    permissions = RBACService.get_user_permissions(user)
    
    if tool_name == "validate_medical_aid":
        if not permissions.get("can_view_patients"):
            raise PermissionError("User cannot validate members")
    
    elif tool_name == "create_preauth_request":
        if not permissions.get("can_create_reports"):
            raise PermissionError("User cannot create pre-auth requests")
    
    # 2. Check patient-level access if needed
    if "member_number" in args and "patient_id" in args:
        patient_id = args["patient_id"]
        if not AccessControlService.can_access_patient(db, user, patient_id):
            raise PermissionError(f"User cannot access patient {patient_id}")
    
    # 3. Call MCP tool
    return call_mcp_tool(tool_name, args)
```

## Token Security

### JWT Cookie Configuration

```python
# From config/settings.py
JWT_COOKIE_SECURE=true          # HTTPS only in production
JWT_COOKIE_HTTPONLY=True        # No JS access
JWT_COOKIE_SAMESITE="Lax"       # CSRF protection
JWT_EXPIRATION_HOURS=24         # Token validity
```

### Best Practices

1. **HTTPS in Production**: Always use HTTPS
2. **Rotate Secrets**: Change JWT_SECRET_KEY periodically
3. **Token Expiration**: Shorter expiration for sensitive operations
4. **Audit Logging**: All access is logged
5. **RBAC Enforcement**: Always check permissions before actions

## Audit Logging

### Logged Events

```python
# Authentication
- User login (method: google, microsoft, local)
- User logout
- OAuth token refresh
- Failed login attempts

# Authorization
- Permission checks
- Role changes
- Access denied events

# Medical Actions
- Member validation
- Pre-auth creation
- Benefit calculations
- Report generation
```

### Access Audit Logs

```bash
# View logs for specific user (admin only)
GET /auth/audit-logs?user_id=123

# Response
[
  {
    "id": 1,
    "user_id": 123,
    "event_type": "login",
    "timestamp": "2024-01-15T10:30:00Z",
    "status": "success",
    "ip_address": "192.168.1.100"
  },
  {
    "id": 2,
    "user_id": 123,
    "event_type": "access",
    "resource_type": "patient",
    "resource_id": "patient456",
    "timestamp": "2024-01-15T10:31:00Z",
    "status": "success"
  }
]
```

## Connector Compatibility

When building MCP connectors between `mcp-medical-server` and `mcp-pacs-server`:

### Token Exchange

```python
# In connector code:
from app.services.jwt_service import JWTService

# Verify token from PACS server
token = request.headers.get("Authorization").replace("Bearer ", "")
payload = JWTService.verify_token(token)

# Extract user info for cross-server calls
user_id = payload["user_id"]
user_email = payload["email"]
user_role = payload["role"]

# Make cross-server call with same token
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(
    "http://pacs-server:8081/patient/data",
    headers=headers
)
```

### RBAC Alignment

Both servers share the same role model:
- Patient
- Referring Doctor
- Radiologist
- Technician
- Admin

This ensures consistent access control across connectors.

## Testing

### Unit Tests

```bash
python -m pytest tests/ -v
```

### Integration Tests

```bash
# Test OAuth flow
python -m pytest tests/test_oauth.py -v

# Test RBAC
python -m pytest tests/test_rbac.py -v

# Test access control
python -m pytest tests/test_access_control.py -v
```

### Manual Testing

```bash
# 1. Start FastAPI server
uvicorn server:fast_app --port 8080

# 2. Start MCP server (separate terminal)
python server.py

# 3. Test OAuth in browser
curl http://localhost:8080/auth/sso/config

# 4. Test local login
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'

# 5. Test MCP tool with token
# (See examples above)
```

## Production Deployment

### Environment Variables

```bash
# Required
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
JWT_SECRET_KEY=...  # Min 32 characters, use: openssl rand -hex 32

# Optional but recommended
DEBUG=false
JWT_COOKIE_SECURE=true
JWT_EXPIRATION_HOURS=24
SESSION_TIMEOUT_MINUTES=30
DATABASE_URL=postgresql://...  # For production database
CORS_ORIGINS=https://yourdomain.com
```

### Running with Gunicorn

```bash
# Install
pip install gunicorn

# Run
gunicorn server:fast_app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8080
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "server:fast_app", "--host", "0.0.0.0", "--port", "8080"]
```

## Troubleshooting

### OAuth Token Refresh Failed

**Issue**: Token expires and refresh fails

**Solution**:
1. Check `MICROSOFT_CLIENT_SECRET` / `GOOGLE_CLIENT_SECRET` are correct
2. Verify OAuth app settings in cloud console
3. Check database for stored refresh tokens
4. Restart server to clear in-memory cache

### RBAC Permission Denied

**Issue**: User cannot access module

**Solution**:
1. Check user role: `GET /auth/me`
2. Check role permissions in database
3. Verify patient-level access: `POST /auth/check-access`
4. View audit log for access denial reason

### MCP Tool Not Accessible

**Issue**: Tool call returns permission error

**Solution**:
1. Verify user is authenticated
2. Check user role has tool permission
3. Check patient-level access if required
4. View audit logs for details

## Next Steps

1. **Create Admin Dashboard**: UI for managing roles and permissions
2. **Implement 2FA**: Add two-factor authentication
3. **API Rate Limiting**: Protect against abuse
4. **GraphQL Layer**: Alternative to REST API
5. **Mobile SSO**: Deep linking and app-based OAuth
6. **Federated Identity**: SAML, OpenID Connect support
7. **Audit Export**: Generate compliance reports

## References

- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [JWT RFC 7519](https://tools.ietf.org/html/rfc7519)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Authlib Documentation](https://docs.authlib.org/)
