# 🏥 Orthanc NAS Integration

A comprehensive medical imaging system that integrates Orthanc DICOM server with Network Attached Storage (NAS) and advanced security features including configurable Two-Factor Authentication (2FA).

## ✨ Features

### 🔐 Security & Authentication
- **Configurable 2FA**: Admin can enable/disable 2FA system-wide or per user role
- **Multiple Auth Methods**: PIN + TOTP (Google Authenticator) + Backup codes
- **Single Session Enforcement**: Users can only have one active session
- **Role-Based Access Control**: Admin, User, and Viewer roles
- **Comprehensive Audit Logging**: All actions logged for compliance

### 🗄️ NAS Integration
- **SMB/CIFS Support**: Connect to Windows shares, Synology, QNAP, etc.
- **Local Storage Fallback**: For testing and development
- **File Operations**: Read, write, delete, and list files on NAS
- **Connection Management**: Automatic reconnection and error handling
- **Space Monitoring**: Real-time storage usage statistics

### 🖼️ Image Management
- **DICOM Metadata**: Complete patient and study information
- **Secure Sharing**: Time-limited, view-limited sharing links
- **Advanced Search**: Filter by patient, modality, date, etc.
- **User Associations**: Images linked to uploading users
- **Tag System**: Custom tagging for organization

### 👥 User Management
- **User Database**: SQLite-based user management
- **Profile Management**: User preferences and settings
- **Session Management**: Secure session handling
- **Statistics Dashboard**: Usage analytics and reporting

## 🚀 Quick Start

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Installation

1. **Clone or download the project**
2. **Run the installation script**:
   ```bash
   python install.py
   ```

3. **Start the application**:
   ```bash
   python start.py
   ```

4. **Open your browser** and go to: http://localhost:5000

### Demo Credentials
- **Admin**: username=`admin`, pin=`admin123`
- **User**: username=`doctor1`, pin=`doctor123`

## 📋 System Requirements

### Backend Dependencies
- Flask 2.3.3 (Web framework)
- Flask-CORS 4.0.0 (Cross-origin requests)
- pyotp 2.9.0 (TOTP authentication)
- qrcode[pil] 7.4.2 (QR code generation)
- smbprotocol 1.12.0 (SMB/CIFS support)
- Pillow 10.0.1 (Image processing)

### Frontend Dependencies (Optional)
- React 18.2.0
- Tailwind CSS 3.3.0
- React Query 3.39.0
- React Router DOM 6.3.0

## 🔧 Configuration

### Basic Configuration
Edit `backend/config_example.py` and rename to `config.py`:

```python
# 2FA Configuration
TWO_FACTOR_CONFIG = {
    'enabled': True,                    # Enable/disable 2FA system-wide
    'required_for_admin': True,         # Require 2FA for admin users
    'required_for_users': False,        # Require 2FA for regular users
    'allowed_methods': ['totp', 'backup_codes'],
    'totp_issuer': 'Orthanc NAS',
    'code_validity_seconds': 300,
    'backup_codes_count': 10,
    'max_failed_attempts': 3,
    'lockout_duration_minutes': 15
}
```

### NAS Configuration
Configure via the admin interface or API:

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

## 📡 API Endpoints

### Authentication
- `POST /api/login` - User login
- `POST /api/logout` - User logout
- `GET /api/profile` - Get user profile
- `PUT /api/profile` - Update user profile

### 2FA Management
- `GET /api/2fa/config` - Get 2FA configuration (admin)
- `POST /api/2fa/config` - Update 2FA configuration (admin)
- `POST /api/2fa/setup/totp` - Setup TOTP for user
- `POST /api/2fa/setup/totp/verify` - Verify TOTP setup
- `POST /api/2fa/verify` - Verify 2FA code
- `POST /api/2fa/backup-codes/generate` - Generate backup codes

### User Management (Admin)
- `GET /api/admin/users` - List all users
- `POST /api/admin/users` - Create new user
- `PUT /api/admin/users/<id>` - Update user
- `DELETE /api/admin/users/<id>` - Delete user

### NAS Management
- `GET /api/nas/config` - Get NAS configuration (admin)
- `POST /api/nas/config` - Update NAS configuration (admin)
- `POST /api/nas/test` - Test NAS connection
- `GET /api/nas/status` - Get NAS status
- `GET /api/nas/browse` - Browse NAS directories

### Image Management
- `GET /api/images` - Get user's images
- `GET /api/images/<id>` - Get image details
- `POST /api/images/<id>/share` - Create shared link
- `POST /api/images/<id>/tags` - Add image tag
- `GET /api/shared/<token>` - View shared image

### System
- `GET /api/health` - Health check
- `GET /api/dashboard/stats` - Dashboard statistics

## 🏗️ Architecture

```
NASIntegration/
├── backend/                    # Python Flask backend
│   ├── app.py                 # Main application
│   ├── auth_2fa.py           # 2FA authentication
│   ├── nas_connector.py      # NAS integration
│   ├── user_db.py            # User management
│   ├── image_db.py           # Image metadata
│   ├── api_endpoints.py      # REST API
│   └── requirements.txt      # Dependencies
├── frontend/                  # React frontend (optional)
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── contexts/         # React contexts
│   │   └── utils/           # Utilities
│   └── package.json         # Frontend dependencies
├── install.py               # Installation script
├── start.py                # Startup script
└── README.md               # This file
```

## 🔒 Security Features

### Two-Factor Authentication
- **TOTP Support**: Compatible with Google Authenticator, Authy, etc.
- **Backup Codes**: Emergency access codes
- **Admin Control**: Enable/disable per user role
- **Failed Attempt Protection**: Account lockout after failed attempts

### Session Security
- **Single Session**: Only one active session per user
- **Session Timeout**: Configurable session expiration
- **Secure Cookies**: HTTP-only, secure cookies
- **CSRF Protection**: Cross-site request forgery protection

### Data Protection
- **PIN Hashing**: PBKDF2 with salt
- **Secure Tokens**: Cryptographically secure random tokens
- **Audit Logging**: All actions logged with timestamps
- **Input Validation**: All inputs validated and sanitized

## 🏥 Medical Compliance

### HIPAA Considerations
- **Access Controls**: Role-based access to patient data
- **Audit Trails**: Comprehensive logging of all access
- **Secure Transmission**: HTTPS for all communications
- **Data Encryption**: Encrypted storage of sensitive data

### DICOM Integration
- **Metadata Extraction**: Full DICOM tag support
- **Patient Privacy**: Secure handling of PHI
- **Study Organization**: Hierarchical patient/study/series structure
- **Modality Support**: CT, MRI, X-Ray, Ultrasound, etc.

## 🛠️ Development

### Running in Development Mode
```bash
cd backend
python app.py
```

### Frontend Development (Optional)
```bash
cd frontend
npm install
npm start
```

### Testing
```bash
cd backend
python test_2fa.py
```

## 📊 Monitoring & Statistics

### Dashboard Metrics
- Total images and storage usage
- User activity and login statistics
- 2FA adoption and security metrics
- NAS connection status and space usage

### Health Checks
- API server status
- Database connectivity
- NAS connection status
- 2FA system status

## 🔧 Troubleshooting

### Common Issues

1. **SMB Connection Failed**
   - Install smbprotocol: `pip install smbprotocol`
   - Check network connectivity to NAS
   - Verify credentials and share permissions

2. **2FA Setup Issues**
   - Ensure system time is synchronized
   - Check QR code generation dependencies
   - Verify TOTP secret generation

3. **Database Errors**
   - Check file permissions in backend directory
   - Ensure SQLite is available
   - Verify database initialization

### Logs
- Application logs: Console output
- Access logs: `backend/logs/` (if configured)
- Error logs: Check console for stack traces

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Check the logs for error messages
4. Contact your system administrator

## 🔮 Future Enhancements

- Face recognition authentication
- Email/SMS 2FA methods
- LDAP/Active Directory integration
- Advanced DICOM viewer
- Mobile application
- Kubernetes deployment
- Advanced analytics dashboard

---

**Made with ❤️ for the medical imaging community**