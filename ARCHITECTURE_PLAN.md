# SDOH Chat - Low-Bandwidth Architecture Plan
## Mxit-Style Chat System for GOTG RIS

**Version**: 1.0  
**Date**: December 27, 2025  
**Status**: Architecture & Planning Phase

---

## 1. Project Overview

### Vision
A **ultra-lightweight, text-first chat platform** optimized for:
- **Low-bandwidth environments** (2G/3G networks, 50KB/s average)
- **Healthcare collaboration** (clinicians, families, patients)
- **Privacy-by-default** (no automatic data sharing)
- **High accessibility** (simple signup, minimal friction)

### Inspired By
**Mxit** (2001-2016 South African platform):
- Text-only by default
- ~5KB per message
- Extremely low server overhead
- Instant signup with numeric codes
- Presence-based communication

### Target Users
- Clinicians coordinating on patient cases
- Family members receiving medical updates
- Patients in low-connectivity areas
- Community health workers in remote regions

---

## 2. Technology Stack

### Backend Framework
- **FastAPI** (already in MCP server) - async, lightweight, excellent streaming support
- **WebSocket** support for real-time messaging
- **Minimal JSON payloads** (no metadata bloat)

### Database
- **SQLite** (bundled, minimal setup) for local deployments
- **PostgreSQL** (optional) for multi-instance deployments
- **Schema optimized for compression** and query performance

### Frontend
- **Pure HTML5/CSS/JavaScript** (no frameworks - keep it tiny)
- **Vanilla WebSocket API** (no Socket.io bloat)
- **Responsive grid layout** - works on small phones
- **Total bundle size target**: <150KB (gzipped)

### Message Protocol
- **Protocol**: JSON over WebSocket (can compress with gzip if needed)
- **Message size target**: 100-500 bytes per message
- **Batch operations**: Group updates to reduce round-trips

---

## 3. Core Features

### 3.1 Authentication & Registration

#### Option A: MCP Server SSO Integration
```
User → "Sign in with GOTG" → OAuth/SSO → Gets user_id + name
```
**Pros**: One-click, automatic setup  
**Cons**: Requires internet for registration

#### Option B: 10-Digit Code + Password (Low-Bandwidth First)
```
Offline Registration:
1. App generates random 10-digit code (e.g., 5847291634)
2. User sets 4-8 character PIN (simple password)
3. Code + PIN hashed, stored locally
4. Code becomes user identifier in chats

Example: User "5847291634" can be added by code
```
**Pros**: Works offline, no personal info required  
**Cons**: Less user-friendly  

#### Hybrid Approach (Recommended)
- **Default**: 10-digit code + PIN (offline-capable)
- **Optional**: Link to MCP SSO if available
- **Benefit**: Works in any scenario, privacy-respecting

### 3.2 User Identity

#### Identifier Format
```json
{
  "user_id": "5847291634",           // 10-digit code (PRIMARY KEY - HIDDEN)
  "alias": "DrSmith",                // REQUIRED, UNIQUE, visible in chats
  "pin_hash": "sha256(...)",         // PIN verification
  "sso_id": "google_oauth_id",       // Optional MCP OAuth link
  "is_code_visible": false           // Default: 10-digit code hidden
}
```

#### Privacy Model (Privacy-First Default)

**In Group Chats**:
- Users see: `DrSmith` (alias only)
- Hidden: 10-digit code `5847291634`
- Code only shared if user manually exchanges it

**In Private Chats (1-to-1)**:
- Initiated by: User sharing their 10-digit code
- Example: "Add me: 5847291634"
- Once added: Can message using alias or code

**Code Visibility Control**:
- **Default**: Code hidden (most private)
- **Optional**: User can enable "Show my code" for easier discovery
- **Never automatic**: Code never shown without user consent

---

## 4. Messaging System

### 4.1 Message Format

#### Core Payload (Minimal)
```json
{
  "id": "msg_156839",          // Client-generated UUID (10 bytes)
  "from": "5847291634",        // 10 digits
  "to": "1234567890",          // 1-to-1 or group_id
  "text": "How is patient?",    // Max 500 chars (IMPORTANT: No auto-expansion)
  "ts": 1703702400,            // Unix timestamp (4 bytes)
  "type": "text"               // text, status, notice
}
```

**Size breakdown**: ~80 bytes per message (before compression)

#### Extended Payload (Optional)
```json
{
  "voice_url": "/voice/msg_156839.wav",  // 10-20KB voice note
  "reply_to": "msg_156838",              // Quote/reply
  "emoji": "✓",                          // Reaction (if supported)
  "edit_id": "msg_156839_v2"             // Edit history
}
```

### 4.2 Chat Types

#### 1-to-1 Chat
- **Endpoint**: `/chat/{user_code}`
- **Private by default**
- **No presence indicator** (reduces traffic)
- **Simple message list**

#### Group Chat
- **Endpoint**: `/group/{group_id}` (generated UUID)
- **Group name**: Optional
- **Members**: List of user codes
- **Privacy**: Explicitly set (open/private/invite-only)
- **Max members**: 50 (keep it lightweight)

#### Status Updates (Broadcast)
- **Endpoint**: `/status/{user_code}`
- **Content**: "Available", "In meeting", "At lunch"
- **No chat history** - current status only
- **Auto-clears** after 8 hours

---

## 5. Data Model

### Tables (Minimal Schema)

#### users
```sql
CREATE TABLE users (
  user_id TEXT PRIMARY KEY,        -- 10-digit code (HIDDEN by default)
  alias TEXT NOT NULL UNIQUE,      -- Display name in chats (REQUIRED)
  pin_hash TEXT NOT NULL,          -- bcrypt(pin)
  sso_id TEXT UNIQUE,              -- Link to MCP OAuth (optional)
  code_visible BOOLEAN DEFAULT FALSE, -- Show code in profile (opt-in)
  created_at TIMESTAMP DEFAULT NOW(),
  last_login TIMESTAMP,
  device_fingerprint TEXT          -- Detect multi-device usage
);
```

#### messages
```sql
CREATE TABLE messages (
  msg_id TEXT PRIMARY KEY,         -- Client-generated UUID
  sender_id TEXT NOT NULL,         -- 10-digit code
  chat_id TEXT NOT NULL,           -- user_id or group_id
  content TEXT NOT NULL,           -- Message text (max 500 chars)
  msg_type VARCHAR(20),            -- text, status, notice, voice
  created_at TIMESTAMP DEFAULT NOW(),
  edited_at TIMESTAMP,
  deleted_at TIMESTAMP,            -- Soft delete
  FOREIGN KEY (sender_id) REFERENCES users(user_id),
  INDEX (chat_id, created_at)      -- Critical for performance
);
```

#### groups
```sql
CREATE TABLE groups (
  group_id TEXT PRIMARY KEY,       -- UUID
  group_name TEXT,
  created_by TEXT NOT NULL,
  is_private BOOLEAN DEFAULT TRUE,
  member_limit INT DEFAULT 50,
  created_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (created_by) REFERENCES users(user_id)
);
```

#### group_members
```sql
CREATE TABLE group_members (
  group_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  joined_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (group_id, user_id),
  FOREIGN KEY (group_id) REFERENCES groups(group_id),
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

#### contacts
```sql
CREATE TABLE contacts (
  user_id TEXT NOT NULL,
  contact_id TEXT NOT NULL,       -- Other user's code
  contact_name TEXT,              -- Their display name (user-set)
  added_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (user_id, contact_id),
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

---

## 6. API Endpoints

### Authentication

#### POST /api/auth/register
**No personal info required - alias is unique identifier in chats**
```json
Request: {} (empty - generate code server-side)
Response: {
  "user_id": "5847291634",
  "needs_alias": true
}
```

#### POST /api/auth/set-alias
**Set unique alias (visible in chats)**
```json
Request: {
  "user_id": "5847291634",
  "alias": "DrSmith"
}
Response: {
  "status": "ok",
  "alias": "DrSmith"
}
```

#### POST /api/auth/login
**10-digit code + PIN (code stays hidden in chats)**
```json
Request: {
  "user_id": "5847291634",
  "pin": "1234"
}
Response: {
  "token": "jwt_short_lived",
  "alias": "DrSmith",
  "expires_in": 86400
}
```

#### POST /api/auth/set-pin
**Set password after registration**
```json
Request: {
  "user_id": "5847291634",
  "pin": "1234"
}
Response: {"status": "ok"}
```

#### POST /api/auth/sso-link (Optional)
**Link existing code to OAuth**
```json
Request: {
  "user_id": "5847291634",
  "sso_token": "oauth_token"
}
Response: {"status": "linked"}
```

---

### Messages

#### WS /ws/chat/{user_id}
**WebSocket for real-time messaging**

**Events**:
```json
// Incoming message
{
  "type": "message",
  "from": "1234567890",
  "to": "5847291634",
  "text": "Hello",
  "ts": 1703702400
}

// Typing indicator (minimal)
{
  "type": "typing",
  "from": "1234567890",
  "to": "5847291634"
}

// Delivery confirmation
{
  "type": "ack",
  "msg_id": "msg_156839",
  "status": "delivered"
}
```

#### GET /api/messages/{chat_id}?limit=50&offset=0
**Fetch message history**

**Response** (100 messages ≈ 20KB):
```json
{
  "messages": [
    {
      "id": "msg_156839",
      "from": "5847291634",
      "text": "How is patient?",
      "ts": 1703702400
    }
  ],
  "has_more": true
}
```

#### POST /api/messages
**Send message (fallback for poor connectivity)**
```json
Request: {
  "to": "1234567890",
  "text": "I'm on my way"
}
Response: {"msg_id": "msg_156840", "status": "ok"}
```

#### DELETE /api/messages/{msg_id}
**Delete message (soft delete)**
```json
Response: {"status": "deleted"}
```

---

### Contacts & Groups

#### GET /api/contacts
**List saved contacts (shows aliases, not codes)**
```json
Response: {
  "contacts": [
    {"user_id": "1234567890", "alias": "JohnFamily"},
    {"user_id": "9876543210", "alias": "Clinician22"}
  ]
}
```

#### POST /api/contacts
**Add contact by their 10-digit code (they choose to share it)**
```json
Request: {
  "user_id": "1234567890",
  "contact_alias": "JohnFamily"  (their alias, not their code)
}
Response: {"status": "added", "alias": "JohnFamily"}
```

#### GET /api/groups
**List groups**
```json
Response: {
  "groups": [
    {
      "id": "group_abc123",
      "name": "Ward 5 Handover",
      "members": 8,
      "unread": 3
    }
  ]
}
```

#### POST /api/groups
**Create group**
```json
Request: {
  "name": "Ward 5 Handover",
  "private": true
}
Response: {
  "id": "group_abc123",
  "invite_link": "sdoh://group/group_abc123"
}
```

#### POST /api/groups/{group_id}/members
**Add member to group**
```json
Request: {"user_id": "1234567890"}
Response: {"status": "added"}
```

---

### Status & Presence

#### POST /api/status
**Update presence status**
```json
Request: {"status": "available"}
Response: {"status": "ok", "expires_at": "2025-12-27T16:00:00Z"}
```

#### GET /api/status/{user_id}
**Check user status**
```json
Response: {
  "user_id": "1234567890",
  "status": "available",
  "last_seen": "2025-12-27T15:45:00Z"
}
```

---

### Voice Messages (Optional, High-Bandwidth)

#### POST /api/voice/upload
**Upload voice note (10-30 seconds max)**
```
Content-Type: audio/wav
Body: Binary audio data (50-200KB per message)

Response: {
  "voice_id": "voice_156839",
  "duration": 15,
  "size_bytes": 120000,
  "url": "/voice/voice_156839.wav"
}
```

#### GET /api/voice/{voice_id}
**Stream voice note**
- **Compression**: Optional gzip
- **Streaming**: Supports range requests (resume downloads)

---

## 7. Frontend Architecture

### 7.1 Page Structure

#### Index/Home (`index.html`)
```
┌─────────────────────┐
│ SDOH Chat           │
├─────────────────────┤
│ [Login] [Register]  │
│                     │
│ Or enter 10-digit   │
│ code to join        │
└─────────────────────┘
```

#### Signup/Registration (`register.html`)
```
┌─────────────────────┐
│ Create Account      │
├─────────────────────┤
│ User Code:          │
│ 5847291634          │ (auto-generated)
│                     │
│ Create Alias:       │
│ [DrSmith] (unique)  │
│                     │
│ Set PIN:            │
│ [••••] (4-8 chars)  │
│                     │
│ [Create Account]    │
└─────────────────────┘
```

#### Dashboard (`dashboard.html`)
```
┌──────────────────────────┐
│ DrSmith [Status ▼]       │
├──────────────────────────┤
│ Recent Chats:            │
│ ✓ JohnFamily             │
│ ✓ Ward5Handover (5)      │
│ ✓ Clinician22            │
│                          │
│ [+ Add Private Chat]     │
│ [+ Create Group]         │
│ [Share My Code]          │
│ [Settings]               │
└──────────────────────────┘
```

#### Chat Window (`chat.html`)
```
┌──────────────────────────────┐
│ JohnFamily                   │
├──────────────────────────────┤
│ How is patient doing?        │
│                     15:30    │
│ (From: DrSmith)              │
│                              │
│          Getting better      │
│                     15:45    │
│ (From: JohnFamily)           │
│                              │
│ [Type message...           ] │
│ [Send]                       │
└──────────────────────────────┘
```

### 7.2 JavaScript Modules

#### `auth.js` (Minimal)
- User registration (code + PIN)
- Login functionality
- Token storage (localStorage)
- SSO linking (optional)

#### `ws-client.js` (Critical)
- WebSocket connection management
- Auto-reconnect with exponential backoff
- Message queue (offline support)
- Compression handling

#### `chat.js` (Main Logic)
- Render message list
- Handle sending messages
- Scroll to newest messages
- Mark messages as read

#### `contacts.js`
- Add contact by code
- List saved contacts
- Search contacts
- Delete contact

#### `groups.js`
- Create/edit groups
- List members
- Add/remove members
- Generate invite links

#### `ui.js` (Utils)
- Format timestamps
- Truncate long messages
- Hide user details (privacy)
- Responsive layout helpers

### 7.3 CSS Strategy

**Target**: <50KB uncompressed

```css
/* Minimal reset */
* { margin: 0; padding: 0; box-sizing: border-box; }

/* Mobile-first (most users on phones) */
body { font-size: 14px; line-height: 1.4; }
.container { width: 100%; padding: 10px; }

/* Chat-specific */
.message { padding: 8px; margin: 4px 0; }
.message.sent { text-align: right; }
.message.received { text-align: left; }

/* Dark mode (battery-friendly) */
@media (prefers-color-scheme: dark) {
  body { background: #000; color: #fff; }
}
```

---

## 8. Optimization Strategies

### 8.1 Bandwidth Reduction

#### Message Compression
```javascript
// Client-side compression before sending
const compressed = await gzip(message);
// Send compressed payload (often 40-60% smaller)
```

#### Lazy Loading
```javascript
// Load older messages on-demand
messages.slice(0, 50);  // Show newest 50
if (user_scrolls_up) {
  load_older(50);  // Fetch 50 older
}
```

#### Image/Voice Handling
- **Default**: Text-only (0KB media per message)
- **Optional**: Voice notes with compression
- **No pictures**: Avoid entirely (too much data)
- **Emojis only**: Single character reactions

#### Request Batching
```javascript
// Instead of 10 separate requests
fetch('/api/messages', {
  chats: ['5847291634', 'group_abc123', '1234567890']
})
// Returns all 3 chat histories in one request
```

### 8.2 Performance Optimization

#### Frontend Caching
```javascript
// Cache user's own messages locally
localStorage.setItem(`chat_${contact_id}`, JSON.stringify(messages));
// Show immediately, sync in background
```

#### Database Indexing
```sql
-- Critical indexes for low-bandwidth
CREATE INDEX idx_messages_chat_ts ON messages(chat_id, created_at DESC);
CREATE INDEX idx_users_code ON users(user_id);
CREATE INDEX idx_contacts_user ON contacts(user_id);
```

#### Connection Pooling
```python
# FastAPI async setup - handle 100+ concurrent users on tiny server
pool_size = 5
max_overflow = 10
```

### 8.3 Offline Support

#### Service Worker (`sw.js`)
```javascript
// Cache essential files on install
const CACHE_V1 = 'sdoh-chat-v1';
const URLS = [
  '/',
  '/chat.html',
  '/chat.js',
  '/auth.js',
  '/style.css'
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE_V1).then(c => c.addAll(URLS)));
});

// Queue messages when offline
if (!navigator.onLine) {
  messageQueue.push(message);
  sync_when_online();
}
```

#### Sync API (W3C standard)
```javascript
// When online, automatically sync queued messages
navigator.serviceWorker.ready.then(reg => {
  return reg.sync.register('sync-messages');
});

self.addEventListener('sync', (e) => {
  if (e.tag === 'sync-messages') {
    e.waitUntil(flush_message_queue());
  }
});
```

---

## 9. Security Model

### 9.1 Privacy by Default

**No automatic sharing**:
- Users see only 10-digit code by default
- Display names are opt-in
- No activity tracking visible
- No "typing indicators" (too chatty)
- No seen receipts (privacy-first)

**Group privacy**:
- Private groups (default): Invite-only
- Members list not visible to others
- Content not indexed or stored outside group

### 9.2 Authentication

#### PIN Security
```python
# Server-side
import bcrypt
pin_hash = bcrypt.hashpw(pin.encode(), bcrypt.gensalt(rounds=12))

# Login
if bcrypt.checkpw(pin.encode(), stored_hash):
    token = jwt.encode({'user_id': user_id}, secret, exp=86400)
```

#### Token Management
- **Expiry**: 24 hours
- **Refresh**: Optional, requires PIN
- **Revocation**: On logout, clear token server-side

### 9.3 Message Encryption (Optional Phase 2)

```python
# TLS in transit (always)
# At rest (optional): AES-256 if paranoid

# Group chat consideration:
# If encrypted, server can't search - acceptable tradeoff
```

---

## 10. Deployment Scenarios

### Scenario 1: Hospital/Clinic Deployment
```
Single server instance:
- SQLite database (sufficient for 1000 users)
- FastAPI running on port 5000
- Deployed on existing MCP server
- CORS configured for local network
```

### Scenario 2: Multi-Facility Network
```
Regional deployment:
- PostgreSQL (shared across instances)
- Load balancer (nginx)
- 2-3 FastAPI instances
- Redis for WebSocket state (optional)
```

### Scenario 3: Community Network
```
Decentralized approach:
- Each facility runs own instance
- Federation API (future)
- Message forwarding between instances
```

---

## 11. Implementation Roadmap

### Phase 1: MVP - Mxit-Style Chat (2-3 weeks)
**Focus**: Pure text-based chat, low bandwidth, privacy-first
- ✅ User registration (10-digit code + unique alias + PIN)
- ✅ Alias is visible in chats (10-digit code hidden)
- ✅ 1-to-1 chat (via shared 10-digit code)
- ✅ Group chat creation
- ✅ Message history (last 100 messages)
- ✅ Contact list (shows aliases only)
- ✅ Offline message queue
- ✅ Status updates
- **Launch with**: Text-only, no AI, no extras

### Phase 2: Groups & Polish (1 week)
- ✅ Group member management
- ✅ Group invite links
- ✅ UI/UX refinements
- ✅ Admin dashboard
- ✅ Privacy controls

### Phase 3: Optional Features (As-needed)
- Voice notes (optional, 10-30 sec max)
- Message search
- Edit/delete messages

### Phase 4: ML Agent System - TFR Problem Solving (FUTURE)
**After chat is production-ready, add intelligent agents**

#### What is TFR Problem?
- **TFR**: Transfer Friction/Transfer Request - Complex medical handoff coordination
- **Challenge**: Managing declining requests, multiple stakeholders, incomplete info
- **Solution**: AI agents to assist coordination

#### Agent Architecture (Future Implementation)
```
SDOH Chat System (Phase 1-3) ← Fully functional baseline

+ AI Agent Layer (Phase 4+):
  ├── Triage Agent
  │   └── Analyzes case complexity → Route to appropriate handler
  │
  ├── Information Gathering Agent
  │   └── Asks clarifying questions → Complete missing patient data
  │
  ├── Decision Support Agent
  │   └── Suggests best transfer options → Based on patient profile
  │
  ├── Negotiation Agent (LLM-powered)
  │   └── Handles declining facilities → Suggest alternatives
  │
  └── Documentation Agent
      └── Auto-generates handoff notes → From chat context
```

#### Agent Integration Points (Phase 4)
```
User Chat Flow (Phase 1-3):
User A: "Patient John Doe, needs transfer"
User B: "Where from/to?"
User A: "From Rural Clinic to Metro Hospital"

With Agents (Phase 4+):
System Agent: "Missing info: patient age, diagnosis. Fetching..."
Triage Agent: "Complexity: High. Need specialist review."
Negotiation Agent: "Hospital X unavailable. Suggesting Y, Z..."
Documentation: "Draft handoff note ready for review"
```

#### Why Separate Phases?
1. **Chat must be rock-solid first** - Users trust it with critical info
2. **Agents need clean data** - Can only work with well-structured messages
3. **Different tech stacks** - Chat = simple, Agents = complex ML/LLM
4. **Testing complexity** - Chat tested locally, Agents need production data
5. **User training** - Chat first, then teach agents' capabilities

#### Agent Development Prerequisites
- Minimum 3 months of chat production data
- Clear TFR decline patterns identified
- Clinical team trained on chat system
- ML models validated on real cases

---

## 12. Success Metrics

| Metric | Target | Why |
|--------|--------|-----|
| Message size | <150 bytes avg | Low bandwidth |
| Page load | <2 seconds | Mobile networks |
| Offline capability | 100% | Remote areas |
| User signup time | <30 seconds | Low friction |
| Server memory | <200MB | Cheap servers |
| Battery drain | <5% per hour | Mobile usage |
| Concurrent users | 100+ | Scale |

---

## 13. Privacy Considerations

### What We DON'T Collect
- ❌ Location data
- ❌ Phone numbers (not required for signup)
- ❌ Real names (completely optional)
- ❌ Device info (minimal fingerprinting)
- ❌ Message read receipts
- ❌ Typing indicators
- ❌ Activity logs visible to others

### What We DO Collect (Minimal)
- ✅ 10-digit user code (anonymous identifier, hidden by default)
- ✅ Unique alias (required for chat, visible to others)
- ✅ PIN hash (for authentication only)
- ✅ Message content (end-to-end only, not indexed)
- ✅ Timestamps (for ordering)
- ✅ Group membership (required for functionality)

### Data Retention
- **Messages**: Keep 90 days, then archive
- **User accounts**: Keep until deleted
- **Logs**: Keep 7 days, auto-rotate
- **Backups**: Monthly, encrypted

---

## 14. File Structure

```
SDOH-chat/
├── ARCHITECTURE_PLAN.md          [This document]
├── backend/
│   ├── routes/
│   │   ├── auth.py               [Registration, login, SSO]
│   │   ├── messages.py           [Send, receive, delete]
│   │   ├── contacts.py           [Add, list, delete contacts]
│   │   ├── groups.py             [Create, manage groups]
│   │   ├── status.py             [Presence status]
│   │   └── voice.py              [Voice note handling]
│   ├── models.py                 [SQLAlchemy models]
│   ├── websocket.py              [WebSocket handler]
│   ├── utils/
│   │   ├── auth_utils.py         [PIN hashing, tokens]
│   │   ├── compression.py        [Gzip handling]
│   │   └── privacy.py            [User info masking]
│   └── schemas.py                [Pydantic schemas]
├── frontend/
│   ├── index.html                [Login/Register]
│   ├── dashboard.html            [Main dashboard]
│   ├── chat.html                 [1-to-1 chat]
│   ├── group.html                [Group chat]
│   ├── contacts.html             [Contact management]
│   ├── js/
│   │   ├── auth.js               [Login/register logic]
│   │   ├── ws-client.js          [WebSocket client]
│   │   ├── chat.js               [Chat UI logic]
│   │   ├── contacts.js           [Contact management]
│   │   ├── groups.js             [Group management]
│   │   ├── ui.js                 [UI utilities]
│   │   └── sw.js                 [Service Worker]
│   ├── css/
│   │   ├── style.css             [Main styles]
│   │   ├── responsive.css        [Mobile first]
│   │   └── dark.css              [Dark mode]
│   └── assets/
│       └── logo.svg              [Simple SVG logo]
├── tests/
│   ├── test_auth.py
│   ├── test_messages.py
│   ├── test_groups.py
│   └── test_performance.py       [Bandwidth benchmarks]
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
└── README.md                     [Getting started]
```

---

## 15. Next Steps

1. **Backend Setup**
   - Create FastAPI routes for auth, messages, groups
   - Build SQLite schema (minimal 5 tables)
   - Implement WebSocket handler

2. **Frontend Setup**
   - Create HTML pages (index, dashboard, chat)
   - Implement auth.js (register/login)
   - Build ws-client.js (WebSocket connection)

3. **Integration**
   - Connect frontend to backend
   - Test 1-to-1 messaging
   - Implement offline support

4. **Testing**
   - Bandwidth measurements (target <5KB per message)
   - Load testing (100+ concurrent users)
   - Offline scenarios

5. **Deployment**
   - Dockerize application
   - Configure CORS with MCP server
   - Deploy alongside RIS

---

## 16. Success Checklist

### MVP Launch
- [ ] Users can register with 10-digit code + unique alias + PIN
- [ ] 10-digit code is hidden by default in chats
- [ ] Alias is required and unique
- [ ] Users can share their code for private chats
- [ ] Users can send/receive text messages (1-to-1)
- [ ] Users can create and join groups
- [ ] Message history loads on demand
- [ ] Offline queue works (messages sync when online)
- [ ] Contact list shows aliases only
- [ ] No 10-digit codes visible in group chats
- [ ] No personal info visible by default
- [ ] Mobile responsive
- [ ] Average message <150 bytes
- [ ] Page load <2 seconds
- [ ] Code validation prevents duplicate aliases

### Production Ready
- [ ] Group chat functional
- [ ] User can add by code
- [ ] Invite links work
- [ ] Message deletion works
- [ ] User can set status
- [ ] Status visible to others
- [ ] Aliases are unique across system
- [ ] Code visibility controls work
- [ ] 100+ concurrent users supported
- [ ] Bandwidth <10MB per 100 messages
- [ ] Security review passed
- [ ] Privacy audit passed
- [ ] Ready for AI agent integration (Phase 4)

---

**Version Control**: Architecture v1.0  
**Last Updated**: December 27, 2025  
**Next Review**: After Phase 1 MVP
