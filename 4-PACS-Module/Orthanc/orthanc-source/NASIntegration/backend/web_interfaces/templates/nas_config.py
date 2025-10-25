#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - NAS Configuration Template

Clean NAS configuration interface extracted from main app.
"""

NAS_CONFIG_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🗄️ NAS Configuration - SA Medical Imaging</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8fafc;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .header p {
            opacity: 0.9;
        }
        
        .content {
            padding: 40px;
        }
        
        .form-group {
            margin-bottom: 25px;
        }
        
        label {
            display: block;
            color: #374151;
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 14px;
        }
        
        input, select {
            width: 100%;
            padding: 14px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 16px;
            transition: all 0.2s;
        }
        
        input:focus, select:focus {
            outline: none;
            border-color: #10b981;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
        }
        
        .checkbox-group {
            display: flex;
            align-items: center;
            padding: 16px;
            background: #f8fafc;
            border-radius: 8px;
            border: 2px solid #e5e7eb;
        }
        
        .checkbox-group input[type="checkbox"] {
            width: auto;
            margin-right: 12px;
            transform: scale(1.2);
        }
        
        .checkbox-group label {
            margin: 0;
            font-weight: 500;
            color: #1f2937;
        }
        
        .btn {
            background: #10b981;
            color: white;
            border: none;
            padding: 14px 28px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            margin-right: 12px;
            transition: all 0.2s;
        }
        
        .btn:hover {
            background: #059669;
            transform: translateY(-1px);
        }
        
        .btn-test {
            background: #3b82f6;
        }
        
        .btn-test:hover {
            background: #2563eb;
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
            margin-bottom: 25px;
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
        
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
        }
        
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }
        
        .info-card {
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 25px;
        }
        
        .info-card h3 {
            color: #0369a1;
            margin-bottom: 10px;
            font-size: 16px;
        }
        
        .info-card ul {
            color: #0c4a6e;
            font-size: 14px;
            line-height: 1.6;
        }
        
        .info-card li {
            margin-bottom: 5px;
        }
        
        .connection-status {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-weight: 500;
        }
        
        .connection-status.connected {
            background: #dcfce7;
            color: #166534;
            border: 1px solid #bbf7d0;
        }
        
        .connection-status.disconnected {
            background: #fef2f2;
            color: #dc2626;
            border: 1px solid #fecaca;
        }
        
        .connection-status.testing {
            background: #fef3c7;
            color: #92400e;
            border: 1px solid #fde68a;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗄️ NAS Configuration</h1>
            <p>🇿🇦 Configure your Network Attached Storage connection</p>
        </div>
        
        <div class="content">
            <div id="status"></div>
            
            <div class="connection-status disconnected" id="connectionStatus">
                <span>🔴 NAS Status: Disconnected</span>
            </div>
            
            <div class="info-card">
                <h3>🇿🇦 South African NAS Integration</h3>
                <ul>
                    <li>✓ Supports all major NAS brands (Synology, QNAP, FreeNAS)</li>
                    <li>✓ SMB/CIFS protocol for Windows compatibility</li>
                    <li>✓ Secure authentication and encryption</li>
                    <li>✓ Automatic reconnection and error handling</li>
                    <li>✓ Real-time storage monitoring</li>
                </ul>
            </div>
            
            <form id="nasConfigForm">
                <div class="form-group">
                    <div class="checkbox-group">
                        <input type="checkbox" id="enabled">
                        <label for="enabled">🔌 Enable NAS Integration</label>
                    </div>
                </div>
                
                <div class="grid">
                    <div class="form-group">
                        <label for="type">🔗 Connection Type</label>
                        <select id="type" name="type">
                            <option value="smb">SMB/CIFS (Windows Share)</option>
                            <option value="nfs">NFS (Network File System)</option>
                            <option value="local">Local Storage (Testing)</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="host">🌐 NAS Host/IP Address</label>
                        <input type="text" id="host" name="host" placeholder="192.168.1.100">
                    </div>
                </div>
                
                <div class="grid">
                    <div class="form-group">
                        <label for="port">🔌 Port</label>
                        <input type="number" id="port" name="port" value="445">
                    </div>
                    
                    <div class="form-group">
                        <label for="share">📁 Share Name</label>
                        <input type="text" id="share" name="share" placeholder="medical_images">
                    </div>
                </div>
                
                <div class="grid">
                    <div class="form-group">
                        <label for="username">👤 Username</label>
                        <input type="text" id="username" name="username" placeholder="nas_user">
                    </div>
                    
                    <div class="form-group">
                        <label for="password">🔒 Password</label>
                        <input type="password" id="password" name="password" placeholder="••••••••">
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="path">📂 Storage Path</label>
                    <input type="text" id="path" name="path" value="/dicom" placeholder="/dicom">
                </div>
                
                <div style="margin-top: 40px; display: flex; gap: 12px; flex-wrap: wrap;">
                    <button type="button" class="btn btn-test" onclick="testConnection()">🧪 Test Connection</button>
                    <button type="button" class="btn" onclick="discoverNAS()" style="background: #f59e0b;">🔍 Discover NAS</button>
                    <button type="button" class="btn" onclick="quickConnect()" style="background: #8b5cf6;">⚡ Quick Connect</button>
                    <button type="submit" class="btn">💾 Save Configuration</button>
                    <button type="button" class="btn btn-secondary" onclick="window.location.href='/'">🏠 Home</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        // Load current configuration
        async function loadConfig() {
            try {
                const response = await fetch('/api/nas/config', { credentials: 'include' });
                const data = await response.json();
                
                if (data.success) {
                    const config = data.config;
                    document.getElementById('enabled').checked = config.enabled || false;
                    document.getElementById('type').value = config.type || 'smb';
                    document.getElementById('host').value = config.host || '';
                    document.getElementById('port').value = config.port || 445;
                    document.getElementById('share').value = config.share || '';
                    document.getElementById('username').value = config.username || '';
                    document.getElementById('path').value = config.path || '/dicom';
                    
                    updateConnectionStatus(config.enabled);
                    // Don't populate password for security
                }
            } catch (error) {
                showStatus('❌ Failed to load configuration', 'error');
            }
        }
        
        function updateConnectionStatus(enabled) {
            const statusEl = document.getElementById('connectionStatus');
            if (enabled) {
                statusEl.className = 'connection-status connected';
                statusEl.innerHTML = '<span>🟢 NAS Status: Connected</span>';
            } else {
                statusEl.className = 'connection-status disconnected';
                statusEl.innerHTML = '<span>🔴 NAS Status: Disconnected</span>';
            }
        }
        
        // Test NAS connection
        async function testConnection() {
            const btn = event.target;
            const originalText = btn.textContent;
            const statusEl = document.getElementById('connectionStatus');
            
            btn.textContent = '🔄 Testing...';
            btn.disabled = true;
            statusEl.className = 'connection-status testing';
            statusEl.innerHTML = '<span>🟡 NAS Status: Testing connection...</span>';
            
            try {
                const response = await fetch('/api/nas/test', {
                    method: 'POST',
                    credentials: 'include'
                });
                const data = await response.json();
                
                if (data.success) {
                    showStatus('✅ Connection successful! ' + data.message, 'success');
                    statusEl.className = 'connection-status connected';
                    statusEl.innerHTML = '<span>🟢 NAS Status: Connection Test Passed</span>';
                } else {
                    showStatus('❌ Connection failed: ' + data.message, 'error');
                    statusEl.className = 'connection-status disconnected';
                    statusEl.innerHTML = '<span>🔴 NAS Status: Connection Test Failed</span>';
                }
            } catch (error) {
                showStatus('❌ Test failed: Network error', 'error');
                statusEl.className = 'connection-status disconnected';
                statusEl.innerHTML = '<span>🔴 NAS Status: Network Error</span>';
            } finally {
                btn.textContent = originalText;
                btn.disabled = false;
            }
        }
        
        // Save configuration
        document.getElementById('nasConfigForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const config = {
                enabled: document.getElementById('enabled').checked,
                type: formData.get('type'),
                host: formData.get('host'),
                port: parseInt(formData.get('port')),
                share: formData.get('share'),
                username: formData.get('username'),
                password: formData.get('password'),
                path: formData.get('path')
            };
            
            try {
                const response = await fetch('/api/nas/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config),
                    credentials: 'include'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showStatus('✅ Configuration saved successfully!', 'success');
                    updateConnectionStatus(config.enabled);
                } else {
                    showStatus('❌ Failed to save: ' + data.error, 'error');
                }
            } catch (error) {
                showStatus('❌ Save failed: Network error', 'error');
            }
        });
        
        function showStatus(message, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.innerHTML = `<div class="status ${type}">${message}</div>`;
            
            // Auto-hide success messages
            if (type === 'success') {
                setTimeout(() => {
                    statusDiv.innerHTML = '';
                }, 5000);
            }
        }
        
        // NAS Discovery Functions
        async function discoverNAS() {
            const ipRange = prompt('Enter IP range to scan for NAS devices (e.g., 192.168.1.0/24):');
            if (!ipRange) return;
            
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '🔄 Discovering...';
            btn.disabled = true;
            
            try {
                showStatus('🔍 Scanning network for NAS devices...', 'success');
                
                const response = await fetch('/api/nas/discover', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({
                        ip_range: ipRange,
                        max_threads: 50
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    const message = `✅ NAS discovery completed!\\n\\n` +
                                  `Total devices found: ${data.total_found}\\n` +
                                  `Recommended NAS devices: ${data.recommended_count}\\n\\n` +
                                  `Check the console for detailed results.`;
                    
                    showStatus(message.replace(/\\n/g, '<br>'), 'success');
                    console.log('NAS Discovery Results:', data);
                    
                    // Show discovered NAS devices
                    if (data.discovered_nas.length > 0) {
                        showDiscoveredNAS(data.discovered_nas);
                    }
                } else {
                    showStatus('❌ NAS discovery failed: ' + data.error, 'error');
                }
            } catch (error) {
                showStatus('❌ NAS discovery failed: Network error', 'error');
            } finally {
                btn.textContent = originalText;
                btn.disabled = false;
            }
        }
        
        function showDiscoveredNAS(nasList) {
            let nasInfo = '\\n\\nDiscovered NAS Devices:\\n';
            nasList.forEach((nas, index) => {
                nasInfo += `\\n${index + 1}. ${nas.ip_address}`;
                if (nas.hostname) nasInfo += ` (${nas.hostname})`;
                if (nas.likely_nas) nasInfo += ' 🗄️ NAS';
                if (nas.manufacturer && nas.manufacturer !== 'Unknown') nasInfo += ` - ${nas.manufacturer}`;
                if (nas.nas_type && nas.nas_type !== 'unknown') nasInfo += ` [${nas.nas_type}]`;
                if (nas.priority_score) nasInfo += ` (Score: ${nas.priority_score})`;
            });
            
            const useNAS = confirm(nasInfo + '\\n\\nWould you like to configure one of these NAS devices?');
            
            if (useNAS) {
                // For now, show instructions
                alert('To configure a discovered NAS:\\n\\n1. Note the IP address and manufacturer\\n2. Use the Quick Connect button\\n3. Enter the NAS credentials\\n\\nFull auto-configuration coming soon!');
            }
        }
        
        async function quickConnect() {
            const host = prompt('Enter NAS IP address:');
            if (!host) return;
            
            const username = prompt('Enter username:');
            if (!username) return;
            
            const password = prompt('Enter password:');
            if (!password) return;
            
            const share = prompt('Enter share name (or press OK for default):', 'dicom');
            
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '🔄 Connecting...';
            btn.disabled = true;
            
            try {
                showStatus('⚡ Setting up quick NAS connection...', 'success');
                
                const response = await fetch('/api/nas/quick-connect', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({
                        host: host,
                        username: username,
                        password: password,
                        share: share || 'dicom',
                        type: 'smb',
                        port: 445
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showStatus('✅ NAS configured successfully!', 'success');
                    
                    // Update form with new configuration
                    loadConfig();
                    
                    // Show connection test result
                    if (data.connection_test) {
                        const testResult = data.connection_test.success ? 
                            `✅ Connection test: ${data.connection_test.message}` :
                            `⚠️ Connection test: ${data.connection_test.message}`;
                        
                        setTimeout(() => showStatus(testResult, data.connection_test.success ? 'success' : 'error'), 2000);
                    }
                } else {
                    showStatus('❌ Quick connect failed: ' + data.error, 'error');
                }
            } catch (error) {
                showStatus('❌ Quick connect failed: Network error', 'error');
            } finally {
                btn.textContent = originalText;
                btn.disabled = false;
            }
        }
        
        // Load configuration on page load
        loadConfig();
    </script>
</body>
</html>
"""