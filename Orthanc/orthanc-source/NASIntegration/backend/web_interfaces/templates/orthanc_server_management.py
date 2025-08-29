#!/usr/bin/env python3
"""
🇿🇦 Orthanc Server Management Interface Template
Complete server management and monitoring interface
"""

ORTHANC_SERVER_MANAGEMENT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🇿🇦 Orthanc Server Management</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            min-height: 100vh; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .main-container { 
            background: rgba(255, 255, 255, 0.95); 
            border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
            margin: 20px auto; 
            padding: 30px; 
            max-width: 1200px;
        }
        .header-section {
            background: linear-gradient(135deg, #28a745, #20c997);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        .status-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-left: 5px solid #28a745;
        }
        .status-running { border-left-color: #28a745; }
        .status-stopped { border-left-color: #dc3545; }
        .status-unknown { border-left-color: #ffc107; }
        .control-buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        .btn-server-control {
            flex: 1;
            min-width: 120px;
            padding: 12px;
            font-weight: bold;
            border-radius: 8px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .stat-number {
            font-size: 2.5rem;
            font-weight: bold;
            color: #28a745;
        }
        .stat-label {
            color: #666;
            font-size: 0.9rem;
            margin-top: 5px;
        }
        .config-section {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .log-viewer {
            background: #1e1e1e;
            color: #00ff00;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
            max-height: 300px;
            overflow-y: auto;
            margin-top: 15px;
        }
        .nav-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        .alert-custom {
            border-radius: 8px;
            border: none;
            padding: 15px;
            margin-bottom: 20px;
        }
        .quick-actions {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .connection-status {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-online { background-color: #28a745; }
        .status-offline { background-color: #dc3545; }
        .status-checking { background-color: #ffc107; animation: pulse 1s infinite; }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="main-container">
        <!-- Header -->
        <div class="header-section">
            <h1><i class="fas fa-server"></i> 🇿🇦 Orthanc PACS Server Management</h1>
            <p class="mb-0">Complete server control and monitoring dashboard</p>
        </div>

        <!-- Navigation -->
        <div class="nav-buttons">
            <a href="/" class="btn btn-outline-primary"><i class="fas fa-home"></i> Home</a>
            <a href="/user-management" class="btn btn-outline-secondary"><i class="fas fa-users"></i> Users</a>
            <a href="/device-management" class="btn btn-outline-info"><i class="fas fa-network-wired"></i> Devices</a>
            <a href="/dicom-viewer" class="btn btn-outline-success"><i class="fas fa-eye"></i> DICOM Viewer</a>
            <a href="/patient-viewer" class="btn btn-outline-warning"><i class="fas fa-user-injured"></i> Patients</a>
            <button class="btn btn-outline-dark" onclick="refreshAll()"><i class="fas fa-sync-alt"></i> Refresh</button>
        </div>

        <!-- Server Status -->
        <div class="status-card" id="serverStatus">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h4><span class="connection-status status-checking" id="statusIndicator"></span>Server Status</h4>
                    <p class="mb-0" id="statusText">Checking server status...</p>
                    <small class="text-muted" id="statusDetails">Please wait while we check the Orthanc server</small>
                </div>
                <div class="text-end">
                    <div class="h5 mb-0" id="serverUptime">--:--:--</div>
                    <small class="text-muted">Uptime</small>
                </div>
            </div>
        </div>

        <!-- Server Controls -->
        <div class="control-buttons">
            <button class="btn btn-success btn-server-control" onclick="startServer()">
                <i class="fas fa-play"></i> Start Server
            </button>
            <button class="btn btn-danger btn-server-control" onclick="stopServer()">
                <i class="fas fa-stop"></i> Stop Server
            </button>
            <button class="btn btn-warning btn-server-control" onclick="restartServer()">
                <i class="fas fa-redo"></i> Restart Server
            </button>
            <button class="btn btn-info btn-server-control" onclick="openOrthancWeb()">
                <i class="fas fa-external-link-alt"></i> Open Orthanc Web
            </button>
        </div>

        <!-- Quick Stats -->
        <div class="stats-grid" id="statsGrid">
            <div class="stat-card">
                <div class="stat-number" id="patientCount">--</div>
                <div class="stat-label">Patients</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="studyCount">--</div>
                <div class="stat-label">Studies</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="seriesCount">--</div>
                <div class="stat-label">Series</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="instanceCount">--</div>
                <div class="stat-label">Instances</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="storageSize">--</div>
                <div class="stat-label">Storage Used</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="activeConnections">--</div>
                <div class="stat-label">Active Connections</div>
            </div>
        </div>

        <!-- Quick Actions -->
        <div class="quick-actions">
            <h5><i class="fas fa-bolt"></i> Quick Actions</h5>
            <div class="row">
                <div class="col-md-6">
                    <button class="btn btn-outline-primary w-100 mb-2" onclick="quickSetup()">
                        <i class="fas fa-magic"></i> Quick Setup Wizard
                    </button>
                    <button class="btn btn-outline-success w-100 mb-2" onclick="viewPatients()">
                        <i class="fas fa-users"></i> View All Patients
                    </button>
                </div>
                <div class="col-md-6">
                    <button class="btn btn-outline-info w-100 mb-2" onclick="showConfig()">
                        <i class="fas fa-cog"></i> Server Configuration
                    </button>
                    <button class="btn btn-outline-warning w-100 mb-2" onclick="showLogs()">
                        <i class="fas fa-file-alt"></i> View Server Logs
                    </button>
                </div>
            </div>
        </div>

        <!-- Configuration Section -->
        <div class="config-section" id="configSection" style="display: none;">
            <h5><i class="fas fa-cog"></i> Server Configuration</h5>
            <div class="row">
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label">Hospital Name</label>
                        <input type="text" class="form-control" id="hospitalName" placeholder="SA Healthcare PACS">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Web Port</label>
                        <input type="number" class="form-control" id="webPort" placeholder="8042">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">DICOM Port</label>
                        <input type="number" class="form-control" id="dicomPort" placeholder="4242">
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label">AET Title</label>
                        <input type="text" class="form-control" id="aetTitle" placeholder="ORTHANC">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Storage Directory</label>
                        <input type="text" class="form-control" id="storageDir" placeholder="./orthanc-storage">
                    </div>
                    <div class="mb-3">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="allowRemote">
                            <label class="form-check-label" for="allowRemote">
                                Allow Remote Access
                            </label>
                        </div>
                    </div>
                </div>
            </div>
            <div class="text-end">
                <button class="btn btn-secondary me-2" onclick="hideConfig()">Cancel</button>
                <button class="btn btn-primary" onclick="saveConfig()">Save Configuration</button>
            </div>
        </div>

        <!-- Log Viewer -->
        <div class="config-section" id="logSection" style="display: none;">
            <h5><i class="fas fa-file-alt"></i> Server Logs</h5>
            <div class="log-viewer" id="logViewer">
                Loading server logs...
            </div>
            <div class="text-end mt-3">
                <button class="btn btn-secondary me-2" onclick="hideLogs()">Close</button>
                <button class="btn btn-outline-primary" onclick="refreshLogs()">Refresh Logs</button>
            </div>
        </div>

        <!-- Loading Indicator -->
        <div class="loading" id="loadingIndicator">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Processing request...</p>
        </div>

        <!-- Alerts Container -->
        <div id="alertsContainer"></div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Global state
        let serverStatus = 'unknown';
        let refreshInterval;

        // Initialize page
        document.addEventListener('DOMContentLoaded', function() {
            checkServerStatus();
            loadQuickStats();
            startAutoRefresh();
        });

        // Auto-refresh every 30 seconds
        function startAutoRefresh() {
            refreshInterval = setInterval(() => {
                checkServerStatus();
                loadQuickStats();
            }, 30000);
        }

        // Check server status
        async function checkServerStatus() {
            try {
                const response = await fetch('/api/orthanc/status');
                const data = await response.json();
                
                if (data.success) {
                    updateServerStatus(data.status);
                } else {
                    updateServerStatus({ status: 'error', message: data.error });
                }
            } catch (error) {
                console.error('Error checking server status:', error);
                updateServerStatus({ status: 'offline', message: 'Cannot connect to server' });
            }
        }

        // Update server status display
        function updateServerStatus(status) {
            const statusCard = document.getElementById('serverStatus');
            const statusIndicator = document.getElementById('statusIndicator');
            const statusText = document.getElementById('statusText');
            const statusDetails = document.getElementById('statusDetails');
            const uptimeElement = document.getElementById('serverUptime');

            // Update status indicator
            statusIndicator.className = 'connection-status';
            
            if (status.status === 'running') {
                statusIndicator.classList.add('status-online');
                statusCard.className = 'status-card status-running';
                statusText.textContent = 'Server Running';
                statusDetails.textContent = `Orthanc PACS server is operational on port ${status.port || '8042'}`;
                uptimeElement.textContent = status.uptime || '--:--:--';
            } else if (status.status === 'stopped') {
                statusIndicator.classList.add('status-offline');
                statusCard.className = 'status-card status-stopped';
                statusText.textContent = 'Server Stopped';
                statusDetails.textContent = 'Orthanc PACS server is not running';
                uptimeElement.textContent = '--:--:--';
            } else {
                statusIndicator.classList.add('status-checking');
                statusCard.className = 'status-card status-unknown';
                statusText.textContent = 'Status Unknown';
                statusDetails.textContent = status.message || 'Unable to determine server status';
                uptimeElement.textContent = '--:--:--';
            }

            serverStatus = status.status;
        }

        // Load quick stats
        async function loadQuickStats() {
            try {
                const response = await fetch('/api/orthanc/quick-stats');
                const data = await response.json();
                
                if (data.success) {
                    updateStats(data.stats);
                }
            } catch (error) {
                console.error('Error loading stats:', error);
                updateStats({});
            }
        }

        // Update stats display
        function updateStats(stats) {
            document.getElementById('patientCount').textContent = stats.patients || '--';
            document.getElementById('studyCount').textContent = stats.studies || '--';
            document.getElementById('seriesCount').textContent = stats.series || '--';
            document.getElementById('instanceCount').textContent = stats.instances || '--';
            document.getElementById('storageSize').textContent = stats.storage_size || '--';
            document.getElementById('activeConnections').textContent = stats.connections || '--';
        }

        // Server control functions
        async function startServer() {
            await serverAction('start', 'Starting Orthanc server...');
        }

        async function stopServer() {
            await serverAction('stop', 'Stopping Orthanc server...');
        }

        async function restartServer() {
            await serverAction('restart', 'Restarting Orthanc server...');
        }

        // Generic server action
        async function serverAction(action, message) {
            showLoading(message);
            
            try {
                const response = await fetch(`/api/orthanc/${action}`, {
                    method: 'POST',
                    credentials: 'include'
                });
                const data = await response.json();
                
                hideLoading();
                
                if (data.success) {
                    showAlert('success', `Server ${action} completed successfully`);
                    setTimeout(checkServerStatus, 2000);
                } else {
                    showAlert('danger', `Failed to ${action} server: ${data.error}`);
                }
            } catch (error) {
                hideLoading();
                showAlert('danger', `Error during ${action}: ${error.message}`);
            }
        }

        // Quick setup wizard
        async function quickSetup() {
            const hospitalName = prompt('Enter hospital name:', 'SA Healthcare PACS');
            if (!hospitalName) return;

            const webPort = prompt('Enter web port:', '8042');
            if (!webPort) return;

            const dicomPort = prompt('Enter DICOM port:', '4242');
            if (!dicomPort) return;

            showLoading('Setting up Orthanc server...');

            try {
                const response = await fetch('/api/orthanc/quick-setup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({
                        hospital_name: hospitalName,
                        web_port: parseInt(webPort),
                        dicom_port: parseInt(dicomPort),
                        allow_remote: true
                    })
                });

                const data = await response.json();
                hideLoading();

                if (data.success) {
                    showAlert('success', 'Quick setup completed! Server is starting...');
                    setTimeout(() => {
                        checkServerStatus();
                        loadQuickStats();
                    }, 3000);
                } else {
                    showAlert('danger', `Setup failed: ${data.error}`);
                }
            } catch (error) {
                hideLoading();
                showAlert('danger', `Setup error: ${error.message}`);
            }
        }

        // Configuration management
        function showConfig() {
            document.getElementById('configSection').style.display = 'block';
            loadCurrentConfig();
        }

        function hideConfig() {
            document.getElementById('configSection').style.display = 'none';
        }

        async function loadCurrentConfig() {
            try {
                const response = await fetch('/api/orthanc/config');
                const data = await response.json();
                
                if (data.success) {
                    const config = data.config;
                    document.getElementById('hospitalName').value = config.Name || '';
                    document.getElementById('webPort').value = config.HttpPort || '';
                    document.getElementById('dicomPort').value = config.DicomPort || '';
                    document.getElementById('aetTitle').value = config.DicomAet || '';
                    document.getElementById('storageDir').value = config.StorageDirectory || '';
                    document.getElementById('allowRemote').checked = config.RemoteAccessAllowed || false;
                }
            } catch (error) {
                console.error('Error loading config:', error);
            }
        }

        async function saveConfig() {
            const config = {
                Name: document.getElementById('hospitalName').value,
                HttpPort: parseInt(document.getElementById('webPort').value),
                DicomPort: parseInt(document.getElementById('dicomPort').value),
                DicomAet: document.getElementById('aetTitle').value,
                StorageDirectory: document.getElementById('storageDir').value,
                RemoteAccessAllowed: document.getElementById('allowRemote').checked
            };

            showLoading('Saving configuration...');

            try {
                const response = await fetch('/api/orthanc/config', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify(config)
                });

                const data = await response.json();
                hideLoading();

                if (data.success) {
                    showAlert('success', 'Configuration saved successfully');
                    hideConfig();
                } else {
                    showAlert('danger', `Failed to save configuration: ${data.error}`);
                }
            } catch (error) {
                hideLoading();
                showAlert('danger', `Configuration error: ${error.message}`);
            }
        }

        // Log viewer
        function showLogs() {
            document.getElementById('logSection').style.display = 'block';
            refreshLogs();
        }

        function hideLogs() {
            document.getElementById('logSection').style.display = 'none';
        }

        function refreshLogs() {
            const logViewer = document.getElementById('logViewer');
            logViewer.innerHTML = 'Loading server logs...\\n\\nThis feature will show Orthanc server logs when available.\\n\\nLog entries will appear here in real-time.';
        }

        // Navigation functions
        function openOrthancWeb() {
            const port = serverStatus === 'running' ? '8042' : '8042';
            window.open(`http://localhost:${port}`, '_blank');
        }

        function viewPatients() {
            window.location.href = '/patient-viewer';
        }

        function refreshAll() {
            checkServerStatus();
            loadQuickStats();
            showAlert('info', 'Refreshing all data...');
        }

        // Utility functions
        function showLoading(message = 'Loading...') {
            const loading = document.getElementById('loadingIndicator');
            loading.querySelector('p').textContent = message;
            loading.style.display = 'block';
        }

        function hideLoading() {
            document.getElementById('loadingIndicator').style.display = 'none';
        }

        function showAlert(type, message) {
            const alertsContainer = document.getElementById('alertsContainer');
            const alertId = 'alert-' + Date.now();
            
            const alertHtml = `
                <div class="alert alert-${type} alert-dismissible fade show alert-custom" id="${alertId}" role="alert">
                    <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-triangle' : 'info-circle'}"></i>
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
            
            alertsContainer.insertAdjacentHTML('beforeend', alertHtml);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                const alert = document.getElementById(alertId);
                if (alert) {
                    alert.remove();
                }
            }, 5000);
        }

        // Cleanup on page unload
        window.addEventListener('beforeunload', function() {
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }
        });
    </script>
</body>
</html>
"""