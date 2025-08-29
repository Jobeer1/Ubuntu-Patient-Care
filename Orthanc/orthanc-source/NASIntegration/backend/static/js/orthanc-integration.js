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
    const searchCriteria = {
        patient_id: document.getElementById('patientId')?.value || '',
        patient_name: document.getElementById('patientName')?.value || '',
        study_date: document.getElementById('studyDate')?.value || '',
        modality: document.getElementById('modality')?.value || ''
    };
    
    if (!searchCriteria.patient_id && !searchCriteria.patient_name && 
        !searchCriteria.study_date && !searchCriteria.modality) {
        window.NASIntegration.core.showMessage('Please enter at least one search criterion', 'warning');
        return;
    }
    
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/patients/search', {
            method: 'POST',
            body: JSON.stringify(searchCriteria)
        });
        
        const resultsElement = document.getElementById('searchResults');
        if (resultsElement) {
            resultsElement.innerHTML = formatPatientResults(data.patients || []);
        }
        
        window.NASIntegration.core.showMessage(`✅ Search completed. Found ${data.patients?.length || 0} results`, 'success');
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

// Share link generation
async function generateShareLink() {
    const shareConfig = {
        patient_id: document.getElementById('sharePatientId')?.value || '',
        study_id: document.getElementById('shareStudyId')?.value || '',
        expires_hours: parseInt(document.getElementById('shareExpiry')?.value) || 24,
        password_protected: document.getElementById('sharePassword')?.checked || false
    };
    
    if (!shareConfig.patient_id && !shareConfig.study_id) {
        window.NASIntegration.core.showMessage('Please enter Patient ID or Study ID', 'warning');
        return;
    }
    
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/share/generate', {
            method: 'POST',
            body: JSON.stringify(shareConfig)
        });
        
        if (data.success) {
            document.getElementById('generatedLink').value = data.share_url;
            window.NASIntegration.core.showMessage(`✅ Share link generated! Expires in ${data.expires}`, 'success');
        } else {
            window.NASIntegration.core.showMessage(`❌ Failed to generate link: ${data.error}`, 'error');
        }
    } catch (error) {
        window.NASIntegration.core.showMessage(`❌ Share link error: ${error.message}`, 'error');
    }
}

function copyLinkToClipboard() {
    const linkField = document.getElementById('generatedLink');
    if (linkField && linkField.value) {
        linkField.select();
        document.execCommand('copy');
        window.NASIntegration.core.showMessage('✅ Link copied to clipboard!', 'success');
    } else {
        window.NASIntegration.core.showMessage('No link to copy - generate a link first', 'error');
    }
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
