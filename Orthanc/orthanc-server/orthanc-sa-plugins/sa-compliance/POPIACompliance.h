/**
 * South African Healthcare Integration for Orthanc
 * POPIA Compliance - Protection of Personal Information Act compliance
 */

#pragma once

#include "../common/SACommon.h"
#include "../database/SADatabaseExtension.h"
#include <orthanc/OrthancCPlugin.h>
#include <string>
#include <vector>
#include <map>

class POPIACompliance {
private:
  OrthancPluginContext* context_;
  SADatabaseExtension* database_;
  
  // POPIA configuration
  static const int DEFAULT_RETENTION_DAYS = 2555; // 7 years
  static const int CONSENT_VALIDITY_DAYS = 365; // 1 year
  
  // Data minimization rules
  std::map<std::string, std::vector<std::string>> data_minimization_rules_;
  
  // Helper methods
  bool IsConsentValid(const std::string& consent_date);
  bool IsDataRetentionValid(const std::string& created_date, int retention_days);
  std::vector<std::string> GetAllowedFieldsForAction(const std::string& action);
  
public:
  explicit POPIACompliance(OrthancPluginContext* context, SADatabaseExtension* database);
  ~POPIACompliance();
  
  // Consent management
  bool CheckPatientConsent(const std::string& patient_id);
  bool UpdatePatientConsent(const std::string& patient_id, bool consent, const std::string& consent_version = "1.0");
  bool IsConsentRequired(const std::string& action);
  
  // Data minimization
  bool IsDataMinimized(const std::string& patient_id, const std::string& action);
  std::vector<std::string> GetMinimizedPatientData(const std::string& patient_id, const std::string& action);
  bool FilterDicomTags(Json::Value& dicom_json, const std::string& action);
  
  // Data retention
  bool IsDataRetentionCompliant(const std::string& patient_id);
  std::vector<std::string> GetExpiredPatientData();
  bool ArchiveExpiredData(const std::string& patient_id);
  bool DeleteExpiredData(const std::string& patient_id);
  
  // Access control
  bool IsAccessAuthorized(const std::string& user_id, const std::string& patient_id, const std::string& action);
  bool LogDataAccess(const std::string& user_id, const std::string& patient_id, const std::string& action,
                     const std::string& ip_address = "", const std::string& user_agent = "");
  
  // Privacy by design
  bool AnonymizePatientData(Json::Value& patient_data);
  bool PseudonymizePatientData(Json::Value& patient_data, const std::string& key);
  std::string GeneratePseudonym(const std::string& original_id, const std::string& key);
  
  // Compliance reporting
  struct POPIAComplianceReport {
    int total_patients;
    int patients_with_consent;
    int patients_without_consent;
    int expired_consents;
    int data_retention_violations;
    int unauthorized_access_attempts;
    double consent_percentage;
    bool overall_compliant;
    std::string report_date;
  };
  
  POPIAComplianceReport GenerateComplianceReport();
  
  // Data subject rights (POPIA Chapter 3)
  struct DataSubjectRights {
    bool right_to_access;
    bool right_to_rectification;
    bool right_to_erasure;
    bool right_to_restrict_processing;
    bool right_to_data_portability;
    bool right_to_object;
  };
  
  bool ProcessDataSubjectRequest(const std::string& patient_id, const std::string& request_type);
  Json::Value ExportPatientData(const std::string& patient_id); // Right to data portability
  bool DeletePatientData(const std::string& patient_id); // Right to erasure
  bool RestrictPatientDataProcessing(const std::string& patient_id, bool restrict); // Right to restrict
  
  // Breach notification
  struct DataBreach {
    std::string breach_id;
    std::string description;
    std::string affected_patients;
    std::string breach_date;
    std::string detected_date;
    std::string severity; // low, medium, high, critical
    bool regulator_notified;
    bool patients_notified;
    std::string mitigation_actions;
  };
  
  bool ReportDataBreach(const DataBreach& breach);
  std::vector<DataBreach> GetDataBreaches(const std::string& start_date = "", const std::string& end_date = "");
  
  // Configuration
  void SetDataRetentionPeriod(int days);
  void SetConsentValidityPeriod(int days);
  void AddDataMinimizationRule(const std::string& action, const std::vector<std::string>& allowed_fields);
  
  // Validation
  bool ValidatePOPIACompliance(const std::string& patient_id, const std::string& action);
  std::vector<std::string> GetComplianceViolations(const std::string& patient_id);
};