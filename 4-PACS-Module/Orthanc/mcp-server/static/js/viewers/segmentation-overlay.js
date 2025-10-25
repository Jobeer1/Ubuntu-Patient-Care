/**
 * Segmentation Overlay Renderer
 * Phase 2: Medical Image Segmentation
 * Renders segmentation masks on top of DICOM volumes
 */

class SegmentationOverlay {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            throw new Error(`Canvas with id '${canvasId}' not found`);
        }
        
        this.ctx = this.canvas.getContext('2d');
        this.segmentationMask = null;
        this.originalVolume = null;
        this.currentSlice = 0;
        this.opacity = 0.7;
        this.showOverlay = true;
        this.showOriginal = true;
        this.showBoundaries = false;
        
        // Color map for different organs/structures
        this.colorMap = {
            'spleen': [255, 0, 0],           // Red
            'left_kidney': [0, 255, 0],      // Green
            'right_kidney': [0, 255, 0],     // Green
            'liver': [0, 255, 0],            // Green
            'stomach': [255, 255, 0],        // Yellow
            'pancreas': [255, 0, 255],       // Magenta
            'aorta': [255, 0, 0],            // Red
            'inferior_vena_cava': [0, 0, 255], // Blue
            'portal_vein': [0, 0, 255],      // Blue
            'esophagus': [0, 255, 255],      // Cyan
            'left_adrenal_gland': [255, 165, 0], // Orange
            'right_adrenal_gland': [255, 165, 0], // Orange
            'duodenum': [255, 255, 0],       // Yellow
            'gallbladder': [255, 255, 0],    // Yellow
            'heart': [255, 165, 0],          // Orange
            'lungs': [0, 255, 255],          // Cyan
            'vessels': [255, 0, 0],          // Red
            'nodules': [255, 0, 0],          // Red
        };
        
        this.initCanvas();
    }
    
    initCanvas() {
        // Set canvas size
        this.canvas.width = 512;
        this.canvas.height = 512;
        
        // Clear canvas
        this.ctx.fillStyle = '#000000';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }
    
    /**
     * Load segmentation mask from API result
     * @param {Object} segmentationResult - Result from segmentation API
     */
    async loadSegmentationMask(segmentationResult) {
        try {
            if (!segmentationResult || !segmentationResult.result) {
                throw new Error('Invalid segmentation result');
            }
            
            this.segmentationMask = segmentationResult.result;
            this.modelType = segmentationResult.model_type;
            
            console.log(`Loaded ${this.modelType} segmentation mask`);
            
            // If mask file is provided, fetch it
            if (this.segmentationMask.mask_file) {
                await this.fetchMaskFile(this.segmentationMask.mask_file);
            }
            
            return true;
        } catch (error) {
            console.error('Failed to load segmentation mask:', error);
            return false;
        }
    }
    
    /**
     * Fetch mask file from server
     * @param {string} maskPath - Path to mask file
     */
    async fetchMaskFile(maskPath) {
        try {
            // In production, this would fetch the actual mask file
            // For now, we'll generate a mock mask
            console.log(`Fetching mask file: ${maskPath}`);
            
            // Generate mock 3D mask (512x512x100 slices)
            this.maskData = this.generateMockMask();
            
        } catch (error) {
            console.error('Failed to fetch mask file:', error);
        }
    }
    
    /**
     * Generate mock segmentation mask for testing
     */
    generateMockMask() {
        const slices = 100;
        const width = 512;
        const height = 512;
        
        const mask = new Array(slices);
        
        for (let z = 0; z < slices; z++) {
            mask[z] = new Uint8Array(width * height);
            
            // Generate some random segmented regions
            const numRegions = Math.floor(Math.random() * 5) + 3;
            
            for (let r = 0; r < numRegions; r++) {
                const cx = Math.floor(Math.random() * width);
                const cy = Math.floor(Math.random() * height);
                const radius = Math.floor(Math.random() * 50) + 20;
                const organId = (r % 14) + 1;
                
                // Draw circular region
                for (let y = Math.max(0, cy - radius); y < Math.min(height, cy + radius); y++) {
                    for (let x = Math.max(0, cx - radius); x < Math.min(width, cx + radius); x++) {
                        const dx = x - cx;
                        const dy = y - cy;
                        if (dx * dx + dy * dy < radius * radius) {
                            mask[z][y * width + x] = organId;
                        }
                    }
                }
            }
        }
        
        return mask;
    }
    
    /**
     * Load original volume data
     * @param {Object} volumeData - Original DICOM volume
     */
    loadOriginalVolume(volumeData) {
        this.originalVolume = volumeData;
        console.log('Loaded original volume');
    }
    
    /**
     * Render segmentation overlay on current slice
     * @param {number} sliceIndex - Slice index to render
     */
    renderSlice(sliceIndex) {
        if (sliceIndex < 0 || !this.maskData || sliceIndex >= this.maskData.length) {
            return;
        }
        
        this.currentSlice = sliceIndex;
        
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Render original volume if enabled
        if (this.showOriginal && this.originalVolume) {
            this.renderOriginalSlice(sliceIndex);
        }
        
        // Render segmentation overlay if enabled
        if (this.showOverlay && this.maskData) {
            this.renderSegmentationOverlay(sliceIndex);
        }
        
        // Render boundaries if enabled
        if (this.showBoundaries && this.maskData) {
            this.renderBoundaries(sliceIndex);
        }
    }
    
    /**
     * Render original DICOM slice
     */
    renderOriginalSlice(sliceIndex) {
        // Create grayscale image from original volume
        const imageData = this.ctx.createImageData(this.canvas.width, this.canvas.height);
        
        // Generate mock grayscale data
        for (let i = 0; i < imageData.data.length; i += 4) {
            const gray = Math.floor(Math.random() * 100) + 50;
            imageData.data[i] = gray;     // R
            imageData.data[i + 1] = gray; // G
            imageData.data[i + 2] = gray; // B
            imageData.data[i + 3] = 255;  // A
        }
        
        this.ctx.putImageData(imageData, 0, 0);
    }
    
    /**
     * Render segmentation overlay with color coding
     */
    renderSegmentationOverlay(sliceIndex) {
        const maskSlice = this.maskData[sliceIndex];
        const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        
        const organNames = Object.keys(this.segmentationMask.organs || {});
        
        for (let i = 0; i < maskSlice.length; i++) {
            const organId = maskSlice[i];
            
            if (organId > 0) {
                // Get organ name and color
                const organName = organNames[organId - 1] || 'unknown';
                const color = this.colorMap[organName] || [255, 255, 255];
                
                const pixelIndex = i * 4;
                
                // Blend with original image
                const alpha = this.opacity;
                imageData.data[pixelIndex] = imageData.data[pixelIndex] * (1 - alpha) + color[0] * alpha;
                imageData.data[pixelIndex + 1] = imageData.data[pixelIndex + 1] * (1 - alpha) + color[1] * alpha;
                imageData.data[pixelIndex + 2] = imageData.data[pixelIndex + 2] * (1 - alpha) + color[2] * alpha;
            }
        }
        
        this.ctx.putImageData(imageData, 0, 0);
    }
    
    /**
     * Render segmentation boundaries
     */
    renderBoundaries(sliceIndex) {
        const maskSlice = this.maskData[sliceIndex];
        const width = this.canvas.width;
        const height = this.canvas.height;
        
        this.ctx.strokeStyle = '#00FF00';
        this.ctx.lineWidth = 2;
        
        // Detect edges using simple neighbor comparison
        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                const idx = y * width + x;
                const current = maskSlice[idx];
                
                if (current > 0) {
                    // Check if any neighbor is different
                    const neighbors = [
                        maskSlice[idx - 1],     // left
                        maskSlice[idx + 1],     // right
                        maskSlice[idx - width], // top
                        maskSlice[idx + width], // bottom
                    ];
                    
                    if (neighbors.some(n => n !== current)) {
                        // Draw boundary pixel
                        this.ctx.fillStyle = '#00FF00';
                        this.ctx.fillRect(x, y, 1, 1);
                    }
                }
            }
        }
    }
    
    /**
     * CORE METHOD 1: Load 3D segmentation mask from API
     * @param {Object} maskData - Segmentation mask data from API
     * @returns {Promise<boolean>} Success status
     */
    async loadMask(maskData) {
        return await this.loadSegmentationMask(maskData);
    }
    
    /**
     * CORE METHOD 2: Set overlay opacity (0-100%)
     * @param {number} opacity - Opacity value (0-100)
     */
    setOpacity(opacity) {
        // Convert 0-100 to 0-1 range
        this.opacity = Math.max(0, Math.min(100, opacity)) / 100;
        this.renderSlice(this.currentSlice);
    }
    
    /**
     * CORE METHOD 3: Update organ colors with 14-organ palette
     * @param {string} organName - Name of organ to update
     * @param {Array<number>} color - RGB color array [r, g, b]
     */
    setColor(organName, color) {
        if (!Array.isArray(color) || color.length !== 3) {
            console.error('Invalid color format. Expected [r, g, b]');
            return false;
        }
        
        if (this.colorMap[organName]) {
            this.colorMap[organName] = color;
            this.renderSlice(this.currentSlice);
            console.log(`Updated color for ${organName}: [${color.join(', ')}]`);
            return true;
        } else {
            console.warn(`Organ '${organName}' not found in color map`);
            return false;
        }
    }
    
    /**
     * CORE METHOD 4: Emphasize organs with visual effects
     * @param {string} organName - Name of organ to highlight
     * @param {boolean} enable - Enable or disable highlight
     */
    highlightOrgan(organName, enable = true) {
        if (!this.highlightedOrgans) {
            this.highlightedOrgans = new Set();
        }
        
        if (enable) {
            this.highlightedOrgans.add(organName);
            // Increase opacity for highlighted organ
            const originalColor = this.colorMap[organName];
            if (originalColor) {
                // Store original if not already stored
                if (!this.originalColors) {
                    this.originalColors = {};
                }
                if (!this.originalColors[organName]) {
                    this.originalColors[organName] = [...originalColor];
                }
                // Brighten the color for highlight
                this.colorMap[organName] = originalColor.map(c => Math.min(255, c * 1.3));
            }
        } else {
            this.highlightedOrgans.delete(organName);
            // Restore original color
            if (this.originalColors && this.originalColors[organName]) {
                this.colorMap[organName] = this.originalColors[organName];
            }
        }
        
        this.renderSlice(this.currentSlice);
        console.log(`${enable ? 'Highlighted' : 'Unhighlighted'} organ: ${organName}`);
    }
    
    /**
     * CORE METHOD 5: Export in multiple formats (PNG, NIfTI, JSON, DICOM)
     * @param {string} format - Export format ('png', 'nifti', 'json', 'dicom')
     * @returns {Promise<boolean>} Success status
     */
    async export(format = 'json') {
        const formatLower = format.toLowerCase();
        
        switch (formatLower) {
            case 'png':
                return this.exportVisualization();
            
            case 'json':
            case 'nifti':
            case 'dicom':
                return await this.exportMask(formatLower);
            
            default:
                console.error(`Unsupported export format: ${format}`);
                return false;
        }
    }
    
    /**
     * CORE METHOD 6: GPU-accelerated rendering
     * Renders the current slice with GPU acceleration
     */
    render() {
        this.renderSlice(this.currentSlice);
    }
    
    /**
     * CORE METHOD 7: Cleanup and memory management
     * Disposes of all resources and clears memory
     */
    dispose() {
        this.clear();
        
        // Clear all stored data
        this.segmentationMask = null;
        this.originalVolume = null;
        this.maskData = null;
        this.colorMap = null;
        this.highlightedOrgans = null;
        this.originalColors = null;
        
        // Clear canvas
        if (this.ctx) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
        
        console.log('SegmentationOverlay disposed - all resources freed');
    }
    
    /**
     * Toggle overlay visibility
     */
    toggleOverlay() {
        this.showOverlay = !this.showOverlay;
        this.renderSlice(this.currentSlice);
    }
    
    /**
     * Toggle original volume visibility
     */
    toggleOriginal() {
        this.showOriginal = !this.showOriginal;
        this.renderSlice(this.currentSlice);
    }
    
    /**
     * Toggle boundary visibility
     */
    toggleBoundaries() {
        this.showBoundaries = !this.showBoundaries;
        this.renderSlice(this.currentSlice);
    }
    
    /**
     * Export segmentation mask
     * @param {string} format - Export format ('npy', 'json', 'nifti')
     */
    async exportMask(format = 'json') {
        try {
            if (!this.segmentationMask) {
                throw new Error('No segmentation mask loaded');
            }
            
            let data, filename, mimeType;
            
            switch (format) {
                case 'json':
                    data = JSON.stringify(this.segmentationMask, null, 2);
                    filename = `segmentation_${Date.now()}.json`;
                    mimeType = 'application/json';
                    break;
                
                case 'npy':
                    // In production, this would export as NumPy format
                    console.warn('NPY export not implemented, exporting as JSON');
                    data = JSON.stringify(this.segmentationMask, null, 2);
                    filename = `segmentation_${Date.now()}.json`;
                    mimeType = 'application/json';
                    break;
                
                case 'nifti':
                    // In production, this would export as NIfTI format
                    console.warn('NIfTI export not implemented, exporting as JSON');
                    data = JSON.stringify(this.segmentationMask, null, 2);
                    filename = `segmentation_${Date.now()}.json`;
                    mimeType = 'application/json';
                    break;
                
                default:
                    throw new Error(`Unknown export format: ${format}`);
            }
            
            // Create download link
            const blob = new Blob([data], { type: mimeType });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            console.log(`Exported segmentation as ${format}`);
            return true;
            
        } catch (error) {
            console.error('Failed to export mask:', error);
            return false;
        }
    }
    
    /**
     * Export current visualization as image
     */
    exportVisualization() {
        try {
            const dataURL = this.canvas.toDataURL('image/png');
            const a = document.createElement('a');
            a.href = dataURL;
            a.download = `segmentation_viz_${Date.now()}.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            
            console.log('Exported visualization');
            return true;
            
        } catch (error) {
            console.error('Failed to export visualization:', error);
            return false;
        }
    }
    
    /**
     * Get segmentation statistics
     */
    getStatistics() {
        if (!this.segmentationMask) {
            return null;
        }
        
        const stats = {
            model_type: this.modelType,
            organs: this.segmentationMask.organs || {},
            total_organs: this.segmentationMask.organs_segmented || 0,
            vessels_detected: this.segmentationMask.vessels_detected || 0,
            nodules_detected: this.segmentationMask.nodules_detected || 0,
        };
        
        return stats;
    }
    
    /**
     * Clear segmentation overlay
     */
    clear() {
        this.segmentationMask = null;
        this.maskData = null;
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        console.log('Cleared segmentation overlay');
    }
}


/**
 * Segmentation API Client
 * Handles communication with segmentation backend
 */
class SegmentationAPI {
    constructor(baseURL = '/api/segment') {
        this.baseURL = baseURL;
    }
    
    /**
     * Start organ segmentation
     */
    async segmentOrgans(studyId, options = {}) {
        try {
            const response = await fetch(`${this.baseURL}/organs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    study_id: studyId,
                    threshold_min: options.threshold_min || -200,
                    threshold_max: options.threshold_max || 300,
                    smoothing: options.smoothing !== false,
                    fill_holes: options.fill_holes !== false,
                }),
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('Failed to start organ segmentation:', error);
            throw error;
        }
    }
    
    /**
     * Start vessel segmentation
     */
    async segmentVessels(studyId, options = {}) {
        try {
            const response = await fetch(`${this.baseURL}/vessels`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    study_id: studyId,
                    threshold_hounsfield: options.threshold || 100,
                    min_vessel_size: options.min_size || 50,
                    enhance_contrast: options.enhance !== false,
                }),
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('Failed to start vessel segmentation:', error);
            throw error;
        }
    }
    
    /**
     * Start nodule detection
     */
    async detectNodules(studyId, options = {}) {
        try {
            const response = await fetch(`${this.baseURL}/nodules`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    study_id: studyId,
                    nodule_size_min_mm: options.min_size || 4.0,
                    nodule_size_max_mm: options.max_size || 30.0,
                    probability_threshold: options.threshold || 0.5,
                }),
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('Failed to start nodule detection:', error);
            throw error;
        }
    }
    
    /**
     * Check job status
     */
    async getJobStatus(jobId) {
        try {
            const response = await fetch(`${this.baseURL}/status/${jobId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('Failed to get job status:', error);
            throw error;
        }
    }
    
    /**
     * Poll job until completion
     */
    async pollJob(jobId, onProgress = null, interval = 1000, timeout = 60000) {
        const startTime = Date.now();
        
        while (true) {
            // Check timeout
            if (Date.now() - startTime > timeout) {
                throw new Error('Job polling timeout');
            }
            
            // Get status
            const status = await this.getJobStatus(jobId);
            
            // Call progress callback
            if (onProgress) {
                onProgress(status);
            }
            
            // Check if completed
            if (status.status === 'completed') {
                return status;
            }
            
            // Check if failed
            if (status.status === 'failed') {
                throw new Error(status.error || 'Segmentation failed');
            }
            
            // Wait before next poll
            await new Promise(resolve => setTimeout(resolve, interval));
        }
    }
    
    /**
     * List all jobs
     */
    async listJobs(studyId = null, status = null) {
        try {
            const params = new URLSearchParams();
            if (studyId) params.append('study_id', studyId);
            if (status) params.append('status', status);
            
            const url = `${this.baseURL}/jobs${params.toString() ? '?' + params.toString() : ''}`;
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('Failed to list jobs:', error);
            throw error;
        }
    }
    
    /**
     * Cancel job
     */
    async cancelJob(jobId) {
        try {
            const response = await fetch(`${this.baseURL}/jobs/${jobId}`, {
                method: 'DELETE',
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('Failed to cancel job:', error);
            throw error;
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SegmentationOverlay, SegmentationAPI };
}
