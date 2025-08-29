#include "HPCSAValidator.h"
#include "../common/SACommon.h"
#include <regex>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <ctime>

namespace SACompliance {

    // Static data initialization
    const std::map<std::string, std::string> HPCSAValidator::VALID_CATEGORIES = {
        {"MP", "Medical Practitioner"},
        {"DP", "Dental Practitioner"},
        {"PS", "Psychology"},
        {"DT", "Dental Therapy"},
        {"OH", "Oral Hygiene"},
        {"EM", "Emergency Medical Care"},
        {"OT", "Occupational Therapy"},
        {"PT", "Physiotherapy"},
        {"PO", "Podiatry"},
        {"OP", "Optometry"},
        {"SP", "Speech-Language Pathology"},
        {"AU", "Audiology"}
    };

    const std::map<std::string, std::string> HPCSAValidator::PROVINCE_CODES = {
        {"GP", "Gauteng"},
        {"WC", "Western Cape"},
        {"KZN", "KwaZulu-Natal"},
        {"EC", "Eastern Cape"},
        {"FS", "Free State"},
        {"LP", "Limpopo"},
        {"MP", "Mpumalanga"},
        {"NC", "Northern Cape"},
        {"NW", "North West"}
    };

    const std::vector<std::string> HPCSAValidator::REQUIRED_PERMISSIONS = {
        "DICOM_ACCESS",
        "PATIENT_VIEW",
        "PATIENT_EDIT",
        "REPORT_GENERATE",
        "STUDY_DOWNLOAD"
    };

    HPCSAValidator::HPCSAValidator() : context_(nullptr) {
        // Initialize with Orthanc context if available
        context_ = OrthancPlugins::GetGlobalContext();
    }

    HPCSAValidator::~HPCSAValidator() {
        // Cleanup if needed
    }

    HPCSAValidator::ValidationResult HPCSAValidator::validateFormat(const std::string& hpcsaNumber) {
        ValidationResult result;
        result.isValid = false;
        result.errorMessage = "";

        // Clean and format the input
        std::string cleanNumber = HPCSAUtils::formatHPCSANumber(hpcsaNumber);
        
        if (cleanNumber.empty()) {
            result.errorMessage = "HPCSA number cannot be empty";
            return result;
        }

        // Check basic format: 2-3 letter prefix + 6 digits
        std::regex hpcsaPattern(R"(^([A-Z]{2,3})(\d{6})$)");
        std::smatch matches;

        if (!std::regex_match(cleanNumber, matches, hpcsaPattern)) {
            result.errorMessage = "Invalid HPCSA number format. Expected format: XX123456 (2-3 letters + 6 digits)";
            return result;
        }

        std::string category = matches[1].str();
        std::string number = matches[2].str();

        // Validate category
        if (VALID_CATEGORIES.find(category) == VALID_CATEGORIES.end()) {
            result.errorMessage = "Invalid HPCSA category: " + category;
            return result;
        }

        // Store parsed components
        result.category = category;
        result.prefix = category;
        result.number = number;
        result.isValid = true;

        return result;
    }

    HPCSAValidator::ValidationResult HPCSAValidator::validateAgainstDatabase(const std::string& hpcsaNumber) {
        ValidationResult result;
        result.isValid = false;

        // First validate format
        ValidationResult formatResult = validateFormat(hpcsaNumber);
        if (!formatResult.isValid) {
            return formatResult;
        }

        std::string cleanNumber = HPCSAUtils::formatHPCSANumber(hpcsaNumber);

        // Query database for professional
        std::string query = R"(
            SELECT hp.*, hc.category_name, sp.province_name 
            FROM sa_healthcare_professionals hp
            LEFT JOIN sa_hpcsa_categories hc ON hp.registration_category = hc.category_code
            LEFT JOIN sa_provinces sp ON hp.province_code = sp.province_code
            WHERE hp.hpcsa_number = ')" + cleanNumber + R"(' 
            AND hp.is_active = TRUE
        )";

        std::vector<std::map<std::string, std::string>> queryResults;
        if (!executeDatabaseQuery(query, queryResults)) {
            result.errorMessage = "Database query failed";
            return result;
        }

        if (queryResults.empty()) {
            result.errorMessage = "HPCSA number not found in database";
            return result;
        }

        auto& professional = queryResults[0];
        
        // Check registration status
        std::string status = professional["registration_status"];
        if (status != "ACTIVE") {
            result.errorMessage = "HPCSA registration is " + status;
            return result;
        }

        result.isValid = true;
        result.category = professional["registration_category"];
        result.prefix = professional["registration_category"];
        
        return result;
    }

    HPCSAValidator::ProfessionalInfo HPCSAValidator::getProfessionalInfo(const std::string& hpcsaNumber) {
        ProfessionalInfo info;
        info.hpcsaNumber = hpcsaNumber;
        info.isVerified = false;

        std::string cleanNumber = HPCSAUtils::formatHPCSANumber(hpcsaNumber);
        
        std::string query = R"(
            SELECT 
                hp.*,
                hc.category_name,
                sp.province_name,
                ms.specialization_name
            FROM sa_healthcare_professionals hp
            LEFT JOIN sa_hpcsa_categories hc ON hp.registration_category = hc.category_code
            LEFT JOIN sa_provinces sp ON hp.province_code = sp.province_code
            LEFT JOIN sa_medical_specializations ms ON hp.specialization = ms.specialization_code
            WHERE hp.hpcsa_number = ')" + cleanNumber + R"('
        )";

        std::vector<std::map<std::string, std::string>> results;
        if (executeDatabaseQuery(query, results) && !results.empty()) {
            auto& row = results[0];
            info.firstName = row["first_name"];
            info.lastName = row["last_name"];
            info.category = row["category_name"];
            info.specialization = row["specialization_name"];
            info.province = row["province_name"];
            info.registrationStatus = row["registration_status"];
            info.isVerified = (row["hpcsa_verified"] == "1" || row["hpcsa_verified"] == "true");
            info.verificationDate = row["hpcsa_verified_date"];
        }

        return info;
    }

    HPCSAValidator::ValidationResult HPCSAValidator::registerProfessional(const ProfessionalInfo& professionalInfo) {
        ValidationResult result;
        result.isValid = false;

        // Validate HPCSA number format first
        ValidationResult formatResult = validateFormat(professionalInfo.hpcsaNumber);
        if (!formatResult.isValid) {
            return formatResult;
        }

        // Check if already exists
        std::string checkQuery = "SELECT id FROM sa_healthcare_professionals WHERE hpcsa_number = '" + 
                                professionalInfo.hpcsaNumber + "'";
        
        std::vector<std::map<std::string, std::string>> existingResults;
        if (executeDatabaseQuery(checkQuery, existingResults) && !existingResults.empty()) {
            result.errorMessage = "HPCSA number already registered";
            return result;
        }

        // Insert new professional
        std::stringstream insertQuery;
        insertQuery << "INSERT INTO sa_healthcare_professionals ("
                   << "hpcsa_number, first_name, last_name, registration_category, "
                   << "specialization, province_code, registration_status, "
                   << "created_at, is_active) VALUES ("
                   << "'" << professionalInfo.hpcsaNumber << "', "
                   << "'" << professionalInfo.firstName << "', "
                   << "'" << professionalInfo.lastName << "', "
                   << "'" << formatResult.category << "', "
                   << "'" << professionalInfo.specialization << "', "
                   << "'" << professionalInfo.province << "', "
                   << "'ACTIVE', "
                   << "NOW(), "
                   << "TRUE)";

        if (executeDatabaseUpdate(insertQuery.str())) {
            result.isValid = true;
            
            // Log the registration
            logValidation(professionalInfo.hpcsaNumber, "REGISTERED", 
                         "New professional registered: " + professionalInfo.firstName + " " + professionalInfo.lastName);
        } else {
            result.errorMessage = "Failed to register professional in database";
        }

        return result;
    }

    bool HPCSAValidator::updateVerificationStatus(const std::string& hpcsaNumber, 
                                                bool isVerified, 
                                                const std::string& verificationDetails) {
        std::string cleanNumber = HPCSAUtils::formatHPCSANumber(hpcsaNumber);
        
        // Update professional record
        std::stringstream updateQuery;
        updateQuery << "UPDATE sa_healthcare_professionals SET "
                   << "hpcsa_verified = " << (isVerified ? "TRUE" : "FALSE") << ", "
                   << "hpcsa_verified_date = " << (isVerified ? "NOW()" : "NULL") << ", "
                   << "updated_at = NOW() "
                   << "WHERE hpcsa_number = '" << cleanNumber << "'";

        bool updateSuccess = executeDatabaseUpdate(updateQuery.str());

        if (updateSuccess) {
            // Log verification attempt
            std::stringstream logQuery;
            logQuery << "INSERT INTO sa_hpcsa_verification_log ("
                    << "professional_id, hpcsa_number, verification_type, "
                    << "verification_status, verification_details, verification_date) "
                    << "SELECT id, '" << cleanNumber << "', 'MANUAL', "
                    << "'" << (isVerified ? "SUCCESS" : "FAILED") << "', "
                    << "'" << verificationDetails << "', NOW() "
                    << "FROM sa_healthcare_professionals "
                    << "WHERE hpcsa_number = '" << cleanNumber << "'";

            executeDatabaseUpdate(logQuery.str());
        }

        return updateSuccess;
    }

    std::map<std::string, std::string> HPCSAValidator::getValidCategories() {
        return VALID_CATEGORIES;
    }

    std::map<std::string, std::string> HPCSAValidator::getValidProvinces() {
        return PROVINCE_CODES;
    }

    std::map<std::string, std::string> HPCSAValidator::getSpecializations(const std::string& categoryCode) {
        std::map<std::string, std::string> specializations;
        
        std::string query = "SELECT specialization_code, specialization_name "
                           "FROM sa_medical_specializations "
                           "WHERE category_code = '" + categoryCode + "' AND is_active = TRUE";

        std::vector<std::map<std::string, std::string>> results;
        if (executeDatabaseQuery(query, results)) {
            for (const auto& row : results) {
                specializations[row.at("specialization_code")] = row.at("specialization_name");
            }
        }

        return specializations;
    }

    HPCSAValidator::ValidationResult HPCSAValidator::verifyWithExternalService(const std::string& hpcsaNumber) {
        ValidationResult result;
        result.isValid = false;
        
        // For now, this is a placeholder for external HPCSA verification
        // In a real implementation, this would call the HPCSA web service
        
        std::string cleanNumber = HPCSAUtils::formatHPCSANumber(hpcsaNumber);
        
        // Log the external verification attempt
        logValidation(cleanNumber, "EXTERNAL_VERIFY_ATTEMPTED", 
                     "External verification service called");
        
        // Simulate external service response (replace with actual implementation)
        result.errorMessage = "External verification service not implemented";
        
        return result;
    }

    bool HPCSAValidator::hasPermission(const std::string& hpcsaNumber, const std::string& permissionType) {
        std::string cleanNumber = HPCSAUtils::formatHPCSANumber(hpcsaNumber);
        
        std::string query = R"(
            SELECT pp.* FROM sa_practice_permissions pp
            JOIN sa_healthcare_professionals hp ON pp.professional_id = hp.id
            WHERE hp.hpcsa_number = ')" + cleanNumber + R"('
            AND pp.permission_type = ')" + permissionType + R"('
            AND pp.is_active = TRUE
            AND (pp.expires_date IS NULL OR pp.expires_date > NOW())
        )";

        std::vector<std::map<std::string, std::string>> results;
        return executeDatabaseQuery(query, results) && !results.empty();
    }

    bool HPCSAValidator::grantPermission(const std::string& hpcsaNumber, 
                                       const std::string& permissionType,
                                       int grantedBy,
                                       const std::string& expiresDate) {
        std::string cleanNumber = HPCSAUtils::formatHPCSANumber(hpcsaNumber);
        
        std::stringstream query;
        query << "INSERT INTO sa_practice_permissions ("
              << "professional_id, permission_type, granted_by, granted_date";
        
        if (!expiresDate.empty()) {
            query << ", expires_date";
        }
        
        query << ") SELECT id, '" << permissionType << "', " << grantedBy << ", NOW()";
        
        if (!expiresDate.empty()) {
            query << ", '" << expiresDate << "'";
        }
        
        query << " FROM sa_healthcare_professionals WHERE hpcsa_number = '" << cleanNumber << "'";

        return executeDatabaseUpdate(query.str());
    }

    std::vector<std::map<std::string, std::string>> HPCSAValidator::getVerificationHistory(const std::string& hpcsaNumber) {
        std::string cleanNumber = HPCSAUtils::formatHPCSANumber(hpcsaNumber);
        
        std::string query = R"(
            SELECT hvl.*, hp.first_name, hp.last_name
            FROM sa_hpcsa_verification_log hvl
            JOIN sa_healthcare_professionals hp ON hvl.professional_id = hp.id
            WHERE hvl.hpcsa_number = ')" + cleanNumber + R"('
            ORDER BY hvl.verification_date DESC
            LIMIT 50
        )";

        std::vector<std::map<std::string, std::string>> results;
        executeDatabaseQuery(query, results);
        return results;
    }

    // Private methods implementation
    bool HPCSAValidator::isValidFormat(const std::string& hpcsaNumber) {
        return validateFormat(hpcsaNumber).isValid;
    }

    bool HPCSAValidator::isValidCategory(const std::string& category) {
        return VALID_CATEGORIES.find(category) != VALID_CATEGORIES.end();
    }

    std::string HPCSAValidator::extractCategory(const std::string& hpcsaNumber) {
        std::regex pattern(R"(^([A-Z]{2,3})\d{6}$)");
        std::smatch matches;
        if (std::regex_match(hpcsaNumber, matches, pattern)) {
            return matches[1].str();
        }
        return "";
    }

    std::string HPCSAValidator::extractNumber(const std::string& hpcsaNumber) {
        std::regex pattern(R"(^[A-Z]{2,3}(\d{6})$)");
        std::smatch matches;
        if (std::regex_match(hpcsaNumber, matches, pattern)) {
            return matches[1].str();
        }
        return "";
    }

    bool HPCSAValidator::executeDatabaseQuery(const std::string& query, 
                                            std::vector<std::map<std::string, std::string>>& results) {
        // This would use the SADatabaseFactory to execute queries
        // For now, return false to indicate not implemented
        if (context_) {
            OrthancPluginLogInfo(context_, ("HPCSA Query: " + query).c_str());
        }
        return false; // Placeholder - implement with actual database connection
    }

    bool HPCSAValidator::executeDatabaseUpdate(const std::string& query) {
        // This would use the SADatabaseFactory to execute updates
        // For now, return false to indicate not implemented
        if (context_) {
            OrthancPluginLogInfo(context_, ("HPCSA Update: " + query).c_str());
        }
        return false; // Placeholder - implement with actual database connection
    }

    void HPCSAValidator::logValidation(const std::string& hpcsaNumber, 
                                     const std::string& result, 
                                     const std::string& details) {
        if (context_) {
            std::string logMessage = "HPCSA Validation - Number: " + hpcsaNumber + 
                                   ", Result: " + result + ", Details: " + details;
            OrthancPluginLogInfo(context_, logMessage.c_str());
        }
    }

    // Utility functions implementation
    namespace HPCSAUtils {
        std::string formatHPCSANumber(const std::string& input) {
            std::string result = input;
            
            // Remove whitespace and convert to uppercase
            result.erase(std::remove_if(result.begin(), result.end(), ::isspace), result.end());
            std::transform(result.begin(), result.end(), result.begin(), ::toupper);
            
            // Remove any non-alphanumeric characters
            result.erase(std::remove_if(result.begin(), result.end(), 
                        [](char c) { return !std::isalnum(c); }), result.end());
            
            return result;
        }

        std::string extractNumericPart(const std::string& hpcsaNumber) {
            std::regex pattern(R"([A-Z]{2,3}(\d{6}))");
            std::smatch matches;
            if (std::regex_match(hpcsaNumber, matches, pattern)) {
                return matches[1].str();
            }
            return "";
        }

        bool isValidSAIdNumber(const std::string& idNumber) {
            // Use the SA ID validation from SACommon
            return SACommon::isValidSAIdNumber(idNumber);
        }

        std::string generateVerificationToken(const std::string& hpcsaNumber, 
                                            const std::string& timestamp) {
            // Simple token generation for external API calls
            std::string combined = hpcsaNumber + timestamp + "HPCSA_VERIFY";
            
            // In a real implementation, use proper cryptographic hashing
            std::hash<std::string> hasher;
            size_t hashValue = hasher(combined);
            
            std::stringstream ss;
            ss << std::hex << hashValue;
            return ss.str();
        }
    }

} // namespace SACompliance