#pragma once

#include <string>
#include <map>
#include <vector>
#include <memory>
#include <chrono>
#include <orthanc/OrthancCPlugin.h>

namespace SACompliance {

    /**
     * SA Audit Logger for HPCSA and POPIA compliance
     * Provides comprehensive audit logging for all system activities
     */
    class SAAuditLogger {
    public:
        enum class EventCategory {
            AUTHENTICATION,
            DICOM,
            PATIENT,
            SYSTEM,
            COMPLIANCE,
            SECURITY,
            ADMIN,
            BACKUP,
            INTEGRATION,
            PERFORMANCE
        };

        enum class EventSeverity {
            INFO,
            WARNING,
            ERROR,
            CRITICAL
        };

        enum class ActionResult {
            SUCCESS,
            FAILED,
            PARTIAL
        };

        struct AuditEvent {
            // Event identification
            std::string eventId;
            std::string eventType;
            EventCategory eventCategory;
            EventSeverity eventSeverity;
            
            // User information
            int userId;
            std::string username;
            std::string hpcsaNumber;
            std::string sessionToken;
            std::string userRole;
            
            // Source information
            std::string sourceIp;
            int sourcePort;
            std::string userAgent;
            std::string clientApplication;
            std::string clientVersion;
            
            // Resource information
            std::string resourceType;
            std::string resourceId;
            std::string resourceName;
            std::string parentResourceId;
            
            // DICOM specific
            std::string patientId;
            std::string studyInstanceUid;
            std::string seriesInstanceUid;
            std::string sopInstanceUid;
            std::string modality;
            std::string studyDate;
            
            // Action details
            std::string actionPerformed;
            ActionResult actionResult;
            std::string actionDetails;
            
            // POPIA compliance
            bool dataSubjectConsent;
            std::string dataProcessingPurpose;
            std::string dataRetentionCategory;
            bool dataMinimizationApplied;
            
            // HPCSA compliance
            std::string professionalContext;
            std::string patientRelationship;
            std::string clinicalJustification;
            
            // Technical information
            std::string requestMethod;
            std::string requestUrl;
            int requestSize;
            int responseCode;
            int responseSize;
            int processingTimeMs;
            
            // Error information
            std::string errorCode;
            std::string errorMessage;
            std::string stackTrace;
            
            // Compliance and security
            std::map<std::string, std::string> complianceFlags;
            std::string securityLevel;
            bool encryptionUsed;
            std::string dataClassification;
            
            // Constructor with defaults
            AuditEvent() : 
                eventCategory(EventCategory::SYSTEM),
                eventSeverity(EventSeverity::INFO),
                userId(0),
                sourcePort(0),
                actionResult(ActionResult::SUCCESS),
                dataSubjectConsent(false),
                dataMinimizationApplied(true),
                requestSize(0),
                responseCode(200),
                responseSize(0),
                processingTimeMs(0),
                encryptionUsed(false),
                securityLevel("STANDARD"),
                dataClassification("INTERNAL") {}
        };

        struct AuditQuery {
            std::string startDate;
            std::string endDate;
            std::vector<EventCategory> categories;
            std::vector<EventSeverity> severities;
            std::string userId;
            std::string hpcsaNumber;
            std::string patientId;
            std::string studyInstanceUid;
            std::string resourceType;
            std::string sourceIp;
            int limit;
            int offset;
            
            AuditQuery() : limit(100), offset(0) {}
        };

        SAAuditLogger();
        ~SAAuditLogger();

        /**
         * Log an audit event
         * @param event The audit event to log
         * @return Success status
         */
        bool logEvent(const AuditEvent& event);

        /**
         * Log authentication event
         * @param username Username attempting authentication
         * @param hpcsaNumber HPCSA number if available
         * @param success Whether authentication succeeded
         * @param sourceIp Source IP address
         * @param details Additional details
         * @return Success status
         */
        bool logAuthentication(const std::string& username,
                             const std::string& hpcsaNumber,
                             bool success,
                             const std::string& sourceIp,
                             const std::string& details = "");

        /**
         * Log DICOM access event
         * @param userId User ID accessing DICOM data
         * @param hpcsaNumber HPCSA number of professional
         * @param studyInstanceUid Study being accessed
         * @param actionPerformed Action performed (VIEW, DOWNLOAD, etc.)
         * @param clinicalJustification Clinical justification for access
         * @param sourceIp Source IP address
         * @return Success status
         */
        bool logDicomAccess(int userId,
                          const std::string& hpcsaNumber,
                          const std::string& studyInstanceUid,
                          const std::string& actionPerformed,
                          const std::string& clinicalJustification,
                          const std::string& sourceIp);

        /**
         * Log patient data access
         * @param userId User ID accessing patient data
         * @param hpcsaNumber HPCSA number of professional
         * @param patientId Patient ID being accessed
         * @param actionPerformed Action performed
         * @param dataProcessingPurpose Purpose for processing
         * @param hasConsent Whether patient consent is verified
         * @param sourceIp Source IP address
         * @return Success status
         */
        bool logPatientAccess(int userId,
                            const std::string& hpcsaNumber,
                            const std::string& patientId,
                            const std::string& actionPerformed,
                            const std::string& dataProcessingPurpose,
                            bool hasConsent,
                            const std::string& sourceIp);

        /**
         * Log system event
         * @param eventType Type of system event
         * @param severity Event severity
         * @param details Event details
         * @param userId User ID if applicable
         * @return Success status
         */
        bool logSystemEvent(const std::string& eventType,
                          EventSeverity severity,
                          const std::string& details,
                          int userId = 0);

        /**
         * Log compliance violation
         * @param violationType Type of violation (HPCSA, POPIA, etc.)
         * @param severity Violation severity
         * @param details Violation details
         * @param userId User ID involved
         * @param hpcsaNumber HPCSA number if applicable
         * @param resourceId Resource involved
         * @return Success status
         */
        bool logComplianceViolation(const std::string& violationType,
                                  EventSeverity severity,
                                  const std::string& details,
                                  int userId,
                                  const std::string& hpcsaNumber = "",
                                  const std::string& resourceId = "");

        /**
         * Log security event
         * @param eventType Type of security event
         * @param severity Event severity
         * @param sourceIp Source IP address
         * @param details Event details
         * @param userId User ID if known
         * @return Success status
         */
        bool logSecurityEvent(const std::string& eventType,
                            EventSeverity severity,
                            const std::string& sourceIp,
                            const std::string& details,
                            int userId = 0);

        /**
         * Query audit logs
         * @param query Query parameters
         * @return Vector of audit events matching query
         */
        std::vector<AuditEvent> queryAuditLogs(const AuditQuery& query);

        /**
         * Get audit summary for date range
         * @param startDate Start date (YYYY-MM-DD)
         * @param endDate End date (YYYY-MM-DD)
         * @param category Optional category filter
         * @return Summary statistics
         */
        std::map<std::string, int> getAuditSummary(const std::string& startDate,
                                                  const std::string& endDate,
                                                  EventCategory category = EventCategory::SYSTEM);

        /**
         * Generate HPCSA compliance report
         * @param startDate Start date for report
         * @param endDate End date for report
         * @param hpcsaNumber Optional HPCSA number filter
         * @return Compliance report data
         */
        std::vector<std::map<std::string, std::string>> generateHPCSAReport(
            const std::string& startDate,
            const std::string& endDate,
            const std::string& hpcsaNumber = "");

        /**
         * Generate POPIA compliance report
         * @param startDate Start date for report
         * @param endDate End date for report
         * @param processingPurpose Optional processing purpose filter
         * @return Compliance report data
         */
        std::vector<std::map<std::string, std::string>> generatePOPIAReport(
            const std::string& startDate,
            const std::string& endDate,
            const std::string& processingPurpose = "");

        /**
         * Archive old audit logs according to retention policy
         * @return Number of records archived
         */
        int archiveOldLogs();

        /**
         * Clean up archived logs according to deletion policy
         * @return Number of records deleted
         */
        int cleanupArchivedLogs();

        /**
         * Get recent critical events
         * @param hours Number of hours to look back
         * @return Vector of critical events
         */
        std::vector<AuditEvent> getRecentCriticalEvents(int hours = 24);

        /**
         * Check if audit logging is healthy
         * @return Health status and details
         */
        std::pair<bool, std::string> checkAuditHealth();

        /**
         * Set context information for subsequent log entries
         * @param key Context key
         * @param value Context value
         */
        void setContext(const std::string& key, const std::string& value);

        /**
         * Clear context information
         */
        void clearContext();

        /**
         * Enable/disable real-time audit monitoring
         * @param enabled Whether to enable monitoring
         */
        void setRealTimeMonitoring(bool enabled);

    private:
        OrthancPluginContext* context_;
        std::map<std::string, std::string> contextData_;
        bool realTimeMonitoring_;
        
        // Internal methods
        std::string generateEventId();
        std::string getCurrentTimestamp();
        std::string eventCategoryToString(EventCategory category);
        std::string eventSeverityToString(EventSeverity severity);
        std::string actionResultToString(ActionResult result);
        EventCategory stringToEventCategory(const std::string& category);
        EventSeverity stringToEventSeverity(const std::string& severity);
        ActionResult stringToActionResult(const std::string& result);
        
        // Database operations
        bool insertAuditEvent(const AuditEvent& event);
        bool executeDatabaseQuery(const std::string& query, 
                                std::vector<std::map<std::string, std::string>>& results);
        bool executeDatabaseUpdate(const std::string& query);
        
        // Validation
        bool validateEvent(const AuditEvent& event);
        bool isValidHPCSANumber(const std::string& hpcsaNumber);
        bool isValidPatientId(const std::string& patientId);
        bool isValidStudyInstanceUid(const std::string& studyInstanceUid);
        
        // Monitoring and alerting
        void checkForCriticalEvents(const AuditEvent& event);
        void sendRealTimeAlert(const AuditEvent& event);
        
        // Performance optimization
        void batchInsertEvents(const std::vector<AuditEvent>& events);
        void updateSummaryStatistics(const AuditEvent& event);
        
        // Utility methods
        std::string sanitizeString(const std::string& input);
        std::string formatJsonString(const std::map<std::string, std::string>& data);
        int calculateProcessingTime(const std::chrono::steady_clock::time_point& start);
    };

    // Utility functions for audit logging
    namespace AuditUtils {
        /**
         * Create audit event from HTTP request
         * @param request HTTP request information
         * @return Partially populated audit event
         */
        SAAuditLogger::AuditEvent createEventFromRequest(
            const std::map<std::string, std::string>& request);

        /**
         * Extract DICOM metadata for audit logging
         * @param dicomData DICOM dataset
         * @return Map of relevant DICOM tags
         */
        std::map<std::string, std::string> extractDicomMetadata(
            const std::string& dicomData);

        /**
         * Determine data classification level
         * @param resourceType Type of resource
         * @param content Resource content
         * @return Data classification level
         */
        std::string determineDataClassification(
            const std::string& resourceType,
            const std::string& content);

        /**
         * Generate compliance flags based on event
         * @param event Audit event
         * @return Map of compliance flags
         */
        std::map<std::string, std::string> generateComplianceFlags(
            const SAAuditLogger::AuditEvent& event);
    }

} // namespace SACompliance