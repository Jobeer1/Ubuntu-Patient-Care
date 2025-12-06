/* Dashboard JavaScript - South African Medical Imaging System */

// Handle logout functionality
async function logout() {
    try {
        const response = await fetch('/api/auth/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            window.location.href = '/login';
        } else {
            console.error('Logout failed');
            // Force redirect anyway for security
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Logout error:', error);
        // Force redirect anyway for security
        window.location.href = '/login';
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if user is authenticated
    checkAuthStatus();
    
    // Update last activity timestamp
    updateLastActivity();
    
    // Set up periodic activity check
    setInterval(updateLastActivity, 60000); // Every minute
});

// Check authentication status
async function checkAuthStatus() {
    try {
        const response = await fetch('/api/auth/status');
        const data = await response.json();
        
        if (!data.authenticated) {
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        // Don't redirect on network errors, user might be offline
    }
}

// Update last activity timestamp
function updateLastActivity() {
    try {
        fetch('/api/auth/activity', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
    } catch (error) {
        console.error('Activity update failed:', error);
    }
}

// Add click handlers for navigation
function initializeNavigation() {
    const navLinks = document.querySelectorAll('.card-btn');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Add loading state
            this.style.opacity = '0.7';
            this.textContent = '⏳ Loading...';
        });
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initializeNavigation);


// ============================================================================
// SSO Admin Control Functions
// ============================================================================

let currentSSOStatus = true;

// Load SSO status on page load
async function loadSSOStatus() {
    try {
        const response = await fetch('/api/auth/sso/status');
        const data = await response.json();
        
        currentSSOStatus = data.enabled;
        updateSSOUI(data.enabled);
    } catch (error) {
        console.error('Failed to load SSO status:', error);
        showNotification('Failed to load SSO status', 'error');
    }
}

// Update SSO UI elements
function updateSSOUI(enabled) {
    const statusText = document.getElementById('ssoStatusText');
    const statusBadge = document.getElementById('ssoStatusBadge');
    const toggleBtn = document.getElementById('ssoToggleBtn');
    const toggleBtnText = document.getElementById('ssoToggleBtnText');
    
    if (!statusText || !statusBadge || !toggleBtn || !toggleBtnText) {
        return; // Elements don't exist (user is not admin)
    }
    
    if (enabled) {
        statusText.textContent = 'SSO Authentication: ';
        statusBadge.textContent = '🟢 Enabled';
        statusBadge.className = 'status-badge enabled';
        toggleBtn.className = 'sso-toggle-btn disable';
        toggleBtnText.textContent = '🔒 Disable SSO';
    } else {
        statusText.textContent = 'SSO Authentication: ';
        statusBadge.textContent = '🔴 Disabled';
        statusBadge.className = 'status-badge disabled';
        toggleBtn.className = 'sso-toggle-btn enable';
        toggleBtnText.textContent = '🔓 Enable SSO';
    }
}

// Toggle SSO status
async function toggleSSO() {
    const toggleBtn = document.getElementById('ssoToggleBtn');
    const toggleBtnText = document.getElementById('ssoToggleBtnText');
    
    if (!toggleBtn || !toggleBtnText) return;
    
    // Disable button during request
    toggleBtn.disabled = true;
    const originalText = toggleBtnText.textContent;
    toggleBtnText.textContent = '⏳ Processing...';
    
    try {
        const newStatus = !currentSSOStatus;
        
        const response = await fetch('/api/auth/sso/toggle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ enabled: newStatus })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            currentSSOStatus = newStatus;
            updateSSOUI(newStatus);
            showNotification(
                `SSO ${newStatus ? 'enabled' : 'disabled'} successfully`,
                'success'
            );
        } else {
            throw new Error(data.error || 'Failed to toggle SSO');
        }
    } catch (error) {
        console.error('Failed to toggle SSO:', error);
        showNotification(error.message || 'Failed to toggle SSO', 'error');
        toggleBtnText.textContent = originalText;
    } finally {
        toggleBtn.disabled = false;
    }
}

// Show notification message
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        border-radius: 8px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        z-index: 10000;
        font-weight: 600;
        animation: slideIn 0.3s ease;
    `;
    
    if (type === 'success') {
        notification.style.background = '#d4edda';
        notification.style.color = '#155724';
        notification.style.borderLeft = '4px solid #28a745';
    } else if (type === 'error') {
        notification.style.background = '#f8d7da';
        notification.style.color = '#721c24';
        notification.style.borderLeft = '4px solid #dc3545';
    } else {
        notification.style.background = '#d1ecf1';
        notification.style.color = '#0c5460';
        notification.style.borderLeft = '4px solid #17a2b8';
    }
    
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Add CSS animation for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Initialize SSO controls when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Check if SSO control elements exist (admin only)
    if (document.getElementById('ssoToggleBtn')) {
        loadSSOStatus();
    }
});
