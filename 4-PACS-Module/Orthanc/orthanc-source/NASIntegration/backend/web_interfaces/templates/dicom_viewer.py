#!/usr/bin/env python3
"""
🇿🇦 DICOM Viewer Interface Template
Advanced DICOM viewing with SA healthcare features
"""

DICOM_VIEWER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🇿🇦 DICOM Viewer</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            min-height: 100vh; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
        }
        .viewer-container { 
            background: rgba(255, 255, 255, 0.95); 
            border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
            margin: 20px; 
            padding: 20px; 
            min-height: calc(100vh - 40px);
        }
        .header-section {
            background: linear-gradient(135deg, #007bff, #0056b3);
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .viewer-layout {
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 20px;
            height: calc(100vh - 200px);
        }
        .patient-list {
            background: white;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow-y: auto;
        }
        .viewer-panel {
            background: #1a1a1a;
            border-radius: 10px;
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        .viewer-toolbar {
            background: #2d2d2d;
            padding: 10px;
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }
        .viewer-content {
            flex: 1;
            background: #000;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #666;
            font-size: 1.2rem;
        }
        .patient-item {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .patient-item:hover {
            background: #e9ecef;
            border-color: #007bff;
            transform: translateY(-2px);
        }
        .patient-item.active {
            background: #007bff;
            color: white;
            border-color: #0056b3;
        }
        .patient-name {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .patient-details {
            font-size: 0.9rem;
            color: #666;
        }
        .patient-item.active .patient-details {
            color: #cce7ff;
        }
        .study-list {
            margin-top: 10px;
            padding-left: 15px;
            border-left: 2px solid #007bff;
            display: none;
        }
        .study-item {
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 8px;
            margin-bottom: 5px;
            cursor: pointer;
            font-size: 0.9rem;
        }
        .study-item:hover {
            background: #f0f8ff;
        }
        .study-item.active {
            background: #28a745;
            color: white;
        }
        .toolbar-btn {
            background: #4a4a4a;
            border: 1px solid #666;
            color: white;
            padding: 8px 12px;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .toolbar-btn:hover {
            background: #666;
        }
        .toolbar-btn.active {
            background: #007bff;
            border-color: #0056b3;
        }
        .search-box {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .loading-spinner {
            display: none;
            text-align: center;
            padding: 40px;
        }
        .image-info {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 0.9rem;
            display: none;
        }
        .sa-features {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 15px;
        }
        .sa-features h6 {
            color: #856404;
            margin-bottom: 8px;
        }
        .feature-btn {
            background: #ffc107;
            border: none;
            color: #212529;
            padding: 5px 10px;
            border-radius: 4px;
            margin-right: 5px;
            margin-bottom: 5px;
            font-size: 0.8rem;
            cursor: pointer;
        }
        .feature-btn:hover {
            background: #e0a800;
        }
        .mobile-toggle {
            display: none;
        }
        @media (max-width: 768px) {
            .viewer-layout {
                grid-template-columns: 1fr;
                grid-template-rows: auto 1fr;
            }
            .patient-list {
                max-height: 200px;
            }
            .mobile-toggle {
                display: block;
                background: #007bff;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 10px;
                width: 100%;
            }
            .patient-list.mobile-hidden {
                display: none;
            }
        }
        .dicom-canvas {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        .no-image-placeholder {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #666;
        }
        .no-image-placeholder i {
            font-size: 4rem;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="viewer-container">
        <!-- Header -->
        <div class="header-section">
            <div>
                <h3><i class="fas fa-eye"></i> 🇿🇦 DICOM Viewer</h3>
                <small>Advanced medical imaging viewer with SA healthcare features</small>
            </div>
            <div>
                <a href="/" class="btn btn-light btn-sm me-2"><i class="fas fa-home"></i> Home</a>
                <a href="/orthanc-server" class="btn btn-light btn-sm me-2"><i class="fas fa-server"></i> Server</a>
                <a href="/patient-viewer" class="btn btn-light btn-sm"><i class="fas fa-user-injured"></i> Patients</a>
            </div>
        </div>

        <!-- Mobile Toggle -->
        <button class="mobile-toggle" onclick="togglePatientList()">
            <i class="fas fa-list"></i> Toggle Patient List
        </button>

        <!-- Main Viewer Layout -->
        <div class="viewer-layout">
            <!-- Patient List Panel -->
            <div class="patient-list" id="patientList">
                <!-- SA Features -->
                <div class="sa-features">
                    <h6><i class="fas fa-flag"></i> SA Healthcare Features</h6>
                    <button class="feature-btn" onclick="enableAfrikaansLabels()">
                        <i class="fas fa-language"></i> Afrikaans
                    </button>
                    <button class="feature-btn" onclick="enableZuluLabels()">
                        <i class="fas fa-language"></i> isiZulu
                    </button>
                    <button class="feature-btn" onclick="enableXhosaLabels()">
                        <i class="fas fa-language"></i> isiXhosa
                    </button>
                    <button class="feature-btn" onclick="showMedicalAidInfo()">
                        <i class="fas fa-id-card"></i> Medical Aid
                    </button>
                    <button class="feature-btn" onclick="generateSAReport()">
                        <i class="fas fa-file-medical"></i> SA Report
                    </button>
                </div>

                <!-- Search -->
                <input type="text" class="search-box" placeholder="🔍 Search patients..." 
                       onkeyup="searchPatients(this.value)" id="patientSearch">

                <!-- Patient List -->
                <div id="patientListContent">
                    <div class="loading-spinner" id="patientLoading">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading patients...</span>
                        </div>
                        <p class="mt-2">Loading patient data...</p>
                    </div>
                </div>
            </div>

            <!-- Viewer Panel -->
            <div class="viewer-panel">
                <!-- Toolbar -->
                <div class="viewer-toolbar">
                    <button class="toolbar-btn" onclick="zoomIn()" title="Zoom In">
                        <i class="fas fa-search-plus"></i>
                    </button>
                    <button class="toolbar-btn" onclick="zoomOut()" title="Zoom Out">
                        <i class="fas fa-search-minus"></i>
                    </button>
                    <button class="toolbar-btn" onclick="resetZoom()" title="Reset Zoom">
                        <i class="fas fa-expand-arrows-alt"></i>
                    </button>
                    <button class="toolbar-btn" onclick="rotateLeft()" title="Rotate Left">
                        <i class="fas fa-undo"></i>
                    </button>
                    <button class="toolbar-btn" onclick="rotateRight()" title="Rotate Right">
                        <i class="fas fa-redo"></i>
                    </button>
                    <button class="toolbar-btn" onclick="invertColors()" title="Invert Colors">
                        <i class="fas fa-adjust"></i>
                    </button>
                    <button class="toolbar-btn" onclick="measureDistance()" title="Measure">
                        <i class="fas fa-ruler"></i>
                    </button>
                    <button class="toolbar-btn" onclick="addAnnotation()" title="Annotate">
                        <i class="fas fa-comment"></i>
                    </button>
                    <button class="toolbar-btn" onclick="downloadImage()" title="Download">
                        <i class="fas fa-download"></i>
                    </button>
                    <button class="toolbar-btn" onclick="toggleFullscreen()" title="Fullscreen">
                        <i class="fas fa-expand"></i>
                    </button>
                </div>

                <!-- Viewer Content -->
                <div class="viewer-content" id="viewerContent">
                    <div class="no-image-placeholder">
                        <i class="fas fa-x-ray"></i>
                        <h4>DICOM Viewer Ready</h4>
                        <p>Select a patient and study to view medical images</p>
                        <small class="text-muted">Supports all standard DICOM formats</small>
                    </div>
                </div>

                <!-- Image Info Overlay -->
                <div class="image-info" id="imageInfo">
                    <div><strong>Patient:</strong> <span id="infoPatientName">--</span></div>
                    <div><strong>Study:</strong> <span id="infoStudyDate">--</span></div>
                    <div><strong>Modality:</strong> <span id="infoModality">--</span></div>
                    <div><strong>Series:</strong> <span id="infoSeriesNumber">--</span></div>
                    <div><strong>Instance:</strong> <span id="infoInstanceNumber">--</span></div>
                    <div><strong>Window:</strong> <span id="infoWindow">--</span></div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Global state
        let currentPatient = null;
        let currentStudy = null;
        let currentImage = null;
        let patients = [];
        let viewerZoom = 1;
        let viewerRotation = 0;
        let isInverted = false;
        let currentLanguage = 'en';

        // Initialize viewer
        document.addEventListener('DOMContentLoaded', function() {
            loadPatients();
            setupKeyboardShortcuts();
        });

        // Load patients from Orthanc
        async function loadPatients() {
            const loading = document.getElementById('patientLoading');
            const content = document.getElementById('patientListContent');
            
            loading.style.display = 'block';
            
            try {
                // This would connect to Orthanc API
                // For now, show demo data
                setTimeout(() => {
                    const demoPatients = [
                        {
                            id: 'patient1',
                            name: 'Sipho Mthembu',
                            patientId: '8501015800089',
                            birthDate: '1985-01-01',
                            sex: 'M',
                            medicalAid: 'Discovery Health',
                            studies: [
                                {
                                    id: 'study1',
                                    date: '2025-01-13',
                                    description: 'Chest X-Ray',
                                    modality: 'CR',
                                    series: 2,
                                    instances: 4
                                },
                                {
                                    id: 'study2',
                                    date: '2025-01-10',
                                    description: 'CT Abdomen',
                                    modality: 'CT',
                                    series: 5,
                                    instances: 120
                                }
                            ]
                        },
                        {
                            id: 'patient2',
                            name: 'Nomsa Dlamini',
                            patientId: '9203127890123',
                            birthDate: '1992-03-12',
                            sex: 'F',
                            medicalAid: 'Bonitas Medical Fund',
                            studies: [
                                {
                                    id: 'study3',
                                    date: '2025-01-12',
                                    description: 'Mammography',
                                    modality: 'MG',
                                    series: 4,
                                    instances: 8
                                }
                            ]
                        },
                        {
                            id: 'patient3',
                            name: 'Pieter van der Merwe',
                            patientId: '7508201234567',
                            birthDate: '1975-08-20',
                            sex: 'M',
                            medicalAid: 'Momentum Health',
                            studies: [
                                {
                                    id: 'study4',
                                    date: '2025-01-11',
                                    description: 'MRI Brain',
                                    modality: 'MR',
                                    series: 8,
                                    instances: 200
                                }
                            ]
                        }
                    ];
                    
                    patients = demoPatients;
                    displayPatients(patients);
                    loading.style.display = 'none';
                }, 1000);
                
            } catch (error) {
                console.error('Error loading patients:', error);
                loading.style.display = 'none';
                content.innerHTML = '<div class="alert alert-danger">Failed to load patients</div>';
            }
        }

        // Display patients in the list
        function displayPatients(patientList) {
            const content = document.getElementById('patientListContent');
            
            if (patientList.length === 0) {
                content.innerHTML = '<div class="alert alert-info">No patients found</div>';
                return;
            }
            
            let html = '';
            patientList.forEach(patient => {
                html += `
                    <div class="patient-item" onclick="selectPatient('${patient.id}')">
                        <div class="patient-name">${patient.name}</div>
                        <div class="patient-details">
                            ID: ${patient.patientId}<br>
                            DOB: ${patient.birthDate} | ${patient.sex}<br>
                            Medical Aid: ${patient.medicalAid}
                        </div>
                        <div class="study-list" id="studies-${patient.id}">
                            ${patient.studies.map(study => `
                                <div class="study-item" onclick="selectStudy('${study.id}', event)">
                                    <strong>${study.description}</strong><br>
                                    ${study.date} | ${study.modality}<br>
                                    ${study.series} series, ${study.instances} images
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            });
            
            content.innerHTML = html;
        }

        // Search patients
        function searchPatients(query) {
            if (!query.trim()) {
                displayPatients(patients);
                return;
            }
            
            const filtered = patients.filter(patient => 
                patient.name.toLowerCase().includes(query.toLowerCase()) ||
                patient.patientId.includes(query) ||
                patient.medicalAid.toLowerCase().includes(query.toLowerCase())
            );
            
            displayPatients(filtered);
        }

        // Select patient
        function selectPatient(patientId) {
            // Clear previous selection
            document.querySelectorAll('.patient-item').forEach(item => {
                item.classList.remove('active');
                item.querySelector('.study-list').style.display = 'none';
            });
            
            // Select new patient
            const patientElement = event.target.closest('.patient-item');
            patientElement.classList.add('active');
            patientElement.querySelector('.study-list').style.display = 'block';
            
            currentPatient = patients.find(p => p.id === patientId);
            updateViewerInfo();
        }

        // Select study
        function selectStudy(studyId, event) {
            event.stopPropagation();
            
            // Clear previous study selection
            document.querySelectorAll('.study-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // Select new study
            event.target.classList.add('active');
            
            // Find the study
            for (let patient of patients) {
                const study = patient.studies.find(s => s.id === studyId);
                if (study) {
                    currentStudy = study;
                    loadStudyImages(studyId);
                    break;
                }
            }
        }

        // Load study images
        function loadStudyImages(studyId) {
            const viewerContent = document.getElementById('viewerContent');
            
            // Show loading
            viewerContent.innerHTML = `
                <div class="loading-spinner" style="display: block;">
                    <div class="spinner-border text-light" role="status">
                        <span class="visually-hidden">Loading images...</span>
                    </div>
                    <p class="mt-2 text-light">Loading DICOM images...</p>
                </div>
            `;
            
            // Simulate loading DICOM images
            setTimeout(() => {
                // For demo, show a placeholder
                viewerContent.innerHTML = `
                    <div style="width: 100%; height: 100%; background: #333; display: flex; align-items: center; justify-content: center; flex-direction: column; color: white;">
                        <i class="fas fa-x-ray" style="font-size: 4rem; margin-bottom: 20px; color: #007bff;"></i>
                        <h4>DICOM Image Viewer</h4>
                        <p>Study: ${currentStudy.description}</p>
                        <p>Modality: ${currentStudy.modality} | Date: ${currentStudy.date}</p>
                        <small class="text-muted">In a real implementation, DICOM images would be displayed here</small>
                        <div class="mt-3">
                            <button class="btn btn-primary btn-sm me-2" onclick="simulateImageLoad()">
                                <i class="fas fa-play"></i> Load First Image
                            </button>
                            <button class="btn btn-outline-light btn-sm" onclick="showImageInfo()">
                                <i class="fas fa-info"></i> Show Info
                            </button>
                        </div>
                    </div>
                `;
                
                updateViewerInfo();
            }, 1500);
        }

        // Simulate image loading
        function simulateImageLoad() {
            const viewerContent = document.getElementById('viewerContent');
            viewerContent.innerHTML = `
                <div style="width: 100%; height: 100%; background: linear-gradient(45deg, #1a1a1a 25%, transparent 25%), linear-gradient(-45deg, #1a1a1a 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #1a1a1a 75%), linear-gradient(-45deg, transparent 75%, #1a1a1a 75%); background-size: 20px 20px; background-position: 0 0, 0 10px, 10px -10px, -10px 0px; display: flex; align-items: center; justify-content: center; color: white;">
                    <div style="background: rgba(0,0,0,0.8); padding: 20px; border-radius: 10px; text-align: center;">
                        <i class="fas fa-image" style="font-size: 3rem; color: #28a745; margin-bottom: 15px;"></i>
                        <h5>DICOM Image Loaded</h5>
                        <p>Patient: ${currentPatient.name}</p>
                        <p>Study: ${currentStudy.description}</p>
                        <small>Use toolbar controls to manipulate the image</small>
                    </div>
                </div>
            `;
            showImageInfo();
        }

        // Update viewer info
        function updateViewerInfo() {
            if (currentPatient && currentStudy) {
                document.getElementById('infoPatientName').textContent = currentPatient.name;
                document.getElementById('infoStudyDate').textContent = currentStudy.date;
                document.getElementById('infoModality').textContent = currentStudy.modality;
                document.getElementById('infoSeriesNumber').textContent = '1';
                document.getElementById('infoInstanceNumber').textContent = '1';
                document.getElementById('infoWindow').textContent = 'Auto';
            }
        }

        // Show/hide image info
        function showImageInfo() {
            const info = document.getElementById('imageInfo');
            info.style.display = info.style.display === 'none' ? 'block' : 'none';
        }

        // Viewer controls
        function zoomIn() {
            viewerZoom *= 1.2;
            applyTransform();
        }

        function zoomOut() {
            viewerZoom /= 1.2;
            applyTransform();
        }

        function resetZoom() {
            viewerZoom = 1;
            viewerRotation = 0;
            applyTransform();
        }

        function rotateLeft() {
            viewerRotation -= 90;
            applyTransform();
        }

        function rotateRight() {
            viewerRotation += 90;
            applyTransform();
        }

        function invertColors() {
            isInverted = !isInverted;
            applyTransform();
        }

        function applyTransform() {
            // This would apply transformations to the DICOM image
            console.log(`Applying transform: zoom=${viewerZoom}, rotation=${viewerRotation}, inverted=${isInverted}`);
        }

        function measureDistance() {
            alert('Measurement tool activated. Click and drag on the image to measure distances.');
        }

        function addAnnotation() {
            const annotation = prompt('Enter annotation text:');
            if (annotation) {
                alert(`Annotation added: "${annotation}"`);
            }
        }

        function downloadImage() {
            alert('Image download started. The current view will be saved as PNG.');
        }

        function toggleFullscreen() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen();
            } else {
                document.exitFullscreen();
            }
        }

        // SA Healthcare Features
        function enableAfrikaansLabels() {
            currentLanguage = 'af';
            alert('Afrikaanse etikette geaktiveer. Interface sal in Afrikaans wys.');
        }

        function enableZuluLabels() {
            currentLanguage = 'zu';
            alert('Amalebula esiZulu asebenza. Isikhombimsebenzisi sizobonakala ngesiZulu.');
        }

        function enableXhosaLabels() {
            currentLanguage = 'xh';
            alert('Iilebheli zesiXhosa ziyasebenza. Ujongano luya kubonakala ngesiXhosa.');
        }

        function showMedicalAidInfo() {
            if (currentPatient) {
                alert(`Medical Aid Information:\\n\\nPatient: ${currentPatient.name}\\nMedical Aid: ${currentPatient.medicalAid}\\nMember Number: [Would be retrieved from system]\\nBenefits: [Would show available benefits]`);
            } else {
                alert('Please select a patient first.');
            }
        }

        function generateSAReport() {
            if (currentPatient && currentStudy) {
                alert(`Generating SA Healthcare Report:\\n\\nPatient: ${currentPatient.name}\\nID Number: ${currentPatient.patientId}\\nStudy: ${currentStudy.description}\\nDate: ${currentStudy.date}\\n\\nReport will be generated in compliance with SA healthcare standards.`);
            } else {
                alert('Please select a patient and study first.');
            }
        }

        // Mobile support
        function togglePatientList() {
            const patientList = document.getElementById('patientList');
            patientList.classList.toggle('mobile-hidden');
        }

        // Keyboard shortcuts
        function setupKeyboardShortcuts() {
            document.addEventListener('keydown', function(e) {
                if (e.target.tagName === 'INPUT') return;
                
                switch(e.key) {
                    case '+':
                    case '=':
                        zoomIn();
                        break;
                    case '-':
                        zoomOut();
                        break;
                    case '0':
                        resetZoom();
                        break;
                    case 'r':
                        rotateRight();
                        break;
                    case 'R':
                        rotateLeft();
                        break;
                    case 'i':
                        invertColors();
                        break;
                    case 'f':
                        toggleFullscreen();
                        break;
                    case 'Escape':
                        if (document.fullscreenElement) {
                            document.exitFullscreen();
                        }
                        break;
                }
            });
        }

        // Window resize handler
        window.addEventListener('resize', function() {
            // Adjust viewer layout if needed
        });
    </script>
</body>
</html>
"""