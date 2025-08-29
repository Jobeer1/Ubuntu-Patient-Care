/**
 * South African Healthcare Integration for Orthanc
 * Two-Factor Authentication Implementation
 */

#include "TwoFactorAuth.h"
#include <random>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <openssl/hmac.h>
#include <openssl/sha.h>
#include <ctime>

TwoFactorAuth::TwoFactorAuth(OrthancPluginContext* context) : context_(context) {
  LoadUserTOTPInfo();
  SAUtils::LogInfo(context_, "TwoFactorAuth initialized");
}

TwoFactorAuth::~TwoFactorAuth() {
  SaveUserTOTPInfo();
  SAUtils::LogInfo(context_, "TwoFactorAuth destroyed");
}

std::string TwoFactorAuth::GenerateSecretKey() {
  // Generate 20-byte (160-bit) secret key
  std::random_device rd;
  std::mt19937 gen(rd());
  std::uniform_int_distribution<> dis(0, 255);
  
  std::string secret;
  secret.reserve(20);
  for (int i = 0; i < 20; ++i) {
    secret += static_cast<char>(dis(gen));
  }
  
  return Base32Encode(secret);
}

std::vector<std::string> TwoFactorAuth::GenerateBackupCodes(int count) {
  std::vector<std::string> codes;
  std::random_device rd;
  std::mt19937 gen(rd());
  std::uniform_int_distribution<> dis(100000, 999999);
  
  for (int i = 0; i < count; ++i) {
    codes.push_back(std::to_string(dis(gen)));
  }
  
  return codes;
}

uint64_t TwoFactorAuth::GetCurrentTimestamp() {
  return static_cast<uint64_t>(std::time(nullptr)) / TOTP_PERIOD;
}

uint32_t TwoFactorAuth::GenerateTOTPCode(const std::string& secret, uint64_t timestamp) {
  // Decode base32 secret
  std::string decoded_secret = Base32Decode(secret);
  
  // Convert timestamp to 8-byte big-endian
  std::string timestamp_bytes;
  timestamp_bytes.reserve(8);
  for (int i = 7; i >= 0; --i) {
    timestamp_bytes += static_cast<char>((timestamp >> (i * 8)) & 0xFF);
  }
  
  // Calculate HMAC-SHA1
  std::string hmac = HMACSHA1(decoded_secret, timestamp_bytes);
  
  // Dynamic truncation
  int offset = hmac.back() & 0x0F;
  uint32_t code = ((hmac[offset] & 0x7F) << 24) |
                  ((hmac[offset + 1] & 0xFF) << 16) |
                  ((hmac[offset + 2] & 0xFF) << 8) |
                  (hmac[offset + 3] & 0xFF);
  
  // Return 6-digit code
  return code % 1000000;
}

std::string TwoFactorAuth::HMACSHA1(const std::string& key, const std::string& data) {
  unsigned char result[SHA_DIGEST_LENGTH];
  unsigned int result_len;
  
  HMAC(EVP_sha1(), key.c_str(), key.length(),
       reinterpret_cast<const unsigned char*>(data.c_str()), data.length(),
       result, &result_len);
  
  return std::string(reinterpret_cast<char*>(result), result_len);
}

std::string TwoFactorAuth::Base32Encode(const std::string& data) {
  const char* alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  std::string result;
  
  int bits = 0;
  int value = 0;
  
  for (char c : data) {
    value = (value << 8) | (c & 0xFF);
    bits += 8;
    
    while (bits >= 5) {
      result += alphabet[(value >> (bits - 5)) & 0x1F];
      bits -= 5;
    }
  }
  
  if (bits > 0) {
    result += alphabet[(value << (5 - bits)) & 0x1F];
  }
  
  return result;
}

std::string TwoFactorAuth::Base32Decode(const std::string& encoded) {
  const char* alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  std::string result;
  
  int bits = 0;
  int value = 0;
  
  for (char c : encoded) {
    if (c == '=') break; // Padding
    
    const char* pos = std::strchr(alphabet, std::toupper(c));
    if (!pos) continue; // Invalid character
    
    value = (value << 5) | (pos - alphabet);
    bits += 5;
    
    if (bits >= 8) {
      result += static_cast<char>((value >> (bits - 8)) & 0xFF);
      bits -= 8;
    }
  }
  
  return result;
}

bool TwoFactorAuth::IsUserLockedOut(const std::string& user_id) {
  auto it = user_totp_info_.find(user_id);
  if (it == user_totp_info_.end()) {
    return false;
  }
  
  const TOTPInfo& info = it->second;
  if (info.failed_attempts < MAX_FAILED_ATTEMPTS) {
    return false;
  }
  
  auto now = std::chrono::system_clock::now();
  auto duration = std::chrono::duration_cast<std::chrono::minutes>(now - info.last_failed_attempt);
  
  return duration.count() < LOCKOUT_DURATION_MINUTES;
}

void TwoFactorAuth::RecordFailedAttempt(const std::string& user_id) {
  auto& info = user_totp_info_[user_id];
  info.failed_attempts++;
  info.last_failed_attempt = std::chrono::system_clock::now();
  
  SAUtils::LogWarning(context_, "Failed 2FA attempt for user: " + user_id + 
                      " (attempt " + std::to_string(info.failed_attempts) + "/" + 
                      std::to_string(MAX_FAILED_ATTEMPTS) + ")");
}

void TwoFactorAuth::ResetFailedAttempts(const std::string& user_id) {
  auto it = user_totp_info_.find(user_id);
  if (it != user_totp_info_.end()) {
    it->second.failed_attempts = 0;
  }
}

std::string TwoFactorAuth::SetupTOTP(const std::string& user_id, const std::string& issuer) {
  TOTPInfo info;
  info.user_id = user_id;
  info.secret_key = GenerateSecretKey();
  info.backup_codes = GenerateBackupCodes();
  info.is_enabled = false; // Will be enabled after verification
  info.failed_attempts = 0;
  
  user_totp_info_[user_id] = info;
  
  SAUtils::LogInfo(context_, "TOTP setup initiated for user: " + user_id);
  return info.secret_key;
}

bool TwoFactorAuth::EnableTOTP(const std::string& user_id, const std::string& verification_code) {
  auto it = user_totp_info_.find(user_id);
  if (it == user_totp_info_.end()) {
    return false;
  }
  
  // Validate the verification code
  if (!ValidateTOTP(user_id, verification_code)) {
    return false;
  }
  
  it->second.is_enabled = true;
  ResetFailedAttempts(user_id);
  
  SAUtils::LogInfo(context_, "TOTP enabled for user: " + user_id);
  return true;
}

bool TwoFactorAuth::DisableTOTP(const std::string& user_id, const std::string& verification_code) {
  auto it = user_totp_info_.find(user_id);
  if (it == user_totp_info_.end() || !it->second.is_enabled) {
    return false;
  }
  
  // Validate the verification code or backup code
  if (!ValidateTOTP(user_id, verification_code) && !ValidateBackupCode(user_id, verification_code)) {
    return false;
  }
  
  it->second.is_enabled = false;
  ResetFailedAttempts(user_id);
  
  SAUtils::LogInfo(context_, "TOTP disabled for user: " + user_id);
  return true;
}

bool TwoFactorAuth::ValidateTOTP(const std::string& user_id, const std::string& code) {
  auto it = user_totp_info_.find(user_id);
  if (it == user_totp_info_.end() || !it->second.is_enabled) {
    return false;
  }
  
  if (IsUserLockedOut(user_id)) {
    SAUtils::LogWarning(context_, "2FA validation blocked - user locked out: " + user_id);
    return false;
  }
  
  const TOTPInfo& info = it->second;
  uint64_t current_timestamp = GetCurrentTimestamp();
  
  // Check current window and adjacent windows
  for (int window = -TOTP_WINDOW_SIZE; window <= TOTP_WINDOW_SIZE; ++window) {
    uint32_t expected_code = GenerateTOTPCode(info.secret_key, current_timestamp + window);
    
    if (std::to_string(expected_code) == code || 
        (expected_code < 100000 && ("0" + std::to_string(expected_code)) == code)) {
      ResetFailedAttempts(user_id);
      SAUtils::LogInfo(context_, "TOTP validation successful for user: " + user_id);
      return true;
    }
  }
  
  RecordFailedAttempt(user_id);
  return false;
}

bool TwoFactorAuth::ValidateBackupCode(const std::string& user_id, const std::string& backup_code) {
  auto it = user_totp_info_.find(user_id);
  if (it == user_totp_info_.end() || !it->second.is_enabled) {
    return false;
  }
  
  if (IsUserLockedOut(user_id)) {
    return false;
  }
  
  TOTPInfo& info = it->second;
  auto code_it = std::find(info.backup_codes.begin(), info.backup_codes.end(), backup_code);
  
  if (code_it != info.backup_codes.end()) {
    // Remove used backup code
    info.backup_codes.erase(code_it);
    ResetFailedAttempts(user_id);
    
    SAUtils::LogInfo(context_, "Backup code validation successful for user: " + user_id);
    return true;
  }
  
  RecordFailedAttempt(user_id);
  return false;
}

bool TwoFactorAuth::IsTOTPEnabled(const std::string& user_id) {
  auto it = user_totp_info_.find(user_id);
  return it != user_totp_info_.end() && it->second.is_enabled;
}

std::string TwoFactorAuth::GetQRCodeURL(const std::string& user_id, const std::string& account_name, const std::string& issuer) {
  auto it = user_totp_info_.find(user_id);
  if (it == user_totp_info_.end()) {
    return "";
  }
  
  std::ostringstream oss;
  oss << "otpauth://totp/" << issuer << ":" << account_name
      << "?secret=" << it->second.secret_key
      << "&issuer=" << issuer
      << "&digits=" << TOTP_DIGITS
      << "&period=" << TOTP_PERIOD;
  
  return oss.str();
}

std::vector<std::string> TwoFactorAuth::GetBackupCodes(const std::string& user_id) {
  auto it = user_totp_info_.find(user_id);
  if (it != user_totp_info_.end()) {
    return it->second.backup_codes;
  }
  return {};
}

std::vector<std::string> TwoFactorAuth::RegenerateBackupCodes(const std::string& user_id) {
  auto it = user_totp_info_.find(user_id);
  if (it != user_totp_info_.end()) {
    it->second.backup_codes = GenerateBackupCodes();
    SAUtils::LogInfo(context_, "Backup codes regenerated for user: " + user_id);
    return it->second.backup_codes;
  }
  return {};
}

void TwoFactorAuth::UnlockUser(const std::string& user_id) {
  ResetFailedAttempts(user_id);
  SAUtils::LogInfo(context_, "User unlocked: " + user_id);
}

int TwoFactorAuth::GetFailedAttempts(const std::string& user_id) const {
  auto it = user_totp_info_.find(user_id);
  return it != user_totp_info_.end() ? it->second.failed_attempts : 0;
}

void TwoFactorAuth::LoadUserTOTPInfo() {
  // TODO: Load from database once database integration is complete
  // For now, this is a placeholder
  SAUtils::LogInfo(context_, "Loading TOTP info from database (placeholder)");
}

void TwoFactorAuth::SaveUserTOTPInfo() {
  // TODO: Save to database once database integration is complete
  // For now, this is a placeholder
  SAUtils::LogInfo(context_, "Saving TOTP info to database (placeholder)");
}