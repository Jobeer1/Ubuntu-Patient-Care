#pragma once

#include <string>
#include <vector>
#include <map>
#include <memory>
#include <orthanc/OrthancCPlugin.h>

namespace SACompliance {

    /**
     * HPCSA (Health Professions Council of South Africa) Number Validator
     * Validates HPCSA registration numbers according to SA healthcare standards
     */
    class HPCSAValidator {
    public:
        struct ValidationResult {
            bool isValid;
            std::string errorMessage;
            std::string category;
            std::string prefix;
            std::string number;
            std::string checkDigit;
        };

        struct ProfessionalInfo {
            std::string hpcsaNumber;
            std::string firstName;
            std::string lastName;
            std::string category;
            std::string specialization;
            std::string province;
            std::string registrationStatus;
            bool isVerified;
            std::string verificationDate;
        };

        HPCSAValidator();
        ~HPCSAValidator();

        /**
         * Validate HPCSA number format and structure
         * @param hpcsaNumber The HPCSA number to validate (e.g., "MP123456")
         * @return ValidationResult with validation status and details
         */
        ValidationResult validateFormat(const std::string& hpcsaNumber);

        /**
         * Validate HPCSA number against database records
         * @param hpcsaNumber The HPCSA number to validate
         * @return ValidationResult with database validation status
         */
        ValidationResult validateAgainstDatabase(const std::string& hpcsaNumber);

        /**
         * Get professional information by HPCSA number
         * @param hpcsaNumber The HPCSA number to lookup
         * @return ProfessionalInfo structure with professional details
         */
        ProfessionalInfo getProfessionalInfo(const std::string& hpcsaNumber);

        /**
         * Register a new healthcare professional
         * @param professionalInfo Professional information to register
         * @return Success status and any error messages
         */
        ValidationResult registerProfessional(const ProfessionalInfo& professionalInfo);

        /**
         * Update professional verification status
         * @param hpcsaNumber HPCSA number to update
         * @param isVerified Verification status
         * @param verificationDetails Additional verification details
         * @return Success status
         */
        bool updateVerificationStatus(const std::string& hpcsaNumber, 
                                    bool isVerified, 
                                    const std::string& verificationDetails = "");

        /**
         * Get list of valid HPCSA categories
         * @return Map of category codes to category names
         */
        std::map<std::string, std::string> getValidCategories();

        /**
         * Get list of valid provinces
         * @return Map of province codes to province names
         */
        std::map<std::string, std::string> getValidProvinces();

        /**
         * Get specializations for a category
         * @param categoryCode The category code (e.g., "MP")
         * @return Map of specialization codes to names
         */
        std::map<std::string, std::string> getSpecializations(const std::string& categoryCode);

        /**
         * Verify HPCSA number with external service (if available)
         * @param hpcsaNumber HPCSA number to verify
         * @return Verification result from external service
         */
        ValidationResult verifyWithExternalService(const std::string& hpcsaNumber);

        /**
         * Check if professional has specific permission
         * @param hpcsaNumber HPCSA number
         * @param permissionType Permission type to check
         * @return True if professional has permission
         */
        bool hasPermission(const std::string& hpcsaNumber, const std::string& permissionType);

        /**
         * Grant permission to professional
         * @param hpcsaNumber HPCSA number
         * @param permissionType Permission type to grant
         * @param grantedBy User ID who granted the permission
         * @param expiresDate Optional expiration date
         * @return Success status
         */
        bool grantPermission(const std::string& hpcsaNumber, 
                           const std::string& permissionType,
                           int grantedBy,
                           const std::string& expiresDate = "");

        /**
         * Get verification history for a professional
         * @param hpcsaNumber HPCSA number
         * @return Vector of verification log entries
         */
        std::vector<std::map<std::string, std::string>> getVerificationHistory(const std::string& hpcsaNumber);

    private:
        OrthancPluginContext* context_;
        
        // Internal validation methods
        bool isValidFormat(const std::string& hpcsaNumber);
        bool isValidCategory(const std::string& category);
        bool isValidCheckDigit(const std::string& hpcsaNumber);
        std::string extractCategory(const std::string& hpcsaNumber);
        std::string extractNumber(const std::string& hpcsaNumber);
        std::string calculateCheckDigit(const std::string& baseNumber);
        
        // Database operations
        bool executeDatabaseQuery(const std::string& query, 
                                std::vector<std::map<std::string, std::string>>& results);
        bool executeDatabaseUpdate(const std::string& query);
        
        // Logging
        void logValidation(const std::string& hpcsaNumber, 
                          const std::string& result, 
                          const std::string& details);
        
        // Static data
        static const std::map<std::string, std::string> VALID_CATEGORIES;
        static const std::map<std::string, std::string> PROVINCE_CODES;
        static const std::vector<std::string> REQUIRED_PERMISSIONS;
    };

    // Utility functions for HPCSA validation
    namespace HPCSAUtils {
        /**
         * Format HPCSA number to standard format
         * @param input Raw HPCSA number input
         * @return Formatted HPCSA number
         */
        std::string formatHPCSANumber(const std::string& input);

        /**
         * Extract numeric part from HPCSA number
         * @param hpcsaNumber Full HPCSA number
         * @return Numeric part only
         */
        std::string extractNumericPart(const std::string& hpcsaNumber);

        /**
         * Validate SA ID number (used for professional registration)
         * @param idNumber 13-digit SA ID number
         * @return True if valid SA ID number
         */
        bool isValidSAIdNumber(const std::string& idNumber);

        /**
         * Generate verification token for external API calls
         * @param hpcsaNumber HPCSA number
         * @param timestamp Current timestamp
         * @return Verification token
         */
        std::string generateVerificationToken(const std::string& hpcsaNumber, 
                                            const std::string& timestamp);
    }

} // namespace SACompliance