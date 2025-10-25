/**
 * User Management Module
 * Handles all user CRUD and display operations
 */

let editingUserId = null;
let currentUsers = [];
const API_BASE = 'http://localhost:8080';

/**
 * Load all users
 */
async function loadUsers() {
    try {
        const users = await apiRequest('/users');
        currentUsers = users;
        
        // Update statistics
        updateUserStats(users);
        
        // Render table
        renderUsersTable(users);
    } catch (error) {
        console.error('Error loading users:', error);
        showAlert('Failed to load users: ' + error.message, 'error');
    }
}

/**
 * Update user statistics
 */
function updateUserStats(users) {
    document.getElementById('totalUsers').textContent = users.length;
    document.getElementById('activeUsers').textContent = users.filter(u => u.active).length;
    document.getElementById('radiologists').textContent = users.filter(u => u.role === 'Radiologist').length;
    document.getElementById('referringDoctors').textContent = users.filter(u => u.role === 'Referring Doctor').length;
}

/**
 * Render users table
 */
function renderUsersTable(users) {
    const tbody = document.getElementById('usersTableBody');
    
    if (users.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    <div>No users found</div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = users.map(user => `
        <tr>
            <td><strong>${escapeHtml(user.name)}</strong></td>
            <td>${escapeHtml(user.email)}</td>
            <td><span class="badge badge-${user.role.toLowerCase().replace(' ', '-')}">${escapeHtml(user.role)}</span></td>
            <td>${user.hpcsa_number ? escapeHtml(user.hpcsa_number) : '-'}</td>
            <td><span class="badge badge-${user.active ? 'active' : 'inactive'}">${user.active ? 'Active' : 'Inactive'}</span></td>
            <td>${user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}</td>
            <td>
                <button class="btn btn-primary btn-small" onclick="editUser(${user.id})">Edit</button>
                <button class="btn btn-secondary btn-small" onclick="viewUserAudit(${user.id})">Audit</button>
            </td>
        </tr>
    `).join('');
}

/**
 * Filter users by search term
 */
function filterUsers() {
    const search = document.getElementById('userSearch').value.toLowerCase();
    const filtered = currentUsers.filter(user => 
        user.name.toLowerCase().includes(search) || 
        user.email.toLowerCase().includes(search)
    );
    renderUsersTable(filtered);
}

/**
 * Open add user modal
 */
function openAddUserModal() {
    editingUserId = null;
    document.getElementById('modalTitle').textContent = 'Add New User';
    clearForm('userForm');
    openModal('userModal');
}

/**
 * Close user modal
 */
function closeUserModal() {
    closeModal('userModal');
}

/**
 * Edit user
 */
async function editUser(userId) {
    try {
        const user = await apiRequest(`/users/${userId}`);
        
        editingUserId = userId;
        document.getElementById('modalTitle').textContent = 'Edit User';
        document.getElementById('userEmail').value = user.email;
        document.getElementById('userName').value = user.name;
        document.getElementById('userRole').value = user.role;
        document.getElementById('userHPCSA').value = user.hpcsa_number || '';
        document.getElementById('userLanguage').value = user.language_preference || 'en-ZA';
        
        openModal('userModal');
    } catch (error) {
        console.error('Error loading user:', error);
        showAlert('Failed to load user: ' + error.message, 'error');
    }
}

/**
 * Save user
 */
async function saveUser(event) {
    event.preventDefault();
    
    try {
        const userData = {
            email: validateEmail(document.getElementById('userEmail').value),
            name: validateInput(document.getElementById('userName').value, 1, 100),
            role: document.getElementById('userRole').value
        };
        
        let response;
        if (editingUserId) {
            // Update existing user
            response = await fetch(`${API_BASE}/users/${editingUserId}`, {
                method: 'PUT',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getCookie('access_token')}`
                },
                body: JSON.stringify({ role: userData.role })
            });
        } else {
            // Create new user
            response = await fetch(`${API_BASE}/users`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getCookie('access_token')}`
                },
                body: JSON.stringify(userData)
            });
        }
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save user');
        }
        
        const message = editingUserId 
            ? 'User updated successfully!' 
            : 'User created successfully!';
        
        showAlert(message, 'success');
        closeUserModal();
        loadUsers();
    } catch (error) {
        console.error('Error saving user:', error);
        showAlert('Error: ' + error.message, 'error');
    }
}

/**
 * View user audit logs
 */
async function viewUserAudit(userId) {
    try {
        const logs = await apiRequest(`/audit/logs?user_id=${userId}&limit=50`);
        
        // Create or update audit modal
        let auditModal = document.getElementById('auditModal');
        if (!auditModal) {
            auditModal = document.createElement('div');
            auditModal.id = 'auditModal';
            auditModal.className = 'modal active';
            document.body.appendChild(auditModal);
        }
        
        renderAuditLogs(logs);
        openModal('auditModal');
    } catch (error) {
        console.error('Error loading audit logs:', error);
        showAlert('Failed to load audit logs: ' + error.message, 'error');
    }
}

/**
 * Render audit logs
 */
function renderAuditLogs(logs) {
    const container = document.getElementById('auditLogsContainer');
    if (!container) return;
    
    if (logs.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #999;">No audit logs found</p>';
        return;
    }
    
    container.innerHTML = logs.map(log => `
        <div style="padding: 10px; border-bottom: 1px solid #eee;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>${escapeHtml(log.action)}</strong>
                    <span style="color: #666; font-size: 12px;"> on ${escapeHtml(log.resource || 'N/A')}</span>
                </div>
                <span style="color: #999; font-size: 12px;">
                    ${new Date(log.timestamp).toLocaleString()}
                </span>
            </div>
            <div style="font-size: 12px; color: #999; margin-top: 5px;">
                IP: ${escapeHtml(log.ip_address || 'N/A')} | 
                Status: <span style="color: ${log.success ? '#27ae60' : '#e74c3c'};">
                    ${log.success ? '✓ Success' : '✗ Failed'}
                </span>
            </div>
        </div>
    `).join('');
}

/**
 * Delete user
 */
async function deleteUser(userId) {
    if (!confirmAction('Are you sure you want to delete this user? This action cannot be undone.')) {
        return;
    }

    try {
        await apiRequest(`/users/${userId}`, {
            method: 'DELETE'
        });

        showAlert('User deleted successfully!', 'success');
        loadUsers();
    } catch (error) {
        console.error('Error deleting user:', error);
        showAlert(`Error: ${error.message}`, 'error');
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Initialize on module load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadUsers);
} else {
    loadUsers();
}
