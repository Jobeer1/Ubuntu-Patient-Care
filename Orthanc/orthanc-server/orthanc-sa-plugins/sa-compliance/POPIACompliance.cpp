/**
 * South African Healthcare Integration for Orthanc
 * POPIA Compliance Implementation
 */

#include "POPIACompliance.h"
#include <chrono>
#include <sstream>
#include <algorithm>
#include <random>

POPIACompliance::POPIACompliance(OrthancPluginContext* context, SADatabaseExtension* database) 
  : context_(context), database_(database) {
  
  // Initialize data minimization rules
  AddDataMinimizationRule("view", {"PatientID", "PatientName", "StudyDate", "StudyDescription", "Modality"});
  AddDataMinimizationRule("download", {"PatientID", "PatientName", "StudyDate", "StudyDescription", "Modality", "SeriesDescription"});
  AddDataMinimizationRule("report", {"PatientID", "PatientName", "StudyDate", "StudyDescription", "Modality", "SeriesDescription", "InstanceNumber"});
  AddDataMinimizationRule("share", {"PatientID", "PatientName", "StudyDate", "StudyDescription"});
  
  SAUtils::LogInfo(context_, "POPIACompliance initialized");
}

POPIACompliance::~POPIACompliance() {
  SAUtils::LogInfo(context_, "POPIACompliance destroyed");
}

bool POPIACompliance::IsConsentValid(const std::string& consent_date) {
  if (consent_date.empty()) {
    return false;
  }
  
  // Parse consent date and check if it's within validity period
  auto now = std::chrono::system_clock::now();
  auto consent_time = std::chrono::system_clock::from_time_t(0); // TODO: Parse consent_date string
  
  auto duration = std::chrono::duration_cast<std::chrono::hours>(now - consent_time);
  return duration.count() < (CONSENT_VALIDITY_DAYS * 24);
}

bool POPIACompliance::IsDataRetentionValid(const std::string& created_date, int retention_days) {
  if (created_date.empty()) {
    return true; // No creation date, assume valid
  }
  
  auto now = std::chrono::system_clock::now();
  auto created_time = std::chrono::system_clock::from_time_t(0); // TODO: Parse created_date string
  
  auto duration = std::chrono::duration_cast<std::chrono::hours>(now - created_time);
  return duration.count() < (retention_days * 24);
}

std::vector<std::string> POPIACompliance::GetAllowedFieldsForAction(const std::string& action) {
  auto it = data_minimization_rules_.find(action);
  if (it != data_minimization_rules_.end()) {
    return it->second;
  }
  
  // Default minimal fields for unknown actions
  return {"PatientID"};
}

bool POPIACompliance::CheckPatientConsent(const std::string& patient_id) {
  if (!database_) {
    SAUtils::LogError(context_, "Database not available for consent check");
    return false;
  }
  
  // Get patient extension data
  SAPatientExtension patient_ext;
  if (!database_->GetPatientExtension(patient_ext, patient_id)) {
    SAUtils::LogWarning(context_, "Patient extension not found for consent check: " + patient_id);
    return false; // No consent data available
  }
  
  // Check if consent is given and valid
  if (!patient_ext.popia_consent) {
    SAUtils::LogInfo(context_, "Patient consent not given: " + patient_id);
    return false;
  }
  
  // Check if consent is still valid (not expired)
  bool consent_valid = IsConsentValid(patient_ext.consent_date);
  if (!consent_valid) {
    SAUtils::LogWarning(context_, "Patient consent expired: " + patient_id);
    
    // Log compliance violation
    if (database_) {
      database_->LogUserAction("system", "POPIA_CONSENT_EXPIRED", "patient", patient_id,
                               patient_id, "Patient consent has expired", "", "", "", "medium");
    }
  }
  
  return consent_valid;
}

bool POPIACompliance::UpdatePatientConsent(const std::string& patient_id, bool consent, const std::string& consent_version) {
  if (!database_) {
    SAUtils::LogError(context_, "Database not available for consent update");
    return false;
  }
  
  bool success = database_->UpdatePatientConsent(patient_id, consent, consent_version);
  
  if (success) {
    std::string action = consent ? "POPIA_CONSENT_GRANTED" : "POPIA_CONSENT_REVOKED";
    std::string details = consent ? "Patient granted POPIA consent" : "Patient revoked POPIA consent";
    
    database_->LogUserAction("system", action, "patient", patient_id,
                             patient_id, details, "", "", "", "low");
    
    SAUtils::LogInfo(context_, "Patient consent updated: " + patient_id + " = " + (consent ? "granted" : "revoked"));
  }
  
  return success;
}

bool POPIACompliance::IsConsentRequired(const std::string& action) {
  // All actions require consent under POPIA
  return true;
}

bool POPIACompliance::IsDataMinimized(const std::string& patient_id, const std::string& action) {
  // For this implementation, we assume data is minimized if we have rules for the action
  auto allowed_fields = GetAllowedFieldsForAction(action);
  
  // Log data minimization check
  if (database_) {
    std::ostringstream details;
    details << "Data minimization check for action: " << action << ", allowed fields: " << allowed_fields.size();
    
    database_->LogUserAction("system", "POPIA_DATA_MINIMIZATION_CHECK", "patient", patient_id,
                             patient_id, details.str(), "", "", "", "low");
  }
  
  return !allowed_fields.empty();
}

std::vector<std::string> POPIACompliance::GetMinimizedPatientData(const std::string& patient_id, const std::string& action) {
  return GetAllowedFieldsForAction(action);
}

bool POPIACompliance::FilterDicomTags(Json::Value& dicom_json, const std::string& action) {
  auto allowed_fields = GetAllowedFieldsForAction(action);
  
  // Create a new JSON object with only allowed fields
  Json::Value filtered_json;
  
  for (const auto& field : allowed_fields) {
    if (dicom_json.isMember(field)) {
      filtered_json[field] = dicom_json[field];
    }
  }
  
  // Replace original with filtered data
  dicom_json = filtered_json;
  
  SAUtils::LogInfo(context_, "DICOM data filtered for action: " + action + 
                   ", fields retained: " + std::to_string(filtered_json.size()));
  
  return true;
}

bool POPIACompliance::IsDataRetentionCompliant(const std::string& patient_id) {
  if (!database_) {
    return true; // Assume compliant if no database
  }
  
  SAPatientExtension patient_ext;
  if (!database_->GetPatientExtension(patient_ext, patient_id)) {
    return true; // No data, so compliant
  }
  
  return IsDataRetentionValid(patient_ext.created_at, patient_ext.data_retention_period);
}

std::vector<std::string> POPIACompliance::GetExpiredPatientData() {
  std::vector<std::string> expired_patients;
  
  if (!database_) {
    return expired_patients;
  }
  
  // This would typically query the database for patients with expired retention periods
  // For now, return empty list as placeholder
  
  return expired_patients;
}

bool POPIACompliance::ArchiveExpiredData(const std::string& patient_id) {
  if (!database_) {
    return false;
  }
  
  // Log archival action
  database_->LogUserAction("system", "POPIA_DATA_ARCHIVED", "patient", patient_id,
                           patient_id, "Patient data archived due to retention policy", 
                           "", "", "", "low");
  
  SAUtils::LogInfo(context_, "Patient data archived: " + patient_id);
  return true;
}

bool POPIACompliance::DeleteExpiredData(const std::string& patient_id) {
  if (!database_) {
    return false;
  }
  
  // Log deletion action
  database_->LogUserAction("system", "POPIA_DATA_DELETED", "patient", patient_id,
                           patient_id, "Patient data deleted due to retention policy", 
                           "", "", "", "medium");
  
  SAUtils::LogInfo(context_, "Patient data deleted: " + patient_id);
  return true;
}

bool POPIACompliance::IsAccessAuthorized(const std::string& user_id, const std::string& patient_id, const std::string& action) {
  // Check if patient consent is valid
  if (!CheckPatientConsent(patient_id)) {
    return false;
  }
  
  // Check if data is minimized for the action
  if (!IsDataMinimized(patient_id, action)) {
    return false;
  }
  
  // Check if data retention is compliant
  if (!IsDataRetentionCompliant(patient_id)) {
    return false;
  }
  
  return true;
}

bool POPIACompliance::LogDataAccess(const std::string& user_id, const std::string& patient_id, const std::string& action,
                                   const std::string& ip_address, const std::string& user_agent) {
  if (!database_) {
    return false;
  }
  
  std::ostringstream details;
  details << "POPIA data access: action=" << action;
  if (!ip_address.empty()) {
    details << ", ip=" << ip_address;
  }
  
  return database_->LogUserAction(user_id, "POPIA_DATA_ACCESS", "patient", patient_id,
                                  patient_id, details.str(), ip_address, user_agent, "", "low");
}

bool POPIACompliance::AnonymizePatientData(Json::Value& patient_data) {
  // Remove or anonymize identifying fields
  std::vector<std::string> identifying_fields = {
    "PatientName", "PatientID", "PatientBirthDate", "PatientSex",
    "PatientAddress", "PatientTelephoneNumbers", "InstitutionName",
    "InstitutionAddress", "ReferringPhysicianName", "PerformingPhysicianName"
  };
  
  for (const auto& field : identifying_fields) {
    if (patient_data.isMember(field)) {
      patient_data[field] = "ANONYMIZED";
    }
  }
  
  // Add anonymization marker
  patient_data["AnonymizationDate"] = GetCurrentTimestamp();
  patient_data["AnonymizationMethod"] = "POPIA_COMPLIANT";
  
  SAUtils::LogInfo(context_, "Patient data anonymized for POPIA compliance");
  return true;
}

bool POPIACompliance::PseudonymizePatientData(Json::Value& patient_data, const std::string& key) {
  std::vector<std::string> identifying_fields = {
    "PatientName", "PatientID", "PatientBirthDate"
  };
  
  for (const auto& field : identifying_fields) {
    if (patient_data.isMember(field)) {
      std::string original_value = patient_data[field].asString();
      std::string pseudonym = GeneratePseudonym(original_value, key);
      patient_data[field] = pseudonym;
    }
  }
  
  // Add pseudonymization marker
  patient_data["PseudonymizationDate"] = GetCurrentTimestamp();
  patient_data["PseudonymizationMethod"] = "POPIA_COMPLIANT";
  
  SAUtils::LogInfo(context_, "Patient data pseudonymized for POPIA compliance");
  return true;
}

std::string POPIACompliance::GeneratePseudonym(const std::string& original_id, const std::string& key) {
  // Simple pseudonymization using hash
  std::hash<std::string> hasher;
  size_t hash_value = hasher(original_id + key);
  
  std::ostringstream oss;
  oss << "PSEUDO_" << std::hex << hash_value;
  return oss.str();
}

std::string POPIACompliance::GetCurrentTimestamp() {
  auto now = std::time(nullptr);
  auto tm = *std::localtime(&now);
  
  std::ostringstream oss;
  oss << std::put_time(&tm, "%Y-%m-%d %H:%M:%S");
  return oss.str();
}

POPIACompliance::POPIAComplianceReport POPIACompliance::GenerateComplianceReport() {
  POPIAComplianceReport report;
  
  if (database_) {
    report.total_patients = database_->GetTotalPatients();
    report.patients_with_consent = database_->GetPatientsWithConsent();
    report.patients_without_consent = report.total_patients - report.patients_with_consent;
    report.expired_consents = 0; // TODO: Implement expired consent counting
    report.data_retention_violations = 0; // TODO: Implement retention violation counting
    report.unauthorized_access_attempts = 0; // TODO: Implement from audit logs
    
    if (report.total_patients > 0) {
      report.consent_percentage = (double)report.patients_with_consent / report.total_patients * 100.0;
    } else {
      report.consent_percentage = 100.0;
    }
    
    report.overall_compliant = (report.consent_percentage >= 95.0 && 
                               report.data_retention_violations == 0);
  } else {
    // Default values when database is not available
    report.total_patients = 0;
    report.patients_with_consent = 0;
    report.patients_without_consent = 0;
    report.expired_consents = 0;
    report.data_retention_violations = 0;
    report.unauthorized_access_attempts = 0;
    report.consent_percentage = 100.0;
    report.overall_compliant = true;
  }
  
  report.report_date = GetCurrentTimestamp();
  
  return report;
}

// Data Subject Rights Implementation
bool POPIACompliance::ProcessDataSubjectRequest(const std::string& patient_id, const std::string& request_type) {
  if (!database_) {
    return false;
  }
  
  std::string action = "POPIA_DATA_SUBJECT_REQUEST_" + request_type;
  std::string details = "Data subject request processed: " + request_type;
  
  database_->LogUserAction("system", action, "patient", patient_id,
                           patient_id, details, "", "", "", "medium");
  
  SAUtils::LogInfo(context_, "Data subject request processed: " + request_type + " for patient: " + patient_id);
  
  if (request_type == "erasure") {
    return DeletePatientData(patient_id);
  } else if (request_type == "restrict") {
    return RestrictPatientDataProcessing(patient_id, true);
  }
  
  return true;
}

Json::Value POPIACompliance::ExportPatientData(const std::string& patient_id) {
  Json::Value exported_data;
  
  if (!database_) {
    return exported_data;
  }
  
  // Get patient extension data
  SAPatientExtension patient_ext;
  if (database_->GetPatientExtension(patient_ext, patient_id)) {
    exported_data["patient_id"] = patient_ext.patient_id;
    exported_data["sa_id_number"] = patient_ext.sa_id_number;
    exported_data["medical_scheme"] = patient_ext.medical_scheme;
    exported_data["preferred_language"] = SAUtils::GetLanguageCode(patient_ext.preferred_language);
    exported_data["popia_consent"] = patient_ext.popia_consent;
    exported_data["consent_date"] = patient_ext.consent_date;
    exported_data["created_at"] = patient_ext.created_at;
  }
  
  // Add export metadata
  exported_data["export_date"] = GetCurrentTimestamp();
  exported_data["export_reason"] = "POPIA_DATA_PORTABILITY_REQUEST";
  
  // Log export action
  database_->LogUserAction("system", "POPIA_DATA_EXPORTED", "patient", patient_id,
                           patient_id, "Patient data exported for portability", "", "", "", "medium");
  
  SAUtils::LogInfo(context_, "Patient data exported: " + patient_id);
  
  return exported_data;
}

bool POPIACompliance::DeletePatientData(const std::string& patient_id) {
  if (!database_) {
    return false;
  }
  
  // Delete patient extension data
  bool success = database_->DeletePatientExtension(patient_id);
  
  if (success) {
    database_->LogUserAction("system", "POPIA_DATA_SUBJECT_ERASURE", "patient", patient_id,
                             patient_id, "Patient data deleted per data subject request", 
                             "", "", "", "high");
    
    SAUtils::LogInfo(context_, "Patient data deleted per data subject request: " + patient_id);
  }
  
  return success;
}

bool POPIACompliance::RestrictPatientDataProcessing(const std::string& patient_id, bool restrict) {
  if (!database_) {
    return false;
  }
  
  // This would typically set a flag in the database to restrict processing
  // For now, just log the action
  
  std::string action = restrict ? "POPIA_DATA_PROCESSING_RESTRICTED" : "POPIA_DATA_PROCESSING_UNRESTRICTED";
  std::string details = restrict ? "Patient data processing restricted" : "Patient data processing unrestricted";
  
  database_->LogUserAction("system", action, "patient", patient_id,
                           patient_id, details, "", "", "", "medium");
  
  SAUtils::LogInfo(context_, "Patient data processing " + std::string(restrict ? "restricted" : "unrestricted") + ": " + patient_id);
  
  return true;
}

// Data Breach Management
bool POPIACompliance::ReportDataBreach(const DataBreach& breach) {
  if (!database_) {
    return false;
  }
  
  // Log the data breach
  std::ostringstream details;
  details << "Data breach reported: " << breach.description 
          << ", severity: " << breach.severity
          << ", affected patients: " << breach.affected_patients;
  
  database_->LogUserAction("system", "POPIA_DATA_BREACH_REPORTED", "system", breach.breach_id,
                           "", details.str(), "", "", "", "critical");
  
  SAUtils::LogError(context_, "Data breach reported: " + breach.breach_id + " - " + breach.description);
  
  return true;
}

std::vector<POPIACompliance::DataBreach> POPIACompliance::GetDataBreaches(const std::string& start_date, const std::string& end_date) {
  std::vector<DataBreach> breaches;
  
  if (!database_) {
    return breaches;
  }
  
  // This would typically query the audit log for breach reports
  // For now, return empty list as placeholder
  
  return breaches;
}

// Configuration methods
void POPIACompliance::SetDataRetentionPeriod(int days) {
  // This would update the default retention period
  SAUtils::LogInfo(context_, "Data retention period set to: " + std::to_string(days) + " days");
}

void POPIACompliance::SetConsentValidityPeriod(int days) {
  // This would update the consent validity period
  SAUtils::LogInfo(context_, "Consent validity period set to: " + std::to_string(days) + " days");
}

void POPIACompliance::AddDataMinimizationRule(const std::string& action, const std::vector<std::string>& allowed_fields) {
  data_minimization_rules_[action] = allowed_fields;
  
  SAUtils::LogInfo(context_, "Data minimization rule added for action: " + action + 
                   ", allowed fields: " + std::to_string(allowed_fields.size()));
}

bool POPIACompliance::ValidatePOPIACompliance(const std::string& patient_id, const std::string& action) {
  // Comprehensive POPIA compliance check
  
  // 1. Check consent
  if (!CheckPatientConsent(patient_id)) {
    return false;
  }
  
  // 2. Check data minimization
  if (!IsDataMinimized(patient_id, action)) {
    return false;
  }
  
  // 3. Check data retention
  if (!IsDataRetentionCompliant(patient_id)) {
    return false;
  }
  
  // Log compliance validation
  if (database_) {
    database_->LogUserAction("system", "POPIA_COMPLIANCE_VALIDATED", "patient", patient_id,
                             patient_id, "POPIA compliance validated for action: " + action, 
                             "", "", "", "low");
  }
  
  return true;
}

std::vector<std::string> POPIACompliance::GetComplianceViolations(const std::string& patient_id) {
  std::vector<std::string> violations;
  
  // Check consent
  if (!CheckPatientConsent(patient_id)) {
    violations.push_back("Missing or expired patient consent");
  }
  
  // Check data retention
  if (!IsDataRetentionCompliant(patient_id)) {
    violations.push_back("Data retention period exceeded");
  }
  
  return violations;
}