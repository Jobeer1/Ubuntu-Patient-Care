/* Device Management page JS — extracted from server template
   Keep global function names to preserve existing inline onclick handlers.
   Do not minify — keep readable for maintenance.
*/

let devices = [];

async function loadDevices() {
    try {
        const response = await fetch('/api/devices', { credentials: 'include' });
        const data = await response.json();

        if (data.success) {
            devices = data.devices;
            renderDevices();
        } else {
            showStatus('Failed to load devices: ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('Failed to load devices: Network error', 'error');
        renderEmptyState('Network Error', 'Unable to connect to the server.');
    }
}

function renderDevices() {
    const grid = document.getElementById('devicesGrid');

    if (devices.length === 0) {
        renderEmptyState('No Devices Found', 'Add your first medical imaging device to get started.');
        return;
    }

    grid.innerHTML = devices.map(device => `
        <div class="device-card">
            <div class="device-header">
                <div class="device-name">${device.name}</div>
                <div class="device-status status-${device.status}">${device.status}</div>
            </div>
            <div class="device-info">
                <div><strong>Type:</strong> ${device.modality_type}</div>
                <div><strong>Manufacturer:</strong> ${device.manufacturer}</div>
                <div><strong>Model:</strong> ${device.model}</div>
                <div><strong>Department:</strong> ${device.department}</div>
                <div><strong>Location:</strong> ${device.location}</div>
                <div><strong>AE Title:</strong> ${device.ae_title}</div>
                <div><strong>Address:</strong> ${device.ip_address}:${device.port}</div>
            </div>
            <div class="device-actions">
                <button class="btn btn-small" onclick="testDevice('${device.id}')"><i class="fas fa-vial me-1"></i>Test</button>
                <button class="btn btn-small" onclick="editDevice('${device.id}')"><i class="fas fa-edit me-1"></i>Edit</button>
                <button class="btn btn-small" onclick="disconnectDevice('${device.ip_address}')"><i class="fas fa-unlink me-1"></i>Disconnect</button>
                <button class="btn btn-small" onclick="deleteDevice('${device.id}', '${device.name}')"><i class="fas fa-trash me-1"></i>Delete</button>
            </div>
        </div>
    `).join('');
}

function renderEmptyState(title, message) {
    const grid = document.getElementById('devicesGrid');
    grid.innerHTML = `
        <div class="empty-state">
            <h3>${title}</h3>
            <p>${message}</p>
        </div>
    `;
}

function addDevice() {
    showStatus('Device wizard coming soon! Use the API endpoints for now.', 'success');
}

async function scanARPTable() {
    try {
        showStatus('🔍 Scanning ARP table for network devices...', 'success');

        const response = await fetch('/api/devices/network/arp-scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include'
        });

        const data = await response.json();

        if (data.success) {
            const message = `✅ ARP scan completed!\n\n` +
                          `Total devices found: ${data.total_found}\n` +
                          `Likely medical devices: ${data.medical_found}\n\n` +
                          `Check the console for detailed results.`;

            showStatus(message.replace(/\n/g, '<br>'), 'success');
            console.log('ARP Scan Results:', data);

            // Show discovered devices
            if (data.discovered_devices.length > 0) {
                showDiscoveredDevices(data.discovered_devices);
            }
        } else {
            showStatus('❌ ARP scan failed: ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('❌ ARP scan failed: Network error', 'error');
    }
}

async function networkDiscovery() {
    const ipRange = prompt('Enter IP range to scan (e.g., 192.168.1.0/24 or 192.168.1.1-192.168.1.50):', '192.168.1.0/24');
    if (!ipRange) return;

    try {
        showStatus('🌐 Performing enhanced network discovery scan...', 'success');

        const response = await fetch('/api/devices/network/enhanced-scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                ip_range: ipRange,
                ports: [104, 11112, 8042, 80, 443, 22, 23, 8080],
                max_threads: 30,
                include_ping_test: true
            })
        });

        const data = await response.json();

        if (data.success) {
            const summary = data.scan_results.summary;
            const message = `✅ Enhanced network discovery completed!\n\n` +
                          `IP Range: ${ipRange}\n` +
                          `Total devices found: ${summary.total_found}\n` +
                          `Medical devices: ${summary.medical_found}\n` +
                          `DICOM capable: ${summary.dicom_capable}\n` +
                          `High confidence: ${summary.high_confidence}`;

            showStatus(message.replace(/\n/g, '<br>'), 'success');
            console.log('Enhanced Network Discovery Results:', data);

            // Show discovered devices with enhanced display
            if (data.scan_results.all_devices.length > 0) {
                showDiscoveredDevices(data.scan_results.all_devices);
            } else {
                showStatus('No devices found in the specified range. Try a different IP range or check network connectivity.', 'error');
            }
        } else {
            showStatus('❌ Network discovery failed: ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('❌ Network discovery failed: Network error', 'error');
    }
}

function showDiscoveredDevices(devices) {
    // Create a detailed results display
    const resultsDiv = document.createElement('div');
    resultsDiv.style.cssText = `
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        background: white; border-radius: 12px; box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        max-width: 90vw; max-height: 80vh; overflow-y: auto; z-index: 1000;
        padding: 0;
    `;

    // Create overlay
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.5); z-index: 999;
    `;

    // Categorize devices
    const medicalDevices = devices.filter(d => d.likely_medical_device);
    const dicomDevices = devices.filter(d => d.dicom_capable);
    const highConfidence = devices.filter(d => d.confidence_score >= 50);

    resultsDiv.innerHTML = `
        <div style="padding: 30px; border-bottom: 1px solid #e5e7eb;">
            <h2 style="margin: 0 0 10px 0; color: #1f2937;">🔍 Device Discovery Results</h2>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0;">
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #3b82f6;">${devices.length}</div>
                    <div style="color: #6b7280;">Total Devices</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #10b981;">${medicalDevices.length}</div>
                    <div style="color: #6b7280;">Medical Devices</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #8b5cf6;">${dicomDevices.length}</div>
                    <div style="color: #6b7280;">DICOM Capable</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #f59e0b;">${highConfidence.length}</div>
                    <div style="color: #6b7280;">High Confidence</div>
                </div>
            </div>
        </div>
        <div style="padding: 20px; max-height: 400px; overflow-y: auto;">
            ${devices.map((device, index) => `
                <div style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: ${device.likely_medical_device ? '#f0fdf4' : '#ffffff'};">
                    <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 10px;">
                        <div>
                            <strong style="color: #1f2937;">${device.hostname || device.ip_address}</strong>
                            ${device.likely_medical_device ? '<span style="background: #10b981; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-left: 10px;">🏥 MEDICAL</span>' : ''}
                            ${device.dicom_capable ? '<span style="background: #8b5cf6; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-left: 5px;">📡 DICOM</span>' : ''}
                        </div>
                        <div style="font-weight: bold; color: ${device.confidence_score >= 70 ? '#10b981' : device.confidence_score >= 40 ? '#f59e0b' : '#ef4444'};">
                            ${device.confidence_score || 0}% confidence
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; font-size: 14px; color: #6b7280;">
                        <div><strong>IP Address:</strong> ${device.ip_address}</div>
                        <div><strong>Manufacturer:</strong> ${device.manufacturer || 'Unknown'}</div>
                        <div><strong>Device Type:</strong> ${(device.device_type || 'unknown').replace('_', ' ')}</div>
                        <div><strong>Open Ports:</strong> ${device.open_ports ? device.open_ports.join(', ') : 'None detected'}</div>
                    </div>
                    ${device.connectivity_tests ? `
                        <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #e5e7eb;">
                            <strong style="font-size: 12px; color: #6b7280;">CONNECTIVITY TESTS:</strong>
                            <div style="display: flex; flex-wrap: wrap; gap: 5px; margin-top: 5px;">
                                ${Object.entries(device.connectivity_tests).map(([test, result]) => `
                                    <span style="background: ${result.success ? '#dcfce7' : '#fef2f2'}; color: ${result.success ? '#166534' : '#dc2626'}; padding: 2px 6px; border-radius: 4px; font-size: 11px;">
                                        ${test.replace('_', ' ')}: ${result.success ? '✅' : '❌'} ${result.response_time_ms ? `(${result.response_time_ms}ms)` : ''}
                                    </span>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}
                    <div style="margin-top: 15px;">
                        <button onclick="quickAddDevice('${device.ip_address}', '${device.hostname || 'Unknown'}', '${device.manufacturer || 'Unknown'}', ${device.dicom_capable})" 
                                style="background: #8b5cf6; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; margin-right: 10px;">
                            ➕ Add to PACS
                        </button>
                        ${device.dicom_capable ? `
                            <button onclick="testDicomDevice('${device.ip_address}')" 
                                    style="background: #10b981; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer;">
                                🩺 Test DICOM
                            </button>
                        ` : ''}
                    </div>
                </div>
            `).join('')}
        </div>
        <div style="padding: 20px; border-top: 1px solid #e5e7eb; text-align: right;">
            <button onclick="closeDiscoveryResults()" style="background: #6b7280; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer;">
                Close
            </button>
        </div>
    `;

    // Add close functionality
    window.closeDiscoveryResults = function() {
        document.body.removeChild(overlay);
        document.body.removeChild(resultsDiv);
    };

    overlay.onclick = window.closeDiscoveryResults;

    document.body.appendChild(overlay);
    document.body.appendChild(resultsDiv);
}

async function quickAddDevice(ipAddress, hostname, manufacturer, dicomCapable) {
    const deviceName = prompt(`Enter device name:`, `${manufacturer} ${hostname}`.trim());
    if (!deviceName) return;

    const modalityType = prompt(`Enter modality type (ultrasound, xray, ct, mri, etc.):`, dicomCapable ? 'ultrasound' : 'other');
    if (!modalityType) return;

    try {
        showStatus('Adding device to PACS...', 'success');

        const response = await fetch('/api/devices/network/quick-add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                ip_address: ipAddress,
                name: deviceName,
                modality_type: modalityType,
                manufacturer: manufacturer,
                ae_title: `${modalityType.toUpperCase()}_${ipAddress.replace(/\./g, '_')}`
            })
        });

        const data = await response.json();

        if (data.success) {
            showStatus(`✅ Device "${deviceName}" added successfully!`, 'success');
            loadDevices(); // Reload the devices list
            closeDiscoveryResults();
        } else {
            showStatus(`❌ Failed to add device: ${data.error}`, 'error');
        }
    } catch (error) {
        showStatus('❌ Failed to add device: Network error', 'error');
    }
}

async function testDicomDevice(ipAddress) {
    try {
        showStatus('Testing DICOM connectivity...', 'success');

        const response = await fetch('/api/devices/network/test-dicom', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                ip_address: ipAddress,
                port: 104,
                ae_title: 'TEST_AE'
            })
        });

        const data = await response.json();

        if (data.success && data.dicom_test.success) {
            showStatus(`✅ DICOM test successful: ${data.dicom_test.message}`, 'success');
        } else {
            showStatus(`❌ DICOM test failed: ${data.dicom_test.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        showStatus('❌ DICOM test failed: Network error', 'error');
    }
}

function editDevice(deviceId) {
    showStatus('Edit device coming soon! Use the API endpoints for now.', 'success');
}

async function testDevice(deviceId) {
    try {
        showStatus('Testing device connectivity...', 'success');

        const response = await fetch(`/api/devices/${deviceId}/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ test_type: 'ping' }),
            credentials: 'include'
        });

        const data = await response.json();

        if (data.success) {
            showStatus(`✅ Device test successful: ${data.message} (${data.response_time_ms}ms)`, 'success');
        } else {
            showStatus(`❌ Device test failed: ${data.message}`, 'error');
        }
    } catch (error) {
        showStatus('❌ Test failed: Network error', 'error');
    }
}

async function deleteDevice(deviceId, deviceName) {
    if (!confirm(`Are you sure you want to delete device "${deviceName}"?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/devices/${deviceId}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        const data = await response.json();

        if (data.success) {
            showStatus('✅ Device deleted successfully', 'success');
            loadDevices(); // Reload devices
        } else {
            showStatus('❌ Failed to delete device: ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('❌ Failed to delete device: Network error', 'error');
    }
}

function showStatus(message, type) {
    const statusDiv = document.getElementById('status');
    statusDiv.innerHTML = `<div class="status ${type}">${message}</div>`;

    if (type === 'success') {
        setTimeout(() => {
            statusDiv.innerHTML = '';
        }, 5000);
    }
}

async function discoverSubnet() {
    const startIp = document.getElementById('subnetStartIp').value;
    const endIp = document.getElementById('subnetEndIp').value;
    const timeout = parseInt(document.getElementById('subnetTimeout').value) || 2;

    if (!startIp || !endIp) {
        showStatus('Please enter start and end IP addresses', 'error');
        return;
    }

    try {
        showStatus('🌐 Discovering subnet devices...', 'success');

        const response = await fetch('/api/devices/network/enhanced-scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                start_ip: startIp,
                end_ip: endIp,
                timeout: timeout,
                include_arp: true,
                include_ping_range: true,
                max_hosts: 254
            })
        });

        const data = await response.json();

        if (data.success) {
            displaySubnetDevices(data.discovered_devices || []);
            showStatus(`✅ Subnet discovery completed! Found ${data.discovered_devices?.length || 0} devices`, 'success');
        } else {
            showStatus('❌ Subnet discovery failed: ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('❌ Subnet discovery failed: Network error', 'error');
    }
}

async function pingSubnetRange() {
    const startIp = document.getElementById('subnetStartIp').value;
    const endIp = document.getElementById('subnetEndIp').value;
    const timeout = parseInt(document.getElementById('subnetTimeout').value) || 2;
    const maxConcurrent = parseInt(document.getElementById('subnetMaxConcurrent').value) || 10;

    if (!startIp || !endIp) {
        showStatus('Please enter start and end IP addresses', 'error');
        return;
    }

    try {
        showStatus('🎯 Pinging IP range...', 'success');

        const response = await fetch('/api/nas/ping_range', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                start_ip: startIp,
                end_ip: endIp,
                timeout: timeout,
                max_concurrent: maxConcurrent
            })
        });

        const data = await response.json();

        if (data.success) {
            displaySubnetDevices(data.ping_range_result?.results || []);
            showStatus(`✅ Ping range completed! ${data.ping_range_result?.statistics?.online_count || 0} devices online`, 'success');
        } else {
            showStatus('❌ Ping range failed: ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('❌ Ping range failed: Network error', 'error');
    }
}

async function scanSubnetDevices() {
    const startIp = document.getElementById('subnetStartIp').value;
    const endIp = document.getElementById('subnetEndIp').value;

    if (!startIp || !endIp) {
        showStatus('Please enter start and end IP addresses', 'error');
        return;
    }

    try {
        showStatus('🔎 Scanning subnet devices for open ports...', 'success');

        const response = await fetch('/api/nas/enhanced_discovery', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                include_arp: false,
                include_ping_range: true,
                start_ip: startIp,
                end_ip: endIp,
                timeout: 2,
                max_hosts: 254
            })
        });

        const data = await response.json();

        if (data.success) {
            displaySubnetDevices(data.discovered_devices || []);
            showStatus(`✅ Subnet scan completed! Scanned ${data.discovered_devices?.length || 0} devices`, 'success');
        } else {
            showStatus('❌ Subnet scan failed: ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('❌ Subnet scan failed: Network error', 'error');
    }
}

function displaySubnetDevices(devices) {
    const resultsDiv = document.getElementById('subnetResults');

    if (!devices || devices.length === 0) {
        resultsDiv.innerHTML = `
            <div style="text-align: center; color: #6b7280; padding: 40px;">
                <h4>No devices found</h4>
                <p>Try adjusting your IP range or check network connectivity</p>
            </div>
        `;
        return;
    }

    let html = `
        <div style="margin-bottom: 20px;">
            <h4 style="color: #1f2937;">Found ${devices.length} device${devices.length !== 1 ? 's' : ''}</h4>
        </div>
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; background: white;">
                <thead>
                    <tr style="background: #f8fafc; border-bottom: 2px solid #e5e7eb;">
                        <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">IP Address</th>
                        <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">Hostname</th>
                        <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">MAC Address</th>
                        <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">Manufacturer</th>
                        <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">Status</th>
                        <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">Medical Device</th>
                        <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;

    devices.forEach(device => {
        const ip = device.ip_address || device.ip || device.ipAddress || '';
        const hostname = device.hostname || device.name || device.host || 'Unknown';
        const mac = device.mac_address || device.mac || device.hardware_address || 'Unknown';
        const manufacturer = device.manufacturer || device.vendor || 'Unknown';
        const responseTime = device.response_time || (device.reachable ? 'OK' : 'Offline');
        const reachable = device.reachable !== false && responseTime !== 'Offline';

        // Calculate medical device confidence. Prefer server-provided NAS confidence if available.
        const openPorts = device.open_ports || device.ports || [];
        const serverScore = (typeof device.nas_confidence_score !== 'undefined') ? device.nas_confidence_score :
                            (typeof device.nas_confidence !== 'undefined') ? device.nas_confidence :
                            (typeof device.score !== 'undefined') ? device.score : null;
        let confidence = 0;
        if (serverScore !== null) {
            confidence = Number(serverScore) || 0;
        } else {
            const medicalPorts = [104, 11112, 8042, 8104]; // DICOM and Orthanc ports
            const hasMedicalPorts = openPorts.some(port => medicalPorts.includes(typeof port === 'object' ? port.port : port));
            confidence = hasMedicalPorts ? 80 : (openPorts.length > 0 ? 40 : 0);
        }

        const confidenceClass = confidence >= 60 ? 'bg-success' : confidence >= 30 ? 'bg-warning text-dark' : 'bg-secondary';

        html += `
            <tr style="border-bottom: 1px solid #e5e7eb;" data-ip="${ip}">
                <td style="padding: 12px;"><code style="background: #f3f4f6; padding: 2px 6px; border-radius: 4px;">${ip}</code></td>
                <td style="padding: 12px;">${hostname}</td>
                <td style="padding: 12px;"><code style="background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-size: 12px;">${mac}</code></td>
                <td style="padding: 12px;">${manufacturer}</td>
                <td style="padding: 12px;">
                    <span style="color: ${reachable ? '#10b981' : '#ef4444'}; font-weight: 500;">
                        ${reachable ? '● Online' : '● Offline'}
                    </span>
                    ${responseTime && responseTime !== 'OK' && responseTime !== 'Offline' ? `<br><small style="color: #6b7280;">${responseTime}</small>` : ''}
                </td>
                <td style="padding: 12px;">
                    <span class="badge ${confidenceClass}" style="font-size: 12px;">${confidence}%</span>
                </td>
                <td style="padding: 12px;">
                    <div style="display: flex; gap: 5px; flex-wrap: wrap;">
                        <button class="btn btn-action btn-outline-primary" onclick="scanDevice('${ip}')" title="Scan" aria-label="Scan ${ip}"><i class="fas fa-search"></i></button>
                        <button class="btn btn-action btn-outline-secondary" onclick="pingDevice('${ip}')" title="Ping" aria-label="Ping ${ip}"><i class="fas fa-wifi"></i></button>
                        <button class="btn btn-action btn-outline-success" onclick="connectToDevice('${ip}')" title="Connect" aria-label="Connect ${ip}"><i class="fas fa-plug"></i></button>
                        <button class="btn btn-action btn-outline-secondary" onclick="disconnectDevice('${ip}')" title="Disconnect" aria-label="Disconnect ${ip}"><i class="fas fa-unlink"></i></button>
                        <button class="btn btn-sm btn-outline-warning" onclick="renameDevice('${ip}', '${ip}')" style="padding: 4px 8px; font-size: 12px;" title="Rename device">✏️ Rename</button>
                        <button class="btn btn-sm btn-outline-danger" onclick="removeDevice('${ip}', '${ip}')" style="padding: 4px 8px; font-size: 12px;" title="Remove device">🗑️ Remove</button>
                    </div>
                </td>
            </tr>
        `;
    });

    html += `
                </tbody>
            </table>
        </div>
    `;

    resultsDiv.innerHTML = html;
}

async function saveSubnetSettings() {
    const settings = {
        startIp: document.getElementById('subnetStartIp').value,
        endIp: document.getElementById('subnetEndIp').value,
        timeout: parseInt(document.getElementById('subnetTimeout').value) || 2,
        maxConcurrent: parseInt(document.getElementById('subnetMaxConcurrent').value) || 10
    };

    try {
        const response = await fetch('/api/nas/network-settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(settings)
        });

        const data = await response.json();

        if (data.success) {
            showStatus('✅ Subnet settings saved successfully!', 'success');
        } else {
            showStatus('❌ Failed to save subnet settings: ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('❌ Failed to save subnet settings: Network error', 'error');
    }
}

async function loadSubnetSettings() {
    try {
        const response = await fetch('/api/nas/network-settings', {
            method: 'GET',
            credentials: 'include'
        });

        const data = await response.json();

        if (data.success && data.settings) {
            const settings = data.settings;
            document.getElementById('subnetStartIp').value = settings.startIp || '192.168.1.1';
            document.getElementById('subnetEndIp').value = settings.endIp || '192.168.1.254';
            document.getElementById('subnetTimeout').value = settings.timeout || 2;
            document.getElementById('subnetMaxConcurrent').value = settings.maxConcurrent || 10;

            showStatus('✅ Subnet settings loaded successfully!', 'success');
        } else {
            showStatus('No saved settings found, using defaults', 'success');
        }
    } catch (error) {
    }
}

async function scanDevice(ip) {
    if (!ip) {
        showStatus('No IP address provided', 'error');
        return;
    }

    try {
        showStatus(`🔍 Scanning ${ip} for open ports...`, 'success');

        const response = await fetch('/api/nas/scan-device', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                ip_address: ip,
                ports: [104, 11112, 8042, 80, 443, 22, 23, 8080, 9000, 9090],
                scan_type: 'nas' // explicit hint so backend uses NAS-specific scanner and scoring
            })
        });

        const data = await response.json();

        if (data.success) {
            const openPorts = data.scan_result?.open_ports?.length || 0;
            showStatus(`✅ Scan completed! Found ${openPorts} open ports on ${ip}`, 'success');

            // Update the device row with scan results
            updateDeviceScanResults(ip, data.scan_result);
        } else {
            showStatus(`❌ Scan failed: ${data.error}`, 'error');
        }
    } catch (error) {
        showStatus(`❌ Scan failed: ${error.message}`, 'error');
    }
}

async function pingDevice(ip) {
    if (!ip) {
        showStatus('No IP address provided', 'error');
        return;
    }

    try {
        showStatus(`🏓 Pinging ${ip}...`, 'success');

        const response = await fetch('/api/nas/ping', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                ip_address: ip,
                timeout: 3
            })
        });

        const data = await response.json();

        if (data.success && data.ping_result) {
            const reachable = data.ping_result.reachable;
            const responseTime = data.ping_result.response_time || 'OK';

            if (reachable) {
                showStatus(`✅ ${ip} is reachable (${responseTime})`, 'success');
            } else {
                showStatus(`❌ ${ip} is not reachable`, 'error');
            }

            // Update the device row status
            updateDeviceStatus(ip, reachable, responseTime);
        } else {
            showStatus(`❌ Ping failed: ${data.error}`, 'error');
        }
    } catch (error) {
        showStatus(`❌ Ping failed: ${error.message}`, 'error');
    }
}

async function connectToDevice(ip) {
    if (!ip) {
        showStatus('No IP address provided', 'error');
        return;
    }

    try {
        showStatus(`🔗 Connecting to ${ip}...`, 'success');

        const response = await fetch('/api/nas/connect-device', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                ip_address: ip
            })
        });

        const data = await response.json();

        if (data.success) {
            showStatus(`✅ Successfully connected to ${ip}`, 'success');

            // Update the device row to show connected status
            updateDeviceConnectionStatus(ip, true);
        } else {
            showStatus(`❌ Connection failed: ${data.error}`, 'error');
        }
    } catch (error) {
        showStatus(`❌ Connection failed: ${error.message}`, 'error');
    }
}

async function disconnectDevice(ip) {
    if (!ip) return showStatus('No IP provided', 'error');
    if (!confirm(`Disconnect ${ip}?`)) return;
    try {
        showStatus(`🔌 Disconnecting ${ip}...`, 'success');
        const response = await fetch('/api/nas/disconnect-device', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ ip_address: ip })
        });
        const data = await response.json();
        if (data.success) {
            showStatus(`✅ Disconnected ${ip}`, 'success');
            // Remove connected badge if present
            updateDeviceConnectionStatus(ip, false);
        } else {
            showStatus(`❌ Disconnect failed: ${data.error}`, 'error');
        }
    } catch (err) {
        showStatus(`❌ Disconnect error: ${err.message}`, 'error');
    }
}

async function renameDevice(ip, currentName) {
    if (!ip) {
        showStatus('No IP address provided', 'error');
        return;
    }

    const newName = prompt(`Rename device ${currentName || ip}:`, currentName || '');
    if (!newName || newName.trim() === '') {
        showStatus('Device name cannot be empty', 'warning');
        return;
    }

    if (newName === currentName) return;

    try {
        showStatus(`✏️ Renaming device to "${newName}"...`, 'success');

        const response = await fetch('/api/nas/rename-device', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                ip_address: ip,
                new_name: newName.trim()
            })
        });

        const data = await response.json();

        if (data.success) {
            showStatus(`✅ Device renamed to "${newName}"`, 'success');

            // Update the device row hostname
            updateDeviceHostname(ip, newName);
        } else {
            showStatus(`❌ Rename failed: ${data.error}`, 'error');
        }
    } catch (error) {
        showStatus(`❌ Rename failed: ${error.message}`, 'error');
    }
}

async function removeDevice(ip, hostname) {
    if (!ip) {
        showStatus('No IP address provided', 'error');
        return;
    }

    if (!confirm(`Are you sure you want to remove device "${hostname || ip}"?`)) {
        return;
    }

    try {
        showStatus(`🗑️ Removing device ${hostname || ip}...`, 'success');

        const response = await fetch('/api/nas/remove-device', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                ip_address: ip
            })
        });

        const data = await response.json();

        if (data.success) {
            showStatus(`✅ Device "${hostname || ip}" removed successfully`, 'success');

            // Remove the device row from the table
            removeDeviceRow(ip);

            // Refresh the subnet display
            discoverSubnet();
        } else {
            showStatus(`❌ Remove failed: ${data.error}`, 'error');
        }
    } catch (error) {
        showStatus(`❌ Remove failed: ${error.message}`, 'error');
    }
}

function updateDeviceScanResults(ip, scanResult) {
    // Update both subnetResults and subnetIpDisplay tables
    const rows = document.querySelectorAll(`tr[data-ip="${ip}"]`);
    rows.forEach(row => {
        const table = row.closest('table');
        if (!table) return;

        const isSubnetResults = table.parentElement.id === 'subnetResults';

        if (isSubnetResults) {
            // Original subnetResults table structure
            const openPorts = scanResult?.open_ports?.length || 0;

            // Update the status cell with scan information
            const statusCell = row.querySelector('td:nth-child(5)');
            if (statusCell) {
                const existingText = statusCell.innerHTML.split('<br>')[0];
                statusCell.innerHTML = `${existingText}<br><small style="color: #6b7280;">Scanned: ${openPorts} ports open</small>`;
            }

            // Update confidence based on scan results. Prefer server-provided NAS score if present.
            const confidenceCell = row.querySelector('td:nth-child(6)');
            if (confidenceCell && scanResult) {
                // Server may return nas_confidence_score, nas_confidence, or score
                const serverScore = (typeof scanResult.nas_confidence_score !== 'undefined') ? scanResult.nas_confidence_score :
                                    (typeof scanResult.nas_confidence !== 'undefined') ? scanResult.nas_confidence :
                                    (typeof scanResult.score !== 'undefined') ? scanResult.score : null;

                let confidence = 0;
                if (serverScore !== null) {
                    confidence = Number(serverScore) || 0;
                } else {
                    // Fallback to legacy client heuristic
                    const medicalPorts = [104, 11112, 8042, 8104];
                    const hasMedicalPorts = scanResult.open_ports?.some(port => 
                        medicalPorts.includes(typeof port === 'object' ? port.port : port)
                    );
                    confidence = hasMedicalPorts ? 80 : (openPorts > 0 ? 40 : 0);
                }

                const confidenceClass = confidence >= 60 ? 'bg-success' : confidence >= 30 ? 'bg-warning text-dark' : 'bg-secondary';
                confidenceCell.innerHTML = `<span class="badge ${confidenceClass}" style="font-size: 12px;">${confidence}%</span>`;
            }
        } else {
            // subnetIpDisplay table structure
            const openPorts = scanResult?.open_ports?.length || 0;

            // Update the status cell with scan information
            const statusCell = row.querySelector('td:nth-child(2)');
            if (statusCell) {
                const existingText = statusCell.innerHTML.split('<br>')[0];
                statusCell.innerHTML = `${existingText}<br><small style="color: #6b7280;">Scanned: ${openPorts} ports open</small>`;
            }
        }
    });
}

function updateDeviceStatus(ip, reachable, responseTime) {
    // Update both subnetResults and subnetIpDisplay tables
    const rows = document.querySelectorAll(`tr[data-ip="${ip}"]`);
    rows.forEach(row => {
        const table = row.closest('table');
        if (!table) return;

        const isSubnetResults = table.parentElement.id === 'subnetResults';
        const statusCellIndex = isSubnetResults ? 5 : 2; // Different column positions

        const statusCell = row.querySelector(`td:nth-child(${statusCellIndex})`);
        if (statusCell) {
            const statusText = reachable ? '● Online' : '● Offline';
            const color = reachable ? '#10b981' : '#ef4444';
            const timeInfo = responseTime && responseTime !== 'OK' ? `<br><small style="color: #6b7280;">${responseTime}</small>` : '';

            statusCell.innerHTML = `<span style="color: ${color}; font-weight: 500;">${statusText}</span>${timeInfo}`;
        }
    });
}

function updateDeviceConnectionStatus(ip, connected) {
    // Update both subnetResults and subnetIpDisplay tables
    const rows = document.querySelectorAll(`tr[data-ip="${ip}"]`);
    rows.forEach(row => {
        const table = row.closest('table');
        if (!table) return;

        const isSubnetResults = table.parentElement.id === 'subnetResults';
        const actionsCellIndex = isSubnetResults ? 7 : 3; // Different column positions

        const actionsCell = row.querySelector(`td:nth-child(${actionsCellIndex})`);
        if (actionsCell && connected) {
            // Add a connected badge
            const badge = document.createElement('span');
            badge.className = 'badge bg-info';
            badge.style.cssText = 'font-size: 10px; margin-left: 5px;';
            badge.textContent = 'Connected';
            actionsCell.appendChild(badge);
        }
    });
}

function updateDeviceHostname(ip, newHostname) {
    // Update both subnetResults and subnetIpDisplay tables
    const rows = document.querySelectorAll(`tr[data-ip="${ip}"]`);
    rows.forEach(row => {
        const table = row.closest('table');
        if (!table) return;

        const isSubnetResults = table.parentElement.id === 'subnetResults';
        const hostnameCellIndex = isSubnetResults ? 2 : 1; // Different column positions (IP is in column 1 for subnetIpDisplay)

        if (isSubnetResults) {
            const hostnameCell = row.querySelector(`td:nth-child(${hostnameCellIndex})`);
            if (hostnameCell) {
                hostnameCell.textContent = newHostname;
            }
        }
        // For subnetIpDisplay, IP address is fixed, so we don't update hostname
    });
}

function removeDeviceRow(ip) {
    // Remove from both subnetResults and subnetIpDisplay tables
    const rows = document.querySelectorAll(`tr[data-ip="${ip}"]`);
    rows.forEach(row => {
        row.remove();
    });
}

function displayAllSubnetIps() {
    const startIp = document.getElementById('subnetStartIp').value;
    const endIp = document.getElementById('subnetEndIp').value;

    if (!startIp || !endIp) {
        showStatus('Please enter start and end IP addresses', 'error');
        return;
    }

    try {
        // Parse IP addresses and generate range
        const startParts = startIp.split('.').map(Number);
        const endParts = endIp.split('.').map(Number);

        if (startParts.length !== 4 || endParts.length !== 4) {
            showStatus('Invalid IP address format', 'error');
            return;
        }

        // Generate IP list
        const ipList = [];
        for (let i = startParts[3]; i <= endParts[3]; i++) {
            ipList.push(`${startParts[0]}.${startParts[1]}.${startParts[2]}.${i}`);
        }

        if (ipList.length > 254) {
            showStatus('IP range too large (max 254 addresses)', 'error');
            return;
        }

        // Display the IP addresses with buttons
        displaySubnetIpList(ipList);
        showStatus(`✅ Generated ${ipList.length} IP addresses in range`, 'success');

    } catch (error) {
        showStatus('Error generating IP range: ' + error.message, 'error');
    }
}

function displaySubnetIpList(ipList) {
    const resultsDiv = document.getElementById('subnetIpDisplay');

    if (!ipList || ipList.length === 0) {
        resultsDiv.innerHTML = `
            <div style="text-align: center; color: #6b7280; padding: 40px;">
                <h4>No IP addresses to display</h4>
                <p>Configure a valid IP range and try again</p>
            </div>
        `;
        return;
    }

    let html = `
        <div style="margin-bottom: 20px;">
            <h4 style="color: #1f2937;">Generated ${ipList.length} IP Address${ipList.length !== 1 ? 'es' : ''}</h4>
            <p style="color: #6b7280; font-size: 14px;">Click buttons to interact with each IP address</p>
        </div>
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; background: white;">
                <thead>
                    <tr style="background: #f8fafc; border-bottom: 2px solid #e5e7eb;">
                        <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">IP Address</th>
                        <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">Status</th>
                        <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;

    ipList.forEach(ip => {
        html += `
            <tr style="border-bottom: 1px solid #e5e7eb;" data-ip="${ip}">
                <td style="padding: 12px;"><code style="background: #f3f4f6; padding: 2px 6px; border-radius: 4px;">${ip}</code></td>
                <td style="padding: 12px;" id="status-${ip.replace(/\./g, '-')}">
                    <span style="color: #6b7280; font-weight: 500;">● Unknown</span>
                </td>
                <td style="padding: 12px;">
                    <div style="display: flex; gap: 5px; flex-wrap: wrap;">
                        <button class="btn btn-action btn-outline-primary" onclick="scanDevice('${ip}')" title="Scan" aria-label="Scan ${ip}"><i class="fas fa-search"></i></button>
                        <button class="btn btn-action btn-outline-secondary" onclick="pingDevice('${ip}')" title="Ping" aria-label="Ping ${ip}"><i class="fas fa-wifi"></i></button>
                        <button class="btn btn-action btn-outline-success" onclick="connectToDevice('${ip}')" title="Connect" aria-label="Connect ${ip}"><i class="fas fa-plug"></i></button>
                        <button class="btn btn-action btn-outline-secondary" onclick="disconnectDevice('${ip}')" title="Disconnect" aria-label="Disconnect ${ip}"><i class="fas fa-unlink"></i></button>
                        <button class="btn btn-sm btn-outline-warning" onclick="renameDevice('${ip}', '${ip}')" style="padding: 4px 8px; font-size: 12px;" title="Rename device">✏️ Rename</button>
                        <button class="btn btn-sm btn-outline-danger" onclick="removeDevice('${ip}', '${ip}')" style="padding: 4px 8px; font-size: 12px;" title="Remove device">🗑️ Remove</button>
                    </div>
                </td>
            </tr>
        `;
    });

    html += `
                </tbody>
            </table>
        </div>
    `;

    resultsDiv.innerHTML = html;
}

// Missing subnet management functions (kept duplicates for compatibility)
async function discoverSubnet() {
    const startIp = document.getElementById('subnetStartIp').value;
    const endIp = document.getElementById('subnetEndIp').value;

    if (!startIp || !endIp) {
        showStatus('Please enter start and end IP addresses', 'error');
        return;
    }

    try {
        showStatus('🔍 Discovering subnet devices...', 'success');

        const response = await fetch('/api/nas/network-discovery', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                start_ip: startIp,
                end_ip: endIp,
                discovery_type: 'arp'
            })
        });

        const data = await response.json();

        if (data.success) {
            showStatus(`✅ Subnet discovery completed! Found ${data.devices?.length || 0} devices`, 'success');

            // Display discovered devices
            if (data.devices && data.devices.length > 0) {
                displayDiscoveredDevices(data.devices);
            }
        } else {
            showStatus(`❌ Subnet discovery failed: ${data.error}`, 'error');
        }
    } catch (error) {
        showStatus(`❌ Subnet discovery failed: ${error.message}`, 'error');
    }
}

// ... end of file - load devices on page load

loadDevices();
