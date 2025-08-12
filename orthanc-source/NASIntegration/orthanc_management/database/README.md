# Orthanc Management Module - Database Foundation

This directory contains the database foundation layer for the Orthanc Management Module, providing multi-database support and abstraction.

## 🏗️ Architecture Overview

The database foundation consists of four main components:

### 1. Schema Generator (`schema_generator.py`)
- **Universal Schema Definition**: Define database schemas once, generate for any supported database
- **Multi-Database Support**: MySQL, PostgreSQL, SQLite, Firebird, SQL Server, Oracle
- **Type Mapping**: Automatic translation of universal column types to database-specific types
- **Index Management**: Consistent index creation across database platforms
- **Constraint Handling**: Foreign keys, check constraints, and unique constraints

**Key Features:**
- Database-agnostic schema definitions using Python dataclasses
- Automatic SQL generation with proper quoting and syntax for each database
- Support for complex relationships and constraints
- Built-in South African healthcare compliance considerations

### 2. Connection Manager (`connection_manager.py`)
- **Multi-Database Connections**: Simultaneous connections to different database types
- **Connection Pooling**: Efficient connection management with async support
- **Transaction Management**: ACID compliance with proper rollback support
- **Configuration Management**: JSON-based configuration with environment support

**Supported Databases:**
- **MySQL** (via aiomysql)
- **PostgreSQL** (via asyncpg)
- **SQLite** (via aiosqlite)
- **Firebird** (via aioodbc)
- **SQL Server** (via aioodbc)
- **Oracle** (via aioodbc)

### 3. Migration System (`migration_system.py`)
- **Version Control**: Track database schema changes over time
- **Rollback Support**: Safe rollback to previous schema versions
- **Dependency Management**: Handle migration dependencies and ordering
- **Integrity Checking**: Checksum validation for migration integrity
- **Multi-Environment**: Support for development, staging, and production migrations

**Migration Features:**
- JSON-based migration definitions
- Automatic dependency resolution
- Rollback SQL generation
- Performance tracking
- Cross-database compatibility

### 4. Data Access Objects (`dao.py`)
- **High-Level Database Operations**: Abstract away SQL complexity
- **Type-Safe Operations**: Structured data access with validation
- **Automatic Query Generation**: Build complex queries from simple parameters
- **Result Standardization**: Consistent result handling across operations
- **Audit Trail Integration**: Built-in compliance logging

**DAO Classes:**
- `ReferringDoctorDAO`: Manage healthcare professional data
- `PatientReferralDAO`: Handle patient referral workflows
- `PatientAuthorizationDAO`: Control access permissions
- `PatientShareDAO`: Manage secure patient sharing
- `AuditLogDAO`: Comprehensive audit trail for HPCSA/POPIA compliance

## 🗄️ Database Schema

The Orthanc Management Module uses a comprehensive schema designed for South African healthcare compliance:

### Core Tables

#### `referring_doctors`
- Healthcare professional information
- HPCSA number validation
- Practice details and specializations
- Access level management
- Geographic distribution (provinces)

#### `patient_referrals` 
- Patient referral tracking
- Study association
- Clinical indications
- Priority management
- Status workflow

#### `patient_authorizations`
- Granular access control
- Time-based permissions
- Study-level security
- Access auditing
- Usage tracking

#### `patient_shares`
- Secure patient portals
- Token-based access
- Download controls
- Mobile optimization
- Notification integration

#### `orthanc_configs`
- Dynamic Orthanc configuration
- Environment management
- Version control
- Validation system
- Backup and restore

#### `orthanc_server_status`
- Real-time monitoring
- Performance metrics
- Resource utilization
- Error tracking
- Uptime monitoring

#### `audit_logs`
- Comprehensive audit trail
- HPCSA compliance
- POPIA data protection
- User activity tracking
- Compliance reporting

#### `notification_queue`
- Multi-channel notifications
- Email and SMS support
- Multi-language support
- Priority queuing
- Retry logic

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Core database support
pip install aiosqlite  # SQLite support (included)

# Optional database drivers
pip install aiomysql asyncpg  # MySQL/PostgreSQL
pip install aioodbc  # Firebird/SQL Server/Oracle
```

### 2. Configure Databases

Create `database_config.json`:

```json
{
  "sqlite_default": {
    "type": "sqlite",
    "file_path": "./orthanc_management.db"
  },
  "mysql_primary": {
    "type": "mysql",
    "host": "localhost",
    "port": 3306,
    "database": "orthanc_management",
    "username": "orthanc_user",
    "password": "orthanc_password"
  },
  "firebird_archive": {
    "type": "firebird",
    "file_path": "./archive.fdb",
    "username": "SYSDBA",
    "password": "masterkey"
  }
}
```

### 3. Initialize Database

```python
from database.connection_manager import setup_databases
from database.migration_system import MigrationManager

# Setup connections and schema
await setup_databases('database_config.json')

# Run migrations
migration_manager = MigrationManager()
await migration_manager.migrate_to_latest()
```

### 4. Use DAOs

```python
from database.dao import DAOFactory

# Create referring doctor
doctor_dao = DAOFactory.get_referring_doctor_dao()
doctor_data = {
    'name': 'Dr. Sarah Johnson',
    'hpcsa_number': 'HP12345',
    'email': 'sarah.johnson@practice.co.za',
    'specialization': 'Radiology',
    'province': 'Gauteng'
}

result = await doctor_dao.create(doctor_data)
if result.success:
    print(f"Created doctor: {result.data['id']}")
```

## 🔧 Database Operations

### Creating Records

```python
# Create patient referral
referral_dao = DAOFactory.get_patient_referral_dao()
referral_data = {
    'patient_id': 'PAT001',
    'patient_name': 'John Doe',
    'referring_doctor_id': 'DOC001',
    'study_type': 'MRI Brain',
    'clinical_indication': 'Chronic headaches',
    'priority': 'urgent'
}

result = await referral_dao.create(referral_data)
```

### Querying Records

```python
# Find doctor's referrals
doctor_referrals = await referral_dao.find_by_doctor('DOC001')

# Check patient authorization
auth_dao = DAOFactory.get_patient_authorization_dao()
access_result = await auth_dao.check_access(
    doctor_id='DOC001',
    patient_id='PAT001', 
    study_uid='1.2.3.4.5'
)
```

### Complex Queries

```python
# Find active doctors in specific province
doctor_dao = DAOFactory.get_referring_doctor_dao()
gauteng_doctors = await doctor_dao.find_all(
    conditions={
        'province': 'Gauteng',
        'is_active': True
    },
    order_by='name ASC'
)
```

## 🛡️ Security & Compliance

### HPCSA Compliance
- Healthcare professional validation
- Practice registration tracking
- Specialization verification
- Geographic practice monitoring

### POPIA Data Protection  
- Comprehensive audit logging
- Data access controls
- Retention policy management
- Consent tracking
- Data minimization

### Access Control
- Role-based permissions
- Time-limited access
- Study-level security
- Multi-factor authentication ready
- Session management

## 🔄 Migration Management

### Creating Migrations

```python
from database.migration_system import Migration

migration = Migration(
    version="002_001_000",
    name="Add Email Notifications",
    description="Add email notification preferences to doctors",
    up_sql=[
        "ALTER TABLE referring_doctors ADD COLUMN email_notifications BOOLEAN DEFAULT TRUE",
        "CREATE INDEX idx_doctors_email_notifications ON referring_doctors(email_notifications)"
    ],
    down_sql=[
        "DROP INDEX idx_doctors_email_notifications",
        "ALTER TABLE referring_doctors DROP COLUMN email_notifications"
    ]
)

# Save migration
migration_manager = MigrationManager()
migration_manager.save_migration(migration)
```

### Running Migrations

```python
# Apply all pending migrations
await migration_manager.migrate_to_latest()

# Rollback to specific version
await migration_manager.rollback_to_version("001_002_000")
```

## 📊 Monitoring & Analytics

### Server Status Tracking

```python
# Monitor Orthanc server
status_data = {
    'server_status': 'running',
    'cpu_usage': 45.2,
    'memory_usage': 2048000000,
    'active_connections': 12,
    'studies_count': 1523
}

# This would be done by monitoring service
```

### Compliance Reporting

```python
from datetime import datetime, timedelta

audit_dao = DAOFactory.get_audit_log_dao()

# Generate compliance report
start_date = datetime.now() - timedelta(days=30)
end_date = datetime.now()

report = await audit_dao.compliance_report(start_date, end_date)
```

## 🔌 Database Driver Requirements

### Required (Always Available)
- **SQLite**: Built-in Python support via `aiosqlite`

### Optional (Install as needed)
- **MySQL**: `pip install aiomysql`
- **PostgreSQL**: `pip install asyncpg`
- **Firebird**: `pip install aioodbc` + Firebird ODBC driver
- **SQL Server**: `pip install aioodbc` + SQL Server ODBC driver  
- **Oracle**: `pip install aioodbc` + Oracle ODBC driver

## 🌍 Multi-Language Support

The database foundation supports multi-language deployments:

- UTF-8 encoding throughout
- Multi-language notification templates
- Locale-aware data formatting
- South African language support (English, Afrikaans, etc.)

## 📈 Performance Optimization

### Connection Pooling
- Configurable pool sizes
- Connection recycling
- Timeout management
- Health checking

### Query Optimization
- Prepared statements
- Index usage analysis
- Query plan optimization
- Batch operations

### Caching Strategy
- Query result caching
- Schema caching
- Configuration caching
- Session data caching

## 🚨 Error Handling

### Database Errors
- Connection failure recovery
- Transaction rollback
- Constraint violation handling
- Data validation errors

### Application Errors
- Graceful degradation
- Error logging
- User feedback
- Recovery procedures

## 📋 Testing

### Unit Tests
```bash
pytest database/tests/
```

### Integration Tests
```bash
pytest database/tests/integration/
```

### Performance Tests
```bash
pytest database/tests/performance/
```

## 🔍 Troubleshooting

### Common Issues

1. **Connection Failures**
   - Check database server status
   - Verify credentials
   - Test network connectivity
   - Review firewall settings

2. **Migration Errors**
   - Check migration dependencies
   - Verify database permissions
   - Review migration SQL syntax
   - Check for data conflicts

3. **Performance Issues**
   - Analyze query execution plans
   - Check index usage
   - Monitor connection pool status
   - Review resource utilization

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 API Reference

### DatabaseManager
- `create_connection(name, config)`: Create named connection
- `get_connection(name)`: Get connection instance
- `connect_all()`: Connect all registered connections
- `disconnect_all()`: Disconnect all connections
- `initialize_schema(connection_name)`: Initialize database schema

### BaseDAO
- `find_by_id(id)`: Find record by primary key
- `find_all(conditions, limit, offset, order_by)`: Query multiple records
- `create(data)`: Create new record
- `update(id, data)`: Update existing record
- `delete(id)`: Delete record
- `count(conditions)`: Count matching records

### Migration System
- `migrate_to_latest()`: Apply all pending migrations
- `rollback_to_version(version)`: Rollback to specific version
- `get_applied_migrations()`: List applied migrations
- `save_migration(migration)`: Save migration to file

---

*This database foundation provides a robust, scalable, and compliant data layer for the Orthanc Management Module, supporting the complex requirements of South African healthcare environments.*
