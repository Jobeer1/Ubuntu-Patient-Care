/**
 * South African Healthcare Integration for Orthanc
 * Session Manager - Handles user sessions and authentication state
 */

#pragma once

#include "../common/SACommon.h"
#include <orthanc/OrthancCPlugin.h>
#include <string>
#include <map>
#include <chrono>
#include <mutex>

class SessionManager {
public:
  struct SessionInfo {
    std::string session_token;
    SAUserInfo user_info;
    std::chrono::system_clock::time_point created_at;
    std::chrono::system_clock::time_point last_accessed;
    std::string ip_address;
    std::string user_agent;
    bool is_active;
  };

private:
  OrthancPluginContext* context_;
  std::map<std::string, SessionInfo> active_sessions_;
  std::mutex sessions_mutex_;
  
  // Session configuration
  static const int SESSION_TIMEOUT_MINUTES = 30;
  static const int MAX_SESSIONS_PER_USER = 1; // Single session enforcement
  
  // Helper methods
  std::string GenerateSessionToken();
  void CleanupExpiredSessions();
  void InvalidateUserSessions(const std::string& user_id);
  bool IsSessionExpired(const SessionInfo& session);
  
public:
  explicit SessionManager(OrthancPluginContext* context);
  ~SessionManager();
  
  // Authentication methods
  bool AuthenticateWithFlaskBackend(const std::string& username, const std::string& password);
  SAUserInfo GetUserInfo(const std::string& username);
  
  // Session management
  std::string CreateSession(const SAUserInfo& user_info, 
                           const std::string& ip_address = "", 
                           const std::string& user_agent = "");
  bool ValidateSession(const std::string& session_token, SAUserInfo& user_info);
  void InvalidateSession(const std::string& session_token);
  void RefreshSession(const std::string& session_token);
  
  // Session queries
  std::vector<SessionInfo> GetActiveSessions();
  std::vector<SessionInfo> GetUserSessions(const std::string& user_id);
  int GetActiveSessionCount();
  
  // Maintenance
  void PerformMaintenance(); // Called periodically to cleanup
};