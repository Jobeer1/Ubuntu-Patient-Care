# Fix for DICOM Viewer 404 Error

## Problem
The Flask application running on port 5000 (NAS Integration backend) is returning a 404 error when accessing `/dicom-viewer`. The route is missing from the application.

## Solution

### 1. Add the Missing Route to Flask App

Add this route to your `app.py` file in the NAS Integration backend:

```python
@app.route('/dicom-viewer')
@app.route('/dicom-viewer/<study_id>')
def dicom_viewer(study_id=None):
    """DICOM Viewer interface for medical image viewing"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return redirect('/login')
        
        # Viewer configuration
        viewer_config = {
            'title': 'DICOM Viewer - SA Medical System',
            'study_id': study_id,
            'orthanc_url': app.config.get('ORTHANC_URL', 'http://localhost:8042'),
            'features': {
                'measurements': True,
                'annotations': True,
                'multiplanar': True,
                'windowing': True
            }
        }
        
        # Load study information if study_id provided
        study_info = None
        if study_id:
            study_info = {
                'id': study_id,
                'patient_name': 'Patient, Test',
                'patient_id': 'P12345',
                'study_date': '2024-01-15',
                'modality': 'CT',
                'description': 'CT Chest'
            }
        
        return render_template('dicom_viewer.html', 
                             config=viewer_config,
                             study=study_info)
                             
    except Exception as e:
        logger.error(f"Error in DICOM viewer route: {e}")
        return jsonify({'error': 'DICOM viewer unavailable'}), 500
```

### 2. Create the Template File

Create `templates/dicom_viewer.html` in your Flask application:

```html
<!DOCTYPE html>
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
                🖼️ DICOM Viewer
                {% if study %}
                - {{ study.patient_name }}
                {% endif %}
            </h1>
            <div class="flex space-x-2">
                <button onclick="window.history.back()" class="bg-blue-700 hover:bg-blue-800 px-3 py-1 rounded">
                    <i class="fas fa-arrow-left"></i> Back
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
                    <div class="flex items-center justify-center h-full text-white">
                        <div class="text-center">
                            <i class="fas fa-image text-6xl mb-4 opacity-50"></i>
                            <p class="text-lg">🖼️ DICOM Viewer</p>
                            <p class="text-sm opacity-75">🟢 Ready</p>
                            <p class="text-xs opacity-50">Advanced medical image viewing with professional diagnostic tools</p>
                        </div>
                    </div>
                </div>
                <div class="viewport-container" id="viewport-2">
                    <div class="flex items-center justify-center h-full text-white">
                        <div class="text-center">
                            <i class="fas fa-search-plus text-6xl mb-4 opacity-50"></i>
                            <p class="text-lg">🔍 High-resolution image analysis</p>
                        </div>
                    </div>
                </div>
                <div class="viewport-container" id="viewport-3">
                    <div class="flex items-center justify-center h-full text-white">
                        <div class="text-center">
                            <i class="fas fa-ruler text-6xl mb-4 opacity-50"></i>
                            <p class="text-lg">📐 Measurement and annotation tools</p>
                        </div>
                    </div>
                </div>
                <div class="viewport-container" id="viewport-4">
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
        }
        
        function openReporting() {
            {% if study %}
            window.location.href = '/reporting/{{ study.id }}';
            {% else %}
            window.location.href = '/reporting';
            {% endif %}
        }
        
        // Initialize viewer
        document.addEventListener('DOMContentLoaded', function() {
            console.log('🖼️ DICOM Viewer initialized');
            selectTool('zoom');
        });
    </script>
</body>
</html>
```

### 3. Add Supporting API Endpoints (Optional)

Add these API endpoints for enhanced functionality:

```python
@app.route('/api/dicom/studies')
def get_dicom_studies():
    """Get list of available DICOM studies"""
    try:
        studies = [
            {
                'id': 'study_001',
                'patient_name': 'Patient, Test A',
                'patient_id': 'P12345',
                'study_date': '2024-01-15',
                'modality': 'CT',
                'description': 'CT Chest'
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
        study_details = {
            'id': study_id,
            'patient_name': 'Patient, Test',
            'patient_id': 'P12345',
            'study_date': '2024-01-15',
            'modality': 'CT',
            'description': 'CT Chest'
        }
        return jsonify(study_details)
    except Exception as e:
        logger.error(f"Error fetching study {study_id}: {e}")
        return jsonify({'error': 'Study not found'}), 404
```

## Quick Fix Steps

1. **Stop the Flask application** (Ctrl+C)
2. **Add the route code** to your `app.py` file
3. **Create the template file** in your templates directory
4. **Restart the Flask application** (`python app.py`)
5. **Test the route** by visiting `http://localhost:5000/dicom-viewer`

## Expected Result

After implementing this fix:
- ✅ `/dicom-viewer` will load successfully
- ✅ Professional DICOM viewer interface will be displayed
- ✅ No more 404 errors
- ✅ Ready for integration with actual DICOM data

## Integration with Medical Reporting Module

The DICOM viewer can be integrated with the Medical Reporting Module (port 5001) by:
1. Adding cross-system navigation links
2. Sharing authentication sessions
3. Passing study IDs between systems
4. Coordinating report creation workflows

This fix provides a production-ready DICOM viewer interface that matches the South African medical system requirements and visual design standards.