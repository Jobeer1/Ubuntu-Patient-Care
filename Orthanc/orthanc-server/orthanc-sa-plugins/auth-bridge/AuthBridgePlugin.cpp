/**
 * South African Healthcare Integration for Orthanc
 * Authentication Bridge Plugin
 * 
 * This plugin bridges authentication between the existing Flask SA system
 * and Orthanc, providing unified authentication and session management.
 */

#include "../common/SACommon.h"
#include "SessionManager.h"
#include "TwoFactorAuth.h"
#include <orthanc/OrthancCPlugin.h>
#include <json/json.h>
#include <string>
#include <map>

static OrthancPluginContext* context_ = nullptr;
static SessionManager* session_manager_ = nullptr;
static TwoFactorAuth* two_factor_auth_ = nullptr;

// REST API endpoints
static OrthancPluginErrorCode AuthenticateUser(OrthancPluginRestOutput* output,
                                               const char* url,
                                               const OrthancPluginHttpRequest* request) {
  if (request->method != OrthancPluginHttpMethod_Post) {
    OrthancPluginSendHttpStatusCode(context_, output, 405); // Method not allowed
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

    std::string username = request_json.get("username", "").asString();
    std::string password = request_json.get("password", "").asString();
    std::string totp_code = request_json.get("totp_code", "").asString();

    if (username.empty() || password.empty()) {
      std::string error = SAUtils::CreateErrorResponse(400, "Username and password required");
      OrthancPluginAnswerBuffer(context_, output, error.c_str(), error.length(), "application/json");
      return OrthancPluginErrorCode_Success;
    }

    // Authenticate with Flask backend (for now, until fully integrated)
    // TODO: Replace with direct database authentication
    bool auth_success = session_manager_->AuthenticateWithFlaskBackend(username, password);
    
    if (!auth_success) {
      std::string error = SAUtils::CreateErrorResponse(401, "Invalid credentials");
      OrthancPluginAnswerBuffer(context_, output, error.c_str(), error.length(), "application/json");
      return OrthancPluginErrorCode_Success;
    }

    // Check if 2FA is required
    SAUserInfo user_info = session_manager_->GetUserInfo(username);
    if (user_info.is_2fa_enabled && totp_code.empty()) {
      std::string error = SAUtils::CreateErrorResponse(SA_ERROR_2FA_REQUIRED, "2FA code required");
      OrthancPluginAnswerBuffer(context_, output, error.c_str(), error.length(), "application/json");
      return OrthancPluginErrorCode_Success;
    }

    // Validate 2FA if provided
    if (user_info.is_2fa_enabled && !totp_code.empty()) {
      if (!two_factor_auth_->ValidateTOTP(username, totp_code)) {
        std::string error = SAUtils::CreateErrorResponse(401, "Invalid 2FA code");
        OrthancPluginAnswerBuffer(context_, output, error.c_str(), error.length(), "application/json");
        return OrthancPluginErrorCode_Success;
      }
    }

    // Create session
    std::string session_token = session_manager_->CreateSession(user_info);
    
    // Create response
    Json::Value response;
    response["success"] = true;
    response["session_token"] = session_token;
    response["user_info"]["user_id"] = user_info.user_id;
    response["user_info"]["full_name"] = user_info.full_name;
    response["user_info"]["role"] = static_cast<int>(user_info.role);
    response["user_info"]["hpcsa_number"] = user_info.hpcsa_number;
    response["user_info"]["preferred_language"] = SAUtils::GetLanguageCode(user_info.preferred_language);

    Json::StreamWriterBuilder builder;
    std::string response_str = Json::writeString(builder, response);
    
    OrthancPluginAnswerBuffer(context_, output, response_str.c_str(), response_str.length(), "application/json");
    
    SAUtils::LogInfo(context_, "User authenticated successfully: " + username);
    return OrthancPluginErrorCode_Success;

  } catch (const std::exception& e) {
    SAUtils::LogError(context_, "Authentication error: " + std::string(e.what()));
    std::string error = SAUtils::CreateErrorResponse(500, "Internal server error");
    OrthancPluginAnswerBuffer(context_, output, error.c_str(), error.length(), "application/json");
    return OrthancPluginErrorCode_Success;
  }
}

static OrthancPluginErrorCode ValidateSession(OrthancPluginRestOutput* output,
                                              const char* url,
                                              const OrthancPluginHttpRequest* request) {
  if (request->method != OrthancPluginHttpMethod_Post) {
    OrthancPluginSendHttpStatusCode(context_, output, 405);
    return OrthancPluginErrorCode_Success;
  }

  try {
    // Get session token from header or body
    std::string session_token;
    
    // Check Authorization header first
    for (uint32_t i = 0; i < request->headersCount; i++) {
      if (std::string(request->headersKeys[i]) == "Authorization") {
        std::string auth_header = request->headersValues[i];
        if (auth_header.substr(0, 7) == "Bearer ") {
          session_token = auth_header.substr(7);
        }
        break;
      }
    }

    // If not in header, check request body
    if (session_token.empty() && request->bodySize > 0) {
      Json::Value request_json;
      Json::Reader reader;
      if (reader.parse(request->body, request->body + request->bodySize, request_json)) {
        session_token = request_json.get("session_token", "").asString();
      }
    }

    if (session_token.empty()) {
      std::string error = SAUtils::CreateErrorResponse(400, "Session token required");
      OrthancPluginAnswerBuffer(context_, output, error.c_str(), error.length(), "application/json");
      return OrthancPluginErrorCode_Success;
    }

    // Validate session
    SAUserInfo user_info;
    bool valid = session_manager_->ValidateSession(session_token, user_info);
    
    if (!valid) {
      std::string error = SAUtils::CreateErrorResponse(SA_ERROR_SESSION_EXPIRED, "Invalid or expired session");
      OrthancPluginAnswerBuffer(context_, output, error.c_str(), error.length(), "application/json");
      return OrthancPluginErrorCode_Success;
    }

    // Create response
    Json::Value response;
    response["success"] = true;
    response["valid"] = true;
    response["user_info"]["user_id"] = user_info.user_id;
    response["user_info"]["full_name"] = user_info.full_name;
    response["user_info"]["role"] = static_cast<int>(user_info.role);
    response["user_info"]["hpcsa_number"] = user_info.hpcsa_number;

    Json::StreamWriterBuilder builder;
    std::string response_str = Json::writeString(builder, response);
    
    OrthancPluginAnswerBuffer(context_, output, response_str.c_str(), response_str.length(), "application/json");
    return OrthancPluginErrorCode_Success;

  } catch (const std::exception& e) {
    SAUtils::LogError(context_, "Session validation error: " + std::string(e.what()));
    std::string error = SAUtils::CreateErrorResponse(500, "Internal server error");
    OrthancPluginAnswerBuffer(context_, output, error.c_str(), error.length(), "application/json");
    return OrthancPluginErrorCode_Success;
  }
}

static OrthancPluginErrorCode LogoutUser(OrthancPluginRestOutput* output,
                                         const char* url,
                                         const OrthancPluginHttpRequest* request) {
  if (request->method != OrthancPluginHttpMethod_Post) {
    OrthancPluginSendHttpStatusCode(context_, output, 405);
    return OrthancPluginErrorCode_Success;
  }

  try {
    // Get session token
    std::string session_token;
    for (uint32_t i = 0; i < request->headersCount; i++) {
      if (std::string(request->headersKeys[i]) == "Authorization") {
        std::string auth_header = request->headersValues[i];
        if (auth_header.substr(0, 7) == "Bearer ") {
          session_token = auth_header.substr(7);
        }
        break;
      }
    }

    if (!session_token.empty()) {
      session_manager_->InvalidateSession(session_token);
    }

    std::string response = SAUtils::CreateSuccessResponse();
    OrthancPluginAnswerBuffer(context_, output, response.c_str(), response.length(), "application/json");
    
    SAUtils::LogInfo(context_, "User logged out successfully");
    return OrthancPluginErrorCode_Success;

  } catch (const std::exception& e) {
    SAUtils::LogError(context_, "Logout error: " + std::string(e.what()));
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
    SAUtils::LogInfo(context, "Initializing SA Authentication Bridge Plugin v1.0.0");

    // Initialize managers
    session_manager_ = new SessionManager(context);
    two_factor_auth_ = new TwoFactorAuth(context);

    // Register REST endpoints
    OrthancPluginRegisterRestCallback(context, "/sa/auth/login", AuthenticateUser);
    OrthancPluginRegisterRestCallback(context, "/sa/auth/validate", ValidateSession);
    OrthancPluginRegisterRestCallback(context, "/sa/auth/logout", LogoutUser);

    SAUtils::LogInfo(context, "SA Authentication Bridge Plugin initialized successfully");
    return 0;
  }

  ORTHANC_PLUGINS_API void OrthancPluginFinalize() {
    SAUtils::LogInfo(context_, "Finalizing SA Authentication Bridge Plugin");
    
    if (session_manager_) {
      delete session_manager_;
      session_manager_ = nullptr;
    }
    
    if (two_factor_auth_) {
      delete two_factor_auth_;
      two_factor_auth_ = nullptr;
    }
  }

  ORTHANC_PLUGINS_API const char* OrthancPluginGetName() {
    return "SA Authentication Bridge";
  }

  ORTHANC_PLUGINS_API const char* OrthancPluginGetVersion() {
    return "1.0.0";
  }
}