#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - Main Interface Template

Clean, modern main interface for the medical imaging system.
"""

MAIN_INTERFACE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🇿🇦 South African Medical Imaging System</title>
    <link rel="icon" type="image/x-icon" href="data:image/x-icon;base64,">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .app-container {
            width: 100%;
            max-width: 400px;
            padding: 20px;
        }
        
        .login-card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 40px;
            text-align: center;
        }
        
        .logo {
            width: 60px;
            height: 60px;
            background: #3b82f6;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            color: white;
            font-size: 24px;
            font-weight: bold;
        }
        
        h1 {
            color: #1f2937;
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .subtitle {
            color: #6b7280;
            font-size: 14px;
            margin-bottom: 30px;
        }
        
        .form-group {
            margin-bottom: 20px;
            text-align: left;
        }
        
        label {
            display: block;
            color: #374151;
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 6px;
        }
        
        input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.2s;
        }
        
        input:focus {
            outline: none;
            border-color: #3b82f6;
        }
        
        .btn {
            width: 100%;
            padding: 12px;
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
            margin-top: 10px;
        }
        
        .btn:hover {
            background: #2563eb;
        }
        
        .btn:disabled {
            background: #9ca3af;
            cursor: not-allowed;
        }
        
        .error {
            background: #fef2f2;
            color: #dc2626;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
            border: 1px solid #fecaca;
        }
        
        .success {
            background: #f0fdf4;
            color: #166534;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
            border: 1px solid #bbf7d0;
        }
        
        .links {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
        }
        
        .links a {
            color: #3b82f6;
            text-decoration: none;
            font-size: 14px;
            margin: 0 10px;
        }
        
        .links a:hover {
            text-decoration: underline;
        }
        
        .sa-flag {
            font-size: 20px;
            margin-right: 8px;
        }
        
        .features {
            margin-top: 20px;
            text-align: left;
            font-size: 12px;
            color: #6b7280;
        }
        
        .features ul {
            list-style: none;
            padding: 0;
        }
        
        .features li {
            margin: 4px 0;
        }
        
        .features li:before {
            content: "✓ ";
            color: #10b981;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="app-container">
        <div class="login-card">
            <div class="logo">🏥</div>
            <h1><span class="sa-flag">🇿🇦</span>Medical Imaging</h1>
            <p class="subtitle">South African Healthcare Technology</p>
            
            <div id="status"></div>
            
            <form id="loginForm">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" required>
                </div>
                
                <div class="form-group">
                    <label for="pin">PIN</label>
                    <input type="password" id="pin" name="pin" required>
                </div>
                
                <button type="submit" class="btn" id="loginBtn">Sign In</button>
            </form>
            
            <div class="links">
                <a href="/user-management">User Management</a>
                <a href="/nas-config">NAS Config</a>
                <a href="/device-management">Devices</a>
                <a href="/system-status">System Status</a>
            </div>
            
            <div class="features">
                <strong>🇿🇦 South African Features:</strong>
                <ul>
                    <li>Multi-language support (EN, AF, ZU)</li>
                    <li>SA medical aid integration</li>
                    <li>Voice dictation with SA accents</li>
                    <li>AI diagnosis for SA conditions</li>
                    <li>Face recognition security</li>
                    <li>Advanced DICOM viewer</li>
                </ul>
            </div>
        </div>
    </div>

    <script>
        // Handle login form submission
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const btn = document.getElementById('loginBtn');
            const originalText = btn.textContent;
            btn.textContent = 'Signing in...';
            btn.disabled = true;
            
            const formData = new FormData(e.target);
            const loginData = {
                username: formData.get('username'),
                pin: formData.get('pin')
            };
            
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(loginData),
                    credentials: 'include'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showStatus('✅ Login successful! Redirecting...', 'success');
                    
                    // Redirect based on user role
                    setTimeout(() => {
                        if (data.user && data.user.role === 'admin') {
                            window.location.href = '/user-management';
                        } else {
                            window.location.href = '/system-status';
                        }
                    }, 1500);
                } else {
                    showStatus('❌ ' + (data.error || 'Login failed'), 'error');
                }
            } catch (error) {
                showStatus('❌ Network error. Please try again.', 'error');
            } finally {
                btn.textContent = originalText;
                btn.disabled = false;
            }
        });
        
        function showStatus(message, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.innerHTML = `<div class="${type}">${message}</div>`;
            
            if (type === 'success') {
                setTimeout(() => {
                    statusDiv.innerHTML = '';
                }, 3000);
            }
        }
        
        // Demo credentials helper
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'd') {
                e.preventDefault();
                document.getElementById('username').value = 'admin';
                document.getElementById('pin').value = 'admin123';
                showStatus('Demo credentials loaded. Press Enter to login.', 'success');
            }
        });
        
        // Show demo credentials hint
        setTimeout(() => {
            showStatus('💡 Press Ctrl+D for demo credentials', 'success');
        }, 2000);
    </script>
</body>
</html>
"""