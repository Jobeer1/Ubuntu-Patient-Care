# SA Authorization Integration TODO

**🔗 Links to Main TODO**: [Main Integration Plan](../ORTHANC_SA_INTEGRATION_TODO.md)
**📋 Spec Reference**: [Tasks](../.kiro/specs/orthanc-sa-integration/tasks.md)

## 🎯 Developer Assignment: **Security/Authorization Developer**
**Focus**: Authentication, authorization, HPCSA compliance, POPIA data protection

---

## Phase 1: Authentication Foundation (Weeks 1-2)

### Week 1: SA Authentication Analysis
- [ ] **Task 1.1**: Analyze existing Flask authentication system
  - Study 2FA implementation in `../orthanc-source/NASIntegration/backend/auth_2fa.py`
  - Document HPCSA-specific authentication requirements
  - Map Flask auth to Orthanc authorization plugin architecture
  - **Files to analyze**: `../orthanc-source/NASIntegration/backend/auth_*.py`
  - **Files to create**: `SA_AUTH_REQUIREMENTS.md`
  - **Main TODO Reference**: Phase 1 → Week 1 → Development Environment

### Week 2: Authorization Plugin Foundation
- [ ] **Task 2.1**: Extend authorization plugin for SA requirements
  - Add HPCSA number validation to authorization flow
  - Implement SA healthcare role hierarchy
  - Create POPIA compliance authorization checks
  - **Files to modify**: `Plugin/AuthorizationPlugin.cpp`
  - **Files to create**: `Plugin/SAAuthorization.cpp`, `Plugin/HPCSAValidator.cpp`
  - **Main TODO Reference**: Phase 1 → Week 2 → Authentication Bridge Plugin

---

## Phase 2: SA-Specific Authorization (Weeks 3-4)

### Week 3: HPCSA Integration
- [ ] **Task 3.1**: Implement HPCSA-based authorization
  - Create HPCSA number validation service
  - Implement healthcare professional verification
  - Add HPCSA-specific access control rules
  - **Files to create**: `Plugin/HPCSAService.cpp`, `Plugin/HPCSADatabase.cpp`
  - **Main TODO Reference**: Phase 2 → Week 3 → SA Compliance Plugin

- [ ] **Task 3.2**: SA healthcare role management
  - Define SA healthcare professional roles (radiologist, referring doctor, etc.)
  - Implement role-based resource access
  - Create SA-specific permission matrix
  - **Files to create**: `Plugin/SARoles.cpp`, `Plugin/SAPermissions.cpp`
  - **Main TODO Reference**: Phase 2 → Week 3 → SA Compliance Plugin

### Week 4: POPIA Compliance
- [ ] **Task 4.1**: Implement POPIA data protection
  - Add patient data access logging
  - Implement consent-based access control
  - Create data minimization rules
  - **Files to create**: `Plugin/POPIACompliance.cpp`, `Plugin/ConsentManager.cpp`
  - **Main TODO Reference**: Phase 2 → Week 4 → Multi-language Support Plugin

- [ ] **Task 4.2**: Audit logging for compliance
  - Implement comprehensive audit trail
  - Add HPCSA compliance logging
  - Create audit report generation
  - **Files to create**: `Plugin/AuditLogger.cpp`, `Plugin/ComplianceReports.cpp`
  - **Main TODO Reference**: Phase 2 → Week 4 → REST API Extensions

---

## Phase 3: Advanced Security Features (Weeks 5-6)

### Week 5: 2FA Integration
- [ ] **Task 5.1**: Integrate 2FA with authorization plugin
  - Port TOTP implementation from Flask app
  - Add backup codes support
  - Implement 2FA enforcement for admin users
  - **Files to create**: `Plugin/TwoFactorAuth.cpp`, `Plugin/TOTPManager.cpp`
  - **Main TODO Reference**: Phase 3 → Week 5 → React App Integration

- [ ] **Task 5.2**: Session management enhancement
  - Implement single-session enforcement
  - Add session timeout for healthcare compliance
  - Create secure session token management
  - **Files to modify**: `Plugin/AuthorizationPlugin.cpp`
  - **Files to create**: `Plugin/SessionManager.cpp`
  - **Main TODO Reference**: Phase 3 → Week 5 → React App Integration

### Week 6: Mobile Security
- [ ] **Task 6.1**: Mobile device authorization
  - Implement device registration and validation
  - Add mobile-specific security policies
  - Create secure mobile session management
  - **Files to create**: `Plugin/MobileAuth.cpp`, `Plugin/DeviceManager.cpp`
  - **Main TODO Reference**: Phase 3 → Week 6 → Mobile and Network Optimization

---

## Phase 4: Security Testing & Compliance (Weeks 7-8)

### Week 7: Security Testing
- [ ] **Task 7.1**: Comprehensive security testing
  - Test HPCSA validation and authorization flows
  - Validate POPIA compliance implementation
  - Test 2FA integration and session management
  - **Files to create**: `UnitTestsSources/SecurityTests.cpp`
  - **Main TODO Reference**: Phase 4 → Week 7 → Testing and Quality Assurance

- [ ] **Task 7.2**: Penetration testing preparation
  - Create security test scenarios
  - Document security architecture
  - Prepare for external security audit
  - **Files to create**: `SECURITY_ARCHITECTURE.md`, `PENETRATION_TEST_PLAN.md`
  - **Main TODO Reference**: Phase 4 → Week 7 → Testing and Quality Assurance

### Week 8: Compliance Validation
- [ ] **Task 8.1**: HPCSA compliance validation
  - Validate healthcare professional authorization flows
  - Test audit logging for HPCSA requirements
  - Create compliance reports
  - **Files to create**: `HPCSA_COMPLIANCE_REPORT.md`
  - **Main TODO Reference**: Phase 4 → Week 8 → Production Deployment

- [ ] **Task 8.2**: POPIA compliance validation
  - Validate patient data protection measures
  - Test consent management system
  - Create POPIA compliance documentation
  - **Files to create**: `POPIA_COMPLIANCE_REPORT.md`
  - **Main TODO Reference**: Phase 4 → Week 8 → Production Deployment

---

## 📋 SA Authorization Requirements

### HPCSA Professional Validation
```cpp
class HPCSAValidator {
public:
    struct HPCSAInfo {
        std::string hpcsa_number;
        std::string full_name;
        std::string specialization;
        std::string practice_number;
        bool is_active;
        std::string expiry_date;
    };
    
    bool ValidateHPCSANumber(const std::string& hpcsa_number);
    HPCSAInfo GetHPCSAInfo(const std::string& hpcsa_number);
    bool IsAuthorizedForPatient(const std::string& hpcsa_number, const std::string& patient_id);
};
```

### SA Healthcare Roles
```cpp
enum class SAHealthcareRole {
    RADIOLOGIST,
    REFERRING_DOCTOR,
    SPECIALIST,
    GENERAL_PRACTITIONER,
    RADIOGRAPHER,
    ADMIN,
    VIEWER_ONLY
};

class SARoleManager {
public:
    bool HasPermission(SAHealthcareRole role, const std::string& resource, const std::string& action);
    std::vector<std::string> GetAllowedResources(SAHealthcareRole role);
    bool CanAccessPatient(SAHealthcareRole role, const std::string& patient_id, const std::string& user_id);
};
```

### POPIA Compliance
```cpp
class POPIACompliance {
public:
    struct ConsentInfo {
        std::string patient_id;
        bool has_consent;
        std::string consent_date;
        std::vector<std::string> authorized_purposes;
        std::string expiry_date;
    };
    
    bool CheckConsent(const std::string& patient_id, const std::string& purpose);
    void LogDataAccess(const std::string& user_id, const std::string& patient_id, const std::string& action);
    ConsentInfo GetConsentInfo(const std::string& patient_id);
};
```

---

## 🔧 Development Environment Setup

### Authorization Plugin Development
```bash
# Build authorization plugin with SA extensions
cd orthanc-authorization
mkdir build && cd build
cmake .. -DORTHANC_FRAMEWORK_SOURCE=path -DALLOW_DOWNLOADS=ON
make -j4

# Test with SA-specific configuration
cp ../Resources/Configuration.json ./sa-auth-config.json
```

### SA Authorization Configuration
```json
{
  "Authorization": {
    "WebServiceRootUrl": "http://localhost:5000/auth/",
    "WebServiceUsername": "orthanc",
    "WebServicePassword": "orthanc",
    "StandardConfigurations": ["osimis-web-viewer"],
    "CheckedLevel": "studies",
    "SACompliance": {
      "EnableHPCSA": true,
      "HPCSAValidationUrl": "http://localhost:5000/api/hpcsa/validate",
      "EnablePOPIA": true,
      "RequireConsent": true,
      "AuditAllAccess": true,
      "SessionTimeout": 1800,
      "Require2FA": {
        "admin": true,
        "radiologist": true,
        "referring_doctor": false
      }
    },
    "SARoles": {
      "radiologist": {
        "permissions": ["view", "download", "annotate", "report", "share"],
        "resources": ["patients", "studies", "series", "instances"]
      },
      "referring_doctor": {
        "permissions": ["view"],
        "resources": ["assigned_patients"]
      },
      "admin": {
        "permissions": ["*"],
        "resources": ["*"]
      }
    }
  }
}
```

## 📊 Progress Tracking

### Completion Checklist
- [ ] **Week 1 Complete**: SA auth requirements analyzed and documented
- [ ] **Week 2 Complete**: Authorization plugin extended for SA requirements
- [ ] **Week 3 Complete**: HPCSA integration and role management implemented
- [ ] **Week 4 Complete**: POPIA compliance and audit logging functional
- [ ] **Week 5 Complete**: 2FA integration and session management enhanced
- [ ] **Week 6 Complete**: Mobile security features implemented
- [ ] **Week 7 Complete**: Security testing complete and documented
- [ ] **Week 8 Complete**: Compliance validation complete and certified

### Integration Dependencies
- **From Core Developer**: Database schema for SA healthcare professionals
- **From Frontend Developer**: 2FA UI components and session management
- **From DICOMweb Developer**: Authorization headers and compliance metadata

---

## 🚨 Critical Security Notes

1. **HPCSA Validation**: Must validate against official HPCSA database or approved service
2. **POPIA Compliance**: All patient data access must be logged and consent-verified
3. **Session Security**: Healthcare sessions require enhanced security measures
4. **Audit Trail**: Comprehensive logging required for healthcare compliance
5. **2FA Enforcement**: Admin and radiologist accounts must enforce 2FA

## 📞 Coordination Points

**Security Reviews**: Weekly coordination with all developers on:
- Authentication flow design and implementation
- Authorization rules and permission matrices
- Security testing scenarios and compliance validation
- Audit logging requirements and data retention policies
- Mobile security policies and device management approaches