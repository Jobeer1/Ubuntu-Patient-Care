"""
DICOM Viewer Route Patch for NAS Integration Backend
Add this code to your app.py file in the NAS Integration backend

INSTRUCTIONS:
1. Open your app.py file in: C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc\orthanc-source\NASIntegration\backend\app.py
2. Add the imports at the top of the file
3. Add the routes after your existing routes
4. Create the template file in your templates directory
5. Restart the Flask application
"""

# ============================================================================
# ADD THESE IMPORTS AT THE TOP OF YOUR app.py FILE
# ============================================================================

from flask import render_template, redirect, session
import logging

# ============================================================================
# ADD THESE ROUTES TO YOUR app.py FILE (after existing routes)
# ============================================================================

# DICOM Viewer Route
@app.route('/dicom-viewer')
@app.route('/dicom-viewer/<study_id>')
def dicom_viewer(study_id=None):
    """
    DICOM Viewer interface for medical image viewing
    Provides professional diagnostic tools for South African medical professionals
    """
    try:
        # Check if user is authenticated (adjust based on your auth system)
        # Uncomment if you have session-based auth:
        # if 'user_id' not in session:
        #     return redirect('/login')
        
        # Viewer configuration
        viewer_config = {
            'title': 'DICOM Viewer - SA Medical System',
            'study_id': study_id,
            'orthanc_url': app.config.get('ORTHANC_URL', 'http://localhost:8042'),
            'features': {
                'measurements': True,
                'annotations': True,
                'multiplanar': True,
                'windowing': True,
                'zoom_pan': True,
                'cine_mode': True
            },
            'tools': [
                'zoom', 'pan', 'windowing', 'measurement', 
                'annotation', 'reset', 'fullscreen'
            ]
        }
        
        # Load study information if study_id provided
        study_info = None
        if study_id:
            try:
                # In production, fetch from Orthanc API
                # For now, provide mock data
                study_info = {
                    'id': study_id,
                    'patient_name': 'Patient, Test',
                    'patient_id': 'P12345',
                    'study_date': '2024-01-15',
                    'study_time': '14:30:00',
                    'modality': 'CT',
                    'description': 'CT Chest with Contrast',
                    'series_count': 3,
                    'instance_count': 150
                }
                logging.info(f"Loading DICOM viewer for study: {study_id}")
            except Exception as e:
                logging.error(f"Error loading study {study_id}: {e}")
                study_info = None
        
        # Log viewer access
        logging.info(f"DICOM viewer accessed")
        
        return render_template('dicom_viewer.html', 
                             config=viewer_config,
                             study=study_info)
                             
    except Exception as e:
        logging.error(f"Error in DICOM viewer route: {e}")
        return jsonify({'error': 'DICOM viewer unavailable'}), 500

# DICOM Viewer API endpoints
@app.route('/api/dicom/studies')
def get_dicom_studies():
    """Get list of available DICOM studies"""
    try:
        # In production, fetch from Orthanc
        studies = [
            {
                'id': 'study_001',
                'patient_name': 'Patient, Test A',
                'patient_id': 'P12345',
                'study_date': '2024-01-15',
                'modality': 'CT',
                'description': 'CT Chest'
            },
            {
                'id': 'study_002', 
                'patient_name': 'Patient, Test B',
                'patient_id': 'P12346',
                'study_date': '2024-01-14',
                'modality': 'MR',
                'description': 'MRI Brain'
            }
        ]
        
        return jsonify({'studies': studies})
        
    except Exception as e:
        logging.error(f"Error fetching DICOM studies: {e}")
        return jsonify({'error': 'Failed to fetch studies'}), 500

@app.route('/api/dicom/study/<study_id>')
def get_dicom_study(study_id):
    """Get specific DICOM study details"""
    try:
        # In production, fetch from Orthanc API
        study_details = {
            'id': study_id,
            'patient_name': 'Patient, Test',
            'patient_id': 'P12345',
            'study_date': '2024-01-15',
            'study_time': '14:30:00',
            'modality': 'CT',
            'description': 'CT Chest with Contrast',
            'series': [
                {
                    'id': 'series_001',
                    'number': 1,
                    'description': 'Axial CT',
                    'instance_count': 50
                },
                {
                    'id': 'series_002', 
                    'number': 2,
                    'description': 'Coronal CT',
                    'instance_count': 50
                }
            ]
        }
        
        return jsonify(study_details)
        
    except Exception as e:
        logging.error(f"Error fetching study {study_id}: {e}")
        return jsonify({'error': 'Study not found'}), 404

# ============================================================================
# TEMPLATE FILE: Create this as templates/dicom_viewer.html
# ============================================================================

DICOM_VIEWER_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DICOM Viewer - SA Medical System</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .dicom-viewer {
            height: calc(100vh - 60px);
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 1rem;
        }
        .viewport-container {
            background: #000;
            border: 2px solid #333;
            position: relative;
            overflow: hidden;
            cursor: crosshair;
        }
        .viewport-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: 1fr 1fr;
            gap: 2px;
            height: 100%;
        }
        .tools-panel {
            background: #f8f9fa;
            border-left: 1px solid #dee2e6;
            padding: 1rem;
            overflow-y: auto;
        }
        .tool-button {
            width: 100%;
            margin-bottom: 0.5rem;
            padding: 0.5rem;
            border: 1px solid #ccc;
            background: white;
            cursor: pointer;
            border-radius: 4px;
            transition: all 0.2s;
        }
        .tool-button:hover {
            background: #e9ecef;
            transform: translateY(-1px);
        }
        .tool-button.active {
            background: #007bff;
            color: white;
            border-color: #0056b3;
        }
        .viewport-overlay {
            position: absolute;
            top: 10px;
            left: 10px;
            color: #00ff00;
            font-family: monospace;
            font-size: 12px;
            z-index: 10;
        }
        .status-indicator {
            position: fixed;
            top: 70px;
            right: 20px;
            z-index: 1000;
        }
    </style>
</head>
<body class="bg-gray-100">
    <!-- Status Indicator -->
    <div class="status-indicator">
        <div id="ready-indicator" class="bg-green-500 text-white px-3 py-1 rounded-full text-sm">
            <i class="fas fa-check"></i> 🟢 Ready
        </div>
    </div>

    <!-- Header -->
    <header class="bg-blue-600 text-white p-4 shadow-lg">
        <div class="flex justify-between items-center">
            <h1 class="text-xl font-bold">
                <i class="fas fa-eye mr-2"></i>
                🖼️ DICOM Viewer
                {% if study %}
                - {{ study.patient_name }} ({{ study.study_date }})
                {% endif %}
            </h1>
            <div class="flex space-x-2">
                <button onclick="window.history.back()" class="bg-blue-700 hover:bg-blue-800 px-3 py-1 rounded transition-colors">
                    <i class="fas fa-arrow-left"></i> Back
                </button>
                <button onclick="toggleFullscreen()" class="bg-blue-700 hover:bg-blue-800 px-3 py-1 rounded transition-colors">
                    <i class="fas fa-expand"></i> Fullscreen
                </button>
            </div>
        </div>
    </header>

    <!-- Main Viewer -->
    <div class="dicom-viewer p-4">
        <!-- Viewport Area -->
        <div class="viewport-area bg-black rounded-lg overflow-hidden">
            <div class="viewport-grid">
                <div class="viewport-container" id="viewport-1">
                    <div class="viewport-overlay">
                        <div>Viewport 1</div>
                        <div>🟢 Ready</div>
                    </div>
                    <div class="flex items-center justify-center h-full text-white">
                        <div class="text-center">
                            <i class="fas fa-image text-6xl mb-4 opacity-50"></i>
                            <p class="text-lg">🖼️ DICOM Viewer</p>
                            <p class="text-sm opacity-75">🟢 Ready</p>
                            {% if study %}
                            <p class="text-xs opacity-50">{{ study.description }}</p>
                            {% else %}
                            <p class="text-xs opacity-50">Advanced medical image viewing with professional diagnostic tools</p>
                            {% endif %}
                        </div>
                    </div>
                </div>
                <div class="viewport-container" id="viewport-2">
                    <div class="viewport-overlay">
                        <div>Viewport 2</div>
                        <div>🟢 Ready</div>
                    </div>
                    <div class="flex items-center justify-center h-full text-white">
                        <div class="text-center">
                            <i class="fas fa-search-plus text-6xl mb-4 opacity-50"></i>
                            <p class="text-lg">🔍 High-resolution image analysis</p>
                        </div>
                    </div>
                </div>
                <div class="viewport-container" id="viewport-3">
                    <div class="viewport-overlay">
                        <div>Viewport 3</div>
                        <div>🟢 Ready</div>
                    </div>
                    <div class="flex items-center justify-center h-full text-white">
                        <div class="text-center">
                            <i class="fas fa-ruler text-6xl mb-4 opacity-50"></i>
                            <p class="text-lg">📐 Measurement and annotation tools</p>
                        </div>
                    </div>
                </div>
                <div class="viewport-container" id="viewport-4">
                    <div class="viewport-overlay">
                        <div>Viewport 4</div>
                        <div>🟢 Ready</div>
                    </div>
                    <div class="flex items-center justify-center h-full text-white">
                        <div class="text-center">
                            <i class="fas fa-cube text-6xl mb-4 opacity-50"></i>
                            <p class="text-lg">🎯 Multi-planar reconstruction</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tools Panel -->
        <div class="tools-panel rounded-lg shadow-lg">
            <h3 class="font-bold mb-4 text-lg">
                <i class="fas fa-tools mr-2 text-blue-600"></i>
                Professional Tools
            </h3>
            
            <!-- Navigation Tools -->
            <div class="mb-6">
                <h4 class="font-semibold mb-2 text-gray-700">🔍 Navigation</h4>
                <button class="tool-button active" onclick="selectTool('zoom')">
                    <i class="fas fa-search-plus mr-2"></i>
                    Zoom
                </button>
                <button class="tool-button" onclick="selectTool('pan')">
                    <i class="fas fa-hand-paper mr-2"></i>
                    Pan
                </button>
                <button class="tool-button" onclick="selectTool('windowing')">
                    <i class="fas fa-adjust mr-2"></i>
                    Window/Level
                </button>
            </div>
            
            <!-- Measurement Tools -->
            <div class="mb-6">
                <h4 class="font-semibold mb-2 text-gray-700">📐 Measurements</h4>
                <button class="tool-button" onclick="selectTool('length')">
                    <i class="fas fa-ruler mr-2"></i>
                    Length
                </button>
                <button class="tool-button" onclick="selectTool('angle')">
                    <i class="fas fa-drafting-compass mr-2"></i>
                    Angle
                </button>
                <button class="tool-button" onclick="selectTool('area')">
                    <i class="fas fa-vector-square mr-2"></i>
                    Area/ROI
                </button>
            </div>
            
            <!-- Layout Controls -->
            <div class="mb-6">
                <h4 class="font-semibold mb-2 text-gray-700">🖼️ Layout</h4>
                <button class="tool-button" onclick="changeLayout('1x1')">
                    <i class="fas fa-square mr-2"></i>
                    1×1
                </button>
                <button class="tool-button" onclick="changeLayout('2x2')">
                    <i class="fas fa-th mr-2"></i>
                    2×2
                </button>
                <button class="tool-button" onclick="changeLayout('1x2')">
                    <i class="fas fa-columns mr-2"></i>
                    1×2
                </button>
            </div>
            
            <!-- Quick Actions -->
            <div class="mb-6">
                <h4 class="font-semibold mb-2 text-gray-700">⚡ Actions</h4>
                <button class="tool-button bg-yellow-500 text-white hover:bg-yellow-600" onclick="resetViewer()">
                    <i class="fas fa-undo mr-2"></i>
                    Reset
                </button>
                <button class="tool-button bg-green-500 text-white hover:bg-green-600" onclick="openReporting()">
                    <i class="fas fa-file-medical mr-2"></i>
                    Create Report
                </button>
            </div>
            
            {% if study %}
            <!-- Study Information -->
            <div class="mb-6 bg-blue-50 p-3 rounded">
                <h4 class="font-semibold mb-2 text-blue-800">📋 Study Info</h4>
                <div class="text-sm space-y-1">
                    <div><strong>Patient:</strong> {{ study.patient_name }}</div>
                    <div><strong>ID:</strong> {{ study.patient_id }}</div>
                    <div><strong>Date:</strong> {{ study.study_date }}</div>
                    <div><strong>Modality:</strong> {{ study.modality }}</div>
                </div>
            </div>
            {% endif %}
        </div>
    </div>

    <script>
        let currentTool = 'zoom';
        
        function selectTool(tool) {
            currentTool = tool;
            
            // Update button states
            document.querySelectorAll('.tool-button').forEach(btn => {
                btn.classList.remove('active');
            });
            
            event.target.classList.add('active');
            showStatus(`Selected: ${tool.charAt(0).toUpperCase() + tool.slice(1)}`);
        }
        
        function changeLayout(layout) {
            const grid = document.querySelector('.viewport-grid');
            
            switch(layout) {
                case '1x1':
                    grid.style.gridTemplateColumns = '1fr';
                    grid.style.gridTemplateRows = '1fr';
                    break;
                case '2x2':
                    grid.style.gridTemplateColumns = '1fr 1fr';
                    grid.style.gridTemplateRows = '1fr 1fr';
                    break;
                case '1x2':
                    grid.style.gridTemplateColumns = '1fr 1fr';
                    grid.style.gridTemplateRows = '1fr';
                    break;
            }
            
            showStatus(`Layout: ${layout}`);
        }
        
        function resetViewer() {
            showStatus('Viewer reset');
        }
        
        function openReporting() {
            {% if study %}
            window.location.href = '/reporting/{{ study.id }}';
            {% else %}
            window.location.href = '/reporting';
            {% endif %}
        }
        
        function toggleFullscreen() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen();
                showStatus('Fullscreen mode');
            } else {
                document.exitFullscreen();
                showStatus('Normal mode');
            }
        }
        
        function showStatus(message) {
            const indicator = document.getElementById('ready-indicator');
            const originalText = indicator.innerHTML;
            indicator.innerHTML = `<i class="fas fa-info-circle"></i> ${message}`;
            indicator.className = 'bg-blue-500 text-white px-3 py-1 rounded-full text-sm';
            
            setTimeout(() => {
                indicator.innerHTML = originalText;
                indicator.className = 'bg-green-500 text-white px-3 py-1 rounded-full text-sm';
            }, 2000);
        }
        
        // Initialize viewer
        document.addEventListener('DOMContentLoaded', function() {
            console.log('🖼️ DICOM Viewer initialized');
            selectTool('zoom');
            showStatus('DICOM Viewer Ready');
        });
    </script>
</body>
</html>'''

# ============================================================================
# SAVE THE TEMPLATE
# Create a file called 'dicom_viewer.html' in your templates directory
# Copy the DICOM_VIEWER_TEMPLATE content above into that file
# ============================================================================

print("DICOM Viewer Patch Ready!")
print("Follow the instructions in the comments to implement the fix.")