# 🎨 Frontend Implementation Guide: User Control & Moderation

## Overview

This guide shows what needs to be added to `dashboard.html` and related frontend files to support:
1. Block/Mute/Ignore user controls
2. Report functionality  
3. Moderator dashboard
4. AI moderator room settings
5. Dynamic credential display

---

## 1. User Control UI Components

### Add to Message Display (Next to User Name)

**In `renderMessages()` function, add action buttons**:

```javascript
// When rendering each message, add user action menu
function renderMessages(messages) {
    const chatContent = document.getElementById('chatContent');
    
    messages.forEach(msg => {
        const msgDiv = document.createElement('div');
        const sender = msg.sender_id || 'System';
        
        // MESSAGE CONTAINER
        msgDiv.innerHTML = `
            <div class="message ${msg.sender_id === currentUser.user_id ? 'sent' : 'received'}">
                <div class="message-header">
                    <span class="sender-alias">${msg.sender_alias || sender}</span>
                    <span class="message-time">${new Date(msg.created_at).toLocaleTimeString()}</span>
                    
                    <!-- USER ACTION MENU (NEW) -->
                    ${msg.sender_id !== currentUser.user_id ? `
                        <div class="user-actions">
                            <button class="action-btn" onclick="openUserMenu('${msg.sender_id}')">⋮</button>
                            <div class="user-menu hidden" id="menu-${msg.sender_id}">
                                <button onclick="muteUser('${msg.sender_id}')">🔇 Mute</button>
                                <button onclick="blockUser('${msg.sender_id}')">🚫 Block</button>
                                <button onclick="ignoreUser('${msg.sender_id}')">👁️ Ignore</button>
                                <button onclick="reportUser('${msg.sender_id}')">⚠️ Report</button>
                            </div>
                        </div>
                    ` : ''}
                </div>
                <div class="message-content">${msg.content}</div>
            </div>
        `;
        
        chatContent.appendChild(msgDiv);
    });
}
```

### CSS for User Actions

```css
.user-actions {
    position: relative;
    display: inline-block;
}

.action-btn {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 16px;
    padding: 4px 8px;
}

.user-menu {
    position: absolute;
    right: 0;
    top: 25px;
    background: #222;
    border: 1px solid #00ff00;
    border-radius: 4px;
    min-width: 120px;
    z-index: 1000;
}

.user-menu button {
    display: block;
    width: 100%;
    padding: 8px 12px;
    background: none;
    border: none;
    color: #0f0;
    cursor: pointer;
    font-size: 13px;
    text-align: left;
}

.user-menu button:hover {
    background: #111;
    color: #0ff;
}

.user-menu.hidden {
    display: none;
}
```

---

## 2. User Control Functions

### Block/Mute/Ignore Implementation

```javascript
async function blockUser(userId) {
    const response = await fetch('/api/sdoh/user/block', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        },
        body: JSON.stringify({ blocked_id: userId })
    });
    
    if (response.ok) {
        showNotification(`✅ User blocked`);
        closeUserMenu();
        // Optionally: hide their messages in current view
        document.querySelectorAll(`[data-sender="${userId}"]`).forEach(el => {
            el.style.display = 'none';
        });
    }
}

async function muteUser(userId) {
    const response = await fetch('/api/sdoh/user/mute', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        },
        body: JSON.stringify({ muted_id: userId })
    });
    
    if (response.ok) {
        showNotification(`🔇 User muted`);
        closeUserMenu();
        // Mark their messages as muted
        document.querySelectorAll(`[data-sender="${userId}"]`).forEach(el => {
            el.classList.add('muted');
        });
    }
}

function ignoreUser(userId) {
    // Add to local ignore list (client-side only)
    let ignoreList = JSON.parse(localStorage.getItem('ignoreList') || '[]');
    if (!ignoreList.includes(userId)) {
        ignoreList.push(userId);
        localStorage.setItem('ignoreList', JSON.stringify(ignoreList));
    }
    showNotification(`👁️ User ignored`);
    closeUserMenu();
}

function openUserMenu(userId) {
    const menu = document.getElementById(`menu-${userId}`);
    menu.classList.toggle('hidden');
}

function closeUserMenu() {
    document.querySelectorAll('.user-menu').forEach(m => {
        m.classList.add('hidden');
    });
}
```

### CSS for Muted Messages

```css
.message.muted {
    opacity: 0.5;
    background: #1a1a1a;
}

.message.muted .message-content {
    color: #666;
}

.message.muted::before {
    content: '[muted] ';
    color: #ff6600;
    font-weight: bold;
}
```

---

## 3. Report Modal

### HTML

```html
<div id="reportModal" class="modal hidden">
    <div class="modal-content">
        <h2>Report User Behavior</h2>
        <div class="form-group">
            <label>User Being Reported:</label>
            <input type="text" id="reportUserId" disabled>
        </div>
        <div class="form-group">
            <label>Reason for Report:</label>
            <select id="reportReason">
                <option>Harassment</option>
                <option>Hate Speech / Slurs</option>
                <option>Threats / Doxxing</option>
                <option>Spam / Advertising</option>
                <option>Inappropriate Content</option>
                <option>Impersonation</option>
                <option>Other</option>
            </select>
        </div>
        <div class="form-group">
            <label>Details:</label>
            <textarea id="reportDetails" placeholder="Describe what happened..."></textarea>
        </div>
        <div class="form-group">
            <label>Context (optional):</label>
            <input type="text" id="reportContext" placeholder="Group name, message ID, etc.">
        </div>
        <div class="button-group">
            <button onclick="submitReport()">Submit Report</button>
            <button onclick="closeReportModal()">Cancel</button>
        </div>
    </div>
</div>
```

### JavaScript

```javascript
function reportUser(userId) {
    document.getElementById('reportUserId').value = userId;
    document.getElementById('reportModal').classList.remove('hidden');
    closeUserMenu();
}

function closeReportModal() {
    document.getElementById('reportModal').classList.add('hidden');
}

async function submitReport() {
    const userId = document.getElementById('reportUserId').value;
    const reason = document.getElementById('reportReason').value;
    const details = document.getElementById('reportDetails').value;
    const context = document.getElementById('reportContext').value;
    
    const response = await fetch('/api/sdoh/report', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        },
        body: JSON.stringify({
            reportee_id: userId,
            reason: `${reason}: ${details}`,
            context: context
        })
    });
    
    if (response.ok) {
        showNotification('✅ Report submitted. Moderators will review.');
        closeReportModal();
    } else {
        showNotification('❌ Error submitting report');
    }
}
```

---

## 4. Settings: Manage Block/Mute Lists

### Add to Settings Modal

```html
<div id="managementSection" class="settings-section">
    <h3>👥 Manage Users</h3>
    
    <div class="control-group">
        <h4>🚫 Blocked Users</h4>
        <div id="blockedList" class="user-list"></div>
        <p id="blockedEmpty" class="empty-state">No blocked users</p>
    </div>
    
    <div class="control-group">
        <h4>🔇 Muted Users</h4>
        <div id="mutedList" class="user-list"></div>
        <p id="mutedEmpty" class="empty-state">No muted users</p>
    </div>
</div>
```

### Load Block/Mute Lists on Settings Open

```javascript
async function loadBlockedLists() {
    const token = localStorage.getItem('authToken');
    
    // Load blocked users
    const blockedResp = await fetch('/api/sdoh/user/blocked-list', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const blockedData = await blockedResp.json();
    
    const blockedList = document.getElementById('blockedList');
    if (blockedData.blocked && blockedData.blocked.length > 0) {
        blockedList.innerHTML = blockedData.blocked.map(b => `
            <div class="user-item">
                <span>${b.user_id}</span>
                <button onclick="unblockUser('${b.user_id}')">Unblock</button>
            </div>
        `).join('');
        document.getElementById('blockedEmpty').style.display = 'none';
    }
    
    // Load muted users (same pattern)
    const mutedResp = await fetch('/api/sdoh/user/muted-list', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const mutedData = await mutedResp.json();
    
    const mutedList = document.getElementById('mutedList');
    if (mutedData.muted && mutedData.muted.length > 0) {
        mutedList.innerHTML = mutedData.muted.map(m => `
            <div class="user-item">
                <span>${m.user_id}</span>
                <button onclick="unmuteUser('${m.user_id}')">Unmute</button>
            </div>
        `).join('');
        document.getElementById('mutedEmpty').style.display = 'none';
    }
}

async function unblockUser(userId) {
    await fetch(`/api/sdoh/user/block/${userId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('authToken')}` }
    });
    loadBlockedLists();
}

async function unmuteUser(userId) {
    await fetch(`/api/sdoh/user/mute/${userId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('authToken')}` }
    });
    loadBlockedLists();
}
```

---

## 5. AI Moderator Room Settings

### Add to Room Settings

```html
<div id="aiModeratorSection" class="settings-section" style="display: none;">
    <h3>🤖 AI Moderator (Optional)</h3>
    <p>Add an optional LLM moderator to help with spam/abuse detection.</p>
    <p><strong>Note:</strong> AI moderator doesn't count toward 20-user room limit.</p>
    
    <div class="form-group">
        <label>
            <input type="checkbox" id="aiModEnabled" onchange="toggleAiModerator()">
            Enable AI Moderator
        </label>
    </div>
    
    <div id="aiKeySection" style="display: none;">
        <label>Optional: Provide Custom Gemini API Key</label>
        <input type="password" id="aiModKey" placeholder="Leave blank to use system default">
        <p style="font-size: 12px; color: #888;">
            If left blank, your room uses the system Gemini key.
        </p>
    </div>
    
    <button onclick="saveAiModeratorSettings()">Save</button>
</div>
```

### Show Only for Room Creator

```javascript
function openRoomSettings(groupId) {
    const group = currentGroups.find(g => g.id === groupId);
    
    // Show AI moderator section only for room creator
    if (group && group.created_by === currentUser.user_id) {
        document.getElementById('aiModeratorSection').style.display = 'block';
        document.getElementById('aiModEnabled').checked = group.ai_moderator_enabled || false;
    } else {
        document.getElementById('aiModeratorSection').style.display = 'none';
    }
}

function toggleAiModerator() {
    const enabled = document.getElementById('aiModEnabled').checked;
    document.getElementById('aiKeySection').style.display = enabled ? 'block' : 'none';
}

async function saveAiModeratorSettings() {
    const groupId = currentGroup.id;
    const enabled = document.getElementById('aiModEnabled').checked;
    const key = document.getElementById('aiModKey').value;
    
    const response = await fetch(`/api/sdoh/group/${groupId}/set-ai-moderator`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        },
        body: JSON.stringify({
            enable: enabled,
            ai_key: key || null
        })
    });
    
    if (response.ok) {
        showNotification('✅ AI moderator settings saved');
    }
}
```

---

## 6. Display User Credentials

### Add to User Profile View

```html
<div class="user-profile">
    <div class="profile-header">
        <h2 id="profileAlias"></h2>
        <p id="profileCode" style="color: #888;"></p>
    </div>
    
    <div class="profile-section">
        <h3>🏆 Credentials</h3>
        <div id="credentialsList" class="credentials-grid"></div>
    </div>
    
    <div class="profile-section">
        <h3>⭐ Community Rating</h3>
        <div id="peerRating"></div>
    </div>
</div>
```

### Load Credentials

```javascript
async function loadUserProfile(userId) {
    const token = localStorage.getItem('authToken');
    
    // Fetch user credentials (backend endpoint needed)
    const response = await fetch(`/api/sdoh/user/${userId}/credentials`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await response.json();
    
    document.getElementById('profileAlias').textContent = data.alias;
    document.getElementById('profileCode').textContent = data.user_id;
    
    // Display credentials
    const credList = document.getElementById('credentialsList');
    credList.innerHTML = data.credentials.map(cred => `
        <div class="credential-badge">
            <div class="cred-type">${cred.credential_type}</div>
            <div class="cred-name">${cred.credential_name}</div>
            <div class="cred-date">${new Date(cred.earned_at).toLocaleDateString()}</div>
        </div>
    `).join('');
}
```

### CSS for Credentials

```css
.credentials-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 12px;
    margin: 16px 0;
}

.credential-badge {
    background: #111;
    border: 2px solid #0f0;
    border-radius: 8px;
    padding: 12px;
    text-align: center;
}

.cred-type {
    font-size: 11px;
    color: #888;
    text-transform: uppercase;
}

.cred-name {
    font-weight: bold;
    color: #0f0;
    margin: 8px 0;
}

.cred-date {
    font-size: 12px;
    color: #666;
}
```

---

## 7. Moderator Dashboard (New Page)

### Create `/sdoh/moderator.html`

```html
<!DOCTYPE html>
<html>
<head>
    <title>SDOH Chat - Moderator Dashboard</title>
    <style>
        body { background: #000; color: #0f0; font-family: monospace; }
        .mod-dashboard { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .report-item { border: 1px solid #0f0; padding: 16px; margin: 12px 0; border-radius: 4px; }
        .status { padding: 4px 8px; border-radius: 2px; font-weight: bold; }
        .status.pending { background: #ff6600; color: #000; }
        .status.investigating { background: #0066ff; color: #fff; }
        .status.resolved { background: #00cc00; color: #000; }
    </style>
</head>
<body>
    <div class="mod-dashboard">
        <h1>👮 Moderator Dashboard</h1>
        
        <div class="mod-section">
            <h2>📋 Pending Reports</h2>
            <div id="reportsList"></div>
        </div>
        
        <div class="mod-section">
            <h2>📜 Action Log</h2>
            <div id="actionLog"></div>
        </div>
    </div>
    
    <script>
        async function loadReports() {
            const token = localStorage.getItem('authToken');
            const response = await fetch('/api/sdoh/reports', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await response.json();
            
            const reportsList = document.getElementById('reportsList');
            reportsList.innerHTML = data.reports.map(report => `
                <div class="report-item">
                    <p><strong>Reported User:</strong> ${report.reportee}</p>
                    <p><strong>Reason:</strong> ${report.reason}</p>
                    <p><strong>Reporter:</strong> ${report.reporter}</p>
                    <span class="status ${report.status}">${report.status}</span>
                    <button onclick="investigateReport('${report.id}')">Investigate</button>
                </div>
            `).join('');
        }
        
        loadReports();
    </script>
</body>
</html>
```

---

## Summary

These changes enable:
1. ✅ Block/Mute/Ignore controls in message UI
2. ✅ Report functionality with modal
3. ✅ Manage block/mute lists in Settings
4. ✅ AI moderator room configuration
5. ✅ Display user credentials/reputation
6. ✅ Moderator dashboard for investigations

**Next**: Connect these UI elements to the backend endpoints created in flask_app.py v7.

All endpoints return proper JSON. Frontend just needs to consume and display appropriately.
