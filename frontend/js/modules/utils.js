// Utility Functions

// HTML Entity Escaping for TTS and Display
function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/'/g, '&#39;')
        .replace(/\n/g, ' '); // Collapse newlines for data attributes
}

// Get Location with GPS + IP Fallback
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
    try {
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
    // Cap at 99
    for (let level = 1; level < 100; level++) {
        if (getXPForLevel(level + 1) > xp) {
            return level;
        }
    }
    return 99;
}

// Global Exports
window.escapeHtml = escapeHtml;
window.getLocation = getLocation;
window.getXPForLevel = getXPForLevel;
window.getLevelAtXP = getLevelAtXP;
