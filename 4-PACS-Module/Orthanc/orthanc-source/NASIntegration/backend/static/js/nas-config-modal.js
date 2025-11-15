/**
 * 🇿🇦 NAS Configuration Modal
 * Provides UI for selecting and switching between NAS configurations
 */

// Initialize NAS configuration UI
function initializeNASConfigurationUI() {
    console.log('🔧 Initializing NAS Configuration UI...');
    
    // Add click handler to NAS Devices card
    const nasDevicesCard = document.getElementById('dashboardNasDevices');
    if (nasDevicesCard) {
        nasDevicesCard.parentElement.parentElement.addEventListener('click', function(e) {
            // Only trigger on click, not on child elements with their own handlers
            if (e.target === nasDevicesCard || e.target.parentElement === nasDevicesCard) {
                showNASConfigurationModal();
            }
        });
    }
    
    // Load and display current NAS configuration
    loadCurrentNASConfig();
}

// Load current NAS configuration from backend
function loadCurrentNASConfig() {
    fetch('/api/nas/indexing/config/active')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateNASDeviceDisplay(data);
            } else {
                console.warn('Could not load active NAS config:', data.error);
            }
        })
        .catch(error => console.error('Error loading NAS config:', error));
}

// Update the NAS Devices display on dashboard
function updateNASDeviceDisplay(config) {
    const nasDevicesElement = document.getElementById('dashboardNasDevices');
    const nasDetailsElement = document.getElementById('dashboardNasDetails');
    
    if (nasDevicesElement && config.path) {
        // Extract NAS name/IP from path
        const nasPath = config.path;
        const pathMatch = nasPath.match(/\\\\([^\\]+)\\/);
        const nasAddress = pathMatch ? pathMatch[1] : 'Unknown';
        
        nasDevicesElement.innerHTML = `
            <span class="badge bg-success" style="cursor: pointer; font-size: 0.9rem;">
                <i class="fas fa-server me-1"></i>${nasAddress}
            </span>
        `;
        
        // Make it clickable
        nasDevicesElement.style.cursor = 'pointer';
        nasDevicesElement.addEventListener('click', showNASConfigurationModal);
        
        // Show modalities if available
        if (config.modalities && config.modalities.length > 0) {
            const modalityCount = config.modalities.length;
            const modalitiesStr = config.modalities.slice(0, 3).join(', ') + 
                                  (modalityCount > 3 ? ` +${modalityCount - 3}` : '');
            
            if (nasDetailsElement) {
                nasDetailsElement.innerHTML = `
                    <div style="font-size: 0.85rem; color: #666;">
                        <div><strong>Modalities:</strong> ${modalitiesStr}</div>
                        <div><strong>Status:</strong> ${config.enabled ? '✅ Active' : '⚠️ Inactive'}</div>
                        <div style="margin-top: 0.5rem; color: #0066cc; cursor: pointer;" onclick="showNASConfigurationModal()">
                            🔧 Click to configure...
                        </div>
                    </div>
                `;
            }
        }
    }
}

// Show NAS Configuration Modal
function showNASConfigurationModal() {
    console.log('📋 Opening NAS Configuration Modal...');
    
    // Create or show modal
    let modal = document.getElementById('nasConfigModal');
    if (!modal) {
        modal = createNASConfigModal();
        document.body.appendChild(modal);
    }
    
    // Load configurations
    loadNASConfigurations();
    
    // Show modal
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
}

// Create NAS Configuration Modal
function createNASConfigModal() {
    const modalDiv = document.createElement('div');
    modalDiv.id = 'nasConfigModal';
    modalDiv.className = 'modal fade';
    modalDiv.tabIndex = '-1';
    
    modalDiv.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header bg-primary text-white">
                    <h5 class="modal-title">
                        <i class="fas fa-server me-2"></i>NAS Configuration
                    </h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                
                <div class="modal-body">
                    <!-- Current Configuration -->
                    <div class="mb-4">
                        <h6 class="mb-2">
                            <i class="fas fa-check-circle text-success me-2"></i>Active Configuration
                        </h6>
                        <div id="currentNasConfig" class="alert alert-info">
                            <span class="spinner-border spinner-border-sm me-2"></span>Loading...
                        </div>
                    </div>
                    
                    <!-- Available Configurations -->
                    <div class="mb-4">
                        <h6 class="mb-2">
                            <i class="fas fa-list me-2"></i>Available NAS Configurations
                        </h6>
                        <div id="nasConfigList" class="list-group" style="max-height: 400px; overflow-y: auto;">
                            <div class="text-muted text-center py-3">
                                <span class="spinner-border spinner-border-sm me-2"></span>Loading configurations...
                            </div>
                        </div>
                    </div>
                    
                    <!-- Configuration Details -->
                    <div id="nasConfigDetails" style="display: none;">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h6 class="card-title" id="detailsTitle">Configuration Details</h6>
                                <dl class="row small">
                                    <dt class="col-sm-4">Path:</dt>
                                    <dd class="col-sm-8"><code id="detailsPath"></code></dd>
                                    
                                    <dt class="col-sm-4">Status:</dt>
                                    <dd class="col-sm-8"><span id="detailsStatus"></span></dd>
                                    
                                    <dt class="col-sm-4">Modalities:</dt>
                                    <dd class="col-sm-8" id="detailsModalities"></dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="button" class="btn btn-primary" id="nasCheckAccessibilityBtn" onclick="checkNASAccessibility()">
                        <i class="fas fa-check me-1"></i>Check Accessibility
                    </button>
                    <button type="button" class="btn btn-success" id="nasSwitchBtn" onclick="switchNASConfiguration()" style="display: none;">
                        <i class="fas fa-exchange-alt me-1"></i>Switch to This NAS
                    </button>
                </div>
            </div>
        </div>
    `;
    
    return modalDiv;
}

// Load and display all NAS configurations
function loadNASConfigurations() {
    console.log('📂 Loading NAS configurations...');
    
    fetch('/api/nas/indexing/config/all')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayNASConfigurations(data.configs, data.active_alias);
                updateCurrentNASDisplay(data.configs[data.active_alias]);
            } else {
                showNASConfigError('Failed to load configurations: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error loading NAS configurations:', error);
            showNASConfigError('Failed to load configurations: ' + error.message);
        });
}

// Display NAS configurations as list items
function displayNASConfigurations(configs, activeAlias) {
    const configList = document.getElementById('nasConfigList');
    if (!configList) return;
    
    configList.innerHTML = '';
    
    // Sort configurations: active first, then enabled
    const sortedConfigs = Object.entries(configs).sort((a, b) => {
        if (a[0] === activeAlias) return -1;
        if (b[0] === activeAlias) return 1;
        return b[1].enabled - a[1].enabled;
    });
    
    sortedConfigs.forEach(([alias, config]) => {
        const item = document.createElement('a');
        item.href = '#';
        item.className = 'list-group-item list-group-item-action ' + 
                        (config.is_active ? 'active' : '');
        
        const statusIcon = config.is_active ? '✅' : 
                          config.enabled ? '✔️' : '❌';
        
        const nasAddress = extractNASAddress(config.path);
        const modalityCount = config.modalities ? config.modalities.length : 0;
        
        item.innerHTML = `
            <div class="d-flex w-100 justify-content-between align-items-start">
                <div style="flex: 1;">
                    <h6 class="mb-1">
                        <span class="me-2">${statusIcon}</span>
                        <strong>${alias}</strong>
                    </h6>
                    <p class="mb-1 text-muted" style="font-size: 0.85rem;">
                        <code>${nasAddress}</code>
                    </p>
                    <small class="text-muted">
                        ${config.description || 'No description'}
                    </small>
                    <br>
                    <small class="text-muted">
                        <i class="fas fa-cube me-1"></i>${modalityCount} modalities
                    </small>
                </div>
                <div>
                    ${config.is_active ? 
                        '<span class="badge bg-success">ACTIVE</span>' :
                        '<span class="badge bg-secondary">Inactive</span>'
                    }
                </div>
            </div>
        `;
        
        item.addEventListener('click', (e) => {
            e.preventDefault();
            selectNASConfiguration(alias, config);
        });
        
        configList.appendChild(item);
    });
}

// Select a NAS configuration
function selectNASConfiguration(alias, config) {
    console.log(`📌 Selected NAS configuration: ${alias}`);
    
    // Update details panel
    const detailsDiv = document.getElementById('nasConfigDetails');
    if (detailsDiv) {
        detailsDiv.style.display = 'block';
        document.getElementById('detailsTitle').textContent = `${alias} Configuration`;
        document.getElementById('detailsPath').textContent = config.path;
        document.getElementById('detailsStatus').innerHTML = 
            config.enabled ? '<span class="badge bg-success">Enabled</span>' : 
            '<span class="badge bg-secondary">Disabled</span>';
        document.getElementById('detailsModalities').textContent = 
            config.modalities ? config.modalities.join(', ') : 'None specified';
    }
    
    // Show switch button if not active
    const switchBtn = document.getElementById('nasSwitchBtn');
    if (switchBtn) {
        switchBtn.style.display = config.is_active ? 'none' : 'block';
        switchBtn.onclick = () => performNASSwitch(alias);
    }
    
    // Store selected config for switching
    window.selectedNASConfig = { alias, config };
}

// Update current NAS display
function updateCurrentNASDisplay(activeConfig) {
    const currentDiv = document.getElementById('currentNasConfig');
    if (!currentDiv) return;
    
    const nasAddress = extractNASAddress(activeConfig.path);
    const modalityCount = activeConfig.modalities ? activeConfig.modalities.length : 0;
    
    currentDiv.innerHTML = `
        <div class="d-flex align-items-start">
            <div style="flex: 1;">
                <h6 class="mb-1">
                    <i class="fas fa-check-circle text-success me-2"></i>
                    <strong>${nasAddress}</strong>
                </h6>
                <p class="mb-1 text-muted" style="font-size: 0.85rem;">
                    <code>${activeConfig.path}</code>
                </p>
                <small class="text-muted">
                    ${activeConfig.description || 'Active NAS configuration'}
                </small>
                <br>
                <small class="text-success">
                    <i class="fas fa-cube me-1"></i>${modalityCount} modalities available
                </small>
            </div>
            <span class="badge bg-success">ACTIVE</span>
        </div>
    `;
}

// Perform NAS configuration switch
function performNASSwitch(alias) {
    if (!confirm(`Switch to NAS configuration: ${alias}?`)) {
        return;
    }
    
    console.log(`🔄 Switching NAS to: ${alias}`);
    
    const switchBtn = document.getElementById('nasSwitchBtn');
    if (switchBtn) {
        switchBtn.disabled = true;
        switchBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Switching...';
    }
    
    fetch('/api/nas/indexing/config/switch', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ alias })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('✅ NAS switched successfully');
            showNASConfigSuccess(`Successfully switched to ${alias}: ${data.new_path}`);
            
            // Reload configurations
            setTimeout(() => {
                loadNASConfigurations();
                loadCurrentNASConfig();
            }, 1000);
        } else {
            showNASConfigError('Failed to switch NAS: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error switching NAS:', error);
        showNASConfigError('Failed to switch NAS: ' + error.message);
    })
    .finally(() => {
        if (switchBtn) {
            switchBtn.disabled = false;
            switchBtn.innerHTML = '<i class="fas fa-exchange-alt me-1"></i>Switch to This NAS';
        }
    });
}

// Check NAS accessibility
function checkNASAccessibility() {
    console.log('🔍 Checking NAS accessibility...');
    
    const btn = document.getElementById('nasCheckAccessibilityBtn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Checking...';
    }
    
    fetch('/api/nas/indexing/config/check-accessibility')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (data.accessible) {
                    showNASConfigSuccess(`NAS is accessible!\n${data.total_items} items found`);
                    console.log('Sample items:', data.sample_items);
                } else {
                    showNASConfigError(`NAS is not accessible:\n${data.error}`);
                }
            } else {
                showNASConfigError('Failed to check accessibility: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error checking accessibility:', error);
            showNASConfigError('Failed to check accessibility: ' + error.message);
        })
        .finally(() => {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-check me-1"></i>Check Accessibility';
            }
        });
}

// Utility: Extract NAS address from path
function extractNASAddress(path) {
    if (!path) return 'Unknown';
    
    // Handle UNC paths: \\server\share
    const uncMatch = path.match(/\\\\([^\\]+)\\/);
    if (uncMatch) return uncMatch[1];
    
    // Handle regular paths: /path/to/share
    const lastSlash = path.lastIndexOf('/');
    if (lastSlash > 0) return path.substring(0, lastSlash);
    
    return path;
}

// Show error message
function showNASConfigError(message) {
    const currentDiv = document.getElementById('currentNasConfig');
    if (currentDiv) {
        currentDiv.innerHTML = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="fas fa-exclamation-circle me-2"></i>
                <strong>Error:</strong> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
    }
}

// Show success message
function showNASConfigSuccess(message) {
    const currentDiv = document.getElementById('currentNasConfig');
    if (currentDiv) {
        currentDiv.innerHTML = `
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                <i class="fas fa-check-circle me-2"></i>
                <strong>Success:</strong> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
    }
}

// Initialize when page is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOMContentLoaded - Initializing NAS Configuration');
    if (typeof initializeNASConfigurationUI === 'function') {
        initializeNASConfigurationUI();
    }
});

// Also initialize if document is already loaded (for late script loads)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeNASConfigurationUI);
} else {
    // Document already loaded
    setTimeout(initializeNASConfigurationUI, 100);
}

console.log('✅ NAS Configuration Modal module loaded');

// Global function to update NAS display from other modules
window.updateNASDashboardDisplay = function() {
    console.log('🔄 Updating NAS dashboard display from global function');
    loadCurrentNASConfig();
};

// Expose functions to global scope for debugging
window.showNASConfigurationModal = showNASConfigurationModal;
window.loadCurrentNASConfig = loadCurrentNASConfig;
window.loadNASConfigurations = loadNASConfigurations;
