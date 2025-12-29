// Forge Panel Logic

let showXPDetails = false;

function toggleXPDisplay() {
    showXPDetails = !showXPDetails;
    if (currentUser) {
        updateForgePanel(currentUser.integrity_score, currentUser.insights);
    }
}

function updateForgePanel(score, insights) {
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

function openInsightsModal() {
    const modal = document.getElementById('insights-modal');
    const list = document.getElementById('full-insights-list');
    const totalXpEl = document.getElementById('modal-total-xp');
    const totalInsightsEl = document.getElementById('modal-total-insights');
    const levelEl = document.getElementById('modal-level');
    
    if (!modal || !list || !currentUser) return;
    
    modal.classList.remove('hidden');
    list.innerHTML = '';
    
    const insights = currentUser.insights || [];
    const score = currentUser.integrity_score || 0;
    
    // Update Stats
    totalXpEl.textContent = score;
    totalInsightsEl.textContent = insights.length;
    levelEl.textContent = getLevelAtXP(score);
    
    if (insights.length === 0) {
        list.innerHTML = '<div style="text-align:center; padding:20px; color:#666">No insights recorded yet. Speak with The Forge to begin your journey.</div>';
        return;
    }
    
    // Render all insights (reversed)
    insights.slice().reverse().forEach(insight => {
        const div = document.createElement('div');
        div.style.padding = '10px';
        div.style.marginBottom = '10px';
        div.style.background = '#222';
        div.style.borderRadius = '5px';
        div.style.borderLeft = '3px solid #444';
        
        // Color code border
        if (insight.type === 'strength') div.style.borderLeftColor = '#00ff00';
        if (insight.type === 'flaw') div.style.borderLeftColor = '#ff4444';
        
        const dateStr = insight.date ? new Date(insight.date).toLocaleDateString() : 'Unknown Date';
        
        // Show XP if it exists (even if 0)
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
