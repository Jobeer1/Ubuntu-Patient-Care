/**
 * SA Medical Reporting Module - Database Connection
 * 
 * Database connection management for PostgreSQL (reporting) and MySQL (legacy/OpenEMR)
 * Provides connection pooling and health monitoring
 * 
 * @package SA_RIS
 * @author Ubuntu Patient Sorg Team
 * @copyright 2025
 */

const { Pool } = require('pg');
const mysql = require('mysql2/promise');
const config = require('../config/config');
const logger = require('../utils/logger');

class DatabaseConnection {
    constructor() {
        this.pools = {};
        this.healthStatus = {};
        this.initializePools();
    }
    
    initializePools() {
        // PostgreSQL pool for reporting module
        this.pools.reporting = new Pool({
            host: config.database.reporting.host,
            port: config.database.reporting.port,
            database: config.database.reporting.database,
            user: config.database.reporting.username,
            password: config.database.reporting.password,
            max: config.database.reporting.pool.max,
            min: config.database.reporting.pool.min,
            idleTimeoutMillis: config.database.reporting.pool.idle,
            connectionTimeoutMillis: config.database.reporting.pool.acquire,
            ssl: config.env === 'production' ? { rejectUnauthorized: false } : false
        });
        
        // MySQL pool for legacy SA RIS
        this.pools.legacy = mysql.createPool({
            host: config.database.legacy.host,
            port: config.database.legacy.port,
            database: config.database.legacy.database,
            user: config.database.legacy.username,
            password: config.database.legacy.password,
            waitForConnections: true,
            connectionLimit: 10,
            queueLimit: 0,
            acquireTimeout: 30000,
            timeout: 60000,
            reconnect: true,
            charset: 'utf8mb4'
        });
        
        // MySQL pool for OpenEMR
        this.pools.openemr = mysql.createPool({
            host: config.database.openemr.host,
            port: config.database.openemr.port,
            database: config.database.openemr.database,
            user: config.database.openemr.username,
            password: config.database.openemr.password,
            waitForConnections: true,
            connectionLimit: 10,
            queueLimit: 0,
            acquireTimeout: 30000,
            timeout: 60000,
            reconnect: true,
            charset: 'utf8mb4'
        });
        
        // Set up error handlers
        this.setupErrorHandlers();
        
        // Start health monitoring
        this.startHealthMonitoring();
    }
    
    setupErrorHandlers() {
        // PostgreSQL error handling
        this.pools.reporting.on('error', (err) => {
            logger.error('PostgreSQL pool error:', err);
            this.healthStatus.reporting = false;
        });
        
        this.pools.reporting.on('connect', () => {
            logger.info('PostgreSQL client connected');
            this.healthStatus.reporting = true;
        });
        
        // MySQL error handling for legacy
        this.pools.legacy.on('connection', (connection) => {
            logger.info('MySQL legacy connection established');
            this.healthStatus.legacy = true;
        });
        
        this.pools.legacy.on('error', (err) => {
            logger.error('MySQL legacy pool error:', err);
            this.healthStatus.legacy = false;
        });
        
        // MySQL error handling for OpenEMR
        this.pools.openemr.on('connection', (connection) => {
            logger.info('MySQL OpenEMR connection established');
            this.healthStatus.openemr = true;
        });
        
        this.pools.openemr.on('error', (err) => {
            logger.error('MySQL OpenEMR pool error:', err);
            this.healthStatus.openemr = false;
        });
    }
    
    startHealthMonitoring() {
        setInterval(async () => {
            await this.checkHealth();
        }, config.monitoring.healthCheckInterval);
    }
    
    async checkHealth() {
        const healthChecks = {
            reporting: this.checkPostgreSQLHealth(),
            legacy: this.checkMySQLHealth('legacy'),
            openemr: this.checkMySQLHealth('openemr')
        };
        
        try {
            const results = await Promise.allSettled(Object.values(healthChecks));
            
            this.healthStatus.reporting = results[0].status === 'fulfilled';
            this.healthStatus.legacy = results[1].status === 'fulfilled';
            this.healthStatus.openemr = results[2].status === 'fulfilled';
            
            const unhealthyConnections = Object.entries(this.healthStatus)
                .filter(([_, healthy]) => !healthy)
                .map(([name, _]) => name);
            
            if (unhealthyConnections.length > 0) {
                logger.warn(`Unhealthy database connections: ${unhealthyConnections.join(', ')}`);
            }
            
        } catch (error) {
            logger.error('Health check error:', error);
        }
    }
    
    async checkPostgreSQLHealth() {
        const client = await this.pools.reporting.connect();
        try {
            await client.query('SELECT 1');
            return true;
        } finally {
            client.release();
        }
    }
    
    async checkMySQLHealth(poolName) {
        const connection = await this.pools[poolName].getConnection();
        try {
            await connection.execute('SELECT 1');
            return true;
        } finally {
            connection.release();
        }
    }
    
    // Get connection for specific database
    async getConnection(database = 'reporting') {
        if (!this.pools[database]) {
            throw new Error(`Unknown database: ${database}`);
        }
        
        if (database === 'reporting') {
            return await this.pools.reporting.connect();
        } else {
            return await this.pools[database].getConnection();
        }
    }
    
    // Execute query on specific database
    async query(database, sql, params = []) {
        const startTime = Date.now();
        let connection;
        
        try {
            connection = await this.getConnection(database);
            
            let result;
            if (database === 'reporting') {
                result = await connection.query(sql, params);
                return result.rows;
            } else {
                const [rows] = await connection.execute(sql, params);
                return rows;
            }
            
        } catch (error) {
            logger.error(`Database query error (${database}):`, {
                sql: sql.substring(0, 100) + '...',
                params,
                error: error.message
            });
            throw error;
            
        } finally {
            if (connection) {
                if (database === 'reporting') {
                    connection.release();
                } else {
                    connection.release();
                }
            }
            
            const duration = Date.now() - startTime;
            if (duration > 1000) {
                logger.warn(`Slow query detected (${duration}ms):`, {
                    database,
                    sql: sql.substring(0, 100) + '...'
                });
            }
        }
    }
    
    // Transaction support
    async transaction(database, callback) {
        let connection;
        
        try {
            connection = await this.getConnection(database);
            
            if (database === 'reporting') {
                await connection.query('BEGIN');
            } else {
                await connection.beginTransaction();
            }
            
            const result = await callback(connection);
            
            if (database === 'reporting') {
                await connection.query('COMMIT');
            } else {
                await connection.commit();
            }
            
            return result;
            
        } catch (error) {
            if (connection) {
                try {
                    if (database === 'reporting') {
                        await connection.query('ROLLBACK');
                    } else {
                        await connection.rollback();
                    }
                } catch (rollbackError) {
                    logger.error('Transaction rollback error:', rollbackError);
                }
            }
            throw error;
            
        } finally {
            if (connection) {
                if (database === 'reporting') {
                    connection.release();
                } else {
                    connection.release();
                }
            }
        }
    }
    
    // Batch operations
    async batchInsert(database, table, records, batchSize = 1000) {
        if (!records || records.length === 0) {
            return { inserted: 0, errors: [] };
        }
        
        const results = { inserted: 0, errors: [] };
        
        for (let i = 0; i < records.length; i += batchSize) {
            const batch = records.slice(i, i + batchSize);
            
            try {
                await this.transaction(database, async (connection) => {
                    for (const record of batch) {
                        const columns = Object.keys(record);
                        const values = Object.values(record);
                        const placeholders = values.map((_, index) => 
                            database === 'reporting' ? `$${index + 1}` : '?'
                        ).join(', ');
                        
                        const sql = `INSERT INTO ${table} (${columns.join(', ')}) VALUES (${placeholders})`;
                        
                        if (database === 'reporting') {
                            await connection.query(sql, values);
                        } else {
                            await connection.execute(sql, values);
                        }
                        
                        results.inserted++;
                    }
                });
                
            } catch (error) {
                logger.error(`Batch insert error for batch starting at index ${i}:`, error);
                results.errors.push({
                    batchStart: i,
                    batchSize: batch.length,
                    error: error.message
                });
            }
        }
        
        return results;
    }
    
    // Get database statistics
    async getStats() {
        const stats = {};
        
        try {
            // PostgreSQL stats
            const pgStats = await this.query('reporting', `
                SELECT 
                    numbackends as active_connections,
                    xact_commit as transactions_committed,
                    xact_rollback as transactions_rolled_back,
                    blks_read as blocks_read,
                    blks_hit as blocks_hit,
                    tup_returned as tuples_returned,
                    tup_fetched as tuples_fetched,
                    tup_inserted as tuples_inserted,
                    tup_updated as tuples_updated,
                    tup_deleted as tuples_deleted
                FROM pg_stat_database 
                WHERE datname = $1
            `, [config.database.reporting.database]);
            
            stats.reporting = pgStats[0] || {};
            
            // MySQL stats for legacy
            const mysqlLegacyStats = await this.query('legacy', `
                SHOW STATUS WHERE Variable_name IN (
                    'Threads_connected', 'Queries', 'Com_select', 'Com_insert', 
                    'Com_update', 'Com_delete', 'Innodb_buffer_pool_reads',
                    'Innodb_buffer_pool_read_requests'
                )
            `);
            
            stats.legacy = {};
            mysqlLegacyStats.forEach(row => {
                stats.legacy[row.Variable_name.toLowerCase()] = parseInt(row.Value) || row.Value;
            });
            
            // MySQL stats for OpenEMR
            const mysqlOpenEMRStats = await this.query('openemr', `
                SHOW STATUS WHERE Variable_name IN (
                    'Threads_connected', 'Queries', 'Com_select', 'Com_insert', 
                    'Com_update', 'Com_delete'
                )
            `);
            
            stats.openemr = {};
            mysqlOpenEMRStats.forEach(row => {
                stats.openemr[row.Variable_name.toLowerCase()] = parseInt(row.Value) || row.Value;
            });
            
        } catch (error) {
            logger.error('Error getting database stats:', error);
        }
        
        return stats;
    }
    
    // Test all connections
    async testConnection() {
        const results = {};
        
        try {
            await this.checkPostgreSQLHealth();
            results.reporting = { status: 'connected', error: null };
        } catch (error) {
            results.reporting = { status: 'error', error: error.message };
        }
        
        try {
            await this.checkMySQLHealth('legacy');
            results.legacy = { status: 'connected', error: null };
        } catch (error) {
            results.legacy = { status: 'error', error: error.message };
        }
        
        try {
            await this.checkMySQLHealth('openemr');
            results.openemr = { status: 'connected', error: null };
        } catch (error) {
            results.openemr = { status: 'error', error: error.message };
        }
        
        return results;
    }
    
    // Close all connections
    async close() {
        const closePromises = [];
        
        if (this.pools.reporting) {
            closePromises.push(this.pools.reporting.end());
        }
        
        if (this.pools.legacy) {
            closePromises.push(this.pools.legacy.end());
        }
        
        if (this.pools.openemr) {
            closePromises.push(this.pools.openemr.end());
        }
        
        await Promise.all(closePromises);
        logger.info('All database connections closed');
    }
    
    // Get health status
    getHealthStatus() {
        return {
            ...this.healthStatus,
            overall: Object.values(this.healthStatus).every(status => status)
        };
    }
}

// Create singleton instance
const database = new DatabaseConnection();

module.exports = database;