/**
 * South African Healthcare Integration for Orthanc
 * Two-Factor Authentication - TOTP and backup codes support
 */

#pragma once

#include "../common/SACommon.h"
#include <orthanc/OrthancCPlugin.h>
#include <string>
#include <vector>
#include <map>

class TwoFactorAuth {
public:
  struct TOTPInfo {
    std::string user_id;
    std::string secret_key;
    std::vector<std::string> backup_codes;
    bool is_enabled;
    int failed_attempts;
    std::chrono::system_clock::time_point last_failed_attempt;
  };

private:
  OrthancPluginContext* context_;
  std::map<std::string, TOTPInfo> user_totp_info_;
  
  // TOTP configuration
  static const int TOTP_WINDOW_SIZE = 1; // Allow 1 window before/after current
  static const int TOTP_DIGITS = 6;
  static const int TOTP_PERIOD = 30; // seconds
  static const int MAX_FAILED_ATTEMPTS = 3;
  static const int LOCKOUT_DURATION_MINUTES = 15;
  
  // Helper methods
  std::string GenerateSecretKey();
  std::vector<std::string> GenerateBackupCodes(int count = 10);
  uint32_t GenerateTOTPCode(const std::string& secret, uint64_t timestamp);
  uint64_t GetCurrentTimestamp();
  bool IsUserLockedOut(const std::string& user_id);
  void RecordFailedAttempt(const std::string& user_id);
  void ResetFailedAttempts(const std::string& user_id);
  
  // Base32 encoding/decoding for TOTP secrets
  std::string Base32Encode(const std::string& data);
  std::string Base32Decode(const std::string& encoded);
  
  // HMAC-SHA1 for TOTP calculation
  std::string HMACSHA1(const std::string& key, const std::string& data);

public:
  explicit TwoFactorAuth(OrthancPluginContext* context);
  ~TwoFactorAuth();
  
  // TOTP setup and management
  std::string SetupTOTP(const std::string& user_id, const std::string& issuer = "Orthanc SA");
  bool EnableTOTP(const std::string& user_id, const std::string& verification_code);
  bool DisableTOTP(const std::string& user_id, const std::string& verification_code);
  
  // TOTP validation
  bool ValidateTOTP(const std::string& user_id, const std::string& code);
  bool ValidateBackupCode(const std::string& user_id, const std::string& backup_code);
  
  // TOTP information
  bool IsTOTPEnabled(const std::string& user_id);
  std::string GetQRCodeURL(const std::string& user_id, const std::string& account_name, const std::string& issuer);
  std::vector<std::string> GetBackupCodes(const std::string& user_id);
  std::vector<std::string> RegenerateBackupCodes(const std::string& user_id);
  
  // Security features
  bool IsUserLockedOut(const std::string& user_id) const;
  int GetFailedAttempts(const std::string& user_id) const;
  void UnlockUser(const std::string& user_id);
  
  // Maintenance
  void LoadUserTOTPInfo(); // Load from database
  void SaveUserTOTPInfo(); // Save to database
};