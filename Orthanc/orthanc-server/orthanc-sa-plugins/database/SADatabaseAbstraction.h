/**
 * South African Healthcare Integration for Orthanc
 * Database Abstraction Layer - Universal database connectivity
 * 
 * This abstraction layer allows easy connection to any database:
 * SQLite, MySQL, PostgreSQL, Firebird, SQL Server, Oracle, etc.
 */

#pragma once

#include "../common/SACommon.h"
#include <orthanc/OrthancCPlugin.h>
#include <string>
#include <vector>
#include <map>
#include <memory>

// Database connection configuration
struct SADatabaseConfig {
  std::string type;           // sqlite, mysql, postgresql, firebird, sqlserver, oracle
  std::string host;           // Database server host
  int port;                   // Database server port
  std::string database;       // Database name
  std::string username;       // Database username
  std::string password;       // Database password
  std::string connection_string; // Full connection string (optional)
  
  // SSL/TLS configuration
  bool use_ssl;
  std::string ssl_cert;
  std::string ssl_key;
  std::string ssl_ca;
  
  // Connection pool settings
  int min_connections;
  int max_connections;
  int connection_timeout;
  
  // Database-specific options
  std::map<std::string, std::string> options;
};

// Abstract database interface
class ISADatabase {
public:
  virtual ~ISADatabase() = default;
  
  // Connection management
  virtual bool Connect(const SADatabaseConfig& config) = 0;
  virtual bool Disconnect() = 0;
  virtual bool IsConnected() = 0;
  virtual bool TestConnection() = 0;
  
  // Transaction management
  virtual bool BeginTransaction() = 0;
  virtual bool CommitTransaction() = 0;
  virtual bool RollbackTransaction() = 0;
  
  // Query execution
  virtual bool ExecuteSQL(const std::string& sql) = 0;
  virtual bool ExecuteSQLWithParams(const std::string& sql, const std::vector<std::string>& params) = 0;
  virtual std::vector<std::map<std::string, std::string>> QuerySQL(const std::string& sql, const std::vector<std::string>& params = {}) = 0;
  
  // Schema management
  virtual bool CreateTables() = 0;
  virtual bool UpgradeSchema(int from_version, int to_version) = 0;
  virtual int GetSchemaVersion() = 0;
  virtual bool SetSchemaVersion(int version) = 0;
  
  // Database-specific SQL generation
  virtual std::string GetCreateTableSQL(const std::string& table_name, const std::vector<std::string>& columns) = 0;
  virtual std::string GetInsertSQL(const std::string& table_name, const std::vector<std::string>& columns) = 0;
  virtual std::string GetUpdateSQL(const std::string& table_name, const std::vector<std::string>& columns, const std::string& where_clause) = 0;
  virtual std::string GetSelectSQL(const std::string& table_name, const std::vector<std::string>& columns, const std::string& where_clause = "") = 0;
  virtual std::string GetDeleteSQL(const std::string& table_name, const std::string& where_clause) = 0;
  
  // Data type mapping
  virtual std::string MapDataType(const std::string& generic_type) = 0;
  virtual std::string GetAutoIncrementSQL() = 0;
  virtual std::string GetTimestampSQL() = 0;
  virtual std::string GetBooleanSQL(bool value) = 0;
  
  // Database information
  virtual std::string GetDatabaseType() = 0;
  virtual std::string GetDatabaseVersion() = 0;
  virtual std::vector<std::string> GetTableList() = 0;
  virtual std::vector<std::string> GetColumnList(const std::string& table_name) = 0;
};

// Database factory for creating database instances
class SADatabaseFactory {
public:
  static std::unique_ptr<ISADatabase> CreateDatabase(const std::string& type);
  static std::vector<std::string> GetSupportedDatabaseTypes();
  static SADatabaseConfig LoadConfigFromFile(const std::string& config_file);
  static SADatabaseConfig LoadConfigFromEnvironment();
  static bool ValidateConfig(const SADatabaseConfig& config);
};

// Universal database manager
class SAUniversalDatabase {
private:
  OrthancPluginContext* context_;
  std::unique_ptr<ISADatabase> database_;
  SADatabaseConfig config_;
  bool is_initialized_;
  
public:
  explicit SAUniversalDatabase(OrthancPluginContext* context);
  ~SAUniversalDatabase();
  
  // Initialization
  bool Initialize(const SADatabaseConfig& config);
  bool Initialize(const std::string& config_file);
  bool InitializeFromEnvironment();
  
  // Database operations (delegates to concrete implementation)
  bool ExecuteSQL(const std::string& sql);
  bool ExecuteSQLWithParams(const std::string& sql, const std::vector<std::string>& params);
  std::vector<std::map<std::string, std::string>> QuerySQL(const std::string& sql, const std::vector<std::string>& params = {});
  
  // High-level operations
  bool CreateSATables();
  bool MigrateSAData();
  bool BackupSAData(const std::string& backup_path);
  bool RestoreSAData(const std::string& backup_path);
  
  // Connection management
  bool TestConnection();
  bool Reconnect();
  std::string GetConnectionInfo();
  
  // Configuration
  SADatabaseConfig GetConfig() const { return config_; }
  std::string GetDatabaseType();
  bool IsInitialized() const { return is_initialized_; }
};

// Specific database implementations
class SAMySQLDatabase : public ISADatabase {
private:
  void* mysql_connection_; // MYSQL* connection
  SADatabaseConfig config_;
  
public:
  SAMySQLDatabase();
  virtual ~SAMySQLDatabase();
  
  // ISADatabase implementation
  bool Connect(const SADatabaseConfig& config) override;
  bool Disconnect() override;
  bool IsConnected() override;
  bool TestConnection() override;
  
  bool BeginTransaction() override;
  bool CommitTransaction() override;
  bool RollbackTransaction() override;
  
  bool ExecuteSQL(const std::string& sql) override;
  bool ExecuteSQLWithParams(const std::string& sql, const std::vector<std::string>& params) override;
  std::vector<std::map<std::string, std::string>> QuerySQL(const std::string& sql, const std::vector<std::string>& params = {}) override;
  
  bool CreateTables() override;
  bool UpgradeSchema(int from_version, int to_version) override;
  int GetSchemaVersion() override;
  bool SetSchemaVersion(int version) override;
  
  std::string GetCreateTableSQL(const std::string& table_name, const std::vector<std::string>& columns) override;
  std::string GetInsertSQL(const std::string& table_name, const std::vector<std::string>& columns) override;
  std::string GetUpdateSQL(const std::string& table_name, const std::vector<std::string>& columns, const std::string& where_clause) override;
  std::string GetSelectSQL(const std::string& table_name, const std::vector<std::string>& columns, const std::string& where_clause = "") override;
  std::string GetDeleteSQL(const std::string& table_name, const std::string& where_clause) override;
  
  std::string MapDataType(const std::string& generic_type) override;
  std::string GetAutoIncrementSQL() override;
  std::string GetTimestampSQL() override;
  std::string GetBooleanSQL(bool value) override;
  
  std::string GetDatabaseType() override { return "mysql"; }
  std::string GetDatabaseVersion() override;
  std::vector<std::string> GetTableList() override;
  std::vector<std::string> GetColumnList(const std::string& table_name) override;
};

class SAPostgreSQLDatabase : public ISADatabase {
private:
  void* pgsql_connection_; // PGconn* connection
  SADatabaseConfig config_;
  
public:
  SAPostgreSQLDatabase();
  virtual ~SAPostgreSQLDatabase();
  
  // ISADatabase implementation (similar to MySQL but with PostgreSQL-specific SQL)
  bool Connect(const SADatabaseConfig& config) override;
  bool Disconnect() override;
  bool IsConnected() override;
  bool TestConnection() override;
  
  bool BeginTransaction() override;
  bool CommitTransaction() override;
  bool RollbackTransaction() override;
  
  bool ExecuteSQL(const std::string& sql) override;
  bool ExecuteSQLWithParams(const std::string& sql, const std::vector<std::string>& params) override;
  std::vector<std::map<std::string, std::string>> QuerySQL(const std::string& sql, const std::vector<std::string>& params = {}) override;
  
  bool CreateTables() override;
  bool UpgradeSchema(int from_version, int to_version) override;
  int GetSchemaVersion() override;
  bool SetSchemaVersion(int version) override;
  
  std::string GetCreateTableSQL(const std::string& table_name, const std::vector<std::string>& columns) override;
  std::string GetInsertSQL(const std::string& table_name, const std::vector<std::string>& columns) override;
  std::string GetUpdateSQL(const std::string& table_name, const std::vector<std::string>& columns, const std::string& where_clause) override;
  std::string GetSelectSQL(const std::string& table_name, const std::vector<std::string>& columns, const std::string& where_clause = "") override;
  std::string GetDeleteSQL(const std::string& table_name, const std::string& where_clause) override;
  
  std::string MapDataType(const std::string& generic_type) override;
  std::string GetAutoIncrementSQL() override;
  std::string GetTimestampSQL() override;
  std::string GetBooleanSQL(bool value) override;
  
  std::string GetDatabaseType() override { return "postgresql"; }
  std::string GetDatabaseVersion() override;
  std::vector<std::string> GetTableList() override;
  std::vector<std::string> GetColumnList(const std::string& table_name) override;
};

class SAFirebirdDatabase : public ISADatabase {
private:
  void* firebird_connection_; // isc_db_handle connection
  SADatabaseConfig config_;
  
public:
  SAFirebirdDatabase();
  virtual ~SAFirebirdDatabase();
  
  // ISADatabase implementation with Firebird-specific SQL
  bool Connect(const SADatabaseConfig& config) override;
  bool Disconnect() override;
  bool IsConnected() override;
  bool TestConnection() override;
  
  bool BeginTransaction() override;
  bool CommitTransaction() override;
  bool RollbackTransaction() override;
  
  bool ExecuteSQL(const std::string& sql) override;
  bool ExecuteSQLWithParams(const std::string& sql, const std::vector<std::string>& params) override;
  std::vector<std::map<std::string, std::string>> QuerySQL(const std::string& sql, const std::vector<std::string>& params = {}) override;
  
  bool CreateTables() override;
  bool UpgradeSchema(int from_version, int to_version) override;
  int GetSchemaVersion() override;
  bool SetSchemaVersion(int version) override;
  
  std::string GetCreateTableSQL(const std::string& table_name, const std::vector<std::string>& columns) override;
  std::string GetInsertSQL(const std::string& table_name, const std::vector<std::string>& columns) override;
  std::string GetUpdateSQL(const std::string& table_name, const std::vector<std::string>& columns, const std::string& where_clause) override;
  std::string GetSelectSQL(const std::string& table_name, const std::vector<std::string>& columns, const std::string& where_clause = "") override;
  std::string GetDeleteSQL(const std::string& table_name, const std::string& where_clause) override;
  
  std::string MapDataType(const std::string& generic_type) override;
  std::string GetAutoIncrementSQL() override;
  std::string GetTimestampSQL() override;
  std::string GetBooleanSQL(bool value) override;
  
  std::string GetDatabaseType() override { return "firebird"; }
  std::string GetDatabaseVersion() override;
  std::vector<std::string> GetTableList() override;
  std::vector<std::string> GetColumnList(const std::string& table_name) override;
};

// Additional database implementations for SQL Server, Oracle, etc. would follow the same pattern