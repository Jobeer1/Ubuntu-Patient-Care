# 🇿🇦 South African Medical Imaging & PACS System

## **Complete Medical Imaging Platform for South African Healthcare**

An integrated PACS (Picture Archiving and Communication System) and reporting platform specifically designed for South African healthcare facilities. Built on Orthanc with enhanced workflows, multi-language support, and SA-specific medical templates.

---

## 🤖 **Model Weights & AI Components**

**Important:** The AI model weights are excluded from the repository due to size constraints.

### **Required Model Files:**
- `medical-reporting-module/models/whisper/base.pt` (138MB) - Base Whisper model for voice transcription
- `medical-reporting-module/models/whisper/cache/medium_temp.pt` (1.16GB) - Cached medium model

### **Download Links:**
🔗 **Model weights will be available for download via cloud storage**
- For hackathon judges: Use the automated setup script `bash setup_hackathon.sh`
- For full deployment: Contact the development team for access to complete model weights

### **Setup Options:**
1. **Quick Demo:** Run `bash setup_hackathon.sh` (downloads fallback models)
2. **Full Setup:** Download complete model weights and place in the paths above
3. **Gitpod Demo:** Models are downloaded automatically in the cloud environment

---

## ⚡ **Current Implementation Status**

### ✅ **Core PACS Functionality**
- **Orthanc Integration**: Full DICOM server management with start/stop/restart controls
- **Medical Device Discovery**: Automated detection and configuration of DICOM devices
- **Image Management**: DICOM image storage, retrieval, and viewing
- **Patient Sharing**: Secure, time-limited patient study sharing
- **Network Storage**: NAS integration for medical image archiving

### ✅ **South African Medical Reporting (Phase 3 Complete)**
- **Multi-Language Templates**: English, Afrikaans, isiZulu medical report templates
- **TB Screening Reports**: Specialized templates for tuberculosis screening
- **Trauma Assessment**: Emergency department reporting workflows
- **Medical Terminology**: 50+ SA medical terms with translations
- **Structured Reporting**: DICOM SR compliance with SA medical standards

### ✅ **Backend Architecture (Refactored August 2025)**
- **Modular Flask Application**: Refactored from 1359-line monolith to organized blueprints
- **Authentication System**: 2FA support with TOTP and backup codes
- **User Management**: Role-based access (Admin/Doctor/Viewer)
- **Device Management**: Medical device scanning with DICOM connectivity testing
- **API Endpoints**: RESTful API for all system functionality

### ✅ **Web Interface**
- **React Frontend**: Modern, responsive web interface with TypeScript
- **Admin Dashboard**: System monitoring, user management, device configuration
- **PACS Management**: Orthanc server control and monitoring
- **Reporting Interface**: Template-based medical reporting
- **Mobile Optimized**: Works on tablets and smartphones

---

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.7+ (tested on 3.10+)
- Node.js & npm (for frontend)
- Orthanc Server (downloadable from orthanc-server.com)

### **Installation**
```bash
# 1. Clone the repository
git clone <repository-url>
cd "Ubuntu Patient Sorg/Orthanc/orthanc-source/NASIntegration"

# 2. Install backend dependencies
python install_clean.py

# 3. Install frontend dependencies (optional)
cd frontend
npm install
cd ..

# 4. Start the system
python start_sa_system.py
```

### **Access Points**
- **Main System**: http://localhost:5000
- **Admin Dashboard**: http://localhost:5000/admin-dashboard
- **User Management**: http://localhost:5000/user-management
- **Device Management**: http://localhost:5000/device-management
- **Reporting Dashboard**: http://localhost:5000/reporting-dashboard
- **Orthanc Web Interface**: http://localhost:8042 (after setup)

### **Demo Credentials**
- **Admin**: `admin` / `admin123`
- **Doctor**: `doctor1` / `doctor123`

---

## 🏗️ **Project Structure**

```
orthanc-source/NASIntegration/
├── backend/                     # Python Flask Backend (Modular Architecture)
│   ├── app.py                  # Main application (~100 lines, refactored from 1359)
│   ├── config.py               # Configuration management
│   ├── auth_utils.py           # Authentication utilities
│   ├── routes/                 # Modular blueprint routes
│   │   ├── auth_routes.py      # Authentication endpoints
│   │   ├── admin_routes.py     # Admin dashboard & user management
│   │   ├── device_routes.py    # Medical device management
│   │   ├── nas_routes.py       # NAS storage integration
│   │   └── web_routes.py       # HTML page routes
│   ├── orthanc_simple_manager.py    # Orthanc PACS management
│   ├── device_management.py    # Medical device discovery
│   └── requirements-core.txt   # Core dependencies
├── frontend/                   # React TypeScript Frontend
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── contexts/          # Authentication & state management
│   │   └── utils/             # Utility functions
│   └── package.json
├── reporting/                  # SA Medical Reporting System
│   ├── backend/               # Reporting API endpoints
│   └── templates/             # Multi-language medical templates
├── orthanc_management/        # PACS server management
├── web_interfaces/            # Additional web tools
└── tools/                     # Utility scripts
```

## 🔧 **Key Features**

### **PACS Management**
- **One-Click Setup**: Automated Orthanc installation and configuration
- **Server Control**: Start, stop, restart Orthanc with web interface
- **Real-Time Monitoring**: Server status, storage usage, study counts
- **Device Integration**: Automatic discovery of DICOM devices on network
- **Patient Sharing**: Generate secure links for referring doctors

### **South African Medical Reporting**
- **Multi-Language Support**: Templates in English, Afrikaans, isiZulu
- **TB Screening**: Specialized tuberculosis screening templates
- **Trauma Reports**: Emergency department assessment workflows
- **Medical Terminology**: SA-specific medical term database
- **Compliance**: DICOM Structured Reporting (SR) compliance

### **Security & Authentication**
- **Two-Factor Authentication**: TOTP (Google Authenticator) and backup codes
- **Role-Based Access**: Admin, Doctor, Viewer permissions
- **Session Management**: Secure session handling with timeout
- **Audit Logging**: Complete audit trail of user activities

### **Network Integration**
- **NAS Support**: SMB/CIFS network storage integration
- **Device Discovery**: Automatic detection of medical devices
- **DICOM Connectivity**: C-ECHO verification for device testing
- **Mobile Access**: Responsive design for tablets and smartphones

## 🛠️ **Development & Testing**

### **Backend Development**
```bash
cd backend
python app.py  # Start development server
```

### **Frontend Development**
```bash
cd frontend
npm start      # Start React development server
```

### **Testing**
```bash
# Test PACS functionality
python test_orthanc_simple.py

# Test reporting system
cd reporting
python test_phase1_integration.py
```

## 📊 **System Requirements**

### **Backend**
- **Python 3.7+** with Flask framework
- **SQLite** for user and configuration storage
- **Orthanc Server** for DICOM functionality
- **Network Access** for device discovery

### **Frontend (Optional)**
- **Node.js 16+** and npm
- **React 18+** with TypeScript
- **Tailwind CSS** for styling

### **Deployment**
- **Windows/Linux/macOS** compatible
- **Docker** support available
- **HTTPS** recommended for production

## 🏥 **South African Healthcare Focus**

### **Regulatory Compliance**
- **HPCSA Integration**: Support for Health Professions Council numbers
- **POPIA Compliance**: Privacy and data protection considerations
- **Medical Terminology**: SA-specific medical terms and abbreviations

### **Language Support**
- **English**: Primary interface language
- **Afrikaans**: Medical templates and terminology
- **isiZulu**: Basic medical terminology support

### **Workflow Optimization**
- **Public Health Focus**: TB screening and trauma assessment
- **Resource Efficiency**: Designed for varied infrastructure capabilities
- **Mobile-First**: Works on basic smartphones and tablets

## 🆘 **Troubleshooting**

### **Common Issues**
```bash
# Check if all services are running
python start_sa_system.py

# Test Orthanc connectivity
curl http://localhost:8042/system

# Verify device discovery
python backend/device_management.py --scan
```

### **Support Resources**
- **Documentation**: See `QUICK_START.md` for detailed setup
- **Architecture**: See `BACKEND_REFACTORING_2025.md` for technical details
- **Progress**: See `PHASE_3_COMPLETE.md` for latest developments

## 🤖 **Model Weights & External Downloads**

### **AI Model Files**
The following AI model weights are **not included** in this repository due to size constraints:

- **Whisper Models**: `medical-reporting-module/models/whisper/*.pt`
- **Medical AI Models**: Various `.pt` and `.pth` files in model directories
- **Training Datasets**: Large dataset files (>100MB)

### **External Download Links**
📥 **Download the model weights from external storage:**

- **Google Drive**: [Coming Soon - Link will be added here]
- **OneDrive**: [Coming Soon - Link will be added here]

### **Installation Instructions**
1. Download the model weights from the links above
2. Extract to the appropriate model directories:
   ```bash
   # Example structure after download:
   medical-reporting-module/
   ├── models/
   │   ├── whisper/
   │   │   ├── base.pt
   │   │   ├── small.pt
   │   │   └── medium.pt
   ```
3. Restart the application after placing the model files

> **Note**: Users can also generate their own voice/text dictation files as needed.

## 📄 **License**
MIT License - See LICENSE file for details

---

<div align="center">
  <p><strong>🇿🇦 Built for South African Healthcare</strong></p>
  <p><em>Modern PACS and reporting platform with SA-specific workflows</em></p>
  <p><em>Backend refactored to modular architecture (August 2025)</em></p>
</div>