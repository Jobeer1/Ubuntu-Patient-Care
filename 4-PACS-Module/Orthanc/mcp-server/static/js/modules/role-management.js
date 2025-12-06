/**
 * Role Management Module
 * Handles all role CRUD operations
 */

let editingRoleName = null;
const API_BASE = 'http://localhost:8080';

/**
 * Open create role modal
 */
function openCreateRoleModal() {
    editingRoleName = null;
    document.getElementById('roleModalTitle').textContent = 'Create New Role';
    document.getElementById('roleName').value = '';
    document.getElementById('roleDescription').value = '';
    document.querySelectorAll('.rolePermission').forEach(cb => cb.checked = false);
    openModal('roleModal');
}

/**
 * Close role modal
 */
function closeRoleModal() {
    closeModal('roleModal');
}

/**
 * Save role (create or update)
 */
async function saveRole(event) {
    event.preventDefault();
    
    try {
        const roleName = validateInput(document.getElementById('roleName').value, 1, 50);
        const description = document.getElementById('roleDescription').value.trim();

        // Collect permissions
        const permissions = {};
        document.querySelectorAll('.rolePermission').forEach(cb => {
            permissions[cb.name] = cb.checked;
        });

        const method = editingRoleName ? 'PUT' : 'POST';
        const url = editingRoleName 
            ? `${API_BASE}/roles/${encodeURIComponent(editingRoleName)}`
            : `${API_BASE}/roles`;

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getCookie('access_token')}`
            },
            body: JSON.stringify({
                name: roleName,
                description: description,
                modules: Object.keys(permissions).filter(k => permissions[k])
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save role');
        }

        const message = editingRoleName 
            ? 'Role updated successfully!' 
            : 'Role created successfully!';
        
        showAlert(message, 'success');
        closeRoleModal();
        loadRoles();
    } catch (error) {
        console.error('Error saving role:', error);
        showAlert(`Error: ${error.message}`, 'error');
    }
}

/**
 * Load all roles
 */
async function loadRoles() {
    try {
        const roles = await apiRequest('/roles');
        renderRolesContainer(roles);
    } catch (error) {
        console.error('Error loading roles:', error);
        showAlert('Failed to load roles', 'error');
    }
}

/**
 * Render roles in container
 */
function renderRolesContainer(roles) {
    const container = document.getElementById('rolesContainer');
    
    if (!roles || roles.length === 0) {
        container.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: #999; padding: 40px;">No roles found. Create one to get started.</p>';
        return;
    }

    container.innerHTML = roles.map(role => `
        <div class="role-card" style="display: flex; flex-direction: column; padding: 20px; border: 2px solid #e0e0e0; border-radius: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                <div>
                    <h3 style="color: #006533; margin: 0; font-size: 18px;">${escapeHtml(role.name)}</h3>
                    ${role.description ? `<p style="color: #666; margin: 5px 0 0 0; font-size: 13px;">${escapeHtml(role.description)}</p>` : ''}
                </div>
                <div style="display: flex; gap: 5px;">
                    <button onclick="editRole('${escapeHtml(role.name)}')" style="background: #FFB81C; border: none; border-radius: 4px; padding: 6px 12px; cursor: pointer; font-size: 12px; color: white; font-weight: bold;">✏️ Edit</button>
                    <button onclick="deleteRole('${escapeHtml(role.name)}')" style="background: #dc3545; border: none; border-radius: 4px; padding: 6px 12px; cursor: pointer; font-size: 12px; color: white; font-weight: bold;">🗑️ Delete</button>
                </div>
            </div>
            
            <div style="flex: 1;">
                <h4 style="margin: 10px 0 8px 0; font-size: 13px; color: #333;">Permissions:</h4>
                <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                    ${role.modules && role.modules.length > 0 
                        ? role.modules.map(perm => `<span class="badge" style="background: #006533; color: white; padding: 4px 10px; border-radius: 12px; font-size: 12px;">${formatPermissionName(perm)}</span>`).join('')
                        : '<span style="color: #999; font-size: 12px;">No permissions</span>'
                    }
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * Format permission name for display
 */
function formatPermissionName(perm) {
    return perm
        .replace(/^can_/, '')
        .replace(/_/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

/**
 * Edit role
 */
function editRole(roleName) {
    editingRoleName = roleName;
    fetchRoleAndPopulate(roleName);
}

/**
 * Fetch role details and populate modal
 */
async function fetchRoleAndPopulate(roleName) {
    try {
        const role = await apiRequest(`/roles/${encodeURIComponent(roleName)}`);
        
        document.getElementById('roleModalTitle').textContent = `Edit Role: ${escapeHtml(role.name)}`;
        document.getElementById('roleName').value = role.name;
        document.getElementById('roleDescription').value = role.description || '';
        
        // Uncheck all first
        document.querySelectorAll('.rolePermission').forEach(cb => cb.checked = false);
        
        // Check selected permissions
        if (role.modules) {
            role.modules.forEach(perm => {
                const cb = document.querySelector(`input[name="${perm}"]`);
                if (cb) cb.checked = true;
            });
        }
        
        openModal('roleModal');
    } catch (error) {
        console.error('Error fetching role:', error);
        showAlert('Error loading role details', 'error');
    }
}

/**
 * Delete role
 */
async function deleteRole(roleName) {
    if (!confirmAction(`Are you sure you want to delete the role "${roleName}"? This action cannot be undone.`)) {
        return;
    }

    try {
        await apiRequest(`/roles/${encodeURIComponent(roleName)}`, {
            method: 'DELETE'
        });

        showAlert('Role deleted successfully!', 'success');
        loadRoles();
    } catch (error) {
        console.error('Error deleting role:', error);
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
    document.addEventListener('DOMContentLoaded', loadRoles);
} else {
    loadRoles();
}
