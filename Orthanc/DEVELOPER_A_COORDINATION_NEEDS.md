# Developer B → Developer A Coordination Requirements

**Date**: August 13, 2025  
**From**: Developer B (Frontend/SA Features)  
**To**: Developer A (C++ Plugins/Core)  
**Status**: 🔄 Phase 2 Active Development  

## 🎯 Immediate Needs from Developer A

### 1. **Authentication Plugin API Specification** ⚡ URGENT
**Status**: React app migration in progress - need plugin endpoints ASAP

**Required Endpoints**:
```cpp
// Authentication Plugin REST API
POST /orthanc/auth/sa/login          // { username, pin } → { token, user }
POST /orthanc/auth/sa/logout         // → { success }
POST /orthanc/auth/sa/2fa/setup      // → { qr_code, backup_codes }
POST /orthanc/auth/sa/2fa/verify     // { token } → { success }
GET  /orthanc/auth/sa/user           // → { user_data, preferences }
GET  /orthanc/auth/sa/session        // → { valid, expires_at }
```

**Current React Usage**:
```javascript
// Developer B has already created unifiedAPI.js
await unifiedAPI.login({ username, pin });
await unifiedAPI.setup2FA();
await unifiedAPI.verify2FA(token);
```

**Timeline Need**: Within 3 days for React integration testing

### 2. **Database Schema for SA Metadata** ⚡ URGENT
**Status**: React app needs to know SA metadata structure

**Required SA Extensions**:
```sql
-- Users table extensions
ALTER TABLE Users ADD COLUMN hpcsa_number VARCHAR(20);
ALTER TABLE Users ADD COLUMN medical_aid_scheme VARCHAR(50);
ALTER TABLE Users ADD COLUMN preferred_language VARCHAR(5);
ALTER TABLE Users ADD COLUMN province VARCHAR(20);

-- Studies table extensions  
ALTER TABLE Studies ADD COLUMN sa_medical_aid VARCHAR(50);
ALTER TABLE Studies ADD COLUMN sa_hpcsa_ref VARCHAR(20);
ALTER TABLE Studies ADD COLUMN sa_language VARCHAR(5);
ALTER TABLE Studies ADD COLUMN sa_province VARCHAR(20);
```

**Current React Usage**:
```javascript
// Already implemented in React components
const study = await unifiedAPI.getStudyWithSAMetadata(studyId);
// Expects: study.saMetadata.medical_aid, study.saMetadata.hpcsa_ref
```

**Timeline Need**: Schema definition within 2 days

### 3. **SA Features Plugin Endpoints** 📋 MEDIUM PRIORITY
**Status**: React SA features ready - need plugin backend

**Required Endpoints**:
```cpp
// SA Healthcare Plugin REST API
GET  /orthanc/sa/localization/languages     // → [{ code, name }]
POST /orthanc/sa/localization/set-language  // { language } → { success }
GET  /orthanc/sa/templates/{type}           // → { template_data }
POST /orthanc/sa/medical-aid/validate       // { number, scheme } → { valid, details }
GET  /orthanc/sa/hpcsa/validate/{number}    // → { valid, practitioner_data }
```

**Current React Implementation**: Already using these via unifiedAPI.js with fallback

**Timeline Need**: Within 1 week for Phase 2 completion

## 🔧 What Developer B Has Completed

### ✅ **React Environment & Build System**
- Production-ready React build (113KB bundle)
- All dependencies installed and working
- Build system fixed and optimized
- Development server ready

### ✅ **Unified API Client**
- Created `unifiedAPI.js` with smart plugin/Flask routing
- Supports gradual migration (tries plugin first, falls back to Flask)
- All SA API methods implemented and ready
- Migration control methods for testing

### ✅ **OHIF Viewer Integration Structure**
- Created `OHIFViewerWrapper.jsx` with SA healthcare features
- Mobile optimization for SA networks
- SA metadata display integration
- Voice dictation integration points ready

### ✅ **Documentation & Analysis**
- SA_FEATURES_MIGRATION_ANALYSIS.md (comprehensive feature mapping)
- SA_API_MIGRATION_STRATEGY.md (detailed migration plan)
- All existing SA features analyzed and documented

## 🤝 Coordination Protocol

### Daily Standups (Next 3 Days):
- **10:00 AM**: Authentication plugin progress check
- **2:00 PM**: Database schema alignment
- **4:00 PM**: API endpoint testing coordination

### Testing Protocol:
1. **Developer A**: Implement plugin endpoint
2. **Developer B**: Enable endpoint in unifiedAPI.js
3. **Both**: Test integration with React app
4. **Developer B**: Update documentation

### Example Testing Flow:
```javascript
// Developer B testing process
unifiedAPI.enablePluginEndpoint('/auth/sa/login');
const result = await unifiedAPI.login({ username: 'test', pin: '1234' });
console.log('Plugin test result:', result);
```

## 🚨 Risk Mitigation

### If Plugin Delays Occur:
- React app continues using Flask APIs (seamless fallback)
- Gradual migration endpoint by endpoint
- No user impact during transition
- Can demo completed features independently

### Quality Assurance:
- All React changes are backward compatible
- Comprehensive error handling in unifiedAPI.js
- Migration rollback capability maintained
- SA features tested independently of plugins

## 📊 Phase 2 Progress Dependencies

### Developer B Blocked On:
1. ⏳ **Authentication plugin** → Cannot complete login/session management
2. ⏳ **Database schema** → Cannot finalize SA metadata display
3. ⏳ **Core SA endpoints** → Cannot complete unified API migration

### Developer B Can Continue:
1. ✅ **OHIF viewer refinement** → Independent development
2. ✅ **Mobile optimization** → Independent development  
3. ✅ **UI/UX improvements** → Independent development
4. ✅ **Documentation updates** → Independent development

## 📋 Next Actions for Developer A

### This Week (High Priority):
1. **Monday-Tuesday**: Complete authentication plugin basic structure
2. **Wednesday**: Provide database schema specification
3. **Thursday-Friday**: Implement first SA endpoints for testing

### Communication:
- Update ORTHANC_SA_INTEGRATION_TODO.md with plugin progress
- Create plugin API documentation as endpoints are completed
- Test plugin endpoints with Developer B's React integration

## 🎯 Success Metrics

### By End of Week:
- [ ] Authentication plugin working with React app
- [ ] SA metadata flowing from plugins to React UI
- [ ] At least 3 SA endpoints migrated from Flask to plugins
- [ ] OHIF viewer displaying real DICOM data with SA metadata

### Team Coordination:
- [ ] Daily standup rhythm established
- [ ] Plugin-React integration testing automated
- [ ] Documentation updated by both developers
- [ ] Clear Phase 3 planning completed

---

**🔥 Bottom Line**: Developer B has created a production-ready React environment and unified API client that's ready for plugin integration. Need Developer A's authentication plugin and SA endpoints to complete the unified system.

**Ready for immediate collaboration and testing as soon as plugin endpoints are available!**
