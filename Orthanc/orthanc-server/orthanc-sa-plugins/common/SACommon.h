/**
 * South African Healthcare Integration for Orthanc
 * Common definitions and utilities
 */

#pragma once

#include <orthanc/OrthancCPlugin.h>
#include <string>
#include <vector>
#include <map>

// SA-specific error codes
#define SA_ERROR_HPCSA_INVALID          1000
#define SA_ERROR_POPIA_VIOLATION        1001
#define SA_ERROR_MEDICAL_AID_INVALID    1002
#define SA_ERROR_LANGUAGE_NOT_SUPPORTED 1003
#define SA_ERROR_SESSION_EXPIRED        1004
#define SA_ERROR_2FA_REQUIRED           1005

// SA healthcare roles
enum class SAHealthcareRole {
  RADIOLOGIST,
  REFERRING_DOCTOR,
  SPECIALIST,
  GENERAL_PRACTITIONER,
  RADIOGRAPHER,
  ADMIN,
  VIEWER_ONLY
};

// SA provinces
enum class SAProvince {
  GAUTENG,
  WESTERN_CAPE,
  KWAZULU_NATAL,
  EASTERN_CAPE,
  LIMPOPO,
  MPUMALANGA,
  NORTH_WEST,
  FREE_STATE,
  NORTHERN_CAPE
};

// SA languages
enum class SALanguage {
  ENGLISH,
  AFRIKAANS,
  ISIZULU,
  ISIXHOSA,
  SEPEDI,
  SETSWANA,
  SESOTHO,
  XITSONGA,
  SISWATI,
  TSHIVENDA,
  ISINDEBELE
};

// Common structures
struct SAUserInfo {
  std::string user_id;
  std::string hpcsa_number;
  std::string full_name;
  SAHealthcareRole role;
  SAProvince province;
  SALanguage preferred_language;
  bool is_2fa_enabled;
  bool is_active;
};

struct SAPatientInfo {
  std::string patient_id;
  std::string sa_id_number;
  std::string medical_scheme;
  std::string medical_scheme_number;
  SALanguage preferred_language;
  bool popia_consent;
  std::string consent_date;
};

// Common utility functions
namespace SAUtils {
  bool IsValidSAIDNumber(const std::string& id_number);
  bool IsValidHPCSANumber(const std::string& hpcsa_number);
  std::string GetLanguageCode(SALanguage language);
  SALanguage GetLanguageFromCode(const std::string& code);
  std::string GetProvinceCode(SAProvince province);
  SAProvince GetProvinceFromCode(const std::string& code);
  
  // Logging utilities
  void LogInfo(OrthancPluginContext* context, const std::string& message);
  void LogWarning(OrthancPluginContext* context, const std::string& message);
  void LogError(OrthancPluginContext* context, const std::string& message);
  
  // JSON utilities
  std::string CreateErrorResponse(int error_code, const std::string& message);
  std::string CreateSuccessResponse(const std::string& data = "");
}

// Global plugin context (set by each plugin)
extern OrthancPluginContext* g_SAPluginContext;