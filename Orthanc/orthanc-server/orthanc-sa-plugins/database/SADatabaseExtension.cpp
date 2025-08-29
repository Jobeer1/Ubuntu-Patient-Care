/**
 * South African Healthcare Integration for Orthanc
 * Database Extension Implementation
 */

#include "SADatabaseExtension.h"
#include <sqlite3.h>
#include <random>
#include <sstream>
#include <iomanip>
#include <fstream>
#include <ctime>

SADatabaseExtension::SADatabaseExtension(OrthancPluginContext* context) 
  : context_(context) {
  
  // Get database path from Orthanc configuration
  // For now, we'll use the same directory as Orthanc's database
  database_path_ = "OrthancStorage/index"; // This will be the same SQLite file as Orthanc
  
  SAUtils::LogInfo(context_, "SADatabaseExtension initialized with database: " + database_path_);
}

SADatabaseExtension::~SADatabaseExtension() {
  SAUtils::LogInfo(context_, "SADatabaseExtension destroyed");
}

std::string SADatabaseExtension::GenerateUUID() {
  std::random_device rd;
  std::mt19937 gen(rd());
  std::uniform_int_distribution<> dis(0, 15);
  
  std::ostringstream oss;
  oss << std::hex;
  for (int i = 0; i < 32; ++i) {
    if (i == 8 || i == 12 || i == 16 || i == 20) {
      oss << "-";
    }
    oss << dis(gen);
  }
  
  return oss.str();
}

std::string SADatabaseExtension::GetCurrentTimestamp() {
  auto now = std::time(nullptr);
  auto tm = *std::localtime(&now);
  
  std::ostringstream oss;
  oss << std::put_time(&tm, "%Y-%m-%d %H:%M:%S");
  return oss.str();
}

bool SADatabaseExtension::ExecuteSQL(const std::string& sql) {
  sqlite3* db;
  int rc = sqlite3_open(database_path_.c_str(), &db);
  
  if (rc != SQLITE_OK) {
    SAUtils::LogError(context_, "Cannot open database: " + std::string(sqlite3_errmsg(db)));
    sqlite3_close(db);
    return false;
  }
  
  char* error_msg = nullptr;
  rc = sqlite3_exec(db, sql.c_str(), nullptr, nullptr, &error_msg);
  
  if (rc != SQLITE_OK) {
    SAUtils::LogError(context_, "SQL error: " + std::string(error_msg));
    sqlite3_free(error_msg);
    sqlite3_close(db);
    return false;
  }
  
  sqlite3_close(db);
  return true;
}

bool SADatabaseExtension::ExecuteSQLWithParams(const std::string& sql, const std::vector<std::string>& params) {
  sqlite3* db;
  int rc = sqlite3_open(database_path_.c_str(), &db);
  
  if (rc != SQLITE_OK) {
    SAUtils::LogError(context_, "Cannot open database: " + std::string(sqlite3_errmsg(db)));
    sqlite3_close(db);
    return false;
  }
  
  sqlite3_stmt* stmt;
  rc = sqlite3_prepare_v2(db, sql.c_str(), -1, &stmt, nullptr);
  
  if (rc != SQLITE_OK) {
    SAUtils::LogError(context_, "Cannot prepare statement: " + std::string(sqlite3_errmsg(db)));
    sqlite3_close(db);
    return false;
  }
  
  // Bind parameters
  for (size_t i = 0; i < params.size(); ++i) {
    rc = sqlite3_bind_text(stmt, i + 1, params[i].c_str(), -1, SQLITE_STATIC);
    if (rc != SQLITE_OK) {
      SAUtils::LogError(context_, "Cannot bind parameter: " + std::string(sqlite3_errmsg(db)));
      sqlite3_finalize(stmt);
      sqlite3_close(db);
      return false;
    }
  }
  
  rc = sqlite3_step(stmt);
  bool success = (rc == SQLITE_DONE || rc == SQLITE_ROW);
  
  sqlite3_finalize(stmt);
  sqlite3_close(db);
  
  return success;
}

std::vector<std::map<std::string, std::string>> SADatabaseExtension::QuerySQL(const std::string& sql, const std::vector<std::string>& params) {
  std::vector<std::map<std::string, std::string>> results;
  
  sqlite3* db;
  int rc = sqlite3_open(database_path_.c_str(), &db);
  
  if (rc != SQLITE_OK) {
    SAUtils::LogError(context_, "Cannot open database: " + std::string(sqlite3_errmsg(db)));
    sqlite3_close(db);
    return results;
  }
  
  sqlite3_stmt* stmt;
  rc = sqlite3_prepare_v2(db, sql.c_str(), -1, &stmt, nullptr);
  
  if (rc != SQLITE_OK) {
    SAUtils::LogError(context_, "Cannot prepare statement: " + std::string(sqlite3_errmsg(db)));
    sqlite3_close(db);
    return results;
  }
  
  // Bind parameters
  for (size_t i = 0; i < params.size(); ++i) {
    rc = sqlite3_bind_text(stmt, i + 1, params[i].c_str(), -1, SQLITE_STATIC);
    if (rc != SQLITE_OK) {
      SAUtils::LogError(context_, "Cannot bind parameter: " + std::string(sqlite3_errmsg(db)));
      sqlite3_finalize(stmt);
      sqlite3_close(db);
      return results;
    }
  }
  
  // Execute and fetch results
  int column_count = sqlite3_column_count(stmt);
  while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {
    std::map<std::string, std::string> row;
    
    for (int i = 0; i < column_count; ++i) {
      const char* column_name = sqlite3_column_name(stmt, i);
      const char* column_value = reinterpret_cast<const char*>(sqlite3_column_text(stmt, i));
      
      row[column_name] = column_value ? column_value : "";
    }
    
    results.push_back(row);
  }
  
  sqlite3_finalize(stmt);
  sqlite3_close(db);
  
  return results;
}

bool SADatabaseExtension::InitializeSATables() {
  SAUtils::LogInfo(context_, "Initializing SA database tables");
  
  // Read and execute the SA schema extension SQL
  std::ifstream schema_file("database-migrations/sa-schema-extension.sql");
  if (!schema_file.is_open()) {
    SAUtils::LogError(context_, "Cannot open SA schema file");
    return false;
  }
  
  std::string schema_sql((std::istreambuf_iterator<char>(schema_file)),
                         std::istreambuf_iterator<char>());
  schema_file.close();
  
  // Split SQL into individual statements and execute them
  std::istringstream iss(schema_sql);
  std::string statement;
  std::string current_statement;
  
  while (std::getline(iss, statement)) {
    // Skip comments and empty lines
    if (statement.empty() || statement[0] == '-' || statement.substr(0, 2) == "/*") {
      continue;
    }
    
    current_statement += statement + "\n";
    
    // Check if statement is complete (ends with semicolon)
    if (statement.find(';') != std::string::npos) {
      if (!ExecuteSQL(current_statement)) {
        SAUtils::LogError(context_, "Failed to execute SA schema statement");
        return false;
      }
      current_statement.clear();
    }
  }
  
  SAUtils::LogInfo(context_, "SA database tables initialized successfully");
  return true;
}

// User management implementation
bool SADatabaseExtension::CreateUser(const SAUser& user) {
  std::string sql = "INSERT INTO SAUsers (user_id, username, password_hash, salt, full_name, email, role, province, preferred_language, is_active, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
  
  std::vector<std::string> params = {
    user.user_id,
    user.username,
    user.password_hash,
    user.salt,
    user.full_name,
    user.email,
    user.role,
    user.province,
    SAUtils::GetLanguageCode(user.preferred_language),
    user.is_active ? "1" : "0",
    user.created_at.empty() ? GetCurrentTimestamp() : user.created_at
  };
  
  bool success = ExecuteSQLWithParams(sql, params);
  if (success) {
    SAUtils::LogInfo(context_, "Created SA user: " + user.username);
    
    // Log audit entry
    LogUserAction(user.user_id, "USER_CREATED", "user", user.user_id, "", 
                  "User account created: " + user.username);
  }
  
  return success;
}

bool SADatabaseExtension::GetUser(SAUser& user, const std::string& user_id) {
  std::string sql = "SELECT * FROM SAUsers WHERE user_id = ?";
  std::vector<std::string> params = {user_id};
  
  auto results = QuerySQL(sql, params);
  if (results.empty()) {
    return false;
  }
  
  auto& row = results[0];
  user.user_id = row["user_id"];
  user.username = row["username"];
  user.password_hash = row["password_hash"];
  user.salt = row["salt"];
  user.full_name = row["full_name"];
  user.email = row["email"];
  user.role = row["role"];
  user.province = row["province"];
  user.preferred_language = SAUtils::GetLanguageFromCode(row["preferred_language"]);
  user.is_active = (row["is_active"] == "1");
  user.created_at = row["created_at"];
  user.last_login = row["last_login"];
  user.login_attempts = std::stoi(row["login_attempts"]);
  user.locked_until = row["locked_until"];
  
  return true;
}

bool SADatabaseExtension::GetUserByUsername(SAUser& user, const std::string& username) {
  std::string sql = "SELECT * FROM SAUsers WHERE username = ?";
  std::vector<std::string> params = {username};
  
  auto results = QuerySQL(sql, params);
  if (results.empty()) {
    return false;
  }
  
  auto& row = results[0];
  user.user_id = row["user_id"];
  user.username = row["username"];
  user.password_hash = row["password_hash"];
  user.salt = row["salt"];
  user.full_name = row["full_name"];
  user.email = row["email"];
  user.role = row["role"];
  user.province = row["province"];
  user.preferred_language = SAUtils::GetLanguageFromCode(row["preferred_language"]);
  user.is_active = (row["is_active"] == "1");
  user.created_at = row["created_at"];
  user.last_login = row["last_login"];
  user.login_attempts = std::stoi(row["login_attempts"]);
  user.locked_until = row["locked_until"];
  
  return true;
}

// Healthcare professional management implementation
bool SADatabaseExtension::CreateHealthcareProfessional(const SAHealthcareProfessional& professional) {
  std::string sql = "INSERT INTO SAHealthcareProfessionals (id, user_id, hpcsa_number, practice_number, practice_name, "
                    "specialization, sub_specialization, province, city, phone, emergency_contact, is_verified, "
                    "verification_method, license_expiry_date, is_active, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
  
  std::vector<std::string> params = {
    professional.id,
    professional.user_id,
    professional.hpcsa_number,
    professional.practice_number,
    professional.practice_name,
    professional.specialization,
    professional.sub_specialization,
    SAUtils::GetProvinceCode(professional.province),
    professional.city,
    professional.phone,
    professional.emergency_contact,
    professional.is_verified ? "1" : "0",
    professional.verification_method,
    professional.license_expiry_date,
    professional.is_active ? "1" : "0",
    professional.created_at.empty() ? GetCurrentTimestamp() : professional.created_at
  };
  
  bool success = ExecuteSQLWithParams(sql, params);
  if (success) {
    SAUtils::LogInfo(context_, "Created SA healthcare professional: " + professional.hpcsa_number);
    
    // Log audit entry
    LogUserAction(professional.user_id, "HEALTHCARE_PROFESSIONAL_CREATED", "healthcare_professional", 
                  professional.id, "", "Healthcare professional created: " + professional.hpcsa_number);
  }
  
  return success;
}

bool SADatabaseExtension::GetHealthcareProfessionalByHPCSA(SAHealthcareProfessional& professional, const std::string& hpcsa_number) {
  std::string sql = "SELECT * FROM SAHealthcareProfessionals WHERE hpcsa_number = ?";
  std::vector<std::string> params = {hpcsa_number};
  
  auto results = QuerySQL(sql, params);
  if (results.empty()) {
    return false;
  }
  
  auto& row = results[0];
  professional.id = row["id"];
  professional.user_id = row["user_id"];
  professional.hpcsa_number = row["hpcsa_number"];
  professional.practice_number = row["practice_number"];
  professional.practice_name = row["practice_name"];
  professional.specialization = row["specialization"];
  professional.sub_specialization = row["sub_specialization"];
  professional.province = SAUtils::GetProvinceFromCode(row["province"]);
  professional.city = row["city"];
  professional.phone = row["phone"];
  professional.emergency_contact = row["emergency_contact"];
  professional.is_verified = (row["is_verified"] == "1");
  professional.verification_date = row["verification_date"];
  professional.verification_method = row["verification_method"];
  professional.license_expiry_date = row["license_expiry_date"];
  professional.is_active = (row["is_active"] == "1");
  professional.created_at = row["created_at"];
  professional.updated_at = row["updated_at"];
  
  return true;
}

// Audit logging implementation
bool SADatabaseExtension::LogUserAction(const std::string& user_id, const std::string& action, 
                                       const std::string& resource_type, const std::string& resource_id,
                                       const std::string& patient_id, const std::string& details,
                                       const std::string& ip_address, const std::string& user_agent,
                                       const std::string& session_id, const std::string& risk_level) {
  
  SAAuditLogEntry entry;
  entry.audit_id = GenerateUUID();
  entry.user_id = user_id;
  entry.action = action;
  entry.resource_type = resource_type;
  entry.resource_id = resource_id;
  entry.patient_id = patient_id;
  entry.details = details;
  entry.ip_address = ip_address;
  entry.user_agent = user_agent;
  entry.session_id = session_id;
  entry.risk_level = risk_level;
  entry.timestamp = GetCurrentTimestamp();
  
  // Get HPCSA number if user is a healthcare professional
  SAUser user;
  if (GetUser(user, user_id)) {
    SAHealthcareProfessional professional;
    if (GetHealthcareProfessionalByHPCSA(professional, user.username)) {
      entry.hpcsa_number = professional.hpcsa_number;
    }
  }
  
  return LogAuditEntry(entry);
}

bool SADatabaseExtension::LogAuditEntry(const SAAuditLogEntry& entry) {
  std::string sql = "INSERT INTO SAAuditLog (audit_id, user_id, hpcsa_number, action, resource_type, resource_id, "
                    "patient_id, details, ip_address, user_agent, session_id, compliance_flags, risk_level, timestamp) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
  
  std::vector<std::string> params = {
    entry.audit_id,
    entry.user_id,
    entry.hpcsa_number,
    entry.action,
    entry.resource_type,
    entry.resource_id,
    entry.patient_id,
    entry.details,
    entry.ip_address,
    entry.user_agent,
    entry.session_id,
    entry.compliance_flags,
    entry.risk_level,
    entry.timestamp
  };
  
  return ExecuteSQLWithParams(sql, params);
}

// Validation methods implementation
bool SADatabaseExtension::ValidateHPCSANumber(const std::string& hpcsa_number) {
  return SAUtils::IsValidHPCSANumber(hpcsa_number);
}

bool SADatabaseExtension::ValidateSAIdNumber(const std::string& sa_id_number) {
  return SAUtils::IsValidSAIDNumber(sa_id_number);
}

bool SADatabaseExtension::IsHPCSANumberUnique(const std::string& hpcsa_number, const std::string& exclude_id) {
  std::string sql = "SELECT COUNT(*) as count FROM SAHealthcareProfessionals WHERE hpcsa_number = ?";
  std::vector<std::string> params = {hpcsa_number};
  
  if (!exclude_id.empty()) {
    sql += " AND id != ?";
    params.push_back(exclude_id);
  }
  
  auto results = QuerySQL(sql, params);
  if (results.empty()) {
    return false;
  }
  
  return std::stoi(results[0]["count"]) == 0;
}

// Statistics implementation
int SADatabaseExtension::GetTotalUsers() {
  std::string sql = "SELECT COUNT(*) as count FROM SAUsers";
  auto results = QuerySQL(sql);
  
  if (results.empty()) {
    return 0;
  }
  
  return std::stoi(results[0]["count"]);
}

int SADatabaseExtension::GetActiveUsers() {
  std::string sql = "SELECT COUNT(*) as count FROM SAUsers WHERE is_active = 1";
  auto results = QuerySQL(sql);
  
  if (results.empty()) {
    return 0;
  }
  
  return std::stoi(results[0]["count"]);
}

int SADatabaseExtension::GetVerifiedHealthcareProfessionals() {
  std::string sql = "SELECT COUNT(*) as count FROM SAHealthcareProfessionals WHERE is_verified = 1 AND is_active = 1";
  auto results = QuerySQL(sql);
  
  if (results.empty()) {
    return 0;
  }
  
  return std::stoi(results[0]["count"]);
}