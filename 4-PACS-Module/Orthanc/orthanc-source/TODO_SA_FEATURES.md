# SA Features Integration TODO

**🔗 Links to Main TODO**: [Main Integration Plan](../ORTHANC_SA_INTEGRATION_TODO.md)
**📋 Spec Reference**: [Tasks](../.kiro/specs/orthanc-sa-integration/tasks.md)

## 🎯 Developer Assignment: **Frontend/SA Features Developer** [DEVELOPER B - ACTIVE]
**Focus**: React frontend, OHIF integration, SA-specific UI components, mobile optimization
**Status**: 🚧 IN PROGRESS - Analysis Phase
**Started**: January 13, 2025

---

## Phase 1: Analysis & Planning (Weeks 1-2)

### Week 1: Existing Code Analysis [🔄 IN PROGRESS]
- [🔄] **Task 1.1**: Analyze existing Flask application structure [STARTED]
  - [✅] Study `NASIntegration/backend/app.py` and modular architecture
  - [🔄] Document all SA-specific features in current system [IN PROGRESS]
  - [ ] Map Flask routes to future Orthanc REST endpoints
  - **Files to analyze**: `NASIntegration/backend/*.py`
  - **Files to create**: `NASIntegration/FEATURE_MAPPING.md` [CREATING NOW]
  - **Main TODO Reference**: Phase 1 → Week 1 → Development Environment

- [🔄] **Task 1.2**: React frontend preparation [STARTED]
  - [✅] Set up React development environment integrated with Orthanc build
  - [🔄] Analyze existing React components in `NASIntegration/web_interfaces/` [IN PROGRESS]
  - [ ] Plan component migration to Orthanc Explorer replacement
  - **Files to analyze**: `NASIntegration/web_interfaces/src/`
  - **Files to create**: `NASIntegration/REACT_MIGRATION_PLAN.md` [NEXT]
  - **Main TODO Reference**: Phase 1 → Week 1 → Development Environment

### Week 2: Data Migration Planning
- [ ] **Task 2.1**: Database migration preparation
  - Analyze existing SQLite databases in `NASIntegration/backend/*.db`
  - Create data export scripts for migration to unified Orthanc database
  - Plan user account and permission migration
  - **Files to analyze**: `NASIntegration/backend/orthanc_management.db`, `collaboration.db`, etc.
  - **Files to create**: `NASIntegration/database-migration/export-scripts/`
  - **Main TODO Reference**: Phase 1 → Week 2 → Database Extension Implementation

---

## Phase 3: Frontend Integration (Weeks 5-6)

### Week 5: React App Integration
- [ ] **Task 5.1**: Replace Orthanc Explorer with React App
  - Create React build system integrated with Orthanc
  - Migrate existing SA components to new structure
  - Implement routing system replacing jQuery Mobile
  - **Files to create**: `../orthanc-server/OrthancServer/OrthancExplorer/sa-react-app/`
  - **Files to modify**: `../orthanc-server/OrthancServer/OrthancExplorer/explorer.html`
  - **Main TODO Reference**: Phase 3 → Week 5 → React App Integration

- [ ] **Task 5.2**: SA Healthcare UI Components
  - Create HPCSA number input and validation components
  - Implement medical aid selection and validation UI
  - Create multi-language switching interface
  - **Files to create**: `../orthanc-server/OrthancServer/OrthancExplorer/sa-react-app/components/`
  - **Main TODO Reference**: Phase 3 → Week 5 → React App Integration

### Week 6: OHIF Viewer Integration
- [ ] **Task 6.1**: Embed OHIF Viewer with SA Customizations
  - Integrate OHIF viewer from `NASIntegration/ohif-viewer/`
  - Configure OHIF for SA healthcare requirements
  - Implement SA-specific viewer plugins and themes
  - **Files to migrate**: `NASIntegration/ohif-viewer/` → `../orthanc-server/OrthancServer/OrthancExplorer/ohif-integration/`
  - **Files to create**: `../orthanc-server/OrthancServer/OrthancExplorer/ohif-integration/sa-config.js`
  - **Main TODO Reference**: Phase 3 → Week 6 → OHIF Viewer Integration

- [ ] **Task 6.2**: Mobile and Network Optimization
  - Migrate mobile optimization from `NASIntegration/sa-dicom-viewer/`
  - Implement adaptive image quality for SA networks
  - Add offline caching and PWA features
  - **Files to migrate**: `NASIntegration/sa-dicom-viewer/` → `../orthanc-server/OrthancServer/OrthancExplorer/mobile/`
  - **Files to create**: `../orthanc-server/OrthancServer/OrthancExplorer/mobile/network-adapter.js`
  - **Main TODO Reference**: Phase 3 → Week 6 → Mobile and Network Optimization

---

## Phase 4: Testing & Feature Integration (Weeks 7-8)

### Week 7: Frontend Testing
- [ ] **Task 7.1**: Component testing
  - Create Jest tests for SA React components
  - Test multi-language switching functionality
  - Test mobile responsiveness and touch interactions
  - **Files to create**: `../orthanc-server/OrthancServer/OrthancExplorer/sa-react-app/tests/`
  - **Main TODO Reference**: Phase 4 → Week 7 → Testing and Quality Assurance

- [ ] **Task 7.2**: Integration testing with backend
  - Test React app with Orthanc REST API
  - Test authentication flow integration
  - Test OHIF viewer with real DICOM data
  - **Files to create**: `../orthanc-server/OrthancServer/OrthancExplorer/tests/integration/`
  - **Main TODO Reference**: Phase 4 → Week 7 → Testing and Quality Assurance

### Week 8: User Experience Testing
- [ ] **Task 8.1**: User acceptance testing preparation
  - Create test scenarios for SA healthcare workflows
  - Prepare demo data and test cases
  - Document user feedback collection process
  - **Files to create**: `NASIntegration/testing/user-acceptance/`
  - **Main TODO Reference**: Phase 4 → Week 8 → Production Deployment

---

## 📁 Current SA Features to Migrate

### High Priority Features
- [ ] **2FA Authentication System**
  - **Source**: `NASIntegration/backend/auth_2fa.py`
  - **Target**: Integrate with Orthanc auth plugin
  - **Components**: TOTP, backup codes, QR generation

- [ ] **Multi-language Support**
  - **Source**: `NASIntegration/backend/south_african_localization.py`
  - **Target**: React components with i18n
  - **Languages**: English, Afrikaans, isiZulu

- [ ] **HPCSA Compliance**
  - **Source**: `NASIntegration/backend/south_african_api_endpoints.py`
  - **Target**: React forms with validation
  - **Features**: HPCSA number validation, professional verification

- [ ] **Medical Aid Integration**
  - **Source**: `NASIntegration/backend/sa_medical_templates.py`
  - **Target**: React components for medical scheme selection
  - **Schemes**: Discovery, Momentum, Bonitas, etc.

- [ ] **Voice Dictation**
  - **Source**: `NASIntegration/backend/south_african_voice_dictation.py`
  - **Target**: React components with Web Speech API
  - **Features**: Multi-language voice recognition

- [ ] **Reporting Templates**
  - **Source**: `NASIntegration/backend/sa_templates_api.py`
  - **Target**: React reporting interface
  - **Templates**: TB screening, trauma assessment

### Medium Priority Features
- [ ] **NAS Integration**
  - **Source**: `NASIntegration/backend/nas_connector.py`
  - **Target**: Backend integration with Orthanc storage
  - **Features**: SMB/CIFS connectivity, file management

- [ ] **Telemedicine Features**
  - **Source**: `NASIntegration/backend/telemedicine_integration.py`
  - **Target**: React video conferencing components
  - **Features**: Secure video calls, screen sharing

- [ ] **Device Management**
  - **Source**: `NASIntegration/backend/device_management.py`
  - **Target**: React admin interface
  - **Features**: DICOM device configuration, monitoring

### Low Priority Features
- [ ] **AI Diagnosis Engine**
  - **Source**: `NASIntegration/backend/ai_diagnosis_engine.py`
  - **Target**: Future integration with OHIF
  - **Features**: AI-powered diagnosis suggestions

---

## 🔧 Development Environment Setup

### Frontend Development Stack
```bash
# Node.js and React setup
cd orthanc-server/OrthancServer/OrthancExplorer/
npm init -y
npm install react react-dom typescript @types/react @types/react-dom
npm install tailwindcss postcss autoprefixer
npm install @testing-library/react @testing-library/jest-dom jest

# OHIF Viewer dependencies
npm install @ohif/viewer @ohif/core @ohif/ui
```

### Directory Structure to Create
```
orthanc-server/OrthancServer/OrthancExplorer/
├── sa-react-app/                 # ← CREATE THIS
│   ├── src/
│   │   ├── components/
│   │   │   ├── auth/
│   │   │   ├── patients/
│   │   │   ├── studies/
│   │   │   ├── reports/
│   │   │   └── admin/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── utils/
│   ├── public/
│   ├── tests/
│   └── package.json
├── ohif-integration/             # ← CREATE THIS
│   ├── sa-config.js
│   ├── sa-plugins/
│   └── sa-themes/
└── mobile/                       # ← CREATE THIS
    ├── network-adapter.js
    ├── touch-gestures.js
    └── offline-cache.js
```

## 📊 Progress Tracking

### Completion Checklist
- [ ] **Week 1 Complete**: Existing code analyzed, migration plan created
- [ ] **Week 2 Complete**: Data migration scripts ready
- [ ] **Week 5 Complete**: React app integrated, SA components migrated
- [ ] **Week 6 Complete**: OHIF integrated, mobile optimization complete
- [ ] **Week 7 Complete**: Frontend testing complete
- [ ] **Week 8 Complete**: User acceptance testing ready

### Dependencies from Core Developer
- **Need by Week 5**: Authentication REST endpoints from core developer
- **Need by Week 6**: SA-specific REST endpoints for medical aid, HPCSA
- **Need by Week 7**: Database migration completed by core developer

---

## 🚨 Critical Migration Notes

1. **Data Preservation**: Ensure all existing user data and configurations are preserved
2. **Feature Parity**: All current Flask app features must be available in React app
3. **Performance**: React app must load faster than current jQuery Mobile interface
4. **Mobile First**: Optimize for SA mobile networks and touch interfaces
5. **Offline Support**: Maintain offline capabilities for poor connectivity areas

## 📞 Coordination Points

**Daily Standups**: Coordinate with core developer on:
- REST API endpoint specifications and data formats
- Authentication token handling and session management
- Database schema changes and data migration timing
- Error handling and user feedback approaches
- Testing data and scenarios for integration testing