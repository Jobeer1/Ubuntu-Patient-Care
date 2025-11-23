# 📋 File Inventory & Quick Links

## 🎯 Start Here

### For First-Time Setup
👉 **READ FIRST**: `QUICK_START.md` (5-minute setup)

### For Complete Understanding
👉 **READ SECOND**: `SSO_RBAC_INTEGRATION_GUIDE.md` (complete guide)

### For Implementation Details
👉 **READ THIRD**: `MIGRATION_COMPLETE.md` (what was built)

---

## 📁 Complete File Structure

### Configuration & Setup
```
config/
├── __init__.py                    # Package init
└── settings.py                    # OAuth creds, JWT config, database URL
```

### Database Layer
```
app/
├── __init__.py                    # App package init
├── database.py                    # SQLAlchemy setup, session factory
└── models.py                      # User, Role, Permission, Audit, Medical models
```

### Authentication Routes
```
app/routes/
├── __init__.py                    # Routes package init
└── auth.py                        # OAuth endpoints (Google, Microsoft, local login)
```

### Authorization Services
```
app/services/
├── __init__.py                    # Services package init
├── rbac_service.py                # Role-based access control (5 roles)
├── jwt_service.py                 # Token generation & validation
├── user_service.py                # User CRUD, password hashing, OAuth tokens
├── access_control.py              # Patient-level access enforcement
└── audit_service.py               # Event logging & audit trails
```

### Middleware & Decorators
```
app/middleware/
├── __init__.py                    # Middleware package init
└── access_control.py              # @require_authentication, @require_patient_access
```

### Server Integration
```
server.py                          # MCP + FastAPI server (updated)
requirements.txt                   # Python dependencies (updated)
```

### Documentation
```
QUICK_START.md                     # 5-minute setup guide
SSO_RBAC_INTEGRATION_GUIDE.md      # Complete 600+ line technical guide
MIGRATION_COMPLETE.md              # Migration summary & features
IMPLEMENTATION_SUMMARY.md          # This implementation overview
FILE_INVENTORY.md                  # This file
```

---

## 📊 File Statistics

### By Type

**Configuration Files** (2)
- config/settings.py (85 lines)
- config/__init__.py (5 lines)

**Database Files** (2)
- app/database.py (58 lines)
- app/models.py (280+ lines)

**Route Files** (2)
- app/routes/auth.py (456 lines)
- app/routes/__init__.py (5 lines)

**Service Files** (5)
- app/services/rbac_service.py (220+ lines)
- app/services/jwt_service.py (65 lines)
- app/services/user_service.py (190+ lines)
- app/services/access_control.py (160+ lines)
- app/services/audit_service.py (200+ lines)
- app/services/__init__.py (10 lines)

**Middleware Files** (2)
- app/middleware/access_control.py (210+ lines)
- app/middleware/__init__.py (10 lines)

**Package Init Files** (3)
- app/__init__.py (15 lines)
- app/routes/__init__.py (5 lines)
- app/middleware/__init__.py (8 lines)

**Documentation** (4)
- QUICK_START.md (250+ lines)
- SSO_RBAC_INTEGRATION_GUIDE.md (600+ lines)
- MIGRATION_COMPLETE.md (350+ lines)
- IMPLEMENTATION_SUMMARY.md (400+ lines)

**Other** (1)
- requirements.txt (10 lines)
- server.py (updated, 630 lines)

**TOTAL**: 19 new files, 2 updated, 4 documentation files

---

## 🔑 Key File Functions

### config/settings.py
```python
# What it does:
- OAuth credential storage (Google, Microsoft)
- JWT configuration (secret, expiration, cookie settings)
- Database URL management
- CORS origins configuration
- Email configuration (optional)
- Cloud storage configuration (optional)

# How to use:
from config.settings import Settings
print(Settings.GOOGLE_CLIENT_ID)
print(Settings.JWT_SECRET_KEY)
```

### app/database.py
```python
# What it does:
- SQLAlchemy engine initialization
- Database session management
- Database initialization (create tables)
- Dependency injection for FastAPI

# How to use:
from app.database import init_db, get_db
init_db()
db = next(get_db())
```

### app/models.py
```python
# What it does:
- User model (email, role, OAuth tokens)
- Role model (permissions)
- UserPermission model (granular overrides)
- AuditLog model (event tracking)
- MedicalScheme model (scheme reference)
- PreAuthRequest model (pre-auth tracking)

# How to use:
from app.models import User, Role
user = db.query(User).filter(User.email == "user@example.com").first()
```

### app/routes/auth.py
```python
# What it does:
- Google OAuth endpoints
- Microsoft OAuth endpoints
- Local email/password login
- Logout endpoint
- Token refresh
- SSO admin controls

# Endpoints:
GET  /auth/google
GET  /auth/google/callback
GET  /auth/microsoft
GET  /auth/microsoft/callback
POST /auth/login
POST /auth/logout
GET  /auth/me
GET  /auth/token
POST /auth/admin/toggle-sso
```

### app/services/rbac_service.py
```python
# What it does:
- Defines 5 roles: Patient, Doctor, Radiologist, Technician, Admin
- Defines 16 permissions per role
- Checks user permissions
- Lists accessible modules
- Manages role initialization

# How to use:
from app.services.rbac_service import RBACService
perms = RBACService.get_user_permissions(user)
RBACService.initialize_default_roles(db)
```

### app/services/jwt_service.py
```python
# What it does:
- Creates JWT tokens with payload
- Validates JWT tokens
- Checks token expiration
- Gets token expiration time

# How to use:
from app.services.jwt_service import JWTService
token = JWTService.create_access_token({"user_id": 1, "email": "user@example.com"})
payload = JWTService.verify_token(token)
```

### app/services/user_service.py
```python
# What it does:
- User CRUD operations
- Password hashing (bcrypt)
- User authentication
- OAuth token storage
- Last login tracking

# How to use:
from app.services.user_service import UserService
UserService.hash_password("password123")
user = UserService.authenticate_user(db, "user@example.com", "password123")
```

### app/services/access_control.py
```python
# What it does:
- Patient-level access determination
- Doctor-patient assignment
- Family access (extensible)
- Study access checking

# How to use:
from app.services.access_control import AccessControlService
can_access = AccessControlService.can_access_patient(db, user, patient_id)
```

### app/services/audit_service.py
```python
# What it does:
- Logs authentication events
- Logs access events
- Logs permission changes
- Generates activity summaries

# How to use:
from app.services.audit_service import AuditService
AuditService.log_login(db, user_id, "google")
AuditService.log_access_denied(db, user_id, "patient", patient_id, "insufficient permissions")
```

### app/middleware/access_control.py
```python
# What it does:
- Request authentication decorator
- Patient access decorator
- Token extraction from headers/cookies
- Token verification

# How to use:
from app.middleware import require_authentication, require_patient_access

@require_authentication
async def protected_endpoint(request):
    pass

@require_patient_access
async def patient_data_endpoint(patient_id: str, request):
    pass
```

---

## 🚀 Usage Flows

### Developer: Setting Up Project
1. Read `QUICK_START.md` (5 min)
2. Install: `pip install -r requirements.txt`
3. Configure: Create `.env` file
4. Run: `uvicorn server:fast_app --port 8080`
5. Test: `curl http://localhost:8080/auth/sso/config`

### User: OAuth Login
1. Browser: Click "Login with Google"
2. Get redirected to Google consent
3. Grant permissions
4. Redirected to `/auth/google/callback?code=...`
5. Backend: Exchanges code for token
6. Backend: Creates user in database
7. Backend: Sets JWT cookie
8. User: Logged in!

### Connector Dev: Cross-Server Call
1. Get JWT from Medical server login
2. Use same JWT on PACS server
3. Verify token with `JWTService.verify_token()`
4. Check permissions with `RBACService.get_user_permissions()`
5. Make MCP call
6. Access is logged automatically

### Admin: Managing Users
1. Login as Admin
2. View users: `GET /auth/users` (implement)
3. Assign roles: `POST /auth/users/{id}/role`
4. View audit logs: `GET /auth/audit-logs`
5. Toggle SSO: `POST /auth/admin/toggle-sso`

---

## 🔍 Finding Code By Feature

### Need to add new role?
→ `app/services/rbac_service.py` (ROLE_PERMISSIONS dict)

### Need to add new permission?
→ `app/models.py` (Role model) + `rbac_service.py`

### Need to change token expiration?
→ `config/settings.py` (JWT_EXPIRATION_HOURS)

### Need to change OAuth flow?
→ `app/routes/auth.py` (login_google, auth_google_callback, etc.)

### Need to change database?
→ `app/database.py` (DATABASE_URL) or `config/settings.py`

### Need to add new audit event?
→ `app/services/audit_service.py` (log_* methods)

### Need to enforce new access check?
→ `app/middleware/access_control.py` (new decorator)

### Need to add new endpoint?
→ `app/routes/auth.py` (add @fast_app.get() or @fast_app.post())

---

## 📊 Dependencies

### What's in requirements.txt?
```
mcp>=0.9.0                  # MCP server framework
fastapi>=0.109.0            # Web framework
uvicorn>=0.27.0             # ASGI server
sqlalchemy>=2.0.0           # ORM
authlib>=1.3.0              # OAuth 2.0
bcrypt>=4.1.0               # Password hashing
pyjwt>=2.8.0                # JWT tokens
python-multipart>=0.0.6     # Form data parsing
pydantic>=2.0.0             # Data validation
python-dotenv>=1.0.0        # .env file loading
```

---

## 🔒 Security Checklist

Before deploying to production:

- [ ] Change `JWT_SECRET_KEY` in `.env`
- [ ] Set `JWT_COOKIE_SECURE=true` for HTTPS
- [ ] Set `DEBUG=false` in `.env`
- [ ] Configure OAuth with production URLs
- [ ] Use PostgreSQL (not SQLite)
- [ ] Set strong CORS origins
- [ ] Enable HTTPS/SSL
- [ ] Set up database backups
- [ ] Configure logging/monitoring
- [ ] Review audit logs regularly

---

## 🆘 Troubleshooting Guide

**Problem**: OAuth token expires
→ Check `app/services/jwt_service.py` (verify_token method)

**Problem**: Access denied for valid user
→ Check `app/services/rbac_service.py` (get_user_permissions)
→ Check `app/services/access_control.py` (can_access_patient)

**Problem**: Database errors
→ Check `config/settings.py` (DATABASE_URL)
→ Check `app/database.py` (init_db)

**Problem**: JWT cookie not set
→ Check `app/routes/auth.py` (JWT cookie setting)
→ Check `config/settings.py` (JWT_COOKIE_* settings)

**Problem**: OAuth redirect loop
→ Check OAuth callback URLs match
→ Check OAuth credentials in `.env`

---

## 📞 Quick Reference

### File purposes at a glance:
- **settings.py**: Configuration & secrets
- **database.py**: Database connection
- **models.py**: Database schema
- **auth.py**: OAuth endpoints
- **rbac_service.py**: Role permissions
- **jwt_service.py**: Token management
- **user_service.py**: User data
- **access_control.py**: Patient-level checks
- **audit_service.py**: Event logging
- **access_control middleware**: Request decorators

---

## 📚 Related Documentation

**In same directory**:
- `QUICK_START.md` - Get running in 5 minutes
- `SSO_RBAC_INTEGRATION_GUIDE.md` - Complete technical guide
- `MIGRATION_COMPLETE.md` - What was implemented
- `IMPLEMENTATION_SUMMARY.md` - Overview & features

**In parent directory** (PACS server):
- `4-PACS-Module/Orthanc/mcp-server/app/routes/auth.py` - Original auth.py
- `4-PACS-Module/Orthanc/mcp-server/app/services/` - Original services

---

**This file is your map. Use it to navigate the codebase.**
