# Orthanc Core Integration TODO

**🔗 Links to Main TODO**: [Main Integration Plan](../ORTHANC_SA_INTEGRATION_TODO.md)
**📋 Spec Reference**: [Tasks](../.kiro/specs/orthanc-sa-integration/tasks.md)

## 🎯 Developer Assignment: **Core Orthanc Developer**
**Focus**: C++ plugin development, database extensions, core system integration

---

## Phase 1: Foundation & Setup (Weeks 1-2)

### Week 1: Plugin Development Environment
- [✅] **Task 1.1**: Set up Orthanc plugin development environment **[COMPLETED - Developer A]**
  - [x] Install CMake 3.16+ and C++14 compatible compiler
  - [x] Download and configure Orthanc SDK headers
  - [x] Create plugin project template with CMakeLists.txt
  - [x] Test basic plugin compilation: `mkdir build && cd build && cmake .. && make`
  - **Files created**: `orthanc-sa-plugins/CMakeLists.txt`, `orthanc-sa-plugins/common/SACommon.h/cpp`
  - **Main TODO Reference**: Phase 1 → Week 1 → Development Environment
  - **Status**: Completed 2025-01-13

- [✅] **Task 1.2**: Database schema extension planning **[COMPLETED - Developer A]**
  - [x] Analyze existing Flask databases in `../orthanc-source/NASIntegration/backend/*.db`
  - [x] Design unified schema extending `OrthancServer/Sources/Database/SQLiteDatabaseWrapper.cpp`
  - [x] Create migration scripts from multiple SQLite DBs
  - **Files created**: 
    - `database-migrations/SA_DATABASE_ANALYSIS.md`
    - `database-migrations/sa-schema-extension.sql`
  - **Files to modify**: `OrthancServer/Sources/Database/SQLiteDatabaseWrapper.cpp`
  - **Main TODO Reference**: Phase 1 → Week 1 → Database Schema Planning
  - **Status**: Completed 2025-01-13 - Schema designed, ready for implementation

### Week 2: Basic Integration Framework
- [✅] **Task 2.1**: Create Authentication Bridge Plugin **[COMPLETED - Developer A]**
  - [x] Create plugin skeleton using Orthanc plugin SDK
  - [x] Implement `OrthancPluginRegisterRestCallback` for auth endpoints
  - [x] Create session token validation system
  - [x] Implement SessionManager with single-session enforcement
  - [x] Implement TwoFactorAuth with TOTP and backup codes
  - **Files created**: 
    - `orthanc-sa-plugins/auth-bridge/AuthBridgePlugin.cpp`
    - `orthanc-sa-plugins/auth-bridge/SessionManager.h/cpp`
    - `orthanc-sa-plugins/auth-bridge/TwoFactorAuth.h/cpp`
  - **Main TODO Reference**: Phase 1 → Week 2 → Authentication Bridge Plugin
  - **Status**: Completed 2025-01-13

- [✅] **Task 2.2**: Universal Database Integration **[COMPLETED - Developer A]**
  - [x] Design SQLite schema with SA healthcare tables
  - [x] Implement database extension in SADatabaseExtension class
  - [x] Create Universal Database Abstraction Layer
  - [x] Support for MySQL, PostgreSQL, Firebird, SQL Server, Oracle
  - [x] Implement HPCSA number validation in C++
  - [x] Create audit logging infrastructure
  - **Files created**: 
    - `orthanc-sa-plugins/database/SADatabaseExtension.h/cpp`
    - `orthanc-sa-plugins/database/SADatabaseAbstraction.h`
    - `orthanc-sa-plugins/database/SADatabaseFactory.cpp`
    - `database-migrations/sa-schema-extension.sql`
    - `database-migrations/UNIVERSAL_DATABASE_SETUP.md`
    - `database-migrations/database-config-examples/*.json` (5 database configs)
  - **Main TODO Reference**: Phase 1 → Week 2 → Database Extension Implementation
  - **Status**: Completed 2025-01-13 - **UNIVERSAL DATABASE SUPPORT IMPLEMENTED**

---

## Phase 2: Core Plugin Development (Weeks 3-4)

### Week 3: SA Compliance Plugin
- [🔄] **Task 3.1**: Develop SA Integration Core Plugin **[IN PROGRESS - Developer A]**
  - [x] Implement HPCSA validation functions
  - [x] Create POPIA compliance checking system
  - [x] Integrate with DICOM processing pipeline using `OrthancPluginRegisterOnStoredInstanceCallback`
  - [🔄] Complete POPIA compliance implementation **[CURRENT WORK - 95% complete]**
  - **Files created**: 
    - `orthanc-sa-plugins/sa-compliance/SACompliancePlugin.cpp`
    - `orthanc-sa-plugins/sa-compliance/HPCSAValidator.h/cpp`
    - `orthanc-sa-plugins/sa-compliance/POPIACompliance.h`
  - **Files in progress**: `orthanc-sa-plugins/sa-compliance/POPIACompliance.cpp`
  - **Main TODO Reference**: Phase 2 → Week 3 → SA Compliance Plugin
  - **Status**: Finishing data subject rights and breach notification

- [ ] **Task 3.2**: Medical Aid Integration Plugin
  - Implement validation for SA medical schemes
  - Create medical aid member verification
  - Add medical aid REST endpoints
  - **Files to create**: `orthanc-sa-plugins/medical-aid/MedicalAidPlugin.cpp`
  - **Files to create**: `orthanc-sa-plugins/medical-aid/SchemeValidator.cpp`
  - **Main TODO Reference**: Phase 2 → Week 3 → Medical Aid Integration Plugin

### Week 4: Advanced Features Plugin
- [ ] **Task 4.1**: Multi-language Support Plugin
  - Create language detection system
  - Implement medical terminology translation
  - Add language preferences to user profiles
  - **Files to create**: `orthanc-sa-plugins/localization/LocalizationPlugin.cpp`
  - **Files to create**: `orthanc-sa-plugins/localization/TerminologyDB.cpp`
  - **Main TODO Reference**: Phase 2 → Week 4 → Multi-language Support Plugin

- [ ] **Task 4.2**: REST API Extensions
  - Create SA-specific REST endpoints
  - Extend existing Orthanc endpoints with SA metadata
  - Implement SA search and filtering
  - **Files to modify**: `OrthancServer/Sources/OrthancRestApi/OrthancRestApi.cpp`
  - **Files to create**: `orthanc-sa-plugins/rest-api/SARestEndpoints.cpp`
  - **Main TODO Reference**: Phase 2 → Week 4 → REST API Extensions

---

## Phase 4: Testing & Core Integration (Weeks 7-8)

### Week 7: Plugin Testing
- [ ] **Task 7.1**: Unit testing for plugins
  - Create Google Test framework for plugin testing
  - Test HPCSA validation functions
  - Test database extension functionality
  - **Files to create**: `orthanc-sa-plugins/tests/TestHPCSAValidation.cpp`
  - **Files to create**: `orthanc-sa-plugins/tests/TestDatabaseExtension.cpp`
  - **Main TODO Reference**: Phase 4 → Week 7 → Testing and Quality Assurance

- [ ] **Task 7.2**: Integration testing
  - Test plugin loading and initialization
  - Test REST API endpoint functionality
  - Test DICOM processing with SA features
  - **Files to create**: `orthanc-sa-plugins/tests/IntegrationTests.cpp`
  - **Main TODO Reference**: Phase 4 → Week 7 → Testing and Quality Assurance

### Week 8: Production Deployment
- [ ] **Task 8.1**: Plugin compilation and packaging
  - Create automated build scripts
  - Package plugins for distribution
  - Create installation documentation
  - **Files to create**: `orthanc-sa-plugins/build-scripts/build-all.sh`
  - **Files to create**: `orthanc-sa-plugins/INSTALL.md`
  - **Main TODO Reference**: Phase 4 → Week 8 → Production Deployment

---

## 🔧 Development Environment Setup

### Required Tools
```bash
# Ubuntu/Debian
sudo apt-get install cmake g++ libgtest-dev

# Build Orthanc from source (for plugin development)
git clone https://github.com/jodogne/OrthancMirror.git
cd OrthancMirror
mkdir build && cd build
cmake .. -DSTANDALONE_BUILD=ON
make -j4
```

### Plugin Development Structure
```
orthanc-server/
├── orthanc-sa-plugins/           # ← CREATE THIS
│   ├── CMakeLists.txt
│   ├── auth-bridge/
│   ├── sa-compliance/
│   ├── medical-aid/
│   ├── localization/
│   ├── database/
│   ├── rest-api/
│   └── tests/
└── OrthancServer/                # ← MODIFY EXISTING
    ├── Sources/Database/         # Extend database
    └── Sources/OrthancRestApi/   # Extend REST API
```

## 📊 Progress Tracking

### Completion Checklist
- [ ] **Week 1 Complete**: Plugin dev environment + database planning
- [ ] **Week 2 Complete**: Auth bridge + database extensions working
- [ ] **Week 3 Complete**: SA compliance + medical aid plugins functional
- [ ] **Week 4 Complete**: Multi-language + REST API extensions ready
- [ ] **Week 7 Complete**: All plugins tested and validated
- [ ] **Week 8 Complete**: Plugins packaged and deployment-ready

### Dependencies for Frontend Developer
- **After Task 2.1**: Authentication endpoints available for frontend integration
- **After Task 4.2**: SA REST endpoints available for frontend consumption
- **After Task 4.1**: Language switching API available for frontend

---

## 🚨 Critical Notes

1. **Plugin Loading Order**: Ensure SA plugins load after core Orthanc initialization
2. **Database Compatibility**: Test with both SQLite and PostgreSQL
3. **Memory Management**: Use Orthanc's memory management functions in plugins
4. **Error Handling**: Implement proper error codes and logging
5. **Thread Safety**: Ensure all plugin functions are thread-safe

## 📞 Coordination Points

**Daily Standups**: Coordinate with frontend developer on:
- API endpoint specifications
- Authentication token formats
- Database schema changes
- Error handling approaches

## 🔄 **CURRENT STATUS UPDATE - Developer A**
**Date**: 2025-01-13  
**Current Work**: Authentication Bridge Plugin development

### ✅ **Completed Today**:
1. **Plugin Development Environment**: Full CMake setup with multi-plugin architecture
2. **Common SA Utilities**: Created shared utilities for HPCSA validation, SA ID validation, language handling
3. **Authentication Plugin Structure**: Basic plugin skeleton with REST endpoints

### 🔄 **Currently Working On**:
- **SessionManager class**: Token-based session management
- **TwoFactorAuth class**: TOTP integration for 2FA
- **Database integration**: Connecting to existing Flask databases

### 📋 **Ready for Developer B**:
- **API Endpoints Available**: 
  - `POST /sa/auth/login` - User authentication
  - `POST /sa/auth/validate` - Session validation  
  - `POST /sa/auth/logout` - User logout
- **Authentication Token Format**: Bearer token in Authorization header
- **Error Response Format**: JSON with success/error_code/message structure

### 🚨 **Need from Developer B**:
- **Frontend Auth Integration**: Update React components to use new `/sa/auth/*` endpoints
- **Session Token Handling**: Store and send Bearer tokens in requests
- **Error Handling**: Handle SA-specific error codes (1000-1005)

### 📅 **Next Steps (Tomorrow)**:
1. Complete SessionManager and TwoFactorAuth classes
2. Start database extension work
3. Begin SA Compliance Plugin development