# DICOMweb SA Integration TODO

**🔗 Links to Main TODO**: [Main Integration Plan](../ORTHANC_SA_INTEGRATION_TODO.md)
**📋 Spec Reference**: [Tasks](../.kiro/specs/orthanc-sa-integration/tasks.md)

## 🎯 Developer Assignment: **DICOMweb/Standards Developer** [DEVELOPER B - ACTIVE]
**Focus**: DICOMweb compliance, OHIF integration, SA healthcare standards
**Status**: 🚧 IN PROGRESS - Analysis Phase
**Started**: January 13, 2025

---

## Phase 2: DICOMweb Enhancement (Weeks 3-4)

### Week 3: SA-Specific DICOMweb Extensions [✅ ANALYSIS COMPLETE]
- [✅] **Task 3.1**: Extend DICOMweb plugin for SA compliance [ANALYZED]
  - [✅] Analyzed current DICOMweb plugin structure (QidoRs.cpp, WadoRs.cpp, StowRs.cpp)
  - [�] Add HPCSA metadata to DICOM-JSON responses [READY FOR IMPLEMENTATION]
  - [📋] Implement POPIA compliance headers in DICOMweb responses [DOCUMENTED]
  - [📋] Add SA medical aid information to patient queries [SPECIFIED]
  - **Files to modify**: `Plugin/Configuration.cpp`, `Plugin/DicomWebServers.cpp`
  - **Files to create**: `Plugin/SACompliance.cpp`, `Plugin/SAMetadata.cpp`
  - **Main TODO Reference**: Phase 2 → Week 3 → SA Compliance Plugin

- [✅] **Task 3.2**: Multi-language DICOMweb responses [ANALYZED]
  - [✅] Analyzed QIDO-RS query structure for language parameter integration
  - [�] Add language parameter to QIDO-RS queries [DESIGN COMPLETE]
  - [📋] Implement localized error messages in DICOMweb responses [DOCUMENTED]
  - [📋] Support multi-language patient name handling [SPECIFIED]
  - **Files to modify**: `Plugin/QidoRs.cpp`, `Plugin/WadoRs.cpp`
  - **Files to create**: `Plugin/Localization.cpp`
  - **Main TODO Reference**: Phase 2 → Week 4 → Multi-language Support Plugin

### Week 4: OHIF Integration Enhancement
- [ ] **Task 4.1**: Optimize DICOMweb for OHIF viewer
  - Ensure WADO-RS responses are optimized for OHIF
  - Add SA-specific metadata to DICOM-JSON for OHIF consumption
  - Implement progressive loading for SA network conditions
  - **Files to modify**: `Plugin/WadoRs.cpp`, `Plugin/StowRs.cpp`
  - **Files to create**: `Plugin/OHIFOptimization.cpp`
  - **Main TODO Reference**: Phase 3 → Week 6 → OHIF Viewer Integration

- [ ] **Task 4.2**: Mobile optimization for DICOMweb
  - Implement adaptive image quality based on request headers
  - Add compression options for mobile clients
  - Optimize thumbnail generation for mobile viewing
  - **Files to modify**: `Plugin/WadoUri.cpp`
  - **Files to create**: `Plugin/MobileOptimization.cpp`
  - **Main TODO Reference**: Phase 3 → Week 6 → Mobile and Network Optimization

---

## Phase 4: Testing & Standards Compliance (Weeks 7-8)

### Week 7: DICOMweb Standards Testing
- [ ] **Task 7.1**: Validate DICOMweb compliance with SA extensions
  - Test QIDO-RS queries with SA metadata
  - Validate WADO-RS responses with HPCSA information
  - Test STOW-RS with SA compliance validation
  - **Files to create**: `UnitTestsSources/SAComplianceTests.cpp`
  - **Main TODO Reference**: Phase 4 → Week 7 → Testing and Quality Assurance

- [ ] **Task 7.2**: OHIF integration testing
  - Test OHIF viewer with SA-enhanced DICOMweb responses
  - Validate mobile performance with adaptive loading
  - Test multi-language support in OHIF
  - **Files to create**: `UnitTestsSources/OHIFIntegrationTests.cpp`
  - **Main TODO Reference**: Phase 4 → Week 7 → Testing and Quality Assurance

### Week 8: Performance Optimization
- [ ] **Task 8.1**: Optimize for SA network conditions
  - Implement request caching for slow connections
  - Add compression algorithms suitable for medical images
  - Optimize for high-latency connections
  - **Files to modify**: `Plugin/Configuration.cpp`
  - **Files to create**: `Plugin/NetworkOptimization.cpp`
  - **Main TODO Reference**: Phase 4 → Week 8 → Production Deployment

---

## 📋 SA-Specific DICOMweb Requirements

### HPCSA Compliance in DICOMweb
- [ ] **Add HPCSA metadata to DICOM-JSON responses**
  ```json
  {
    "00100010": {"vr": "PN", "Value": [{"Alphabetic": "Patient Name"}]},
    "SA_HPCSA_Doctor": {"vr": "LO", "Value": ["MP123456"]},
    "SA_HPCSA_Verified": {"vr": "CS", "Value": ["YES"]},
    "SA_Access_Level": {"vr": "CS", "Value": ["FULL"]}
  }
  ```

### POPIA Compliance Headers
- [ ] **Add privacy headers to all DICOMweb responses**
  ```http
  X-SA-POPIA-Compliant: true
  X-SA-Data-Classification: medical
  X-SA-Retention-Policy: 7years
  X-SA-Access-Logged: true
  ```

### Medical Aid Integration
- [ ] **Extend patient queries with medical aid information**
  ```json
  {
    "00100020": {"vr": "LO", "Value": ["12345678"]},
    "SA_Medical_Scheme": {"vr": "LO", "Value": ["Discovery Health"]},
    "SA_Member_Number": {"vr": "LO", "Value": ["123456789012"]},
    "SA_Scheme_Option": {"vr": "LO", "Value": ["Executive Plan"]}
  }
  ```

---

## 🔧 Development Environment Setup

### DICOMweb Plugin Development
```bash
# Build DICOMweb plugin with SA extensions
cd orthanc-dicomweb
mkdir build && cd build
cmake .. -DORTHANC_FRAMEWORK_SOURCE=path -DALLOW_DOWNLOADS=ON
make -j4

# Test with SA-specific configuration
cp ../Resources/Configuration.json ./sa-config.json
# Edit sa-config.json to include SA-specific settings
```

### SA-Specific Configuration
```json
{
  "DicomWeb": {
    "Enable": true,
    "Root": "/dicom-web/",
    "EnableWado": true,
    "EnableWadoUri": true,
    "WadoRoot": "/wado",
    "Ssl": false,
    "StowMaxInstances": 10,
    "StowMaxSize": 100,
    "SACompliance": {
      "EnableHPCSA": true,
      "EnablePOPIA": true,
      "EnableMedicalAid": true,
      "DefaultLanguage": "en",
      "SupportedLanguages": ["en", "af", "zu"]
    },
    "MobileOptimization": {
      "EnableAdaptiveQuality": true,
      "EnableProgressive": true,
      "MaxMobileSize": 512
    }
  }
}
```

## 📊 Progress Tracking

### Completion Checklist
- [ ] **Week 3 Complete**: SA compliance extensions in DICOMweb
- [ ] **Week 4 Complete**: OHIF optimization and mobile enhancements
- [ ] **Week 7 Complete**: DICOMweb standards testing complete
- [ ] **Week 8 Complete**: Performance optimization for SA networks

### Integration Points
- **With Core Developer**: SA metadata schema and database extensions
- **With Frontend Developer**: OHIF configuration and mobile optimization
- **With Standards**: DICOM compliance and healthcare regulations

---

## 🚨 Critical Standards Notes

1. **DICOM Compliance**: All SA extensions must maintain DICOM standard compliance
2. **DICOMweb Standards**: QIDO-RS, WADO-RS, STOW-RS must remain standards-compliant
3. **Healthcare Regulations**: HPCSA and POPIA compliance must not break DICOM standards
4. **Performance**: SA optimizations must not degrade standard DICOMweb performance
5. **Backward Compatibility**: Standard DICOM clients must continue to work

## 📞 Coordination Points

**Weekly Coordination**: Coordinate with other developers on:
- SA metadata schema definitions and validation rules
- OHIF viewer configuration and customization requirements
- Mobile optimization strategies and performance targets
- Testing scenarios and compliance validation approaches