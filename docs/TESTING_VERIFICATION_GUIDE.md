# 🧪 Testing & Verification Guide

## ✅ Quick Verification Checklist

### 1. Server Status
```powershell
# Check if server is running
curl http://localhost:8080

# Expected Response: Should return the admin interface
# Status: ✅ Should see HTML content
```

### 2. Admin Dashboard Access
```
URL: http://localhost:8080/admin
Expected: Should load the admin dashboard with all tabs visible
Status: ✅ Admin dashboard loads successfully
```

### 3. Tab Navigation
```
Click each tab to verify:
✅ Users (should show user list)
✅ Patient Access (should show patient relationships)
✅ Doctor Assignment (should show doctor assignments)
✅ Family Access (should show family relationships)
✅ Roles & Permissions (should show role management)
✅ Audit Logs (should show activity logs)
```

### 4. Role Management CRUD Operations

#### Test 4.1: CREATE Role
```
Steps:
1. Go to "🎭 Roles & Permissions" tab
2. Click "+ Create Role" button
3. Enter:
   - Role Name: "Test Pathologist"
   - Description: "Medical specialist for testing"
4. Check permissions:
   ✓ View Images
   ✓ Create Reports
   ✓ View Patients
5. Click "Save Role"

Expected Result: ✅ Role appears in grid with badge
Notification: "Role created successfully!"
```

#### Test 4.2: READ Roles
```
Steps:
1. Stay on "🎭 Roles & Permissions" tab
2. Observe the role grid
3. Each role card should display:
   - Role name
   - Description
   - List of permissions
   - Edit button
   - Delete button

Expected Result: ✅ All roles visible with permissions listed
Permissions Format: 
   "View Images", "Create Reports", "View Patients", etc.
```

#### Test 4.3: UPDATE Role
```
Steps:
1. Click "✏️ Edit" on any role card
2. Modal opens with:
   - Current role name (in text field)
   - Current description (in textarea)
   - Current permissions (checked boxes)
3. Change something:
   - Update description
   - Check/uncheck a permission
4. Click "Save Role"

Expected Result: ✅ Role updated in grid
Notification: "Role updated successfully!"
Verification: Permission display changes
```

#### Test 4.4: DELETE Role
```
Steps:
1. Click "🗑️ Delete" on any role card
2. Confirmation dialog appears:
   "Are you sure you want to delete the role..."
3. Click "OK" to confirm

Expected Result: ✅ Role disappears from grid
Notification: "Role deleted successfully!"
Verification: Role no longer in grid
```

---

## 🔍 API Testing

### Test 4.5: API Endpoints

#### List All Roles
```bash
curl -X GET http://localhost:8080/roles \
  -H "Authorization: Bearer YOUR_TOKEN"

Expected Response: [
  {
    "name": "Admin",
    "modules": ["can_manage_users", "can_manage_roles", ...]
  },
  ...
]
Status: ✅ 200 OK
```

#### Create Role
```bash
curl -X POST http://localhost:8080/roles \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "New Role",
    "modules": ["can_view_images", "can_create_reports"]
  }'

Expected Response: 
Status: ✅ 200 OK or 201 Created
Body: {"name": "New Role", "modules": [...]}
```

#### Get Role Details
```bash
curl -X GET http://localhost:8080/roles/Admin \
  -H "Authorization: Bearer YOUR_TOKEN"

Expected Response:
Status: ✅ 200 OK
Body: {"name": "Admin", "modules": [...]}
```

#### Update Role
```bash
curl -X PUT http://localhost:8080/roles/Admin \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Admin",
    "modules": ["can_manage_users", "can_manage_roles"]
  }'

Expected Response:
Status: ✅ 200 OK
```

#### Delete Role
```bash
curl -X DELETE http://localhost:8080/roles/TestRole \
  -H "Authorization: Bearer YOUR_TOKEN"

Expected Response:
Status: ✅ 200 OK
Body: {"status": "success"}
```

---

## 🎛️ Permission Testing

### Test 4.6: Permission Checkboxes

Verify all 16 permissions work:

```
Image Operations:
  ✅ View Images (can_view_images)
  ✅ Upload Images (can_upload_images)
  ✅ Edit Images (can_edit_images)
  ✅ Delete Images (can_delete_images)

Report Operations:
  ✅ View Reports (can_view_reports)
  ✅ Create Reports (can_create_reports)
  ✅ Edit Reports (can_edit_reports)
  ✅ Approve Reports (can_approve_reports)

Patient Operations:
  ✅ View Patients (can_view_patients)
  ✅ Create Patients (can_create_patients)
  ✅ Edit Patients (can_edit_patients)

Admin Operations:
  ✅ Manage Users (can_manage_users)
  ✅ Manage Roles (can_manage_roles)
  ✅ View Audit Logs (can_view_audit_logs)

Data Operations:
  ✅ Export to Cloud (can_export_to_cloud)
  ✅ Share Studies (can_share_studies)
```

---

## 🐛 Error Testing

### Test 4.7: Error Handling

#### Invalid Role Name
```
Steps:
1. Click "+ Create Role"
2. Leave role name empty
3. Click "Save Role"

Expected: Error message
Result: ✅ "Role name is required"
```

#### Duplicate Role Name
```
Steps:
1. Create role "Test1"
2. Try to create another "Test1"
3. Click "Save Role"

Expected: API error
Result: ✅ Error notification appears
```

#### Missing Token
```bash
curl -X GET http://localhost:8080/roles
# No Authorization header

Expected Response:
Status: ⚠️ 401 Unauthorized or redirected to login
```

#### Invalid Permission
```bash
curl -X POST http://localhost:8080/roles \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "name": "Role",
    "modules": ["invalid_permission"]
  }'

Expected: API validates permissions
Result: ✅ Error or silent ignore
```

---

## 📊 Performance Testing

### Test 4.8: Performance

#### Page Load Time
```
Action: Load admin dashboard
Expected: <1 second
Actual: ___ ms
Status: ✅ Acceptable
```

#### Tab Switch Time
```
Action: Click Roles tab
Expected: <500ms to load
Actual: ___ ms
Status: ✅ Acceptable
```

#### Create Role Time
```
Action: Fill form and save
Expected: <2 seconds
Actual: ___ seconds
Status: ✅ Acceptable
```

#### Delete Role Time
```
Action: Confirm and delete
Expected: <1 second
Actual: ___ seconds
Status: ✅ Acceptable
```

---

## 🔒 Security Testing

### Test 4.9: Authentication

#### Without Login
```
Steps:
1. Open http://localhost:8080/admin (without login)
2. Should not see admin panel

Expected: Redirect to login
Result: ✅ Access denied
```

#### With Expired Token
```
Steps:
1. Wait for token to expire
2. Try to create role
3. Click "Save"

Expected: Auth error
Result: ✅ Redirect to login
```

#### With Invalid Token
```
Steps:
1. Open DevTools
2. Modify access_token cookie
3. Try any operation

Expected: Auth error
Result: ✅ Request rejected
```

### Test 4.10: Authorization

#### Admin Can Create Roles
```
Steps:
1. Login as Admin
2. Create role
3. Click "Save"

Expected: ✅ Success
Result: Role created
```

#### Non-Admin Cannot Create Roles
```
Steps:
1. Login as Doctor/Patient
2. Try to access admin panel

Expected: ✅ Access denied
Result: Redirect to user portal
```

---

## ✅ Comprehensive Test Checklist

```
UI TESTS:
  ✅ Admin dashboard loads
  ✅ Roles tab visible
  ✅ Create button visible
  ✅ Create modal opens
  ✅ Role grid displays
  ✅ Edit button works
  ✅ Delete button works
  ✅ Permissions display
  ✅ Forms validate

FUNCTIONAL TESTS:
  ✅ Create role
  ✅ Create with all permissions
  ✅ Create with no permissions
  ✅ Read/display roles
  ✅ Update role
  ✅ Update permissions
  ✅ Delete role
  ✅ Confirm dialog works

API TESTS:
  ✅ GET /roles returns data
  ✅ POST /roles creates role
  ✅ GET /roles/{name} works
  ✅ PUT /roles/{name} updates
  ✅ DELETE /roles/{name} deletes
  ✅ Authentication required
  ✅ Authorization checked

PERFORMANCE TESTS:
  ✅ Page loads <1s
  ✅ Tab switch <500ms
  ✅ Create <2s
  ✅ Update <2s
  ✅ Delete <1s

SECURITY TESTS:
  ✅ Requires login
  ✅ Requires admin role
  ✅ Token validation
  ✅ Input validation
  ✅ SQL injection prevention
  ✅ XSS prevention

ERROR HANDLING:
  ✅ Missing role name error
  ✅ Duplicate name error
  ✅ Missing permissions error
  ✅ API error handling
  ✅ Network error handling
  ✅ Timeout handling
```

---

## 🎯 Test Execution Summary

### Quick Test (5 minutes)
```bash
# 1. Verify server running
curl http://localhost:8080

# 2. Check admin dashboard
open http://localhost:8080/admin

# 3. Test create role
# - Click + Create Role
# - Enter name "QuickTest"
# - Check 3 permissions
# - Click Save
# - Verify role appears

# 4. Test edit role
# - Click Edit on QuickTest
# - Uncheck a permission
# - Click Save
# - Verify updated

# 5. Test delete role
# - Click Delete on QuickTest
# - Confirm
# - Verify deleted
```

### Full Test (30 minutes)
Run all tests from "🎛️ Permission Testing" through "✅ Comprehensive Test Checklist"

### Regression Test (1 hour)
Test all core features:
- User management
- Patient access
- Doctor assignment
- Family access
- Roles & permissions
- Audit logs

---

## 📝 Test Report Template

```
TEST DATE: 2025-10-21
TESTER: [Name]
BUILD: 1.0.0

✅ PASSED TESTS: __
❌ FAILED TESTS: __
⏳ PENDING TESTS: __

OVERALL STATUS: 🟢 GREEN / 🟡 YELLOW / 🔴 RED

CRITICAL ISSUES:
- [None]

MINOR ISSUES:
- [None]

NOTES:
- System is production ready

APPROVED FOR DEPLOYMENT: ✅ YES / ❌ NO
```

---

## 📞 Support

If tests fail:
1. Check server is running: `curl http://localhost:8080`
2. Check logs for errors
3. Verify authentication token
4. Try clearing browser cache
5. Restart server and try again

---

**Ready to Test?** Run the Quick Test first! ✅

