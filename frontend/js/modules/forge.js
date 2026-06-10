// Forge Panel Logic

let showXPDetails = false;

window.toggleXPDisplay = function() {
    showXPDetails = !showXPDetails;
    if (window.currentUser) {
        window.updateForgePanel(window.currentUser.integrity_score, window.currentUser.insights);
    }
}

window.updateForgePanel = function(score, insights) {
    const bar = document.getElementById('integrity-bar');
    const text = document.getElementById('integrity-score-text');
    const list = document.getElementById('insights-list');
    
    if (!bar || !text || !list) return;

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
    barContainer.onclick = window.toggleXPDisplay;
    barContainer.style.cursor = 'pointer';
    barContainer.title = "Click to toggle XP view";
    
    text.onclick = window.toggleXPDisplay;
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
            
            // Check type for color
            let color = '#aaa'; // default gray
            if (insight.type === 'strength') color = '#00ff00'; // Green
            if (insight.type === 'flaw') color = '#ff4444'; // Red
            
            const xpText = insight.xp ? `<span style="color: #4caf50; font-weight: bold; font-size: 0.9em; margin-left: 5px;">(+${insight.xp} XP)</span>` : '';
            
            div.innerHTML = `<span style="color:${color}">•</span> ${insight.text} ${xpText}`;
            list.appendChild(div);
        });
    } else {
        list.innerHTML = '<div style="font-style:italic; color:#666">No insights yet...</div>';
    }
}

function openInsightsModal(insights) {
    const modal = document.getElementById('insights-modal');
    const list = document.getElementById('full-insights-list');
    if (!modal || !list) {
        console.error("Insights modal or list not found", { modal, list });
        return;
    }

    modal.classList.remove('hidden');
    list.innerHTML = '';

    const activeInsights = insights || (typeof window.currentUser !== 'undefined' ? window.currentUser.insights : []);
    
    // Update summary stats in modal
    const totalXpEl = document.getElementById('modal-total-xp');
    const totalInsightsEl = document.getElementById('modal-total-insights');
    const levelEl = document.getElementById('modal-level');
    
    if (window.currentUser) {
        if (totalXpEl) totalXpEl.textContent = window.currentUser.integrity_score || 0;
        if (totalInsightsEl) totalInsightsEl.textContent = Array.isArray(activeInsights) ? activeInsights.length : 0;
        if (levelEl) {
            const score = window.currentUser.integrity_score || 0;
             // RuneScape-ish leveling or simple 100xp per level
            levelEl.textContent = Math.floor(score / 100) + 1;
        }
    }

    if (!activeInsights || !Array.isArray(activeInsights) || activeInsights.length === 0) {
        list.innerHTML = '<div style="text-align:center; color:#666; padding:20px">No insights recorded yet.</div>';
        return;
    }

    activeInsights.slice().reverse().forEach(insight => {
        const div = document.createElement('div');
        div.className = 'insight-card';
        div.style.background = '#222';
        div.style.border = '1px solid #444';
        div.style.padding = '10px';
        div.style.marginBottom = '10px';
        div.style.borderRadius = '5px';

        const dateStr = insight.created_at ? new Date(insight.created_at).toLocaleDateString() : 'N/A';
        
        let xpText = '';
        if (insight.xp !== undefined && insight.xp !== null) {
             const xpVal = parseInt(insight.xp);
             const xpColor = xpVal > 0 ? '#4caf50' : '#666';
             xpText = `<span style="color: ${xpColor}; font-weight: bold; float: right;">${xpVal > 0 ? '+' : ''}${xpVal} XP</span>`;
        }
        
        // Trigger Message Context
        let triggerContext = '';
        if (insight.trigger_msg) {
            triggerContext = `
                <div style="margin-top:5px; padding:5px; background:#333; border-radius:3px; font-size:10px; color:#aaa; font-style:italic;">
                    <span style="color:#666">Triggered by:</span> "${insight.trigger_msg}"
                </div>
            `;
        }
        
        div.innerHTML = `
            <div style="font-size:10px; color:#888; margin-bottom:5px; display:flex; justify-content:space-between">
                <span>${dateStr} • ${insight.type ? insight.type.toUpperCase() : 'GENERAL'}</span>
                ${xpText}
            </div>
            <div style="color:#ddd; line-height:1.4">${insight.text}</div>
            ${triggerContext}
        `;
        list.appendChild(div);
    });
}

function closeInsightsModal() {
    const modal = document.getElementById('insights-modal');
    if (modal) modal.classList.add('hidden');
}

// Global Exports
window.openInsightsModal = openInsightsModal;
window.closeInsightsModal = closeInsightsModal;
// window.updateForgePanel is already set at declaration
window.updateQuestPanel = updateQuestPanel;

function updateQuestPanel(score, insights, inventory, activeQuestId) {
    const levelEl = document.getElementById('quest-level');
    const xpText = document.getElementById('quest-xp-text');
    const bar = document.getElementById('quest-bar');
    const activeQuestInfo = document.getElementById('active-quest-info');
    const inventoryList = document.getElementById('quest-inventory-list');
    const questInsightsList = document.getElementById('quest-insights-list');
    const endQuestBtn = document.getElementById('end-quest-btn');

    if (!levelEl || !xpText || !bar) return;

    // XP Logic (Same as Forge for now)
    const currentLevel = window.getLevelAtXP ? window.getLevelAtXP(score) : 1;
    const currentLevelXP = window.getXPForLevel ? window.getXPForLevel(currentLevel) : 0;
    const nextLevelXP = window.getXPForLevel ? window.getXPForLevel(currentLevel + 1) : 100;
    
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

    levelEl.textContent = currentLevel;
    xpText.textContent = Math.floor(xpInLevel) + " / " + Math.floor(xpNeeded) + " XP";
    bar.style.width = progressPercent + "%";

    // Active Quest
    if (activeQuestId) {
        activeQuestInfo.innerHTML = '<div style="color:#ffaa00; font-weight:bold">' + activeQuestId + '</div>';
        if (endQuestBtn) endQuestBtn.classList.remove('hidden');
        
        // Show publish button if there's a quest log
        const publishBtn = document.getElementById('publish-story-btn');
        if (publishBtn) {
            if (window.currentUser && window.currentUser.quest_progress && window.currentUser.quest_progress.quest_log) {
                publishBtn.classList.remove('hidden');
            } else {
                publishBtn.classList.add('hidden');
            }
        }
    } else {
        activeQuestInfo.innerHTML = '<div style="font-style:italic; color:#666">No active quest...</div>';
        if (endQuestBtn) endQuestBtn.classList.add('hidden');
        const publishBtn = document.getElementById('publish-story-btn');
        if (publishBtn) publishBtn.classList.add('hidden');
    }

    // Inventory
    if (inventoryList) {
        inventoryList.innerHTML = '';
        if (inventory && inventory.length > 0) {
            inventory.forEach(item => {
                const div = document.createElement('div');
                div.style.color = '#ccc';
                div.textContent = '• ' + item;
                inventoryList.appendChild(div);
            });
        } else {
            inventoryList.innerHTML = '<div style="font-style:italic; color:#666">Empty...</div>';
        }
    }

    // Quest Logs (Insights)
    if (questInsightsList) {
        questInsightsList.innerHTML = '';
        if (insights && insights.length > 0) {
            insights.slice().reverse().slice(0, 5).forEach(insight => {
                const div = document.createElement('div');
                div.style.marginBottom = '5px';
                div.style.paddingBottom = '5px';
                div.style.borderBottom = '1px solid #333';
                div.style.fontSize = '10px';
                div.style.color = '#aaa';
                div.textContent = '• ' + insight.text;
                questInsightsList.appendChild(div);
            });
        } else {
            questInsightsList.innerHTML = '<div style="font-style:italic; color:#666">No quest logs yet...</div>';
        }
    }
}
