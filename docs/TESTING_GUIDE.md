# Testing Guide - Patient Image Access Control System

**Version**: 1.0
**Date**: 2025-10-21
**Status**: Ready for Testing

---

## 🎯 Quick Start Testing

### Prerequisites
1. ✅ MCP server running on port 8080
2. ✅ PACS backend running on port 5000
3. ✅ Database migrations applied
4. ✅ Test users created

---

## 👥 Test User Accounts

Create these test users in the MCP database:

### Admin User
```
Email: admin@hospital.com
Password: admin123
Role: Admin
```

### Radiologist User
```
Email: radiologist@hospital.com
Password: radio123
Role: Radiologist
```

### Referring Doctor User
```
Email: doctor@hospital.com
Password: doctor123
Role: Referring Doctor
```

### Patient User
```
Email: patient@hospital.com
Password: patient123
Role: Patient
Patient ID: P123 (must exist in PACS)
```

---

## 🧪 Test Scenarios

### Test 1: Admin Workflow
**Objective**: Verify admin can manage patient access

**Steps**:
1. Open http://localhost:8080
2. Log in as admin@hospital.com
3. Verify you stay on MCP dashboard
4. Click "Patient Access" tab
5. Click "Grant Access" button
6. Fill form:
   - User: Select doctor@hospital.com
   - Patient ID: P123
   - Access Level: read
7. Click "Submit"
8. Verify success message
9. Verify entry appears in table

**Expected Result**: ✅ Access granted successfully

---

### Test 2: Doctor Auto-Redirect
**Objective**: Verify doctor is redirected to PACS

**Steps**:
1. Open http://localhost:8080
2. Log in as doctor@hospital.com
3. Wait for redirect

**Expected Result**: 
- ✅ Redirected to http://localhost:5000/patients
- ✅ User banner shows "Dr. [Name]" and "Referring Doctor"
- ✅ Access badge shows "🔒 Limited Access (X patients)"
- ✅ Only assigned patients visible

---

### Test 3: Patient Auto-Redirect
**Objective**: Verify patient is redirected to PACS

**Steps**:
1. Open http://localhost:8080
2. Log in as patient@hospital.com
3. Wait for redirect

**Expected Result**:
- ✅ Redirected to http://localhost:5000/patients
- ✅ User banner shows patient name and "Patient" role
- ✅ Access badge shows "🔒 Limited Access (X patients)"
- ✅ Only own records visible

---

### Test 4: Doctor Assignment
**Objective**: Verify admin can assign doctor to patient

**Steps**:
1. Log in as admin@hospital.com
2. Go to "Doctor Assignments" tab
3. Click "Assign Doctor"
4. Fill form:
   - Doctor: Select doctor@hospital.com
   - Patient ID: P456
   - Assignment Type: primary
5. Click "Submit"
6. Verify success message
7. Log out
8. Log in as doctor@hospital.com
9. Verify P456 is now visible

**Expected Result**: ✅ Doctor can now access P456

---

### Test 5: Family Access
**Objective**: Verify admin can grant family access

**Steps**:
1. Log in as admin@hospital.com
2. Go to "Family Access" tab
3. Click "Grant Family Access"
4. Fill form:
   - Parent User: Select patient@hospital.com
   - Child Patient ID: P789
   - Relationship: parent
5. Click "Submit"
6. Verify success message
7. Log out
8. Log in as patient@hospital.com
9. Verify P789 is now visible

**Expected Result**: ✅ Parent can now access child's records

---

### Test 6: Access Revocation
**Objective**: Verify admin can revoke access

**Steps**:
1. Log in as admin@hospital.com
2. Go to "Patient Access" tab
3. Find entry for doctor@hospital.com → P123
4. Click "Revoke" button
5. Confirm revocation
6. Verify success message
7. Log out
8. Log in as doctor@hospital.com
9. Verify P123 is no longer visible

**Expected Result**: ✅ Access revoked successfully

---

### Test 7: No Token Access
**Objective**: Verify PACS requires authentication

**Steps**:
1. Open http://localhost:5000/patients directly (no login)
2. Observe the page

**Expected Result**:
- ✅ "Authentication Required" screen shown
- ✅ Lock icon displayed
- ✅ "Go to Login" button present
- ✅ No patient data visible

---

### Test 8: Expired Token
**Objective**: Verify expired tokens are handled

**Steps**:
1. Log in as doctor@hospital.com
2. Wait for token to expire (or manually expire in DB)
3. Refresh PACS page
4. Observe the page

**Expected Result**:
- ✅ "Session Expired" screen shown
- ✅ Warning icon displayed
- ✅ "Log In Again" button present
- ✅ No patient data visible

---

### Test 9: Token Validation
**Objective**: Verify token is validated with MCP

**Steps**:
1. Log in as doctor@hospital.com
2. Open browser DevTools (F12)
3. Go to Network tab
4. Observe requests

**Expected Result**:
- ✅ Request to /auth/status (MCP server)
- ✅ Request to /access/user/{id}/patients (MCP server)
- ✅ Both return 200 OK
- ✅ User info displayed correctly

---

### Test 10: Patient Filtering
**Objective**: Verify patients are filtered correctly

**Steps**:
1. Log in as admin@hospital.com
2. Grant access to doctor@hospital.com for P123 only
3. Log out
4. Log in as doctor@hospital.com
5. Search for different patients

**Expected Result**:
- ✅ P123 is visible and accessible
- ✅ Other patients are not visible
- ✅ Search only returns P123
- ✅ No error messages

---

## 🔍 API Testing

### Test API Endpoints with cURL

**1. Verify Token**:
```bash
curl -X GET http://localhost:8080/auth/status \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Expected**: 200 OK with user info

**2. Get Accessible Patients**:
```bash
curl -X GET http://localhost:8080/access/user/5/patients \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected**: 200 OK with patient list

**3. Check Access**:
```bash
curl -X GET "http://localhost:8080/access/check?user_id=5&patient_id=P123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected**: 200 OK with has_access: true/false

**4. Grant Access**:
```bash
curl -X POST http://localhost:8080/access/patient-relationship \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "P123",
    "user_id": 5,
    "access_level": "read"
  }'
```

**Expected**: 200 OK with success message

---

## 🐛 Common Issues & Solutions

### Issue 1: Redirect Loop
**Symptom**: Page keeps redirecting
**Solution**: Clear localStorage and cookies, log in again

### Issue 2: Token Not Found
**Symptom**: "Authentication Required" screen
**Solution**: Log in through MCP server first

### Issue 3: No Patients Visible
**Symptom**: Empty patient list for doctor/patient
**Solution**: Admin must grant access first

### Issue 4: MCP Server Connection Failed
**Symptom**: "Failed to initialize access control"
**Solution**: Verify MCP server is running on port 8080

### Issue 5: CORS Errors
**Symptom**: Network errors in browser console
**Solution**: Configure CORS in MCP server settings

---

## 📊 Test Results Template

Use this template to document test results:

```
Test Date: ___________
Tester: ___________

| Test # | Test Name | Status | Notes |
|--------|-----------|--------|-------|
| 1 | Admin Workflow | ☐ Pass ☐ Fail | |
| 2 | Doctor Auto-Redirect | ☐ Pass ☐ Fail | |
| 3 | Patient Auto-Redirect | ☐ Pass ☐ Fail | |
| 4 | Doctor Assignment | ☐ Pass ☐ Fail | |
| 5 | Family Access | ☐ Pass ☐ Fail | |
| 6 | Access Revocation | ☐ Pass ☐ Fail | |
| 7 | No Token Access | ☐ Pass ☐ Fail | |
| 8 | Expired Token | ☐ Pass ☐ Fail | |
| 9 | Token Validation | ☐ Pass ☐ Fail | |
| 10 | Patient Filtering | ☐ Pass ☐ Fail | |

Overall Result: ☐ All Pass ☐ Some Failures

Issues Found:
1. ___________
2. ___________
3. ___________
```

---

## 🚀 Performance Testing

### Load Test Scenarios

**1. Concurrent Users**:
- Simulate 50 concurrent users
- Each user logs in and views patients
- Measure response times

**2. Database Performance**:
- Query 1000 patients
- Measure query time (<100ms expected)

**3. Token Validation**:
- Validate 100 tokens
- Measure average time (<200ms expected)

**4. Patient Filtering**:
- Filter 1000 patients
- Measure client-side time (<50ms expected)

---

## 🔐 Security Testing

### Security Test Checklist

- [ ] SQL injection attempts blocked
- [ ] XSS attempts blocked
- [ ] Invalid tokens rejected
- [ ] Expired tokens rejected
- [ ] Unauthorized access denied
- [ ] CSRF protection working
- [ ] Audit logs created
- [ ] Sensitive data not exposed

### Penetration Testing

**1. Token Manipulation**:
- Try modifying JWT token
- Expected: Rejected

**2. Direct API Access**:
- Try accessing API without token
- Expected: 401 Unauthorized

**3. Role Escalation**:
- Try accessing admin endpoints as doctor
- Expected: 403 Forbidden

**4. Patient ID Manipulation**:
- Try accessing unauthorized patient
- Expected: 403 Forbidden

---

## 📝 Test Report Template

```
# Test Report - Patient Image Access Control

**Date**: ___________
**Tester**: ___________
**Environment**: Development / Staging / Production

## Summary
- Total Tests: ___
- Passed: ___
- Failed: ___
- Pass Rate: ___%

## Functional Tests
[Results from Test Scenarios 1-10]

## API Tests
[Results from API Testing]

## Performance Tests
[Results from Performance Testing]

## Security Tests
[Results from Security Testing]

## Issues Found
1. [Issue description]
   - Severity: High / Medium / Low
   - Status: Open / Fixed
   
2. [Issue description]
   - Severity: High / Medium / Low
   - Status: Open / Fixed

## Recommendations
1. ___________
2. ___________
3. ___________

## Sign-off
Tester: ___________ Date: ___________
Reviewer: ___________ Date: ___________
```

---

## 🎯 Acceptance Criteria

System is ready for production when:

- [ ] All 10 test scenarios pass
- [ ] All API endpoints return correct responses
- [ ] Performance meets requirements (<1s page load)
- [ ] Security tests pass
- [ ] No critical bugs found
- [ ] Documentation complete
- [ ] User training completed

---

**Happy Testing!** 🧪

For issues or questions, refer to:
- `IMPLEMENTATION_PROGRESS.md` - Implementation details
- `PROJECT_COMPLETE.md` - System overview
- `ARCHITECTURE_DIAGRAM.md` - Technical architecture
