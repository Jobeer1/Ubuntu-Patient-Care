// Main Entry Point

// Load Dashboard
async function loadDashboard() {
    try {
        const res = await fetchWithAuth('/dashboard');
        if (!res) return;
        
        const data = await res.json();
        window.currentUser = data.user;
        window.aliasColors = data.user.alias_colors || {};
        window.allGroups = data.groups; // Store globally for access
        
        // Load counts if available
        if (!window.unreadCounts) window.unreadCounts = {};
        
        renderGroups(data.groups);
        loadContacts(); // Load contacts after groups
        startNotificationPolling(); // Start notifications system
    } catch (e) {
        console.error(e);
    }
}

let notificationInterval = null;
function startNotificationPolling() {
    if (notificationInterval) clearInterval(notificationInterval);
    notificationInterval = setInterval(checkNotifications, 5000); // Check every 5 seconds
}

async function checkNotifications() {
    try {
        const res = await window.fetchWithAuth('/notifications');
        if (!res || !res.ok) return;
        const data = await res.json();
        
        let hasChanges = false;
        for (const [chatId, info] of Object.entries(data)) {
            const lastSeen = localStorage.getItem(`last_seen_${chatId}`);
            if (lastSeen) {
                if (new Date(info.last_msg_at) > new Date(lastSeen)) {
                    // New message!
                    if (!window.unreadCounts[chatId]) {
                        window.unreadCounts[chatId] = 1;
                        hasChanges = true;
                    }
                }
            } else {
                // First time seeing this chat?
                // Don't ping if everything is new, just seed it
                localStorage.setItem(`last_seen_${chatId}`, info.last_msg_at);
            }
        }
        
        if (hasChanges) {
            renderGroups(window.allGroups);
            if (typeof window.loadContacts === 'function') window.loadContacts();
        }
    } catch (e) {
        console.error("Notification check failed:", e);
    }
}

function renderGroups(groups) {
    const container = document.getElementById('groups-list');
    container.innerHTML = '';
    
    // 1. Private Chats (Personal Forge)
    const privHeader = document.createElement('div');
    privHeader.className = 'category-header';
    privHeader.innerHTML = `<span><span class="category-arrow expanded">></span> Private Chats</span> <span>(5)</span>`;
    privHeader.onclick = () => {
        window.toggleCategory('private-chats');
        privHeader.querySelector('.category-arrow').classList.toggle('expanded');
    };
    
    const privContent = document.createElement('div');
    privContent.id = 'private-chats';
    privContent.className = 'category-content expanded';
    
    // Add Personal Forge
    const forgeDiv = document.createElement('div');
    const forgeChatId = `forge_${window.currentUser.user_id}`;
    const forgeUnread = window.unreadCounts && window.unreadCounts[forgeChatId];
    forgeDiv.className = 'group-item';
    forgeDiv.innerHTML = `
        <div style="display:flex; align-items:center">
            <span class="online-dot" style="background:var(--red); box-shadow:0 0 5px var(--red)"></span>
            <span style="color:var(--red); font-weight:bold">THE FORGE ${forgeUnread ? '🔴' : ''}</span>
        </div>
        <span style="font-size:12px; color:#666">${forgeUnread ? 'NEW PING' : '[AUDITOR]'}</span>
    `;
    forgeDiv.onclick = () => window.openForgeChat();
    privContent.appendChild(forgeDiv);
    
    // Add The Quest
    const questDiv = document.createElement('div');
    const questChatId = `quest_${window.currentUser.user_id}`;
    const questUnread = window.unreadCounts && window.unreadCounts[questChatId];
    questDiv.className = 'group-item';
    questDiv.innerHTML = `
        <div style="display:flex; align-items:center">
            <span class="online-dot" style="background:#ffaa00; box-shadow:0 0 5px #ffaa00"></span>
            <span style="color:#ffaa00; font-weight:bold">THE QUEST ${questUnread ? '🔴' : ''}</span>
        </div>
        <span style="font-size:12px; color:#666">${questUnread ? 'NEW PING' : '[MASTER]'}</span>
    `;
    questDiv.onclick = () => window.openQuestChat();
    privContent.appendChild(questDiv);

    const sdohDiv = document.createElement('div');
    const sdohChatId = `sdoh_${window.currentUser.user_id}`;
    const sdohUnread = window.unreadCounts && window.unreadCounts[sdohChatId];
    sdohDiv.className = 'group-item';
    sdohDiv.innerHTML = `
        <div style="display:flex; align-items:center">
            <span class="online-dot" style="background:var(--cyan); box-shadow:0 0 5px var(--cyan)"></span>
            <span style="color:var(--cyan); font-weight:bold">SDOH NAVIGATOR ${sdohUnread ? '🔴' : ''}</span>
        </div>
        <span style="font-size:12px; color:#666">${sdohUnread ? 'NEW PING' : '[CONTINUITY]'}</span>
    `;
    sdohDiv.onclick = () => window.openSdohChat();
    privContent.appendChild(sdohDiv);

    const pacsDiv = document.createElement('div');
    const pacsChatId = `pacs_${window.currentUser.user_id}`;
    const pacsUnread = window.unreadCounts && window.unreadCounts[pacsChatId];
    pacsDiv.className = 'group-item';
    pacsDiv.innerHTML = `
        <div style="display:flex; align-items:center">
            <span class="online-dot" style="background:#00ff44; box-shadow:0 0 5px #00ff44"></span>
            <span style="color:#00ff44; font-weight:bold">PACS CONTINUITY ${pacsUnread ? '🔴' : ''}</span>
        </div>
        <span style="font-size:12px; color:#666">${pacsUnread ? 'NEW PING' : '[GENERAL SUPPORT]'}</span>
    `;
    pacsDiv.onclick = () => window.openPacsChat();
    privContent.appendChild(pacsDiv);

    // Add Hall of Heroes
    const heroesDiv = document.createElement('div');
    heroesDiv.className = 'group-item';
    heroesDiv.innerHTML = `
        <div style="display:flex; align-items:center">
            <span class="online-dot" style="background:#00ffff; box-shadow:0 0 5px #00ffff"></span>
            <span style="color:#00ffff; font-weight:bold">HALL OF HEROES</span>
        </div>
        <span style="font-size:12px; color:#666">[CHRONICLES]</span>
    `;
    heroesDiv.onclick = () => window.openHallOfHeroes();
    privContent.appendChild(heroesDiv);
    
    container.appendChild(privHeader);
    container.appendChild(privContent);

    // 2. Public Chatrooms Category
    const catHeader = document.createElement('div');
    catHeader.className = 'category-header';
    catHeader.innerHTML = `<span><span class="category-arrow expanded">></span> Chat Rooms</span> <span>(${groups.length})</span>`;
    catHeader.onclick = () => {
        window.toggleCategory('public-chats');
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
        const unread = window.unreadCounts && window.unreadCounts[g.id];
        
        div.innerHTML = `
            <div style="display:flex; align-items:center">
                <span class="online-dot" style="background:${unread ? 'var(--red)' : '#00ff00'}; box-shadow:${unread ? '0 0 5px var(--red)' : 'none'}"></span>
                <span style="${unread ? 'font-weight:bold' : ''}">${g.name} ${unread ? '🔴' : ''}</span>
            </div>
            <span style="font-size:12px; color:${statusColor}">(${memberStatus})</span>
        `;
        div.onclick = () => window.openChat(g);
        catContent.appendChild(div);
    });
    
    container.appendChild(catHeader);
    container.appendChild(catContent);
    
    // 3. Mock Categories
    window.addMockCategory(container, 'Apps & Games', 0);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    
    // Setup Input Listener
    const input = document.getElementById('msg-input');
    if (input) {
        input.addEventListener('keypress', (e) => window.handleEnter(e));
    }
    
    // Setup TTS Settings Listeners
    const stabilityInput = document.getElementById('tts-stability');
    if (stabilityInput) {
        stabilityInput.oninput = (e) => document.getElementById('stability-value').textContent = e.target.value;
    }
    
    const clarityInput = document.getElementById('tts-clarity');
    if (clarityInput) {
        clarityInput.oninput = (e) => document.getElementById('clarity-value').textContent = e.target.value;
    }
    
    const rateInput = document.getElementById('tts-rate');
    if (rateInput) {
        rateInput.oninput = (e) => document.getElementById('rate-value').textContent = e.target.value + 'x';
    }
    
    const pitchInput = document.getElementById('tts-pitch');
    if (pitchInput) {
        pitchInput.oninput = (e) => document.getElementById('pitch-value').textContent = e.target.value + ' semitones';
    }
});
