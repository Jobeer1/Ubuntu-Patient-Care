// UI Logic

function toggleCategory(id) {
    const el = document.getElementById(id);
    el.classList.toggle('expanded');
}

function openChat(group) {
    window.currentGroup = group;
    
    // Clear notifications
    if (window.unreadCounts) {
        delete window.unreadCounts[group.id];
        // In a real app we'd also mark as read on server. 
        // For now, update local storage to latest message time if we can.
        // We'll let the next poll handle the "seeding".
    }
    
    document.getElementById('channel-screen').classList.add('hidden');
    document.getElementById('chat-screen').classList.remove('hidden');
    document.getElementById('current-chat-title').textContent = group.name;
    document.getElementById('current-chat-title').style.color = 'white'; // Reset color
    const sdohPanel = document.getElementById('sdoh-panel');
    if (sdohPanel) sdohPanel.classList.add('hidden');
    
    // Check if renamed recently (mock logic for banner)
    if (group.last_renamed_at) {
        document.getElementById('vote-banner').classList.remove('hidden');
    } else {
        document.getElementById('vote-banner').classList.add('hidden');
    }
    
    loadMessages(group.id);
}

function closeChat() {
    window.currentGroup = null;
    document.getElementById('chat-screen').classList.add('hidden');
    document.getElementById('channel-screen').classList.remove('hidden');
    document.getElementById('forge-panel').classList.add('hidden');
    document.getElementById('quest-panel').classList.add('hidden');
    const sdohPanel = document.getElementById('sdoh-panel');
    if (sdohPanel) sdohPanel.classList.add('hidden');
    loadDashboard(); // Refresh list to update notification dots
}

function openForgeChat() {
    const forgeChatId = `forge_${window.currentUser.user_id}`;
    window.currentGroup = { id: 'forge', name: 'THE FORGE' };
    
    // Clear notifications
    if (window.unreadCounts) delete window.unreadCounts[forgeChatId];
    
    document.getElementById('channel-screen').classList.add('hidden');
    document.getElementById('chat-screen').classList.remove('hidden');
    document.getElementById('current-chat-title').textContent = 'THE FORGE [INTEGRITY AUDIT]';
    document.getElementById('current-chat-title').style.color = 'var(--red)';
    document.getElementById('vote-banner').classList.add('hidden');
    const sdohPanel = document.getElementById('sdoh-panel');
    if (sdohPanel) sdohPanel.classList.add('hidden');
    
    // Show Forge Panel
    document.getElementById('forge-panel').classList.remove('hidden');
    updateForgePanel(window.currentUser.integrity_score, window.currentUser.insights);
    
    loadMessages(forgeChatId);
}

function togglePanelContent(id) {
    const el = document.getElementById(id);
    if (el) {
        if (el.style.display === 'none') {
            el.style.display = 'block';
        } else {
            el.style.display = 'none';
        }
    }
}

function openQuestChat() {
    const questChatId = `quest_${window.currentUser.user_id}`;
    window.currentGroup = { id: 'quest', name: 'THE QUEST' };
    
    // Clear notifications
    if (window.unreadCounts) delete window.unreadCounts[questChatId];
    
    document.getElementById('channel-screen').classList.add('hidden');
    document.getElementById('chat-screen').classList.remove('hidden');
    document.getElementById('current-chat-title').textContent = 'THE QUEST [CHALLENGE MASTER]';
    document.getElementById('current-chat-title').style.color = '#ffaa00';
    document.getElementById('vote-banner').classList.add('hidden');
    const sdohPanel = document.getElementById('sdoh-panel');
    if (sdohPanel) sdohPanel.classList.add('hidden');
    
    // Show Quest Panel
    document.getElementById('quest-panel').classList.remove('hidden');
    // Update panel if data exists
    if (window.currentUser && typeof updateQuestPanel === 'function') {
        updateQuestPanel(window.currentUser.integrity_score, window.currentUser.insights, window.currentUser.inventory, window.currentUser.active_quest_id);
    }
    
    // Check for starting inventory
    if (!window.currentUser.inventory || window.currentUser.inventory.length === 0) {
        document.getElementById('class-selection-modal').classList.remove('hidden');
    }
    
    loadMessages(questChatId);
}

function openSdohChat() {
    const sdohChatId = `sdoh_${window.currentUser.user_id}`;
    window.currentGroup = { id: sdohChatId, name: 'SDOH NAVIGATOR' };

    if (window.unreadCounts) delete window.unreadCounts[sdohChatId];

    document.getElementById('channel-screen').classList.add('hidden');
    document.getElementById('chat-screen').classList.remove('hidden');
    document.getElementById('current-chat-title').textContent = 'SDOH NAVIGATOR [CONTINUITY PORTAL]';
    document.getElementById('current-chat-title').style.color = 'var(--cyan)';
    document.getElementById('vote-banner').classList.add('hidden');
    document.getElementById('forge-panel').classList.add('hidden');
    document.getElementById('quest-panel').classList.add('hidden');

    const sdohPanel = document.getElementById('sdoh-panel');
    if (sdohPanel) sdohPanel.classList.remove('hidden');

    if (typeof renderSdohPanel === 'function') {
        renderSdohPanel(loadSdohExportBundle());
    }

    loadMessages(sdohChatId);
}

function openPacsChat() {
    const pacsChatId = `pacs_${window.currentUser.user_id}`;
    window.currentGroup = { id: pacsChatId, name: 'PACS CONTINUITY' };

    if (window.unreadCounts) delete window.unreadCounts[pacsChatId];

    document.getElementById('channel-screen').classList.add('hidden');
    document.getElementById('chat-screen').classList.remove('hidden');
    document.getElementById('current-chat-title').textContent = 'PACS CONTINUITY [GENERAL SUPPORT]';
    document.getElementById('current-chat-title').style.color = '#00ff44';
    document.getElementById('vote-banner').classList.add('hidden');
    document.getElementById('forge-panel').classList.add('hidden');
    document.getElementById('quest-panel').classList.add('hidden');
    document.getElementById('sdoh-panel').classList.add('hidden');

    const pacsPanel = document.getElementById('pacs-panel');
    if (pacsPanel) pacsPanel.classList.remove('hidden');

    const pacsStatus = document.getElementById('pacs-status-text');
    if (pacsStatus) pacsStatus.textContent = 'GENERAL SUPPORT';

    const pacsStep = document.getElementById('pacs-recovery-step');
    if (pacsStep) pacsStep.textContent = 'General PACS mentorship is online. Use break-glass only for verified recovery actions.';

    loadMessages(pacsChatId);
}

async function selectClass(className) {
    try {
        const res = await fetchWithAuth('/quest/select_class', {
            method: 'POST',
            body: JSON.stringify({ class: className })
        });
        
        if (res && res.ok) {
            const data = await res.json();
            window.currentUser.inventory = data.inventory;
            if (typeof updateQuestPanel === 'function') {
                updateQuestPanel(window.currentUser.integrity_score, window.currentUser.insights, window.currentUser.inventory, window.currentUser.active_quest_id);
            }
            document.getElementById('class-selection-modal').classList.add('hidden');
            
            // Send a system message to chat to confirm
            const container = document.getElementById('messages');
            const div = document.createElement('div');
            div.className = 'msg';
            div.style.borderLeftColor = '#ffaa00';
            div.innerHTML = `
                <span class="msg-sender" style="color:#ffaa00">SYSTEM:</span>
                You have chosen the path of the ${className.toUpperCase()}. Your starting gear has been added to your inventory.
                <span class="msg-time">Now</span>
            `;
            container.appendChild(div);
            container.scrollTop = container.scrollHeight;
        }
    } catch (e) {
        console.error("Error selecting class:", e);
        alert("Failed to select class. Please try again.");
    }
}

function openQuestBoard() {
    if (!window.allGroups) return;
    const boardGroup = window.allGroups.find(g => g.name === 'Quest Board');
    if (boardGroup) {
        openChat(boardGroup);
    } else {
        alert("Quest Board not found!");
    }
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

// Settings Logic
function openSettings() {
    document.getElementById('settings-modal').classList.remove('hidden');
    renderAliasEditor();
    // Pre-fill API Key
    if (window.currentUser.custom_api_key) {
        document.getElementById('custom-api-key').value = window.currentUser.custom_api_key;
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

async function saveSettings() {
    const newAlias = document.getElementById('alias-preview').textContent;
    const newKey = document.getElementById('custom-api-key').value;
    
    // Save TTS Settings
    localStorage.setItem('elevenlabs-api-key', document.getElementById('elevenlabs-api-key').value);
    localStorage.setItem('tts-voice', document.getElementById('tts-voice').value);
    localStorage.setItem('tts-stability', document.getElementById('tts-stability').value);
    localStorage.setItem('tts-clarity', document.getElementById('tts-clarity').value);
    localStorage.setItem('tts-rate', document.getElementById('tts-rate').value);
    localStorage.setItem('tts-pitch', document.getElementById('tts-pitch').value);
    
    try {
        const res = await fetchWithAuth('/settings', {
            method: 'POST',
            body: JSON.stringify({
                alias: newAlias,
                custom_api_key: newKey,
                alias_colors: window.aliasColors
            })
        });
        
        if (res && res.ok) {
            alert('Settings saved!');
            closeSettings();
            loadDashboard(); // Reload to update alias
        } else {
            alert('Failed to save settings');
        }
    } catch (e) {
        console.error(e);
        alert('Error saving settings');
    }
}

// Alias Editor Logic
function renderAliasEditor() {
    const container = document.getElementById('alias-editor');
    if (!container) return;
    
    container.innerHTML = '';
    
    const alias = window.currentUser.alias || 'USER';
    const letters = alias.split('');
    
    // Ensure window.aliasColors is populated
    if (!window.aliasColors || Object.keys(window.aliasColors).length === 0) {
        window.aliasColors = window.currentUser.alias_colors || {};
    }
    
    // Create a wrapper for the letters
    const lettersDiv = document.createElement('div');
    lettersDiv.id = 'alias-preview-inner';
    lettersDiv.style.marginBottom = '10px';
    
    letters.forEach((char, idx) => {
        const span = document.createElement('span');
        span.textContent = char;
        span.style.color = window.aliasColors[idx] || '#00ff00';
        span.style.cursor = 'pointer';
        span.style.padding = '0 2px';
        span.style.border = window.selectedLetterIdx === idx ? '1px solid white' : 'none';
        span.style.fontSize = '24px';
        span.style.fontWeight = 'bold';
        
        span.onclick = () => {
            window.selectedLetterIdx = idx;
            renderAliasEditor(); // Re-render to show selection
        };
        
        lettersDiv.appendChild(span);
    });
    
    container.appendChild(lettersDiv);
    
    // Color Palette (Dynamic)
    const palette = ['#00ff00', '#ff0000', '#0000ff', '#ffff00', '#ff00ff', '#00ffff', '#ffffff', '#ff0080', '#ff6600', '#9900ff'];
    const paletteDiv = document.createElement('div');
    paletteDiv.className = 'color-picker';
    paletteDiv.style.marginTop = '10px';
    paletteDiv.style.display = 'flex';
    paletteDiv.style.justifyContent = 'center';
    paletteDiv.style.gap = '5px';
    
    palette.forEach(color => {
        const btn = document.createElement('div');
        btn.className = 'color-swatch';
        btn.style.backgroundColor = color;
        btn.style.width = '20px';
        btn.style.height = '20px';
        btn.style.cursor = 'pointer';
        btn.style.border = '1px solid #333';
        
        btn.onclick = () => {
            if (window.selectedLetterIdx !== -1) {
                window.aliasColors[window.selectedLetterIdx] = color;
                renderAliasEditor();
            }
        };
        
        paletteDiv.appendChild(btn);
    });
    
    container.appendChild(paletteDiv);
}

// Invite Link Logic
async function showInviteLink() {
    try {
        const response = await fetchWithAuth('/invites/my-link');
        if (!response) return;
        
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
        <h3 style="margin-top:0">INVITE LINK GENERATED</h3>
        <p>Share this link to invite others to your zone:</p>
        <div style="background:#111; padding:10px; word-break:break-all; margin:10px 0; border:1px solid #333">
            ${window.location.origin}/sdoh/register.html?invite=${inviteData.code}
        </div>
        <p style="font-size:12px; color:#888">
            Uses remaining: ${inviteData.uses_remaining}<br>
            Expires: ${new Date(inviteData.expires_at).toLocaleDateString()}
        </p>
        <div style="text-align:right; margin-top:20px">
            <button id="close-invite-modal" style="background:none; border:1px solid #00ff00; color:#00ff00; padding:5px 10px; cursor:pointer">CLOSE</button>
        </div>
    `;
    
    modal.appendChild(content);
    document.body.appendChild(modal);
    
    document.getElementById('close-invite-modal').onclick = () => {
        document.body.removeChild(modal);
    };
}

function promptRename() {
    const newName = prompt("Enter new name for this chat:");
    if (newName) {
        // Mock implementation
        alert("Rename proposal submitted for voting!");
    }
}

async function endCurrentQuest() {
    if (!confirm("Are you sure you want to end your current quest? All progress will be lost.")) return;
    
    try {
        const res = await fetchWithAuth('/quest/end', {
            method: 'POST'
        });
        
        if (res && res.ok) {
            const data = await res.json();
            window.currentUser.active_quest_id = null;
            if (typeof updateQuestPanel === 'function') {
                updateQuestPanel(window.currentUser.integrity_score, window.currentUser.insights, window.currentUser.inventory, null);
            }
            alert(data.message);
            
            // Reload messages to show quest is ended
            loadMessages(`quest_${window.currentUser.user_id}`);
        }
    } catch (e) {
        console.error("Error ending quest:", e);
    }
}

async function loadForgeGreeting() {
    try {
        const res = await fetchWithAuth('/forge/greeting');
        if (!res) return;
        const data = await res.json();
        
        // Display greeting as agent message
        const container = document.getElementById('messages');
        container.innerHTML = '';
        const div = document.createElement('div');
        div.className = 'msg';
        div.style.borderLeftColor = 'var(--red)';
        
        // Create button element separately to properly set data attribute
        const listenBtn = document.createElement('button');
        listenBtn.className = 'tts-btn';
        listenBtn.style.cssText = 'float:right; margin-left:5px';
        listenBtn.textContent = '🔊 LISTEN';
        listenBtn.setAttribute('data-text', data.greeting); // Store unescaped text
        listenBtn.onclick = function() { startTTS(this); };
        
        // Create formatted greeting with proper HTML rendering
        const greetingText = data.greeting
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
        
        div.innerHTML = `
            <div style="margin-bottom:5px">
                <span class="msg-sender" style="color:var(--red)">THE FORGE:</span>
            </div>
            <div style="clear:both; margin:10px 0; white-space: pre-wrap; line-height:1.5">${greetingText}</div>
            <div style="margin-top:10px; overflow:hidden">
                <span class="msg-time" style="float:left">Now</span>
            </div>
        `;
        
        // Append listen button to the message
        const buttonContainer = document.createElement('div');
        buttonContainer.style.marginBottom = '10px';
        buttonContainer.appendChild(listenBtn);
        div.insertBefore(buttonContainer, div.children[1]);
        
        container.appendChild(div);
    } catch (e) {
        console.error(e);
    }
}

async function loadQuestGreeting() {
    try {
        const res = await fetchWithAuth('/quest/greeting');
        if (!res) return;
        const data = await res.json();
        
        // Display greeting as agent message
        const container = document.getElementById('messages');
        container.innerHTML = '';
        const div = document.createElement('div');
        div.className = 'msg';
        div.style.borderLeftColor = '#ffaa00';
        
        // Create button element separately to properly set data attribute
        const listenBtn = document.createElement('button');
        listenBtn.className = 'tts-btn';
        listenBtn.style.cssText = 'float:right; margin-left:5px';
        listenBtn.textContent = '🔊 LISTEN';
        listenBtn.setAttribute('data-text', data.greeting); // Store unescaped text
        listenBtn.onclick = function() { startTTS(this); };
        
        // Create formatted greeting with proper HTML rendering
        const greetingText = data.greeting
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
        
        div.innerHTML = `
            <div style="margin-bottom:5px">
                <span class="msg-sender" style="color:#ffaa00">QUEST MASTER:</span>
            </div>
            <div style="clear:both; margin:10px 0; white-space: pre-wrap; line-height:1.5">${greetingText}</div>
            <div style="margin-top:10px; overflow:hidden">
                <span class="msg-time" style="float:left">Now</span>
            </div>
        `;
        
        // Append listen button to the message
        const buttonContainer = document.createElement('div');
        buttonContainer.style.marginBottom = '10px';
        buttonContainer.appendChild(listenBtn);
        div.insertBefore(buttonContainer, div.children[1]);
        
        container.appendChild(div);
    } catch (e) {
        console.error(e);
    }
}

// Hall of Heroes Logic
async function openHallOfHeroes() {
    document.getElementById('hall-of-heroes-modal').classList.remove('hidden');
    const list = document.getElementById('stories-list');
    list.innerHTML = '<div style="text-align:center; color:#666; padding:20px">Loading stories...</div>';
    
    try {
        const res = await fetchWithAuth(`/quest/stories`);
        if (!res) return;
        const stories = await res.json();
        
        if (stories.length === 0) {
            list.innerHTML = '<div style="text-align:center; color:#666; padding:20px">No stories have been shared yet. Be the first!</div>';
            return;
        }
        
        list.innerHTML = '';
        window.__hallOfHeroesStories = stories;
        
        // Group stories by user
        const groups = {};
        stories.forEach(story => {
            const key = story.user_id || 'UNKNOWN';
            if (!groups[key]) {
                groups[key] = {
                    id: key,
                    alias: story.user_alias || 'Unknown Hero',
                    stories: []
                };
            }
            groups[key].stories.push(story);
        });

        // Sort stories within groups by date (newest first)
        Object.values(groups).forEach(g => {
            g.stories.sort((a, b) => b.id.localeCompare(a.id)); // Assuming UUIDs or sequential IDs
        });

        // Sort groups so current user is first, then by story count
        const sortedGroupKeys = Object.keys(groups).sort((a, b) => {
            if (window.currentUser) {
                if (a === window.currentUser.user_id) return -1;
                if (b === window.currentUser.user_id) return 1;
            }
            return groups[b].stories.length - groups[a].stories.length;
        });

        sortedGroupKeys.forEach(userId => {
            const group = groups[userId];
            const isMe = window.currentUser && userId === window.currentUser.user_id;

            const sectionWrapper = document.createElement('div');
            sectionWrapper.style.marginBottom = '20px';
            sectionWrapper.style.border = isMe ? '1px solid #00ffff' : '1px solid #333';
            sectionWrapper.style.borderRadius = '8px';
            sectionWrapper.style.overflow = 'hidden';
            sectionWrapper.style.background = isMe ? 'rgba(0,255,255,0.02)' : 'transparent';

            const header = document.createElement('div');
            header.style.cssText = `
                padding: 12px 15px;
                background: ${isMe ? 'rgba(0,255,255,0.1)' : 'rgba(255,255,255,0.05)'};
                cursor: pointer;
                display: flex;
                justify-content: space-between;
                align-items: center;
                user-select: none;
            `;
            header.innerHTML = `
                <div style="display:flex; align-items:center">
                    <span style="color:${isMe ? '#00ffff' : '#aaa'}; font-weight:bold; font-size:14px">
                        ${isMe ? '👤 MY SAGA' : '🛡️ ' + group.alias}
                    </span>
                    <span style="font-size:10px; color:#666; margin-left:10px">${group.stories.length} stories</span>
                    ${isMe ? `
                        <div style="margin-left:15px; display:flex; gap:5px" onclick="event.stopPropagation()">
                            <select id="my-stories-sort" style="background:#111; color:#00ffff; border:1px solid #00ffff; font-size:8px; border-radius:3px">
                                <option value="newest">NEWEST</option>
                                <option value="popular">POPULAR</option>
                            </select>
                        </div>
                    ` : ''}
                </div>
                <div style="display:flex; align-items:center">
                    ${isMe ? `<button onclick="event.stopPropagation(); window.clearMyStories()" style="background:none; border:1px solid #ff4444; color:#ff4444; font-size:9px; cursor:pointer; padding:2px 6px; border-radius:3px; margin-right:15px">🗑️ CLEAR PROFILE</button>` : ''}
                    <span class="section-arrow" style="transition: transform 0.3s; transform: rotate(${isMe ? '0deg' : '-90deg'})">▼</span>
                </div>
            `;

            const content = document.createElement('div');
            content.style.display = isMe ? 'block' : 'none';
            content.style.padding = '10px';

            if (isMe) {
                setTimeout(() => {
                    const sortBtn = document.getElementById('my-stories-sort');
                    if (sortBtn) {
                        sortBtn.onchange = () => {
                            const val = sortBtn.value;
                            group.stories.sort((a, b) => {
                                if (val === 'popular') return b.likes - a.likes;
                                return b.id.localeCompare(a.id);
                            });
                            content.innerHTML = '';
                            group.stories.forEach(story => content.appendChild(renderStoryBlock(story)));
                        };
                    }
                }, 0);
            }

            function renderStoryBlock(story) {
                const div = document.createElement('div');
                div.className = 'story-block';
                div.style.border = '1px solid #222';
                div.style.padding = '15px';
                div.style.marginBottom = '10px';
                div.style.borderRadius = '5px';
                div.style.background = '#050505';
                div.style.cursor = 'pointer';
                div.onclick = () => window.toggleStory(story.id);

                div.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:flex-start">
                        <div style="flex:1">
                            <div style="color:#00ffff; font-weight:bold; font-size:14px; text-transform:uppercase">${story.title}</div>
                            <div style="color:#666; font-size:10px; margin-bottom:10px">${story.quest_name}</div>
                            ${story.voice_note_url ? `
                                <div style="margin-bottom:10px; background: rgba(0,255,255,0.05); padding: 8px; border-radius: 4px; border: 1px solid #00ffff33">
                                    <div style="color:#00ffff; font-size:8px; margin-bottom:5px; text-transform:uppercase">🔊 Voice note</div>
                                    <audio controls style="width:100%; height:25px; filter: invert(100%)">
                                        <source src="${story.voice_note_url}" type="audio/mpeg">
                                    </audio>
                                </div>
                            ` : ''}
                            <div id="desc-${story.id}" style="color:#ccc; font-size:11px; font-style:italic; line-height:1.4">${story.description || "An epic saga waiting to be read..."}</div>
                        </div>
                        <div style="text-align:right; margin-left:10px">
                            <button onclick="event.stopPropagation(); likeStory('${story.id}', this)" style="background:none; border:1px solid #ff0080; color:#ff0080; font-size:10px; cursor:pointer; padding:2px 5px; border-radius:3px">❤️ ${story.likes}</button>
                        </div>
                    </div>
                    <div id="content-${story.id}" class="hidden" style="margin-top:20px; border-top:1px solid #222; padding-top:15px">
                        <div style="text-align:center; color:#666; font-size:11px">Expanding saga...</div>
                    </div>
                `;
                return div;
            }

            group.stories.forEach(story => content.appendChild(renderStoryBlock(story)));

            header.onclick = () => {
                const isNowExpanded = content.style.display === 'none';
                content.style.display = isNowExpanded ? 'block' : 'none';
                const arrow = header.querySelector('.section-arrow');
                arrow.style.transform = `rotate(${isNowExpanded ? '0deg' : '-90deg'})`;
            };

            sectionWrapper.appendChild(header);
            sectionWrapper.appendChild(content);
            list.appendChild(sectionWrapper);

            sectionWrapper.appendChild(header);
            sectionWrapper.appendChild(content);
            list.appendChild(sectionWrapper);
        });
    } catch (e) {
        list.innerHTML = '<div style="text-align:center; color:#ff0000; padding:20px">Error loading stories.</div>';
    }
}

window.toggleStory = function(storyId) {
    const el = document.getElementById(`content-${storyId}`);
    if (!el) return;

    if (el.classList.contains('hidden')) {
        el.classList.remove('hidden');

        // Lazy Render Fragments if not already done
        if (!el.dataset.rendered) {
            const story = (window.__hallOfHeroesStories || []).find(s => s.id === storyId);
            if (story && story.fragments) {
                // Prevent concurrent rendering if user double-clicks
                if (el.dataset.rendered === "rendering") return;
                el.dataset.rendered = "rendering";

                const fragments = story.fragments;
                const CHUNK_SIZE = 3; // Small chunks
                let currentIndex = 0;
                
                // Show a progress loader at the bottom
                el.innerHTML = `<div id="loader-${storyId}" style="text-align:center; color:#00ffff; font-size:10px; padding:15px; background:rgba(0,255,255,0.05); border:1px dashed #00ffff; border-radius:3px; margin-top:10px">Expanding Saga: 0/${fragments.length} parts...</div>`;
                
                function renderChunk() {
                    // Safety check: Stop if element was removed or hidden again
                    if (el.classList.contains('hidden') || !document.body.contains(el)) {
                        el.dataset.rendered = ""; // Allow restart later
                        return;
                    }
                    
                    if (currentIndex >= fragments.length) {
                        const loader = document.getElementById(`loader-${storyId}`);
                        if (loader) loader.remove();
                        el.dataset.rendered = "true";
                        return;
                    }
                    
                    // Update loader progress
                    const loader = document.getElementById(`loader-${storyId}`);
                    if (loader) loader.textContent = `Expanding Saga: ${currentIndex}/${fragments.length} parts... (Tap to close if needed)`;
                    
                    const chunk = fragments.slice(currentIndex, currentIndex + CHUNK_SIZE);
                    const fragmentNodes = document.createDocumentFragment();
                    
                    chunk.forEach((frag, idx) => {
                        const globalIndex = currentIndex + idx;
                        const canEdit = window.currentUser && story.user_id === window.currentUser.user_id;
                        
                        const fragDiv = document.createElement('div');
                        fragDiv.style.cssText = "margin-bottom:15px; padding:12px; background:#111; border-radius:4px; border-left:3px solid #00ffff; contain: content;";
                        
                        // Use a cheaper HTML template for the fragment
                        fragDiv.innerHTML = `
                            <div style="font-size:10px; color:#555; margin-bottom:8px; display:flex; justify-content:space-between; font-family:monospace">
                                <span>PHASE ${globalIndex + 1}</span>
                                ${canEdit ? `
                                    <div style="font-size:9px">
                                        <span onclick="event.stopPropagation(); window.editStoryFragment('${frag.id}')" style="cursor:pointer; color:#00ffff; margin-right:8px; border-bottom:1px solid #00ffff">EDIT</span>
                                        <span onclick="event.stopPropagation(); window.deleteStoryFragment('${frag.id}')" style="cursor:pointer; color:#ff4444; border-bottom:1px solid #ff4444">DELETE</span>
                                    </div>
                                ` : ''}
                            </div>
                            <div id="frag-content-${frag.id}" style="font-size:13px; color:#ddd; line-height:1.5; margin-bottom:12px; white-space: pre-line; word-break: break-word;">${frag.content}</div>
                            <button class="tts-btn" 
                                    data-frag-id="${frag.id}"
                                    onclick="event.stopPropagation(); window.startTTS(this)" 
                                    style="width:100%; padding:6px; font-size:11px; border:1px solid #00ffff; color:#00ffff; background:rgba(0,255,255,0.05); cursor:pointer; border-radius:2px; font-family:inherit">
                                🔊 LISTEN TO PHASE ${globalIndex + 1}
                            </button>
                        `;
                        fragmentNodes.appendChild(fragDiv);
                    });
                    
                    // Batch append before the loader
                    if (loader) {
                        el.insertBefore(fragmentNodes, loader);
                    } else {
                        el.appendChild(fragmentNodes);
                    }
                    
                    currentIndex += CHUNK_SIZE;
                    
                    // Yield more time to the browser for layout/scrolling
                    // 30ms is usually enough for a full frame + layout on mobile
                    setTimeout(renderChunk, 35);
                }
                
                // Start rendering in chunks
                renderChunk();
            }
        }
    } else {
        el.classList.add('hidden');
    }
};

async function submitStory() {
    const title = document.getElementById('publish-story-title').value;
    const description = document.getElementById('publish-story-description').value;
    const content = document.getElementById('publish-story-content').value;
    
    if (!title || !content) {
        alert("Please provide both a title and your story content.");
        return;
    }
    
    try {
        const res = await fetchWithAuth(`/quest/stories/publish`, {
            method: 'POST',
            body: JSON.stringify({
                quest_name: window.currentUser.active_quest_id || "Epic Journey",
                title: title,
                description: description,
                content: content
            })
        });
        
        if (res && res.ok) {
            alert("Your story has been published to the Hall of Heroes!");
            document.getElementById('publish-story-modal').classList.add('hidden');
            // Clear inputs
            document.getElementById('publish-story-title').value = '';
            document.getElementById('publish-story-description').value = '';
            document.getElementById('publish-story-content').value = '';
            
            openHallOfHeroes(); // Refresh the hall
        } else {
            const data = res ? await res.json() : { error: "Failed to publish story." };
            alert(data.error || "Failed to publish story.");
        }
    } catch (e) {
        console.error(e);
        alert("Error publishing story.");
    }
}

async function editStoryFragment(fragId) {
    const el = document.getElementById(`frag-content-${fragId}`);
    if (!el) return;
    
    const oldContent = el.innerText;
    const newContent = prompt("Edit your story fragment (this updates your public profile):", oldContent);
    
    if (newContent !== null && newContent !== oldContent) {
        try {
            const res = await fetchWithAuth(`/quest/stories/${fragId}`, {
                method: 'PUT',
                body: JSON.stringify({ content: newContent })
            });
            
            if (res && res.ok) {
                alert("Fragment updated!");
                openHallOfHeroes(); // Refresh
            } else {
                const data = res ? await res.json() : { error: "Failed to update fragment." };
                alert(data.error || "Failed to update fragment.");
            }
        } catch (e) {
            console.error(e);
            alert("Error updating fragment.");
        }
    }
}

async function deleteStoryFragment(fragId) {
    if (!confirm("Are you sure you want to delete this story fragment?")) return;
    
    try {
        const res = await fetchWithAuth(`/quest/stories/${fragId}`, {
            method: 'DELETE'
        });
        
        if (res && res.ok) {
            alert("Fragment deleted!");
            openHallOfHeroes(); // Refresh
        } else {
            alert("Failed to delete fragment.");
        }
    } catch (e) {
        console.error(e);
        alert("Error deleting fragment.");
    }
}

async function clearMyStories() {
    if (!confirm("Are you sure you want to clear your entire Hall of Heroes profile? This cannot be undone.")) return;
    
    try {
        const res = await fetchWithAuth(`/quest/stories/clear`, {
            method: 'POST'
        });
        
        if (res && res.ok) {
            alert("Profile cleared!");
            openHallOfHeroes(); // Refresh
        } else {
            alert("Failed to clear profile.");
        }
    } catch (e) {
        console.error(e);
        alert("Error clearing profile.");
    }
}

function closeHallOfHeroes() {
    document.getElementById('hall-of-heroes-modal').classList.add('hidden');
    window.speechSynthesis.cancel();
}

async function likeStory(storyId, btn) {
    try {
        const res = await fetchWithAuth(`/quest/stories/${storyId}/like`, {
            method: 'POST'
        });
        if (res && res.ok) {
            const data = await res.json();
            btn.innerHTML = `❤️ ${data.likes}`;
        }
    } catch (e) {
        console.error(e);
    }
}

function publishCurrentStory() {
    const modal = document.getElementById('publish-story-modal');
    const contentArea = document.getElementById('publish-story-content');
    const titleArea = document.getElementById('publish-story-title');
    
    if (!modal || !contentArea) return;
    
    // Pre-fill from quest log if available
    let storyText = "";
    if (window.currentUser && window.currentUser.quest_progress && window.currentUser.quest_progress.quest_log) {
        const log = window.currentUser.quest_progress.quest_log;
        if (Array.isArray(log)) {
            // Collect all entries into a narrative, separated by explicit markers for backend splitting
            storyText = log.map(entry => {
                const text = typeof entry === 'string' ? entry : (entry.text || entry.content || "");
                return text;
            }).join("\n\n---\n\n");
        } else {
            // It's already a string
            storyText = log;
        }
    }
    
    contentArea.value = storyText;
    titleArea.value = window.currentUser ? (window.currentUser.active_quest_id || "") : "";
    
    modal.classList.remove('hidden');
}

function voteRevert() {
    alert("Revert vote cast. Waiting for community consensus...");
    document.getElementById('vote-banner').classList.add('hidden');
}

function applyColor(color) {
    if (!window.currentUser) return;
    // Mock save
    console.log(`Applying color: ${color}`);
}

function updateValue(id) {
    const input = document.getElementById(`tts-${id}`);
    const display = document.getElementById(`${id}-value`);
    if (input && display) {
        let val = input.value;
        if (id === 'rate') val += 'x';
        display.textContent = val;
        
        // Auto-save settings to localStorage so they apply immediately to Browser TTS
        localStorage.setItem(`tts-${id}`, input.value);
    }
}

async function previewVoice() {
    const msg = "This is a preview of the selected voice and settings.";
    
    // Use playTTS directly for preview
    if (typeof window.playTTS === 'function') {
        const btn = document.getElementById('preview-btn');
        const originalText = btn.textContent;
        btn.textContent = '🔊 PLAYING...';
        btn.disabled = true;
        
        await window.playTTS(msg);
        
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// Global UI Exports
window.openChat = openChat;
window.addMockCategory = addMockCategory;
window.publishCurrentStory = publishCurrentStory;
window.voteRevert = voteRevert;
window.applyColor = applyColor;
window.updateValue = updateValue;
window.previewVoice = previewVoice;
window.openForgeChat = openForgeChat;
window.openQuestChat = openQuestChat;
window.openSdohChat = openSdohChat;
window.openPacsChat = openPacsChat;
window.toggleCategory = toggleCategory;
window.togglePanelContent = togglePanelContent;
window.openHallOfHeroes = openHallOfHeroes;
window.submitStory = submitStory;
window.editStoryFragment = editStoryFragment;
window.deleteStoryFragment = deleteStoryFragment;
window.clearMyStories = clearMyStories;
window.closeHallOfHeroes = closeHallOfHeroes;
window.likeStory = likeStory;
window.closeChat = closeChat;
window.endCurrentQuest = endCurrentQuest;
window.openQuestBoard = openQuestBoard;
window.loadForgeGreeting = loadForgeGreeting;
window.promptRename = promptRename;
window.selectClass = selectClass;
window.openSettings = openSettings;
window.closeSettings = closeSettings;

window.triggerPacsEmergency = function() {
    const status = document.getElementById('pacs-status-text');
    if (status) status.textContent = 'BREAK-GLASS ARMED';

    const step = document.getElementById('pacs-recovery-step');
    if (step) step.textContent = 'Break-glass armed. Upload the directive to unlock recovery actions.';

    const fileInput = document.getElementById('pacs-auth-file');
    if (fileInput) fileInput.click();
};

window.triggerPacsAuth = window.triggerPacsEmergency;

window.runPacsDiscovery = async function() {
    const list = document.getElementById('pacs-discovery-list');
    list.innerHTML = '<div style="color:#00ff44">SCANNING NETWORK...</div>';
    try {
        const res = await fetchWithAuth('/pacs/discover', { method: 'POST', body: JSON.stringify({}) });
        const data = await res.json();
        list.innerHTML = '';
        if (data.devices && data.devices.length > 0) {
            data.devices.forEach(d => {
                const item = document.createElement('div');
                item.textContent = `[${d.mac}] ${d.vendor || 'Unknown Hardware'}`;
                list.appendChild(item);
            });
        } else {
            list.innerHTML = '<div class="text-dim">No devices found. Ensure local network access.</div>';
        }
    } catch (e) {
        list.innerHTML = '<div style="color:red">SCAN FAILED</div>';
    }
};

window.generatePacsReport = async function() {
    try {
        const res = await fetchWithAuth('/pacs/report');
        const data = await res.json();
        alert("INCIDENT REPORT GENERATED:\n\n" + data.report_summary);
    } catch (e) {
        alert("Failed to generate report.");
    }
};

window.triggerPacsAuth = function() {
    document.getElementById('pacs-auth-file').click();
};

window.handlePacsAuth = async function(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        // We use fetch directly since fetchWithAuth assumes JSON
        const res = await fetch(`${window.API_BASE}/pacs/verify-auth`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${window.token}` },
            body: formData
        });
        const data = await res.json();
        
        if (data.status === 'success') {
            document.getElementById('pacs-status-text').textContent = 'VERIFIED';
            document.getElementById('pacs-bar').style.width = '20%';
            document.getElementById('pacs-recovery-step').textContent = 'Authorization Confirmed. Access Phase 1 modules.';
            alert("PACS OVERRIDE ACTIVE: " + data.message);
            loadMessages(`pacs_${window.currentUser.user_id}`);
        } else {
            alert("PACS VERIFICATION FAILED: " + data.message);
        }
    } catch (e) {
        console.error("Auth upload failed:", e);
        alert("Upload failed. Check console.");
    }
};

window.saveSettings = saveSettings;
window.showInviteLink = showInviteLink;
window.toggleSubPanel = typeof toggleSubPanel !== 'undefined' ? toggleSubPanel : null;
window.togglePanelContent = typeof togglePanelContent !== 'undefined' ? togglePanelContent : (id) => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('hidden');
};
window.toggleModMenu = (groupId) => {
    const el = document.getElementById(`mod-menu-${groupId}`);
    if (el) el.style.display = (el.style.display === 'none') ? 'block' : 'none';
};
