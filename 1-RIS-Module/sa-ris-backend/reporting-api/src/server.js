/**
 * SA Medical Reporting Module - Main Server
 * 
 * Express.js server for the SA Medical Reporting Module
 * Handles voice dictation, transcription workflow, and doctor authorization
 * 
 * @package SA_RIS
 * @author Ubuntu Patient Sorg Team
 * @copyright 2025
 */

const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const morgan = require('morgan');
const path = require('path');

// Import configuration and utilities
const config = require('./config/config');
const logger = require('./utils/logger');
const database = require('./database/connection');
const redisClient = require('./utils/redis');

// Import middleware
const authMiddleware = require('./middleware/auth');
const errorHandler = require('./middleware/errorHandler');
const auditLogger = require('./middleware/auditLogger');

// Import routes
const reportRoutes = require('./routes/reports');
const dictationRoutes = require('./routes/dictation');
const transcriptionRoutes = require('./routes/transcription');
const authorizationRoutes = require('./routes/authorization');
const billingRoutes = require('./routes/billing');
const dicomRoutes = require('./routes/dicom');
const userRoutes = require('./routes/users');
const analyticsRoutes = require('./routes/analytics');
const healthRoutes = require('./routes/health');

// Import socket handlers
const socketHandlers = require('./sockets/handlers');

// Initialize Express app
const app = express();
const server = http.createServer(app);

// Initialize Socket.IO
const io = socketIo(server, {
    cors: {
        origin: config.cors.origins,
        methods: ['GET', 'POST'],
        credentials: true
    },
    transports: ['websocket', 'polling']
});

// Security middleware
app.use(helmet({
    contentSecurityPolicy: {
        directives: {
            defaultSrc: ["'self'"],
            styleSrc: ["'self'", "'unsafe-inline'"],
            scriptSrc: ["'self'"],
            imgSrc: ["'self'", "data:", "https:"],
            connectSrc: ["'self'", "ws:", "wss:"],
            fontSrc: ["'self'"],
            objectSrc: ["'none'"],
            mediaSrc: ["'self'"],
            frameSrc: ["'none'"],
        },
    },
    crossOriginEmbedderPolicy: false
}));

// CORS configuration
app.use(cors({
    origin: config.cors.origins,
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
}));

// Compression middleware
app.use(compression());

// Rate limiting
const limiter = rateLimit({
    windowMs: config.rateLimit.windowMs,
    max: config.rateLimit.max,
    message: {
        error: 'Too many requests from this IP, please try again later.',
        retryAfter: config.rateLimit.windowMs / 1000
    },
    standardHeaders: true,
    legacyHeaders: false,
});
app.use('/api/', limiter);

// Logging middleware
app.use(morgan('combined', {
    stream: {
        write: (message) => logger.info(message.trim())
    }
}));

// Body parsing middleware
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Static file serving
app.use('/uploads', express.static(path.join(__dirname, '../uploads')));
app.use('/audio', express.static(path.join(__dirname, '../audio_storage')));

// Audit logging middleware
app.use(auditLogger);

// Health check endpoint (before auth)
app.use('/health', healthRoutes);

// Authentication middleware (applied to all API routes)
app.use('/api', authMiddleware);

// API Routes
app.use('/api/reports', reportRoutes);
app.use('/api/dictation', dictationRoutes);
app.use('/api/transcription', transcriptionRoutes);
app.use('/api/authorization', authorizationRoutes);
app.use('/api/billing', billingRoutes);
app.use('/api/dicom', dicomRoutes);
app.use('/api/users', userRoutes);
app.use('/api/analytics', analyticsRoutes);

// Socket.IO connection handling
io.on('connection', (socket) => {
    logger.info(`Socket connected: ${socket.id}`);
    
    // Initialize socket handlers
    socketHandlers.initializeHandlers(socket, io);
    
    socket.on('disconnect', (reason) => {
        logger.info(`Socket disconnected: ${socket.id}, reason: ${reason}`);
    });
    
    socket.on('error', (error) => {
        logger.error(`Socket error: ${socket.id}`, error);
    });
});

// Error handling middleware (must be last)
app.use(errorHandler);

// 404 handler
app.use('*', (req, res) => {
    res.status(404).json({
        success: false,
        message: 'Endpoint not found',
        path: req.originalUrl
    });
});

// Graceful shutdown handling
process.on('SIGTERM', gracefulShutdown);
process.on('SIGINT', gracefulShutdown);

async function gracefulShutdown(signal) {
    logger.info(`Received ${signal}. Starting graceful shutdown...`);
    
    // Close server
    server.close(() => {
        logger.info('HTTP server closed');
    });
    
    // Close database connections
    try {
        await database.close();
        logger.info('Database connections closed');
    } catch (error) {
        logger.error('Error closing database connections:', error);
    }
    
    // Close Redis connection
    try {
        await redisClient.quit();
        logger.info('Redis connection closed');
    } catch (error) {
        logger.error('Error closing Redis connection:', error);
    }
    
    // Exit process
    process.exit(0);
}

// Start server
async function startServer() {
    try {
        // Test database connection
        await database.testConnection();
        logger.info('Database connection established');
        
        // Test Redis connection
        await redisClient.ping();
        logger.info('Redis connection established');
        
        // Start HTTP server
        const port = config.server.port;
        server.listen(port, () => {
            logger.info(`SA Medical Reporting API server started on port ${port}`);
            logger.info(`Environment: ${config.env}`);
            logger.info(`Socket.IO enabled on port ${port}`);
        });
        
    } catch (error) {
        logger.error('Failed to start server:', error);
        process.exit(1);
    }
}

// Initialize server
startServer();

// Export for testing
module.exports = { app, server, io };