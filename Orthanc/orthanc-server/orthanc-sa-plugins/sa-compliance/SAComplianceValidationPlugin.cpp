#include "SAComplianceValidationPlugin.h"
#include "HPCSAValidator.h"
#include "POPIACompliance.h"
#include "SAAuditLogger.h"
#include "../common/SACommon.h"
#include <orthanc/OrthancCPlugin.h>
#include <json/json.h>
#include <string>
#include <memory>
#include <regex>

static OrthancPluginContext* context = nullptr;
static std::unique_ptr<SACompliance::HPCSAValidator> hpcsaValidator;
static std::unique_ptr<SACompliance::POPIACompliance> popiaCompliance;
static std::unique_ptr<SACompliance::SAAuditLogger> auditLogger;

// Plugin information
static const char* PLUGIN_NAME = "SA Compliance Validation";
static const char* PLUGIN_VERSION = "1.0.0";
static const char* PLUGIN_DESCRIPTION = "South African Healthcare Compliance Validation Plugin for Orthanc";

namespace SACompliance {

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

    // HPCSA Validation Handlers
    OrthancPluginErrorCode HandleHPCSAValidation(OrthancPluginRestOutput* output,
                                               const OrthancPluginHttpRequest* request) {
        try {
            if (request->method != OrthancPluginHttpMethod_Post) {
                SendErrorResponse(output, "Method not allowed", 405);
                return OrthancPluginErrorCode_Success;
            }
            
            Json::Value requestJson = ParseJsonBody(request);
            
            std::string hpcsaNumber = requestJson.get("hpcsa_number", "").asString();
            std::string registrationCategory = requestJson.get("registration_category", "").asString();
            
            if (hpcsaNumber.empty()) {
                SendErrorResponse(output, "HPCSA number is required", 400);
                return OrthancPluginErrorCode_Success;
            }
            
            // Validate HPCSA number
            HPCSAValidationResult result = hpcsaValidator->validateHPCSANumber(hpcsaNumber, registrationCategory);
            
            // Log validation attempt
            auditLogger->logHPCSAValidation(hpcsaNumber, result.isValid, result.errorMessage);
            
            // Prepare response
            Json::Value response;
            response["success"] = true;
            response["hpcsa_number"] = result.hpcsaNumber;
            response["is_valid"] = result.isValid;
            response["registration_category"] = result.registrationCategory;
            response["category_name"] = result.categoryName;
            response["validation_details"] = result.validationDetails;
            
            if (!result.isValid) {
                response["error"] = result.errorMessage;
                response["validation_errors"] = Json::Value(Json::arrayValue);
                for (const auto& error : result.validationErrors) {
                    response["validation_errors"].append(error);
                }
            }
            
            if (!result.warnings.empty()) {
                response["warnings"] = Json::Value(Json::arrayValue);
                for (const auto& warning : result.warnings) {
                    response["warnings"].append(warning);
                }
            }
            
            SendJsonResponse(output, response);
            return OrthancPluginErrorCode_Success;
            
        } catch (const std::exception& e) {
            OrthancPluginLogError(context, ("HPCSA validation error: " + std::string(e.what())).c_str());
            SendErrorResponse(output, "Internal server error", 500);
            return OrthancPluginErrorCode_Success;
        }
    }
    
    OrthancPluginErrorCode HandleBulkHPCSAValidation(OrthancPluginRestOutput* output,
                                                   const OrthancPluginHttpRequest* request) {
        try {
            if (request->method != OrthancPluginHttpMethod_Post) {
                SendErrorResponse(output, "Method not allowed", 405);
                return OrthancPluginErrorCode_Success;
            }
            
            Json::Value requestJson = ParseJsonBody(request);
            
            if (!requestJson.isArray()) {
                SendErrorResponse(output, "Request body must be an array of HPCSA numbers", 400);
                return OrthancPluginErrorCode_Success;
            }
            
            Json::Value response;
            response["success"] = true;
            response["total_processed"] = requestJson.size();
            response["valid_count"] = 0;
            response["invalid_count"] = 0;
            response["results"] = Json::Value(Json::arrayValue);
            
            for (const auto& item : requestJson) {
                std::string hpcsaNumber = item.get("hpcsa_number", "").asString();
                std::string registrationCategory = item.get("registration_category", "").asString();
                
                if (hpcsaNumber.empty()) {
                    Json::Value result;
                    result["hpcsa_number"] = "";
                    result["is_valid"] = false;
                    result["error"] = "HPCSA number is required";
                    response["results"].append(result);
                    response["invalid_count"] = response["invalid_count"].asInt() + 1;
                    continue;
                }
                
                HPCSAValidationResult validationResult = hpcsaValidator->validateHPCSANumber(hpcsaNumber, registrationCategory);
                
                Json::Value result;
                result["hpcsa_number"] = validationResult.hpcsaNumber;
                result["is_valid"] = validationResult.isValid;
                result["registration_category"] = validationResult.registrationCategory;
                result["category_name"] = validationResult.categoryName;
                
                if (!validationResult.isValid) {
                    result["error"] = validationResult.errorMessage;
                    response["invalid_count"] = response["invalid_count"].asInt() + 1;
                } else {
                    response["valid_count"] = response["valid_count"].asInt() + 1;
                }
                
                response["results"].append(result);
                
                // Log validation
                auditLogger->logHPCSAValidation(hpcsaNumber, validationResult.isValid, validationResult.errorMessage);
            }
            
            response["success_rate"] = (response["valid_count"].asDouble() / response["total_processed"].asDouble()) * 100.0;
            
            SendJsonResponse(output, response);
            return OrthancPluginErrorCode_Success;
            
        } catch (const std::exception& e) {
            OrthancPluginLogError(context, ("Bulk HPCSA validation error: " + std::string(e.what())).c_str());
            SendErrorResponse(output, "Internal server error", 500);
            return OrthancPluginErrorCode_Success;
        }
    }

    // SA ID Number Validation Handler
    OrthancPluginErrorCode HandleSAIDValidation(OrthancPluginRestOutput* output,
                                              const OrthancPluginHttpRequest* request) {
        try {
            if (request->method != OrthancPluginHttpMethod_Post) {
                SendErrorResponse(output, "Method not allowed", 405);
                return OrthancPluginErrorCode_Success;
            }
            
            Json::Value requestJson = ParseJsonBody(request);
            
            std::string idNumber = requestJson.get("id_number", "").asString();
            
            if (idNumber.empty()) {
                SendErrorResponse(output, "SA ID number is required", 400);
                return OrthancPluginErrorCode_Success;
            }
            
            // Validate SA ID number format (13 digits)
            std::regex idPattern("^[0-9]{13}$");
            bool isValidFormat = std::regex_match(idNumber, idPattern);
            
            Json::Value response;
            response["success"] = true;
            response["id_number"] = idNumber;
            response["is_valid_format"] = isValidFormat;
            
            if (isValidFormat) {
                // Extract information from ID number
                std::string birthDate = idNumber.substr(0, 6);
                std::string genderDigit = idNumber.substr(6, 1);
                std::string citizenshipDigit = idNumber.substr(10, 1);
                
                // Parse birth date (YYMMDD)
                int year = std::stoi(birthDate.substr(0, 2));
                int month = std::stoi(birthDate.substr(2, 2));
                int day = std::stoi(birthDate.substr(4, 2));
                
                // Determine century (assume current century for years 00-30, previous for 31-99)
                if (year <= 30) {
                    year += 2000;
                } else {
                    year += 1900;
                }
                
                response["birth_date"] = std::to_string(year) + "-" + 
                                       (month < 10 ? "0" : "") + std::to_string(month) + "-" +
                                       (day < 10 ? "0" : "") + std::to_string(day);
                
                response["gender"] = (std::stoi(genderDigit) >= 5) ? "Male" : "Female";
                response["citizenship"] = (citizenshipDigit == "0") ? "SA Citizen" : "Permanent Resident";
                
                // Validate checksum (Luhn algorithm)
                int sum = 0;
                for (int i = 0; i < 12; i++) {
                    int digit = idNumber[i] - '0';
                    if (i % 2 == 1) {
                        digit *= 2;
                        if (digit > 9) digit -= 9;
                    }
                    sum += digit;
                }
                
                int checkDigit = (10 - (sum % 10)) % 10;
                bool isValidChecksum = (checkDigit == (idNumber[12] - '0'));
                
                response["is_valid_checksum"] = isValidChecksum;
                response["is_valid"] = isValidFormat && isValidChecksum;
                
                if (!isValidChecksum) {
                    response["error"] = "Invalid checksum";
                }
            } else {
                response["is_valid"] = false;
                response["error"] = "Invalid format - must be 13 digits";
            }
            
            // Log validation attempt
            auditLogger->logSAIDValidation(idNumber, response["is_valid"].asBool(), 
                                         response.get("error", "").asString());
            
            SendJsonResponse(output, response);
            return OrthancPluginErrorCode_Success;
            
        } catch (const std::exception& e) {
            OrthancPluginLogError(context, ("SA ID validation error: " + std::string(e.what())).c_str());
            SendErrorResponse(output, "Internal server error", 500);
            return OrthancPluginErrorCode_Success;
        }
    }

    // POPIA Compliance Handlers
    OrthancPluginErrorCode HandlePOPIAConsentCheck(OrthancPluginRestOutput* output,
                                                 const OrthancPluginHttpRequest* request) {
        try {
            if (request->method != OrthancPluginHttpMethod_Post) {
                SendErrorResponse(output, "Method not allowed", 405);
                return OrthancPluginErrorCode_Success;
            }
            
            Json::Value requestJson = ParseJsonBody(request);
            
            std::string patientId = requestJson.get("patient_id", "").asString();
            std::string processingPurpose = requestJson.get("processing_purpose", "").asString();
            
            if (patientId.empty()) {
                SendErrorResponse(output, "Patient ID is required", 400);
                return OrthancPluginErrorCode_Success;
            }
            
            // Check POPIA consent
            POPIAConsentResult consentResult = popiaCompliance->checkConsent(patientId, processingPurpose);
            
            Json::Value response;
            response["success"] = true;
            response["patient_id"] = patientId;
            response["processing_purpose"] = processingPurpose;
            response["consent_status"] = consentResult.consentStatus;
            response["consent_given"] = consentResult.consentGiven;
            response["consent_date"] = consentResult.consentDate;
            response["legal_basis"] = consentResult.legalBasis;
            response["can_process"] = consentResult.canProcess;
            
            if (!consentResult.canProcess) {
                response["reason"] = consentResult.reason;
            }
            
            // Log consent check
            auditLogger->logPOPIAConsentCheck(patientId, processingPurpose, consentResult.consentGiven);
            
            SendJsonResponse(output, response);
            return OrthancPluginErrorCode_Success;
            
        } catch (const std::exception& e) {
            OrthancPluginLogError(context, ("POPIA consent check error: " + std::string(e.what())).c_str());
            SendErrorResponse(output, "Internal server error", 500);
            return OrthancPluginErrorCode_Success;
        }
    }
    
    OrthancPluginErrorCode HandlePOPIADataClassification(OrthancPluginRestOutput* output,
                                                       const OrthancPluginHttpRequest* request) {
        try {
            if (request->method != OrthancPluginHttpMethod_Post) {
                SendErrorResponse(output, "Method not allowed", 405);
                return OrthancPluginErrorCode_Success;
            }
            
            Json::Value requestJson = ParseJsonBody(request);
            
            std::string dataType = requestJson.get("data_type", "").asString();
            Json::Value dataContent = requestJson.get("data_content", Json::Value());
            
            if (dataType.empty()) {
                SendErrorResponse(output, "Data type is required", 400);
                return OrthancPluginErrorCode_Success;
            }
            
            // Classify data according to POPIA
            POPIADataClassification classification = popiaCompliance->classifyData(dataType, dataContent);
            
            Json::Value response;
            response["success"] = true;
            response["data_type"] = dataType;
            response["classification"] = classification.classification;
            response["sensitivity_level"] = classification.sensitivityLevel;
            response["contains_personal_info"] = classification.containsPersonalInfo;
            response["contains_special_personal_info"] = classification.containsSpecialPersonalInfo;
            response["retention_period_days"] = classification.retentionPeriodDays;
            response["processing_restrictions"] = Json::Value(Json::arrayValue);
            
            for (const auto& restriction : classification.processingRestrictions) {
                response["processing_restrictions"].append(restriction);
            }
            
            response["required_safeguards"] = Json::Value(Json::arrayValue);
            for (const auto& safeguard : classification.requiredSafeguards) {
                response["required_safeguards"].append(safeguard);
            }
            
            SendJsonResponse(output, response);
            return OrthancPluginErrorCode_Success;
            
        } catch (const std::exception& e) {
            OrthancPluginLogError(context, ("POPIA data classification error: " + std::string(e.what())).c_str());
            SendErrorResponse(output, "Internal server error", 500);
            return OrthancPluginErrorCode_Success;
        }
    }

    // Compliance Report Handler
    OrthancPluginErrorCode HandleComplianceReport(OrthancPluginRestOutput* output,
                                                const OrthancPluginHttpRequest* request) {
        try {
            if (request->method != OrthancPluginHttpMethod_Get) {
                SendErrorResponse(output, "Method not allowed", 405);
                return OrthancPluginErrorCode_Success;
            }
            
            // Generate compliance report
            Json::Value report;
            report["success"] = true;
            report["report_generated"] = SAUtils::GetCurrentTimestamp();
            
            // HPCSA compliance statistics
            HPCSAComplianceStats hpcsaStats = hpcsaValidator->getComplianceStatistics();
            report["hpcsa_compliance"]["total_professionals"] = hpcsaStats.totalProfessionals;
            report["hpcsa_compliance"]["validated_professionals"] = hpcsaStats.validatedProfessionals;
            report["hpcsa_compliance"]["pending_validation"] = hpcsaStats.pendingValidation;
            report["hpcsa_compliance"]["validation_failures"] = hpcsaStats.validationFailures;
            report["hpcsa_compliance"]["compliance_rate"] = hpcsaStats.complianceRate;
            
            // POPIA compliance statistics
            POPIAComplianceStats popiaStats = popiaCompliance->getComplianceStatistics();
            report["popia_compliance"]["total_patients"] = popiaStats.totalPatients;
            report["popia_compliance"]["patients_with_consent"] = popiaStats.patientsWithConsent;
            report["popia_compliance"]["consent_rate"] = popiaStats.consentRate;
            report["popia_compliance"]["data_breaches"] = popiaStats.dataBreaches;
            report["popia_compliance"]["retention_violations"] = popiaStats.retentionViolations;
            
            // Audit log statistics
            AuditLogStats auditStats = auditLogger->getAuditStatistics();
            report["audit_compliance"]["total_events"] = auditStats.totalEvents;
            report["audit_compliance"]["security_events"] = auditStats.securityEvents;
            report["audit_compliance"]["access_violations"] = auditStats.accessViolations;
            report["audit_compliance"]["data_access_events"] = auditStats.dataAccessEvents;
            
            SendJsonResponse(output, report);
            return OrthancPluginErrorCode_Success;
            
        } catch (const std::exception& e) {
            OrthancPluginLogError(context, ("Compliance report error: " + std::string(e.what())).c_str());
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
        if (urlStr == "/sa-compliance/hpcsa/validate") {
            return HandleHPCSAValidation(output, request);
        }
        else if (urlStr == "/sa-compliance/hpcsa/validate-bulk") {
            return HandleBulkHPCSAValidation(output, request);
        }
        else if (urlStr == "/sa-compliance/sa-id/validate") {
            return HandleSAIDValidation(output, request);
        }
        else if (urlStr == "/sa-compliance/popia/consent-check") {
            return HandlePOPIAConsentCheck(output, request);
        }
        else if (urlStr == "/sa-compliance/popia/data-classification") {
            return HandlePOPIADataClassification(output, request);
        }
        else if (urlStr == "/sa-compliance/report") {
            return HandleComplianceReport(output, request);
        }
        else {
            SendErrorResponse(output, "Endpoint not found", 404);
            return OrthancPluginErrorCode_Success;
        }
    }

    // DICOM processing callback for compliance validation
    OrthancPluginErrorCode OnStoredInstance(OrthancPluginDicomInstance* instance,
                                          const char* instanceId) {
        try {
            // Extract patient information from DICOM
            Json::Value patientInfo;
            
            // Get patient ID
            const char* patientId = nullptr;
            if (OrthancPluginGetInstanceSimplifiedJson(context, &patientId, instance) == OrthancPluginErrorCode_Success) {
                Json::Value instanceJson;
                Json::Reader reader;
                if (reader.parse(patientId, instanceJson)) {
                    patientInfo = instanceJson.get("PatientID", Json::Value());
                }
            }
            
            // Validate compliance for stored instance
            if (!patientInfo.isNull()) {
                std::string patientIdStr = patientInfo.asString();
                
                // Check POPIA consent for medical imaging
                POPIAConsentResult consentResult = popiaCompliance->checkConsent(patientIdStr, "MEDICAL_IMAGING");
                
                if (!consentResult.canProcess) {
                    OrthancPluginLogWarning(context, 
                        ("POPIA compliance warning: No consent for medical imaging processing for patient " + patientIdStr).c_str());
                    
                    // Log compliance violation
                    auditLogger->logComplianceViolation("POPIA_NO_CONSENT", patientIdStr, "Medical imaging stored without consent");
                }
                
                // Log DICOM storage event
                auditLogger->logDICOMAccess("STORE", instanceId, patientIdStr, "SYSTEM");
            }
            
            return OrthancPluginErrorCode_Success;
            
        } catch (const std::exception& e) {
            OrthancPluginLogError(context, ("DICOM compliance validation error: " + std::string(e.what())).c_str());
            return OrthancPluginErrorCode_InternalError;
        }
    }

    // Initialize plugin
    extern "C" ORTHANC_PLUGINS_API int32_t OrthancPluginInitialize(OrthancPluginContext* c) {
        context = c;
        
        OrthancPluginLogInfo(context, "Initializing SA Compliance Validation Plugin...");
        
        // Set plugin information
        OrthancPluginSetDescription(context, PLUGIN_DESCRIPTION);
        
        try {
            // Initialize validators and compliance checkers
            hpcsaValidator = std::make_unique<HPCSAValidator>();
            popiaCompliance = std::make_unique<POPIACompliance>();
            auditLogger = std::make_unique<SAAuditLogger>();
            
            // Register REST API endpoints
            OrthancPluginRegisterRestCallback(context, "/sa-compliance/hpcsa/validate", RestApiHandler);
            OrthancPluginRegisterRestCallback(context, "/sa-compliance/hpcsa/validate-bulk", RestApiHandler);
            OrthancPluginRegisterRestCallback(context, "/sa-compliance/sa-id/validate", RestApiHandler);
            OrthancPluginRegisterRestCallback(context, "/sa-compliance/popia/consent-check", RestApiHandler);
            OrthancPluginRegisterRestCallback(context, "/sa-compliance/popia/data-classification", RestApiHandler);
            OrthancPluginRegisterRestCallback(context, "/sa-compliance/report", RestApiHandler);
            
            // Register DICOM instance callback for compliance validation
            OrthancPluginRegisterOnStoredInstanceCallback(context, OnStoredInstance);
            
            OrthancPluginLogInfo(context, "SA Compliance Validation Plugin initialized successfully");
            return 0;
            
        } catch (const std::exception& e) {
            std::string error = "Failed to initialize SA Compliance Validation Plugin: ";
            error += e.what();
            OrthancPluginLogError(context, error.c_str());
            return -1;
        }
    }

    // Finalize plugin
    extern "C" ORTHANC_PLUGINS_API void OrthancPluginFinalize() {
        OrthancPluginLogInfo(context, "Finalizing SA Compliance Validation Plugin...");
        
        // Cleanup resources
        hpcsaValidator.reset();
        popiaCompliance.reset();
        auditLogger.reset();
        
        OrthancPluginLogInfo(context, "SA Compliance Validation Plugin finalized");
    }

    // Get plugin name
    extern "C" ORTHANC_PLUGINS_API const char* OrthancPluginGetName() {
        return PLUGIN_NAME;
    }

    // Get plugin version
    extern "C" ORTHANC_PLUGINS_API const char* OrthancPluginGetVersion() {
        return PLUGIN_VERSION;
    }

} // namespace SACompliance