/* 🇿🇦 NAS Integration Core Module - South African Medical Imaging System */

// Global state management
window.NASIntegration = {
    isLoading: false,
    lastDiscoveryResults: null,
    lastResultType: null,
    config: {
        refreshInterval: 60000,
        statusInterval: 30000
    }
};

// Initialize page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🏥 NAS Medical Image Management System Loaded');
    initializePage();
});

// Page Initialization
function initializePage() {
    console.log('🔧 Initializing NAS Integration page...');
    
    // Check system status
    if (typeof checkOrthancStatus === 'function') {
        checkOrthancStatus();
    }
    if (typeof checkIndexStatus === 'function') {
        checkIndexStatus();
    }
    
    // Set up periodic status updates
    setInterval(() => {
        if (typeof checkOrthancStatus === 'function') {
            checkOrthancStatus();
        }
    }, window.NASIntegration.config.refreshInterval);
    
    setInterval(() => {
        if (typeof checkIndexStatus === 'function') {
            checkIndexStatus();
        }
    }, window.NASIntegration.config.statusInterval);
    
    // Initialize form values
    initializeFormDefaults();
    
    // Load network settings
    if (typeof loadNetworkSettings === 'function') {
        loadNetworkSettings();
    }

    // Load cached devices by default (shows known devices and offline IPs)
    if (typeof window.NASIntegration.network !== 'undefined' && typeof window.NASIntegration.network.loadCachedDevices === 'function') {
        window.NASIntegration.network.loadCachedDevices();
    }
    
    console.log('✅ NAS Integration initialization complete');
}

function initializeFormDefaults() {
    console.log('📋 Setting default form values...');
    
    // Orthanc connection defaults
    const orthancUrl = document.getElementById('orthancUrl');
    const orthancUsername = document.getElementById('orthancUsername');
    const orthancPassword = document.getElementById('orthancPassword');
    
    if (orthancUrl && !orthancUrl.value) orthancUrl.value = 'http://localhost:8042';
    if (orthancUsername && !orthancUsername.value) orthancUsername.value = 'orthanc';
    if (orthancPassword && !orthancPassword.value) orthancPassword.value = 'orthanc';
    
    // Network discovery defaults
    const startIp = document.getElementById('startIp');
    const endIp = document.getElementById('endIp');
    const timeoutMs = document.getElementById('timeoutMs');
    
    if (startIp && !startIp.value) startIp.value = '155.235.81.1';
    if (endIp && !endIp.value) endIp.value = '155.235.81.100';
    if (timeoutMs && !timeoutMs.value) timeoutMs.value = '2000';
}

// Global utility functions
function showLoading(show, message = 'Loading...') {
    window.NASIntegration.isLoading = show;
    const loadingElement = document.getElementById('loadingIndicator');
    const messageElement = document.getElementById('loadingMessage');
    
    if (loadingElement) {
        loadingElement.style.display = show ? 'block' : 'none';
    }
    
    if (messageElement && show) {
        messageElement.textContent = message;
    }
    
    // Disable/enable action buttons
    const actionButtons = document.querySelectorAll('.btn:not(.btn-secondary)');
    actionButtons.forEach(btn => {
        btn.disabled = show;
        if (show) {
            btn.classList.add('loading');
        } else {
            btn.classList.remove('loading');
        }
    });
}

function showMessage(message, type = 'info') {
    console.log(`📢 ${type.toUpperCase()}: ${message}`);
    
    const messageContainer = document.getElementById('messageContainer') || createMessageContainer();
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `alert alert-${type} message-item`;
    
    const icon = getMessageIcon(type);
    messageDiv.innerHTML = `
        <div class="message-content">
            <span class="message-icon">${icon}</span>
            <span class="message-text">${message}</span>
            <button class="message-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    
    messageContainer.appendChild(messageDiv);
    
    // Auto-remove after 5 seconds for non-error messages
    if (type !== 'error') {
        setTimeout(() => {
            if (messageDiv.parentElement) {
                messageDiv.remove();
            }
        }, 5000);
    }
}

function createMessageContainer() {
    const container = document.createElement('div');
    container.id = 'messageContainer';
    container.className = 'message-container';
    document.body.appendChild(container);
    return container;
}

function getMessageIcon(type) {
    const icons = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    };
    return icons[type] || 'ℹ️';
}

function clearMessages() {
    const messageContainer = document.getElementById('messageContainer');
    if (messageContainer) {
        messageContainer.innerHTML = '';
    }
}

// API helper function
async function makeAPIRequest(url, options = {}) {
    try {
        showLoading(true, `Connecting to ${url}...`);
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        const finalOptions = { ...defaultOptions, ...options };
        
        const response = await fetch(url, finalOptions);

        // Try to parse JSON only when the response looks like JSON
        const contentType = response.headers.get('content-type') || '';
        let data = null;

        if (contentType.includes('application/json')) {
            try {
                data = await response.json();
            } catch (err) {
                // JSON parse failed despite content-type; capture body as text for diagnostics
                const text = await response.text();
                throw new Error(`Failed to parse JSON response: ${err.message} - Response body starts with: ${text.slice(0,120)}`);
            }
        } else {
            // non-JSON response (likely HTML error page), capture a short snippet
            const text = await response.text();
            const snippet = text ? text.slice(0,200) : '<empty response>';
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText} - Server returned non-JSON response: ${snippet}`);
            }
            // If OK but not JSON, return the raw text inside an object
            return { success: true, raw: snippet };
        }

        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
        }

        return data;
    } catch (error) {
        console.error(`API request failed for ${url}:`, error);
        showMessage(`API Error: ${error.message}`, 'error');
        throw error;
    } finally {
        showLoading(false);
    }
}

// Storage for last successful results
function storeLastResults(key, data) {
    try {
        localStorage.setItem(`nas_${key}`, JSON.stringify(data));
    } catch (error) {
        console.warn('Failed to store results in localStorage:', error);
    }
}

function getLastResults(key) {
    try {
        const stored = localStorage.getItem(`nas_${key}`);
        return stored ? JSON.parse(stored) : null;
    } catch (error) {
        console.warn('Failed to retrieve results from localStorage:', error);
        return null;
    }
}

// Clear search form function
function clearSearchForm() {
    console.log('🔄 Clearing search form...');
    const searchForm = document.getElementById('patientSearchForm');
    if (searchForm) {
        searchForm.reset();
        const resultsDiv = document.getElementById('searchResults');
        if (resultsDiv) {
            resultsDiv.innerHTML = '';
        }
    }
}

// Export functions for other modules
window.NASIntegration.core = {
    showLoading,
    showMessage,
    clearMessages,
    makeAPIRequest,
    storeLastResults,
    getLastResults,
    clearSearchForm,
    getLastResultType: function() {
        return window.NASIntegration.lastResultType || 'enhanced_discovery';
    },
    setLastResultType: function(type) {
        window.NASIntegration.lastResultType = type;
    },
    storeLastResults: function(type, data) {
        window.NASIntegration.lastResultType = type;
        window.NASIntegration.lastDiscoveryResults = data;
    }
};

console.log('✅ NAS Core module loaded successfully');
