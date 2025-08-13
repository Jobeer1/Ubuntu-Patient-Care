/**
 * SA Medical Reporting Module - Logger Utility
 * 
 * Winston-based logging with file rotation and structured logging
 * Supports different log levels and audit trail logging
 * 
 * @package SA_RIS
 * @author Ubuntu Patient Sorg Team
 * @copyright 2025
 */

const winston = require('winston');
const path = require('path');
const fs = require('fs');
const config = require('../config/config');

// Ensure logs directory exists
const logsDir = path.dirname(config.logging.file);
if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir, { recursive: true });
}

// Custom format for structured logging
const customFormat = winston.format.combine(
    winston.format.timestamp({
        format: 'YYYY-MM-DD HH:mm:ss.SSS'
    }),
    winston.format.errors({ stack: true }),
    winston.format.json(),
    winston.format.printf(({ timestamp, level, message, ...meta }) => {
        let logEntry = {
            timestamp,
            level: level.toUpperCase(),
            message,
            ...meta
        };
        
        // Add request context if available
        if (meta.req) {
            logEntry.request = {
                method: meta.req.method,
                url: meta.req.url,
                ip: meta.req.ip,
                userAgent: meta.req.get('User-Agent'),
                userId: meta.req.user?.id
            };
            delete logEntry.req;
        }
        
        // Add error details if present
        if (meta.error && meta.error instanceof Error) {
            logEntry.error = {
                name: meta.error.name,
                message: meta.error.message,
                stack: meta.error.stack
            };
            delete logEntry.error;
        }
        
        return JSON.stringify(logEntry);
    })
);

// Console format for development
const consoleFormat = winston.format.combine(
    winston.format.colorize(),
    winston.format.timestamp({
        format: 'HH:mm:ss'
    }),
    winston.format.printf(({ timestamp, level, message, ...meta }) => {
        let output = `${timestamp} [${level}] ${message}`;
        
        if (Object.keys(meta).length > 0) {
            output += ` ${JSON.stringify(meta, null, 2)}`;
        }
        
        return output;
    })
);

// Create logger instance
const logger = winston.createLogger({
    level: config.logging.level,
    format: customFormat,
    defaultMeta: {
        service: 'sa-medical-reporting',
        environment: config.env,
        version: process.env.npm_package_version || '1.0.0'
    },
    transports: [
        // File transport with rotation
        new winston.transports.File({
            filename: config.logging.file,
            maxsize: config.logging.maxSize,
            maxFiles: config.logging.maxFiles,
            tailable: true,
            zippedArchive: true
        }),
        
        // Error file transport
        new winston.transports.File({
            filename: path.join(logsDir, 'error.log'),
            level: 'error',
            maxsize: config.logging.maxSize,
            maxFiles: config.logging.maxFiles,
            tailable: true,
            zippedArchive: true
        })
    ],
    
    // Handle uncaught exceptions and rejections
    exceptionHandlers: [
        new winston.transports.File({
            filename: path.join(logsDir, 'exceptions.log'),
            maxsize: config.logging.maxSize,
            maxFiles: 3
        })
    ],
    
    rejectionHandlers: [
        new winston.transports.File({
            filename: path.join(logsDir, 'rejections.log'),
            maxsize: config.logging.maxSize,
            maxFiles: 3
        })
    ]
});

// Add console transport for development
if (config.env !== 'production') {
    logger.add(new winston.transports.Console({
        format: consoleFormat,
        level: 'debug'
    }));
}

// Audit logger for POPI compliance
const auditLogger = winston.createLogger({
    level: 'info',
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
    ),
    transports: [
        new winston.transports.File({
            filename: path.join(logsDir, 'audit.log'),
            maxsize: '50MB',
            maxFiles: 10,
            tailable: true,
            zippedArchive: true
        })
    ]
});

// Performance logger
const performanceLogger = winston.createLogger({
    level: 'info',
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
    ),
    transports: [
        new winston.transports.File({
            filename: path.join(logsDir, 'performance.log'),
            maxsize: '20MB',
            maxFiles: 5,
            tailable: true,
            zippedArchive: true
        })
    ]
});

// Security logger
const securityLogger = winston.createLogger({
    level: 'warn',
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
    ),
    transports: [
        new winston.transports.File({
            filename: path.join(logsDir, 'security.log'),
            maxsize: '20MB',
            maxFiles: 10,
            tailable: true,
            zippedArchive: true
        })
    ]
});

// Helper functions for structured logging
const logHelpers = {
    // Log database operations
    logDatabaseOperation(operation, table, duration, recordCount = null) {
        performanceLogger.info('Database Operation', {
            operation,
            table,
            duration,
            recordCount,
            timestamp: new Date().toISOString()
        });
    },
    
    // Log API requests
    logApiRequest(req, res, duration) {
        const logData = {
            method: req.method,
            url: req.originalUrl,
            statusCode: res.statusCode,
            duration,
            ip: req.ip,
            userAgent: req.get('User-Agent'),
            userId: req.user?.id,
            contentLength: res.get('Content-Length'),
            timestamp: new Date().toISOString()
        };
        
        if (res.statusCode >= 400) {
            logger.warn('API Request Error', logData);
        } else {
            logger.info('API Request', logData);
        }
        
        // Log performance issues
        if (duration > 5000) {
            performanceLogger.warn('Slow API Request', logData);
        }
    },
    
    // Log user actions for audit trail
    logUserAction(userId, action, resourceType, resourceId, details = {}) {
        if (!config.compliance.enabled) return;
        
        auditLogger.info('User Action', {
            userId,
            action,
            resourceType,
            resourceId,
            details,
            timestamp: new Date().toISOString(),
            sessionId: details.sessionId,
            ipAddress: details.ipAddress
        });
    },
    
    // Log security events
    logSecurityEvent(eventType, severity, details, req = null) {
        const logData = {
            eventType,
            severity,
            details,
            timestamp: new Date().toISOString()
        };
        
        if (req) {
            logData.request = {
                ip: req.ip,
                userAgent: req.get('User-Agent'),
                url: req.originalUrl,
                method: req.method,
                userId: req.user?.id
            };
        }
        
        securityLogger.warn('Security Event', logData);
        
        // Also log to main logger for high severity events
        if (severity === 'high' || severity === 'critical') {
            logger.error('Security Alert', logData);
        }
    },
    
    // Log workflow state changes
    logWorkflowStateChange(reportId, fromState, toState, userId, duration = null) {
        auditLogger.info('Workflow State Change', {
            reportId,
            fromState,
            toState,
            userId,
            duration,
            timestamp: new Date().toISOString()
        });
    },
    
    // Log STT processing
    logSTTProcessing(sessionId, duration, confidence, wordCount, success) {
        performanceLogger.info('STT Processing', {
            sessionId,
            duration,
            confidence,
            wordCount,
            success,
            timestamp: new Date().toISOString()
        });
    },
    
    // Log medical aid integration
    logMedicalAidIntegration(scheme, operation, success, duration, details = {}) {
        const logData = {
            scheme,
            operation,
            success,
            duration,
            details,
            timestamp: new Date().toISOString()
        };
        
        if (success) {
            logger.info('Medical Aid Integration', logData);
        } else {
            logger.error('Medical Aid Integration Failed', logData);
        }
    },
    
    // Log system health metrics
    logHealthMetrics(metrics) {
        performanceLogger.info('System Health', {
            ...metrics,
            timestamp: new Date().toISOString()
        });
    }
};

// Extend logger with helper functions
Object.assign(logger, logHelpers);

// Add specialized loggers
logger.audit = auditLogger;
logger.performance = performanceLogger;
logger.security = securityLogger;

// Log startup information
logger.info('Logger initialized', {
    level: config.logging.level,
    environment: config.env,
    logFile: config.logging.file,
    auditEnabled: config.compliance.enabled
});

module.exports = logger;