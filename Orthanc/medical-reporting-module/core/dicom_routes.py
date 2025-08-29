#!/usr/bin/env python3
"""
DICOM Routes for Medical Reporting Module
DICOM viewer and management interfaces
"""

import logging

logger = logging.getLogger(__name__)

def render_dicom_viewer():
    """Render the DICOM viewer interface"""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DICOM Viewer - SA Medical Reporting</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        
        <style>
            .dicom-viewer-container {
                height: calc(100vh - 120px);
                background: #1a1a1a;
                border-radius: 8px;
                position: relative;
                overflow: hidden;
            }
            
            .dicom-image-area {
                width: 100%;
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #000;
                position: relative;
            }
            
            .dicom-tools {
                position: absolute;
                top: 10px;
                left: 10px;
                z-index: 10;
                display: flex;
                gap: 8px;
            }
            
            .dicom-tool-btn {
                background: rgba(0, 0, 0, 0.7);
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                cursor: pointer;
                transition: background 0.3s;
            }
            
            .dicom-tool-btn:hover {
                background: rgba(0, 0, 0, 0.9);
            }
            
            .dicom-tool-btn.active {
                background: #007A4D;
            }
            
            .dicom-info-panel {
                position: absolute;
                top: 10px;
                right: 10px;
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 12px;
                border-radius: 4px;
                font-size: 12px;
                max-width: 250px;
            }
            
            .study-list {
                max-height: 400px;
                overflow-y: auto;
            }
            
            .study-item {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 8px;
                cursor: pointer;
                transition: all 0.3s;
            }
            
            .study-item:hover {
                border-color: #007A4D;
                background: #f0f9ff;
            }
            
            .study-item.selected {
                border-color: #007A4D;
                background: #e6f7ff;
            }
            
            .loading-overlay {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.7);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                z-index: 20;
            }
            
            .loading-spinner {
                border: 3px solid #333;
                border-top: 3px solid #007A4D;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin-right: 12px;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body class="bg-gray-100">
        <!-- Header -->
        <header class="bg-white shadow-sm border-b">
            <div class="container mx-auto px-6 py-4">
                <div class="flex justify-between items-center">
                    <div class="flex items-center space-x-4">
                        <div class="bg-blue-100 p-2 rounded-full">
                            <i class="fas fa-eye text-blue-600"></i>
                        </div>
                        <div>
                            <h1 class="text-2xl font-bold text-gray-800">DICOM Viewer</h1>
                            <p class="text-gray-600">Professional Medical Image Viewer</p>
                        </div>
                    </div>
                    <div class="flex items-center space-x-4">
                        <button id="upload-btn" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
                            <i class="fas fa-upload mr-2"></i>Upload DICOM
                        </button>
                        <a href="/" class="text-gray-600 hover:text-gray-800">
                            <i class="fas fa-home mr-2"></i>Dashboard
                        </a>
                    </div>
                </div>
            </div>
        </header>

        <!-- Main Content -->
        <div class="container mx-auto px-6 py-6">
            <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
                <!-- Study List Panel -->
                <div class="lg:col-span-1">
                    <div class="bg-white rounded-lg shadow p-6">
                        <h3 class="text-lg font-semibold mb-4 flex items-center">
                            <i class="fas fa-list mr-2 text-blue-600"></i>
                            Studies
                        </h3>
                        
                        <!-- Search Form -->
                        <div class="mb-4 space-y-3">
                            <input type="text" id="patient-search" placeholder="Patient ID or Name..." 
                                   class="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 text-sm">
                            <input type="date" id="study-date" 
                                   class="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 text-sm">
                            <button id="search-btn" class="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 text-sm">
                                <i class="fas fa-search mr-2"></i>Search Studies
                            </button>
                        </div>
                        
                        <!-- Study List -->
                        <div id="study-list" class="study-list">
                            <div class="text-center text-gray-500 py-8">
                                <i class="fas fa-search text-3xl mb-2"></i>
                                <p>Search for studies to begin</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- DICOM Viewer Panel -->
                <div class="lg:col-span-3">
                    <div class="bg-white rounded-lg shadow p-6">
                        <h3 class="text-lg font-semibold mb-4 flex items-center">
                            <i class="fas fa-image mr-2 text-green-600"></i>
                            Image Viewer
                        </h3>
                        
                        <div class="dicom-viewer-container">
                            <!-- Loading Overlay -->
                            <div id="loading-overlay" class="loading-overlay hidden">
                                <div class="loading-spinner"></div>
                                <span>Loading DICOM image...</span>
                            </div>
                            
                            <!-- DICOM Tools -->
                            <div class="dicom-tools">
                                <button class="dicom-tool-btn" id="zoom-tool" title="Zoom">
                                    <i class="fas fa-search-plus"></i>
                                </button>
                                <button class="dicom-tool-btn" id="pan-tool" title="Pan">
                                    <i class="fas fa-hand-paper"></i>
                                </button>
                                <button class="dicom-tool-btn" id="window-tool" title="Window/Level">
                                    <i class="fas fa-adjust"></i>
                                </button>
                                <button class="dicom-tool-btn" id="measure-tool" title="Measure">
                                    <i class="fas fa-ruler"></i>
                                </button>
                                <button class="dicom-tool-btn" id="reset-tool" title="Reset">
                                    <i class="fas fa-undo"></i>
                                </button>
                            </div>
                            
                            <!-- DICOM Info Panel -->
                            <div id="dicom-info" class="dicom-info-panel hidden">
                                <div class="font-semibold mb-2">Image Information</div>
                                <div id="dicom-details"></div>
                            </div>
                            
                            <!-- Image Display Area -->
                            <div class="dicom-image-area" id="dicom-display">
                                <div class="text-center text-gray-400">
                                    <i class="fas fa-image text-6xl mb-4"></i>
                                    <p class="text-xl">Select a study to view DICOM images</p>
                                    <p class="text-sm mt-2">Professional DICOM viewer with advanced tools</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Upload Modal -->
        <div id="upload-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-50">
            <div class="bg-white rounded-lg p-6 w-full max-w-md mx-4">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-semibold">Upload DICOM File</h3>
                    <button id="close-upload" class="text-gray-500 hover:text-gray-700">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <div class="mb-4">
                    <input type="file" id="dicom-file" accept=".dcm,.dicom" 
                           class="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500">
                    <p class="text-sm text-gray-600 mt-2">Select a DICOM file (.dcm, .dicom)</p>
                </div>
                
                <div class="flex justify-end space-x-4">
                    <button id="cancel-upload" class="px-4 py-2 border rounded text-gray-600 hover:bg-gray-50">
                        Cancel
                    </button>
                    <button id="confirm-upload" class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
                        <i class="fas fa-upload mr-2"></i>Upload
                    </button>
                </div>
            </div>
        </div>

        <script>
            // DICOM Viewer JavaScript
            class DICOMViewer {
                constructor() {
                    this.currentStudy = null;
                    this.currentSeries = null;
                    this.currentTool = 'zoom';
                    
                    this.initializeElements();
                    this.setupEventListeners();
                    this.checkOrthancConnection();
                }
                
                initializeElements() {
                    this.studyList = document.getElementById('study-list');
                    this.dicomDisplay = document.getElementById('dicom-display');
                    this.dicomInfo = document.getElementById('dicom-info');
                    this.loadingOverlay = document.getElementById('loading-overlay');
                    this.uploadModal = document.getElementById('upload-modal');
                }
                
                setupEventListeners() {
                    // Search functionality
                    document.getElementById('search-btn').addEventListener('click', () => this.searchStudies());
                    document.getElementById('patient-search').addEventListener('keypress', (e) => {
                        if (e.key === 'Enter') this.searchStudies();
                    });
                    
                    // Tool buttons
                    document.querySelectorAll('.dicom-tool-btn').forEach(btn => {
                        btn.addEventListener('click', (e) => this.selectTool(e.target.id));
                    });
                    
                    // Upload functionality
                    document.getElementById('upload-btn').addEventListener('click', () => this.showUploadModal());
                    document.getElementById('close-upload').addEventListener('click', () => this.hideUploadModal());
                    document.getElementById('cancel-upload').addEventListener('click', () => this.hideUploadModal());
                    document.getElementById('confirm-upload').addEventListener('click', () => this.uploadDICOM());
                }
                
                async checkOrthancConnection() {
                    try {
                        const response = await fetch('/api/dicom/orthanc/status');
                        const data = await response.json();
                        
                        if (data.connected) {
                            console.log('✅ Orthanc PACS connected:', data.status.version);
                        } else {
                            console.warn('⚠️ Orthanc PACS not connected:', data.status.error);
                            this.showMessage('Orthanc PACS not connected. Some features may be limited.', 'warning');
                        }
                    } catch (error) {
                        console.error('❌ Failed to check Orthanc connection:', error);
                    }
                }
                
                async searchStudies() {
                    const patientSearch = document.getElementById('patient-search').value;
                    const studyDate = document.getElementById('study-date').value;
                    
                    if (!patientSearch && !studyDate) {
                        this.showMessage('Please enter search criteria', 'error');
                        return;
                    }
                    
                    this.showLoading('Searching studies...');
                    
                    try {
                        const params = new URLSearchParams();
                        if (patientSearch) {
                            if (patientSearch.includes(' ')) {
                                params.append('patient_name', patientSearch);
                            } else {
                                params.append('patient_id', patientSearch);
                            }
                        }
                        if (studyDate) params.append('study_date', studyDate.replace(/-/g, ''));
                        
                        const response = await fetch(`/api/dicom/studies?${params}`);
                        const data = await response.json();
                        
                        this.displayStudies(data.studies || []);
                        
                    } catch (error) {
                        console.error('Study search error:', error);
                        this.showMessage('Failed to search studies', 'error');
                    } finally {
                        this.hideLoading();
                    }
                }
                
                displayStudies(studies) {
                    if (studies.length === 0) {
                        this.studyList.innerHTML = `
                            <div class="text-center text-gray-500 py-8">
                                <i class="fas fa-search text-3xl mb-2"></i>
                                <p>No studies found</p>
                                <p class="text-sm">Try different search criteria</p>
                            </div>
                        `;
                        return;
                    }
                    
                    this.studyList.innerHTML = studies.map(study => `
                        <div class="study-item" data-study-id="${study.orthanc_id}">
                            <div class="font-semibold text-sm">${study.patient_name || 'Unknown Patient'}</div>
                            <div class="text-xs text-gray-600 mt-1">
                                ID: ${study.patient_id || 'N/A'}<br>
                                Date: ${this.formatDate(study.study_date)}<br>
                                Description: ${study.study_description || 'N/A'}<br>
                                Series: ${study.series_count} | Instances: ${study.instances_count}
                            </div>
                        </div>
                    `).join('');
                    
                    // Add click handlers
                    this.studyList.querySelectorAll('.study-item').forEach(item => {
                        item.addEventListener('click', () => this.selectStudy(item.dataset.studyId));
                    });
                }
                
                async selectStudy(studyId) {
                    // Update UI
                    this.studyList.querySelectorAll('.study-item').forEach(item => {
                        item.classList.remove('selected');
                    });
                    this.studyList.querySelector(`[data-study-id="${studyId}"]`).classList.add('selected');
                    
                    this.showLoading('Loading study details...');
                    
                    try {
                        const response = await fetch(`/api/dicom/studies/${studyId}`);
                        const data = await response.json();
                        
                        this.currentStudy = data.study;
                        this.displayStudyInfo();
                        
                        // Load first series if available
                        if (this.currentStudy.series && this.currentStudy.series.length > 0) {
                            this.loadSeries(this.currentStudy.series[0]);
                        }
                        
                    } catch (error) {
                        console.error('Study selection error:', error);
                        this.showMessage('Failed to load study details', 'error');
                    } finally {
                        this.hideLoading();
                    }
                }
                
                displayStudyInfo() {
                    if (!this.currentStudy) return;
                    
                    const details = `
                        <div><strong>Patient:</strong> ${this.currentStudy.patient_name}</div>
                        <div><strong>ID:</strong> ${this.currentStudy.patient_id}</div>
                        <div><strong>Date:</strong> ${this.formatDate(this.currentStudy.study_date)}</div>
                        <div><strong>Description:</strong> ${this.currentStudy.study_description}</div>
                        <div><strong>Series:</strong> ${this.currentStudy.series.length}</div>
                        <div><strong>Instances:</strong> ${this.currentStudy.total_instances}</div>
                    `;
                    
                    document.getElementById('dicom-details').innerHTML = details;
                    this.dicomInfo.classList.remove('hidden');
                }
                
                async loadSeries(series) {
                    this.showLoading('Loading DICOM image...');
                    
                    try {
                        // For demo purposes, show a placeholder
                        this.dicomDisplay.innerHTML = `
                            <div class="text-center text-white">
                                <i class="fas fa-x-ray text-6xl mb-4"></i>
                                <p class="text-xl">DICOM Image Viewer</p>
                                <p class="text-sm mt-2">Series: ${series.series_description}</p>
                                <p class="text-sm">Modality: ${series.modality}</p>
                                <p class="text-sm">Instances: ${series.instances_count}</p>
                                <div class="mt-4 text-xs text-gray-400">
                                    Professional DICOM viewer would display the actual image here
                                </div>
                            </div>
                        `;
                        
                    } catch (error) {
                        console.error('Series loading error:', error);
                        this.showMessage('Failed to load DICOM image', 'error');
                    } finally {
                        this.hideLoading();
                    }
                }
                
                selectTool(toolId) {
                    // Update tool buttons
                    document.querySelectorAll('.dicom-tool-btn').forEach(btn => {
                        btn.classList.remove('active');
                    });
                    document.getElementById(toolId).classList.add('active');
                    
                    this.currentTool = toolId.replace('-tool', '');
                    console.log('Selected tool:', this.currentTool);
                }
                
                showUploadModal() {
                    this.uploadModal.classList.remove('hidden');
                }
                
                hideUploadModal() {
                    this.uploadModal.classList.add('hidden');
                    document.getElementById('dicom-file').value = '';
                }
                
                async uploadDICOM() {
                    const fileInput = document.getElementById('dicom-file');
                    const file = fileInput.files[0];
                    
                    if (!file) {
                        this.showMessage('Please select a DICOM file', 'error');
                        return;
                    }
                    
                    const formData = new FormData();
                    formData.append('file', file);
                    
                    this.showLoading('Uploading DICOM file...');
                    
                    try {
                        const response = await fetch('/api/dicom/upload', {
                            method: 'POST',
                            body: formData
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            this.showMessage('DICOM file uploaded successfully', 'success');
                            this.hideUploadModal();
                            // Refresh studies if search was performed
                            if (this.studyList.children.length > 0) {
                                this.searchStudies();
                            }
                        } else {
                            this.showMessage(data.error || 'Upload failed', 'error');
                        }
                        
                    } catch (error) {
                        console.error('Upload error:', error);
                        this.showMessage('Failed to upload DICOM file', 'error');
                    } finally {
                        this.hideLoading();
                    }
                }
                
                showLoading(message) {
                    this.loadingOverlay.querySelector('span').textContent = message;
                    this.loadingOverlay.classList.remove('hidden');
                }
                
                hideLoading() {
                    this.loadingOverlay.classList.add('hidden');
                }
                
                showMessage(message, type) {
                    // Create notification
                    const notification = document.createElement('div');
                    notification.className = `fixed top-4 right-4 p-4 rounded-lg text-white z-50 ${
                        type === 'success' ? 'bg-green-600' : 
                        type === 'warning' ? 'bg-yellow-600' : 'bg-red-600'
                    }`;
                    notification.innerHTML = `
                        <div class="flex items-center">
                            <i class="fas fa-${type === 'success' ? 'check' : type === 'warning' ? 'exclamation-triangle' : 'times'} mr-2"></i>
                            ${message}
                        </div>
                    `;
                    
                    document.body.appendChild(notification);
                    
                    setTimeout(() => {
                        document.body.removeChild(notification);
                    }, 5000);
                }
                
                formatDate(dateStr) {
                    if (!dateStr) return 'N/A';
                    if (dateStr.length === 8) {
                        return `${dateStr.substr(0,4)}-${dateStr.substr(4,2)}-${dateStr.substr(6,2)}`;
                    }
                    return dateStr;
                }
            }
            
            // Initialize DICOM viewer
            document.addEventListener('DOMContentLoaded', function() {
                console.log('🏥 Initializing DICOM Viewer...');
                window.dicomViewer = new DICOMViewer();
                console.log('✅ DICOM Viewer initialized');
            });
        </script>
    </body>
    </html>
    '''