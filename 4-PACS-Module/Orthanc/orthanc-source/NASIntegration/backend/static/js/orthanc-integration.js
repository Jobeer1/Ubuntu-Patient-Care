/* 🇿🇦 Orthanc Integration Module - South African Medical Imaging System */

// Orthanc server management functions
async function connectToOrthanc() {
    const url = document.getElementById('orthancUrl').value;
    const username = document.getElementById('orthancUsername').value;
    const password = document.getElementById('orthancPassword').value;
    
    if (!url || !username || !password) {
        window.NASIntegration.core.showMessage('Please fill in all Orthanc connection fields', 'error');
        return;
    }
    
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/orthanc/connect', {
            method: 'POST',
            body: JSON.stringify({ url, username, password })
        });
        
        if (data.success) {
            window.NASIntegration.core.showMessage('✅ Connected to Orthanc successfully!', 'success');
            await checkOrthancStatus();
        } else {
            window.NASIntegration.core.showMessage(`❌ Connection failed: ${data.error}`, 'error');
        }
    } catch (error) {
        window.NASIntegration.core.showMessage(`❌ Connection error: ${error.message}`, 'error');
    }
}

// Backwards-compatible wrapper used by the Jinja template `nas_integration.html`.
// The template calls `connectOrthanc()` and expects form fields with ids
// `orthancUrl`, `orthancUser`, `orthancPass`. The original implementation
// used slightly different ids and a different function name; provide a
// small shim so the page continues to work without changing templates.
async function connectOrthanc() {
    const url = document.getElementById('orthancUrl')?.value;
    const username = document.getElementById('orthancUser')?.value || document.getElementById('orthancUsername')?.value;
    const password = document.getElementById('orthancPass')?.value || document.getElementById('orthancPassword')?.value;

    if (!url) {
        window.NASIntegration.core.showMessage('Please provide Orthanc URL', 'warning');
        return;
    }

    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/orthanc/connect', {
            method: 'POST',
            body: JSON.stringify({ url, username, password })
        });

        if (data && data.success) {
            window.NASIntegration.core.showMessage('✅ Connected to Orthanc successfully!', 'success');
            // refresh status
            if (typeof checkOrthancStatus === 'function') await checkOrthancStatus();
        } else {
            window.NASIntegration.core.showMessage(`❌ Connection failed: ${data?.error || data?.message || 'Unknown'}`, 'error');
        }
    } catch (err) {
        window.NASIntegration.core.showMessage(`❌ Connection error: ${err?.message || err}`, 'error');
    }
}

// Backwards-compatible wrapper for checking Orthanc status from the page
async function testOrthancConnection() {
    if (typeof checkOrthancStatus === 'function') {
        await checkOrthancStatus();
    } else {
        try {
            const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/orthanc/status');
            updateOrthancStatus(data);
        } catch (err) {
            window.NASIntegration.core.showMessage(`❌ Status check error: ${err?.message || err}`, 'error');
        }
    }
}

async function checkOrthancStatus() {
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/orthanc/status');
        updateOrthancStatus(data);
        window.NASIntegration.core.storeLastResults('orthanc_status', data);
    } catch (error) {
        console.error('Failed to check Orthanc status:', error);
        updateOrthancStatus({ 
            success: false, 
            status: 'disconnected', 
            error: error.message 
        });
    }
}

function updateOrthancStatus(data) {
    const statusElement = document.getElementById('orthancStatus');
    if (!statusElement) return;
    
    let statusHtml = '';
    
    if (data.success) {
        statusHtml = `
            <div class="status-card connected">
                <div class="status-header">
                    <h4>🟢 Orthanc Connected</h4>
                </div>
                <div class="status-details">
                    <div class="status-item">
                        <span class="label">Version:</span>
                        <span class="value">${data.version || 'Unknown'}</span>
                    </div>
                    <div class="status-item">
                        <span class="label">Database:</span>
                        <span class="value">${data.database_version || 'Unknown'}</span>
                    </div>
                    <div class="status-item">
                        <span class="label">Patients:</span>
                        <span class="value">${data.patients_count || 0}</span>
                    </div>
                    <div class="status-item">
                        <span class="label">Studies:</span>
                        <span class="value">${data.studies_count || 0}</span>
                    </div>
                </div>
            </div>
        `;
    } else {
        statusHtml = `
            <div class="status-card disconnected">
                <div class="status-header">
                    <h4>🔴 Orthanc Disconnected</h4>
                </div>
                <div class="status-details">
                    <p>Unable to connect to Orthanc server</p>
                    ${data.error ? `<p class="error-detail">Error: ${data.error}</p>` : ''}
                </div>
            </div>
        `;
    }
    
    statusElement.innerHTML = statusHtml;
}

// Indexing management functions
async function startIndexing() {
    const orthancUrl = document.getElementById('orthancUrl').value;
    
    if (!orthancUrl) {
        window.NASIntegration.core.showMessage('Please configure Orthanc connection first', 'error');
        return;
    }
    
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/indexing/start', {
            method: 'POST',
            body: JSON.stringify({ orthanc_url: orthancUrl })
        });
        
        if (data.success) {
            window.NASIntegration.core.showMessage('✅ Indexing started successfully!', 'success');
            setTimeout(pollIndexingProgress, 2000);
        } else {
            window.NASIntegration.core.showMessage(`❌ Failed to start indexing: ${data.error}`, 'error');
        }
    } catch (error) {
        window.NASIntegration.core.showMessage(`❌ Indexing error: ${error.message}`, 'error');
    }
}

async function checkIndexStatus() {
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/indexing/status');
        updateIndexingStatus(data);
        window.NASIntegration.core.storeLastResults('indexing_status', data);
    } catch (error) {
        console.error('Failed to check indexing status:', error);
        updateIndexingStatus({ 
            success: false, 
            status: 'error', 
            error: error.message 
        });
    }
}

async function pollIndexingProgress() {
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/indexing/status');
        updateIndexingStatus(data);
        
        if (data.status === 'running') {
            setTimeout(pollIndexingProgress, 3000);
        }
    } catch (error) {
        console.error('Failed to poll indexing progress:', error);
    }
}

async function stopIndexing() {
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/indexing/stop', {
            method: 'POST'
        });
        
        if (data.success) {
            window.NASIntegration.core.showMessage('✅ Indexing stopped successfully!', 'success');
            await checkIndexStatus();
        } else {
            window.NASIntegration.core.showMessage(`❌ Failed to stop indexing: ${data.error}`, 'error');
        }
    } catch (error) {
        window.NASIntegration.core.showMessage(`❌ Stop indexing error: ${error.message}`, 'error');
    }
}

function updateIndexingStatus(data) {
    const statusElement = document.getElementById('indexingStatus');
    if (!statusElement) return;
    
    let statusHtml = '';
    
    if (data.success) {
        const statusColor = data.status === 'running' ? '🟡' : 
                           data.status === 'completed' ? '🟢' : '⚪';
        
        statusHtml = `
            <div class="status-card ${data.status}">
                <div class="status-header">
                    <h4>${statusColor} Indexing ${data.status.charAt(0).toUpperCase() + data.status.slice(1)}</h4>
                </div>
                <div class="status-details">
                    ${data.progress !== undefined ? `
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${data.progress}%"></div>
                            <span class="progress-text">${data.progress}%</span>
                        </div>
                    ` : ''}
                    <div class="status-item">
                        <span class="label">Indexed Files:</span>
                        <span class="value">${data.indexed_files || 0}</span>
                    </div>
                    <div class="status-item">
                        <span class="label">Total Files:</span>
                        <span class="value">${data.total_files || 0}</span>
                    </div>
                    ${data.last_indexed ? `
                        <div class="status-item">
                            <span class="label">Last Update:</span>
                            <span class="value">${new Date(data.last_indexed).toLocaleString()}</span>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    } else {
        statusHtml = `
            <div class="status-card error">
                <div class="status-header">
                    <h4>🔴 Indexing Error</h4>
                </div>
                <div class="status-details">
                    <p>Unable to get indexing status</p>
                    ${data.error ? `<p class="error-detail">Error: ${data.error}</p>` : ''}
                </div>
            </div>
        `;
    }
    
    statusElement.innerHTML = statusHtml;
}

// Patient search functions
async function searchPatients() {
    // Support both the compact single-field search UI (patientQuery + searchType)
    // and the legacy multi-field inputs (patientId, patientName, studyDate, modality).
    const compactQuery = document.getElementById('patientQuery')?.value?.trim() || '';
    const compactType = document.getElementById('searchType')?.value || '';

    let searchCriteria = {
        patient_id: '',
        patient_name: '',
        study_date: '',
        modality: ''
    };

    if (compactQuery) {
        // Map compact input to the selected type
        switch (compactType) {
            case 'id':
                searchCriteria.patient_id = compactQuery;
                break;
            case 'study_date':
                searchCriteria.study_date = compactQuery;
                break;
            case 'modality':
                searchCriteria.modality = compactQuery;
                break;
            case 'name':
            default:
                searchCriteria.patient_name = compactQuery;
                break;
        }
    } else {
        // Fallback to legacy multi-field form
        searchCriteria = {
            patient_id: document.getElementById('patientId')?.value || '',
            patient_name: document.getElementById('patientName')?.value || '',
            study_date: document.getElementById('studyDate')?.value || '',
            modality: document.getElementById('modality')?.value || ''
        };
    }

    // Validation: require at least one non-empty criterion
    if (!searchCriteria.patient_id && !searchCriteria.patient_name && 
        !searchCriteria.study_date && !searchCriteria.modality) {
        window.NASIntegration.core.showMessage('Please enter at least one search criterion', 'warning');
        return;
    }

    try {
    const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/search/patient', {
            method: 'POST',
            body: JSON.stringify(searchCriteria)
        });

        const resultsElement = document.getElementById('searchResults');
        if (resultsElement) {
            // Convert patients object to array, or use empty array if no patients
            const patientsArray = Array.isArray(data.patients) ? data.patients : 
                                 (data.patients && typeof data.patients === 'object' && Object.keys(data.patients).length > 0) ?
                                 Object.values(data.patients) : [];
            resultsElement.innerHTML = formatPatientResults(patientsArray);
        }

        // Use total_found from API response for accurate count
        const totalFound = data.total_found !== undefined ? data.total_found : 
                          (Array.isArray(data.patients) ? data.patients.length : 
                           (data.patients && typeof data.patients === 'object' ? Object.keys(data.patients).length : 0));
        window.NASIntegration.core.showMessage(`✅ Search completed. Found ${totalFound} results`, 'success');
    } catch (error) {
        window.NASIntegration.core.showMessage(`❌ Search error: ${error.message}`, 'error');
    }
}

function formatPatientResults(patients) {
    if (!patients || patients.length === 0) {
        return '<p class="no-data">No patients found matching your criteria</p>';
    }
    
    let html = `<h4>🔍 Found ${patients.length} Patient(s)</h4><div class="patient-results">`;
    
    patients.forEach(patient => {
        html += `
            <div class="patient-card">
                <div class="patient-header">
                    <h5>${patient.name || 'Unknown Patient'}</h5>
                    <span class="patient-id">ID: ${patient.id || 'N/A'}</span>
                </div>
                <div class="patient-details">
                    <div class="detail-item">
                        <span class="label">Birth Date:</span>
                        <span class="value">${patient.birth_date || 'Unknown'}</span>
                    </div>
                    <div class="detail-item">
                        <span class="label">Sex:</span>
                        <span class="value">${patient.sex || 'Unknown'}</span>
                    </div>
                    <div class="detail-item">
                        <span class="label">Studies:</span>
                        <span class="value">${patient.studies?.length || 0}</span>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    return html;
}

// Enhanced medical sharing system
async function generateShareLink() {
    const shareConfig = {
        patient_id: document.getElementById('sharePatientId')?.value || '',
        doctor_name: document.getElementById('doctorName')?.value || 'Dr. Unknown',
        doctor_email: document.getElementById('doctorEmail')?.value || '',
        recipient_type: document.getElementById('recipientType')?.value || 'doctor',
        expiry_hours: parseInt(document.getElementById('linkExpiry')?.value) || 72, // 3 days default
        message: document.getElementById('shareMessage')?.value || '',
        allow_download: document.getElementById('allowDownload')?.checked !== false
    };
    
    if (!shareConfig.patient_id) {
        window.NASIntegration.core.showMessage('❌ Please enter Patient ID', 'warning');
        return;
    }
    
    try {
        const resultDiv = document.getElementById('shareResults');
        resultDiv.innerHTML = '<div class="spinner-border spinner-border-sm me-2"></div>Generating secure medical sharing link...';
        
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/share/generate', {
            method: 'POST',
            body: JSON.stringify(shareConfig)
        });
        
        if (data.success) {
            const shareHtml = `
                <div class="share-success">
                    <h5>✅ ${data.message}</h5>
                    <div class="patient-info mb-3">
                        <strong>Patient:</strong> ${data.patient_info.name} (${data.patient_info.id})<br>
                        <strong>Studies Available:</strong> ${data.patient_info.studies_available}
                    </div>
                    <div class="share-details">
                        <label>🔗 Secure Link:</label>
                        <div class="input-group mb-2">
                            <input type="text" class="form-control" id="generatedLink" value="${data.share_link}" readonly>
                            <button class="btn btn-outline-primary" onclick="copyLinkToClipboard()">📋 Copy</button>
                        </div>
                        <label>🔑 Access Code:</label>
                        <div class="input-group mb-2">
                            <input type="text" class="form-control" id="generatedCode" value="${data.access_code}" readonly>
                            <button class="btn btn-outline-success" onclick="copyCodeToClipboard()">📋 Copy Code</button>
                        </div>
                        <div class="share-instructions">
                            <h6>📋 Instructions for ${shareConfig.recipient_type}:</h6>
                            <ol>
                                <li>${data.instructions.step1}</li>
                                <li>${data.instructions.step2}</li>
                                <li>${data.instructions.step3}</li>
                                <li>${data.instructions.step4}</li>
                            </ol>
                            ${data.instructions.security ? `<p class="text-info"><strong>🔒 ${data.instructions.security}</strong></p>` : ''}
                        </div>
                        <div class="share-actions mt-3">
                            <button class="btn btn-success btn-sm" onclick="sendShareEmail('${data.share_link}', '${data.access_code}')">
                                📧 Email to ${shareConfig.recipient_type}
                            </button>
                            <button class="btn btn-info btn-sm" onclick="openShareLink('${data.share_link}')">
                                🔍 Test Link
                            </button>
                        </div>
                    </div>
                </div>
            `;
            resultDiv.innerHTML = shareHtml;
            
            window.NASIntegration.core.showMessage(`✅ Medical sharing link generated for ${data.patient_info.name}`, 'success');
        } else {
            resultDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            window.NASIntegration.core.showMessage(`❌ Sharing failed: ${data.error}`, 'error');
        }
    } catch (error) {
        document.getElementById('shareResults').innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
        window.NASIntegration.core.showMessage(`❌ Share link error: ${error.message}`, 'error');
    }
}

function copyLinkToClipboard() {
    const linkField = document.getElementById('generatedLink');
    if (linkField && linkField.value) {
        linkField.select();
        document.execCommand('copy');
        window.NASIntegration.core.showMessage('✅ Share link copied to clipboard!', 'success');
    } else {
        window.NASIntegration.core.showMessage('❌ No link to copy - generate a link first', 'warning');
    }
}

function copyCodeToClipboard() {
    const codeField = document.getElementById('generatedCode');
    if (codeField && codeField.value) {
        codeField.select();
        document.execCommand('copy');
        window.NASIntegration.core.showMessage('✅ Access code copied to clipboard!', 'success');
    } else {
        window.NASIntegration.core.showMessage('❌ No access code to copy', 'warning');
    }
}

function sendShareEmail(shareLink, accessCode) {
    const doctorEmail = document.getElementById('doctorEmail')?.value || '';
    const patientName = document.getElementById('sharePatientId')?.value || 'Unknown Patient';
    const doctorName = document.getElementById('doctorName')?.value || 'Doctor';
    
    const subject = `Medical Image Sharing - ${patientName}`;
    const body = `Dear ${doctorName},

You have been granted secure access to medical images for patient: ${patientName}

🔗 Secure Access Link: ${shareLink}
🔑 Access Code: ${accessCode}

Instructions:
1. Click the secure link above
2. Enter the access code when prompted
3. View and download the medical images as needed

This link is time-limited and access is logged for HIPAA compliance.

Best regards,
Medical Imaging System`;
    
    if (doctorEmail) {
        window.location.href = `mailto:${doctorEmail}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    } else {
        // Copy email content to clipboard
        navigator.clipboard.writeText(`${subject}\n\n${body}`).then(() => {
            window.NASIntegration.core.showMessage('✅ Email content copied to clipboard!', 'success');
        });
    }
}

function openShareLink(shareLink) {
    window.open(shareLink, '_blank', 'width=800,height=600,scrollbars=yes,resizable=yes');
}

function clearShareForm() {
    document.getElementById('sharePatientId').value = '';
    document.getElementById('doctorName').value = 'Dr. ';
    document.getElementById('doctorEmail').value = '';
    document.getElementById('recipientType').value = 'doctor';
    document.getElementById('linkExpiry').value = '72';
    document.getElementById('shareMessage').value = '';
    document.getElementById('allowDownload').checked = true;
    document.getElementById('shareResults').innerHTML = `
        <div class="text-muted">
            <i class="fas fa-info-circle me-2"></i>
            Enter patient ID and doctor information to generate a secure sharing link
        </div>
    `;
    window.NASIntegration.core.showMessage('✅ Sharing form cleared', 'info');
}

// Export Orthanc functions
window.NASIntegration.orthanc = {
    connectToOrthanc,
    checkOrthancStatus,
    startIndexing,
    checkIndexStatus,
    stopIndexing,
    pollIndexingProgress,
    updateIndexingStatus,
    searchPatients,
    generateShareLink,
    copyLinkToClipboard
};

// Medical Image Indexing Functions
async function startIndexing() {
    const path = document.getElementById('indexPath')?.value;
    const priority = document.getElementById('indexPriority')?.value || 'normal';
    const options = document.getElementById('indexOptions')?.value || 'scan_only';
    
    if (!path) {
        window.NASIntegration.core.showMessage('Please enter a DICOM directory path', 'error');
        return;
    }
    
    window.NASIntegration.core.showLoading(true, 'Starting DICOM indexing...');
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/indexing/start', {
            method: 'POST',
            body: JSON.stringify({ 
                path, 
                priority,
                options 
            })
        });
        
        if (data.success) {
            document.getElementById('indexResults').innerHTML = formatIndexingStatus(data.indexing);
            updateIndexingStatus('Running');
            // Start polling for progress
            setTimeout(pollIndexingProgress, 2000);
            window.NASIntegration.core.showMessage('✅ DICOM indexing started successfully', 'success');
        } else {
            document.getElementById('indexResults').innerHTML = `❌ Error: ${data.error}`;
            window.NASIntegration.core.showMessage(`❌ Failed to start indexing: ${data.error}`, 'error');
        }
    } catch (error) {
        document.getElementById('indexResults').innerHTML = `❌ Error: ${error.message}`;
        window.NASIntegration.core.showMessage(`❌ Indexing error: ${error.message}`, 'error');
    }
    window.NASIntegration.core.showLoading(false);
}

async function checkIndexStatus() {
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/indexing/status');
        
        if (data.success && data.indexing) {
            updateIndexingStatus(data.indexing.status || 'Unknown');
            
            // Update results if currently showing indexing info
            const resultsArea = document.getElementById('indexResults');
            if (resultsArea && (resultsArea.textContent.includes('indexing') || resultsArea.textContent.includes('Ready to index'))) {
                resultsArea.innerHTML = formatIndexingStatus(data.indexing);
            }
        }
    } catch (error) {
        console.error('Indexing status check failed:', error);
    }
}

async function pollIndexingProgress() {
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/indexing/status');
        
        if (data.success && data.indexing) {
            document.getElementById('indexResults').innerHTML = formatIndexingStatus(data.indexing);
            
            // Continue polling if still running
            if (data.indexing.status === 'running') {
                setTimeout(pollIndexingProgress, 5000);
            }
        }
    } catch (error) {
        console.error('Indexing progress poll failed:', error);
    }
}

async function stopIndexing() {
    window.NASIntegration.core.showLoading(true, 'Stopping DICOM indexing...');
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/indexing/stop', {
            method: 'POST'
        });
        
        if (data.success) {
            document.getElementById('indexResults').innerHTML = formatIndexingStatus(data.indexing);
            updateIndexingStatus('Stopped');
            window.NASIntegration.core.showMessage('✅ DICOM indexing stopped successfully', 'success');
        } else {
            window.NASIntegration.core.showMessage(`❌ Failed to stop indexing: ${data.error}`, 'error');
        }
    } catch (error) {
        window.NASIntegration.core.showMessage(`❌ Stop indexing error: ${error.message}`, 'error');
    }
    window.NASIntegration.core.showLoading(false);
}

function updateIndexingStatus(status) {
    const statusElement = document.getElementById('indexingStatusText');
    if (statusElement) {
        statusElement.textContent = status;
    }
    
    // Update status indicator
    const statusItem = document.getElementById('indexingStatus');
    if (statusItem) {
        statusItem.className = `status-item ${status.toLowerCase()}`;
    }
}

function formatIndexingStatus(indexing) {
    if (!indexing) {
        return '<p class="text-muted">Indexing status unavailable</p>';
    }
    
    const status = indexing.status || 'unknown';
    const statusClass = status === 'running' ? 'success' : status === 'completed' ? 'info' : 'secondary';
    
    return `
        <div class="indexing-status-card">
            <div class="status-header">
                <h5>📊 DICOM Indexing Status</h5>
                <span class="badge bg-${statusClass}">${status.toUpperCase()}</span>
            </div>
            <div class="status-details">
                <p><strong>Path:</strong> ${indexing.path || 'N/A'}</p>
                <p><strong>Files Processed:</strong> ${indexing.files_processed || 0}</p>
                <p><strong>Total Files:</strong> ${indexing.total_files || 0}</p>
                <p><strong>Progress:</strong> ${indexing.progress || 0}%</p>
                <p><strong>Started:</strong> ${indexing.started_at || 'N/A'}</p>
                ${indexing.completed_at ? `<p><strong>Completed:</strong> ${indexing.completed_at}</p>` : ''}
                ${indexing.error ? `<p class="text-danger"><strong>Error:</strong> ${indexing.error}</p>` : ''}
            </div>
            ${status === 'running' ? `
                <div class="progress mt-2">
                    <div class="progress-bar" role="progressbar" style="width: ${indexing.progress || 0}%"></div>
                </div>
            ` : ''}
        </div>
    `;
}

console.log('✅ Orthanc Integration module loaded successfully');

// Dashboard Functions
async function refreshDashboard() {
    console.log('🔄 Refreshing dashboard...');
    
    try {
        // Use the efficient single API call for dashboard data
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/dashboard/status');
        
        if (data.success && data.dashboard) {
            updateDashboardFromData(data.dashboard);
        } else {
            // Fallback to individual calls
            await Promise.all([
                updateOrthancDashboard(),
                updateNasDashboard(),
                updateIndexDashboard()
            ]);
        }
    } catch (error) {
        console.warn('Dashboard API failed, using individual calls:', error);
        // Fallback to individual calls
        await Promise.all([
            updateOrthancDashboard(),
            updateNasDashboard(),
            updateIndexDashboard()
        ]);
    }
}

function updateDashboardFromData(dashboard) {
    // Update Orthanc status
    const orthancStatus = document.getElementById('dashboardOrthancStatus');
    const orthancDetails = document.getElementById('dashboardOrthancDetails');
    
    if (orthancStatus && orthancDetails) {
        const orthanc = dashboard.orthanc || {};
        if (orthanc.status === 'connected') {
            orthancStatus.innerHTML = '<i class="fas fa-check-circle status-online me-2"></i>Connected';
            orthancDetails.innerHTML = `<div class="small"><strong>${orthanc.name || 'Orthanc'}</strong><br>${orthanc.details || 'Connected'}</div>`;
            orthancStatus.className = 'status-value status-online';
        } else {
            orthancStatus.innerHTML = '<i class="fas fa-exclamation-circle status-offline me-2"></i>Disconnected';
            orthancDetails.innerHTML = '<div class="small">PACS server not connected</div>';
            orthancStatus.className = 'status-value status-offline';
        }
    }
    
    // Update NAS devices
    const nasDevices = document.getElementById('dashboardNasDevices');
    const nasDetails = document.getElementById('dashboardNasDetails');
    
    if (nasDevices && nasDetails) {
        const nas = dashboard.nas_devices || {};
        const total = nas.total || 0;
        const online = nas.online || 0;
        const nasCount = nas.nas_count || 0;
        
        nasDevices.innerHTML = `<i class="fas fa-server status-info me-2"></i>${total} Found`;
        nasDetails.innerHTML = `
            <div class="small">
                ${nas.details || `Online: ${online} | NAS: ${nasCount}`}<br>
                Last scan: ${nas.last_scan ? new Date(nas.last_scan).toLocaleTimeString() : 'Never'}
            </div>
        `;
        nasDevices.className = total > 0 ? 'status-value status-online' : 'status-value status-warning';
    }
    
    // Update indexing status
    const indexStatus = document.getElementById('dashboardIndexStatus');
    const indexDetails = document.getElementById('dashboardIndexDetails');
    const progressElement = document.getElementById('dashboardIndexProgress');
    
    if (indexStatus && indexDetails) {
        const indexing = dashboard.indexing || {};
        const autoIndexing = dashboard.auto_indexing || {};
        const state = indexing.state || 'idle';
        const progress = indexing.progress || 0;
        const details = indexing.details || 'No details available';
        const autoMode = indexing.auto_mode || false;
        const lastUpdated = indexing.last_updated || 'Never';
        
        if (state === 'running') {
            const icon = autoMode ? 'fa-magic' : 'fa-spinner fa-spin';
            const modeText = autoMode ? 'Auto-Indexing' : 'Manual Indexing';
            indexStatus.innerHTML = `<i class="fas ${icon} status-info me-2"></i>${modeText}`;
            indexDetails.innerHTML = `
                <div class="small">
                    ${details}<br>
                    Progress: ${progress}% | Mode: ${autoMode ? 'Automatic' : 'Manual'}<br>
                    <small class="text-muted">Last updated: ${lastUpdated === 'In progress' ? 'In progress' : new Date(lastUpdated).toLocaleString()}</small>
                </div>
            `;
            indexStatus.className = 'status-value status-info';
            
            if (progressElement) {
                progressElement.style.display = 'block';
                const progressBar = progressElement.querySelector('.progress-bar');
                if (progressBar) {
                    progressBar.style.width = `${progress}%`;
                    progressBar.className = autoMode ? 'progress-bar bg-success' : 'progress-bar bg-info';
                }
            }
        } else if (state === 'completed') {
            indexStatus.innerHTML = '<i class="fas fa-check-circle status-online me-2"></i>Ready';
            indexDetails.innerHTML = `
                <div class="small">
                    ${details}<br>
                    <small class="text-muted">Last updated: ${lastUpdated === 'Never' ? 'Never' : new Date(lastUpdated).toLocaleString()}</small>
                    ${autoIndexing.active ? '<br><span class="badge bg-success">Auto-monitoring active</span>' : ''}
                </div>
            `;
            indexStatus.className = 'status-value status-online';
            if (progressElement) progressElement.style.display = 'none';
        } else {
            const isAutoMode = autoIndexing.monitoring && autoIndexing.mounted_shares > 0;
            indexStatus.innerHTML = `<i class="fas ${isAutoMode ? 'fa-eye' : 'fa-pause-circle'} status-warning me-2"></i>${isAutoMode ? 'Monitoring' : 'Idle'}`;
            indexDetails.innerHTML = `
                <div class="small">
                    ${details}<br>
                    <small class="text-muted">
                        ${autoIndexing.monitoring ? `Auto-monitoring: ${autoIndexing.mounted_shares} shares` : 'Auto-monitoring disabled'}<br>
                        Last check: ${autoIndexing.last_check ? new Date(autoIndexing.last_check).toLocaleString() : 'Never'}
                    </small>
                </div>
            `;
            indexStatus.className = isAutoMode ? 'status-value status-info' : 'status-value status-warning';
            if (progressElement) progressElement.style.display = 'none';
        }
    }
}

async function updateOrthancDashboard() {
    const statusElement = document.getElementById('dashboardOrthancStatus');
    const detailsElement = document.getElementById('dashboardOrthancDetails');
    
    if (!statusElement || !detailsElement) return;
    
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/orthanc/status');
        
        if (data.success && data.status === 'running') {
            statusElement.innerHTML = '<i class="fas fa-check-circle status-online me-2"></i>Connected';
            detailsElement.innerHTML = `
                <div class="small">
                    <strong>${data.version || 'Unknown'}</strong><br>
                    Patients: ${data.patients_count || 0} | Studies: ${data.studies_count || 0}
                </div>
            `;
            statusElement.className = 'status-value status-online';
        } else {
            statusElement.innerHTML = '<i class="fas fa-exclamation-circle status-offline me-2"></i>Disconnected';
            detailsElement.innerHTML = '<div class="small">PACS server not connected</div>';
            statusElement.className = 'status-value status-offline';
        }
    } catch (error) {
        statusElement.innerHTML = '<i class="fas fa-times-circle status-offline me-2"></i>Error';
        detailsElement.innerHTML = '<div class="small">Unable to check status</div>';
        statusElement.className = 'status-value status-offline';
    }
}

async function updateNasDashboard() {
    const devicesElement = document.getElementById('dashboardNasDevices');
    const detailsElement = document.getElementById('dashboardNasDetails');
    
    if (!devicesElement || !detailsElement) return;
    
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/cached-devices');
        
        if (data.success) {
            const totalDevices = data.total || 0;
            const onlineDevices = (data.devices || []).filter(d => d.reachable).length;
            const nasDevices = (data.devices || []).filter(d => 
                d.type && (d.type.toLowerCase().includes('nas') || 
                          d.type.toLowerCase().includes('storage') ||
                          d.ping_status === 'Online')
            ).length;
            
            devicesElement.innerHTML = `<i class="fas fa-server status-info me-2"></i>${totalDevices} Found`;
            detailsElement.innerHTML = `
                <div class="small">
                    Online: ${onlineDevices} | Potential NAS: ${nasDevices}<br>
                    Last scan: ${data.last_discovery ? new Date(data.last_discovery).toLocaleTimeString() : 'Never'}
                </div>
            `;
            devicesElement.className = totalDevices > 0 ? 'status-value status-online' : 'status-value status-warning';
        } else {
            devicesElement.innerHTML = '<i class="fas fa-question-circle status-warning me-2"></i>Unknown';
            detailsElement.innerHTML = '<div class="small">Unable to scan network</div>';
            devicesElement.className = 'status-value status-warning';
        }
    } catch (error) {
        devicesElement.innerHTML = '<i class="fas fa-times-circle status-offline me-2"></i>Error';
        detailsElement.innerHTML = '<div class="small">Network scan failed</div>';
        devicesElement.className = 'status-value status-offline';
    }
}

async function updateIndexDashboard() {
    const statusElement = document.getElementById('dashboardIndexStatus');
    const detailsElement = document.getElementById('dashboardIndexDetails');
    const progressElement = document.getElementById('dashboardIndexProgress');
    
    if (!statusElement || !detailsElement) return;
    
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/indexing/status');
        
        // Debug logging
        console.log('📊 Indexing status response:', data);
        console.log('📊 Full response object:', JSON.stringify(data, null, 2));
        
        if (data.success && data.status) {
            const status = data.status.state || 'idle';
            const progress = data.status.progress || 0;
            const details = data.status.details || 'No details available';
            
            console.log(`🔍 Status check: state=${status}, progress=${progress}%, details=${details}`);
            console.log(`🔍 Checking condition: status === 'running' || status === 'indexing'`);
            console.log(`🔍 Condition result: ${status === 'running' || status === 'indexing'}`);
            
            if (status === 'running' || status === 'indexing') {
                statusElement.innerHTML = '<i class="fas fa-spinner fa-spin status-info me-2"></i>Indexing';
                detailsElement.innerHTML = `<div class="small">${details}<br>Progress: ${progress}%</div>`;
                statusElement.className = 'status-value status-info';
                
                if (progressElement) {
                    progressElement.style.display = 'block';
                    const progressBar = progressElement.querySelector('.progress-bar');
                    if (progressBar) {
                        progressBar.style.width = `${progress}%`;
                    }
                }
            } else if (status === 'completed') {
                statusElement.innerHTML = '<i class="fas fa-check-circle status-online me-2"></i>Completed';
                detailsElement.innerHTML = `<div class="small">Index up to date<br>${details}</div>`;
                statusElement.className = 'status-value status-online';
                if (progressElement) progressElement.style.display = 'none';
            } else {
                statusElement.innerHTML = '<i class="fas fa-pause-circle status-warning me-2"></i>Idle';
                detailsElement.innerHTML = '<div class="small">No indexing in progress<br>Click "Start Indexing" to begin</div>';
                statusElement.className = 'status-value status-warning';
                if (progressElement) progressElement.style.display = 'none';
            }
        } else {
            statusElement.innerHTML = '<i class="fas fa-question-circle status-warning me-2"></i>Unknown';
            detailsElement.innerHTML = '<div class="small">Unable to check indexing status</div>';
            statusElement.className = 'status-value status-warning';
            if (progressElement) progressElement.style.display = 'none';
        }
    } catch (error) {
        statusElement.innerHTML = '<i class="fas fa-times-circle status-offline me-2"></i>Error';
        detailsElement.innerHTML = '<div class="small">Status check failed</div>';
        statusElement.className = 'status-value status-offline';
        if (progressElement) progressElement.style.display = 'none';
    }
}

// Auto-refresh dashboard every 30 seconds
setInterval(refreshDashboard, 30000);

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit for other components to load
    setTimeout(refreshDashboard, 1000);
});
