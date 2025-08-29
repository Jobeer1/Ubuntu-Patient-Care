# Design Document

## Overview

This design document outlines the technical approach for integrating South African medical imaging custom modules with the core Orthanc PACS system. The solution transforms the current dual-system architecture into a unified, plugin-based system while preserving all SA-specific healthcare features.

## Architecture

### Current State Architecture
```
┌─────────────────┐    ┌─────────────────┐
│   Flask App     │    │   Orthanc Core  │
│   Port 5000     │◄──►│   Port 8042     │
│                 │    │                 │
│ - React UI      │    │ - jQuery Mobile │
│ - SA Features   │    │ - DICOM Storage │
│ - Multiple DBs  │    │ - REST API      │
└─────────────────┘    └─────────────────┘
```

### Target State Architecture
```
┌─────────────────────────────────────────┐
│           Unified Orthanc System        │
│                Port 8042                │
│                                         │
│  ┌─────────────┐  ┌─────────────────┐   │
│  │ React UI    │  │ SA Plugins      │   │
│  │ (Embedded)  │  │ - HPCSA         │   │
│  │             │  │ - POPIA         │   │
│  │ - OHIF      │  │ - Multi-lang    │   │
│  │ - SA UI     │  │ - Medical Aid   │   │
│  └─────────────┘  └─────────────────┘   │
│                                         │
│  ┌─────────────────────────────────────┐ │
│  │        Unified Database             │ │
│  │    (Orthanc + SA Extensions)       │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Components and Interfaces

### 1. SA Integration Plugin (C++)
**File**: `orthanc-sa-integration-plugin/`

```cpp
class SAIntegrationPlugin : public OrthancPlugins {
public:
    // Core plugin interface
    void Initialize();
    void Finalize();
    
    // SA-specific functionality
    bool ValidateHPCSA(const std::string& hpcsa_number);
    bool EnforcePOPIA(const DicomMap& patient_data);
    std::string GetLocalizedText(const std::string& key, const std::string& language);
    
    // Medical aid integration
    bool ValidateMedicalAid(const std::string& scheme, const std::string& member_id);
    
    // REST API extensions
    void RegisterSAEndpoints();
};
```

### 2. Authentication Bridge Plugin (C++)
**File**: `orthanc-sa-auth-plugin/`

```cpp
class SAAuthPlugin : public OrthancPlugins {
public:
    // Authentication interface
    bool AuthenticateUser(const std::string& username, const std::string& password);
    bool ValidateSession(const std::string& session_token);
    
    // 2FA integration
    bool Validate2FA(const std::string& user_id, const std::string& code);
    
    // Role-based access control
    bool HasPermission(const std::string& user_id, const std::string& resource, const std::string& action);
};
```

### 3. Database Extension Plugin (C++)
**File**: `orthanc-sa-database-plugin/`

```cpp
class SADatabasePlugin : public IDatabaseWrapper {
public:
    // Extended database operations
    void StorePatientMetadata(const std::string& patient_id, const Json::Value& sa_metadata);
    void StoreDoctorInfo(const std::string& doctor_id, const Json::Value& doctor_data);
    void StoreAuditLog(const Json::Value& audit_entry);
    
    // SA-specific queries
    Json::Value GetPatientsByMedicalAid(const std::string& scheme);
    Json::Value GetDoctorsByProvince(const std::string& province);
    Json::Value GetComplianceReport(const std::string& date_range);
};
```

### 4. React Frontend Integration
**File**: `orthanc-server/OrthancServer/OrthancExplorer/sa-react-app/`

```javascript
// Replace jQuery Mobile with React
class SAOrthancExplorer extends React.Component {
    render() {
        return (
            <Router>
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/patients" element={<PatientList />} />
                    <Route path="/studies" element={<StudyViewer />} />
                    <Route path="/reports" element={<ReportingModule />} />
                    <Route path="/admin" element={<AdminPanel />} />
                </Routes>
            </Router>
        );
    }
}
```

### 5. OHIF Viewer Integration
**File**: `orthanc-server/OrthancServer/OrthancExplorer/ohif-integration/`

```javascript
// Embed OHIF viewer with SA customizations
const SAOHIFViewer = {
    config: {
        // SA-specific OHIF configuration
        language: 'auto-detect', // EN/AF/ZU
        theme: 'sa-medical',
        compliance: {
            hpcsa: true,
            popia: true
        },
        mobile: {
            optimized: true,
            gestures: true,
            offline: true
        }
    }
};
```

## Data Models

### Extended Patient Model
```sql
-- Extend Orthanc's patient table
ALTER TABLE Patients ADD COLUMN sa_id_number VARCHAR(13);
ALTER TABLE Patients ADD COLUMN medical_scheme VARCHAR(100);
ALTER TABLE Patients ADD COLUMN medical_scheme_number VARCHAR(50);
ALTER TABLE Patients ADD COLUMN preferred_language VARCHAR(10);
ALTER TABLE Patients ADD COLUMN popia_consent_date DATETIME;
ALTER TABLE Patients ADD COLUMN traditional_name VARCHAR(255);
```

### SA Healthcare Professionals Table
```sql
CREATE TABLE SAHealthcareProfessionals (
    id VARCHAR(50) PRIMARY KEY,
    orthanc_user_id VARCHAR(50),
    hpcsa_number VARCHAR(20) UNIQUE,
    name VARCHAR(100) NOT NULL,
    surname VARCHAR(100) NOT NULL,
    practice_name VARCHAR(200),
    specialization VARCHAR(100),
    province VARCHAR(50),
    phone VARCHAR(20),
    email VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_access TIMESTAMP,
    FOREIGN KEY (orthanc_user_id) REFERENCES Users(id)
);
```

### SA Audit Log Table
```sql
CREATE TABLE SAAuditLog (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50),
    hpcsa_number VARCHAR(20),
    action VARCHAR(100),
    resource_type VARCHAR(50),
    resource_id VARCHAR(50),
    patient_id VARCHAR(50),
    compliance_flags JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(100)
);
```

## Error Handling

### Plugin Error Management
```cpp
class SAErrorHandler {
public:
    enum SAErrorCode {
        SA_ERROR_HPCSA_INVALID = 1000,
        SA_ERROR_POPIA_VIOLATION = 1001,
        SA_ERROR_MEDICAL_AID_INVALID = 1002,
        SA_ERROR_LANGUAGE_NOT_SUPPORTED = 1003
    };
    
    static void HandleError(SAErrorCode code, const std::string& details);
    static std::string GetLocalizedErrorMessage(SAErrorCode code, const std::string& language);
};
```

### Frontend Error Handling
```javascript
class SAErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, errorInfo: null };
    }
    
    static getDerivedStateFromError(error) {
        return { hasError: true };
    }
    
    componentDidCatch(error, errorInfo) {
        // Log SA-specific errors
        this.logSAError(error, errorInfo);
    }
    
    logSAError(error, errorInfo) {
        // Send to SA audit system
        fetch('/api/sa/audit/error', {
            method: 'POST',
            body: JSON.stringify({ error, errorInfo, timestamp: new Date() })
        });
    }
}
```

## Testing Strategy

### Unit Testing
- **Plugin Testing**: Test each SA plugin independently
- **Database Testing**: Verify extended schema operations
- **Frontend Testing**: Test React components with SA features
- **API Testing**: Validate SA REST endpoints

### Integration Testing
- **Authentication Flow**: Test SSO between Orthanc and SA features
- **Database Synchronization**: Verify data consistency
- **DICOM Processing**: Test SA compliance in DICOM pipeline
- **Frontend Integration**: Test React app within Orthanc

### Performance Testing
- **Load Testing**: Simulate multiple SA healthcare users
- **DICOM Processing**: Measure performance impact of SA plugins
- **Database Performance**: Test extended schema under load
- **Mobile Performance**: Test on SA network conditions

### Compliance Testing
- **HPCSA Validation**: Test healthcare professional verification
- **POPIA Compliance**: Verify privacy protection measures
- **Audit Logging**: Validate comprehensive audit trails
- **Medical Aid Integration**: Test scheme validation

## Security Considerations

### Authentication Security
- **Single Sign-On**: Secure token exchange between systems
- **Session Management**: Unified session handling
- **2FA Integration**: Maintain existing 2FA functionality
- **Password Policies**: Enforce SA healthcare password requirements

### Data Protection
- **POPIA Compliance**: Implement privacy by design
- **Encryption**: Encrypt sensitive SA healthcare data
- **Access Control**: Role-based access for SA features
- **Audit Trails**: Comprehensive logging for compliance

### Network Security
- **API Security**: Secure SA REST endpoints
- **Mobile Security**: Secure mobile access for SA networks
- **Load Shedding**: Handle power interruptions securely
- **Offline Security**: Secure offline data storage

## Deployment Strategy

### Development Environment
1. **Plugin Development**: Set up Orthanc plugin development environment
2. **Database Setup**: Create extended schema in development
3. **Frontend Integration**: Integrate React app with Orthanc
4. **Testing Setup**: Configure comprehensive testing environment

### Staging Environment
1. **Integration Testing**: Test complete integrated system
2. **Performance Testing**: Validate performance requirements
3. **User Acceptance Testing**: Test with SA healthcare professionals
4. **Security Testing**: Validate security and compliance

### Production Deployment
1. **Data Migration**: Migrate existing data to unified system
2. **Plugin Installation**: Deploy SA plugins to Orthanc
3. **Frontend Deployment**: Replace Orthanc Explorer with React app
4. **Monitoring Setup**: Configure system monitoring and alerting

## Migration Plan

### Phase 1: Foundation (Weeks 1-2)
- Set up plugin development environment
- Create database extension schema
- Implement basic authentication bridge

### Phase 2: Core Integration (Weeks 3-4)
- Develop SA integration plugin
- Implement database synchronization
- Create unified authentication system

### Phase 3: Frontend Integration (Weeks 5-6)
- Replace Orthanc Explorer with React app
- Integrate OHIF viewer
- Implement SA-specific UI components

### Phase 4: Testing and Deployment (Weeks 7-8)
- Comprehensive integration testing
- Performance optimization
- User acceptance testing
- Production deployment