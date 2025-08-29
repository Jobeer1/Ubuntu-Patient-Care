# SA Features API Migration Strategy

**Developer B Task**: React App → Unified Orthanc Plugin Integration  
**Date**: August 13, 2025  
**Status**: 🔄 Phase 2 Planning  

## 🎯 Migration Goal

Transform the current **dual API system** (React app calling Flask APIs + Orthanc APIs) into a **unified system** where the React app calls only Orthanc plugin APIs that include all SA functionality.

## 📊 Current Architecture Analysis

### Current Dual System:
```
React App → Flask API (SA features) + Orthanc API (DICOM)
           ↓                        ↓
     SA Database(s)             DICOM Database
```

### Target Unified System:
```
React App → Unified Orthanc Plugin APIs (SA + DICOM)
           ↓
     Unified Database (Orthanc + SA extensions)
```

## 🔍 SA API Endpoints Analysis

### 1. **Authentication & User Management**
**Current Flask Endpoints**: 
```python
# auth_api.py
POST /api/auth/login
POST /api/auth/logout  
POST /api/auth/2fa/setup
POST /api/auth/2fa/verify
GET  /api/auth/user
```

**Migration Target**: 
```cpp
// Orthanc Plugin Extensions
POST /auth/sa/login          // → SA authentication plugin
POST /auth/sa/logout
POST /auth/sa/2fa/setup
POST /auth/sa/2fa/verify  
GET  /auth/sa/user
```

**Developer A Coordination**: Authentication bridge plugin must implement these endpoints

### 2. **SA Healthcare Features**
**Current Flask Endpoints**:
```python
# south_african_api_endpoints.py
GET  /api/sa/localization/languages
POST /api/sa/localization/set-language
GET  /api/sa/voice/dictate
POST /api/sa/voice/transcribe
GET  /api/sa/templates/{type}
POST /api/sa/medical-aid/validate
GET  /api/sa/hpcsa/validate/{number}
```

**Migration Target**:
```cpp
// SA Integration Plugin 
GET  /sa/localization/languages     // → Multi-language plugin
POST /sa/localization/set-language  
GET  /sa/voice/dictate              // → Voice dictation plugin
POST /sa/voice/transcribe
GET  /sa/templates/{type}           // → Medical templates plugin  
POST /sa/medical-aid/validate       // → Medical aid plugin
GET  /sa/hpcsa/validate/{number}    // → HPCSA compliance plugin
```

### 3. **DICOM + SA Metadata**
**Current Dual Calls**:
```javascript
// React app currently makes 2 calls:
const dicomData = await orthancAPI.get('/studies/{id}');
const saMetadata = await flaskAPI.get('/api/images/{id}/sa-metadata');
```

**Migration Target**:
```cpp
// Enhanced DICOMweb Plugin
GET /dicom-web/studies/{id}  // → Returns DICOM + SA metadata combined
// Response includes: medical_aid, hpcsa_ref, language, province, etc.
```

## 🛠️ React App Migration Tasks

### Phase 2A: API Client Updates (This Week)
- [🔄] **Create Unified API Client**: Replace dual Flask+Orthanc with single Orthanc client
- [🔄] **Update Authentication**: Integrate with new SA authentication plugin
- [🔄] **Migrate SA Feature Calls**: Update all SA endpoints to plugin APIs
- [🔄] **Error Handling**: Unified error handling for plugin responses

### Phase 2B: OHIF Integration (Next Week)  
- [ ] **Embed OHIF Viewer**: Replace custom DICOM viewer with OHIF
- [ ] **SA OHIF Customization**: Add SA-specific OHIF extensions
- [ ] **Mobile Optimization**: Ensure OHIF works on SA mobile networks
- [ ] **Language Integration**: Connect OHIF with SA localization

## 📁 File-by-File Migration Plan

### React Components to Update:

#### 1. **API Client** (`src/utils/api.js`)
```javascript
// BEFORE: Dual API clients
const orthancAPI = axios.create({ baseURL: '/orthanc' });
const flaskAPI = axios.create({ baseURL: '/api' });

// AFTER: Unified API client  
const unifiedAPI = axios.create({ baseURL: '/orthanc' });
// All calls go through Orthanc plugins
```

#### 2. **Authentication** (`src/contexts/AuthContext.js`)
```javascript
// BEFORE: Flask auth endpoints
await flaskAPI.post('/api/auth/login', credentials);

// AFTER: Plugin auth endpoints
await unifiedAPI.post('/auth/sa/login', credentials);
```

#### 3. **SA Features** (`src/components/`)
```javascript
// BEFORE: Flask SA endpoints
await flaskAPI.get('/api/sa/localization/languages');

// AFTER: Plugin SA endpoints  
await unifiedAPI.get('/sa/localization/languages');
```

#### 4. **DICOM Data** (`src/components/images/`)
```javascript
// BEFORE: Separate calls
const dicom = await orthancAPI.get('/studies/{id}');
const saMeta = await flaskAPI.get('/api/images/{id}/sa-metadata');

// AFTER: Combined response
const combined = await unifiedAPI.get('/dicom-web/studies/{id}');
// Contains both DICOM and SA metadata
```

## 🌐 DICOMweb Plugin SA Extensions

### Required Plugin Modifications:

#### 1. **QIDO-RS Enhancements** (`QidoRs.cpp`)
```cpp
// Add SA metadata to query responses
// Include: medical_aid, hpcsa_ref, language, province
// Support multi-language patient names
```

#### 2. **WADO-RS Optimizations** (`WadoRs.cpp`)  
```cpp
// Mobile optimization for SA networks
// Adaptive image quality based on connection
// Load shedding resilience features
```

#### 3. **Configuration Extensions** (`Configuration.cpp`)
```cpp
// SA-specific configuration options
// Multi-language settings
// Medical aid integration settings
// HPCSA validation settings
```

## 🔄 OHIF Integration Strategy

### 1. **Embed OHIF in React App**
```jsx
// New component: src/components/viewer/OHIFViewer.jsx
import { OHIFViewer } from '@ohif/viewer';

const SAOHIFViewer = ({ studyInstanceUID }) => {
  const config = {
    // SA-specific OHIF configuration
    language: userLanguage, // From SA localization
    servers: [{ 
      name: 'Orthanc SA',
      wadoUriRoot: '/orthanc/wado',
      qidoRoot: '/orthanc/dicom-web',
      wadoRoot: '/orthanc/dicom-web'
    }]
  };
  
  return <OHIFViewer config={config} />;
};
```

### 2. **SA OHIF Extensions**
```javascript
// Create SA-specific OHIF extensions:
// - SA medical templates overlay
// - Multi-language interface
// - Mobile touch optimization
// - Voice dictation integration
```

## 🤝 Coordination Points with Developer A

### Critical Dependencies:
1. **Authentication Plugin API**: Need exact endpoint specifications
2. **Database Schema**: SA metadata fields in unified database  
3. **Plugin Configuration**: SA-specific config options
4. **Error Codes**: Unified error handling between plugins

### Weekly Sync Requirements:
- **Monday**: Review authentication plugin progress
- **Wednesday**: Test plugin API endpoints  
- **Friday**: Coordinate database schema changes

## 📅 Timeline & Milestones

### Week 1 (Current): API Migration Setup
- [🔄] **Day 1-2**: Create unified API client
- [🔄] **Day 3-4**: Update authentication integration
- [ ] **Day 5**: Test basic plugin connectivity

### Week 2: OHIF Integration  
- [ ] **Day 1-2**: Embed OHIF viewer in React app
- [ ] **Day 3-4**: Add SA-specific OHIF customizations
- [ ] **Day 5**: Mobile optimization testing

### Week 3: SA Features Migration
- [ ] **Day 1-2**: Migrate voice dictation integration
- [ ] **Day 3-4**: Migrate medical templates
- [ ] **Day 5**: Migrate HPCSA/medical aid validation

## 🚨 Risk Mitigation

### Potential Issues:
1. **Plugin API Delays**: Fallback to gradual migration
2. **OHIF Complexity**: Start with basic viewer, add features incrementally  
3. **Mobile Performance**: Progressive enhancement approach
4. **Authentication Integration**: Maintain session compatibility

### Contingency Plans:
- Keep Flask APIs running during transition
- Gradual feature migration (not big bang)
- Comprehensive testing at each step
- Rollback capability maintained

## 🎯 Success Criteria

### Technical Goals:
- [ ] Single API client in React app
- [ ] OHIF viewer fully integrated
- [ ] All SA features accessible through plugins
- [ ] Mobile performance maintained/improved
- [ ] Single sign-on working across all features

### User Experience Goals:
- [ ] Seamless transition (no user impact)
- [ ] Improved performance (unified system)
- [ ] Enhanced mobile experience (OHIF)
- [ ] Maintained SA healthcare workflow

---

**🔥 Next Action**: Start unified API client implementation and coordinate authentication plugin requirements with Developer A.

**Coordination Status**: Ready for daily standups with Developer A on plugin API specifications.
