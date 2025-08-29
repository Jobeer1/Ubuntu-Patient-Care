#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - Device Management Template

Clean device management interface for medical equipment.
"""

DEVICE_MANAGEMENT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏥 Device Management - SA Medical Imaging</title>
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
            background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
            color: white;
            padding: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .content {
            padding: 30px;
        }
        
        .btn {
            background: #8b5cf6;
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
            background: #7c3aed;
            transform: translateY(-1px);
        }
        
        .btn-secondary {
            background: #6b7280;
        }
        
        .btn-secondary:hover {
            background: #4b5563;
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
        }
        
        .status.error {
            background: #fef2f2;
            color: #dc2626;
        }
        
        .devices-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .device-card {
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            padding: 20px;
            transition: all 0.2s;
        }
        
        .device-card:hover {
            border-color: #8b5cf6;
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        }
        
        .device-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .device-name {
            font-size: 18px;
            font-weight: 600;
            color: #1f2937;
        }
        
        .device-status {
            padding: 4px 8px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .status-active {
            background: #dcfce7;
            color: #166534;
        }
        
        .status-inactive {
            background: #fef2f2;
            color: #dc2626;
        }
        
        .device-info {
            color: #6b7280;
            font-size: 14px;
            line-height: 1.5;
        }
        
        .device-actions {
            margin-top: 15px;
            display: flex;
            gap: 8px;
        }
        
        .btn-small {
            padding: 6px 12px;
            font-size: 12px;
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #6b7280;
        }
        
        .empty-state h3 {
            font-size: 20px;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>🏥 Device Management</h1>
                <p>🇿🇦 Manage medical imaging equipment</p>
            </div>
            <div>
                <button class="btn" onclick="addDevice()">➕ Add Device</button>
                <button class="btn" onclick="scanARPTable()">🔍 Scan ARP Table</button>
                <button class="btn" onclick="networkDiscovery()">🌐 Network Discovery</button>
                <button class="btn btn-secondary" onclick="window.location.href='/'">🏠 Home</button>
                <button class="btn btn-secondary" onclick="window.location.href='/user-management'">👥 Users</button>
                <button class="btn btn-secondary" onclick="window.location.href='/orthanc-server'">🖥️ Orthanc Server</button>
                <button class="btn btn-secondary" onclick="window.location.href='/patient-viewer'">🏥 Patients</button>
                <button class="btn btn-secondary" onclick="window.location.href='/dicom-viewer'">📱 DICOM Viewer</button>
            </div>
        </div>
        
        <div class="content">
            <div id="status"></div>
            
            <div class="devices-grid" id="devicesGrid">
                <div class="empty-state">
                    <h3>Loading devices...</h3>
                    <p>Please wait while we load your medical equipment.</p>
                </div>
            </div>
        </div>
    </div>

    <script>
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
                        <button class="btn btn-small" onclick="testDevice('${device.id}')">🧪 Test</button>
                        <button class="btn btn-small" onclick="editDevice('${device.id}')">✏️ Edit</button>
                        <button class="btn btn-small" onclick="deleteDevice('${device.id}', '${device.name}')">🗑️ Delete</button>
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
                    const message = `✅ ARP scan completed!\\n\\n` +
                                  `Total devices found: ${data.total_found}\\n` +
                                  `Likely medical devices: ${data.medical_found}\\n\\n` +
                                  `Check the console for detailed results.`;
                    
                    showStatus(message.replace(/\\n/g, '<br>'), 'success');
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
                    const message = `✅ Enhanced network discovery completed!\\n\\n` +
                                  `IP Range: ${ipRange}\\n` +
                                  `Total devices found: ${summary.total_found}\\n` +
                                  `Medical devices: ${summary.medical_found}\\n` +
                                  `DICOM capable: ${summary.dicom_capable}\\n` +
                                  `High confidence: ${summary.high_confidence}`;
                    
                    showStatus(message.replace(/\\n/g, '<br>'), 'success');
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
                        ae_title: `${modalityType.toUpperCase()}_${ipAddress.replace(/\\./g, '_')}`
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
        
        // Load devices on page load
        loadDevices();
    </script>
</body>
</html>
"""