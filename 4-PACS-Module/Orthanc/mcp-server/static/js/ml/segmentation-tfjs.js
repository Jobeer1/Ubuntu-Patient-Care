/**
 * Client-Side Segmentation Engine using TensorFlow.js / ONNX.js
 * Runs ML inference on user's GPU via WebGL backend
 * No server GPU required!
 */

class ClientSegmentationEngine {
    constructor() {
        this.models = {};
        this.backend = null;
        this.initialized = false;
        
        // Model configurations
        this.modelConfigs = {
            'vessels': {
                path: '/api/models/vessel-segmentation.onnx',
                inputSize: [128, 128, 128],
                threshold: 0.45
            },
            'organs': {
                path: '/api/models/organ-segmentation.onnx',
                inputSize: [128, 128, 128],
                threshold: 0.5
            },
            'nodules': {
                path: '/api/models/nodule-detection.onnx',
                inputSize: [128, 128, 128],
                threshold: 0.65
            }
        };
        
        console.log('ClientSegmentationEngine created');
    }
    
    /**
     * Initialize the engine and detect best backend
     */
    async initialize() {
        if (this.initialized) return;
        
        try {
            // Detect best available backend
            this.backend = await this.detectBackend();
            console.log(`Using backend: ${this.backend}`);
            
            // Initialize ONNX Runtime with WebGL
            if (typeof ort !== 'undefined') {
                ort.env.wasm.numThreads = navigator.hardwareConcurrency || 4;
                ort.env.wasm.simd = true;
                console.log('ONNX Runtime initialized');
            }
            
            this.initialized = true;
            return true;
        } catch (error) {
            console.error('Failed to initialize:', error);
            return false;
        }
    }
    
    /**
     * Detect best available compute backend
     */
    async detectBackend() {
        // Check for WebGPU (future)
        if (navigator.gpu) {
            try {
                const adapter = await navigator.gpu.requestAdapter();
                if (adapter) return 'webgpu';
            } catch (e) {
                console.log('WebGPU not available');
            }
        }
        
        // Check for WebGL 2.0
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl2');
        if (gl) {
            const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
            if (debugInfo) {
                const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
                console.log('GPU:', renderer);
            }
            return 'webgl';
        }
        
        // Fallback to WebAssembly (CPU)
        return 'wasm';
    }
    
    /**
     * Load a segmentation model
     */
    async loadModel(modelType) {
        if (!this.initialized) {
            await this.initialize();
        }
        
        if (this.models[modelType]) {
            console.log(`Model ${modelType} already loaded`);
            return true;
        }
        
        try {
            const config = this.modelConfigs[modelType];
            if (!config) {
                throw new Error(`Unknown model type: ${modelType}`);
            }
            
            console.log(`Loading ${modelType} model from ${config.path}...`);
            const startTime = performance.now();
            
            // Load ONNX model with WebGL backend
            const session = await ort.InferenceSession.create(config.path, {
                executionProviders: ['webgl', 'wasm'],  // GPU with CPU fallback
                graphOptimizationLevel: 'all'
            });
            
            const loadTime = performance.now() - startTime;
            console.log(`Model ${modelType} loaded in ${loadTime.toFixed(0)}ms`);
            
            this.models[modelType] = {
                session: session,
                config: config,
                loadTime: loadTime
            };
            
            return true;
        } catch (error) {
            console.error(`Failed to load model ${modelType}:`, error);
            return false;
        }
    }
    
    /**
     * Preprocess volume data for inference
     */
    preprocessVolume(volumeData, targetSize) {
        console.log('Preprocessing volume...');
        const startTime = performance.now();
        
        // Normalize to [0, 1] range (HU units: -1000 to 3000)
        const normalized = new Float32Array(volumeData.length);
        for (let i = 0; i < volumeData.length; i++) {
            const hu = Math.max(-1000, Math.min(3000, volumeData[i]));
            normalized[i] = (hu + 1000) / 4000.0;
        }
        
        // Resize if needed (simplified - in production use proper interpolation)
        let resized = normalized;
        const currentSize = Math.cbrt(volumeData.length);
        if (currentSize !== targetSize[0]) {
            console.log(`Resizing from ${currentSize}³ to ${targetSize[0]}³`);
            // For now, use simple sampling
            // In production, implement trilinear interpolation
            resized = this.simpleResize3D(normalized, currentSize, targetSize[0]);
        }
        
        const preprocessTime = performance.now() - startTime;
        console.log(`Preprocessing completed in ${preprocessTime.toFixed(0)}ms`);
        
        return resized;
    }
    
    /**
     * Simple 3D resize (nearest neighbor)
     * In production, use trilinear interpolation
     */
    simpleResize3D(data, oldSize, newSize) {
        const scale = oldSize / newSize;
        const resized = new Float32Array(newSize * newSize * newSize);
        
        for (let z = 0; z < newSize; z++) {
            for (let y = 0; y < newSize; y++) {
                for (let x = 0; x < newSize; x++) {
                    const oldX = Math.floor(x * scale);
                    const oldY = Math.floor(y * scale);
                    const oldZ = Math.floor(z * scale);
                    const oldIdx = oldZ * oldSize * oldSize + oldY * oldSize + oldX;
                    const newIdx = z * newSize * newSize + y * newSize + x;
                    resized[newIdx] = data[oldIdx];
                }
            }
        }
        
        return resized;
    }
    
    /**
     * Run segmentation inference on client GPU
     */
    async segment(volumeData, modelType, options = {}) {
        try {
            const startTime = performance.now();
            
            // Load model if not already loaded
            if (!this.models[modelType]) {
                await this.loadModel(modelType);
            }
            
            const model = this.models[modelType];
            const config = model.config;
            const threshold = options.threshold || config.threshold;
            
            // Preprocess volume
            const preprocessed = this.preprocessVolume(volumeData, config.inputSize);
            
            // Create input tensor [batch, channel, depth, height, width]
            const inputTensor = new ort.Tensor(
                'float32',
                preprocessed,
                [1, 1, ...config.inputSize]
            );
            
            console.log(`Running inference on ${this.backend}...`);
            const inferenceStart = performance.now();
            
            // Run inference on GPU
            const results = await model.session.run({ input: inputTensor });
            
            const inferenceTime = performance.now() - inferenceStart;
            console.log(`Inference completed in ${inferenceTime.toFixed(0)}ms`);
            
            // Get output tensor
            const outputTensor = results.output || results[Object.keys(results)[0]];
            const outputData = outputTensor.data;
            
            // Apply threshold
            const mask = new Uint8Array(outputData.length);
            for (let i = 0; i < outputData.length; i++) {
                mask[i] = outputData[i] > threshold ? 1 : 0;
            }
            
            // Post-process mask
            const processedMask = this.postprocessMask(mask, config.inputSize);
            
            const totalTime = performance.now() - startTime;
            
            return {
                success: true,
                mask: processedMask,
                modelType: modelType,
                threshold: threshold,
                inferenceTime: inferenceTime,
                totalTime: totalTime,
                backend: this.backend,
                statistics: this.calculateStatistics(processedMask)
            };
            
        } catch (error) {
            console.error('Segmentation failed:', error);
            return {
                success: false,
                error: error.message,
                modelType: modelType
            };
        }
    }
    
    /**
     * Post-process segmentation mask
     */
    postprocessMask(mask, size) {
        console.log('Post-processing mask...');
        
        // Simple morphological operations
        // In production, implement proper morphological closing/opening
        
        // Remove small components (< 100 voxels)
        const cleaned = this.removeSmallComponents(mask, size, 100);
        
        return cleaned;
    }
    
    /**
     * Remove small connected components
     */
    removeSmallComponents(mask, size, minSize) {
        // Simplified version - in production use proper connected component analysis
        // For now, just return the mask
        return mask;
    }
    
    /**
     * Calculate segmentation statistics
     */
    calculateStatistics(mask) {
        let segmentedVoxels = 0;
        for (let i = 0; i < mask.length; i++) {
            if (mask[i] > 0) segmentedVoxels++;
        }
        
        const totalVoxels = mask.length;
        const percentage = (segmentedVoxels / totalVoxels) * 100;
        
        return {
            totalVoxels: totalVoxels,
            segmentedVoxels: segmentedVoxels,
            percentage: percentage.toFixed(2),
            volumeMm3: segmentedVoxels  // Assuming 1mm³ voxels
        };
    }
    
    /**
     * Segment organs (14 anatomical structures)
     */
    async segmentOrgans(volumeData, options = {}) {
        console.log('Starting organ segmentation on client GPU...');
        return await this.segment(volumeData, 'organs', options);
    }
    
    /**
     * Segment blood vessels
     */
    async segmentVessels(volumeData, options = {}) {
        console.log('Starting vessel segmentation on client GPU...');
        return await this.segment(volumeData, 'vessels', options);
    }
    
    /**
     * Detect lung nodules
     */
    async detectNodules(volumeData, options = {}) {
        console.log('Starting nodule detection on client GPU...');
        const result = await this.segment(volumeData, 'nodules', options);
        
        if (result.success) {
            // Extract individual nodules
            result.nodules = this.extractNodules(result.mask, options.minSizeMm || 4.0);
        }
        
        return result;
    }
    
    /**
     * Extract individual nodules from mask
     */
    extractNodules(mask, minSizeMm) {
        // Simplified version - in production use proper connected component labeling
        const nodules = [];
        
        // Mock nodule extraction for now
        // In production, implement proper 3D connected component analysis
        
        return nodules;
    }
    
    /**
     * Get system information
     */
    getSystemInfo() {
        return {
            backend: this.backend,
            initialized: this.initialized,
            modelsLoaded: Object.keys(this.models),
            hardwareConcurrency: navigator.hardwareConcurrency,
            deviceMemory: navigator.deviceMemory || 'unknown',
            platform: navigator.platform
        };
    }
    
    /**
     * Cleanup resources
     */
    dispose() {
        for (const modelType in this.models) {
            const model = this.models[modelType];
            if (model.session) {
                model.session.release();
            }
        }
        this.models = {};
        this.initialized = false;
        console.log('ClientSegmentationEngine disposed');
    }
}

// Create singleton instance
const clientSegmentationEngine = new ClientSegmentationEngine();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ClientSegmentationEngine, clientSegmentationEngine };
}
