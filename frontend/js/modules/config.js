// Configuration and Global State
const API_BASE = '/api/sdoh';
let currentUser = null;
let currentGroup = null;
let selectedLetterIdx = -1;
let aliasColors = {}; // {index: color}

// Check auth immediately
const token = localStorage.getItem('token');
if (!token) window.location.href = '/sdoh/index.html';
