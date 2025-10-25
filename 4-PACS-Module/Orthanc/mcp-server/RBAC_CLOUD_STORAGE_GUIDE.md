# Role-Based Access Control & Cloud Storage Integration Guide

## 🎯 Overview

This system implements comprehensive role-based access control (RBAC) with direct cloud storage integration for Google Drive and OneDrive. Users can sign in with local credentials, Google, or Microsoft accounts and access modules based on their role.

---

## 🔐 Authentication Methods

### 1. Local Sign In
- Email and password authentication
- Password hashing with bcrypt
- Suitable for internal users

### 2. Sign In with Google
- OAuth 2.0 authentication
- Automatic Google Drive integration
- Offline access for direct file uploads

### 3. Sign In with Microsoft
- OAuth 2.0 authentication
- Automatic OneDrive integration
- Offline access for direct file uploads

### 4. Sign Up
- Self-registration for patients
- Admin-managed registration for staff

---

## 👥 User Roles & Permissions

### Patient
**Access Level:** Restricted to own data only

**Permissions:**
- ✅ View own images
- ✅ View own reports
- ✅ Export to cloud storage
- ❌ View other patients' data
- ❌ Create/edit reports
- ❌ Manage users

**Accessible Modules:**
- My Images
- My Reports

**Use Case:** Patients can log in to view their own medical images and reports, and export them to their personal cloud storage.

---

### Referring Doctor
**Access Level:** View-only access to their patients' data

**Permissions:**
- ✅ View assigned patients
- ✅ View patients' images (read-only)
- ✅ View patients' reports (read-only)
- ✅ Export to cloud storage
- ✅ Share studies
- ❌ Edit images or reports
- ❌ View unassigned patients
- ❌ Manage users

**Accessible Modules:**
- Patients (assigned only)
- Images (read-only)
- Reports (read-only)

**Use Case:** Referring doctors can monitor their patients' imaging studies and reports without editing capabilities.

---

### Radiologist
**Access Level:** Full access to imaging and reporting

**Permissions:**
- ✅ View all images
- ✅ View all reports
- ✅ Create reports
- ✅ Edit reports
- ✅ Approve reports
- ✅ View all patients
- ✅ Export to cloud storage
- ✅ Share studies
- ❌ Manage users
- ❌ Delete images

**Accessible Modules:**
- Worklist
- Reporting
- Images
- Patients

**Use Case:** Radiologists can review images, create and approve reports for all patients.

---

### Technician
**Access Level:** Image acquisition and patient management

**Permissions:**
- ✅ View images
- ✅ Upload images
- ✅ Edit images
- ✅ View patients
- ✅ Create patients
- ✅ Edit patients
- ❌ Create/edit reports
- ❌ Delete images
- ❌ Manage users

**Accessible Modules:**
- Acquisition
- Patients
- Images

**Use Case:** Technicians can acquire images, register patients, and manage patient information.

---

### Admin
**Access Level:** Full system access

**Permissions:**
- ✅ All image permissions
- ✅ All report permissions
- ✅ All patient permissions
- ✅ Manage users
- ✅ Manage roles
- ✅ View audit logs
- ✅ Export to cloud storage
- ✅ Share studies

**Accessible Modules:**
- Admin
- Users
- Audit
- Worklist
- Reporting
- Images
- Patients

**Use Case:** System administrators can manage all aspects of the system.

---

## ☁️ Cloud Storage Integration

### Direct Upload Feature

When a user signs in with Google or Microsoft, the system stores their refresh token securely. This enables **direct uploads** to their cloud storage without downloading files first.

### How It Works

1. **User Authentication:**
   - User signs in with Google/Microsoft
   - System requests offline access
   - Refresh token is stored securely in database

2. **Export to Cloud:**
   - User selects images to export
   - Clicks "Send to Google Drive" or "Send to OneDrive"
   - System fetches DICOM files from PACS
   - Files are uploaded directly to user's cloud storage
   - No download required on user's device

3. **Security:**
   - Refresh tokens are encrypted in database
   - Access is validated before each upload
   - Audit logs track all exports

### API Endpoint

```http
POST /cloud/upload
Content-Type: application/json

{
  "study_id": "1.2.840.113619.2.55.3.2831164340.123",
  "patient_id": "PAT001",
  "instance_ids": ["instance1", "instance2"],
  "provider": "google_drive"  // or "onedrive"
}
```

**Response:**
```json
{
  "success": true,
  "provider": "google_drive",
  "uploaded_count": 2,
  "failed_count": 0,
  "results": [
    {
      "success": true,
      "file_id": "1abc...",
      "file_name": "study_instance1.dcm",
      "web_link": "https://drive.google.com/file/d/1abc..."
    }
  ]
}
```

---

## 🔒 Access Control Implementation

### Patient Data Access

```python
# Check if user can access patient data
can_access = RBACService.can_access_patient_data(db, user, patient_id)

# Rules:
# - Patients: Only their own data (user.patient_id == patient_id)
# - Referring Doctors: Only assigned patients
# - Radiologists/Technicians/Admins: All patients
```

### Study Access

```python
# Check if user can access a study
can_access = RBACService.can_access_study(db, user, study_patient_id)

# Same rules as patient data access
```

### Module Access

```python
# Get accessible modules for user
modules = RBACService.get_accessible_modules(user)

# Returns list like: ["worklist", "reporting", "images", "patients"]
```

---

## 🛠️ Configuration

### Individual Permission Grants

Admins can grant specific permissions to individual users:

```python
# Grant permission to view specific patient
RBACService.grant_permission(
    db=db,
    user_id=doctor_id,
    permission_type="view_patient",
    resource_id="PAT001",
    granted_by=admin_id,
    expires_at=datetime(2025, 12, 31)
)
```

### Linking Patients to Referring Doctors

```python
# Assign patient to referring doctor
patient.referring_doctor_id = doctor.id
db.commit()

# Now doctor can view this patient's data
```

---

## 📊 Audit Logging

All authentication and data access events are logged:

```python
# Logged events:
- login_google
- login_microsoft
- login_local
- signup_local
- export_to_google_drive
- export_to_onedrive
- view_patient
- view_study
- create_report
- approve_report
```

Query audit logs:
```http
GET /audit/logs?user_id=123&action=export_to_google_drive
```

---

## 🚀 Quick Start

### 1. Start the Server

```bash
cd mcp-server
python run.py
```

### 2. Access Login Page

```
http://localhost:8080/login
```

### 3. Sign In

Choose one of:
- **Sign In:** Local email/password
- **Sign Up:** Create new account
- **Sign in with Google:** OAuth + Google Drive
- **Sign in with Microsoft:** OAuth + OneDrive

### 4. Access Dashboard

After login, you'll be redirected to:
```
http://localhost:8080/dashboard?modules=worklist,reporting,images
```

Modules shown depend on your role.

### 5. Export to Cloud

1. Navigate to images module
2. Select images to export
3. Click "Send to Google Drive" or "Send to OneDrive"
4. Images upload directly without downloading

---

## 🔧 API Endpoints

### Authentication

```http
POST /auth/login          # Local login
POST /auth/signup         # Local signup
GET  /auth/google         # Initiate Google OAuth
GET  /auth/microsoft      # Initiate Microsoft OAuth
GET  /auth/status         # Check auth status
GET  /auth/logout         # Logout
```

### Cloud Storage

```http
POST /cloud/upload        # Upload to cloud storage
GET  /cloud/status        # Check cloud connections
POST /cloud/disconnect/{provider}  # Disconnect cloud
```

### Users & Permissions

```http
GET  /users               # List users (admin only)
GET  /users/{id}          # Get user details
PUT  /users/{id}/role     # Update user role (admin only)
POST /users/{id}/permissions  # Grant permission (admin only)
```

### Audit

```http
GET  /audit/logs          # View audit logs (admin only)
GET  /audit/user/{id}     # User-specific logs
```

---

## 🎨 Frontend Integration

### Check User Permissions

```javascript
// Get current user and permissions
const response = await fetch('/auth/status');
const data = await response.json();

if (data.authenticated) {
    const user = data.user;
    console.log('Role:', user.role);
    console.log('Modules:', modules);
}
```

### Export to Cloud

```javascript
async function exportToGoogleDrive(studyId, patientId, instanceIds) {
    const response = await fetch('/cloud/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            study_id: studyId,
            patient_id: patientId,
            instance_ids: instanceIds,
            provider: 'google_drive'
        })
    });
    
    const result = await response.json();
    if (result.success) {
        alert(`Uploaded ${result.uploaded_count} files to Google Drive!`);
    }
}
```

---

## 🔐 Security Best Practices

1. **Refresh Tokens:**
   - Stored encrypted in database
   - Never exposed to frontend
   - Rotated on each use

2. **Access Control:**
   - Validated on every request
   - Logged in audit trail
   - Enforced at database level

3. **OAuth Scopes:**
   - Minimal required scopes
   - Offline access for cloud storage
   - User consent required

4. **Password Security:**
   - Bcrypt hashing
   - Salt per password
   - No plaintext storage

---

## 📝 Database Schema

### Users Table
```sql
- id: Primary key
- email: Unique, indexed
- password_hash: Bcrypt hash (nullable for OAuth users)
- name: Full name
- role: Patient, Referring Doctor, Radiologist, Technician, Admin
- patient_id: For patients (nullable)
- referring_doctor_id: Link to doctor (nullable)
- google_refresh_token: Encrypted (nullable)
- microsoft_refresh_token: Encrypted (nullable)
- active: Boolean
- created_at: Timestamp
- last_login: Timestamp
```

### Roles Table
```sql
- id: Primary key
- name: Role name
- description: Role description
- can_view_images: Boolean
- can_upload_images: Boolean
- can_edit_images: Boolean
- can_delete_images: Boolean
- can_view_reports: Boolean
- can_create_reports: Boolean
- can_edit_reports: Boolean
- can_approve_reports: Boolean
- can_view_patients: Boolean
- can_create_patients: Boolean
- can_edit_patients: Boolean
- can_manage_users: Boolean
- can_manage_roles: Boolean
- can_view_audit_logs: Boolean
- can_export_to_cloud: Boolean
- can_share_studies: Boolean
```

### User Permissions Table
```sql
- id: Primary key
- user_id: Foreign key to users
- permission_type: String (e.g., "view_patient")
- resource_id: Specific resource (e.g., "PAT001")
- granted_by: Foreign key to users
- granted_at: Timestamp
- expires_at: Timestamp (nullable)
```

---

## 🎯 Use Case Examples

### Example 1: Patient Views Own Images

1. Patient logs in with email/password
2. System checks: `user.role == "Patient"`
3. Dashboard shows: "My Images", "My Reports"
4. Patient clicks "My Images"
5. System filters: `WHERE patient_id = user.patient_id`
6. Patient sees only their own images

### Example 2: Referring Doctor Views Patient

1. Doctor logs in with Microsoft
2. OneDrive automatically connected
3. Dashboard shows: "Patients", "Images", "Reports"
4. Doctor clicks "Patients"
5. System filters: `WHERE referring_doctor_id = user.id`
6. Doctor sees only assigned patients
7. Doctor selects patient, views images (read-only)
8. Doctor exports images to OneDrive (no download)

### Example 3: Radiologist Creates Report

1. Radiologist logs in with Google
2. Google Drive automatically connected
3. Dashboard shows: "Worklist", "Reporting", "Images", "Patients"
4. Radiologist opens worklist
5. Selects study, creates report
6. Report saved with `created_by = radiologist.id`
7. Audit log records: "create_report"

---

## 📞 Support

For questions or issues:
- Check audit logs: `/audit/logs`
- Review user permissions: `/users/{id}`
- Test cloud connection: `/cloud/status`

---

**Version:** 1.0.0  
**Last Updated:** October 18, 2025  
**Maintained By:** Ubuntu Patient Care Development Team
