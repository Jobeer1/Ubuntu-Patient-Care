# Universal Database Setup for SA PACS

## 🎯 **Easy Database Connection Guide**

The SA PACS system can connect to **ANY database** easily. Choose your preferred database and follow the simple setup instructions below.

## 📋 **Supported Databases**

✅ **SQLite** - Default, no setup required  
✅ **MySQL/MariaDB** - Popular open-source database  
✅ **PostgreSQL** - Advanced open-source database  
✅ **Firebird** - Lightweight enterprise database  
✅ **SQL Server** - Microsoft enterprise database  
✅ **Oracle** - Enterprise database  

## 🚀 **Quick Setup Methods**

### Method 1: Configuration File (Recommended)
1. Copy the appropriate config file from `database-config-examples/`
2. Edit the connection details
3. Start Orthanc with: `--sa-db-config=your-config.json`

### Method 2: Environment Variables
Set these environment variables and restart Orthanc:
```bash
export SA_DB_TYPE=mysql
export SA_DB_HOST=localhost
export SA_DB_PORT=3306
export SA_DB_NAME=orthanc_sa
export SA_DB_USER=orthanc_user
export SA_DB_PASSWORD=your_password
```

### Method 3: Connection String
Set a direct connection string:
```bash
export SA_DB_CONNECTION_STRING="mysql://user:pass@localhost:3306/orthanc_sa"
```

## 🔧 **Database-Specific Setup**

### MySQL/MariaDB Setup
```sql
-- 1. Create database and user
CREATE DATABASE orthanc_sa CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'orthanc_user'@'%' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON orthanc_sa.* TO 'orthanc_user'@'%';
FLUSH PRIVILEGES;

-- 2. Use config file
cp database-config-examples/mysql-config.json mysql-sa.json
# Edit mysql-sa.json with your details

-- 3. Start Orthanc
./Orthanc --sa-db-config=mysql-sa.json
```

### PostgreSQL Setup
```sql
-- 1. Create database and user
CREATE DATABASE orthanc_sa WITH ENCODING 'UTF8';
CREATE USER orthanc_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE orthanc_sa TO orthanc_user;

-- 2. Use config file
cp database-config-examples/postgresql-config.json postgres-sa.json
# Edit postgres-sa.json with your details

-- 3. Start Orthanc
./Orthanc --sa-db-config=postgres-sa.json
```

### Firebird Setup
```bash
# 1. Create database
isql -user SYSDBA -password masterkey
CREATE DATABASE '/path/to/orthanc_sa.fdb' PAGE_SIZE 16384 DEFAULT CHARACTER SET UTF8;
QUIT;

# 2. Use config file
cp database-config-examples/firebird-config.json firebird-sa.json
# Edit firebird-sa.json with your details

# 3. Start Orthanc
./Orthanc --sa-db-config=firebird-sa.json
```

### SQL Server Setup
```sql
-- 1. Create database and user
CREATE DATABASE orthanc_sa;
CREATE LOGIN orthanc_user WITH PASSWORD = 'SecurePassword123!';
USE orthanc_sa;
CREATE USER orthanc_user FOR LOGIN orthanc_user;
ALTER ROLE db_owner ADD MEMBER orthanc_user;

-- 2. Use config file
cp database-config-examples/sqlserver-config.json sqlserver-sa.json
# Edit sqlserver-sa.json with your details

-- 3. Start Orthanc
./Orthanc --sa-db-config=sqlserver-sa.json
```

### Oracle Setup
```sql
-- 1. Create user and tablespace
CREATE TABLESPACE orthanc_sa_data DATAFILE 'orthanc_sa_data.dbf' SIZE 100M AUTOEXTEND ON;
CREATE USER orthanc_user IDENTIFIED BY secure_password DEFAULT TABLESPACE orthanc_sa_data;
GRANT CONNECT, RESOURCE, DBA TO orthanc_user;

-- 2. Use config file
cp database-config-examples/oracle-config.json oracle-sa.json
# Edit oracle-sa.json with your details

-- 3. Start Orthanc
./Orthanc --sa-db-config=oracle-sa.json
```

## 🔒 **SSL/TLS Configuration**

For secure connections, add SSL configuration to your config file:

```json
{
  "use_ssl": true,
  "ssl_cert": "/path/to/client-cert.pem",
  "ssl_key": "/path/to/client-key.pem",
  "ssl_ca": "/path/to/ca-cert.pem"
}
```

## ⚡ **Performance Tuning**

### Connection Pool Settings
```json
{
  "min_connections": 2,
  "max_connections": 20,
  "connection_timeout": 30
}
```

### Database-Specific Options
Each database type supports specific optimization options in the `options` section:

**MySQL:**
```json
"options": {
  "charset": "utf8mb4",
  "autocommit": "true",
  "wait_timeout": "28800"
}
```

**PostgreSQL:**
```json
"options": {
  "sslmode": "require",
  "statement_timeout": "30000"
}
```

## 🧪 **Testing Your Connection**

After setup, test your database connection:

```bash
# Test connection
curl -X GET http://localhost:8042/sa/database/test

# Get database info
curl -X GET http://localhost:8042/sa/database/info

# Check SA tables
curl -X GET http://localhost:8042/sa/database/tables
```

## 🔄 **Migration from Existing Systems**

### From SQLite to MySQL/PostgreSQL
```bash
# 1. Export existing data
./orthanc-sa-migrate export --source=sqlite --output=sa-data.json

# 2. Setup new database
# Follow database-specific setup above

# 3. Import data
./orthanc-sa-migrate import --target=mysql --input=sa-data.json --config=mysql-sa.json
```

### From Flask App Databases
```bash
# Migrate from existing Flask databases
./orthanc-sa-migrate flask-import --flask-dir=orthanc-source/NASIntegration/backend --config=your-db.json
```

## 🚨 **Troubleshooting**

### Common Issues

**Connection Refused:**
- Check database server is running
- Verify host and port settings
- Check firewall settings

**Authentication Failed:**
- Verify username and password
- Check user permissions
- Ensure user can connect from Orthanc server IP

**SSL Errors:**
- Verify SSL certificate paths
- Check certificate validity
- Ensure SSL is enabled on database server

**Performance Issues:**
- Increase connection pool size
- Add database indexes
- Optimize database configuration

### Debug Mode
Enable debug logging:
```json
{
  "options": {
    "debug": "true",
    "log_level": "debug"
  }
}
```

## 📞 **Support**

For database-specific issues:
- **MySQL**: Check MySQL documentation and logs
- **PostgreSQL**: Check PostgreSQL logs and configuration
- **Firebird**: Check Firebird logs and connection settings
- **SQL Server**: Check SQL Server logs and network configuration
- **Oracle**: Check Oracle logs and TNS configuration

---

**🎉 Result**: Your SA PACS system can now connect to ANY database with just a simple configuration file!