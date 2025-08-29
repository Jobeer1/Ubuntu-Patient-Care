# 🏥 Orthanc Management Module - Complete Specification
*Note: Backend infrastructure recently refactored to modular architecture (January 2025) for improved maintainability*

## Overview
This module provides comprehensive Orthanc PACS server management, referring doctor workflow automation, patient image authorization, and secure patient sharing capabilities for South African healthcare facilities.

*The implementation leverages the new modular backend structure with blueprint-based routing for better organization and maintenance.*

## 🎯 Core Requirements

### 1. **Orthanc Server Management**
- **Server Control**: Start, stop, restart, status monitoring
- **Configuration Management**: Dynamic configuration updates
- **Port & Network Settings**: Configure listening ports, DICOM ports, web interface
- **Storage Management**: Configure storage paths, compression, retention policies
- **Performance Monitoring**: Real-time server metrics and health checks

### 2. **Referring Doctor Workflow**
- **Doctor Registration**: Easy onboarding of referring doctors
- **Automatic Access**: Doctors automatically see patients they referred
- **Referral Tracking**: Track which doctor referred which patient
- **Notification System**: Alert doctors when studies are ready
- **Secure Access**: Time-limited, secure access to specific studies

### 3. **Patient Image Authorization**
- **Manual Authorization**: Admin grants doctors access to specific patients
- **Bulk Authorization**: Grant access to multiple images at once
- **Access Levels**: View-only, download, annotations, reports
- **Time-Limited Access**: Set expiration dates for access
- **Audit Trail**: Track who accessed what and when

### 4. **Patient Link Sharing**
- **Direct Patient Links**: Secure, time-limited links for patients
- **Download Management**: Control what patients can download
- **Mobile Optimization**: Links work on patient mobile devices
- **Password Protection**: Optional password protection for sensitive studies
- **Usage Tracking**: Monitor patient link usage and downloads

## 🏗️ Module Architecture

### Core Components

```
orthanc_management/
├── server_controller.py          # Orthanc server management
├── doctor_manager.py            # Referring doctor management
├── patient_authorization.py     # Patient access control
├── patient_sharing.py           # Patient link sharing
├── orthanc_config_manager.py    # Dynamic configuration
├── referral_tracker.py          # Referral workflow tracking
├── notification_service.py      # Email/SMS notifications
├── audit_logger.py             # Comprehensive audit logging
├── api/
│   ├── orthanc_api.py          # Orthanc management endpoints
│   ├── doctor_api.py           # Doctor management endpoints
│   ├── patient_api.py          # Patient management endpoints
│   └── sharing_api.py          # Sharing management endpoints
├── templates/
│   ├── orthanc_dashboard.html  # Server management UI
│   ├── doctor_management.html  # Doctor workflow UI
│   ├── patient_access.html     # Patient authorization UI
│   └── sharing_center.html     # Link sharing UI
└── static/
    ├── js/orthanc_management.js
    ├── css/management_styles.css
    └── images/
```

## 📋 Detailed Feature Specifications

### 1. Orthanc Server Management

#### 1.1 Server Control Panel
```python
class OrthancServerController:
    """Manages Orthanc server lifecycle and configuration"""
    
    def start_server(self, config_path=None):
        """Start Orthanc with specified configuration"""
    
    def stop_server(self):
        """Gracefully stop Orthanc server"""
    
    def restart_server(self):
        """Restart Orthanc with new configuration"""
    
    def get_server_status(self):
        """Get current server status and metrics"""
    
    def update_configuration(self, config_updates):
        """Update Orthanc configuration dynamically"""
```

#### 1.2 Configuration Management
- **Network Settings**: HTTP port, DICOM port, listening addresses
- **Storage Configuration**: Storage paths, compression settings, retention
- **Security Settings**: Authentication, SSL certificates, access controls
- **Performance Tuning**: Memory limits, worker threads, cache settings
- **Plugin Management**: Enable/disable plugins, plugin configurations

#### 1.3 Real-time Monitoring
- Server uptime and status
- Active DICOM connections
- Storage usage and growth
- Memory and CPU utilization
- Study ingestion rates
- Error logs and alerts

### 2. Referring Doctor Management

#### 2.1 Doctor Registration & Onboarding
```python
class ReferringDoctor:
    """Represents a referring doctor in the system"""
    
    doctor_id: str
    name: str
    practice_name: str
    hpcsa_number: str
    email: str
    phone: str
    specialization: str
    facility_type: str  # private_practice, clinic, hospital
    province: str
    referral_patterns: dict  # Analytics on referral behavior
    access_level: str  # view_only, download, annotate
    is_active: bool
    created_date: datetime
    last_access: datetime
```

#### 2.2 Automatic Patient Access
- **Referral Linking**: Automatically link studies to referring doctors
- **Smart Matching**: Match patients by referral source, patient ID, name
- **Access Notification**: Notify doctors when their studies are ready
- **Dashboard Integration**: Custom dashboard showing their patients only

#### 2.3 Referral Workflow
```python
class PatientReferral:
    """Tracks patient referrals and access rights"""
    
    referral_id: str
    patient_id: str
    referring_doctor_id: str
    study_instance_uid: str
    referral_date: datetime
    study_type: str
    clinical_indication: str
    priority: str  # routine, urgent, emergency
    access_granted: bool
    access_expires: datetime
    notification_sent: bool
    patient_contacted: bool
```

### 3. Patient Image Authorization

#### 3.1 Authorization Management
```python
class PatientAuthorization:
    """Manages doctor access to patient images"""
    
    def grant_access(self, doctor_id, patient_id, study_uids, access_level, expires_in_days=30):
        """Grant doctor access to specific patient studies"""
    
    def bulk_authorize(self, doctor_id, authorization_list):
        """Grant access to multiple patients/studies at once"""
    
    def revoke_access(self, authorization_id):
        """Revoke previously granted access"""
    
    def check_access(self, doctor_id, study_uid):
        """Check if doctor has access to specific study"""
    
    def get_doctor_patients(self, doctor_id):
        """Get all patients accessible to a doctor"""
```

#### 3.2 Access Control Levels
- **View Only**: Can view images but not download
- **Download**: Can download DICOM files
- **Annotate**: Can add annotations and measurements
- **Report Access**: Can view and download reports
- **Share**: Can create patient sharing links

#### 3.3 Bulk Operations
- Select multiple studies from search results
- Grant access to multiple doctors simultaneously
- Set uniform expiration dates
- Apply access templates for common scenarios

### 4. Patient Link Sharing

#### 4.1 Patient Sharing System
```python
class PatientShare:
    """Manages secure patient access links"""
    
    share_id: str
    patient_id: str
    study_uids: list
    created_by: str  # admin user
    patient_name: str
    patient_email: str
    patient_phone: str
    share_token: str
    access_url: str
    password_required: bool
    password_hash: str
    expires_at: datetime
    max_downloads: int
    download_count: int
    access_count: int
    last_accessed: datetime
    is_active: bool
    mobile_optimized: bool
```

#### 4.2 Patient Access Features
- **Mobile-Friendly Viewer**: Optimized for patient smartphones
- **Download Management**: Control what files patients can download
- **Usage Tracking**: Track when patients access their images
- **Password Protection**: Optional password for sensitive studies
- **Expiration Control**: Links automatically expire

#### 4.3 Patient Communication
- **Email Notifications**: Send links via email with instructions
- **SMS Integration**: Send links via SMS for mobile access
- **Multi-Language**: Support English, Afrikaans, isiZulu
- **Instructions**: Clear instructions for patients on how to access

## 🔄 Workflow Examples

### Scenario 1: New Referring Doctor Onboarding
1. Admin registers new referring doctor
2. Doctor receives welcome email with credentials
3. System creates doctor profile with default access rules
4. Doctor can immediately see patients they refer
5. Automatic notifications when studies are ready

### Scenario 2: Patient Study Ready for Referrer
1. New study arrives in Orthanc
2. System identifies referring doctor from study metadata
3. Automatic access granted to referring doctor
4. Email notification sent to doctor
5. Doctor logs in and sees new study in their dashboard

### Scenario 3: Admin Grants Additional Access
1. Admin searches for patient studies
2. Selects studies to share with specific doctor
3. Sets access level and expiration date
4. System creates authorization record
5. Doctor is notified of new access

### Scenario 4: Patient Link Creation
1. Admin selects patient studies
2. Enters patient contact information
3. Sets download permissions and expiration
4. System generates secure link
5. Patient receives link via email/SMS
6. Patient clicks link and views/downloads images

## 🛡️ Security & Compliance

### HPCSA Compliance
- All doctor access logged with HPCSA numbers
- Audit trail of all image access
- Professional verification required
- Session timeout and access controls

### POPIA Compliance
- Patient consent tracking for sharing
- Data minimization in patient links
- Access logging and audit trails
- Secure link expiration and cleanup

### Security Features
- JWT tokens for API authentication
- Encrypted patient sharing links
- Rate limiting on access attempts
- IP-based access controls
- Automatic link expiration

## 📊 Admin Dashboard Features

### 1. Orthanc Server Dashboard
- Real-time server status
- Storage utilization graphs
- Active connections monitor
- Performance metrics
- Configuration management interface

### 2. Doctor Management Dashboard
- List all referring doctors
- Doctor performance analytics
- Referral pattern analysis
- Access audit reports
- Bulk operations interface

### 3. Patient Authorization Center
- Search and filter patients
- Quick access granting interface
- Bulk authorization tools
- Expiration management
- Access audit logs

### 4. Patient Sharing Center
- Create patient sharing links
- Monitor link usage
- Manage patient communications
- Download analytics
- Link expiration management

## 🔧 Technical Implementation

### Database Schema
```sql
-- Referring Doctors
CREATE TABLE referring_doctors (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    hpcsa_number VARCHAR(20) UNIQUE,
    email VARCHAR(100),
    phone VARCHAR(20),
    practice_name VARCHAR(100),
    specialization VARCHAR(50),
    facility_type VARCHAR(50),
    province VARCHAR(50),
    access_level VARCHAR(20) DEFAULT 'view_only',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_access TIMESTAMP
);

-- Patient Referrals
CREATE TABLE patient_referrals (
    id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    referring_doctor_id VARCHAR(50) NOT NULL,
    study_instance_uid VARCHAR(100),
    referral_date TIMESTAMP,
    study_type VARCHAR(100),
    clinical_indication TEXT,
    priority VARCHAR(20) DEFAULT 'routine',
    access_granted BOOLEAN DEFAULT FALSE,
    access_expires TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (referring_doctor_id) REFERENCES referring_doctors(id)
);

-- Patient Authorizations
CREATE TABLE patient_authorizations (
    id VARCHAR(50) PRIMARY KEY,
    doctor_id VARCHAR(50) NOT NULL,
    patient_id VARCHAR(50) NOT NULL,
    study_instance_uid VARCHAR(100),
    access_level VARCHAR(20) DEFAULT 'view_only',
    granted_by VARCHAR(50) NOT NULL,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    access_count INT DEFAULT 0,
    last_accessed TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES referring_doctors(id)
);

-- Patient Shares
CREATE TABLE patient_shares (
    id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    patient_name VARCHAR(100),
    patient_email VARCHAR(100),
    patient_phone VARCHAR(20),
    study_uids TEXT,  -- JSON array of study UIDs
    share_token VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    max_downloads INT DEFAULT 10,
    download_count INT DEFAULT 0,
    access_count INT DEFAULT 0,
    last_accessed TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    mobile_optimized BOOLEAN DEFAULT TRUE
);

-- Orthanc Configuration
CREATE TABLE orthanc_configs (
    id VARCHAR(50) PRIMARY KEY,
    config_name VARCHAR(100) NOT NULL,
    config_data TEXT,  -- JSON configuration
    is_active BOOLEAN DEFAULT FALSE,
    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_at TIMESTAMP
);

-- Audit Logs
CREATE TABLE audit_logs (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50),
    user_type VARCHAR(20),  -- admin, doctor, patient
    action VARCHAR(50),
    resource_type VARCHAR(50),
    resource_id VARCHAR(50),
    details TEXT,  -- JSON details
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API Endpoints
```python
# Orthanc Management API
/api/orthanc/status              # GET - Server status
/api/orthanc/start               # POST - Start server
/api/orthanc/stop                # POST - Stop server
/api/orthanc/restart             # POST - Restart server
/api/orthanc/config              # GET/PUT - Configuration management

# Doctor Management API
/api/doctors                     # GET/POST - List/Create doctors
/api/doctors/<id>                # GET/PUT/DELETE - Doctor CRUD
/api/doctors/<id>/patients       # GET - Doctor's patients
/api/doctors/<id>/authorize      # POST - Grant patient access

# Patient Authorization API
/api/authorizations              # GET/POST - List/Create authorizations
/api/authorizations/<id>         # GET/PUT/DELETE - Authorization CRUD
/api/authorizations/bulk         # POST - Bulk operations
/api/patients/<id>/doctors       # GET - Doctors with patient access

# Patient Sharing API
/api/patient-shares              # GET/POST - List/Create patient shares
/api/patient-shares/<id>         # GET/PUT/DELETE - Share CRUD
/api/patient-shares/<id>/usage   # GET - Share usage statistics
/api/patient-access/<token>      # GET - Patient access endpoint
```

## 📋 Detailed Implementation Plan

### **STEP 1: Database Foundation (Day 1-2)**

#### 1.1 Create Database Schema
```sql
-- File: orthanc_management/database/schema.sql
```

**Tasks:**
- [ ] Create `referring_doctors` table with HPCSA validation
- [ ] Create `patient_referrals` table with workflow tracking
- [ ] Create `patient_authorizations` table for access control
- [ ] Create `patient_shares` table for secure sharing
- [ ] Create `orthanc_configs` table for dynamic configuration
- [ ] Create `audit_logs` table for compliance tracking
- [ ] Add proper indexes for performance
- [ ] Create foreign key constraints for data integrity

#### 1.2 Database Migration System
```python
# File: orthanc_management/database/migrations.py
```

**Tasks:**
- [ ] Create migration framework
- [ ] Version control for schema changes
- [ ] Rollback capabilities
- [ ] Data seeding for initial setup

---

### **STEP 2: Core Models & Managers (Day 3-4)**

#### 2.1 Data Models
```python
# File: orthanc_management/models/
```

**Files to Create:**
- [ ] `referring_doctor.py` - ReferringDoctor model with HPCSA validation
- [ ] `patient_referral.py` - PatientReferral model with workflow states
- [ ] `patient_authorization.py` - PatientAuthorization model with access levels
- [ ] `patient_share.py` - PatientShare model with secure tokens
- [ ] `orthanc_config.py` - OrthancConfig model for dynamic settings
- [ ] `audit_log.py` - AuditLog model for compliance tracking

#### 2.2 Database Managers
```python
# File: orthanc_management/managers/
```

**Files to Create:**
- [ ] `doctor_manager.py` - CRUD operations for referring doctors
- [ ] `referral_manager.py` - Workflow management for referrals
- [ ] `authorization_manager.py` - Access control management
- [ ] `sharing_manager.py` - Patient link sharing management
- [ ] `config_manager.py` - Orthanc configuration management
- [ ] `audit_manager.py` - Compliance and audit logging

---

### **STEP 3: Orthanc Server Controller (Day 5-6)**

#### 3.1 Server Management
```python
# File: orthanc_management/server_controller.py
```

**Core Functions:**
- [ ] `start_orthanc(config_path)` - Start server with configuration
- [ ] `stop_orthanc()` - Graceful server shutdown
- [ ] `restart_orthanc()` - Restart with new configuration
- [ ] `get_server_status()` - Real-time status monitoring
- [ ] `get_server_metrics()` - Performance metrics collection
- [ ] `check_server_health()` - Health check endpoint

#### 3.2 Configuration Management
```python
# File: orthanc_management/config_manager.py
```

**Configuration Features:**
- [ ] Dynamic configuration updates without restart
- [ ] Configuration validation and error checking
- [ ] Backup and restore configurations
- [ ] Template-based configuration generation
- [ ] Environment-specific settings (dev/staging/prod)

#### 3.3 Process Management
```python
# File: orthanc_management/process_manager.py
```

**Process Control:**
- [ ] Cross-platform process management (Windows/Linux)
- [ ] Process monitoring and auto-restart
- [ ] Log file management and rotation
- [ ] Resource usage monitoring
- [ ] Graceful shutdown handling

---

### **STEP 4: Referring Doctor System (Day 7-9)**

#### 4.1 Doctor Registration & Management
```python
# File: orthanc_management/doctor_manager.py
```

**Registration Flow:**
- [ ] `register_doctor(doctor_data)` - New doctor onboarding
- [ ] `validate_hpcsa_number(hpcsa_num)` - HPCSA verification
- [ ] `send_welcome_email(doctor)` - Automated welcome process
- [ ] `create_doctor_credentials(doctor)` - Login setup
- [ ] `assign_default_permissions(doctor)` - Role-based access

#### 4.2 Automatic Patient Access
```python
# File: orthanc_management/referral_tracker.py
```

**Auto-Access Features:**
- [ ] `detect_referral_source(study_metadata)` - Smart referral detection
- [ ] `link_study_to_doctor(study, doctor)` - Automatic linking
- [ ] `grant_automatic_access(doctor, study)` - Permission assignment
- [ ] `notify_doctor_study_ready(doctor, study)` - Email/SMS notifications
- [ ] `track_referral_patterns(doctor)` - Analytics and insights

#### 4.3 Doctor Dashboard
```python
# File: orthanc_management/doctor_dashboard.py
```

**Dashboard Features:**
- [ ] `get_doctor_patients(doctor_id)` - Patient list for doctor
- [ ] `get_pending_studies(doctor_id)` - Studies awaiting review
- [ ] `get_referral_statistics(doctor_id)` - Referral analytics
- [ ] `search_patient_studies(doctor_id, criteria)` - Advanced search
- [ ] `export_patient_data(doctor_id, patient_id)` - Data export

---

### **STEP 5: Patient Authorization System (Day 10-12)**

#### 5.1 Access Control Engine
```python
# File: orthanc_management/patient_authorization.py
```

**Core Authorization:**
- [ ] `grant_patient_access(doctor_id, patient_id, access_level)` - Single access grant
- [ ] `bulk_authorize_patients(doctor_id, patient_list)` - Bulk operations
- [ ] `revoke_patient_access(authorization_id)` - Access revocation
- [ ] `check_access_permissions(doctor_id, study_uid)` - Permission checking
- [ ] `set_access_expiration(authorization_id, expires_at)` - Time limits

#### 5.2 Access Level Management
```python
# File: orthanc_management/access_levels.py
```

**Access Control Levels:**
- [ ] `VIEW_ONLY` - Can view images only
- [ ] `DOWNLOAD` - Can download DICOM files
- [ ] `ANNOTATE` - Can add annotations
- [ ] `REPORT_ACCESS` - Can view/download reports
- [ ] `SHARE` - Can create patient sharing links
- [ ] `FULL_ACCESS` - Complete access to patient data

#### 5.3 Bulk Operations Interface
```python
# File: orthanc_management/bulk_operations.py
```

**Bulk Management:**
- [ ] `select_multiple_studies(search_criteria)` - Multi-select interface
- [ ] `apply_bulk_authorization(study_list, doctor_list)` - Batch processing
- [ ] `set_uniform_expiration(authorization_list, expires_at)` - Bulk expiration
- [ ] `generate_access_report(authorization_list)` - Bulk reporting
- [ ] `export_authorization_data(criteria)` - Data export

---

### **STEP 6: Patient Link Sharing (Day 13-15)**

#### 6.1 Secure Link Generation
```python
# File: orthanc_management/patient_sharing.py
```

**Link Generation:**
- [ ] `create_patient_link(patient_data, study_uids)` - Generate secure link
- [ ] `set_link_permissions(link_id, permissions)` - Configure access
- [ ] `set_link_expiration(link_id, expires_at)` - Time limits
- [ ] `generate_secure_token()` - Cryptographically secure tokens
- [ ] `create_password_protection(link_id, password)` - Optional passwords

#### 6.2 Mobile-Optimized Patient Viewer
```html
<!-- File: orthanc_management/templates/patient_viewer.html -->
```

**Mobile Features:**
- [ ] Touch-friendly image navigation
- [ ] Responsive design for smartphones
- [ ] Progressive image loading for slow connections
- [ ] Download management with file size indicators
- [ ] Multi-language support (EN/AF/ZU)

#### 6.3 Patient Communication
```python
# File: orthanc_management/notification_service.py
```

**Communication Features:**
- [ ] `send_email_link(patient_email, link_data)` - Email delivery
- [ ] `send_sms_link(patient_phone, link_data)` - SMS delivery
- [ ] `generate_patient_instructions()` - Multi-language instructions
- [ ] `track_patient_engagement(link_id)` - Usage analytics
- [ ] `send_reminder_notifications(link_id)` - Follow-up reminders

---

### **STEP 7: Admin Interface Development (Day 16-18)**

#### 7.1 Orthanc Management Dashboard
```html
<!-- File: orthanc_management/templates/orthanc_dashboard.html -->
```

**Dashboard Components:**
- [ ] Server status indicators (online/offline/restarting)
- [ ] Real-time performance metrics (CPU, memory, storage)
- [ ] Active connections monitor
- [ ] Configuration management interface
- [ ] Log viewer with filtering and search
- [ ] Quick actions (start/stop/restart/configure)

#### 7.2 Doctor Management Interface
```html
<!-- File: orthanc_management/templates/doctor_management.html -->
```

**Doctor Management UI:**
- [ ] Doctor registration form with HPCSA validation
- [ ] Doctor list with search and filtering
- [ ] Bulk operations for doctor management
- [ ] Access analytics and reporting
- [ ] Communication history tracking

#### 7.3 Patient Authorization Interface
```html
<!-- File: orthanc_management/templates/patient_authorization.html -->
```

**Authorization UI:**
- [ ] Patient search with advanced filters
- [ ] Study selection with thumbnails
- [ ] Bulk authorization interface
- [ ] Access level configuration
- [ ] Expiration date management
- [ ] Authorization audit trail

#### 7.4 Patient Sharing Center
```html
<!-- File: orthanc_management/templates/patient_sharing.html -->
```

**Sharing Interface:**
- [ ] Link creation wizard
- [ ] Patient contact management
- [ ] Link usage analytics
- [ ] Communication tracking
- [ ] Bulk link management

---

### **STEP 8: API Development (Day 19-21)**

#### 8.1 Orthanc Management API
```python
# File: orthanc_management/api/orthanc_api.py
```

**API Endpoints:**
- [ ] `GET /api/orthanc/status` - Server status
- [ ] `POST /api/orthanc/start` - Start server
- [ ] `POST /api/orthanc/stop` - Stop server
- [ ] `POST /api/orthanc/restart` - Restart server
- [ ] `GET/PUT /api/orthanc/config` - Configuration management
- [ ] `GET /api/orthanc/metrics` - Performance metrics
- [ ] `GET /api/orthanc/logs` - Log retrieval

#### 8.2 Doctor Management API
```python
# File: orthanc_management/api/doctor_api.py
```

**API Endpoints:**
- [ ] `GET/POST /api/doctors` - List/Create doctors
- [ ] `GET/PUT/DELETE /api/doctors/<id>` - Doctor CRUD
- [ ] `GET /api/doctors/<id>/patients` - Doctor's patients
- [ ] `POST /api/doctors/<id>/authorize` - Grant access
- [ ] `GET /api/doctors/<id>/analytics` - Referral analytics
- [ ] `POST /api/doctors/bulk-operations` - Bulk management

#### 8.3 Patient Authorization API
```python
# File: orthanc_management/api/patient_api.py
```

**API Endpoints:**
- [ ] `GET/POST /api/authorizations` - List/Create authorizations
- [ ] `GET/PUT/DELETE /api/authorizations/<id>` - Authorization CRUD
- [ ] `POST /api/authorizations/bulk` - Bulk operations
- [ ] `GET /api/patients/<id>/doctors` - Patient's authorized doctors
- [ ] `POST /api/patients/search` - Advanced patient search
- [ ] `GET /api/patients/<id>/audit` - Access audit trail

#### 8.4 Patient Sharing API
```python
# File: orthanc_management/api/sharing_api.py
```

**API Endpoints:**
- [ ] `GET/POST /api/patient-shares` - List/Create shares
- [ ] `GET/PUT/DELETE /api/patient-shares/<id>` - Share CRUD
- [ ] `GET /api/patient-shares/<id>/usage` - Usage analytics
- [ ] `GET /api/patient-access/<token>` - Patient access endpoint
- [ ] `POST /api/patient-shares/bulk` - Bulk operations
- [ ] `POST /api/patient-shares/<id>/notify` - Send notifications

---

### **STEP 9: Security & Compliance (Day 22-24)**

#### 9.1 Authentication & Authorization
```python
# File: orthanc_management/security/auth_manager.py
```

**Security Features:**
- [ ] JWT token-based authentication
- [ ] Role-based access control (RBAC)
- [ ] Session management with timeout
- [ ] Two-factor authentication (2FA)
- [ ] API key management for external access
- [ ] Rate limiting and brute force protection

#### 9.2 HPCSA Compliance
```python
# File: orthanc_management/compliance/hpcsa_compliance.py
```

**HPCSA Requirements:**
- [ ] Healthcare professional verification
- [ ] Comprehensive audit logging
- [ ] Access control enforcement
- [ ] Session monitoring and timeout
- [ ] Professional registration validation
- [ ] Compliance reporting

#### 9.3 POPIA Compliance
```python
# File: orthanc_management/compliance/popia_compliance.py
```

**POPIA Requirements:**
- [ ] Patient consent management
- [ ] Data minimization enforcement
- [ ] Access logging and monitoring
- [ ] Data retention policies
- [ ] Patient rights management (access, correction, deletion)
- [ ] Privacy impact assessments

#### 9.4 Audit System
```python
# File: orthanc_management/audit_logger.py
```

**Comprehensive Auditing:**
- [ ] All user actions logged
- [ ] System events tracking
- [ ] Data access monitoring
- [ ] Failed access attempts
- [ ] Configuration changes
- [ ] Automated compliance reporting

---

### **STEP 10: Integration & Testing (Day 25-28)**

#### 10.1 Integration with Existing System
```python
# File: orthanc_management/integration/
```

**Integration Points:**
- [ ] Flask admin_api.py integration
- [ ] Existing authentication system
- [ ] Current user management
- [ ] SA DICOM viewer integration
- [ ] Secure link sharing compatibility

#### 10.2 Testing Framework
```python
# File: orthanc_management/tests/
```

**Test Coverage:**
- [ ] Unit tests for all managers and models
- [ ] API endpoint testing
- [ ] Integration tests for workflows
- [ ] Security testing and penetration tests
- [ ] Performance and load testing
- [ ] Mobile compatibility testing

#### 10.3 Documentation
```markdown
# File: orthanc_management/docs/
```

**Documentation Suite:**
- [ ] Installation and setup guide
- [ ] Admin user manual
- [ ] Doctor onboarding guide
- [ ] Patient access instructions
- [ ] API documentation
- [ ] Troubleshooting guide

---

### **STEP 11: Deployment & Monitoring (Day 29-30)**

#### 11.1 Deployment Preparation
```bash
# File: orthanc_management/deployment/
```

**Deployment Tasks:**
- [ ] Production configuration templates
- [ ] Database migration scripts
- [ ] Static file optimization
- [ ] Security hardening checklist
- [ ] Backup and recovery procedures
- [ ] Monitoring setup

#### 11.2 Production Monitoring
```python
# File: orthanc_management/monitoring/
```

**Monitoring Features:**
- [ ] Real-time performance monitoring
- [ ] Error tracking and alerting
- [ ] Usage analytics and reporting
- [ ] Security event monitoring
- [ ] Automated backup verification
- [ ] Health check endpoints

---

## 🎯 **Implementation Priority Matrix**

### **Critical Path (Must Complete First):**
1. **Database Foundation** (Step 1) - Everything depends on this
2. **Core Models & Managers** (Step 2) - Foundation for all features
3. **Orthanc Server Controller** (Step 3) - Core server management
4. **API Development** (Step 8) - Interface for all operations

### **Feature Development (Can Parallelize):**
- **Referring Doctor System** (Step 4)
- **Patient Authorization System** (Step 5)  
- **Patient Link Sharing** (Step 6)
- **Admin Interface** (Step 7)

### **Final Integration (Must Complete Last):**
- **Security & Compliance** (Step 9)
- **Integration & Testing** (Step 10)
- **Deployment & Monitoring** (Step 11)

---

## 📋 **Daily Implementation Checklist**

Each step includes:
- [ ] **Code Implementation** - Write the actual functionality
- [ ] **Unit Tests** - Test individual components
- [ ] **Integration Tests** - Test component interactions
- [ ] **Documentation** - Document APIs and usage
- [ ] **Security Review** - Ensure compliance and security
- [ ] **Performance Testing** - Verify performance requirements

---

This detailed plan breaks down the complex Orthanc Management Module into 30 manageable daily tasks, with clear dependencies and priorities. Each step is specific enough to start coding immediately while maintaining the overall architecture vision.

## 🎯 Success Metrics
- **Doctor Onboarding**: <5 minutes from registration to first access
- **Patient Access**: Automatic access within 1 minute of study arrival
- **Link Generation**: Patient links created in <30 seconds
- **Mobile Performance**: Patient viewer loads in <3 seconds on 3G
- **Security Compliance**: 100% audit trail coverage

## 🔮 Future Enhancements
- **AI Integration**: Automatic referral source detection
- **Analytics Dashboard**: Referral pattern analysis
- **Mobile App**: Dedicated mobile app for doctors and patients
- **Telegram/WhatsApp**: Alternative notification channels
- **Telemedicine**: Integrated video consultation
- **Blockchain**: Immutable audit trails

---

This module will transform your Orthanc installation into a complete healthcare workflow management system, specifically optimized for South African medical practices with full regulatory compliance.

**Ready to proceed with implementation?** 

This is a comprehensive module that will require careful, step-by-step implementation. Would you like me to start with Phase 1 (Core Infrastructure) or would you prefer to review and modify any aspects of this specification first?
