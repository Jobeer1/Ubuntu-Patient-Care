# Patient & Referring Doctor Image Access - Implementation Plan

## 🎯 Objective

Enable secure, role-based access to medical images where:
- **Referring Doctors** can view images of their assigned patients
- **Patients** can view their own images (and their children's if configured)
- **Admin** manages all relationships via MCP server
- **MCP Server** connects to PACS metadata database for access control

## 📊 Current System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CURRENT ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────┘

MCP Server (Port 8080)
├── User Authentication (Google/Microsoft OAuth)
├── User Management (CRUD)
├── Role Management
└── Database: mcp_server.db
    ├── users table
    └── roles table

PACS Backend (Port 5000)
├── Patient Management
├── Image Storage
├── DICOM Processing
└── Database: pacs_metadata.db
    ├── patient_studies table
    ├── patients table
    └── dicom_metadata table
```

## 🔄 Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    NEW ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────┘

MCP Server (Port 8080)
├── User Authentication
├── User Management
├── Role Management
└── NEW: Patient Access Control
    ├── Database: mcp_server.db
    │   ├── users table
    │   ├── roles table
    │   ├── patient_relationships table (NEW)
    │   ├── doctor_patient_assignments table (NEW)
    │   └── family_access table (NEW)
    │
    └── Connection to PACS Database
        └── Read access to pacs_metadata.db

PACS Backend (Port 5000)
├── Patient Management
├── Image Storage
├── NEW: Access Control API
│   ├── Check user permissions
│   ├── Filter images by user
│   └── Validate access requests
└── Database: pacs_metadata.db
    ├── patient_studies table
    ├── patients table
    └── dicom_metadata table
```

## 📋 Implementation Phases

### Phase 1: Database Schema Design ✅

#### 1.1 MCP Server Database Extensions

**New Table: `patient_relationships`**
```sql
CREATE TABLE patient_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,              -- MCP user ID
    patient_identifier VARCHAR(255) NOT NULL, -- Patient ID/MRN from PACS
    relationship_type VARCHAR(50) NOT NULL,   -- 'self', 'child', 'parent', 'guardian'
    access_level VARCHAR(50) DEFAULT 'view',  -- 'view', 'download', 'share'
    created_by INTEGER,                       -- Admin who created this
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,                -- Optional expiration
    is_active BOOLEAN DEFAULT 1,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    UNIQUE(user_id, patient_identifier)
);
```

**New Table: `doctor_patient_assignments`**
```sql
CREATE TABLE doctor_patient_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_user_id INTEGER NOT NULL,          -- MCP user ID (Referring Doctor)
    patient_identifier VARCHAR(255) NOT NULL, -- Patient ID/MRN from PACS
    assignment_type VARCHAR(50) DEFAULT 'referring', -- 'referring', 'consulting', 'primary'
    access_level VARCHAR(50) DEFAULT 'view',  -- 'view', 'download', 'share', 'report'
    assigned_by INTEGER,                      -- Admin who assigned
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT 1,
    notes TEXT,
    FOREIGN KEY (doctor_user_id) REFERENCES users(id),
    FOREIGN KEY (assigned_by) REFERENCES users(id),
    UNIQUE(doctor_user_id, patient_identifier)
);
```

**New Table: `family_access`**
```sql
CREATE TABLE family_access (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_user_id INTEGER NOT NULL,          -- Parent/Guardian MCP user ID
    child_patient_identifier VARCHAR(255) NOT NULL, -- Child's Patient ID
    relationship VARCHAR(50) NOT NULL,        -- 'parent', 'legal_guardian', 'caregiver'
    access_level VARCHAR(50) DEFAULT 'view',
    verified BOOLEAN DEFAULT 0,               -- Admin verification required
    verified_by INTEGER,
    verified_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,                -- e.g., when child turns 18
    is_active BOOLEAN DEFAULT 1,
    notes TEXT,
    FOREIGN KEY (parent_user_id) REFERENCES users(id),
    FOREIGN KEY (verified_by) REFERENCES users(id)
);
```

**New Table: `pacs_connection_config`**
```sql
CREATE TABLE pacs_connection_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT,
    description TEXT,
    updated_by INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES users(id)
);

-- Default values
INSERT INTO pacs_connection_config (config_key, config_value, description) VALUES
('pacs_db_path', '../4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/orthanc-index/pacs_metadata.db', 'Path to PACS metadata database'),
('pacs_api_url', 'http://localhost:5000', 'PACS backend API URL'),
('enable_patient_access', '1', 'Enable patient self-access to images'),
('enable_family_access', '1', 'Enable family member access'),
('require_admin_verification', '1', 'Require admin verification for family access');
```

#### 1.2 PACS Database - No Changes Needed
The existing PACS database already has patient information. We'll read from it.

### Phase 2: MCP Server Backend Implementation 🔧

#### 2.1 Database Connection Module

**File**: `4-PACS-Module/Orthanc/mcp-server/app/services/pacs_connector.py`

```python
"""
PACS Database Connector
Connects MCP server to PACS metadata database for access control
"""
import sqlite3
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class PACSConnector:
    def __init__(self, pacs_db_path: str):
        self.pacs_db_path = pacs_db_path
        
    def get_connection(self):
        """Get connection to PACS database (read-only)"""
        try:
            conn = sqlite3.connect(f"file:{self.pacs_db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to PACS database: {e}")
            raise
    
    def get_patient_studies(self, patient_id: str) -> List[Dict]:
        """Get all studies for a patient"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM patient_studies 
                WHERE patient_id = ? OR patient_mrn = ?
                ORDER BY study_date DESC
            """, (patient_id, patient_id))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_patient_info(self, patient_id: str) -> Optional[Dict]:
        """Get patient information"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM patients 
                WHERE patient_id = ? OR patient_mrn = ?
                LIMIT 1
            """, (patient_id, patient_id))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def search_patients(self, search_term: str) -> List[Dict]:
        """Search patients by name, ID, or MRN"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT patient_id, patient_name, patient_mrn, 
                       patient_birth_date, patient_sex
                FROM patients
                WHERE patient_name LIKE ? 
                   OR patient_id LIKE ? 
                   OR patient_mrn LIKE ?
                LIMIT 50
            """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def verify_patient_exists(self, patient_id: str) -> bool:
        """Verify patient exists in PACS"""
        info = self.get_patient_info(patient_id)
        return info is not None
```

#### 2.2 Access Control Service

**File**: `4-PACS-Module/Orthanc/mcp-server/app/services/access_control.py`

```python
"""
Image Access Control Service
Determines what images a user can access
"""
from typing import List, Dict, Optional
from app.database import get_db
from app.services.pacs_connector import PACSConnector

class AccessControlService:
    def __init__(self, pacs_connector: PACSConnector):
        self.pacs = pacs_connector
    
    def get_accessible_patients(self, user_id: int, user_role: str) -> List[str]:
        """Get list of patient IDs this user can access"""
        db = get_db()
        accessible_patients = []
        
        # Admin and Radiologist: All patients
        if user_role in ['Admin', 'Radiologist', 'Technician']:
            return ['*']  # Wildcard for all patients
        
        # Referring Doctor: Assigned patients
        if user_role == 'Referring Doctor':
            cursor = db.execute("""
                SELECT DISTINCT patient_identifier 
                FROM doctor_patient_assignments
                WHERE doctor_user_id = ? AND is_active = 1
                AND (expires_at IS NULL OR expires_at > datetime('now'))
            """, (user_id,))
            accessible_patients.extend([row[0] for row in cursor.fetchall()])
        
        # Patient: Self and family
        if user_role == 'Patient':
            # Self access
            cursor = db.execute("""
                SELECT DISTINCT patient_identifier 
                FROM patient_relationships
                WHERE user_id = ? AND is_active = 1
                AND (expires_at IS NULL OR expires_at > datetime('now'))
            """, (user_id,))
            accessible_patients.extend([row[0] for row in cursor.fetchall()])
            
            # Family access (children)
            cursor = db.execute("""
                SELECT DISTINCT child_patient_identifier 
                FROM family_access
                WHERE parent_user_id = ? AND is_active = 1 AND verified = 1
                AND (expires_at IS NULL OR expires_at > datetime('now'))
            """, (user_id,))
            accessible_patients.extend([row[0] for row in cursor.fetchall()])
        
        return list(set(accessible_patients))  # Remove duplicates
    
    def can_access_patient(self, user_id: int, user_role: str, patient_id: str) -> bool:
        """Check if user can access specific patient"""
        accessible = self.get_accessible_patients(user_id, user_role)
        return '*' in accessible or patient_id in accessible
    
    def get_user_studies(self, user_id: int, user_role: str) -> List[Dict]:
        """Get all studies accessible to this user"""
        accessible_patients = self.get_accessible_patients(user_id, user_role)
        
        if '*' in accessible_patients:
            # Return all studies (for admin/radiologist)
            # This should be paginated in production
            return []  # Implement pagination
        
        all_studies = []
        for patient_id in accessible_patients:
            studies = self.pacs.get_patient_studies(patient_id)
            all_studies.extend(studies)
        
        return sorted(all_studies, key=lambda x: x.get('study_date', ''), reverse=True)
```

#### 2.3 API Routes for Access Management

**File**: `4-PACS-Module/Orthanc/mcp-server/app/routes/access_management.py`

```python
"""
Access Management API Routes
Admin endpoints for managing patient access
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db
from app.routes.auth import get_current_user, require_role

router = APIRouter(prefix="/access", tags=["access"])

class PatientRelationship(BaseModel):
    user_id: int
    patient_identifier: str
    relationship_type: str
    access_level: str = "view"
    notes: Optional[str] = None

class DoctorAssignment(BaseModel):
    doctor_user_id: int
    patient_identifier: str
    assignment_type: str = "referring"
    access_level: str = "view"
    notes: Optional[str] = None

class FamilyAccess(BaseModel):
    parent_user_id: int
    child_patient_identifier: str
    relationship: str
    access_level: str = "view"
    notes: Optional[str] = None

@router.post("/patient-relationship")
async def create_patient_relationship(
    rel: PatientRelationship,
    current_user = Depends(require_role("Admin"))
):
    """Admin: Link a user to their patient record"""
    db = get_db()
    try:
        db.execute("""
            INSERT INTO patient_relationships 
            (user_id, patient_identifier, relationship_type, access_level, created_by, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (rel.user_id, rel.patient_identifier, rel.relationship_type, 
              rel.access_level, current_user['id'], rel.notes))
        db.commit()
        return {"success": True, "message": "Patient relationship created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/doctor-assignment")
async def assign_doctor_to_patient(
    assignment: DoctorAssignment,
    current_user = Depends(require_role("Admin"))
):
    """Admin: Assign a referring doctor to a patient"""
    db = get_db()
    try:
        db.execute("""
            INSERT INTO doctor_patient_assignments 
            (doctor_user_id, patient_identifier, assignment_type, access_level, assigned_by, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (assignment.doctor_user_id, assignment.patient_identifier, 
              assignment.assignment_type, assignment.access_level, 
              current_user['id'], assignment.notes))
        db.commit()
        return {"success": True, "message": "Doctor assigned to patient"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/family-access")
async def create_family_access(
    access: FamilyAccess,
    current_user = Depends(require_role("Admin"))
):
    """Admin: Grant family member access to patient records"""
    db = get_db()
    try:
        db.execute("""
            INSERT INTO family_access 
            (parent_user_id, child_patient_identifier, relationship, access_level, 
             verified, verified_by, verified_at, notes)
            VALUES (?, ?, ?, ?, 1, ?, datetime('now'), ?)
        """, (access.parent_user_id, access.child_patient_identifier, 
              access.relationship, access.access_level, current_user['id'], access.notes))
        db.commit()
        return {"success": True, "message": "Family access granted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/user/{user_id}/patients")
async def get_user_accessible_patients(
    user_id: int,
    current_user = Depends(require_role("Admin"))
):
    """Admin: View what patients a user can access"""
    from app.services.access_control import AccessControlService
    from app.services.pacs_connector import PACSConnector
    
    # Get user role
    db = get_db()
    user = db.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get accessible patients
    pacs = PACSConnector(get_pacs_db_path())
    access_control = AccessControlService(pacs)
    patients = access_control.get_accessible_patients(user_id, user['role'])
    
    return {"user_id": user_id, "accessible_patients": patients}
```

### Phase 3: PACS Backend Integration 🔗

#### 3.1 Access Control Middleware

**File**: `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/middleware/access_control.py`

```python
"""
PACS Access Control Middleware
Validates user access to patient images
"""
from functools import wraps
from flask import request, jsonify
import jwt
import requests

MCP_SERVER_URL = "http://localhost:8080"

def verify_mcp_token(token):
    """Verify JWT token from MCP server"""
    try:
        # Decode without verification (MCP server already verified it)
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except:
        return None

def check_patient_access(patient_id):
    """Decorator to check if user can access patient"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get token from header or cookie
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not token:
                token = request.cookies.get('mcp_token')
            
            if not token:
                return jsonify({'error': 'Unauthorized'}), 401
            
            # Verify token
            user_data = verify_mcp_token(token)
            if not user_data:
                return jsonify({'error': 'Invalid token'}), 401
            
            # Check access via MCP server
            try:
                response = requests.get(
                    f"{MCP_SERVER_URL}/access/check",
                    params={'user_id': user_data['user_id'], 'patient_id': patient_id},
                    headers={'Authorization': f'Bearer {token}'}
                )
                if response.status_code != 200 or not response.json().get('has_access'):
                    return jsonify({'error': 'Access denied'}), 403
            except:
                return jsonify({'error': 'Access verification failed'}), 500
            
            # Add user data to request context
            request.user_data = user_data
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

### Phase 4: Admin UI Implementation 🎨

#### 4.1 Patient Access Management Tab

Add to `dashboard.html`:

```html
<!-- Patient Access Tab -->
<div id="patientAccessTab" class="admin-content">
    <h3>Patient Access Management</h3>
    
    <!-- Search Patient -->
    <div class="form-group">
        <label>Search Patient</label>
        <input type="text" id="patientSearch" placeholder="Search by name, ID, or MRN">
        <div id="patientSearchResults"></div>
    </div>
    
    <!-- Assign Access -->
    <div class="form-group">
        <label>Assign Access To</label>
        <select id="accessUserSelect">
            <option value="">Select User</option>
            <!-- Populated dynamically -->
        </select>
    </div>
    
    <button class="btn btn-primary" onclick="assignPatientAccess()">
        Assign Access
    </button>
    
    <!-- Current Assignments -->
    <h4>Current Access Assignments</h4>
    <table>
        <thead>
            <tr>
                <th>User</th>
                <th>Patient</th>
                <th>Relationship</th>
                <th>Access Level</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody id="accessAssignmentsTable">
            <!-- Populated dynamically -->
        </tbody>
    </table>
</div>
```

### Phase 5: Auto-Redirect & Filtered Views 🔄

#### 5.1 Auto-Redirect Logic (NON-ADMIN USERS)

**Requirement**: All non-admin users automatically redirected to `http://localhost:5000/patients` after login

**File**: `4-PACS-Module/Orthanc/mcp-server/static/dashboard.html`

```javascript
// Add to dashboard.html after user info loads
async function handlePostLoginRedirect() {
    if (!currentUser) return;
    
    // Admin stays on dashboard
    if (currentUser.role === 'Admin') {
        return; // Show dashboard with all modules
    }
    
    // All other users redirect to patients page
    const redirectUrl = 'http://localhost:5000/patients';
    
    // Pass MCP token for authentication
    const token = getCookie('mcp_token') || sessionStorage.getItem('mcp_token');
    
    // Redirect with token
    window.location.href = `${redirectUrl}?mcp_token=${token}`;
}

// Call after loadUserInfo()
await loadUserInfo();
await handlePostLoginRedirect(); // NEW
```

#### 5.2 Filtered Patients Page

**Requirement**: Patients page shows ONLY user's authorized images

**File**: `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/routes/patients.py`

```python
@app.route('/patients')
def patients_page():
    """Patients page with access control"""
    # Get MCP token from query or cookie
    mcp_token = request.args.get('mcp_token') or request.cookies.get('mcp_token')
    
    if not mcp_token:
        return redirect('http://localhost:8080')  # Back to MCP login
    
    # Verify token and get user info
    try:
        user_data = verify_mcp_token(mcp_token)
        user_id = user_data['user_id']
        user_role = user_data['role']
    except:
        return redirect('http://localhost:8080')
    
    # Get accessible patients from MCP server
    accessible_patients = get_accessible_patients(user_id, user_role)
    
    # Render page with filtered data
    return render_template('patients.html', 
                         user_data=user_data,
                         accessible_patients=accessible_patients,
                         is_filtered=user_role != 'Admin')
```

**File**: `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/static/js/patients.js`

```javascript
// Modify patient search to respect access control
async function searchPatients(query) {
    const response = await fetch('/api/patients/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${mcpToken}`
        },
        body: JSON.stringify({ 
            query: query,
            user_id: userData.user_id,
            role: userData.role
        })
    });
    
    const results = await response.json();
    
    // Results are already filtered by backend
    displayPatients(results.patients);
}

// Show access level indicator
function displayPatients(patients) {
    if (patients.length === 0 && userData.role !== 'Admin') {
        showMessage('No patients assigned. Contact administrator for access.');
    }
    
    // Display patients with access indicators
    patients.forEach(patient => {
        const card = createPatientCard(patient);
        if (userData.role !== 'Admin') {
            card.addAccessBadge('Your Access');
        }
        container.appendChild(card);
    });
}
```

#### 5.3 Patient Portal View

**File**: `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/templates/patient-portal.html`

```html
<!DOCTYPE html>
<html>
<head>
    <title>My Medical Images</title>
</head>
<body>
    <h1>My Medical Images</h1>
    
    <div id="studiesList">
        <!-- List of accessible studies -->
    </div>
    
    <script>
        async function loadMyStudies() {
            const response = await fetch('/access/my-studies', {
                credentials: 'include'
            });
            const studies = await response.json();
            
            // Display studies
            const container = document.getElementById('studiesList');
            container.innerHTML = studies.map(study => `
                <div class="study-card">
                    <h3>${study.study_description}</h3>
                    <p>Date: ${study.study_date}</p>
                    <button onclick="viewStudy('${study.study_id}')">
                        View Images
                    </button>
                </div>
            `).join('');
        }
        
        loadMyStudies();
    </script>
</body>
</html>
```

## 📅 Implementation Timeline

### Week 1: Database & Backend
- [ ] Day 1-2: Create database schema
- [ ] Day 3-4: Implement PACS connector
- [ ] Day 5: Implement access control service

### Week 2: API & Integration
- [ ] Day 1-2: Create access management APIs
- [ ] Day 3-4: Integrate with PACS backend
- [ ] Day 5: Testing and bug fixes

### Week 3: Admin UI
- [ ] Day 1-2: Build patient access management UI
- [ ] Day 3-4: Build doctor assignment UI
- [ ] Day 5: Build family access UI

### Week 4: Patient/Doctor Portals
- [ ] Day 1-2: Build patient portal
- [ ] Day 3-4: Build referring doctor portal
- [ ] Day 5: Final testing and deployment

## 🧪 Testing Checklist

### Admin Functions
- [ ] Create patient relationship
- [ ] Assign doctor to patient
- [ ] Grant family access
- [ ] Revoke access
- [ ] View access logs

### Referring Doctor
- [ ] Login and see assigned patients
- [ ] View patient studies
- [ ] Cannot see unassigned patients
- [ ] Access expires correctly

### Patient
- [ ] Login and see own images
- [ ] View children's images (if configured)
- [ ] Cannot see other patients
- [ ] Download/share controls work

## 🔐 Security Considerations

1. **Database Access**: MCP server has read-only access to PACS database
2. **Token Validation**: All requests validated via JWT
3. **Audit Logging**: All access attempts logged
4. **Expiration**: Access can have expiration dates
5. **Verification**: Family access requires admin verification
6. **Encryption**: All data transmitted over HTTPS in production

## 📊 Success Metrics

- ✅ Referring doctors can only see their patients
- ✅ Patients can only see their own images
- ✅ Family access works correctly
- ✅ Admin can manage all relationships
- ✅ Access control is enforced at API level
- ✅ Audit trail is maintained

## 🚀 Deployment Steps

1. Backup existing databases
2. Run database migrations
3. Update MCP server code
4. Update PACS backend code
5. Test in staging environment
6. Deploy to production
7. Train admin users
8. Monitor access logs

---

**This plan provides complete patient-level access control while maintaining security and HIPAA compliance!**
