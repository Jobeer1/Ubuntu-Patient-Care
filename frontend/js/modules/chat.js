// Chat Logic

let pollInterval = null;
window.unreadCounts = {}; // Store unread counts by groupID

function updateNotification(groupId, count = 1) {
    if (window.currentGroup && (window.currentGroup.id === groupId || (window.currentGroup.name === 'THE FORGE' && groupId.startsWith('forge_')) || (window.currentGroup.name === 'THE QUEST' && groupId.startsWith('quest_')) || (window.currentGroup.name === 'SDOH NAVIGATOR' && groupId.startsWith('sdoh_')))) {
        return; // Don't notify if we're in the chat
    }
    window.unreadCounts[groupId] = (window.unreadCounts[groupId] || 0) + count;
    // We need to re-render the sidebars or just update the specific element if we can find it
    // For simplicity, we can trigger loadDashboard() or just a focused update
    if (typeof loadDashboard === 'function') {
        loadDashboard(); 
    }
}

async function loadMessages(groupId) {
    console.log(`Loading messages for group: ${groupId}`); // Debug
    const container = document.getElementById('messages');
    container.innerHTML = '<div style="text-align:center; color:#666">Loading...</div>';
    
    try {
        const isQuestBoard = window.currentGroup && window.currentGroup.name === 'Quest Board';
        // Increase limit for Quest Board to ensure we see all standard quests too
        const url = isQuestBoard ? `/messages/${groupId}?limit=200` : `/messages/${groupId}`;
        const res = await fetchWithAuth(url);
        if (!res) return;
        
        const messages = await res.json();
        
        if (!Array.isArray(messages)) {
            console.error('Expected array of messages, got:', messages);
            container.innerHTML = '<div style="text-align:center; color:red">Error loading messages (Invalid format)</div>';
            return;
        }

        if (
            groupId === `pacs_${window.currentUser.user_id}` &&
            messages.length > 0 &&
            messages.every(msg => msg.sender_id === 'SYSTEM') &&
            messages.some(msg => /unauthorized|emergency directive|unlock recovery modules|auth denied/i.test(msg.content || ''))
        ) {
            loadPacsGreeting();
            return;
        }

        container.innerHTML = '';
        
        // Update last seen to now
        localStorage.setItem(`last_seen_${groupId}`, new Date().toISOString());

        if (messages.length === 0) {
            container.innerHTML = '<div style="text-align:center; color:#666; margin-top:20px">No messages yet. Start the conversation!</div>';
            if (groupId === `forge_${window.currentUser.user_id}`) {
                loadForgeGreeting();
            }
            if (groupId === `quest_${window.currentUser.user_id}`) {
                loadQuestGreeting();
            }
            if (groupId === `sdoh_${window.currentUser.user_id}`) {
                loadSdohGreeting();
            }
            if (groupId === `pacs_${window.currentUser.user_id}`) {
                loadPacsGreeting();
            }
            return;
        }

        const renderMsg = (msg) => {
            const div = document.createElement('div');
            div.className = 'msg';
            const isMe = msg.sender_alias === window.currentUser.alias;
            const senderColor = isMe ? '#00ff00' : (window.aliasColors[msg.sender_alias] || '#ff00ff');
            
            const alias = msg.sender_alias;
            
            // Pre-process quest text for TTS
            let textToRead = msg.content;
            if (msg.content && msg.content.includes('[QUEST_DATA]')) {
                textToRead = "A new quest challenge arises. Open the quest card to read the details.";
            }
            
            // Whisper/Reply button for others
            const replyBtn = !isMe ? `<button class="btn-icon" style="float:right; font-size:10px; padding:2px 5px; margin-left:5px; color:#00ffff; border-color:#008888; margin-top:5px" onclick="replyTo('${alias}')" title="Reply/Whisper">💬 WHISPER</button>` : '';

            // Add Listen button for ALL messages
            const listenBtnOuter = `<button class="tts-btn" style="float:right; margin-left:5px; margin-top:5px" data-text="${escapeHtml(textToRead)}" onclick="startTTS(this)">🔊 LISTEN</button>`;
            
            // Add Delete button for ALL messages (Me + Forge)
            const deleteBtn = `<button class="btn-icon" style="float:right; font-size:10px; padding:2px 5px; margin-left:5px; color:#666; border-color:#444; margin-top:5px" onclick="deleteMessage('${msg.msg_id}')" title="Delete Message">🗑️</button>`;

            // Check for Quest Data
            if (msg.content && typeof msg.content === 'string' && msg.content.includes('[QUEST_DATA]')) {
                const questMatch = msg.content.match(/\[QUEST_DATA\]:?\s*(.*)/);
                if (questMatch) {
                    try {
                        const questData = JSON.parse(questMatch[1]);
                        
                        const isSystemQuest = questData.source === 'quest_master' || questData.source === 'boss_instance';
                        const isBoss = questData.difficulty === 'BOSS' || questData.source === 'boss_instance' || (questData.title && questData.title.toLowerCase().includes('boss'));
                        const sourceLabel = isBoss ? 'LEGENDARY CHALLENGE' : (isSystemQuest ? 'QUEST MASTER' : 'COMMUNITY QUEST');
                        const sourceColor = isBoss ? '#ff0000' : (isSystemQuest ? '#ffaa00' : '#00ffff');
                        const reqs = questData.requirements ? `<div style="font-size:0.8em; color:#aaa; margin-top:5px"><strong>Requirements:</strong> ${questData.requirements.join(', ')}</div>` : '';

                        div.style.borderLeftColor = sourceColor;
                        div.innerHTML = `
                            <div style="margin-bottom:5px">
                                <span class="msg-sender" style="color:${sourceColor}">${sourceLabel}:</span>
                                ${isBoss ? '<span style="background:#ff0000; color:white; font-size:10px; padding:2px 5px; border-radius:3px; margin-left:5px; font-weight:bold">BOSS</span>' : ''}
                                ${listenBtnOuter}
                                ${replyBtn}
                            </div>
                            <div style="background:#222; padding:10px; border:1px solid ${sourceColor}; cursor:pointer" onclick="showQuestDetails(this)" 
                                 data-title="${escapeHtml(questData.title)}" 
                                 data-desc="${escapeHtml(questData.description)}" 
                                 data-start="${escapeHtml(questData.start_location || '')}"
                                 data-goal="${escapeHtml(questData.end_goal || '')}"
                                 data-xp="${questData.xp}"
                                 data-boss="${isBoss}"
                                 data-reqs="${escapeHtml(questData.requirements ? questData.requirements.join(', ') : '')}">
                                <div style="font-weight:bold; color:${sourceColor}; font-size:1.2em">${isBoss ? '💀' : '📜'} ${questData.title}</div>
                                <div style="font-size:0.9em; color:#ccc; margin-top:5px">Reward: <span style="color:#00ff00">${questData.xp} XP</span></div>
                                ${reqs}
                                <div style="font-size:0.8em; color:#666; margin-top:5px; font-style:italic">(Click to Read & Listen)</div>
                            </div>
                            <div style="margin-top:5px; overflow:hidden">
                                <span class="msg-time" style="float:left">${new Date(msg.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                                ${deleteBtn}
                            </div>
                        `;
                        return div;
                    } catch(e) {
                        console.error('Failed to parse quest data:', e);
                    }
                }
            }

            div.innerHTML = `
                <div style="margin-bottom:5px">
                    <span class="msg-sender" style="color:${senderColor}">${msg.sender_alias}:</span>
                    ${listenBtnOuter}
                    ${replyBtn}
                </div>
                <div style="clear:both">${msg.content}</div>
                <div style="margin-top:5px; overflow:hidden">
                    <span class="msg-time" style="float:left">${new Date(msg.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                    ${deleteBtn}
                </div>
            `;
            
            return div;
        };

        if (isQuestBoard) {
            const masterQuests = [];
            const communityQuests = [];
            const bosses = [];
            const chats = [];
            
            messages.forEach(msg => {
                const questMatch = msg.content && msg.content.match(/\[QUEST_DATA\]:?\s*(.*)/);
                if (questMatch) {
                    try {
                        const data = JSON.parse(questMatch[1]);
                        if (data.difficulty === 'BOSS' || data.source === 'boss_instance' || (data.title && data.title.toLowerCase().includes('boss'))) {
                            bosses.push(msg);
                        } else if (data.source === 'quest_master' || msg.sender_id === 'QUEST') {
                            masterQuests.push(msg);
                        } else {
                            communityQuests.push(msg);
                        }
                    } catch(e) { 
                        if (msg.sender_id === 'QUEST') masterQuests.push(msg);
                        else chats.push(msg); 
                    }
                } else if (msg.sender_id === 'QUEST') {
                    masterQuests.push(msg);
                } else {
                    chats.push(msg);
                }
            });

            const createSection = (title, color, msgs, isInitiallyExpanded = true) => {
                const sectionId = `section-${title.replace(/\s+/g, '-').toLowerCase()}`;
                const wrapper = document.createElement('div');
                wrapper.style.margin = '15px 0';
                wrapper.style.border = `1px solid ${color}33`;
                wrapper.style.borderRadius = '5px';
                wrapper.style.overflow = 'hidden';
                
                const header = document.createElement('div');
                header.style.cssText = `
                    color: ${color}; 
                    font-weight: bold; 
                    border-bottom: 1px solid ${color}66; 
                    padding: 12px; 
                    font-size: 1.1em; 
                    cursor: pointer; 
                    display: flex; 
                    justify-content: space-between; 
                    align-items: center;
                    background: rgba(255,255,255,0.05);
                `;
                header.innerHTML = `<span>${title} (${msgs.length})</span> <span class="section-arrow" style="transition: transform 0.3s; transform: rotate(${isInitiallyExpanded ? '0deg' : '-90deg'})">▼</span>`;
                
                const content = document.createElement('div');
                content.id = sectionId;
                content.style.display = isInitiallyExpanded ? 'block' : 'none';
                content.style.padding = '5px';
                
                if (msgs.length === 0) {
                    content.innerHTML = `<div style="padding:10px; color:#666; font-style:italic">No active quests in this category.</div>`;
                } else {
                    msgs.forEach(m => content.appendChild(renderMsg(m)));
                }
                
                header.onclick = () => {
                    const isNowExpanded = content.style.display === 'none';
                    content.style.display = isNowExpanded ? 'block' : 'none';
                    const arrow = header.querySelector('.section-arrow');
                    arrow.style.transform = `rotate(${isNowExpanded ? '0deg' : '-90deg'})`;
                };
                
                wrapper.appendChild(header);
                wrapper.appendChild(content);
                container.appendChild(wrapper);
            };

            createSection('💀 BOSS FIGHTS', '#ff4444', bosses, false);
            createSection('📜 GAME QUESTS', '#ffa500', masterQuests, true);
            createSection('🗺️ COMMUNITY QUESTS', '#00cccc', communityQuests, true);
            createSection('💬 BOARD DISCUSSIONS', '#888888', chats, false);
            
        } else {
            messages.forEach(msg => {
                container.appendChild(renderMsg(msg));
            });
        }
        
        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
        
    } catch (e) {
        console.error(e);
        container.innerHTML = '<div style="text-align:center; color:red">Error loading messages</div>';
    }
}

function showQuestDetails(el) {
    const title = el.getAttribute('data-title');
    const desc = el.getAttribute('data-desc');
    const start = el.getAttribute('data-start');
    const goal = el.getAttribute('data-goal');
    const xp = el.getAttribute('data-xp');
    const reqs = el.getAttribute('data-reqs');
    const isBoss = el.getAttribute('data-boss') === 'true';
    
    // Let's use a custom modal for this.
    let modal = document.getElementById('quest-detail-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'quest-detail-modal';
        modal.className = 'modal hidden';
        modal.innerHTML = `
            <div class="modal-content" style="max-width:500px">
                <h3 id="qd-title" style="color:#ffaa00; border-bottom:1px solid #ffaa00; padding-bottom:10px"></h3>
                <div id="qd-reqs" style="font-size:0.9em; color:#aaa; margin-top:10px; font-style:italic"></div>
                <div style="margin-top:15px">
                    <div id="qd-start-label" style="color:#ffaa00; font-size:0.8em; font-weight:bold">STARTING LOCATION:</div>
                    <div id="qd-start" style="color:#ddd; margin-bottom:10px"></div>
                    
                    <div id="qd-goal-label" style="color:#ffaa00; font-size:0.8em; font-weight:bold">END GOAL:</div>
                    <div id="qd-goal" style="color:#ddd; margin-bottom:10px"></div>
                </div>
                <div id="qd-desc" style="margin:20px 0; line-height:1.5; color:#ddd; white-space: pre-wrap; border-top:1px solid #333; padding-top:10px"></div>
                <div style="text-align:center; margin-top:20px">
                    <div style="color:#00ff00; font-weight:bold; margin-bottom:10px">REWARD: <span id="qd-xp"></span> XP</div>
                    <button id="qd-listen-btn" class="tts-btn" style="font-size:14px; padding:10px 20px">🔊 LISTEN TO QUEST</button>
                    <button id="qd-start-btn" class="tts-btn" style="font-size:14px; padding:10px 20px; margin-left:10px; background:#ffaa00; color:black; border:none; font-weight:bold">⚔️ START QUEST</button>
                    <br><br>
                    <button class="btn-icon" onclick="document.getElementById('quest-detail-modal').classList.add('hidden')">CLOSE</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    const themeColor = isBoss ? '#ff0000' : '#ffaa00';
    document.getElementById('qd-title').textContent = (isBoss ? '💀 ' : '📜 ') + title;
    document.getElementById('qd-title').style.color = themeColor;
    document.getElementById('qd-title').style.borderBottomColor = themeColor;
    document.getElementById('qd-start-label').style.color = themeColor;
    document.getElementById('qd-goal-label').style.color = themeColor;

    document.getElementById('qd-desc').textContent = desc;
    document.getElementById('qd-start').textContent = start || 'Unknown';
    document.getElementById('qd-goal').textContent = goal || 'Unknown';
    document.getElementById('qd-xp').textContent = xp;
    document.getElementById('qd-reqs').textContent = reqs ? `Requirements: ${reqs}` : '';
    
    const startBtn = document.getElementById('qd-start-btn');
    startBtn.style.background = themeColor;
    startBtn.textContent = isBoss ? '💀 CHALLENGE BOSS' : '⚔️ START QUEST';
    startBtn.onclick = function() { startQuest(title); };

    const listenBtn = document.getElementById('qd-listen-btn');
    listenBtn.setAttribute('data-text', `${title}. Starting at ${start}. Goal: ${goal}. ${desc}`);
    listenBtn.onclick = function() { 
        if (typeof window.startTTS === 'function') {
            window.startTTS(this);
        } else {
            console.error("TTS module not found");
        }
    };
    
    modal.classList.remove('hidden');
}

window.replyTo = function(alias) {
    const input = document.getElementById('msg-input');
    if (input) {
        input.value = `@${alias} ` + input.value;
        input.focus();
    }
}

async function startQuest(title) {
    document.getElementById('quest-detail-modal').classList.add('hidden');
    
    // Send acceptance message
    await sendToQuest(`I accept the quest: ${title}`);
    
    // Switch to Quest Chat
    if (typeof openQuestChat === 'function') {
        openQuestChat();
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
            if (window.currentGroup) {
                loadMessages(window.currentGroup.id === 'forge' ? `forge_${window.currentUser.user_id}` : 
                             window.currentGroup.id === 'quest' ? `quest_${window.currentUser.user_id}` : 
                             window.currentGroup.id);
            }
        }
    } catch (e) {
        console.error("Delete failed:", e);
    }
}

async function clearChatHistory() {
    if (!confirm("Are you sure you want to clear ALL messages in this chat? This cannot be undone.")) return;
    
    let chatId = window.currentGroup.id;
    if (chatId === 'forge') chatId = `forge_${window.currentUser.user_id}`;
    if (chatId === 'quest') chatId = `quest_${window.currentUser.user_id}`;
    
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
    if (!window.currentGroup) return;
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
        <span class="msg-sender" style="color:#00ff00">${window.currentUser.alias}:</span>
        <button class="tts-btn" style="float:right; margin-left:5px" data-text="${escapeHtml(text)}" onclick="startTTS(this)">🔊 LISTEN</button>
        <div style="clear:both">${text}</div>
        <span class="msg-time">Sending...</span>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    
    // Route to correct handler
    if (window.currentGroup.id === 'forge') {
        sendToForge(text);
    } else if (window.currentGroup.id === 'quest') {
        sendToQuest(text);
    } else if (window.currentGroup.id === `sdoh_${window.currentUser.user_id}`) {
        sendToSdoh(text);
    } else if (window.currentGroup.id === `pacs_${window.currentUser.user_id}`) {
        sendToPacs(text);
    } else {
        // Normal group chat
        try {
            await fetchWithAuth(`/messages/send`, {
                method: 'POST',
                body: JSON.stringify({ to: window.currentGroup.id, text: text })
            });
            // Reload to get server timestamp/confirmation
            loadMessages(window.currentGroup.id); 
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

        const res = await fetch(`${window.API_BASE}/forge/chat`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.token}`
            },
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        
        // Update Panel
        if (data.score !== undefined) {
            window.currentUser.integrity_score = data.score;
            window.currentUser.insights = data.insights;
            updateForgePanel(data.score, data.insights);
        }
        
        // Append Agent Response with TTS button
        const container = document.getElementById('messages');
        const div = document.createElement('div');
        div.className = 'msg';
        div.style.borderLeftColor = 'var(--red)';
        const escapedForgeResponse = escapeHtml(data.response);
        div.innerHTML = `
            <div style="margin-bottom:5px">
                <span class="msg-sender" style="color:var(--red)">THE FORGE:</span>
                <button class="tts-btn" style="float:right; margin-left:5px" data-text="${escapedForgeResponse}" onclick="startTTS(this)">🔊 LISTEN</button>
            </div>
            <div style="clear:both">${data.response}</div>
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
        const res = await fetch(`${window.API_BASE}/quest/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.token}`
            },
            body: JSON.stringify({ content: text })
        });
        
        const data = await res.json();
        
        // Update Panel
        if (data.score !== undefined) {
            window.currentUser.integrity_score = data.score;
            window.currentUser.insights = data.insights;
            window.currentUser.inventory = data.inventory;
            window.currentUser.active_quest_id = data.active_quest_id;
            
            if (typeof updateQuestPanel === 'function') {
                updateQuestPanel(data.score, data.insights, data.inventory, data.active_quest_id);
            }
        }
        
        // Display response
        const container = document.getElementById('messages');
        const div = document.createElement('div');
        div.className = 'msg';
        div.style.borderLeftColor = '#ffaa00';
        const escapedQuestResponse = escapeHtml(data.response);
        div.innerHTML = `
            <div style="margin-bottom:5px">
                <span class="msg-sender" style="color:#ffaa00">THE QUEST:</span>
                <button class="tts-btn" style="float:right; margin-left:5px" data-text="${escapedQuestResponse}" onclick="startTTS(this)">🔊 LISTEN</button>
            </div>
            <div style="clear:both">${data.response}</div>
            ${data.quest_posted ? '<br><br><strong style="color:#ffaa00">[Quest Posted to Board!]</strong>' : ''}
            ${data.story_published ? '<br><br><strong style="color:#00ffff">🏛️ [A new story has been published to the Hall of Heroes!]</strong>' : ''}
            <span class="msg-time">Now</span>
        `;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        
    } catch (e) {
        console.error(e);
    }
}

function saveSdohExportBundle(bundle) {
    if (!bundle || !window.currentUser) return;
    try {
        localStorage.setItem(`sdoh_export_bundle_${window.currentUser.user_id}`, JSON.stringify(bundle));
    } catch (e) {
        console.error('Failed to persist SDOH export bundle:', e);
    }
}

function loadSdohExportBundle() {
    if (!window.currentUser) return null;
    try {
        const raw = localStorage.getItem(`sdoh_export_bundle_${window.currentUser.user_id}`);
        return raw ? JSON.parse(raw) : null;
    } catch (e) {
        console.error('Failed to read SDOH export bundle:', e);
        return null;
    }
}

function downloadTextFile(content, filename, mimeType) {
    if (!content) return;
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
}

function renderSdohPanel(bundle) {
    const panel = document.getElementById('sdoh-panel');
    if (!panel) return;

    const summary = document.getElementById('sdoh-summary');
    const timeline = document.getElementById('sdoh-timeline-list');
    const status = document.getElementById('sdoh-status-text');
    const bar = document.getElementById('sdoh-bar');
    const exportFlag = document.getElementById('sdoh-export-flag');
    const analyticsBlock = document.getElementById('sdoh-analytics');
    const analyticsNote = document.getElementById('sdoh-analytics-note');
    const guardrail = document.getElementById('sdoh-guardrail');
    const downloadIcsBtn = document.getElementById('sdoh-download-ics');
    const downloadPassportBtn = document.getElementById('sdoh-download-passport');
    const copySummaryBtn = document.getElementById('sdoh-copy-summary');

    const exportReady = Boolean(bundle && bundle.export_ready);
    const timelineItems = bundle?.calendar_events || [];
    const analytics = bundle?.analytics || null;

    if (summary) {
        summary.textContent = bundle?.passport_markdown
            ? bundle.passport_markdown.split('\n').slice(0, 6).join(' ').replace(/\s+/g, ' ').trim()
            : 'No continuity snapshot yet...';
    }

    if (timeline) {
        timeline.innerHTML = '';
        if (timelineItems.length === 0) {
            timeline.innerHTML = '<div style="font-style:italic; color:#456">No active recovery items...</div>';
        } else {
            timelineItems.forEach((item) => {
                const div = document.createElement('div');
                div.className = 'sdoh-item';
                div.innerHTML = `
                    <strong>${escapeHtml(item.summary || 'Recovery item')}</strong><br>
                    <span>Status: ${escapeHtml(item.status || 'upcoming')}</span> | 
                    <span>Severity: ${escapeHtml(item.severity || 'low')}</span> | 
                    <span>Priority: ${escapeHtml(item.priority || 'low')}</span>
                `;
                timeline.appendChild(div);
            });
        }
    }

    if (analyticsBlock) {
        if (analytics) {
            analyticsBlock.innerHTML = `
                <strong style="color:var(--cyan)">Interactions:</strong> ${analytics.total_interactions || 0}<br>
                <strong style="color:var(--cyan)">Ack rate:</strong> ${(analytics.reminder_acknowledgment_rate || 0).toFixed ? analytics.reminder_acknowledgment_rate.toFixed(3) : analytics.reminder_acknowledgment_rate || 0}<br>
                <strong style="color:var(--cyan)">Completion rate:</strong> ${(analytics.follow_up_completion_rate || 0).toFixed ? analytics.follow_up_completion_rate.toFixed(3) : analytics.follow_up_completion_rate || 0}<br>
                <strong style="color:var(--cyan)">Transport success:</strong> ${(analytics.transport_coordination_success_rate || 0).toFixed ? analytics.transport_coordination_success_rate.toFixed(3) : analytics.transport_coordination_success_rate || 0}<br>
                <strong style="color:var(--cyan)">Rescues:</strong> ${analytics.missed_follow_up_rescue_count || 0}${analytics.last_demo_case ? `<br><strong style="color:var(--highlight)">Demo:</strong> ${escapeHtml(analytics.last_demo_case)}` : ''}
            `;
        } else {
            analyticsBlock.textContent = 'No analytics yet...';
        }
    }

    if (analyticsNote) {
        analyticsNote.textContent = analytics && analytics.last_event ? 'updated just now' : 'live counters';
    }

    if (status) status.textContent = exportReady ? 'READY TO EXPORT' : 'VERIFICATION NEEDED';
    if (bar) bar.style.width = exportReady ? '100%' : '40%';
    if (exportFlag) exportFlag.textContent = exportReady ? 'approved items available' : 'awaiting approved items';
    if (guardrail) {
        guardrail.textContent = exportReady
            ? 'Approved continuity items can be downloaded locally as .ICS and PATIENT_PASSPORT.md.'
            : 'Exports stay draft-only until the confidence gate is satisfied.';
    }
    if (downloadIcsBtn) downloadIcsBtn.disabled = !exportReady;
    if (downloadPassportBtn) downloadPassportBtn.disabled = !exportReady;
    if (copySummaryBtn) copySummaryBtn.disabled = !bundle;

    panel.dataset.exportReady = exportReady ? 'true' : 'false';
    panel.dataset.icsContent = bundle?.ics_content || '';
    panel.dataset.passportMarkdown = bundle?.passport_markdown || '';
    panel.dataset.schemaNotes = bundle?.schema_notes || '';
}

async function sendToSdoh(text) {
    try {
        const res = await fetchWithAuth('/sdoh/chat', {
            method: 'POST',
            body: JSON.stringify({ content: text })
        });

        if (!res) return;

        const data = await res.json();

        if (data.score !== undefined) {
            window.currentUser.integrity_score = data.score;
            window.currentUser.insights = data.insights;
        }

        if (data.export_bundle) {
            saveSdohExportBundle(data.export_bundle);
            renderSdohPanel(data.export_bundle);
        } else if (data.analytics) {
            renderSdohPanel({
                export_ready: Boolean(data.export_ready),
                calendar_events: data.calendar_events || [],
                calendar_filename: data.calendar_filename,
                ics_content: data.ics_content,
                passport_filename: data.passport_filename,
                passport_markdown: data.passport_markdown,
                schema_notes: data.schema_notes,
                analytics: data.analytics,
            });
        }

        const container = document.getElementById('messages');
        const div = document.createElement('div');
        div.className = 'msg';
        div.style.borderLeftColor = 'var(--cyan)';
        const responseText = escapeHtml(data.response);
        const draftCard = data.draft_message ? `<div style="margin-top:8px; padding:8px; border:1px solid #0f4f57; background:rgba(0,255,255,0.04)"><strong style="color:var(--cyan)">DRAFT MESSAGE</strong><div style="margin-top:4px">${escapeHtml(data.draft_message)}</div></div>` : '';
        const verificationCard = data.verification_required ? '<div style="margin-top:8px; padding:6px 8px; border:1px solid #aa8800; color:#ffdd88; background:rgba(255,170,0,0.08)">Verification required before export.</div>' : '';
        const exportCard = data.export_bundle && data.export_bundle.export_ready ? '<div style="margin-top:8px; padding:6px 8px; border:1px solid var(--cyan); color:var(--cyan); background:rgba(0,255,255,0.06)">Local export ready.</div>' : '';
        const paymentDraft = data.payment_allocation_draft ? `<div style="margin-top:8px; padding:8px; border:1px solid #2b6cb0; background:rgba(59,130,246,0.08)"><strong style="color:#93c5fd">PAYMENT ALLOCATION</strong><div style="margin-top:4px">Status: ${escapeHtml(data.payment_allocation_draft.status || 'draft')}</div><div>Patient: ${escapeHtml(data.payment_allocation_draft.patient_alias || '')}</div><div>Account: ${escapeHtml(data.payment_allocation_draft.account_number || 'n/a')}</div><div>Invoice: ${escapeHtml(data.payment_allocation_draft.invoice_number || 'n/a')}</div><div>Amount: ${escapeHtml(data.payment_allocation_draft.amount || 'n/a')} ${escapeHtml(data.payment_allocation_draft.currency || '')}</div><div>Reference: ${escapeHtml(data.payment_allocation_draft.payment_reference || 'n/a')}</div></div>` : '';

        div.innerHTML = `
            <div style="margin-bottom:5px">
                <span class="msg-sender" style="color:var(--cyan)">SDOH NAVIGATOR:</span>
                <button class="tts-btn" style="float:right; margin-left:5px" data-text="${responseText}" onclick="startTTS(this)">🔊 LISTEN</button>
            </div>
            <div style="clear:both">${data.response}</div>
            ${verificationCard}
            ${draftCard}
            ${paymentDraft}
            ${exportCard}
            <span class="msg-time">Now</span>
        `;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    } catch (e) {
        console.error(e);
    }
}

async function loadSdohGreeting() {
    try {
        const res = await fetchWithAuth('/sdoh/greeting');
        if (!res) return;
        const data = await res.json();

        const container = document.getElementById('messages');
        container.innerHTML = '';
        const div = document.createElement('div');
        div.className = 'msg';
        div.style.borderLeftColor = 'var(--cyan)';

        const listenBtn = document.createElement('button');
        listenBtn.className = 'tts-btn';
        listenBtn.style.cssText = 'float:right; margin-left:5px';
        listenBtn.textContent = '🔊 LISTEN';
        listenBtn.setAttribute('data-text', data.greeting);
        listenBtn.onclick = function() { startTTS(this); };

        const greetingText = data.greeting
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');

        div.innerHTML = `
            <div style="margin-bottom:5px">
                <span class="msg-sender" style="color:var(--cyan)">SDOH NAVIGATOR:</span>
            </div>
            <div style="clear:both; margin:10px 0; white-space: pre-wrap; line-height:1.5">${greetingText}</div>
            <div style="margin-top:10px; overflow:hidden">
                <span class="msg-time" style="float:left">Now</span>
            </div>
        `;

        const buttonContainer = document.createElement('div');
        buttonContainer.style.marginBottom = '10px';
        buttonContainer.appendChild(listenBtn);
        div.insertBefore(buttonContainer, div.children[1]);

        container.appendChild(div);
    } catch (e) {
        console.error(e);
    }
}

async function loadPacsGreeting() {
    try {
        const res = await fetchWithAuth('/pacs/greet');
        if (!res) return;
        const data = await res.json();

        const container = document.getElementById('messages');
        if (!container) return;
        container.innerHTML = '';
        const div = document.createElement('div');
        div.className = 'msg';
        div.style.borderLeftColor = '#00ff44'; // Matrix/Terminal Green

        const greeting = data.greeting || "PACS CONTINUITY MENTOR READY. GENERAL PACS ADMIN HELP IS AVAILABLE NOW FOR ROUTING, WORKLISTS, ARCHIVE HEALTH, AND INTERFACE TRIAGE. USE BREAK-GLASS ONLY FOR PASSWORD RECOVERY OR VERIFIED EMERGENCY ACTIONS.";

        const listenBtn = document.createElement('button');
        listenBtn.className = 'tts-btn';
        listenBtn.style.cssText = 'float:right; margin-left:5px';
        listenBtn.textContent = '🔊 LISTEN';
        listenBtn.setAttribute('data-text', greeting);
        listenBtn.onclick = function() { startTTS(this); };

        const greetingText = greeting
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');

        div.innerHTML = `
            <div style="margin-bottom:5px">
                <span class="msg-sender" style="color:#00ff44">PACS CONTINUITY MENTOR:</span>
            </div>
            <div style="clear:both; margin:10px 0; white-space: pre-wrap; line-height:1.5; font-family: 'Courier New', monospace;">${greetingText}</div>
            <div style="margin-top:10px; overflow:hidden">
                <span class="msg-time" style="float:left">SYSTEM TIME: ${new Date().toLocaleTimeString()}</span>
            </div>
        `;

        const buttonContainer = document.createElement('div');
        buttonContainer.style.marginBottom = '10px';
        buttonContainer.appendChild(listenBtn);
        div.insertBefore(buttonContainer, div.children[1]);

        container.appendChild(div);
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
        const res = await fetchWithAuth(`/quest/greeting`);
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

function downloadSdohICS() {
    const panel = document.getElementById('sdoh-panel');
    if (!panel || panel.dataset.exportReady !== 'true') return;
    downloadTextFile(panel.dataset.icsContent, 'sdoh-followups.ics', 'text/calendar');
}

function downloadSdohPassport() {
    const panel = document.getElementById('sdoh-panel');
    if (!panel || panel.dataset.exportReady !== 'true') return;
    downloadTextFile(panel.dataset.passportMarkdown, 'PATIENT_PASSPORT.md', 'text/markdown');
}

async function copySdohSummary() {
    const panel = document.getElementById('sdoh-panel');
    if (!panel) return;
    const text = [panel.dataset.passportMarkdown || '', panel.dataset.schemaNotes || ''].filter(Boolean).join('\n\n');
    if (!text) return;
    try {
        await navigator.clipboard.writeText(text);
    } catch (e) {
        console.error('Copy failed:', e);
    }
}

function handleEnter(e) {
    if (e.key === 'Enter') sendMessage();
}

// Global Exports
window.sendMessage = sendMessage;
window.handleEnter = handleEnter;
window.deleteMessage = deleteMessage;
window.clearChatHistory = clearChatHistory;
window.loadMessages = loadMessages;
window.sendToSdoh = sendToSdoh;
window.sendToPacs = async function(text) {
    try {
        const res = await fetchWithAuth('/pacs/chat', {
            method: 'POST',
            body: JSON.stringify({ message: text })
        });
        const data = await res.json();
        
        if (data.status) document.getElementById('pacs-status-text').textContent = data.status;
           const progressValue = data.index_progress !== undefined && data.index_progress !== null ? data.index_progress : data.progress;
           if (progressValue !== undefined && progressValue !== null) {
               document.getElementById('pacs-bar').style.width = progressValue + '%';
        }
           if (data.index_step || data.current_step) {
               document.getElementById('pacs-recovery-step').textContent = data.index_step || data.current_step;
        }

        loadMessages(`pacs_${window.currentUser.user_id}`);
    } catch (e) {
        console.error(e);
    }
};
window.loadSdohGreeting = loadSdohGreeting;
window.loadPacsGreeting = loadPacsGreeting;
window.loadSdohExportBundle = loadSdohExportBundle;
window.renderSdohPanel = renderSdohPanel;
window.downloadSdohICS = downloadSdohICS;
window.downloadSdohPassport = downloadSdohPassport;
window.copySdohSummary = copySdohSummary;
