# Frontend Upgrade Guide - Medical Authorization Portal

## Overview
The frontend has been completely redesigned with:
- ✅ Google and Microsoft OAuth integration
- ✅ Orthanc-inspired Tailwind design (Blue gradient #1e3c72 → #2a5298)
- ✅ Modern, professional healthcare UI
- ✅ Port changed to 8080
- ✅ Responsive mobile-first design
- ✅ Professional forms, tables, and components

---

## What's New

### 1. Port Change
**OLD**: `http://localhost:5000`  
**NEW**: `http://localhost:8080`

The Flask app now runs on port 8080 for better compatibility with other services.

### 2. OAuth Authentication

#### Google Login
- **Location**: Login page - "Google" button
- **Flow**: Click → redirects to Google → sign in → returns to dashboard
- **Setup Required**:
  ```
  1. Go to https://console.cloud.google.com/
  2. Create new project
  3. Create OAuth 2.0 credentials (Web application)
  4. Add redirect URI: http://localhost:8080/auth/google/callback
  5. Copy Client ID and Client Secret
  6. Add to .env file
  ```

#### Microsoft Login
- **Location**: Login page - "Microsoft" button  
- **Flow**: Click → redirects to Microsoft → sign in → returns to dashboard
- **Setup Required**:
  ```
  1. Go to https://portal.azure.com/
  2. Register new application
  3. Create OAuth 2.0 credentials
  4. Add redirect URI: http://localhost:8080/auth/microsoft/callback
  5. Copy Client ID and Client Secret
  6. Add to .env file
  ```

### 3. Design System

#### Colors (Tailwind-based)
- **Primary**: Blue (#1e3c72, #2a5298, #2563eb)
- **Secondary**: Slate (#0f172a, #1e293b, #334155)
- **Success**: Green (#16a34a)
- **Warning**: Orange (#ea580c)
- **Danger**: Red (#dc2626)

#### Typography
- **Font**: Inter (modern, clean, professional)
- **Sizes**: 12px-18px (mobile-optimized)
- **Weights**: 300, 400, 500, 600, 700

#### Components
- Cards: White background, subtle shadows
- Buttons: Gradient buttons with hover effects
- Forms: Clean input fields with focus states
- Tables: Modern table design with hover states
- Alerts: Color-coded success/warning/error/info
- Badges: Small status indicators

### 4. Login Page Features

```
[Logo]
Medical Portal
Secure Healthcare Authorization System

[Google Button] [Microsoft Button]
          OR continue with email

[Email/Username Input]
[Password Input with Toggle]
[Sign In Button]

Don't have an account? Create one here

[Security Notice Box]
```

### 5. Email/Password Fallback

Users can still login with traditional credentials:
1. Username field
2. Password field (with show/hide toggle)
3. Sign In button
4. Create account link

---

## Configuration Steps

### Step 1: Install Dependencies
```bash
cd medical-authorization-portal
pip install -r requirements.txt
```

### Step 2: Set Up OAuth Credentials

#### For Google:
```bash
1. Visit: https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID
3. Application type: Web application
4. Authorized redirect URIs: http://localhost:8080/auth/google/callback
5. Note: Client ID and Client Secret
```

#### For Microsoft:
```bash
1. Visit: https://portal.azure.com/
2. Go to Azure Active Directory → App registrations
3. New registration
4. Name: Medical Portal
5. Supported account types: Accounts in any organizational directory
6. Redirect URI: Web - http://localhost:8080/auth/microsoft/callback
7. Note: Application (client) ID and Client Secret
```

### Step 3: Create .env File
```bash
cp .env.example .env
```

Edit `.env`:
```
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
FLASK_ENV=development
SECRET_KEY=medical-portal-secret-key-2025
```

### Step 4: Run the Application
```bash
python app.py
```

Expected output:
```
[SYSTEM] MEDICAL AUTHORIZATION PORTAL
============================================================
[OK] Starting Flask application...
[OK] Database initialized
[OK] MCP modules loaded

[INFO] Access the portal at: http://localhost:8080
```

### Step 5: Access the Application
```
http://localhost:8080
```

---

## OAuth User Flow

### Google OAuth
1. User clicks "Google" button on login page
2. Browser redirects to Google OAuth consent screen
3. User signs in with Google account
4. Google redirects back to `/auth/google/callback` with auth code
5. Backend exchanges code for access token
6. Backend fetches user info (email, name)
7. Backend creates/updates user in database
8. User logged in and redirected to dashboard

### Microsoft OAuth
1. User clicks "Microsoft" button on login page
2. Browser redirects to Microsoft sign-in page
3. User signs in with Microsoft account
4. Microsoft redirects back to `/auth/microsoft/callback` with auth code
5. Backend exchanges code for access token
6. Backend fetches user info from Microsoft Graph API
7. Backend creates/updates user in database
8. User logged in and redirected to dashboard

### Traditional Login
1. User enters username/email and password
2. Backend hashes password and checks database
3. If valid, creates session and redirects to dashboard
4. If invalid, shows error message

---

## File Structure

```
medical-authorization-portal/
├── app.py                          # Main Flask app with OAuth routes
├── requirements.txt                # Python dependencies (updated)
├── .env.example                    # Environment configuration template
│
├── templates/
│   ├── login.html                  # NEW: Modern login with OAuth
│   ├── register.html               # Registration page (to be updated)
│   ├── dashboard.html              # Dashboard (to be updated)
│   ├── chat.html                   # Chat interface (to be updated)
│   ├── patients.html               # Patient search (to be updated)
│   ├── authorizations.html         # Authorizations (to be updated)
│   ├── base.html                   # Base template
│   ├── 404.html                    # 404 error page
│   └── 500.html                    # 500 error page
│
├── static/
│   └── css/
│       └── style.css               # NEW: Tailwind-inspired modern CSS
│
├── users.db                        # SQLite database (auto-created)
└── flask_session/                  # Flask session storage
```

---

## OAuth Route Reference

```
GET  /auth/google              → Start Google OAuth flow
GET  /auth/google/callback     → Google OAuth callback
GET  /auth/microsoft           → Start Microsoft OAuth flow
GET  /auth/microsoft/callback  → Microsoft OAuth callback
POST /login                    → Email/password login
GET  /login                    → Login page
POST /register                 → Create account
GET  /register                 → Registration page
POST /logout                   → Logout (set empty session)
GET  /dashboard                → Main dashboard (requires auth)
```

---

## Backend OAuth Implementation

### OAuth Helper Function
```python
def create_user_from_oauth(email, name, oauth_provider, oauth_id):
    """Create or get user from OAuth provider"""
    # Check if user exists by email
    # If yes, return existing user
    # If no, create new user with random password
    # Auto-assign role as 'clinician'
```

### Google Route Handler
```python
@app.route('/auth/google')
def google_login():
    # Redirect to Google OAuth consent screen
    
@app.route('/auth/google/callback')
def google_callback():
    # Exchange auth code for token
    # Fetch user info
    # Create/get user
    # Set session
    # Redirect to dashboard
```

### Microsoft Route Handler
```python
@app.route('/auth/microsoft')
def microsoft_login():
    # Redirect to Microsoft sign-in page
    
@app.route('/auth/microsoft/callback')
def microsoft_callback():
    # Exchange auth code for token
    # Fetch user info from Microsoft Graph
    # Create/get user
    # Set session
    # Redirect to dashboard
```

---

## Design Specifications

### Color Palette
```css
Primary Colors (Blue):
- #1e3c72 (Orthanc Dark)
- #2a5298 (Orthanc Light)
- #2563eb (Bright Blue)

Secondary Colors (Slate):
- #0f172a (Slate 900)
- #1e293b (Slate 800)
- #334155 (Slate 700)

Status Colors:
- Green #16a34a (Success)
- Orange #ea580c (Warning)
- Red #dc2626 (Error)
```

### Typography
```
Font Family: Inter
- Headings: 700 (bold)
- Buttons: 600 (semibold)
- Body: 400 (regular)
- Small: 300 (light)

Sizes:
- H1: 28px
- H2: 24px
- Button: 14px
- Input: 14px
- Small: 12px
```

### Spacing
```
8px base unit
- Padding: 10px, 16px, 20px, 24px
- Margins: 10px, 16px, 20px, 24px
- Gaps: 8px, 12px, 16px, 20px, 24px
```

### Shadows
```
sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05)
md: 0 4px 6px -1px rgba(0, 0, 0, 0.1)
lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1)
xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1)
```

### Border Radius
```
6px: Default for inputs, buttons
8px: Cards, modals
12px: Large components
```

---

## Troubleshooting

### OAuth Not Working
**Problem**: "Redirect URI mismatch"  
**Solution**: 
1. Check .env file has correct Client ID and Secret
2. Verify redirect URI in OAuth provider settings matches exactly
3. Make sure app is running on port 8080

### Database Error
**Problem**: "No such table: users"  
**Solution**: Database auto-creates on first run. If still missing, delete `users.db` and restart app.

### Session Not Persisting
**Problem**: Logged in but redirected to login on refresh  
**Solution**: Check Flask SECRET_KEY in app.py is set correctly.

### CSS Not Loading
**Problem**: Page looks unstyled  
**Solution**: 
1. Check `/static/css/style.css` exists
2. Clear browser cache (Ctrl+Shift+Del)
3. Check browser console for 404 errors

---

## Next Steps

### Recommended Updates
1. Update remaining HTML templates with new Tailwind design
2. Add password reset via OAuth email
3. Add two-factor authentication
4. Add social profile linking (link multiple OAuth providers to one account)
5. Add profile page showing OAuth provider used

### Production Deployment
1. Set `FLASK_ENV=production`
2. Set `DEBUG=False`
3. Set `SESSION_COOKIE_SECURE=True`
4. Use HTTPS (required for OAuth)
5. Use Gunicorn/Waitress instead of Flask dev server
6. Store credentials in secure environment variables

---

## Support & Questions

For OAuth setup help:
- Google: https://developers.google.com/identity/protocols/oauth2
- Microsoft: https://docs.microsoft.com/en-us/azure/active-directory/develop/

For Flask help:
- Flask Docs: https://flask.palletsprojects.com/
- Flask-SQLAlchemy: https://flask-sqlalchemy.palletsprojects.com/

---

**Last Updated**: October 26, 2025  
**Version**: 2.0 (OAuth & Modern Design)
