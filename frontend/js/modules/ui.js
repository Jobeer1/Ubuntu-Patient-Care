// UI Logic

function toggleCategory(id) {
    const el = document.getElementById(id);
    el.classList.toggle('expanded');
}

function openChat(group) {
    currentGroup = group;
    document.getElementById('channel-screen').classList.add('hidden');
    document.getElementById('chat-screen').classList.remove('hidden');
    document.getElementById('current-chat-title').textContent = group.name;
    document.getElementById('current-chat-title').style.color = 'white'; // Reset color
    
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
                alias_colors: aliasColors
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
    
    const alias = currentUser.alias || 'USER';
    const letters = alias.split('');
    
    // Ensure aliasColors is populated
    if (!aliasColors || Object.keys(aliasColors).length === 0) {
        aliasColors = currentUser.alias_colors || {};
    }
    
    // Create a wrapper for the letters
    const lettersDiv = document.createElement('div');
    lettersDiv.id = 'alias-preview-inner';
    lettersDiv.style.marginBottom = '10px';
    
    letters.forEach((char, idx) => {
        const span = document.createElement('span');
        span.textContent = char;
        span.style.color = aliasColors[idx] || '#00ff00';
        span.style.cursor = 'pointer';
        span.style.padding = '0 2px';
        span.style.border = selectedLetterIdx === idx ? '1px solid white' : 'none';
        span.style.fontSize = '24px';
        span.style.fontWeight = 'bold';
        
        span.onclick = () => {
            selectedLetterIdx = idx;
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
            if (selectedLetterIdx !== -1) {
                aliasColors[selectedLetterIdx] = color;
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
