# Patient Image Access - Implementation Task List

## 🎯 Project Overview

**Goal**: Implement patient-level access control where:
- Non-admin users automatically redirected to `http://localhost:5000/patients`
- Users see ONLY their authorized images (configured by admin)
- Admin manages all access relationships via MCP server
- MCP server connects to PACS metadata database

**Timeline**: 3-4 weeks
**Team Size**: 2-4 developers
**Complexity**: Medium

---

## 📋 Task Breakdown by Developer Role

### 🔵 Developer 1: Database & Backend Infrastructure

#### Task 1.1: Database Schema Setup
**Priority**: HIGH | **Estimated Time**: 4 hours | **Dependencies**: None

**Subtasks:**
- [ ] Create migration script for MCP database
- [ ] Add `patient_relationships` table
- [ ] Add `doctor_patient_assignments` table
- [ ] Add `family_access` table
- [ ] Add `pacs_connection_config` table
- [ ] Add indexes for performance
- [ ] Test migration on dev database
- [ ] Document schema changes

**Files to Create:**
- `4-PACS-Module/Orthanc/mcp-server/migrations/001_patient_access.sql`
- `4-PACS-Module/Orthanc/mcp-server/migrations/README.md`

**Acceptance Criteria:**
- ✅ All tables created successfully
- ✅ Foreign keys working
- ✅ Indexes created
- ✅ Sample data can be inserted

---

#### Task 1.2: PACS Database Connector
**Priority**: HIGH | **Estimated Time**: 6 hours | **Dependencies**: Task 1.1

**Subtasks:**
- [ ] Create `PACSConnector` class
- [ ] Implement read-only connection
- [ ] Add `get_patient_studies()` method
- [ ] Add `get_patient_info()` method
- [ ] Add `search_patients()` method
- [ ] Add `verify_patient_exists()` method
- [ ] Add error handling
- [ ] Write unit tests
- [ ] Document API

**Files to Create:**
- `4-PACS-Module/Orthanc/mcp-server/app/services/pacs_connector.py`
- `4-PACS-Module/Orthanc/mcp-server/tests/test_pacs_connector.py`

**Acceptance Criteria:**
- ✅ Can connect to PACS database
- ✅ Can query patient data
- ✅ Read-only access enforced
- ✅ All tests passing

---

#### Task 1.3: Access Control Service
**Priority**: HIGH | **Estimated Time**: 8 hours | **Dependencies**: Task 1.2

**Subtasks:**
- [ ] Create `AccessControlService` class
- [ ] Implement `get_accessible_patients()` method
- [ ] Implement `can_access_patient()` method
- [ ] Implement `get_user_studies()` method
- [ ] Add role-based logic (Admin, Doctor, Patient)
- [ ] Add family access logic
- [ ] Add caching for performance
- [ ] Write unit tests
- [ ] Document access rules

**Files to Create:**
- `4-PACS-Module/Orthanc/mcp-server/app/services/access_control.py`
- `4-PACS-Module/Orthanc/mcp-server/tests/test_access_control.py`

**Acceptance Criteria:**
- ✅ Correct patients returned for each role
- ✅ Family access working
- ✅ Performance acceptable (<100ms)
- ✅ All tests passing

---

### 🟢 Developer 2: API Endpoints & Integration

#### Task 2.1: Access Management API Routes
**Priority**: HIGH | **Estimated Time**: 8 hours | **Dependencies**: Task 1.3

**Subtasks:**
- [ ] Create access management router
- [ ] Add `POST /access/patient-relationship` endpoint
- [ ] Add `POST /access/doctor-assignment` endpoint
- [ ] Add `POST /access/family-access` endpoint
- [ ] Add `GET /access/user/{user_id}/patients` endpoint
- [ ] Add `GET /access/check` endpoint (for PACS validation)
- [ ] Add `DELETE /access/revoke` endpoint
- [ ] Add request validation (Pydantic models)
- [ ] Add authentication middleware
- [ ] Write API tests
- [ ] Document endpoints (OpenAPI)

**Files to Create:**
- `4-PACS-Module/Orthanc/mcp-server/app/routes/access_management.py`
- `4-PACS-Module/Orthanc/mcp-server/tests/test_access_api.py`

**Acceptance Criteria:**
- ✅ All endpoints working
- ✅ Proper authentication
- ✅ Input validation working
- ✅ API documentation complete

---

#### Task 2.2: User Studies API
**Priority**: HIGH | **Estimated Time**: 6 hours | **Dependencies**: Task 1.3

**Subtasks:**
- [ ] Add `GET /access/my-studies` endpoint
- [ ] Add `GET /access/my-patients` endpoint (for doctors)
- [ ] Add pagination support
- [ ] Add filtering (date range, modality)
- [ ] Add sorting options
- [ ] Implement caching
- [ ] Write API tests
- [ ] Document endpoints

**Files to Create:**
- `4-PACS-Module/Orthanc/mcp-server/app/routes/user_studies.py`
- `4-PACS-Module/Orthanc/mcp-server/tests/test_user_studies.py`

**Acceptance Criteria:**
- ✅ Users see only their studies
- ✅ Pagination working
- ✅ Performance acceptable
- ✅ Tests passing

---

#### Task 2.3: MCP-PACS Integration
**Priority**: HIGH | **Estimated Time**: 8 hours | **Dependencies**: Task 2.1, 2.2

**Subtasks:**
- [ ] Create PACS access control middleware
- [ ] Add token verification function
- [ ] Add `check_patient_access()` decorator
- [ ] Integrate with existing PACS routes
- [ ] Add audit logging
- [ ] Handle token expiration
- [ ] Write integration tests
- [ ] Document integration

**Files to Create:**
- `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/middleware/access_control.py`
- `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/tests/test_access_middleware.py`

**Acceptance Criteria:**
- ✅ PACS validates MCP tokens
- ✅ Access control enforced
- ✅ Audit logs created
- ✅ Tests passing

---

### 🟡 Developer 3: Frontend - Admin UI

#### Task 3.1: Patient Access Management Tab
**Priority**: MEDIUM | **Estimated Time**: 10 hours | **Dependencies**: Task 2.1

**Subtasks:**
- [ ] Add "Patient Access" tab to admin dashboard
- [ ] Create patient search component
- [ ] Create user selection dropdown
- [ ] Create relationship type selector
- [ ] Create access level selector
- [ ] Add "Assign Access" button
- [ ] Create current assignments table
- [ ] Add edit/delete actions
- [ ] Add success/error notifications
- [ ] Write frontend tests
- [ ] Document UI components

**Files to Modify:**
- `4-PACS-Module/Orthanc/mcp-server/static/dashboard.html`

**Files to Create:**
- `4-PACS-Module/Orthanc/mcp-server/static/js/patient-access.js`
- `4-PACS-Module/Orthanc/mcp-server/static/css/patient-access.css`

**Acceptance Criteria:**
- ✅ Admin can search patients
- ✅ Admin can assign access
- ✅ Admin can view assignments
- ✅ Admin can revoke access
- ✅ UI is responsive

---

#### Task 3.2: Doctor Assignment Interface
**Priority**: MEDIUM | **Estimated Time**: 8 hours | **Dependencies**: Task 2.1

**Subtasks:**
- [ ] Add "Doctor Assignments" section
- [ ] Create doctor selection dropdown
- [ ] Create patient search for assignment
- [ ] Create assignment type selector
- [ ] Add bulk assignment feature
- [ ] Create assignments table
- [ ] Add filter by doctor
- [ ] Add export to CSV
- [ ] Write frontend tests

**Files to Modify:**
- `4-PACS-Module/Orthanc/mcp-server/static/dashboard.html`

**Files to Create:**
- `4-PACS-Module/Orthanc/mcp-server/static/js/doctor-assignments.js`

**Acceptance Criteria:**
- ✅ Admin can assign doctors to patients
- ✅ Bulk assignment working
- ✅ Filtering working
- ✅ Export working

---

#### Task 3.3: Family Access Configuration
**Priority**: MEDIUM | **Estimated Time**: 8 hours | **Dependencies**: Task 2.1

**Subtasks:**
- [ ] Add "Family Access" section
- [ ] Create parent user selector
- [ ] Create child patient search
- [ ] Create relationship selector
- [ ] Add verification checkbox
- [ ] Create pending approvals list
- [ ] Add approve/deny actions
- [ ] Add expiration date picker
- [ ] Write frontend tests

**Files to Modify:**
- `4-PACS-Module/Orthanc/mcp-server/static/dashboard.html`

**Files to Create:**
- `4-PACS-Module/Orthanc/mcp-server/static/js/family-access.js`

**Acceptance Criteria:**
- ✅ Admin can grant family access
- ✅ Verification workflow working
- ✅ Expiration dates working
- ✅ UI intuitive

---

### 🟠 Developer 4: Frontend - User Portals

#### Task 4.1: Auto-Redirect Logic
**Priority**: HIGH | **Estimated Time**: 4 hours | **Dependencies**: Task 2.2

**Subtasks:**
- [ ] Modify MCP dashboard redirect logic
- [ ] Add role-based redirect rules
- [ ] Redirect non-admin to `/patients` with MCP token
- [ ] Pass user context in URL/token
- [ ] Handle redirect errors
- [ ] Add loading state
- [ ] Write tests
- [ ] Document redirect flow

**Files to Modify:**
- `4-PACS-Module/Orthanc/mcp-server/static/dashboard.html`
- `4-PACS-Module/Orthanc/mcp-server/app/routes/auth.py`

**Acceptance Criteria:**
- ✅ Admin stays on dashboard
- ✅ Non-admin redirected to patients page
- ✅ Token passed correctly
- ✅ No redirect loops

---

#### Task 4.2: Filtered Patients Page
**Priority**: HIGH | **Estimated Time**: 10 hours | **Dependencies**: Task 2.2, 4.1

**Subtasks:**
- [ ] Modify patients page to accept MCP token
- [ ] Add token validation on page load
- [ ] Fetch user's accessible patients from MCP
- [ ] Filter patient list by accessible IDs
- [ ] Update search to respect access control
- [ ] Add "No patients found" message
- [ ] Add "Request Access" button
- [ ] Update UI to show access level
- [ ] Write frontend tests
- [ ] Document changes

**Files to Modify:**
- `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/templates/patients.html`
- `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/static/js/patients.js`

**Acceptance Criteria:**
- ✅ Users see only their patients
- ✅ Search respects access control
- ✅ UI shows access restrictions
- ✅ Performance acceptable

---

#### Task 4.3: Patient Portal View
**Priority**: MEDIUM | **Estimated Time**: 8 hours | **Dependencies**: Task 4.2

**Subtasks:**
- [ ] Create patient-specific view
- [ ] Show "My Images" heading
- [ ] Display studies in card format
- [ ] Add study details (date, modality, description)
- [ ] Add "View Images" button
- [ ] Add download option (if permitted)
- [ ] Add share option (if permitted)
- [ ] Show children's images separately
- [ ] Write frontend tests

**Files to Create:**
- `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/templates/patient-portal.html`
- `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/static/js/patient-portal.js`
- `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/static/css/patient-portal.css`

**Acceptance Criteria:**
- ✅ Patient sees own images
- ✅ Children's images shown separately
- ✅ Actions respect permissions
- ✅ UI user-friendly

---

#### Task 4.4: Referring Doctor Portal
**Priority**: MEDIUM | **Estimated Time**: 8 hours | **Dependencies**: Task 4.2

**Subtasks:**
- [ ] Create doctor-specific view
- [ ] Show "My Patients" heading
- [ ] List assigned patients
- [ ] Add patient search within assigned
- [ ] Show patient study count
- [ ] Add "View Patient Images" button
- [ ] Add patient details panel
- [ ] Add "Request New Patient" button
- [ ] Write frontend tests

**Files to Create:**
- `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/templates/doctor-portal.html`
- `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/static/js/doctor-portal.js`
- `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/static/css/doctor-portal.css`

**Acceptance Criteria:**
- ✅ Doctor sees assigned patients
- ✅ Can view patient images
- ✅ Search working
- ✅ UI professional

---

### 🔴 All Developers: Testing & Documentation

#### Task 5.1: Integration Testing
**Priority**: HIGH | **Estimated Time**: 12 hours | **Dependencies**: All above tasks

**Subtasks:**
- [ ] Create end-to-end test scenarios
- [ ] Test admin workflow (assign access)
- [ ] Test patient workflow (view own images)
- [ ] Test doctor workflow (view assigned patients)
- [ ] Test family access workflow
- [ ] Test access denial scenarios
- [ ] Test token expiration
- [ ] Test concurrent access
- [ ] Document test results
- [ ] Fix identified bugs

**Files to Create:**
- `tests/integration/test_patient_access_e2e.py`
- `tests/integration/test_doctor_access_e2e.py`
- `tests/integration/test_family_access_e2e.py`
- `tests/integration/TEST_RESULTS.md`

**Acceptance Criteria:**
- ✅ All workflows tested
- ✅ No critical bugs
- ✅ Performance acceptable
- ✅ Security validated

---

#### Task 5.2: Documentation
**Priority**: MEDIUM | **Estimated Time**: 8 hours | **Dependencies**: Task 5.1

**Subtasks:**
- [ ] Write admin user guide
- [ ] Write patient user guide
- [ ] Write doctor user guide
- [ ] Document API endpoints
- [ ] Create video tutorials
- [ ] Write troubleshooting guide
- [ ] Document database schema
- [ ] Create deployment guide
- [ ] Write security guidelines

**Files to Create:**
- `docs/ADMIN_GUIDE.md`
- `docs/PATIENT_GUIDE.md`
- `docs/DOCTOR_GUIDE.md`
- `docs/API_DOCUMENTATION.md`
- `docs/DEPLOYMENT_GUIDE.md`
- `docs/TROUBLESHOOTING.md`

**Acceptance Criteria:**
- ✅ All guides complete
- ✅ Screenshots included
- ✅ Clear instructions
- ✅ Examples provided

---

#### Task 5.3: Security Audit
**Priority**: HIGH | **Estimated Time**: 6 hours | **Dependencies**: Task 5.1

**Subtasks:**
- [ ] Review access control logic
- [ ] Test SQL injection prevention
- [ ] Test XSS prevention
- [ ] Verify token security
- [ ] Check audit logging
- [ ] Review HIPAA compliance
- [ ] Test authorization bypass attempts
- [ ] Document security measures
- [ ] Create security checklist

**Files to Create:**
- `docs/SECURITY_AUDIT.md`
- `docs/SECURITY_CHECKLIST.md`

**Acceptance Criteria:**
- ✅ No security vulnerabilities
- ✅ HIPAA compliant
- ✅ Audit trail complete
- ✅ Documentation complete

---

## 📊 Task Dependencies Diagram

```
Database Setup (1.1)
    ↓
PACS Connector (1.2)
    ↓
Access Control Service (1.3)
    ↓
    ├─→ Access Management API (2.1)
    │       ↓
    │   Admin UI (3.1, 3.2, 3.3)
    │
    ├─→ User Studies API (2.2)
    │       ↓
    │   Auto-Redirect (4.1)
    │       ↓
    │   Filtered Patients Page (4.2)
    │       ↓
    │   Patient/Doctor Portals (4.3, 4.4)
    │
    └─→ MCP-PACS Integration (2.3)
            ↓
        Integration Testing (5.1)
            ↓
        Documentation (5.2) + Security Audit (5.3)
```

---

## 📅 Sprint Planning (4 Sprints x 1 Week Each)

### Sprint 1: Foundation (Week 1)
**Focus**: Database & Core Backend

**Tasks**:
- Task 1.1: Database Schema Setup
- Task 1.2: PACS Database Connector
- Task 1.3: Access Control Service

**Deliverables**:
- ✅ Database tables created
- ✅ PACS connector working
- ✅ Access control logic implemented

**Team Assignment**:
- Developer 1: All tasks

---

### Sprint 2: API & Integration (Week 2)
**Focus**: API Endpoints & PACS Integration

**Tasks**:
- Task 2.1: Access Management API Routes
- Task 2.2: User Studies API
- Task 2.3: MCP-PACS Integration

**Deliverables**:
- ✅ All API endpoints working
- ✅ PACS integration complete
- ✅ Token validation working

**Team Assignment**:
- Developer 2: All tasks

---

### Sprint 3: Admin UI & User Portals (Week 3)
**Focus**: Frontend Development

**Tasks**:
- Task 3.1: Patient Access Management Tab
- Task 3.2: Doctor Assignment Interface
- Task 3.3: Family Access Configuration
- Task 4.1: Auto-Redirect Logic
- Task 4.2: Filtered Patients Page

**Deliverables**:
- ✅ Admin UI complete
- ✅ Auto-redirect working
- ✅ Filtered patients page working

**Team Assignment**:
- Developer 3: Tasks 3.1, 3.2, 3.3
- Developer 4: Tasks 4.1, 4.2

---

### Sprint 4: Portals & Testing (Week 4)
**Focus**: User Portals, Testing & Documentation

**Tasks**:
- Task 4.3: Patient Portal View
- Task 4.4: Referring Doctor Portal
- Task 5.1: Integration Testing
- Task 5.2: Documentation
- Task 5.3: Security Audit

**Deliverables**:
- ✅ Patient portal complete
- ✅ Doctor portal complete
- ✅ All tests passing
- ✅ Documentation complete
- ✅ Security audit passed

**Team Assignment**:
- Developer 3: Task 4.3
- Developer 4: Task 4.4
- All Developers: Tasks 5.1, 5.2, 5.3

---

## 🎯 Success Metrics

### Functional Requirements
- [ ] Admin can assign patient access
- [ ] Admin can assign doctors to patients
- [ ] Admin can grant family access
- [ ] Patients see only their images
- [ ] Doctors see only assigned patients
- [ ] Non-admin users auto-redirected to patients page
- [ ] Access control enforced at API level

### Performance Requirements
- [ ] Page load < 2 seconds
- [ ] API response < 500ms
- [ ] Database queries < 100ms
- [ ] Supports 100+ concurrent users

### Security Requirements
- [ ] No unauthorized access possible
- [ ] All access attempts logged
- [ ] HIPAA compliant
- [ ] Tokens expire appropriately
- [ ] SQL injection prevented
- [ ] XSS prevented

---

## 📝 Daily Standup Template

**What did you complete yesterday?**
- Task X.X: [Description]

**What will you work on today?**
- Task X.X: [Description]

**Any blockers?**
- [Blocker description]

**Dependencies needed?**
- Waiting for Task X.X from Developer Y

---

## 🚀 Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Code reviewed
- [ ] Documentation complete
- [ ] Security audit passed
- [ ] Database backup created
- [ ] Rollback plan ready

### Deployment Steps
1. [ ] Backup production database
2. [ ] Run database migrations
3. [ ] Deploy MCP server updates
4. [ ] Deploy PACS backend updates
5. [ ] Deploy frontend updates
6. [ ] Verify health checks
7. [ ] Test critical workflows
8. [ ] Monitor error logs
9. [ ] Notify users of changes

### Post-Deployment
- [ ] Monitor system for 24 hours
- [ ] Check error logs
- [ ] Verify access control working
- [ ] Collect user feedback
- [ ] Document any issues
- [ ] Plan hotfixes if needed

---

## 📞 Communication Plan

### Daily
- Morning standup (15 min)
- Slack updates on progress
- Blocker resolution

### Weekly
- Sprint planning (Monday)
- Sprint review (Friday)
- Sprint retrospective (Friday)

### Tools
- **Task Tracking**: Jira / Trello / GitHub Projects
- **Communication**: Slack / Teams
- **Code Review**: GitHub Pull Requests
- **Documentation**: Confluence / GitHub Wiki

---

**Total Estimated Time**: 120-140 hours
**Team Size**: 2-4 developers
**Duration**: 4 weeks
**Complexity**: Medium
**Risk Level**: Low-Medium

**Ready to start? Assign tasks and begin Sprint 1!** 🚀
