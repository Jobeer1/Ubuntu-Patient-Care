/**
 * SA Offline DICOM Viewer - Core Application
 * Ubuntu Patient Care System
 * POPI Act Compliant DICOM Viewer for South African Healthcare
 */

class SADicomViewer {
    constructor() {
        this.currentStudy = null;
        this.currentSeries = null;
        this.currentImageIndex = 0;
        this.images = [];
        this.isPlaying = false;
        this.playbackInterval = null;
        this.tools = {};
        this.measurements = [];
        
        this.init();
    }

    async init() {
        console.log('Initializing SA Offline DICOM Viewer...');
        
        // Initialize Cornerstone
        await this.initializeCornerstone();
        
        // Initialize tools
        this.initializeTools();
        
        // Initialize database for offline storage
        await this.initializeDatabase();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Load any cached studies
        await this.loadCachedStudies();
        
        console.log('SA DICOM Viewer initialized successfully');
    }

    async initializeCornerstone() {
        try {
            // Initialize cornerstone
            cornerstone.enable(document.getElementById('dicomElement'));
            
            // Configure DICOM parsers
            cornerstoneWADOImageLoader.external.cornerstone = cornerstone;
            cornerstoneWADOImageLoader.external.dicomParser = dicomParser;
            
            // Initialize web image loader
            cornerstoneWebImageLoader.external.cornerstone = cornerstone;
            
            // Configure for offline use
            cornerstoneWADOImageLoader.configure({
                useWebWorkers: true,
                decodeConfig: {
                    convertFloatPixelDataToInt: false,
                    framesPerChunk: 30
                }
            });

            console.log('Cornerstone initialized successfully');
        } catch (error) {
            console.error('Failed to initialize Cornerstone:', error);
            this.showError('Failed to initialize DICOM viewer');
        }
    }

    initializeTools() {
        const element = document.getElementById('dicomElement');
        
        // Initialize cornerstone tools
        cornerstoneTools.external.cornerstone = cornerstone;
        cornerstoneTools.external.Hammer = Hammer;
        cornerstoneTools.init();

        // Add tools
        const tools = [
            'Wwwc', 'Zoom', 'Pan', 'Length', 'Angle', 'Rectangle', 'Ellipse',
            'Rotate', 'Flip', 'Invert', 'Magnify', 'Probe'
        ];

        tools.forEach(tool => {
            cornerstoneTools.addTool(cornerstoneTools[`${tool}Tool`]);
        });

        // Set initial tool states
        cornerstoneTools.setToolActive('Wwwc', { mouseButtonMask: 1 });
        cornerstoneTools.setToolActive('Zoom', { mouseButtonMask: 2 });
        cornerstoneTools.setToolActive('Pan', { mouseButtonMask: 4 });

        // Enable touch gestures for mobile/tablet support
        cornerstoneTools.addTool(cornerstoneTools.TouchPinchTool);
        cornerstoneTools.addTool(cornerstoneTools.TouchDragTool);
        cornerstoneTools.setToolActive('TouchPinch', {});
        cornerstoneTools.setToolActive('TouchDrag', {});

        console.log('Tools initialized successfully');
    }

    async initializeDatabase() {
        try {
            // Initialize IndexedDB for offline storage
            this.db = new Dexie('SADicomViewer');
            
            this.db.version(1).stores({
                studies: '++id, studyInstanceUID, patientID, studyDate, modality, patientName',
                series: '++id, studyInstanceUID, seriesInstanceUID, modality, bodyPart',
                images: '++id, studyInstanceUID, seriesInstanceUID, sopInstanceUID, imageData',
                measurements: '++id, studyInstanceUID, seriesInstanceUID, toolType, data, timestamp',
                auditLog: '++id, action, studyInstanceUID, timestamp, userInfo'
            });

            await this.db.open();
            console.log('Database initialized successfully');
        } catch (error) {
            console.error('Failed to initialize database:', error);
            // Fallback to localStorage
            this.useLocalStorage = true;
        }
    }

    setupEventListeners() {
        const element = document.getElementById('dicomElement');

        // Cornerstone events
        element.addEventListener('cornerstoneimagerendered', (event) => {
            this.updateImageInfo(event.detail);
        });

        element.addEventListener('cornerstonenewimage', (event) => {
            this.onNewImageDisplayed(event.detail);
        });

        // Tool events
        element.addEventListener('cornerstonetoolsmeasurementadded', (event) => {
            this.onMeasurementAdded(event.detail);
        });

        // Window events
        window.addEventListener('beforeunload', () => {
            this.saveMeasurements();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            this.handleKeyboardShortcuts(event);
        });

        // Touch events for mobile support
        this.setupTouchGestures();
    }

    setupTouchGestures() {
        const element = document.getElementById('dicomElement');
        const hammer = new Hammer(element);

        // Enable pinch and rotate
        hammer.get('pinch').set({ enable: true });
        hammer.get('rotate').set({ enable: true });

        hammer.on('pinchstart pinchmove', (event) => {
            const viewport = cornerstone.getViewport(element);
            viewport.scale = Math.max(0.1, Math.min(10, viewport.scale * event.scale));
            cornerstone.setViewport(element, viewport);
        });

        hammer.on('rotatestart rotatemove', (event) => {
            const viewport = cornerstone.getViewport(element);
            viewport.rotation += event.rotation;
            cornerstone.setViewport(element, viewport);
        });
    }

    async loadStudyFromFiles(files) {
        this.showProgress('Loading DICOM files...', 0);
        
        try {
            const study = {
                studyInstanceUID: null,
                patientID: null,
                patientName: null,
                studyDate: null,
                studyDescription: null,
                modality: null,
                series: new Map(),
                images: []
            };

            let processedFiles = 0;
            
            for (const file of files) {
                try {
                    const arrayBuffer = await this.readFileAsArrayBuffer(file);
                    const byteArray = new Uint8Array(arrayBuffer);
                    const dataSet = dicomParser.parseDicom(byteArray);

                    // Extract DICOM metadata
                    const imageData = this.extractDicomMetadata(dataSet, byteArray);
                    
                    // Group by study
                    if (!study.studyInstanceUID) {
                        study.studyInstanceUID = imageData.studyInstanceUID;
                        study.patientID = imageData.patientID;
                        study.patientName = imageData.patientName;
                        study.studyDate = imageData.studyDate;
                        study.studyDescription = imageData.studyDescription;
                        study.modality = imageData.modality;
                    }

                    // Group by series
                    if (!study.series.has(imageData.seriesInstanceUID)) {
                        study.series.set(imageData.seriesInstanceUID, {
                            seriesInstanceUID: imageData.seriesInstanceUID,
                            seriesNumber: imageData.seriesNumber,
                            seriesDescription: imageData.seriesDescription,
                            modality: imageData.modality,
                            bodyPart: imageData.bodyPart,
                            images: []
                        });
                    }

                    study.series.get(imageData.seriesInstanceUID).images.push(imageData);
                    study.images.push(imageData);

                    processedFiles++;
                    this.updateProgress(`Processing DICOM files... ${processedFiles}/${files.length}`, 
                                      (processedFiles / files.length) * 100);

                } catch (error) {
                    console.warn(`Failed to process file ${file.name}:`, error);
                }
            }

            // Sort images by instance number
            study.images.sort((a, b) => (a.instanceNumber || 0) - (b.instanceNumber || 0));
            
            // Sort series images
            study.series.forEach(series => {
                series.images.sort((a, b) => (a.instanceNumber || 0) - (b.instanceNumber || 0));
            });

            // Store study in database
            await this.storeStudy(study);

            // Load the study
            await this.loadStudy(study);

            this.hideProgress();
            this.logAuditEvent('STUDY_LOADED', study.studyInstanceUID);

        } catch (error) {
            console.error('Failed to load study:', error);
            this.hideProgress();
            this.showError('Failed to load DICOM files');
        }
    }

    extractDicomMetadata(dataSet, byteArray) {
        const getString = (tag) => {
            const element = dataSet.elements[tag];
            return element ? dataSet.string(tag) : '';
        };

        const getNumber = (tag) => {
            const element = dataSet.elements[tag];
            return element ? dataSet.intString(tag) : 0;
        };

        // Create image ID for cornerstone
        const imageId = cornerstoneWADOImageLoader.wadouri.fileManager.add(new File([byteArray], 'dicom'));

        return {
            imageId: imageId,
            sopInstanceUID: getString('x00080018'),
            studyInstanceUID: getString('x0020000d'),
            seriesInstanceUID: getString('x0020000e'),
            patientID: getString('x00100020'),
            patientName: getString('x00100010'),
            patientBirthDate: getString('x00100030'),
            patientSex: getString('x00100040'),
            studyDate: getString('x00080020'),
            studyTime: getString('x00080030'),
            studyDescription: getString('x00081030'),
            seriesNumber: getNumber('x00200011'),
            seriesDescription: getString('x0008103e'),
            instanceNumber: getNumber('x00200013'),
            modality: getString('x00080060'),
            bodyPart: getString('x00180015'),
            institutionName: getString('x00080080'),
            stationName: getString('x00081010'),
            manufacturerModelName: getString('x00081090'),
            sliceThickness: getString('x00180050'),
            pixelSpacing: getString('x00280030'),
            windowCenter: getString('x00281050'),
            windowWidth: getString('x00281051'),
            rescaleIntercept: getString('x00281052'),
            rescaleSlope: getString('x00281053'),
            dataSet: dataSet,
            byteArray: byteArray
        };
    }

    async loadStudy(study) {
        this.currentStudy = study;
        this.images = study.images;
        
        // Update UI
        this.updateStudyList();
        this.updateSeriesList();
        this.updatePatientInfo();
        
        // Load first image
        if (this.images.length > 0) {
            await this.loadImage(0);
            this.generateThumbnails();
        }
    }

    async loadImage(index) {
        if (index < 0 || index >= this.images.length) return;

        this.currentImageIndex = index;
        const image = this.images[index];
        
        try {
            this.showProgress('Loading image...', 0);
            
            const element = document.getElementById('dicomElement');
            await cornerstone.loadAndCacheImage(image.imageId);
            await cornerstone.displayImage(element, image);
            
            // Apply default window/level if available
            if (image.windowCenter && image.windowWidth) {
                const viewport = cornerstone.getViewport(element);
                viewport.voi.windowCenter = parseInt(image.windowCenter);
                viewport.voi.windowWidth = parseInt(image.windowWidth);
                cornerstone.setViewport(element, viewport);
            }

            this.updateImageControls();
            this.hideProgress();
            
        } catch (error) {
            console.error('Failed to load image:', error);
            this.hideProgress();
            this.showError('Failed to load image');
        }
    }

    updateImageInfo(eventDetail) {
        const image = eventDetail.image;
        const viewport = eventDetail.viewport;
        
        // Update overlay information
        const windowLevel = `W/L: ${Math.round(viewport.voi.windowWidth)}/${Math.round(viewport.voi.windowCenter)}`;
        const zoomLevel = `Zoom: ${Math.round(viewport.scale * 100)}%`;
        const sliceInfo = `Image: ${this.currentImageIndex + 1}/${this.images.length}`;
        
        document.querySelector('.window-level').textContent = windowLevel;
        document.querySelector('.zoom-level').textContent = zoomLevel;
        document.querySelector('.slice-info').textContent = sliceInfo;
        
        // Update slider controls
        document.getElementById('windowSlider').value = viewport.voi.windowWidth;
        document.getElementById('levelSlider').value = viewport.voi.windowCenter;
        document.getElementById('imageSlider').value = this.currentImageIndex + 1;
        document.getElementById('imageCounter').textContent = sliceInfo;
    }

    updatePatientInfo() {
        if (!this.currentStudy) return;
        
        const patientInfo = document.getElementById('patientInfo');
        const studyInfo = document.getElementById('studyInfo');
        
        // Patient information (with POPI compliance)
        patientInfo.querySelector('.patient-name').textContent = 
            this.anonymizeIfNeeded(this.currentStudy.patientName) || 'Unknown Patient';
        patientInfo.querySelector('.patient-id').textContent = 
            `ID: ${this.anonymizeIfNeeded(this.currentStudy.patientID) || 'Unknown'}`;
        
        // Study information
        studyInfo.querySelector('.study-date').textContent = 
            `Study Date: ${this.formatDate(this.currentStudy.studyDate)}`;
        studyInfo.querySelector('.modality').textContent = 
            `Modality: ${this.currentStudy.modality || 'Unknown'}`;
        
        // Institution info
        if (this.images.length > 0) {
            document.getElementById('institutionName').textContent = 
                this.images[0].institutionName || 'Healthcare Institution';
        }
    }

    // Tool management methods
    activateTool(toolName) {
        const element = document.getElementById('dicomElement');
        
        // Deactivate all tools first
        cornerstoneTools.setToolPassive('Wwwc');
        cornerstoneTools.setToolPassive('Zoom');
        cornerstoneTools.setToolPassive('Pan');
        cornerstoneTools.setToolPassive('Length');
        cornerstoneTools.setToolPassive('Angle');
        cornerstoneTools.setToolPassive('Rectangle');
        cornerstoneTools.setToolPassive('Ellipse');
        
        // Activate selected tool
        switch (toolName) {
            case 'wwwc':
                cornerstoneTools.setToolActive('Wwwc', { mouseButtonMask: 1 });
                break;
            case 'zoom':
                cornerstoneTools.setToolActive('Zoom', { mouseButtonMask: 1 });
                break;
            case 'pan':
                cornerstoneTools.setToolActive('Pan', { mouseButtonMask: 1 });
                break;
            case 'length':
                cornerstoneTools.setToolActive('Length', { mouseButtonMask: 1 });
                break;
            case 'angle':
                cornerstoneTools.setToolActive('Angle', { mouseButtonMask: 1 });
                break;
            case 'rectangle':
                cornerstoneTools.setToolActive('Rectangle', { mouseButtonMask: 1 });
                break;
            case 'ellipse':
                cornerstoneTools.setToolActive('Ellipse', { mouseButtonMask: 1 });
                break;
            case 'reset':
                this.resetView();
                return;
        }
        
        // Update UI
        document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[data-tool="${toolName}"]`).classList.add('active');
        
        cornerstone.updateImage(element);
    }

    resetView() {
        const element = document.getElementById('dicomElement');
        cornerstone.reset(element);
        cornerstone.updateImage(element);
    }

    // Navigation methods
    nextImage() {
        if (this.currentImageIndex < this.images.length - 1) {
            this.loadImage(this.currentImageIndex + 1);
        }
    }

    previousImage() {
        if (this.currentImageIndex > 0) {
            this.loadImage(this.currentImageIndex - 1);
        }
    }

    firstImage() {
        this.loadImage(0);
    }

    lastImage() {
        this.loadImage(this.images.length - 1);
    }

    goToImage(index) {
        this.loadImage(parseInt(index) - 1);
    }

    togglePlayback() {
        if (this.isPlaying) {
            this.stopPlayback();
        } else {
            this.startPlayback();
        }
    }

    startPlayback() {
        this.isPlaying = true;
        document.getElementById('playBtn').innerHTML = '<i class="icon-pause"></i>';
        
        this.playbackInterval = setInterval(() => {
            if (this.currentImageIndex < this.images.length - 1) {
                this.nextImage();
            } else {
                this.firstImage();
            }
        }, 200); // 5 FPS
    }

    stopPlayback() {
        this.isPlaying = false;
        document.getElementById('playBtn').innerHTML = '<i class="icon-play"></i>';
        
        if (this.playbackInterval) {
            clearInterval(this.playbackInterval);
            this.playbackInterval = null;
        }
    }

    // Window/Level adjustment
    adjustWindow(value) {
        const element = document.getElementById('dicomElement');
        const viewport = cornerstone.getViewport(element);
        viewport.voi.windowWidth = parseInt(value);
        cornerstone.setViewport(element, viewport);
    }

    adjustLevel(value) {
        const element = document.getElementById('dicomElement');
        const viewport = cornerstone.getViewport(element);
        viewport.voi.windowCenter = parseInt(value);
        cornerstone.setViewport(element, viewport);
    }

    applyWindowPreset(preset) {
        if (!preset) return;
        
        const presets = {
            bone: { window: 2000, level: 300 },
            lung: { window: 1500, level: -600 },
            soft_tissue: { window: 400, level: 50 },
            brain: { window: 80, level: 40 },
            liver: { window: 150, level: 90 },
            spine: { window: 250, level: 50 }
        };
        
        if (presets[preset]) {
            const element = document.getElementById('dicomElement');
            const viewport = cornerstone.getViewport(element);
            viewport.voi.windowWidth = presets[preset].window;
            viewport.voi.windowCenter = presets[preset].level;
            cornerstone.setViewport(element, viewport);
            
            // Update sliders
            document.getElementById('windowSlider').value = presets[preset].window;
            document.getElementById('levelSlider').value = presets[preset].level;
        }
    }

    // Utility methods
    async readFileAsArrayBuffer(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (event) => resolve(event.target.result);
            reader.onerror = (error) => reject(error);
            reader.readAsArrayBuffer(file);
        });
    }

    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        const year = dateString.substring(0, 4);
        const month = dateString.substring(4, 6);
        const day = dateString.substring(6, 8);
        return `${day}/${month}/${year}`;
    }

    anonymizeIfNeeded(value) {
        // Check if anonymization is enabled for POPI compliance
        const isAnonymized = localStorage.getItem('anonymizeData') === 'true';
        return isAnonymized ? 'ANONYMIZED' : value;
    }

    showProgress(message, percentage) {
        const overlay = document.getElementById('progressOverlay');
        const text = document.getElementById('progressText');
        const fill = document.getElementById('progressFill');
        
        text.textContent = message;
        fill.style.width = `${percentage}%`;
        overlay.style.display = 'flex';
    }

    updateProgress(message, percentage) {
        const text = document.getElementById('progressText');
        const fill = document.getElementById('progressFill');
        
        text.textContent = message;
        fill.style.width = `${percentage}%`;
    }

    hideProgress() {
        document.getElementById('progressOverlay').style.display = 'none';
    }

    showError(message) {
        alert(`Error: ${message}`);
    }

    async logAuditEvent(action, studyUID) {
        try {
            const auditEntry = {
                action: action,
                studyInstanceUID: studyUID,
                timestamp: new Date().toISOString(),
                userInfo: navigator.userAgent,
                ipAddress: 'offline'
            };

            if (this.db) {
                await this.db.auditLog.add(auditEntry);
            } else {
                const logs = JSON.parse(localStorage.getItem('auditLog') || '[]');
                logs.push(auditEntry);
                localStorage.setItem('auditLog', JSON.stringify(logs));
            }
        } catch (error) {
            console.warn('Failed to log audit event:', error);
        }
    }

    handleKeyboardShortcuts(event) {
        if (event.ctrlKey || event.metaKey) return;
        
        switch (event.code) {
            case 'ArrowLeft':
                event.preventDefault();
                this.previousImage();
                break;
            case 'ArrowRight':
                event.preventDefault();
                this.nextImage();
                break;
            case 'Home':
                event.preventDefault();
                this.firstImage();
                break;
            case 'End':
                event.preventDefault();
                this.lastImage();
                break;
            case 'Space':
                event.preventDefault();
                this.togglePlayback();
                break;
            case 'KeyR':
                event.preventDefault();
                this.resetView();
                break;
        }
    }

    // Additional methods for study management, export, etc. will be added...
}

// Initialize the application
let saViewer;
document.addEventListener('DOMContentLoaded', () => {
    saViewer = new SADicomViewer();
});

// Global functions for HTML event handlers
function loadStudyFromFile() {
    document.getElementById('fileInput').click();
}

function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    if (files.length > 0) {
        saViewer.loadStudyFromFiles(files);
    }
}

function activateTool(toolName) {
    saViewer.activateTool(toolName);
}

function nextImage() {
    saViewer.nextImage();
}

function previousImage() {
    saViewer.previousImage();
}

function firstImage() {
    saViewer.firstImage();
}

function lastImage() {
    saViewer.lastImage();
}

function goToImage(index) {
    saViewer.goToImage(index);
}

function togglePlayback() {
    saViewer.togglePlayback();
}

function adjustWindow(value) {
    saViewer.adjustWindow(value);
}

function adjustLevel(value) {
    saViewer.adjustLevel(value);
}

function applyWindowPreset(preset) {
    saViewer.applyWindowPreset(preset);
}
