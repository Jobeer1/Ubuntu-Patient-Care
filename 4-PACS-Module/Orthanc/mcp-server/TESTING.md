# MCP Server - Testing Guide

## 🧪 Complete Testing Checklist

### Prerequisites
- MCP Server installed and running
- Database initialized
- `.env` file configured

---

## Test 1: Server Health Check ✓

### Test the server is running
```bash
curl http://localhost:8080/health
```

**Expected Response:**
```json
{
  "status": "healthy"
}
```

---

## Test 2: API Documentation ✓

### Access interactive API docs
Open in browser: http://localhost:8080/docs

**Expected:** Swagger UI with all endpoints listed

---

## Test 3: User Management ✓

### List all users
```bash
curl http://localhost:8080/users
```

**Expected:** JSON array with default users (admin, radiologist, tech)

### Create a new user
```bash
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@clinic.org",
    "name": "Test User",
    "role": "Technician"
  }'
```

**Expected:** User object with ID

### Get specific user
```bash
curl http://localhost:8080/users/1
```

**Expected:** User details for ID 1

---

## Test 4: JWT Token Generation ✓

### Manual token creation (for testing)

Create a Python script `test_jwt.py`:
```python
from app.services import JWTService

token_data = {
    "user_id": 1,
    "email": "test@clinic.org",
    "name": "Test User",
    "role": "Radiologist"
}

token = JWTService.create_access_token(token_data)
print(f"JWT Token: {token}")

# Verify token
payload = JWTService.verify_token(token)
print(f"Payload: {payload}")
```

Run:
```bash
python test_jwt.py
```

**Expected:** Token string and decoded payload

---

## Test 5: Token Validation ✓

### Validate a JWT token
```bash
curl -X POST http://localhost:8080/token/validate \
  -H "Content-Type: application/json" \
  -d '{
    "token": "YOUR_JWT_TOKEN_HERE",
    "resource": "/studies/123"
  }'
```

**Expected:**
```json
{
  "valid": true,
  "user_id": 1,
  "email": "test@clinic.org",
  "role": "Radiologist",
  "message": "Token is valid"
}
```

---

## Test 6: Audit Logging ✓

### View audit logs
```bash
curl http://localhost:8080/audit/logs
```

**Expected:** Array of audit log entries

### View logs for specific user
```bash
curl http://localhost:8080/audit/user/1
```

**Expected:** Audit logs for user ID 1

---

## Test 7: OAuth Authentication (Google) ✓

### Prerequisites
- Google OAuth credentials configured in `.env`
- Server running

### Test flow
1. Open browser: http://localhost:8080/test
2. Click "Sign in with Google"
3. Login with Google account
4. Should redirect back with authentication

**Expected:** 
- Redirected to RIS frontend URL
- Cookie `access_token` set
- Audit log entry created

### Verify authentication
```bash
curl http://localhost:8080/auth/status \
  --cookie "access_token=YOUR_TOKEN"
```

**Expected:**
```json
{
  "authenticated": true,
  "user": {
    "id": 1,
    "email": "your@email.com",
    "name": "Your Name",
    "role": "Radiologist"
  }
}
```

---

## Test 8: OAuth Authentication (Microsoft) ✓

### Prerequisites
- Microsoft OAuth credentials configured in `.env`
- Server running

### Test flow
1. Open browser: http://localhost:8080/test
2. Click "Sign in with Microsoft"
3. Login with Microsoft account
4. Should redirect back with authentication

**Expected:** Same as Google test

---

## Test 9: Logout ✓

### Test logout
```bash
curl http://localhost:8080/auth/logout \
  --cookie "access_token=YOUR_TOKEN"
```

**Expected:**
```json
{
  "message": "Logged out successfully"
}
```

Cookie should be deleted.

---

## Test 10: PACS Integration (Token Validation) ✓

### Simulate PACS proxy validation

Create a test script `test_pacs_access.py`:
```python
import requests

# Get a valid token first (from OAuth or manual creation)
token = "YOUR_JWT_TOKEN"

# Simulate PACS proxy validating token
response = requests.post(
    "http://localhost:8080/token/validate",
    json={
        "token": token,
        "resource": "/studies/123"
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

if response.json()["valid"]:
    print("✓ Access granted to PACS")
else:
    print("✗ Access denied")
```

**Expected:** Valid token grants access

---

## Test 11: RIS Integration ✓

### Test RIS authentication flow

1. RIS frontend redirects to: `http://localhost:8080/auth/google`
2. User authenticates
3. MCP redirects to: `https://127.0.0.1:5443` with JWT cookie
4. RIS validates JWT on each API call

### Test JWT in RIS requests
```bash
curl https://127.0.0.1:5443/api/reports \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Expected:** RIS backend validates token and returns data

---

## Test 12: Role-Based Access Control ✓

### Test different roles

Create users with different roles:
```bash
# Admin
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","name":"Admin","role":"Admin"}'

# Radiologist
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{"email":"rad@test.com","name":"Radiologist","role":"Radiologist"}'

# Technician
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{"email":"tech@test.com","name":"Tech","role":"Technician"}'
```

Generate tokens for each and verify role in payload.

---

## Test 13: Token Expiration ✓

### Test expired token

1. Create a token with short expiration:
```python
from app.services import JWTService

token = JWTService.create_access_token(
    {"user_id": 1, "email": "test@test.com"},
    expires_delta=1  # 1 second
)
print(token)
```

2. Wait 2 seconds

3. Validate token:
```bash
curl -X POST http://localhost:8080/token/validate \
  -H "Content-Type: application/json" \
  -d '{"token": "EXPIRED_TOKEN"}'
```

**Expected:**
```json
{
  "valid": false,
  "message": "Invalid or expired token"
}
```

---

## Test 14: Concurrent Users ✓

### Load test with multiple users

Create `load_test.py`:
```python
import requests
import concurrent.futures

def test_user(user_id):
    response = requests.get(f"http://localhost:8080/users/{user_id}")
    return response.status_code

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(test_user, i) for i in range(1, 11)]
    results = [f.result() for f in futures]
    
print(f"Success rate: {results.count(200)}/10")
```

**Expected:** All requests succeed

---

## Test 15: Security Tests ✓

### Test invalid token
```bash
curl -X POST http://localhost:8080/token/validate \
  -H "Content-Type: application/json" \
  -d '{"token": "invalid.token.here"}'
```

**Expected:** `valid: false`

### Test SQL injection (should be prevented)
```bash
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com; DROP TABLE users;--","name":"Hacker"}'
```

**Expected:** Request fails or email is sanitized

### Test XSS (should be prevented)
```bash
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","name":"<script>alert(1)</script>"}'
```

**Expected:** Script tags escaped or rejected

---

## Test 16: Audit Trail Verification ✓

### Verify all actions are logged

1. Perform various actions (login, create user, etc.)
2. Check audit logs:
```bash
curl http://localhost:8080/audit/logs | python -m json.tool
```

**Expected:** All actions logged with:
- Timestamp
- User ID and email
- Action type
- IP address
- Success/failure

---

## Test 17: Database Integrity ✓

### Check database
```bash
sqlite3 mcp_server.db "SELECT * FROM users;"
sqlite3 mcp_server.db "SELECT * FROM audit_logs LIMIT 10;"
sqlite3 mcp_server.db "SELECT * FROM roles;"
```

**Expected:** All tables populated correctly

---

## Test 18: Error Handling ✓

### Test various error scenarios

#### Missing user
```bash
curl http://localhost:8080/users/9999
```
**Expected:** 404 Not Found

#### Invalid JSON
```bash
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d 'invalid json'
```
**Expected:** 422 Unprocessable Entity

#### Duplicate user
```bash
# Create user twice with same email
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{"email":"dup@test.com","name":"Test"}'

curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{"email":"dup@test.com","name":"Test"}'
```
**Expected:** Second request fails with 400

---

## Test 19: Performance ✓

### Measure response times

```bash
# Test token validation speed
time curl -X POST http://localhost:8080/token/validate \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_TOKEN"}'
```

**Expected:** < 100ms response time

---

## Test 20: Integration Test (Full Flow) ✓

### Complete authentication flow

1. Start MCP server
2. Open test page: http://localhost:8080/test
3. Click "Sign in with Google"
4. Complete Google authentication
5. Verify redirected with token
6. Check authentication status
7. Access PACS (simulate with token validation)
8. Access RIS (simulate with token validation)
9. View audit logs
10. Logout

**Expected:** All steps complete successfully

---

## 🎯 Test Results Summary

Create a checklist:

```
[ ] Server health check
[ ] API documentation accessible
[ ] User management (CRUD)
[ ] JWT token generation
[ ] Token validation
[ ] Audit logging
[ ] Google OAuth
[ ] Microsoft OAuth
[ ] Logout functionality
[ ] PACS integration
[ ] RIS integration
[ ] Role-based access
[ ] Token expiration
[ ] Concurrent users
[ ] Security tests
[ ] Audit trail
[ ] Database integrity
[ ] Error handling
[ ] Performance
[ ] Full integration flow
```

---

## 🐛 Troubleshooting

### Server won't start
- Check Python version (3.8+)
- Verify all dependencies installed
- Check `.env` file exists
- View logs: `tail -f logs/mcp-server.log`

### OAuth not working
- Verify credentials in `.env`
- Check redirect URIs match exactly
- Ensure HTTPS in production
- Check Google/Microsoft console settings

### Token validation fails
- Verify JWT_SECRET_KEY matches
- Check token hasn't expired
- Ensure token format is correct

### Database errors
- Delete and recreate: `rm mcp_server.db && python scripts/setup_database.py`
- Check file permissions
- Verify SQLite installed

---

## 📊 Automated Testing

Create `run_all_tests.sh`:
```bash
#!/bin/bash

echo "Running all MCP Server tests..."

# Test 1: Health check
echo "Test 1: Health check"
curl -s http://localhost:8080/health | grep "healthy" && echo "✓ PASS" || echo "✗ FAIL"

# Test 2: List users
echo "Test 2: List users"
curl -s http://localhost:8080/users | grep "email" && echo "✓ PASS" || echo "✗ FAIL"

# Add more tests...

echo "Testing complete!"
```

Run: `bash run_all_tests.sh`

---

## 📝 Test Report Template

```
MCP Server Test Report
Date: [DATE]
Tester: [NAME]
Version: 1.0.0

Test Results:
- Total Tests: 20
- Passed: __
- Failed: __
- Skipped: __

Failed Tests:
1. [Test name] - [Reason]

Notes:
[Additional observations]

Recommendation:
[ ] Ready for production
[ ] Needs fixes
```
