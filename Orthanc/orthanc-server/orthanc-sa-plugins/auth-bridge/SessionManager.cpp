#include "SessionManager.h"
#include <random>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <mutex>

namespace SAAuth {

    SessionManager::SessionManager() 
        : context_(nullptr), sessionTimeoutMinutes_(30), singleSessionMode_(false) {
    }

    SessionManager::~SessionManager() {
        std::lock_guard<std::mutex> lock(sessionsMutex_);
        sessions_.clear();
    }

    std::string SessionManager::generateSessionToken() {
        // Generate cryptographically secure random token
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_int_distribution<> dis(0, 255);
        
        std::stringstream ss;
        ss << std::hex;
        
        for (int i = 0; i < 32; ++i) {
            ss << std::setw(2) << std::setfill('0') << dis(gen);
        }
        
        return ss.str();
    }

    std::string SessionManager::createSession(const std::string& username,
                                            const std::string& hpcsaNumber,
                                            const std::string& userRole,
                                            const std::string& ipAddress) {
        std::lock_guard<std::mutex> lock(sessionsMutex_);
        
        // If single session mode, destroy existing sessions for user
        if (singleSessionMode_) {
            auto it = sessions_.begin();
            while (it != sessions_.end()) {
                if (it->second->username == username) {
                    logSessionEvent("SESSION_DESTROYED_SINGLE_MODE", it->first, 
                                  "Destroyed due to single session mode");
                    it = sessions_.erase(it);
                } else {
                    ++it;
                }
            }
        }
        
        // Generate unique session token
        std::string sessionToken;
        do {
            sessionToken = generateSessionToken();
        } while (sessions_.find(sessionToken) != sessions_.end());
        
        // Create session info
        auto session = std::make_shared<SessionInfo>();
        session->sessionToken = sessionToken;
        session->username = username;
        session->hpcsaNumber = hpcsaNumber;
        session->userRole = userRole;
        session->ipAddress = ipAddress;
        session->createdAt = std::chrono::steady_clock::now();
        session->lastActivity = session->createdAt;
        session->isActive = true;
        session->twoFactorVerified = false;
        
        // Store session
        sessions_[sessionToken] = session;
        
        logSessionEvent("SESSION_CREATED", sessionToken, 
                       "User: " + username + ", Role: " + userRole + ", IP: " + ipAddress);
        
        return sessionToken;
    }

    std::shared_ptr<SessionManager::SessionInfo> SessionManager::validateSession(const std::string& sessionToken) {
        std::lock_guard<std::mutex> lock(sessionsMutex_);
        
        auto it = sessions_.find(sessionToken);
        if (it == sessions_.end()) {
            return nullptr;
        }
        
        auto session = it->second;
        
        // Check if session is expired
        if (isSessionExpired(session)) {
            logSessionEvent("SESSION_EXPIRED", sessionToken, "Session expired due to timeout");
            sessions_.erase(it);
            return nullptr;
        }
        
        // Check if session is active
        if (!session->isActive) {
            return nullptr;
        }
        
        return session;
    }

    bool SessionManager::updateActivity(const std::string& sessionToken) {
        std::lock_guard<std::mutex> lock(sessionsMutex_);
        
        auto it = sessions_.find(sessionToken);
        if (it == sessions_.end()) {
            return false;
        }
        
        auto session = it->second;
        if (!session->isActive || isSessionExpired(session)) {
            return false;
        }
        
        session->lastActivity = std::chrono::steady_clock::now();
        return true;
    }

    bool SessionManager::destroySession(const std::string& sessionToken) {
        std::lock_guard<std::mutex> lock(sessionsMutex_);
        
        auto it = sessions_.find(sessionToken);
        if (it == sessions_.end()) {
            return false;
        }
        
        logSessionEvent("SESSION_DESTROYED", sessionToken, "Session manually destroyed");
        sessions_.erase(it);
        return true;
    }

    bool SessionManager::setTwoFactorStatus(const std::string& sessionToken, bool verified) {
        std::lock_guard<std::mutex> lock(sessionsMutex_);
        
        auto it = sessions_.find(sessionToken);
        if (it == sessions_.end()) {
            return false;
        }
        
        auto session = it->second;
        if (!session->isActive || isSessionExpired(session)) {
            return false;
        }
        
        session->twoFactorVerified = verified;
        session->lastActivity = std::chrono::steady_clock::now();
        
        logSessionEvent("TWO_FACTOR_STATUS_CHANGED", sessionToken, 
                       verified ? "2FA verified" : "2FA unverified");
        
        return true;
    }

    std::string SessionManager::getSessionMetadata(const std::string& sessionToken, const std::string& key) {
        std::lock_guard<std::mutex> lock(sessionsMutex_);
        
        auto it = sessions_.find(sessionToken);
        if (it == sessions_.end()) {
            return "";
        }
        
        auto session = it->second;
        if (!session->isActive || isSessionExpired(session)) {
            return "";
        }
        
        auto metaIt = session->metadata.find(key);
        return (metaIt != session->metadata.end()) ? metaIt->second : "";
    }

    bool SessionManager::setSessionMetadata(const std::string& sessionToken, 
                                          const std::string& key, 
                                          const std::string& value) {
        std::lock_guard<std::mutex> lock(sessionsMutex_);
        
        auto it = sessions_.find(sessionToken);
        if (it == sessions_.end()) {
            return false;
        }
        
        auto session = it->second;
        if (!session->isActive || isSessionExpired(session)) {
            return false;
        }
        
        session->metadata[key] = value;
        session->lastActivity = std::chrono::steady_clock::now();
        
        return true;
    }

    std::vector<std::string> SessionManager::getUserSessions(const std::string& username) {
        std::lock_guard<std::mutex> lock(sessionsMutex_);
        
        std::vector<std::string> userSessions;
        
        for (const auto& pair : sessions_) {
            if (pair.second->username == username && 
                pair.second->isActive && 
                !isSessionExpired(pair.second)) {
                userSessions.push_back(pair.first);
            }
        }
        
        return userSessions;
    }

    int SessionManager::destroyUserSessions(const std::string& username) {
        std::lock_guard<std::mutex> lock(sessionsMutex_);
        
        int destroyedCount = 0;
        auto it = sessions_.begin();
        
        while (it != sessions_.end()) {
            if (it->second->username == username) {
                logSessionEvent("SESSION_DESTROYED_USER", it->first, 
                               "All user sessions destroyed");
                it = sessions_.erase(it);
                destroyedCount++;
            } else {
                ++it;
            }
        }
        
        return destroyedCount;
    }

    int SessionManager::cleanupExpiredSessions() {
        std::lock_guard<std::mutex> lock(sessionsMutex_);
        
        int cleanedCount = 0;
        auto it = sessions_.begin();
        
        while (it != sessions_.end()) {
            if (isSessionExpired(it->second)) {
                logSessionEvent("SESSION_CLEANUP", it->first, "Expired session cleaned up");
                it = sessions_.erase(it);
                cleanedCount++;
            } else {
                ++it;
            }
        }
        
        return cleanedCount;
    }

    std::map<std::string, int> SessionManager::getSessionStatistics() {
        std::lock_guard<std::mutex> lock(sessionsMutex_);
        
        std::map<std::string, int> stats;
        stats["total_sessions"] = sessions_.size();
        stats["active_sessions"] = 0;
        stats["expired_sessions"] = 0;
        stats["two_factor_verified"] = 0;
        
        for (const auto& pair : sessions_) {
            if (isSessionExpired(pair.second)) {
                stats["expired_sessions"]++;
            } else if (pair.second->isActive) {
                stats["active_sessions"]++;
                if (pair.second->twoFactorVerified) {
                    stats["two_factor_verified"]++;
                }
            }
        }
        
        return stats;
    }

    void SessionManager::setSessionTimeout(int timeoutMinutes) {
        sessionTimeoutMinutes_ = timeoutMinutes;
    }

    void SessionManager::setSingleSessionMode(bool enabled) {
        singleSessionMode_ = enabled;
    }

    bool SessionManager::isSessionExpired(const std::shared_ptr<SessionInfo>& session) {
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::minutes>(now - session->lastActivity);
        return elapsed.count() >= sessionTimeoutMinutes_;
    }

    void SessionManager::logSessionEvent(const std::string& event, 
                                       const std::string& sessionToken, 
                                       const std::string& details) {
        // Log to Orthanc logging system if context is available
        if (context_) {
            std::string logMessage = "SA Auth: " + event + " [" + 
                                   sessionToken.substr(0, 8) + "...] " + details;
            OrthancPluginLogInfo(context_, logMessage.c_str());
        }
    }

} // namespace SAAuth