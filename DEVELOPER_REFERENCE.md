# SDOH Chat - Developer Quick Reference

## 🚀 Getting Started (5 minutes)

### 1. Install
```bash
pip install -r SDOH-chat/requirements.txt
```

### 2. Update main.py (3 lines)
```python
# Add imports
from RIS-1.SDOH-chat.backend.db import init_db
from RIS-1.SDOH-chat.backend.integration import setup_sdoh_routes, setup_sdoh_static

# After creating FastAPI app
init_db()
setup_sdoh_routes(app)
setup_sdoh_static(app)
```

### 3. Run
```bash
python run.py
```

### 4. Visit
```
http://localhost:5000/sdoh/index.html
```

---

## 📱 Test User Flow

### Create Account
1. Click "Sign Up"
2. "Create New Account" → Get code: `5847291634`
3. Alias: `DrSmith`
4. PIN: `1234`
5. Auto-login

### Test Direct Message
1. Create 2 accounts
2. User A: "+ Private Chat" → User B's code
3. Send message
4. User B receives in dashboard

### Test Group Chat
1. User A: "+ Group" → "Test Group"
2. User B: "+ Private Chat" → User A's code
3. User A: Group settings → Add User B
4. Both message in group

---

## 🏗️ Architecture Overview

### Request Flow
```
Frontend (HTML/JS)
    ↓ (HTTP/JSON)
FastAPI Routes (/api/sdoh/*)
    ↓ (Validates with Pydantic)
Business Logic (Routes)
    ↓ (ORM queries)
SQLAlchemy Models
    ↓ (SQL)
SQLite Database
```

### Privacy Flow
```
Raw Data (sender_id: "5847291634")
    ↓ (PrivacyUtils)
Check code_visible setting
    ↓ if FALSE
Return alias only ("DrSmith")
    ↓
Frontend displays ("DrSmith")
```

---

## 🗄️ Database Quick Reference

### Query Examples

```python
from RIS-1.SDOH-chat.backend.db import get_session
from RIS-1.SDOH-chat.backend.models import User, Message, Group, Contact

db = get_session()

# Get user
user = db.query(User).filter(User.user_id == "5847291634").first()

# Get messages for chat
messages = db.query(Message).filter(
    Message.chat_id == "group_123"
).order_by(Message.created_at.desc()).limit(50).all()

# Get user's groups
user.groups  # Direct relationship access

# Get group members
group.members  # Many-to-many relationship

# Get user's contacts
user.contacts  # One-to-many relationship
```

### Important Queries

```python
# Find all messages for a user
user_messages = db.query(Message).filter(
    Message.sender_id == user_id
).all()

# Find all messages in group (excluding deleted)
group_messages = db.query(Message).filter(
    Message.chat_id == group_id,
    Message.deleted_at == None
).order_by(Message.created_at).all()

# Check if users are in same group
group = db.query(Group).filter(Group.id == group_id).first()
user_in_group = user in group.members

# Get unread message count for user
from sqlalchemy import and_
unread = db.query(Message).filter(
    and_(
        Message.chat_id == chat_id,
        Message.sender_id != current_user_id,
        Message.deleted_at == None
    )
).count()
```

---

## 🔑 API Patterns

### Authentication
All protected endpoints require `token` query parameter:
```
GET /api/sdoh/messages/chat_123?token=eyJhbGc...
```

Or pass as query parameter:
```python
# Frontend
fetch(`/api/sdoh/messages/${chatId}?token=${token}`)
```

### Request Format
```python
# POST body
{
    "field1": "value1",
    "field2": "value2"
}

# Pydantic validates before hitting route
```

### Response Format
```python
# Success
{
    "status": "ok",
    "msg_id": "uuid",
    "data": { ... }
}

# Error (FastAPI automatic)
{
    "detail": "Error message",
    "status_code": 400
}
```

---

## 🔒 Privacy Controls Reference

### Privacy Flow Example
```python
# User sets code_visible = False (default)
user.code_visible = False
db.commit()

# When message is returned:
from RIS-1.SDOH-chat.backend.utils.auth_utils import PrivacyUtils

formatted = PrivacyUtils.format_message_response(
    message=msg_obj,
    include_code=False  # Because user's code is private
)

# Result: sender_alias="DrSmith" (no user_id)
```

### Checking Privacy Settings
```python
# Before returning user data
if user.code_visible:
    user_data['user_id'] = user.user_id  # Include code
else:
    user_data['user_id'] = None  # Hide code

# Or use utility
user_response = PrivacyUtils.format_user_for_response(
    user=user_obj,
    show_code=user.code_visible
)
```

---

## 🧪 Testing Endpoints

### Using curl

```bash
# Register
curl -X POST http://localhost:5000/api/sdoh/auth/register \
  -H "Content-Type: application/json" \
  -d '{}'

# Set alias
curl -X POST http://localhost:5000/api/sdoh/auth/set-alias \
  -H "Content-Type: application/json" \
  -d '{"user_id": "5847291634", "alias": "DrSmith"}'

# Set PIN
curl -X POST http://localhost:5000/api/sdoh/auth/set-pin \
  -H "Content-Type: application/json" \
  -d '{"user_id": "5847291634", "pin": "1234"}'

# Login
curl -X POST http://localhost:5000/api/sdoh/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id": "5847291634", "pin": "1234"}'
```

### Using Python

```python
import requests

API = "http://localhost:5000/api/sdoh"

# Register
resp = requests.post(f"{API}/auth/register", json={})
code = resp.json()['user_id']

# Set alias
resp = requests.post(f"{API}/auth/set-alias", json={
    "user_id": code,
    "alias": "DrSmith"
})

# Set PIN
resp = requests.post(f"{API}/auth/set-pin", json={
    "user_id": code,
    "pin": "1234"
})

# Login
resp = requests.post(f"{API}/auth/login", json={
    "user_id": code,
    "pin": "1234"
})
token = resp.json()['token']

# Send message
resp = requests.post(f"{API}/messages/send?token={token}", json={
    "to": "other_user_code",
    "text": "Hello!"
})
```

---

## 🐛 Debugging

### Check Database
```bash
# SQLite CLI
sqlite3 SDOH-chat/sdoh_chat.db

# List tables
.tables

# Check users
SELECT user_id, alias, code_visible FROM users;

# Check messages
SELECT msg_id, sender_id, content FROM messages LIMIT 10;
```

### Enable Logging
```python
# In main.py, after creating app
import logging
logging.basicConfig(level=logging.DEBUG)

# Or for SQLAlchemy
import sqlalchemy.dialects.sqlite
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Check Tokens
```python
from RIS-1.SDOH-chat.backend.utils.auth_utils import AuthUtils

token = "eyJhbGc..."
payload = AuthUtils.verify_token(token)
print(payload)  # {'user_id': '5847291634', 'alias': 'DrSmith', 'exp': ...}
```

---

## 📊 Common Operations

### Add Message to Database
```python
from RIS-1.SDOH-chat.backend.models import Message
from RIS-1.SDOH-chat.backend.db import get_session

db = get_session()
msg = Message(
    sender_id="5847291634",
    chat_id="1234567890",  # recipient code
    content="Hello!",
    msg_type="text"
)
db.add(msg)
db.commit()
```

### Create Group
```python
from RIS-1.SDOH-chat.backend.models import Group
from RIS-1.SDOH-chat.backend.db import get_session

db = get_session()
group = Group(
    group_name="Ward 5 Handover",
    created_by="5847291634",
    is_private=True
)
db.add(group)
db.commit()

# Add creator as member
group.members.append(creator_user)
db.commit()
```

### Search Users
```python
from RIS-1.SDOH-chat.backend.models import User
from RIS-1.SDOH-chat.backend.db import get_session

db = get_session()
results = db.query(User).filter(
    User.alias.ilike("%smith%")
).limit(10).all()
```

---

## 🎨 Frontend Development

### Update Dashboard UI
Edit `frontend/dashboard.html`:
- Update styles in `<style>` section
- Modify HTML structure
- Update JavaScript functions

### Add New Modal
```html
<div id="myModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">Title</div>
        <!-- content -->
        <div class="form-actions">
            <button class="primary" onclick="doAction()">Action</button>
            <button class="secondary" onclick="closeModal()">Cancel</button>
        </div>
    </div>
</div>

<script>
    function openModal() {
        document.getElementById('myModal').classList.add('active');
    }
    
    function closeModal() {
        document.getElementById('myModal').classList.remove('active');
    }
</script>
```

### API Call Pattern
```javascript
const token = localStorage.getItem('sdoh_token');
const API_BASE = '/api/sdoh';

fetch(`${API_BASE}/endpoint?token=${token}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ field: 'value' })
})
.then(res => res.json())
.then(data => {
    if (data.status === 'ok') {
        // Success
    } else {
        // Error in response
    }
})
.catch(err => {
    // Network error
    console.error(err);
});
```

---

## ⚡ Performance Tips

### Database
- Use limit for message queries (max 100)
- Index on (chat_id, created_at) used automatically
- Soft deletes avoid expensive operations

### Frontend
- Load 50 messages at a time
- Lazy load older messages on scroll
- Cache token in localStorage (or use cookies in prod)

### API
- All endpoints return quickly (<100ms)
- Token validation cached where possible
- Paginated responses for large data

---

## 🔐 Security Checklist

- [ ] PIN hashed with bcrypt (12 rounds)
- [ ] Token validated on every request
- [ ] Only sender can delete/edit own messages
- [ ] Codes hidden unless user enables visibility
- [ ] No sensitive data in logs
- [ ] CORS configured properly
- [ ] HTTPS in production
- [ ] httpOnly cookies (not localStorage) for tokens in prod

---

## 📚 File Quick Links

| File | Purpose |
|------|---------|
| `models.py` | Database schema |
| `schemas.py` | Request/response validation |
| `auth_utils.py` | Security utilities |
| `sdoh_auth.py` | Auth endpoints |
| `sdoh_messages.py` | Message endpoints |
| `sdoh_contacts.py` | Contact endpoints |
| `sdoh_groups.py` | Group endpoints |
| `index.html` | Login/Register UI |
| `dashboard.html` | Main chat UI |
| `ARCHITECTURE_PLAN.md` | Full design |
| `README.md` | Features overview |
| `SETUP_GUIDE.md` | Integration guide |

---

**Quick Help**: See ARCHITECTURE_PLAN.md for full API specs  
**Integration Help**: See SETUP_GUIDE.md  
**Feature Help**: See README.md  
