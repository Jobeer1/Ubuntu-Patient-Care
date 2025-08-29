#pragma once

#include <orthanc/OrthancCPlugin.h>
#include <string>
#include <vector>
#include <map>

namespace SAMedicalAid {

    // Medical Aid Scheme Structure
    struct MedicalAidScheme {
        std::string code;
        std::string name;
        std::string provider;
        bool isActive;
        std::string memberNumberPattern;
        int minLength;
        int maxLength;
        
        MedicalAidScheme() : isActive(true), minLength(8), maxLength(12) {}
        
        MedicalAidScheme(const std::string& c, const std::string& n, const std::string& p, 
                        bool active, const std::string& pattern, int minLen, int maxLen)
            : code(c), name(n), provider(p), isActive(active), 
              memberNumberPattern(pattern), minLength(minLen), maxLength(maxLen) {}
    };

    // Medical Aid Validation Result Structure
    struct MedicalAidValidationResult {
        std::string schemeCode;
        std::string schemeName;
        std::string provider;
        std::string memberNumber;
        bool isValid;
        std::string errorMessage;
        std::string validationMessage;
        
        MedicalAidValidationResult() : isValid(false) {}
    };

    // Medical Aid Member Information Structure
    struct MedicalAidMemberInfo {
        std::string schemeCode;
        std::string memberNumber;
        bool isFound;
        std::string errorMessage;
        
        // Member details
        std::string memberName;
        std::string memberStatus;
        std::string planName;
        std::string planType;
        std::string effectiveDate;
        std::string expiryDate;
        int dependents;
        
        // Benefits information
        bool hasChronicBenefits;
        bool hasDentalCover;
        bool hasOpticalCover;
        double annualThreshold;
        double currentSpending;
        double remainingBenefits;
        
        MedicalAidMemberInfo() : isFound(false), dependents(0), 
                               hasChronicBenefits(false), hasDentalCover(false), hasOpticalCover(false),
                               annualThreshold(0.0), currentSpending(0.0), remainingBenefits(0.0) {}
    };

    // Medical Aid Statistics Structure
    struct MedicalAidStatistics {
        int totalSchemes;
        int activeSchemes;
        int inactiveSchemes;
        int totalValidations;
        int successfulValidations;
        int failedValidations;
        int memberLookups;
        int successfulLookups;
        double validationSuccessRate;
        double lookupSuccessRate;
        
        MedicalAidStatistics() : totalSchemes(0), activeSchemes(0), inactiveSchemes(0),
                               totalValidations(0), successfulValidations(0), failedValidations(0),
                               memberLookups(0), successfulLookups(0),
                               validationSuccessRate(0.0), lookupSuccessRate(0.0) {}
    };

    // Plugin API Functions
    extern "C" {
        ORTHANC_PLUGINS_API int32_t OrthancPluginInitialize(OrthancPluginContext* context);
        ORTHANC_PLUGINS_API void OrthancPluginFinalize();
        ORTHANC_PLUGINS_API const char* OrthancPluginGetName();
        ORTHANC_PLUGINS_API const char* OrthancPluginGetVersion();
    }

    // Core Medical Aid Functions
    MedicalAidValidationResult ValidateMemberNumber(const std::string& schemeCode, const std::string& memberNumber);
    MedicalAidMemberInfo GetMemberInfo(const std::string& schemeCode, const std::string& memberNumber);

    // REST API Handlers
    OrthancPluginErrorCode HandleGetSchemes(OrthancPluginRestOutput* output,
                                          const OrthancPluginHttpRequest* request);
    
    OrthancPluginErrorCode HandleValidateMember(OrthancPluginRestOutput* output,
                                              const OrthancPluginHttpRequest* request);
    
    OrthancPluginErrorCode HandleGetMemberInfo(OrthancPluginRestOutput* output,
                                             const OrthancPluginHttpRequest* request);
    
    OrthancPluginErrorCode HandleBulkValidation(OrthancPluginRestOutput* output,
                                              const OrthancPluginHttpRequest* request);
    
    OrthancPluginErrorCode HandleMedicalAidStatistics(OrthancPluginRestOutput* output,
                                                    const OrthancPluginHttpRequest* request);

    OrthancPluginErrorCode RestApiHandler(OrthancPluginRestOutput* output,
                                        const char* url,
                                        const OrthancPluginHttpRequest* request);

    // Utility Functions
    std::string GetRequestBody(const OrthancPluginHttpRequest* request);
    Json::Value ParseJsonBody(const OrthancPluginHttpRequest* request);
    void SendJsonResponse(OrthancPluginRestOutput* output, const Json::Value& json, int statusCode = 200);
    void SendErrorResponse(OrthancPluginRestOutput* output, const std::string& message, int statusCode = 400);

} // namespace SAMedicalAid