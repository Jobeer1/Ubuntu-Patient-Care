/**
 * UI Utilities Module
 * Shared functions for alerts, modals, and common operations
 */

const API_BASE = 'http://localhost:8080';

/**
 * Get cookie value by name
 */
function getCookie(name) {
    const nameEQ = name + "=";
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
        let c = cookies[i].trim();
        if (c.indexOf(nameEQ) === 0) {
            return c.substring(nameEQ.length);
        }
    }
    return null;
}

/**
 * Show alert/notification
 */
function showAlert(message, type = 'success', duration = 5000) {
    const alertContainer = document.getElementById('alertContainer');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    alert.style.marginBottom = '10px';
    
    alertContainer.appendChild(alert);
    
    setTimeout(() => {
        alert.fadeOut = true;
        alert.style.opacity = '0';
        alert.style.transition = 'opacity 0.3s';
        setTimeout(() => alert.remove(), 300);
    }, duration);
}

/**
 * Make API request with error handling
 */
async function apiRequest(endpoint, options = {}) {
    const defaultHeaders = {
        'Authorization': `Bearer ${getCookie('access_token')}`,
        'Content-Type': 'application/json'
    };

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers: {
                ...defaultHeaders,
                ...(options.headers || {})
            }
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        throw error;
    }
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

/**
 * Trim and validate text input
 */
function validateInput(value, minLength = 1, maxLength = 255) {
    const trimmed = value.trim();
    if (trimmed.length < minLength) {
        throw new Error(`Minimum ${minLength} characters required`);
    }
    if (trimmed.length > maxLength) {
        throw new Error(`Maximum ${maxLength} characters allowed`);
    }
    return trimmed;
}

/**
 * Validate email format
 */
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!re.test(email)) {
        throw new Error('Invalid email format');
    }
    return email.toLowerCase();
}

/**
 * Clear form fields
 */
function clearForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.reset();
    }
}

/**
 * Open modal
 */
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

/**
 * Close modal
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        clearForm(modalId.replace('Modal', 'Form'));
    }
}

/**
 * Filter array by search term
 */
function filterArray(array, searchTerm, fields = []) {
    if (!searchTerm.trim()) return array;
    
    const term = searchTerm.toLowerCase();
    return array.filter(item => {
        return fields.some(field => {
            const value = item[field];
            return value && value.toString().toLowerCase().includes(term);
        });
    });
}

/**
 * Confirm action with dialog
 */
function confirmAction(message) {
    return confirm(message);
}

/**
 * Module status check
 */
async function checkModule(module) {
    const dot = document.getElementById('dot-' + module.id);
    const statusEl = document.getElementById('status-' + module.id);
    
    try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 2500);
        
        const res = await fetch(module.url, {
            method: 'GET',
            mode: 'no-cors',
            signal: controller.signal
        });
        
        clearTimeout(timeout);
        
        dot.classList.remove('module-offline');
        dot.classList.add('module-online');
        if (statusEl) statusEl.textContent = 'Online';
    } catch (err) {
        dot.classList.remove('module-online');
        dot.classList.add('module-offline');
        if (statusEl) statusEl.textContent = 'Offline';
    }
}

/**
 * Check all modules
 */
function checkAllModules() {
    const MODULES = [
        { id: 'dictation', url: 'http://localhost:5443' },
        { id: 'pacs', url: 'http://localhost:5000' },
        { id: 'ris', url: 'http://localhost:3000' },
        { id: 'billing', url: 'http://localhost:3000' }
    ];

    MODULES.forEach(m => checkModule(m));
}
