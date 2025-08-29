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
