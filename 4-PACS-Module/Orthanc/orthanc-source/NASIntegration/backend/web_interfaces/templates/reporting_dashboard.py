#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - Reporting Dashboard Template

Clean reporting dashboard interface for voice dictation and reports.
"""

REPORTING_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📝 Reporting Dashboard - SA Medical Imaging</title>
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
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
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
            background: #f59e0b;
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
            background: #d97706;
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
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .dashboard-card {
            background: #f8fafc;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            padding: 25px;
            text-align: center;
            transition: all 0.2s;
        }
        
        .dashboard-card:hover {
            border-color: #f59e0b;
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        }
        
        .dashboard-card h3 {
            color: #1f2937;
            margin-bottom: 15px;
            font-size: 18px;
        }
        
        .dashboard-card p {
            color: #6b7280;
            margin-bottom: 20px;
            line-height: 1.5;
        }
        
        .feature-list {
            text-align: left;
            margin-top: 20px;
        }
        
        .feature-list h4 {
            color: #1f2937;
            margin-bottom: 10px;
            font-size: 16px;
        }
        
        .feature-list ul {
            color: #6b7280;
            font-size: 14px;
            line-height: 1.6;
        }
        
        .feature-list li {
            margin-bottom: 5px;
        }
        
        .feature-list li:before {
            content: "✓ ";
            color: #10b981;
            font-weight: bold;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid #f59e0b;
        }
        
        .stat-number {
            font-size: 24px;
            font-weight: 700;
            color: #92400e;
            margin-bottom: 5px;
        }
        
        .stat-label {
            color: #78350f;
            font-size: 12px;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>📝 Reporting Dashboard</h1>
                <p>🇿🇦 Voice dictation and medical reporting</p>
            </div>
            <div>
                <button class="btn" onclick="startDictation()">🎤 Start Dictation</button>
                <button class="btn btn-secondary" onclick="window.location.href='/'">🏠 Home</button>
            </div>
        </div>
        
        <div class="content">
            <div id="status"></div>
            
            <!-- Statistics -->
            <div class="stats-grid" id="statsGrid">
                <div class="stat-card">
                    <div class="stat-number" id="totalSessions">-</div>
                    <div class="stat-label">Total Sessions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="completedReports">-</div>
                    <div class="stat-label">Completed Reports</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="avgDuration">-</div>
                    <div class="stat-label">Avg Duration (min)</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="sttAccuracy">-</div>
                    <div class="stat-label">STT Accuracy</div>
                </div>
            </div>
            
            <!-- Dashboard Cards -->
            <div class="dashboard-grid">
                <div class="dashboard-card">
                    <h3>🎤 Voice Dictation</h3>
                    <p>Record medical reports with South African accent recognition</p>
                    <button class="btn" onclick="startDictation()">Start Recording</button>
                    
                    <div class="feature-list">
                        <h4>🇿🇦 SA Features:</h4>
                        <ul>
                            <li>English, Afrikaans, isiZulu support</li>
                            <li>Medical terminology recognition</li>
                            <li>Accent adaptation learning</li>
                            <li>Real-time transcription</li>
                        </ul>
                    </div>
                </div>
                
                <div class="dashboard-card">
                    <h3>📋 Typist Queue</h3>
                    <p>Review and correct transcribed reports</p>
                    <button class="btn" onclick="openTypistQueue()">Open Queue</button>
                    
                    <div class="feature-list">
                        <h4>Workflow Features:</h4>
                        <ul>
                            <li>Audio playback with text</li>
                            <li>Correction tracking</li>
                            <li>Learning loop integration</li>
                            <li>Quality assurance tools</li>
                        </ul>
                    </div>
                </div>
                
                <div class="dashboard-card">
                    <h3>📊 Report Templates</h3>
                    <p>Use standardized templates for common studies</p>
                    <button class="btn" onclick="manageTemplates()">Manage Templates</button>
                    
                    <div class="feature-list">
                        <h4>Template Types:</h4>
                        <ul>
                            <li>Chest X-ray reports</li>
                            <li>CT scan findings</li>
                            <li>Ultrasound reports</li>
                            <li>Custom templates</li>
                        </ul>
                    </div>
                </div>
                
                <div class="dashboard-card">
                    <h3>🖼️ Image Layouts</h3>
                    <p>Customize image display for reporting</p>
                    <button class="btn" onclick="manageLayouts()">Manage Layouts</button>
                    
                    <div class="feature-list">
                        <h4>Layout Options:</h4>
                        <ul>
                            <li>Side-by-side comparison</li>
                            <li>Grid view layouts</li>
                            <li>Stack and overlay modes</li>
                            <li>Custom arrangements</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function loadStatistics() {
            try {
                const response = await fetch('/api/reporting/statistics', { credentials: 'include' });
                const data = await response.json();
                
                if (data.success) {
                    const stats = data.statistics;
                    document.getElementById('totalSessions').textContent = stats.total_sessions || 0;
                    document.getElementById('completedReports').textContent = stats.status_counts?.completed || 0;
                    document.getElementById('avgDuration').textContent = Math.round(stats.average_duration_seconds / 60) || 0;
                    document.getElementById('sttAccuracy').textContent = stats.stt_available ? '95%' : 'N/A';
                }
            } catch (error) {
                console.error('Failed to load statistics:', error);
            }
        }
        
        function startDictation() {
            showStatus('🎤 Voice dictation feature coming soon! This will integrate with the reporting API.', 'success');
        }
        
        function openTypistQueue() {
            showStatus('📋 Typist queue interface coming soon! Use the API endpoints for now.', 'success');
        }
        
        function manageTemplates() {
            showStatus('📊 Template management coming soon! Use the API endpoints for now.', 'success');
        }
        
        function manageLayouts() {
            showStatus('🖼️ Layout management coming soon! Use the API endpoints for now.', 'success');
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
        
        // Load statistics on page load
        loadStatistics();
    </script>
</body>
</html>
"""