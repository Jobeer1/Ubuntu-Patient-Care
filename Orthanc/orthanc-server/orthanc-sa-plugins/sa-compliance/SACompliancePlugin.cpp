/**
 * South African Healthcare Integration for Orthanc
 * SA Compliance Plugin - HPCSA and POPIA compliance integration
 * 
 * This plugin integrates SA healthcare compliance requirements into
 * Orthanc's DICOM processing pipeline and REST API.
 */

#include "../common/SACommon.h"
#include "../database/SADatabaseExtension.h"
#include "HPCSAValidator.h"
#include "POPIACompliance.h"
#include "SAAuditLogger.h"
#include <orthanc/OrthancCPlugin.h>
#include <json/json.h>
#include <string>
#include <map>
#include <chrono>

static OrthancPluginContext* context_ = nullptr;
static SADatabaseExtension* database_ = nullptr;
static std::unique_ptr<SACompliance::HPCSAValidator> hpcsa_validator_ = nullptr;
static std::unique_ptr<SACompliance::POPIACompliance> popia_compliance_ = nullptr;
static std::unique_ptr<SACompliance::SAAuditLogger> audit_logger_ = nullptr;

// DICOM instance callback - called when DICOM is stored
static OrthancPluginErrorCode OnStoredInstance(const OrthancPluginDicomInstance* instance,
                                               const char* instanceId) {
  auto startTime = std::chrono::steady_clock::now();
  
  try {
    SAUtils::LogInfo(context_, "SA Compliance check for stored instance: " + std::string(instanceId));
    
    // Get DICOM tags for compliance checking
    Json::Value dicom_json;
    char* json_str = OrthancPluginGetInstanceSimplifiedJson(context_, instanceId);
    if (json_str) {
      Json::Reader reader;
      reader.parse(json_str, dicom_json);
      OrthancPluginFreeString(context_, json_str);
    }
    
    // Extract DICOM metadata
    std::string patient_id = dicom_json.get("PatientID", "").asString();
    std::string patient_name = dicom_json.get("PatientName", "").asString();
    std::string study_instance_uid = dicom_json.get("StudyInstanceUID", "").asString();
    std::string series_instance_uid = dicom_json.get("SeriesInstanceUID", "").asString();
    std::string sop_instance_uid = dicom_json.get("SOPInstanceUID", "").asString();
    std::string modality = dicom_json.get("Modality", "").asString();
    std::string study_date = dicom_json.get("StudyDate", "").asString();
    
    // Create comprehensive audit event
    SACompliance::SAAuditLogger::AuditEvent auditEvent;
    auditEvent.eventType = "DICOM_STORE";
    auditEvent.eventCategory = SACompliance::SAAuditLogger::EventCategory::DICOM;
    auditEvent.eventSeverity = SACompliance::SAAuditLogger::EventSeverity::INFO;
    auditEvent.userId = 0; // System operation
    auditEvent.username = "system";
    auditEvent.resourceType = "INSTANCE";
    auditEvent.resourceId = instanceId;
    auditEvent.patientId = patient_id;
    auditEvent.studyInstanceUid = study_instance_uid;
    auditEvent.seriesInstanceUid = series_instance_uid;
    auditEvent.sopInstanceUid = sop_instance_uid;
    auditEvent.modality = modality;
    auditEvent.studyDate = study_date;
    auditEvent.actionPerformed = "STORE";
    auditEvent.dataProcessingPurpose = "MEDICAL_TREATMENT";
    auditEvent.professionalContext = "DICOM_STORAGE";
    auditEvent.dataClassification = "CONFIDENTIAL";
    auditEvent.securityLevel = "HIGH";
    auditEvent.dataMinimizationApplied = true;
    
    bool overallCompliant = true;
    std::string complianceDetails = "";
    
    if (patient_id.empty()) {
      SAUtils::LogWarning(context_, "No PatientID found in DICOM instance: " + std::string(instanceId));
      auditEvent.eventSeverity = SACompliance::SAAuditLogger::EventSeverity::WARNING;
      auditEvent.errorMessage = "Missing PatientID in DICOM instance";
      complianceDetails += "Missing PatientID; ";
      overallCompliant = false;
    }
    
    // Check POPIA compliance for patient data
    if (popia_compliance_ && !patient_id.empty()) {
      bool consent_valid = popia_compliance_->checkPatientConsent(patient_id, "MEDICAL_TREATMENT");
      auditEvent.dataSubjectConsent = consent_valid;
      
      if (!consent_valid) {
        SAUtils::LogWarning(context_, "POPIA: No valid consent for patient: " + patient_id);
        complianceDetails += "No POPIA consent; ";
        overallCompliant = false;
        
        // Log specific compliance violation
        if (audit_logger_) {
          audit_logger_->logComplianceViolation("POPIA_NO_CONSENT", 
                                              SACompliance::SAAuditLogger::EventSeverity::WARNING,
                                              "DICOM stored without valid POPIA consent",
                                              0, "", patient_id);
        }
      }
      
      // Check data minimization
      bool data_minimized = popia_compliance_->checkDataMinimization(patient_id, "MEDICAL_TREATMENT");
      auditEvent.dataMinimizationApplied = data_minimized;
      if (!data_minimized) {
        complianceDetails += "Data not minimized; ";
      }
    }
    
    // Check if this is a SA patient (has SA ID number)
    SAPatientExtension patient_ext;
    if (database_ && database_->GetPatientExtensionByOrthancId(patient_ext, patient_id)) {
      if (!patient_ext.sa_id_number.empty()) {
        // Validate SA ID number format
        if (!SAUtils::IsValidSAIDNumber(patient_ext.sa_id_number)) {
          SAUtils::LogError(context_, "Invalid SA ID number format: " + patient_ext.sa_id_number);
          complianceDetails += "Invalid SA ID format; ";
          overallCompliant = false;
          
          // Log compliance violation
          if (audit_logger_) {
            audit_logger_->logComplianceViolation("INVALID_SA_ID", 
                                                SACompliance::SAAuditLogger::EventSeverity::ERROR,
                                                "Invalid SA ID number: " + patient_ext.sa_id_number,
                                                0, "", patient_id);
          }
        }
      }
      
      // Check medical scheme validation
      if (!patient_ext.medical_scheme.empty()) {
        bool scheme_valid = database_->ValidateMedicalScheme(patient_ext.medical_scheme);
        if (!scheme_valid) {
          SAUtils::LogWarning(context_, "Invalid medical scheme: " + patient_ext.medical_scheme);
          complianceDetails += "Invalid medical scheme; ";
        }
      }
    }
    
    // Set compliance flags
    auditEvent.complianceFlags["POPIA_CONSENT"] = auditEvent.dataSubjectConsent ? "true" : "false";
    auditEvent.complianceFlags["DATA_MINIMIZED"] = auditEvent.dataMinimizationApplied ? "true" : "false";
    auditEvent.complianceFlags["PATIENT_ID_PRESENT"] = patient_id.empty() ? "false" : "true";
    auditEvent.complianceFlags["OVERALL_COMPLIANT"] = overallCompliant ? "true" : "false";
    
    // Set final audit event properties
    auditEvent.actionResult = overallCompliant ? 
      SACompliance::SAAuditLogger::ActionResult::SUCCESS : 
      SACompliance::SAAuditLogger::ActionResult::PARTIAL;
    auditEvent.actionDetails = complianceDetails;
    
    // Calculate processing time
    auto endTime = std::chrono::steady_clock::now();
    auditEvent.processingTimeMs = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime).count();
    
    // Log the comprehensive audit event
    if (audit_logger_) {
      audit_logger_->logEvent(auditEvent);
    }
    
    // Legacy logging for backward compatibility
    if (database_) {
      std::string risk_level = overallCompliant ? "low" : "medium";
      database_->LogUserAction("system", "DICOM_STORED", "instance", instanceId,
                               patient_id, "DICOM instance stored with compliance check: " + complianceDetails,
                               "", "", "", risk_level);
    }
    
    std::string logMessage = "SA Compliance check completed for instance: " + std::string(instanceId) + 
                           " - " + (overallCompliant ? "COMPLIANT" : "NON-COMPLIANT");
    if (!complianceDetails.empty()) {
      logMessage += " (" + complianceDetails + ")";
    }
    SAUtils::LogInfo(context_, logMessage);
    
    return OrthancPluginErrorCode_Success;
    
  } catch (const std::exception& e) {
    // Log error event
    if (audit_logger_) {
      SACompliance::SAAuditLogger::AuditEvent errorEvent;
      errorEvent.eventType = "DICOM_STORE_ERROR";
      errorEvent.eventCategory = SACompliance::SAAuditLogger::EventCategory::SYSTEM;
      errorEvent.eventSeverity = SACompliance::SAAuditLogger::EventSeverity::ERROR;
      errorEvent.resourceType = "INSTANCE";
      errorEvent.resourceId = instanceId;
      errorEvent.actionPerformed = "STORE";
      errorEvent.actionResult = SACompliance::SAAuditLogger::ActionResult::FAILED;
      errorEvent.errorMessage = e.what();
      errorEvent.actionDetails = "Exception during SA compliance check";
      
      auto endTime = std::chrono::steady_clock::now();
      errorEvent.processingTimeMs = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime).count();
      
      audit_logger_->logEvent(errorEvent);
    }
    
    SAUtils::LogError(context_, "SA Compliance error in OnStoredInstance: " + std::string(e.what()));
    return OrthancPluginErrorCode_Success; // Don't block storage on compliance errors
  }
}

// REST API endpoint for HPCSA validation
static OrthancPluginErrorCode ValidateHPCSA(OrthancPluginRestOutput* output,
                                            const char* url,
                                            const OrthancPluginHttpRequest* request) {
  if (request->method != OrthancPluginHttpMethod_Post) {
    OrthancPluginSendHttpStatusCode(context_, output, 405);
    return OrthancPluginErrorCode_Success;
  }

  try {
    // Parse request body
    Json::Value request_json;
    Json::Reader reader;
    if (!reader.parse(request->body, request->body + request->bodySize, request_json)) {
      std::string error = SAUtils::CreateErrorResponse(400, "Invalid JSON in request body");
      OrthancPluginAnswerBuffer(context_, output, error.c_str(), error.length(), "application/json");
      return OrthancPluginErrorCode_Success;
    }

    std::string hpcsa_number = request_json.get("hpcsa_number", "").asString();
    if (hpcsa_number.empty()) {
      std::string error = SAUtils::CreateErrorResponse(400, "HPCSA number required");
      OrthancPluginAnswerBuffer(context_, output, error.c_str(), error.length(), "application/json");
      return OrthancPluginErrorCode_Success;
    }

    // Validate HPCSA number format
    bool format_valid = SAUtils::IsValidHPCSANumber(hpcsa_number);
    if (!format_valid) {
      std::string error = SAUtils::CreateErrorResponse(SA_ERROR_HPCSA_INVALID, "Invalid HPCSA number format");
      OrthancPluginAnswerBuffer(context_, output, error.c_str(), error.length(), "application/json");
      return OrthancPluginErrorCode_Success;
    }

    // Check if HPCSA number exists in database
    SAHealthcareProfessional professional;
    bool exists = database_ && database_->GetHealthcareProfessionalByHPCSA(professional, hpcsa_number);
    
    // Validate with external HPCSA service if available
    bool external_valid = true;
    if (hpcsa_validator_) {
      external_valid = hpcsa_validator_->ValidateWithHPCSAService(hpcsa_number);
    }

    // Create response
    Json::Value response;
    response["success"] = true;
    response["hpcsa_number"] = hpcsa_number;
    response["format_valid"] = format_valid;
    response["exists_in_database"] = exists;
    response["external_validation"] = external_valid;
    response["is_verified"] = exists && professional.is_verified;
    
    if (exists) {
      response["professional_info"]["full_name"] = professional.practice_name;
      response["professional_info"]["specialization"] = professional.specialization;
      response["professional_info"]["province"] = SAUtils::GetProvinceCode(professional.province);
      response["professional_info"]["is_active"] = professional.is_active;
      response["professional_info"]["verification_date"] = professional.verification_date;
    }

    Json::StreamWriterBuilder builder;
    std::string response_str = Json::writeString(builder, response);
    
    OrthancPluginAnswerBuffer(context_, output, response_str.c_str(), response_str.length(), "application/json");
    
    // Log validation request
    if (database_) {
      std::string user_id = "unknown"; // TODO: Get from session
      database_->LogUserAction(user_id, "HPCSA_VALIDATION", "hpcsa_number", hpcsa_number,
                               "", "HPCSA number validation requested");
    }
    
    return OrthancPluginErrorCode_Success;

  } catch (const std::exception& e) {
    SAUtils::LogError(context_, "HPCSA validation error: " + std::string(e.what()));
    std::string error = SAUtils::CreateErrorResponse(500, "Internal server error");
    OrthancPluginAnswerBuffer(context_, output, error.c_str(), error.length(), "application/json");
    return OrthancPluginErrorCode_Success;
  }
}

// REST API endpoint for POPIA compliance check
static OrthancPluginErrorCode CheckPOPIACompliance(OrthancPluginRestOutput* output,
                                                   const char* url,
                                                   const OrthancPluginHttpRequest* request) {
  if (request->method != OrthancPluginHttpMethod_Post) {
    OrthancPluginSendHttpStatusCode(context_, output, 405);
    return OrthancPluginErrorCode_Success;
  }

  try {
    // Parse request body
    Json::Value request_json;
    Json::Reader reader;
    if (!reader.parse(request->body, request->body + request->bodySize, request_json)) {
      std::string error = SAUtils::CreateErrorResponse(400, "Invalid JSON in request body");
      OrthancPluginAnswerBuffer(context_, output, error.c_str(), error.length(), "application/json");
      return OrthancPluginErrorCode_Success;
    }

    std::string patient_id = request_json.get("patient_id", "").asString();
    std::string action = request_json.get("action", "view").asString();
    
    if (patient_id.empty()) {
      std::string error = SAUtils::CreateErrorResponse(400, "Patient ID required");
      OrthancPluginAnswerBuffer(context_, output, error.c_str(), error.length(), "application/json");
      return OrthancPluginErrorCode_Success;
    }

    // Check POPIA compliance
    bool consent_valid = false;
    bool data_minimized = false;
    std::string consent_date = "";
    std::string consent_version = "";
    
    if (popia_compliance_) {
      consent_valid = popia_compliance_->CheckPatientConsent(patient_id);
      data_minimized = popia_compliance_->IsDataMinimized(patient_id, action);
    }
    
    // Get patient consent information from database
    SAPatientExtension patient_ext;
    if (database_ && database_->GetPatientExtension(patient_ext, patient_id)) {
      consent_date = patient_ext.consent_date;
      consent_version = patient_ext.consent_version;
    }

    // Create response
    Json::Value response;
    response["success"] = true;
    response["patient_id"] = patient_id;
    response["action"] = action;
    response["popia_compliant"] = consent_valid && data_minimized;
    response["consent_valid"] = consent_valid;
    response["data_minimized"] = data_minimized;
    response["consent_date"] = consent_date;
    response["consent_version"] = consent_version;
    
    if (!consent_valid) {
      response["compliance_issues"] = Json::Value(Json::arrayValue);
      response["compliance_issues"].append("Missing or expired patient consent");
    }
    
    if (!data_minimized) {
      if (!response.isMember("compliance_issues")) {
        response["compliance_issues"] = Json::Value(Json::arrayValue);
      }
      response["compliance_issues"].append("Data access not minimized for requested action");
    }

    Json::StreamWriterBuilder builder;
    std::string response_str = Json::writeString(builder, response);
    
    OrthancPluginAnswerBuffer(context_, output, response_str.c_str(), response_str.length(), "application/json");
    
    // Log compliance check
    if (database_) {
      std::string user_id = "unknown"; // TODO: Get from session
      std::string risk_level = consent_valid ? "low" : "medium";
      database_->LogUserAction(user_id, "POPIA_COMPLIANCE_CHECK", "patient", patient_id,
                               patient_id, "POPIA compliance check for action: " + action,
                               "", "", "", risk_level);
    }
    
    return OrthancPluginErrorCode_Success;

  } catch (const std::exception& e) {
    SAUtils::LogError(context_, "POPIA compliance error: " + std::string(e.what()));
    std::string error = SAUtils::CreateErrorResponse(500, "Internal server error");
    OrthancPluginAnswerBuffer(context_, output, error.c_str(), error.length(), "application/json");
    return OrthancPluginErrorCode_Success;
  }
}

// REST API endpoint for SA compliance report
static OrthancPluginErrorCode GetComplianceReport(OrthancPluginRestOutput* output,
                                                  const char* url,
                                                  const OrthancPluginHttpRequest* request) {
  if (request->method != OrthancPluginHttpMethod_Get) {
    OrthancPluginSendHttpStatusCode(context_, output, 405);
    return OrthancPluginErrorCode_Success;
  }

  try {
    // Get compliance statistics
    Json::Value response;
    response["success"] = true;
    response["report_generated"] = SAUtils::GetCurrentTimestamp();
    
    if (database_) {
      // User statistics
      response["users"]["total"] = database_->GetTotalUsers();
      response["users"]["active"] = database_->GetActiveUsers();
      
      // Healthcare professional statistics
      response["healthcare_professionals"]["verified"] = database_->GetVerifiedHealthcareProfessionals();
      
      // Patient statistics
      response["patients"]["total"] = database_->GetTotalPatients();
      response["patients"]["with_consent"] = database_->GetPatientsWithConsent();
      
      // Report statistics
      response["reports"]["total"] = database_->GetTotalReports();
      
      // Secure shares statistics
      response["secure_shares"]["active"] = database_->GetActiveSecureShares();
      
      // Compliance metrics
      int total_patients = database_->GetTotalPatients();
      int patients_with_consent = database_->GetPatientsWithConsent();
      
      if (total_patients > 0) {
        double consent_percentage = (double)patients_with_consent / total_patients * 100.0;
        response["compliance"]["popia_consent_percentage"] = consent_percentage;
        response["compliance"]["popia_compliant"] = (consent_percentage >= 95.0); // 95% threshold
      } else {
        response["compliance"]["popia_consent_percentage"] = 100.0;
        response["compliance"]["popia_compliant"] = true;
      }
      
      int verified_professionals = database_->GetVerifiedHealthcareProfessionals();
      response["compliance"]["hpcsa_verification_count"] = verified_professionals;
    }

    Json::StreamWriterBuilder builder;
    std::string response_str = Json::writeString(builder, response);
    
    OrthancPluginAnswerBuffer(context_, output, response_str.c_str(), response_str.length(), "application/json");
    
    // Log report generation
    if (database_) {
      std::string user_id = "unknown"; // TODO: Get from session
      database_->LogUserAction(user_id, "COMPLIANCE_REPORT_GENERATED", "system", "compliance_report",
                               "", "SA compliance report generated");
    }
    
    return OrthancPluginErrorCode_Success;

  } catch (const std::exception& e) {
    SAUtils::LogError(context_, "Compliance report error: " + std::string(e.what()));
    std::string error = SAUtils::CreateErrorResponse(500, "Internal server error");
    OrthancPluginAnswerBuffer(context_, output, error.c_str(), error.length(), "application/json");
    return OrthancPluginErrorCode_Success;
  }
}

extern "C" {
  ORTHANC_PLUGINS_API int32_t OrthancPluginInitialize(OrthancPluginContext* context) {
    context_ = context;
    g_SAPluginContext = context;

    // Log plugin initialization
    SAUtils::LogInfo(context, "Initializing SA Compliance Plugin v1.0.0");

    // Initialize database extension
    database_ = new SADatabaseExtension(context);
    if (!database_->InitializeSATables()) {
      SAUtils::LogError(context, "Failed to initialize SA database tables");
      return -1;
    }

    // Initialize audit logger
    audit_logger_ = std::make_unique<SACompliance::SAAuditLogger>();

    // Initialize HPCSA validator
    hpcsa_validator_ = std::make_unique<SACompliance::HPCSAValidator>();

    // Initialize POPIA compliance
    popia_compliance_ = std::make_unique<SACompliance::POPIACompliance>();

    // Register DICOM instance callback
    OrthancPluginRegisterOnStoredInstanceCallback(context, OnStoredInstance);

    // Register REST endpoints
    OrthancPluginRegisterRestCallback(context, "/sa/compliance/hpcsa/validate", ValidateHPCSA);
    OrthancPluginRegisterRestCallback(context, "/sa/compliance/popia/check", CheckPOPIACompliance);
    OrthancPluginRegisterRestCallback(context, "/sa/compliance/report", GetComplianceReport);

    SAUtils::LogInfo(context, "SA Compliance Plugin initialized successfully");
    SAUtils::LogInfo(context, "Available endpoints:");
    SAUtils::LogInfo(context, "  POST /sa/compliance/hpcsa/validate - Validate HPCSA number");
    SAUtils::LogInfo(context, "  POST /sa/compliance/popia/check - Check POPIA compliance");
    SAUtils::LogInfo(context, "  GET /sa/compliance/report - Generate compliance report");
    
    return 0;
  }

  ORTHANC_PLUGINS_API void OrthancPluginFinalize() {
    SAUtils::LogInfo(context_, "Finalizing SA Compliance Plugin");
    
    // Clean up smart pointers (automatic cleanup)
    popia_compliance_.reset();
    hpcsa_validator_.reset();
    audit_logger_.reset();
    
    if (database_) {
      delete database_;
      database_ = nullptr;
    }
  }

  ORTHANC_PLUGINS_API const char* OrthancPluginGetName() {
    return "SA Compliance";
  }

  ORTHANC_PLUGINS_API const char* OrthancPluginGetVersion() {
    return "1.0.0";
  }
}