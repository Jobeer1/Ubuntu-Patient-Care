# SA Features Mapping - Developer B Analysis

**Status**: 🔄 IN PROGRESS  
**Developer**: B  
**Date**: January 13, 2025  
**Purpose**: Document all SA-specific features found in existing system for Orthanc plugin integration

---

## 📋 Existing SA Features Analysis

### 🔐 Authentication & Security Features
**Location**: `backend/auth_2fa.py`, `backend/auth_api.py`, `backend/admin_api.py`

#### Current Implementation:
- ✅ **2FA System**: TOTP + backup codes with configurable policies
- ✅ **Role-based Access**: Admin, User, Viewer roles
- ✅ **Session Management**: Single session per user enforcement
- ✅ **PIN Authentication**: PBKDF2 hashed PINs
- ✅ **Audit Logging**: All authentication events tracked

#### Migration to Orthanc:
- 🔄 **Requires**: Authentication plugin from Developer A
- 🔄 **Integration Point**: REST API bridge for session validation
- 🔄 **Database**: User tables to be extended in Orthanc DB

### 🏥 SA Healthcare-Specific Features
**Location**: `backend/south_african_*.py` files

#### Current Implementation:
- ✅ **HPCSA Integration**: Healthcare professional validation
- ✅ **Medical Aid Support**: Discovery, Momentum, other SA schemes
- ✅ **Multi-language**: English, Afrikaans, isiZulu support
- ✅ **SA Medical Templates**: TB, HIV, trauma reporting templates
- ✅ **Voice Dictation**: Optimized for SA accents

#### Migration to Orthanc:
- 🔄 **Requires**: SA compliance plugin from Developer A
- 🔄 **Frontend**: React components for SA healthcare workflows
- 🔄 **API Extensions**: SA-specific REST endpoints

### 💾 Storage & NAS Features
**Location**: `backend/nas_connector.py`, `backend/image_db.py`

#### Current Implementation:
- ✅ **NAS Integration**: SMB/CIFS support for local storage
- ✅ **Offline-first**: Local storage with cloud sync
- ✅ **Load shedding resilience**: Offline operation capability
- ✅ **Image Management**: DICOM metadata + tagging + sharing

#### Migration to Orthanc:
- 🔄 **Plugin**: Custom storage plugin for NAS integration
- 🔄 **Sync**: Background sync jobs for cloud backup
- 🔄 **Metadata**: Extended DICOM metadata for SA features

### 📊 Reporting & Analytics
**Location**: `backend/reporting_*.py`, `backend/sa_templates_api.py`

#### Current Implementation:
- ✅ **Template System**: SA medical report templates
- ✅ **Voice-to-Text**: Dictation with SA accent support
- ✅ **PDF Export**: Professional report generation
- ✅ **DICOM SR**: Structured reporting support
- ✅ **Analytics Dashboard**: Usage statistics and compliance metrics

#### Migration to Orthanc:
- 🔄 **Plugin**: Reporting plugin with SA templates
- 🔄 **UI**: React reporting interface
- 🔄 **Storage**: Report storage in Orthanc database

---

## 🌐 Frontend Features Analysis

### 📱 React Components (Current)
**Location**: `frontend/src/components/`

#### Existing Components:
- ✅ **Authentication**: Login, 2FA setup/verify, profile management
- ✅ **Dashboard**: Stats, health checks, user activity
- ✅ **Image Browser**: DICOM navigation, search, filters
- ✅ **Admin Tools**: User management, system config
- ✅ **Reporting**: Report editor, template selection
- ✅ **Mobile**: Touch-friendly interfaces

#### Migration Strategy:
- 🔄 **Replace OrthancExplorer**: New unified React app
- 🔄 **OHIF Integration**: Embed advanced DICOM viewer
- 🔄 **SA Customization**: Local language, workflows, templates
- 🔄 **Offline Support**: Service worker for load shedding

---

## 🔌 API Mapping: Flask → Orthanc Plugins

### Authentication Endpoints
```
Current Flask                 → Future Orthanc Plugin
POST /api/login              → POST /sa/auth/login
POST /api/2fa/setup          → POST /sa/auth/2fa/setup
GET /api/profile             → GET /sa/users/{id}/profile
```

### SA Healthcare Endpoints
```
Current Flask                 → Future Orthanc Plugin  
GET /api/hpcsa/validate      → GET /sa/healthcare/hpcsa/{number}
POST /api/medical-aid/verify → POST /sa/healthcare/medical-aid/verify
GET /api/templates/sa        → GET /sa/reports/templates
```

### Storage & Images
```
Current Flask                 → Future Orthanc Plugin
GET /api/images              → GET /patients (extended with SA metadata)
POST /api/nas/config         → POST /sa/storage/nas/config
GET /api/nas/status          → GET /sa/storage/status
```

---

## 🚧 Developer A Coordination Needs

### Plugin Interface Requirements
1. **Authentication Plugin** needs to provide:
   - Session validation endpoint
   - User role checking
   - 2FA verification status

2. **SA Compliance Plugin** needs to provide:
   - HPCSA validation endpoint
   - Medical aid verification
   - POPIA compliance checking

3. **Database Extensions** needed:
   - SA user fields (HPCSA number, medical aid, language preference)
   - Extended patient fields (SA ID, medical aid member number)
   - Audit log tables for compliance

### Daily Standup Questions for Developer A:
1. What's the authentication plugin interface design?
2. How will SA-specific fields be added to Orthanc database?
3. What REST endpoints will be available for SA features?
4. How should the React app authenticate with new plugin system?

---

## ⚡ Next Steps for Developer B

### This Week:
1. Complete this feature mapping
2. Create React migration plan
3. Set up new unified React development environment
4. Coordinate authentication strategy with Developer A

### Next Week:
1. Begin building unified React app structure
2. Implement authentication bridge to plugins
3. Start migrating core SA components
4. Test integration with Developer A's plugins

---

**Status**: 📊 Analysis 80% complete. Ready to start building once Developer A provides plugin interfaces!
