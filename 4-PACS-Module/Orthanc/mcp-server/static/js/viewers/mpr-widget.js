/**
 * Multiplanar Reconstruction (MPR) Widget
 * Displays axial, sagittal, and coronal views with synchronized crosshairs
 */

class MPRWidget {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.volumeData = null;
        this.currentSlices = {
            axial: 0,
            sagittal: 0,
            coronal: 0
        };
        this.crosshairPosition = { x: 0, y: 0, z: 0 };
        this.canvases = {};
        this.contexts = {};
        this.isInitialized = false;
        
        this.init();
    }

    init() {
        if (!this.container) {
            console.error('MPR container not found');
            return;
        }

        // Create MPR layout
        this.createLayout();
        
        // Setup event listeners
        this.setupEventListeners();
        
        this.isInitialized = true;
        console.log('MPR Widget initialized');
    }

    createLayout() {
        // Clear existing content
        this.container.innerHTML = '';

        // Create MPR grid container
        const mprGrid = document.createElement('div');
        mprGrid.className = 'mpr-grid';
        mprGrid.innerHTML = `
            <div class="mpr-view" id="mpr-axial">
                <div class="mpr-header">
                    <h4>Axial</h4>
                    <span class="mpr-slice-info" id="axial-info">Slice: 0/0</span>
                </div>
                <canvas id="mpr-canvas-axial" class="mpr-canvas"></canvas>
                <div class="mpr-controls">
                    <input type="range" id="axial-slider" class="mpr-slider" min="0" max="100" value="50">
                </div>
            </div>
            
            <div class="mpr-view" id="mpr-sagittal">
                <div class="mpr-header">
                    <h4>Sagittal</h4>
                    <span class="mpr-slice-info" id="sagittal-info">Slice: 0/0</span>
                </div>
                <canvas id="mpr-canvas-sagittal" class="mpr-canvas"></canvas>
                <div class="mpr-controls">
                    <input type="range" id="sagittal-slider" class="mpr-slider" min="0" max="100" value="50">
                </div>
            </div>
            
            <div class="mpr-view" id="mpr-coronal">
                <div class="mpr-header">
                    <h4>Coronal</h4>
                    <span class="mpr-slice-info" id="coronal-info">Slice: 0/0</span>
                </div>
                <canvas id="mpr-canvas-coronal" class="mpr-canvas"></canvas>
                <div class="mpr-controls">
                    <input type="range" id="coronal-slider" class="mpr-slider" min="0" max="100" value="50">
                </div>
            </div>
            
            <div class="mpr-view" id="mpr-3d">
                <div class="mpr-header">
                    <h4>3D View</h4>
                    <span class="mpr-slice-info">Crosshair Position</span>
                </div>
                <canvas id="mpr-canvas-3d" class="mpr-canvas"></canvas>
                <div class="mpr-controls">
                    <button id="mpr-reset" class="btn-secondary">Reset Views</button>
                </div>
            </div>
        `;

        this.container.appendChild(mprGrid);

        // Get canvas references
        this.canvases = {
            axial: document.getElementById('mpr-canvas-axial'),
            sagittal: document.getElementById('mpr-canvas-sagittal'),
            coronal: document.getElementById('mpr-canvas-coronal'),
            threeD: document.getElementById('mpr-canvas-3d')
        };

        // Get 2D contexts
        this.contexts = {
            axial: this.canvases.axial.getContext('2d'),
            sagittal: this.canvases.sagittal.getContext('2d'),
            coronal: this.canvases.coronal.getContext('2d')
        };

        // Set canvas sizes
        Object.values(this.canvases).forEach(canvas => {
            canvas.width = 400;
            canvas.height = 400;
        });
    }

    setupEventListeners() {
        // Slider events
        const axialSlider = document.getElementById('axial-slider');
        const sagittalSlider = document.getElementById('sagittal-slider');
        const coronalSlider = document.getElementById('coronal-slider');

        if (axialSlider) {
            axialSlider.addEventListener('input', (e) => {
                this.updateSlice('axial', parseInt(e.target.value));
            });
        }

        if (sagittalSlider) {
            sagittalSlider.addEventListener('input', (e) => {
                this.updateSlice('sagittal', parseInt(e.target.value));
            });
        }

        if (coronalSlider) {
            coronalSlider.addEventListener('input', (e) => {
                this.updateSlice('coronal', parseInt(e.target.value));
            });
        }

        // Canvas click events for crosshair positioning
        Object.keys(this.canvases).forEach(plane => {
            if (plane !== 'threeD') {
                this.canvases[plane].addEventListener('click', (e) => {
                    this.handleCanvasClick(plane, e);
                });
            }
        });

        // Reset button
        const resetBtn = document.getElementById('mpr-reset');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetViews());
        }

        // Mouse move for crosshair preview
        Object.keys(this.canvases).forEach(plane => {
            if (plane !== 'threeD') {
                this.canvases[plane].addEventListener('mousemove', (e) => {
                    this.handleMouseMove(plane, e);
                });
            }
        });
    }

    loadVolume(volumeData) {
        console.log('Loading volume into MPR widget:', volumeData);
        this.volumeData = volumeData;

        if (!volumeData || !volumeData.dimensions) {
            console.error('Invalid volume data');
            return;
        }

        // Initialize slice positions to center
        this.currentSlices = {
            axial: Math.floor(volumeData.dimensions[2] / 2),
            sagittal: Math.floor(volumeData.dimensions[0] / 2),
            coronal: Math.floor(volumeData.dimensions[1] / 2)
        };

        // Update crosshair to center
        this.crosshairPosition = {
            x: Math.floor(volumeData.dimensions[0] / 2),
            y: Math.floor(volumeData.dimensions[1] / 2),
            z: Math.floor(volumeData.dimensions[2] / 2)
        };

        // Update sliders
        this.updateSliders();

        // Render all views
        this.renderAllViews();
    }

    updateSliders() {
        if (!this.volumeData) return;

        const axialSlider = document.getElementById('axial-slider');
        const sagittalSlider = document.getElementById('sagittal-slider');
        const coronalSlider = document.getElementById('coronal-slider');

        if (axialSlider) {
            axialSlider.max = this.volumeData.dimensions[2] - 1;
            axialSlider.value = this.currentSlices.axial;
        }

        if (sagittalSlider) {
            sagittalSlider.max = this.volumeData.dimensions[0] - 1;
            sagittalSlider.value = this.currentSlices.sagittal;
        }

        if (coronalSlider) {
            coronalSlider.max = this.volumeData.dimensions[1] - 1;
            coronalSlider.value = this.currentSlices.coronal;
        }
    }

    updateSlice(plane, sliceIndex) {
        if (!this.volumeData) return;

        this.currentSlices[plane] = sliceIndex;

        // Update crosshair position based on plane
        switch(plane) {
            case 'axial':
                this.crosshairPosition.z = sliceIndex;
                break;
            case 'sagittal':
                this.crosshairPosition.x = sliceIndex;
                break;
            case 'coronal':
                this.crosshairPosition.y = sliceIndex;
                break;
        }

        // Update slice info
        this.updateSliceInfo(plane);

        // Render the updated view
        this.renderView(plane);

        // Update crosshairs on other views
        this.renderCrosshairs();
    }

    updateSliceInfo(plane) {
        const infoElement = document.getElementById(`${plane}-info`);
        if (infoElement && this.volumeData) {
            const maxSlice = this.volumeData.dimensions[
                plane === 'axial' ? 2 : plane === 'sagittal' ? 0 : 1
            ] - 1;
            infoElement.textContent = `Slice: ${this.currentSlices[plane]}/${maxSlice}`;
        }
    }

    renderAllViews() {
        this.renderView('axial');
        this.renderView('sagittal');
        this.renderView('coronal');
        this.render3DView();
        this.renderCrosshairs();
    }

    renderView(plane) {
        if (!this.volumeData || !this.contexts[plane]) return;

        const ctx = this.contexts[plane];
        const canvas = this.canvases[plane];
        const sliceIndex = this.currentSlices[plane];

        // Clear canvas
        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // In production, this would fetch actual slice data from the backend
        // For now, render a placeholder with slice information
        this.renderPlaceholderSlice(ctx, canvas, plane, sliceIndex);

        // Update slice info
        this.updateSliceInfo(plane);
    }

    renderPlaceholderSlice(ctx, canvas, plane, sliceIndex) {
        // Draw gradient to simulate slice data
        const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
        gradient.addColorStop(0, '#1a1a1a');
        gradient.addColorStop(0.5, '#3a3a3a');
        gradient.addColorStop(1, '#1a1a1a');
        
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw grid
        ctx.strokeStyle = '#333333';
        ctx.lineWidth = 1;
        for (let i = 0; i < canvas.width; i += 40) {
            ctx.beginPath();
            ctx.moveTo(i, 0);
            ctx.lineTo(i, canvas.height);
            ctx.stroke();
        }
        for (let i = 0; i < canvas.height; i += 40) {
            ctx.beginPath();
            ctx.moveTo(0, i);
            ctx.lineTo(canvas.width, i);
            ctx.stroke();
        }

        // Draw plane label
        ctx.fillStyle = '#667eea';
        ctx.font = 'bold 24px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(plane.toUpperCase(), canvas.width / 2, canvas.height / 2);

        // Draw slice number
        ctx.font = '16px Arial';
        ctx.fillStyle = '#ffffff';
        ctx.fillText(`Slice ${sliceIndex}`, canvas.width / 2, canvas.height / 2 + 30);

        // Draw orientation markers
        ctx.font = '12px Arial';
        ctx.fillStyle = '#ffb81c';
        
        switch(plane) {
            case 'axial':
                ctx.fillText('A', canvas.width / 2, 20);
                ctx.fillText('P', canvas.width / 2, canvas.height - 10);
                ctx.fillText('L', 20, canvas.height / 2);
                ctx.fillText('R', canvas.width - 20, canvas.height / 2);
                break;
            case 'sagittal':
                ctx.fillText('S', canvas.width / 2, 20);
                ctx.fillText('I', canvas.width / 2, canvas.height - 10);
                ctx.fillText('A', 20, canvas.height / 2);
                ctx.fillText('P', canvas.width - 20, canvas.height / 2);
                break;
            case 'coronal':
                ctx.fillText('S', canvas.width / 2, 20);
                ctx.fillText('I', canvas.width / 2, canvas.height - 10);
                ctx.fillText('L', 20, canvas.height / 2);
                ctx.fillText('R', canvas.width - 20, canvas.height / 2);
                break;
        }
    }

    renderCrosshairs() {
        // Render crosshairs on each view
        Object.keys(this.contexts).forEach(plane => {
            this.renderCrosshair(plane);
        });
    }

    renderCrosshair(plane) {
        if (!this.volumeData || !this.contexts[plane]) return;

        const ctx = this.contexts[plane];
        const canvas = this.canvases[plane];

        // Calculate crosshair position based on plane
        let x, y;
        
        switch(plane) {
            case 'axial':
                x = (this.crosshairPosition.x / this.volumeData.dimensions[0]) * canvas.width;
                y = (this.crosshairPosition.y / this.volumeData.dimensions[1]) * canvas.height;
                break;
            case 'sagittal':
                x = (this.crosshairPosition.y / this.volumeData.dimensions[1]) * canvas.width;
                y = (this.crosshairPosition.z / this.volumeData.dimensions[2]) * canvas.height;
                break;
            case 'coronal':
                x = (this.crosshairPosition.x / this.volumeData.dimensions[0]) * canvas.width;
                y = (this.crosshairPosition.z / this.volumeData.dimensions[2]) * canvas.height;
                break;
        }

        // Draw crosshair lines
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);

        // Vertical line
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();

        // Horizontal line
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();

        // Draw center circle
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, 2 * Math.PI);
        ctx.stroke();

        ctx.fillStyle = '#00ff00';
        ctx.beginPath();
        ctx.arc(x, y, 2, 0, 2 * Math.PI);
        ctx.fill();
    }

    render3DView() {
        if (!this.canvases.threeD) return;

        const ctx = this.canvases.threeD.getContext('2d');
        const canvas = this.canvases.threeD;

        // Clear canvas
        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw 3D representation placeholder
        ctx.fillStyle = '#667eea';
        ctx.font = 'bold 20px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('3D View', canvas.width / 2, canvas.height / 2 - 20);

        // Draw crosshair position
        ctx.font = '14px Arial';
        ctx.fillStyle = '#ffffff';
        ctx.fillText(
            `Position: (${this.crosshairPosition.x}, ${this.crosshairPosition.y}, ${this.crosshairPosition.z})`,
            canvas.width / 2,
            canvas.height / 2 + 20
        );

        // Draw simple 3D cube representation
        this.draw3DCube(ctx, canvas);
    }

    draw3DCube(ctx, canvas) {
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const size = 100;

        // Draw cube edges
        ctx.strokeStyle = '#667eea';
        ctx.lineWidth = 2;

        // Front face
        ctx.strokeRect(centerX - size/2, centerY - size/2, size, size);

        // Back face (offset)
        const offset = 30;
        ctx.strokeRect(centerX - size/2 + offset, centerY - size/2 - offset, size, size);

        // Connecting lines
        ctx.beginPath();
        ctx.moveTo(centerX - size/2, centerY - size/2);
        ctx.lineTo(centerX - size/2 + offset, centerY - size/2 - offset);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(centerX + size/2, centerY - size/2);
        ctx.lineTo(centerX + size/2 + offset, centerY - size/2 - offset);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(centerX - size/2, centerY + size/2);
        ctx.lineTo(centerX - size/2 + offset, centerY + size/2 - offset);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(centerX + size/2, centerY + size/2);
        ctx.lineTo(centerX + size/2 + offset, centerY + size/2 - offset);
        ctx.stroke();

        // Draw crosshair position indicator
        const posX = centerX + (this.crosshairPosition.x / this.volumeData.dimensions[0] - 0.5) * size;
        const posY = centerY + (this.crosshairPosition.y / this.volumeData.dimensions[1] - 0.5) * size;

        ctx.fillStyle = '#00ff00';
        ctx.beginPath();
        ctx.arc(posX, posY, 4, 0, 2 * Math.PI);
        ctx.fill();
    }

    handleCanvasClick(plane, event) {
        if (!this.volumeData) return;

        const canvas = this.canvases[plane];
        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

        // Convert canvas coordinates to volume coordinates
        const volumeX = Math.floor((x / canvas.width) * this.volumeData.dimensions[0]);
        const volumeY = Math.floor((y / canvas.height) * this.volumeData.dimensions[1]);
        const volumeZ = Math.floor((y / canvas.height) * this.volumeData.dimensions[2]);

        // Update crosshair position based on plane
        switch(plane) {
            case 'axial':
                this.crosshairPosition.x = volumeX;
                this.crosshairPosition.y = volumeY;
                // Update other slices
                this.currentSlices.sagittal = volumeX;
                this.currentSlices.coronal = volumeY;
                break;
            case 'sagittal':
                this.crosshairPosition.y = volumeX;
                this.crosshairPosition.z = volumeZ;
                // Update other slices
                this.currentSlices.axial = volumeZ;
                this.currentSlices.coronal = volumeX;
                break;
            case 'coronal':
                this.crosshairPosition.x = volumeX;
                this.crosshairPosition.z = volumeZ;
                // Update other slices
                this.currentSlices.axial = volumeZ;
                this.currentSlices.sagittal = volumeX;
                break;
        }

        // Update sliders
        this.updateSliders();

        // Re-render all views
        this.renderAllViews();
    }

    handleMouseMove(plane, event) {
        // Show preview crosshair on hover (optional enhancement)
        // This could be implemented to show a preview before clicking
    }

    resetViews() {
        if (!this.volumeData) return;

        // Reset to center
        this.currentSlices = {
            axial: Math.floor(this.volumeData.dimensions[2] / 2),
            sagittal: Math.floor(this.volumeData.dimensions[0] / 2),
            coronal: Math.floor(this.volumeData.dimensions[1] / 2)
        };

        this.crosshairPosition = {
            x: Math.floor(this.volumeData.dimensions[0] / 2),
            y: Math.floor(this.volumeData.dimensions[1] / 2),
            z: Math.floor(this.volumeData.dimensions[2] / 2)
        };

        // Update sliders
        this.updateSliders();

        // Re-render all views
        this.renderAllViews();

        console.log('MPR views reset to center');
    }

    dispose() {
        // Clean up resources
        this.volumeData = null;
        this.canvases = {};
        this.contexts = {};
        this.isInitialized = false;
    }
}

// Global MPR widget instance
let mprWidget = null;

// Initialize MPR widget when needed
function initializeMPR(containerId = 'mpr-container') {
    if (!mprWidget) {
        mprWidget = new MPRWidget(containerId);
        console.log('MPR Widget created');
    }
    return mprWidget;
}

// Load volume into MPR widget
function loadVolumeIntoMPR(volumeData) {
    if (!mprWidget) {
        console.error('MPR Widget not initialized');
        return;
    }
    mprWidget.loadVolume(volumeData);
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { MPRWidget, initializeMPR, loadVolumeIntoMPR };
}
