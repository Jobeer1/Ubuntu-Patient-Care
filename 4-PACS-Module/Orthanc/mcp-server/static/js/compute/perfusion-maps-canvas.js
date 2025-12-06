/**
 * Canvas 2D Perfusion Map Analysis - Client-Side GPU Computation
 * Computes perfusion parameters: CBF (cerebral blood flow), CBV (cerebral blood volume),
 * MTT (mean transit time), TTP (time-to-peak) using 2D canvas acceleration
 * 
 * Medical Background:
 * - Perfusion imaging shows tissue blood flow and blood volume
 * - CBF: mL/100g/min (normal ~50-60)
 * - CBV: mL/100g (normal ~3.5-4.5)
 * - MTT: seconds (normal ~3-5 seconds)
 * - TTP: seconds (time from bolus arrival to peak intensity)
 * - Low CBF/CBV or high MTT indicates ischemia
 * 
 * @author GPU Compute Team
 * @version 1.0.0
 * @date October 2025
 */

class PerfusionMapAnalyzer {
    constructor(canvasId = null) {
        this.canvas = canvasId ? document.getElementById(canvasId) : document.createElement('canvas');
        this.ctx = null;
        this.imageData = null;
        this.timeSeriesData = null;
        this.parameters = null;
        this.initialized = false;
        
        // Perfusion thresholds for clinical interpretation
        this.thresholds = {
            cbf: { low: 30, normal: 50, high: 80 },
            cbv: { low: 2.5, normal: 3.5, high: 5.0 },
            mtt: { low: 2, normal: 4, high: 8 }
        };
        
        console.log('PerfusionMapAnalyzer initialized');
    }
    
    /**
     * Initialize Canvas 2D context
     * @returns {boolean} - Success status
     */
    initialize() {
        if (this.initialized) return true;
        
        try {
            if (!this.canvas.getContext) {
                const newCanvas = document.createElement('canvas');
                this.canvas = newCanvas;
            }
            
            this.ctx = this.canvas.getContext('2d', {
                willReadFrequently: true,
                alpha: false
            });
            
            if (!this.ctx) {
                console.error('Canvas 2D context not available');
                return false;
            }
            
            this.initialized = true;
            console.log('Canvas 2D initialized for perfusion analysis');
            return true;
        } catch (error) {
            console.error('Failed to initialize Canvas 2D:', error);
            return false;
        }
    }
    
    /**
     * Load time series perfusion data
     * @param {Array<Float32Array>} timeSeriesFrames - Array of volume data frames
     * @param {number} width - Image width in pixels
     * @param {number} height - Image height in pixels
     * @param {number} temporalResolution - Time between frames in seconds
     * @returns {boolean} - Success status
     */
    loadTimeSeriesData(timeSeriesFrames, width, height, temporalResolution = 1.0) {
        if (!this.initialized) {
            this.initialize();
        }
        
        try {
            this.canvas.width = width;
            this.canvas.height = height;
            
            this.timeSeriesData = {
                frames: timeSeriesFrames,
                width: width,
                height: height,
                temporalResolution: temporalResolution,
                numFrames: timeSeriesFrames.length
            };
            
            console.log(`Time series loaded: ${width}x${height}, ${timeSeriesFrames.length} frames, ${temporalResolution}s temporal resolution`);
            return true;
        } catch (error) {
            console.error('Failed to load time series:', error);
            return false;
        }
    }
    
    /**
     * Calculate Cerebral Blood Flow (CBF) from perfusion data
     * CBF = delta(I) / integral(C(t))
     * @param {Float32Array} frameData - Single frame intensity data
     * @param {Float32Array} baselineData - Baseline/pre-bolus data
     * @returns {Float32Array} - CBF map (mL/100g/min)
     */
    calculateCBF(frameData, baselineData) {
        const width = this.timeSeriesData.width;
        const height = this.timeSeriesData.height;
        const cbfMap = new Float32Array(width * height);
        
        // Create image data for processing
        this.canvas.width = width;
        this.canvas.height = height;
        const imageData = this.ctx.createImageData(width, height);
        const data = imageData.data;
        
        // Calculate maximum slope (deconvolution)
        const maxSlopeMap = this.calculateMaxSlope();
        
        // CBF proportional to maximum slope of time-intensity curve
        for (let i = 0; i < width * height; i++) {
            const baseline = baselineData[i] || 0;
            const intensity = frameData[i] || 0;
            const deltaI = Math.max(0, intensity - baseline);
            const maxSlope = maxSlopeMap[i];
            
            // CBF = (deltaI / baselineHU) × maxSlope × calibration factor
            const cbf = (deltaI / (baseline + 1)) * maxSlope * 100; // Normalized to mL/100g/min
            cbfMap[i] = cbf;
        }
        
        return cbfMap;
    }
    
    /**
     * Calculate Cerebral Blood Volume (CBV) from perfusion data
     * CBV = integral(C(t))
     * @param {Array<Float32Array>} timeFrames - Temporal data frames
     * @returns {Float32Array} - CBV map (mL/100g)
     */
    calculateCBV(timeFrames) {
        const width = this.timeSeriesData.width;
        const height = this.timeSeriesData.height;
        const cbvMap = new Float32Array(width * height);
        const dt = this.timeSeriesData.temporalResolution;
        
        // Integrate area under the curve
        for (let i = 0; i < width * height; i++) {
            let auc = 0; // Area under curve
            let maxValue = 0;
            
            for (let t = 0; t < timeFrames.length; t++) {
                const value = timeFrames[t][i] || 0;
                auc += value * dt; // Trapezoidal integration
                maxValue = Math.max(maxValue, value);
            }
            
            // CBV = AUC normalized by peak intensity
            cbvMap[i] = maxValue > 0 ? (auc / maxValue) * 4.0 : 0; // Normalized to mL/100g
        }
        
        return cbvMap;
    }
    
    /**
     * Calculate Mean Transit Time (MTT) from perfusion parameters
     * MTT = CBV / CBF
     * @param {Float32Array} cbvMap - Cerebral blood volume
     * @param {Float32Array} cbfMap - Cerebral blood flow
     * @returns {Float32Array} - MTT map (seconds)
     */
    calculateMTT(cbvMap, cbfMap) {
        const mttMap = new Float32Array(cbvMap.length);
        
        for (let i = 0; i < cbvMap.length; i++) {
            const cbv = cbvMap[i];
            const cbf = cbfMap[i];
            
            // MTT = CBV / CBF, with division by zero protection
            if (cbf > 1.0) {
                mttMap[i] = (cbv / cbf) * 60; // Convert to seconds
            } else {
                mttMap[i] = 0;
            }
        }
        
        return mttMap;
    }
    
    /**
     * Calculate Time-to-Peak (TTP) from time-intensity curve
     * @param {Array<Float32Array>} timeFrames - Temporal data frames
     * @returns {Float32Array} - TTP map (seconds)
     */
    calculateTTP(timeFrames) {
        const width = this.timeSeriesData.width;
        const height = this.timeSeriesData.height;
        const ttpMap = new Float32Array(width * height);
        const dt = this.timeSeriesData.temporalResolution;
        
        for (let i = 0; i < width * height; i++) {
            let maxValue = -Infinity;
            let maxTime = 0;
            
            for (let t = 0; t < timeFrames.length; t++) {
                const value = timeFrames[t][i] || 0;
                if (value > maxValue) {
                    maxValue = value;
                    maxTime = t * dt;
                }
            }
            
            ttpMap[i] = maxTime;
        }
        
        return ttpMap;
    }
    
    /**
     * Calculate maximum slope of the time-intensity curve
     * @private
     * @returns {Float32Array} - Maximum slope map
     */
    calculateMaxSlope() {
        if (!this.timeSeriesData || !this.timeSeriesData.frames) {
            return new Float32Array(this.timeSeriesData.width * this.timeSeriesData.height).fill(1.0);
        }
        
        const width = this.timeSeriesData.width;
        const height = this.timeSeriesData.height;
        const frames = this.timeSeriesData.frames;
        const dt = this.timeSeriesData.temporalResolution;
        const maxSlopeMap = new Float32Array(width * height);
        
        for (let i = 0; i < width * height; i++) {
            let maxSlope = 0;
            
            for (let t = 1; t < frames.length; t++) {
                const deltaI = (frames[t][i] || 0) - (frames[t - 1][i] || 0);
                const slope = Math.abs(deltaI) / dt;
                maxSlope = Math.max(maxSlope, slope);
            }
            
            maxSlopeMap[i] = maxSlope > 0 ? maxSlope : 1.0;
        }
        
        return maxSlopeMap;
    }
    
    /**
     * Create color-mapped visualization of perfusion parameter
     * @param {Float32Array} parameterMap - Parameter values
     * @param {string} parameter - Parameter type: 'cbf', 'cbv', 'mtt', 'ttp'
     * @param {Object} options - Display options
     * @returns {ImageData} - Colored visualization
     */
    visualizeParameter(parameterMap, parameter = 'cbf', options = {}) {
        const width = this.timeSeriesData.width;
        const height = this.timeSeriesData.height;
        
        const {
            colorMap = 'viridis',
            minValue = Math.min(...parameterMap) * 0.8,
            maxValue = Math.max(...parameterMap) * 1.2,
            showScale = true
        } = options;
        
        // Create image data
        this.canvas.width = width;
        this.canvas.height = height;
        const imageData = this.ctx.createImageData(width, height);
        const data = imageData.data;
        
        // Normalize and color map
        for (let i = 0; i < width * height; i++) {
            const value = parameterMap[i];
            const normalized = (value - minValue) / (maxValue - minValue);
            const clamped = Math.max(0, Math.min(1, normalized));
            
            // Apply color map
            const [r, g, b] = this.getColorMapValue(clamped, colorMap);
            
            const pixelIndex = i * 4;
            data[pixelIndex] = r;
            data[pixelIndex + 1] = g;
            data[pixelIndex + 2] = b;
            data[pixelIndex + 3] = 255;
        }
        
        return imageData;
    }
    
    /**
     * Get color map value using standard scientific colormaps
     * @private
     */
    getColorMapValue(value, colorMap = 'viridis') {
        // value: 0-1 range
        switch (colorMap) {
            case 'viridis':
                return this.colorMapViridis(value);
            case 'plasma':
                return this.colorMapPlasma(value);
            case 'hot':
                return this.colorMapHot(value);
            case 'cool':
                return this.colorMapCool(value);
            default:
                return this.colorMapViridis(value);
        }
    }
    
    /**
     * Viridis colormap (blue -> green -> yellow)
     * @private
     */
    colorMapViridis(t) {
        const r = Math.round(268 * t + (255 - 268 * t) * 0.25 * Math.cos(Math.PI * t));
        const g = Math.round(204 * t + 30);
        const b = Math.round(145 - 133 * t);
        return [r, g, b];
    }
    
    /**
     * Plasma colormap (purple -> red -> yellow)
     * @private
     */
    colorMapPlasma(t) {
        const r = Math.round(200 + 55 * Math.cos(2 * Math.PI * (t - 0.5)) + 55 * t);
        const g = Math.round(100 + 150 * t);
        const b = Math.round(255 * (1 - t));
        return [r, g, b];
    }
    
    /**
     * Hot colormap (black -> red -> yellow -> white)
     * @private
     */
    colorMapHot(t) {
        const r = t < 0.5 ? Math.round(255 * (t / 0.5)) : 255;
        const g = t < 0.5 ? 0 : Math.round(255 * ((t - 0.5) / 0.5));
        const b = t > 0.75 ? Math.round(255 * ((t - 0.75) / 0.25)) : 0;
        return [r, g, b];
    }
    
    /**
     * Cool colormap (black -> cyan -> white)
     * @private
     */
    colorMapCool(t) {
        const r = Math.round(255 * t);
        const g = Math.round(255 * t);
        const b = Math.round(255 * (1 - t));
        return [r, g, b];
    }
    
    /**
     * Complete perfusion analysis
     * @param {Array<Float32Array>} timeSeriesFrames - Time series data
     * @param {number} width - Image width
     * @param {number} height - Image height
     * @param {number} temporalResolution - Time between frames in seconds
     * @returns {Object} - Complete perfusion analysis results
     */
    async analyzePerfusion(timeSeriesFrames, width, height, temporalResolution = 1.0) {
        if (!this.initialized) {
            this.initialize();
        }
        
        console.log('Starting perfusion analysis...');
        const startTime = performance.now();
        
        try {
            // Load data
            this.loadTimeSeriesData(timeSeriesFrames, width, height, temporalResolution);
            
            // Get baseline (first few frames)
            const baselineFrames = timeSeriesFrames.slice(0, Math.min(3, timeSeriesFrames.length));
            const baselineData = new Float32Array(width * height);
            for (let i = 0; i < width * height; i++) {
                baselineData[i] = baselineFrames.reduce((sum, frame) => sum + (frame[i] || 0), 0) / baselineFrames.length;
            }
            
            // Calculate perfusion parameters
            const peakFrame = timeSeriesFrames[Math.floor(timeSeriesFrames.length / 2)];
            const cbfMap = this.calculateCBF(peakFrame, baselineData);
            const cbvMap = this.calculateCBV(timeSeriesFrames);
            const ttpMap = this.calculateTTP(timeSeriesFrames);
            const mttMap = this.calculateMTT(cbvMap, cbfMap);
            
            // Compute statistics
            const stats = {
                cbf: this.getStatistics(cbfMap),
                cbv: this.getStatistics(cbvMap),
                mtt: this.getStatistics(mttMap),
                ttp: this.getStatistics(ttpMap)
            };
            
            const processingTime = performance.now() - startTime;
            
            this.parameters = {
                cbfMap, cbvMap, mttMap, ttpMap,
                stats, processingTime
            };
            
            console.log(`Perfusion analysis complete: ${processingTime.toFixed(0)}ms`);
            console.log(`CBF: ${stats.cbf.mean.toFixed(1)} ± ${stats.cbf.stdDev.toFixed(1)} mL/100g/min`);
            console.log(`CBV: ${stats.cbv.mean.toFixed(1)} ± ${stats.cbv.stdDev.toFixed(1)} mL/100g`);
            console.log(`MTT: ${stats.mtt.mean.toFixed(1)} ± ${stats.mtt.stdDev.toFixed(1)} sec`);
            console.log(`TTP: ${stats.ttp.mean.toFixed(1)} ± ${stats.ttp.stdDev.toFixed(1)} sec`);
            
            return {
                success: true,
                cbfMap, cbvMap, mttMap, ttpMap,
                stats,
                processingTime,
                backend: 'canvas-2d'
            };
        } catch (error) {
            console.error('Perfusion analysis failed:', error);
            return { success: false, error: error.message };
        }
    }
    
    /**
     * Calculate statistics for a parameter map
     * @private
     */
    getStatistics(data) {
        const validData = Array.from(data).filter(v => v > 0 && isFinite(v));
        if (validData.length === 0) return { mean: 0, stdDev: 0, min: 0, max: 0 };
        
        const mean = validData.reduce((a, b) => a + b) / validData.length;
        const variance = validData.reduce((a, b) => a + (b - mean) ** 2, 0) / validData.length;
        const stdDev = Math.sqrt(variance);
        
        return {
            mean,
            stdDev,
            min: Math.min(...validData),
            max: Math.max(...validData)
        };
    }
    
    /**
     * Assess perfusion abnormality
     * @param {Object} stats - Statistics object from analysis
     * @returns {Object} - Abnormality assessment
     */
    assessAbnormality(stats) {
        const assessment = {
            cbfStatus: this.assessParameter(stats.cbf.mean, this.thresholds.cbf),
            cbvStatus: this.assessParameter(stats.cbv.mean, this.thresholds.cbv),
            mttStatus: this.assessParameter(stats.mtt.mean, this.thresholds.mtt),
            ttpStatus: stats.ttp.mean > 10 ? 'delayed' : 'normal'
        };
        
        // Determine overall perfusion status
        const abnormalCount = Object.values(assessment).filter(s => s === 'low' || s === 'high' || s === 'delayed').length;
        
        let overallStatus = 'normal';
        if (abnormalCount === 1) overallStatus = 'mildly_abnormal';
        if (abnormalCount === 2) overallStatus = 'moderately_abnormal';
        if (abnormalCount >= 3) overallStatus = 'severely_abnormal';
        
        return { ...assessment, overallStatus };
    }
    
    /**
     * Assess single parameter value
     * @private
     */
    assessParameter(value, thresholds) {
        if (value < thresholds.low) return 'low';
        if (value > thresholds.high) return 'high';
        return 'normal';
    }
    
    /**
     * Dispose resources
     */
    dispose() {
        this.ctx = null;
        this.timeSeriesData = null;
        this.parameters = null;
        this.initialized = false;
        console.log('PerfusionMapAnalyzer disposed');
    }
}

// Create singleton instance
const perfusionAnalyzer = new PerfusionMapAnalyzer();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { PerfusionMapAnalyzer, perfusionAnalyzer };
}
