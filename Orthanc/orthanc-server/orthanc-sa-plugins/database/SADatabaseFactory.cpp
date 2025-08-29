/**
 * South African Healthcare Integration for Orthanc
 * Database Factory Implementation - Universal database connectivity
 */

#include "SADatabaseAbstraction.h"
#include <fstream>
#include <json/json.h>
#include <cstdlib>

std::unique_ptr<ISADatabase> SADatabaseFactory::CreateDatabase(const std::string& type) {
  std::string db_type = type;
  std::transform(db_type.begin(), db_type.end(), db_type.begin(), ::tolower);
  
  if (db_type == "mysql" || db_type == "mariadb") {
    return std::make_unique<SAMySQLDatabase>();
  }
  else if (db_type == "postgresql" || db_type == "postgres") {
    return std::make_unique<SAPostgreSQLDatabase>();
  }
  else if (db_type == "firebird") {
    return std::make_unique<SAFirebirdDatabase>();
  }
  else if (db_type == "sqlite") {
    // Use the existing SQLite implementation
    return std::make_unique<SASQLiteDatabase>();
  }
  else if (db_type == "sqlserver" || db_type == "mssql") {
    return std::make_unique<SASQLServerDatabase>();
  }
  else if (db_type == "oracle") {
    return std::make_unique<SAOracleDatabase>();
  }
  
  return nullptr; // Unsupported database type
}

std::vector<std::string> SADatabaseFactory::GetSupportedDatabaseTypes() {
  return {
    "sqlite",
    "mysql",
    "mariadb", 
    "postgresql",
    "postgres",
    "firebird",
    "sqlserver",
    "mssql",
    "oracle"
  };
}

SADatabaseConfig SADatabaseFactory::LoadConfigFromFile(const std::string& config_file) {
  SADatabaseConfig config;
  
  std::ifstream file(config_file);
  if (!file.is_open()) {
    throw std::runtime_error("Cannot open database config file: " + config_file);
  }
  
  Json::Value json_config;
  Json::Reader reader;
  if (!reader.parse(file, json_config)) {
    throw std::runtime_error("Invalid JSON in database config file: " + config_file);
  }
  
  // Parse configuration
  config.type = json_config.get("type", "sqlite").asString();
  config.host = json_config.get("host", "localhost").asString();
  config.port = json_config.get("port", 0).asInt();
  config.database = json_config.get("database", "").asString();
  config.username = json_config.get("username", "").asString();
  config.password = json_config.get("password", "").asString();
  config.connection_string = json_config.get("connection_string", "").asString();
  
  // SSL configuration
  config.use_ssl = json_config.get("use_ssl", false).asBool();
  config.ssl_cert = json_config.get("ssl_cert", "").asString();
  config.ssl_key = json_config.get("ssl_key", "").asString();
  config.ssl_ca = json_config.get("ssl_ca", "").asString();
  
  // Connection pool settings
  config.min_connections = json_config.get("min_connections", 1).asInt();
  config.max_connections = json_config.get("max_connections", 10).asInt();
  config.connection_timeout = json_config.get("connection_timeout", 30).asInt();
  
  // Database-specific options
  if (json_config.isMember("options")) {
    Json::Value options = json_config["options"];
    for (const auto& key : options.getMemberNames()) {
      config.options[key] = options[key].asString();
    }
  }
  
  return config;
}

SADatabaseConfig SADatabaseFactory::LoadConfigFromEnvironment() {
  SADatabaseConfig config;
  
  // Load from environment variables
  const char* db_type = std::getenv("SA_DB_TYPE");
  const char* db_host = std::getenv("SA_DB_HOST");
  const char* db_port = std::getenv("SA_DB_PORT");
  const char* db_name = std::getenv("SA_DB_NAME");
  const char* db_user = std::getenv("SA_DB_USER");
  const char* db_pass = std::getenv("SA_DB_PASSWORD");
  const char* db_conn_str = std::getenv("SA_DB_CONNECTION_STRING");
  
  config.type = db_type ? db_type : "sqlite";
  config.host = db_host ? db_host : "localhost";
  config.port = db_port ? std::atoi(db_port) : 0;
  config.database = db_name ? db_name : "";
  config.username = db_user ? db_user : "";
  config.password = db_pass ? db_pass : "";
  config.connection_string = db_conn_str ? db_conn_str : "";
  
  // SSL environment variables
  const char* use_ssl = std::getenv("SA_DB_USE_SSL");
  config.use_ssl = use_ssl ? (std::string(use_ssl) == "true" || std::string(use_ssl) == "1") : false;
  
  const char* ssl_cert = std::getenv("SA_DB_SSL_CERT");
  const char* ssl_key = std::getenv("SA_DB_SSL_KEY");
  const char* ssl_ca = std::getenv("SA_DB_SSL_CA");
  
  config.ssl_cert = ssl_cert ? ssl_cert : "";
  config.ssl_key = ssl_key ? ssl_key : "";
  config.ssl_ca = ssl_ca ? ssl_ca : "";
  
  // Connection pool environment variables
  const char* min_conn = std::getenv("SA_DB_MIN_CONNECTIONS");
  const char* max_conn = std::getenv("SA_DB_MAX_CONNECTIONS");
  const char* conn_timeout = std::getenv("SA_DB_CONNECTION_TIMEOUT");
  
  config.min_connections = min_conn ? std::atoi(min_conn) : 1;
  config.max_connections = max_conn ? std::atoi(max_conn) : 10;
  config.connection_timeout = conn_timeout ? std::atoi(conn_timeout) : 30;
  
  return config;
}

bool SADatabaseFactory::ValidateConfig(const SADatabaseConfig& config) {
  // Validate database type
  auto supported_types = GetSupportedDatabaseTypes();
  if (std::find(supported_types.begin(), supported_types.end(), config.type) == supported_types.end()) {
    return false;
  }
  
  // Validate required fields based on database type
  if (config.type != "sqlite") {
    if (config.host.empty()) return false;
    if (config.database.empty()) return false;
    if (config.username.empty()) return false;
  }
  
  // Validate port ranges
  if (config.port < 0 || config.port > 65535) return false;
  
  // Validate connection pool settings
  if (config.min_connections < 1) return false;
  if (config.max_connections < config.min_connections) return false;
  if (config.connection_timeout < 1) return false;
  
  return true;
}

// Universal Database Manager Implementation
SAUniversalDatabase::SAUniversalDatabase(OrthancPluginContext* context) 
  : context_(context), is_initialized_(false) {
  SAUtils::LogInfo(context_, "SAUniversalDatabase created");
}

SAUniversalDatabase::~SAUniversalDatabase() {
  if (database_) {
    database_->Disconnect();
  }
  SAUtils::LogInfo(context_, "SAUniversalDatabase destroyed");
}

bool SAUniversalDatabase::Initialize(const SADatabaseConfig& config) {
  if (!SADatabaseFactory::ValidateConfig(config)) {
    SAUtils::LogError(context_, "Invalid database configuration");
    return false;
  }
  
  config_ = config;
  
  // Create database instance
  database_ = SADatabaseFactory::CreateDatabase(config.type);
  if (!database_) {
    SAUtils::LogError(context_, "Unsupported database type: " + config.type);
    return false;
  }
  
  // Connect to database
  if (!database_->Connect(config)) {
    SAUtils::LogError(context_, "Failed to connect to database: " + config.type);
    return false;
  }
  
  // Create SA tables if they don't exist
  if (!database_->CreateTables()) {
    SAUtils::LogError(context_, "Failed to create SA tables");
    return false;
  }
  
  is_initialized_ = true;
  SAUtils::LogInfo(context_, "Successfully initialized " + config.type + " database");
  
  return true;
}

bool SAUniversalDatabase::Initialize(const std::string& config_file) {
  try {
    SADatabaseConfig config = SADatabaseFactory::LoadConfigFromFile(config_file);
    return Initialize(config);
  } catch (const std::exception& e) {
    SAUtils::LogError(context_, "Failed to load database config from file: " + std::string(e.what()));
    return false;
  }
}

bool SAUniversalDatabase::InitializeFromEnvironment() {
  try {
    SADatabaseConfig config = SADatabaseFactory::LoadConfigFromEnvironment();
    return Initialize(config);
  } catch (const std::exception& e) {
    SAUtils::LogError(context_, "Failed to load database config from environment: " + std::string(e.what()));
    return false;
  }
}

bool SAUniversalDatabase::ExecuteSQL(const std::string& sql) {
  if (!is_initialized_ || !database_) {
    SAUtils::LogError(context_, "Database not initialized");
    return false;
  }
  
  return database_->ExecuteSQL(sql);
}

bool SAUniversalDatabase::ExecuteSQLWithParams(const std::string& sql, const std::vector<std::string>& params) {
  if (!is_initialized_ || !database_) {
    SAUtils::LogError(context_, "Database not initialized");
    return false;
  }
  
  return database_->ExecuteSQLWithParams(sql, params);
}

std::vector<std::map<std::string, std::string>> SAUniversalDatabase::QuerySQL(const std::string& sql, const std::vector<std::string>& params) {
  if (!is_initialized_ || !database_) {
    SAUtils::LogError(context_, "Database not initialized");
    return {};
  }
  
  return database_->QuerySQL(sql, params);
}

bool SAUniversalDatabase::TestConnection() {
  if (!is_initialized_ || !database_) {
    return false;
  }
  
  return database_->TestConnection();
}

bool SAUniversalDatabase::Reconnect() {
  if (!database_) {
    return false;
  }
  
  database_->Disconnect();
  bool success = database_->Connect(config_);
  
  if (success) {
    SAUtils::LogInfo(context_, "Successfully reconnected to database");
  } else {
    SAUtils::LogError(context_, "Failed to reconnect to database");
  }
  
  return success;
}

std::string SAUniversalDatabase::GetConnectionInfo() {
  if (!is_initialized_) {
    return "Database not initialized";
  }
  
  std::ostringstream oss;
  oss << "Database Type: " << config_.type << "\n";
  oss << "Host: " << config_.host << "\n";
  oss << "Port: " << config_.port << "\n";
  oss << "Database: " << config_.database << "\n";
  oss << "Username: " << config_.username << "\n";
  oss << "SSL Enabled: " << (config_.use_ssl ? "Yes" : "No") << "\n";
  oss << "Connection Pool: " << config_.min_connections << "-" << config_.max_connections << "\n";
  
  return oss.str();
}

std::string SAUniversalDatabase::GetDatabaseType() {
  if (!is_initialized_ || !database_) {
    return "unknown";
  }
  
  return database_->GetDatabaseType();
}