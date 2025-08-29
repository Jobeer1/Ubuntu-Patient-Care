<div align="center">
  <img src="https://www.orthanc-server.com/static/img/logo.png" width="120" alt="Orthanc Logo" />
  <h1>🏥 Orthanc NAS Integration</h1>
  <p><b>Brutally Honest Medical Imaging Platform</b></p>
  <p>Integrates <a href="https://www.orthanc-server.com/">Orthanc DICOM server</a> with Network Attached Storage (NAS), security, and user management. <br> <b>This project is actively developed, but not everything is perfect.</b></p>
  <p><i>🔧 Recently refactored backend to modular architecture (January 2025)</i></p>
</div>

---

## ⚡ What Actually Works (and What Doesn't)

- **Backend:** 🆕 **Modular Flask app** (refactored from 1359 lines to ~100 lines main app), SQLite DB, NAS (SMB/CIFS) integration, DICOM image management, 2FA (TOTP, backup codes), user roles (admin/user/viewer), REST API.
- **Frontend:** React SPA, login, 2FA setup/verify, dashboard, image browser, admin/user dashboards, live stats. UI is modern but not bug-free.
- **Security:** 2FA is enforced for admins, PINs are hashed, sessions are single-user, but you MUST change demo credentials and use HTTPS in production.
- **NAS:** Works with SMB/CIFS, but NFS is experimental. Network issues and permissions WILL cause headaches.
- **DICOM:** Metadata extraction, image sharing, tagging. Viewer is basic; advanced features are planned, not present.
- **Testing:** Some backend tests exist, but coverage is spotty. No automated CI/CD.
- **Documentation:** This README is now honest. Some code comments are outdated.
- **🔧 Architecture:** Now uses blueprint-based modular structure for better maintainability and development experience.

---

## 🚀 Quick Start (If You Just Want to Try It)
*Updated for the new modular backend architecture*

### Prerequisites
- Python 3.7+ (tested on 3.10)
- pip (Python package manager)
- Node.js & npm (for frontend, optional)

### Installation
1. **Clone or download the project**
2. **Install backend dependencies**
   ```bash
   python install.py
   ```
3. **Configure backend** (now using centralized config system)
   - Copy `backend/config_example.py` to `backend/config.py` and edit for your needs
   - For NAS, update `nas_config.json` or use the admin web interface
4. **Start backend server** (now using refactored modular app)
   ```bash
   python start_api_server.py
   ```
5. **(Optional) Start frontend**
   ```bash
   cd frontend
   npm install
   npm start
   ```
6. **Open your browser:** [http://localhost:5000](http://localhost:5000)

#### Demo Credentials (Change These!)
- **Admin:** `admin` / `admin123`
- **User:** `doctor1` / `doctor123`

### 🔧 New Modular Architecture Benefits
- **Easier maintenance**: Routes organized by functionality
- **Better debugging**: Issues isolated to specific modules
- **Improved development**: Clear separation of concerns
- **Future-ready**: Easier to add new features and tests

---

## 🛠️ System Requirements

**Backend:**
- Python 3.7+
- Flask, Flask-CORS, pyotp, qrcode[pil], smbprotocol, Pillow

**Frontend (Optional):**
- React, Tailwind CSS, React Query, React Router DOM

---

## 🔧 Configuration

### Backend
1. Copy `backend/config_example.py` to `backend/config.py`
2. Edit settings for 2FA, session, and security
   ```python
   TWO_FACTOR_CONFIG = {
       'enabled': True,
       'required_for_admin': True,
       'required_for_users': False,
       'allowed_methods': ['totp', 'backup_codes'],
       'totp_issuer': 'Orthanc NAS',
       'code_validity_seconds': 300,
       'backup_codes_count': 10,
       'max_failed_attempts': 3,
       'lockout_duration_minutes': 15
   }
   ```

### NAS
- Configure via admin web interface or edit `nas_config.json`:
  ```json
  {
    "enabled": true,
    "type": "smb",
    "host": "192.168.1.100",
    "port": 445,
    "share": "medical_images",
    "username": "nas_user",
    "password": "nas_password",
    "path": "/dicom"
  }
  ```

### Environment Variables (Production Only)
- Store secrets (passwords, keys) in `.env` files or environment variables
- Never commit sensitive data to source control

---

## 📡 API Overview (What You Can Actually Use)

**Authentication:**
- `POST /api/login` — Login
- `POST /api/logout` — Logout
- `GET /api/profile` — Get profile
- `PUT /api/profile` — Update profile

**2FA:**
- `GET /api/2fa/config` — Get config
- `POST /api/2fa/config` — Update config
- `POST /api/2fa/setup/totp` — Setup TOTP
- `POST /api/2fa/verify` — Verify code
- `POST /api/2fa/backup-codes/generate` — Backup codes

**User Management (Admin):**
- `GET /api/admin/users` — List users
- `POST /api/admin/users` — Create user
- `PUT /api/admin/users/<id>` — Update user
- `DELETE /api/admin/users/<id>` — Delete user

**NAS:**
- `GET /api/nas/config` — Get config
- `POST /api/nas/config` — Update config
- `POST /api/nas/test` — Test connection
- `GET /api/nas/status` — Status
- `GET /api/nas/browse` — Browse

**Images:**
- `GET /api/images` — List images
- `GET /api/images/<id>` — Details
- `POST /api/images/<id>/share` — Share
- `POST /api/images/<id>/tags` — Tag
- `GET /api/shared/<token>` — View shared

**System:**
- `GET /api/health` — Health check
- `GET /api/dashboard/stats` — Stats

---

## 🏗️ Project Structure (Backend & Frontend)
*Updated to reflect the new modular backend architecture*

```text
NASIntegration/
├── backend/         # Python Flask backend (Refactored January 2025)
│   ├── app.py       # Main app (~100 lines, down from 1359)
│   ├── config.py    # Centralized configuration
│   ├── auth_utils.py # Shared authentication utilities
│   ├── routes/      # Modular route blueprints
│   │   ├── __init__.py
│   │   ├── auth_routes.py     # Authentication endpoints
│   │   ├── admin_routes.py    # Admin dashboard
│   │   ├── device_routes.py   # Medical device management
│   │   ├── nas_routes.py      # NAS integration
│   │   └── web_routes.py      # Web interface routes
│   ├── api_endpoints.py, auth_2fa.py, nas_connector.py, user_db.py, image_db.py, ... # Legacy modules
│   └── requirements.txt
├── frontend/        # React frontend (optional)
│   ├── src/         # App.js, components, contexts, utils
│   └── package.json
├── install.py       # Install script
├── start_api_server.py # Start backend
├── BACKEND_REFACTORING_2025.md # Technical documentation for refactoring
└── README.md
```

### 🔧 Architecture Benefits (Post-Refactoring)
- **Maintainability**: 87% reduction in main app complexity
- **Modularity**: Clear separation of concerns by functionality
- **Debugging**: Issues isolated to specific blueprint modules
- **Development**: Easier to onboard new developers
- **Testing**: Each module can be tested independently
- **Scalability**: Easy to add new feature modules

---

## 🔒 Security (The Good, The Bad, The Ugly)

- **2FA (TOTP, backup codes):** Works for admins, optional for users. If you skip 2FA, you’re asking for trouble.
- **PIN hashing:** PBKDF2 + salt. Decent, but not perfect.
- **Sessions:** Single session per user. Not immune to session hijacking if you don’t use HTTPS.
- **Audit logging:** Most actions tracked, but log rotation is DIY.
- **Input validation:** Present, but not bulletproof. Don’t trust user input blindly.
- **CSRF protection:** Implemented, but test it yourself.

---

## 🏥 Medical Compliance & DICOM

- **HIPAA-oriented:** Role-based access, audit trails, encrypted storage. But YOU must deploy with HTTPS and secure your NAS.
- **DICOM support:** Metadata extraction, privacy, multi-modality. Viewer is basic; don’t expect miracles.

---

## 🛠️ Development & Testing
*Updated for the new modular backend architecture*

**Backend (Modular):**
```bash
cd backend
python app.py  # Uses new modular structure
```

**Testing individual modules:**
```bash
# Test specific blueprint modules
python -c "from routes.auth_routes import auth_bp; print('Auth module working')"
python -c "from routes.admin_routes import admin_bp; print('Admin module working')"
python -c "from config import DevelopmentConfig; print('Config system working')"
```

**Frontend (optional):**
```bash
cd frontend
npm install
npm start
```

**Testing:**
```bash
cd backend
python test_2fa.py
```
*Test coverage is incomplete. The modular structure makes it easier to add unit tests for individual components. Manual testing is recommended before production.*

---

## 📊 Monitoring & Health

- **Dashboard:** Images, storage, user activity, 2FA stats
- **Health checks:** API, database, NAS, 2FA

---

## 🆘 Troubleshooting (What Will Go Wrong)

**NAS Issues:**
- Install `smbprotocol` (`pip install smbprotocol`)
- Network, credentials, permissions WILL cause problems. Debug with logs.

**2FA Problems:**
- Sync system time. QR code issues? Check dependencies.

**Database Errors:**
- File permissions, SQLite availability, DB initialization. Don’t run as root.

**Logs:**
- Console output. For production, set up log files and rotation yourself.

---

## 🤝 Contributing

1. Fork this repo
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## 📄 License

MIT License — see LICENSE file

---

## 🆘 Support

1. See troubleshooting above
2. Review API docs
3. Check logs for errors
4. Contact your system administrator

---

## 🔮 Roadmap & Future (No Promises)

- Face recognition authentication (experimental)
- Email/SMS 2FA (planned)
- LDAP/AD integration (planned)
- Advanced DICOM viewer (planned)
- Mobile app (maybe)
- Kubernetes deployment (maybe)
- Analytics dashboard (planned)

---

<div align="center">
  <b>Made with ❤️, but not magic. Expect bugs. Open issues if you find them.</b>
  <br>
  <i>🔧 Backend refactored to modular architecture (January 2025) - See BACKEND_REFACTORING_2025.md for technical details</i>
</div>

1. **Clone or download the project**
2. **Install dependencies**
   ```bash
   python install.py
   ```
3. **Configure the backend**
   - Copy `backend/config_example.py` to `backend/config.py` and edit as needed
   - For NAS, update `nas_config.json` or use the admin web interface
4. **Start the backend server**
   ```bash
   python start_api_server.py
   ```
5. **(Optional) Start the frontend**
   ```bash
   cd frontend
   npm install
   npm start
   ```
6. **Access the app:** [http://localhost:5000](http://localhost:5000)

#### Demo Credentials (Change for Production!)
- **Admin:** `admin` / `admin123`
- **User:** `doctor1` / `doctor123`


---

## �️ System Requirements

**Backend:**
- Python 3.7+
- Flask, Flask-CORS, pyotp, qrcode[pil], smbprotocol, Pillow

**Frontend (Optional):**
- React, Tailwind CSS, React Query, React Router DOM


---

## 🔧 Configuration

### Backend
1. Copy `backend/config_example.py` to `backend/config.py`
2. Edit settings for 2FA, session, and security
    ```python
    TWO_FACTOR_CONFIG = {
          'enabled': True,
          'required_for_admin': True,
          'required_for_users': False,
          'allowed_methods': ['totp', 'backup_codes'],
          'totp_issuer': 'Orthanc NAS',
          'code_validity_seconds': 300,
          'backup_codes_count': 10,
          'max_failed_attempts': 3,
          'lockout_duration_minutes': 15
    }
    ```

### NAS
- Configure via admin web interface or edit `nas_config.json`:
   ```json
   {
      "enabled": true,
      "type": "smb",
      "host": "192.168.1.100",
      "port": 445,
      "share": "medical_images",
      "username": "nas_user",
      "password": "nas_password",
      "path": "/dicom"
   }
   ```

### Environment Variables (Recommended for Production)
- Store secrets (passwords, keys) in `.env` files or environment variables
- Never commit sensitive data to source control


---

## 📡 API Overview

**Authentication:**
- `POST /api/login` — Login
- `POST /api/logout` — Logout
- `GET /api/profile` — Get profile
- `PUT /api/profile` — Update profile

**2FA:**
- `GET /api/2fa/config` — Get config
- `POST /api/2fa/config` — Update config
- `POST /api/2fa/setup/totp` — Setup TOTP
- `POST /api/2fa/verify` — Verify code
- `POST /api/2fa/backup-codes/generate` — Backup codes

**User Management (Admin):**
- `GET /api/admin/users` — List users
- `POST /api/admin/users` — Create user
- `PUT /api/admin/users/<id>` — Update user
- `DELETE /api/admin/users/<id>` — Delete user

**NAS:**
- `GET /api/nas/config` — Get config
- `POST /api/nas/config` — Update config
- `POST /api/nas/test` — Test connection
- `GET /api/nas/status` — Status
- `GET /api/nas/browse` — Browse

**Images:**
- `GET /api/images` — List images
- `GET /api/images/<id>` — Details
- `POST /api/images/<id>/share` — Share
- `POST /api/images/<id>/tags` — Tag
- `GET /api/shared/<token>` — View shared

**System:**
- `GET /api/health` — Health check
- `GET /api/dashboard/stats` — Stats


---

## 🏗️ Project Structure

```text
NASIntegration/
├── backend/         # Python Flask backend
│   ├── app.py       # Main app
│   ├── ...          # Auth, NAS, user, image, API modules
│   └── requirements.txt
├── frontend/        # React frontend (optional)
│   └── ...
├── install.py       # Install script
├── start_api_server.py # Start backend
└── README.md
```


---

## 🔒 Security Highlights

- **2FA (TOTP, backup codes)** — Google Authenticator, Authy, etc.
- **Role-based access** — Admin, User, Viewer
- **Single session per user** — Prevents account sharing
- **Session timeout & secure cookies**
- **PIN hashing (PBKDF2 + salt)**
- **Audit logging** — All actions tracked
- **Input validation & CSRF protection**


---

## 🏥 Medical Compliance & DICOM

- **HIPAA-oriented:** Role-based access, audit trails, encrypted storage
- **Secure transmission:** Use HTTPS in production
- **DICOM support:** Full tag extraction, privacy, multi-modality


---

## 🛠️ Development & Testing

**Backend:**
```bash
cd backend
python app.py
```

**Frontend (optional):**
```bash
cd frontend
npm install
npm start
```

**Testing:**
```bash
cd backend
python test_2fa.py
```


---

## 📊 Monitoring & Health

- **Dashboard:** Images, storage, user activity, 2FA stats
- **Health checks:** API, database, NAS, 2FA


---

## 🆘 Troubleshooting

**SMB/NAS Issues:**
- Install `smbprotocol` (`pip install smbprotocol`)
- Check network, credentials, permissions

**2FA Problems:**
- Sync system time
- Check QR code dependencies

**Database Errors:**
- Check file permissions
- Ensure SQLite is available

**Logs:**
- Console output
- (Optional) `backend/logs/` for access/error logs


---

## 🤝 Contributing

1. Fork this repo
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request


---

## 📄 License

MIT License — see LICENSE file


---

## 🆘 Support

1. See troubleshooting above
2. Review API docs
3. Check logs for errors
4. Contact your system administrator


---

## 🔮 Roadmap & Future

- Face recognition authentication
- Email/SMS 2FA
- LDAP/AD integration
- Advanced DICOM viewer
- Mobile app
- Kubernetes deployment
- Analytics dashboard

---

<div align="center">
   <b>Made with ❤️ for the medical imaging community</b>
</div>