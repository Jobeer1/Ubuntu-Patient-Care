# DICOM Viewer Route Fix for NAS Integration Backend
# Add this to your Flask app.py file in the NAS Integration backend

from flask import render_template, jsonify, request, session
import logging

logger = logging.getLogger(__name__)

# DICOM Viewer Route
@app.route('/dicom-viewer')
@app.route('/dicom-viewer/<study_id>')
def dicom_viewer(study_id=None):
    """
    DICOM Viewer interface for medical image viewing
    Integrates with Orthanc server and provides professional diagnostic tools
    """
    try:
        # Check if user is authenticated
        if 'user_id' not in session:
            return redirect('/login')
        
        # Default viewer configuration
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
        
        # If study_id provided, load study information
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
                logger.info(f"Loading DICOM viewer for study: {study_id}")
            except Exception as e:
                logger.error(f"Error loading study {study_id}: {e}")
                study_info = None
        
        # Log viewer access
        logger.info(f"DICOM viewer accessed by user: {session.get('user_id', 'unknown')}")
        
        return render_template('dicom_viewer.html', 
                             config=viewer_config,
                             study=study_info)
                             
    except Exception as e:
        logger.error(f"Error in DICOM viewer route: {e}")
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
        logger.error(f"Error fetching DICOM studies: {e}")
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
        logger.error(f"Error fetching study {study_id}: {e}")
        return jsonify({'error': 'Study not found'}), 404

# Add this template file as well
DICOM_VIEWER_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ config.title }}</title>
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
        }
        
        .tool-button:hover {
            background: #e9ecef;
        }
        
        .tool-button.active {
            background: #007bff;
            color: white;
        }
    </style>
</head>
<body class="bg-gray-100">
    <!-- Header -->
    <header class="bg-blue-600 text-white p-4">
        <div class="flex justify-between items-center">
            <h1 class="text-xl font-bold">
                <i class="fas fa-eye mr-2"></i>
                DICOM Viewer
                {% if study %}
                - {{ study.patient_name }} ({{ study.study_date }})
                {% endif %}
            </h1>
            <div class="flex space-x-2">
                <button onclick="window.history.back()" class="bg-blue-700 hover:bg-blue-800 px-3 py-1 rounded">
                    <i class="fas fa-arrow-left"></i> Back
                </button>
                <button class="bg-blue-700 hover:bg-blue-800 px-3 py-1 rounded">
                    <i class="fas fa-cog"></i> Settings
                </button>
            </div>
        </div>
    </header>

    <!-- Main Viewer -->
    <div class="dicom-viewer">
        <!-- Viewport Area -->
        <div class="viewport-area">
            <div class="viewport-grid">
                <div class="viewport-container" id="viewport-1">
                    <div class="flex items-center justify-center h-full text-white">
                        <div class="text-center">
                            <i class="fas fa-image text-6xl mb-4 opacity-50"></i>
                            <p>Viewport 1</p>
                            {% if study %}
                            <p class="text-sm opacity-75">{{ study.description }}</p>
                            {% else %}
                            <p class="text-sm opacity-75">No study loaded</p>
                            {% endif %}
                        </div>
                    </div>
                </div>
                <div class="viewport-container" id="viewport-2">
                    <div class="flex items-center justify-center h-full text-white">
                        <div class="text-center">
                            <i class="fas fa-image text-6xl mb-4 opacity-50"></i>
                            <p>Viewport 2</p>
                        </div>
                    </div>
                </div>
                <div class="viewport-container" id="viewport-3">
                    <div class="flex items-center justify-center h-full text-white">
                        <div class="text-center">
                            <i class="fas fa-image text-6xl mb-4 opacity-50"></i>
                            <p>Viewport 3</p>
                        </div>
                    </div>
                </div>
                <div class="viewport-container" id="viewport-4">
                    <div class="flex items-center justify-center h-full text-white">
                        <div class="text-center">
                            <i class="fas fa-image text-6xl mb-4 opacity-50"></i>
                            <p>Viewport 4</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tools Panel -->
        <div class="tools-panel">
            <h3 class="font-bold mb-4">
                <i class="fas fa-tools mr-2"></i>
                Viewer Tools
            </h3>
            
            <!-- Navigation Tools -->
            <div class="mb-6">
                <h4 class="font-semibold mb-2">Navigation</h4>
                <button class="tool-button" onclick="selectTool('zoom')">
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
                <h4 class="font-semibold mb-2">Measurements</h4>
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
                    Area
                </button>
            </div>
            
            <!-- Annotation Tools -->
            <div class="mb-6">
                <h4 class="font-semibold mb-2">Annotations</h4>
                <button class="tool-button" onclick="selectTool('arrow')">
                    <i class="fas fa-arrow-right mr-2"></i>
                    Arrow
                </button>
                <button class="tool-button" onclick="selectTool('text')">
                    <i class="fas fa-font mr-2"></i>
                    Text
                </button>
            </div>
            
            <!-- Layout Controls -->
            <div class="mb-6">
                <h4 class="font-semibold mb-2">Layout</h4>
                <button class="tool-button" onclick="changeLayout('1x1')">
                    <i class="fas fa-square mr-2"></i>
                    1x1
                </button>
                <button class="tool-button" onclick="changeLayout('2x2')">
                    <i class="fas fa-th mr-2"></i>
                    2x2
                </button>
                <button class="tool-button" onclick="changeLayout('1x2')">
                    <i class="fas fa-columns mr-2"></i>
                    1x2
                </button>
            </div>
            
            <!-- Study Information -->
            {% if study %}
            <div class="mb-6">
                <h4 class="font-semibold mb-2">Study Info</h4>
                <div class="text-sm space-y-1">
                    <div><strong>Patient:</strong> {{ study.patient_name }}</div>
                    <div><strong>ID:</strong> {{ study.patient_id }}</div>
                    <div><strong>Date:</strong> {{ study.study_date }}</div>
                    <div><strong>Modality:</strong> {{ study.modality }}</div>
                    {% if study.series_count %}
                    <div><strong>Series:</strong> {{ study.series_count }}</div>
                    {% endif %}
                </div>
            </div>
            {% endif %}
            
            <!-- Reset and Actions -->
            <div>
                <button class="tool-button bg-yellow-500 text-white" onclick="resetViewer()">
                    <i class="fas fa-undo mr-2"></i>
                    Reset
                </button>
                <button class="tool-button bg-green-500 text-white" onclick="openReporting()">
                    <i class="fas fa-file-medical mr-2"></i>
                    Create Report
                </button>
            </div>
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
            
            console.log('Selected tool:', tool);
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
            
            console.log('Changed layout to:', layout);
        }
        
        function resetViewer() {
            console.log('Resetting viewer');
            // Reset zoom, pan, windowing to defaults
        }
        
        function openReporting() {
            {% if study %}
            window.location.href = '/reporting/{{ study.id }}';
            {% else %}
            alert('No study loaded for reporting');
            {% endif %}
        }
        
        // Initialize viewer
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DICOM Viewer initialized');
            
            // Set default tool
            selectTool('zoom');
            
            {% if study %}
            console.log('Study loaded:', {{ study | tojson }});
            {% endif %}
        });
    </script>
</body>
</html>
'''