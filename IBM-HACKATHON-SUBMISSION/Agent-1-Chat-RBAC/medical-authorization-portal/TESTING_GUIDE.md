# Quick Start Guide - Medical Authorization Portal

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- pip package manager
- Virtual environment (recommended)

### Installation

```bash
# Navigate to project directory
cd "c:\Users\parkh\OneDrive\Desktop\05i_DEMO_Reinforcement\Ubuntu Patient Sorg\Ubuntu-Patient-Care\medical-authorization-portal"

# Create virtual environment (optional but recommended)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install flask python-dotenv requests

# Run the application
python app.py
```

### Access the Portal
- **URL:** http://localhost:8080
- **Login Page:** http://localhost:8080/login
- **Registration:** http://localhost:8080/register

---

## 🔐 Testing OAuth Login

### Test Case 1: Admin Login (Microsoft)
```
Email: admin@hospital.com
```
**Expected Result:** 
- Redirects to admin_dashboard.html
- Shows user management, system settings
- Full system administration controls

---

### Test Case 2: Doctor Login (Google)
```
Email: doctor@medical.com
```
**Expected Result:**
- Redirects to doctor_dashboard.html
- Shows pending pre-authorizations
- Patient management table
- Approve/Deny buttons

---

### Test Case 3: Patient Login (Google)
```
Email: patient@gmail.com
```
**Expected Result:**
- Redirects to patient_dashboard.html
- Shows personal medical information
- Benefits overview
- Authorization history

---

## 📋 Manual Testing Checklist

### Login Page
- [ ] Page loads with green and gold theme
- [ ] Microsoft button displays with 4-square logo
- [ ] Google button displays with colorful logo
- [ ] Username/password form is visible
- [ ] Responsive on mobile/tablet/desktop

### OAuth Login Flow
- [ ] Clicking "Sign in with Microsoft" redirects to Microsoft login
- [ ] Clicking "Sign in with Google" redirects to Google login
- [ ] After login, user returns to correct dashboard
- [ ] Session is properly maintained

### Admin Dashboard
- [ ] Header shows "Admin Dashboard"
- [ ] User management table displays
- [ ] System settings checkboxes work
- [ ] Stats cards show numeric values
- [ ] Logout button functions

### Patient Dashboard
- [ ] Header shows "My Medical Portal"
- [ ] Personal information displays correctly
- [ ] Benefits section shows R500,000 annual limit
- [ ] Authorization history shows 3 sample cards
- [ ] Status badges (Approved/Pending/Denied) display correctly
- [ ] Request New Authorization button is accessible

### Doctor Dashboard
- [ ] Header shows "Doctor Dashboard"
- [ ] Statistics show pending reviews (8), approvals (12), etc.
- [ ] Pre-authorization cards display with patient details
- [ ] Approve button is green
- [ ] Deny button is red
- [ ] View Details button functions
- [ ] Patient table shows at least 3 rows

### Responsive Design
- [ ] Page renders correctly on 320px (mobile)
- [ ] Page renders correctly on 768px (tablet)
- [ ] Page renders correctly on 1024px+ (desktop)
- [ ] All buttons are clickable and properly sized

---

## 🛠️ Troubleshooting

### Issue: "Port 8080 already in use"
**Solution:**
```bash
# Find process using port 8080
netstat -ano | findstr :8080

# Kill the process (Windows)
taskkill /PID <PID> /F

# Or use different port
python app.py --port 8081
```

### Issue: "ModuleNotFoundError: No module named 'flask'"
**Solution:**
```bash
pip install flask python-dotenv requests
```

### Issue: "Microsoft OAuth failing - unauthorized_client"
**Solution:**
- Verify .env file exists in project root
- Check MICROSOFT_CLIENT_ID matches Azure app registration
- Verify MICROSOFT_TENANT_ID is correct: `fba55b68-1de1-4d10-a7cc-efa55942f829`
- Ensure redirect URI matches: `http://localhost:8080/auth/microsoft/callback`

### Issue: "Google OAuth failing"
**Solution:**
- Verify GOOGLE_CLIENT_ID is correct in .env
- Check authorized redirect URI in Google Console
- Ensure cookies are enabled in browser

### Issue: "Database locked" error
**Solution:**
```bash
# Delete and recreate database
del users.db
python app.py
```

---

## 🔍 Viewing Application Logs

```bash
# Start with debug output
python app.py

# Output will show:
# [OK] MCP modules initialized successfully
# [OK] Database initialized
# [INFO] Access the portal at: http://localhost:8080
# 127.0.0.1 - - [26/Oct/2025 XX:XX:XX] "GET /login HTTP/1.1" 200
```

---

## 📊 Dashboard Summary

### Admin Dashboard Features
| Feature | Purpose |
|---------|---------|
| Stats Cards | Quick overview of system metrics |
| User Management | Add, edit, disable user accounts |
| System Settings | Configure OAuth, 2FA, maintenance mode |
| Authorization Log | Track all pre-authorizations |
| Audit Trail | View user activity history |

### Patient Dashboard Features
| Feature | Purpose |
|---------|---------|
| Medical Info | Display personal health information |
| Benefits Overview | Show insurance benefits and limits |
| Authorization History | View past/pending/denied pre-auths |
| Appeal Option | Request appeal for denied authorizations |
| New Request | Submit new pre-authorization request |

### Doctor Dashboard Features
| Feature | Purpose |
|---------|---------|
| Stats Cards | Show pending reviews and approvals |
| Pre-Auth Queue | Review pending authorization requests |
| Approve/Deny | Make authorization decisions |
| Patient List | View and manage patient list |
| Quick Actions | Fast access to common tasks |

---

## 🎨 Color Scheme

### Admin Dashboard
- **Primary:** #006533 (South African Green)
- **Accent:** #FFB81C (South African Gold)

### Patient Dashboard
- **Primary:** #006533 (Green)
- **Highlight:** #00d084 (Light Green)

### Doctor Dashboard
- **Primary:** #005580 (Medical Blue)
- **Accent:** #FFB81C (Gold)

---

## 📞 Support

For issues or questions:
1. Check application logs in terminal
2. Review error messages in browser console (F12)
3. Verify .env configuration
4. Ensure all dependencies are installed

---

## 📚 Related Documentation

- `LATEST_UPDATES.md` - Complete list of changes and fixes
- `SYSTEM_ARCHITECTURE.md` - Technical architecture and database schema
- `app.py` - Main application code with route definitions
- `templates/` - HTML templates for each dashboard

---

**Medical Authorization Portal v1.0**  
**Last Updated:** October 26, 2025  
**Status:** ✅ Ready for Use
