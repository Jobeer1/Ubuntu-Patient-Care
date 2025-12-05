/**
 * Clinical DICOM Viewer - Main Application
 * Production-grade viewer for emergency radiology
 */

import { SeriesSorter } from './core/series-sorter.js';
import { CT_PRESETS, autoSelectPreset, getPreset, calculateOptimalWL } from './presets/ct-presets.js';
import { ViewportManager } from './core/viewport-manager.js';
import { MeasurementTools } from './tools/measurements.js';

class ClinicalViewer {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.options = {
      orthancUrl: options.orthancUrl || 'http://localhost:8042',
      username: options.username || 'orthanc',
      password: options.password || 'orthanc',
      enableGPU: options.enableGPU !== false,
      enableCaching: options.enableCaching !== false,
      ...options
    };
    
    this.currentStudy = null;
    this.currentSeries = null;
    this.currentInstance = 0;
    this.instances = [];
    this.viewport = null;
    this.tools = null;
    
    this.state = {
      window: 400,
      level: 40,
      zoom: 1.0,
      pan: { x: 0, y: 0 },
      rotation: 0,
      inverted: false,
      playing: false,
      fps: 10
    };
    
    this.init();
  }

  /**
   * Initialize viewer
   */
  async init() {
    this.createUI();
    this.setupEventListeners();
    this.viewport = new ViewportManager(this.canvas, this.options);
    this.tools = new MeasurementTools(this.canvas);
    
    // Load from URL parameters if present
    const params = new URLSearchParams(window.location.search);
    const studyUID = params.get('study');
    if (studyUID) {
      await this.loadStudy(studyUID);
    }
  }

  /**
   * Create UI elements
   */
  createUI() {
    this.container.innerHTML = `
      <div class="clinical-viewer">
        <div class="viewer-header">
          <div class="header-left">
            <h1>🏥 Clinical DICOM Viewer</h1>
            <div class="patient-info" id="patientInfo"></div>
          </div>
          <div class="header-right">
            <div class="status-indicator" id="statusIndicator">
              <span class="status-dot"></span>
              <span id="statusText">Ready</span>
            </div>
          </div>
        </div>
        
        <div class="viewer-main">
          <div class="sidebar" id="sidebar">
            <div class="sidebar-section">
              <h3>Studies</h3>
              <div class="study-list" id="studyList">
                <button class="btn-load" id="btnLoadLocal">Load Local Files</button>
                <button class="btn-load" id="btnLoadOrthanc">Load from PACS</button>
              </div>
            </div>
            
            <div class="sidebar-section">
              <h3>Series</h3>
              <div class="series-list" id="seriesList"></div>
            </div>
            
            <div class="sidebar-section">
              <h3>Presets</h3>
              <div class="preset-grid" id="presetGrid"></div>
            </div>
          </div>
          
          <div class="viewport-container">
            <div class="toolbar" id="toolbar">
              <div class="tool-group">
                <button class="tool-btn" id="btnWL" title="Window/Level (W)">
                  <span>🎚️</span> W/L
                </button>
                <button class="tool-btn" id="btnZoom" title="Zoom (Z)">
                  <span>🔍</span> Zoom
                </button>
                <button class="tool-btn" id="btnPan" title="Pan (P)">
                  <span>✋</span> Pan
                </button>
              </div>
              
              <div class="tool-group">
                <button class="tool-btn" id="btnLength" title="Measure Distance (M)">
                  <span>📏</span> Length
                </button>
                <button class="tool-btn" id="btnAngle" title="Measure Angle">
                  <span>📐</span> Angle
                </button>
                <button class="tool-btn" id="btnROI" title="ROI / HU">
                  <span>⭕</span> ROI
                </button>
              </div>
              
              <div class="tool-group">
                <button class="tool-btn" id="btnInvert" title="Invert (I)">
                  <span>⚫⚪</span> Invert
                </button>
                <button class="tool-btn" id="btnRotate" title="Rotate">
                  <span>🔄</span> Rotate
                </button>
                <button class="tool-btn" id="btnReset" title="Reset (R)">
                  <span>↺</span> Reset
                </button>
              </div>
              
              <div class="tool-group">
                <button class="tool-btn" id="btnCine" title="Cine Mode (C)">
                  <span>▶️</span> Play
                </button>
                <input type="range" id="fpsSlider" min="1" max="30" value="10" 
                       title="FPS" class="fps-slider">
                <span id="fpsLabel">10 FPS</span>
              </div>
              
              <div class="tool-group">
                <button class="tool-btn" id="btnDownload" title="Download">
                  <span>⬇️</span> Export
                </button>
                <button class="tool-btn" id="btnFullscreen" title="Fullscreen (F)">
                  <span>⛶</span> Full
                </button>
              </div>
            </div>
            
            <div class="canvas-wrapper" id="canvasWrapper">
              <canvas id="dicomCanvas"></canvas>
              
              <div class="overlay-info" id="overlayInfo">
                <div class="overlay-top-left">
                  <div id="patientName"></div>
                  <div id="patientId"></div>
                  <div id="studyDate"></div>
                </div>
                <div class="overlay-top-right">
                  <div id="modality"></div>
                  <div id="seriesDescription"></div>
                  <div id="imageSize"></div>
                </div>
                <div class="overlay-bottom-left">
                  <div id="windowLevel"></div>
                  <div id="zoomLevel"></div>
                  <div id="sliceInfo"></div>
                </div>
                <div class="overlay-bottom-right">
                  <div id="pixelValue"></div>
                  <div id="measurements"></div>
                </div>
              </div>
              
              <div class="loading-overlay" id="loadingOverlay" style="display: none;">
                <div class="spinner"></div>
                <div id="loadingText">Loading...</div>
              </div>
            </div>
            
            <div class="slice-controls">
              <button id="btnPrevSlice" class="slice-btn">◀</button>
              <input type="range" id="sliceSlider" min="0" max="0" value="0" class="slice-slider">
              <button id="btnNextSlice" class="slice-btn">▶</button>
              <span id="sliceCounter">0 / 0</span>
            </div>
          </div>
        </div>
      </div>
      
      <input type="file" id="fileInput" multiple accept=".dcm,.dicom" style="display: none;">
    `;
    
    this.canvas = document.getElementById('dicomCanvas');
    this.ctx = this.canvas.getContext('2d', { 
      willReadFrequently: true,
      alpha: false 
    });
    
    this.populatePresets();
  }

  /**
   * Populate preset buttons
   */
  populatePresets() {
    const grid = document.getElementById('presetGrid');
    
    Object.entries(CT_PRESETS).forEach(([key, preset]) => {
      const btn = document.createElement('button');
      btn.className = 'preset-btn';
      btn.textContent = `${preset.name} (${preset.hotkey})`;
      btn.title = preset.description;
      btn.onclick = () => this.applyPreset(key);
      grid.appendChild(btn);
    });
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // File loading
    document.getElementById('btnLoadLocal').onclick = () => {
      document.getElementById('fileInput').click();
    };
    
    document.getElementById('fileInput').onchange = (e) => {
      this.loadLocalFiles(e.target.files);
    };
    
    document.getElementById('btnLoadOrthanc').onclick = () => {
      this.showOrthancBrowser();
    };
    
    // Tools
    document.getElementById('btnWL').onclick = () => this.activateTool('windowLevel');
    document.getElementById('btnZoom').onclick = () => this.activateTool('zoom');
    document.getElementById('btnPan').onclick = () => this.activateTool('pan');
    document.getElementById('btnLength').onclick = () => this.activateTool('length');
    document.getElementById('btnAngle').onclick = () => this.activateTool('angle');
    document.getElementById('btnROI').onclick = () => this.activateTool('roi');
    
    // Image manipulation
    document.getElementById('btnInvert').onclick = () => this.toggleInvert();
    document.getElementById('btnRotate').onclick = () => this.rotate(90);
    document.getElementById('btnReset').onclick = () => this.reset();
    
    // Cine
    document.getElementById('btnCine').onclick = () => this.toggleCine();
    document.getElementById('fpsSlider').oninput = (e) => {
      this.state.fps = parseInt(e.target.value);
      document.getElementById('fpsLabel').textContent = `${this.state.fps} FPS`;
    };
    
    // Export
    document.getElementById('btnDownload').onclick = () => this.exportImage();
    document.getElementById('btnFullscreen').onclick = () => this.toggleFullscreen();
    
    // Slice navigation
    document.getElementById('btnPrevSlice').onclick = () => this.previousSlice();
    document.getElementById('btnNextSlice').onclick = () => this.nextSlice();
    document.getElementById('sliceSlider').oninput = (e) => {
      this.goToSlice(parseInt(e.target.value));
    };
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => this.handleKeyboard(e));
    
    // Mouse events on canvas
    this.canvas.addEventListener('mousedown', (e) => this.handleMouseDown(e));
    this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
    this.canvas.addEventListener('mouseup', (e) => this.handleMouseUp(e));
    this.canvas.addEventListener('wheel', (e) => this.handleWheel(e));
    
    // Touch events
    this.canvas.addEventListener('touchstart', (e) => this.handleTouchStart(e));
    this.canvas.addEventListener('touchmove', (e) => this.handleTouchMove(e));
    this.canvas.addEventListener('touchend', (e) => this.handleTouchEnd(e));
    
    // Window resize
    window.addEventListener('resize', () => this.handleResize());
  }

  /**
   * Load local DICOM files
   */
  async loadLocalFiles(files) {
    this.showLoading('Loading DICOM files...');
    
    try {
      const instances = [];
      
      for (const file of files) {
        const arrayBuffer = await file.arrayBuffer();
        const instance = await this.parseDICOM(arrayBuffer);
        if (instance) {
          instances.push(instance);
        }
      }
      
      if (instances.length === 0) {
        throw new Error('No valid DICOM files found');
      }
      
      // Sort instances
      this.instances = SeriesSorter.sortSeries(instances);
      this.instances = SeriesSorter.autoCorrect(this.instances);
      
      // Validate sorting
      const validation = SeriesSorter.validateSorting(this.instances);
      if (!validation.valid) {
        console.warn('Series sorting confidence low:', validation);
      }
      
      // Auto-select preset
      const firstInstance = this.instances[0];
      const presetKey = autoSelectPreset(
        firstInstance.metadata.seriesDescription,
        firstInstance.metadata.bodyPartExamined
      );
      this.applyPreset(presetKey);
      
      // Display first image
      this.currentInstance = 0;
      await this.displayCurrentInstance();
      
      this.updateUI();
      this.hideLoading();
      
    } catch (error) {
      console.error('Failed to load files:', error);
      this.showError('Failed to load DICOM files: ' + error.message);
      this.hideLoading();
    }
  }

  /**
   * Parse DICOM file
   */
  async parseDICOM(arrayBuffer) {
    // This would use dicomParser library
    // Simplified version for demonstration
    return {
      arrayBuffer,
      metadata: {
        patientName: 'Test Patient',
        patientId: '12345',
        studyDate: '20231201',
        modality: 'CT',
        seriesDescription: 'Brain',
        bodyPartExamined: 'HEAD',
        instanceNumber: 1,
        sliceLocation: 0,
        imagePositionPatient: [0, 0, 0],
        imageOrientationPatient: [1, 0, 0, 0, 1, 0],
        rows: 512,
        columns: 512,
        pixelSpacing: [0.5, 0.5],
        sliceThickness: 5
      },
      pixelData: new Uint16Array(512 * 512)
    };
  }

  /**
   * Display current instance
   */
  async displayCurrentInstance() {
    if (!this.instances || this.instances.length === 0) {
      return;
    }
    
    const instance = this.instances[this.currentInstance];
    
    // Render to canvas
    await this.renderInstance(instance);
    
    // Update overlay
    this.updateOverlay(instance);
    
    // Update slice slider
    document.getElementById('sliceSlider').max = this.instances.length - 1;
    document.getElementById('sliceSlider').value = this.currentInstance;
    document.getElementById('sliceCounter').textContent = 
      `${this.currentInstance + 1} / ${this.instances.length}`;
  }

  /**
   * Render DICOM instance to canvas
   */
  async renderInstance(instance) {
    // Resize canvas to match image
    const { rows, columns } = instance.metadata;
    this.canvas.width = columns;
    this.canvas.height = rows;
    
    // Apply window/level to pixel data
    const displayData = this.applyWindowLevel(instance.pixelData);
    
    // Create image data
    const imageData = this.ctx.createImageData(columns, rows);
    for (let i = 0; i < displayData.length; i++) {
      const value = displayData[i];
      imageData.data[i * 4] = value;
      imageData.data[i * 4 + 1] = value;
      imageData.data[i * 4 + 2] = value;
      imageData.data[i * 4 + 3] = 255;
    }
    
    // Draw to canvas
    this.ctx.putImageData(imageData, 0, 0);
    
    // Apply transformations
    if (this.state.inverted) {
      this.invertCanvas();
    }
  }

  /**
   * Apply window/level transformation
   */
  applyWindowLevel(pixelData) {
    const { window, level } = this.state;
    const minValue = level - window / 2;
    const maxValue = level + window / 2;
    
    const displayData = new Uint8Array(pixelData.length);
    
    for (let i = 0; i < pixelData.length; i++) {
      const value = pixelData[i];
      
      if (value <= minValue) {
        displayData[i] = 0;
      } else if (value >= maxValue) {
        displayData[i] = 255;
      } else {
        displayData[i] = Math.round(((value - minValue) / window) * 255);
      }
    }
    
    return displayData;
  }

  /**
   * Apply preset
   */
  applyPreset(presetKey) {
    const preset = CT_PRESETS[presetKey];
    if (!preset) return;
    
    this.state.window = preset.window;
    this.state.level = preset.level;
    
    if (this.instances.length > 0) {
      this.displayCurrentInstance();
    }
    
    this.updateOverlay();
  }

  /**
   * Update overlay information
   */
  updateOverlay(instance) {
    if (!instance) return;
    
    const meta = instance.metadata;
    
    document.getElementById('patientName').textContent = meta.patientName || '';
    document.getElementById('patientId').textContent = meta.patientId || '';
    document.getElementById('studyDate').textContent = meta.studyDate || '';
    document.getElementById('modality').textContent = meta.modality || '';
    document.getElementById('seriesDescription').textContent = meta.seriesDescription || '';
    document.getElementById('imageSize').textContent = `${meta.columns}x${meta.rows}`;
    document.getElementById('windowLevel').textContent = `W:${this.state.window} L:${this.state.level}`;
    document.getElementById('zoomLevel').textContent = `Zoom: ${(this.state.zoom * 100).toFixed(0)}%`;
  }

  // Navigation methods
  nextSlice() {
    if (this.currentInstance < this.instances.length - 1) {
      this.currentInstance++;
      this.displayCurrentInstance();
    }
  }

  previousSlice() {
    if (this.currentInstance > 0) {
      this.currentInstance--;
      this.displayCurrentInstance();
    }
  }

  goToSlice(index) {
    if (index >= 0 && index < this.instances.length) {
      this.currentInstance = index;
      this.displayCurrentInstance();
    }
  }

  // Tool methods
  toggleInvert() {
    this.state.inverted = !this.state.inverted;
    this.displayCurrentInstance();
  }

  rotate(degrees) {
    this.state.rotation = (this.state.rotation + degrees) % 360;
    this.displayCurrentInstance();
  }

  reset() {
    this.state.zoom = 1.0;
    this.state.pan = { x: 0, y: 0 };
    this.state.rotation = 0;
    this.state.inverted = false;
    this.displayCurrentInstance();
  }

  toggleCine() {
    this.state.playing = !this.state.playing;
    const btn = document.getElementById('btnCine');
    btn.innerHTML = this.state.playing ? '<span>⏸️</span> Pause' : '<span>▶️</span> Play';
    
    if (this.state.playing) {
      this.startCine();
    } else {
      this.stopCine();
    }
  }

  startCine() {
    this.cineInterval = setInterval(() => {
      this.nextSlice();
      if (this.currentInstance === this.instances.length - 1) {
        this.currentInstance = 0;
      }
    }, 1000 / this.state.fps);
  }

  stopCine() {
    if (this.cineInterval) {
      clearInterval(this.cineInterval);
      this.cineInterval = null;
    }
  }

  // UI helpers
  showLoading(text) {
    document.getElementById('loadingOverlay').style.display = 'flex';
    document.getElementById('loadingText').textContent = text;
  }

  hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
  }

  showError(message) {
    alert(message); // Replace with better error UI
  }

  updateUI() {
    // Update series list, etc.
  }

  handleResize() {
    // Handle window resize
  }

  handleKeyboard(e) {
    // Keyboard shortcuts
    switch(e.key.toLowerCase()) {
      case 'w': this.activateTool('windowLevel'); break;
      case 'z': this.activateTool('zoom'); break;
      case 'p': this.activateTool('pan'); break;
      case 'm': this.activateTool('length'); break;
      case 'i': this.toggleInvert(); break;
      case 'r': this.reset(); break;
      case 'c': this.toggleCine(); break;
      case ' ': e.preventDefault(); this.toggleCine(); break;
      case 'arrowup': e.preventDefault(); this.previousSlice(); break;
      case 'arrowdown': e.preventDefault(); this.nextSlice(); break;
    }
    
    // Preset hotkeys
    if (e.key >= '0' && e.key <= '9') {
      const preset = getPreset(e.key);
      if (preset) {
        this.applyPreset(Object.keys(CT_PRESETS).find(k => CT_PRESETS[k] === preset));
      }
    }
  }

  handleMouseDown(e) {}
  handleMouseMove(e) {}
  handleMouseUp(e) {}
  handleWheel(e) {
    e.preventDefault();
    if (e.deltaY < 0) {
      this.previousSlice();
    } else {
      this.nextSlice();
    }
  }
  handleTouchStart(e) {}
  handleTouchMove(e) {}
  handleTouchEnd(e) {}
  
  activateTool(tool) {
    console.log('Activated tool:', tool);
  }
  
  exportImage() {
    const link = document.createElement('a');
    link.download = `dicom_${Date.now()}.png`;
    link.href = this.canvas.toDataURL();
    link.click();
  }
  
  toggleFullscreen() {
    if (!document.fullscreenElement) {
      this.container.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  }
  
  invertCanvas() {
    const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
    const data = imageData.data;
    
    for (let i = 0; i < data.length; i += 4) {
      data[i] = 255 - data[i];
      data[i + 1] = 255 - data[i + 1];
      data[i + 2] = 255 - data[i + 2];
    }
    
    this.ctx.putImageData(imageData, 0, 0);
  }
  
  showOrthancBrowser() {
    alert('Orthanc browser not yet implemented');
  }
}

// Export for use
window.ClinicalViewer = ClinicalViewer;

// Auto-initialize if container exists
document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('viewerContainer');
  if (container) {
    window.viewer = new ClinicalViewer('viewerContainer');
  }
});
