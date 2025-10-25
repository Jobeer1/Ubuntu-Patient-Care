/**
 * Tab Manager Module
 * Handles tab switching and state management
 */

/**
 * Switch to specified tab
 */
function switchTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        content.classList.remove('active');
    });

    // Remove active class from all buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.classList.remove('active');
    });

    // Show selected tab content
    const activeContent = document.getElementById(tabName + 'Content');
    if (activeContent) {
        activeContent.classList.add('active');
    }

    // Add active class to clicked button
    event.target.classList.add('active');

    // Load data for specific tabs
    loadTabData(tabName);
}

/**
 * Load data when tab is activated
 */
function loadTabData(tabName) {
    switch(tabName) {
        case 'users':
            loadUsers();
            break;
        case 'access':
            loadAccessControl();
            break;
        case 'roles':
            loadRoles();
            break;
        case 'statistics':
            loadStatistics();
            break;
    }
}

/**
 * Initialize tabs on page load
 */
function initializeTabs() {
    // Set up tab button listeners
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const tabName = this.getAttribute('data-tab');
            switchTab(tabName);
        });
    });

    // Activate first tab by default
    const firstButton = document.querySelector('.tab-button');
    if (firstButton) {
        firstButton.classList.add('active');
        const firstTab = firstButton.getAttribute('data-tab');
        const firstContent = document.getElementById(firstTab + 'Content');
        if (firstContent) {
            firstContent.classList.add('active');
        }
        loadTabData(firstTab);
    }
}

/**
 * Load statistics data
 */
async function loadStatistics() {
    try {
        const stats = await apiRequest('/api/statistics');
        
        // Update statistics cards
        document.getElementById('totalUsers').textContent = stats.total_users || 0;
        document.getElementById('activeUsers').textContent = stats.active_users || 0;
        document.getElementById('totalRoles').textContent = stats.total_roles || 0;
        document.getElementById('totalPermissions').textContent = stats.total_permissions || 0;
        
        // Check all modules
        checkAllModules();
    } catch (error) {
        console.error('Error loading statistics:', error);
        showAlert('Failed to load statistics', 'error');
    }
}

/**
 * Initialize scroll behavior for tabs
 */
function initializeTabScrolling() {
    const tabContainer = document.querySelector('.tab-buttons');
    if (tabContainer) {
        // Add smooth scrolling
        tabContainer.addEventListener('wheel', (e) => {
            if (e.deltaY !== 0) {
                e.preventDefault();
                tabContainer.scrollLeft += e.deltaY;
            }
        });
    }
}

// Initialize on document ready
document.addEventListener('DOMContentLoaded', function() {
    initializeTabs();
    initializeTabScrolling();
});
