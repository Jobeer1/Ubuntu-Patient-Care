// Configuration and Global State
window.API_BASE = '/api/sdoh';
window.currentUser = null;
window.currentGroup = null;
window.selectedLetterIdx = -1;
window.aliasColors = {}; // {index: color}

// Check auth immediately
window.token = localStorage.getItem('token');
if (!window.token) window.location.href = '/sdoh/index.html';
