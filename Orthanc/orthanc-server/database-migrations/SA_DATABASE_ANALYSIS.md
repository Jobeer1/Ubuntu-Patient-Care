# SA Database Analysis - Existing Flask Databases

## 📋 **Identified Databases**

Based on analysis of `orthanc-source/NASIntegration/backend/`, the following SQLite databases exist:

### Core Databases
1. **`orthanc_management.db`** - Core Orthanc server management
2. **`orthanc_users.db`** - User authentication and management  
3. **`orthanc_2fa.db`** - Two-factor authentication data
4. **`orthanc_images.db`** - DICOM image metadata and caching

### SA Healthcare Specific
5. **`sa_healthcare_users.db`** - SA healthcare professionals (HPCSA data)
6. **`sa_secure_shares.db`** - Patient link sharing and secure access
7. **`reporting.db`** - Medical reporting and templates

### Feature-Specific Databases  
8. **`collaboration.db`** - Real-time collaboration features
9. **`telemedicine.db`** - Telemedicine integration
10. **`medical_devices.db`** - Medical device management
11. **`multi_hospital_network.db`** - Multi-hospital networking
12. **`nas_discovery.db`** - NAS discovery and configuration

## 🎯 **Migration Strategy**

### Phase 1: Core Integration (Priority 1)
**Target**: Integrate essential authentication and SA healthcare data into Orthanc database

#### Tables to Migrate to Orthanc Database:
```sql
-- From orthanc_users.db
CREATE TABLE SAUsers (
    user_id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    email VARCHAR(100),
    role VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- From sa_healthcare_users.db  
CREATE TABLE SAHealthcareProfessionals (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50),
    hpcsa_number VARCHAR(20) UNIQUE,
    practice_name VARCHAR(200),
    specialization VARCHAR(100),
    province VARCHAR(50),
    phone VARCHAR(20),
    is_verified BOOLEAN DEFAULT FALSE,
    verification_date TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES SAUsers(user_id)
);

-- From orthanc_2fa.db
CREATE TABLE SA2FA (
    user_id VARCHAR(50) PRIMARY KEY,
    secret_key VARCHAR(100),
    backup_codes TEXT, -- JSON array
    is_enabled BOOLEAN DEFAULT FALSE,
    failed_attempts INTEGER DEFAULT 0,
    last_failed_attempt TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES SAUsers(user_id)
);

-- Extend Orthanc's Patients table
ALTER TABLE Patients ADD COLUMN sa_id_number VARCHAR(13);
ALTER TABLE Patients ADD COLUMN medical_scheme VARCHAR(100);
ALTER TABLE Patients ADD COLUMN medical_scheme_number VARCHAR(50);
ALTER TABLE Patients ADD COLUMN preferred_language VARCHAR(10);
ALTER TABLE Patients ADD COLUMN popia_consent BOOLEAN DEFAULT FALSE;
ALTER TABLE Patients ADD COLUMN consent_date TIMESTAMP;
```

### Phase 2: Feature Integration (Priority 2)
**Target**: Integrate reporting and sharing features

#### Tables to Migrate:
```sql
-- From reporting.db
CREATE TABLE SAReports (
    report_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50),
    study_id VARCHAR(50),
    template_id VARCHAR(50),
    content TEXT,
    language VARCHAR(10),
    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES SAUsers(user_id)
);

-- From sa_secure_shares.db
CREATE TABLE SASecureShares (
    share_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50),
    study_id VARCHAR(50),
    share_token VARCHAR(100) UNIQUE,
    created_by VARCHAR(50),
    expires_at TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (created_by) REFERENCES SAUsers(user_id)
);
```

### Phase 3: Advanced Features (Priority 3)
**Target**: Integrate collaboration and telemedicine features

#### Tables to Consider:
- Collaboration sessions and real-time features
- Telemedicine appointments and video calls
- Medical device configurations
- Multi-hospital networking

## 🔧 **Implementation Plan**

### Step 1: Database Schema Extension
**File**: `orthanc-server/OrthancServer/Sources/Database/SQLiteDatabaseWrapper.cpp`

```cpp
// Add SA-specific tables to Orthanc database initialization
void SQLiteDatabaseWrapper::CreateSATables() {
    // Create SA Users table
    db_.Execute("CREATE TABLE IF NOT EXISTS SAUsers ("
                "user_id VARCHAR(50) PRIMARY KEY,"
                "username VARCHAR(100) UNIQUE NOT NULL,"
                "password_hash VARCHAR(255) NOT NULL,"
                "full_name VARCHAR(200),"
                "email VARCHAR(100),"
                "role VARCHAR(50),"
                "is_active BOOLEAN DEFAULT TRUE,"
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
                "last_login TIMESTAMP"
                ")");
    
    // Create SA Healthcare Professionals table
    db_.Execute("CREATE TABLE IF NOT EXISTS SAHealthcareProfessionals ("
                "id VARCHAR(50) PRIMARY KEY,"
                "user_id VARCHAR(50),"
                "hpcsa_number VARCHAR(20) UNIQUE,"
                "practice_name VARCHAR(200),"
                "specialization VARCHAR(100),"
                "province VARCHAR(50),"
                "phone VARCHAR(20),"
                "is_verified BOOLEAN DEFAULT FALSE,"
                "verification_date TIMESTAMP,"
                "FOREIGN KEY (user_id) REFERENCES SAUsers(user_id)"
                ")");
    
    // Add more tables...
}
```

### Step 2: Data Migration Scripts
**File**: `orthanc-server/database-migrations/migrate-flask-data.py`

```python
import sqlite3
import json
from datetime import datetime

def migrate_users_data():
    # Connect to Flask databases
    flask_users_db = sqlite3.connect('orthanc-source/NASIntegration/backend/orthanc_users.db')
    flask_healthcare_db = sqlite3.connect('orthanc-source/NASIntegration/backend/sa_healthcare_users.db')
    
    # Connect to Orthanc database
    orthanc_db = sqlite3.connect('orthanc-server/OrthancStorage/index')
    
    # Migrate user data
    # Implementation details...
```

### Step 3: Database Access Layer
**File**: `orthanc-server/orthanc-sa-plugins/database/SADatabaseExtension.cpp`

```cpp
class SADatabaseExtension {
public:
    // User management
    bool CreateUser(const SAUserInfo& user_info);
    SAUserInfo GetUser(const std::string& user_id);
    bool UpdateUser(const SAUserInfo& user_info);
    bool DeleteUser(const std::string& user_id);
    
    // Healthcare professional management
    bool CreateHealthcareProfessional(const SAHealthcareProfessional& professional);
    SAHealthcareProfessional GetHealthcareProfessional(const std::string& hpcsa_number);
    
    // 2FA management
    bool Store2FAInfo(const std::string& user_id, const SA2FAInfo& info);
    SA2FAInfo Get2FAInfo(const std::string& user_id);
};
```

## 📊 **Migration Priorities**

### Immediate (This Week):
1. ✅ Authentication Bridge Plugin (Completed)
2. 🔄 Database schema extension (In Progress)
3. ⏳ User and HPCSA data migration

### Short Term (Next Week):
1. ⏳ Reporting and sharing data migration
2. ⏳ Patient data extensions
3. ⏳ SA compliance integration

### Medium Term (Following Weeks):
1. ⏳ Advanced feature migration
2. ⏳ Performance optimization
3. ⏳ Data synchronization testing

## 🚨 **Critical Considerations**

### Data Integrity:
- All existing user accounts must be preserved
- HPCSA numbers must remain unique and validated
- Patient data must maintain POPIA compliance
- 2FA settings must be preserved

### Performance:
- Database queries must not slow down Orthanc operations
- Indexing strategy for SA-specific searches
- Connection pooling for concurrent access

### Security:
- Password hashes must be migrated securely
- 2FA secrets must be encrypted in transit
- Audit trail for all data migration operations

### Rollback Strategy:
- Complete database backup before migration
- Rollback scripts for each migration step
- Validation procedures to verify migration success

---

**Next Steps for Developer A**:
1. Implement database schema extension in SQLiteDatabaseWrapper.cpp
2. Create data migration scripts
3. Test migration with sample data
4. Coordinate with Developer B on frontend data requirements