// Chat Logic

let pollInterval = null;

async function loadMessages(groupId) {
    console.log(`Loading messages for group: ${groupId}`); // Debug
    const container = document.getElementById('messages');
    container.innerHTML = '<div style="text-align:center; color:#666">Loading...</div>';
    
    try {
        const res = await fetchWithAuth(`/messages/${groupId}`);
        if (!res) return;
        
        const messages = await res.json();
        
        if (!Array.isArray(messages)) {
            console.error('Expected array of messages, got:', messages);
            container.innerHTML = '<div style="text-align:center; color:red">Error loading messages (Invalid format)</div>';
            return;
        }

        container.innerHTML = '';
        
        if (messages.length === 0) {
            container.innerHTML = '<div style="text-align:center; color:#666; margin-top:20px">No messages yet. Start the conversation!</div>';
            // If Forge, maybe load greeting?
            if (groupId === `forge_${currentUser.user_id}`) {
                loadForgeGreeting();
            }
            return;
        }
        
        messages.forEach(msg => {
            const div = document.createElement('div');
            div.className = 'msg';
            const isMe = msg.sender_alias === currentUser.alias;
            const senderColor = isMe ? '#00ff00' : (aliasColors[msg.sender_alias] || '#ff00ff');
            
            // Add Listen button for agents
            const alias = msg.sender_alias;
            const isAgent = (alias === 'The Forge' || alias === 'Quest Master' || alias === 'THE FORGE' || alias === 'QUEST MASTER');
            const escapedContent = escapeHtml(msg.content);
            const listenBtn = isAgent ? `<button class="tts-btn" style="float:right; margin-left:5px" data-text="${escapedContent}" onclick="startTTS(this)">🔊 LISTEN</button>` : '';
            
            // Add Delete button for ALL messages (Me + Forge)
            // Moved to bottom right of message
            const deleteBtn = `<button class="btn-icon" style="float:right; font-size:10px; padding:2px 5px; margin-left:5px; color:#666; border-color:#444; margin-top:5px" onclick="deleteMessage('${msg.msg_id}')" title="Delete Message">🗑️</button>`;

            div.innerHTML = `
                <div style="margin-bottom:5px">
                    <span class="msg-sender" style="color:${senderColor}">${msg.sender_alias}:</span>
                    ${listenBtn}
                </div>
                <div style="clear:both">${msg.content}</div>
                <div style="margin-top:5px; overflow:hidden">
                    <span class="msg-time" style="float:left">${new Date(msg.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                    ${deleteBtn}
                </div>
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

async function deleteMessage(msgId) {
    if (!confirm("Delete this message?")) return;
    
    try {
        const res = await fetchWithAuth('/messages/delete', {
            method: 'POST',
            body: JSON.stringify({ msg_id: msgId })
        });
        
        if (res && res.ok) {
            // Reload messages to reflect deletion
            if (currentGroup) {
                loadMessages(currentGroup.id === 'forge' ? `forge_${currentUser.user_id}` : 
                             currentGroup.id === 'quest' ? `quest_${currentUser.user_id}` : 
                             currentGroup.id);
            }
        }
    } catch (e) {
        console.error("Delete failed:", e);
    }
}

async function clearChatHistory() {
    if (!confirm("Are you sure you want to clear ALL messages in this chat? This cannot be undone.")) return;
    
    let chatId = currentGroup.id;
    if (chatId === 'forge') chatId = `forge_${currentUser.user_id}`;
    if (chatId === 'quest') chatId = `quest_${currentUser.user_id}`;
    
    try {
        const res = await fetchWithAuth('/messages/clear_history', {
            method: 'POST',
            body: JSON.stringify({ chat_id: chatId })
        });
        
        if (res && res.ok) {
            document.getElementById('messages').innerHTML = '<div style="text-align:center; color:#666; margin-top:20px">Chat history cleared.</div>';
        }
    } catch (e) {
        console.error("Clear history failed:", e);
    }
}

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(pollMessages, 3000);
}

async function pollMessages() {
    if (!currentGroup) return;
    // In a real app, we'd use a timestamp or ID to fetch only new messages
    // For this demo, we might just re-fetch or skip if user is typing?
    // Let's skip for now to avoid UI jumping, or implement proper delta updates later.
    // For now, do nothing to keep it simple as per "refactor" request (don't add new complex logic).
}

async function sendMessage() {
    const input = document.getElementById('msg-input');
    const text = input.value.trim();
    if (!text) return;
    
    // Clear input immediately
    input.value = '';
    
    // Optimistic UI Update
    const container = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'msg';
    div.innerHTML = `
        <span class="msg-sender" style="color:#00ff00">${currentUser.alias}:</span>
        ${text}
        <span class="msg-time">Sending...</span>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    
    // Route to correct handler
    if (currentGroup.id === 'forge') {
        sendToForge(text);
    } else if (currentGroup.id === 'quest') {
        sendToQuest(text);
    } else {
        // Normal group chat
        try {
            await fetchWithAuth(`/messages/send`, {
                method: 'POST',
                body: JSON.stringify({ to: currentGroup.id, text: text })
            });
            // Reload to get server timestamp/confirmation
            loadMessages(currentGroup.id); 
        } catch (e) {
            console.error(e);
            div.style.opacity = 0.5;
            div.innerHTML += ' <span style="color:red">(Failed)</span>';
        }
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
        const escapedForgeResponse = escapeHtml(data.response);
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
        const escapedQuestResponse = escapeHtml(data.response);
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

async function loadForgeGreeting() {
    try {
        const res = await fetchWithAuth(`/forge/greeting`);
        if (!res) return;
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

function handleEnter(e) {
    if (e.key === 'Enter') sendMessage();
}
