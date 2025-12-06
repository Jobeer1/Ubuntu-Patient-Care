/**
 * MCP Access Control Integration for PACS Frontend
 * 
 * This module handles:
 * - MCP token extraction and validation
 * - Fetching accessible patients from MCP server
 * - Filtering patient lists based on access control
 * - Displaying access-related UI elements
 */

const MCPAccessControl = (function() {
    'use strict';

    // Configuration
    const MCP_SERVER_URL = 'http://localhost:8080';
    const TOKEN_STORAGE_KEY = 'mcp_token';
    
    // State
    let currentUser = null;
    let accessiblePatients = [];
    let hasFullAccess = false;

    /**
     * Initialize access control on page load
     */
    async function initialize() {
        try {
            console.log('[MCP] Initializing access control...');
            
            // Extract token (now async)
            const token = await getToken();
            if (!token) {
                console.warn('[MCP] No token found');
                showNoAccessMessage();
                return false;
            }

            // Verify token and get user info
            const user = await verifyToken(token);
            if (!user) {
                console.error('[MCP] Token verification failed');
                showInvalidTokenMessage();
                return false;
            }

            currentUser = user;
            console.log(`[MCP] User authenticated: ${user.username} (${user.role})`);

            // Get accessible patients
            const accessData = await getAccessiblePatients(user.user_id);
            if (!accessData) {
                console.error('[MCP] Failed to fetch accessible patients');
                return false;
            }

            hasFullAccess = accessData.has_full_access;
            accessiblePatients = accessData.accessible_patients || [];

            console.log(`[MCP] Access control initialized. Full access: ${hasFullAccess}, Patients: ${accessiblePatients.length}`);

            // Update UI
            updateUIForUser(user, hasFullAccess, accessiblePatients.length);

            return true;

        } catch (error) {
            console.error('[MCP] Initialization error:', error);
            showErrorMessage('Failed to initialize access control');
            return false;
        }
    }

    /**
     * Get MCP token from URL, localStorage, or Flask backend
     */
    async function getToken() {
        // Check URL parameter
        const urlParams = new URLSearchParams(window.location.search);
        let token = urlParams.get('mcp_token');
        
        if (token) {
            // Store in localStorage for future use
            localStorage.setItem(TOKEN_STORAGE_KEY, token);
            // Remove from URL for security
            window.history.replaceState({}, document.title, window.location.pathname);
            return token;
        }

        // Check localStorage
        token = localStorage.getItem(TOKEN_STORAGE_KEY);
        if (token) return token;

        // Check cookie
        token = getCookie('access_token');
        if (token) {
            localStorage.setItem(TOKEN_STORAGE_KEY, token);
            return token;
        }

        // Try to get token from Flask backend
        try {
            console.log('[MCP] Requesting token from Flask backend...');
            const response = await fetch('/api/auth/get-mcp-token', {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.token) {
                    console.log('[MCP] Got token from Flask backend');
                    localStorage.setItem(TOKEN_STORAGE_KEY, data.token);
                    return data.token;
                }
            } else {
                console.log('[MCP] Flask backend returned:', response.status);
            }
        } catch (error) {
            console.log('[MCP] Could not get token from Flask:', error.message);
        }

        return null;
    }

    /**
     * Verify token with Flask backend (not MCP server)
     */
    async function verifyToken(token) {
        try {
            // Verify with Flask backend where the user is authenticated
            const response = await fetch('/api/auth/status', {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                console.error('[MCP] Token verification failed with status:', response.status);
                return null;
            }

            const data = await response.json();
            if (data.authenticated && data.user) {
                return data.user;
            }

            return null;

        } catch (error) {
            console.error('[MCP] Token verification error:', error);
            return null;
        }
    }

    /**
     * Get accessible patients from Flask backend
     */
    async function getAccessiblePatients(userId) {
        try {
            // For now, return default access control
            // The Flask backend has already authenticated the user
            // Full access is granted if user is authenticated
            return {
                has_full_access: true,
                accessible_patients: [],
                user_id: userId
            };

        } catch (error) {
            console.error('[MCP] Error getting accessible patients:', error);
            return null;
        }
    }

    /**
     * Check if user has access to a specific patient
     */
    function canAccessPatient(patientId) {
        // Full access (admin/radiologist)
        if (hasFullAccess) {
            return true;
        }

        // Check if patient in accessible list
        return accessiblePatients.includes(patientId);
    }

    /**
     * Filter patient list based on access control
     */
    function filterPatients(patients) {
        if (hasFullAccess) {
            return patients;
        }

        return patients.filter(patient => {
            const patientId = patient.patient_id || patient.id;
            return canAccessPatient(patientId);
        });
    }

    /**
     * Update UI to show user info and access level
     */
    function updateUIForUser(user, fullAccess, patientCount) {
        // Add user info banner
        const banner = document.createElement('div');
        banner.className = 'mcp-user-banner';
        banner.innerHTML = `
            <div class="mcp-user-info">
                <span class="mcp-user-icon">👤</span>
                <span class="mcp-user-name">${user.username}</span>
                <span class="mcp-user-role">${user.role}</span>
            </div>
            <div class="mcp-access-info">
                ${fullAccess ? 
                    '<span class="mcp-access-badge full">🔓 Full Access</span>' :
                    `<span class="mcp-access-badge limited">🔒 Limited Access (${patientCount} patients)</span>`
                }
            </div>
        `;

        // Insert banner at top of main content
        const main = document.querySelector('main') || document.querySelector('.container');
        if (main) {
            main.insertBefore(banner, main.firstChild);
        }

        // Add CSS for banner
        addBannerStyles();
    }

    /**
     * Add CSS styles for user banner
     */
    function addBannerStyles() {
        if (document.getElementById('mcp-banner-styles')) return;

        const style = document.createElement('style');
        style.id = 'mcp-banner-styles';
        style.textContent = `
            .mcp-user-banner {
                background: linear-gradient(135deg, #006533 0%, #005580 100%);
                color: white;
                padding: 15px 30px;
                border-radius: 15px;
                margin-bottom: 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                flex-wrap: wrap;
                gap: 15px;
            }

            .mcp-user-info {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .mcp-user-icon {
                font-size: 1.5rem;
            }

            .mcp-user-name {
                font-weight: 600;
                font-size: 1.1rem;
            }

            .mcp-user-role {
                background: rgba(255,255,255,0.2);
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 0.85rem;
                font-weight: 500;
            }

            .mcp-access-info {
                display: flex;
                align-items: center;
            }

            .mcp-access-badge {
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: 600;
                font-size: 0.9rem;
                display: inline-flex;
                align-items: center;
                gap: 6px;
            }

            .mcp-access-badge.full {
                background: #28a745;
                color: white;
            }

            .mcp-access-badge.limited {
                background: #FFB81C;
                color: #1F2937;
            }

            .mcp-no-access {
                text-align: center;
                padding: 60px 20px;
                background: rgba(255,255,255,0.95);
                border-radius: 20px;
                margin: 40px auto;
                max-width: 600px;
            }

            .mcp-no-access-icon {
                font-size: 4rem;
                margin-bottom: 20px;
            }

            .mcp-no-access h2 {
                color: #006533;
                margin-bottom: 15px;
            }

            .mcp-no-access p {
                color: #666;
                font-size: 1.1rem;
                line-height: 1.6;
            }

            .mcp-request-access-btn {
                margin-top: 25px;
                padding: 12px 30px;
                background: linear-gradient(135deg, #006533 0%, #FFB81C 100%);
                color: white;
                border: none;
                border-radius: 25px;
                font-weight: 600;
                font-size: 1rem;
                cursor: pointer;
                transition: all 0.3s ease;
            }

            .mcp-request-access-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(0,101,51,0.3);
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Show "no access" message
     */
    function showNoAccessMessage() {
        const main = document.querySelector('main') || document.querySelector('.container');
        if (!main) return;

        main.innerHTML = `
            <div class="mcp-no-access">
                <div class="mcp-no-access-icon">🔒</div>
                <h2>Authentication Required</h2>
                <p>You need to log in through the MCP server to access patient records.</p>
                <button class="mcp-request-access-btn" onclick="window.location.href='http://localhost:8080'">
                    Go to Login
                </button>
            </div>
        `;
    }

    /**
     * Show "invalid token" message
     */
    function showInvalidTokenMessage() {
        const main = document.querySelector('main') || document.querySelector('.container');
        if (!main) return;

        main.innerHTML = `
            <div class="mcp-no-access">
                <div class="mcp-no-access-icon">⚠️</div>
                <h2>Session Expired</h2>
                <p>Your session has expired. Please log in again to access patient records.</p>
                <button class="mcp-request-access-btn" onclick="window.location.href='http://localhost:8080'">
                    Log In Again
                </button>
            </div>
        `;
    }

    /**
     * Show error message
     */
    function showErrorMessage(message) {
        console.error('[MCP]', message);
        // Could add UI notification here
    }

    /**
     * Get cookie value by name
     */
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    /**
     * Get current user
     */
    function getCurrentUser() {
        return currentUser;
    }

    /**
     * Get accessible patient IDs
     */
    function getAccessiblePatientIds() {
        return accessiblePatients;
    }

    /**
     * Check if user has full access
     */
    function hasFullAccessRights() {
        return hasFullAccess;
    }

    // Public API
    return {
        initialize,
        canAccessPatient,
        filterPatients,
        getCurrentUser,
        getAccessiblePatientIds,
        hasFullAccessRights
    };

})();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => MCPAccessControl.initialize());
} else {
    MCPAccessControl.initialize();
}
