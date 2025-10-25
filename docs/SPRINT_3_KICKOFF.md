# Sprint 3 Kickoff - Frontend Development

**Date**: 2025-10-21
**Status**: 🔵 READY TO START
**Sprint Duration**: Week 3 (estimated 40 hours)

---

## 🎉 Sprint 1 & 2 Achievements

### ✅ Backend Infrastructure Complete (5 hours total)

**Sprint 1 - Database & Core Services (3.5 hours)**:
- ✅ Database schema with 5 tables, 12 indexes
- ✅ PACS connector with 9 methods
- ✅ Access control service with 7 methods
- ✅ 20 unit tests (all passing)

**Sprint 2 - API Endpoints & Integration (1.5 hours)**:
- ✅ 9 REST API endpoints
- ✅ Access management (create, check, revoke)
- ✅ User studies and patients endpoints
- ✅ PACS middleware with decorators
- ✅ 19 tests (all passing)

**Total Backend Tests**: 39 tests, all passing ✅

---

## 🎯 Sprint 3 Objectives

### Goal
Build the frontend interfaces for:
1. **Admin UI**: Patient access management, doctor assignments, family access
2. **User Portals**: Auto-redirect logic and filtered patients page

### Success Criteria
- [ ] Admin can manage patient access via UI
- [ ] Admin can assign doctors to patients
- [ ] Admin can grant family access
- [ ] Non-admin users auto-redirect to patients page
- [ ] Users see only their authorized patients
- [ ] All UI components responsive and user-friendly

---

## 📋 Sprint 3 Tasks

### Task 3.1: Patient Access Management Tab
**Priority**: HIGH | **Estimated**: 10 hours

**Features**:
- Add "Patient Access" tab to admin dashboard
- Patient search component
- User selection dropdown
- Relationship type selector
- Access level selector (read/download)
- Current assignments table with edit/delete
- Success/error notifications

**Files to Create/Modify**:
- `static/dashboard.html` (add new tab)
- `static/js/patient-access.js` (new file)
- `static/css/patient-access.css` (new file)

**API Endpoints to Use**:
- `POST /access/patient-relationship`
- `GET /access/user/{user_id}/patients`
- `DELETE /access/revoke`

---

### Task 3.2: Doctor Assignment Interface
**Priority**: MEDIUM | **Estimated**: 8 hours

**Features**:
- "Doctor Assignments" section in admin dashboard
- Doctor selection dropdown (filtered by role)
- Patient search for assignment
- Assignment type selector (primary/consulting)
- Bulk assignment feature
- Assignments table with filters
- Export to CSV

**Files to Create/Modify**:
- `static/dashboard.html` (add section)
- `static/js/doctor-assignments.js` (new file)

**API Endpoints to Use**:
- `POST /access/doctor-assignment`
- `GET /access/user/{user_id}/patients`
- `DELETE /access/revoke`

---

### Task 3.3: Family Access Configuration
**Priority**: MEDIUM | **Estimated**: 8 hours

**Features**:
- "Family Access" section in admin dashboard
- Parent user selector
- Child patient search
- Relationship selector (parent/guardian/spouse)
- Verification checkbox
- Pending approvals list
- Approve/deny actions
- Expiration date picker

**Files to Create/Modify**:
- `static/dashboard.html` (add section)
- `static/js/family-access.js` (new file)

**API Endpoints to Use**:
- `POST /access/family-access`
- `GET /access/user/{user_id}/patients`
- `DELETE /access/revoke`

---

### Task 4.1: Auto-Redirect Logic
**Priority**: HIGH | **Estimated**: 4 hours

**Features**:
- Modify MCP dashboard redirect logic
- Role-based redirect rules:
  - Admin/Radiologist/Technician → Stay on dashboard
  - Referring Doctor → Redirect to `/patients` with token
  - Patient → Redirect to `/patients` with token
- Pass MCP token in URL/cookie
- Handle redirect errors
- Add loading state

**Files to Modify**:
- `static/dashboard.html` (add redirect logic)
- `app/routes/auth.py` (add token generation for redirect)

**Logic**:
```javascript
// After login success
if (userRole === 'Admin' || userRole === 'Radiologist' || userRole === 'Technician') {
    // Stay on dashboard
    window.location.href = '/dashboard.html';
} else {
    // Redirect to PACS patients page with token
    const token = localStorage.getItem('mcp_token');
    window.location.href = `http://localhost:5000/patients?mcp_token=${token}`;
}
```

---

### Task 4.2: Filtered Patients Page
**Priority**: HIGH | **Estimated**: 10 hours

**Features**:
- Modify PACS patients page to accept MCP token
- Token validation on page load
- Fetch user's accessible patients from MCP
- Filter patient list by accessible IDs
- Update search to respect access control
- Add "No patients found" message
- Add "Request Access" button
- Show access level indicator

**Files to Modify**:
- `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/templates/patients.html`
- `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/static/js/patients.js`
- `4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/routes.py` (add token validation)

**API Endpoints to Use**:
- `GET /access/my-patients?user_id={user_id}` (from MCP server)
- `GET /access/check?user_id={user_id}&patient_id={patient_id}` (for validation)

**Logic Flow**:
1. Extract MCP token from URL/cookie
2. Verify token with MCP server
3. Get user's accessible patients
4. Filter displayed patients
5. Update search/filter to respect access

---

## 🔧 Technical Implementation Notes

### Token Flow
```
1. User logs in to MCP → JWT token generated
2. Token stored in localStorage and cookie
3. Non-admin redirected to PACS with token
4. PACS validates token with MCP server
5. PACS fetches accessible patients
6. PACS filters UI based on access
```

### API Integration Pattern
```javascript
// Example: Fetch accessible patients
async function getAccessiblePatients(userId) {
    const response = await fetch(`http://localhost:8080/access/my-patients?user_id=${userId}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    const data = await response.json();
    return data;
}
```

### Error Handling
- Token expired → Redirect to login
- Token invalid → Show error, redirect to login
- MCP server down → Show error, allow admin override
- No patients accessible → Show friendly message

---

## 📊 Sprint 3 Timeline

### Week 3 Breakdown
- **Day 1-2**: Task 3.1 (Patient Access Management Tab)
- **Day 3**: Task 3.2 (Doctor Assignment Interface)
- **Day 4**: Task 3.3 (Family Access Configuration)
- **Day 5**: Task 4.1 (Auto-Redirect Logic)
- **Day 6-7**: Task 4.2 (Filtered Patients Page)

### Milestones
- **End of Day 2**: Admin can manage patient access
- **End of Day 4**: All admin features complete
- **End of Day 7**: User portals complete, Sprint 3 done

---

## 🧪 Testing Checklist

### Admin UI Testing
- [ ] Can search and select patients
- [ ] Can assign access to users
- [ ] Can assign doctors to patients
- [ ] Can grant family access
- [ ] Can view current assignments
- [ ] Can revoke access
- [ ] Error messages display correctly
- [ ] Success messages display correctly

### User Portal Testing
- [ ] Non-admin users redirected correctly
- [ ] Token passed correctly
- [ ] Users see only their patients
- [ ] Search respects access control
- [ ] "No access" message displays correctly
- [ ] Request access button works

### Cross-Browser Testing
- [ ] Chrome
- [ ] Firefox
- [ ] Edge
- [ ] Safari (if available)

---

## 🚀 Getting Started

### Prerequisites
1. Backend services running:
   - MCP server: `http://localhost:8080`
   - PACS backend: `http://localhost:5000`
   - Orthanc: `http://localhost:8042`

2. Database migrations applied:
   - MCP database with access control tables
   - PACS metadata database

3. Test users created:
   - Admin user
   - Referring Doctor user
   - Patient user

### Development Setup
```bash
# Start MCP server
cd 4-PACS-Module/Orthanc/mcp-server
uvicorn app.main:app --reload --port 8080

# Start PACS backend
cd 4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend
python app.py

# Open dashboard
http://localhost:8080/dashboard.html
```

---

## 📝 Notes

### Design Guidelines
- Use existing dashboard styling (Ubuntu colors: #006533, #FFB81C, #005580)
- Keep UI consistent with current modules
- Mobile-responsive design
- Clear error messages
- Loading states for async operations

### Security Considerations
- Always validate tokens server-side
- Never trust client-side access checks
- Log all access attempts
- Implement rate limiting on sensitive endpoints
- Use HTTPS in production

### Performance Considerations
- Cache accessible patients list (5 min TTL)
- Paginate large patient lists
- Lazy load patient details
- Debounce search inputs
- Show loading indicators

---

## 🔗 Related Documents

- **Implementation Progress**: `IMPLEMENTATION_PROGRESS.md`
- **Task List**: `PATIENT_ACCESS_IMPLEMENTATION_TASKS.md`
- **API Documentation**: Check MCP server routes
- **Database Schema**: `4-PACS-Module/Orthanc/mcp-server/migrations/001_patient_access.sql`

---

**Ready to start Sprint 3!** 🚀

Let's build the frontend and bring this access control system to life!
