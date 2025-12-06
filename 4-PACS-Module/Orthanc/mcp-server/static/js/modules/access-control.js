/**
 * Access Control Management Module
 * Handles patient access, doctor assignments, and family access
 */

let currentPatientAccess = [];
let currentDoctorAssignments = [];
let currentFamilyAccess = [];
const API_BASE = 'http://localhost:8080';

/**
 * ============ PATIENT ACCESS MANAGEMENT ============
 */

/**
 * Load patient access relationships
 */
async function loadPatientAccess() {
    try {
        const data = await apiRequest('/access/user/relationships');
        currentPatientAccess = data;
        renderPatientAccessTable(data);
    } catch (error) {
        console.error('Error loading patient access:', error);
        showAlert('Failed to load patient access: ' + error.message, 'error');
        document.getElementById('patientAccessTableBody').innerHTML = `
            <tr><td colspan="8" style="text-align: center; padding: 40px;">Error loading data</td></tr>
        `;
    }
}

/**
 * Render patient access table
 */
function renderPatientAccessTable(relations) {
    const tbody = document.getElementById('patientAccessTableBody');
    
    if (relations.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 40px;">
                    No patient access relationships found
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = relations.map(rel => `
        <tr>
            <td><strong>${escapeHtml(rel.patient_id)}</strong></td>
            <td>${rel.patient_name ? escapeHtml(rel.patient_name) : '-'}</td>
            <td>${escapeHtml(rel.user_name)}</td>
            <td><span class="badge" style="background: #667eea; color: white;">${escapeHtml(rel.access_level || 'read')}</span></td>
            <td>${rel.expires_at ? new Date(rel.expires_at).toLocaleDateString() : 'Never'}</td>
            <td><span class="badge badge-${rel.is_active ? 'active' : 'inactive'}">${rel.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>${escapeHtml(rel.created_by_name)}</td>
            <td>
                <button class="btn btn-primary btn-small" onclick="editPatientAccess(${rel.id})">Edit</button>
                <button class="btn btn-danger btn-small" onclick="revokePatientAccess(${rel.id})">Revoke</button>
            </td>
        </tr>
    `).join('');
}

/**
 * Filter patient access
 */
function filterPatientAccess() {
    const search = document.getElementById('patientAccessSearch').value.toLowerCase();
    const filtered = currentPatientAccess.filter(rel =>
        rel.patient_id.toLowerCase().includes(search) ||
        (rel.patient_name && rel.patient_name.toLowerCase().includes(search)) ||
        rel.user_name.toLowerCase().includes(search)
    );
    renderPatientAccessTable(filtered);
}

/**
 * Open grant access modal
 */
function openGrantAccessModal() {
    clearForm('grantAccessForm');
    openModal('grantAccessModal');
}

/**
 * Close grant access modal
 */
function closeGrantAccessModal() {
    closeModal('grantAccessModal');
}

/**
 * Save patient access
 */
async function savePatientAccess(event) {
    event.preventDefault();
    
    try {
        const payload = {
            patient_id: validateInput(document.getElementById('patientId').value, 1, 50),
            user_id: parseInt(document.getElementById('userId').value),
            access_level: document.getElementById('accessLevel').value,
            expires_at: document.getElementById('expiresAt').value || null
        };
        
        const response = await fetch(`${API_BASE}/access/patient-relationship`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getCookie('access_token')}`
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to grant access');
        }
        
        showAlert('Patient access granted successfully', 'success');
        closeGrantAccessModal();
        loadPatientAccess();
    } catch (error) {
        console.error('Error granting access:', error);
        showAlert('Error: ' + error.message, 'error');
    }
}

/**
 * Revoke patient access
 */
async function revokePatientAccess(relationshipId) {
    if (!confirmAction('Are you sure you want to revoke this access?')) {
        return;
    }

    try {
        await apiRequest(`/access/revoke?relationship_id=${relationshipId}`, {
            method: 'DELETE'
        });
        
        showAlert('Access revoked successfully', 'success');
        loadPatientAccess();
    } catch (error) {
        console.error('Error revoking access:', error);
        showAlert('Error: ' + error.message, 'error');
    }
}

/**
 * ============ DOCTOR ASSIGNMENT MANAGEMENT ============
 */

/**
 * Load doctor assignments
 */
async function loadDoctorAssignments() {
    try {
        const data = await apiRequest('/access/doctor-assignments');
        currentDoctorAssignments = data;
        renderDoctorAssignmentTable(data);
    } catch (error) {
        console.error('Error loading doctor assignments:', error);
        showAlert('Failed to load doctor assignments: ' + error.message, 'error');
        document.getElementById('doctorAssignmentTableBody').innerHTML = `
            <tr><td colspan="9" style="text-align: center; padding: 40px;">Error loading data</td></tr>
        `;
    }
}

/**
 * Render doctor assignment table
 */
function renderDoctorAssignmentTable(assignments) {
    const tbody = document.getElementById('doctorAssignmentTableBody');
    
    if (assignments.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" style="text-align: center; padding: 40px;">
                    No doctor assignments found
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = assignments.map(assign => `
        <tr>
            <td><strong>${escapeHtml(assign.doctor_name)}</strong></td>
            <td>${escapeHtml(assign.doctor_email)}</td>
            <td><strong>${escapeHtml(assign.patient_id)}</strong></td>
            <td>${assign.patient_name ? escapeHtml(assign.patient_name) : '-'}</td>
            <td><span class="badge" style="background: #17a2b8; color: white;">${escapeHtml(assign.assignment_type || 'primary')}</span></td>
            <td><span class="badge badge-${assign.is_active ? 'active' : 'inactive'}">${assign.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>${escapeHtml(assign.assigned_by_name)}</td>
            <td>${new Date(assign.created_at).toLocaleDateString()}</td>
            <td>
                <button class="btn btn-primary btn-small" onclick="editDoctorAssignment(${assign.id})">Edit</button>
                <button class="btn btn-danger btn-small" onclick="removeDoctorAssignment(${assign.id})">Remove</button>
            </td>
        </tr>
    `).join('');
}

/**
 * Filter doctor assignments
 */
function filterDoctorAssignments() {
    const search = document.getElementById('doctorAssignmentSearch').value.toLowerCase();
    const filtered = currentDoctorAssignments.filter(assign =>
        assign.doctor_name.toLowerCase().includes(search) ||
        assign.patient_id.toLowerCase().includes(search) ||
        (assign.patient_name && assign.patient_name.toLowerCase().includes(search))
    );
    renderDoctorAssignmentTable(filtered);
}

/**
 * Open doctor assignment modal
 */
function openDoctorAssignmentModal() {
    clearForm('doctorAssignmentForm');
    openModal('doctorAssignmentModal');
}

/**
 * Close doctor assignment modal
 */
function closeDoctorAssignmentModal() {
    closeModal('doctorAssignmentModal');
}

/**
 * Save doctor assignment
 */
async function saveDoctorAssignment(event) {
    event.preventDefault();
    
    try {
        const payload = {
            doctor_user_id: parseInt(document.getElementById('doctorUserId').value),
            patient_id: validateInput(document.getElementById('assignmentPatientId').value, 1, 50),
            assignment_type: document.getElementById('assignmentType').value
        };
        
        const response = await fetch(`${API_BASE}/access/doctor-assignment`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getCookie('access_token')}`
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create assignment');
        }
        
        showAlert('Doctor assignment created successfully', 'success');
        closeDoctorAssignmentModal();
        loadDoctorAssignments();
    } catch (error) {
        console.error('Error saving assignment:', error);
        showAlert('Error: ' + error.message, 'error');
    }
}

/**
 * Remove doctor assignment
 */
async function removeDoctorAssignment(assignmentId) {
    if (!confirmAction('Are you sure you want to remove this assignment?')) {
        return;
    }

    try {
        await apiRequest(`/access/revoke?assignment_id=${assignmentId}`, {
            method: 'DELETE'
        });
        
        showAlert('Assignment removed successfully', 'success');
        loadDoctorAssignments();
    } catch (error) {
        console.error('Error removing assignment:', error);
        showAlert('Error: ' + error.message, 'error');
    }
}

/**
 * ============ FAMILY ACCESS MANAGEMENT ============
 */

/**
 * Load family access
 */
async function loadFamilyAccess() {
    try {
        const data = await apiRequest('/access/family-access');
        currentFamilyAccess = data;
        renderFamilyAccessTable(data);
    } catch (error) {
        console.error('Error loading family access:', error);
        showAlert('Failed to load family access: ' + error.message, 'error');
        document.getElementById('familyAccessTableBody').innerHTML = `
            <tr><td colspan="9" style="text-align: center; padding: 40px;">Error loading data</td></tr>
        `;
    }
}

/**
 * Render family access table
 */
function renderFamilyAccessTable(familyAccess) {
    const tbody = document.getElementById('familyAccessTableBody');
    
    if (familyAccess.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" style="text-align: center; padding: 40px;">
                    No family access configurations found
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = familyAccess.map(fa => `
        <tr>
            <td><strong>${escapeHtml(fa.parent_name)}</strong></td>
            <td>${escapeHtml(fa.parent_email)}</td>
            <td><strong>${escapeHtml(fa.child_patient_id)}</strong></td>
            <td><span class="badge" style="background: #FFB81C; color: #333;">${escapeHtml(fa.relationship || 'parent')}</span></td>
            <td><span class="badge badge-${fa.verified ? 'active' : 'inactive'}">${fa.verified ? '✓ Verified' : '⊘ Pending'}</span></td>
            <td><span class="badge badge-${fa.is_active ? 'active' : 'inactive'}">${fa.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>${fa.expires_at ? new Date(fa.expires_at).toLocaleDateString() : 'Never'}</td>
            <td>${new Date(fa.created_at).toLocaleDateString()}</td>
            <td>
                ${!fa.verified ? `<button class="btn btn-success btn-small" onclick="verifyFamilyAccess(${fa.id})">Verify</button>` : ''}
                <button class="btn btn-primary btn-small" onclick="editFamilyAccess(${fa.id})">Edit</button>
                <button class="btn btn-danger btn-small" onclick="revokeFamilyAccess(${fa.id})">Revoke</button>
            </td>
        </tr>
    `).join('');
}

/**
 * Filter family access
 */
function filterFamilyAccess() {
    const search = document.getElementById('familyAccessSearch').value.toLowerCase();
    const filtered = currentFamilyAccess.filter(fa =>
        fa.parent_name.toLowerCase().includes(search) ||
        fa.parent_email.toLowerCase().includes(search) ||
        fa.child_patient_id.toLowerCase().includes(search)
    );
    renderFamilyAccessTable(filtered);
}

/**
 * Open family access modal
 */
function openFamilyAccessModal() {
    clearForm('familyAccessForm');
    openModal('familyAccessModal');
}

/**
 * Close family access modal
 */
function closeFamilyAccessModal() {
    closeModal('familyAccessModal');
}

/**
 * Save family access
 */
async function saveFamilyAccess(event) {
    event.preventDefault();
    
    try {
        const payload = {
            parent_user_id: parseInt(document.getElementById('parentUserId').value),
            child_patient_id: validateInput(document.getElementById('childPatientId').value, 1, 50),
            relationship: document.getElementById('relationship').value,
            expires_at: document.getElementById('familyExpiresAt').value || null
        };
        
        const response = await fetch(`${API_BASE}/access/family-access`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getCookie('access_token')}`
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create family access');
        }
        
        showAlert('Family access created successfully', 'success');
        closeFamilyAccessModal();
        loadFamilyAccess();
    } catch (error) {
        console.error('Error saving family access:', error);
        showAlert('Error: ' + error.message, 'error');
    }
}

/**
 * Verify family access
 */
async function verifyFamilyAccess(familyAccessId) {
    try {
        await apiRequest(`/access/family-access/${familyAccessId}/verify`, {
            method: 'POST'
        });
        
        showAlert('Family access verified successfully', 'success');
        loadFamilyAccess();
    } catch (error) {
        console.error('Error verifying access:', error);
        showAlert('Error: ' + error.message, 'error');
    }
}

/**
 * Revoke family access
 */
async function revokeFamilyAccess(familyAccessId) {
    if (!confirmAction('Are you sure you want to revoke this family access?')) {
        return;
    }

    try {
        await apiRequest(`/access/revoke?family_access_id=${familyAccessId}`, {
            method: 'DELETE'
        });
        
        showAlert('Family access revoked successfully', 'success');
        loadFamilyAccess();
    } catch (error) {
        console.error('Error revoking access:', error);
        showAlert('Error: ' + error.message, 'error');
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
    document.addEventListener('DOMContentLoaded', function() {
        loadPatientAccess();
        loadDoctorAssignments();
        loadFamilyAccess();
    });
} else {
    loadPatientAccess();
    loadDoctorAssignments();
    loadFamilyAccess();
}
