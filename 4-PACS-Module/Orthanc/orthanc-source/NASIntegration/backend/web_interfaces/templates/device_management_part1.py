#!/usr/bin/env python3
"""
Part 1 of the Device Management template (header + layout).
This file contains the first half of the HTML template to keep files small.
"""

DEVICE_MANAGEMENT_TEMPLATE_PART1 = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏥 Device Management - SA Medical Imaging</title>
    <!-- Font Awesome for action icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Dashboard styling to match the rest of the app -->
    <link rel="stylesheet" href="/static/css/dashboard.css">
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
        
        /* Dashboard-consistent utilities */
        .header h1 { font-size: 20px; margin: 0; }
        .action-buttons .btn { border-radius: 8px; padding: 8px 12px; font-weight: 600; }
        .btn-primary, .btn[style*="#3b82f6"] { background: #3b82f6; color: #fff; }
        .btn-success, .btn[style*="#10b981"] { background: #10b981; color: #fff; }
        .btn-ghost { background: transparent; border: 1px solid #e5e7eb; }
        .devices-grid { padding: 20px; }
        .device-card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; margin-bottom: 12px; display: flex; gap: 16px; align-items: center; }
        .device-header .device-name { font-weight: 700; color: #111827; }
        .device-info { color: #6b7280; font-size: 13px; }
        .device-actions .btn { margin-right: 6px; }
        .table thead { background: #f8fafc; }
        .device-row.online { background: #f0fdf4; }
        .device-row.offline { background: #fff7ed; }
        .badge { border-radius: 999px; padding: 6px 8px; font-size: 12px; }
        .btn-action { width: 36px; height: 36px; display: inline-flex; align-items: center; justify-content: center; border-radius: 8px; }
        .btn-action i { font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header" style="display:flex; justify-content:space-between; align-items:center; padding:18px 20px;">
            <div>
                <h1 style="margin:0; font-size:22px;">📡 Device Management</h1>
                <div id="status" style="margin-top:8px;"></div>
            </div>
            <div style="display:flex; gap:12px; align-items:center;">
                <div class="config-item">
                    <label style="display: block; margin-bottom: 5px; font-weight: 500; color: #374151;">Start IP:</label>
                    <input type="text" id="subnetStartIp" value="192.168.1.1" style="width: 140px; padding: 8px; border: 1px solid #d1d5db; border-radius: 6px;">
                </div>
                <div class="config-item">
                    <label style="display: block; margin-bottom: 5px; font-weight: 500; color: #374151;">End IP:</label>
                    <input type="text" id="subnetEndIp" value="192.168.1.254" style="width: 140px; padding: 8px; border: 1px solid #d1d5db; border-radius: 6px;">
                </div>
                <div class="config-item">
                    <label style="display: block; margin-bottom: 5px; font-weight: 500; color: #374151;">Timeout (s):</label>
                    <input type="number" id="subnetTimeout" min="1" max="60" value="2" style="width: 80px; padding: 8px; border: 1px solid #d1d5db; border-radius: 6px;">
                </div>
                <div class="config-item">
                    <label style="display: block; margin-bottom: 5px; font-weight: 500; color: #374151;">Max Concurrent:</label>
                    <input type="number" id="subnetMaxConcurrent" min="1" max="50" value="10" style="width: 80px; padding: 8px; border: 1px solid #d1d5db; border-radius: 6px;">
                </div>
            </div>
        </div>

        <div class="action-buttons" style="display: flex; gap: 10px; flex-wrap: wrap; padding: 12px 16px;">
            <button class="btn" onclick="discoverSubnet()" style="background: #3b82f6; color: white;">🔍 Discover Subnet</button>
            <button class="btn" onclick="pingSubnetRange()" style="background: #10b981; color: white;">🎯 Ping Range</button>
            <button class="btn" onclick="scanSubnetDevices()" style="background: #8b5cf6; color: white;">🔎 Scan Devices</button>
            <button class="btn btn-secondary" onclick="saveSubnetSettings()" style="background: #6b7280; color: white;">💾 Save Settings</button>
            <button class="btn btn-secondary" onclick="loadSubnetSettings()" style="background: #4b5563; color: white;">📂 Load Settings</button>
        </div>

        <!-- Discovered IP Addresses Section -->
        <div class="discovered-ips-section" style="margin: 18px 16px;">
            <h3 style="margin-bottom: 12px; color: #1f2937;">📋 Discovered IP Addresses</h3>
            <div id="subnetResults" style="background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="text-align: center; color: #6b7280; padding: 40px;">
                    <p>Configure subnet above and click "Discover Subnet" to find devices</p>
                </div>
            </div>
        </div>

        <div class="devices-grid" id="devicesGrid" style="padding: 0 16px 20px 16px;">
            <div class="empty-state">
                <h3>Loading devices...</h3>
                <p>Please wait while we load your medical equipment.</p>
            </div>
        </div>

        <!-- Subnet IP Addresses Display (below connected machines) -->
        <div class="subnet-ips-display" style="margin: 18px 16px 40px 16px;">
            <h3 style="margin-bottom: 12px; color: #1f2937;">🌐 Subnet IP Addresses</h3>
            <div id="subnetIpDisplay" style="background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="text-align: center; color: #6b7280; padding: 40px;">
                    <p>Set IP range above and click "Display All IPs" to show subnet addresses</p>
                    <button class="btn" onclick="displayAllSubnetIps()" style="background: #8b5cf6; color: white; margin-top: 15px;">📋 Display All IPs</button>
                </div>
            </div>
        </div>
    </div>

"""
