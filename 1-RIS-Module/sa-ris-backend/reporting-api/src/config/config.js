/**
 * SA Medical Reporting Module - Configuration
 * 
 * Central configuration management for the reporting API
 * Loads environment variables and provides default values
 * 
 * @package SA_RIS
 * @author Ubuntu Patient Sorg Team
 * @copyright 2025
 */

const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '../../../.env') });

const config = {
    // Environment
    env: process.env.NODE_ENV || 'development',
    
    // Server configuration
    server: {
        port: parseInt(process.env.REPORTING_API_PORT) || 3001,
        host: process.env.REPORTING_API_HOST || '0.0.0.0',
        timezone: process.env.APP_TIMEZONE || 'Africa/Johannesburg'
    },
    
    // Database configuration
    database: {
        reporting: {
            host: process.env.REPORTING_DB_HOST || 'localhost',
            port: parseInt(process.env.REPORTING_DB_PORT) || 5432,
            database: process.env.REPORTING_DB_NAME || 'sa_ris_reporting',
            username: process.env.REPORTING_DB_USERNAME || 'sa_ris_user',
            password: process.env.REPORTING_DB_PASSWORD || '',
            dialect: 'postgres',
            pool: {
                max: 20,
                min: 5,
                acquire: 30000,
                idle: 10000
            }
        },
        legacy: {
            host: process.env.LEGACY_DB_HOST || 'localhost',
            port: parseInt(process.env.LEGACY_DB_PORT) || 3306,
            database: process.env.LEGACY_DB_NAME || 'sa_ris_db',
            username: process.env.LEGACY_DB_USERNAME || 'sa_ris_user',
            password: process.env.LEGACY_DB_PASSWORD || '',
            dialect: 'mysql'
        },
        openemr: {
            host: process.env.OPENEMR_DB_HOST || 'localhost',
            port: parseInt(process.env.OPENEMR_DB_PORT) || 3306,
            database: process.env.OPENEMR_DB_NAME || 'openemr',
            username: process.env.OPENEMR_DB_USERNAME || 'openemr',
            password: process.env.OPENEMR_DB_PASSWORD || '',
            dialect: 'mysql'
        }
    },
    
    // Redis configuration
    redis: {
        host: process.env.REDIS_HOST || 'localhost',
        port: parseInt(process.env.REDIS_PORT) || 6379,
        password: process.env.REDIS_PASSWORD || null,
        db: parseInt(process.env.REDIS_DB) || 0,
        retryDelayOnFailover: 100,
        maxRetriesPerRequest: 3
    },
    
    // JWT configuration
    jwt: {
        secret: process.env.JWT_SECRET || 'your-super-secret-jwt-key',
        expiresIn: process.env.JWT_EXPIRY || '24h',
        issuer: 'sa-medical-reporting',
        audience: 'sa-ris-users'
    },
    
    // CORS configuration
    cors: {
        origins: process.env.CORS_ORIGINS ? 
            process.env.CORS_ORIGINS.split(',') : 
            ['http://localhost:3000', 'https://localhost:3000']
    },
    
    // Rate limiting
    rateLimit: {
        windowMs: 15 * 60 * 1000, // 15 minutes
        max: parseInt(process.env.API_RATE_LIMIT) || 100
    },
    
    // Speech-to-Text configuration
    stt: {
        serviceUrl: process.env.STT_SERVICE_URL || 'http://localhost:8080',
        modelPath: process.env.STT_MODEL_PATH || '/app/models/vosk-model-en-za-0.22',
        language: process.env.STT_LANGUAGE || 'en-ZA',
        sampleRate: parseInt(process.env.STT_SAMPLE_RATE) || 16000,
        enableMedicalDictionary: process.env.STT_ENABLE_MEDICAL_DICTIONARY === 'true',
        confidenceThreshold: parseFloat(process.env.STT_CONFIDENCE_THRESHOLD) || 0.7
    },
    
    // Audio storage configuration
    audio: {
        storagePath: process.env.AUDIO_STORAGE_PATH || path.join(__dirname, '../../../audio_storage'),
        encryptionEnabled: process.env.AUDIO_ENCRYPTION_ENABLED === 'true',
        retentionDays: parseInt(process.env.AUDIO_RETENTION_DAYS) || 365,
        maxFileSize: process.env.AUDIO_MAX_FILE_SIZE || '100MB',
        allowedFormats: process.env.AUDIO_ALLOWED_FORMATS ? 
            process.env.AUDIO_ALLOWED_FORMATS.split(',') : 
            ['wav', 'mp3', 'ogg']
    },
    
    // Transcriptionist workflow configuration
    transcription: {
        queueSize: parseInt(process.env.TRANSCRIPTIONIST_QUEUE_SIZE) || 50,
        autoAssign: process.env.TRANSCRIPTIONIST_AUTO_ASSIGN === 'true',
        workloadBalance: process.env.TRANSCRIPTIONIST_WORKLOAD_BALANCE === 'true',
        qualityThreshold: parseFloat(process.env.TRANSCRIPTIONIST_QUALITY_THRESHOLD) || 8.0
    },
    
    // Doctor authorization configuration
    authorization: {
        mfaRequired: process.env.DOCTOR_MFA_REQUIRED === 'true',
        signatureAlgorithm: process.env.DOCTOR_SIGNATURE_ALGORITHM || 'RSA-SHA256',
        sessionTimeout: parseInt(process.env.DOCTOR_SESSION_TIMEOUT) || 30,
        batchAuthorizeLimit: parseInt(process.env.DOCTOR_BATCH_AUTHORIZE_LIMIT) || 10
    },
    
    // Report templates configuration
    templates: {
        enabled: process.env.REPORT_TEMPLATES_ENABLED === 'true',
        path: process.env.REPORT_TEMPLATES_PATH || path.join(__dirname, '../../../templates'),
        autoPopulate: process.env.REPORT_AUTO_POPULATE === 'true'
    },
    
    // Workflow configuration
    workflow: {
        timeoutMinutes: parseInt(process.env.WORKFLOW_TIMEOUT_MINUTES) || 480,
        escalationEnabled: process.env.WORKFLOW_ESCALATION_ENABLED === 'true',
        notificationsEnabled: process.env.WORKFLOW_NOTIFICATIONS_ENABLED === 'true',
        performanceTracking: process.env.WORKFLOW_PERFORMANCE_TRACKING === 'true'
    },
    
    // Integration configuration
    integration: {
        openemr: {
            enabled: process.env.INTEGRATION_OPENEMR_ENABLED === 'true',
            baseUrl: process.env.OPENEMR_BASE_URL || 'http://localhost:8080',
            apiKey: process.env.OPENEMR_API_KEY || '',
            timeout: parseInt(process.env.OPENEMR_TIMEOUT) || 30000
        },
        orthanc: {
            enabled: process.env.INTEGRATION_ORTHANC_ENABLED === 'true',
            baseUrl: process.env.ORTHANC_URL || 'http://localhost:8042',
            username: process.env.ORTHANC_USERNAME || 'orthanc',
            password: process.env.ORTHANC_PASSWORD || 'orthanc',
            timeout: parseInt(process.env.ORTHANC_TIMEOUT) || 30000
        },
        billing: {
            enabled: process.env.INTEGRATION_BILLING_ENABLED === 'true',
            syncInterval: parseInt(process.env.INTEGRATION_SYNC_INTERVAL) || 300
        }
    },
    
    // Email configuration
    email: {
        host: process.env.MAIL_HOST || 'localhost',
        port: parseInt(process.env.MAIL_PORT) || 587,
        secure: process.env.MAIL_ENCRYPTION === 'ssl',
        auth: {
            user: process.env.MAIL_USERNAME || '',
            pass: process.env.MAIL_PASSWORD || ''
        },
        from: {
            name: process.env.MAIL_FROM_NAME || 'SA Medical Reporting',
            address: process.env.MAIL_FROM_ADDRESS || 'noreply@sa-ris.local'
        }
    },
    
    // SMS configuration
    sms: {
        provider: process.env.SMS_PROVIDER || 'twilio',
        apiKey: process.env.SMS_API_KEY || '',
        fromNumber: process.env.SMS_FROM_NUMBER || '',
        enabled: process.env.SMS_ENABLED === 'true'
    },
    
    // File upload configuration
    upload: {
        maxFileSize: process.env.MAX_UPLOAD_SIZE || '50MB',
        allowedMimeTypes: [
            'audio/wav',
            'audio/mpeg',
            'audio/ogg',
            'application/pdf',
            'image/jpeg',
            'image/png',
            'application/dicom'
        ],
        tempPath: process.env.UPLOAD_TEMP_PATH || path.join(__dirname, '../../../temp')
    },
    
    // Security configuration
    security: {
        encryptionKey: process.env.ENCRYPTION_KEY || 'your-32-character-encryption-key',
        hashRounds: parseInt(process.env.HASH_ROUNDS) || 12,
        sessionSecret: process.env.SESSION_SECRET || 'your-session-secret',
        csrfEnabled: process.env.CSRF_ENABLED === 'true'
    },
    
    // Logging configuration
    logging: {
        level: process.env.LOG_LEVEL || 'info',
        file: process.env.LOG_FILE || path.join(__dirname, '../../../logs/reporting-api.log'),
        maxSize: process.env.LOG_MAX_SIZE || '10MB',
        maxFiles: parseInt(process.env.LOG_MAX_FILES) || 5,
        auditEnabled: process.env.AUDIT_LOG_ENABLED === 'true'
    },
    
    // Performance monitoring
    monitoring: {
        enabled: process.env.MONITORING_ENABLED === 'true',
        metricsInterval: parseInt(process.env.METRICS_INTERVAL) || 60000,
        healthCheckInterval: parseInt(process.env.HEALTH_CHECK_INTERVAL) || 30000
    },
    
    // POPI Act compliance
    compliance: {
        enabled: process.env.POPI_COMPLIANCE_ENABLED === 'true',
        dataRetentionYears: parseInt(process.env.DATA_RETENTION_YEARS) || 7,
        auditLogRetentionYears: parseInt(process.env.AUDIT_LOG_RETENTION_YEARS) || 10,
        anonymizationEnabled: process.env.ANONYMIZATION_ENABLED === 'true',
        consentExpiryMonths: parseInt(process.env.CONSENT_EXPIRY_MONTHS) || 24
    }
};

// Validate required configuration
function validateConfig() {
    const required = [
        'database.reporting.host',
        'database.reporting.username',
        'database.reporting.password',
        'jwt.secret',
        'security.encryptionKey'
    ];
    
    const missing = [];
    
    required.forEach(key => {
        const value = key.split('.').reduce((obj, k) => obj && obj[k], config);
        if (!value) {
            missing.push(key);
        }
    });
    
    if (missing.length > 0) {
        throw new Error(`Missing required configuration: ${missing.join(', ')}`);
    }
}

// Validate configuration on load
if (config.env === 'production') {
    validateConfig();
}

module.exports = config;