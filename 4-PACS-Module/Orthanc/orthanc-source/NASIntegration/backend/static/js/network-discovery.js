/* 🇿🇦 Network Discovery Module - South African Medical Imaging System */

// Network discovery and scanning functions
async function getArpTable() {
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/arp-table');
        
        // Use the same logic as refreshArpTable for consistency
        if (data.success && (data.arp_entries || data.devices || data.discovered_devices)) {
            // Prioritize arp_entries, then fall back to other formats
            const devices = data.arp_entries || data.devices || data.discovered_devices || [];
            const total = data.total_entries || data.total || devices.length;
            
            const arpTableHtml = window.NASIntegration.ui.formatArpTable(devices, total);
            const resultsElement = document.getElementById('subnetResults') || document.getElementById('discoveryResults');
            if (resultsElement) {
                resultsElement.innerHTML = arpTableHtml;
            }
            
            window.NASIntegration.core.showMessage(`✅ ARP table loaded! Found ${devices.length} devices`, 'success');
            window.NASIntegration.lastDiscoveryResults = data;
            window.NASIntegration.core.storeLastResults('arp_table', data);
        } else {
            const resultsElement = document.getElementById('subnetResults') || document.getElementById('discoveryResults');
            if (resultsElement) {
                resultsElement.innerHTML = `❌ Error: ${data.error || data.message || 'No devices found'}`;
            }
        }
    } catch (error) {
        const resultsElement = document.getElementById('subnetResults') || document.getElementById('discoveryResults');
        if (resultsElement) {
            resultsElement.innerHTML = `❌ Error: ${error.message}`;
        }
    }
}

async function refreshArpTable() {
    const refreshButton = document.querySelector('.refresh-btn');
    const originalText = refreshButton ? refreshButton.textContent : '';
    
    if (refreshButton) {
        refreshButton.disabled = true;
        refreshButton.textContent = '🔄 Refreshing...';
    }
    
    window.NASIntegration.core.showLoading(true, 'Refreshing ARP table...');
    
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/arp-table');
        
        if (data.success && data.arp_entries) {
            // Update the display with new ARP table data
            const arpTableHtml = window.NASIntegration.ui.formatArpTable(data.arp_entries, data.total_entries || data.arp_entries.length);
            const resultsElement = document.getElementById('subnetResults') || document.getElementById('discoveryResults');
            if (resultsElement) {
                resultsElement.innerHTML = arpTableHtml;
            }
            
            window.NASIntegration.core.showMessage(`✅ ARP table refreshed! Found ${data.arp_entries.length} devices`, 'success');
            window.NASIntegration.lastDiscoveryResults = data;
            window.NASIntegration.core.storeLastResults('arp_table', data);
        } else {
            window.NASIntegration.core.showMessage(`❌ Failed to refresh ARP table: ${data.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        window.NASIntegration.core.showMessage(`❌ Network error refreshing ARP table: ${error.message}`, 'error');
    } finally {
        window.NASIntegration.core.showLoading(false);
        if (refreshButton) {
            refreshButton.disabled = false;
            refreshButton.textContent = originalText;
        }
    }
}

// Load cached discovered devices and display full subnet (including offline IPs)
async function loadCachedDevices() {
    try {
        const cached = await window.NASIntegration.core.makeAPIRequest('/api/nas/cached-devices');

        // Get network settings to build full subnet list
        let settings = {};
        try {
            const s = await window.NASIntegration.core.makeAPIRequest('/api/nas/network-settings');
            settings = s.settings || s;
        } catch (e) {
            // ignore - we'll fallback to cached devices only
            settings = {};
        }

        const startIp = settings.startIp || document.getElementById('startIp')?.value;
        const endIp = settings.endIp || document.getElementById('endIp')?.value;

        let devices = cached.discovered_devices || cached.devices || cached.arp_entries || cached.devices || [];

        // If we have a start/end, build full list and mark missing IPs as offline
        if (startIp && endIp) {
            // build numeric IP list
            try {
                const ips = [];
                const sParts = startIp.split('.').map(n => parseInt(n,10));
                const eParts = endIp.split('.').map(n => parseInt(n,10));
                // simple range only when first three octets match
                if (sParts.length === 4 && eParts.length === 4 && sParts[0]===eParts[0] && sParts[1]===eParts[1] && sParts[2]===eParts[2]) {
                    for (let i = sParts[3]; i <= eParts[3]; i++) {
                        ips.push(`${sParts[0]}.${sParts[1]}.${sParts[2]}.${i}`);
                    }
                }

                if (ips.length > 0) {
                    const deviceMap = {};
                    devices.forEach(d => { deviceMap[d.ip_address || d.ip || d.ipAddress] = d; });

                    const full = ips.map(ip => {
                        const found = deviceMap[ip];
                        if (found) return found;
                        return {
                            ip_address: ip,
                            hostname: 'Unknown',
                            mac_address: 'Unknown',
                            manufacturer: 'Unknown',
                            response_time: 'N/A',
                            reachable: false,
                            source: 'Subnet Placeholder'
                        };
                    });

                    devices = full;
                }
            } catch (err) {
                // ignore and use cached devices only
            }
        }

        // Render using ARP table formatter for consistent columns
        const arpTableHtml = window.NASIntegration.ui.formatArpTable(devices, devices.length);
        const resultsElement = document.getElementById('subnetResults') || document.getElementById('discoveryResults');
        if (resultsElement) {
            resultsElement.innerHTML = arpTableHtml;
        }
        window.NASIntegration.lastDiscoveryResults = { devices };
        window.NASIntegration.core.setLastResultType('cached_devices');
    } catch (error) {
        console.warn('Failed to load cached devices:', error);
    }
}

async function pingRange() {
    // tolerate different input IDs (legacy vs current templates) and avoid null access
    const startIp = document.getElementById('startIp')?.value;
    const endIp = document.getElementById('endIp')?.value;
    const timeoutRaw = document.getElementById('timeoutMs')?.value ?? document.getElementById('pingTimeout')?.value;
    const timeout = parseInt(timeoutRaw) || 2000;
    
    if (!startIp || !endIp) {
        window.NASIntegration.core.showMessage('Please enter start and end IP addresses', 'warning');
        return;
    }
    
    try {
    // Check for port-scan opt-in checkbox (legacy IDs supported)
    const includePortScan = document.getElementById('includePortScan')?.checked || document.getElementById('include_port_scan')?.checked || false;

    const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/ping_range', {
            method: 'POST',
            body: JSON.stringify({
                start_ip: startIp,
                end_ip: endIp,
                timeout: Math.round(timeout / 1000), // Convert to seconds
                max_concurrent: 10,
                include_port_scan: includePortScan
            })
        });
        
        if (data.success) {
            const resultsHtml = window.NASIntegration.ui.formatRangePingResults(data.ping_range_result.results, data.ping_range_result.statistics, data.ping_range_result.range);
            const resultsElement = document.getElementById('subnetResults') || document.getElementById('discoveryResults');
            if (resultsElement) {
                resultsElement.innerHTML = resultsHtml;
            }
            
            window.NASIntegration.core.showMessage(`✅ Ping range completed! ${data.ping_range_result.statistics.online_count} devices online`, 'success');
            window.NASIntegration.lastDiscoveryResults = data;
        } else {
            window.NASIntegration.core.showMessage(`❌ Ping range failed: ${data.error}`, 'error');
        }
    } catch (error) {
        window.NASIntegration.core.showMessage(`❌ Ping range error: ${error.message}`, 'error');
    }
}

async function pingSingleDevice() {
    // support both 'singleDeviceIp' and 'singlePingIp' element IDs
    const deviceIp = document.getElementById('singleDeviceIp')?.value || document.getElementById('singlePingIp')?.value;
    const timeout = parseInt(document.getElementById('singlePingTimeout')?.value) || 3000;
    
    if (!deviceIp) {
        window.NASIntegration.core.showMessage('Please enter device IP address', 'warning');
        return;
    }
    
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/ping', {
            method: 'POST',
            body: JSON.stringify({
                ip_address: deviceIp,
                timeout: Math.round(timeout / 1000)
            })
        });
        
        if (data.success) {
            const resultHtml = window.NASIntegration.ui.formatPingResult(data.ping_result);
            const resultsElement = document.getElementById('subnetResults') || document.getElementById('discoveryResults');
            if (resultsElement) {
                resultsElement.innerHTML = resultHtml;
            }
            
            const status = data.ping_result.reachable ? 'online' : 'offline';
            window.NASIntegration.core.showMessage(`✅ Ping completed! Device ${deviceIp} is ${status}`, 'success');
        } else {
            window.NASIntegration.core.showMessage(`❌ Ping failed: ${data.error}`, 'error');
        }
    } catch (error) {
        window.NASIntegration.core.showMessage(`❌ Ping error: ${error.message}`, 'error');
    }
}

async function enhancedDiscover(includeArp = true, includePingRange = false) {
    const startIp = document.getElementById('startIp')?.value;
    const endIp = document.getElementById('endIp')?.value;
    const timeoutRaw = document.getElementById('timeoutMs')?.value ?? document.getElementById('pingTimeout')?.value;
    const timeout = parseInt(timeoutRaw) || 2000;
    
    try {
        const requestData = {
            include_arp: includeArp,
            include_ping_range: includePingRange,
            timeout: Math.round(timeout / 1000)
        };
        
        if (includePingRange && startIp && endIp) {
            requestData.start_ip = startIp;
            requestData.end_ip = endIp;
        }
        // Apply client-side max_hosts safety cap to avoid accidental wide scans
        // Default cap is 254; warn when scan > 100
        let maxHosts = null;
        try {
            const explicitRange = document.getElementById('networkRange')?.value || '';
            if (explicitRange && explicitRange.includes('/')) {
                // compute host count from CIDR
                const parts = explicitRange.split('/');
                const prefix = parseInt(parts[1], 10);
                if (!isNaN(prefix) && prefix >= 0 && prefix <= 32) {
                    const hostCount = Math.max(0, Math.pow(2, 32 - prefix) - 2);
                    maxHosts = hostCount;
                }
            }
        } catch (e) {
            maxHosts = null;
        }

        // Apply a safety cap and user warning
        const CLIENT_SAFE_CAP = 254;
        if (typeof maxHosts === 'number') {
            if (maxHosts > CLIENT_SAFE_CAP) {
                window.NASIntegration.core.showMessage(`⚠️ Requested CIDR contains ${maxHosts} hosts; limiting to ${CLIENT_SAFE_CAP} hosts to avoid long scans`, 'warning');
                maxHosts = CLIENT_SAFE_CAP;
            }
        } else {
            // default cap if none computed
            maxHosts = CLIENT_SAFE_CAP;
        }

        // Require explicit user confirmation for moderately large scans (>100 hosts)
        if (maxHosts > 100) {
            const prompt = `The scan will target up to ${maxHosts} hosts and may take a long time. Do you want to continue?`;
            // Prefer a project-level confirmation method if available
            const confirmed = (window.NASIntegration && window.NASIntegration.core && typeof window.NASIntegration.core.confirm === 'function')
                ? window.NASIntegration.core.confirm(prompt)
                : window.confirm(prompt);
            if (!confirmed) {
                window.NASIntegration.core.showMessage('Scan cancelled by user', 'info');
                return;
            }
        }

        requestData.max_hosts = maxHosts;

    // Read optional port-scan checkbox (legacy ID support)
    const includePortScan = document.getElementById('includePortScan')?.checked || document.getElementById('include_port_scan')?.checked || false;

    const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/enhanced_discovery', {
            method: 'POST',
            body: JSON.stringify(requestData)
        });
        
        if (data.success) {
            const resultsHtml = window.NASIntegration.ui.formatDiscoveredDevices(data.discovered_devices);
            const resultsElement = document.getElementById('subnetResults') || document.getElementById('discoveryResults');
            if (resultsElement) {
                resultsElement.innerHTML = resultsHtml;
            }
            
            const methodsUsed = data.methods_used ? data.methods_used.join(', ') : 'Enhanced Discovery';
            window.NASIntegration.core.showMessage(`✅ ${data.message} using ${methodsUsed}`, 'success');
            window.NASIntegration.lastDiscoveryResults = data;
            window.NASIntegration.core.storeLastResults('enhanced_discovery', data);
        } else {
            window.NASIntegration.core.showMessage(`❌ Enhanced discovery failed: ${data.error}`, 'error');
        }
    } catch (error) {
        window.NASIntegration.core.showMessage(`❌ Enhanced discovery error: ${error.message}`, 'error');
    }
}

async function startNetworkScan() {
    const scanType = document.querySelector('input[name="scanType"]:checked')?.value || 'arp';
    
    window.NASIntegration.core.showMessage('🔍 Starting network scan...', 'info');
    
    switch (scanType) {
        case 'arp':
            await getArpTable();
            break;
        case 'ping_range':
            await pingRange();
            break;
        case 'enhanced':
            // Determine whether to include ping-range based on form fields
            const startIp = document.getElementById('startIp')?.value;
            const endIp = document.getElementById('endIp')?.value;
            const includePingRange = !!(startIp && endIp);
            await enhancedDiscover(true, includePingRange);
            break;
        default:
            await getArpTable();
    }
}

// Storage configuration functions
async function configureStorage() {
    const storageConfig = {
        nas_path: document.getElementById('nasPath')?.value || '',
        backup_path: document.getElementById('backupPath')?.value || '',
        storage_path: document.getElementById('storagePath')?.value || '',
        auto_backup: document.getElementById('autoBackup')?.checked || false,
        compression: document.getElementById('enableCompression')?.checked || false,
        compression_level: document.getElementById('compressionLevel')?.value || 'none'
    };
    
    if (!storageConfig.storage_path && !storageConfig.nas_path) {
        window.NASIntegration.core.showMessage('Please enter storage path', 'warning');
        return;
    }
    
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/storage/config', {
            method: 'POST',
            body: JSON.stringify(storageConfig)
        });
        
        if (data.success) {
            window.NASIntegration.core.showMessage('✅ Storage configuration saved successfully!', 'success');
            document.getElementById('storageResults').innerHTML = window.NASIntegration.ui.formatStorageStatus(data);
        } else {
            window.NASIntegration.core.showMessage(`❌ Failed to save storage config: ${data.error}`, 'error');
        }
    } catch (error) {
        window.NASIntegration.core.showMessage(`❌ Storage config error: ${error.message}`, 'error');
    }
}

async function testStorage() {
    window.NASIntegration.core.showLoading(true, 'Testing storage paths...');
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/storage/test');
        
        if (data.success) {
            const storageHtml = window.NASIntegration.ui.formatStorageStatus(data);
            document.getElementById('storageResults').innerHTML = storageHtml;
            window.NASIntegration.core.showMessage('✅ Storage test completed successfully!', 'success');
        } else {
            window.NASIntegration.core.showMessage(`❌ Storage test failed: ${data.error}`, 'error');
        }
    } catch (error) {
        window.NASIntegration.core.showMessage(`❌ Storage test error: ${error.message}`, 'error');
    }
    window.NASIntegration.core.showLoading(false);
}

async function testStoragePaths() {
    await testStorage();
}

// Network settings management
async function saveNetworkSettings() {
    const networkSettings = {
        startIp: document.getElementById('startIp')?.value || '',
        endIp: document.getElementById('endIp')?.value || '',
    timeout: parseInt(document.getElementById('timeoutMs')?.value ?? document.getElementById('pingTimeout')?.value) || 2000,
        maxConcurrent: parseInt(document.getElementById('maxConcurrent')?.value) || 10,
        networkRange: document.getElementById('networkRange')?.value || ''
    };
    
    try {
        const data = await window.NASIntegration.core.makeAPIRequest('/api/nas/network-settings', {
            method: 'POST',
            body: JSON.stringify(networkSettings)
        });
        
        if (data.success) {
            window.NASIntegration.core.showMessage('✅ Network settings saved successfully!', 'success');
        } else {
            window.NASIntegration.core.showMessage(`❌ Failed to save network settings: ${data.error}`, 'error');
        }
    } catch (error) {
        window.NASIntegration.core.showMessage(`❌ Network settings error: ${error.message}`, 'error');
    }
}

async function loadNetworkSettings() {
    try {
        const response = await fetch('/api/nas/network-settings');
        const data = await response.json();
        
        if (data.success && data.settings) {
            const settings = data.settings;
            
            if (document.getElementById('startIp')) document.getElementById('startIp').value = settings.startIp || '';
            if (document.getElementById('endIp')) document.getElementById('endIp').value = settings.endIp || '';
            // populate both possible timeout fields
            if (document.getElementById('timeoutMs')) document.getElementById('timeoutMs').value = settings.timeout || 2000;
            if (document.getElementById('pingTimeout')) document.getElementById('pingTimeout').value = settings.timeout || 2000;
            if (document.getElementById('maxConcurrent')) document.getElementById('maxConcurrent').value = settings.maxConcurrent || 10;
            if (document.getElementById('networkRange')) document.getElementById('networkRange').value = settings.networkRange || '';
            
            console.log('✅ Network settings loaded successfully');
        }
    } catch (error) {
        console.warn('Failed to load network settings:', error);
    }
}

// Export network discovery functions
window.NASIntegration.network = {
    getArpTable,
    refreshArpTable,
    pingRange,
    pingSingleDevice,
    enhancedDiscover,
    startNetworkScan,
    configureStorage,
    testStorage,
    testStoragePaths,
    saveNetworkSettings,
    loadNetworkSettings,
    loadCachedDevices
};

console.log('✅ Network Discovery module loaded successfully');
