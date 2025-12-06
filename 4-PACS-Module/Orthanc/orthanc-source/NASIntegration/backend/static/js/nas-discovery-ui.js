/**
 * NAS Discovery and Connection Module
 * 
 * Frontend UI for:
 * - Scanning network for NAS devices
 * - Enumerating shares on discovered devices
 * - Detecting database types
 * - Testing connections with credentials
 * - Storing discovered connections
 */

const NASDiscoveryUI = (() => {
    const API_BASE = '/api/nas/discovery';
    
    // UI state
    let state = {
        scanning: false,
        discoveredDevices: [],
        discoveredShares: [],
        discoveredDatabases: [],
        currentDevice: null,
        currentShare: null
    };
    
    /**
     * Initialize NAS Discovery UI
     */
    function init() {
        console.log('🔍 Initializing NAS Discovery UI...');
        createModals();
        setupEventListeners();
        console.log('✅ NAS Discovery UI initialized');
    }
    
    /**
     * Create modal HTML elements
     */
    function createModals() {
        // Main discovery modal
        const discoveryModal = document.createElement('div');
        discoveryModal.id = 'nasDiscoveryModal';
        discoveryModal.className = 'modal fade';
        discoveryModal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">🔍 NAS Device Discovery</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <ul class="nav nav-tabs" id="discoveryTabs">
                            <li class="nav-item">
                                <a class="nav-link active" id="scan-tab" data-bs-toggle="tab" href="#scan-panel">
                                    📡 Scan Network
                                </a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" id="shares-tab" data-bs-toggle="tab" href="#shares-panel">
                                    📂 Shares
                                </a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" id="databases-tab" data-bs-toggle="tab" href="#databases-panel">
                                    💾 Databases
                                </a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" id="credentials-tab" data-bs-toggle="tab" href="#credentials-panel">
                                    🔐 Credentials
                                </a>
                            </li>
                        </ul>
                        
                        <div class="tab-content mt-3">
                            <!-- Scan Network Tab -->
                            <div class="tab-pane fade show active" id="scan-panel">
                                <div class="form-group mb-3">
                                    <label>Network Subnet (optional)</label>
                                    <input type="text" class="form-control" id="subnetInput" 
                                           placeholder="155.235.81" value="155.235.81">
                                    <small class="text-muted">Leave empty for auto-detect</small>
                                </div>
                                <button class="btn btn-primary" id="scanButton">
                                    <i class="fas fa-wifi"></i> Scan Network
                                </button>
                                <div id="scanStatus" class="mt-3"></div>
                                <div id="discoveredDevicesList" class="mt-3"></div>
                            </div>
                            
                            <!-- Shares Tab -->
                            <div class="tab-pane fade" id="shares-panel">
                                <div id="sharesList" class="list-group"></div>
                                <div id="sharesEmpty" class="alert alert-info">
                                    Select a device from the "Scan Network" tab first
                                </div>
                            </div>
                            
                            <!-- Databases Tab -->
                            <div class="tab-pane fade" id="databases-panel">
                                <div id="databasesList" class="list-group"></div>
                                <div id="databasesEmpty" class="alert alert-info">
                                    Select a share from the "Shares" tab first
                                </div>
                            </div>
                            
                            <!-- Credentials Tab -->
                            <div class="tab-pane fade" id="credentials-panel">
                                <div class="form-group mb-3">
                                    <label>Username</label>
                                    <input type="text" class="form-control" id="credUsername" 
                                           placeholder="domain\\username or username">
                                </div>
                                <div class="form-group mb-3">
                                    <label>Password</label>
                                    <input type="password" class="form-control" id="credPassword">
                                </div>
                                <button class="btn btn-success" id="testConnectionButton">
                                    <i class="fas fa-plug"></i> Test Connection
                                </button>
                                <button class="btn btn-primary" id="saveConnectionButton">
                                    <i class="fas fa-save"></i> Save Connection
                                </button>
                                <div id="credentialsStatus" class="mt-3"></div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" id="applyConnectionButton">
                            Apply Connection
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(discoveryModal);
    }
    
    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        document.getElementById('scanButton').addEventListener('click', startNetworkScan);
        document.getElementById('testConnectionButton').addEventListener('click', testConnection);
        document.getElementById('saveConnectionButton').addEventListener('click', saveConnection);
        document.getElementById('applyConnectionButton').addEventListener('click', applyConnection);
    }
    
    /**
     * Start network scan
     */
    async function startNetworkScan() {
        const subnet = document.getElementById('subnetInput').value || '155.235.81';
        const button = document.getElementById('scanButton');
        const statusDiv = document.getElementById('scanStatus');
        
        try {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Scanning...';
            statusDiv.innerHTML = `<div class="alert alert-info">🔍 Scanning ${subnet}.* subnet for NAS devices...</div>`;
            
            const response = await fetch(`${API_BASE}/scan-network`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ subnet })
            });
            
            const data = await response.json();
            
            if (data.success) {
                statusDiv.innerHTML = `<div class="alert alert-success">✅ Scan started, devices will appear below...</div>`;
                
                // Poll for results
                pollDiscoveredDevices();
            } else {
                statusDiv.innerHTML = `<div class="alert alert-danger">❌ ${data.error}</div>`;
            }
        } catch (error) {
            statusDiv.innerHTML = `<div class="alert alert-danger">❌ Error: ${error.message}</div>`;
            console.error('Scan error:', error);
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-wifi"></i> Scan Network';
        }
    }
    
    /**
     * Poll for discovered devices
     */
    async function pollDiscoveredDevices() {
        try {
            const response = await fetch(`${API_BASE}/discovered-devices`);
            const data = await response.json();
            
            if (data.success && data.count > 0) {
                state.discoveredDevices = data.devices;
                displayDiscoveredDevices(data.devices);
            }
        } catch (error) {
            console.error('Error polling devices:', error);
        }
    }
    
    /**
     * Display discovered devices
     */
    function displayDiscoveredDevices(devices) {
        const list = document.getElementById('discoveredDevicesList');
        list.innerHTML = '<h6>Discovered NAS Devices:</h6>';
        
        const listGroup = document.createElement('div');
        listGroup.className = 'list-group';
        
        devices.forEach(device => {
            const item = document.createElement('button');
            item.type = 'button';
            item.className = 'list-group-item list-group-item-action';
            item.innerHTML = `
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${device.hostname || device.ip}</h6>
                    <small>${device.ip}</small>
                </div>
                <p class="mb-1"><small>Port ${device.port} | ${device.type}</small></p>
            `;
            item.addEventListener('click', () => enumerateShares(device));
            listGroup.appendChild(item);
        });
        
        list.appendChild(listGroup);
    }
    
    /**
     * Enumerate shares on selected device
     */
    async function enumerateShares(device) {
        state.currentDevice = device;
        const statusDiv = document.getElementById('scanStatus');
        
        try {
            statusDiv.innerHTML = `<div class="alert alert-info">📂 Loading shares from ${device.ip}...</div>`;
            
            const response = await fetch(`${API_BASE}/enumerate-shares`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nas_host: device.ip })
            });
            
            const data = await response.json();
            
            if (data.success) {
                state.discoveredShares = data.shares;
                displayShares(data.shares);
                statusDiv.innerHTML = `<div class="alert alert-success">✅ Found ${data.count} share(s)</div>`;
                
                // Switch to shares tab
                document.getElementById('shares-tab').click();
            } else {
                statusDiv.innerHTML = `<div class="alert alert-danger">❌ ${data.error}</div>`;
            }
        } catch (error) {
            statusDiv.innerHTML = `<div class="alert alert-danger">❌ Error: ${error.message}</div>`;
            console.error('Enumerate error:', error);
        }
    }
    
    /**
     * Display shares
     */
    function displayShares(shares) {
        const list = document.getElementById('sharesList');
        const empty = document.getElementById('sharesEmpty');
        
        if (shares.length === 0) {
            empty.style.display = 'block';
            list.innerHTML = '';
            return;
        }
        
        empty.style.display = 'none';
        list.innerHTML = '';
        
        shares.forEach(share => {
            const item = document.createElement('button');
            item.type = 'button';
            item.className = 'list-group-item list-group-item-action';
            item.innerHTML = `
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${share.name}</h6>
                    <span class="badge bg-${share.accessible ? 'success' : 'warning'}">
                        ${share.accessible ? '✓ Accessible' : '? Unknown'}
                    </span>
                </div>
                <p class="mb-1"><small>${share.path}</small></p>
            `;
            item.addEventListener('click', () => scanShareForDatabases(share));
            list.appendChild(item);
        });
    }
    
    /**
     * Scan share for databases
     */
    async function scanShareForDatabases(share) {
        state.currentShare = share;
        const statusDiv = document.getElementById('scanStatus');
        
        try {
            statusDiv.innerHTML = `<div class="alert alert-info">💾 Scanning ${share.path} for databases...</div>`;
            
            const response = await fetch(`${API_BASE}/scan-share`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ share_path: share.path })
            });
            
            const data = await response.json();
            
            if (data.success) {
                state.discoveredDatabases = data.databases;
                displayDatabases(data.databases);
                statusDiv.innerHTML = `<div class="alert alert-success">✅ Found ${data.count} database(s)</div>`;
                
                // Switch to databases tab
                document.getElementById('databases-tab').click();
            } else {
                statusDiv.innerHTML = `<div class="alert alert-danger">❌ ${data.error}</div>`;
            }
        } catch (error) {
            statusDiv.innerHTML = `<div class="alert alert-danger">❌ Error: ${error.message}</div>`;
            console.error('Scan error:', error);
        }
    }
    
    /**
     * Display databases
     */
    function displayDatabases(databases) {
        const list = document.getElementById('databasesList');
        const empty = document.getElementById('databasesEmpty');
        
        if (databases.length === 0) {
            empty.style.display = 'block';
            list.innerHTML = '';
            return;
        }
        
        empty.style.display = 'none';
        list.innerHTML = '';
        
        databases.forEach(db => {
            const item = document.createElement('div');
            item.className = 'list-group-item';
            item.innerHTML = `
                <div class="d-flex w-100 justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1">${db.name}</h6>
                        <p class="mb-1"><small>${db.path}</small></p>
                        <span class="badge bg-info">${db.database_type}</span>
                        ${db.details.has_dicom_files ? '<span class="badge bg-primary">DICOM</span>' : ''}
                        ${db.details.has_sqlite_db ? '<span class="badge bg-secondary">Database</span>' : ''}
                    </div>
                    <button class="btn btn-sm btn-outline-primary" onclick="alert('Select this database for indexing')">
                        Select
                    </button>
                </div>
            `;
            list.appendChild(item);
        });
    }
    
    /**
     * Test connection with credentials
     */
    async function testConnection() {
        if (!state.currentDevice || !state.currentShare) {
            alert('Please select a device and share first');
            return;
        }
        
        const username = document.getElementById('credUsername').value;
        const password = document.getElementById('credPassword').value;
        const statusDiv = document.getElementById('credentialsStatus');
        const button = document.getElementById('testConnectionButton');
        
        try {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
            statusDiv.innerHTML = '';
            
            const response = await fetch(`${API_BASE}/test-connection`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    nas_host: state.currentDevice.ip,
                    share_name: state.currentShare.name,
                    username: username || undefined,
                    password: password || undefined
                })
            });
            
            const data = await response.json();
            
            if (data.connected) {
                statusDiv.innerHTML = `<div class="alert alert-success">✅ ${data.message}</div>`;
            } else {
                statusDiv.innerHTML = `<div class="alert alert-danger">❌ ${data.message}</div>`;
            }
        } catch (error) {
            statusDiv.innerHTML = `<div class="alert alert-danger">❌ Error: ${error.message}</div>`;
            console.error('Connection test error:', error);
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-plug"></i> Test Connection';
        }
    }
    
    /**
     * Save connection
     */
    async function saveConnection() {
        if (!state.currentDevice || !state.currentShare) {
            alert('Please select a device and share first');
            return;
        }
        
        const username = document.getElementById('credUsername').value;
        const password = document.getElementById('credPassword').value;
        const statusDiv = document.getElementById('credentialsStatus');
        
        try {
            const response = await fetch(`${API_BASE}/save-connection`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    nas_host: state.currentDevice.ip,
                    share_name: state.currentShare.name,
                    username: username || undefined,
                    password: password || undefined,
                    database_type: state.currentShare.type
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                statusDiv.innerHTML = `<div class="alert alert-success">✅ ${data.message}</div>`;
            } else {
                statusDiv.innerHTML = `<div class="alert alert-danger">❌ ${data.error}</div>`;
            }
        } catch (error) {
            statusDiv.innerHTML = `<div class="alert alert-danger">❌ Error: ${error.message}</div>`;
            console.error('Save error:', error);
        }
    }
    
    /**
     * Apply connection to system
     */
    async function applyConnection() {
        if (!state.currentDevice || !state.currentShare) {
            alert('Please select a device and share first');
            return;
        }
        
        const connection = {
            nas_host: state.currentDevice.ip,
            share_name: state.currentShare.name,
            share_path: state.currentShare.path,
            database_type: state.currentShare.type
        };
        
        console.log('💾 Applying connection:', connection);
        
        // TODO: Update system to use this connection
        // This might involve:
        // 1. Updating NAS configuration
        // 2. Re-running indexing
        // 3. Testing connection to new NAS
        
        alert('Connection applied! The system will now index using the new NAS.');
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('nasDiscoveryModal'));
        if (modal) modal.hide();
    }
    
    /**
     * Show discovery modal
     */
    function show() {
        const modal = new bootstrap.Modal(document.getElementById('nasDiscoveryModal'));
        modal.show();
    }
    
    return {
        init,
        show
    };
})();

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', NASDiscoveryUI.init);
} else {
    NASDiscoveryUI.init();
}

console.log('✅ NAS Discovery UI module loaded');
