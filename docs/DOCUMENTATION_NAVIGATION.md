# 📂 Project Documentation Index

All documentation has been organized into logical folders. Use this guide to find what you need.

## 🎯 Quick Navigation

### By System/Module

**👨‍⚕️ Radiological Information System (RIS)**
→ See: `1-RIS-Module/`
- Quick start guides
- Feature documentation
- Setup instructions

**💳 Medical Billing System**
→ See: `2-Medical-Billing/`
- Billing documentation
- Claims management
- Configuration guides

**🎤 Dictation & Reporting**
→ See: `3-Dictation-Reporting/`
- Voice transcription setup
- Reporting module guides
- Whisper AI configuration

**🏥 PACS (Medical Imaging)**
→ See: `4-PACS-Module/`
- Patient imaging access
- Image recognition
- DICOM handling

### By Category

**🔐 Authentication & Security**
→ See: `docs/OAUTH_*.md`, `docs/MCP_*.md`, `docs/SESSION_*.md`
- OAuth setup and integration
- MCP server configuration
- Session management
- Authentication architecture

**☁️ Cloud & Storage**
→ See: `docs/ONEDRIVE_*.md`, `docs/CLOUD_STORAGE_*.md`
- OneDrive setup
- Cloud storage configuration
- Azure integration
- Google Drive setup

**⚙️ Infrastructure & Setup**
→ See: `docs/SYSTEM_ARCHITECTURE*.md`, `docs/COMMAND_REFERENCE.md`
- System architecture
- Command reference
- Deployment guides
- Integration documentation

**🧪 Testing & Verification**
→ See: `tests/`
- Functional tests
- Integration tests
- API endpoint tests
- Verification utilities

**🔧 Scripts & Tools**
→ See: `scripts/`
- Service startup/shutdown
- System checks
- Utility scripts
- Configuration tools

**📝 Logs**
→ See: `logs/`
- Application logs
- Build logs
- System logs

**💾 Data**
→ See: `data/`
- Database files
- Configuration data
- Reference data

---

## 📚 Key Documentation Files

### Getting Started
- `1-RIS-Module/START_YOUR_COMPLETE_RIS.md` - Start the complete RIS
- `3-Dictation-Reporting/START_HERE_REPORTING_MODULE_FIX.md` - Reporting module
- `docs/RUNNING.md` - How to run the system
- `docs/START_SYSTEM_CORRECTLY.md` - System startup guide

### Setup & Installation
- `docs/COMMAND_REFERENCE.md` - All commands
- `docs/MODULE_STRUCTURE.md` - Module overview
- `docs/SYSTEM_ARCHITECTURE.md` - Architecture guide
- `docs/DOCUMENTATION_INDEX.md` - Full documentation index

### OAuth & Authentication
- `docs/OAUTH_QUICK_START.md` - Quick start
- `docs/OAUTH_SETUP_GUIDE.md` - Setup guide
- `docs/OAUTH_IMPLEMENTATION_SUMMARY.md` - Implementation details
- `docs/README_OAUTH.md` - OAuth overview

### Cloud Storage
- `docs/ONEDRIVE_SETUP_GUIDE.md` - OneDrive setup
- `docs/ONEDRIVE_COMPLETE.md` - Complete guide
- `docs/CLOUD_STORAGE_COMPLETE.md` - Cloud storage overview
- `docs/GOOGLE_DRIVE_SETUP.md` - Google Drive setup

### Medical Features
- `4-PACS-Module/PATIENT_ACCESS_QUICK_START.md` - Patient image access
- `3-Dictation-Reporting/REPORTING_MODULE_COMPLETE_SUMMARY.md` - Reporting
- `docs/README_MEDICAL_AUTH.md` - Medical authentication

---

## 🗂️ Complete Folder Structure

```
Ubuntu-Patient-Care/
├── README.md                    Main project documentation
├── LICENSE                      Project license
├── .gitignore                   Git configuration
│
├── 1-RIS-Module/                Radiological Information System
│   ├── QUICK_START_RIS.md
│   ├── START_YOUR_COMPLETE_RIS.md
│   ├── RIS_COMPLETE_FEATURES.md
│   └── ... (more RIS docs)
│
├── 2-Medical-Billing/           Medical Billing System
│   └── ... (billing docs)
│
├── 3-Dictation-Reporting/       Voice & Reporting System
│   ├── START_HERE_REPORTING_MODULE_FIX.md
│   ├── REPORTING_MODULE_COMPLETE_SUMMARY.md
│   ├── INVESTIGATION_COMPLETE_SUMMARY.md
│   └── ... (more reporting docs)
│
├── 4-PACS-Module/               Medical Imaging (PACS)
│   ├── PATIENT_ACCESS_QUICK_START.md
│   ├── PATIENT_IMAGE_ACCESS_PLAN.md
│   └── ... (more PACS docs)
│
├── docs/                        General Documentation (90+ files)
│   ├── OAUTH_*.md               OAuth/Authentication docs
│   ├── ONEDRIVE_*.md            OneDrive/Cloud storage docs
│   ├── MCP_*.md                 MCP server docs
│   ├── SYSTEM_ARCHITECTURE*.md  Architecture docs
│   ├── DOCUMENTATION_INDEX.md   Full index
│   ├── RUNNING.md               How to run
│   ├── COMMAND_REFERENCE.md     Command reference
│   └── ... (90+ more docs)
│
├── scripts/                     Executable Scripts
│   ├── START_ALL_SERVICES.bat
│   ├── start_system.bat
│   ├── setup_hackathon.sh
│   └── ... (17 scripts total)
│
├── tests/                       Test Files
│   ├── functional_test.js
│   ├── integration_test.js
│   ├── test_oauth_endpoints.py
│   └── ... (8 test files)
│
├── logs/                        Application Logs
├── data/                        Database & Data Files
└── ... (other system folders)
```

---

## 🚀 Common Tasks

### "I want to start the system"
→ Read: `docs/START_SYSTEM_CORRECTLY.md` or run: `scripts/START_ALL_SERVICES.bat`

### "I need to set up OAuth"
→ Read: `docs/OAUTH_QUICK_START.md` then `docs/OAUTH_SETUP_GUIDE.md`

### "I want to configure OneDrive"
→ Read: `docs/ONEDRIVE_SETUP_GUIDE.md`

### "I need the reporting module to work"
→ Read: `3-Dictation-Reporting/START_HERE_REPORTING_MODULE_FIX.md`

### "I want to access patient images"
→ Read: `4-PACS-Module/PATIENT_ACCESS_QUICK_START.md`

### "I need to start RIS"
→ Read: `1-RIS-Module/START_YOUR_COMPLETE_RIS.md`

### "I want to understand the architecture"
→ Read: `docs/SYSTEM_ARCHITECTURE.md` or `docs/MODULE_STRUCTURE.md`

### "I need all available commands"
→ Read: `docs/COMMAND_REFERENCE.md`

---

## 📞 Finding Specific Topics

Use the search feature or browse by category:

| Topic | Location |
|-------|----------|
| Authentication | `docs/OAUTH_*.md`, `docs/MCP_*.md` |
| Authorization | `docs/ADMIN_ROLES_QUICK_GUIDE.md` |
| Cloud Storage | `docs/ONEDRIVE_*.md`, `docs/CLOUD_STORAGE_*.md` |
| System Setup | `docs/SYSTEM_ARCHITECTURE*.md`, `docs/COMMAND_REFERENCE.md` |
| Reporting | `3-Dictation-Reporting/` |
| Medical Imaging | `4-PACS-Module/` |
| Information System | `1-RIS-Module/` |
| Billing | `2-Medical-Billing/` |
| Testing | `tests/` |
| Scripts | `scripts/` |

---

## ✅ Notes

- **Root folder is clean**: Only README.md, LICENSE, .gitignore, and .gitpod.yml
- **Modular organization**: Each module has its own folder
- **Centralized infrastructure docs**: General setup in `docs/`
- **Easy maintenance**: Structure is scalable and professional
- **Proper categorization**: Files grouped by function and purpose

---

**Last Updated**: October 25, 2025
**Status**: ✅ Complete and Organized

For full documentation details, see: `docs/FOLDER_STRUCTURE_SUMMARY.md`

