#pragma once

#include <orthanc/OrthancCPlugin.h>
#include <string>
#include <vector>
#include <map>

namespace SACompliance {

    // HPCSA Validation Result Structure
    struct HPCSAValidationResult {
        std::string hpcsaNumber;
        bool isValid;
        std::string registrationCategory;
        std::string categoryName;
        std::string errorMessage;
        std::vector<std::string> validationErrors;
        std::vector<std::string> warnings;
        std::string validationDetails;
        
        HPCSAValidationResult() : isValid(false) {}
    };

    // HPCSA Compliance Statistics
    struct HPCSAComplianceStats {
        int totalProfessionals;
        int validatedProfessionals;
        int pendingValidation;
        int validationFailures;
        double complianceRate;
        
        HPCSAComplianceStats() : totalProfessionals(0), validatedProfessionals(0), 
                               pendingValidation(0), validationFailures(0), complianceRate(0.0) {}
    };

    // POPIA Consent Result Structure
    struct POPIAConsentResult {
        std::string consentStatus;
        bool consentGiven;
        std::string consentDate;
        std::string legalBasis;
        bool canProcess;
        std::string reason;
        
        POPIAConsentResult() : consentGiven(false), canProcess(false) {}
    };

    // POPIA Data Classification Structure
    struct POPIADataClassification {
        std::string classification;
        int sensitivityLevel;
        bool containsPersonalInfo;
        bool containsSpecialPersonalInfo;
        int retentionPeriodDays;
        std::vector<std::string> processingRestrictions;
        std::vector<std::string> requiredSafeguards;
        
        POPIADataClassification() : sensitivityLevel(1), containsPersonalInfo(false), 
                                  containsSpecialPersonalInfo(false), retentionPeriodDays(2555) {}
    };

    // POPIA Compliance Statistics
    struct POPIAComplianceStats {
        int totalPatients;
        int patientsWithConsent;
        double consentRate;
        int dataBreaches;
        int retentionViolations;
        
        POPIAComplianceStats() : totalPatients(0), patientsWithConsent(0), 
                               consentRate(0.0), dataBreaches(0), retentionViolations(0) {}
    };

    // Audit Log Statistics
    struct AuditLogStats {
        int totalEvents;
        int securityEvents;
        int accessViolations;
        int dataAccessEvents;
        
        AuditLogStats() : totalEvents(0), securityEvents(0), 
                        accessViolations(0), dataAccessEvents(0) {}
    };

    // Plugin API Functions
    extern "C" {
        ORTHANC_PLUGINS_API int32_t OrthancPluginInitialize(OrthancPluginContext* context);
        ORTHANC_PLUGINS_API void OrthancPluginFinalize();
        ORTHANC_PLUGINS_API const char* OrthancPluginGetName();
        ORTHANC_PLUGINS_API const char* OrthancPluginGetVersion();
    }

    // REST API Handlers
    OrthancPluginErrorCode HandleHPCSAValidation(OrthancPluginRestOutput* output,
                                               const OrthancPluginHttpRequest* request);
    
    OrthancPluginErrorCode HandleBulkHPCSAValidation(OrthancPluginRestOutput* output,
                                                   const OrthancPluginHttpRequest* request);
    
    OrthancPluginErrorCode HandleSAIDValidation(OrthancPluginRestOutput* output,
                                              const OrthancPluginHttpRequest* request);
    
    OrthancPluginErrorCode HandlePOPIAConsentCheck(OrthancPluginRestOutput* output,
                                                 const OrthancPluginHttpRequest* request);
    
    OrthancPluginErrorCode HandlePOPIADataClassification(OrthancPluginRestOutput* output,
                                                       const OrthancPluginHttpRequest* request);
    
    OrthancPluginErrorCode HandleComplianceReport(OrthancPluginRestOutput* output,
                                                const OrthancPluginHttpRequest* request);

    OrthancPluginErrorCode RestApiHandler(OrthancPluginRestOutput* output,
                                        const char* url,
                                        const OrthancPluginHttpRequest* request);

    // DICOM Processing Callbacks
    OrthancPluginErrorCode OnStoredInstance(OrthancPluginDicomInstance* instance,
                                          const char* instanceId);

    // Utility Functions
    std::string GetRequestBody(const OrthancPluginHttpRequest* request);
    Json::Value ParseJsonBody(const OrthancPluginHttpRequest* request);
    void SendJsonResponse(OrthancPluginRestOutput* output, const Json::Value& json, int statusCode = 200);
    void SendErrorResponse(OrthancPluginRestOutput* output, const std::string& message, int statusCode = 400);

} // namespace SACompliance