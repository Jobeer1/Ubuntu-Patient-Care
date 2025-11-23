# Quick Start - Medical Authorization Portal v2.0

## What's Changed
✅ **Port**: Now runs on **8080** (was 5000)  
✅ **Login**: Google & Microsoft OAuth buttons added  
✅ **Design**: Modern Tailwind-inspired UI (matches Orthanc)  
✅ **Frontend**: Professional healthcare aesthetic  

---

## 3-Minute Setup

### 1. Install packages
```bash
pip install -r requirements.txt
```

### 2. Create .env file
```bash
copy .env.example .env
# Edit .env and add your OAuth credentials (optional for testing)
```

### 3. Run the app
```bash
python app.py
```

### 4. Open browser
```
http://localhost:8080
```

---

## Login Methods

### Option A: OAuth (Recommended)
Click **"Google"** or **"Microsoft"** button to sign in with your account.

### Option B: Email/Password  
Create account via "Register" → login with username/email and password.

---

## Getting OAuth Credentials

### Google OAuth
1. Go to https://console.cloud.google.com/
2. Create project → Credentials → OAuth 2.0 Client ID
3. Add redirect: `http://localhost:8080/auth/google/callback`
4. Copy credentials to `.env`

### Microsoft OAuth
1. Go to https://portal.azure.com/
2. Azure AD → App registrations → New
3. Add redirect: `http://localhost:8080/auth/microsoft/callback`
4. Create client secret
5. Copy credentials to `.env`

---

## Files Changed

| File | Change |
|------|--------|
| `app.py` | Added OAuth routes, changed port to 8080 |
| `templates/login.html` | Rebuilt with Google/Microsoft buttons |
| `static/css/style.css` | Modern Tailwind-inspired design |
| `requirements.txt` | Added authlib, requests, python-dotenv |
| `.env.example` | New environment config template |

---

## Environment Variables
```
GOOGLE_CLIENT_ID=your-id
GOOGLE_CLIENT_SECRET=your-secret
MICROSOFT_CLIENT_ID=your-id
MICROSOFT_CLIENT_SECRET=your-secret
```

---

## Color Scheme
- **Primary**: Blue #1e3c72 → #2a5298 (Orthanc)
- **Secondary**: Slate #0f172a → #475569
- **Accents**: Success (Green), Warning (Orange), Error (Red)

---

## Help

### App won't start?
- Check Python 3.8+: `python --version`
- Check port 8080 is free
- Check all dependencies installed

### OAuth not working?
- Verify .env file has credentials
- Check redirect URI matches exactly
- Clear browser cache

### Database error?
- Delete `users.db` and restart app
- Database auto-creates on first run

---

See `FRONTEND_UPGRADE_GUIDE.md` for detailed documentation.
