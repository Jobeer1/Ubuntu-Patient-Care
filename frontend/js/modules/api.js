// API Wrappers

async function fetchWithAuth(endpoint, options = {}) {
    const isFormData = options.body instanceof FormData;
    const headers = {
        'Authorization': `Bearer ${window.token}`,
        ...options.headers
    };

    if (!isFormData) {
        headers['Content-Type'] = 'application/json';
    }
    
    const res = await fetch(`${window.API_BASE}${endpoint}`, {
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

window.fetchWithAuth = fetchWithAuth;
window.logout = logout;
