const API_BASE = '/api/sdoh';
let currentUser = null;
let currentGroup = null;
let selectedLetterIdx = -1;
let aliasColors = {}; // {index: color}

// Check auth
const token = localStorage.getItem('token');
if (!token) window.location.href = '/sdoh/index.html';

let showXPDetails = false;

function toggleXPDisplay() {
    showXPDetails = !showXPDetails;
    if (currentUser) {
        updateForgePanel(currentUser.integrity_score, currentUser.insights);
    }
}

// RuneScape XP Logic
function getXPForLevel(level) {
    let total = 0;
    for (let l = 1; l < level; l++) {
        const diff = Math.floor(l + 300 * Math.pow(2, l / 7.0));
        total += Math.floor(diff / 4);
    }
    return total;
}

function getLevelAtXP(xp) {
    // Level 1 starts at 0 XP
    // Cap at 99 or 120? Let's go with 99 for now.
    for (let level = 1; level < 100; level++) {
        if (getXPForLevel(level + 1) > xp) {
            return level;
        }
    }
    return 99;
}

function updateForgePanel(score, insights) {
    const bar = document.getElementById('integrity-bar');
    const text = document.getElementById('integrity-score-text');
    const list = document.getElementById('insights-list');
    
    // Treat score as Total XP
    const currentLevel = getLevelAtXP(score);
    const currentLevelXP = getXPForLevel(currentLevel);
    const nextLevelXP = getXPForLevel(currentLevel + 1);
    
    // Calculate progress within the level
    let progressPercent = 0;
    let xpInLevel = 0;
    let xpNeeded = 0;

    if (currentLevel < 99) {
        xpInLevel = score - currentLevelXP;
        xpNeeded = nextLevelXP - currentLevelXP;
        progressPercent = (xpInLevel / xpNeeded) * 100;
    } else {
        progressPercent = 100;
    }
    
    bar.style.width = `${progressPercent}%`;
    
    // Toggle Text
    if (showXPDetails) {
        text.textContent = `${Math.floor(xpInLevel)} / ${Math.floor(xpNeeded)} XP`;
    } else {
        text.textContent = `Lvl ${currentLevel} (${Math.floor(progressPercent)}%)`;
    }

    // Add click handlers
    const barContainer = bar.parentElement;
    barContainer.onclick = toggleXPDisplay;
    barContainer.style.cursor = 'pointer';
    barContainer.title = "Click to toggle XP view";
    
    text.onclick = toggleXPDisplay;
    text.style.cursor = 'pointer';
    text.title = "Click to toggle XP view";
    
    if (insights && insights.length > 0) {
        list.innerHTML = '';
        // Show last 10 insights reversed
        insights.slice().reverse().slice(0, 10).forEach(insight => {
            const div = document.createElement('div');
            div.style.marginBottom = '5px';
            div.style.paddingBottom = '5px';
            div.style.borderBottom = '1px solid #222';
            
            const xpText = insight.xp ? `<span style="color: #4caf50; font-weight: bold; font-size: 0.9em; margin-left: 5px;">(+${insight.xp} XP)</span>` : '';
            
            div.innerHTML = `• ${insight.text} ${xpText}`;
            list.appendChild(div);
        });
    } else {
        list.innerHTML = '<div style="font-style:italic; color:#666">No insights yet...</div>';
    }
}

// Load Dashboard
async function loadDashboard() {
    try {
        const res = await fetch(`${API_BASE}/dashboard`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (res.status === 401) {
            logout();
            return;
        }
        
        const data = await res.json();
        currentUser = data.user;
        aliasColors = data.user.alias_colors || {};
        
        renderGroups(data.groups);
        loadContacts(); // Load contacts after groups
    } catch (e) {
        console.error(e);
    }
}

function renderGroups(groups) {
    const container = document.getElementById('groups-list');
    container.innerHTML = '';
    
    // 1. Public Chatrooms Category
    const catHeader = document.createElement('div');
    catHeader.className = 'category-header';
    catHeader.innerHTML = `<span><span class="category-arrow expanded">></span> Chat Rooms</span> <span>(${groups.length})</span>`;
    catHeader.onclick = () => {
        toggleCategory('public-chats');
        catHeader.querySelector('.category-arrow').classList.toggle('expanded');
    };
    
    const catContent = document.createElement('div');
    catContent.id = 'public-chats';
    catContent.className = 'category-content'; 
    // Auto-expand if it's the main one
    catContent.classList.add('expanded');
    
    groups.forEach(g => {
        const div = document.createElement('div');
        div.className = 'group-item';
        const memberStatus = `${g.member_count}/${g.max_members}`;
        const isFull = g.member_count >= g.max_members;
        const statusColor = isFull ? 'var(--red)' : '#666';
        
        div.innerHTML = `
            <div style="display:flex; align-items:center">
                <span class="online-dot"></span>
                <span>${g.name}</span>
            </div>
            <span style="font-size:12px; color:${statusColor}">(${memberStatus})</span>
        `;
        div.onclick = () => openChat(g);
        catContent.appendChild(div);
    });
    
    container.appendChild(catHeader);
    container.appendChild(catContent);
    
    // 2. Private Chats (Personal Forge)
    const privHeader = document.createElement('div');
    privHeader.className = 'category-header';
    privHeader.innerHTML = `<span><span class="category-arrow expanded">></span> Private Chats</span> <span>(1)</span>`;
    privHeader.onclick = () => {
        toggleCategory('private-chats');
        privHeader.querySelector('.category-arrow').classList.toggle('expanded');
    };
    
    const privContent = document.createElement('div');
    privContent.id = 'private-chats';
    privContent.className = 'category-content expanded';
    
    // Add Personal Forge
    const forgeDiv = document.createElement('div');
    forgeDiv.className = 'group-item';
    forgeDiv.innerHTML = `
        <div style="display:flex; align-items:center">
            <span class="online-dot" style="background:var(--red); box-shadow:0 0 5px var(--red)"></span>
            <span style="color:var(--red); font-weight:bold">THE FORGE</span>
        </div>
        <span style="font-size:12px; color:#666">[AUDITOR]</span>
    `;
    forgeDiv.onclick = () => openForgeChat();
    privContent.appendChild(forgeDiv);
    
    // Add The Quest
    const questDiv = document.createElement('div');
    questDiv.className = 'group-item';
    questDiv.innerHTML = `
        <div style="display:flex; align-items:center">
            <span class="online-dot" style="background:#ffaa00; box-shadow:0 0 5px #ffaa00"></span>
            <span style="color:#ffaa00; font-weight:bold">THE QUEST</span>
        </div>
        <span style="font-size:12px; color:#666">[MASTER]</span>
    `;
    questDiv.onclick = () => openQuestChat();
    privContent.appendChild(questDiv);
    
    container.appendChild(privHeader);
    container.appendChild(privContent);
    
    // 3. Mock Categories
    addMockCategory(container, 'Apps & Games', 0);
}

function openForgeChat() {
    currentGroup = { id: 'forge', name: 'THE FORGE' };
    document.getElementById('channel-screen').classList.add('hidden');
    document.getElementById('chat-screen').classList.remove('hidden');
    document.getElementById('current-chat-title').textContent = 'THE FORGE [INTEGRITY AUDIT]';
    document.getElementById('current-chat-title').style.color = 'var(--red)';
    document.getElementById('vote-banner').classList.add('hidden');
    
    // Show Forge Panel
    document.getElementById('forge-panel').classList.remove('hidden');
    updateForgePanel(currentUser.integrity_score, currentUser.insights);
    
    loadMessages(`forge_${currentUser.user_id}`);
    
    // Load greeting if no messages
    const messagesContainer = document.getElementById('messages');
    // Wait for loadMessages to finish? No, loadMessages is async.
    // But loadMessages clears the container first.
    // We should probably check AFTER loadMessages returns.
    // For now, let's rely on loadMessages handling the "No messages" state.
}

function openQuestChat() {
    currentGroup = { id: 'quest', name: 'THE QUEST' };
    document.getElementById('channel-screen').classList.add('hidden');
    document.getElementById('chat-screen').classList.remove('hidden');
    document.getElementById('current-chat-title').textContent = 'THE QUEST [CHALLENGE MASTER]';
    document.getElementById('current-chat-title').style.color = '#ffaa00';
    document.getElementById('vote-banner').classList.add('hidden');
    
    loadMessages(`quest_${currentUser.user_id}`);
}

async function loadForgeGreeting() {
    try {
        const res = await fetch(`${API_BASE}/forge/greeting`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        
        // Display greeting as agent message
        const container = document.getElementById('messages');
        container.innerHTML = '';
        const div = document.createElement('div');
        div.className = 'msg';
        div.innerHTML = `
            <span class="msg-sender" style="color:var(--red)">THE FORGE:</span>
            ${data.greeting}
            <span class="msg-time">Now</span>
        `;
        container.appendChild(div);
    } catch (e) {
        console.error(e);
    }
}

function toggleCategory(id) {
    const el = document.getElementById(id);
    el.classList.toggle('expanded');
}

function addMockCategory(container, name, count) {
    const header = document.createElement('div');
    header.className = 'category-header';
    header.innerHTML = `<span><span class="category-arrow">></span> ${name}</span> <span>(${count})</span>`;
    header.style.opacity = "0.7"; // Dim empty categories
    header.onclick = () => {
        header.querySelector('.category-arrow').classList.toggle('expanded');
    };
    container.appendChild(header);
}

function openChat(group) {
    currentGroup = group;
    document.getElementById('channel-screen').classList.add('hidden');
    document.getElementById('chat-screen').classList.remove('hidden');
    document.getElementById('current-chat-title').textContent = group.name;
    
    // Check if renamed recently (mock logic for banner)
    if (group.last_renamed_at) {
        document.getElementById('vote-banner').classList.remove('hidden');
    } else {
        document.getElementById('vote-banner').classList.add('hidden');
    }
    
    loadMessages(group.id);
}

function closeChat() {
    currentGroup = null;
    document.getElementById('chat-screen').classList.add('hidden');
    document.getElementById('channel-screen').classList.remove('hidden');
    document.getElementById('forge-panel').classList.add('hidden');
    loadDashboard(); // Refresh list
}

// Settings Logic
function openSettings() {
    document.getElementById('settings-modal').classList.remove('hidden');
    renderAliasEditor();
    // Pre-fill API Key
    if (currentUser.custom_api_key) {
        document.getElementById('custom-api-key').value = currentUser.custom_api_key;
    } else {
        document.getElementById('custom-api-key').value = '';
    }
    
    // Pre-fill TTS settings from localStorage
    const elevenlabsKey = localStorage.getItem('elevenlabs-api-key') || '';
    document.getElementById('elevenlabs-api-key').value = elevenlabsKey;
    
    const ttsVoice = localStorage.getItem('tts-voice') || '21m00Tcm4TlvDq8ikWAM';
    document.getElementById('tts-voice').value = ttsVoice;
    
    const stability = localStorage.getItem('tts-stability') || '0.5';
    document.getElementById('tts-stability').value = stability;
    document.getElementById('stability-value').textContent = stability;
    
    const clarity = localStorage.getItem('tts-clarity') || '0.75';
    document.getElementById('tts-clarity').value = clarity;
    document.getElementById('clarity-value').textContent = clarity;
    
    const rate = localStorage.getItem('tts-rate') || '1.0';
    document.getElementById('tts-rate').value = rate;
    document.getElementById('rate-value').textContent = rate + 'x';
    
    const pitch = localStorage.getItem('tts-pitch') || '0';
    document.getElementById('tts-pitch').value = pitch;
    document.getElementById('pitch-value').textContent = pitch + ' semitones';
}

function closeSettings() {
    document.getElementById('settings-modal').classList.add('hidden');
}

// Invite Link Logic
async function showInviteLink() {
    const token = localStorage.getItem('token');
    if (!token) {
        alert('Not logged in');
        return;
    }
    
    try {
        const response = await fetch('/api/invites/my-link', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.status === 401) {
            localStorage.removeItem('auth-token');
            window.location.reload();
            return;
        }
        
        if (!response.ok) {
            alert('Error getting invite link');
            return;
        }
        
        const data = await response.json();
        showInviteModal(data);
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function showInviteModal(inviteData) {
    // Create modal overlay
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;
    
    const content = document.createElement('div');
    content.style.cssText = `
        background: #000;
        border: 2px solid #00ff00;
        padding: 20px;
        max-width: 400px;
        width: 90%;
        border-radius: 5px;
        color: #00ff00;
        font-family: 'Courier New', Courier, monospace;
    `;
    
    content.innerHTML = `
        <h3 style="text-align: center; margin-top: 0;">📧 INVITE FRIENDS</h3>
        <p style="text-align: center; font-size: 12px;">Share this link to invite users to SDOH Chat</p>
        
        <div style="
            background: #001100;
            border: 1px solid #00ff00;
            padding: 10px;
            margin: 15px 0;
            border-radius: 3px;
            word-break: break-all;
            font-size: 12px;
        ">
            ${inviteData.invite_url}
        </div>
        
        <div style="display: flex; gap: 10px; flex-direction: column;">
            <button onclick="
                navigator.clipboard.writeText('${inviteData.invite_url}');
                alert('✓ Link copied to clipboard!');
            " style="
                background: #00ff00;
                color: #000;
                border: none;
                padding: 8px;
                cursor: pointer;
                font-weight: bold;
                border-radius: 3px;
            ">📋 COPY LINK</button>
            
            <a href="${inviteData.share_links.whatsapp}" target="_blank" style="
                background: #25D366;
                color: #fff;
                border: none;
                padding: 8px;
                cursor: pointer;
                font-weight: bold;
                border-radius: 3px;
                text-align: center;
                text-decoration: none;
                display: block;
            ">💬 WHATSAPP</a>
            
            <a href="${inviteData.share_links.email}" target="_blank" style="
                background: #EA4335;
                color: #fff;
                border: none;
                padding: 8px;
                cursor: pointer;
                font-weight: bold;
                border-radius: 3px;
                text-align: center;
                text-decoration: none;
                display: block;
            ">📧 EMAIL</a>
            
            <a href="${inviteData.share_links.sms}" style="
                background: #1f2937;
                color: #fff;
                border: 1px solid #4b5563;
                padding: 8px;
                cursor: pointer;
                font-weight: bold;
                border-radius: 3px;
                text-align: center;
                text-decoration: none;
                display: block;
            ">📱 SMS</a>
        </div>
        
        <p style="
            font-size: 11px;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #333;
            text-align: center;
            color: #00aa00;
        ">
            Uses remaining: <strong>${inviteData.uses_remaining}</strong>
        </p>
        
        <button onclick="this.closest('div').parentElement.remove()" style="
            width: 100%;
            background: #333;
            color: var(--red);
            border: 1px solid var(--red);
            padding: 10px;
            cursor: pointer;
            font-weight: bold;
        ">CLOSE</button>
    `;
    
    modal.appendChild(content);
    document.body.appendChild(modal);
    
    // Close on background click
    modal.onclick = (e) => {
        if (e.target === modal) modal.remove();
    };
}

// Show Insights Modal
function showInsights() {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.9);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;
    
    const content = document.createElement('div');
    content.style.cssText = `
        background: #000;
        border: 2px solid var(--red);
        padding: 20px;
        max-width: 500px;
        width: 90%;
        max-height: 80vh;
        overflow-y: auto;
        color: var(--red);
        font-family: 'Courier New', Courier, monospace;
    `;
    
    let insightsHtml = '';
    
    if (!currentUser.insights || currentUser.insights.length === 0) {
        insightsHtml = '<p style="text-align:center; color:#666">No insights extracted yet. Keep chatting with the Forge.</p>';
    } else {
        // Separate insights
        const strengths = currentUser.insights.filter(i => !i.type || i.type === 'strength');
        const flaws = currentUser.insights.filter(i => i.type === 'flaw');
        
        // Render Strengths
        if (strengths.length > 0) {
            insightsHtml += `<div style="margin-bottom:20px"><h4 style="color:#00ff00; border-bottom:1px solid #00ff00">STRENGTHS & VALUES</h4>`;
            insightsHtml += strengths.map(insight => `
                <div style="
                    border-left: 3px solid #00ff00;
                    padding: 10px;
                    margin-bottom: 10px;
                    background: #001100;
                ">
                    <div style="color:#fff">${typeof insight === 'string' ? insight : insight.text}</div>
                    ${typeof insight === 'object' && insight.date ? `<div style="font-size:10px; color:#666; margin-top:5px">${new Date(insight.date).toLocaleDateString()}</div>` : ''}
                </div>
            `).join('');
            insightsHtml += `</div>`;
        }
        
        // Render Flaws
        if (flaws.length > 0) {
            insightsHtml += `<div><h4 style="color:var(--red); border-bottom:1px solid var(--red)">EDGES & FLAWS</h4>`;
            insightsHtml += flaws.map(insight => `
                <div style="
                    border-left: 3px solid var(--red);
                    padding: 10px;
                    margin-bottom: 10px;
                    background: #110000;
                ">
                    <div style="color:#fff">${insight.text}</div>
                    ${insight.date ? `<div style="font-size:10px; color:#666; margin-top:5px">${new Date(insight.date).toLocaleDateString()}</div>` : ''}
                </div>
            `).join('');
            insightsHtml += `</div>`;
        }
    }
    
    content.innerHTML = `
        <h3 style="text-align: center; margin-top: 0; border-bottom: 1px solid var(--red); padding-bottom: 10px;">
            👁️ FORGE INSIGHTS
        </h3>
        <div style="margin: 20px 0;">
            ${insightsHtml}
        </div>
        <button onclick="this.closest('div').parentElement.remove()" style="
            width: 100%;
            background: #333;
            color: var(--red);
            border: 1px solid var(--red);
            padding: 10px;
            cursor: pointer;
            font-weight: bold;
        ">CLOSE</button>
    `;
    
    modal.appendChild(content);
    document.body.appendChild(modal);
    
    modal.onclick = (e) => {
        if (e.target === modal) modal.remove();
    };
}

function closeSettings() {
    document.getElementById('settings-modal').classList.add('hidden');
}

function renderAliasEditor() {
    const container = document.getElementById('alias-editor');
    container.innerHTML = '';
    const alias = currentUser.alias || 'USER';
    
    for (let i = 0; i < alias.length; i++) {
        const span = document.createElement('span');
        span.textContent = alias[i];
        span.className = 'letter-select';
        span.style.color = aliasColors[i] || '#00ff00';
        span.onclick = () => selectLetter(i);
        if (i === selectedLetterIdx) span.classList.add('selected');
        container.appendChild(span);
    }
}

function selectLetter(idx) {
    selectedLetterIdx = idx;
    renderAliasEditor();
}

function applyColor(color) {
    if (selectedLetterIdx === -1) return;
    aliasColors[selectedLetterIdx] = color;
    renderAliasEditor();
}

async function saveSettings() {
    const customKey = document.getElementById('custom-api-key').value.trim();
    
    // Save TTS settings to localStorage
    const elevenLabsKey = document.getElementById('elevenlabs-api-key').value.trim();
    const ttsVoice = document.getElementById('tts-voice').value;
    const ttsStability = document.getElementById('tts-stability').value;
    const ttsClarity = document.getElementById('tts-clarity').value;
    const ttsRate = document.getElementById('tts-rate').value;
    const ttsPitch = document.getElementById('tts-pitch').value;

    localStorage.setItem('elevenlabs-api-key', elevenLabsKey);
    localStorage.setItem('tts-voice', ttsVoice);
    localStorage.setItem('tts-stability', ttsStability);
    localStorage.setItem('tts-clarity', ttsClarity);
    localStorage.setItem('tts-rate', ttsRate);
    localStorage.setItem('tts-pitch', ttsPitch);

    try {
        await fetch(`${API_BASE}/user/settings`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ 
                alias_colors: aliasColors,
                custom_api_key: customKey
            })
        });
        currentUser.alias_colors = aliasColors;
        currentUser.custom_api_key = customKey;
        closeSettings();
        alert('Settings saved! TTS settings stored locally.');
    } catch (e) {
        alert('Error saving settings');
    }
}

// Rename Logic
async function promptRename() {
    const newName = prompt("Enter new group name:");
    if (!newName) return;
    
    try {
        const res = await fetch(`${API_BASE}/groups/${currentGroup.id}/rename`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ name: newName })
        });
        
        const data = await res.json();
        if (!res.ok) {
            alert(data.error);
        } else {
            document.getElementById('current-chat-title').textContent = data.name;
            alert('Group renamed!');
        }
    } catch (e) {
        alert('Error renaming group');
    }
}

async function voteRevert() {
    try {
        const res = await fetch(`${API_BASE}/groups/${currentGroup.id}/vote-revert`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        if (data.status === 'reverted') {
            alert('Vote passed! Name reverted to: ' + data.name);
            document.getElementById('current-chat-title').textContent = data.name;
            document.getElementById('vote-banner').classList.add('hidden');
        } else if (data.error) {
            alert(data.error);
        } else {
            alert(`Vote cast! Total votes: ${data.votes}/3`);
        }
    } catch (e) {
        alert('Error voting');
    }
}

function logout() {
    localStorage.clear();
    window.location.href = '/sdoh/index.html';
}

// Real Message Loading
async function loadMessages(groupId) {
    const container = document.getElementById('messages');
    container.innerHTML = '<div style="text-align:center; color:#666">Loading...</div>';
    
    try {
        const res = await fetch(`${API_BASE}/messages/${groupId}?limit=50`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (!res.ok) throw new Error('Failed to load messages');
        
        const messages = await res.json();
        container.innerHTML = '';
        
        if (messages.length === 0) {
            if (groupId.startsWith('forge_')) {
                loadForgeGreeting();
            } else {
                container.innerHTML = '<div style="text-align:center; color:#666">No messages yet...</div>';
            }
            return;
        }
        
        messages.forEach(msg => {
            const div = document.createElement('div');
            div.className = 'msg';
            const isMe = msg.sender_alias === currentUser.alias;
            const senderColor = isMe ? '#00ff00' : '#ff00ff'; // Simple color logic
            
            // Add Listen button for agents
            const alias = msg.sender_alias;
            const isAgent = (alias === 'The Forge' || alias === 'Quest Master' || alias === 'THE FORGE' || alias === 'QUEST MASTER');
            const escapedContent = msg.content.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/'/g, '&#39;').replace(/\n/g, ' ');
            const listenBtn = isAgent ? `<button class="tts-btn" style="float:right; margin-left:5px" data-text="${escapedContent}" onclick="startTTS(this)">🔊 LISTEN</button>` : '';

            div.innerHTML = `
                <span class="msg-sender" style="color:${senderColor}">${msg.sender_alias}:</span>
                ${listenBtn}
                ${msg.content}
                <span class="msg-time">${new Date(msg.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
            `;

            container.appendChild(div);
        });
        
        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
        
    } catch (e) {
        console.error(e);
        container.innerHTML = '<div style="text-align:center; color:red">Error loading messages</div>';
    }
}

function handleEnter(e) {
    if (e.key === 'Enter') sendMessage();
}

function sendMessage() {
    const input = document.getElementById('msg-input');
    const text = input.value.trim();
    if (!text) return;
    
    // Optimistic UI update
    const container = document.getElementById('messages');
    if (container.children[0]?.innerText === 'No messages yet...') container.innerHTML = '';
    
    const div = document.createElement('div');
    div.className = 'msg';
    div.innerHTML = `
        <span class="msg-sender" style="color:#00ff00">${currentUser.alias}:</span>
        ${text}
        <span class="msg-time">Now</span>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    input.value = '';
    
    // Route to correct agent
    if (currentGroup.id === 'forge') {
        sendToForge(text);
    } else if (currentGroup.id === 'quest') {
        sendToQuest(text);
    } else {
        // Normal group chat (future)
    }
}

async function sendToForge(text) {
    try {
        const location = await getLocation();
        const payload = { content: text };
        if (location) {
            payload.location = location;
        }

        const res = await fetch(`${API_BASE}/forge/chat`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        
        // Update Panel
        if (data.score !== undefined) {
            currentUser.integrity_score = data.score;
            currentUser.insights = data.insights;
            updateForgePanel(data.score, data.insights);
        }
        
        // Append Agent Response with TTS button
        const container = document.getElementById('messages');
        const div = document.createElement('div');
        div.className = 'msg';
        div.style.borderLeftColor = 'var(--red)';
        const escapedForgeResponse = data.response.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/'/g, '&#39;').replace(/\n/g, ' ');
        div.innerHTML = `
            <span class="msg-sender" style="color:var(--red)">THE FORGE:</span>
            <button class="tts-btn" style="float:right; margin-left:5px" data-text="${escapedForgeResponse}" onclick="startTTS(this)">🔊 LISTEN</button>
            ${data.response}
            <span class="msg-time">Now</span>
        `;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        
    } catch (e) {
        console.error(e);
    }
}

async function sendToQuest(text) {
    try {
        const res = await fetch(`${API_BASE}/quest/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ content: text })
        });
        
        const data = await res.json();
        
        // Display response
        const container = document.getElementById('messages');
        const div = document.createElement('div');
        div.className = 'msg';
        div.style.borderLeftColor = '#ffaa00';
        const escapedQuestResponse = data.response.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/'/g, '&#39;').replace(/\n/g, ' ');
        div.innerHTML = `
            <span class="msg-sender" style="color:#ffaa00">THE QUEST:</span>
            <button class="tts-btn" style="float:right; margin-left:5px" data-text="${escapedQuestResponse}" onclick="startTTS(this)">🔊 LISTEN</button>
            ${data.response}
            ${data.quest_posted ? '<br><br><strong style="color:#ffaa00">[Quest Posted to Board!]</strong>' : ''}
            <span class="msg-time">Now</span>
        `;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        
    } catch (e) {
        console.error(e);
    }
}

// ============================================================================
// VOICE & TTS FUNCTIONS
// ============================================================================

// Play TTS for a message
async function playTTS(text) {
    const apiKey = localStorage.getItem('elevenlabs-api-key');
    const voiceId = localStorage.getItem('tts-voice') || '21m00Tcm4TlvDq8ikWAM'; // Default Rachel
    const stability = localStorage.getItem('tts-stability') || '0.5';
    const clarity = localStorage.getItem('tts-clarity') || '0.75';
    const rate = localStorage.getItem('tts-rate') || '1.0';
    const pitch = localStorage.getItem('tts-pitch') || '0';

    // If no API key, use browser TTS
    if (!apiKey) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = parseFloat(rate);
        utterance.pitch = 1.0 + (parseFloat(pitch) / 20); // Approximate pitch mapping
        window.speechSynthesis.speak(utterance);
        return;
    }

    try {
        const response = await fetch('/api/tts/speak', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                text: text,
                voice_id: voiceId,
                api_key: apiKey,
                stability: parseFloat(stability),
                clarity: parseFloat(clarity)
            })
        });

        if (!response.ok) throw new Error('TTS Failed');

        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        audio.play();

    } catch (e) {
        console.error('TTS Error:', e);
        // Fallback to browser TTS
        const utterance = new SpeechSynthesisUtterance(text);
        window.speechSynthesis.speak(utterance);
    }
}

// TTS Settings Management
function updateValue(type) {
    if (type === 'stability') {
        const val = document.getElementById('tts-stability').value;
        document.getElementById('stability-value').textContent = val;
    } else if (type === 'clarity') {
        const val = document.getElementById('tts-clarity').value;
        document.getElementById('clarity-value').textContent = val;
    } else if (type === 'rate') {
        const val = document.getElementById('tts-rate').value;
        document.getElementById('rate-value').textContent = val + 'x';
    } else if (type === 'pitch') {
        const val = document.getElementById('tts-pitch').value;
        document.getElementById('pitch-value').textContent = val + ' semitones';
    }
}

// Preview Voice with Local Server Previews
async function previewVoice() {
    const voiceSelectElement = document.getElementById('tts-voice');
    const voiceId = voiceSelectElement.value;
    const voiceName = voiceSelectElement.options[voiceSelectElement.selectedIndex].text.split(' ')[0].toLowerCase();
    const previewBtn = document.getElementById('preview-btn');
    const apiKey = localStorage.getItem('elevenlabs-api-key');
    
    try {
        previewBtn.textContent = '[LOADING...]';
        previewBtn.disabled = true;

        let audioBlob = null;

        // First, try to fetch from local server (admin-generated previews)
        try {
            const response = await fetch(`/api/tts/preview/${voiceName}.mp3`);
            if (response.ok) {
                const audioBuffer = await response.arrayBuffer();
                audioBlob = new Blob([audioBuffer], { type: 'audio/mpeg' });
            }
        } catch (e) {
            console.log('Server preview not available, will try backend TTS');
        }

        // If server preview not available, use backend TTS endpoint
        if (!audioBlob) {
            if (!apiKey) {
                throw new Error('ElevenLabs API key not set. Enter it in Settings and click SAVE CHANGES.');
            }

            const stability = localStorage.getItem('tts-stability') || '0.5';
            const clarity = localStorage.getItem('tts-clarity') || '0.75';

            const response = await fetch('/api/tts/speak', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    text: 'Hello, how can I help you today?',
                    voice_id: voiceId,
                    api_key: apiKey,
                    stability: parseFloat(stability),
                    clarity: parseFloat(clarity)
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || 'TTS failed: ' + response.status);
            }

            audioBlob = await response.blob();
        }

        if (audioBlob) {
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            previewBtn.textContent = '[PLAYING...]';

            audio.onended = () => {
                previewBtn.textContent = '[PREVIEW]';
                previewBtn.disabled = false;
            };

            audio.onerror = () => {
                previewBtn.textContent = '[PREVIEW]';
                previewBtn.disabled = false;
                alert('Error playing audio');
            };

            audio.play();
        } else {
            throw new Error('Could not load audio preview');
        }
    } catch (e) {
        console.error('Preview error:', e);
        
        // Fallback to browser TTS if ElevenLabs fails
        if (e.message.includes('ElevenLabs') || e.message.includes('401') || e.message.includes('403')) {
            if (confirm(`ElevenLabs Error: ${e.message}\n\nWould you like to hear a basic preview using your browser's built-in voice instead?`)) {
                const utterance = new SpeechSynthesisUtterance('Hello, how can I help you today?');
                window.speechSynthesis.speak(utterance);
            }
        } else {
            alert('Preview failed: ' + e.message);
        }
        
        previewBtn.textContent = '[PREVIEW]';
        previewBtn.disabled = false;
    }
}

// Voice Input Toggle
function toggleVoiceInput() {
    document.getElementById('voice-file-input').click();
}

// Voice Recording Variables
let mediaRecorder = null;
let recordedChunks = [];
let recordingStartTime = null;
let recordingInterval = null;

// Toggle Voice Recording
async function toggleRecording() {
    const recordBtn = document.getElementById('record-btn');
    
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        // Stop recording
        mediaRecorder.stop();
        recordBtn.textContent = '🎙️ REC';
        recordBtn.classList.remove('recording');
        clearInterval(recordingInterval);
        document.getElementById('recording-timer').style.display = 'none';
    } else {
        // Start recording
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            recordedChunks = [];
            recordingStartTime = Date.now();
            
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    recordedChunks.push(event.data);
                }
            };
            
            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(recordedChunks, { type: 'audio/wav' });
                // Send recorded audio to transcription
                const formData = new FormData();
                formData.append('file', audioBlob, 'recording.wav');
                
                recordBtn.textContent = '🎙️ TRANSCRI…';
                recordBtn.disabled = true;
                
                try {
                    const response = await fetch('/api/dictation/transcribe', {
                        method: 'POST',
                        body: formData,
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    
                    const result = await response.json();
                    if (result.text) {
                        document.getElementById('msg-input').value = result.text;
                        document.getElementById('msg-input').focus();
                    } else {
                        alert('Transcription failed: ' + (result.error || 'Unknown error'));
                    }
                } catch (e) {
                    alert('Error transcribing: ' + e.message);
                } finally {
                    recordBtn.textContent = '🎙️ REC';
                    recordBtn.disabled = false;
                    // Stop all audio tracks
                    stream.getTracks().forEach(track => track.stop());
                }
            };
            
            mediaRecorder.start();
            recordBtn.textContent = '⏹️ STOP';
            recordBtn.classList.add('recording');
            
            // Show timer
            document.getElementById('recording-timer').style.display = 'block';
            recordingInterval = setInterval(() => {
                const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
                const mins = Math.floor(elapsed / 60);
                const secs = elapsed % 60;
                document.getElementById('timer').textContent = 
                    `${mins}:${secs.toString().padStart(2, '0')}`;
            }, 100);
            
        } catch (e) {
            alert('Microphone access denied: ' + e.message + '\n\nNote: Your browser must use HTTPS to access the microphone.');
        }
    }
}

// Handle Voice File Upload
async function handleVoiceFile(event) {
    const file = event.target.files[0];
    if (!file) return;

    try {
        // Show loading state
        const voiceBtn = document.getElementById('voice-btn');
        voiceBtn.textContent = '🎤 TRANSCRIBING...';
        voiceBtn.disabled = true;

        // Transcribe using Whisper Mini from Dictation module
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/dictation/transcribe', {
            method: 'POST',
            body: formData,
            headers: { 'Authorization': `Bearer ${token}` }
        });

        const result = await response.json();

        if (result.text) {
            // Put transcribed text in input
            document.getElementById('msg-input').value = result.text;
            document.getElementById('msg-input').focus();
        } else {
            alert('Transcription failed: ' + (result.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Error transcribing voice: ' + e.message);
    } finally {
        voiceBtn.textContent = '🎤 VOICE';
        voiceBtn.disabled = false;
        event.target.value = ''; // Reset input
    }
}


// ============================================================================
// FAST TTS FUNCTION - Web Speech API only (no API calls, no text injection)
// ============================================================================

window.startTTS = function(button) {
    // Read text from data attribute instead of function parameter
    const text = button.getAttribute('data-text');
    if (!text) {
        console.error('No text found for TTS');
        return;
    }
    
    // If already playing, stop it
    if (button.classList.contains('playing')) {
        window.speechSynthesis.cancel();
        button.classList.remove('playing');
        button.textContent = '🔊 LISTEN';
        button.disabled = false;
        return;
    }
    
    // Start playing
    button.classList.add('playing');
    button.textContent = '[PLAYING...]';
    button.disabled = true;
    
    window.speechSynthesis.cancel(); // Clear any queued speech
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.5; // Fast speed
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    
    utterance.onend = () => {
        button.classList.remove('playing');
        button.textContent = '🔊 LISTEN';
        button.disabled = false;
    };
    
    utterance.onerror = (e) => {
        console.error('TTS error:', e);
        button.classList.remove('playing');
        button.textContent = '🔊 LISTEN';
        button.disabled = false;
    };
    
    window.speechSynthesis.speak(utterance);
};

// Helper to get location (with IP fallback)
async function getLocation() {
    // 1. Try Browser Geolocation (Short timeout)
    const browserLoc = await new Promise((resolve) => {
        if (!navigator.geolocation) {
            resolve(null);
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (position) => {
                resolve({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    source: 'gps'
                });
            },
            (error) => {
                resolve(null);
            },
            { timeout: 1500 }
        );
    });

    if (browserLoc) return browserLoc;

    // 2. Fallback to IP Geolocation (using ipapi.co)
    // Only try this if we really need to, and maybe cache it?
    // For now, let's keep it but make it faster or skip if it fails quickly.
    try {
        // console.log("Falling back to IP location...");
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 1500); // 1.5s timeout for IP API
        
        const res = await fetch('https://ipapi.co/json/', { signal: controller.signal });
        clearTimeout(timeoutId);
        
        if (res.ok) {
            const data = await res.json();
            return {
                latitude: data.latitude,
                longitude: data.longitude,
                city: data.city,
                region: data.region,
                country: data.country_name,
                source: 'ip'
            };
        }
    } catch (e) {
        // console.error("IP Location failed:", e);
    }

    return null;
}



// ============================================================================
// CONTACTS LOGIC
// ============================================================================

async function loadContacts() {
    try {
        const res = await fetch(`/api/contacts`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const contacts = await res.json();
        renderContacts(contacts);
    } catch (e) {
        console.error(e);
    }
}

function renderContacts(contacts) {
    const container = document.getElementById('groups-list');
    // Check if contacts section already exists
    let catContent = document.getElementById('contacts-list');
    
    if (!catContent) {
        // Create Header
        const catHeader = document.createElement('div');
        catHeader.className = 'category-header';
        catHeader.innerHTML = `
            <span><span class="category-arrow">></span> Contacts</span> 
            <span>
                <button onclick="event.stopPropagation(); promptAddContact()" style="background:none; border:none; color:var(--highlight); cursor:pointer; font-weight:bold; font-size:14px" title="Add Contact">+</button>
                (${contacts.length})
            </span>`;
        catHeader.onclick = () => {
            toggleCategory('contacts-list');
            catHeader.querySelector('.category-arrow').classList.toggle('expanded');
        };
        
        catContent = document.createElement('div');
        catContent.id = 'contacts-list';
        catContent.className = 'category-content';
        
        container.appendChild(catHeader);
        container.appendChild(catContent);
    } else {
        // Update count in header (simplified)
        const header = catContent.previousElementSibling;
        header.innerHTML = `
            <span><span class="category-arrow expanded">></span> Contacts</span> 
            <span>
                <button onclick="event.stopPropagation(); promptAddContact()" style="background:none; border:none; color:var(--highlight); cursor:pointer; font-weight:bold; font-size:14px" title="Add Contact">+</button>
                (${contacts.length})
            </span>`;
        header.onclick = () => {
            toggleCategory('contacts-list');
            header.querySelector('.category-arrow').classList.toggle('expanded');
        };
    }
    
    catContent.innerHTML = '';
    contacts.forEach(c => {
        const div = document.createElement('div');
        div.className = 'group-item';
        div.innerHTML = `
            <div style="display:flex; align-items:center">
                <span class="online-dot" style="background:${c.is_online ? '#00ff00' : '#666'}"></span>
                <span>${c.alias}</span>
            </div>
            <span style="font-size:10px; color:#666">DM</span>
        `;
        div.onclick = () => openContactChat(c.user_id);
        catContent.appendChild(div);
    });
}

async function promptAddContact() {
    const target = prompt("Enter Username or User ID to add:");
    if (!target) return;
    
    try {
        const res = await fetch(`/api/contacts/add`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ target })
        });
        
        const data = await res.json();
        if (res.ok) {
            alert('Contact added!');
            loadContacts();
        } else {
            alert(data.error);
        }
    } catch (e) {
        alert('Error adding contact');
    }
}

async function openContactChat(contactId) {
    try {
        const res = await fetch(`/api/contacts/${contactId}/chat`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (res.ok) {
            const group = await res.json();
            // Normalize group object to match what openChat expects
            const groupObj = {
                id: group.group_id,
                name: group.name,
                is_private: true,
                max_members: 2,
                member_count: 2
            };
            openChat(groupObj);
        } else {
            const data = await res.json();
            alert(data.error);
        }
    } catch (e) {
        console.error(e);
    }
}

// Init
loadDashboard();
