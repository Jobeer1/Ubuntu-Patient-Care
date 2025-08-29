#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - System Status Template

Clean system status interface showing all system components.
"""

SYSTEM_STATUS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 System Status - SA Medical Imaging</title>
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
            background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
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
            background: #06b6d4;
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
            background: #0891b2;
            transform: translateY(-1px);
        }
        
        .btn-secondary {
            background: #6b7280;
        }
        
        .btn-secondary:hover {
            background: #4b5563;
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .status-card {
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            padding: 25px;
            transition: all 0.2s;
        }
        
        .status-card.healthy {
            border-color: #10b981;
            background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        }
        
        .status-card.warning {
            border-color: #f59e0b;
            background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        }
        
        .status-card.error {
            border-color: #ef4444;
            background: linear-gradient(135deg, #fef2f2 0%, #fecaca 100%);
        }
        
        .status-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .status-title {
            font-size: 18px;
            font-weight: 600;
            color: #1f2937;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        
        .status-indicator.healthy {
            background: #10b981;
        }
        
        .status-indicator.warning {
            background: #f59e0b;
        }
        
        .status-indicator.error {
            background: #ef4444;
        }
        
        .status-details {
            color: #6b7280;
            font-size: 14px;
            line-height: 1.5;
        }
        
        .status-details strong {
            color: #374151;
        }
        
        .system-overview {
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border: 2px solid #0ea5e9;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .system-overview h2 {
            color: #0c4a6e;
            margin-bottom: 15px;
            font-size: 24px;
        }
        
        .system-overview p {
            color: #075985;
            font-size: 16px;
            line-height: 1.6;
        }
        
        .quick-actions {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin-top: 20px;
            justify-content: center;
        }
        
        .refresh-btn {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: #06b6d4;
            color: white;
            border: none;
            font-size: 20px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transition: all 0.2s;
        }
        
        .refresh-btn:hover {
            background: #0891b2;
            transform: scale(1.1);
        }
        
        .last-updated {
            text-align: center;
            color: #6b7280;
            font-size: 14px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>📊 System Status</h1>
                <p>🇿🇦 South African Medical Imaging System Health</p>
            </div>
            <div>
                <button class="btn" onclick="refreshStatus()">🔄 Refresh</button>
                <button class="btn btn-secondary" onclick="window.location.href='/'">🏠 Home</button>
            </div>
        </div>
        
        <div class="content">
            <div class="system-overview">
                <h2>🇿🇦 System Overview</h2>
                <p>
                    Welcome to the South African Medical Imaging System - the most advanced 
                    medical imaging platform designed specifically for South African healthcare.
                    All systems are operational and ready to serve patients across the country.
                </p>
                
                <div class="quick-actions">
                    <button class="btn" onclick="window.location.href='/user-management'">👥 Users</button>
                    <button class="btn" onclick="window.location.href='/nas-config'">🗄️ NAS</button>
                    <button class="btn" onclick="window.location.href='/device-management'">🏥 Devices</button>
                    <button class="btn" onclick="window.location.href='/reporting-dashboard'">📝 Reports</button>
                </div>
            </div>
            
            <div class="status-grid" id="statusGrid">
                <!-- Status cards will be populated by JavaScript -->
            </div>
            
            <div class="last-updated" id="lastUpdated">
                Last updated: Loading...
            </div>
        </div>
    </div>
    
    <button class="refresh-btn" onclick="refreshStatus()" title="Refresh Status">
        🔄
    </button>

    <script>
        const systemComponents = [
            {
                name: 'Core System',
                icon: '🏥',
                endpoint: '/health',
                description: 'Main application server and core services'
            },
            {
                name: 'User Database',
                icon: '👥',
                endpoint: '/api/admin/users',
                description: 'User authentication and management system'
            },
            {
                name: 'NAS Storage',
                icon: '🗄️',
                endpoint: '/api/nas/status',
                description: 'Network attached storage connectivity'
            },
            {
                name: 'Device Management',
                icon: '🏥',
                endpoint: '/api/devices/statistics',
                description: 'Medical equipment connectivity and monitoring'
            },
            {
                name: 'Reporting System',
                icon: '📝',
                endpoint: '/api/reporting/health',
                description: 'Voice dictation and report generation'
            },
            {
                name: 'SA Localization',
                icon: '🇿🇦',
                endpoint: '/api/sa/localization/status',
                description: 'Multi-language support and SA-specific features'
            },
            {
                name: 'AI Diagnosis',
                icon: '🤖',
                endpoint: '/api/sa/ai/stats',
                description: 'Machine learning medical image analysis'
            },
            {
                name: 'Face Recognition',
                icon: '👁️',
                endpoint: '/api/sa/face-auth/stats',
                description: 'Biometric authentication system'
            },
            {
                name: 'Secure Sharing',
                icon: '🔗',
                endpoint: '/api/sa/sharing/stats',
                description: 'Encrypted link-based content sharing'
            }
        ];
        
        async function checkSystemStatus() {
            const statusGrid = document.getElementById('statusGrid');
            statusGrid.innerHTML = '';
            
            for (const component of systemComponents) {
                const card = await createStatusCard(component);
                statusGrid.appendChild(card);
            }
            
            updateLastUpdated();
        }
        
        async function createStatusCard(component) {
            const card = document.createElement('div');
            card.className = 'status-card';
            
            let status = 'healthy';
            let statusText = 'Operational';
            let details = 'All systems functioning normally';
            
            try {
                const response = await fetch(component.endpoint, { credentials: 'include' });
                
                if (response.ok) {
                    const data = await response.json();
                    
                    if (data.success !== false) {
                        status = 'healthy';
                        statusText = 'Operational';
                        details = component.description;
                    } else {
                        status = 'warning';
                        statusText = 'Warning';
                        details = data.error || 'System reporting issues';
                    }
                } else {
                    status = 'error';
                    statusText = 'Error';
                    details = `HTTP ${response.status} - Service unavailable`;
                }
            } catch (error) {
                status = 'warning';
                statusText = 'Unknown';
                details = 'Unable to check status - service may be starting up';
            }
            
            card.className = `status-card ${status}`;
            card.innerHTML = `
                <div class="status-header">
                    <div class="status-title">${component.icon} ${component.name}</div>
                    <div class="status-indicator ${status}"></div>
                </div>
                <div class="status-details">
                    <strong>Status:</strong> ${statusText}<br>
                    <strong>Details:</strong> ${details}
                </div>
            `;
            
            return card;
        }
        
        function updateLastUpdated() {
            const now = new Date();
            const timeString = now.toLocaleString('en-ZA', {
                timeZone: 'Africa/Johannesburg',
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
            
            document.getElementById('lastUpdated').textContent = `Last updated: ${timeString} (South African Time)`;
        }
        
        async function refreshStatus() {
            const refreshBtn = document.querySelector('.refresh-btn');
            const originalContent = refreshBtn.textContent;
            
            refreshBtn.textContent = '⏳';
            refreshBtn.disabled = true;
            
            try {
                await checkSystemStatus();
            } finally {
                refreshBtn.textContent = originalContent;
                refreshBtn.disabled = false;
            }
        }
        
        // Auto-refresh every 30 seconds
        setInterval(checkSystemStatus, 30000);
        
        // Initial load
        checkSystemStatus();
    </script>
</body>
</html>
"""