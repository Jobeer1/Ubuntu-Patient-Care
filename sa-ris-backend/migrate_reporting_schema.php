<?php

/**
 * SA Medical Reporting Module - Database Migration Script
 * 
 * This script creates the reporting module database schema
 * and integrates with the existing SA RIS system
 * 
 * @package SA_RIS
 * @author Ubuntu Patient Sorg Team
 * @copyright 2025
 */

require_once 'config/database.php';

class ReportingModuleMigration {
    
    private $pdo;
    private $logFile;
    
    public function __construct() {
        $this->logFile = 'logs/migration_' . date('Y-m-d_H-i-s') . '.log';
        $this->initializeDatabase();
    }
    
    private function initializeDatabase() {
        try {
            // Database configuration
            $host = $_ENV['DB_HOST'] ?? 'localhost';
            $port = $_ENV['DB_PORT'] ?? '5432';
            $dbname = $_ENV['DB_NAME'] ?? 'sa_ris_db';
            $username = $_ENV['DB_USERNAME'] ?? 'sa_ris_user';
            $password = $_ENV['DB_PASSWORD'] ?? '';
            
            $dsn = "pgsql:host={$host};port={$port};dbname={$dbname}";
            
            $this->pdo = new PDO($dsn, $username, $password, [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
            ]);
            
            $this->log("Database connection established successfully");
            
        } catch (PDOException $e) {
            $this->log("Database connection failed: " . $e->getMessage(), 'ERROR');
            throw $e;
        }
    }
    
    public function migrate() {
        try {
            $this->log("Starting SA Medical Reporting Module migration");
            
            // Check if migration has already been run
            if ($this->isMigrationComplete()) {
                $this->log("Migration already completed. Skipping...");
                return true;
            }
            
            // Start transaction
            $this->pdo->beginTransaction();
            
            // Run migration steps
            $this->createExtensions();
            $this->createTables();
            $this->createIndexes();
            $this->createFunctions();
            $this->createTriggers();
            $this->createViews();
            $this->createRoles();
            $this->insertSampleData();
            $this->updateSchemaVersion();
            
            // Commit transaction
            $this->pdo->commit();
            
            $this->log("Migration completed successfully");
            return true;
            
        } catch (Exception $e) {
            // Rollback on error
            $this->pdo->rollback();
            $this->log("Migration failed: " . $e->getMessage(), 'ERROR');
            throw $e;
        }
    }
    
    private function isMigrationComplete() {
        try {
            $stmt = $this->pdo->query("SELECT version FROM schema_version WHERE version = '1.0.0'");
            return $stmt->rowCount() > 0;
        } catch (PDOException $e) {
            // Table doesn't exist yet
            return false;
        }
    }
    
    private function createExtensions() {
        $this->log("Creating database extensions");
        
        $extensions = [
            'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"',
            'CREATE EXTENSION IF NOT EXISTS "pg_trgm"', // For text search
            'CREATE EXTENSION IF NOT EXISTS "btree_gin"' // For JSONB indexing
        ];
        
        foreach ($extensions as $sql) {
            try {
                $this->pdo->exec($sql);
                $this->log("Extension created: " . $sql);
            } catch (PDOException $e) {
                $this->log("Extension creation warning: " . $e->getMessage(), 'WARNING');
            }
        }
    }
    
    private function createTables() {
        $this->log("Creating database tables");
        
        // Read and execute the schema file
        $schemaFile = __DIR__ . '/reporting_schema.sql';
        if (!file_exists($schemaFile)) {
            throw new Exception("Schema file not found: {$schemaFile}");
        }
        
        $schema = file_get_contents($schemaFile);
        
        // Split into individual statements
        $statements = array_filter(
            array_map('trim', explode(';', $schema)),
            function($stmt) {
                return !empty($stmt) && !preg_match('/^\s*--/', $stmt);
            }
        );
        
        foreach ($statements as $statement) {
            if (trim($statement)) {
                try {
                    $this->pdo->exec($statement);
                } catch (PDOException $e) {
                    // Log but continue for non-critical errors
                    if (strpos($e->getMessage(), 'already exists') === false) {
                        $this->log("Statement execution warning: " . $e->getMessage(), 'WARNING');
                    }
                }
            }
        }
        
        $this->log("Database tables created successfully");
    }
    
    private function createIndexes() {
        $this->log("Creating additional performance indexes");
        
        $indexes = [
            // Full-text search indexes
            "CREATE INDEX IF NOT EXISTS idx_radiology_reports_findings_fts 
             ON radiology_reports USING gin(to_tsvector('english', findings))",
            
            "CREATE INDEX IF NOT EXISTS idx_radiology_reports_impression_fts 
             ON radiology_reports USING gin(to_tsvector('english', impression))",
            
            // JSONB indexes
            "CREATE INDEX IF NOT EXISTS idx_radiology_reports_billing_codes 
             ON radiology_reports USING gin(billing_codes)",
            
            "CREATE INDEX IF NOT EXISTS idx_audio_sessions_medical_terms 
             ON audio_sessions USING gin(medical_terms_detected)",
            
            // Partial indexes for active records
            "CREATE INDEX IF NOT EXISTS idx_radiology_reports_active 
             ON radiology_reports(status, priority, created_at) 
             WHERE status NOT IN ('delivered', 'archived')",
            
            // Composite indexes for common queries
            "CREATE INDEX IF NOT EXISTS idx_transcription_queue_priority 
             ON radiology_reports(priority, dictation_timestamp) 
             WHERE status IN ('awaiting_transcription', 'transcription_in_progress')",
        ];
        
        foreach ($indexes as $index) {
            try {
                $this->pdo->exec($index);
                $this->log("Index created successfully");
            } catch (PDOException $e) {
                $this->log("Index creation warning: " . $e->getMessage(), 'WARNING');
            }
        }
    }
    
    private function createFunctions() {
        $this->log("Creating database functions");
        
        $functions = [
            // Function to calculate report turnaround time
            "CREATE OR REPLACE FUNCTION calculate_turnaround_time(report_id UUID)
             RETURNS INTERVAL AS $$
             DECLARE
                 created_time TIMESTAMP WITH TIME ZONE;
                 completed_time TIMESTAMP WITH TIME ZONE;
             BEGIN
                 SELECT created_at, authorized_at INTO created_time, completed_time
                 FROM radiology_reports WHERE id = report_id;
                 
                 IF completed_time IS NULL THEN
                     RETURN NULL;
                 END IF;
                 
                 RETURN completed_time - created_time;
             END;
             $$ LANGUAGE plpgsql;",
            
            // Function to get next report for transcriptionist
            "CREATE OR REPLACE FUNCTION get_next_transcription_report(transcriptionist_id VARCHAR)
             RETURNS UUID AS $$
             DECLARE
                 next_report_id UUID;
             BEGIN
                 SELECT r.id INTO next_report_id
                 FROM radiology_reports r
                 LEFT JOIN user_assignments ua ON r.id = ua.report_id 
                     AND ua.user_role = 'transcriptionist'
                 WHERE r.status = 'awaiting_transcription'
                     AND (ua.user_id IS NULL OR ua.user_id = transcriptionist_id)
                 ORDER BY 
                     CASE r.priority 
                         WHEN 'stat' THEN 1 
                         WHEN 'urgent' THEN 2 
                         WHEN 'routine' THEN 3 
                     END,
                     r.dictation_timestamp ASC
                 LIMIT 1;
                 
                 RETURN next_report_id;
             END;
             $$ LANGUAGE plpgsql;",
        ];
        
        foreach ($functions as $function) {
            try {
                $this->pdo->exec($function);
                $this->log("Function created successfully");
            } catch (PDOException $e) {
                $this->log("Function creation error: " . $e->getMessage(), 'ERROR');
            }
        }
    }
    
    private function createTriggers() {
        $this->log("Creating database triggers");
        
        // Triggers are already included in the schema file
        $this->log("Triggers created from schema file");
    }
    
    private function createViews() {
        $this->log("Creating database views");
        
        // Views are already included in the schema file
        $this->log("Views created from schema file");
    }
    
    private function createRoles() {
        $this->log("Creating database roles");
        
        $roles = [
            'sa_ris_radiologist',
            'sa_ris_transcriptionist', 
            'sa_ris_billing_clerk',
            'sa_ris_admin'
        ];
        
        foreach ($roles as $role) {
            try {
                $this->pdo->exec("CREATE ROLE {$role}");
                $this->log("Role created: {$role}");
            } catch (PDOException $e) {
                if (strpos($e->getMessage(), 'already exists') !== false) {
                    $this->log("Role already exists: {$role}");
                } else {
                    $this->log("Role creation error: " . $e->getMessage(), 'WARNING');
                }
            }
        }
    }
    
    private function insertSampleData() {
        $this->log("Inserting sample data");
        
        // Sample data is already included in the schema file
        $this->log("Sample data inserted from schema file");
    }
    
    private function updateSchemaVersion() {
        $this->log("Updating schema version");
        
        try {
            $stmt = $this->pdo->prepare("
                INSERT INTO schema_version (version, description) 
                VALUES (?, ?) 
                ON CONFLICT (version) DO NOTHING
            ");
            
            $stmt->execute(['1.0.0', 'Initial SA Medical Reporting Module schema']);
            $this->log("Schema version updated to 1.0.0");
            
        } catch (PDOException $e) {
            $this->log("Schema version update error: " . $e->getMessage(), 'ERROR');
            throw $e;
        }
    }
    
    public function rollback() {
        $this->log("Starting rollback of SA Medical Reporting Module");
        
        try {
            $this->pdo->beginTransaction();
            
            // Drop tables in reverse order
            $tables = [
                'notification_queue',
                'performance_metrics',
                'audit_log',
                'report_templates',
                'medical_terminology',
                'user_assignments',
                'workflow_state_history',
                'text_changes',
                'transcription_reviews',
                'audio_sessions',
                'radiology_reports',
                'schema_version'
            ];
            
            foreach ($tables as $table) {
                try {
                    $this->pdo->exec("DROP TABLE IF EXISTS {$table} CASCADE");
                    $this->log("Dropped table: {$table}");
                } catch (PDOException $e) {
                    $this->log("Error dropping table {$table}: " . $e->getMessage(), 'WARNING');
                }
            }
            
            // Drop views
            $views = [
                'authorization_queue',
                'transcription_queue', 
                'active_reports_with_assignments'
            ];
            
            foreach ($views as $view) {
                try {
                    $this->pdo->exec("DROP VIEW IF EXISTS {$view} CASCADE");
                    $this->log("Dropped view: {$view}");
                } catch (PDOException $e) {
                    $this->log("Error dropping view {$view}: " . $e->getMessage(), 'WARNING');
                }
            }
            
            // Drop functions
            $functions = [
                'calculate_turnaround_time(UUID)',
                'get_next_transcription_report(VARCHAR)',
                'update_updated_at_column()',
                'log_workflow_state_change()'
            ];
            
            foreach ($functions as $function) {
                try {
                    $this->pdo->exec("DROP FUNCTION IF EXISTS {$function} CASCADE");
                    $this->log("Dropped function: {$function}");
                } catch (PDOException $e) {
                    $this->log("Error dropping function {$function}: " . $e->getMessage(), 'WARNING');
                }
            }
            
            $this->pdo->commit();
            $this->log("Rollback completed successfully");
            
        } catch (Exception $e) {
            $this->pdo->rollback();
            $this->log("Rollback failed: " . $e->getMessage(), 'ERROR');
            throw $e;
        }
    }
    
    public function validateSchema() {
        $this->log("Validating database schema");
        
        $requiredTables = [
            'radiology_reports',
            'audio_sessions',
            'transcription_reviews',
            'text_changes',
            'workflow_state_history',
            'user_assignments',
            'medical_terminology',
            'report_templates',
            'audit_log',
            'performance_metrics',
            'notification_queue'
        ];
        
        $missingTables = [];
        
        foreach ($requiredTables as $table) {
            $stmt = $this->pdo->prepare("
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = ?
                )
            ");
            $stmt->execute([$table]);
            
            if (!$stmt->fetchColumn()) {
                $missingTables[] = $table;
            }
        }
        
        if (empty($missingTables)) {
            $this->log("Schema validation passed - all tables exist");
            return true;
        } else {
            $this->log("Schema validation failed - missing tables: " . implode(', ', $missingTables), 'ERROR');
            return false;
        }
    }
    
    private function log($message, $level = 'INFO') {
        $timestamp = date('Y-m-d H:i:s');
        $logMessage = "[{$timestamp}] [{$level}] {$message}" . PHP_EOL;
        
        // Ensure logs directory exists
        $logDir = dirname($this->logFile);
        if (!is_dir($logDir)) {
            mkdir($logDir, 0755, true);
        }
        
        // Write to log file
        file_put_contents($this->logFile, $logMessage, FILE_APPEND | LOCK_EX);
        
        // Also output to console
        echo $logMessage;
    }
}

// Command line interface
if (php_sapi_name() === 'cli') {
    $action = $argv[1] ?? 'migrate';
    
    try {
        $migration = new ReportingModuleMigration();
        
        switch ($action) {
            case 'migrate':
                $migration->migrate();
                echo "Migration completed successfully!\n";
                break;
                
            case 'rollback':
                $migration->rollback();
                echo "Rollback completed successfully!\n";
                break;
                
            case 'validate':
                if ($migration->validateSchema()) {
                    echo "Schema validation passed!\n";
                    exit(0);
                } else {
                    echo "Schema validation failed!\n";
                    exit(1);
                }
                break;
                
            default:
                echo "Usage: php migrate_reporting_schema.php [migrate|rollback|validate]\n";
                exit(1);
        }
        
    } catch (Exception $e) {
        echo "Error: " . $e->getMessage() . "\n";
        exit(1);
    }
}