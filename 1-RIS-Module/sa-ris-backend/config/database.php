<?php

/**
 * SA Medical Reporting Module - Database Configuration
 * 
 * Database connection configuration for the reporting module
 * Supports both PostgreSQL (primary) and MySQL (fallback)
 * 
 * @package SA_RIS
 * @author Ubuntu Patient Sorg Team
 * @copyright 2025
 */

// Load environment variables
if (file_exists(__DIR__ . '/../.env')) {
    $lines = file(__DIR__ . '/../.env', FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        if (strpos(trim($line), '#') === 0) {
            continue;
        }
        list($name, $value) = explode('=', $line, 2);
        $_ENV[trim($name)] = trim($value);
    }
}

class DatabaseConfig {
    
    // Primary database configuration (PostgreSQL for reporting module)
    public static function getReportingConnection() {
        $config = [
            'driver' => $_ENV['REPORTING_DB_DRIVER'] ?? 'pgsql',
            'host' => $_ENV['REPORTING_DB_HOST'] ?? 'localhost',
            'port' => $_ENV['REPORTING_DB_PORT'] ?? '5432',
            'database' => $_ENV['REPORTING_DB_NAME'] ?? 'sa_ris_reporting',
            'username' => $_ENV['REPORTING_DB_USERNAME'] ?? 'sa_ris_user',
            'password' => $_ENV['REPORTING_DB_PASSWORD'] ?? '',
            'charset' => $_ENV['REPORTING_DB_CHARSET'] ?? 'utf8',
            'options' => [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
                PDO::ATTR_PERSISTENT => true,
            ]
        ];
        
        return self::createConnection($config);
    }
    
    // Legacy database connection (MySQL for existing SA RIS)
    public static function getLegacyConnection() {
        $config = [
            'driver' => $_ENV['LEGACY_DB_DRIVER'] ?? 'mysql',
            'host' => $_ENV['LEGACY_DB_HOST'] ?? 'localhost',
            'port' => $_ENV['LEGACY_DB_PORT'] ?? '3306',
            'database' => $_ENV['LEGACY_DB_NAME'] ?? 'sa_ris_db',
            'username' => $_ENV['LEGACY_DB_USERNAME'] ?? 'sa_ris_user',
            'password' => $_ENV['LEGACY_DB_PASSWORD'] ?? '',
            'charset' => $_ENV['LEGACY_DB_CHARSET'] ?? 'utf8mb4',
            'options' => [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
                PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci"
            ]
        ];
        
        return self::createConnection($config);
    }
    
    // OpenEMR database connection
    public static function getOpenEMRConnection() {
        $config = [
            'driver' => $_ENV['OPENEMR_DB_DRIVER'] ?? 'mysql',
            'host' => $_ENV['OPENEMR_DB_HOST'] ?? 'localhost',
            'port' => $_ENV['OPENEMR_DB_PORT'] ?? '3306',
            'database' => $_ENV['OPENEMR_DB_NAME'] ?? 'openemr',
            'username' => $_ENV['OPENEMR_DB_USERNAME'] ?? 'openemr',
            'password' => $_ENV['OPENEMR_DB_PASSWORD'] ?? '',
            'charset' => $_ENV['OPENEMR_DB_CHARSET'] ?? 'utf8mb4',
            'options' => [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
                PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci"
            ]
        ];
        
        return self::createConnection($config);
    }
    
    private static function createConnection($config) {
        try {
            $dsn = self::buildDSN($config);
            
            $pdo = new PDO(
                $dsn,
                $config['username'],
                $config['password'],
                $config['options']
            );
            
            // Set timezone for PostgreSQL
            if ($config['driver'] === 'pgsql') {
                $pdo->exec("SET timezone = '" . date_default_timezone_get() . "'");
            }
            
            return $pdo;
            
        } catch (PDOException $e) {
            error_log("Database connection failed: " . $e->getMessage());
            throw new Exception("Database connection failed: " . $e->getMessage());
        }
    }
    
    private static function buildDSN($config) {
        $driver = $config['driver'];
        $host = $config['host'];
        $port = $config['port'];
        $database = $config['database'];
        $charset = $config['charset'];
        
        switch ($driver) {
            case 'pgsql':
                return "pgsql:host={$host};port={$port};dbname={$database}";
                
            case 'mysql':
                return "mysql:host={$host};port={$port};dbname={$database};charset={$charset}";
                
            case 'sqlite':
                return "sqlite:{$database}";
                
            default:
                throw new Exception("Unsupported database driver: {$driver}");
        }
    }
    
    // Connection pool management
    private static $connections = [];
    
    public static function getPooledConnection($type = 'reporting') {
        if (!isset(self::$connections[$type])) {
            switch ($type) {
                case 'reporting':
                    self::$connections[$type] = self::getReportingConnection();
                    break;
                case 'legacy':
                    self::$connections[$type] = self::getLegacyConnection();
                    break;
                case 'openemr':
                    self::$connections[$type] = self::getOpenEMRConnection();
                    break;
                default:
                    throw new Exception("Unknown connection type: {$type}");
            }
        }
        
        return self::$connections[$type];
    }
    
    // Health check for all connections
    public static function healthCheck() {
        $results = [];
        
        $connectionTypes = ['reporting', 'legacy', 'openemr'];
        
        foreach ($connectionTypes as $type) {
            try {
                $pdo = self::getPooledConnection($type);
                $stmt = $pdo->query('SELECT 1');
                $results[$type] = [
                    'status' => 'healthy',
                    'response_time' => microtime(true)
                ];
            } catch (Exception $e) {
                $results[$type] = [
                    'status' => 'unhealthy',
                    'error' => $e->getMessage()
                ];
            }
        }
        
        return $results;
    }
    
    // Database migration utilities
    public static function runMigrations($type = 'reporting') {
        $pdo = self::getPooledConnection($type);
        
        // Create migrations table if it doesn't exist
        if ($type === 'reporting') {
            $pdo->exec("
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    migration VARCHAR(255) NOT NULL,
                    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ");
        } else {
            $pdo->exec("
                CREATE TABLE IF NOT EXISTS migrations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    migration VARCHAR(255) NOT NULL,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ");
        }
        
        // Get list of executed migrations
        $stmt = $pdo->query("SELECT migration FROM migrations");
        $executedMigrations = $stmt->fetchAll(PDO::FETCH_COLUMN);
        
        // Find migration files
        $migrationDir = __DIR__ . "/../migrations/{$type}";
        if (!is_dir($migrationDir)) {
            mkdir($migrationDir, 0755, true);
        }
        
        $migrationFiles = glob($migrationDir . '/*.sql');
        sort($migrationFiles);
        
        $newMigrations = [];
        foreach ($migrationFiles as $file) {
            $migrationName = basename($file, '.sql');
            if (!in_array($migrationName, $executedMigrations)) {
                $newMigrations[] = [
                    'name' => $migrationName,
                    'file' => $file
                ];
            }
        }
        
        // Execute new migrations
        foreach ($newMigrations as $migration) {
            try {
                $pdo->beginTransaction();
                
                $sql = file_get_contents($migration['file']);
                $pdo->exec($sql);
                
                $stmt = $pdo->prepare("INSERT INTO migrations (migration) VALUES (?)");
                $stmt->execute([$migration['name']]);
                
                $pdo->commit();
                
                echo "Executed migration: {$migration['name']}\n";
                
            } catch (Exception $e) {
                $pdo->rollback();
                throw new Exception("Migration failed: {$migration['name']} - " . $e->getMessage());
            }
        }
        
        return count($newMigrations);
    }
}

// Global database connection functions for backward compatibility
function getReportingDB() {
    return DatabaseConfig::getPooledConnection('reporting');
}

function getLegacyDB() {
    return DatabaseConfig::getPooledConnection('legacy');
}

function getOpenEMRDB() {
    return DatabaseConfig::getPooledConnection('openemr');
}

// Database health check endpoint
if (isset($_GET['health']) && php_sapi_name() !== 'cli') {
    header('Content-Type: application/json');
    echo json_encode(DatabaseConfig::healthCheck());
    exit;
}