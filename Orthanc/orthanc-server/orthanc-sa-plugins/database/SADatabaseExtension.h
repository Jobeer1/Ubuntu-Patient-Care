/**
 * South African Healthcare Integration for Orthanc
 * Database Extension - SA-specific database operations
 */

#pragma once

#include "../common/SACommon.h"
#include <orthanc/OrthancCPlugin.h>
#include <string>
#include <vector>
#include <map>

// Forward declarations
struct SAUser;
struct SAHealthcareProfessional;
struct SAPatientExtension;
struct SAReport;
struct SASecureShare;
struct SAAuditLogEntry;

// SA-specific database structures
struct SAUser {
  std::string user_id;
  std::string username;
  std::string password_hash;
  std::string salt;
  std::string full_name;
  std::string email;
  std::string role;
  std::string province;
  SALanguage preferred_language;
  bool is_active;
  std::string created_at;
  std::string last_login;
  int login_attempts;
  std::string locked_until;
};

struct SAHealthcareProfessional {
  std::string id;
  std::string user_id;
  std::string hpcsa_number;
  std::string practice_number;
  std::string practice_name;
  std::string specialization;
  std::string sub_specialization;
  SAProvince province;
  std::string city;
  std::string phone;
  std::string emergency_contact;
  bool is_verified;
  std::string verification_date;
  std::string verification_method;
  std::string license_expiry_date;
  bool is_active;
  std::string created_at;
  std::string updated_at;
};

struct SAPatientExtension {
  std::string patient_id;
  std::string orthanc_patient_id;
  std::string sa_id_number;
  std::string medical_scheme;
  std::string medical_scheme_number;
  std::string scheme_option;
  SALanguage preferred_language;
  std::string traditional_name;
  bool popia_consent;
  std::string consent_date;
  std::string consent_version;
  int data_retention_period;
  std::string created_at;
  std::string updated_at;
};

struct SAReport {
  std::string report_id;
  std::string patient_id;
  std::string study_id;
  std::string series_id;
  std::string template_id;
  std::string template_name;
  std::string content;
  std::string structured_data;
  SALanguage language;
  std::string status;
  std::string created_by;
  std::string reviewed_by;
  std::string signed_by;
  std::string created_at;
  std::string completed_at;
  std::string signed_at;
  int version;
};

struct SASecureShare {
  std::string share_id;
  std::string patient_id;
  std::string study_id;
  std::string series_id;
  std::string share_token;
  std::string share_type;
  std::string password_hash;
  std::string created_by;
  std::string recipient_email;
  std::string recipient_name;
  std::string expires_at;
  int access_count;
  int max_access_count;
  std::string last_accessed;
  std::string last_access_ip;
  bool is_active;
  std::string created_at;
};

struct SAAuditLogEntry {
  std::string audit_id;
  std::string user_id;
  std::string hpcsa_number;
  std::string action;
  std::string resource_type;
  std::string resource_id;
  std::string patient_id;
  std::string details;
  std::string ip_address;
  std::string user_agent;
  std::string session_id;
  std::string compliance_flags;
  std::string risk_level;
  std::string timestamp;
};

/**
 * SA Database Extension Class
 * Provides SA-specific database operations while integrating with Orthanc's database
 */
class SADatabaseExtension {
private:
  OrthancPluginContext* context_;
  std::string database_path_;
  
  // Helper methods
  std::string GenerateUUID();
  std::string GetCurrentTimestamp();
  bool ExecuteSQL(const std::string& sql);
  bool ExecuteSQLWithParams(const std::string& sql, const std::vector<std::string>& params);
  std::vector<std::map<std::string, std::string>> QuerySQL(const std::string& sql, const std::vector<std::string>& params = {});
  
public:
  explicit SADatabaseExtension(OrthancPluginContext* context);
  ~SADatabaseExtension();
  
  // Database initialization
  bool InitializeSATables();
  bool UpgradeSASchema(int from_version, int to_version);
  
  // User management
  bool CreateUser(const SAUser& user);
  bool GetUser(SAUser& user, const std::string& user_id);
  bool GetUserByUsername(SAUser& user, const std::string& username);
  bool UpdateUser(const SAUser& user);
  bool DeleteUser(const std::string& user_id);
  bool SetUserPassword(const std::string& user_id, const std::string& password_hash, const std::string& salt);
  bool UpdateUserLoginAttempts(const std::string& user_id, int attempts, const std::string& locked_until = "");
  std::vector<SAUser> GetAllUsers(bool active_only = true);
  
  // Healthcare professional management
  bool CreateHealthcareProfessional(const SAHealthcareProfessional& professional);
  bool GetHealthcareProfessional(SAHealthcareProfessional& professional, const std::string& id);
  bool GetHealthcareProfessionalByHPCSA(SAHealthcareProfessional& professional, const std::string& hpcsa_number);
  bool UpdateHealthcareProfessional(const SAHealthcareProfessional& professional);
  bool DeleteHealthcareProfessional(const std::string& id);
  bool VerifyHealthcareProfessional(const std::string& id, const std::string& verification_method);
  std::vector<SAHealthcareProfessional> GetHealthcareProfessionalsByProvince(SAProvince province);
  std::vector<SAHealthcareProfessional> GetHealthcareProfessionalsBySpecialization(const std::string& specialization);
  
  // Patient extension management
  bool CreatePatientExtension(const SAPatientExtension& extension);
  bool GetPatientExtension(SAPatientExtension& extension, const std::string& patient_id);
  bool GetPatientExtensionByOrthancId(SAPatientExtension& extension, const std::string& orthanc_patient_id);
  bool GetPatientExtensionBySAId(SAPatientExtension& extension, const std::string& sa_id_number);
  bool UpdatePatientExtension(const SAPatientExtension& extension);
  bool DeletePatientExtension(const std::string& patient_id);
  bool UpdatePatientConsent(const std::string& patient_id, bool consent, const std::string& consent_version);
  std::vector<SAPatientExtension> GetPatientsByMedicalScheme(const std::string& medical_scheme);
  
  // Report management
  bool CreateReport(const SAReport& report);
  bool GetReport(SAReport& report, const std::string& report_id);
  bool UpdateReport(const SAReport& report);
  bool DeleteReport(const std::string& report_id);
  bool SignReport(const std::string& report_id, const std::string& signed_by);
  std::vector<SAReport> GetReportsByPatient(const std::string& patient_id);
  std::vector<SAReport> GetReportsByStudy(const std::string& study_id);
  std::vector<SAReport> GetReportsByCreator(const std::string& created_by);
  
  // Secure share management
  bool CreateSecureShare(const SASecureShare& share);
  bool GetSecureShare(SASecureShare& share, const std::string& share_id);
  bool GetSecureShareByToken(SASecureShare& share, const std::string& share_token);
  bool UpdateSecureShare(const SASecureShare& share);
  bool DeleteSecureShare(const std::string& share_id);
  bool IncrementShareAccess(const std::string& share_token, const std::string& access_ip);
  bool DeactivateExpiredShares();
  std::vector<SASecureShare> GetSecureSharesByCreator(const std::string& created_by);
  std::vector<SASecureShare> GetActiveSecureShares();
  
  // Audit logging
  bool LogAuditEntry(const SAAuditLogEntry& entry);
  bool LogUserAction(const std::string& user_id, const std::string& action, 
                     const std::string& resource_type, const std::string& resource_id,
                     const std::string& patient_id = "", const std::string& details = "",
                     const std::string& ip_address = "", const std::string& user_agent = "",
                     const std::string& session_id = "", const std::string& risk_level = "low");
  std::vector<SAAuditLogEntry> GetAuditLogsByUser(const std::string& user_id, int limit = 100);
  std::vector<SAAuditLogEntry> GetAuditLogsByPatient(const std::string& patient_id, int limit = 100);
  std::vector<SAAuditLogEntry> GetAuditLogsByAction(const std::string& action, int limit = 100);
  std::vector<SAAuditLogEntry> GetAuditLogsByTimeRange(const std::string& start_time, const std::string& end_time);
  
  // Validation methods
  bool ValidateHPCSANumber(const std::string& hpcsa_number);
  bool ValidateSAIdNumber(const std::string& sa_id_number);
  bool ValidateMedicalScheme(const std::string& medical_scheme);
  bool IsHPCSANumberUnique(const std::string& hpcsa_number, const std::string& exclude_id = "");
  bool IsSAIdNumberUnique(const std::string& sa_id_number, const std::string& exclude_patient_id = "");
  
  // Statistics and reporting
  int GetTotalUsers();
  int GetActiveUsers();
  int GetVerifiedHealthcareProfessionals();
  int GetTotalPatients();
  int GetPatientsWithConsent();
  int GetTotalReports();
  int GetActiveSecureShares();
  std::map<std::string, int> GetUsersByRole();
  std::map<std::string, int> GetProfessionalsByProvince();
  std::map<std::string, int> GetPatientsByMedicalScheme();
  
  // Maintenance operations
  bool CleanupExpiredSessions();
  bool CleanupExpiredShares();
  bool ArchiveOldAuditLogs(int days_to_keep = 2555); // 7 years default
  bool OptimizeDatabase();
  bool BackupSAData(const std::string& backup_path);
  bool RestoreSAData(const std::string& backup_path);
};