#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - User Management Template

Clean user management interface extracted from main app.
"""

USER_MANAGEMENT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>👥 User Management - SA Medical Imaging</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8fafc;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            color: white;
            padding: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-size: 28px;
            font-weight: 600;
        }
        
        .header p {
            opacity: 0.9;
            margin-top: 5px;
        }
        
        .content {
            padding: 30px;
        }
        
        .btn {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            margin-right: 10px;
            transition: all 0.2s;
        }
        
        .btn:hover {
            background: #2563eb;
            transform: translateY(-1px);
        }
        
        .btn-danger {
            background: #ef4444;
        }
        
        .btn-danger:hover {
            background: #dc2626;
        }
        
        .btn-secondary {
            background: #6b7280;
        }
        
        .btn-secondary:hover {
            background: #4b5563;
        }
        
        .users-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .users-table th,
        .users-table td {
            padding: 16px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }
        
        .users-table th {
            background: #f8fafc;
            font-weight: 600;
            color: #374151;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .users-table tr:hover {
            background: #f9fafb;
        }
        
        .role-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .role-admin {
            background: #fef2f2;
            color: #dc2626;
        }
        
        .role-user {
            background: #eff6ff;
            color: #2563eb;
        }
        
        .role-typist {
            background: #f0fdf4;
            color: #166534;
        }
        
        .status-active {
            color: #10b981;
        }
        
        .status-inactive {
            color: #ef4444;
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            backdrop-filter: blur(4px);
        }
        
        .modal-content {
            background: white;
            margin: 50px auto;
            padding: 40px;
            border-radius: 16px;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        
        .modal h2 {
            color: #1f2937;
            margin-bottom: 20px;
            font-size: 24px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            color: #374151;
            font-weight: 500;
            margin-bottom: 8px;
            font-size: 14px;
        }
        
        input, select {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.2s;
        }
        
        input:focus, select:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
        
        .status {
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-weight: 500;
        }
        
        .status.success {
            background: #dcfce7;
            color: #166534;
            border: 1px solid #bbf7d0;
        }
        
        .status.error {
            background: #fef2f2;
            color: #dc2626;
            border: 1px solid #fecaca;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid #e2e8f0;
        }
        
        .stat-number {
            font-size: 32px;
            font-weight: 700;
            color: #3b82f6;
            margin-bottom: 5px;
        }
        
        .stat-label {
            color: #6b7280;
            font-size: 14px;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>👥 User Management</h1>
                <p>🇿🇦 Manage system users and permissions</p>
            </div>
            <div>
                <button class="btn" onclick="showAddUserModal()">➕ Add User</button>
                <button class="btn btn-secondary" onclick="window.location.href='/'">🏠 Home</button>
                <button class="btn btn-secondary" onclick="window.location.href='/nas-config'">⚙️ NAS Config</button>
                <button class="btn btn-secondary" onclick="window.location.href='/device-management'">📱 Devices</button>
            </div>
        </div>
        
        <div class="content">
            <!-- Search and Filter Bar -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding: 15px; background: #f8fafc; border-radius: 8px; border: 1px solid #e5e7eb;">
                <div style="display: flex; gap: 15px; align-items: center;">
                    <input type="text" id="searchUsers" placeholder="🔍 Search users..." onkeyup="filterUsers()" style="padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; width: 250px;">
                    <select id="roleFilter" onchange="filterUsers()" style="padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px;">
                        <option value="">All Roles</option>
                        <option value="admin">Administrator</option>
                        <option value="radiologist">Radiologist</option>
                        <option value="technologist">Technologist</option>
                        <option value="nurse">Nurse</option>
                    </select>
                </div>
                <button class="btn btn-secondary" onclick="loadUsers()">🔄 Refresh</button>
            </div>
            <div id="status"></div>
            
            <!-- Statistics -->
            <div class="stats-grid" id="statsGrid">
                <div class="stat-card">
                    <div class="stat-number" id="totalUsers">-</div>
                    <div class="stat-label">Total Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="activeUsers">-</div>
                    <div class="stat-label">Active Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="adminUsers">-</div>
                    <div class="stat-label">Administrators</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="recentLogins">-</div>
                    <div class="stat-label">Recent Logins</div>
                </div>
            </div>
            
            <table class="users-table">
                <thead>
                    <tr>
                        <th>User</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Last Login</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="usersTableBody">
                    <tr>
                        <td colspan="5" style="text-align: center; padding: 40px; color: #6b7280;">
                            Loading users...
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <!-- Add/Edit User Modal -->
    <div id="userModal" class="modal">
        <div class="modal-content">
            <h2 id="modalTitle">Add New User</h2>
            <form id="userForm">
                <input type="hidden" id="userId" name="userId">
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div class="form-group">
                        <label for="username">Username *</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="email">Email Address *</label>
                        <input type="email" id="email" name="email" required>
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div class="form-group">
                        <label for="name">Full Name</label>
                        <input type="text" id="name" name="name" placeholder="Dr. John Smith">
                    </div>
                    
                    <div class="form-group">
                        <label for="phone">Phone Number</label>
                        <input type="tel" id="phone" name="phone" placeholder="+27-11-123-4567">
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div class="form-group">
                        <label for="role">Role *</label>
                        <select id="role" name="role" required>
                            <option value="">Select Role</option>
                            <option value="admin">System Administrator</option>
                            <option value="radiologist">Radiologist</option>
                            <option value="technologist">Radiologic Technologist</option>
                            <option value="nurse">Nursing Sister</option>
                            <option value="clerk">Clerk</option>
                            <option value="student">Student</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="province">Province</label>
                        <select id="province" name="province">
                            <option value="gauteng">Gauteng</option>
                            <option value="western_cape">Western Cape</option>
                            <option value="kwazulu_natal">KwaZulu-Natal</option>
                            <option value="eastern_cape">Eastern Cape</option>
                            <option value="free_state">Free State</option>
                            <option value="limpopo">Limpopo</option>
                            <option value="mpumalanga">Mpumalanga</option>
                            <option value="north_west">North West</option>
                            <option value="northern_cape">Northern Cape</option>
                        </select>
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div class="form-group">
                        <label for="facility_name">Facility Name</label>
                        <input type="text" id="facility_name" name="facility_name" placeholder="Chris Hani Baragwanath Hospital">
                    </div>
                    
                    <div class="form-group">
                        <label for="hpcsa_number">HPCSA Number</label>
                        <input type="text" id="hpcsa_number" name="hpcsa_number" placeholder="PR1234567">
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="pin">Password/PIN *</label>
                    <input type="password" id="pin" name="pin" required>
                    <small style="color: #6b7280;">Minimum 6 characters</small>
                </div>
                
                <div style="margin-top: 30px; display: flex; gap: 10px;">
                    <button type="submit" class="btn" style="flex: 1;">💾 Save User</button>
                    <button type="button" class="btn btn-secondary" onclick="closeModal()" style="flex: 1;">❌ Cancel</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        let users = [];
        
        // Load users and statistics on page load
        async function loadUsers() {
            try {
                const response = await fetch('/api/admin/users', { credentials: 'include' });
                const data = await response.json();
                
                if (data.success) {
                    users = data.users;
                    renderUsersTable();
                    updateStatistics();
                } else {
                    showStatus('Failed to load users: ' + data.error, 'error');
                }
            } catch (error) {
                showStatus('Failed to load users: Network error', 'error');
            }
        }
        
        function updateStatistics() {
            const totalUsers = users.length;
            const activeUsers = users.filter(u => u.is_active).length;
            const adminUsers = users.filter(u => u.role === 'admin').length;
            const recentLogins = users.filter(u => {
                if (!u.last_login) return false;
                const loginDate = new Date(u.last_login);
                const weekAgo = new Date();
                weekAgo.setDate(weekAgo.getDate() - 7);
                return loginDate > weekAgo;
            }).length;
            
            document.getElementById('totalUsers').textContent = totalUsers;
            document.getElementById('activeUsers').textContent = activeUsers;
            document.getElementById('adminUsers').textContent = adminUsers;
            document.getElementById('recentLogins').textContent = recentLogins;
        }
        
        function renderUsersTable() {
            const tbody = document.getElementById('usersTableBody');
            const searchTerm = document.getElementById('searchUsers')?.value.toLowerCase() || '';
            const roleFilter = document.getElementById('roleFilter')?.value || '';
            
            // Filter users based on search and role
            let filteredUsers = users.filter(user => {
                const matchesSearch = !searchTerm || 
                    user.username.toLowerCase().includes(searchTerm) ||
                    user.email.toLowerCase().includes(searchTerm) ||
                    user.name?.toLowerCase().includes(searchTerm);
                
                const matchesRole = !roleFilter || user.role === roleFilter;
                
                return matchesSearch && matchesRole;
            });
            
            if (filteredUsers.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 40px; color: #6b7280;">No users found</td></tr>';
                return;
            }
            
            tbody.innerHTML = filteredUsers.map(user => `
                <tr>
                    <td>
                        <div style="display: flex; align-items: center;">
                            <div style="width: 40px; height: 40px; background: #3b82f6; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; margin-right: 12px;">
                                ${user.username.charAt(0).toUpperCase()}
                            </div>
                            <div>
                                <div style="font-weight: 600; color: #1f2937;">${user.username}</div>
                                <div style="font-size: 14px; color: #6b7280;">${user.email}</div>
                            </div>
                        </div>
                    </td>
                    <td><span class="role-badge role-${user.role}">${user.role}</span></td>
                    <td><span class="status-${user.is_active ? 'active' : 'inactive'}">${user.is_active ? '🟢 Active' : '🔴 Inactive'}</span></td>
                    <td>${user.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}</td>
                    <td>
                        <button class="btn" onclick="editUser('${user.user_id}')" style="padding: 8px 16px; font-size: 12px;">✏️ Edit</button>
                        <button class="btn btn-danger" onclick="deleteUser('${user.user_id}', '${user.username}')" style="padding: 8px 16px; font-size: 12px;">🗑️ Delete</button>
                    </td>
                </tr>
            `).join('');
        }
        
        function filterUsers() {
            renderUsersTable();
        }
        
        function showAddUserModal() {
            document.getElementById('modalTitle').textContent = 'Add New User';
            document.getElementById('userForm').reset();
            document.getElementById('userId').value = '';
            document.getElementById('userModal').style.display = 'block';
        }
        
        function editUser(userId) {
            const user = users.find(u => u.user_id === userId);
            if (!user) return;
            
            document.getElementById('modalTitle').textContent = 'Edit User';
            document.getElementById('userId').value = user.user_id;
            document.getElementById('username').value = user.username;
            document.getElementById('email').value = user.email;
            document.getElementById('name').value = user.name || '';
            document.getElementById('role').value = user.role;
            document.getElementById('province').value = user.province || 'gauteng';
            document.getElementById('facility_name').value = user.facility_name || '';
            document.getElementById('hpcsa_number').value = user.hpcsa_number || '';
            document.getElementById('phone').value = user.phone_number || '';
            document.getElementById('pin').value = ''; // Don't populate PIN for security
            document.getElementById('userModal').style.display = 'block';
        }
        
        function closeModal() {
            document.getElementById('userModal').style.display = 'none';
        }
        
        async function deleteUser(userId, username) {
            if (!confirm(`Are you sure you want to delete user "${username}"?\\n\\nThis action cannot be undone.`)) {
                return;
            }
            
            try {
                const response = await fetch(`/api/admin/users/${userId}`, {
                    method: 'DELETE',
                    credentials: 'include'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showStatus('✅ User deleted successfully', 'success');
                    loadUsers(); // Reload users
                } else {
                    showStatus('❌ Failed to delete user: ' + data.error, 'error');
                }
            } catch (error) {
                showStatus('❌ Failed to delete user: Network error', 'error');
            }
        }
        
        // Handle form submission
        document.getElementById('userForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const userData = {
                username: formData.get('username'),
                email: formData.get('email'),
                name: formData.get('name'),
                role: formData.get('role'),
                province: formData.get('province'),
                facility_name: formData.get('facility_name'),
                hpcsa_number: formData.get('hpcsa_number'),
                pin: formData.get('pin'),
                phone_number: formData.get('phone')
            };
            
            const userId = formData.get('userId');
            const isEdit = !!userId;
            
            try {
                const url = isEdit ? `/api/admin/users/${userId}` : '/api/admin/users';
                const method = isEdit ? 'PUT' : 'POST';
                
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(userData),
                    credentials: 'include'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showStatus(`✅ User ${isEdit ? 'updated' : 'created'} successfully`, 'success');
                    closeModal();
                    loadUsers(); // Reload users
                } else {
                    showStatus(`❌ Failed to ${isEdit ? 'update' : 'create'} user: ` + data.error, 'error');
                }
            } catch (error) {
                showStatus(`❌ Failed to ${isEdit ? 'update' : 'create'} user: Network error`, 'error');
            }
        });
        
        function showStatus(message, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.innerHTML = `<div class="status ${type}">${message}</div>`;
            
            if (type === 'success') {
                setTimeout(() => {
                    statusDiv.innerHTML = '';
                }, 5000);
            }
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('userModal');
            if (event.target === modal) {
                closeModal();
            }
        }
        
        // Load users on page load
        loadUsers();
    </script>
</body>
</html>
"""