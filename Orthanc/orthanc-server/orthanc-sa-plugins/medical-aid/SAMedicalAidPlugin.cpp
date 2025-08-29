#include "SAMedicalAidPlugin.h"
#include "../common/SACommon.h"
#include <orthanc/OrthancCPlugin.h>
#include <json/json.h>
#include <string>
#include <memory>
#include <map>
#include <regex>
#include <algorithm>

static OrthancPluginContext* context = nullptr;

// Plugin information
static const char* PLUGIN_NAME = "SA Medical Aid Integration";
static const char* PLUGIN_VERSION = "1.0.0";
static const char* PLUGIN_DESCRIPTION = "South African Medical Aid Integration Plugin for Orthanc";

namespace SAMedicalAid {

    // Medical Aid Schemes Database
    static const std::map<std::string, MedicalAidScheme> MEDICAL_AID_SCHEMES = {
        {"DISC", {"DISC", "Discovery Health Medical Scheme", "Discovery", true, "^[0-9]{8,12}$", 8, 12}},
        {"GEMS", {"GEMS", "Government Employees Medical Scheme", "GEMS", true, "^[0-9]{10}$", 10, 10}},
        {"BONITAS", {"BONITAS", "Bonitas Medical Fund", "Bonitas", true, "^[0-9]{9,11}$", 9, 11}},
        {"MEDSHIELD", {"MEDSHIELD", "Medshield Medical Scheme", "Medshield", true, "^[0-9]{8,10}$", 8, 10}},
        {"MOMENTUM", {"MOMENTUM", "Momentum Health", "Momentum", true, "^[0-9]{9,12}$", 9, 12}},
        {"FEDHEALTH", {"FEDHEALTH", "Federated Employers Medical Aid Society", "Fedhealth", true, "^[0-9]{8,10}$", 8, 10}},
        {"KEYHEALTH", {"KEYHEALTH", "KeyHealth Medical Scheme", "KeyHealth", true, "^[0-9]{8,11}$", 8, 11}},
        {"PROFMED", {"PROFMED", "Professional Provident Society Medical Scheme", "ProfMed", true, "^[0-9]{7,9}$", 7, 9}},
        {"BESTMED", {"BESTMED", "Bestmed Medical Scheme", "Bestmed", true, "^[0-9]{8,10}$", 8, 10}},
        {"POLMED", {"POLMED", "South African Police Service Medical Scheme", "Polmed", true, "^[0-9]{8,10}$", 8, 10}},
        {"SAMWUMED", {"SAMWUMED", "South African Municipal Workers Union Medical Scheme", "Samwumed", true, "^[0-9]{8,10}$", 8, 10}},
        {"BANKMED", {"BANKMED", "Bankmed", "Bankmed", true, "^[0-9]{8,10}$", 8, 10}},
        {"CAMAF", {"CAMAF", "Consolidated African Medical Aid Fund", "CAMAF", true, "^[0-9]{8,10}$", 8, 10}},
        {"COMPCARE", {"COMPCARE", "CompCare Medical Scheme", "CompCare", true, "^[0-9]{8,10}$", 8, 10}},
        {"GENESIS", {"GENESIS", "Genesis Medical Scheme", "Genesis", true, "^[0-9]{8,10}$", 8, 10}},
        {"LIBERTY", {"LIBERTY", "Liberty Medical Scheme", "Liberty", true, "^[0-9]{8,10}$", 8, 10}},
        {"MEDIHELP", {"MEDIHELP", "Medihelp Medical Scheme", "Medihelp", true, "^[0-9]{8,10}$", 8, 10}},
        {"SELFMED", {"SELFMED", "Selfmed Medical Scheme", "Selfmed", true, "^[0-9]{8,10}$", 8, 10}},
        {"SIZANI", {"SIZANI", "Sizani Medical Fund", "Sizani", true, "^[0-9]{8,10}$", 8, 10}},
        {"TOPMED", {"TOPMED", "Topmed Medical Scheme", "Topmed", true, "^[0-9]{8,10}$", 8, 10}}
    };

    // Utility functions
    std::string GetRequestBody(const OrthancPluginHttpRequest* request) {
        if (request->body == nullptr || request->bodySize == 0) {
            return "";
        }
        return std::string(request->body, request->bodySize);
    }
    
    Json::Value ParseJsonBody(const OrthancPluginHttpRequest* request) {
        Json::Value json;
        Json::Reader reader;
        std::string body = GetRequestBody(request);
        
        if (!body.empty() && !reader.parse(body, json)) {
            throw std::runtime_error("Invalid JSON in request body");
        }
        
        return json;
    }
    
    void SendJsonResponse(OrthancPluginRestOutput* output, const Json::Value& json, int statusCode = 200) {
        Json::StreamWriterBuilder builder;
        std::string response = Json::writeString(builder, json);
        
        OrthancPluginAnswerBuffer(output, response.c_str(), response.size(), "application/json");
    }
    
    void SendErrorResponse(OrthancPluginRestOutput* output, const std::string& message, int statusCode = 400) {
        Json::Value error;
        error["success"] = false;
        error["error"] = message;
        error["error_code"] = statusCode;
        
        SendJsonResponse(output, error, statusCode);
    }

    // Medical Aid Validation Functions
    MedicalAidValidationResult ValidateMemberNumber(const std::string& schemeCode, const std::string& memberNumber) {
        MedicalAidValidationResult result;
        result.schemeCode = schemeCode;
        result.memberNumber = memberNumber;
        result.isValid = false;
        
        // Convert to uppercase for consistency
        std::string upperSchemeCode = schemeCode;
        std::transform(upperSchemeCode.begin(), upperSchemeCode.end(), upperSchemeCode.begin(), ::toupper);
        
        // Find scheme
        auto schemeIt = MEDICAL_AID_SCHEMES.find(upperSchemeCode);
        if (schemeIt == MEDICAL_AID_SCHEMES.end()) {
            result.errorMessage = "Unknown medical aid scheme: " + upperSchemeCode;
            return result;
        }
        
        const MedicalAidScheme& scheme = schemeIt->second;
        result.schemeName = scheme.name;
        result.provider = scheme.provider;
        
        if (!scheme.isActive) {
            result.errorMessage = "Medical aid scheme is not active: " + scheme.name;
            return result;
        }
        
        // Validate member number format
        if (memberNumber.empty()) {
            result.errorMessage = "Member number is required";
            return result;
        }
        
        // Check length
        if (memberNumber.length() < scheme.minLength || memberNumber.length() > scheme.maxLength) {
            result.errorMessage = "Invalid member number length for " + scheme.name + 
                                " (expected " + std::to_string(scheme.minLength) + 
                                "-" + std::to_string(scheme.maxLength) + " digits)";
            return result;
        }
        
        // Check pattern
        std::regex pattern(scheme.memberNumberPattern);
        if (!std::regex_match(memberNumber, pattern)) {
            result.errorMessage = "Invalid member number format for " + scheme.name;
            return result;
        }
        
        // If we get here, validation passed
        result.isValid = true;
        result.validationMessage = "Member number format is valid for " + scheme.name;
        
        return result;
    }
    
    MedicalAidMemberInfo GetMemberInfo(const std::string& schemeCode, const std::string& memberNumber) {
        MedicalAidMemberInfo memberInfo;
        memberInfo.schemeCode = schemeCode;
        memberInfo.memberNumber = memberNumber;
        memberInfo.isFound = false;
        
        // Validate first
        MedicalAidValidationResult validation = ValidateMemberNumber(schemeCode, memberNumber);
        if (!validation.isValid) {
            memberInfo.errorMessage = validation.errorMessage;
            return memberInfo;
        }
        
        // TODO: Implement actual member lookup against medical aid databases
        // For now, return mock data for testing
        if (memberNumber == "123456789" || memberNumber == "987654321") {
            memberInfo.isFound = true;
            memberInfo.memberName = "Test Member";
            memberInfo.memberStatus = "ACTIVE";
            memberInfo.planName = "Hospital Plan";
            memberInfo.planType = "HOSPITAL";
            memberInfo.effectiveDate = "2020-01-01";
            memberInfo.expiryDate = "2024-12-31";
            memberInfo.dependents = 2;
            memberInfo.hasChronicBenefits = true;
            memberInfo.hasDentalCover = false;
            memberInfo.hasOpticalCover = true;
            memberInfo.annualThreshold = 50000.0;
            memberInfo.currentSpending = 15000.0;
            memberInfo.remainingBenefits = 35000.0;
        } else {
            memberInfo.errorMessage = "Member not found in " + validation.schemeName + " database";
        }
        
        return memberInfo;
    }

    // REST API Handlers
    OrthancPluginErrorCode HandleGetSchemes(OrthancPluginRestOutput* output,
                                          const OrthancPluginHttpRequest* request) {
        try {
            if (request->method != OrthancPluginHttpMethod_Get) {
                SendErrorResponse(output, "Method not allowed", 405);
                return OrthancPluginErrorCode_Success;
            }
            
            Json::Value response;
            response["success"] = true;
            response["schemes"] = Json::Value(Json::arrayValue);
            
            for (const auto& pair : MEDICAL_AID_SCHEMES) {
                const MedicalAidScheme& scheme = pair.second;
                
                Json::Value schemeJson;
                schemeJson["code"] = scheme.code;
                schemeJson["name"] = scheme.name;
                schemeJson["provider"] = scheme.provider;
                schemeJson["is_active"] = scheme.isActive;
                schemeJson["member_number_pattern"] = scheme.memberNumberPattern;
                schemeJson["min_length"] = scheme.minLength;
                schemeJson["max_length"] = scheme.maxLength;
                
                response["schemes"].append(schemeJson);
            }
            
            response["total_schemes"] = static_cast<int>(MEDICAL_AID_SCHEMES.size());
            
            SendJsonResponse(output, response);
            return OrthancPluginErrorCode_Success;
            
        } catch (const std::exception& e) {
            OrthancPluginLogError(context, ("Get schemes error: " + std::string(e.what())).c_str());
            SendErrorResponse(output, "Internal server error", 500);
            return OrthancPluginErrorCode_Success;
        }
    }
    
    OrthancPluginErrorCode HandleValidateMember(OrthancPluginRestOutput* output,
                                              const OrthancPluginHttpRequest* request) {
        try {
            if (request->method != OrthancPluginHttpMethod_Post) {
                SendErrorResponse(output, "Method not allowed", 405);
                return OrthancPluginErrorCode_Success;
            }
            
            Json::Value requestJson = ParseJsonBody(request);
            
            std::string schemeCode = requestJson.get("scheme_code", "").asString();
            std::string memberNumber = requestJson.get("member_number", "").asString();
            
            if (schemeCode.empty() || memberNumber.empty()) {
                SendErrorResponse(output, "Scheme code and member number are required", 400);
                return OrthancPluginErrorCode_Success;
            }
            
            // Validate member number
            MedicalAidValidationResult validation = ValidateMemberNumber(schemeCode, memberNumber);
            
            Json::Value response;
            response["success"] = true;
            response["scheme_code"] = validation.schemeCode;
            response["scheme_name"] = validation.schemeName;
            response["provider"] = validation.provider;
            response["member_number"] = validation.memberNumber;
            response["is_valid"] = validation.isValid;
            
            if (validation.isValid) {
                response["message"] = validation.validationMessage;
            } else {
                response["error"] = validation.errorMessage;
            }
            
            SendJsonResponse(output, response);
            return OrthancPluginErrorCode_Success;
            
        } catch (const std::exception& e) {
            OrthancPluginLogError(context, ("Validate member error: " + std::string(e.what())).c_str());
            SendErrorResponse(output, "Internal server error", 500);
            return OrthancPluginErrorCode_Success;
        }
    }
    
    OrthancPluginErrorCode HandleGetMemberInfo(OrthancPluginRestOutput* output,
                                             const OrthancPluginHttpRequest* request) {
        try {
            if (request->method != OrthancPluginHttpMethod_Get) {
                SendErrorResponse(output, "Method not allowed", 405);
                return OrthancPluginErrorCode_Success;
            }
            
            // Extract scheme code and member number from URL path
            std::string url(request->uri);
            
            // Expected format: /sa-medical-aid/member/{scheme_code}/{member_number}
            std::regex urlPattern(R"(/sa-medical-aid/member/([^/]+)/([^/]+))");
            std::smatch matches;
            
            if (!std::regex_match(url, matches, urlPattern)) {
                SendErrorResponse(output, "Invalid URL format. Expected: /sa-medical-aid/member/{scheme_code}/{member_number}", 400);
                return OrthancPluginErrorCode_Success;
            }
            
            std::string schemeCode = matches[1].str();
            std::string memberNumber = matches[2].str();
            
            // Get member information
            MedicalAidMemberInfo memberInfo = GetMemberInfo(schemeCode, memberNumber);
            
            Json::Value response;
            response["success"] = true;
            response["scheme_code"] = memberInfo.schemeCode;
            response["member_number"] = memberInfo.memberNumber;
            response["is_found"] = memberInfo.isFound;
            
            if (memberInfo.isFound) {
                response["member_info"]["name"] = memberInfo.memberName;
                response["member_info"]["status"] = memberInfo.memberStatus;
                response["member_info"]["plan_name"] = memberInfo.planName;
                response["member_info"]["plan_type"] = memberInfo.planType;
                response["member_info"]["effective_date"] = memberInfo.effectiveDate;
                response["member_info"]["expiry_date"] = memberInfo.expiryDate;
                response["member_info"]["dependents"] = memberInfo.dependents;
                response["member_info"]["has_chronic_benefits"] = memberInfo.hasChronicBenefits;
                response["member_info"]["has_dental_cover"] = memberInfo.hasDentalCover;
                response["member_info"]["has_optical_cover"] = memberInfo.hasOpticalCover;
                response["member_info"]["annual_threshold"] = memberInfo.annualThreshold;
                response["member_info"]["current_spending"] = memberInfo.currentSpending;
                response["member_info"]["remaining_benefits"] = memberInfo.remainingBenefits;
            } else {
                response["error"] = memberInfo.errorMessage;
            }
            
            SendJsonResponse(output, response);
            return OrthancPluginErrorCode_Success;
            
        } catch (const std::exception& e) {
            OrthancPluginLogError(context, ("Get member info error: " + std::string(e.what())).c_str());
            SendErrorResponse(output, "Internal server error", 500);
            return OrthancPluginErrorCode_Success;
        }
    }
    
    OrthancPluginErrorCode HandleBulkValidation(OrthancPluginRestOutput* output,
                                              const OrthancPluginHttpRequest* request) {
        try {
            if (request->method != OrthancPluginHttpMethod_Post) {
                SendErrorResponse(output, "Method not allowed", 405);
                return OrthancPluginErrorCode_Success;
            }
            
            Json::Value requestJson = ParseJsonBody(request);
            
            if (!requestJson.isArray()) {
                SendErrorResponse(output, "Request body must be an array of member validation requests", 400);
                return OrthancPluginErrorCode_Success;
            }
            
            Json::Value response;
            response["success"] = true;
            response["total_processed"] = requestJson.size();
            response["valid_count"] = 0;
            response["invalid_count"] = 0;
            response["results"] = Json::Value(Json::arrayValue);
            
            for (const auto& item : requestJson) {
                std::string schemeCode = item.get("scheme_code", "").asString();
                std::string memberNumber = item.get("member_number", "").asString();
                
                if (schemeCode.empty() || memberNumber.empty()) {
                    Json::Value result;
                    result["scheme_code"] = schemeCode;
                    result["member_number"] = memberNumber;
                    result["is_valid"] = false;
                    result["error"] = "Scheme code and member number are required";
                    response["results"].append(result);
                    response["invalid_count"] = response["invalid_count"].asInt() + 1;
                    continue;
                }
                
                MedicalAidValidationResult validation = ValidateMemberNumber(schemeCode, memberNumber);
                
                Json::Value result;
                result["scheme_code"] = validation.schemeCode;
                result["scheme_name"] = validation.schemeName;
                result["member_number"] = validation.memberNumber;
                result["is_valid"] = validation.isValid;
                
                if (validation.isValid) {
                    result["message"] = validation.validationMessage;
                    response["valid_count"] = response["valid_count"].asInt() + 1;
                } else {
                    result["error"] = validation.errorMessage;
                    response["invalid_count"] = response["invalid_count"].asInt() + 1;
                }
                
                response["results"].append(result);
            }
            
            response["success_rate"] = (response["valid_count"].asDouble() / response["total_processed"].asDouble()) * 100.0;
            
            SendJsonResponse(output, response);
            return OrthancPluginErrorCode_Success;
            
        } catch (const std::exception& e) {
            OrthancPluginLogError(context, ("Bulk validation error: " + std::string(e.what())).c_str());
            SendErrorResponse(output, "Internal server error", 500);
            return OrthancPluginErrorCode_Success;
        }
    }
    
    OrthancPluginErrorCode HandleMedicalAidStatistics(OrthancPluginRestOutput* output,
                                                    const OrthancPluginHttpRequest* request) {
        try {
            if (request->method != OrthancPluginHttpMethod_Get) {
                SendErrorResponse(output, "Method not allowed", 405);
                return OrthancPluginErrorCode_Success;
            }
            
            Json::Value response;
            response["success"] = true;
            response["statistics"]["total_schemes"] = static_cast<int>(MEDICAL_AID_SCHEMES.size());
            response["statistics"]["active_schemes"] = 0;
            response["statistics"]["inactive_schemes"] = 0;
            
            // Count active/inactive schemes
            for (const auto& pair : MEDICAL_AID_SCHEMES) {
                if (pair.second.isActive) {
                    response["statistics"]["active_schemes"] = response["statistics"]["active_schemes"].asInt() + 1;
                } else {
                    response["statistics"]["inactive_schemes"] = response["statistics"]["inactive_schemes"].asInt() + 1;
                }
            }
            
            // TODO: Add actual usage statistics from database
            response["statistics"]["total_validations"] = 0;
            response["statistics"]["successful_validations"] = 0;
            response["statistics"]["failed_validations"] = 0;
            response["statistics"]["member_lookups"] = 0;
            response["statistics"]["successful_lookups"] = 0;
            
            response["generated_at"] = SAUtils::GetCurrentTimestamp();
            
            SendJsonResponse(output, response);
            return OrthancPluginErrorCode_Success;
            
        } catch (const std::exception& e) {
            OrthancPluginLogError(context, ("Medical aid statistics error: " + std::string(e.what())).c_str());
            SendErrorResponse(output, "Internal server error", 500);
            return OrthancPluginErrorCode_Success;
        }
    }

    // Main REST API handler
    OrthancPluginErrorCode RestApiHandler(OrthancPluginRestOutput* output,
                                        const char* url,
                                        const OrthancPluginHttpRequest* request) {
        
        std::string urlStr(url);
        
        // Route to appropriate handler
        if (urlStr == "/sa-medical-aid/schemes") {
            return HandleGetSchemes(output, request);
        }
        else if (urlStr == "/sa-medical-aid/validate") {
            return HandleValidateMember(output, request);
        }
        else if (urlStr == "/sa-medical-aid/validate-bulk") {
            return HandleBulkValidation(output, request);
        }
        else if (urlStr == "/sa-medical-aid/statistics") {
            return HandleMedicalAidStatistics(output, request);
        }
        else if (urlStr.find("/sa-medical-aid/member/") == 0) {
            return HandleGetMemberInfo(output, request);
        }
        else {
            SendErrorResponse(output, "Endpoint not found", 404);
            return OrthancPluginErrorCode_Success;
        }
    }

    // Initialize plugin
    extern "C" ORTHANC_PLUGINS_API int32_t OrthancPluginInitialize(OrthancPluginContext* c) {
        context = c;
        
        OrthancPluginLogInfo(context, "Initializing SA Medical Aid Integration Plugin...");
        
        // Set plugin information
        OrthancPluginSetDescription(context, PLUGIN_DESCRIPTION);
        
        try {
            // Register REST API endpoints
            OrthancPluginRegisterRestCallback(context, "/sa-medical-aid/schemes", RestApiHandler);
            OrthancPluginRegisterRestCallback(context, "/sa-medical-aid/validate", RestApiHandler);
            OrthancPluginRegisterRestCallback(context, "/sa-medical-aid/validate-bulk", RestApiHandler);
            OrthancPluginRegisterRestCallback(context, "/sa-medical-aid/statistics", RestApiHandler);
            OrthancPluginRegisterRestCallback(context, "/sa-medical-aid/member/(.*)", RestApiHandler);
            
            OrthancPluginLogInfo(context, "SA Medical Aid Integration Plugin initialized successfully");
            return 0;
            
        } catch (const std::exception& e) {
            std::string error = "Failed to initialize SA Medical Aid Integration Plugin: ";
            error += e.what();
            OrthancPluginLogError(context, error.c_str());
            return -1;
        }
    }

    // Finalize plugin
    extern "C" ORTHANC_PLUGINS_API void OrthancPluginFinalize() {
        OrthancPluginLogInfo(context, "Finalizing SA Medical Aid Integration Plugin...");
        OrthancPluginLogInfo(context, "SA Medical Aid Integration Plugin finalized");
    }

    // Get plugin name
    extern "C" ORTHANC_PLUGINS_API const char* OrthancPluginGetName() {
        return PLUGIN_NAME;
    }

    // Get plugin version
    extern "C" ORTHANC_PLUGINS_API const char* OrthancPluginGetVersion() {
        return PLUGIN_VERSION;
    }

} // namespace SAMedicalAid