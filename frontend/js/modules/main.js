// Main Entry Point

// Load Dashboard
async function loadDashboard() {
    try {
        const res = await fetchWithAuth('/dashboard');
        if (!res) return;
        
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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    
    // Setup Input Listener
    const input = document.getElementById('msg-input');
    if (input) {
        input.addEventListener('keypress', handleEnter);
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
