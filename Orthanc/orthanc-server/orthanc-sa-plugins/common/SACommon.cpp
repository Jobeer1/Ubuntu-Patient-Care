/**
 * South African Healthcare Integration for Orthanc
 * Common utilities implementation
 */

#include "SACommon.h"
#include <regex>
#include <sstream>
#include <iomanip>

OrthancPluginContext* g_SAPluginContext = nullptr;

namespace SAUtils {

bool IsValidSAIDNumber(const std::string& id_number) {
  // SA ID number validation (13 digits with Luhn algorithm)
  if (id_number.length() != 13) {
    return false;
  }
  
  // Check if all characters are digits
  for (char c : id_number) {
    if (!std::isdigit(c)) {
      return false;
    }
  }
  
  // Luhn algorithm validation
  int sum = 0;
  bool alternate = false;
  
  for (int i = id_number.length() - 1; i >= 0; i--) {
    int digit = id_number[i] - '0';
    
    if (alternate) {
      digit *= 2;
      if (digit > 9) {
        digit = (digit % 10) + 1;
      }
    }
    
    sum += digit;
    alternate = !alternate;
  }
  
  return (sum % 10) == 0;
}

bool IsValidHPCSANumber(const std::string& hpcsa_number) {
  // HPCSA number format: MP followed by 6 digits
  std::regex hpcsa_pattern("^MP\\d{6}$");
  return std::regex_match(hpcsa_number, hpcsa_pattern);
}

std::string GetLanguageCode(SALanguage language) {
  switch (language) {
    case SALanguage::ENGLISH: return "en";
    case SALanguage::AFRIKAANS: return "af";
    case SALanguage::ISIZULU: return "zu";
    case SALanguage::ISIXHOSA: return "xh";
    case SALanguage::SEPEDI: return "nso";
    case SALanguage::SETSWANA: return "tn";
    case SALanguage::SESOTHO: return "st";
    case SALanguage::XITSONGA: return "ts";
    case SALanguage::SISWATI: return "ss";
    case SALanguage::TSHIVENDA: return "ve";
    case SALanguage::ISINDEBELE: return "nr";
    default: return "en";
  }
}

SALanguage GetLanguageFromCode(const std::string& code) {
  if (code == "en") return SALanguage::ENGLISH;
  if (code == "af") return SALanguage::AFRIKAANS;
  if (code == "zu") return SALanguage::ISIZULU;
  if (code == "xh") return SALanguage::ISIXHOSA;
  if (code == "nso") return SALanguage::SEPEDI;
  if (code == "tn") return SALanguage::SETSWANA;
  if (code == "st") return SALanguage::SESOTHO;
  if (code == "ts") return SALanguage::XITSONGA;
  if (code == "ss") return SALanguage::SISWATI;
  if (code == "ve") return SALanguage::TSHIVENDA;
  if (code == "nr") return SALanguage::ISINDEBELE;
  return SALanguage::ENGLISH; // Default
}

std::string GetProvinceCode(SAProvince province) {
  switch (province) {
    case SAProvince::GAUTENG: return "GP";
    case SAProvince::WESTERN_CAPE: return "WC";
    case SAProvince::KWAZULU_NATAL: return "KZN";
    case SAProvince::EASTERN_CAPE: return "EC";
    case SAProvince::LIMPOPO: return "LP";
    case SAProvince::MPUMALANGA: return "MP";
    case SAProvince::NORTH_WEST: return "NW";
    case SAProvince::FREE_STATE: return "FS";
    case SAProvince::NORTHERN_CAPE: return "NC";
    default: return "GP";
  }
}

SAProvince GetProvinceFromCode(const std::string& code) {
  if (code == "GP") return SAProvince::GAUTENG;
  if (code == "WC") return SAProvince::WESTERN_CAPE;
  if (code == "KZN") return SAProvince::KWAZULU_NATAL;
  if (code == "EC") return SAProvince::EASTERN_CAPE;
  if (code == "LP") return SAProvince::LIMPOPO;
  if (code == "MP") return SAProvince::MPUMALANGA;
  if (code == "NW") return SAProvince::NORTH_WEST;
  if (code == "FS") return SAProvince::FREE_STATE;
  if (code == "NC") return SAProvince::NORTHERN_CAPE;
  return SAProvince::GAUTENG; // Default
}

void LogInfo(OrthancPluginContext* context, const std::string& message) {
  if (context) {
    std::string full_message = "[SA-Plugin] INFO: " + message;
    OrthancPluginLogInfo(context, full_message.c_str());
  }
}

void LogWarning(OrthancPluginContext* context, const std::string& message) {
  if (context) {
    std::string full_message = "[SA-Plugin] WARNING: " + message;
    OrthancPluginLogWarning(context, full_message.c_str());
  }
}

void LogError(OrthancPluginContext* context, const std::string& message) {
  if (context) {
    std::string full_message = "[SA-Plugin] ERROR: " + message;
    OrthancPluginLogError(context, full_message.c_str());
  }
}

std::string CreateErrorResponse(int error_code, const std::string& message) {
  std::ostringstream oss;
  oss << "{"
      << "\"success\": false,"
      << "\"error_code\": " << error_code << ","
      << "\"message\": \"" << message << "\""
      << "}";
  return oss.str();
}

std::string CreateSuccessResponse(const std::string& data) {
  std::ostringstream oss;
  oss << "{"
      << "\"success\": true";
  if (!data.empty()) {
    oss << ",\"data\": " << data;
  }
  oss << "}";
  return oss.str();
}

} // namespace SAUtils