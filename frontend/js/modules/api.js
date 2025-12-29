// API Wrappers

async function fetchWithAuth(endpoint, options = {}) {
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    const res = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers
    });
    
    if (res.status === 401) {
        logout();
        return null;
    }
    
    return res;
}

async function logout() {
    localStorage.removeItem('token');
    window.location.href = '/sdoh/index.html';
}
