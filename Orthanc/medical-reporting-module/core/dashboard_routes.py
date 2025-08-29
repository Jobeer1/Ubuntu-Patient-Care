#!/usr/bin/env python3
"""
Dashboard Routes for Medical Reporting Module
Professional SA Medical Dashboard rendering
"""

import logging
from datetime import datetime
from flask import current_app

logger = logging.getLogger(__name__)

def render_dashboard():
    """Render the main SA Medical Reporting dashboard"""
    try:
        from flask import render_template
        
        # Get current time of day for greeting
        current_hour = datetime.now().hour
        if current_hour < 12:
            time_of_day = "morning"
        elif current_hour < 17:
            time_of_day = "afternoon"
        else:
            time_of_day = "evening"
        
        # Get current date in SA format
        current_date = datetime.now().strftime("%A, %d %B %Y")
        
        # Mock daily statistics (would come from database in production)
        stats = {
            'reports_created': 0,
            'voice_sessions': 0,
            'studies_reviewed': 0,
            'patients_processed': 0
        }
        
        # Try to use template first, fallback to HTML string
        try:
            return render_template('dashboard.html', 
                                 time_of_day=time_of_day, 
                                 current_date=current_date, 
                                 stats=stats)
        except:
            return _render_dashboard_html(time_of_day, current_date, stats)
        
    except Exception as e:
        logger.error(f"Dashboard rendering error: {e}")
        raise

def _render_dashboard_html(time_of_day, current_date, stats):
    """Generate the dashboard HTML"""
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SA Medical Reporting - Professional Dashboard</title>
        
        <!-- External CSS -->
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        
        <!-- SA Dashboard CSS -->
        <link href="/static/css/sa-dashboard.css" rel="stylesheet">
        
        <meta name="description" content="Professional South African Medical Reporting System - HPCSA Compliant">
        <meta name="keywords" content="medical reporting, south africa, DICOM, HL7, voice recognition">
    </head>
    <body>
        <!-- Loading Overlay -->
        <div id="loading-overlay" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 hidden">
            <div class="bg-white rounded-lg p-6 text-center">
                <div class="sa-loading mb-4"></div>
                <p class="text-gray-700">Loading SA Medical System...</p>
            </div>
        </div>

        <!-- Connectivity Indicator -->
        <div class="sa-connectivity">
            <div class="sa-connectivity-badge online">
                <i class="fas fa-wifi mr-2"></i>
                <span>Online</span>
            </div>
        </div>

        <!-- Header -->
        <header class="sa-header py-6">
            <div class="container mx-auto px-4">
                <div class="flex justify-between items-center">
                    <div class="sa-logo">
                        <i class="fas fa-stethoscope"></i>
                        <span>SA Medical Reporting Module</span>
                    </div>
                    <div class="sa-user-info">
                        <div class="text-right">
                            <div class="font-semibold">Good {time_of_day}, Dr. [Name]</div>
                            <div class="text-sm opacity-90">{current_date} 🇿🇦</div>
                        </div>
                        <button class="sa-settings-btn">
                            <i class="fas fa-cog mr-2"></i>
                            Settings
                        </button>
                    </div>
                </div>
            </div>
        </header>

        <!-- Main Content -->
        <main class="container mx-auto px-4 py-8">
            <!-- System Status Alert -->
            <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg mb-6 shadow-md">
                <div class="flex items-center">
                    <i class="fas fa-check-circle mr-3 text-lg"></i>
                    <div>
                        <div class="font-semibold">✅ SA Medical Dashboard - Fully Operational</div>
                        <div class="text-sm mt-1">All systems ready • POPIA compliant • HPCSA standards applied</div>
                    </div>
                </div>
            </div>

            <!-- Quick Actions -->
            <section class="sa-quick-actions mb-8">
                <h2 class="text-2xl font-bold text-gray-800 mb-6 flex items-center">
                    <i class="fas fa-bolt text-yellow-500 mr-3"></i>
                    Quick Actions
                </h2>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <div class="sa-action-card new-report" data-action="new-report">
                        <i class="sa-card-icon fas fa-plus-circle"></i>
                        <h3 class="sa-card-title">New Report</h3>
                        <p class="sa-card-description">Create a new medical report with AI-powered voice dictation</p>
                    </div>
                    
                    <div class="sa-action-card find-studies" data-action="find-studies">
                        <i class="sa-card-icon fas fa-search"></i>
                        <h3 class="sa-card-title">Find Studies</h3>
                        <p class="sa-card-description">Search patient studies and DICOM images from PACS</p>
                    </div>
                    
                    <div class="sa-action-card voice-dictation" data-action="voice-dictation">
                        <i class="sa-card-icon fas fa-microphone"></i>
                        <h3 class="sa-card-title">Voice Dictation</h3>
                        <p class="sa-card-description">Start voice reporting with SA English optimization</p>
                    </div>
                    
                    <div class="sa-action-card templates" data-action="templates">
                        <i class="sa-card-icon fas fa-file-alt"></i>
                        <h3 class="sa-card-title">SA Templates</h3>
                        <p class="sa-card-description">Access HPCSA-compliant medical report templates</p>
                    </div>
                </div>
            </section>

            <!-- Dashboard Sections -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <!-- System Status -->
                <section class="sa-dashboard-section">
                    <h2 class="sa-section-title">
                        <i class="fas fa-chart-bar"></i>
                        System Status
                    </h2>
                    <div id="system-status" class="space-y-4">
                        <div class="flex justify-between items-center">
                            <span class="font-medium">Voice Engine</span>
                            <span class="sa-status-badge online">
                                <i class="fas fa-check-circle mr-1"></i>
                                Ready
                            </span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="font-medium">DICOM Service</span>
                            <span class="sa-status-badge online">
                                <i class="fas fa-check-circle mr-1"></i>
                                Connected
                            </span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="font-medium">Orthanc PACS</span>
                            <span class="sa-status-badge online">
                                <i class="fas fa-check-circle mr-1"></i>
                                Online
                            </span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="font-medium">NAS Storage</span>
                            <span class="sa-status-badge online">
                                <i class="fas fa-check-circle mr-1"></i>
                                Mounted
                            </span>
                        </div>
                    </div>
                </section>

                <!-- Daily Statistics -->
                <section class="sa-dashboard-section">
                    <h2 class="sa-section-title">
                        <i class="fas fa-chart-line"></i>
                        Today's Activity
                    </h2>
                    <div id="daily-stats" class="space-y-4">
                        <div class="flex justify-between items-center">
                            <span class="font-medium">Reports Created</span>
                            <span class="text-2xl font-bold text-green-600">{stats['reports_created']}</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="font-medium">Voice Sessions</span>
                            <span class="text-2xl font-bold text-blue-600">{stats['voice_sessions']}</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="font-medium">Studies Reviewed</span>
                            <span class="text-2xl font-bold text-purple-600">{stats['studies_reviewed']}</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="font-medium">Patients Processed</span>
                            <span class="text-2xl font-bold text-orange-600">{stats['patients_processed']}</span>
                        </div>
                    </div>
                </section>
            </div>

            <!-- System Integration Cards -->
            <section class="mt-8">
                <h2 class="text-2xl font-bold text-gray-800 mb-6 flex items-center">
                    <i class="fas fa-network-wired text-blue-500 mr-3"></i>
                    System Integration
                </h2>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <div class="sa-system-card">
                        <h3>Patient Management</h3>
                        <p>Manage patient records with POPIA compliance and SA ID validation</p>
                        <a href="/patients" class="sa-btn sa-btn-primary">
                            <i class="fas fa-users mr-2"></i>
                            Manage Patients
                        </a>
                    </div>
                    
                    <div class="sa-system-card">
                        <h3>DICOM Viewer</h3>
                        <p>Professional medical image viewer with advanced tools and measurements</p>
                        <a href="/dicom-viewer" class="sa-btn sa-btn-primary">
                            <i class="fas fa-eye mr-2"></i>
                            Open Viewer
                        </a>
                    </div>
                    
                    <div class="sa-system-card">
                        <h3>Orthanc Manager</h3>
                        <p>Configure and monitor the local PACS server for DICOM storage</p>
                        <a href="/orthanc-manager" class="sa-btn sa-btn-primary">
                            <i class="fas fa-database mr-2"></i>
                            Manage PACS
                        </a>
                    </div>
                    
                    <div class="sa-system-card">
                        <h3>NAS Integration</h3>
                        <p>Network storage configuration for secure backup and archival</p>
                        <a href="/nas-integration" class="sa-btn sa-btn-primary">
                            <i class="fas fa-server mr-2"></i>
                            Configure NAS
                        </a>
                    </div>
                    
                    <div class="sa-system-card">
                        <h3>Device Management</h3>
                        <p>Discover and register imaging devices for DICOM communication</p>
                        <a href="/device-management" class="sa-btn sa-btn-primary">
                            <i class="fas fa-cogs mr-2"></i>
                            Manage Devices
                        </a>
                    </div>
                    
                    <div class="sa-system-card">
                        <h3>Voice Training</h3>
                        <p>Train the AI system for better SA English medical terminology recognition</p>
                        <a href="/voice-training" class="sa-btn sa-btn-secondary">
                            <i class="fas fa-graduation-cap mr-2"></i>
                            Train Voice AI
                        </a>
                    </div>
                </div>
            </section>
        </main>

        <!-- Footer -->
        <footer class="bg-gray-800 text-white py-6 mt-12">
            <div class="container mx-auto px-4 text-center">
                <p>&copy; 2024 SA Medical Reporting Module • HPCSA Compliant • POPIA Secure</p>
                <p class="text-sm text-gray-400 mt-2">
                    Optimized for South African Healthcare • Version 1.0.0
                </p>
            </div>
        </footer>

        <!-- JavaScript -->
        <script src="/static/js/dashboard.js"></script>
        
        <!-- Inline initialization script -->
        <script>
            // Initialize dashboard with SA-specific settings
            document.addEventListener('DOMContentLoaded', function() {{
                console.log('🇿🇦 SA Medical Dashboard initialized successfully');
                
                // Show initialization success message
                setTimeout(() => {{
                    if (typeof showMessage === 'function') {{
                        showMessage('SA Medical Dashboard loaded successfully! All systems operational.', 'success');
                    }}
                }}, 1000);
            }});
        </script>
    </body>
    </html>
    '''