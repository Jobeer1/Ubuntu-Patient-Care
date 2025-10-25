# ✅ Session Persistence Fix

## 🔧 Problem

When clicking the PACS flag from MCP admin dashboard (`http://localhost:8080/admin`), users were redirected to PACS (`http://localhost:5000`) but then immediately redirected back to login, even though they were authenticated.

## 🎯 Root Cause

1. **SameSite Cookie Policy**: `SESSION_COOKIE_SAMESITE = 'Lax'` was preventing cookies from being set during cross-origin redirects (from port 8080 to port 5000)
2. **Session Not Permanent**: Session wasn't marked as permanent, so it wasn't being saved properly
3. **Session Not Modified**: Flask wasn't detecting session changes

## ✅ Solution

### 1. Updated Session Configuration (`config.py`)

Changed:
```python
SESSION_COOKIE_SAMESITE = 'Lax'  # ❌ Blocks cross-origin
```

To:
```python
SESSION_COOKIE_SAMESITE = None  # ✅ Allows cross-origin for MCP SSO
```

### 2. Updated Dashboard Route (`web_routes.py`)

Added:
```python
session.permanent = True  # Make session permanent
session.modified = True   # Force Flask to save session
logger.info(f"MCP SSO successful for {email} - Session created")
```

## 🚀 How It Works Now

### SSO Flow:

```
1. User authenticated in MCP admin (http://localhost:8080/admin)
2. Clicks PACS flag
3. MCP redirects to: http://localhost:5000/?mcp_token=JWT_TOKEN
4. PACS validates token
5. PACS creates permanent session with proper cookie settings
6. PACS redirects to clean URL: http://localhost:5000/
7. ✅ User stays logged in!
```

## ✅ What's Fixed

- ✅ Session persists across redirects
- ✅ Cookies work cross-origin (port 8080 → 5000)
- ✅ No more redirect loop
- ✅ Admin can access PACS from MCP dashboard
- ✅ Session lasts 24 hours

## 🧪 Testing

1. **Login to MCP**:
   - Visit: http://localhost:8080/login
   - Sign in with Microsoft/Google
   - You'll see the MCP admin dashboard

2. **Access PACS**:
   - Click the PACS flag in MCP admin
   - Should redirect to: http://localhost:5000
   - ✅ You're logged in to PACS!
   - ✅ No redirect to login page!

3. **Verify Session**:
   - Refresh the page
   - Navigate to different pages
   - ✅ Session persists!

## 📊 Technical Details

### Session Cookie Settings

```python
SESSION_COOKIE_SECURE = False      # Allow HTTP (for localhost)
SESSION_COOKIE_HTTPONLY = True     # Prevent JavaScript access
SESSION_COOKIE_SAMESITE = None     # Allow cross-origin
SESSION_PERMANENT_LIFETIME = 24h   # Session lasts 24 hours
```

### Session Data

```python
session['user_id'] = email
session['username'] = name
session['email'] = email
session['role'] = 'Admin' or 'user'
session['is_admin'] = True/False
session['user_type'] = 'admin' or 'user'
session['authenticated'] = True
session['oauth_provider'] = 'mcp'
session.permanent = True
session.modified = True
```

## ✅ Status

**Status**: ✅ **FIXED**

- MCP to PACS SSO: Working ✅
- Session persistence: Working ✅
- Cross-origin cookies: Working ✅
- No redirect loops: Fixed ✅

---

**Fixed**: October 21, 2025
**Issue**: Session not persisting across MCP → PACS redirect
**Solution**: Changed SameSite policy and made session permanent
